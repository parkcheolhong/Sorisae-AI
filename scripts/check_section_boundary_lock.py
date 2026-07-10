#!/usr/bin/env python3
"""VoIP ↔ 소리새 섹션 경계 잠금 — 한 PR/작업에서 양쪽 소스 동시 수정 시 FAIL.

공유 허용(세션 가드·freeze 오디오·CI) 외 교차 패치를 차단한다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# VoIP 전용 — 소리새 작업 시 수정 금지
VOIP_PREFIXES = (
    "backend/voip/",
    "apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx",
    "apps/mobile-nadotongryoksa/src/services/voipCallClient.ts",
    "apps/mobile-nadotongryoksa/src/services/voipToneService.ts",
    "apps/mobile-nadotongryoksa/src/native/voipAudio",
    "apps/mobile-nadotongryoksa/src/features/voip-auto/",
    "apps/mobile-nadotongryoksa/src/features/voip-voice-relay/",
)

# 소리새 전용 — VoIP 작업 시 수정 금지
SORISAE_PREFIXES = (
    "apps/mobile-nadotongryoksa/src/features/sorisae/",
    "apps/mobile-nadotongryoksa/src/app/appFaceVoicePlayback.ts",
    "apps/mobile-nadotongryoksa/src/features/face-interpretation/",
    "apps/mobile-nadotongryoksa/src/features/face-conversation/",
    "scripts/run_sorisae_friend_chat_probe.py",
    "scripts/check_sorisae_regression_lock.py",
)

# 양쪽 작업에서 공통으로 허용 (세션 헌법·문서·게이트·APK baseline)
SHARED_PREFIXES = (
    "apps/mobile-nadotongryoksa/src/services/voipSessionGuard.ts",
    "apps/mobile-nadotongryoksa/src/services/voiceCaptureLease.ts",
    "knowledge/worldlinco_section_freeze.json",
    "knowledge/worldlinco_apk_baseline.json",
    "knowledge/worldlinco_tuning_config.json",
    "backend/marketplace/worldlinco_section_freeze.py",
    "backend/voip/voip_tts_prosody.py",
    "backend/voip/bridge_voice_io.py",
    "scripts/check_worldlinco_section_ssot_lock.py",
    "scripts/check_section_boundary_lock.py",
    "docs/worldlinco-v2/AUDIO_SECTION_SSOT.md",
    "AGENTS.md",
    "Makefile",
    "evidence/",
    ".runtime/",
    "uploads/",
)

# voice_gateway: friend-chat 본문은 소리새, TTS 운율 분기만 공유 — VoIP 작업 시 diff 에 friend-chat 키워드 있으면 WARN→FAIL
VOIP_FORBIDDEN_IN_VOICE_GATEWAY = (
    "voice/friend-chat",
    "FRIEND_REPLY_CACHE",
    "VOICE_FRIEND_MAX_TOKENS",
    "_friend_chat_base_url",
    "_sorisae_cfg",
)


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _classify(path: str) -> str:
    p = _norm(path)
    for prefix in SHARED_PREFIXES:
        if p == prefix.rstrip("/") or p.startswith(prefix):
            return "shared"
    for prefix in VOIP_PREFIXES:
        if p == prefix.rstrip("/") or p.startswith(prefix):
            return "voip"
    for prefix in SORISAE_PREFIXES:
        if p == prefix.rstrip("/") or p.startswith(prefix):
            return "sorisae"
    if p == "backend/llm/voice_gateway.py":
        return "voice_gateway"
    if p == "apps/mobile-nadotongryoksa/App.tsx":
        return "app_shell"
    return "other"


def _changed_files() -> list[str]:
    files: list[str] = []
    for cmd in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only", "--cached"],
    ):
        try:
            out = subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        for line in out.splitlines():
            line = line.strip()
            if line:
                files.append(_norm(line))
    return sorted(set(files))


def _voice_gateway_voip_touched_sorisae() -> list[str]:
    path = ROOT / "backend/llm/voice_gateway.py"
    if not path.exists():
        return []
    try:
        diff = subprocess.check_output(
            ["git", "diff", "HEAD", "--", "backend/llm/voice_gateway.py"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    if not diff.strip():
        return []
    hits = [kw for kw in VOIP_FORBIDDEN_IN_VOICE_GATEWAY if kw in diff]
    return hits


def main() -> int:
    changed = _changed_files()
    if not changed:
        print("[PASS] section boundary lock (no local diff)")
        return 0

    buckets: dict[str, list[str]] = {"voip": [], "sorisae": [], "voice_gateway": [], "app_shell": [], "shared": [], "other": []}
    for f in changed:
        buckets[_classify(f)].append(f)

    errors: list[str] = []

    if buckets["voip"] and buckets["sorisae"]:
        errors.append(
            "VoIP + 소리새 전용 경로 동시 수정 금지. "
            f"voip={buckets['voip'][:5]} sorisae={buckets['sorisae'][:5]}"
        )

    if buckets["voip"] and buckets["voice_gateway"]:
        hits = _voice_gateway_voip_touched_sorisae()
        if hits:
            errors.append(
                "voice_gateway.py 에 소리새 friend-chat 영역 변경 감지 — VoIP 작업 시 금지: "
                + ", ".join(hits)
            )

    if buckets["app_shell"] and (buckets["voip"] or buckets["sorisae"]):
        errors.append(
            "App.tsx + 섹션 전용 파일 동시 수정 — VoIP/소리새 중 하나만 App.tsx 에 반영하거나 분리 PR 사용"
        )

    if errors:
        print("[FAIL] section boundary lock")
        for err in errors:
            print(f"  - {err}")
        print("\n  VoIP만: backend/voip/*, VoIPCallScreen, voipCallClient …")
        print("  소리새만: features/sorisae/*, appFaceVoicePlayback …")
        print("  공유: voipSessionGuard, voiceCaptureLease, freeze(오디오), CI 스크립트")
        return 1

    print("[PASS] section boundary lock")
    if buckets["voip"]:
        print(f"  voip-only: {len(buckets['voip'])} files")
    if buckets["sorisae"]:
        print(f"  sorisae-only: {len(buckets['sorisae'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
