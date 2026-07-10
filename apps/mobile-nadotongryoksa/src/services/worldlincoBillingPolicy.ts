import AsyncStorage from '@react-native-async-storage/async-storage';

export type WorldlincoBillingPolicySnapshot = {
    version: number;
    updated_at: string | null;
    access_mode: 'free' | 'paid';
    configured_access_mode?: 'free' | 'paid';
    billing_collection_paused: boolean;
    free_access_active: boolean;
    show_pricing_ui: boolean;
    promo_label: string;
    promo_starts_at?: string | null;
    promo_ends_at?: string | null;
    auto_switch_to_paid_on_promo_end?: boolean;
};

export const WORLDLINGCO_BILLING_POLICY_DEFAULTS: WorldlincoBillingPolicySnapshot = {
    version: 1,
    updated_at: null,
    access_mode: 'free',
    billing_collection_paused: false,
    free_access_active: true,
    show_pricing_ui: false,
    promo_label: '베타 무료 기간',
};

const STORAGE_KEY = '@worldlinco/billing-policy/v1';

let cachedSnapshot: WorldlincoBillingPolicySnapshot = { ...WORLDLINGCO_BILLING_POLICY_DEFAULTS };
let refreshPromise: Promise<WorldlincoBillingPolicySnapshot> | null = null;

function normalizeSnapshot(raw: unknown): WorldlincoBillingPolicySnapshot {
    if (!raw || typeof raw !== 'object') {
        return { ...WORLDLINGCO_BILLING_POLICY_DEFAULTS };
    }
    const data = raw as Record<string, unknown>;
    const accessMode = data.access_mode === 'paid' ? 'paid' : 'free';
    const billingPaused = Boolean(data.billing_collection_paused);
    const freeAccessActive = typeof data.free_access_active === 'boolean'
        ? data.free_access_active
        : accessMode === 'free' || billingPaused;
    return {
        version: Number(data.version) || 1,
        updated_at: typeof data.updated_at === 'string' ? data.updated_at : null,
        access_mode: accessMode,
        configured_access_mode: data.configured_access_mode === 'paid' ? 'paid' : 'free',
        billing_collection_paused: billingPaused,
        free_access_active: freeAccessActive,
        show_pricing_ui: Boolean(data.show_pricing_ui),
        promo_label: String(data.promo_label || WORLDLINGCO_BILLING_POLICY_DEFAULTS.promo_label),
        promo_starts_at: typeof data.promo_starts_at === 'string' ? data.promo_starts_at : null,
        promo_ends_at: typeof data.promo_ends_at === 'string' ? data.promo_ends_at : null,
        auto_switch_to_paid_on_promo_end: Boolean(data.auto_switch_to_paid_on_promo_end),
    };
}

export function getWorldlincoBillingPolicySnapshot(): WorldlincoBillingPolicySnapshot {
    return cachedSnapshot;
}

export async function hydrateWorldlincoBillingPolicyFromStorage(): Promise<WorldlincoBillingPolicySnapshot> {
    try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) {
            cachedSnapshot = normalizeSnapshot(JSON.parse(raw));
        }
    } catch {
        // Best-effort cache only.
    }
    return cachedSnapshot;
}

export async function refreshWorldlincoBillingPolicy(apiBaseUrl: string): Promise<WorldlincoBillingPolicySnapshot> {
    if (refreshPromise) {
        return refreshPromise;
    }
    refreshPromise = (async () => {
        const base = apiBaseUrl.replace(/\/$/, '');
        try {
            const response = await fetch(`${base}/api/marketplace/worldlinco/billing-policy`, {
                headers: { Accept: 'application/json' },
            });
            if (!response.ok) {
                throw new Error(`billing-policy HTTP ${response.status}`);
            }
            const payload = normalizeSnapshot(await response.json());
            cachedSnapshot = payload;
            await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
            return payload;
        } finally {
            refreshPromise = null;
        }
    })();
    return refreshPromise;
}

export function isWorldlincoFreeAccessForUser(
    policy: WorldlincoBillingPolicySnapshot,
    hasSession: boolean,
): boolean {
    return hasSession && policy.free_access_active;
}
