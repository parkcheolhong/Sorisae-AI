/**
 * [기능 분리 Phase5.6e-1] 국가↔언어 매핑 SSOT (country 클러스터 토대).
 *
 * App.tsx 인라인의 `COUNTRY_LANG_MAP` + `resolveLangFromCountry` 를 분리한다.
 * 가입국가 카탈로그(A) / GPS·방언 리전힌트(C) 가 이 매핑에 의존하므로 가장 먼저 추출한다.
 * 순수(부수효과 없음) — 단위 테스트로 회귀 가드.
 *
 * 정책:
 *  - 중국어는 지역별 코드 분리: CN=간체(zh), TW=번체(zh-tw), HK/MO=粵語(zh-hk)
 *  - 다언어·관광·비즈니스 공용어 국가는 English(en) 기본
 *  - 미등록 ISO 국가는 resolveLangFromCountryOrEnglish() 로 en 폴백
 */
import type { LangCode } from '../language/languageCatalog';

/** English as international lingua franca — multilingual / business-default countries. */
const ENGLISH_COMMON_COUNTRY_CODES = new Set([
    'US', 'GB', 'AU', 'CA', 'NZ', 'IE', 'SG',
    'LK', 'KE', 'TZ', 'UG', 'NG', 'ZA', 'GH', 'JM', 'MT', 'CY',
    'BE', 'CH', 'LU', 'NL',
]);

const COUNTRY_LANG_MAP: Partial<Record<string, LangCode>> = {
    KR: 'ko',
    US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', SG: 'en', PH: 'fil',
    IN: 'hi', MY: 'ms', LK: 'en', KE: 'en', TZ: 'en', UG: 'en',
    NG: 'en', ZA: 'en', GH: 'en', JM: 'en', MT: 'en', CY: 'en',
    BE: 'en', CH: 'en', LU: 'en',
    CN: 'zh',
    TW: 'zh-tw',
    HK: 'zh-hk',
    MO: 'zh-hk',
    JP: 'ja',
    ES: 'es', MX: 'es', AR: 'es', CL: 'es', CO: 'es', PE: 'es',
    FR: 'fr',
    DE: 'de', AT: 'de',
    PT: 'pt', BR: 'pt',
    RU: 'ru',
    SA: 'ar', AE: 'ar', EG: 'ar', QA: 'ar', KW: 'ar',
    IT: 'it',
    TR: 'tr',
    VN: 'vi',
    TH: 'th',
    ID: 'id',
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
    GR: 'el',
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
    ET: 'am',
};

/** 국가코드 → 대표 언어코드(미등록이면 null). 대소문자 무관. */
export function resolveLangFromCountry(countryCode: string): LangCode | null {
    const normalized = countryCode.toUpperCase().trim();
    if (!normalized) {
        return null;
    }
    return COUNTRY_LANG_MAP[normalized] ?? null;
}

/** 미등록 국가·GPS 미매칭 시 English(en) 폴백. */
export function resolveLangFromCountryOrEnglish(countryCode: string): LangCode {
    return resolveLangFromCountry(countryCode) ?? 'en';
}

/** English 공용어 정책 대상 국가인지(문서·UI 힌트용). */
export function isEnglishCommonCountry(countryCode: string): boolean {
    return ENGLISH_COMMON_COUNTRY_CODES.has(countryCode.toUpperCase().trim());
}
