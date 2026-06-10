'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';

// ── 추가 타입 ──────────────────────────────────────────────
type PurchaseResult = {
    id: number;
    project_id: number;
    buyer_id: number;
    amount: number;
    status: string;
    payment_method: string;
};

type UserInfo = {
    id: number;
    email: string;
    username?: string;
};

type ProjectSummary = {
    id: number;
    title?: string | null;
    demo_url?: string | null;
};

// ── 인증 헬퍼 ─────────────────────────────────────────────
function setStoredToken(token: string) {
    if (typeof window === 'undefined') return;
    localStorage.setItem('customer_token', token);
}
function clearStoredToken() {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('customer_token');
    localStorage.removeItem('admin_token');
}

async function callLoginApi(email: string, password: string): Promise<string> {
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_API_URL ?? '') : ''}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
        signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `로그인 실패 (HTTP ${res.status})`);
    }
    const data = await res.json();
    return data.access_token as string;
}

async function callMeApi(apiBase: string, token: string): Promise<UserInfo> {
    const res = await fetch(`${apiBase}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(8_000),
    });
    if (!res.ok) throw new Error('내 정보 조회 실패');
    return res.json();
}

async function callCreatePurchaseApi(apiBase: string, projectId: number, amount: number): Promise<PurchaseResult> {
    const token = typeof window !== 'undefined' ? (localStorage.getItem('customer_token') || localStorage.getItem('admin_token') || '') : '';
    if (!token) throw new Error('결제는 로그인 후 사용할 수 있습니다.');
    const res = await fetch(`${apiBase}/api/marketplace/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ project_id: projectId, amount, payment_method: 'card' }),
        signal: AbortSignal.timeout(10_000),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(result.detail || `구매 생성 실패 HTTP ${res.status}`);
    return result;
}

async function callInitiatePaymentApi(apiBase: string, purchaseId: number): Promise<{ payment_url: string; transaction_id: string }> {
    const token = typeof window !== 'undefined' ? (localStorage.getItem('customer_token') || localStorage.getItem('admin_token') || '') : '';
    if (!token) throw new Error('결제는 로그인 후 사용할 수 있습니다.');
    const res = await fetch(`${apiBase}/api/marketplace/purchase/${purchaseId}/pay`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(10_000),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(result.detail || `결제 초기화 실패 HTTP ${res.status}`);
    return result;
}

function osmEmbedUrl(lat: number, lon: number): string {
    const d = 0.015;
    return `https://www.openstreetmap.org/export/embed.html?bbox=${lon - d},${lat - d},${lon + d},${lat + d}&layer=mapnik&marker=${lat},${lon}`;
}

const LANGS = [
    { label: '한국어', code: 'ko' },
    { label: 'English', code: 'en' },
    { label: '中文(简体)', code: 'zh' },
    { label: '繁體中文', code: 'zh-tw' },
    { label: '日本語', code: 'ja' },
    { label: 'Español', code: 'es' },
    { label: 'Français', code: 'fr' },
    { label: 'Deutsch', code: 'de' },
    { label: 'Português', code: 'pt' },
    { label: 'Русский', code: 'ru' },
    { label: 'العربية', code: 'ar' },
    { label: 'हिन्दी', code: 'hi' },
    { label: 'Italiano', code: 'it' },
    { label: 'Türkçe', code: 'tr' },
    { label: 'Tiếng Việt', code: 'vi' },
    { label: 'ภาษาไทย', code: 'th' },
    { label: 'Indonesia', code: 'id' },
    { label: 'Melayu', code: 'ms' },
    { label: 'Nederlands', code: 'nl' },
    { label: 'Polski', code: 'pl' },
    { label: 'Українська', code: 'uk' },
    { label: 'Svenska', code: 'sv' },
    { label: 'Norsk', code: 'no' },
    { label: 'Dansk', code: 'da' },
] as const;

const CATEGORY_OPTIONS = [
    { label: '전체', value: 'all' },
    { label: '호텔', value: 'hotel' },
    { label: '공항', value: 'airport' },
    { label: '식당', value: 'restaurant' },
    { label: '관광명소', value: 'attraction' },
] as const;

const RADIUS_OPTIONS = [
    { label: '1km', value: 1000 },
    { label: '3km', value: 3000 },
    { label: '5km', value: 5000 },
    { label: '10km', value: 10000 },
    { label: '20km', value: 20000 },
] as const;

type LangCode = (typeof LANGS)[number]['code'];
type SearchCategory = (typeof CATEGORY_OPTIONS)[number]['value'];

/** ISO 3166-1 alpha-2 국가코드 → 대상 언어 자동 매핑 (GPS 기반) */
const COUNTRY_LANG_MAP: Record<string, LangCode> = {
    KR: 'ko',
    US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', SG: 'en',
    CN: 'zh',
    TW: 'zh-tw', HK: 'zh-tw', MO: 'zh-tw',
    JP: 'ja',
    ES: 'es', MX: 'es', AR: 'es', CO: 'es', CL: 'es', PE: 'es', VE: 'es', EC: 'es', BO: 'es',
    FR: 'fr', BE: 'fr', CH: 'fr', LU: 'fr', MC: 'fr',
    DE: 'de', AT: 'de', LI: 'de',
    BR: 'pt', PT: 'pt', AO: 'pt', MZ: 'pt',
    RU: 'ru', BY: 'ru', KZ: 'ru',
    SA: 'ar', AE: 'ar', EG: 'ar', IQ: 'ar', MA: 'ar', DZ: 'ar', TN: 'ar', LY: 'ar', JO: 'ar', KW: 'ar', QA: 'ar', BH: 'ar', OM: 'ar', YE: 'ar',
    IN: 'hi', NP: 'hi',
    IT: 'it', SM: 'it',
    TR: 'tr',
    VN: 'vi',
    TH: 'th',
    ID: 'id',
    MY: 'ms', BN: 'ms',
    NL: 'nl',
    PL: 'pl',
    UA: 'uk',
    SE: 'sv',
    NO: 'no',
    DK: 'da',
};

type NearbyPlace = {
    id: string;
    category: 'hotel' | 'airport' | 'restaurant' | 'attraction';
    category_label: string;
    name: string;
    address: string;
    distance_m: number;
    rating: number;
    price_tier: string;
    booking_supported: boolean;
    phone: string;
    summary: string;
    amenities: string[];
    latitude: number;
    longitude: number;
    google_maps_url: string;
    naver_map_url: string;
    review_query: string;
    maps_reviews_path: string;
};

type MapsReviewItem = {
    title: string;
    snippet: string;
    source?: string | null;
    rating?: number | null;
};

type BookingResponse = {
    confirmation_id: string;
    booking_message: string;
    translated_message: string;
    place_name: string;
    support_phone: string;
    google_maps_url: string;
};

const API_BASE = typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_API_URL ?? '') : '';
const NADO_PROJECT_SEARCH = '나도통역사';
const NADO_APK_FILENAME = 'nadotongryoksa-v1.apk';
let cachedNadoProjectId: number | null = null;

const OFFLINE_DICT: Record<string, string> = {
    '안녕하세요': 'Hello',
    '감사합니다': 'Thank you',
    '도와주세요': 'Please help me',
    '얼마입니까': 'How much is it?',
    '병원이 어디인가요': 'Where is the hospital?',
    '화장실이 어디인가요': 'Where is the restroom?',
};

function getStoredToken(): string {
    if (typeof window === 'undefined') {
        return '';
    }
    return localStorage.getItem('customer_token') || localStorage.getItem('admin_token') || '';
}

async function resolveNadotongryoksaProjectId(apiBase: string): Promise<number> {
    if (cachedNadoProjectId !== null) {
        return cachedNadoProjectId;
    }

    const query = new URLSearchParams({ search: NADO_PROJECT_SEARCH, limit: '12' });
    const response = await fetch(`${apiBase}/api/marketplace/projects?${query.toString()}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(8_000),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(payload.detail || `프로젝트 조회 실패 HTTP ${response.status}`);
    }

    const projects: ProjectSummary[] = Array.isArray(payload.projects) ? payload.projects : [];
    const project = projects.find((item) => String(item.demo_url ?? '').includes(NADO_APK_FILENAME))
        ?? projects.find((item) => String(item.title ?? '').includes(NADO_PROJECT_SEARCH))
        ?? projects[0];
    if (!project?.id) {
        throw new Error('나도통역사 상품을 찾을 수 없습니다.');
    }

    cachedNadoProjectId = Number(project.id);
    return cachedNadoProjectId;
}

function resolveUiLangForTranslation(lang: UiLangCode): string {
    if (lang === 'zh-tw') return 'zh';
    return String(lang).split('-')[0] || 'en';
}

async function callUiTranslateApi(text: string, uiLang: UiLangCode): Promise<string> {
    if (!text.trim() || uiLang === 'ko') return text;
    const toLang = resolveUiLangForTranslation(uiLang);
    const response = await fetch(`${API_BASE}/api/llm/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, from_lang: 'ko', to_lang: toLang }),
        signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) {
        throw new Error(`ui translate http ${response.status}`);
    }
    const payload = await response.json().catch(() => ({}));
    return String(payload.translated ?? payload.result ?? text);
}
async function callTranslateApi(
    text: string,
    from: LangCode,
    to: LangCode,
): Promise<{ translated: string; engine: string; offline: boolean }> {
    try {
        const res = await fetch(`${API_BASE}/api/llm/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, from_lang: from, to_lang: to }),
            signal: AbortSignal.timeout(10_000),
        });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        return {
            translated: data.translated ?? data.result ?? text,
            engine: data.engine ?? 'sorisae',
            offline: false,
        };
    } catch {
        const fallback = from === 'ko' && to === 'en' ? OFFLINE_DICT[text] : undefined;
        return {
            translated: fallback ? `${fallback} (오프라인 폴백)` : `[오프라인] 연결 후 전체 통역 가능\n입력: ${text}`,
            engine: 'offline',
            offline: true,
        };
    }
}

async function callNearbyPlacesApi(params: {
    lat: string;
    lon: string;
    category: SearchCategory;
    radiusM: number;
    targetLang: LangCode;
}): Promise<NearbyPlace[]> {
    const query = new URLSearchParams({
        lat: params.lat,
        lon: params.lon,
        category: params.category,
        radius_m: String(params.radiusM),
        target_lang: params.targetLang,
        limit: '8',
    });
    const response = await fetch(`${API_BASE}/api/marketplace/nadotongryoksa/lbs/nearby?${query.toString()}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) {
        throw new Error(`주변검색 실패: HTTP ${response.status}`);
    }
    const payload = await response.json();
    return Array.isArray(payload.places) ? payload.places : [];
}

async function callMapsReviewsApi(reviewQuery: string): Promise<MapsReviewItem[]> {
    const token = getStoredToken();
    if (!token) {
        throw new Error('리뷰 조회는 로그인 후 사용할 수 있습니다.');
    }
    const params = new URLSearchParams({ q: reviewQuery, limit: '3' });
    const response = await fetch(`${API_BASE}/api/external-search/maps-reviews?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(12_000),
    });
    const payload = await response.json().catch(() => ({ data: [] }));
    if (!response.ok || payload.status === 'error') {
        throw new Error(payload.error?.message || `HTTP ${response.status}`);
    }
    return Array.isArray(payload.data) ? payload.data : [];
}

async function callBookingApi(payload: {
    placeId: string;
    customerName: string;
    checkinDate: string;
    checkoutDate: string;
    guests: number;
    roomCount: number;
    note: string;
    targetLang: LangCode;
}): Promise<BookingResponse> {
    const token = getStoredToken();
    if (!token) {
        throw new Error('예약은 로그인 후 사용할 수 있습니다.');
    }
    const response = await fetch(`${API_BASE}/api/marketplace/nadotongryoksa/lbs/bookings`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            place_id: payload.placeId,
            customer_name: payload.customerName,
            checkin_date: payload.checkinDate,
            checkout_date: payload.checkoutDate,
            guests: payload.guests,
            room_count: payload.roomCount,
            note: payload.note,
            target_lang: payload.targetLang,
        }),
        signal: AbortSignal.timeout(10_000),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(result.detail || `HTTP ${response.status}`);
    }
    return result;
}

function formatDistance(distanceM: number): string {
    return distanceM >= 1000 ? `${(distanceM / 1000).toFixed(1)}km` : `${distanceM}m`;
}

function todayPlus(days: number): string {
    const now = new Date();
    now.setDate(now.getDate() + days);
    return now.toISOString().slice(0, 10);
}

export default function NadoTongryoksaPage() {
    // ── 로그인/내정보 ─────────────────────────────────────
    const [token, setToken] = useState('');
    const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
    const [showLoginModal, setShowLoginModal] = useState(false);
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPw, setLoginPw] = useState('');
    const [loginLoading, setLoginLoading] = useState(false);
    const [loginError, setLoginError] = useState('');
    const [showMyInfo, setShowMyInfo] = useState(false);
    const [myPurchases, setMyPurchases] = useState<{ id: number, amount: number, status: string, payment_method: string, created_at?: string }[] | null>(null);
    const [myPurchasesLoading, setMyPurchasesLoading] = useState(false);

    const [from, setFrom] = useState<LangCode>('ko');
    const [to, setTo] = useState<LangCode>('en');
    const [input, setInput] = useState('');
    const [result, setResult] = useState('');
    const [loading, setLoading] = useState(false);
    const [engine, setEngine] = useState('');
    const [offline, setOffline] = useState(false);
    const [gpsLangLoading, setGpsLangLoading] = useState(false);

    // ── 통역 통화 모드 ────────────────────────────────────────
    const [interCallActive, setInterCallActive] = useState(false);
    const [interCallTurn, setInterCallTurn] = useState<'from' | 'to'>('from');
    const [interCallStatus, setInterCallStatus] = useState('');
    const [interCallLog, setInterCallLog] = useState<Array<{ turn: 'from' | 'to'; text: string; translated: string }>>([]);
    const interCallActiveRef = useRef(false);
    const interRecogRef = useRef<any>(null);
    const fromRef = useRef<LangCode>('ko');
    const toRef = useRef<LangCode>('en');

    const [lat, setLat] = useState('37.5665');
    const [lon, setLon] = useState('126.9780');
    const [nearbyCategory, setNearbyCategory] = useState<SearchCategory>('all');
    const [radiusM, setRadiusM] = useState<number>(5000);
    const [nearbyLoading, setNearbyLoading] = useState(false);
    const [nearbyError, setNearbyError] = useState('');
    const [nearbyPlaces, setNearbyPlaces] = useState<NearbyPlace[]>([]);
    const [reviewLoadingId, setReviewLoadingId] = useState('');
    const [reviewsByPlace, setReviewsByPlace] = useState<Record<string, MapsReviewItem[]>>({});
    const [reviewError, setReviewError] = useState('');
    const [selectedHotelId, setSelectedHotelId] = useState('');
    const [bookingName, setBookingName] = useState('');
    const [checkinDate, setCheckinDate] = useState(todayPlus(1));
    const [checkoutDate, setCheckoutDate] = useState(todayPlus(2));
    const [guests, setGuests] = useState(2);
    const [roomCount, setRoomCount] = useState(1);
    const [bookingNote, setBookingNote] = useState('');
    const [bookingLoading, setBookingLoading] = useState(false);
    const [bookingError, setBookingError] = useState('');
    const [bookingResult, setBookingResult] = useState<BookingResponse | null>(null);

    // ── 지도 레일 ─────────────────────────────────────────
    const [mapPlace, setMapPlace] = useState<NearbyPlace | null>(null);

    // ── 결제 레일 ─────────────────────────────────────────
    const [payLoading, setPayLoading] = useState(false);
    const [payError, setPayError] = useState('');
    const [purchaseResult, setPurchaseResult] = useState<PurchaseResult | null>(null);
    const [payUrl, setPayUrl] = useState('');

    const selectedHotel = nearbyPlaces.find((item) => item.id === selectedHotelId) ?? null;

    // ── 토큰 복원 ─────────────────────────────────────────
    useEffect(() => {
        const stored = typeof window !== 'undefined' ? (localStorage.getItem('customer_token') || localStorage.getItem('admin_token') || '') : '';
        if (!stored) return;
        setToken(stored);
        callMeApi(API_BASE, stored).then(setUserInfo).catch(() => { clearStoredToken(); setToken(''); });
    }, []);

    // ── 로그인 ────────────────────────────────────────────
    const handleLogin = async () => {
        if (!loginEmail.trim() || !loginPw.trim()) { setLoginError('이메일과 비밀번호를 입력하세요.'); return; }
        setLoginLoading(true); setLoginError('');
        try {
            const tk = await callLoginApi(loginEmail.trim(), loginPw);
            setStoredToken(tk); setToken(tk);
            const me = await callMeApi(API_BASE, tk);
            setUserInfo(me); setShowLoginModal(false); setLoginEmail(''); setLoginPw('');
        } catch (e: any) { setLoginError(e?.message || '로그인 실패'); }
        finally { setLoginLoading(false); }
    };
    const handleLogout = () => { clearStoredToken(); setToken(''); setUserInfo(null); setShowMyInfo(false); setMyPurchases(null); };

    const handleShowPurchases = async () => {
        if (myPurchases !== null) { setMyPurchases(null); return; }
        setMyPurchasesLoading(true);
        try {
            const apiBase = typeof window !== 'undefined' ? (window.location.origin) : '';
            const t = typeof window !== 'undefined' ? (localStorage.getItem('customer_token') || localStorage.getItem('admin_token') || '') : '';
            const res = await fetch(`${apiBase}/api/marketplace/purchases`, { headers: { Authorization: `Bearer ${t}` } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            setMyPurchases(Array.isArray(data) ? data : (data.purchases ?? data.items ?? []));
        } catch {
            setMyPurchases([]);
        } finally {
            setMyPurchasesLoading(false);
        }
    };

    // ── 결제 ──────────────────────────────────────────────
    const handlePayment = useCallback(async () => {
        if (!bookingResult || !selectedHotel) { setPayError('예약을 먼저 완료해 주세요.'); return; }
        if (!token) { setShowLoginModal(true); setPayError('결제는 로그인 후 사용할 수 있습니다.'); return; }
        setPayLoading(true); setPayError('');
        try {
            const nights = Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000));
            const amount = nights * roomCount * 80000;
            const projectId = await resolveNadotongryoksaProjectId(API_BASE);
            const purchase = await callCreatePurchaseApi(API_BASE, projectId, amount);
            setPurchaseResult(purchase);
            const payData = await callInitiatePaymentApi(API_BASE, purchase.id);
            setPayUrl(payData.payment_url);
        } catch (e: any) { setPayError(e?.message || '결제 초기화에 실패했습니다.'); }
        finally { setPayLoading(false); }
    }, [bookingResult, selectedHotel, token, checkinDate, checkoutDate, roomCount]);

    const LANG_BCP47: Record<LangCode, string> = {
        ko: 'ko-KR', en: 'en-US', zh: 'zh-CN', 'zh-tw': 'zh-TW', ja: 'ja-JP',
        es: 'es-ES', fr: 'fr-FR', de: 'de-DE', pt: 'pt-BR', ru: 'ru-RU',
        ar: 'ar-SA', hi: 'hi-IN', it: 'it-IT', tr: 'tr-TR', vi: 'vi-VN',
        th: 'th-TH', id: 'id-ID', ms: 'ms-MY', nl: 'nl-NL', pl: 'pl-PL',
        uk: 'uk-UA', sv: 'sv-SE', no: 'nb-NO', da: 'da-DK',
    };

    const handleTranslate = useCallback(async () => {
        if (!input.trim()) {
            return;
        }
        setLoading(true);
        setResult('');
        const data = await callTranslateApi(input.trim(), from, to);
        setResult(data.translated);
        setEngine(data.engine);
        setOffline(data.offline);
        setLoading(false);
    }, [input, from, to]);

    // fromRef / toRef 동기화
    useEffect(() => { fromRef.current = from; }, [from]);
    useEffect(() => { toRef.current = to; }, [to]);

    const handleSwap = () => {
        setFrom(to);
        setTo(from);
        setInput(result);
        setResult(input);
    };

    /** 통역 통화 모드 — 한 쪽이 말하면 번역 후 TTS 재생, 끝나면 반대편 STT 자동 시작 */
    const startInterCallCycle = useCallback((turn: 'from' | 'to') => {
        if (!interCallActiveRef.current) return;
        const listenLang = turn === 'from' ? fromRef.current : toRef.current;
        const translateTo = turn === 'from' ? toRef.current : fromRef.current;
        const listenLabel = LANGS.find((l) => l.code === listenLang)?.label ?? listenLang;
        setInterCallTurn(turn);
        setInterCallStatus(`🎤 ${listenLabel} 로 말하세요...`);

        const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognitionCtor) return;
        const recognizer = new SpeechRecognitionCtor();
        recognizer.lang = LANG_BCP47[listenLang];
        recognizer.interimResults = false;
        interRecogRef.current = recognizer;

        recognizer.onresult = async (event: any) => {
            const spokenText: string = event.results[0][0].transcript;
            if (!interCallActiveRef.current) return;
            setInterCallStatus('🔄 번역 중...');
            try {
                const res = await fetch(`${API_BASE}/api/llm/translate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: spokenText, from_lang: listenLang, to_lang: translateTo }),
                });
                const data = await res.json();
                const translatedText: string = data.translated ?? data.result ?? spokenText;
                setInterCallLog((prev) => [...prev.slice(-19), { turn, text: spokenText, translated: translatedText }]);
                if (!interCallActiveRef.current) return;
                const toLabel = LANGS.find((l) => l.code === translateTo)?.label ?? translateTo;
                setInterCallStatus(`🔊 ${toLabel} 로 읽는 중...`);
                const utter = new SpeechSynthesisUtterance(translatedText);
                utter.lang = LANG_BCP47[translateTo];
                utter.rate = 0.9;
                utter.onend = () => {
                    if (interCallActiveRef.current) startInterCallCycle(turn === 'from' ? 'to' : 'from');
                };
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utter);
            } catch {
                if (interCallActiveRef.current) setTimeout(() => startInterCallCycle(turn), 1500);
            }
        };
        recognizer.onerror = () => {
            if (interCallActiveRef.current) setTimeout(() => startInterCallCycle(turn), 1500);
        };
        recognizer.start();
    }, []);

    const handleInterCallToggle = useCallback(() => {
        if (interCallActiveRef.current) {
            interCallActiveRef.current = false;
            setInterCallActive(false);
            setInterCallStatus('');
            try { interRecogRef.current?.stop(); } catch {}
            interRecogRef.current = null;
            window.speechSynthesis?.cancel();
        } else {
            const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            if (!SpeechRecognitionCtor) {
                alert('통역 통화는 Chrome 브라우저(데스크톱/Android)에서 지원됩니다.');
                return;
            }
            setInterCallLog([]);
            interCallActiveRef.current = true;
            setInterCallActive(true);
            startInterCallCycle('from');
        }
    }, [startInterCallCycle]);

    /** GPS 위치 → 국가 → 번역 대상 언어 자동 설정 */
    const handleDetectLangByGPS = useCallback(async () => {
        if (typeof window === 'undefined' || !navigator.geolocation) {
            alert('이 브라우저에서는 위치 정보를 사용할 수 없습니다.');
            return;
        }
        setGpsLangLoading(true);
        try {
            const position = await new Promise<GeolocationPosition>((resolve, reject) =>
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 8000,
                    maximumAge: 60000,
                })
            );
            const { latitude, longitude } = position.coords;
            setLat(latitude.toFixed(6));
            setLon(longitude.toFixed(6));

            const res = await fetch(
                `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`,
                { headers: { 'Accept-Language': 'en' } }
            );
            if (!res.ok) throw new Error('역지오코딩 실패');
            const data = await res.json();
            const countryCode: string = (data.address?.country_code ?? '').toUpperCase();
            const detectedLang = COUNTRY_LANG_MAP[countryCode];
            if (detectedLang) {
                setTo(detectedLang);
            }
        } catch {
            alert('위치 기반 언어 감지에 실패했습니다. 직접 선택해 주세요.');
        } finally {
            setGpsLangLoading(false);
        }
    }, []);

    const handleSpeak = (text: string, lang: LangCode) => {
        if (!text || typeof window === 'undefined' || !window.speechSynthesis) {
            return;
        }
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = LANG_BCP47[lang];
        utter.rate = 0.9;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utter);
    };

    const handleVoiceInput = () => {
        if (typeof window === 'undefined') {
            return;
        }
        const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognitionCtor) {
            alert('이 브라우저는 음성 인식을 지원하지 않습니다.\nChrome을 사용하세요.');
            return;
        }
        const recognizer = new SpeechRecognitionCtor();
        recognizer.lang = LANG_BCP47[from];
        recognizer.interimResults = false;
        recognizer.onresult = (event: any) => {
            const text = event.results[0][0].transcript;
            setInput(text);
        };
        recognizer.start();
    };

    const handleUseCurrentLocation = () => {
        if (typeof window === 'undefined' || !navigator.geolocation) {
            alert('이 브라우저에서는 위치 정보를 사용할 수 없습니다.');
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                setLat(position.coords.latitude.toFixed(6));
                setLon(position.coords.longitude.toFixed(6));
            },
            () => {
                alert('현재 위치를 불러오지 못했습니다. 좌표를 직접 입력하세요.');
            },
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 },
        );
    };

    const handleSearchNearby = useCallback(async () => {
        if (!lat.trim() || !lon.trim()) {
            setNearbyError('위도와 경도를 입력해 주세요.');
            return;
        }
        setNearbyLoading(true);
        setNearbyError('');
        setReviewError('');
        setBookingResult(null);
        try {
            const places = await callNearbyPlacesApi({ lat, lon, category: nearbyCategory, radiusM, targetLang: to });
            setNearbyPlaces(places);
            if (!places.length) {
                setNearbyError('현재 반경에서 찾은 장소가 없습니다. 반경을 넓혀 보세요.');
            }
        } catch (error: any) {
            setNearbyPlaces([]);
            setNearbyError(error?.message || '주변검색 중 오류가 발생했습니다.');
        } finally {
            setNearbyLoading(false);
        }
    }, [lat, lon, nearbyCategory, radiusM, to]);

    const handleLoadReviews = useCallback(async (place: NearbyPlace) => {
        setReviewLoadingId(place.id);
        setReviewError('');
        try {
            const reviews = await callMapsReviewsApi(place.review_query);
            setReviewsByPlace((prev) => ({ ...prev, [place.id]: reviews }));
        } catch (error: any) {
            setReviewError(error?.message || '리뷰를 불러오지 못했습니다.');
        } finally {
            setReviewLoadingId('');
        }
    }, []);

    const handleReserveHotel = useCallback(async () => {
        if (!selectedHotel) {
            setBookingError('예약할 호텔을 먼저 선택하세요.');
            return;
        }
        if (!bookingName.trim() || !checkinDate || !checkoutDate) {
            setBookingError('예약자명과 체크인/체크아웃 날짜를 입력하세요.');
            return;
        }
        setBookingLoading(true);
        setBookingError('');
        setBookingResult(null);
        try {
            const payload = await callBookingApi({
                placeId: selectedHotel.id,
                customerName: bookingName.trim(),
                checkinDate,
                checkoutDate,
                guests,
                roomCount,
                note: bookingNote,
                targetLang: to,
            });
            setBookingResult(payload);
        } catch (error: any) {
            setBookingError(error?.message || '예약 요청에 실패했습니다.');
        } finally {
            setBookingLoading(false);
        }
    }, [selectedHotel, bookingName, checkinDate, checkoutDate, guests, roomCount, bookingNote, to]);

    const handleApkDownload = async () => {
        const token = getStoredToken();
        if (!token) {
            alert('로그인 후 다운로드할 수 있습니다.\n마켓플레이스 상단의 로그인 버튼을 이용하세요.');
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/api/marketplace/apk/test-token/${NADO_APK_FILENAME}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'unknown' }));
                alert(`다운로드 링크 발급 실패: ${err.detail ?? res.status}`);
                return;
            }
            const { download_url } = await res.json();
            window.location.href = download_url;
        } catch {
            alert('네트워크 오류로 다운로드 링크를 가져올 수 없습니다.');
        }
    };

    return (
        <main
            style={{
                minHeight: '100vh',
                background: 'linear-gradient(180deg, #07111f 0%, #0b0f16 40%, #101725 100%)',
                color: '#e6edf3',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                padding: '0',
            }}
        >
            {/* ── 로그인 모달 ── */}
            {showLoginModal && (
                <div style={{ position: 'fixed', inset: 0, background: '#000c', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    onClick={(e) => { if (e.target === e.currentTarget) setShowLoginModal(false); }}>
                    <div style={{ background: '#151b23', border: '1px solid #21262d', borderRadius: 16, padding: 24, width: 360, maxWidth: '92vw' }}>
                        <h2 style={{ margin: '0 0 16px', fontSize: 18, color: '#58c9ff' }}>🔐 로그인</h2>
                        <input type="email" placeholder="이메일" value={loginEmail}
                            onChange={(e) => setLoginEmail(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                            style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px', width: '100%', boxSizing: 'border-box', marginBottom: 10 }} />
                        <input type="password" placeholder="비밀번호" value={loginPw}
                            onChange={(e) => setLoginPw(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                            style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px', width: '100%', boxSizing: 'border-box', marginBottom: 14 }} />
                        {loginError && <div style={{ color: '#ffb4b4', fontSize: 13, marginBottom: 10 }}>{loginError}</div>}
                        <div style={{ display: 'flex', gap: 10 }}>
                            <button onClick={handleLogin} disabled={loginLoading}
                                style={{ flex: 2, background: '#2a7cff', border: 'none', color: '#fff', borderRadius: 10, padding: '11px 0', fontWeight: 800, cursor: loginLoading ? 'not-allowed' : 'pointer' }}>
                                {loginLoading ? '로그인 중...' : '로그인'}
                            </button>
                            <button onClick={() => setShowLoginModal(false)}
                                style={{ flex: 1, background: '#151b23', border: '1px solid #21262d', color: '#8b949e', borderRadius: 10, padding: '11px 0', cursor: 'pointer', fontWeight: 600 }}>닫기</button>
                        </div>
                        <p style={{ margin: '10px 0 0', fontSize: 12, color: '#6b7280', textAlign: 'center' }}>
                            계정이 없으면 <a href="/marketplace/auth/register" style={{ color: '#79c0ff' }}>회원가입</a>
                        </p>
                    </div>
                </div>
            )}

            {/* ── 상단 헤더 (sticky) ── */}
            <div
                style={{
                    background: 'rgba(21, 27, 35, 0.96)',
                    backdropFilter: 'blur(10px)',
                    borderBottom: '1px solid #21262d',
                    padding: '14px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    position: 'sticky',
                    top: 0,
                    zIndex: 50,
                }}
            >
                <span style={{ fontSize: 28 }}>📱</span>
                <div style={{ flex: 1 }}>
                    <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#58c9ff' }}>나도통역사</h1>
                    <p style={{ margin: 0, fontSize: 13, color: '#8b949e' }}>신세계소리새 AI · 통번역 · 지도 · 예약 · 결제</p>
                </div>
                {engine && (
                    <span style={{ background: '#1a2535', border: '1px solid #21262d', borderRadius: 20, padding: '3px 10px', fontSize: 12, color: offline ? '#f0b050' : '#31c45d' }}>
                        {offline ? '🔴 오프라인' : `🟢 ${engine}`}
                    </span>
                )}
                {/* 로그인/내정보 레일 */}
                {userInfo ? (
                    <div style={{ position: 'relative' }}>
                        <button onClick={() => setShowMyInfo((v) => !v)}
                            style={{ background: '#153020', border: '1px solid #2d6b43', color: '#effff3', borderRadius: 10, padding: '8px 14px', fontWeight: 700, cursor: 'pointer', fontSize: 13 }}>
                            👤 {userInfo.username || userInfo.email.split('@')[0]}
                        </button>
                        {showMyInfo && (
                            <div style={{ position: 'absolute', right: 0, top: 44, background: '#151b23', border: '1px solid #21262d', borderRadius: 14, padding: 16, minWidth: 220, zIndex: 100, boxShadow: '0 8px 32px #000a' }}>
                                <div style={{ fontWeight: 700, color: '#f8fbff', marginBottom: 6 }}>내 정보</div>
                                <div style={{ fontSize: 13, color: '#8b949e', marginBottom: 4 }}>이메일: {userInfo.email}</div>
                                <div style={{ fontSize: 13, color: '#8b949e', marginBottom: 12 }}>ID: {userInfo.id}</div>
                                <button onClick={handleShowPurchases} style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', color: '#79c0ff', fontSize: 13, marginBottom: 4, cursor: 'pointer', padding: 0 }}>
                                    {myPurchasesLoading ? '⏳ 불러오는 중...' : myPurchases !== null ? '📋 내역 닫기' : '📋 구매/예약 내역'}
                                </button>
                                {myPurchases !== null && (
                                    <div style={{ maxHeight: 160, overflowY: 'auto', marginBottom: 8, background: '#0d1117', borderRadius: 8, padding: '8px 10px' }}>
                                        {myPurchases.length === 0 ? (
                                            <div style={{ fontSize: 12, color: '#8b949e' }}>구매 내역이 없습니다.</div>
                                        ) : myPurchases.map((p) => (
                                            <div key={p.id} style={{ fontSize: 12, color: '#c9d1d9', borderBottom: '1px solid #21262d', paddingBottom: 6, marginBottom: 6 }}>
                                                <span style={{ color: '#79c0ff' }}>#{p.id}</span> · {p.amount?.toLocaleString()}원 · <span style={{ color: p.status === 'completed' ? '#3fb950' : '#f0883e' }}>{p.status}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <button onClick={handleLogout} style={{ width: '100%', background: '#2a1616', border: '1px solid #5e2727', color: '#ffb4b4', borderRadius: 8, padding: '8px 0', fontWeight: 700, cursor: 'pointer' }}>로그아웃</button>
                            </div>
                        )}
                    </div>
                ) : (
                    <button onClick={() => { setShowLoginModal(true); setLoginError(''); }}
                        style={{ background: '#11243d', border: '1px solid #35506c', color: '#79c0ff', borderRadius: 10, padding: '8px 14px', fontWeight: 700, cursor: 'pointer', fontSize: 13 }}>
                        🔐 로그인
                    </button>
                )}
            </div>

            <div style={{ maxWidth: 960, margin: '0 auto', padding: '20px 16px 40px' }}>
                <div
                    style={{
                        display: 'grid',
                        gap: 18,
                        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                        alignItems: 'start',
                    }}
                >
                    <section style={{ background: '#151b23', border: '1px solid #21262d', borderRadius: 16, padding: 18 }}>
                        <div style={{ marginBottom: 12 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                                <span style={{ fontSize: 12, color: '#8b949e' }}>원본 언어</span>
                                <button
                                    onClick={handleDetectLangByGPS}
                                    disabled={gpsLangLoading}
                                    title="현재 위치로 번역 언어 자동 감지"
                                    style={{
                                        marginLeft: 'auto',
                                        background: '#0e1e30',
                                        border: '1px solid #35506c',
                                        color: gpsLangLoading ? '#6b7280' : '#79c0ff',
                                        borderRadius: 8,
                                        padding: '4px 10px',
                                        fontSize: 12,
                                        fontWeight: 700,
                                        cursor: gpsLangLoading ? 'not-allowed' : 'pointer',
                                        whiteSpace: 'nowrap',
                                    }}
                                >
                                    {gpsLangLoading ? '⏳ 감지 중...' : '🌐 GPS 언어 감지'}
                                </button>
                            </div>
                            <select
                                value={from}
                                onChange={(e) => setFrom(e.target.value as LangCode)}
                                style={{
                                    width: '100%',
                                    background: '#0f1623',
                                    border: '1px solid #21262d',
                                    color: '#f8fbff',
                                    borderRadius: 10,
                                    padding: '10px 12px',
                                    fontSize: 14,
                                    cursor: 'pointer',
                                    appearance: 'auto',
                                }}
                            >
                                {LANGS.map((lang) => (
                                    <option key={lang.code} value={lang.code}>{lang.label}</option>
                                ))}
                            </select>
                        </div>

                        <div style={{ background: '#0f1623', border: '1px solid #21262d', borderRadius: 12, padding: 14, marginBottom: 10 }}>
                            <textarea
                                value={input}
                                onChange={(event) => setInput(event.target.value)}
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                                        handleTranslate();
                                    }
                                }}
                                placeholder="번역할 텍스트를 입력하세요 (Ctrl+Enter로 번역)"
                                rows={5}
                                style={{
                                    width: '100%',
                                    background: 'transparent',
                                    border: 'none',
                                    outline: 'none',
                                    color: '#e6edf3',
                                    fontSize: 16,
                                    resize: 'vertical',
                                    fontFamily: 'inherit',
                                }}
                            />
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
                                <button onClick={handleVoiceInput} title="음성 입력" style={{ background: 'none', border: '1px solid #21262d', borderRadius: 8, padding: '4px 10px', cursor: 'pointer', fontSize: 16 }}>🎤</button>
                                <button onClick={() => handleSpeak(input, from)} title="읽기" style={{ background: 'none', border: '1px solid #21262d', borderRadius: 8, padding: '4px 10px', cursor: 'pointer', fontSize: 16 }}>🔊</button>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
                            <button onClick={handleSwap} style={{ flex: 1, background: '#151b23', border: '1px solid #21262d', borderRadius: 10, padding: '12px 0', color: '#8b949e', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>⇄ 언어 스왑</button>
                            <button onClick={handleTranslate} disabled={loading || !input.trim()} style={{ flex: 2, background: loading ? '#1a3a1a' : '#31c45d', border: 'none', borderRadius: 10, padding: '12px 0', color: '#fff', fontSize: 16, fontWeight: 800, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading || !input.trim() ? 0.7 : 1 }}>{loading ? '번역 중...' : '번역'}</button>
                        </div>

                        <div style={{ marginBottom: 8 }}>
                            <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 6 }}>번역 언어</div>
                            <select
                                value={to}
                                onChange={(e) => setTo(e.target.value as LangCode)}
                                style={{
                                    width: '100%',
                                    background: '#0f1623',
                                    border: '1px solid #31c45d55',
                                    color: '#f8fbff',
                                    borderRadius: 10,
                                    padding: '10px 12px',
                                    fontSize: 14,
                                    cursor: 'pointer',
                                    appearance: 'auto',
                                }}
                            >
                                {LANGS.map((lang) => (
                                    <option key={lang.code} value={lang.code}>{lang.label}</option>
                                ))}
                            </select>
                        </div>

                        <div style={{ background: '#0f1623', border: `1px solid ${result ? '#31c45d33' : '#21262d'}`, borderRadius: 12, padding: 14, minHeight: 120, marginTop: 8 }}>
                            {loading ? (
                                <div style={{ color: '#8b949e', fontSize: 14 }}>신세계소리새 AI 번역 중...</div>
                            ) : result ? (
                                <>
                                    <p style={{ margin: 0, fontSize: 16, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{result}</p>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
                                        <button onClick={() => handleSpeak(result, to)} title="읽기" style={{ background: 'none', border: '1px solid #21262d', borderRadius: 8, padding: '4px 10px', cursor: 'pointer', fontSize: 16 }}>🔊</button>
                                        <button onClick={() => navigator.clipboard?.writeText(result)} title="복사" style={{ background: 'none', border: '1px solid #21262d', borderRadius: 8, padding: '4px 10px', cursor: 'pointer', fontSize: 16 }}>📋</button>
                                    </div>
                                </>
                            ) : (
                                <p style={{ margin: 0, color: '#8b949e', fontSize: 14 }}>번역 결과가 여기에 표시됩니다</p>
                            )}
                        </div>

                        {offline && (
                            <div style={{ background: '#2a1a00', border: '1px solid #5a3a00', borderRadius: 8, padding: '10px 14px', marginTop: 10, fontSize: 13, color: '#f0b050' }}>
                                📡 오프라인 모드 — 백엔드 연결 후 신세계소리새 전체 통역 엔진 사용 가능
                            </div>
                        )}

                        {/* ── 통역 통화 모드 ── */}
                        <div style={{ marginTop: 16, borderTop: '1px solid #21262d', paddingTop: 14 }}>
                            <button
                                onClick={handleInterCallToggle}
                                style={{
                                    width: '100%',
                                    borderRadius: 12,
                                    border: 'none',
                                    background: interCallActive ? '#5e1a1a' : '#0d3b1e',
                                    color: interCallActive ? '#ffb4b4' : '#3fb950',
                                    padding: '14px 0',
                                    fontSize: 16,
                                    fontWeight: 800,
                                    cursor: 'pointer',
                                    letterSpacing: 0.5,
                                    boxShadow: interCallActive ? '0 0 0 2px #ff444444' : '0 0 0 2px #31c45d44',
                                }}
                            >
                                {interCallActive ? '📵 통역 통화 종료' : '📞 통역 통화 시작'}
                            </button>

                            {interCallActive && (
                                <div style={{ marginTop: 12, background: '#0a1a0a', border: '1px solid #2d6b43', borderRadius: 14, padding: 14 }}>
                                    {/* 통화 상태 헤더 */}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                                        <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#31c45d', boxShadow: '0 0 6px #31c45d' }} />
                                        <span style={{ fontSize: 13, fontWeight: 700, color: '#3fb950' }}>통화 중</span>
                                        <span style={{ fontSize: 12, color: '#8b949e', marginLeft: 'auto' }}>
                                            {LANGS.find((l) => l.code === fromRef.current)?.label} ⇄ {LANGS.find((l) => l.code === toRef.current)?.label}
                                        </span>
                                    </div>

                                    {/* 현재 상태 */}
                                    <div style={{
                                        background: interCallTurn === 'from' ? '#0d2a4a' : '#1a2a0d',
                                        border: `1px solid ${interCallTurn === 'from' ? '#2a7cff44' : '#31c45d44'}`,
                                        borderRadius: 10,
                                        padding: '10px 14px',
                                        fontSize: 14,
                                        color: interCallTurn === 'from' ? '#79c0ff' : '#3fb950',
                                        fontWeight: 600,
                                        marginBottom: 10,
                                        minHeight: 40,
                                    }}>
                                        {interCallStatus || '준비 중...'}
                                    </div>

                                    {/* 대화 로그 */}
                                    {interCallLog.length > 0 && (
                                        <div style={{ display: 'grid', gap: 8, maxHeight: 260, overflowY: 'auto' }}>
                                            {[...interCallLog].reverse().map((entry, idx) => (
                                                <div
                                                    key={idx}
                                                    style={{
                                                        background: entry.turn === 'from' ? '#0d2240' : '#102a12',
                                                        border: `1px solid ${entry.turn === 'from' ? '#1f4a7a' : '#2d6b43'}`,
                                                        borderRadius: 10,
                                                        padding: '10px 12px',
                                                    }}
                                                >
                                                    <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 4 }}>
                                                        {entry.turn === 'from'
                                                            ? LANGS.find((l) => l.code === fromRef.current)?.label
                                                            : LANGS.find((l) => l.code === toRef.current)?.label}
                                                    </div>
                                                    <div style={{ fontSize: 14, color: '#e6edf3', marginBottom: 4 }}>{entry.text}</div>
                                                    <div style={{ fontSize: 13, color: entry.turn === 'from' ? '#79c0ff' : '#3fb950' }}>→ {entry.translated}</div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </section>

                    <section style={{ background: '#151b23', border: '1px solid #21262d', borderRadius: 16, padding: 18 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                            <div>
                                <h2 style={{ margin: 0, fontSize: 18, color: '#f8fbff' }}>📍 주변 검색</h2>
                                <p style={{ margin: '4px 0 0', fontSize: 13, color: '#8b949e' }}>호텔 · 공항 · 식당 · 관광명소를 현재 좌표 기준으로 찾습니다.</p>
                            </div>
                            <button onClick={handleUseCurrentLocation} style={{ border: '1px solid #35506c', background: '#08111d', color: '#79c0ff', borderRadius: 10, padding: '8px 12px', fontWeight: 700, cursor: 'pointer' }}>현재 위치</button>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10, marginBottom: 10 }}>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: '#8b949e' }}>
                                <span>위도</span>
                                <input value={lat} onChange={(event) => setLat(event.target.value)} style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: '#8b949e' }}>
                                <span>경도</span>
                                <input value={lon} onChange={(event) => setLon(event.target.value)} style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                            </label>
                        </div>

                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                            {CATEGORY_OPTIONS.map((option) => (
                                <button key={option.value} onClick={() => setNearbyCategory(option.value)} style={{ borderRadius: 20, border: '1px solid', borderColor: nearbyCategory === option.value ? '#79c0ff' : '#21262d', background: nearbyCategory === option.value ? '#11243d' : '#0f1623', color: nearbyCategory === option.value ? '#f8fbff' : '#8b949e', padding: '6px 14px', cursor: 'pointer', fontWeight: 700 }}>{option.label}</button>
                            ))}
                        </div>

                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                            {RADIUS_OPTIONS.map((option) => (
                                <button key={option.value} onClick={() => setRadiusM(option.value)} style={{ borderRadius: 20, border: '1px solid', borderColor: radiusM === option.value ? '#31c45d' : '#21262d', background: radiusM === option.value ? '#153020' : '#0f1623', color: radiusM === option.value ? '#effff3' : '#8b949e', padding: '6px 14px', cursor: 'pointer', fontWeight: 700 }}>{option.label}</button>
                            ))}
                        </div>

                        <button onClick={handleSearchNearby} disabled={nearbyLoading} style={{ width: '100%', borderRadius: 12, border: 'none', background: nearbyLoading ? '#26466b' : '#2a7cff', color: '#fff', padding: '12px 14px', fontWeight: 800, cursor: nearbyLoading ? 'not-allowed' : 'pointer', marginBottom: 10 }}>{nearbyLoading ? '주변 검색 중...' : '주변 장소 찾기'}</button>

                        {nearbyError && <div style={{ background: '#2a1616', border: '1px solid #5e2727', color: '#ffb4b4', borderRadius: 10, padding: '10px 12px', fontSize: 13, marginBottom: 10 }}>{nearbyError}</div>}
                        {reviewError && <div style={{ background: '#251d10', border: '1px solid #5a4624', color: '#f5cb7f', borderRadius: 10, padding: '10px 12px', fontSize: 13, marginBottom: 10 }}>{reviewError}</div>}

                        <div style={{ display: 'grid', gap: 12 }}>
                            {nearbyPlaces.map((place) => (
                                <div key={place.id} style={{ background: '#0f1623', border: selectedHotelId === place.id ? '1px solid #31c45d' : '1px solid #21262d', borderRadius: 14, padding: 14 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                                        <div>
                                            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                                                <strong style={{ fontSize: 16 }}>{place.name}</strong>
                                                <span style={{ fontSize: 12, color: '#79c0ff' }}>{place.category_label}</span>
                                                <span style={{ fontSize: 12, color: '#8b949e' }}>{formatDistance(place.distance_m)}</span>
                                            </div>
                                            <div style={{ fontSize: 13, color: '#8b949e', marginTop: 4 }}>{place.address}</div>
                                        </div>
                                        <div style={{ textAlign: 'right', minWidth: 88 }}>
                                            <div style={{ fontWeight: 800, color: '#ffd166' }}>★ {place.rating.toFixed(1)}</div>
                                            <div style={{ fontSize: 12, color: '#8b949e' }}>{place.price_tier}</div>
                                        </div>
                                    </div>

                                    <p style={{ margin: '10px 0 8px', fontSize: 14, lineHeight: 1.6, color: '#dbe7f5' }}>{place.summary}</p>
                                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                                        {place.amenities.map((amenity) => (
                                            <span key={`${place.id}-${amenity}`} style={{ fontSize: 12, color: '#9fb3c8', border: '1px solid #24364b', background: '#0a1320', borderRadius: 999, padding: '4px 10px' }}>{amenity}</span>
                                        ))}
                                    </div>

                                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                        <button onClick={() => setMapPlace(place)} style={{ background: '#1e3a2a', border: '1px solid #2d6b43', color: '#effff3', padding: '8px 12px', borderRadius: 10, cursor: 'pointer', fontWeight: 700 }}>🗺️ 지도</button>
                                        <a href={place.google_maps_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', background: '#2a7cff', color: '#fff', padding: '8px 12px', borderRadius: 10, fontWeight: 700 }}>Google Maps</a>
                                        <a href={place.naver_map_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', background: '#00c73c', color: '#fff', padding: '8px 12px', borderRadius: 10, fontWeight: 700 }}>Naver 지도</a>
                                        <button onClick={() => handleLoadReviews(place)} disabled={reviewLoadingId === place.id} style={{ background: '#151b23', border: '1px solid #35506c', color: '#dbe7f5', padding: '8px 12px', borderRadius: 10, cursor: 'pointer', fontWeight: 700 }}>{reviewLoadingId === place.id ? '리뷰 조회 중...' : 'Google 리뷰'}</button>
                                        {place.booking_supported && (
                                            <button onClick={() => { setSelectedHotelId(place.id); setBookingResult(null); setBookingError(''); setPurchaseResult(null); setPayUrl(''); setPayError(''); }} style={{ background: selectedHotelId === place.id ? '#31c45d' : '#18291e', border: '1px solid #2d6b43', color: '#effff3', padding: '8px 12px', borderRadius: 10, cursor: 'pointer', fontWeight: 700 }}>호텔 예약</button>
                                        )}
                                    </div>

                                    {reviewsByPlace[place.id]?.length ? (
                                        <div style={{ marginTop: 12, borderTop: '1px solid #1e2a39', paddingTop: 12, display: 'grid', gap: 8 }}>
                                            {reviewsByPlace[place.id].map((review, index) => (
                                                <div key={`${place.id}-review-${index}`} style={{ background: '#0b1018', border: '1px solid #1f2e40', borderRadius: 10, padding: 10 }}>
                                                    <div style={{ fontSize: 13, fontWeight: 700, color: '#dbe7f5' }}>{review.title || '리뷰'}</div>
                                                    <div style={{ fontSize: 13, color: '#8b949e', marginTop: 4, lineHeight: 1.5 }}>{review.snippet || '요약이 없습니다.'}</div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : null}
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                <section style={{ background: '#151b23', border: '1px solid #21262d', borderRadius: 16, padding: 18, marginTop: 18 }}>
                    <div style={{ display: 'grid', gap: 18, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                        <div>
                            <h2 style={{ margin: '0 0 8px', fontSize: 18, color: '#f8fbff' }}>🏨 호텔 예약 패널</h2>
                            <p style={{ margin: '0 0 12px', fontSize: 13, color: '#8b949e' }}>주변검색 결과에서 호텔을 선택하면 예약 요청을 보낼 수 있습니다.</p>
                            <div style={{ background: '#0f1623', border: '1px solid #21262d', borderRadius: 12, padding: 14, minHeight: 124 }}>
                                {selectedHotel ? (
                                    <>
                                        <div style={{ fontWeight: 800, fontSize: 16, color: '#effff3' }}>{selectedHotel.name}</div>
                                        <div style={{ fontSize: 13, color: '#8b949e', marginTop: 4 }}>{selectedHotel.address}</div>
                                        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                            <span style={{ fontSize: 12, color: '#79c0ff' }}>{selectedHotel.price_tier}</span>
                                            <span style={{ fontSize: 12, color: '#ffd166' }}>★ {selectedHotel.rating.toFixed(1)}</span>
                                            <span style={{ fontSize: 12, color: '#8b949e' }}>{formatDistance(selectedHotel.distance_m)}</span>
                                        </div>
                                        <button onClick={() => setMapPlace(selectedHotel)} style={{ marginTop: 10, background: '#1e3a2a', border: '1px solid #2d6b43', color: '#effff3', padding: '6px 12px', borderRadius: 8, cursor: 'pointer', fontWeight: 700, fontSize: 13 }}>🗺️ 지도에서 보기</button>
                                    </>
                                ) : (
                                    <div style={{ color: '#8b949e', fontSize: 14 }}>주변검색 결과에서 예약 가능한 호텔을 선택하세요.</div>
                                )}
                            </div>
                        </div>

                        <div style={{ display: 'grid', gap: 10 }}>
                            <input value={bookingName} onChange={(event) => setBookingName(event.target.value)} placeholder="예약자명" style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                                <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: '#8b949e' }}>
                                    <span>체크인</span>
                                    <input type="date" value={checkinDate} onChange={(event) => setCheckinDate(event.target.value)} style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                                </label>
                                <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: '#8b949e' }}>
                                    <span>체크아웃</span>
                                    <input type="date" value={checkoutDate} onChange={(event) => setCheckoutDate(event.target.value)} style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                                </label>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                                <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: '#8b949e' }}>
                                    <span>인원</span>
                                    <input type="number" min={1} max={8} value={guests} onChange={(event) => setGuests(Number(event.target.value) || 1)} style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                                </label>
                                <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: '#8b949e' }}>
                                    <span>객실 수</span>
                                    <input type="number" min={1} max={4} value={roomCount} onChange={(event) => setRoomCount(Number(event.target.value) || 1)} style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px' }} />
                                </label>
                            </div>
                            <textarea value={bookingNote} onChange={(event) => setBookingNote(event.target.value)} rows={3} placeholder="추가 요청사항 (예: 금연실, 늦은 체크인)" style={{ borderRadius: 10, border: '1px solid #21262d', background: '#0f1623', color: '#f8fbff', padding: '10px 12px', resize: 'vertical', fontFamily: 'inherit' }} />
                            <button onClick={handleReserveHotel} disabled={bookingLoading || !selectedHotel} style={{ borderRadius: 12, border: 'none', background: bookingLoading || !selectedHotel ? '#294034' : '#31c45d', color: '#fff', padding: '12px 14px', fontWeight: 800, cursor: bookingLoading || !selectedHotel ? 'not-allowed' : 'pointer' }}>{bookingLoading ? '예약 요청 중...' : '예약 요청 보내기'}</button>
                            {bookingError && <div style={{ background: '#2a1616', border: '1px solid #5e2727', color: '#ffb4b4', borderRadius: 10, padding: '10px 12px', fontSize: 13 }}>{bookingError}</div>}
                            {bookingResult && (
                                <div style={{ background: '#102416', border: '1px solid #215c36', color: '#dff7e7', borderRadius: 12, padding: 14 }}>
                                    <div style={{ fontWeight: 800 }}>예약 확인번호 {bookingResult.confirmation_id}</div>
                                    <div style={{ marginTop: 6, fontSize: 13, lineHeight: 1.6 }}>{bookingResult.booking_message}</div>
                                    <div style={{ marginTop: 6, fontSize: 13, lineHeight: 1.6, color: '#9be8b3' }}>{bookingResult.translated_message}</div>
                                    <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                        <a href={bookingResult.google_maps_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', background: '#2a7cff', color: '#fff', padding: '8px 12px', borderRadius: 10, fontWeight: 700 }}>호텔 위치 열기</a>
                                        <span style={{ fontSize: 12, color: '#b9dccc', alignSelf: 'center' }}>지원 전화 {bookingResult.support_phone}</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* ── 지도 레일 (OpenStreetMap) ── */}
                {mapPlace && (
                    <section style={{ background: '#151b23', border: '1px solid #2d6b43', borderRadius: 16, padding: 18, marginTop: 18 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                            <div>
                                <h2 style={{ margin: 0, fontSize: 18, color: '#effff3' }}>🗺️ {mapPlace.name}</h2>
                                <p style={{ margin: '4px 0 0', fontSize: 13, color: '#8b949e' }}>{mapPlace.address}</p>
                            </div>
                            <button onClick={() => setMapPlace(null)} style={{ background: 'none', border: '1px solid #21262d', color: '#8b949e', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontSize: 14 }}>✕ 닫기</button>
                        </div>
                        <iframe
                            src={osmEmbedUrl(mapPlace.latitude ?? Number(lat), mapPlace.longitude ?? Number(lon))}
                            width="100%"
                            height="360"
                            style={{ border: 'none', borderRadius: 12 }}
                            title={`지도: ${mapPlace.name}`}
                            loading="lazy"
                        />
                        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            <a href={mapPlace.google_maps_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', background: '#2a7cff', color: '#fff', padding: '8px 14px', borderRadius: 10, fontWeight: 700, fontSize: 13 }}>🌐 Google Maps</a>
                            <a href={mapPlace.naver_map_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', background: '#00c73c', color: '#fff', padding: '8px 14px', borderRadius: 10, fontWeight: 700, fontSize: 13 }}>🗺️ Naver 지도</a>
                            <a
                                href={`https://www.openstreetmap.org/?mlat=${encodeURIComponent(String(mapPlace.latitude ?? Number(lat)))}&mlon=${encodeURIComponent(String(mapPlace.longitude ?? Number(lon)))}#map=15/${encodeURIComponent(String(mapPlace.latitude ?? Number(lat)))}/${encodeURIComponent(String(mapPlace.longitude ?? Number(lon)))}`}
                                target="_blank"
                                rel="noreferrer"
                                style={{ textDecoration: 'none', background: '#1e3a2a', border: '1px solid #2d6b43', color: '#effff3', padding: '8px 14px', borderRadius: 10, fontWeight: 700, fontSize: 13 }}
                            >
                                🌍 OpenStreetMap
                            </a>
                        </div>
                    </section>
                )}

                {/* ── 결제 레일 ── */}
                {bookingResult && (
                    <section style={{ background: '#151b23', border: '1px solid #21262d', borderRadius: 16, padding: 18, marginTop: 18 }}>
                        <h2 style={{ margin: '0 0 12px', fontSize: 18, color: '#f8fbff' }}>💳 결제</h2>
                        <div style={{ background: '#102416', border: '1px solid #215c36', borderRadius: 12, padding: 14, marginBottom: 14 }}>
                            <div style={{ fontWeight: 800, color: '#9be8b3', marginBottom: 6 }}>예약 확인 완료 · {bookingResult.confirmation_id}</div>
                            <div style={{ fontSize: 13, color: '#8b949e', marginBottom: 4 }}>
                                체크인 {checkinDate} → 체크아웃 {checkoutDate} · {roomCount}객실 ·
                                {' '}{Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000))}박
                            </div>
                            <div style={{ fontSize: 16, fontWeight: 800, color: '#ffd166' }}>
                                결제 예정 금액: {(Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000)) * roomCount * 80000).toLocaleString('ko-KR')}원
                            </div>
                        </div>
                        {payError && <div style={{ background: '#2a1616', border: '1px solid #5e2727', color: '#ffb4b4', borderRadius: 10, padding: '10px 12px', fontSize: 13, marginBottom: 12 }}>{payError}</div>}
                        {purchaseResult ? (
                            <div style={{ background: '#11243d', border: '1px solid #35506c', borderRadius: 12, padding: 14 }}>
                                <div style={{ fontWeight: 800, color: '#79c0ff', marginBottom: 6 }}>구매 ID: {purchaseResult.id} · 상태: {purchaseResult.status}</div>
                                {payUrl ? (
                                    <a href={payUrl} target="_blank" rel="noreferrer"
                                        style={{ display: 'inline-block', background: '#2a7cff', color: '#fff', padding: '12px 24px', borderRadius: 12, fontWeight: 800, fontSize: 15, textDecoration: 'none' }}>
                                        🔗 결제 페이지 열기
                                    </a>
                                ) : (
                                    <div style={{ color: '#8b949e', fontSize: 13 }}>결제 URL을 불러오는 중...</div>
                                )}
                            </div>
                        ) : (
                            <button onClick={handlePayment} disabled={payLoading || !token}
                                style={{ borderRadius: 12, border: 'none', background: (!token || payLoading) ? '#26466b' : '#2a7cff', color: '#fff', padding: '14px 24px', fontWeight: 800, fontSize: 16, cursor: (!token || payLoading) ? 'not-allowed' : 'pointer', width: '100%' }}>
                                {payLoading ? '결제 처리 중...' : token ? '💳 결제 진행하기' : '🔐 로그인 후 결제'}
                            </button>
                        )}
                        {!token && (
                            <p style={{ margin: '8px 0 0', fontSize: 12, color: '#8b949e', textAlign: 'center' }}>
                                결제를 진행하려면 <button onClick={() => setShowLoginModal(true)} style={{ background: 'none', border: 'none', color: '#79c0ff', cursor: 'pointer', textDecoration: 'underline', fontSize: 12 }}>로그인</button>이 필요합니다.
                            </p>
                        )}
                    </section>
                )}

                <div style={{ background: '#151b23', border: '1px solid #21262d', borderRadius: 12, padding: 20, marginTop: 24 }}>
                    <h3 style={{ margin: '0 0 6px', fontSize: 16, color: '#e6edf3' }}>📱 모바일 앱 설치</h3>
                    <p style={{ margin: '0 0 14px', fontSize: 13, color: '#8b949e' }}>Android 기기에 설치해 오프라인에서도 사용하세요.</p>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                        <button onClick={handleApkDownload} style={{ display: 'inline-block', background: '#2a7cff', color: '#fff', padding: '10px 20px', borderRadius: 10, fontWeight: 700, fontSize: 14, border: 'none', cursor: 'pointer' }}>📥 APK 다운로드 (로그인 필요)</button>
                        <a href="/marketplace/1" style={{ display: 'inline-block', background: '#151b23', border: '1px solid #21262d', color: '#8b949e', padding: '10px 20px', borderRadius: 10, fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>마켓플레이스로 돌아가기</a>
                    </div>
                    <p style={{ margin: '12px 0 0', fontSize: 12, color: '#6b7280' }}>
                        APK 패키지에는 Expo React Native 소스 + EAS 빌드 가이드가 포함됩니다.<br />
                        EAS CLI로 클라우드 빌드하면 실제 설치 가능한 APK가 생성됩니다.
                    </p>
                </div>

                <div style={{ textAlign: 'center', marginTop: 24, color: '#6b7280', fontSize: 12 }}>
                    나도통역사 v3.0 · NadoTranslator AI 엔진<br />
                    한국어 · English · 中文 · 繁體 · 日本語 · Español · Français · Deutsch · Português · Русский · العربية · हिन्दी · Italiano · Türkçe · Tiếng Việt · ภาษาไทย · Indonesia · Melayu · Nederlands · Polski · Українська · Svenska · Norsk · Dansk (24개 언어)
                </div>
            </div>
        </main>
    );
}