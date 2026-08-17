import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';

import {
    isBiometricLoginEnabled,
    loadBiometricCredentials,
    saveBiometricCredentials,
    setBiometricLoginEnabled,
} from '../auth/biometricGate';

jest.mock('@react-native-async-storage/async-storage', () => ({
    __esModule: true,
    default: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
    },
}));

jest.mock('expo-local-authentication', () => ({
    hasHardwareAsync: jest.fn(),
    isEnrolledAsync: jest.fn(),
    authenticateAsync: jest.fn(),
}));

jest.mock('expo-secure-store', () => ({
    setItemAsync: jest.fn(),
    getItemAsync: jest.fn(),
    deleteItemAsync: jest.fn(),
}));

describe('biometricGate', () => {
    let asyncStorage: Map<string, string>;
    let secureStore: Map<string, string>;

    beforeEach(() => {
        jest.clearAllMocks();
        asyncStorage = new Map();
        secureStore = new Map();

        (AsyncStorage.getItem as jest.MockedFunction<typeof AsyncStorage.getItem>).mockImplementation(
            async (key: string) => asyncStorage.get(key) ?? null,
        );
        (AsyncStorage.setItem as jest.MockedFunction<typeof AsyncStorage.setItem>).mockImplementation(
            async (key: string, value: string) => {
                asyncStorage.set(key, value);
            },
        );
        (AsyncStorage.removeItem as jest.MockedFunction<typeof AsyncStorage.removeItem>).mockImplementation(
            async (key: string) => {
                asyncStorage.delete(key);
            },
        );
        (LocalAuthentication.hasHardwareAsync as jest.MockedFunction<typeof LocalAuthentication.hasHardwareAsync>)
            .mockResolvedValue(true);
        (LocalAuthentication.isEnrolledAsync as jest.MockedFunction<typeof LocalAuthentication.isEnrolledAsync>)
            .mockResolvedValue(true);
        (SecureStore.setItemAsync as jest.MockedFunction<typeof SecureStore.setItemAsync>).mockImplementation(
            async (key: string, value: string) => {
                secureStore.set(key, value);
            },
        );
        (SecureStore.getItemAsync as jest.MockedFunction<typeof SecureStore.getItemAsync>).mockImplementation(
            async (key: string) => secureStore.get(key) ?? null,
        );
        (SecureStore.deleteItemAsync as jest.MockedFunction<typeof SecureStore.deleteItemAsync>).mockImplementation(
            async (key: string) => {
                secureStore.delete(key);
            },
        );
    });

    it('removes saved credentials when biometric login is disabled during logout', async () => {
        await saveBiometricCredentials({ email: 'user@example.com', password: 'old-password' });
        await expect(isBiometricLoginEnabled()).resolves.toBe(true);
        await expect(loadBiometricCredentials()).resolves.toEqual({
            email: 'user@example.com',
            password: 'old-password',
        });

        await setBiometricLoginEnabled(false);

        await expect(isBiometricLoginEnabled()).resolves.toBe(false);
        await expect(loadBiometricCredentials()).resolves.toBeNull();
        expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('worldlinco_biometric_credentials_v1');
    });
});
