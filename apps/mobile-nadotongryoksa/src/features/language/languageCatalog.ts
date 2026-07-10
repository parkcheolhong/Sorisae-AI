// [기능 분리 Phase5.5 선행] 공용 언어 카탈로그 SSOT — 여러 기능(대면/소리새/노래/VOIP/일반전화)이
// 공유하는 언어 코드·라벨·감지/정규화·자동 타깃 결정 헬퍼. 부작용/React 상태 비의존(순수).
// App.tsx 모놀리스에서 추출. song 언어 헬퍼는 이 모듈을 의존(순환 import 회피).

import { resolveLangFromCountry } from '../country/countryLanguage';

export const LANGS = [
    { label: '한국어', code: 'ko', tts: 'ko-KR' },
    { label: 'English', code: 'en', tts: 'en-US' },
    { label: '中文(简体)', code: 'zh', tts: 'zh-CN' },
    { label: '繁體中文(台灣)', code: 'zh-tw', tts: 'zh-TW' },
    { label: '粵語(香港)', code: 'zh-hk', tts: 'zh-HK' },
    { label: '日本語', code: 'ja', tts: 'ja-JP' },
    { label: 'Español', code: 'es', tts: 'es-ES' },
    { label: 'Français', code: 'fr', tts: 'fr-FR' },
    { label: 'Deutsch', code: 'de', tts: 'de-DE' },
    { label: 'Português', code: 'pt', tts: 'pt-BR' },
    { label: 'Русский', code: 'ru', tts: 'ru-RU' },
    { label: 'العربية', code: 'ar', tts: 'ar-SA' },
    { label: 'हिन्दी', code: 'hi', tts: 'hi-IN' },
    { label: 'Italiano', code: 'it', tts: 'it-IT' },
    { label: 'Türkçe', code: 'tr', tts: 'tr-TR' },
    { label: 'Tiếng Việt', code: 'vi', tts: 'vi-VN' },
    { label: 'ภาษาไทย', code: 'th', tts: 'th-TH' },
    { label: 'Bahasa Indonesia', code: 'id', tts: 'id-ID' },
    { label: 'Bahasa Melayu', code: 'ms', tts: 'ms-MY' },
    { label: 'Nederlands', code: 'nl', tts: 'nl-NL' },
    { label: 'Polski', code: 'pl', tts: 'pl-PL' },
    { label: 'Українська', code: 'uk', tts: 'uk-UA' },
    { label: 'Svenska', code: 'sv', tts: 'sv-SE' },
    { label: 'Norsk', code: 'no', tts: 'nb-NO' },
    { label: 'Dansk', code: 'da', tts: 'da-DK' },
    { label: 'Suomi', code: 'fi', tts: 'fi-FI' },
    { label: 'Čeština', code: 'cs', tts: 'cs-CZ' },
    { label: 'Română', code: 'ro', tts: 'ro-RO' },
    { label: 'Magyar', code: 'hu', tts: 'hu-HU' },
    { label: 'Ελληνικά', code: 'el', tts: 'el-GR' },
    { label: 'עברית', code: 'he', tts: 'he-IL' },
    { label: 'Български', code: 'bg', tts: 'bg-BG' },
    { label: 'Hrvatski', code: 'hr', tts: 'hr-HR' },
    { label: 'Srpski', code: 'sr', tts: 'sr-RS' },
    { label: 'Slovenčina', code: 'sk', tts: 'sk-SK' },
    { label: 'Slovenščina', code: 'sl', tts: 'sl-SI' },
    { label: 'Lietuvių', code: 'lt', tts: 'lt-LT' },
    { label: 'Latviešu', code: 'lv', tts: 'lv-LV' },
    { label: 'Eesti', code: 'et', tts: 'et-EE' },
    { label: 'فارسی', code: 'fa', tts: 'fa-IR' },
    { label: 'اردو', code: 'ur', tts: 'ur-PK' },
    { label: 'বাংলা', code: 'bn', tts: 'bn-BD' },
    { label: 'தமிழ்', code: 'ta', tts: 'ta-IN' },
    { label: 'తెలుగు', code: 'te', tts: 'te-IN' },
    { label: 'മലയാളം', code: 'ml', tts: 'ml-IN' },
    { label: 'ગુજરાતી', code: 'gu', tts: 'gu-IN' },
    { label: 'मराठी', code: 'mr', tts: 'mr-IN' },
    { label: 'Filipino', code: 'fil', tts: 'fil-PH' },
    { label: 'Kiswahili', code: 'sw', tts: 'sw-KE' },
    { label: 'Català', code: 'ca', tts: 'ca-ES' },
    { label: 'አማርኛ', code: 'am', tts: 'am-ET' },
] as const;

export type LangCode = (typeof LANGS)[number]['code'];
export const SUPPORTED_LANGUAGE_COUNT = LANGS.length;

export function getLangLabelText(code: LangCode): string {
    return LANGS.find((item) => item.code === code)?.label ?? code;
}

export function isSupportedLangCode(value: string): value is LangCode {
    return LANGS.some((item) => item.code === value);
}

export const WHISPER_LANG_MAP: Record<string, LangCode> = {
    chinese: 'zh', mandarin: 'zh', china: 'zh', chinese_language: 'zh', 중국: 'zh', 중국어: 'zh', 중문: 'zh', zh: 'zh',
    cantonese: 'zh-hk', yue: 'zh-hk', hongkong: 'zh-hk', 'zh-hk': 'zh-hk', 'zh-hant-hk': 'zh-hk',
    guangdong: 'zh-hk', 광둥: 'zh-hk', 粵語: 'zh-hk', 廣東話: 'zh-hk', 홍콩: 'zh-hk',
    taiwan: 'zh-tw', 'zh-tw': 'zh-tw', 'zh-hant': 'zh-tw', 繁體: 'zh-tw', 대만: 'zh-tw',
    japanese: 'ja', japan: 'ja', 일본: 'ja', 일본어: 'ja', 일어: 'ja', ja: 'ja',
    korean: 'ko', korea: 'ko', southkorea: 'ko', 한국: 'ko', 한국어: 'ko', 한글: 'ko', ko: 'ko',
    english: 'en', american: 'en', america: 'en', usa: 'en', us: 'en', england: 'en', britain: 'en', 미국: 'en', 영국: 'en', 영어: 'en', 영문: 'en', en: 'en',
    spanish: 'es', spain: 'es', 스페인: 'es', 스페인어: 'es', es: 'es',
    french: 'fr', france: 'fr', 프랑스: 'fr', 프랑스어: 'fr', fr: 'fr',
    german: 'de', germany: 'de', 독일: 'de', 독일어: 'de', de: 'de',
    portuguese: 'pt', portugal: 'pt', brazil: 'pt', 포르투갈: 'pt', 브라질: 'pt', 포르투갈어: 'pt', pt: 'pt',
    russian: 'ru', russia: 'ru', 러시아: 'ru', 러시아어: 'ru', ru: 'ru',
    arabic: 'ar', saudi: 'ar', 사우디: 'ar', 아랍: 'ar', 아랍어: 'ar', ar: 'ar',
    hindi: 'hi', india: 'hi', 인도: 'hi', 힌디어: 'hi', hi: 'hi',
    italian: 'it', italy: 'it', 이탈리아: 'it', 이탈리아어: 'it', it: 'it',
    turkish: 'tr', turkey: 'tr', 터키: 'tr', 터키어: 'tr', tr: 'tr',
    thai: 'th', thailand: 'th', 태국: 'th', 태국어: 'th', th: 'th',
    vietnamese: 'vi', vietnam: 'vi', 베트남: 'vi', 베트남어: 'vi', vi: 'vi',
    indonesian: 'id', indonesia: 'id', 인도네시아: 'id', 인도네시아어: 'id', id: 'id',
    malay: 'ms', malaysia: 'ms', 말레이시아: 'ms', 말레이어: 'ms', ms: 'ms',
    dutch: 'nl', netherlands: 'nl', 네덜란드: 'nl', 네덜란드어: 'nl', nl: 'nl',
    polish: 'pl', poland: 'pl', 폴란드: 'pl', 폴란드어: 'pl', pl: 'pl',
    ukrainian: 'uk', ukraine: 'uk', 우크라이나: 'uk', 우크라이나어: 'uk', uk: 'uk',
    swedish: 'sv', sweden: 'sv', 스웨덴: 'sv', 스웨덴어: 'sv', sv: 'sv',
    norwegian: 'no', norway: 'no', 노르웨이: 'no', 노르웨이어: 'no', no: 'no',
    danish: 'da', denmark: 'da', 덴마크: 'da', 덴마크어: 'da', da: 'da',
    finnish: 'fi', finland: 'fi', 핀란드: 'fi', 핀란드어: 'fi', fi: 'fi',
    czech: 'cs', czechia: 'cs', cesky: 'cs', 체코: 'cs', 체코어: 'cs', cs: 'cs',
    romanian: 'ro', romania: 'ro', 루마니아: 'ro', 루마니아어: 'ro', ro: 'ro',
    hungarian: 'hu', hungary: 'hu', 헝가리: 'hu', 헝가리어: 'hu', hu: 'hu',
    greek: 'el', greece: 'el', 그리스: 'el', 그리스어: 'el', el: 'el',
    hebrew: 'he', israel: 'he', 이스라엘: 'he', 히브리어: 'he', he: 'he',
    bulgarian: 'bg', bulgaria: 'bg', 불가리아: 'bg', 불가리아어: 'bg', bg: 'bg',
    croatian: 'hr', croatia: 'hr', 크로아티아: 'hr', 크로아티아어: 'hr', hr: 'hr',
    serbian: 'sr', serbia: 'sr', 세르비아: 'sr', 세르비아어: 'sr', sr: 'sr',
    slovak: 'sk', slovakia: 'sk', 슬로바키아: 'sk', 슬로바키아어: 'sk', sk: 'sk',
    slovenian: 'sl', slovenia: 'sl', 슬로베니아: 'sl', 슬로베니아어: 'sl', sl: 'sl',
    lithuanian: 'lt', lithuania: 'lt', 리투아니아: 'lt', 리투아니아어: 'lt', lt: 'lt',
    latvian: 'lv', latvia: 'lv', 라트비아: 'lv', 라트비아어: 'lv', lv: 'lv',
    estonian: 'et', estonia: 'et', 에스토니아: 'et', 에스토니아어: 'et', et: 'et',
    persian: 'fa', farsi: 'fa', iran: 'fa', 페르시아어: 'fa', 이란: 'fa', fa: 'fa',
    urdu: 'ur', pakistan: 'ur', 파키스탄: 'ur', 우르두어: 'ur', ur: 'ur',
    bengali: 'bn', bangla: 'bn', bangladesh: 'bn', 벵골어: 'bn', 방글라데시: 'bn', bn: 'bn',
    tamil: 'ta', tamilnadu: 'ta', 타밀어: 'ta', ta: 'ta',
    telugu: 'te', 텔루구어: 'te', te: 'te',
    malayalam: 'ml', 말라얄람어: 'ml', ml: 'ml',
    gujarati: 'gu', 구자라트어: 'gu', gu: 'gu',
    marathi: 'mr', 마라티어: 'mr', mr: 'mr',
    filipino: 'fil', tagalog: 'fil', 필리핀어: 'fil', 타갈로그어: 'fil', fil: 'fil',
    swahili: 'sw', kiswahili: 'sw', 케냐: 'sw', 스와힐리어: 'sw', sw: 'sw',
    catalan: 'ca', catalonia: 'ca', 카탈루냐어: 'ca', ca: 'ca',
    amharic: 'am', ethiopia: 'am', 에티오피아: 'am', 암하라어: 'am', am: 'am',
};

/** 임의의 감지 언어 문자열(이름/별칭/로캘)을 지원 `LangCode` 로 정규화. 미인식 시 null. */
export function normalizeDetectedLangCode(value: unknown): LangCode | null {
    const raw = String(value ?? '').trim().toLowerCase().replace('_', '-');
    if (!raw) return null;
    const compact = raw.split(/[\s,;/]+/)[0];
    const base = compact.split('-')[0];
    const normalizedCompact = compact.replace(/[^\p{L}-]/gu, '');
    const strippedCompact = normalizedCompact.replace(/(language|lang|나라|국가|언어|국어|말|어|으로|로)$/u, '');
    const strippedBase = base.replace(/(language|lang|나라|국가|언어|국어|말|어|으로|로)$/u, '');
    return WHISPER_LANG_MAP[compact]
        ?? WHISPER_LANG_MAP[base]
        ?? WHISPER_LANG_MAP[normalizedCompact]
        ?? WHISPER_LANG_MAP[strippedCompact]
        ?? WHISPER_LANG_MAP[strippedBase]
        ?? null;
}

/** 문자 스크립트로 발화 언어를 추정(STT 라벨 없을 때의 fallback 분기). */
export function inferSpeechLangCode(text: string, fallback: LangCode = 'en'): LangCode {
    const value = text.trim();
    if (!value) return fallback;

    if (/[\uac00-\ud7a3]/.test(value)) return 'ko';
    if (/[\u3040-\u30ff]/.test(value)) return 'ja';
    if (/[\u4e00-\u9fff]/.test(value)) return 'zh';
    if (/[\u0600-\u06ff]/.test(value)) return 'ar';
    if (/[\u0900-\u097f]/.test(value)) return 'hi';
    if (/[\u0400-\u04ff]/.test(value)) return 'ru';
    if (/[\u0e00-\u0e7f]/.test(value)) return 'th';

    const lower = value.toLowerCase();
    if (/[¿¡ñ]/.test(lower)) return 'es';
    if (/[äöüß]/.test(lower)) return 'de';
    if (/[ğşıİıç]/.test(value)) return 'tr';
    if (/[àâçéèêëîïôûùüÿœæ]/.test(lower)) return 'fr';
    if (/[ãõ]/.test(lower)) return 'pt';
    if (/[a-z]/.test(lower)) return 'en';

    return fallback;
}

/** 자동 타깃 언어 결정 — 타깃이 소스와 같을 때만 보정(ko↔en, 그 외 ko). */
export function resolveAutoTargetLang(source: LangCode, currentTarget: LangCode): LangCode {
    if (currentTarget !== source) return currentTarget;
    if (source === 'ko') return 'en';
    if (source === 'en') return 'ko';
    return 'ko';
}

/**
 * 출력 언어 SSOT.
 * preferred_language 는 항상 "출력 언어"로만 해석하고,
 * 입력 세션 언어(fromLang)와는 독립적으로 유지한다.
 */
export function resolvePreferredOutputLang(
    preferredLanguage: string | null | undefined,
    fallbackOutput: LangCode,
): LangCode {
    const normalizedPreferred = String(preferredLanguage || '').trim().toLowerCase();
    if (isSupportedLangCode(normalizedPreferred)) {
        return normalizedPreferred;
    }
    return fallbackOutput;
}

/**
 * VoIP 상대 타깃 언어 결정.
 * 상대 지정언어가 내 언어와 같게 잘못 들어오면, 상대 국가코드의 대표 언어로 한 번 더 복구한다.
 */
export function resolveVoipPeerTargetLang(
    localSource: LangCode,
    currentTarget: LangCode,
    remotePreferredLanguage?: string | null,
    remoteCountryCode?: string | null,
): LangCode {
    const normalizedRemotePreferred = String(remotePreferredLanguage || '').trim().toLowerCase();
    if (isSupportedLangCode(normalizedRemotePreferred) && normalizedRemotePreferred !== localSource) {
        return normalizedRemotePreferred;
    }

    const countryFallback = resolveLangFromCountry(String(remoteCountryCode || '').trim().toUpperCase());
    if (countryFallback && countryFallback !== localSource) {
        return countryFallback;
    }

    return resolveAutoTargetLang(localSource, currentTarget);
}
