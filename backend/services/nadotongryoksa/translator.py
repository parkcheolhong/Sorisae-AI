"""
WorldLinco 전용 번역 엔진 (NadoTranslator)
- 소리새(SorisaeInterpreter)와 완전 독립
- 50개국어 지원
- googletrans 3.x async + ThreadPoolExecutor (FastAPI 이벤트루프 충돌 방지)
- 자체 여행 필수 문장 사전 캐시 (DB 없이 즉시 응답)
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import re
from threading import Lock
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nado.translator")

# ──────────────────────────────────────────────
# 50개국어 (모바일 App.tsx LANGS 와 동기화)
# ──────────────────────────────────────────────
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "ko": "한국어",
    "en": "영어",
    "zh": "중국어(간체)",
    "zh-tw": "중국어(번체)",
    "ja": "일본어",
    "es": "스페인어",
    "fr": "프랑스어",
    "de": "독일어",
    "pt": "포르투갈어",
    "ru": "러시아어",
    "ar": "아랍어",
    "hi": "힌디어",
    "it": "이탈리아어",
    "tr": "터키어",
    "vi": "베트남어",
    "th": "태국어",
    "id": "인도네시아어",
    "ms": "말레이어",
    "nl": "네덜란드어",
    "pl": "폴란드어",
    "uk": "우크라이나어",
    "sv": "스웨덴어",
    "no": "노르웨이어",
    "da": "덴마크어",
    "fi": "핀란드어",
    "cs": "체코어",
    "ro": "루마니아어",
    "hu": "헝가리어",
    "el": "그리스어",
    "he": "히브리어",
    "bg": "불가리아어",
    "hr": "크로아티아어",
    "sr": "세르비아어",
    "sk": "슬로바키아어",
    "sl": "슬로베니아어",
    "lt": "리투아니아어",
    "lv": "라트비아어",
    "et": "에스토니아어",
    "fa": "페르시아어",
    "ur": "우르두어",
    "bn": "벵골어",
    "ta": "타밀어",
    "te": "텔루구어",
    "ml": "말라얄람어",
    "gu": "구자라트어",
    "mr": "마라티어",
    "fil": "필리핀어",
    "sw": "스와힐리어",
    "ca": "카탈루냐어",
    "am": "암하라어",
}

# 모바일 `App.tsx` LANGS 코드 목록 (정합 감사용 SSOT)
MOBILE_SUPPORTED_LANGUAGE_CODES: Tuple[str, ...] = tuple(SUPPORTED_LANGUAGES.keys())

SUPPORTED_DIALECT_COUNTRY_PROFILES: Dict[str, Dict[str, str]] = {
    "jeju": {"language": "ko", "label": "제주"},
    "guangdong": {"language": "zh", "label": "광둥"},
    "kansai": {"language": "ja", "label": "간사이"},
    "bihar": {"language": "hi", "label": "비하르"},
    "naples": {"language": "it", "label": "나폴리"},
}

_DIALECT_REPLACEMENTS: Dict[Tuple[str, str], List[Tuple[re.Pattern[str], str]]] = {
    ("ko", "jeju"): [
        (re.compile(r"혼저\s*옵서예", re.IGNORECASE), "어서 오세요"),
        (re.compile(r"하영\s*고맙수다", re.IGNORECASE), "많이 고맙습니다"),
    ],
    ("zh", "guangdong"): [
        (re.compile(r"唔该"), "谢谢"),
        (re.compile(r"喺边度食饭"), "在哪里吃饭"),
    ],
    ("ja", "kansai"): [
        (re.compile(r"ほんま"), "本当"),
        (re.compile(r"おおきに"), "ありがとう"),
        (re.compile(r"あかんで"), "だめで"),
    ],
    ("hi", "bihar"): [
        (
            re.compile(r"humra kitna hai re, jaldi karo na", re.IGNORECASE),
            "hamara kitna hai, kripya jaldi kijiye",
        ),
    ],
    ("it", "naples"): [
        (re.compile(r"Uaglio", re.IGNORECASE), "ragazzo"),
        (re.compile(r"che fai mo", re.IGNORECASE), "cosa fai adesso"),
    ],
}

# googletrans에서 사용하는 언어코드 매핑 (차이가 있는 것만)
_GTRANS_LANG_MAP: Dict[str, str] = {
    "zh": "zh-cn",
    "zh-tw": "zh-tw",
}

# ──────────────────────────────────────────────
# 여행 필수 문장 사전 (즉시 응답용 캐시)
# 키: (from_lang, to_lang, 원문 strip lowercase)
# ──────────────────────────────────────────────
_PHRASE_DICT: Dict[Tuple[str, str, str], str] = {
    # 한국어 → 영어
    ("ko", "en", "안녕하세요"): "Hello",
    ("ko", "en", "감사합니다"): "Thank you",
    ("ko", "en", "도와주세요"): "Please help me",
    ("ko", "en", "얼마예요?"): "How much is it?",
    ("ko", "en", "화장실이 어디예요?"): "Where is the restroom?",
    ("ko", "en", "물 한 잔 주세요"): "A glass of water, please",
    ("ko", "en", "택시를 불러주세요"): "Please call a taxi",
    # 한국어 → 중국어
    ("ko", "zh", "안녕하세요"): "你好",
    ("ko", "zh", "감사합니다"): "谢谢",
    ("ko", "zh", "얼마예요?"): "多少钱？",
    # 한국어 → 일본어
    ("ko", "ja", "안녕하세요"): "こんにちは",
    ("ko", "ja", "감사합니다"): "ありがとうございます",
    # 일본어 → 한국어
    ("ja", "ko", "こんにちは"): "안녕하세요",
    ("ja", "ko", "ありがとう"): "감사합니다",
    # 영어 → 한국어
    ("en", "ko", "hello"): "안녕하세요",
    ("en", "ko", "thank you"): "감사합니다",
    ("en", "ko", "help me"): "도와주세요",
}


# ──────────────────────────────────────────────
# V.2 음성부(LLM) — vLLM(OpenAI 호환) 문맥 번역 경로
#   · 기본 1차 엔진. 실패/비활성 시 googletrans 폴백.
#   · 응답 스키마·핫패스 계약 변경 없음(번역 내부 엔진만 교체).
# ──────────────────────────────────────────────
def _llm_translate_enabled() -> bool:
    return os.getenv("WORLDLINCO_LLM_TRANSLATE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
        "",
    )


def _llm_translate_base_url() -> str:
    raw = (
        os.getenv("LLM_TRANSLATE_BASE_URL")
        or os.getenv("OLLAMA_BASE")
        or "http://host.docker.internal:8008/v1"
    ).strip().rstrip("/")
    # 컨테이너 내부에서 127.0.0.1/localhost는 호스트의 vLLM에 닿지 못하므로 host.docker.internal로 보정.
    # (네이티브 호스트 실행 시에는 보정하지 않도록 /.dockerenv 로 컨테이너 여부를 가드)
    if os.path.exists("/.dockerenv"):
        raw = raw.replace("://127.0.0.1", "://host.docker.internal").replace(
            "://localhost", "://host.docker.internal"
        )
    return raw


def _llm_translate_timeout() -> float:
    try:
        return float(os.getenv("LLM_TRANSLATE_TIMEOUT", "8"))
    except (TypeError, ValueError):
        return 8.0


_DEFAULT_LLM_TRANSLATE_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
_DISCOVERED_LLM_MODEL: Optional[str] = None


def _discover_served_model() -> Optional[str]:
    """vLLM /v1/models 의 실서빙 모델 ID를 1회 조회 후 캐시.

    채팅 모델 기본값(get_chat_model)은 서버 실서빙 모델과 다를 수 있어
    (예: .env=14B 인데 서버는 32B) 404를 유발하므로, 실제 서빙 ID를 직접 확인한다.
    """
    global _DISCOVERED_LLM_MODEL
    if _DISCOVERED_LLM_MODEL is not None:
        return _DISCOVERED_LLM_MODEL or None
    try:
        import httpx

        response = httpx.get(f"{_llm_translate_base_url()}/models", timeout=5)
        if response.status_code == 200:
            data = (response.json() or {}).get("data") or []
            if data:
                model_id = str(data[0].get("id") or "").strip()
                if model_id:
                    _DISCOVERED_LLM_MODEL = model_id
                    return model_id
    except Exception as exc:
        logger.warning("llm-translate model discovery failed: %s", exc)
    _DISCOVERED_LLM_MODEL = ""  # 음수 캐시(재조회 폭주 방지)
    return None


def _resolve_llm_translate_model() -> str:
    override = os.getenv("LLM_TRANSLATE_MODEL")
    if override:
        return override
    return _discover_served_model() or _DEFAULT_LLM_TRANSLATE_MODEL


# 모델 프롬프트용 영어 언어명(주요 언어). 미등록 코드는 한국어명(코드)로 폴백.
_LLM_LANG_NAMES: Dict[str, str] = {
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "it": "Italian",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "nl": "Dutch",
    "pl": "Polish",
}


def _llm_lang_label(code: str) -> str:
    english = _LLM_LANG_NAMES.get(code)
    if english:
        return english
    korean = SUPPORTED_LANGUAGES.get(code)
    return f"{korean} ({code})" if korean else code


_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
_KANA_RE = re.compile(r"[\u3040-\u30ff]")


def _has_residual_source_script(text: str, to_lang: str) -> bool:
    """대상 언어 스크립트와 양립 불가한 원문 스크립트가 남아있으면 True(번역 누수).

    예) ko→ja 인데 결과에 한글이 남음, 또는 대상이 가나를 안 쓰는데 가나가 남음.
    LLM(코드 모델)이 원문 일부를 미번역으로 흘리는 경우를 잡아 googletrans로 폴백한다.
    """
    if to_lang != "ko" and _HANGUL_RE.search(text):
        return True
    # 가나는 일본어 전용. 대상이 일본어가 아닌데 가나가 남으면 누수.
    if to_lang != "ja" and _KANA_RE.search(text):
        return True
    return False


def _strip_llm_translation(content: str) -> str:
    out = (content or "").strip()
    if not out:
        return ""
    # 모델이 따옴표/접두사를 덧붙이는 경우 정리.
    for prefix in ("translation:", "translated:", "번역:", "translation -", "output:"):
        if out.lower().startswith(prefix):
            out = out[len(prefix):].strip()
    if len(out) >= 2 and out[0] in "\"'“”「『" and out[-1] in "\"'“”」』":
        out = out[1:-1].strip()
    return out


class NadoTranslator:
    """WorldLinco 전용 번역기. 소리새 의존성 없음."""

    _instance: Optional["NadoTranslator"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        worker_count = max(1, int(os.getenv("NADO_TRANSLATOR_MAX_WORKERS", "4")))
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=worker_count)
        self._cache: Dict[Tuple[str, str, str], str] = {}
        self._cache_lock: Lock = Lock()

    @classmethod
    def get_instance(cls) -> "NadoTranslator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ──────────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────────

    def translate(
        self,
        text: str,
        from_lang: str = "ko",
        to_lang: str = "en",
        region_hint: str | None = None,
        context_hint: str | None = None,
    ) -> str:
        """
        텍스트를 번역한다.
        1) 로컬 사전 캐시 우선
        2) googletrans fallback
        Returns translated string.

        ``context_hint``(선택, V.2 Session Core): 최근 대화 맥락 요약. 제공되면 LLM
        프롬프트에 보조 힌트로만 주입해 호칭·대명사·존댓말 일관성을 돕는다. 맥락은
        턴마다 달라지므로, 제공 시 원격 캐시를 우회한다(캐시 오염 방지). ``None``이면
        기존 동작과 100% 동일(대면 경로 등 호출부 무영향).
        """
        text = text.strip()
        if not text:
            return text

        from_lang = from_lang.lower().strip()
        to_lang = to_lang.lower().strip()
        text = self._normalize_dialect_text(text, from_lang, region_hint)

        # 동일 언어이면 그대로
        if from_lang == to_lang:
            return text

        # 1) 로컬 사전(문맥 무관 고정 표현)은 항상 우선.
        cached = _PHRASE_DICT.get((from_lang, to_lang, text.lower()))
        if cached:
            return cached

        use_context = bool(context_hint and context_hint.strip())
        cache_key = (from_lang, to_lang, text)
        # 맥락 주입 시에는 캐시 우회(턴별로 결과가 달라질 수 있음).
        if not use_context:
            with self._cache_lock:
                cached_remote = self._cache.get(cache_key)
            if cached_remote:
                return cached_remote

        # 2) LLM 문맥 번역 (1차) — 실시간 통역 품질. 실패/비활성 시 googletrans 폴백.
        translated = self._llm_translate(
            text,
            from_lang,
            to_lang,
            context_hint=context_hint if use_context else None,
        )
        if not translated:
            translated = self._googletrans(text, from_lang, to_lang)
        # 성공한 번역만 캐시한다. 두 엔진 모두 실패(일시적 네트워크/타임아웃)한 경우
        # 원문을 캐시에 넣으면 그 문장이 영구히 미번역으로 고정되므로 캐시하지 않고,
        # 핫패스 계약(문자열 반환)을 지키기 위해 원문을 그대로 반환한다(다음 호출에서 재시도).
        if translated:
            # 맥락 주입 결과는 턴 특이적이라 캐시하지 않는다.
            if not use_context:
                with self._cache_lock:
                    self._cache[cache_key] = translated
            return translated
        logger.warning(
            "translate fallthrough (모든 엔진 실패, 캐시 생략) %s→%s: %r",
            from_lang,
            to_lang,
            text[:40],
        )
        return text

    def supported_languages(self) -> Dict[str, str]:
        return dict(SUPPORTED_LANGUAGES)

    @staticmethod
    def _normalize_dialect_text(
        text: str,
        source_lang: str,
        region_hint: str | None,
    ) -> str:
        normalized_region = str(region_hint or "").strip().lower()
        if not normalized_region:
            return text
        replacements = _DIALECT_REPLACEMENTS.get((source_lang, normalized_region), [])
        normalized = text
        for pattern, replacement in replacements:
            normalized = pattern.sub(replacement, normalized)
        return normalized

    # ──────────────────────────────────────────────
    # 내부 구현
    # ──────────────────────────────────────────────

    def _googletrans(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """
        googletrans 3.x async를 별도 스레드/이벤트루프에서 실행.
        FastAPI 이벤트루프와 충돌하지 않도록 ThreadPoolExecutor 사용.

        실패(타임아웃/예외) 시 원문 대신 ``None``을 반환한다. 원문을 반환하면
        호출부에서 '번역 성공'으로 오인해 미번역 원문을 캐시·재생하게 되므로,
        실패를 명시적으로 알려 캐시 오염과 미번역 송출을 방지한다.
        """
        src = _GTRANS_LANG_MAP.get(from_lang, from_lang)
        dest = _GTRANS_LANG_MAP.get(to_lang, to_lang)

        async def _do() -> str:
            from googletrans import Translator
            t = Translator()
            result = await t.translate(text, src=src, dest=dest)
            return result.text

        def _run() -> str:
            return asyncio.run(_do())

        try:
            future = self._pool.submit(_run)
            return future.result(timeout=20)
        except concurrent.futures.TimeoutError:
            logger.warning("googletrans timeout: %s→%s '%s'", from_lang, to_lang, text[:30])
            return None
        except Exception as exc:
            logger.warning("googletrans error: %s→%s '%s' err=%s", from_lang, to_lang, text[:30], exc)
            return None

    def _llm_translate(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
        context_hint: str | None = None,
    ) -> Optional[str]:
        """vLLM(OpenAI 호환) 문맥 번역. 실패/비활성 시 None을 반환해 googletrans로 폴백.

        ``context_hint``(선택): 최근 대화 맥락 요약. 제공 시 system 프롬프트에 보조 힌트로만
        덧붙여 호칭·대명사·존댓말 일관성을 돕는다(맥락 자체는 번역/출력하지 않음).
        """
        if not _llm_translate_enabled():
            return None
        try:
            import httpx

            src = _llm_lang_label(from_lang)
            tgt = _llm_lang_label(to_lang)
            system = (
                "You are a professional real-time speech interpreter. "
                f"Translate the user's message from {src} to {tgt}. "
                f"Output ONLY the {tgt} translation as natural spoken text. "
                f"Translate the ENTIRE message completely into {tgt}; never leave any "
                f"{src} words untranslated and never mix scripts. "
                "Do not add quotes, notes, romanization, pronunciation, or the original text. "
                "Preserve meaning, proper nouns, numbers, and tone. "
                "If the input is not coherent speech in the source language, output nothing."
            )
            hint = (context_hint or "").strip()
            if hint:
                # 맥락은 일관성 보조용으로만 사용. 절대 번역/출력 대상이 아님.
                system += (
                    " For consistency of names, pronouns, and honorifics, consider this "
                    "recent conversation context (do NOT translate or output it): "
                    f"{hint[:600]}"
                )
            payload = {
                "model": _resolve_llm_translate_model(),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.1,
                "max_tokens": min(1024, max(64, len(text) * 4)),
                "stream": False,
            }
            response = httpx.post(
                f"{_llm_translate_base_url()}/chat/completions",
                json=payload,
                timeout=_llm_translate_timeout(),
            )
            if response.status_code != 200:
                logger.warning(
                    "llm-translate http %s: %s→%s",
                    response.status_code,
                    from_lang,
                    to_lang,
                )
                return None
            data = response.json()
            choices = data.get("choices") or []
            content = ""
            if choices:
                content = (choices[0].get("message") or {}).get("content") or ""
            out = _strip_llm_translation(content)
            if not out:
                return None
            if _has_residual_source_script(out, to_lang):
                logger.info(
                    "llm-translate residual-source-script, fallback %s→%s: %r",
                    from_lang,
                    to_lang,
                    out[:60],
                )
                return None
            logger.info("llm-translate ok %s→%s len=%d", from_lang, to_lang, len(out))
            return out
        except Exception as exc:
            logger.warning("llm-translate error %s→%s: %s", from_lang, to_lang, exc)
            return None

    def identify_language(self, text: str, candidates: List[str]) -> Optional[str]:
        """후보 언어 코드 중 text가 어느 언어인지 LLM으로 식별.

        V.2 대면(bilingual) 통역 라우팅 보강용. Whisper 언어감지·문자셋 매칭이
        애매할 때만 호출되어, 짧은 발화에서의 오감지로 인한 하드 거부를 줄인다.
        비활성/실패/불확실 시 None을 반환해 기존 거부 로직으로 폴백한다.
        (번역 엔진과 동일한 vLLM 설정을 재사용 — 정합성 유지.)
        """
        text = (text or "").strip()
        cands = [c for c in dict.fromkeys(candidates or []) if c]
        if not text or len(cands) < 2:
            return cands[0] if cands else None
        if not _llm_translate_enabled():
            return None
        try:
            import httpx

            labeled = ", ".join(f"{c} ({_llm_lang_label(c)})" for c in cands)
            system = (
                "You are a strict language identifier. Decide which language the "
                f"user's text is written in, choosing ONLY from these options: {labeled}. "
                f"Respond with ONLY the language code (e.g. '{cands[0]}'), nothing else."
            )
            payload = {
                "model": _resolve_llm_translate_model(),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.0,
                "max_tokens": 8,
                "stream": False,
            }
            response = httpx.post(
                f"{_llm_translate_base_url()}/chat/completions",
                json=payload,
                timeout=_llm_translate_timeout(),
            )
            if response.status_code != 200:
                return None
            data = response.json()
            choices = data.get("choices") or []
            content = ((choices[0].get("message") or {}).get("content") if choices else "") or ""
            guess = content.strip().lower().strip("'\"`. ")
            if not guess:
                return None
            tokens = guess.replace("-", " ").split()
            for c in cands:
                cl = c.lower()
                if guess == cl or cl in tokens or guess.startswith(cl):
                    return c
            for c in cands:  # 언어명으로 응답한 경우(예: "Korean")
                if _llm_lang_label(c).lower() in guess:
                    return c
            return None
        except Exception as exc:
            logger.warning("llm identify-language error: %s", exc)
            return None


# 모듈 레벨 편의 함수
def translate(
    text: str,
    from_lang: str = "ko",
    to_lang: str = "en",
    region_hint: str | None = None,
) -> str:
    return NadoTranslator.get_instance().translate(
        text,
        from_lang=from_lang,
        to_lang=to_lang,
        region_hint=region_hint,
    )
