import { describe, expect, it } from '@jest/globals';

import { formatDistance, escapeMapLabel, buildNearbyMapHtml, todayPlus } from '../features/travel-booking/travelBooking';
import type { NearbyPlace } from '../features/travel-booking/types';

describe('formatDistance — m/km 표시', () => {
    it('1km 미만은 m, 1km 이상은 소수1자리 km', () => {
        expect(formatDistance(0)).toBe('0m');
        expect(formatDistance(999)).toBe('999m');
        expect(formatDistance(1000)).toBe('1.0km');
        expect(formatDistance(1500)).toBe('1.5km');
        expect(formatDistance(12345)).toBe('12.3km');
    });
});

describe('escapeMapLabel — HTML 엔티티 이스케이프', () => {
    it('&, <, >, ", \' 를 안전하게 이스케이프한다', () => {
        expect(escapeMapLabel('A & B')).toBe('A &amp; B');
        expect(escapeMapLabel('<b>"x"</b>')).toBe('&lt;b&gt;&quot;x&quot;&lt;/b&gt;');
        expect(escapeMapLabel("it's")).toBe('it&#39;s');
    });

    it('& 를 가장 먼저 처리해 이중 이스케이프하지 않는다', () => {
        expect(escapeMapLabel('<')).toBe('&lt;');
        expect(escapeMapLabel('&lt;')).toBe('&amp;lt;');
    });
});

describe('todayPlus — YYYY-MM-DD 오프셋', () => {
    it('YYYY-MM-DD 형식을 반환한다', () => {
        expect(todayPlus(0)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('+1일은 기준일보다 하루 뒤다', () => {
        const base = new Date(`${todayPlus(0)}T00:00:00Z`);
        const next = new Date(`${todayPlus(1)}T00:00:00Z`);
        expect(next.getTime() - base.getTime()).toBe(24 * 60 * 60 * 1000);
    });
});

describe('buildNearbyMapHtml — Leaflet WebView HTML', () => {
    const place: NearbyPlace = {
        id: 'p1',
        category: 'hotel',
        category_label: '호텔',
        name: 'Grand & "Best" Hotel',
        address: '서울시 중구 <테스트>',
        distance_m: 1500,
        rating: 4.5,
        price_tier: '$$',
        booking_supported: true,
        phone: '02-000-0000',
        summary: '',
        latitude: 37.5,
        longitude: 127.0,
        google_maps_url: 'https://maps.example/p1',
    };

    const html = buildNearbyMapHtml({
        centerLat: 37.5665,
        centerLon: 126.978,
        places: [place],
        selectedPlaceId: 'p1',
    });

    it('유효한 HTML 문서를 반환한다', () => {
        expect(html.startsWith('<!DOCTYPE html>')).toBe(true);
        expect(html).toContain('id="map"');
        expect(html).toContain('leaflet');
    });

    it('장소 라벨을 이스케이프해 주입한다', () => {
        expect(html).toContain('Grand &amp; &quot;Best&quot; Hotel');
        expect(html).toContain('&lt;테스트&gt;');
        expect(html).toContain('1.5km');
    });

    it('중심 좌표와 선택 장소 id 를 직렬화한다', () => {
        expect(html).toContain('37.5665');
        expect(html).toContain('126.978');
        expect(html).toContain('"p1"');
    });

    it('[회귀가드] 마커 루프에 오삽입 JSX(accessibilityRole/item.key)가 없다', () => {
        // build35 베이스라인부터 지도 스크립트에 섞여 있던 JSX 3줄 제거 회귀 방지.
        expect(html).not.toContain('accessibilityRole');
        expect(html).not.toContain('item.key');
        expect(html).not.toContain('buildSectionRailSelector');
        expect(html).toContain('places.forEach((place) => {');
    });
});
