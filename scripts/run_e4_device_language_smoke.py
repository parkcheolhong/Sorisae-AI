#!/usr/bin/env python3
"""E-4 실기기 4언어(ko/en/ja/zh) 스모크 — ADB UI 덤프 + 혼용 검사."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVICE = (sys.argv[1] if len(sys.argv) > 1 else "172.30.1.19:5555").strip()
PKG = "com.parkcheolhong.worldlinco"
EMAIL = "119cash@naver.com"
PASSWORD = (sys.argv[2] if len(sys.argv) > 2 else "").strip()


def resolve_password() -> str:
    if PASSWORD:
        return PASSWORD
    proc = subprocess.run(
        ["docker", "exec", "devanalysis114-backend", "cat", "/run/codeai-secrets/fixed_admin_password.txt"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "").strip()


EVIDENCE = ROOT / "evidence" / "build312-plus-331"
REMOTE_DUMP = "/sdcard/wl-e4-ui.xml"

LANGS = ("ko", "en", "ja", "zh")
SCREENS = (
    ("workspace", "worldlinco-section-rail-chat-button"),
    ("chat", "worldlinco-section-rail-chat-button"),
    ("tourism", "worldlinco-section-rail-tourism-promo-button"),
)

HANGUL = re.compile(r"[\uAC00-\uD7A3]")
CJK = re.compile(r"[\u4E00-\u9FFF]")
KANA = re.compile(r"[\u3040-\u30FF]")
EMAIL_RE = re.compile(r"@")
IGNORE_HANGUL = re.compile(r"^(저장|Saved|保存|已保存)|@|\.com$")
LANG_PAIR_BADGE = re.compile(r"⇄")


def adb(*args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["adb", "-s", DEVICE, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def dump_ui() -> str:
    adb("shell", "uiautomator", "dump", REMOTE_DUMP)
    proc = adb("shell", "cat", REMOTE_DUMP)
    return proc.stdout or ""


def save_dump(name: str, xml: str) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / name
    path.write_text(xml, encoding="utf-8")
    return path


def find_center(xml: str, needle: str) -> tuple[int, int] | None:
    patterns = [
        rf'content-desc="{re.escape(needle)}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        rf'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*content-desc="{re.escape(needle)}"',
        rf'resource-id="{re.escape(needle)}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        rf'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*resource-id="{re.escape(needle)}"',
    ]
    for pat in patterns:
        m = re.search(pat, xml)
        if m:
            x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def tap(center: tuple[int, int] | None, fallback: tuple[int, int] | None = None) -> bool:
    if center:
        cx, cy = center
    elif fallback:
        cx, cy = fallback
    else:
        return False
    adb("shell", "input", "tap", str(cx), str(cy))
    return True


def extract_texts(xml: str) -> list[str]:
    raw = re.findall(r'text="([^"]{1,160})"', xml)
    out: list[str] = []
    for t in raw:
        t = t.replace("&#128038;", "").replace("&#128222;", "").replace("&#128172;", "").strip()
        if t and t not in out:
            out.append(t)
    return out


def analyze(lang: str, texts: list[str]) -> list[str]:
    issues: list[str] = []

    def is_noise(text: str) -> bool:
        if EMAIL_RE.search(text):
            return True
        if LANG_PAIR_BADGE.search(text):
            return True
        if len(text.strip()) <= 3 and HANGUL.search(text):
            return True
        return False

    if lang != "ko":
        hangul = [t for t in texts if HANGUL.search(t) and not is_noise(t)]
        if hangul:
            issues.append(f"unexpected_hangul={hangul[:8]}")
    if lang == "ja":
        if not any(KANA.search(t) or CJK.search(t) for t in texts):
            issues.append("ja_screen_no_japanese_script")
    if lang == "zh":
        if not any(CJK.search(t) for t in texts):
            issues.append("zh_screen_no_chinese_script")
    return issues


def is_logged_in(xml: str) -> bool:
    if find_center(xml, "worldlinco-auth-login-submit-button"):
        return False
    return bool(find_center(xml, "worldlinco-bottom-tab-settings"))


def adb_input_text(raw: str) -> None:
    escaped = (
        raw.replace("\\", "\\\\")
        .replace(" ", "%s")
        .replace("@", "\\@")
        .replace("#", "\\#")
        .replace("&", "\\&")
        .replace(";", "\\;")
        .replace("|", "\\|")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("'", "\\'")
    )
    adb("shell", "input", "text", escaped)


def clear_field() -> None:
    for _ in range(48):
        adb("shell", "input", "keyevent", "67")


def ensure_login() -> None:
    for _ in range(12):
        if is_logged_in(dump_ui()):
            return
        time.sleep(5)
    xml = dump_ui()
    if is_logged_in(xml):
        return
    if find_center(xml, "worldlinco-auth-open-login-modal-button"):
        tap(find_center(xml, "worldlinco-auth-open-login-modal-button"), (540, 1700))
        time.sleep(1.5)
    elif find_center(xml, "worldlinco-header-login-button"):
        tap(find_center(xml, "worldlinco-header-login-button"), (950, 120))
        time.sleep(1.5)
    elif find_center(xml, "worldlinco-inline-open-login-button"):
        tap(find_center(xml, "worldlinco-inline-open-login-button"), (540, 1200))
        time.sleep(1.5)
    xml = dump_ui()
    email = find_center(xml, "worldlinco-auth-email-input")
    if email and resolve_password():
        pwd_text = resolve_password()
        tap(email, email)
        clear_field()
        adb_input_text(EMAIL)
        pwd = find_center(dump_ui(), "worldlinco-auth-password-input") or email
        tap(pwd, pwd)
        clear_field()
        adb_input_text(pwd_text)
        submit = find_center(dump_ui(), "worldlinco-auth-login-submit-button")
        tap(submit, (540, 1640))
        for _ in range(18):
            time.sleep(5)
            if is_logged_in(dump_ui()):
                return


def close_settings_if_open() -> None:
    xml = dump_ui()
    if find_center(xml, "worldlinco-settings-close"):
        tap(find_center(xml, "worldlinco-settings-close"), (965, 208))
        time.sleep(1.5)


def open_settings() -> None:
    close_settings_if_open()
    xml = dump_ui()
    tap(find_center(xml, "worldlinco-bottom-tab-settings"), (972, 1976))
    time.sleep(2)


def set_lang(lang: str) -> None:
    xml = dump_ui()
    chip = find_center(xml, f"worldlinco-settings-download-lang-{lang}")
    if chip:
        tap(chip, chip)
        time.sleep(5)
        return
    toggle = find_center(xml, "worldlinco-settings-language-toggle")
    if toggle:
        tap(toggle, toggle)
        time.sleep(1)
    xml = dump_ui()
    opt = find_center(xml, f"worldlinco-settings-language-{lang}")
    if not tap(opt, None):
        raise RuntimeError(f"language control not found: {lang}")
    time.sleep(5)


def go_workspace() -> None:
    xml = dump_ui()
    chat = find_center(xml, "worldlinco-section-rail-chat-button")
    if chat:
        tap(chat, chat)
        time.sleep(0.8)
        tap(chat, chat)
        time.sleep(1.5)


def open_screen(screen_id: str, selector: str) -> None:
    close_settings_if_open()
    if screen_id == "workspace":
        go_workspace()
        return
    xml = dump_ui()
    center = find_center(xml, selector)
    if center:
        tap(center, center)
        time.sleep(2.5)


def main() -> int:
    report: dict = {
        "device": DEVICE,
        "build": 331,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "languages": {},
        "login_ok": False,
    }

    adb("shell", "am", "force-stop", PKG)
    adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(35)

    if not is_logged_in(dump_ui()):
        ensure_login()

    report["login_ok"] = is_logged_in(dump_ui())
    if not report["login_ok"]:
        print(json.dumps({"e4_pass": False, "login_ok": False, "error": "login_failed"}, ensure_ascii=False))
        return 1

    for lang in LANGS:
        lang_result: dict = {"screens": {}, "issues": []}
        open_settings()
        set_lang(lang)
        xml_settings = dump_ui()
        save_dump(f"device-ui-{lang}-settings.xml", xml_settings)
        texts = extract_texts(xml_settings)
        lang_result["screens"]["settings"] = texts[:40]
        lang_result["issues"].extend(analyze(lang, texts))

        for screen_id, selector in SCREENS:
            open_screen(screen_id, selector)
            xml_screen = dump_ui()
            save_dump(f"device-ui-{lang}-{screen_id}.xml", xml_screen)
            screen_texts = extract_texts(xml_screen)
            lang_result["screens"][screen_id] = screen_texts[:40]
            lang_result["issues"].extend(analyze(lang, screen_texts))

        lang_result["pass"] = len(lang_result["issues"]) == 0
        report["languages"][lang] = lang_result

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["e4_pass"] = all(v.get("pass") for v in report["languages"].values()) and report.get("login_ok", True)
    out = EVIDENCE / "e4-smoke-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"e4_pass": report["e4_pass"], "login_ok": report["login_ok"], "languages": {
        k: {"pass": v["pass"], "issues": v["issues"]} for k, v in report["languages"].items()
    }}, ensure_ascii=False, indent=2))
    return 0 if report["e4_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
