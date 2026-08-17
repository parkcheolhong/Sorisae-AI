import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    callLogoutApi,
    callLoginApi,
    callSignupApi,
    callSignupConfirmApi,
    callSignupRequestCodeApi,
    callUpdateMeApi,
    clearCurrentUserCache,
    getCurrentUserApi,
} from '../api';
import { clearStoredAuthState, loadStoredAuthState, saveStoredAuthState } from '../app/appStorage';
import type { SignupPayload, UserInfo, UserProfileUpdatePayload } from '../app/appTypes';
import { useAuthUiState } from '../state';

function buildOptimisticUserInfo(email: string): UserInfo {
    const normalizedEmail = email.trim().toLowerCase();
    let hash = 0;
    for (let index = 0; index < normalizedEmail.length; index += 1) {
        hash = (hash * 31 + normalizedEmail.charCodeAt(index)) >>> 0;
    }

    return {
        id: Math.max(1, hash % 2147483647),
        email: normalizedEmail,
        username: normalizedEmail,
    };
}

export function useAuth() {
    const qc = useQueryClient();
    const {
        token,
        setToken,
        setUserInfo,
        setShowLogin,
        setLoginEmail,
        setLoginPw,
        setLoginError,
    } = useAuthUiState();

    const authStateQuery = useQuery({
        queryKey: ['auth', 'stored'],
        queryFn: loadStoredAuthState,
        staleTime: Infinity,
    });

    const loginMutation = useMutation({
        mutationFn: async (params: { email: string; password: string }) => {
            const token = await callLoginApi(params.email, params.password);
            return { token, userInfo: buildOptimisticUserInfo(params.email) };
        },
        onSuccess: async ({ token, userInfo: optimisticUserInfo }) => {
            setToken(token);
            setUserInfo(optimisticUserInfo);
            setShowLogin(false);
            await saveStoredAuthState(token, optimisticUserInfo);
            void getCurrentUserApi(token, true)
                .then(async (realUserInfo) => {
                    await saveStoredAuthState(token, realUserInfo);
                    setUserInfo(realUserInfo);
                    qc.invalidateQueries({ queryKey: ['auth'] });
                })
                .catch(() => {
                    qc.invalidateQueries({ queryKey: ['auth'] });
                });
        },
    });

    const restoreSessionMutation = useMutation({
        mutationFn: async () => {
            const RESTORE_ME_TIMEOUT_MS = 8000;
            const isUnauthorizedRestoreError = (error: unknown) => {
                if (!error || typeof error !== 'object') {
                    return false;
                }
                const status = 'status' in error ? (error as { status?: unknown }).status : undefined;
                return status === 401 || status === 403;
            };

            const resolveCurrentUserWithTimeout = async (token: string) => {
                let timeoutId: ReturnType<typeof setTimeout> | null = null;
                try {
                    return await Promise.race<UserInfo>([
                        getCurrentUserApi(token, true),
                        new Promise<UserInfo>((_, reject) => {
                            timeoutId = setTimeout(() => reject(new Error('restore-session-timeout')), RESTORE_ME_TIMEOUT_MS);
                        }),
                    ]);
                } finally {
                    if (timeoutId) {
                        clearTimeout(timeoutId);
                    }
                }
            };

            const storedAuth = await loadStoredAuthState();
            if (!storedAuth) {
                return null;
            }
            try {
                const userInfo = await resolveCurrentUserWithTimeout(storedAuth.token);
                await saveStoredAuthState(storedAuth.token, userInfo);
                return { token: storedAuth.token, userInfo };
            } catch (error) {
                if (isUnauthorizedRestoreError(error)) {
                    // 서버 응답이 401/403 이더라도 사용자가 명시적으로 로그아웃하지 않았다면
                    // 로컬 저장 세션은 유지한다.
                    return { token: storedAuth.token, userInfo: storedAuth.userInfo };
                }
                // 일시적 네트워크/타임아웃 실패시 저장된 세션을 유지
                return { token: storedAuth.token, userInfo: storedAuth.userInfo };
            }
        },
    });

    const logoutMutation = useMutation({
        mutationFn: async () => {
            const currentToken = token.trim();
            if (currentToken) {
                try {
                    await callLogoutApi(currentToken);
                } catch {
                    // 서버 로그아웃 실패여도 클라이언트는 명시적 로그아웃 절차를 계속 진행한다.
                }
            }
            await clearStoredAuthState();
        },
        onSuccess: () => {
            clearCurrentUserCache();
            setToken('');
            setUserInfo(null);
            qc.removeQueries({ queryKey: ['auth'] });
        },
    });

    const signupRequestCodeMutation = useMutation({
        mutationFn: (payload: SignupPayload) => callSignupRequestCodeApi(payload),
    });

    const signupConfirmMutation = useMutation({
        mutationFn: async (params: {
            signupSessionToken: string;
            verificationCode: string;
            profile: Pick<SignupPayload, 'preferred_language' | 'country_code' | 'full_name'>;
        }) => callSignupConfirmApi(params.signupSessionToken, params.verificationCode, params.profile),
    });

    const signupMutation = useMutation({
        mutationFn: (payload: SignupPayload) => callSignupApi(payload),
    });

    const updateProfileMutation = useMutation({
        mutationFn: (params: { token: string; payload: UserProfileUpdatePayload }) =>
            callUpdateMeApi(params.token, params.payload),
        onSuccess: (userInfo, params) => {
            setUserInfo(userInfo);
            clearCurrentUserCache(params.token);
            qc.invalidateQueries({ queryKey: ['auth'] });
        },
    });

    return {
        authStateQuery,
        loginMutation,
        restoreSessionMutation,
        logoutMutation,
        signupMutation,
        signupRequestCodeMutation,
        signupConfirmMutation,
        updateProfileMutation,
        fetchUserByToken: (token: string) => getCurrentUserApi(token, true),
    };
}
