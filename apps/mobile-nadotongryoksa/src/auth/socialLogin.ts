import { API_BASE } from '../app/appConstants';

export type SocialLoginProvider = 'google' | 'naver' | 'kakao';

export type SocialLoginProviderConfig = {
    provider: SocialLoginProvider;
    label: string;
    icon: string;
    hint: string;
    accentColor: string;
};

export const SOCIAL_LOGIN_REDIRECT_URI = 'worldlinco://auth/callback';

export const SOCIAL_LOGIN_PROVIDER_CONFIGS: SocialLoginProviderConfig[] = [
    {
        provider: 'google',
        label: 'Google',
        icon: '🟦',
        hint: '구글 계정으로 시작',
        accentColor: '#1e6fe0',
    },
    {
        provider: 'naver',
        label: 'Naver',
        icon: '🟩',
        hint: '네이버 계정으로 시작',
        accentColor: '#03c75a',
    },
    {
        provider: 'kakao',
        label: 'Kakao',
        icon: '🟨',
        hint: '카카오 계정으로 시작',
        accentColor: '#f7e600',
    },
];

function getProviderUrlEnvKey(provider: SocialLoginProvider): string {
    return `EXPO_PUBLIC_${provider.toUpperCase()}_SOCIAL_LOGIN_URL`;
}

export function buildSocialLoginStartUrl(provider: SocialLoginProvider, apiBase: string = API_BASE): string {
    const override = String((process.env as Record<string, string | undefined>)[getProviderUrlEnvKey(provider)] || '').trim();
    if (override) {
        return override;
    }
    const normalizedApiBase = String(apiBase || '').trim().replace(/\/+$/, '');
    return `${normalizedApiBase}/api/auth/social/${provider}/start?redirect_uri=${encodeURIComponent(SOCIAL_LOGIN_REDIRECT_URI)}`;
}
