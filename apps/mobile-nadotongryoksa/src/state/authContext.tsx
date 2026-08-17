import React, { createContext, useCallback, useContext, useMemo, useReducer, type ReactNode } from 'react';

import type { AuthModalMode, UserInfo } from '../app/appTypes';

export type AuthUiState = {
    token: string;
    userInfo: UserInfo | null;
    authHydrated: boolean;
    showLogin: boolean;
    authModalMode: AuthModalMode;
    loginEmail: string;
    loginPw: string;
    showLoginPw: boolean;
    loginLoading: boolean;
    loginError: string;
};

type AuthUiStateAction = {
    key: keyof AuthUiState;
    value: AuthUiState[keyof AuthUiState];
};

const INITIAL_AUTH_UI_STATE: AuthUiState = {
    token: '',
    userInfo: null,
    authHydrated: false,
    showLogin: false,
    authModalMode: 'login',
    loginEmail: '',
    loginPw: '',
    showLoginPw: false,
    loginLoading: false,
    loginError: '',
};

function authUiStateReducer(state: AuthUiState, action: AuthUiStateAction): AuthUiState {
    return {
        ...state,
        [action.key]: action.value,
    };
}

type AuthUiContextValue = AuthUiState & {
    setToken: (nextToken: string) => void;
    setUserInfo: (nextUserInfo: UserInfo | null) => void;
    setAuthHydrated: (nextAuthHydrated: boolean) => void;
    setShowLogin: (nextShowLogin: boolean) => void;
    setAuthModalMode: (nextAuthModalMode: AuthModalMode | ((prev: AuthModalMode) => AuthModalMode)) => void;
    setLoginEmail: (nextLoginEmail: string) => void;
    setLoginPw: (nextLoginPw: string) => void;
    setShowLoginPw: (nextShowLoginPw: boolean | ((prev: boolean) => boolean)) => void;
    setLoginLoading: (nextLoginLoading: boolean) => void;
    setLoginError: (nextLoginError: string) => void;
};

const AuthUiContext = createContext<AuthUiContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [authUiState, dispatchAuthUiState] = useReducer(authUiStateReducer, INITIAL_AUTH_UI_STATE);

    const setToken = useCallback((nextToken: string) => {
        dispatchAuthUiState({ key: 'token', value: nextToken });
    }, []);
    const setUserInfo = useCallback((nextUserInfo: UserInfo | null) => {
        dispatchAuthUiState({ key: 'userInfo', value: nextUserInfo });
    }, []);
    const setAuthHydrated = useCallback((nextAuthHydrated: boolean) => {
        dispatchAuthUiState({ key: 'authHydrated', value: nextAuthHydrated });
    }, []);
    const setShowLogin = useCallback((nextShowLogin: boolean) => {
        dispatchAuthUiState({ key: 'showLogin', value: nextShowLogin });
    }, []);
    const setAuthModalMode = useCallback((nextAuthModalMode: AuthModalMode | ((prev: AuthModalMode) => AuthModalMode)) => {
        dispatchAuthUiState({
            key: 'authModalMode',
            value: typeof nextAuthModalMode === 'function' ? nextAuthModalMode(authUiState.authModalMode) : nextAuthModalMode,
        });
    }, [authUiState.authModalMode]);
    const setLoginEmail = useCallback((nextLoginEmail: string) => {
        dispatchAuthUiState({ key: 'loginEmail', value: nextLoginEmail });
    }, []);
    const setLoginPw = useCallback((nextLoginPw: string) => {
        dispatchAuthUiState({ key: 'loginPw', value: nextLoginPw });
    }, []);
    const setShowLoginPw = useCallback((nextShowLoginPw: boolean | ((prev: boolean) => boolean)) => {
        dispatchAuthUiState({
            key: 'showLoginPw',
            value: typeof nextShowLoginPw === 'function' ? nextShowLoginPw(authUiState.showLoginPw) : nextShowLoginPw,
        });
    }, [authUiState.showLoginPw]);
    const setLoginLoading = useCallback((nextLoginLoading: boolean) => {
        dispatchAuthUiState({ key: 'loginLoading', value: nextLoginLoading });
    }, []);
    const setLoginError = useCallback((nextLoginError: string) => {
        dispatchAuthUiState({ key: 'loginError', value: nextLoginError });
    }, []);

    const value = useMemo<AuthUiContextValue>(() => ({
        ...authUiState,
        setToken,
        setUserInfo,
        setAuthHydrated,
        setShowLogin,
        setAuthModalMode,
        setLoginEmail,
        setLoginPw,
        setShowLoginPw,
        setLoginLoading,
        setLoginError,
    }), [
        authUiState,
        setAuthHydrated,
        setAuthModalMode,
        setLoginEmail,
        setLoginError,
        setLoginLoading,
        setLoginPw,
        setShowLogin,
        setShowLoginPw,
        setToken,
        setUserInfo,
    ]);

    return <AuthUiContext.Provider value={value}>{children}</AuthUiContext.Provider>;
}

export function useAuthUiState(): AuthUiContextValue {
    const ctx = useContext(AuthUiContext);
    if (!ctx) {
        throw new Error('useAuthUiState must be used within AuthProvider');
    }
    return ctx;
}
