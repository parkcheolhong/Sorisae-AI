/**
 * [기능 분리 Phase5.6e-1] 국가↔언어 매핑 SSOT (country 클러스터 토대).
 *
 * App.tsx 인라인의 `COUNTRY_LANG_MAP` + `resolveLangFromCountry` 를 분리한다.
 * 가입국가 카탈로그(A) / GPS·방언 리전힌트(C) 가 이 매핑에 의존하므로 가장 먼저 추출한다.
 * 순수(부수효과 없음) — 단위 테스트로 회귀 가드.
 */
import type { LangCode } from '../language/languageCatalog';

const COUNTRY_LANG_MAP: Partial<Record<string, LangCode>> = {
    KR: 'ko',
    US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', SG: 'en', PH: 'en',
    CN: 'zh',
    TW: 'zh-tw', HK: 'zh-tw', MO: 'zh-tw',
    JP: 'ja',
    ES: 'es', MX: 'es', AR: 'es', CL: 'es', CO: 'es', PE: 'es',
    FR: 'fr', BE: 'fr', CH: 'fr',
    DE: 'de', AT: 'de',
    PT: 'pt', BR: 'pt',
    RU: 'ru',
    SA: 'ar', AE: 'ar', EG: 'ar', QA: 'ar', KW: 'ar',
    IN: 'hi',
    IT: 'it',
    TR: 'tr',
    VN: 'vi',
    TH: 'th',
    ID: 'id',
    MY: 'ms',
    NL: 'nl',
    PL: 'pl',
    UA: 'uk',
    SE: 'sv',
    NO: 'no',
    DK: 'da',
    FI: 'fi',
    CZ: 'cs',
    RO: 'ro', MD: 'ro',
    HU: 'hu',
    GR: 'el', CY: 'el',
    IL: 'he',
    BG: 'bg',
    HR: 'hr',
    RS: 'sr', BA: 'sr', ME: 'sr',
    SK: 'sk',
    SI: 'sl',
    LT: 'lt',
    LV: 'lv',
    EE: 'et',
    IR: 'fa', AF: 'fa',
    PK: 'ur',
    BD: 'bn',
    LK: 'ta',
    ET: 'am',
    KE: 'sw', TZ: 'sw', UG: 'sw',
};

/** 국가코드 → 대표 언어코드(미등록이면 null). 대소문자 무관. */
export function resolveLangFromCountry(countryCode: string): LangCode | null {
    return COUNTRY_LANG_MAP[countryCode.toUpperCase()] ?? null;
}
