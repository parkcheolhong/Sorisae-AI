import { describe, expect, it } from '@jest/globals';

import {
    resolveGpsDialectRegionHint,
    resolveGpsCoordinateFallback,
    resolveRegionHintForSourceLanguage,
} from '../features/country/regionHints';

describe('resolveGpsDialectRegionHint — 방언 리전 힌트', () => {
    it('지오코딩 텍스트의 키워드로 리전을 매칭한다(영문/한글/현지어)', () => {
        expect(resolveGpsDialectRegionHint('KR', { city: 'Busan' })).toBe('busan');
        expect(resolveGpsDialectRegionHint('KR', { region: '제주특별자치도' })).toBe('jeju');
        expect(resolveGpsDialectRegionHint('JP', { city: 'Osaka' })).toBe('kansai');
        expect(resolveGpsDialectRegionHint('CN', { city: '上海' })).toBe('shanghai');
    });

    it('국가 미등록/지오코딩 없음/미매칭은 null', () => {
        expect(resolveGpsDialectRegionHint('US', { city: 'New York' })).toBeNull();
        expect(resolveGpsDialectRegionHint('KR', null)).toBeNull();
        expect(resolveGpsDialectRegionHint('KR', { city: 'Nowhere' })).toBeNull();
    });
});

describe('resolveGpsCoordinateFallback — 좌표 근방 폴백', () => {
    it('±0.35° 이내면 대표 지역을 반환한다', () => {
        expect(resolveGpsCoordinateFallback(33.5, 126.53)).toEqual({ countryCode: 'KR', regionHint: 'jeju' });
        expect(resolveGpsCoordinateFallback(34.69, 135.5)).toEqual({ countryCode: 'JP', regionHint: 'kansai' });
    });

    it('범위 밖이면 null', () => {
        expect(resolveGpsCoordinateFallback(37.5665, 126.978)).toBeNull(); // 서울 — 폴백 좌표 아님
        expect(resolveGpsCoordinateFallback(0, 0)).toBeNull();
    });
});

describe('resolveRegionHintForSourceLanguage — 소스언어 일치 시에만 힌트 적용', () => {
    it('국가 대표언어 == 소스언어면 힌트 유지', () => {
        expect(resolveRegionHintForSourceLanguage('ko', 'KR', 'busan')).toBe('busan');
        expect(resolveRegionHintForSourceLanguage('ja', 'JP', 'kansai')).toBe('kansai');
    });

    it('언어 불일치/빈 입력이면 undefined', () => {
        expect(resolveRegionHintForSourceLanguage('en', 'KR', 'busan')).toBeUndefined();
        expect(resolveRegionHintForSourceLanguage('ko', '', 'busan')).toBeUndefined();
        expect(resolveRegionHintForSourceLanguage('ko', 'KR', '')).toBeUndefined();
    });
});
