import { afterEach, beforeEach, describe, expect, it } from '@jest/globals';

import { buildSocialLoginStartUrl } from '../auth/socialLogin';

describe('socialLogin', () => {
    const originalGoogleUrl = process.env.EXPO_PUBLIC_GOOGLE_SOCIAL_LOGIN_URL;

    beforeEach(() => {
        process.env.EXPO_PUBLIC_GOOGLE_SOCIAL_LOGIN_URL = '';
    });

    it('builds a provider start url that returns to the app callback', () => {
        const url = buildSocialLoginStartUrl('kakao', 'https://api.example.com');
        expect(url).toBe('https://api.example.com/api/auth/social/kakao/start?redirect_uri=worldlingo%3A%2F%2Fauth%2Fcallback');
    });

    it('prefers an explicit provider url override when configured', () => {
        process.env.EXPO_PUBLIC_GOOGLE_SOCIAL_LOGIN_URL = 'https://login.example.com/google/start';
        const url = buildSocialLoginStartUrl('google', 'https://api.example.com');
        expect(url).toBe('https://login.example.com/google/start');
    });

    afterEach(() => {
        process.env.EXPO_PUBLIC_GOOGLE_SOCIAL_LOGIN_URL = originalGoogleUrl;
    });
});
