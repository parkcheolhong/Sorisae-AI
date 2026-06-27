// 소리새 AI — 관광 특화 구조화 일정 패널.
// /api/llm/voice/answer 의 일자별 JSON 을 일정 카드 + OSM(Leaflet) 지도로 렌더한다.
// 지도/링크는 OpenStreetMap(ODbL)만 사용 — Google Maps 약관 회피(자체 인덱스 그라운딩과 동일 정책).
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import WebView from 'react-native-webview';

import {
  getAbVariant,
  requestTravelItinerary,
  streamTravelItinerary,
  submitItineraryFeedback,
  type ItineraryPlace,
  type ItineraryPreview,
  type TravelItinerary,
} from '../../api/tourismAnswer';
import {
  getLocationConsent,
  setLocationConsent,
  LOCATION_CONSENT_VERSION,
} from '../../privacy/locationConsent';
import LicensedImage from '../../components/LicensedImage';

interface TravelItineraryPanelProps {
  latitude?: number;
  longitude?: number;
  language?: string;
  regionHint?: string;
  countryCode?: string;
  apiBase?: string;
  // 소리새 AI 음성 인식 결과를 입력으로 자동 연결(seed). seedNonce 가 바뀔 때마다 seedQuery 를 입력에 채운다
  // (동일 문장을 다시 말해도 nonce 증가로 재반영). 생성은 사용자가 직접 '일정 만들기'로 트리거.
  seedQuery?: string;
  seedNonce?: number;
}

const DAY_OPTIONS = [1, 2, 3, 4, 5];

function escapeHtml(value: string): string {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

interface FlatPlace extends ItineraryPlace {
  dayNum: number;
  order: number;
}

function flattenPlaces(itinerary: TravelItinerary | null): FlatPlace[] {
  if (!itinerary) return [];
  const out: FlatPlace[] = [];
  let order = 0;
  for (const day of itinerary.days) {
    for (const item of day.items) {
      if (typeof item.latitude === 'number' && typeof item.longitude === 'number') {
        order += 1;
        out.push({ ...item, dayNum: day.day, order });
      }
    }
  }
  return out;
}

function buildItineraryMapHtml(places: FlatPlace[]): string | null {
  if (places.length === 0) return null;
  const centerLat = places.reduce((s, p) => s + (p.latitude as number), 0) / places.length;
  const centerLon = places.reduce((s, p) => s + (p.longitude as number), 0) / places.length;
  const markers = places.map((p) => ({
    lat: p.latitude,
    lon: p.longitude,
    order: p.order,
    day: p.dayNum,
    name: escapeHtml(p.name),
    blurb: escapeHtml(p.blurb || ''),
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
    .pin {
      background: #1d4ed8; color: #fff; border: 2px solid #9be8b3; border-radius: 999px;
      width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.5);
    }
    .pop-title { font-weight: 700; font-size: 13px; }
    .pop-meta { font-size: 11px; color: #8fd3ff; margin-top: 3px; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const center = [${JSON.stringify(centerLat)}, ${JSON.stringify(centerLon)}];
    const markers = ${JSON.stringify(markers)};
    const map = L.map('map', { zoomControl: false, attributionControl: true }).setView(center, 13);
    map.attributionControl.setPrefix('');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors (ODbL)' }).addTo(map);
    const bounds = [];
    markers.forEach((m) => {
      const point = [m.lat, m.lon];
      bounds.push(point);
      const icon = L.divIcon({ className: '', html: '<div class="pin">' + m.order + '</div>', iconSize: [26, 26], iconAnchor: [13, 13] });
      const metaLabel = m.day ? ('Day ' + m.day) : '추천 후보';
      const popup = '<div class="pop-title">' + m.order + '. ' + m.name + '</div>'
        + '<div class="pop-meta">' + metaLabel + (m.blurb ? ' · ' + m.blurb : '') + '</div>';
      L.marker(point, { icon: icon }).addTo(map).bindPopup(popup);
    });
    if (bounds.length > 1) { map.fitBounds(bounds, { padding: [28, 28] }); }
    else if (bounds.length === 1) { map.setView(bounds[0], 15); }
  </script>
</body>
</html>`;
}

const TravelItineraryPanel: React.FC<TravelItineraryPanelProps> = ({
  latitude,
  longitude,
  language,
  regionHint,
  countryCode,
  apiBase,
  seedQuery,
  seedNonce,
}) => {
  const [query, setQuery] = useState('');
  const [days, setDays] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [itinerary, setItinerary] = useState<TravelItinerary | null>(null);
  // 스트리밍 preview(검색 직후 장소·도시컨텍스트). 최종 일정(final) 도착 전까지 지도를 먼저 그린다.
  const [preview, setPreview] = useState<ItineraryPreview | null>(null);
  // 위치 동의: null=미결정, true=동의(좌표 전송), false=거부(지역명만).
  const [locationConsent, setLocationConsentState] = useState<boolean | null>(null);
  const streamCancelRef = useRef<null | (() => void)>(null);

  // 파일럿 베타 피드백(만족도·NPS·A/B).
  const [abVariant, setAbVariant] = useState<'A' | 'B'>('A');
  const [fbRating, setFbRating] = useState<'up' | 'down' | null>(null);
  const [fbNps, setFbNps] = useState<number | null>(null);
  const [fbComment, setFbComment] = useState('');
  const [fbSent, setFbSent] = useState(false);

  // 언마운트 시 진행 중인 스트림 정리.
  useEffect(() => () => { streamCancelRef.current?.(); }, []);

  // 설치별 안정 A/B 버킷 로드(variant 별 NPS 비교용).
  useEffect(() => {
    let alive = true;
    void (async () => {
      const v = await getAbVariant();
      if (alive) setAbVariant(v);
    })();
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const state = await getLocationConsent();
      if (!alive) return;
      setLocationConsentState(
        state.granted && state.version === LOCATION_CONSENT_VERSION ? true : state.version ? false : null,
      );
    })();
    return () => {
      alive = false;
    };
  }, []);

  const decideConsent = async (granted: boolean) => {
    await setLocationConsent(granted);
    setLocationConsentState(granted);
  };

  const hasCoords =
    typeof latitude === 'number' && Number.isFinite(latitude) &&
    typeof longitude === 'number' && Number.isFinite(longitude);

  // 소리새 AI 음성 발화가 들어오면(seedNonce 변경) 입력창을 그 문장으로 채운다.
  useEffect(() => {
    if (!seedNonce) return;
    const seeded = (seedQuery || '').trim();
    if (seeded) {
      setQuery(seeded);
    }
    // seedNonce 변경에만 반응(같은 문장 재발화도 반영). seedQuery 는 nonce 와 함께 갱신됨.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedNonce]);

  const flatPlaces = useMemo(() => flattenPlaces(itinerary), [itinerary]);
  // preview 장소(좌표 보유)를 지도 핀으로(day=0 → "추천 후보"). final 도착 전 즉시 표시.
  const previewPlaces = useMemo<FlatPlace[]>(() => {
    if (!preview) return [];
    const out: FlatPlace[] = [];
    let order = 0;
    for (const item of preview.places) {
      if (typeof item.latitude === 'number' && typeof item.longitude === 'number') {
        order += 1;
        out.push({ ...item, dayNum: 0, order });
      }
    }
    return out;
  }, [preview]);
  const mapPlaces = itinerary ? flatPlaces : previewPlaces;
  const mapHtml = useMemo(() => buildItineraryMapHtml(mapPlaces), [mapPlaces]);
  // 도시 컨텍스트는 최종 일정 우선, 없으면 preview 의 것을 먼저 보여준다.
  const cityContext = itinerary?.city_context ?? preview?.city_context ?? null;
  const currentMonth = useMemo(() => new Date().getMonth() + 1, []);

  const onGenerate = () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    setError('');
    setItinerary(null);
    setPreview(null);
    setFbSent(false);
    setFbRating(null);
    setFbNps(null);
    setFbComment('');

    // 데이터 최소화: 위치 동의가 있을 때만 정밀 좌표를 전송. 미동의 시 지역명만 사용.
    const sendCoords = locationConsent === true && hasCoords;
    const params = {
      query: q,
      language,
      regionHint,
      countryCode,
      latitude: sendCoords ? (latitude as number) : undefined,
      longitude: sendCoords ? (longitude as number) : undefined,
      days,
    };

    const applyFinal = (result: TravelItinerary) => {
      setItinerary(result);
      setPreview(null);
      if (result.days.length === 0) {
        setError('관광 인덱스에서 결과를 찾지 못했어요. 위치/검색어를 바꿔 보세요.');
      }
    };

    // 비스트리밍 폴백(구버전 백엔드/스트림 차단 시).
    const fallback = () => {
      void (async () => {
        try {
          const result = await requestTravelItinerary(params, 60000, apiBase);
          applyFinal(result);
        } catch (err) {
          setError(err instanceof Error ? err.message : '일정 생성 실패');
          setItinerary(null);
          setPreview(null);
        } finally {
          setLoading(false);
        }
      })();
    };

    // SSE-over-POST 스트리밍: preview(지도 즉시) → final(전체 일정).
    streamCancelRef.current?.();
    let finished = false;
    streamCancelRef.current = streamTravelItinerary(
      params,
      {
        onPreview: (p) => {
          if (!finished) setPreview(p);
        },
        onFinal: (it) => {
          finished = true;
          applyFinal(it);
          setLoading(false);
        },
        onError: () => {
          if (finished) return;
          finished = true;
          fallback();
        },
      },
      apiBase,
    );
  };

  const onSubmitFeedback = async () => {
    if (fbSent || (!fbRating && fbNps === null)) return;
    // 베스트에포트: 성공/실패와 무관하게 감사 표시(반복 노출 방지).
    setFbSent(true);
    await submitItineraryFeedback(
      {
        query: itinerary?.query || query.trim(),
        language: itinerary?.language || language,
        variant: abVariant,
        rating: fbRating || undefined,
        nps: fbNps ?? undefined,
        comment: fbComment.trim() || undefined,
        days,
        candidate_count: itinerary?.candidate_count,
      },
      apiBase,
    );
  };

  const openMap = (place: ItineraryPlace) => {
    const url =
      place.map_url ||
      (typeof place.latitude === 'number' && typeof place.longitude === 'number'
        ? `https://www.openstreetmap.org/?mlat=${place.latitude}&mlon=${place.longitude}#map=17/${place.latitude}/${place.longitude}`
        : '');
    if (url) {
      void Linking.openURL(url);
    }
  };

  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>AI 여행 일정</Text>
        <Text style={styles.subtitle}>소리새 AI · 관광 특화</Text>
      </View>
      <Text style={styles.hint}>가고 싶은 도시·테마를 적어 주세요. 예: "오사카 라멘 맛집 위주로", "파리 미술관 코스"</Text>

      {hasCoords && locationConsent === null ? (
        <View style={styles.consentWrap}>
          <Text style={styles.consentText}>
            더 가까운 추천을 위해 현재 위치(좌표)를 사용할까요? 동의하지 않으면 지역명만으로 추천합니다.
            위치는 추천 처리에만 쓰이며 저장되지 않습니다.
          </Text>
          <View style={styles.consentBtnRow}>
            <Pressable
              style={[styles.consentBtn, styles.consentBtnPrimary]}
              onPress={() => { void decideConsent(true); }}
              accessibilityLabel="sorisae-location-consent-allow"
              testID="sorisae-location-consent-allow"
            >
              <Text style={styles.consentBtnPrimaryText}>위치 사용 동의</Text>
            </Pressable>
            <Pressable
              style={styles.consentBtn}
              onPress={() => { void decideConsent(false); }}
              accessibilityLabel="sorisae-location-consent-deny"
              testID="sorisae-location-consent-deny"
            >
              <Text style={styles.consentBtnText}>지역명만 사용</Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      {hasCoords && locationConsent !== null ? (
        <Pressable
          style={styles.consentStatusRow}
          onPress={() => { void decideConsent(!locationConsent); }}
          accessibilityLabel="sorisae-location-consent-toggle"
          testID="sorisae-location-consent-toggle"
        >
          <Text style={styles.consentStatusText}>
            {locationConsent ? '📍 위치 사용 동의됨' : '🚫 위치 미사용(지역명만)'} · 탭하여 변경
          </Text>
        </Pressable>
      ) : null}

      <TextInput
        style={styles.input}
        value={query}
        onChangeText={setQuery}
        placeholder="여행 요청을 입력하세요"
        placeholderTextColor="#79889a"
        multiline
        accessibilityLabel="sorisae-itinerary-query-input"
        testID="sorisae-itinerary-query-input"
      />

      <Text style={styles.label}>일정 일수</Text>
      <View style={styles.dayRow}>
        {DAY_OPTIONS.map((d) => (
          <Pressable
            key={d}
            style={[styles.dayBtn, days === d && styles.dayBtnActive]}
            onPress={() => setDays(d)}
            accessibilityLabel={`sorisae-itinerary-days-${d}`}
            testID={`sorisae-itinerary-days-${d}`}
          >
            <Text style={[styles.dayBtnText, days === d && styles.dayBtnTextActive]}>{d}일</Text>
          </Pressable>
        ))}
      </View>

      <Pressable
        style={[styles.generateBtn, loading && styles.generateBtnDisabled]}
        onPress={onGenerate}
        disabled={loading}
        accessibilityLabel="sorisae-itinerary-generate-button"
        testID="sorisae-itinerary-generate-button"
      >
        {loading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.generateBtnText}>일정 만들기</Text>}
      </Pressable>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {loading && preview && !itinerary ? (
        <Text style={styles.previewBanner}>
          📍 후보 {previewPlaces.length}곳을 먼저 표시했어요 · AI가 일정을 작성 중…
        </Text>
      ) : null}

      {itinerary && itinerary.summary ? (
        <Text style={styles.summary}>{itinerary.summary}</Text>
      ) : null}

      {cityContext &&
      (cityContext.festivals.length > 0 || cityContext.foods.length > 0) ? (
        <View style={styles.kgWrap}>
          <Text style={styles.kgTitle}>{cityContext.city_name} 알아두기</Text>
          {cityContext.festivals.length > 0 ? (
            <View style={styles.kgSection}>
              <Text style={styles.kgLabel}>축제</Text>
              {cityContext.festivals.map((f, idx) => {
                const isThisMonth =
                  typeof f.month === 'number' && f.month === currentMonth;
                return (
                  <View key={`fest-${idx}`} style={styles.kgRow}>
                    <Text style={styles.kgName}>
                      {f.name}
                      {typeof f.month === 'number' ? `  ·  ${f.month}월` : ''}
                      {isThisMonth ? '  · 이번 달' : ''}
                    </Text>
                    {f.description ? <Text style={styles.kgDesc}>{f.description}</Text> : null}
                  </View>
                );
              })}
            </View>
          ) : null}
          {cityContext.foods.length > 0 ? (
            <View style={styles.kgSection}>
              <Text style={styles.kgLabel}>향토 음식</Text>
              <Text style={styles.kgFoods}>
                {cityContext.foods.map((f) => f.name).join(' · ')}
              </Text>
            </View>
          ) : null}
        </View>
      ) : null}

      {mapHtml ? (
        <View
          style={styles.mapWrap}
          accessible
          accessibilityLabel={`여행 일정 지도 — 장소 ${mapPlaces.length}곳을 ${itinerary ? '일자별' : '추천 후보'} 번호 핀으로 표시`}
        >
          <WebView
            originWhitelist={['*']}
            source={{ html: mapHtml }}
            style={styles.mapWebView}
            scrollEnabled={false}
            nestedScrollEnabled
          />
        </View>
      ) : null}

      {itinerary?.days.map((day) => (
        <View key={day.day} style={styles.dayCard}>
          <Text style={styles.dayCardTitle}>Day {day.day}{day.title ? ` · ${day.title}` : ''}</Text>
          {day.items.map((place, idx) => (
            <View
              key={`${day.day}-${place.place_id}-${idx}`}
              style={styles.placeRow}
              accessible
              accessibilityLabel={[
                `Day ${day.day} 일정 ${idx + 1}번`,
                place.name,
                place.category || '',
                place.address ? `주소 ${place.address}` : '',
                place.blurb || '',
              ].filter(Boolean).join(', ')}
            >
              {place.media && place.media.length > 0 ? (
                <LicensedImage media={place.media[0]} height={150} style={styles.placeImage} />
              ) : null}
              <Text style={styles.placeName}>{place.name}{place.category ? `  ·  ${place.category}` : ''}</Text>
              {place.blurb ? <Text style={styles.placeBlurb}>{place.blurb}</Text> : null}
              {place.address ? <Text style={styles.placeMeta}>{place.address}</Text> : null}
              {place.phone ? <Text style={styles.placeMeta}>전화 {place.phone}</Text> : null}
              {place.hours ? <Text style={styles.placeMeta}>영업 {place.hours}</Text> : null}
              {place.map_url || (typeof place.latitude === 'number' && typeof place.longitude === 'number') ? (
                <Pressable
                  style={styles.mapLinkBtn}
                  onPress={() => openMap(place)}
                  accessibilityLabel={`sorisae-itinerary-map-${day.day}-${idx}`}
                  testID={`sorisae-itinerary-map-${day.day}-${idx}`}
                >
                  <Text style={styles.mapLinkText}>지도에서 보기</Text>
                </Pressable>
              ) : null}
            </View>
          ))}
        </View>
      ))}

      {itinerary && itinerary.tips.length > 0 ? (
        <View style={styles.tipsWrap}>
          <Text style={styles.tipsTitle}>여행 팁 (안전·법규·예절·음식)</Text>
          {itinerary.tips.map((tip, idx) => (
            <Text key={idx} style={styles.tipText}>• {tip}</Text>
          ))}
        </View>
      ) : null}

      {itinerary && itinerary.days.length > 0 ? (
        <>
          <Text style={styles.disclosure}>ℹ️ {itinerary.disclosure}</Text>
          <Text style={styles.attribution}>{itinerary.attribution}</Text>

          <View style={styles.fbWrap}>
            {fbSent ? (
              <Text style={styles.fbThanks}>피드백 감사합니다! 더 나은 추천에 반영할게요. 🙏</Text>
            ) : (
              <>
                <Text style={styles.fbTitle}>이 일정이 도움이 되었나요?</Text>
                <View style={styles.fbThumbRow}>
                  <Pressable
                    style={[styles.fbThumb, fbRating === 'up' && styles.fbThumbSel]}
                    onPress={() => setFbRating(fbRating === 'up' ? null : 'up')}
                    accessibilityLabel="sorisae-itinerary-feedback-up"
                    testID="sorisae-itinerary-feedback-up"
                  >
                    <Text style={[styles.fbThumbText, fbRating === 'up' && styles.fbThumbTextSel]}>👍 도움됐어요</Text>
                  </Pressable>
                  <Pressable
                    style={[styles.fbThumb, fbRating === 'down' && styles.fbThumbSel]}
                    onPress={() => setFbRating(fbRating === 'down' ? null : 'down')}
                    accessibilityLabel="sorisae-itinerary-feedback-down"
                    testID="sorisae-itinerary-feedback-down"
                  >
                    <Text style={[styles.fbThumbText, fbRating === 'down' && styles.fbThumbTextSel]}>👎 아쉬워요</Text>
                  </Pressable>
                </View>

                <Text style={styles.fbNpsLabel}>친구에게 추천할 의향 (0–10)</Text>
                <View style={styles.fbNpsRow}>
                  {Array.from({ length: 11 }, (_, n) => (
                    <Pressable
                      key={n}
                      style={[styles.fbNps, fbNps === n && styles.fbNpsSel]}
                      onPress={() => setFbNps(fbNps === n ? null : n)}
                      accessibilityLabel={`sorisae-itinerary-nps-${n}`}
                      testID={`sorisae-itinerary-nps-${n}`}
                    >
                      <Text style={[styles.fbNpsText, fbNps === n && styles.fbNpsTextSel]}>{n}</Text>
                    </Pressable>
                  ))}
                </View>

                <TextInput
                  style={styles.fbComment}
                  value={fbComment}
                  onChangeText={setFbComment}
                  placeholder="개선 의견(선택)"
                  placeholderTextColor="#79889a"
                  multiline
                  accessibilityLabel="sorisae-itinerary-feedback-comment"
                  testID="sorisae-itinerary-feedback-comment"
                />

                <Pressable
                  style={[styles.fbSubmit, !fbRating && fbNps === null && styles.fbSubmitDisabled]}
                  onPress={() => { void onSubmitFeedback(); }}
                  disabled={!fbRating && fbNps === null}
                  accessibilityLabel="sorisae-itinerary-feedback-submit"
                  testID="sorisae-itinerary-feedback-submit"
                >
                  <Text style={styles.fbSubmitText}>피드백 보내기</Text>
                </Pressable>
              </>
            )}
          </View>
        </>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    marginTop: 16,
    padding: 14,
    borderRadius: 14,
    backgroundColor: '#0b1622',
    borderWidth: 1,
    borderColor: '#1d3047',
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { color: '#e6edf3', fontWeight: '800', fontSize: 15 },
  subtitle: { color: '#79c0ff', fontSize: 12 },
  hint: { color: '#8b9bad', fontSize: 12, marginTop: 6, lineHeight: 17 },
  consentWrap: {
    marginTop: 10,
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#10202e',
    borderWidth: 1,
    borderColor: '#27405a',
  },
  consentText: { color: '#c2cedb', fontSize: 12, lineHeight: 18 },
  consentBtnRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
  consentBtn: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: '#0d2236',
    borderWidth: 1,
    borderColor: '#27405a',
  },
  consentBtnText: { color: '#a9b7c6', fontWeight: '700', fontSize: 12 },
  consentBtnPrimary: { backgroundColor: '#1d4ed8', borderColor: '#1d4ed8' },
  consentBtnPrimaryText: { color: '#fff', fontWeight: '800', fontSize: 12 },
  consentStatusRow: { marginTop: 8, alignSelf: 'flex-start' },
  consentStatusText: { color: '#79c0ff', fontSize: 11, fontWeight: '700' },
  input: {
    marginTop: 10,
    minHeight: 44,
    maxHeight: 96,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#27405a',
    backgroundColor: '#08121d',
    color: '#e6edf3',
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    textAlignVertical: 'top',
  },
  label: { color: '#a9b7c6', fontSize: 12, marginTop: 12, marginBottom: 6 },
  dayRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  dayBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: '#0d2236',
    borderWidth: 1,
    borderColor: '#27405a',
  },
  dayBtnActive: { backgroundColor: '#1d4ed8', borderColor: '#1d4ed8' },
  dayBtnText: { color: '#a9b7c6', fontWeight: '700', fontSize: 13 },
  dayBtnTextActive: { color: '#fff' },
  generateBtn: {
    marginTop: 14,
    borderRadius: 12,
    backgroundColor: '#1d4ed8',
    paddingVertical: 13,
    alignItems: 'center',
  },
  generateBtnDisabled: { opacity: 0.6 },
  generateBtnText: { color: '#fff', fontWeight: '800', fontSize: 14 },
  error: { color: '#ff9b9b', fontSize: 13, marginTop: 10 },
  previewBanner: {
    color: '#9be8b3',
    fontSize: 12,
    marginTop: 12,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 10,
    backgroundColor: '#0f2419',
    borderWidth: 1,
    borderColor: '#1f5436',
    fontWeight: '700',
  },
  summary: { color: '#e6edf3', fontSize: 14, marginTop: 14, lineHeight: 20, fontWeight: '600' },
  kgWrap: {
    marginTop: 12,
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#161029',
    borderWidth: 1,
    borderColor: '#3a2b5c',
  },
  kgTitle: { color: '#c9a6ff', fontWeight: '800', fontSize: 13, marginBottom: 8 },
  kgSection: { marginTop: 6 },
  kgLabel: { color: '#b08bff', fontSize: 12, fontWeight: '700', marginBottom: 4 },
  kgRow: { marginTop: 4 },
  kgName: { color: '#e6edf3', fontSize: 13, fontWeight: '600' },
  kgDesc: { color: '#a99cc4', fontSize: 12, marginTop: 1, lineHeight: 17 },
  kgFoods: { color: '#ddd3f0', fontSize: 13, lineHeight: 19 },
  mapWrap: {
    marginTop: 12,
    height: 220,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#1d3047',
  },
  mapWebView: { flex: 1, backgroundColor: '#08111b' },
  dayCard: {
    marginTop: 12,
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#08121d',
    borderWidth: 1,
    borderColor: '#1d3047',
  },
  dayCardTitle: { color: '#79c0ff', fontWeight: '800', fontSize: 14, marginBottom: 8 },
  placeRow: {
    paddingVertical: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#1d3047',
  },
  placeImage: { marginBottom: 8 },
  placeName: { color: '#e6edf3', fontWeight: '700', fontSize: 14 },
  placeBlurb: { color: '#c2cedb', fontSize: 13, marginTop: 3, lineHeight: 18 },
  placeMeta: { color: '#8b9bad', fontSize: 12, marginTop: 2 },
  mapLinkBtn: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: '#0d2a4a',
    borderWidth: 1,
    borderColor: '#35506c',
  },
  mapLinkText: { color: '#79c0ff', fontWeight: '700', fontSize: 12 },
  tipsWrap: {
    marginTop: 14,
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#0d1f14',
    borderWidth: 1,
    borderColor: '#1f3d28',
  },
  tipsTitle: { color: '#9be8b3', fontWeight: '800', fontSize: 13, marginBottom: 6 },
  tipText: { color: '#cfe8d6', fontSize: 13, marginTop: 4, lineHeight: 18 },
  disclosure: { color: '#8b9bad', fontSize: 11, marginTop: 12, lineHeight: 16 },
  attribution: { color: '#79889a', fontSize: 10, marginTop: 4, textAlign: 'right' },
  fbWrap: {
    marginTop: 14,
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#10202e',
    borderWidth: 1,
    borderColor: '#27405a',
  },
  fbTitle: { color: '#e6edf3', fontWeight: '800', fontSize: 13 },
  fbThumbRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
  fbThumb: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: '#0d2236',
    borderWidth: 1,
    borderColor: '#27405a',
  },
  fbThumbSel: { backgroundColor: '#1d4ed8', borderColor: '#1d4ed8' },
  fbThumbText: { color: '#a9b7c6', fontWeight: '700', fontSize: 12 },
  fbThumbTextSel: { color: '#fff' },
  fbNpsLabel: { color: '#8b9bad', fontSize: 11, marginTop: 12 },
  fbNpsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  fbNps: {
    width: 30,
    height: 30,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0d2236',
    borderWidth: 1,
    borderColor: '#27405a',
  },
  fbNpsSel: { backgroundColor: '#1f5436', borderColor: '#2f8a57' },
  fbNpsText: { color: '#a9b7c6', fontWeight: '700', fontSize: 12 },
  fbNpsTextSel: { color: '#9be8b3' },
  fbComment: {
    marginTop: 10,
    minHeight: 38,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#27405a',
    backgroundColor: '#0d2236',
    color: '#e6edf3',
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 13,
  },
  fbSubmit: {
    marginTop: 10,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: '#1d4ed8',
  },
  fbSubmitDisabled: { opacity: 0.5 },
  fbSubmitText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  fbThanks: { color: '#9be8b3', fontSize: 13, fontWeight: '700', textAlign: 'center', paddingVertical: 6 },
});

export default TravelItineraryPanel;
