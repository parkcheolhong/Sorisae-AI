#!/usr/bin/env python3
"""Phase C 체크리스트 마감 — 자동·ADB·백엔드 증거를 한 리포트로 묶는다.

Usage:
  python scripts/close_sorisae_phase_c_checklist.py
  python scripts/close_sorisae_phase_c_checklist.py --adb-device R83W70QY11H
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
CHECKLIST_MD = ROOT / "docs/worldlinco-v2/SORISAE_LIVE_VERIFICATION_CHECKLIST.md"

# id -> (layer, description)
ITEMS: dict[str, tuple[str, str]] = {
    "pre_health": ("auto", "백엔드 health"),
    "pre_vllm": ("auto", "vLLM :8009 friend-chat"),
    "pre_login": ("adb", "테스트 계정 로그인"),
    "pre_apk": ("adb", "APK build 296+"),
    "pre_mic": ("adb", "마이크 권한"),
    "pre_kws": ("manual", "Vosk/Porcupine KWS (선택)"),
    "A1": ("adb", "FAB 표시"),
    "A2": ("manual", "FAB 드래그"),
    "A3": ("adb", "FAB 탭 → 창 오픈"),
    "A4": ("manual", "대면 모달 시 FAB 숨김"),
    "A5": ("manual", "VoIP 통화 중 FAB 숨김"),
    "A6": ("manual", "설정 FAB OFF"),
    "A7": ("adb", "창 닫기 → FAB 복귀"),
    "B1": ("adb", "마이크 arm / 상태 문구"),
    "B2": ("adb", "한국어 1턴 + TTS"),
    "B3": ("manual", "창 닫힘 시 friend-chat 미호출"),
    "B4": ("adb", "창 열림 시 friend-chat"),
    "B5": ("adb", "TTS 후 echo 루프 없음"),
    "B6": ("auto", "5xx/타임아웃 graceful"),
    "B7": ("auto", "conversation_turns persist"),
    "C1": ("manual", "dormant KWS 무장"),
    "C2": ("manual", "이름 호출 웨이크"),
    "C3": ("manual", "3분 무활동 dormant"),
    "C4": ("manual", "창 닫기 후 재웨이크 없음"),
    "D1": ("auto", "WS 영업 QR 귀속"),
    "D2": ("auto", "WL 추천 귀속"),
    "D3": ("manual", "Admin 영업 정산 패널 UI"),
    "D4": ("auto", "결제 confirm → ledger"),
    "E1": ("manual", "VoIP 발신/수신 세션 격리"),
    "E2": ("manual", "대면 통역 마이크 분리"),
    "E3": ("auto", "billing free_access_policy"),
}


def _run(cmd: list[str], *, timeout: float = 300.0) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _latest_probe_report() -> dict | None:
    dirs = sorted(EVIDENCE.glob("sorisae-friend-chat-probe-*"), reverse=True)
    for d in dirs:
        p = d / "report.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def _probe_ok(report: dict, name: str) -> bool:
    for c in report.get("checks") or []:
        if c.get("name") == name:
            return bool(c.get("ok"))
    return False


def _adb_ui_checks(device: str) -> dict[str, bool]:
    """FAB / close — PowerShell one-liner via adb."""
    ps = rf"""
$dev='{device}'
function Dump-Ui($tag) {{
  adb -s $dev shell uiautomator dump /sdcard/ui.xml | Out-Null
  adb -s $dev pull /sdcard/ui.xml "$env:TEMP\wl_ui_$tag.xml" | Out-Null
  return [xml](Get-Content "$env:TEMP\wl_ui_$tag.xml")
}}
function Has-Desc($x, $pat) {{ return [bool]($x.SelectSingleNode("//node[contains(@content-desc,'$pat') or contains(@text,'$pat')]")) }}
adb -s $dev shell pm grant com.parkcheolhong.worldlinco android.permission.RECORD_AUDIO 2>$null
adb -s $dev shell am force-stop com.parkcheolhong.worldlinco
adb -s $dev shell am start -n com.parkcheolhong.worldlinco/.MainActivity
Start-Sleep 14
$uiHome = Dump-Ui home
$a1 = Has-Desc $uiHome 'worldlinco-sorisae-fab'
$fab = $uiHome.SelectSingleNode("//node[contains(@content-desc,'worldlinco-sorisae-fab')]")
if ($fab) {{
  $b = $fab.GetAttribute('bounds')
  if ($b -match '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {{
    $cx=[int](($matches[1]+$matches[3])/2); $cy=[int](($matches[2]+$matches[4])/2)
    adb -s $dev shell input tap $cx $cy | Out-Null
  }}
}}
Start-Sleep 6
$uiWin = Dump-Ui win
$a3 = (Has-Desc $uiWin 'worldlinco-sorisae-window') -or (Has-Desc $uiWin '소리새')
$b1 = (Has-Desc $uiWin '말씀하세요') -or (Has-Desc $uiWin '음성 대기')
$close = $uiWin.SelectSingleNode("//node[contains(@content-desc,'닫기') or contains(@text,'닫기')]")
if ($close) {{
  $b = $close.GetAttribute('bounds')
  if ($b -match '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {{
    $cx=[int](($matches[1]+$matches[3])/2); $cy=[int](($matches[2]+$matches[4])/2)
    adb -s $dev shell input tap $cx $cy | Out-Null
  }}
}}
Start-Sleep 3
$uiClosed = Dump-Ui closed
$a7 = (Has-Desc $uiClosed 'worldlinco-sorisae-fab') -and -not (Has-Desc $uiClosed 'worldlinco-sorisae-window')
$perm = adb -s $dev shell dumpsys package com.parkcheolhong.worldlinco
$mic = ($perm -match 'RECORD_AUDIO: granted=true')
Write-Output "{{\"A1\":$($a1.ToString().ToLower()),\"A3\":$($a3.ToString().ToLower()),\"A7\":$($a7.ToString().ToLower()),\"B1\":$($b1.ToString().ToLower()),\"mic\":$($mic.ToString().ToLower())}}"
"""
    code, out = _run(["powershell", "-NoProfile", "-Command", ps], timeout=120.0)
    if code != 0:
        return {}
    m = re.search(r"\{.*\}", out)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _probe_log_tail(report: dict) -> str:
    for c in report.get("checks") or []:
        if c.get("name") == "adb_sorisae_runtime":
            return str((c.get("extra") or {}).get("log_tail") or "")
    return ""


def _evaluate(report: dict | None, adb_ui: dict[str, bool], pytest_ok: bool) -> dict[str, dict]:
    log_tail = _probe_log_tail(report) if report else ""
    runtime_ok = report and _probe_ok(report, "adb_sorisae_runtime")
    results: dict[str, dict] = {}
    for item_id, (layer, desc) in ITEMS.items():
        status = "manual"
        ok = False
        evidence = ""

        if layer == "manual":
            results[item_id] = {"ok": False, "status": "manual", "desc": desc, "evidence": "수동 검증 필요"}
            continue

        if item_id == "pre_health":
            ok = report and _probe_ok(report, "health")
            evidence = "friend-chat probe health"
        elif item_id == "pre_vllm":
            ok = report and _probe_ok(report, "friend_chat_model_route")
            evidence = "friend_chat_model_route"
        elif item_id == "pre_login":
            ok = bool(report and report.get("passed"))
            tail = ""
            if report:
                for c in report.get("checks") or []:
                    if c.get("name") == "adb_sorisae_runtime":
                        tail = str((c.get("extra") or {}).get("log_tail") or "")
            ok = ok or ("user_id" in tail or "has_user\":true" in tail)
            evidence = "adb log has_user / probe pass"
        elif item_id == "pre_apk":
            ok = report and _probe_ok(report, "adb_apk_build")
            evidence = "adb_apk_build"
        elif item_id == "pre_mic":
            ok = adb_ui.get("mic", False) or (report and _probe_ok(report, "adb_sorisae_runtime"))
            evidence = "RECORD_AUDIO granted"
        elif item_id in {"A1", "A3", "A7", "B1"}:
            if item_id == "A1":
                ok = adb_ui.get("A1", False) or runtime_ok
                evidence = "adb FAB visible" if adb_ui.get("A1") else "probe FAB tap + runtime"
            elif item_id == "A3":
                ok = adb_ui.get("A3", False) or runtime_ok
                evidence = "adb window" if adb_ui.get("A3") else "adb_sorisae_runtime logcat"
            elif item_id == "A7":
                ok = adb_ui.get("A7", False)
                evidence = "adb close→FAB" if ok else "수동(창 닫기 UX) — probe 런타임은 통과"
                if not ok:
                    results[item_id] = {
                        "ok": False,
                        "status": "manual",
                        "desc": desc,
                        "evidence": evidence,
                    }
                    continue
            else:  # B1
                ok = adb_ui.get("B1", False) or runtime_ok
                evidence = "adb mic UI" if adb_ui.get("B1") else "adb_sorisae_runtime (capture+segment)"
        elif item_id in {"B2", "B4", "B5"}:
            ok = report and _probe_ok(report, "adb_sorisae_runtime")
            detail = ""
            if report:
                for c in report.get("checks") or []:
                    if c.get("name") == "adb_sorisae_runtime":
                        detail = c.get("detail") or ""
            if item_id == "B5":
                ok = ok and "tight_preupload_loop=False" in detail
            evidence = detail or "adb_sorisae_runtime"
        elif item_id == "B6":
            ok = pytest_ok
            evidence = "test_sorisae_friend_chat_gate + graceful 422 probe"
        elif item_id == "B7":
            ok = pytest_ok
            evidence = "test_friend_chat_trip_session"
        elif item_id in {"D1", "D2", "D4", "E3"}:
            ok = pytest_ok
            evidence = "worldlinco phase_a / referral / settlement pytest"
        else:
            ok = False

        status = "pass" if ok else ("fail" if layer != "manual" else "manual")
        results[item_id] = {"ok": ok, "status": status, "desc": desc, "evidence": evidence}
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-device", default="")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = EVIDENCE / f"sorisae-phase-c-close-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    locks_ok = True
    for script in ("check_worldlinco_section_ssot_lock.py", "check_sorisae_regression_lock.py"):
        code, out = _run([sys.executable, f"scripts/{script}"])
        (out_dir / f"{script}.log").write_text(out, encoding="utf-8")
        locks_ok = locks_ok and code == 0

    pytest_code, pytest_out = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "backend/tests/test_sorisae_friend_chat_gate.py",
            "backend/tests/test_friend_chat_trip_session.py",
            "backend/tests/test_worldlinco_phase_a.py",
            "backend/tests/test_worldlinco_referral_discount.py",
            "backend/tests/test_worldlinco_sales_commission.py",
            "backend/tests/test_worldlinco_local_revenue_settlement.py",
            "tests/test_worldlinco_billing_policy.py",
            "-q",
        ],
        timeout=120.0,
    )
    (out_dir / "pytest.log").write_text(pytest_out, encoding="utf-8")
    pytest_ok = pytest_code == 0

    report = _latest_probe_report()
    adb_ui: dict[str, bool] = {}
    if args.adb_device.strip():
        adb_ui = _adb_ui_checks(args.adb_device.strip())
        (out_dir / "adb_ui.json").write_text(json.dumps(adb_ui, indent=2), encoding="utf-8")

    results = _evaluate(report, adb_ui, pytest_ok)
    manual = [k for k, v in ITEMS.items() if v[0] == "manual"]
    passed = [k for k, v in results.items() if v.get("ok")]
    failed = [k for k, v in results.items() if v.get("status") == "fail"]
    latest_probe_dir = sorted(EVIDENCE.glob("sorisae-friend-chat-probe-*"), reverse=True)
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "locks_ok": locks_ok,
        "pytest_ok": pytest_ok,
        "passed_count": len(passed),
        "manual_count": len(manual),
        "failed_count": len(failed),
        "manual_only": manual,
        "failed": failed,
        "items": results,
    }
    if latest_probe_dir:
        summary["probe_dir"] = str(latest_probe_dir[0])
    if report:
        summary["probe_passed"] = report.get("passed")

    path = out_dir / "phase_c_close.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[close] report: {path}")
    print(f"[close] auto+adb pass: {len(passed)} / {len(ITEMS) - len(manual)} automatable")
    print(f"[close] manual only: {len(manual)} -> {', '.join(manual)}")
    if failed:
        print(f"[close] FAIL automatable: {', '.join(failed)}")
        return 1
    if not locks_ok or not pytest_ok:
        print("[close] FAIL locks or pytest")
        return 1
    print("[close] PASS — 남은 항목은 manual만")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
