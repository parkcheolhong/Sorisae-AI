import { describe, expect, it } from '@jest/globals';

import {
    formatCountryDisplay,
    getCountryDisplayName,
} from '../features/i18n/countryDisplayCatalog';

describe('countryDisplayCatalog', () => {
    it('localizes KR by service country display locale', () => {
        expect(getCountryDisplayName('KR', 'ko')).toBe('대한민국');
        expect(getCountryDisplayName('KR', 'en')).toBe('South Korea');
        expect(getCountryDisplayName('KR', 'ja')).toBe('大韓民国');
        expect(formatCountryDisplay('KR', 'en')).toBe('🇰🇷 South Korea');
    });

    it('localizes non-KR countries by display locale', () => {
        expect(getCountryDisplayName('FR', 'en')).toBe('France');
        expect(getCountryDisplayName('FR', 'ko')).toBe('프랑스');
        expect(formatCountryDisplay('FR', 'en')).toBe('🇫🇷 France');
        expect(getCountryDisplayName('US', 'ja')).toBe('アメリカ');
    });
});
