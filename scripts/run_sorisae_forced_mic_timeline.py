#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = "com.parkcheolhong.worldlinco"
DEFAULT_ACTIVITY = ".MainActivity"
DEFAULT_OPEN_X = int(os.getenv("SORISAE_FORCE_OPEN_X", "739"))
DEFAULT_OPEN_Y = int(os.getenv("SORISAE_FORCE_OPEN_Y", "479"))
DEFAULT_MIC_X = int(os.getenv("SORISAE_FORCE_MIC_X", "400"))
DEFAULT_MIC_Y = int(os.getenv("SORISAE_FORCE_MIC_Y", "1000"))
DEFAULT_WAIT_AFTER_MIC_SEC = int(os.getenv("SORISAE_FORCE_WAIT_AFTER_MIC_SEC", "55"))
FIXTURE_M4A = ROOT / "scripts" / "fixtures" / "sorisae_probe_ko_speech.m4a"
DEFAULT_LOGIN_EMAIL = os.getenv("SORISAE_FORCE_LOGIN_EMAIL", "119cash@naver.com")
DEFAULT_LOGIN_PASSWORD_FILE = ROOT / ".runtime" / "secrets" / "fixed_admin_password.txt"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _run(cmd: list[str], timeout: float = 90.0, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)


def _adb(device: str, *args: str, timeout: float = 90.0) -> subprocess.CompletedProcess[str]:
    return _run(["adb", "-s", device, *args], timeout=timeout)


def _play_audio_on_host(m4a: Path) -> None:
    ffplay = shutil.which("ffplay")
    if not ffplay:
        raise RuntimeError("ffplay not found on PATH")
    proc = subprocess.Popen(
        [ffplay, "-nodisp", "-autoexit", "-volume", "100", str(m4a)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()


def _center_from_bounds(bounds: str) -> tuple[int, int] | None:
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def _dump_ui_xml(device: str, out_path: Path) -> str:
    remote = "/sdcard/Download/worldlinco_ui_dump.xml"
    _adb(device, "shell", "uiautomator", "dump", remote, timeout=30)
    _adb(device, "pull", remote, str(out_path), timeout=30)
    if not out_path.exists():
        return ""
    return out_path.read_text(encoding="utf-8", errors="ignore")


def _find_center_from_ui(xml_text: str, selector: str) -> tuple[int, int] | None:
    if not xml_text.strip():
        return None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    for node in root.iter("node"):
        rid = node.attrib.get("resource-id", "")
        desc = node.attrib.get("content-desc", "")
        text = node.attrib.get("text", "")
        hay = f"{rid} {desc} {text}"
        if selector in hay:
            return _center_from_bounds(node.attrib.get("bounds", ""))
    return None


def _find_first_center_from_ui(xml_text: str, selectors: list[str]) -> tuple[int, int] | None:
    for selector in selectors:
        center = _find_center_from_ui(xml_text, selector)
        if center:
            return center
    return None


def _escape_adb_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace(" ", "%s")
    escaped = escaped.replace("@", "\\@")
    escaped = escaped.replace(".", "\\.")
    escaped = escaped.replace("%", "\\%")
    return escaped


def _tap_selector_or_fallback(device: str, xml_text: str, selector: str, fallback: tuple[int, int]) -> tuple[int, int]:
    center = _find_center_from_ui(xml_text, selector)
    if not center:
        center = fallback
    _adb(device, "shell", "input", "tap", str(center[0]), str(center[1]))
    return center


def _read_login_password() -> str:
    env_pw = (os.getenv("WORLDLINCO_VOIP_API_PASSWORD") or "").strip()
    if env_pw:
        return env_pw
    if DEFAULT_LOGIN_PASSWORD_FILE.exists():
        return DEFAULT_LOGIN_PASSWORD_FILE.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def _input_text(device: str, value: str) -> None:
    for _ in range(48):
        _adb(device, "shell", "input", "keyevent", "67")
    _adb(device, "shell", "input", "text", _escape_adb_text(value))


def _ensure_logged_in(device: str, work_dir: Path, email: str) -> bool:
    password = _read_login_password()
    if not email or not password:
        return False

    xml_path = work_dir / "ui-login-check.xml"
    xml_text = _dump_ui_xml(device, xml_path)
    unauth_markers = [
        "worldlinco-inline-auth-panel",
        "worldlinco-inline-open-login-button",
        "worldlinco-header-login-button",
        "로그인이 필요해요",
        "로그인이 필요합니다",
        "인증 상태를 확인해 주세요",
    ]

    is_unauth = any(m in xml_text for m in unauth_markers)
    if not is_unauth and "worldlinco-auth-login-submit-button" not in xml_text:
        return True

    # Open login modal from lobby/header CTA when needed.
    if "worldlinco-auth-email-input" not in xml_text:
        center = _find_first_center_from_ui(
            xml_text,
            ["worldlinco-inline-open-login-button", "worldlinco-header-login-button", "로그인 / 회원가입"],
        )
        if center:
            _adb(device, "shell", "input", "tap", str(center[0]), str(center[1]))
            time.sleep(2)
            xml_text = _dump_ui_xml(device, xml_path)

    _tap_selector_or_fallback(device, xml_text, "worldlinco-auth-email-input", (422, 605))
    time.sleep(0.4)
    _input_text(device, email)
    time.sleep(0.4)

    xml_text = _dump_ui_xml(device, xml_path)
    _tap_selector_or_fallback(device, xml_text, "worldlinco-auth-password-input", (398, 755))
    time.sleep(0.4)
    _input_text(device, password)
    time.sleep(0.4)

    xml_text = _dump_ui_xml(device, xml_path)
    _tap_selector_or_fallback(device, xml_text, "worldlinco-auth-login-submit-button", (400, 860))
    time.sleep(8)

    xml_text = _dump_ui_xml(device, xml_path)
    still_unauth = any(m in xml_text for m in unauth_markers)
    return not still_unauth


def _filter_face_lines(log_text: str) -> list[str]:
    out: list[str] = []
    for line in log_text.splitlines():
        if "[FACE_CONVERSATION]" in line or "[FACE_CAPTURE_TRACE]" in line or "[COMPANION_HANDLER]" in line:
            out.append(line)
    return out


def _extract_payload_json(line: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}\s*$", line)
    if not m:
        return None
    raw = m.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _analyze_face_lines(lines: list[str]) -> dict[str, Any]:
    post_start = False
    segment_response_any = False
    segment_response_ok_true = False
    segment_response_sorisae_ok_true = False
    segment_lines: list[str] = []

    for line in lines:
        payload = _extract_payload_json(line)
        if not payload:
            continue
        event = str(payload.get("event") or "")
        if event == "post_start":
            post_start = True
        if event == "segment_response":
            segment_response_any = True
            segment_lines.append(line)
            ok = bool(payload.get("ok"))
            route = str(payload.get("route") or "")
            if ok:
                segment_response_ok_true = True
                if route == "sorisae":
                    segment_response_sorisae_ok_true = True

    return {
        "post_start_present": post_start,
        "segment_response_present": segment_response_any,
        "segment_response_ok_true": segment_response_ok_true,
        "segment_response_sorisae_ok_true": segment_response_sorisae_ok_true,
        "segment_response_lines": segment_lines,
    }


def _single_round(
    device: str,
    out_dir: Path,
    package_name: str,
    activity: str,
    open_x: int,
    open_y: int,
    mic_x: int,
    mic_y: int,
    wait_after_mic_sec: int,
    login_email: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ui_before = out_dir / "ui-before-mic.xml"
    ui_after = out_dir / "ui-after-mic.xml"
    log_all = out_dir / "logcat-reactnative-time.log"
    log_face = out_dir / "logcat-face-tags-time.log"

    _adb(device, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    _adb(device, "shell", "media", "volume", "--stream", "3", "--set", "15")
    _adb(device, "shell", "media", "volume", "--stream", "1", "--set", "15")
    _adb(device, "shell", "am", "force-stop", package_name)
    _adb(device, "logcat", "-c")
    _adb(device, "shell", "am", "start", "-n", f"{package_name}/{activity}")
    time.sleep(12)

    login_ok = _ensure_logged_in(device, out_dir, login_email)
    if login_ok:
        time.sleep(2)

    ui_home = _dump_ui_xml(device, out_dir / "ui-home-before-open.xml")
    open_center = _find_first_center_from_ui(
        ui_home,
        [
            "worldlinco-home-face-hero",
            "worldlinco-sorisae-fab",
            "🐦",
            "worldlinco-companion-voicecall-toggle",
            "worldlinco-section-rail-chat-button",
            "소리새",
            "대화",
        ],
    )
    if not open_center:
        open_center = (open_x, open_y)
    _adb(device, "shell", "input", "tap", str(open_center[0]), str(open_center[1]))
    time.sleep(3)

    ui_text = _dump_ui_xml(device, ui_before)
    mic_center = _find_first_center_from_ui(
        ui_text,
        [
            "worldlinco-sorisae-window-mic",
            "worldlinco-face-screen-mic",
            "worldlinco-sorisae-window",
            "마이크",
        ],
    )
    mic_from_selector = bool(mic_center)
    if not mic_center:
        mic_center = (mic_x, mic_y)

    _adb(device, "shell", "input", "tap", str(mic_center[0]), str(mic_center[1]))
    time.sleep(1)
    _dump_ui_xml(device, ui_after)

    _play_audio_on_host(FIXTURE_M4A)
    time.sleep(wait_after_mic_sec)
    _adb(device, "shell", "input", "keyevent", "KEYCODE_WAKEUP")

    log_proc = _adb(device, "logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S", timeout=120)
    log_text = log_proc.stdout or ""
    log_all.write_text(log_text, encoding="utf-8")

    face_lines = _filter_face_lines(log_text)
    log_face.write_text("\n".join(face_lines) + ("\n" if face_lines else ""), encoding="utf-8")
    analysis = _analyze_face_lines(face_lines)

    summary = {
        "device": device,
        "login_ok": login_ok,
        "mic_tap": {
            "selector_used": mic_from_selector,
            "x": mic_center[0],
            "y": mic_center[1],
        },
        "analysis": analysis,
        "pass": bool(analysis["post_start_present"] and analysis["segment_response_sorisae_ok_true"]),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "verdict.txt").write_text(
        "PASS\n" if summary["pass"] else "FAIL\n"
        + f"post_start_present={analysis['post_start_present']}\n"
        + f"segment_response_sorisae_ok_true={analysis['segment_response_sorisae_ok_true']}\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run forced Sorisae mic scenario and capture FACE tag evidence")
    parser.add_argument("--adb-device", required=True)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--package-name", default=DEFAULT_PACKAGE)
    parser.add_argument("--activity", default=DEFAULT_ACTIVITY)
    parser.add_argument("--open-x", type=int, default=DEFAULT_OPEN_X)
    parser.add_argument("--open-y", type=int, default=DEFAULT_OPEN_Y)
    parser.add_argument("--mic-x", type=int, default=DEFAULT_MIC_X)
    parser.add_argument("--mic-y", type=int, default=DEFAULT_MIC_Y)
    parser.add_argument("--wait-after-mic-sec", type=int, default=DEFAULT_WAIT_AFTER_MIC_SEC)
    parser.add_argument("--login-email", default=DEFAULT_LOGIN_EMAIL)
    args = parser.parse_args()

    if not FIXTURE_M4A.exists() or FIXTURE_M4A.stat().st_size < 1000:
        raise SystemExit(f"fixture missing or too small: {FIXTURE_M4A}")

    stamp = _utc_stamp()
    base = ROOT / "evidence" / f"sorisae-forced-mic-timeline-{stamp}"
    base.mkdir(parents=True, exist_ok=True)

    rounds: list[dict[str, Any]] = []
    for i in range(1, max(1, args.rounds) + 1):
        run_dir = base / f"round-{i}"
        print(f"[round {i}] start -> {run_dir}")
        summary = _single_round(
            device=args.adb_device,
            out_dir=run_dir,
            package_name=args.package_name,
            activity=args.activity,
            open_x=args.open_x,
            open_y=args.open_y,
            mic_x=args.mic_x,
            mic_y=args.mic_y,
            wait_after_mic_sec=args.wait_after_mic_sec,
            login_email=args.login_email,
        )
        print(
            f"[round {i}] pass={summary['pass']} "
            f"post_start={summary['analysis']['post_start_present']} "
            f"segment_response_sorisae_ok={summary['analysis']['segment_response_sorisae_ok_true']}"
        )
        rounds.append(summary)

    overall = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "adb_device": args.adb_device,
        "rounds": rounds,
        "all_passed": all(r.get("pass") for r in rounds),
    }
    report_path = base / "report.json"
    report_path.write_text(json.dumps(overall, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[report] {report_path}")
    return 0 if overall["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())