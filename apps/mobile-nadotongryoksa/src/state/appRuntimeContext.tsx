import React, { createContext, useContext, useMemo, type ReactNode } from 'react';

import { API_BASE } from '../app/appConstants';
import { AppUiProvider, useAppUiState } from './appUiContext';
import { AuthProvider, useAuthUiState } from './authContext';
import { ProfileProvider, useProfileState } from './profileContext';

type AppRuntimeContextValue = {
    apiBase: string;
    auth: ReturnType<typeof useAuthUiState>;
    appUi: ReturnType<typeof useAppUiState>;
    profile: ReturnType<typeof useProfileState>;
};

const AppRuntimeContext = createContext<AppRuntimeContextValue | null>(null);

function AppRuntimeInner({ children }: { children: ReactNode }) {
    const auth = useAuthUiState();
    const appUi = useAppUiState();
    const profile = useProfileState();

    const value = useMemo<AppRuntimeContextValue>(() => ({
        apiBase: API_BASE,
        auth,
        appUi,
        profile,
    }), [auth, appUi, profile]);

    return <AppRuntimeContext.Provider value={value}>{children}</AppRuntimeContext.Provider>;
}

export function AppRuntimeProvider({ children }: { children: ReactNode }) {
    return (
        <AuthProvider>
            <AppUiProvider>
                <ProfileProvider>
                    <AppRuntimeInner>{children}</AppRuntimeInner>
                </ProfileProvider>
            </AppUiProvider>
        </AuthProvider>
    );
}

export function useAppRuntime(): AppRuntimeContextValue {
    const ctx = useContext(AppRuntimeContext);
    if (!ctx) {
        throw new Error('useAppRuntime must be used within AppRuntimeProvider');
    }
    return ctx;
}
