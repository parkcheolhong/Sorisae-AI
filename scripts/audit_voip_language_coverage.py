#!/usr/bin/env python3
"""Audit VoIP language coverage across mobile, translator, STT, and TTS layers."""
from __future__ import annotations

import re
from pathlib import Path

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES
from backend.voip_language_locales import (
    EDGE_TTS_NEURAL_VOICES,
    MOBILE_TTS_LOCALES,
    resolve_whisper_language_hint,
)

ROOT = Path(__file__).resolve().parents[1]
MOBILE_LOCALES = ROOT / "apps" / "mobile-nadotongryoksa" / "src" / "constants" / "voipLanguageLocales.ts"

backend_codes = set(SUPPORTED_LANGUAGES.keys())
mobile_ts_codes = set(
    re.findall(r"^\s+'?([a-z]{2,3}(?:-[a-z]+)?)'?: '", MOBILE_LOCALES.read_text(encoding="utf-8"), re.M)
)

whisper_hinted = {code for code in backend_codes if resolve_whisper_language_hint(code)}

print("=== SSOT parity ===")
print(f"backend: {len(backend_codes)}")
print(f"mobile voipLanguageLocales.ts: {len(mobile_ts_codes)}")
print(f"mobile/backend match: {mobile_ts_codes == backend_codes}")
print(f"MOBILE_TTS_LOCALES: {len(MOBILE_TTS_LOCALES)}/{len(backend_codes)}")
print(f"EDGE_TTS_NEURAL_VOICES: {len(EDGE_TTS_NEURAL_VOICES)}/{len(backend_codes)}")
print(f"STT whisper hint: {len(whisper_hinted)}/{len(backend_codes)}")

missing = sorted(backend_codes - whisper_hinted)
if missing:
    print("missing whisper hint:", ", ".join(missing))
else:
    print("STT/TTS 50-country coverage: OK")
