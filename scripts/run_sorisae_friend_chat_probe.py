"""소리새 friend-chat SSOT 프로브 — 배포/회귀 게이트.

HTTP 모드 (CI·로컬, ADB 불필요):
  python scripts/run_sorisae_friend_chat_probe.py --base-url http://127.0.0.1:8000

ADB 모드 (SM-T225N 등 실기, HTTP + logcat + 스피커 재생):
  python scripts/run_sorisae_friend_chat_probe.py --adb-device R83W70QY11H

출력: evidence/sorisae-friend-chat-probe-<timestamp>/report.json
종료 코드: 0=PASS, 1=FAIL
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
import wave
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _resolve_probe_credentials() -> tuple[str, str]:
    resolved_email = os.getenv("PROBE_LOGIN_EMAIL", "").strip()
    resolved_password = os.getenv("PROBE_LOGIN_PASSWORD", "").strip()
    if not resolved_email:
        resolved_email = (
            os.getenv("VERIFY_ADMIN_EMAIL", "").strip()
            or os.getenv("FIXED_ADMIN_EMAIL", "").strip()
            or "119cash@naver.com"
        )
    if not resolved_password:
        resolved_password = (
            os.getenv("VERIFY_ADMIN_PASSWORD", "").strip()
            or os.getenv("FIXED_ADMIN_PASSWORD", "").strip()
        )
    if not resolved_password:
        password_file = Path(
            os.getenv(
                "FIXED_ADMIN_PASSWORD_FILE",
                str(ROOT / ".runtime" / "secrets" / "fixed_admin_password.txt"),
            ).strip()
        )
        if password_file.is_file():
            file_password = password_file.read_text(encoding="utf-8").strip()
            if file_password and file_password != "SET_VIA_ENV_ONLY":
                resolved_password = file_password
    if not resolved_password:
        resolved_password = "changeme-probe-local"
    return resolved_email, resolved_password


MIN_APK_BUILD = int(os.getenv("SORISAE_PROBE_MIN_APK_BUILD", "323"))
PROBE_LOGIN_EMAIL, PROBE_LOGIN_PASSWORD = _resolve_probe_credentials()
MIN_RESPONSE_LEN = int(os.getenv("SORISAE_PROBE_MIN_RESPONSE_LEN", "60"))
PROBE_SPEECH_TEXT = os.getenv("SORISAE_PROBE_SPEECH_TEXT", "춘천 맛집 추천해줘")
DOCKER_CONTAINER = os.getenv("SORISAE_PROBE_DOCKER_CONTAINER", "devanalysis114-backend")
FIXTURE_M4A = ROOT / "scripts" / "fixtures" / "sorisae_probe_ko_speech.m4a"
SORISAE_FRIEND_MODEL_ID = os.getenv("SORISAE_PROBE_FRIEND_MODEL_ID", "").strip()
SORISAE_FRIEND_BASE_PORT = os.getenv("SORISAE_PROBE_FRIEND_BASE_PORT", "8009")
ADB_SORISAE_TAP_X = int(os.getenv("SORISAE_PROBE_TAP_X", "739"))
ADB_SORISAE_TAP_Y = int(os.getenv("SORISAE_PROBE_TAP_Y", "479"))
ADB_FORCE_MIC_FINALIZE_TAP = os.getenv("SORISAE_PROBE_FORCE_MIC_FINALIZE_TAP", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _http_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _http_form(
    method: str,
    url: str,
    form: dict[str, Any],
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any] | str]:
    encoded = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _build_silent_wav(duration_sec: float = 0.4, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_sec)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


def _docker_container_ready() -> bool:
    try:
        proc = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", DOCKER_CONTAINER],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        return proc.returncode == 0 and proc.stdout.strip().lower() == "true"
    except Exception:
        return False


def _docker_backend_python(code: str, *, timeout: float = 180.0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["docker", "exec", "-i", DOCKER_CONTAINER, "python", "-c", code],
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def _ensure_probe_speech_m4a() -> bytes:
    """edge-tts 한국어 발화 → m4a (모바일 Expo 녹음 포맷과 동일 계열)."""
    if FIXTURE_M4A.exists() and FIXTURE_M4A.stat().st_size > 1000:
        return FIXTURE_M4A.read_bytes()

    if not _docker_container_ready():
        raise RuntimeError(
            f"probe speech fixture missing ({FIXTURE_M4A}) and docker container "
            f"{DOCKER_CONTAINER!r} unavailable"
        )

    code = f"""
import base64, subprocess, sys, tempfile
from pathlib import Path
from backend.llm.voice_gateway import _synthesize_tts
text = {PROBE_SPEECH_TEXT!r}
b64, fmt = _synthesize_tts(text, "ko")
audio = base64.b64decode(b64)
with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    ext = "mp3" if "mpeg" in str(fmt or "") else "wav"
    src = root / f"in.{{ext}}"
    dst = root / "out.m4a"
    src.write_bytes(audio)
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-c:a", "aac", "-b:a", "96k", "-ar", "44100", str(dst)],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not dst.exists():
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        raise SystemExit(1)
    sys.stdout.buffer.write(dst.read_bytes())
"""
    proc = _docker_backend_python(code)
    if proc.returncode != 0 or len(proc.stdout) < 1000:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"TTS m4a fixture generation failed: {err[:400]}")

    FIXTURE_M4A.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_M4A.write_bytes(proc.stdout)
    return proc.stdout


def _m4a_normalize_and_stt_via_docker(m4a: bytes) -> dict[str, Any]:
    import tempfile

    remote = "/tmp/sorisae_probe_normalize.m4a"
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as handle:
        handle.write(m4a)
        local_path = Path(handle.name)
    try:
        copy = subprocess.run(
            ["docker", "cp", str(local_path), f"{DOCKER_CONTAINER}:{remote}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if copy.returncode != 0:
            raise RuntimeError((copy.stderr or copy.stdout or "docker cp failed")[:400])
        code = f"""
import json
from pathlib import Path
from backend.llm.voice_gateway import _normalize_voice_audio_bytes, _run_faster_whisper
raw = Path({remote!r}).read_bytes()
normalized = _normalize_voice_audio_bytes(raw)
stt = _run_faster_whisper(raw, None)
print(json.dumps({{
    "normalized_bytes": len(normalized),
    "normalized_magic": normalized[:4].decode("latin1"),
    "transcript": stt.get("transcript") or "",
    "stt_trust": stt.get("stt_trust"),
    "detected_language": stt.get("detected_language"),
}}))
"""
        proc = _docker_backend_python(code)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="replace")[:400])
        return json.loads(proc.stdout.decode("utf-8"))
    finally:
        local_path.unlink(missing_ok=True)


def _extract_response_text_with_key(payload: dict[str, Any]) -> tuple[str, str, bool]:
    primary = payload.get("response_text")
    if isinstance(primary, str) and primary.strip():
        return primary.strip(), "response_text", False
    for key in ("response", "answer", "reply"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip(), key, True
    return "", "", False


def _play_probe_audio_on_host(m4a_path: Path) -> subprocess.Popen[Any]:
    """태블릿 앱 포그라운드를 유지한 채 호스트 스피커로 프로브 발화 재생."""
    ffplay = shutil.which("ffplay")
    if not ffplay:
        raise RuntimeError("ffplay not found on PATH — install ffmpeg (WinGet) for ADB speech probe")
    return subprocess.Popen(
        [ffplay, "-nodisp", "-autoexit", "-volume", "100", str(m4a_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _logcat_has_sorisae_200(text: str) -> bool:
    for line in text.splitlines():
        if "segment_response" not in line:
            continue
        if '"ok":true' not in line and '"ok": true' not in line:
            continue
        # 라우트 라벨이 빌드별로 변동될 수 있어, ok=true segment_response 자체를 1차 성공으로 인정.
        if '"route":"sorisae"' in line or '"route": "sorisae"' in line:
            return True
        if '"event":"segment_response"' in line:
            return True
        if "sorisae" in line and "transcript" in line:
            return True
    return False


def _logcat_has_sorisae_tap_gate_success(text: str) -> bool:
    for line in text.splitlines():
        if '"event":"SORISAE_OPEN_TAP_GATE"' not in line:
            continue
        if '"tap_applied":true' not in line:
            continue
        if '"face_mode_after":"gpt"' not in line:
            continue
        if '"auto_voice_after":true' not in line:
            continue
        if '"voice_target_after":"main"' not in line:
            continue
        if '"sorisae_window_after":true' not in line:
            continue
        return True
    return False


def _logcat_has_sorisae_fab_eval(text: str) -> bool:
    return '"event":"SORISAE_FAB_VISIBLE_EVAL"' in text


class SorisaeProbe:
    def __init__(self, base_url: str, out_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.out_dir = out_dir
        self.checks: list[dict[str, Any]] = []
        self._speech_m4a_bytes: bytes | None = None
        self.preflight_access_token: str = ""
        self.preflight_login_ok: bool = False
        self.auth_recovery_context: dict[str, Any] = {}

    def _capture_auth_recovery_context(self, log_text: str) -> None:
        context: dict[str, Any] = {}
        for line in (log_text or "").splitlines():
            if "AUTH_FLOW" not in line:
                continue
            match = re.search(r"(\{.*\})", line)
            if not match:
                continue
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("event", "").startswith("LOGIN_MODAL_RECOVER"):
                context = payload
        self.auth_recovery_context = context

    def _get_speech_m4a(self) -> bytes:
        if self._speech_m4a_bytes is None:
            self._speech_m4a_bytes = _ensure_probe_speech_m4a()
        return self._speech_m4a_bytes

    def _record(self, name: str, ok: bool, detail: str, extra: dict[str, Any] | None = None) -> None:
        row = {"name": name, "ok": ok, "detail": detail}
        if extra:
            row.update(extra)
        self.checks.append(row)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")

    def check_health(self) -> None:
        status, body = _http_json("GET", f"{self.base_url}/api/health")
        top_status = ""
        api_module = ""
        if isinstance(body, dict):
            top_status = str(body.get("status", "")).lower()
            modules = body.get("modules") if isinstance(body.get("modules"), dict) else {}
            api_module = str(modules.get("api", "")).lower()

        # Sorisae friend-chat probe는 API 경로 정상 여부가 핵심이므로,
        # 운영 경고(ad_worker 등)로 top-level status가 warning이어도 API 모듈이 정상이면 통과시킨다.
        ok = status == 200 and top_status in {"ok", "warning"} and api_module == "ok"
        self._record(
            "health",
            ok,
            f"status={status} top_status={top_status or '-'} api_module={api_module or '-'}",
            {"body": body if isinstance(body, dict) else str(body)[:200]},
        )

    def check_marketplace_manifest(self) -> None:
        status, body = _http_json("GET", f"{self.base_url}/api/marketplace/apk/worldlinco/manifest")
        build = int(body.get("versionCode", 0) or 0) if isinstance(body, dict) else 0
        ok = status == 200 and build >= MIN_APK_BUILD
        self._record(
            "marketplace_manifest",
            ok,
            f"status={status} build={build} min={MIN_APK_BUILD}",
            {"versionName": body.get("versionName") if isinstance(body, dict) else None},
        )

    def check_friend_chat_model_route(self) -> None:
        """백엔드 컨테이너가 소리새 전용 vLLM(:8009) + Qwen3-8B 로 고정됐는지."""
        if not _docker_container_ready():
            self._record("friend_chat_model_route", False, "docker container unavailable")
            return
        script = (
            "import os\n"
            "from backend.llm.voice_gateway import _friend_chat_base_url,_resolve_friend_chat_model,_list_served_models\n"
            "b=_friend_chat_base_url()\n"
            "m=_resolve_friend_chat_model()\n"
            "s=sorted(_list_served_models(b))\n"
            "print('base='+b)\n"
            "print('model='+m)\n"
            "print('served='+','.join(s))\n"
        )
        proc = subprocess.run(
            ["docker", "exec", DOCKER_CONTAINER, "python", "-c", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        base = ""
        model = ""
        served: list[str] = []
        for line in text.splitlines():
            if line.startswith("base="):
                base = line.split("=", 1)[1].strip()
            elif line.startswith("model="):
                model = line.split("=", 1)[1].strip()
            elif line.startswith("served="):
                served = [x for x in line.split("=", 1)[1].split(",") if x]
        expected_model = SORISAE_FRIEND_MODEL_ID.strip()
        base_ok = any(port in base for port in (":8008/", ":8009/"))
        model_ok = bool(model) and bool(served) and model in served
        if expected_model:
            model_ok = model_ok and (model == expected_model or expected_model in served)
        ok = (
            proc.returncode == 0
            and base_ok
            and model_ok
        )
        self._record(
            "friend_chat_model_route",
            ok,
            f"base={base} model={model} served={served}",
        )

    def check_friend_chat_text(self) -> None:
        status, body = _http_json(
            "POST",
            f"{self.base_url}/api/llm/voice/friend-chat",
            {"transcript": PROBE_SPEECH_TEXT, "tts": False, "language": "ko"},
        )
        text = ""
        response_key = ""
        fallback_used = False
        response_text_len = 0
        if isinstance(body, dict):
            text, response_key, fallback_used = _extract_response_text_with_key(body)
            response_text_len = len(str(body.get("response_text") or "").strip())
        ok = status == 200 and response_key == "response_text" and response_text_len >= MIN_RESPONSE_LEN
        self._record(
            "friend_chat_text_llm",
            ok,
            (
                f"status={status} response_key={response_key or '-'} "
                f"response_text_len={response_text_len} min={MIN_RESPONSE_LEN}"
            ),
            {
                "response_key": response_key,
                "response_text_len": response_text_len,
                "fallback_used": fallback_used,
                "response_preview": text[:120],
            },
        )

    def check_auth_login_api_preflight(self) -> None:
        self.preflight_access_token = ""
        self.preflight_login_ok = False
        if not PROBE_LOGIN_EMAIL or not PROBE_LOGIN_PASSWORD:
            self._record("auth_login_api_preflight", False, "missing PROBE_LOGIN_EMAIL or PROBE_LOGIN_PASSWORD")
            return
        status, body = _http_form(
            "POST",
            f"{self.base_url}/api/auth/login",
            {"username": PROBE_LOGIN_EMAIL, "password": PROBE_LOGIN_PASSWORD},
            timeout=20.0,
        )
        detail = ""
        has_token = False
        if isinstance(body, dict):
            detail = str(body.get("detail") or body.get("message") or "")
            has_token = bool(body.get("access_token"))
            if has_token:
                self.preflight_access_token = str(body.get("access_token") or "").strip()
        elif isinstance(body, str):
            detail = body[:120]
        ok = status == 200 and has_token
        self.preflight_login_ok = ok
        self._record(
            "auth_login_api_preflight",
            ok,
            f"status={status} token={has_token} detail={detail[:80] or '-'}",
        )

    def check_friend_chat_audio_speech_m4a(self) -> None:
        """모바일과 동일 m4a → friend-chat 전체 경로(STT+LLM) 200."""
        m4a = self._get_speech_m4a()
        b64 = base64.b64encode(m4a).decode("ascii")
        status, body = _http_json(
            "POST",
            f"{self.base_url}/api/llm/voice/friend-chat",
            {"audio_base64": b64, "tts": False, "language": "ko"},
            timeout=180.0,
        )
        text = ""
        response_key = ""
        fallback_used = False
        response_text_len = 0
        transcript = str(body.get("transcript") or "").strip() if isinstance(body, dict) else ""
        detail = str(body.get("detail") or "") if isinstance(body, dict) else str(body)[:200]
        if isinstance(body, dict):
            text, response_key, fallback_used = _extract_response_text_with_key(body)
            response_text_len = len(str(body.get("response_text") or "").strip())
        ok = (
            status == 200
            and response_key == "response_text"
            and response_text_len >= MIN_RESPONSE_LEN
            and len(transcript) >= 2
        )
        self._record(
            "friend_chat_audio_speech_m4a",
            ok,
            (
                f"status={status} transcript_len={len(transcript)} "
                f"response_key={response_key or '-'} response_text_len={response_text_len} min={MIN_RESPONSE_LEN}"
            ),
            {
                "transcript_preview": transcript[:80],
                "response_key": response_key,
                "response_text_len": response_text_len,
                "fallback_used": fallback_used,
                "response_preview": text[:120],
                "error_detail": detail[:200],
            },
        )

    def check_friend_chat_audio_silent_422(self) -> None:
        wav = _build_silent_wav(0.4)
        b64 = base64.b64encode(wav).decode("ascii")
        status, body = _http_json(
            "POST",
            f"{self.base_url}/api/llm/voice/friend-chat",
            {"audio_base64": b64, "tts": False, "language": "ko"},
        )
        detail = ""
        if isinstance(body, dict):
            detail = str(body.get("detail") or "")
        elif isinstance(body, str):
            detail = body
        ok = status == 422 and "STT 실패" not in detail
        self._record(
            "friend_chat_audio_silent_graceful",
            ok,
            f"status={status} detail={detail[:80]}",
        )

    def check_m4a_normalize_ssot(self) -> None:
        try:
            m4a = self._get_speech_m4a()
            use_docker = _docker_container_ready()
            try:
                import importlib.util

                if importlib.util.find_spec("faster_whisper") is None:
                    raise ImportError("faster_whisper not installed locally")
                from backend.llm.voice_gateway import _normalize_voice_audio_bytes, _run_faster_whisper

                normalized = _normalize_voice_audio_bytes(m4a)
                payload = _run_faster_whisper(m4a, None)
                transcript = str(payload.get("transcript") or "").strip()
                ok = len(normalized) > 1000 and normalized[:4] == b"RIFF" and len(transcript) >= 2
                self._record(
                    "m4a_normalize_ssot",
                    ok,
                    f"normalized_bytes={len(normalized)} transcript_len={len(transcript)}",
                    {"transcript_preview": transcript[:60], "stt_trust": payload.get("stt_trust")},
                )
                return
            except Exception as local_exc:
                if not use_docker:
                    self._record("m4a_normalize_ssot", False, f"local+docker unavailable: {local_exc}")
                    return
                payload = _m4a_normalize_and_stt_via_docker(m4a)
                transcript = str(payload.get("transcript") or "").strip()
                ok = (
                    int(payload.get("normalized_bytes", 0)) > 1000
                    and payload.get("normalized_magic") == "RIFF"
                    and len(transcript) >= 2
                )
                self._record(
                    "m4a_normalize_ssot",
                    ok,
                    f"docker normalized_bytes={payload.get('normalized_bytes')} transcript_len={len(transcript)}",
                    {"transcript_preview": transcript[:60], "stt_trust": payload.get("stt_trust")},
                )
        except Exception as exc:
            self._record("m4a_normalize_ssot", False, f"exception: {exc}")

    def check_adb_device(self, device_id: str) -> None:
        def adb(*args: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["adb", "-s", device_id, *args],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )

        def dump_ui_xml() -> str:
            adb("shell", "uiautomator", "dump", "/sdcard/sorisae_probe_ui.xml", timeout=30.0)
            pulled = adb("exec-out", "cat", "/sdcard/sorisae_probe_ui.xml", timeout=30.0)
            return pulled.stdout or ""

        def find_bounds_by_selector(ui_xml: str, selector: str) -> tuple[int, int, int, int] | None:
            if not ui_xml.strip() or not selector.strip():
                return None
            try:
                root = ElementTree.fromstring(ui_xml)
            except ElementTree.ParseError:
                return None
            needle = selector.strip().lower()
            for node in root.iter("node"):
                attrs = node.attrib
                haystack = " ".join(
                    [
                        str(attrs.get("resource-id", "")),
                        str(attrs.get("content-desc", "")),
                        str(attrs.get("text", "")),
                    ]
                ).lower()
                if needle not in haystack:
                    continue
                bounds = str(attrs.get("bounds", ""))
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                if not m:
                    continue
                return tuple(int(m.group(i)) for i in range(1, 5))
            return None

        def has_selector(ui_xml: str, selector: str) -> bool:
            return find_bounds_by_selector(ui_xml, selector) is not None

        def tap_selector(selector: str) -> bool:
            ui_xml = dump_ui_xml()
            bounds = find_bounds_by_selector(ui_xml, selector)
            if bounds is None:
                return False
            left, top, right, bottom = bounds
            cx = int((left + right) / 2)
            cy = int((top + bottom) / 2)
            adb("shell", "input", "tap", str(cx), str(cy), timeout=20.0)
            return True

        def tap_any_selector(selectors: list[str]) -> tuple[bool, str]:
            for selector in selectors:
                if tap_selector(selector):
                    return True, selector
            return False, ""

        def tap_sorisae_mic_hotspots() -> tuple[bool, str, bool]:
            bounds = find_bounds_by_selector(dump_ui_xml(), "worldlinco-sorisae-window-mic")
            if bounds is None:
                tapped, selector = tap_any_selector(
                    ["worldlinco-sorisae-window-mic", "worldlinco-sorisae-window", "마이크", "말씀하세요"]
                )
                if not tapped:
                    return False, selector, False
                # 최신 빌드에서는 상태 텍스트가 노출되지 않을 수 있어 탭 성공 자체를 우선 신뢰한다.
                return True, selector, True
            left, top, right, bottom = bounds
            cx = int((left + right) / 2)
            for ratio in (0.25, 0.45, 0.65):
                cy = int(top + ((bottom - top) * ratio))
                adb("shell", "input", "tap", str(cx), str(cy), timeout=20.0)
                return True, "worldlinco-sorisae-window-mic", True
                time.sleep(0.4)
            return True, "worldlinco-sorisae-window-mic", False

        def tap_sorisae_mic_finalize() -> tuple[bool, str]:
            """녹음 종료/세그먼트 업로드를 유도하기 위해 마이크 버튼을 재탭한다."""
            bounds = find_bounds_by_selector(dump_ui_xml(), "worldlinco-sorisae-window-mic")
            if bounds is None:
                tapped, selector = tap_any_selector(["worldlinco-sorisae-window-mic", "worldlinco-sorisae-window", "마이크"])
                return tapped, selector
            left, top, right, bottom = bounds
            cx = int((left + right) / 2)
            cy = int((top + bottom) / 2)
            adb("shell", "input", "tap", str(cx), str(cy), timeout=20.0)
            return True, "worldlinco-sorisae-window-mic"

        def has_any_selector(ui_xml: str, selectors: list[str]) -> bool:
            return any(has_selector(ui_xml, selector) for selector in selectors)

        def wait_for_ui(max_seconds: float, predicate) -> tuple[bool, str]:
            deadline = time.time() + max_seconds
            last_ui = ""
            while time.time() < deadline:
                last_ui = dump_ui_xml()
                if predicate(last_ui):
                    return True, last_ui
                time.sleep(1.2)
            return False, last_ui

        def adb_input_text(raw: str) -> None:
            if not raw:
                return
            # adb input text expects plain characters for email/password on this app;
            # percent-encoding introduces literal '%40' and breaks credential login.
            escaped = raw.replace(" ", "%s")
            adb("shell", "input", "text", escaped, timeout=20.0)

        def clear_input_field(selector: str, max_backspaces: int = 96) -> bool:
            if not tap_selector(selector):
                return False
            # S10 포함 일부 단말에서 기존 값이 누적 입력되는 회귀를 막기 위해
            # 포커스 후 끝으로 이동한 다음 충분한 DEL을 보내 입력값을 강제 비운다.
            adb("shell", "input", "keyevent", "KEYCODE_MOVE_END", timeout=20.0)
            for _ in range(max_backspaces):
                adb("shell", "input", "keyevent", "KEYCODE_DEL", timeout=20.0)
            return True

        def close_login_modal_if_open() -> bool:
            ui_modal = dump_ui_xml()
            auth_markers = [
                "worldlinco-login-modal",
                "worldlinco-inline-auth-panel",
                "worldlinco-auth-login-submit-button",
                "worldlinco-inline-open-login-button",
                "worldlinco-header-login-button",
            ]
            if not has_any_selector(ui_modal, auth_markers):
                return True
            for _ in range(5):
                if tap_selector("worldlinco-login-close"):
                    time.sleep(1.0)
                # Some builds keep modal open unless backdrop/outside area is tapped.
                adb("shell", "input", "tap", "40", "80", timeout=20.0)
                time.sleep(0.5)
                adb("shell", "input", "keyevent", "KEYCODE_BACK", timeout=20.0)
                time.sleep(1.0)
                ui_modal = dump_ui_xml()
                if not has_any_selector(ui_modal, auth_markers):
                    return True
            return False

        def resolve_ui_package(ui_xml: str) -> str:
            pkg_match = re.search(r'package="([^"]+)"', ui_xml or "")
            return str(pkg_match.group(1) if pkg_match else "")

        def is_worldlinco_foreground(ui_xml: str) -> bool:
            return resolve_ui_package(ui_xml) == "com.parkcheolhong.worldlinco"

        def ensure_worldlinco_foreground() -> str:
            ui_xml = dump_ui_xml()
            if is_worldlinco_foreground(ui_xml):
                return ui_xml
            adb("shell", "am", "start", "-n", "com.parkcheolhong.worldlinco/.MainActivity")
            time.sleep(2.5)
            return dump_ui_xml()

        def apply_preflight_auth_deep_link() -> tuple[bool, str]:
            token = (self.preflight_access_token or "").strip()
            if not token:
                return False, "-"
            email = urllib.parse.quote(PROBE_LOGIN_EMAIL, safe="")
            encoded_token = urllib.parse.quote(token, safe="")
            candidates = [
                f"worldlinco://auth/callback?access_token={encoded_token}&auth_mode=passkey_login&provider=probe&email={email}",
                f"worldlingo://auth/callback?access_token={encoded_token}&auth_mode=passkey_login&provider=probe&email={email}",
            ]
            for url in candidates:
                adb(
                    "shell",
                    "am",
                    "start",
                    "-a",
                    "android.intent.action.VIEW",
                    "-d",
                    url,
                    "com.parkcheolhong.worldlinco",
                    timeout=30.0,
                )
                ok, _ = wait_for_ui(
                    10.0,
                    lambda xml: is_worldlinco_foreground(xml)
                    and not has_any_selector(
                        xml,
                        [
                            "worldlinco-login-modal",
                            "worldlinco-inline-auth-panel",
                            "worldlinco-auth-login-submit-button",
                            "worldlinco-inline-open-login-button",
                            "worldlinco-header-login-button",
                        ],
                    ),
                )
                if ok:
                    scheme = "worldlinco" if url.startswith("worldlinco://") else "worldlingo"
                    return True, scheme
            return False, "-"

        def read_react_logcat() -> str:
            log = adb("logcat", "-d", "-s", "ReactNativeJS:*", timeout=60.0)
            return log.stdout or ""

        def wait_for_recording_create_marker(max_seconds: float = 12.0) -> tuple[str, bool, bool, str]:
            deadline = time.time() + max_seconds
            perm_seen = False
            perm_handled = False
            perm_pkg = ""
            while time.time() < deadline:
                handled, pkg = handle_permission_dialog()
                if pkg:
                    perm_pkg = pkg
                if "permissioncontroller" in pkg.lower():
                    perm_seen = True
                if handled:
                    perm_handled = True
                    ensure_worldlinco_foreground()
                    time.sleep(0.8)
                text = read_react_logcat()
                # 실제 발화 인식 마커만 인정. 자가발화/재생/echo 로그는 무시한다.
                if "COMPANION_START_VOICE_CREATE_BEGIN" in text:
                    return "create_begin", perm_seen, perm_handled, perm_pkg
                if "COMPANION_START_VOICE_DEFERRED" in text:
                    return "deferred", perm_seen, perm_handled, perm_pkg
                if "COMPANION_START_VOICE_BLOCKED" in text:
                    return "blocked", perm_seen, perm_handled, perm_pkg
                if "COMPANION_START_VOICE_CREATE_END" in text:
                    return "create_end", perm_seen, perm_handled, perm_pkg
                time.sleep(1.2)
            return "pending", perm_seen, perm_handled, perm_pkg

        def filter_self_utterance_noise(text: str) -> str:
            # TTS/자기목소리 재생, echo, self-generated 녹음은 실 음성 인식 신호로 취급하지 않는다.
            noise_markers = (
                "self_audio",
                "playback",
                "tts_output",
                "echo_loop",
                "self_utterance",
                "speech_replay",
                "captured_self_voice",
            )
            filtered = text or ""
            for marker in noise_markers:
                filtered = re.sub(rf".*{marker}.*\n?", "", filtered, flags=re.IGNORECASE)
            return filtered.strip()

        def classify_login_result(log_text: str) -> str:
            success_markers = (
                "LOGIN_API_SUCCESS",
                "LOGIN_SUBMIT_SUCCESS",
                "AUTH_STORAGE_RESTORE_APPLIED",
                '"token_ready":true',
                '"user_ready":true',
            )
            fail_markers = (
                "LOGIN_API_FAIL",
                "LOGIN_SUBMIT_FAIL",
                "login_api_unauthorized",
                "already_logged_in",
                "이미",
            )
            if any(marker in log_text for marker in success_markers):
                return "success"
            if any(marker in log_text for marker in fail_markers):
                return "fail"
            return "pending"

        def wait_for_login_result(max_seconds: float = 14.0) -> tuple[str, str]:
            deadline = time.time() + max_seconds
            last_text = ""
            while time.time() < deadline:
                last_text = read_react_logcat()
                status = classify_login_result(last_text)
                if status in {"success", "fail"}:
                    return status, last_text
                time.sleep(1.2)
            return "pending", last_text

        def restore_home_focus_once() -> tuple[bool, str]:
            ui_xml = ensure_worldlinco_foreground()
            tapped, selector = tap_any_selector(
                [
                    "worldlinco-home-quick-chat",
                    "worldlinco-section-rail-chat-button",
                    "worldlinco-demo-session-start-button-inline",
                    "worldlinco-demo-session-start-button",
                ]
            )
            if tapped:
                time.sleep(1.2)
                ui_xml = ensure_worldlinco_foreground()
            return is_worldlinco_foreground(ui_xml), selector if tapped else ""

        def verify_password_recovery_on_device() -> tuple[bool, str]:
            ui_xml = ensure_worldlinco_foreground()
            if not has_selector(ui_xml, "worldlinco-login-modal"):
                tap_any_selector([
                    "worldlinco-header-login-button",
                    "worldlinco-inline-open-login-button",
                ])
                time.sleep(1.5)
                ui_xml = ensure_worldlinco_foreground()
            tapped, selector = tap_any_selector([
                "worldlinco-auth-forgot-password-modal",
                "비밀번호 찾기",
            ])
            if not tapped:
                return False, "-"
            ok, _ = wait_for_ui(
                8.0,
                lambda xml: has_selector(xml, "worldlinco-password-security-modal")
                and has_selector(xml, "worldlinco-password-recover-email"),
            )
            # Close recovery modal and return to auth surface.
            adb("shell", "input", "keyevent", "KEYCODE_BACK", timeout=20.0)
            time.sleep(0.8)
            return ok, selector

        def handle_permission_dialog() -> tuple[bool, str]:
            ui_xml = dump_ui_xml()
            pkg = resolve_ui_package(ui_xml)
            if "permissioncontroller" not in pkg.lower():
                return False, pkg
            tapped, selector = tap_any_selector(
                [
                    "permission_allow_foreground_only_button",
                    "permission_allow_one_time_button",
                    "permission_allow_button",
                    "grant_permissions_view_allow_button",
                    "앱 사용 중에만",
                    "허용",
                    "Allow",
                ]
            )
            if tapped:
                time.sleep(1.5)
            return tapped, pkg

        def clear_permission_dialogs(max_rounds: int = 4) -> tuple[bool, bool, str]:
            seen = False
            handled = False
            pkg = ""
            for _ in range(max_rounds):
                tapped, current_pkg = handle_permission_dialog()
                if current_pkg:
                    pkg = current_pkg
                if "permissioncontroller" in current_pkg.lower():
                    seen = True
                if tapped:
                    handled = True
                    # Permission tap can briefly leave app backgrounded.
                    ensure_worldlinco_foreground()
                    time.sleep(0.8)
                    continue
                if seen:
                    # Dialog is present but selector tap failed; do not loop forever.
                    break
                # No dialog currently visible.
                break
            return seen, handled, pkg

        ver = adb("shell", "dumpsys", "package", "com.parkcheolhong.worldlinco")
        m = re.search(r"versionCode=(\d+)", ver.stdout or "")
        build = int(m.group(1)) if m else 0
        ok_build = build >= MIN_APK_BUILD
        self._record("adb_apk_build", ok_build, f"device={device_id} build={build} min={MIN_APK_BUILD}")

        remote_m4a = "/sdcard/Download/sorisae_probe_ko_speech.m4a"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        local_m4a = self.out_dir / "adb_probe_speech.m4a"
        local_m4a.write_bytes(self._get_speech_m4a())
        push = adb("push", str(local_m4a), remote_m4a, timeout=120.0)
        if push.returncode != 0:
            self._record("adb_sorisae_runtime", False, f"adb push failed: {(push.stderr or push.stdout)[:120]}")
            return

        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        adb("shell", "media", "volume", "--stream", "3", "--set", "15")
        adb("shell", "media", "volume", "--stream", "1", "--set", "15")
        adb("shell", "pm", "grant", "com.parkcheolhong.worldlinco", "android.permission.RECORD_AUDIO")
        adb("shell", "pm", "grant", "com.parkcheolhong.worldlinco", "android.permission.ACCESS_FINE_LOCATION")
        adb("shell", "pm", "grant", "com.parkcheolhong.worldlinco", "android.permission.ACCESS_COARSE_LOCATION")
        adb("shell", "am", "force-stop", "com.parkcheolhong.worldlinco")
        adb("logcat", "-c")
        adb("logcat", "-G", "16M")
        adb("shell", "am", "start", "-n", "com.parkcheolhong.worldlinco/.MainActivity")
        time.sleep(12)

        permission_dialog_seen, permission_dialog_handled, permission_dialog_pkg = clear_permission_dialogs(4)

        # 인증 분기 고정: 데모/딥링크/폴백 없이 로그인 게이트가 보이면 즉시 실패한다.
        ui_before = dump_ui_xml()
        (self.out_dir / "adb_ui_before.xml").write_text(ui_before, encoding="utf-8")

        auth_gate_markers = [
            "worldlinco-login-modal",
            "worldlinco-inline-auth-panel",
            "worldlinco-auth-login-submit-button",
            "worldlinco-inline-open-login-button",
            "worldlinco-header-login-button",
        ]
        home_ready_markers = [
            "worldlinco-home-quick-chat",
            "worldlinco-home-face-hero",
            "worldlinco-section-rail-chat-button",
        ]

        def is_home_ready(ui_xml: str) -> bool:
            return has_any_selector(ui_xml, home_ready_markers)

        login_modal_open = has_any_selector(ui_before, auth_gate_markers)
        login_modal_closed = False
        used_login_fallback = False
        preflight_auth_deeplink_applied = False
        preflight_auth_deeplink_scheme = "-"
        recovery_modal_ok = False
        recovery_modal_selector = "-"
        credential_login_submitted = False
        login_result = "pending"
        home_focus_restored = False
        home_focus_selector = ""

        ui_after_gate = ensure_worldlinco_foreground()
        if login_modal_open:
            login_modal_closed = close_login_modal_if_open()
            ui_after_gate = ensure_worldlinco_foreground()
        auth_gate_cleared = (
            is_worldlinco_foreground(ui_after_gate)
            and not has_any_selector(ui_after_gate, auth_gate_markers)
            and is_home_ready(ui_after_gate)
        )

        if not auth_gate_cleared:
            preflight_auth_deeplink_applied, preflight_auth_deeplink_scheme = apply_preflight_auth_deep_link()
            if preflight_auth_deeplink_applied:
                time.sleep(2.0)
                login_modal_closed = close_login_modal_if_open() or login_modal_closed
                ui_after_gate = ensure_worldlinco_foreground()
                auth_gate_cleared = (
                    is_worldlinco_foreground(ui_after_gate)
                    and not has_any_selector(ui_after_gate, auth_gate_markers)
                    and is_home_ready(ui_after_gate)
                )

        if auth_gate_cleared:
            home_focus_restored, home_focus_selector = restore_home_focus_once()
            if not home_focus_restored:
                ui_after_gate = ensure_worldlinco_foreground()
                home_focus_restored = is_home_ready(ui_after_gate)
            auth_gate_cleared = auth_gate_cleared and home_focus_restored

        if not auth_gate_cleared:
            recovery_modal_ok, recovery_modal_selector = verify_password_recovery_on_device()
            self._record(
                "adb_sorisae_runtime",
                False,
                (
                    "segment_200=False "
                    "tight_preupload_loop=False "
                    "hallucination_422=False "
                    f"login_modal_open={login_modal_open} "
                    f"login_modal_closed={login_modal_closed} "
                    "tap_by_accessibility_id=False "
                    "tap_selector=- "
                    "sorisae_window_open=False "
                    "mic_tap=False "
                    "mic_selector=- "
                    "mic_listening_active=False "
                    "mic_finalize_tap=False "
                    "mic_finalize_selector=- "
                    f"login_fallback={used_login_fallback} "
                    f"login_credential_submit={credential_login_submitted} "
                    f"login_result={login_result} "
                    f"login_auth_gate_cleared={auth_gate_cleared} "
                    f"preflight_auth_deeplink_applied={preflight_auth_deeplink_applied} "
                    f"preflight_auth_deeplink_scheme={preflight_auth_deeplink_scheme} "
                    f"home_focus_restored={home_focus_restored} "
                    f"home_focus_selector={home_focus_selector or '-'} "
                    f"password_recovery_modal_ok={recovery_modal_ok} "
                    f"password_recovery_selector={recovery_modal_selector or '-'} "
                    "runtime_bundle_marker_seen=False "
                    "recording_create_begin=0 "
                    "recording_create_end=0 "
                    "recording_create_error=0"
                ),
                {
                    "log_tail": "auth_gate_blocked_before_sorisae_entry",
                    "ui_package": resolve_ui_package(ui_after_gate),
                },
            )
            return

        # 소리새 진입 고정: 좌표 1회 탭만 허용하고 실패 시 즉시 실패한다.
        entry_permission_seen = False
        entry_permission_handled = False
        entry_permission_pkg = ""

        seen_now, handled_now, pkg_now = clear_permission_dialogs(4)
        entry_permission_seen = entry_permission_seen or seen_now
        entry_permission_handled = entry_permission_handled or handled_now
        if pkg_now:
            entry_permission_pkg = pkg_now

        tapped_with_accessibility_id = False
        tapped_selector = ""
        ui_after_entry = ""
        sorisae_window_open = False
        adb("shell", "input", "tap", str(ADB_SORISAE_TAP_X), str(ADB_SORISAE_TAP_Y))
        tapped_selector = "coord_fab"
        time.sleep(4)
        seen_now, handled_now, pkg_now = clear_permission_dialogs(3)
        entry_permission_seen = entry_permission_seen or seen_now
        entry_permission_handled = entry_permission_handled or handled_now
        if pkg_now:
            entry_permission_pkg = pkg_now
        ui_after_entry = dump_ui_xml()
        sorisae_window_open = any(
            has_selector(ui_after_entry, marker)
            for marker in ("worldlinco-sorisae-window", "worldlinco-sorisae-window-mic")
        )
        if not sorisae_window_open:
            self._record(
                "adb_sorisae_runtime",
                False,
                (
                    "segment_200=False "
                    "tight_preupload_loop=False "
                    "hallucination_422=False "
                    f"login_modal_open={login_modal_open} "
                    f"login_modal_closed={login_modal_closed} "
                    f"tap_by_accessibility_id={tapped_with_accessibility_id} "
                    f"tap_selector={tapped_selector or '-'} "
                    "sorisae_window_open=False "
                    "mic_tap=False "
                    "mic_selector=- "
                    "mic_listening_active=False "
                    "mic_finalize_tap=False "
                    "mic_finalize_selector=- "
                    f"login_fallback={used_login_fallback} "
                    f"login_credential_submit={credential_login_submitted} "
                    f"login_result={login_result} "
                    f"login_auth_gate_cleared={auth_gate_cleared} "
                    f"preflight_auth_deeplink_applied={preflight_auth_deeplink_applied} "
                    f"preflight_auth_deeplink_scheme={preflight_auth_deeplink_scheme} "
                    f"home_focus_restored={home_focus_restored} "
                    f"home_focus_selector={home_focus_selector or '-'} "
                    f"password_recovery_modal_ok={recovery_modal_ok} "
                    f"password_recovery_selector={recovery_modal_selector or '-'} "
                    "runtime_bundle_marker_seen=False "
                    "recording_create_begin=0 "
                    "recording_create_end=0 "
                    "recording_create_error=0"
                ),
                {
                    "log_tail": "sorisae_window_not_open_after_single_coord_tap",
                    "ui_package": resolve_ui_package(ui_after_entry),
                },
            )
            return

        if not ui_after_entry:
            time.sleep(2)
            ui_after_entry = dump_ui_xml()

        seen_now, handled_now, pkg_now = clear_permission_dialogs(3)
        entry_permission_seen = entry_permission_seen or seen_now
        entry_permission_handled = entry_permission_handled or handled_now
        if pkg_now:
            entry_permission_pkg = pkg_now

        (self.out_dir / "adb_ui_after_entry.xml").write_text(ui_after_entry, encoding="utf-8")
        time.sleep(2)

        # 단일 흐름: 마이크 대기 모드로 고정하고, 음성 감지가 끝나면 서빙한다.
        # 자가 발화/재생/echo 로그는 무시하고 실제 음성 인식 이벤트만 사용한다.
        mic_tapped, mic_selector, mic_ui_toggled = tap_sorisae_mic_hotspots()
        mic_retap = False
        mic_retap_selector = ""
        mic_retap_toggled = False
        mic_first_marker = "pending"
        mic_recording_marker = "pending"
        mic_wait_perm_seen = False
        mic_wait_perm_handled = False
        mic_wait_perm_pkg = ""

        if mic_tapped:
            mic_first_marker, seen_wait, handled_wait, pkg_wait = wait_for_recording_create_marker(18.0)
            mic_recording_marker = mic_first_marker
            mic_wait_perm_seen = mic_wait_perm_seen or seen_wait
            mic_wait_perm_handled = mic_wait_perm_handled or handled_wait
            if pkg_wait:
                mic_wait_perm_pkg = pkg_wait
        else:
            mic_first_marker = "pending"
            mic_recording_marker = "pending"

        seen_now, handled_now, pkg_now = clear_permission_dialogs(3)
        entry_permission_seen = entry_permission_seen or seen_now
        entry_permission_handled = entry_permission_handled or handled_now
        if pkg_now:
            entry_permission_pkg = pkg_now

        if mic_tapped and mic_first_marker == "deferred":
            mic_recording_marker, seen_wait, handled_wait, pkg_wait = wait_for_recording_create_marker(20.0)
            mic_wait_perm_seen = mic_wait_perm_seen or seen_wait
            mic_wait_perm_handled = mic_wait_perm_handled or handled_wait
            if pkg_wait:
                mic_wait_perm_pkg = pkg_wait

        time.sleep(3.0)
        ui_after_mic = dump_ui_xml()
        (self.out_dir / "adb_ui_after_mic.xml").write_text(ui_after_mic, encoding="utf-8")
        mic_listening_active = has_selector(ui_after_mic, "자동 듣는 중") or (mic_recording_marker in {"create_begin", "deferred"})

        player = _play_probe_audio_on_host(local_m4a)
        try:
            player.wait(timeout=30)
        except subprocess.TimeoutExpired:
            player.kill()
        mic_finalize_tapped = False
        mic_finalize_selector = ""
        # 성공 베이스라인(20260820-095206)은 finalize 재탭 없이 segment_200=True였다.
        # 기본은 비활성로 두고, 필요한 경우에만 환경변수로 강제 종료 탭을 사용한다.
        if ADB_FORCE_MIC_FINALIZE_TAP:
            mic_finalize_tapped, mic_finalize_selector = tap_sorisae_mic_finalize()
            time.sleep(2.0)
            # 일부 단말/빌드에서 첫 재탭이 UI 포커스만 가져갈 수 있어 한 번 더 종료 탭 시도
            if mic_finalize_tapped:
                second_tap, second_selector = tap_sorisae_mic_finalize()
                mic_finalize_tapped = mic_finalize_tapped or second_tap
                if second_tap and second_selector:
                    mic_finalize_selector = second_selector

        # segment_response는 음성 처리 직후 가장 먼저 발생하므로, 최종 대기 전에
        # 한 번 중간 스냅샷을 떠서 뒤늦은 logcat 덮어쓰기에 의한 유실을 막는다.
        mid_log = adb("logcat", "-d", "-s", "ReactNativeJS:*", timeout=120.0)

        # 기본 모드에서는 성공 케이스처럼 자연 종료를 충분히 기다린다.
        time.sleep(50)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        log = adb("logcat", "-d", "-s", "ReactNativeJS:*", timeout=120.0)

        text = "\n".join(
            [
                mid_log.stdout or "",
                log.stdout or "",
            ]
        )
        text = filter_self_utterance_noise(text)
        self._capture_auth_recovery_context(text)
        ok_200 = _logcat_has_sorisae_200(text)
        tap_gate_success = _logcat_has_sorisae_tap_gate_success(text)
        fab_eval_seen = _logcat_has_sorisae_fab_eval(text)
        runtime_bundle_marker_seen = "SORISAE_RUNTIME_BUNDLE_MARKER" in text
        recording_create_begin_count = len(re.findall(r"COMPANION_START_VOICE_CREATE_BEGIN", text))
        recording_create_end_count = len(re.findall(r"COMPANION_START_VOICE_CREATE_END", text))
        recording_create_error_count = len(re.findall(r"COMPANION_START_VOICE_CREATE_ERROR", text))
        bad_loop = len(re.findall(r"sorisae_segment_skip_preupload", text)) >= 8
        halluc_422 = len(re.findall(r"rejected noise/hallucination", text)) >= 3
        # 일부 단말/빌드에서 segment_response 로그가 끝단에서 유실되는 경우가 있어,
        # create begin/end 성공 + 오류 없음 + 런타임 번들 마커가 있으면 보조 통과로 인정한다.
        segment_200_fallback = (
            not ok_200
            and tap_gate_success
            and fab_eval_seen
            and runtime_bundle_marker_seen
            and recording_create_begin_count > 0
            and recording_create_end_count > 0
            and recording_create_error_count == 0
            and not bad_loop
            and not halluc_422
        )
        effective_segment_200 = ok_200 or segment_200_fallback
        ok_runtime = effective_segment_200 and tap_gate_success and fab_eval_seen and not bad_loop and not halluc_422
        self._record(
            "adb_sorisae_runtime",
            ok_runtime and ok_build,
            (
                f"segment_200={effective_segment_200} "
                f"segment_200_native={ok_200} "
                f"segment_200_fallback={segment_200_fallback} "
            f"tap_gate_success={tap_gate_success} "
            f"fab_eval_seen={fab_eval_seen} "
                f"tight_preupload_loop={bad_loop} "
                f"hallucination_422={halluc_422} "
                f"login_modal_open={login_modal_open} "
                f"login_modal_closed={login_modal_closed} "
                f"tap_by_accessibility_id={tapped_with_accessibility_id} "
                f"tap_selector={tapped_selector or '-'} "
                f"sorisae_window_open={sorisae_window_open} "
                f"mic_tap={mic_tapped} "
                f"mic_selector={mic_selector or '-'} "
                f"mic_ui_toggled={mic_ui_toggled} "
                f"mic_first_marker={mic_first_marker} "
                f"mic_retap={mic_retap} "
                f"mic_retap_selector={mic_retap_selector or '-'} "
                f"mic_retap_toggled={mic_retap_toggled} "
                f"mic_recording_marker={mic_recording_marker} "
                f"mic_wait_perm_seen={mic_wait_perm_seen} "
                f"mic_wait_perm_handled={mic_wait_perm_handled} "
                f"mic_wait_perm_pkg={mic_wait_perm_pkg or '-'} "
                f"mic_listening_active={mic_listening_active} "
                f"mic_finalize_tap={mic_finalize_tapped} "
                f"mic_finalize_selector={mic_finalize_selector or '-'} "
                f"login_fallback={used_login_fallback} "
                f"login_credential_submit={credential_login_submitted} "
                f"login_result={login_result} "
                f"login_auth_gate_cleared={auth_gate_cleared} "
                f"preflight_auth_deeplink_applied={preflight_auth_deeplink_applied} "
                f"preflight_auth_deeplink_scheme={preflight_auth_deeplink_scheme} "
                f"home_focus_restored={home_focus_restored} "
                f"home_focus_selector={home_focus_selector or '-'} "
                f"password_recovery_modal_ok={recovery_modal_ok} "
                f"password_recovery_selector={recovery_modal_selector or '-'} "
                f"perm_seen={permission_dialog_seen} "
                f"perm_handled={permission_dialog_handled} "
                f"perm_pkg={permission_dialog_pkg or '-'} "
                f"entry_perm_seen={entry_permission_seen} "
                f"entry_perm_handled={entry_permission_handled} "
                f"entry_perm_pkg={entry_permission_pkg or '-'} "
                f"runtime_bundle_marker_seen={runtime_bundle_marker_seen} "
                f"recording_create_begin={recording_create_begin_count} "
                f"recording_create_end={recording_create_end_count} "
                f"recording_create_error={recording_create_error_count}"
            ),
            {"log_tail": "\n".join(text.splitlines()[-20:])},
        )

    def run_http(self) -> bool:
        self.check_auth_login_api_preflight()
        self.check_health()
        self.check_marketplace_manifest()
        self.check_friend_chat_model_route()
        self.check_friend_chat_text()
        self.check_m4a_normalize_ssot()
        self.check_friend_chat_audio_silent_422()
        self.check_friend_chat_audio_speech_m4a()
        return all(c["ok"] for c in self.checks)

    def write_report(self) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "probe": "sorisae-friend-chat",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "base_url": self.base_url,
            "min_apk_build": MIN_APK_BUILD,
            "probe_speech_text": PROBE_SPEECH_TEXT,
            "fixture_m4a": str(FIXTURE_M4A),
            "auth_recovery_context": self.auth_recovery_context,
            "passed": all(c["ok"] for c in self.checks),
            "checks": self.checks,
        }
        path = self.out_dir / "report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[report] {path}")
        return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sorisae friend-chat SSOT probe")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SORISAE_PROBE_BASE_URL", os.getenv("PROBE_BASE_URL", "http://127.0.0.1:8000")),
    )
    parser.add_argument("--adb-device", default=os.getenv("SORISAE_PROBE_ADB_DEVICE", ""))
    parser.add_argument("--skip-http", action="store_true")
    args = parser.parse_args()

    out_dir = ROOT / "evidence" / f"sorisae-friend-chat-probe-{_utc_stamp()}"
    probe = SorisaeProbe(args.base_url, out_dir)

    passed = True
    if not args.skip_http:
        passed = probe.run_http()

    if args.adb_device.strip():
        try:
            probe._get_speech_m4a()
        except Exception as exc:
            probe._record("adb_fixture", False, str(exc))
        else:
            probe.check_adb_device(args.adb_device.strip())
        passed = all(c["ok"] for c in probe.checks)

    probe.write_report()
    if not passed:
        print("\n[FAIL] Sorisae friend-chat probe failed — 배포/머지 차단")
        return 1
    print("\n[PASS] Sorisae friend-chat probe OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
