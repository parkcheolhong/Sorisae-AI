// [기능 분리 Phase5.3/5.5] 노래 번역 기능 — 언어 결정 순수 헬퍼.
// 공용 언어 카탈로그(languageCatalog)를 의존하므로 App.tsx 가 아닌 공용 모듈에서 import → 순환 import 없음.

import { type LangCode, normalizeDetectedLangCode, resolveAutoTargetLang } from '../language/languageCatalog';

/** 감지 언어 문자열을 song 파일 언어로 정규화. 미인식 시 fallback 유지. */
export function normalizeSongFileLang(value: string, fallback: LangCode): LangCode {
    return normalizeDetectedLangCode(value) ?? fallback;
}

/** song 파일 타깃 언어 결정 — 한국어 소스는 한국어 자막 우선, 그 외는 자동 타깃 규칙. */
export function resolveSongFileTargetLang(currentSource: LangCode, currentTarget: LangCode): LangCode {
    if (currentSource === 'ko') return 'ko';
    if (currentTarget !== currentSource) return currentTarget;
    return resolveAutoTargetLang(currentSource, currentTarget);
}
