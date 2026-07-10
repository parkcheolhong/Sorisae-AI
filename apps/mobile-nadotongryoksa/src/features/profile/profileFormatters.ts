/**
 * [기능 분리 Phase5.6c] 프로필 표시용 순수 포매터 SSOT.
 *
 * App.tsx 인라인에 있던 국기/로케일/언어 라벨 + 성별 라벨 헬퍼를 분리한다.
 * 모두 순수(부수효과 없음)하여 단위 테스트로 회귀 가드한다.
 *  - 국기 이모지: `resolveCountryFlag`
 *  - 단말 로케일 국가코드: `resolveLocaleCountryCode`
 *  - 언어 라벨: `resolveLanguageLabel` (언어 SSOT `LANGS` 의존)
 *  - 성별 라벨/매핑: `formatVoipGenderLabel` / `formatDiscoveryGenderLabel` / `resolveDiscoveryGenderFromProfile`
 *
 * ※ `resolveCountryName`/`COUNTRY_NAME_MAP` 은 `SIGNUP_COUNTRY_OPTIONS` 클러스터와
 *   강결합돼 있어 별도 country 모듈 단계에서 분리한다(빅뱅 방지).
 */
import { LANGS } from '../language/languageCatalog';
import type { DiscoveryGender } from '../friends/types';

export type VoipGenderOption = 'male' | 'female' | 'unknown';

/** ISO 3166-1 alpha-2 국가코드를 국기 이모지로 변환(2자리 영문 아니면 🌐). */
export function resolveCountryFlag(countryCode: string): string {
    const code = countryCode.toUpperCase();
    if (!/^[A-Z]{2}$/.test(code)) {
        return '🌐';
    }
    return String.fromCodePoint(...Array.from(code).map((char) => 127397 + char.charCodeAt(0)));
}

/** 단말 로케일에서 국가(region) 코드를 추출(미상이면 KR). */
export function resolveLocaleCountryCode(): string {
    const locale = Intl.DateTimeFormat().resolvedOptions().locale || 'ko-KR';
    const localeSegments = locale.split(/[-_]/);
    const rawRegion = localeSegments[localeSegments.length - 1] || 'KR';
    return rawRegion.toUpperCase();
}

/** 언어 코드를 "라벨 (CODE)" 형태로 표기(미설정/미지원 처리 포함). */
export function resolveLanguageLabel(languageCode?: string | null): string {
    const normalized = String(languageCode || '').trim().toLowerCase();
    if (!normalized) {
        return '미설정';
    }
    const match = LANGS.find((item) => item.code === normalized);
    return match ? `${match.label} (${match.code.toUpperCase()})` : normalized.toUpperCase();
}

/** VoIP 프로필 성별 라벨(male/female 외는 미설정). */
export function formatVoipGenderLabel(gender: VoipGenderOption): string {
    switch (gender) {
        case 'male':
            return '남성';
        case 'female':
            return '여성';
        default:
            return '미설정';
    }
}

/** 친구 탐색 성별 라벨(other 포함). */
export function formatDiscoveryGenderLabel(gender?: DiscoveryGender | VoipGenderOption): string {
    switch (gender) {
        case 'male':
            return '남성';
        case 'female':
            return '여성';
        case 'other':
            return '기타';
        default:
            return '미설정';
    }
}

/** VoIP 프로필 성별 → 친구 탐색 성별 매핑(미상은 unknown). */
export function resolveDiscoveryGenderFromProfile(gender: VoipGenderOption): DiscoveryGender {
    if (gender === 'male' || gender === 'female') {
        return gender;
    }
    return 'unknown';
}
