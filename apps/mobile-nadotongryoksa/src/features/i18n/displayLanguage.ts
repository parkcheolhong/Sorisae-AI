/**
 * UI 표시 언어 SSOT — 프로필 preferred_language · 국가 매핑 언어가
 * fromLang(번역 방향) · uiLang(전역 Text/Alert/placeholder 패치)에 동시 반영된다.
 *
 * 규칙: 화면 라벨·버튼·알림은 getDisplayUiText()(= getUiLang()) 로 조회한다.
 * fromLang/toLang 은 STT·번역 파이프라인 전용이며 UI 표시에 쓰지 않는다.
 */
import { getUiText } from '../../app/appUiText';
import { isSupportedLangCode, type LangCode } from '../language/languageCatalog';
import { getUiLang, localizeUiString, prefetchUiStrings, setUiLang } from './uiI18n';

const HANGUL_RE = /[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]/;

export function normalizeDisplayLang(lang: string | null | undefined): LangCode {
    const norm = String(lang || 'ko').trim().toLowerCase();
    return isSupportedLangCode(norm) ? (norm as LangCode) : 'ko';
}

/** uiLang AsyncStorage 캐시 로드 + tick — 전역 패치가 새 언어로 치환한다. */
export async function syncUiLang(lang: string | null | undefined): Promise<LangCode> {
    const safe = normalizeDisplayLang(lang);
    await setUiLang(safe);
    void prefetchUiStrings();
    return safe;
}

/** 화면 표시용 UI 사전 — 정적 카탈로그 우선, 한글 잔여분만 런타임 번역. */
export function getDisplayUiText() {
    const raw = getUiText(getUiLang());
    if (getUiLang() === 'ko') {
        return raw;
    }
    const localized = { ...raw };
    (Object.keys(localized) as Array<keyof typeof localized>).forEach((key) => {
        const value = localized[key];
        if (typeof value === 'string' && HANGUL_RE.test(value)) {
            localized[key] = localizeUiString(value);
        }
    });
    return localized;
}
