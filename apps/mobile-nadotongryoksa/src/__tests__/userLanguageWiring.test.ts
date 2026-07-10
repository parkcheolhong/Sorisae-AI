/**
 * 사용자 언어/i18n SSOT 배선 검증 — 파일 누락·카탈로그 단절 시 CI 실패.
 */
jest.mock('../features/i18n/uiI18n', () => {
    let profileCountry: string | null = null;
    const countryLang: Record<string, string> = {
        KR: 'ko', US: 'en', JP: 'ja', CN: 'zh', RU: 'ru',
    };
    return {
        getUiLang: () => 'en',
        getEffectiveUiLang: () => {
            if (profileCountry && countryLang[profileCountry]) {
                return countryLang[profileCountry];
            }
            return 'en';
        },
        setProfileUiLangOverride: jest.fn(),
        setProfileCountryCode: (cc: string | null) => { profileCountry = cc; },
        setUiLang: jest.fn(),
        localizeUiString: (s: string) => s,
        prefetchUiStrings: jest.fn(),
    };
});

import fs from 'fs';
import path from 'path';

import { resolveBootstrapUiLang } from '../features/i18n/bootstrapUiLang';
import { getFeatureUiText, getAllFeatureUiKeys } from '../features/i18n/featureUiCatalog';
import { setProfileCountryCode } from '../features/i18n/uiI18n';
import { formatBidirectionalLanguagePair, formatFlagPrefixedName } from '../features/i18n/userDisplayIdentity';

const SRC_ROOT = path.join(__dirname, '..');

describe('user language wiring SSOT', () => {
    it('required i18n SSOT files exist in repo (not doc-only)', () => {
        const required = [
            'features/i18n/BidirectionalLanguagePairBadge.tsx',
            'features/i18n/bootstrapUiLang.ts',
            'features/i18n/featureUiCatalog.ts',
            'features/i18n/userDisplayIdentity.ts',
            'features/i18n/displayLanguage.ts',
            'features/i18n/profileDisplayLocale.ts',
            'features/i18n/countryDisplayCatalog.ts',
            'features/i18n/languageDisplayCatalog.ts',
            'features/operator/OperatorLogSection.tsx',
        ];
        for (const rel of required) {
            expect(fs.existsSync(path.join(SRC_ROOT, rel))).toBe(true);
        }
    });

    it('bootstrapUiLang resolves supported lang on cold start', () => {
        const lang = resolveBootstrapUiLang();
        expect(['ko', 'en', 'ja', 'zh']).toContain(lang);
    });

    it('featureUiCatalog serves non-Korean text for en/ja uiLang', () => {
        expect(getFeatureUiText('user.bidirectionalMode', undefined, 'en')).toBe('Auto bidirectional interpretation');
        expect(getFeatureUiText('pstn.callWaiting', undefined, 'ja')).toBe('通話待機中...');
        expect(getFeatureUiText('home.greeting', undefined, 'en')).not.toMatch(/안녕/);
    });

    it('language pair uses human labels not raw codes', () => {
        const pair = formatBidirectionalLanguagePair('en', 'ja');
        expect(pair).toContain('English');
        expect(pair).toContain('日本語');
        expect(pair).not.toMatch(/\ben\b.*\bja\b/i);
    });

    it('flag+name prefix does not duplicate flag', () => {
        expect(formatFlagPrefixedName('🇺🇸', '🇺🇸 Alice')).toBe('🇺🇸 Alice');
        expect(formatFlagPrefixedName('🇯🇵', 'Bob')).toBe('🇯🇵 Bob');
    });

    it('service country drives catalog display lang over preferred_language', () => {
        setProfileCountryCode('US');
        expect(getFeatureUiText('chat.list.title')).toBe('Chat');
        setProfileCountryCode(null);
    });

    it('catalog includes VoIP/Chat/PSTN/Home keys used on user screens', () => {
        const keys = new Set(getAllFeatureUiKeys());
        for (const required of [
            'voip.metaNickname',
            'chat.list.title',
            'chat.hubTitle',
            'contacts.title',
            'capture.listeningSorisae',
            'gps.checkingPermission',
            'pstn.interToggleStart',
            'pstn.peerLanguageLabel',
            'pstn.peerLanguageHint',
            'home.greeting',
            'face.peerPlaceholder',
            'user.mySpeechInput',
            'travel.mapPreview',
            'tourism.nearbyBadge',
            'manual.back',
        ]) {
            expect(keys.has(required as never)).toBe(true);
        }
    });

    it('App.tsx keeps my-language SSOT in settings/signup only (no scattered overrides)', () => {
        const appPath = path.join(__dirname, '..', '..', 'App.tsx');
        const appSource = fs.readFileSync(appPath, 'utf8');

        expect(appSource).toContain('const currentVoipPreferredLanguage: LangCode = fromLang;');
        expect(appSource).not.toMatch(/handleSwap\s*=\s*\(/);
        expect(appSource).not.toMatch(/setLangPickerFor\('from'\)/);
        expect(appSource).not.toMatch(/voipLocalLangOverride/);
        expect(appSource).not.toMatch(/통역 지정 언어\(이 단말\)/);
        expect(appSource).toContain('worldlinco-pstn-peer-lang');

        const setFromLangMatches = appSource.match(/setFromLang\(/g) ?? [];
        expect(setFromLangMatches).toHaveLength(2);
        expect(appSource).toContain('applySyncedCountryLanguage');
        expect(appSource).toContain('handleSelectSignupCountry');
    });
});
