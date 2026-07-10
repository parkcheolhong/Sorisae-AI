// App.tsx 에서 분리한 소형 순수 헬퍼.
import { DEMO_SESSION_EMAIL_DOMAIN } from './appConstants';
import { isSupportedLangCode, type LangCode } from '../features/language/languageCatalog';

export function buildInstantDemoCredentials(seed: string) {
    const normalizedSeed = seed.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 10) || 'guestdemo';
    return {
        email: `instant-${normalizedSeed}@${DEMO_SESSION_EMAIL_DOMAIN}`,
        username: `instant_${normalizedSeed}`,
        password: `WorldLinco!${normalizedSeed}A1`,
    };
}

export function resolveVoipRemoteLanguageHint(...values: Array<string | null | undefined>): LangCode | null {
    for (const value of values) {
        const normalized = String(value || '').trim().toLowerCase();
        if (isSupportedLangCode(normalized)) {
            return normalized;
        }
    }
    return null;
}
