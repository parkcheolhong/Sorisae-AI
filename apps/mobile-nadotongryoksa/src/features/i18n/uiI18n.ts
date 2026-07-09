/**
 * 전역 UI 자동 번역(SSOT) — 회원가입/프로필에서 지정한 언어로 앱의 모든 한국어 텍스트를 표시한다.
 *
 * 동작 개요
 *  - 기준(원문) 언어는 한국어. uiLang !== 'ko' 이면 화면에 그려지는 한글 포함 문자열을 그 언어로 바꾼다.
 *  - 실제 치환은 전역 Text 렌더 패치(App.tsx)가 translateUiSync() 로 "동기" 조회해 수행한다.
 *  - 캐시에 없으면 일단 원문(한글)을 보여주고, 백그라운드로 번역을 받아 캐시에 채운 뒤 tick 을 올려 다시 그린다.
 *  - 번역 결과는 언어별로 AsyncStorage 에 영속 → 다음 실행부터는 즉시 표시(네트워크/플리커 없음).
 *
 * 다국어 혼용 방지(영어 라벨까지)
 *  - 한국어뿐 아니라 화면에 박힌 영어 자연어 라벨("My language", "Pick image" 등)도 지정 언어로 바꾼다.
 *    → 중국어 사용자에게 영어가 섞여 보이는 "혼용"을 없앤다(자국 프로그램처럼).
 *  - 원문 언어는 글자 기준으로 추정(한글 → ko, 그 외 라틴 → en)해 번역 정확도를 높인다.
 *
 * 안전장치(오역/오작동 방지)
 *  - 브랜드(WorldLinco)·이메일·URL·버전(v1.0.x)·대문자 약어/코드(GPS, KR, OFF 단독)·숫자/기호는 번역 제외.
 *  - 표시(children)만 치환하고 props/state 는 그대로 → onPress 등 앱 로직에는 영향이 없다.
 *  - 원문 언어 == 표시 언어면 API 호출 없이 원문 그대로(불필요 호출 방지).
 *  - 실패 시 잠깐 쿨다운을 둬 재요청 폭주를 막는다.
 *  - tick 은 새 번역이 실제로 추가됐을 때만 올려 리렌더 폭주를 막는다.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

import { translateText } from '../../api/translate';
import { resolveBootstrapUiLang } from './bootstrapUiLang';
import { collectKoUiStrings } from './uiStringCatalog';

const HANGUL_RE = /[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]/;
const LATIN_RE = /[A-Za-z]/;
const LOWER_RE = /[a-z]/;
const STORAGE_PREFIX = 'worldlinco.uiI18n.v1.'; // + lang
const UI_LANG_STORAGE_KEY = 'worldlinco.uiLang.v1';
const MAX_LEN = 400;       // 이보다 긴 문자열은 번역 생략(원문 유지) — UI 라벨은 짧다.
const FLUSH_MS = 250;
const BATCH = 24;
const COOLDOWN_MS = 4000;

let uiLang = resolveBootstrapUiLang();
const cache = new Map<string, string>();   // key: `${lang}\u0000${text}`
const pending = new Set<string>();
const loadedLangs = new Set<string>();
let queue: Array<{ lang: string; text: string }> = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let cooldownUntil = 0;
let dirtyLang: string | null = null;

let tick = 0;
const tickListeners = new Set<() => void>();

function bumpTick() {
    tick += 1;
    tickListeners.forEach((fn) => {
        try { fn(); } catch { /* no-op */ }
    });
}

export function getUiLang(): string {
    return uiLang;
}

/** 원문 언어 추정: 한글이 있으면 ko, 라틴 글자가 있으면 en, 그 외 null(번역 대상 아님). */
function sourceLangOf(text: string): 'ko' | 'en' | null {
    if (HANGUL_RE.test(text)) return 'ko';
    const t = text.trim();
    if (t.length < 2) return null;
    if (!LATIN_RE.test(t) || !LOWER_RE.test(t)) return null; // 글자 없음·전부 대문자/약어/코드 → 제외
    if (/worldlinco/i.test(t)) return null;                  // 브랜드
    if (t.includes('@')) return null;                        // 이메일
    if (/https?:\/\/|www\./i.test(t)) return null;           // URL
    if (/\bv?\d+\.\d+/i.test(t)) return null;                // 버전(v1.0.x)
    if (!/\s/.test(t) && t.length < 4) return null;          // 너무 짧은 단일 토큰
    return 'en';
}

export function shouldTranslate(text: string): boolean {
    if (uiLang === 'ko' || !text || text.length > MAX_LEN) return false;
    const src = sourceLangOf(text);
    return src !== null && src !== uiLang; // 원문 == 표시 언어면 번역 불필요
}

function keyFor(lang: string, text: string): string {
    return `${lang}\u0000${text}`;
}

/** 동기 조회: 캐시에 있으면 번역문, 없으면 원문(한글) + 백그라운드 큐잉. */
export function translateUiSync(text: string): string {
    if (!shouldTranslate(text)) return text;
    const lang = uiLang;
    const key = keyFor(lang, text);
    const hit = cache.get(key);
    if (hit !== undefined) return hit;
    if (!pending.has(key)) {
        pending.add(key);
        queue.push({ lang, text });
        scheduleFlush();
    }
    return text;
}

/** 프로그램matic UI 문자열(상태·Alert 인자 등)용 — translateUiSync 별칭. */
export function localizeUiString(text: string): string {
    return translateUiSync(text);
}

/** 언어 변경 직후 카탈로그 원문을 백그라운드 번역 큐에 넣어 51개 LANG 전환을 가속한다. */
export function prefetchUiStrings(extra: string[] = []): void {
    if (uiLang === 'ko') return;
    const strings = [...collectKoUiStrings(), ...extra];
    strings.forEach((text) => { translateUiSync(text); });
}

function scheduleFlush() {
    if (flushTimer) return;
    const delay = Math.max(FLUSH_MS, cooldownUntil - Date.now());
    flushTimer = setTimeout(() => { void flushQueue(); }, delay);
}

async function flushQueue() {
    flushTimer = null;
    if (Date.now() < cooldownUntil) { scheduleFlush(); return; }
    const batch = queue.splice(0, BATCH);
    if (batch.length === 0) return;
    let added = 0;
    let failed = false;
    await Promise.all(batch.map(async ({ lang, text }) => {
        const key = keyFor(lang, text);
        try {
            const src = HANGUL_RE.test(text) ? 'ko' : 'en';
            const r = await translateText(text, src, lang, 10000);
            const translated = (r.translated || '').trim();
            if (translated && !r.offline) {
                cache.set(key, translated);
                added += 1;
                dirtyLang = lang;
            } else {
                // 오프라인/빈 응답: 캐시하지 않고 다음 기회에 재시도.
                failed = true;
            }
        } catch {
            failed = true;
        } finally {
            pending.delete(key);
        }
    }));
    if (failed) cooldownUntil = Date.now() + COOLDOWN_MS;
    if (added > 0) {
        scheduleSave();
        bumpTick();
    }
    if (queue.length > 0) scheduleFlush();
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
        const obj: Record<string, string> = {};
        const prefix = `${lang}\u0000`;
        cache.forEach((v, k) => {
            if (k.startsWith(prefix)) obj[k.slice(prefix.length)] = v;
        });
        await AsyncStorage.setItem(STORAGE_PREFIX + lang, JSON.stringify(obj));
    } catch { /* no-op */ }
}

async function loadCacheForLang(lang: string): Promise<void> {
    if (lang === 'ko' || loadedLangs.has(lang)) return;
    loadedLangs.add(lang);
    try {
        const raw = await AsyncStorage.getItem(STORAGE_PREFIX + lang);
        if (raw) {
            const obj = JSON.parse(raw) as Record<string, string>;
            Object.entries(obj).forEach(([text, translated]) => {
                cache.set(keyFor(lang, text), translated);
            });
            bumpTick();
        }
    } catch { /* no-op */ }
}

/** 회원가입/프로필/로그인에서 호출 — UI 표시 언어를 바꾼다(영속 캐시 로드 포함). */
export async function setUiLang(lang: string | null | undefined): Promise<void> {
    const norm = String(lang || 'ko').trim().toLowerCase() || 'ko';
    const changed = norm !== uiLang;
    uiLang = norm;
    if (norm !== 'ko') await loadCacheForLang(norm);
    if (changed || norm !== 'ko') bumpTick();
    void AsyncStorage.setItem(UI_LANG_STORAGE_KEY, norm).catch(() => { /* no-op */ });
}

/** 앱 cold start — 마지막 uiLang 을 즉시 복원(프로필 로드 전 한국어 플래시 완화). */
export async function hydrateUiLangFromStorage(): Promise<string | null> {
    try {
        const raw = await AsyncStorage.getItem(UI_LANG_STORAGE_KEY);
        const norm = String(raw || '').trim().toLowerCase();
        if (!norm || norm === 'ko') return null;
        await setUiLang(norm);
        prefetchUiStrings();
        return norm;
    } catch {
        return null;
    }
}

export function subscribeTick(fn: () => void): () => void {
    tickListeners.add(fn);
    return () => { tickListeners.delete(fn); };
}

/** 전역 Text 패치가 구독 — 새 번역이 도착하면 자동 리렌더. */
export function useUiI18nTick(): void {
    const [, setV] = useState(0);
    useEffect(() => subscribeTick(() => setV((v) => v + 1)), []);
}
