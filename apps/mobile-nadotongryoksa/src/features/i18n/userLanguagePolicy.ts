/**
 * 사용자 언어 우선 정책 SSOT.
 *
 * **사용자(유저)** = 실구매·실사용 고객. 관계자(운영/개발)와 구분한다.
 *
 * - **양방향 통역(기본):** 회원가입 시 등록된 `preferred_language`·국가 기준으로
 *   발신자 ↔ 수신자가 각자의 언어로 소통한다. 설정에서 수동 전환하기 전까지 이 규칙이 유지된다.
 * - **표시(UI):** getUserDisplayLang() / getDisplayUiText() / getFeatureUiText()
 * - **발화(TTS):** resolveUserOutputLang(preferred_language)
 * - **fromLang/toLang:** 번역 파이프라인 전용 — 사용자 화면·TTS에 직접 노출 금지.
 * - **관계자 정보:** 언어 코드·call_id·감사 로그 → 설정「관계자 로그」또는 웹 대시보드만.
 *
 * @see docs/USER_LANGUAGE_POLICY.md
 */
import { resolvePreferredOutputLang, type LangCode } from '../language/languageCatalog';
import { isOperatorSurfaceVisible } from '../operator/operatorAccess';
import { getUiLang } from './uiI18n';

/** 현재 사용자 UI 표시 언어 (= 프로필 preferred_language 동기화된 uiLang). */
export function getUserDisplayLang(): string {
    return getUiLang();
}

/** 사용자 발화(TTS)·읽어주기 출력 언어. preferred_language 가 없으면 fallback. */
export function resolveUserOutputLang(
    preferredLanguage: string | null | undefined,
    fallback: LangCode = 'ko',
): LangCode {
    return resolvePreferredOutputLang(preferredLanguage, fallback);
}

/** 사용자 화면에 언어 코드·개발 메타를 노출해도 되는지(관계자 전용이면 true). */
export function shouldExposeLanguageMetaToViewer(): boolean {
    return isOperatorSurfaceVisible();
}

/** 사용자 UI에 노출 금지 — 원시 언어 코드·개발 메타 여부 간단 판별. */
export function isUserVisibleLanguageAnnotation(text: string): boolean {
    const t = String(text || '').trim();
    if (!t) return false;
    if (/백엔드|call_id|event_type|auto_relay|로컬 직접|마이크 타겟|파일 타겟/i.test(t)) return true;
    if (/^[a-z]{2}(-[a-z]{2})?$/i.test(t)) return true;
    if (/[A-Z]{2}\s*→\s*[A-Z]{2}/.test(t)) return true;
    return false;
}
