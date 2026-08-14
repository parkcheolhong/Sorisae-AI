import { describe, expect, it } from '@jest/globals';

import { parseAppEntryDeepLink } from '../app/appDeepLinks';

describe('appDeepLinks auth callback', () => {
    it('parses social auth callback payloads', () => {
        const target = parseAppEntryDeepLink(
            'worldlinco://auth/callback?provider=google&access_token=abc123&refresh_token=r1&id_token=i1&expires_in=3600&email=user@example.com&user_id=42&username=user&display_name=User%20Name',
        );
        expect(target).toEqual({
            type: 'auth',
            provider: 'google',
            accessToken: 'abc123',
            refreshToken: 'r1',
            idToken: 'i1',
            expiresInSec: 3600,
            email: 'user@example.com',
            userId: 42,
            username: 'user',
            displayName: 'User Name',
        });
    });

    it('rejects auth callbacks without a token', () => {
        expect(parseAppEntryDeepLink('worldlinco://auth/callback?provider=kakao')).toBeNull();
    });
});
