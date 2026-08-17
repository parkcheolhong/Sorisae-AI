// App.tsx 에서 분리한 소형 순수 헬퍼.
import { isSupportedLangCode, type LangCode } from '../features/language/languageCatalog';

export function resolveVoipRemoteLanguageHint(...values: Array<string | null | undefined>): LangCode | null {
    for (const value of values) {
        const normalized = String(value || '').trim().toLowerCase();
        if (isSupportedLangCode(normalized)) {
            return normalized;
        }
    }
    return null;
}
