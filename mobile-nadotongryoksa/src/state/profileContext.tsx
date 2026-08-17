import React, { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

import type { LangCode } from '../features/language/languageCatalog';
import type { SignupCountryCode } from '../features/country/countryCatalog';

type ProfileStateValue = {
    profilePreferredLanguage: LangCode;
    setProfilePreferredLanguage: (next: LangCode) => void;
    profileCountryCode: SignupCountryCode;
    setProfileCountryCode: (next: SignupCountryCode) => void;
    profileSaving: boolean;
    setProfileSaving: (next: boolean) => void;
    profileMessage: string;
    setProfileMessage: (next: string) => void;
};

const ProfileContext = createContext<ProfileStateValue | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
    const [profilePreferredLanguage, setProfilePreferredLanguage] = useState<LangCode>('ko');
    const [profileCountryCode, setProfileCountryCodeState] = useState<SignupCountryCode>('KR');
    const [profileSaving, setProfileSaving] = useState(false);
    const [profileMessage, setProfileMessage] = useState('');

    const setProfileCountryCode = useCallback((next: SignupCountryCode) => {
        setProfileCountryCodeState(next);
    }, []);

    const value = useMemo<ProfileStateValue>(() => ({
        profilePreferredLanguage,
        setProfilePreferredLanguage,
        profileCountryCode,
        setProfileCountryCode,
        profileSaving,
        setProfileSaving,
        profileMessage,
        setProfileMessage,
    }), [
        profileCountryCode,
        profileMessage,
        profilePreferredLanguage,
        profileSaving,
        setProfileCountryCode,
    ]);

    return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfileState(): ProfileStateValue {
    const ctx = useContext(ProfileContext);
    if (!ctx) {
        throw new Error('useProfileState must be used within ProfileProvider');
    }
    return ctx;
}
