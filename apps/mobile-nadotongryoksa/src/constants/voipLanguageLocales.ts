import { detectDominantScriptLang } from '../utils/scriptLangResolver';

/** WorldLinco VoIP TTS locales — synced with backend/voip_language_locales.py (50 codes). */
export const VOIP_TTS_LOCALE_MAP: Record<string, string> = {
  ko: 'ko-KR',
  en: 'en-US',
  zh: 'zh-CN',
  'zh-tw': 'zh-TW',
  ja: 'ja-JP',
  es: 'es-ES',
  fr: 'fr-FR',
  de: 'de-DE',
  pt: 'pt-BR',
  ru: 'ru-RU',
  ar: 'ar-SA',
  hi: 'hi-IN',
  it: 'it-IT',
  tr: 'tr-TR',
  vi: 'vi-VN',
  th: 'th-TH',
  id: 'id-ID',
  ms: 'ms-MY',
  nl: 'nl-NL',
  pl: 'pl-PL',
  uk: 'uk-UA',
  sv: 'sv-SE',
  no: 'nb-NO',
  da: 'da-DK',
  fi: 'fi-FI',
  cs: 'cs-CZ',
  ro: 'ro-RO',
  hu: 'hu-HU',
  el: 'el-GR',
  he: 'he-IL',
  bg: 'bg-BG',
  hr: 'hr-HR',
  sr: 'sr-RS',
  sk: 'sk-SK',
  sl: 'sl-SI',
  lt: 'lt-LT',
  lv: 'lv-LV',
  et: 'et-EE',
  fa: 'fa-IR',
  ur: 'ur-PK',
  bn: 'bn-BD',
  ta: 'ta-IN',
  te: 'te-IN',
  ml: 'ml-IN',
  gu: 'gu-IN',
  mr: 'mr-IN',
  fil: 'fil-PH',
  sw: 'sw-KE',
  ca: 'ca-ES',
  am: 'am-ET',
};

export function resolveVoipTtsLocale(languageCode?: string | null, text?: string | null): string {
  const normalized = String(languageCode || '').trim().toLowerCase();
  // (G5) 스크립트 누수 교정 — 발화 텍스트의 우세 스크립트가 지정 언어와 다르면 실제
  // 스크립트 로케일로 교정한다(단일 SSOT detectDominantScriptLang). text 미지정 시 기존 동작 유지.
  if (text) {
    const scriptLang = detectDominantScriptLang(text);
    const baseLang = normalized.split('-')[0] || normalized;
    if (scriptLang && scriptLang !== baseLang && VOIP_TTS_LOCALE_MAP[scriptLang]) {
      return VOIP_TTS_LOCALE_MAP[scriptLang];
    }
  }
  if (!normalized) {
    return VOIP_TTS_LOCALE_MAP.ko;
  }
  if (VOIP_TTS_LOCALE_MAP[normalized]) {
    return VOIP_TTS_LOCALE_MAP[normalized];
  }
  const base = normalized.split('-')[0];
  return VOIP_TTS_LOCALE_MAP[base] || VOIP_TTS_LOCALE_MAP.en;
}
