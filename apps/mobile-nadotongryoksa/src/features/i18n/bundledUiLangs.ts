/**
 * 오프라인 정적 UI 번역이 번들된 언어 — 한국어 플래시 없이 즉시 표시.
 * 회원가입·설정 설명서·VoIP/채팅/PSTN 카탈로그에 사용.
 */
import type { LangCode } from '../language/languageCatalog';

export const BUNDLED_UI_LANGS = ['ko', 'en', 'ja', 'zh'] as const;
export type BundledUiLang = (typeof BUNDLED_UI_LANGS)[number];

export function isBundledUiLang(lang: string | null | undefined): lang is BundledUiLang {
    return BUNDLED_UI_LANGS.includes(String(lang || '').trim().toLowerCase() as BundledUiLang);
}

/** 카탈로그 조회용 — 번들 없는 언어는 en 으로 즉시 폴백(ko 원문 노출 방지). */
export function resolveBundledCatalogLang(lang: string | null | undefined): BundledUiLang {
    const norm = String(lang || '').trim().toLowerCase();
    if (isBundledUiLang(norm)) {
        return norm;
    }
    return 'en';
}
