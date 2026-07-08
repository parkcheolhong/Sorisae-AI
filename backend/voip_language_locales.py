"""WorldLinco VoIP STT/TTS locale SSOT — synced with mobile App.tsx LANGS (50 codes)."""
from __future__ import annotations

from typing import Dict, Optional

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES

# BCP-47 locale tags used by expo-speech / device TTS.
MOBILE_TTS_LOCALES: Dict[str, str] = {
    "ko": "ko-KR",
    "en": "en-US",
    "zh": "zh-CN",
    "zh-tw": "zh-TW",
    "ja": "ja-JP",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "pt": "pt-BR",
    "ru": "ru-RU",
    "ar": "ar-SA",
    "hi": "hi-IN",
    "it": "it-IT",
    "tr": "tr-TR",
    "vi": "vi-VN",
    "th": "th-TH",
    "id": "id-ID",
    "ms": "ms-MY",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "uk": "uk-UA",
    "sv": "sv-SE",
    "no": "nb-NO",
    "da": "da-DK",
    "fi": "fi-FI",
    "cs": "cs-CZ",
    "ro": "ro-RO",
    "hu": "hu-HU",
    "el": "el-GR",
    "he": "he-IL",
    "bg": "bg-BG",
    "hr": "hr-HR",
    "sr": "sr-RS",
    "sk": "sk-SK",
    "sl": "sl-SI",
    "lt": "lt-LT",
    "lv": "lv-LV",
    "et": "et-EE",
    "fa": "fa-IR",
    "ur": "ur-PK",
    "bn": "bn-BD",
    "ta": "ta-IN",
    "te": "te-IN",
    "ml": "ml-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
    "fil": "fil-PH",
    "sw": "sw-KE",
    "ca": "ca-ES",
    "am": "am-ET",
}

# Microsoft Edge neural voices (one default female/neutral voice per locale).
EDGE_TTS_NEURAL_VOICES: Dict[str, str] = {
    "ko": "ko-KR-SunHiNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "zh-tw": "zh-TW-HsiaoChenNeural",
    "ja": "ja-JP-NanamiNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "hi": "hi-IN-SwaraNeural",
    "it": "it-IT-ElsaNeural",
    "tr": "tr-TR-EmelNeural",
    "vi": "vi-VN-HoaiMyNeural",
    "th": "th-TH-PremwadeeNeural",
    "id": "id-ID-GadisNeural",
    "ms": "ms-MY-YasminNeural",
    "nl": "nl-NL-ColetteNeural",
    "pl": "pl-PL-ZofiaNeural",
    "uk": "uk-UA-PolinaNeural",
    "sv": "sv-SE-SofieNeural",
    "no": "nb-NO-PernilleNeural",
    "da": "da-DK-ChristelNeural",
    "fi": "fi-FI-NooraNeural",
    "cs": "cs-CZ-VlastaNeural",
    "ro": "ro-RO-AlinaNeural",
    "hu": "hu-HU-NoemiNeural",
    "el": "el-GR-AthinaNeural",
    "he": "he-IL-HilaNeural",
    "bg": "bg-BG-KalinaNeural",
    "hr": "hr-HR-GabrijelaNeural",
    "sr": "sr-RS-SophieNeural",
    "sk": "sk-SK-ViktoriaNeural",
    "sl": "sl-SI-PetraNeural",
    "lt": "lt-LT-OnaNeural",
    "lv": "lv-LV-EveritaNeural",
    "et": "et-EE-AnuNeural",
    "fa": "fa-IR-DilaraNeural",
    "ur": "ur-PK-UzmaNeural",
    "bn": "bn-BD-NabanitaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "ml": "ml-IN-SobhanaNeural",
    "gu": "gu-IN-DhwaniNeural",
    "mr": "mr-IN-AarohiNeural",
    "fil": "fil-PH-BlessicaNeural",
    "sw": "sw-KE-ZuriNeural",
    "ca": "ca-ES-JoanaNeural",
    "am": "am-ET-MekdesNeural",
}

# faster-whisper language codes (ISO 639-1); special remaps only where required.
_WHISPER_LANG_OVERRIDES: Dict[str, str] = {
    "zh-tw": "zh",
    "fil": "tl",
    "no": "no",
}

_WHISPER_INITIAL_PROMPTS: Dict[str, str] = {
    "ko": "회의 통역 문장입니다.",
    "en": "Conversation translation sentence.",
    "ja": "会議の通訳文です。",
    "zh": "会议翻译句子。",
    "vi": "Câu dịch thuật hội thoại.",
    "th": "ประโยคแปลบทสนทนา",
    "es": "Frase de traducción de conversación.",
    "fr": "Phrase de traduction de conversation.",
    "de": "Satz für Gesprächsübersetzung.",
    "pt": "Frase de tradução de conversa.",
    "ru": "Предложение для перевода разговора.",
    "ar": "جملة ترجمة المحادثة.",
    "hi": "बातचीत अनुवाद वाक्य।",
    "it": "Frase di traduzione conversazione.",
    "tr": "Konuşma çeviri cümlesi.",
    "id": "Kalimat terjemahan percakapan.",
    "ms": "Ayat terjemahan perbualan.",
    "nl": "Zin voor gespreksvertaling.",
    "pl": "Zdanie tłumaczenia rozmowy.",
    "uk": "Речення для перекладу розмови.",
    "sv": "Mening för samtalsöversättning.",
    "no": "Setning for samtaleoversettelse.",
    "da": "Sætning til samtaleoversættelse.",
    "fi": "Lause keskustelukäännökseen.",
    "cs": "Věta pro překlad konverzace.",
    "ro": "Propoziție pentru traducerea conversației.",
    "hu": "Mondat beszélgetésfordításhoz.",
    "el": "Πρόταση μετάφρασης συνομιλίας.",
    "he": "משפט לתרגום שיחה.",
    "bg": "Изречение за превод на разговор.",
    "hr": "Rečenica za prijevod razgovora.",
    "sr": "Реченица за превод разговора.",
    "sk": "Veta na preklad rozhovoru.",
    "sl": "Stavek za prevod pogovora.",
    "lt": "Sakinys pokalbio vertimui.",
    "lv": "Teikums sarunas tulkojumam.",
    "et": "Lause vestluse tõlkeks.",
    "fa": "جمله ترجمه مکالمه.",
    "ur": "گفتگو ترجمہ جملہ۔",
    "bn": "কথোপকথন অনুবাদ বাক্য।",
    "ta": "உரையாடல் மொழிபெயர்ப்பு வாக்கியம்.",
    "te": "సంభాషణ అనువాద వాక్యం.",
    "ml": "സംഭാഷണ വിവർത്തന വാക്യം.",
    "gu": "વાતચીત અનુવાદ વાક્ય.",
    "mr": "संभाषण भाषांतर वाक्य.",
    "fil": "Pangungusap para sa pagsasalin ng usapan.",
    "sw": "Sentensi ya tafsiri ya mazungumzo.",
    "ca": "Frase de traducció de conversa.",
    "am": "የውይይት ትርጉም ዓረፍተ ነገር።",
}


def _normalize_lang_code(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower()
    if not normalized or normalized == "auto":
        return None
    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    base = normalized.split("-")[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    return None


def resolve_whisper_language_hint(language: Optional[str]) -> Optional[str]:
    lang_code = _normalize_lang_code(language)
    if not lang_code:
        return None
    return _WHISPER_LANG_OVERRIDES.get(lang_code, lang_code.split("-")[0])


def resolve_whisper_initial_prompt(language: Optional[str]) -> str:
    lang_code = _normalize_lang_code(language)
    if not lang_code:
        return ""
    whisper_hint = resolve_whisper_language_hint(lang_code)
    return _WHISPER_INITIAL_PROMPTS.get(lang_code) or _WHISPER_INITIAL_PROMPTS.get(
        whisper_hint or "",
        "Conversation translation sentence.",
    )


def resolve_mobile_tts_locale(language: Optional[str]) -> str:
    lang_code = _normalize_lang_code(language)
    if not lang_code:
        return MOBILE_TTS_LOCALES["ko"]
    return MOBILE_TTS_LOCALES.get(lang_code, MOBILE_TTS_LOCALES["en"])


def resolve_edge_tts_voice(language: Optional[str]) -> str:
    lang_code = _normalize_lang_code(language)
    if not lang_code:
        return EDGE_TTS_NEURAL_VOICES["ko"]
    return EDGE_TTS_NEURAL_VOICES.get(lang_code, EDGE_TTS_NEURAL_VOICES["en"])


def assert_voip_locale_coverage() -> None:
    missing_mobile = sorted(set(SUPPORTED_LANGUAGES) - set(MOBILE_TTS_LOCALES))
    missing_edge = sorted(set(SUPPORTED_LANGUAGES) - set(EDGE_TTS_NEURAL_VOICES))
    if missing_mobile or missing_edge:
        raise RuntimeError(
            "VoIP locale coverage incomplete: "
            f"mobile={missing_mobile} edge={missing_edge}"
        )


assert_voip_locale_coverage()
