/**
 * 사용 설명서 번역 영속 캐시 — uiI18n.ts 와 동일 패턴(언어별 AsyncStorage).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface CachedManualSection {
    heading: string;
    lines: string[];
}

export interface CachedManual {
    title: string;
    summary: string;
    sections: CachedManualSection[];
}

const STORAGE_PREFIX = 'worldlinco.manualI18n.v1.';
const memCache = new Map<string, CachedManual>();
const loadedLangs = new Set<string>();
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let dirtyLang: string | null = null;

export function manualI18nCacheKey(manualId: string, lang: string): string {
    return `${manualId}:${lang}`;
}

export function getCachedManual(manualId: string, lang: string): CachedManual | undefined {
    return memCache.get(manualI18nCacheKey(manualId, lang));
}

export function setCachedManual(manualId: string, lang: string, data: CachedManual): void {
    if (!lang || lang === 'ko') return;
    memCache.set(manualI18nCacheKey(manualId, lang), data);
    dirtyLang = lang;
    scheduleSave();
}

export async function loadManualI18nCacheForLang(lang: string): Promise<void> {
    const norm = String(lang || '').trim().toLowerCase();
    if (!norm || norm === 'ko' || loadedLangs.has(norm)) return;
    loadedLangs.add(norm);
    try {
        const raw = await AsyncStorage.getItem(STORAGE_PREFIX + norm);
        if (!raw) return;
        const obj = JSON.parse(raw) as Record<string, CachedManual>;
        Object.entries(obj).forEach(([manualId, manual]) => {
            memCache.set(manualI18nCacheKey(manualId, norm), manual);
        });
    } catch {
        /* 손상된 캐시는 무시 */
    }
}

function scheduleSave() {
    if (saveTimer) return;
    saveTimer = setTimeout(() => { void saveCache(); }, 1500);
}

async function saveCache() {
    saveTimer = null;
    const lang = dirtyLang;
    if (!lang || lang === 'ko') return;
    try {
        const obj: Record<string, CachedManual> = {};
        const suffix = `:${lang}`;
        memCache.forEach((manual, key) => {
            if (key.endsWith(suffix)) {
                obj[key.slice(0, -suffix.length)] = manual;
            }
        });
        await AsyncStorage.setItem(STORAGE_PREFIX + lang, JSON.stringify(obj));
    } catch {
        /* no-op */
    }
}
