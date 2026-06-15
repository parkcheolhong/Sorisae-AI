"""WorldLinco 50-language alignment: mobile LANGS ↔ backend SUPPORTED_LANGUAGES."""

from backend.services.nadotongryoksa.translator import (
    MOBILE_SUPPORTED_LANGUAGE_CODES,
    NadoTranslator,
    SUPPORTED_LANGUAGES,
)

# Keep in sync with apps/mobile-nadotongryoksa/App.tsx LANGS[].code
MOBILE_LANGS_FROM_APP = (
    "ko", "en", "zh", "zh-tw", "ja", "es", "fr", "de", "pt", "ru",
    "ar", "hi", "it", "tr", "vi", "th", "id", "ms", "nl", "pl",
    "uk", "sv", "no", "da", "fi", "cs", "ro", "hu", "el", "he",
    "bg", "hr", "sr", "sk", "sl", "lt", "lv", "et", "fa", "ur",
    "bn", "ta", "te", "ml", "gu", "mr", "fil", "sw", "ca", "am",
)


def test_supported_language_count_is_50():
    assert len(SUPPORTED_LANGUAGES) == 50
    assert len(MOBILE_SUPPORTED_LANGUAGE_CODES) == 50


def test_supported_languages_match_mobile_langs():
    backend_codes = set(SUPPORTED_LANGUAGES.keys())
    mobile_codes = set(MOBILE_LANGS_FROM_APP)
    assert backend_codes == mobile_codes
    assert tuple(sorted(backend_codes)) == tuple(sorted(MOBILE_SUPPORTED_LANGUAGE_CODES))


def test_ko_ja_phrase_dictionary():
    translator = NadoTranslator.get_instance()
    assert "こんにちは" in translator.translate("안녕하세요", from_lang="ko", to_lang="ja")
    assert "안녕하세요" in translator.translate("こんにちは", from_lang="ja", to_lang="ko")
