export const WORLDLINGO_BRAND_NAME = 'WorldLinco';
export const WORLDLINGO_BRAND_NAME_KO = '월드링코';
export const WORLDLINGO_ENGINE_LABEL = 'WorldLinco AI';

export const WORLDLINGO_LEGACY_SLUG = 'nadotongryoksa';
export const WORLDLINGO_MARKETPLACE_ROUTE = '/marketplace/worldlinco';
export const WORLDLINGO_LEGACY_MARKETPLACE_ROUTE = '/marketplace/nadotongryoksa';
export const WORLDLINGO_MARKETPLACE_API_PREFIX = '/api/marketplace/nadotongryoksa';

export const WORLDLINGO_PROJECT_MATCH_TOKENS = [
    'worldlinco',
    'worldlingo',
    '월드링코',
    'nadotongryoksa',
    '나도통역사',
    '통번역 스위트',
    'translation-v1',
    '신세계소리새',
] as const;

export const WORLDLINGO_APK_FILENAME_PREFIXES = [
    'worldlinco-v',
    'nadotongryoksa-v',
] as const;

export function normalizeWorldLincoSearchText(value: unknown): string {
    return String(value ?? '').trim().toLowerCase();
}

export function matchesWorldLincoProjectHaystack(haystack: string): boolean {
    const normalized = normalizeWorldLincoSearchText(haystack);
    return WORLDLINGO_PROJECT_MATCH_TOKENS.some((token) => normalized.includes(token.toLowerCase()));
}

export function matchesWorldLincoProjectTitle(title: unknown): boolean {
    return matchesWorldLincoProjectHaystack(normalizeWorldLincoSearchText(title));
}

export function matchesWorldLincoApkFilename(filename: unknown): boolean {
    const normalized = normalizeWorldLincoSearchText(filename);
    return WORLDLINGO_APK_FILENAME_PREFIXES.some((prefix) => normalized.includes(prefix));
}
