/**
 * [기능 분리 Phase5.9] 소리새 AI 진화형 동반자 — 50개국 언어쌍 교습 센스(순수 모듈).
 *
 * "지정 언어(사용자 언어)와 사용자가 물어보는 언어를 언어쌍으로 가르쳐 주는 센스":
 *  - detectLanguageTutorIntent: 발화가 "X어로 뭐라고 해 / how do you say ~ in Y" 류 교습 의도인지.
 *  - resolveTargetLanguageFromText: 50개국(LANGS) 중 사용자가 물어본 대상 언어를 해석(별칭/이름/코드).
 *  - buildLanguagePair / buildLanguagePairLabel: (지정 언어 ↔ 대상 언어) 쌍 구성.
 *
 * 순수·결정적. 실제 번역/발음 생성은 백엔드 친구 페르소나(LLM)가 수행하고, 본 모듈은
 * 의도 감지 + 언어쌍 결정만 담당한다(온디바이스 도메인/기억과 정합).
 */
import {
    LANGS,
    getLangLabelText,
    normalizeDetectedLangCode,
    type LangCode,
} from '../language/languageCatalog';

// 교습 의도 신호(한·영). 보수적으로 — 일상 대화를 교습으로 오인하지 않게 특이적 표현만.
const TUTOR_INTENT_PATTERNS: readonly RegExp[] = [
    /뭐라고\s*해|뭐라구\s*해|뭐라고\s*하|어떻게\s*말|어떻게\s*해\b/u,
    /(으로|로)\s*(뭐|어떻게|말)/u,
    /라고\s*해|이라고\s*해/u,
    /번역\s*해|번역해|가르쳐\s*줘|가르쳐줘|발음|회화|단어|표현이/u,
    /how\s+(do|to)\s+you?\s*say|how\s+to\s+say|say\s+.+\s+in\s+\w+|word\s+for|translate\b|teach\s+me/iu,
];

export function detectLanguageTutorIntent(text: string): boolean {
    const raw = String(text || '').trim();
    if (!raw) return false;
    return TUTOR_INTENT_PATTERNS.some((re) => re.test(raw));
}

// "X어로 / X語로 / in X" 처럼 대상 언어를 가리키는 토큰 후보를 추출.
const KO_LANG_TOKEN_RE = /([가-힣A-Za-z]+(?:어|語|말))(?:로|으로|로는|로요)?/gu;
const EN_IN_LANG_RE = /\bin\s+([a-z]+)\b/giu;

/**
 * 발화에서 사용자가 물어본 대상 언어를 해석한다(50개국 LANGS 범위). 미해석 시 null.
 * 1) 'X어로/X語' 한국어 패턴 → 2) 'in X' 영어 패턴 → 3) 일반 토큰 스캔 순으로 시도.
 */
export function resolveTargetLanguageFromText(text: string): LangCode | null {
    const raw = String(text || '').trim();
    if (!raw) return null;

    // 1) 한국어 'X어로' 패턴 우선(가장 명시적).
    for (const m of raw.matchAll(KO_LANG_TOKEN_RE)) {
        const code = normalizeDetectedLangCode(m[1]);
        if (code) return code;
    }
    // 2) 영어 'in X' 패턴.
    for (const m of raw.matchAll(EN_IN_LANG_RE)) {
        const code = normalizeDetectedLangCode(m[1]);
        if (code) return code;
    }
    // 3) 일반 토큰 스캔(언어 이름/별칭이 직접 등장).
    for (const tok of raw.toLowerCase().split(/[\s.,!?;:'"()\[\]{}~·…]+/u)) {
        if (tok.length < 2) continue;
        const code = normalizeDetectedLangCode(tok);
        if (code) return code;
    }
    return null;
}

export interface LanguagePair {
    /** 지정 언어(사용자 언어). */
    sourceLang: LangCode;
    /** 사용자가 물어본 대상 언어. */
    targetLang: LangCode;
    sourceLabel: string;
    targetLabel: string;
}

/** 지정 언어 + 대상 언어로 언어쌍을 구성(동일 언어면 보정: ko↔en). */
export function buildLanguagePair(sourceLang: LangCode, targetLang: LangCode): LanguagePair {
    let target = targetLang;
    if (target === sourceLang) {
        target = sourceLang === 'en' ? 'ko' : 'en';
    }
    return {
        sourceLang,
        targetLang: target,
        sourceLabel: getLangLabelText(sourceLang),
        targetLabel: getLangLabelText(target),
    };
}

/** "한국어 ↔ 日本語" 형태의 표시 라벨. */
export function buildLanguagePairLabel(sourceLang: LangCode, targetLang: LangCode): string {
    const pair = buildLanguagePair(sourceLang, targetLang);
    return `${pair.sourceLabel} ↔ ${pair.targetLabel}`;
}

/** 지원 언어 수(센스 안내 문구용). */
export const TUTOR_SUPPORTED_LANGUAGE_COUNT = LANGS.length;
