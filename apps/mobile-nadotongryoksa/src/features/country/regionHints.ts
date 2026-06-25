/**
 * [기능 분리 Phase5.6e-3] GPS/방언 리전 힌트 SSOT.
 *
 * App.tsx 인라인의 좌표 폴백 + 방언 키워드 맵 + 리전 힌트 해석 헬퍼를 분리한다.
 * 순수(부수효과 없음) — 단위 테스트로 회귀 가드. 언어 매핑은 countryLanguage(B)에 위임.
 */
import type { LocationGeocodedAddress } from 'expo-location';
import type { LangCode } from '../language/languageCatalog';
import { resolveLangFromCountry } from './countryLanguage';

/** 좌표 근방(±0.35°) 매칭용 대표 지역 폴백 좌표. */
const GPS_REGION_COORDINATE_FALLBACKS = [
    { countryCode: 'KR', regionHint: 'jeju', latitude: 33.4996, longitude: 126.5312 },
    { countryCode: 'CN', regionHint: 'guangdong', latitude: 23.1291, longitude: 113.2644 },
    { countryCode: 'JP', regionHint: 'kansai', latitude: 34.6937, longitude: 135.5023 },
    { countryCode: 'IN', regionHint: 'bihar', latitude: 25.5941, longitude: 85.1376 },
    { countryCode: 'IT', regionHint: 'naples', latitude: 40.8518, longitude: 14.2681 },
] as const;

/** 국가별 방언 리전 힌트 키워드(지오코딩 텍스트 매칭용). */
const DIALECT_REGION_HINT_KEYWORDS: Record<string, Array<{ hint: string; keywords: string[] }>> = {
    KR: [
        { hint: 'jeju', keywords: ['jeju', '제주'] },
        { hint: 'busan', keywords: ['busan', '부산'] },
        { hint: 'gyeongsang', keywords: ['daegu', '울산', 'gyeongsang', '경상', '포항', '창원'] },
        { hint: 'jeolla', keywords: ['gwangju', '전주', 'jeolla', '전라', '목포', '순천'] },
        { hint: 'seoul', keywords: ['seoul', '서울', 'incheon', '인천', 'gyeonggi', '경기', 'suwon', '수원'] },
    ],
    CN: [
        { hint: 'guangdong', keywords: ['guangzhou', 'shenzhen', 'dongguan', 'foshan', 'guangdong', '광동', '广东', '廣東'] },
        { hint: 'sichuan', keywords: ['chengdu', 'mianyang', 'sichuan', '사천', '四川'] },
        { hint: 'dongbei', keywords: ['liaoning', 'jilin', 'heilongjiang', 'dongbei', '东北', '瀋陽', 'shenyang', 'harbin'] },
        { hint: 'shanghai', keywords: ['shanghai', '상하이', '上海'] },
        { hint: 'beijing', keywords: ['beijing', '베이징', '北京', 'tianjin', '天津'] },
    ],
    JP: [
        { hint: 'kansai', keywords: ['osaka', 'kyoto', 'nara', 'kobe', 'wakayama', 'kansai', '간사이', '関西', '大阪', '京都'] },
        { hint: 'hakata', keywords: ['fukuoka', 'hakata', '후쿠오카', '博多', '福岡'] },
        { hint: 'tohoku', keywords: ['sendai', 'aomori', 'akita', 'iwate', 'yamagata', 'tohoku', '도호쿠', '東北', '仙台'] },
        { hint: 'okinawa', keywords: ['okinawa', '오키나와', '沖縄', 'naha', '나하'] },
        { hint: 'tokyo', keywords: ['tokyo', '도쿄', '東京', 'yokohama', '요코하마', 'kanagawa', '가나가와'] },
    ],
    IN: [
        { hint: 'delhi', keywords: ['delhi', 'new delhi', 'ncr', 'दिल्ली'] },
        { hint: 'mumbai', keywords: ['mumbai', 'bombay', 'maharashtra', 'मुंबई', 'pune', 'पुणे'] },
        { hint: 'bihar', keywords: ['bihar', 'patna', 'पटना', 'बिहार'] },
        { hint: 'punjab', keywords: ['punjab', 'amritsar', 'ludhiana', 'पंजाब'] },
        { hint: 'uttar-pradesh', keywords: ['uttar pradesh', 'uttar-pradesh', 'lucknow', 'kanpur', 'वाराणसी', 'varanasi'] },
    ],
    IT: [
        { hint: 'rome', keywords: ['rome', 'roma', 'lazio'] },
        { hint: 'milan', keywords: ['milan', 'milano', 'lombardy', 'lombardia'] },
        { hint: 'naples', keywords: ['naples', 'napoli', 'campania'] },
        { hint: 'sicily', keywords: ['sicily', 'sicilia', 'palermo', 'catania'] },
        { hint: 'venice', keywords: ['venice', 'venezia', 'veneto', 'padova'] },
    ],
};

/** 지오코딩 주소에서 국가별 방언 리전 힌트를 추출(미매칭이면 null). */
export function resolveGpsDialectRegionHint(
    countryCode: string,
    geocoded: Partial<LocationGeocodedAddress> | null,
): string | null {
    const regionProfiles = DIALECT_REGION_HINT_KEYWORDS[countryCode.toUpperCase()];
    if (!regionProfiles?.length || !geocoded) {
        return null;
    }

    const haystack = [
        geocoded.region,
        geocoded.city,
        geocoded.district,
        geocoded.subregion,
        geocoded.street,
        geocoded.name,
    ]
        .map((value) => String(value || '').trim().toLowerCase())
        .filter(Boolean)
        .join(' | ');

    if (!haystack) {
        return null;
    }

    const matchedRegion = regionProfiles.find(({ keywords }) => keywords.some((keyword) => haystack.includes(keyword.toLowerCase())));
    return matchedRegion?.hint ?? null;
}

/** 좌표 근방 대표 지역 폴백(미매칭이면 null). */
export function resolveGpsCoordinateFallback(latitude: number, longitude: number): { countryCode: string; regionHint: string } | null {
    const matched = GPS_REGION_COORDINATE_FALLBACKS.find((candidate) => {
        const latitudeDelta = Math.abs(candidate.latitude - latitude);
        const longitudeDelta = Math.abs(candidate.longitude - longitude);
        return latitudeDelta <= 0.35 && longitudeDelta <= 0.35;
    });

    return matched
        ? {
            countryCode: matched.countryCode,
            regionHint: matched.regionHint,
        }
        : null;
}

/** 소스 언어와 국가의 대표 언어가 일치할 때만 리전 힌트를 적용. */
export function resolveRegionHintForSourceLanguage(
    sourceLang: LangCode,
    countryCode: string,
    regionHint: string,
): string | undefined {
    if (!countryCode || !regionHint) {
        return undefined;
    }
    return resolveLangFromCountry(countryCode) === sourceLang ? regionHint : undefined;
}
