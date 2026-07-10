import { describe, expect, it } from '@jest/globals';

import {
    SECTION_RAIL_DEFS,
    SECTION_RAIL_ITEMS,
    buildSectionRailSelector,
    parseSectionRailKey,
    sectionNumericId,
    sectionByNumericId,
    sectionDefByKey,
    featureIdForSection,
} from '../features/navigation/sectionRegistry';

describe('자동 넘버링 — numericId', () => {
    it('정의 순서대로 1부터 고유 번호가 부여된다', () => {
        expect(SECTION_RAIL_DEFS.map((d) => d.numericId)).toEqual([1, 2, 3, 4, 5]);
    });

    it('numericId 는 전역 고유하다', () => {
        const ids = SECTION_RAIL_DEFS.map((d) => d.numericId);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it('key ↔ numericId 왕복 매핑이 일관된다', () => {
        for (const def of SECTION_RAIL_DEFS) {
            expect(sectionNumericId(def.key)).toBe(def.numericId);
            expect(sectionByNumericId(def.numericId)?.key).toBe(def.key);
        }
        expect(sectionByNumericId(999)).toBeNull();
    });
});

describe('자동 연결 — 모든 레일이 전 표면에 연결된다', () => {
    it('SECTION_RAIL_ITEMS 는 tabVisible 레일만 파생', () => {
        expect(SECTION_RAIL_ITEMS).toEqual(
            SECTION_RAIL_DEFS.filter((d) => d.tabVisible).map(({ key, label, icon }) => ({ key, label, icon })),
        );
        expect(SECTION_RAIL_ITEMS.map((d) => d.key)).not.toContain('song-mode');
    });

    it('모든 레일이 correlation featureId 에 연결된다', () => {
        for (const def of SECTION_RAIL_DEFS) {
            expect(featureIdForSection(def.key)).toBe(def.featureId);
            expect(typeof def.featureId).toBe('string');
            expect(def.featureId.length).toBeGreaterThan(0);
        }
    });

    it('셀렉터는 key 로부터 결정적으로 생성된다', () => {
        expect(buildSectionRailSelector('chat')).toBe('worldlinco-section-rail-chat-button');
        expect(buildSectionRailSelector('travel-booking')).toBe('worldlinco-section-rail-travel-booking-button');
    });

    it('sectionDefByKey 로 정의를 조회한다', () => {
        expect(sectionDefByKey('voip')?.label).toBe('통화');
        expect(sectionDefByKey('tourism-promo')?.icon).toBe('📣');
    });
});

describe('parseSectionRailKey — key + alias 자동 매핑', () => {
    it('정규 key 를 대소문자/공백 무관 매핑', () => {
        expect(parseSectionRailKey('chat')).toBe('chat');
        expect(parseSectionRailKey('  VOIP ')).toBe('voip');
        expect(parseSectionRailKey('tourism-promo')).toBe('tourism-promo');
        expect(parseSectionRailKey('travel-booking')).toBe('travel-booking');
    });

    it('레거시 별칭(promo/tourism/travel)도 매핑', () => {
        expect(parseSectionRailKey('promo')).toBe('tourism-promo');
        expect(parseSectionRailKey('tourism')).toBe('tourism-promo');
        expect(parseSectionRailKey('travel')).toBe('travel-booking');
    });

    it('song-mode 및 별칭 song 매핑', () => {
        expect(parseSectionRailKey('song-mode')).toBe('song-mode');
        expect(parseSectionRailKey('song')).toBe('song-mode');
    });

    it('미지원/빈 입력은 null', () => {
        expect(parseSectionRailKey('unknown')).toBeNull();
        expect(parseSectionRailKey('')).toBeNull();
        expect(parseSectionRailKey(null)).toBeNull();
        expect(parseSectionRailKey(undefined)).toBeNull();
    });
});
