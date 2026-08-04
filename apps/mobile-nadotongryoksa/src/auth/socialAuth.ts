import { API_BASE } from '../app/appConstants';
import type { SocialAuthProvider } from '../app/appTypes';

export const SOCIAL_AUTH_CALLBACK_URL = 'worldlingo://auth/social/callback';

export function buildSocialAuthStartUrl(
    provider: SocialAuthProvider,
    returnTo = '/marketplace',
    callbackUrl = SOCIAL_AUTH_CALLBACK_URL,
): string {
    const params = new URLSearchParams({
        return_to: returnTo,
        callback_url: callbackUrl,
    });
    return `${API_BASE}/api/auth/oauth/${provider}/start?${params.toString()}`;
}
