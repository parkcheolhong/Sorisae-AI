import { afterEach, beforeEach, describe, expect, it } from '@jest/globals';

import { buildSocialLoginStartUrl, openSocialLoginProvider } from '../auth/socialLogin';
import { shouldForceHideLoginModal } from '../state/authVisibility';

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

    it('opens the provider auth URL when launching a social login', async () => {
        const openUrl = jest.fn().mockResolvedValue(undefined);
        const result = await openSocialLoginProvider('naver', 'https://api.example.com', openUrl);

        expect(result).toBe('https://api.example.com/api/auth/social/naver/start?redirect_uri=worldlingo%3A%2F%2Fauth%2Fcallback');
        expect(openUrl).toHaveBeenCalledWith(result);
    });

    it('does not force the login modal closed from a valid authenticated session', () => {
        expect(shouldForceHideLoginModal({
            token: 'abc',
            userInfo: {
                id: 7,
                email: 'tester@example.com',
                username: 'tester',
                country_code: 'KR',
                preferred_language: 'ko',
            },
        })).toBe(false);
        expect(shouldForceHideLoginModal({
            token: '',
            userInfo: {
                id: 7,
                email: 'tester@example.com',
                username: 'tester',
            },
        })).toBe(false);
    });

    afterEach(() => {
        process.env.EXPO_PUBLIC_GOOGLE_SOCIAL_LOGIN_URL = originalGoogleUrl;
    });
});
