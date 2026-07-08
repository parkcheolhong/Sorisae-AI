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
import wave
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MIN_APK_BUILD = int(os.getenv("SORISAE_PROBE_MIN_APK_BUILD", "296"))
PROBE_SPEECH_TEXT = os.getenv("SORISAE_PROBE_SPEECH_TEXT", "춘천 맛집 추천해줘")
DOCKER_CONTAINER = os.getenv("SORISAE_PROBE_DOCKER_CONTAINER", "devanalysis114-backend")
FIXTURE_M4A = ROOT / "scripts" / "fixtures" / "sorisae_probe_ko_speech.m4a"
SORISAE_FRIEND_MODEL_ID = os.getenv("SORISAE_PROBE_FRIEND_MODEL_ID", "Qwen/Qwen3-8B-AWQ")
SORISAE_FRIEND_BASE_PORT = os.getenv("SORISAE_PROBE_FRIEND_BASE_PORT", "8009")
ADB_SORISAE_TAP_X = int(os.getenv("SORISAE_PROBE_TAP_X", "739"))
ADB_SORISAE_TAP_Y = int(os.getenv("SORISAE_PROBE_TAP_Y", "479"))


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
    encoded = base64.b64encode(m4a).decode("ascii")
    code = f"""
import base64
import json
from backend.llm.voice_gateway import _normalize_voice_audio_bytes, _run_faster_whisper
raw = base64.b64decode({encoded!r})
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


def _extract_response_text(payload: dict[str, Any]) -> str:
    for key in ("response_text", "response", "answer", "reply"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


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
        if '"route":"sorisae"' in line or '"route": "sorisae"' in line:
            return True
        if "sorisae" in line and "transcript" in line:
            return True
    return False


class SorisaeProbe:
    def __init__(self, base_url: str, out_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.out_dir = out_dir
        self.checks: list[dict[str, Any]] = []
        self._speech_m4a_bytes: bytes | None = None

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
        ok = status == 200 and isinstance(body, dict) and str(body.get("status", "")).lower() == "ok"
        self._record("health", ok, f"status={status}", {"body": body if isinstance(body, dict) else str(body)[:200]})

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
        ok = (
            proc.returncode == 0
            and SORISAE_FRIEND_BASE_PORT in base
            and model == SORISAE_FRIEND_MODEL_ID
            and SORISAE_FRIEND_MODEL_ID in served
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
        text = _extract_response_text(body) if isinstance(body, dict) else ""
        ok = status == 200 and len(text) >= 80
        self._record(
            "friend_chat_text_llm",
            ok,
            f"status={status} response_len={len(text)}",
            {"response_preview": text[:120]},
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
        text = _extract_response_text(body) if isinstance(body, dict) else ""
        transcript = str(body.get("transcript") or "").strip() if isinstance(body, dict) else ""
        detail = str(body.get("detail") or "") if isinstance(body, dict) else str(body)[:200]
        ok = status == 200 and len(text) >= 80 and len(transcript) >= 2
        self._record(
            "friend_chat_audio_speech_m4a",
            ok,
            f"status={status} transcript_len={len(transcript)} response_len={len(text)}",
            {
                "transcript_preview": transcript[:80],
                "response_preview": text[:120],
                "detail": detail[:200],
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
        adb("shell", "am", "force-stop", "com.parkcheolhong.worldlinco")
        adb("logcat", "-c")
        adb("shell", "am", "start", "-n", "com.parkcheolhong.worldlinco/.MainActivity")
        time.sleep(12)
        adb("shell", "input", "tap", str(ADB_SORISAE_TAP_X), str(ADB_SORISAE_TAP_Y))
        time.sleep(6)
        player = _play_probe_audio_on_host(local_m4a)
        try:
            player.wait(timeout=30)
        except subprocess.TimeoutExpired:
            player.kill()
        time.sleep(50)
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        log = adb("logcat", "-d", "-s", "ReactNativeJS:*", timeout=120.0)
        text = log.stdout or ""
        ok_200 = _logcat_has_sorisae_200(text)
        bad_loop = len(re.findall(r"sorisae_segment_skip_preupload", text)) >= 8
        halluc_422 = len(re.findall(r"rejected noise/hallucination", text)) >= 3
        ok_runtime = ok_200 and not bad_loop and not halluc_422
        self._record(
            "adb_sorisae_runtime",
            ok_runtime and ok_build,
            f"segment_200={ok_200} tight_preupload_loop={bad_loop} hallucination_422={halluc_422}",
            {"log_tail": "\n".join(text.splitlines()[-20:])},
        )

    def run_http(self) -> bool:
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
