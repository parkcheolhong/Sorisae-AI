import React, { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

type AppUiContextValue = {
    showPasswordSecurity: boolean;
    setShowPasswordSecurity: (next: boolean) => void;
    passwordSecurityMode: 'recover' | 'change';
    setPasswordSecurityMode: (next: 'recover' | 'change') => void;
    showMyInfo: boolean;
    setShowMyInfo: (next: boolean | ((prev: boolean) => boolean)) => void;
    showDataSources: boolean;
    setShowDataSources: (next: boolean) => void;
    settingsTabOpen: boolean;
    setSettingsTabOpen: (next: boolean) => void;
};

const AppUiContext = createContext<AppUiContextValue | null>(null);

export function AppUiProvider({ children }: { children: ReactNode }) {
    const [showPasswordSecurity, setShowPasswordSecurity] = useState(false);
    const [passwordSecurityMode, setPasswordSecurityMode] = useState<'recover' | 'change'>('recover');
    const [showMyInfo, setShowMyInfoState] = useState(false);
    const [showDataSources, setShowDataSources] = useState(false);
    const [settingsTabOpen, setSettingsTabOpen] = useState(false);

    const setShowMyInfo = useCallback((next: boolean | ((prev: boolean) => boolean)) => {
        setShowMyInfoState((prev) => (typeof next === 'function' ? next(prev) : next));
    }, []);

    const value = useMemo<AppUiContextValue>(() => ({
        showPasswordSecurity,
        setShowPasswordSecurity,
        passwordSecurityMode,
        setPasswordSecurityMode,
        showMyInfo,
        setShowMyInfo,
        showDataSources,
        setShowDataSources,
        settingsTabOpen,
        setSettingsTabOpen,
    }), [passwordSecurityMode, settingsTabOpen, setShowDataSources, setSettingsTabOpen, setPasswordSecurityMode, setShowMyInfo, showDataSources, showMyInfo, showPasswordSecurity]);

    return <AppUiContext.Provider value={value}>{children}</AppUiContext.Provider>;
}

export function useAppUiState(): AppUiContextValue {
    const ctx = useContext(AppUiContext);
    if (!ctx) {
        throw new Error('useAppUiState must be used within AppUiProvider');
    }
    return ctx;
}
