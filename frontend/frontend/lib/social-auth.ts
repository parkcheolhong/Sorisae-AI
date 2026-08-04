export type SocialProvider = 'google' | 'kakao' | 'naver';

export function buildSocialLoginStartUrl(apiBaseUrl: string, provider: SocialProvider, returnTo: string) {
    const url = new URL(`/api/auth/oauth/${provider}/start`, apiBaseUrl);
    if (returnTo.trim()) {
        url.searchParams.set('return_to', returnTo);
    }
    return url.toString();
}
