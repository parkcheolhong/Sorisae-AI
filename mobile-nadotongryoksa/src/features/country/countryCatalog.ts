/**
 * [기능 분리 Phase5.6e-2] 가입/프로필 국가 카탈로그 SSOT.
 *
 * App.tsx 인라인의 가입국가 목록·타입·이름맵 + 정규화/역매핑 헬퍼를 분리한다.
 * 순수(부수효과 없음) — 단위 테스트로 회귀 가드. 언어 매핑은 countryLanguage(B)에 위임.
 */
import type { LangCode } from '../language/languageCatalog';
import { resolveLangFromCountry } from './countryLanguage';

/** 가입/프로필에서 선택 가능한 서비스 국가 목록(라벨 표기 포함). */
export const SIGNUP_COUNTRY_OPTIONS = [
    { code: 'KR', label: '대한민국' },
    { code: 'US', label: '미국' },
    { code: 'JP', label: '일본' },
    { code: 'CN', label: '중국' },
    { code: 'TW', label: '대만' },
    { code: 'HK', label: '홍콩' },
    { code: 'VN', label: '베트남' },
    { code: 'TH', label: '태국' },
    { code: 'PH', label: '필리핀' },
    { code: 'ID', label: '인도네시아' },
    { code: 'MY', label: '말레이시아' },
    { code: 'SG', label: '싱가포르' },
    { code: 'FR', label: '프랑스' },
    { code: 'DE', label: '독일' },
    { code: 'GB', label: '영국' },
    { code: 'CA', label: '캐나다' },
    { code: 'AU', label: '호주' },
    { code: 'NZ', label: '뉴질랜드' },
    { code: 'IE', label: '아일랜드' },
    { code: 'IT', label: '이탈리아' },
    { code: 'ES', label: '스페인' },
    { code: 'MX', label: '멕시코' },
    { code: 'AR', label: '아르헨티나' },
    { code: 'CL', label: '칠레' },
    { code: 'CO', label: '콜롬비아' },
    { code: 'PE', label: '페루' },
    { code: 'PT', label: '포르투갈' },
    { code: 'BR', label: '브라질' },
    { code: 'RU', label: '러시아' },
    { code: 'SA', label: '사우디아라비아' },
    { code: 'AE', label: '아랍에미리트' },
    { code: 'EG', label: '이집트' },
    { code: 'QA', label: '카타르' },
    { code: 'KW', label: '쿠웨이트' },
    { code: 'IN', label: '인도' },
    { code: 'PK', label: '파키스탄' },
    { code: 'BD', label: '방글라데시' },
    { code: 'TR', label: '튀르키예' },
    { code: 'NL', label: '네덜란드' },
    { code: 'PL', label: '폴란드' },
    { code: 'UA', label: '우크라이나' },
    { code: 'SE', label: '스웨덴' },
    { code: 'NO', label: '노르웨이' },
    { code: 'DK', label: '덴마크' },
    { code: 'FI', label: '핀란드' },
    { code: 'CZ', label: '체코' },
    { code: 'RO', label: '루마니아' },
    { code: 'HU', label: '헝가리' },
    { code: 'GR', label: '그리스' },
    { code: 'IL', label: '이스라엘' },
] as const;

export type SignupCountryCode = (typeof SIGNUP_COUNTRY_OPTIONS)[number]['code'];

export const SIGNUP_COUNTRY_OPTION_CODES: SignupCountryCode[] = SIGNUP_COUNTRY_OPTIONS.map((item) => item.code);

/** 국가코드 → 한글 국가명(가입 목록 + 추가 국가). 미등록이면 호출부에서 코드 대문자로 폴백. */
export const COUNTRY_NAME_MAP: Record<string, string> = {
    ...(Object.fromEntries(SIGNUP_COUNTRY_OPTIONS.map((item) => [item.code, item.label])) as Record<string, string>),
    BE: '벨기에',
    CH: '스위스',
    AT: '오스트리아',
    MO: '마카오',
    CY: '키프로스',
    BA: '보스니아 헤르체고비나',
    ME: '몬테네그로',
    SK: '슬로바키아',
    SI: '슬로베니아',
    LT: '리투아니아',
    LV: '라트비아',
    EE: '에스토니아',
    IR: '이란',
    AF: '아프가니스탄',
    LK: '스리랑카',
    ET: '에티오피아',
    KE: '케냐',
    TZ: '탄자니아',
    UG: '우간다',
    MD: '몰도바',
    RS: '세르비아',
};

/** 값이 지원 가입국가 코드인지 타입가드. */
export function isSupportedSignupCountryCode(value: string): value is SignupCountryCode {
    return SIGNUP_COUNTRY_OPTIONS.some((item) => item.code === value);
}

/** 임의 입력을 지원 가입국가 코드로 정규화(미지원이면 KR). */
export function normalizeSignupCountryCode(value: string | null | undefined): SignupCountryCode {
    const normalized = String(value || '').trim().toUpperCase();
    return isSupportedSignupCountryCode(normalized) ? normalized : 'KR';
}

/** 언어코드에 대응하는 가입국가 코드 역매핑(미매칭이면 KR). */
export function resolveSignupCountryFromLang(languageCode: LangCode): SignupCountryCode {
    const matchedCountry = SIGNUP_COUNTRY_OPTIONS.find((item) => resolveLangFromCountry(item.code) === languageCode);
    return matchedCountry?.code ?? 'KR';
}

/** 국가코드 → 한글 국가명(미등록이면 코드 대문자). */
export function resolveCountryName(countryCode: string): string {
    return COUNTRY_NAME_MAP[countryCode.toUpperCase()] ?? countryCode.toUpperCase();
}
