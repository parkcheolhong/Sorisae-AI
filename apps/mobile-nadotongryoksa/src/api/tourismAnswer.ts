// 소리새 AI 관광 특화 구조화 답변(/api/llm/voice/answer) 클라이언트.
// RAG(자체 관광 인덱스, hybrid 검색) → LLM(스키마 강제) → 일자별 일정 JSON.
// 장소 사실(이름·주소·좌표·지도URL)은 서버가 검색결과에서 주입하므로 환각이 없다.
// 지도 링크는 OpenStreetMap(ODbL)만 사용한다(친구챗 그라운딩과 동일한 합법 오픈데이터 정책).
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { MediaInput } from '../media/licenseGate';

const BASE_URL: string =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  'http://10.0.2.2:8000';

export interface ItineraryPlace {
  place_id: number;
  name: string;
  category?: string | null;
  address?: string | null;
  phone?: string | null;
  hours?: string | null;
  website?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  map_url?: string | null;
  source?: string | null;
  license?: string | null;
  blurb?: string | null;
  media?: MediaInput[];
}

export interface ItineraryDay {
  day: number;
  title: string;
  items: ItineraryPlace[];
}

export interface ItineraryFestival {
  name: string;
  month?: number | null;
  season?: string | null;
  description?: string | null;
}

export interface ItineraryFood {
  name: string;
  description?: string | null;
  scope?: string | null; // 'city' | 'country'
}

export interface ItineraryCityContext {
  city_id: string;
  city_name: string;
  country_code?: string | null;
  festivals: ItineraryFestival[];
  foods: ItineraryFood[];
}

export interface TravelItinerary {
  query: string;
  language: string;
  location_hint?: string | null;
  summary: string;
  days: ItineraryDay[];
  tips: string[];
  attribution: string;
  candidate_count: number;
  city_context?: ItineraryCityContext | null;
  sponsored: boolean;
  disclosure: string;
}

export interface TravelItineraryRequest {
  query: string;
  language?: string;
  regionHint?: string;
  countryCode?: string;
  latitude?: number;
  longitude?: number;
  days?: number;
  maxPlaces?: number;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

// 여행 일정/장소 찾기 의도 키워드 — 이 신호가 있을 때만 소리새 AI 발화를 일정 패널 입력으로 연결한다.
// (일상 잡담·일반 질문은 패널을 건드리지 않게 한다.)
const ITINERARY_INTENT_KEYWORDS = [
  '일정', '코스', '동선', '플랜', '여행', '관광', '명소', '가볼만', '가 볼 만', '둘러보', '돌아보',
  '갈만한', '갈 만한', '당일치기', '데이트코스', '며칠', '추천', '가이드', '맛집', '여행지',
  '가볼곳', '가 볼 곳', '관광지', '투어',
  'itinerary', 'plan', 'trip', 'tour', 'sightsee', 'things to do', 'where to go',
  'what to do', 'day trip', 'recommend',
];
// "3박4일", "2박", "3일" 같은 기간 표현도 일정 의도로 본다.
const ITINERARY_DURATION_RE = /(\d+\s*박)|(\d+\s*일\b)|(\d+\s*days?)|(\d+\s*nights?)/i;

export function isTravelItineraryIntent(text: string): boolean {
  const raw = (text || '').trim();
  if (!raw) return false;
  const low = raw.toLowerCase();
  if (ITINERARY_DURATION_RE.test(low)) return true;
  return ITINERARY_INTENT_KEYWORDS.some((k) => low.includes(k.toLowerCase()));
}

function normalizePlace(raw: any): ItineraryPlace | null {
  const name = typeof raw?.name === 'string' ? raw.name.trim() : '';
  if (!name) return null;
  return {
    place_id: isFiniteNumber(raw?.place_id) ? raw.place_id : -1,
    name,
    category: raw?.category ?? null,
    address: raw?.address ?? null,
    phone: raw?.phone ?? null,
    hours: raw?.hours ?? null,
    website: raw?.website ?? null,
    latitude: isFiniteNumber(raw?.latitude) ? raw.latitude : null,
    longitude: isFiniteNumber(raw?.longitude) ? raw.longitude : null,
    map_url: typeof raw?.map_url === 'string' ? raw.map_url : null,
    source: raw?.source ?? null,
    license: raw?.license ?? null,
    blurb: typeof raw?.blurb === 'string' ? raw.blurb : null,
    media: Array.isArray(raw?.media)
      ? (raw.media as any[])
          .filter((m) => m && typeof m.url === 'string')
          .map((m) => ({
            url: m.url,
            type: m.type ?? 'image',
            title: m.title ?? null,
            author: m.author ?? null,
            source: m.source ?? null,
            license: m.license ?? null,
            license_id: m.license_id ?? null,
            license_url: m.license_url ?? null,
          }))
      : undefined,
  };
}

function parseCityContext(cc: any): ItineraryCityContext | null {
  if (!cc || typeof cc?.city_id !== 'string') return null;
  return {
    city_id: cc.city_id,
    city_name: typeof cc?.city_name === 'string' ? cc.city_name : cc.city_id,
    country_code: cc?.country_code ?? null,
    festivals: Array.isArray(cc?.festivals)
      ? cc.festivals
          .filter((f: any) => typeof f?.name === 'string' && f.name.trim())
          .map((f: any) => ({
            name: f.name,
            month: isFiniteNumber(f?.month) ? f.month : null,
            season: f?.season ?? null,
            description: f?.description ?? null,
          }))
      : [],
    foods: Array.isArray(cc?.foods)
      ? cc.foods
          .filter((f: any) => typeof f?.name === 'string' && f.name.trim())
          .map((f: any) => ({
            name: f.name,
            description: f?.description ?? null,
            scope: f?.scope ?? null,
          }))
      : [],
  };
}

export function parseItineraryResponse(data: any, fallbackQuery: string, fallbackLang = 'ko'): TravelItinerary {
  const days: ItineraryDay[] = Array.isArray(data?.days)
    ? data.days.map((d: any) => ({
        day: isFiniteNumber(d?.day) ? d.day : 1,
        title: typeof d?.title === 'string' ? d.title : '',
        items: Array.isArray(d?.items)
          ? d.items.map(normalizePlace).filter((p: ItineraryPlace | null): p is ItineraryPlace => p !== null)
          : [],
      }))
    : [];
  return {
    query: typeof data?.query === 'string' ? data.query : fallbackQuery,
    language: typeof data?.language === 'string' ? data.language : fallbackLang,
    location_hint: data?.location_hint ?? null,
    summary: typeof data?.summary === 'string' ? data.summary : '',
    days,
    tips: Array.isArray(data?.tips) ? data.tips.filter((t: unknown) => typeof t === 'string') : [],
    attribution:
      typeof data?.attribution === 'string' ? data.attribution : '© OpenStreetMap contributors (ODbL)',
    candidate_count: isFiniteNumber(data?.candidate_count) ? data.candidate_count : 0,
    city_context: parseCityContext(data?.city_context),
    sponsored: Boolean(data?.sponsored),
    disclosure:
      typeof data?.disclosure === 'string'
        ? data.disclosure
        : '오픈데이터(OSM·Wikidata) 기반 추천 · 광고/제휴 미포함',
  };
}

function buildAnswerBody(params: TravelItineraryRequest): Record<string, unknown> {
  const query = (params.query || '').trim();
  const body: Record<string, unknown> = { query };
  if (params.language) body.language = params.language;
  if (params.regionHint) body.region_hint = params.regionHint;
  if (params.countryCode) body.country_code = params.countryCode;
  if (isFiniteNumber(params.latitude)) body.latitude = params.latitude;
  if (isFiniteNumber(params.longitude)) body.longitude = params.longitude;
  if (isFiniteNumber(params.days)) body.days = params.days;
  if (isFiniteNumber(params.maxPlaces)) body.max_places = params.maxPlaces;
  return body;
}

export async function requestTravelItinerary(
  params: TravelItineraryRequest,
  timeoutMs = 60000,
  baseUrl: string = BASE_URL,
): Promise<TravelItinerary> {
  const query = (params.query || '').trim();
  if (!query) {
    throw new Error('질의가 비어 있습니다');
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${baseUrl}/api/llm/voice/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAnswerBody(params)),
      signal: controller.signal,
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({} as any));
      const message = typeof payload?.detail === 'string' ? payload.detail : `HTTP ${res.status}`;
      throw new Error(message);
    }
    const data = await res.json();
    return parseItineraryResponse(data, query, params.language || 'ko');
  } finally {
    clearTimeout(timer);
  }
}

export interface ItineraryPreview {
  query: string;
  language: string;
  location_hint?: string | null;
  city_context: ItineraryCityContext | null;
  places: ItineraryPlace[];
  candidate_count: number;
}

export interface ItineraryStreamHandlers {
  onPreview?: (preview: ItineraryPreview) => void;
  onFinal?: (itinerary: TravelItinerary) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
}

/**
 * SSE-over-POST 스트리밍 클라이언트(React Native).
 * EventSource 는 GET 전용·헤더 제약이 있어 XHR 점진 응답(responseText)으로 SSE 프레임을 파싱한다.
 * preview(검색 직후) → final(LLM 일정) → done 순으로 콜백. 반환값은 취소 함수.
 */
export function streamTravelItinerary(
  params: TravelItineraryRequest,
  handlers: ItineraryStreamHandlers,
  baseUrl: string = BASE_URL,
): () => void {
  const query = (params.query || '').trim();
  if (!query) {
    handlers.onError?.(new Error('질의가 비어 있습니다'));
    return () => {};
  }

  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${baseUrl}/api/llm/voice/answer/stream`);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.setRequestHeader('Accept', 'text/event-stream');

  let processed = 0; // responseText 중 이미 처리한 길이

  const dispatch = (eventName: string, dataStr: string) => {
    let data: any;
    try {
      data = JSON.parse(dataStr);
    } catch {
      return;
    }
    if (eventName === 'preview') {
      handlers.onPreview?.({
        query: typeof data?.query === 'string' ? data.query : query,
        language: typeof data?.language === 'string' ? data.language : params.language || 'ko',
        location_hint: data?.location_hint ?? null,
        city_context: parseCityContext(data?.city_context),
        places: Array.isArray(data?.places)
          ? data.places.map(normalizePlace).filter((p: ItineraryPlace | null): p is ItineraryPlace => p !== null)
          : [],
        candidate_count: isFiniteNumber(data?.candidate_count) ? data.candidate_count : 0,
      });
    } else if (eventName === 'final') {
      handlers.onFinal?.(parseItineraryResponse(data, query, params.language || 'ko'));
    } else if (eventName === 'done') {
      handlers.onDone?.();
    }
  };

  const drain = () => {
    const text = xhr.responseText || '';
    let buf = text.slice(processed);
    // SSE 프레임 경계는 빈 줄(\n\n). 완결 프레임만 처리.
    let sep: number;
    while ((sep = buf.indexOf('\n\n')) !== -1) {
      const frame = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      processed = text.length - buf.length;
      let eventName = 'message';
      const dataLines: string[] = [];
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      }
      if (dataLines.length) dispatch(eventName, dataLines.join('\n'));
    }
  };

  xhr.onreadystatechange = () => {
    if (xhr.readyState === 3 || xhr.readyState === 4) {
      if (xhr.status && xhr.status >= 400) {
        handlers.onError?.(new Error(`HTTP ${xhr.status}`));
        return;
      }
      drain();
    }
  };
  xhr.onerror = () => handlers.onError?.(new Error('스트리밍 연결 오류'));
  xhr.send(JSON.stringify(buildAnswerBody(params)));

  return () => {
    try {
      xhr.abort();
    } catch {
      /* noop */
    }
  };
}

// ── 파일럿 베타 피드백(만족도·NPS·A/B) ─────────────────────────────────────
const AB_VARIANT_KEY = 'worldlinco_tourism_ab_variant_v1';

/** 설치별 안정적 A/B 버킷(50:50). 한 번 정해지면 유지 → variant 별 NPS 비교 가능. */
export async function getAbVariant(): Promise<'A' | 'B'> {
  try {
    const cached = await AsyncStorage.getItem(AB_VARIANT_KEY);
    if (cached === 'A' || cached === 'B') return cached;
    const variant: 'A' | 'B' = Math.random() < 0.5 ? 'A' : 'B';
    await AsyncStorage.setItem(AB_VARIANT_KEY, variant);
    return variant;
  } catch {
    return 'A';
  }
}

export interface ItineraryFeedbackInput {
  query?: string;
  language?: string;
  variant?: 'A' | 'B';
  rating?: 'up' | 'down';
  nps?: number;
  comment?: string;
  days?: number;
  candidate_count?: number;
  cached?: boolean;
  total_ms?: number;
}

/** 일정 결과 평가 전송(엄지/NPS). 실패는 조용히 무시(피드백은 베스트에포트). */
export async function submitItineraryFeedback(
  input: ItineraryFeedbackInput,
  baseUrl: string = BASE_URL,
): Promise<boolean> {
  if (!input.rating && !isFiniteNumber(input.nps)) return false;
  try {
    const res = await fetch(`${baseUrl}/api/tourism-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    return res.ok;
  } catch {
    return false;
  }
}
