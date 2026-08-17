import AsyncStorage from '@react-native-async-storage/async-storage';

export type TourismPromoCtaAction = 'face_interpretation' | 'travel_booking' | 'none';

export type TourismPromoPayload = {
    country_code: string | null;
    language: string | null;
    version: number;
    updated_at: string | null;
    title: string;
    subtitle: string;
    body: string;
    cta_label: string;
    cta_action: TourismPromoCtaAction | string;
    accent_color: string;
    image_url: string | null;
    enabled: boolean;
    reason?: string | null;
    spot_id?: string | null;
    distance_km?: number | null;
    radius_km?: number | null;
};

export type TourismPromoBoardItem = {
    spot_id: string | null;
    post_id?: string | null;
    source?: 'user' | 'admin' | string;
    author_username?: string | null;
    author_user_id?: number | null;
    title: string;
    subtitle: string;
    body: string;
    cta_label: string;
    cta_action: TourismPromoCtaAction | string;
    accent_color: string;
    image_url: string | null;
    distance_km: number | null;
    radius_km: number | null;
    nearby: boolean;
    language: string;
    created_at?: string | null;
};

export type TourismPromoBoardPayload = {
    enabled: boolean;
    reason?: string | null;
    country_code: string | null;
    language: string | null;
    version: number;
    updated_at: string | null;
    user_can_post?: boolean;
    items: TourismPromoBoardItem[];
};

export type UserTourismPromoCreateInput = {
    title: string;
    subtitle?: string;
    body: string;
    cta_label?: string;
    cta_action?: string;
    countryCode: string;
    latitude?: number | null;
    longitude?: number | null;
    language: string;
};

export type TourismPromoQuery = {
    countryCode: string | null | undefined;
    latitude: string | number | null | undefined;
    longitude: string | number | null | undefined;
    language: string | null | undefined;
};

const CACHE_KEY = '@worldlinco/tourism-promo/v2';
const BOARD_CACHE_KEY = '@worldlinco/tourism-promo-board/v1';
const CACHE_TTL_MS = 60_000;

type CacheEntry = {
    key: string;
    payload: TourismPromoPayload | null;
    fetchedAt: number;
};

let cached: CacheEntry | null = null;
const promoInFlight = new Map<string, Promise<TourismPromoPayload | null>>();

function normalizeCountryCode(raw: string | null | undefined): string | null {
    const code = String(raw || '').trim().toUpperCase();
    return /^[A-Z]{2}$/.test(code) ? code : null;
}

function parseCoordinate(raw: string | number | null | undefined): number | null {
    if (raw === null || raw === undefined || raw === '') {
        return null;
    }
    const value = typeof raw === 'number' ? raw : Number.parseFloat(String(raw));
    return Number.isFinite(value) ? value : null;
}

function buildCacheKey(query: TourismPromoQuery): string | null {
    const country = normalizeCountryCode(query.countryCode);
    const lat = parseCoordinate(query.latitude);
    const lon = parseCoordinate(query.longitude);
    const lang = String(query.language || 'ko').trim().toLowerCase() || 'ko';
    if (!country || lat === null || lon === null) {
        return null;
    }
    return `${country}:${lat.toFixed(3)}:${lon.toFixed(3)}:${lang}`;
}

function buildBoardCacheKey(query: TourismPromoQuery): string | null {
    const country = normalizeCountryCode(query.countryCode);
    const lat = parseCoordinate(query.latitude);
    const lon = parseCoordinate(query.longitude);
    const lang = String(query.language || 'ko').trim().toLowerCase() || 'ko';
    if (!country) {
        return null;
    }
    const coordPart = lat !== null && lon !== null
        ? `${lat.toFixed(3)}:${lon.toFixed(3)}`
        : 'no-gps';
    return `board:${country}:${coordPart}:${lang}`;
}

type BoardCacheEntry = {
    key: string;
    payload: TourismPromoBoardPayload | null;
    fetchedAt: number;
};

let boardCached: BoardCacheEntry | null = null;
const boardInFlight = new Map<string, Promise<TourismPromoBoardPayload | null>>();

export async function fetchTourismPromoBoard(
    apiBaseUrl: string,
    query: TourismPromoQuery,
): Promise<TourismPromoBoardPayload | null> {
    const cacheKey = buildBoardCacheKey(query);
    if (!cacheKey) {
        return null;
    }

    const now = Date.now();
    if (boardCached && boardCached.key === cacheKey && now - boardCached.fetchedAt < CACHE_TTL_MS) {
        return boardCached.payload;
    }

    const existing = boardInFlight.get(cacheKey);
    if (existing) {
        return existing;
    }

    const base = String(apiBaseUrl || '').replace(/\/$/, '');
    if (!base) {
        return null;
    }

    const country = normalizeCountryCode(query.countryCode)!;
    const lang = String(query.language || 'ko').trim().toLowerCase() || 'ko';
    const lat = parseCoordinate(query.latitude);
    const lon = parseCoordinate(query.longitude);

    const params = new URLSearchParams({
        country,
        lang,
        mode: 'board',
    });
    if (lat !== null && lon !== null) {
        params.set('lat', String(lat));
        params.set('lon', String(lon));
    }

    const requestPromise = (async () => {
    try {
        const response = await fetch(`${base}/api/marketplace/worldlinco/tourism-promo?${params.toString()}`, {
            headers: { Accept: 'application/json' },
        });
        if (!response.ok) {
            return null;
        }
        const payload = (await response.json()) as TourismPromoBoardPayload;
        boardCached = { key: cacheKey, payload, fetchedAt: now };
        void AsyncStorage.setItem(BOARD_CACHE_KEY, JSON.stringify(boardCached)).catch(() => {});
        return payload;
    } catch {
        try {
            const raw = await AsyncStorage.getItem(BOARD_CACHE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw) as BoardCacheEntry;
                if (parsed.key === cacheKey && parsed.payload) {
                    return parsed.payload;
                }
            }
        } catch {
            // no-op
        }
        return null;
    }
    })();

    boardInFlight.set(cacheKey, requestPromise);
    try {
        return await requestPromise;
    } finally {
        boardInFlight.delete(cacheKey);
    }
}

export async function fetchTourismPromo(
    apiBaseUrl: string,
    query: TourismPromoQuery,
): Promise<TourismPromoPayload | null> {
    const cacheKey = buildCacheKey(query);
    if (!cacheKey) {
        return null;
    }

    const now = Date.now();
    if (cached && cached.key === cacheKey && now - cached.fetchedAt < CACHE_TTL_MS) {
        return cached.payload;
    }

    const existing = promoInFlight.get(cacheKey);
    if (existing) {
        return existing;
    }

    const base = String(apiBaseUrl || '').replace(/\/$/, '');
    if (!base) {
        return null;
    }

    const country = normalizeCountryCode(query.countryCode)!;
    const lat = parseCoordinate(query.latitude)!;
    const lon = parseCoordinate(query.longitude)!;
    const lang = String(query.language || 'ko').trim().toLowerCase() || 'ko';

    const params = new URLSearchParams({
        country,
        lat: String(lat),
        lon: String(lon),
        lang,
    });

    const requestPromise = (async () => {
    try {
        const response = await fetch(`${base}/api/marketplace/worldlinco/tourism-promo?${params.toString()}`, {
            headers: { Accept: 'application/json' },
        });
        if (!response.ok) {
            return null;
        }
        const payload = (await response.json()) as TourismPromoPayload;
        if (!payload?.enabled || !payload.title) {
            cached = { key: cacheKey, payload: null, fetchedAt: now };
            return null;
        }
        cached = { key: cacheKey, payload, fetchedAt: now };
        void AsyncStorage.setItem(CACHE_KEY, JSON.stringify({ key: cacheKey, payload, fetchedAt: now })).catch(() => {});
        return payload;
    } catch {
        try {
            const raw = await AsyncStorage.getItem(CACHE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw) as CacheEntry;
                if (parsed.key === cacheKey && parsed.payload?.enabled) {
                    return parsed.payload;
                }
            }
        } catch {
            // no-op
        }
        return null;
    }
    })();

    promoInFlight.set(cacheKey, requestPromise);
    try {
        return await requestPromise;
    } finally {
        promoInFlight.delete(cacheKey);
    }
}

export function clearTourismPromoCache(): void {
    cached = null;
    boardCached = null;
}

export async function postUserTourismPromo(
    apiBaseUrl: string,
    authToken: string,
    input: UserTourismPromoCreateInput,
): Promise<{ ok: boolean; post?: { id: string } }> {
    const base = String(apiBaseUrl || '').replace(/\/$/, '');
    const token = String(authToken || '').trim();
    const country = normalizeCountryCode(input.countryCode);
    if (!base || !token || !country) {
        throw new Error('login_and_gps_required');
    }

    const lat = parseCoordinate(input.latitude);
    const lon = parseCoordinate(input.longitude);
    const lang = String(input.language || 'ko').trim().toLowerCase() || 'ko';

    const response = await fetch(`${base}/api/marketplace/worldlinco/tourism-promo`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            title: input.title.trim(),
            subtitle: (input.subtitle || '').trim(),
            body: input.body.trim(),
            cta_label: (input.cta_label || '').trim(),
            cta_action: (input.cta_action || 'none').trim(),
            country_code: country,
            latitude: lat,
            longitude: lon,
            language: lang,
        }),
    });

    if (!response.ok) {
        const detail = await response.text().catch(() => '');
        throw new Error(detail || `post_failed_${response.status}`);
    }

    clearTourismPromoCache();
    return (await response.json()) as { ok: boolean; post?: { id: string } };
}
