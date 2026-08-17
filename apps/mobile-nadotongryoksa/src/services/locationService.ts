import * as Location from 'expo-location';

type CacheEntry<T> = {
    value: T;
    expiresAt: number;
    inFlight?: Promise<T>;
};

const FOREGROUND_PERMISSION_TTL_MS = 10_000;
const LOCATION_SERVICES_TTL_MS = 15_000;
const CURRENT_POSITION_TTL_MS = 2_500;
const LAST_KNOWN_TTL_MS = 10_000;
const REVERSE_GEOCODE_TTL_MS = 60_000;

const foregroundPermissionCache = new Map<string, CacheEntry<Location.LocationPermissionResponse>>();
const locationServicesCache = new Map<string, CacheEntry<boolean>>();
const currentPositionCache = new Map<string, CacheEntry<Location.LocationObject>>();
const lastKnownPositionCache = new Map<string, CacheEntry<Location.LocationObject | null>>();
const reverseGeocodeCache = new Map<string, CacheEntry<Location.LocationGeocodedAddress[]>>();

function getCacheEntry<T>(cache: Map<string, CacheEntry<T>>, key: string): CacheEntry<T> | null {
    const entry = cache.get(key);
    if (!entry) {
        return null;
    }
    if (entry.expiresAt <= Date.now() && !entry.inFlight) {
        cache.delete(key);
        return null;
    }
    return entry;
}

async function resolveCachedValue<T>(
    cache: Map<string, CacheEntry<T>>,
    key: string,
    ttlMs: number,
    factory: () => Promise<T>,
): Promise<T> {
    const cached = getCacheEntry(cache, key);
    if (cached?.inFlight) {
        return cached.inFlight;
    }
    if (cached && cached.expiresAt > Date.now()) {
        return cached.value;
    }

    const inFlight = factory().then((value) => {
        cache.set(key, {
            value,
            expiresAt: Date.now() + ttlMs,
        });
        return value;
    }).catch((error) => {
        cache.delete(key);
        throw error;
    });

    cache.set(key, {
        value: cached?.value as T,
        expiresAt: Date.now() + ttlMs,
        inFlight,
    });

    return inFlight;
}

function normalizePositionKey(latitude: number, longitude: number): string {
    return `${latitude.toFixed(5)}:${longitude.toFixed(5)}`;
}

export function clearLocationCache(): void {
    foregroundPermissionCache.clear();
    locationServicesCache.clear();
    currentPositionCache.clear();
    lastKnownPositionCache.clear();
    reverseGeocodeCache.clear();
}

export async function getForegroundPermissions(forceRefresh = false): Promise<Location.LocationPermissionResponse> {
    const key = 'foreground';
    if (forceRefresh) {
        foregroundPermissionCache.delete(key);
    }
    return resolveCachedValue(foregroundPermissionCache, key, FOREGROUND_PERMISSION_TTL_MS, async () => Location.getForegroundPermissionsAsync());
}

export async function requestForegroundPermissions(): Promise<Location.LocationPermissionResponse> {
    const result = await Location.requestForegroundPermissionsAsync();
    foregroundPermissionCache.set('foreground', {
        value: result,
        expiresAt: Date.now() + FOREGROUND_PERMISSION_TTL_MS,
    });
    return result;
}

export async function getLocationServicesEnabled(forceRefresh = false): Promise<boolean> {
    const key = 'services';
    if (forceRefresh) {
        locationServicesCache.delete(key);
    }
    return resolveCachedValue(locationServicesCache, key, LOCATION_SERVICES_TTL_MS, async () => Location.hasServicesEnabledAsync());
}

export async function getCurrentPosition(
    options: Parameters<typeof Location.getCurrentPositionAsync>[0],
    cacheKey?: string,
    forceRefresh = false,
): Promise<Location.LocationObject> {
    const key = cacheKey || JSON.stringify(options);
    if (forceRefresh) {
        currentPositionCache.delete(key);
    }
    return resolveCachedValue(currentPositionCache, key, CURRENT_POSITION_TTL_MS, async () => Location.getCurrentPositionAsync(options));
}

export async function getLastKnownPosition(
    options: Parameters<typeof Location.getLastKnownPositionAsync>[0],
    cacheKey?: string,
    forceRefresh = false,
): Promise<Location.LocationObject | null> {
    const key = cacheKey || JSON.stringify(options);
    if (forceRefresh) {
        lastKnownPositionCache.delete(key);
    }
    return resolveCachedValue(lastKnownPositionCache, key, LAST_KNOWN_TTL_MS, async () => Location.getLastKnownPositionAsync(options));
}

export async function reverseGeocode(
    coordinates: { latitude: number; longitude: number },
    forceRefresh = false,
): Promise<Location.LocationGeocodedAddress[]> {
    const key = normalizePositionKey(coordinates.latitude, coordinates.longitude);
    if (forceRefresh) {
        reverseGeocodeCache.delete(key);
    }
    return resolveCachedValue(reverseGeocodeCache, key, REVERSE_GEOCODE_TTL_MS, async () => Location.reverseGeocodeAsync(coordinates));
}

export function watchPositionAsync(
    options: Parameters<typeof Location.watchPositionAsync>[0],
    callback: Parameters<typeof Location.watchPositionAsync>[1],
): ReturnType<typeof Location.watchPositionAsync> {
    return Location.watchPositionAsync(options, callback);
}