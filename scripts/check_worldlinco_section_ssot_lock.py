#!/usr/bin/env python3
"""WorldLinco 섹션 SSOT 회귀 잠금 — 오디오 freeze + APK baseline 분리.

APK: knowledge/worldlinco_apk_baseline.json
오디오: knowledge/worldlinco_section_freeze.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "knowledge" / "worldlinco_section_freeze.json"
APK_BASELINE = ROOT / "knowledge" / "worldlinco_apk_baseline.json"

FORBIDDEN: list[tuple[str, str, str]] = [
    (
        "apps/mobile-nadotongryoksa/src/features/sorisae/sorisaeCaptureSegment.ts",
        r"audioBase64:\s*null,\s*audioFormat:\s*null",
        "소리새 server TTS 우회(null,null) 재도입 금지",
    ),
    (
        "apps/mobile-nadotongryoksa/src/app/appFaceVoicePlayback.ts",
        r"Math\.min\(30_000,\s*Math\.max\(6_000,\s*speakText\.length\s*\*\s*220",
        "30s TTS 상한 회귀 금지 — computeFaceTtsSafetyCapMs SSOT 사용",
    ),
    (
        "apps/mobile-nadotongryoksa/src/services/worldlincoTuningConfig.ts",
        r"playback_cap_ms:\s*8500",
        "playback_cap_ms 8.5s 회귀 금지",
    ),
    (
        "backend/llm/voice_gateway.py",
        r'return \("-4%", "\+12%", "\+1Hz"\)',
        "전역 Edge TTS +12% 회귀 금지 — VoIP/기본은 +6%, 소리새는 feature_id 분리",
    ),
    (
        "backend/voip/media_bridge.py",
        r'feature_id\s*=\s*["\']face\.interpret',
        "VoIP 브리지 TTS에 face.interpret 주입 금지",
    ),
    (
        "backend/voip/media_bridge.py",
        r'_synthesize_tts\([^)]*face\.interpret',
        "VoIP 브리지 _synthesize_tts face.interpret 인자 금지",
    ),
    (
        "backend/voip/media_bridge.py",
        r"push_timeline_pad|_make_plc_hold|_remember_hold_pcm",
        "VoIP 브리지 미문서 PLC/타임라인 패딩 금지 — SSOT AUDIO_SECTION_SSOT §7",
    ),
    (
        "apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx",
        r"setInterval\([^)]*reapplyVoipCallAudioStack|reapplyVoipCallAudioStack",
        "VoIP 화면 주기적 reapplyVoipCallAudioStack 금지",
    ),
    (
        "apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx",
        r"enableVoipAudio\(true,\s*true\)|setVoipSpeakerphone\(true\)",
        "VoIP 화면 스피커 강제 ON 금지 — 사용자 토글·defaultSpeakerOn 만",
    ),
    (
        "apps/mobile-nadotongryoksa/src/services/voipCallClient.ts",
        r"ICE_DISCONNECT_GRACE_MS\s*=\s*(?!2500)\d+",
        "ICE disconnected grace 는 2500ms 고정(명시 PR 전 변경 금지)",
    ),
    (
        "apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx",
        r"FEATURE_IDS\.faceInterpret|['\"]face\.interpret['\"]",
        "VoIP 화면 face.interpret TTS 경로 금지",
    ),
]

REQUIRED: list[tuple[str, str, str]] = [
    (
        "apps/mobile-nadotongryoksa/src/app/appFaceVoicePlayback.ts",
        "computeFaceTtsSafetyCapMs",
        "소리새 TTS safety cap SSOT",
    ),
    (
        "apps/mobile-nadotongryoksa/src/app/appFaceVoicePlayback.ts",
        "isVoipSessionActive",
        "통화 중 VoIP 오디오 모드 해제 금지 가드",
    ),
    (
        "backend/llm/voice_gateway.py",
        "_resolve_edge_tts_prosody",
        "기능별 Edge TTS 운율 분리",
    ),
    (
        "apps/mobile-nadotongryoksa/src/services/voipSessionGuard.ts",
        "quiesceNonVoipAudioForVoipSession",
        "VoIP 세션 시 비-VoIP 오디오 정지",
    ),
    (
        "apps/mobile-nadotongryoksa/src/services/voiceCaptureLease.ts",
        "acquireVoiceCapture",
        "마이크 단일 소유 lease",
    ),
    (
        "backend/llm/voice_gateway.py",
        "_friend_chat_dedicated_instance",
        "소리새 전용 vLLM 라우트",
    ),
    (
        "backend/marketplace/worldlinco_section_freeze.py",
        "frozen_sorisae_edge_tts_prosody_ko",
        "소리새 Edge TTS freeze 로더",
    ),
    (
        "backend/marketplace/worldlinco_section_freeze.py",
        "frozen_voip_edge_tts_prosody_ko_default",
        "VoIP Edge TTS freeze 로더",
    ),
    (
        "backend/voip/media_bridge.py",
        "bridge_voice_io",
        "VoIP 브리지 STT/TTS는 bridge_voice_io 어댑터만",
    ),
    (
        "backend/voip/media_bridge.py",
        "bridge_synthesize_tts",
        "VoIP 브리지 TTS bridge_voice_io 경유",
    ),
]


def _load_freeze() -> dict:
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _check_freeze_manifest(errors: list[str]) -> None:
    if not FREEZE.exists():
        errors.append(f"missing freeze manifest: {FREEZE}")
        return
    if not APK_BASELINE.exists():
        errors.append(f"missing apk baseline: {APK_BASELINE}")
        return
    freeze = _load_freeze()
    mobile = json.loads(APK_BASELINE.read_text(encoding="utf-8"))
    sorisae = (freeze.get("sections") or {}).get("sorisae") or {}

    app_json = json.loads((ROOT / "apps/mobile-nadotongryoksa/app.json").read_text(encoding="utf-8"))
    vc = int(app_json["expo"]["android"]["versionCode"])
    vn = str(app_json["expo"]["version"])
    if vc < int(mobile.get("versionCode", 0)):
        errors.append(f"app.json versionCode {vc} < freeze baseline {mobile.get('versionCode')}")
    if vn != str(mobile.get("versionName", vn)):
        errors.append(f"app.json versionName {vn!r} != apk baseline {mobile.get('versionName')!r}")

    probe = (ROOT / "scripts/run_sorisae_friend_chat_probe.py").read_text(encoding="utf-8")
    min_build = int(mobile.get("probe_min_build", 0))
    if f'MIN_APK_BUILD = int(os.getenv("SORISAE_PROBE_MIN_APK_BUILD", "{min_build}"))' not in probe:
        if f'"{min_build}"' not in probe:
            errors.append(f"probe MIN_APK_BUILD != freeze {min_build}")

    timing = (ROOT / "apps/mobile-nadotongryoksa/src/features/shared/audioConversationTiming.ts").read_text(
        encoding="utf-8"
    )
    cap = int(sorisae.get("playback_cap_ms", 0))
    if f"FACE_CONVERSATION_PLAYBACK_CAP_MS = {cap:_}" not in timing:
        errors.append(f"FACE_CONVERSATION_PLAYBACK_CAP_MS != freeze {cap}")

    tuning = (ROOT / "apps/mobile-nadotongryoksa/src/services/worldlincoTuningConfig.ts").read_text(encoding="utf-8")
    cap_patterns = (f"playback_cap_ms: {cap}", f"playback_cap_ms: {cap:_}")
    if not any(p in tuning for p in cap_patterns):
        errors.append(f"worldlincoTuningConfig playback_cap_ms != freeze {cap}")

    vg = (ROOT / "backend/llm/voice_gateway.py").read_text(encoding="utf-8")
    if "frozen_sorisae_edge_tts_prosody_ko" not in vg:
        errors.append("voice_gateway must load sorisae prosody from section freeze SSOT")
    if "voip_tts_prosody" not in vg:
        errors.append("voice_gateway VoIP default prosody must delegate to backend.voip.voip_tts_prosody")

    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from backend.marketplace.worldlinco_section_freeze import (
            frozen_sorisae_edge_tts_prosody_ko,
            frozen_voip_edge_tts_prosody_ko_default,
        )

        prosody = sorisae.get("edge_tts_prosody_ko") or []
        if len(prosody) == 3:
            expected = tuple(str(x) for x in prosody)
            if frozen_sorisae_edge_tts_prosody_ko() != expected:
                errors.append(f"freeze loader sorisae prosody != manifest {expected}")

        voip_default = ((freeze.get("sections") or {}).get("voip") or {}).get("edge_tts_prosody_ko_default") or []
        if len(voip_default) == 3:
            expected_voip = tuple(str(x) for x in voip_default)
            if frozen_voip_edge_tts_prosody_ko_default() != expected_voip:
                errors.append(f"freeze loader voip prosody != manifest {expected_voip}")
    except Exception as exc:
        errors.append(f"section freeze loader: {exc}")


def main() -> int:
    errors: list[str] = []
    _check_freeze_manifest(errors)

    for rel, pattern, reason in FORBIDDEN:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        if re.search(pattern, path.read_text(encoding="utf-8")):
            errors.append(f"FORBIDDEN [{reason}] in {rel}")

    for rel, snippet, reason in REQUIRED:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        if snippet not in path.read_text(encoding="utf-8"):
            errors.append(f"REQUIRED missing [{reason}] in {rel}: {snippet!r}")

    if errors:
        print("[FAIL] worldlinco section SSOT lock")
        for err in errors:
            print(f"  - {err}")
        print(f"\n  freeze manifest: {FREEZE.relative_to(ROOT)}")
        print("  의도적 변경 시 freeze JSON + 회귀 테스트를 함께 갱신하세요.")
        return 1

    print("[PASS] worldlinco section SSOT lock (baseline frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
