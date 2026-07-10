// [기능 분리 Phase5.4] 일반전화+예약(여행 예약) 기능 — 순수 헬퍼(자족적, App 상태 비의존).
// App.tsx 모놀리스에서 추출. 거리 포맷/HTML 이스케이프/근처 지도 HTML 빌드/예약 날짜는 부작용이 없어 안전하게 분리된다.

import type { NearbyPlace } from './types';

/** 미터 거리 → `###m` 또는 `#.#km` 표시 문자열. */
export function formatDistance(distanceM: number): string {
    return distanceM >= 1000 ? `${(distanceM / 1000).toFixed(1)}km` : `${distanceM}m`;
}

/** 지도 라벨을 WebView HTML에 안전 주입하기 위한 HTML 이스케이프. */
export function escapeMapLabel(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** 근처 장소 목록을 Leaflet/OSM WebView 지도 HTML 문자열로 빌드. */
export function buildNearbyMapHtml(params: {
    centerLat: number;
    centerLon: number;
    places: NearbyPlace[];
    selectedPlaceId: string;
}): string {
    const places = params.places.map((place) => ({
        id: place.id,
        name: escapeMapLabel(place.name),
        address: escapeMapLabel(place.address),
        categoryLabel: escapeMapLabel(place.category_label),
        distanceLabel: formatDistance(place.distance_m),
        lat: place.latitude,
        lon: place.longitude,
        googleMapsUrl: place.google_maps_url,
        bookingSupported: place.booking_supported,
        reservable: place.booking_supported && (place.category === 'hotel' || place.category === 'airport'),
    }));

    return `<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        html, body, #map { height: 100%; margin: 0; padding: 0; background: #08111b; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .leaflet-container { background: linear-gradient(180deg, #0b1622 0%, #071018 100%); }
        .leaflet-popup-content-wrapper, .leaflet-popup-tip { background: #0f1b2a; color: #e6edf3; }
        .leaflet-popup-content { margin: 10px 12px; line-height: 1.4; }
        .map-popup-title { font-weight: 700; font-size: 13px; }
        .map-popup-meta { font-size: 11px; color: #8fd3ff; margin-top: 4px; }
        .map-popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .map-popup-btn {
            border: 0;
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 11px;
            font-weight: 700;
            color: #e6edf3;
            background: #1d4ed8;
        }
        .map-popup-btn.secondary { background: #0d2a4a; color: #79c0ff; border: 1px solid #35506c; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const postToApp = (payload) => {
            if (window.ReactNativeWebView && typeof window.ReactNativeWebView.postMessage === 'function') {
                window.ReactNativeWebView.postMessage(JSON.stringify(payload));
            }
        };
        const center = [${JSON.stringify(params.centerLat)}, ${JSON.stringify(params.centerLon)}];
        const places = ${JSON.stringify(places)};
        const selectedPlaceId = ${JSON.stringify(params.selectedPlaceId)};
        const map = L.map('map', {
            zoomControl: false,
            attributionControl: true,
        }).setView(center, places.length ? 12 : 11);
        // ODbL/OSM 타일 정책상 출처표기 필수. Leaflet 프리픽스는 숨기고 OSM 크레딧만 노출.
        map.attributionControl.setPrefix('');

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors (ODbL)',
        }).addTo(map);

        const bounds = [];
        const selectedMarkerStyle = { radius: 10, color: '#ffd166', weight: 3, fillColor: '#ff7b00', fillOpacity: 0.95 };
        const defaultMarkerStyle = { radius: 8, color: '#7dd3fc', weight: 2, fillColor: '#1d4ed8', fillOpacity: 0.92 };

        const userMarker = L.circleMarker(center, {
            radius: 9,
            color: '#9be8b3',
            weight: 3,
            fillColor: '#22c55e',
            fillOpacity: 0.9,
        }).addTo(map).bindPopup('<div class="map-popup-title">현재 위치</div>');
        bounds.push(center);

        document.addEventListener('click', (event) => {
            const target = event.target;
            if (!(target instanceof HTMLElement)) {
                return;
            }
            const button = target.closest('.map-popup-btn');
            if (!button) {
                return;
            }
            const action = button.getAttribute('data-action');
            const placeId = button.getAttribute('data-place-id');
            const googleMapsUrl = button.getAttribute('data-google-maps-url');
            if (!action || !placeId) {
                return;
            }
            postToApp({
                type: 'nearby-map-action',
                action,
                placeId,
                googleMapsUrl,
            });
        });

        let selectedMarker = null;
        places.forEach((place) => {
            const point = [place.lat, place.lon];
            bounds.push(point);
            const popupHtml = '<div class="map-popup-title">' + place.name + '</div>'
                + '<div class="map-popup-meta">' + place.categoryLabel + ' · ' + place.distanceLabel + '<br/>' + place.address + '</div>'
                + '<div class="map-popup-actions">'
                + '<button type="button" class="map-popup-btn secondary" data-action="focus" data-place-id="' + place.id + '">선택</button>'
                + '<button type="button" class="map-popup-btn" data-action="route" data-place-id="' + place.id + '" data-google-maps-url="' + place.googleMapsUrl + '">길찾기</button>'
                + (place.reservable
                    ? '<button type="button" class="map-popup-btn secondary" data-action="book" data-place-id="' + place.id + '">예약 선택</button>'
                    : '')
                + '</div>';
            const marker = L.circleMarker(point, place.id === selectedPlaceId ? selectedMarkerStyle : defaultMarkerStyle)
                .addTo(map)
                .bindPopup(popupHtml);
            marker.on('click', () => {
                postToApp({ type: 'nearby-map-action', action: 'focus', placeId: place.id, googleMapsUrl: place.googleMapsUrl });
            });
            if (place.id === selectedPlaceId) {
                selectedMarker = marker;
            }
        });

        if (bounds.length > 1) {
            map.fitBounds(bounds, { padding: [26, 26] });
        }

        if (selectedMarker) {
            selectedMarker.openPopup();
        } else {
            userMarker.openPopup();
        }
    </script>
</body>
</html>`;
}

/** 오늘 + N일을 `YYYY-MM-DD` 로 (체크인/체크아웃 기본값 등 예약 날짜). */
export function todayPlus(days: number): string {
    const now = new Date();
    now.setDate(now.getDate() + days);
    return now.toISOString().slice(0, 10);
}
