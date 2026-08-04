import { parseSocialAuthDeepLink } from '../app/appDeepLinks';

describe('parseSocialAuthDeepLink', () => {
    it('parses a WorldLinco social callback deep link', () => {
        const parsed = parseSocialAuthDeepLink(
            'worldlingo://auth/social/callback#access_token=test-token&provider=google&return_to=%2Fmarketplace',
        );

        expect(parsed).toEqual({
            provider: 'google',
            accessToken: 'test-token',
            returnTo: '/marketplace',
        });
    });

    it('rejects non-social callback links', () => {
        expect(parseSocialAuthDeepLink('worldlingo://voip/open')).toBeNull();
    });
});
