/**
 * 소리새 호출어(KWS) 설정 영속 — SettingsScreen onSaveKws ↔ COMPANION_KWS_* AsyncStorage SSOT.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

import {
    COMPANION_KWS_MODEL_PATH_STORAGE_KEY,
    COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY,
    COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY,
    COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY,
    COMPANION_KWS_PROVIDER_STORAGE_KEY,
    DEFAULT_COMPANION_KWS_MODEL_PATH,
} from '../../app/appConstants';
import type { OnDeviceKwsProvider } from '../../native/onDeviceKws';

export interface CompanionKwsSettings {
    provider: OnDeviceKwsProvider;
    modelPath: string;
    porcupineAccessKey: string;
    porcupineKeywordPaths: string[];
}

export const DEFAULT_COMPANION_KWS_SETTINGS: CompanionKwsSettings = {
    provider: 'vosk',
    modelPath: DEFAULT_COMPANION_KWS_MODEL_PATH,
    porcupineAccessKey: '',
    porcupineKeywordPaths: [],
};

function normalizeCompanionKwsSettings(input: {
    provider: OnDeviceKwsProvider;
    modelPath: string;
    porcupineAccessKey: string;
    porcupineKeywordPaths: string[];
}): CompanionKwsSettings {
    const normalizedPorcupineKeywordPaths = (input.porcupineKeywordPaths || [])
        .map((path) => String(path || '').trim())
        .filter((path) => path.length > 0);
    return {
        provider: input.provider,
        modelPath: String(input.modelPath || '').trim(),
        porcupineAccessKey: String(input.porcupineAccessKey || '').trim(),
        porcupineKeywordPaths: normalizedPorcupineKeywordPaths,
    };
}

export async function loadCompanionKwsSettings(): Promise<CompanionKwsSettings> {
    try {
        const [
            savedModelPath,
            savedProvider,
            savedAccessKey,
            savedKeywordPath,
            savedKeywordPathsJson,
        ] = await Promise.all([
            AsyncStorage.getItem(COMPANION_KWS_MODEL_PATH_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PROVIDER_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY),
        ]);

        const providerRaw = String(savedProvider || '').trim().toLowerCase();
        const provider: OnDeviceKwsProvider = providerRaw === 'porcupine' ? 'porcupine' : 'vosk';
        const modelPath = String(savedModelPath || '').trim() || DEFAULT_COMPANION_KWS_MODEL_PATH;
        const porcupineAccessKey = String(savedAccessKey || '').trim();

        let porcupineKeywordPaths: string[] = [];
        try {
            const parsed = JSON.parse(String(savedKeywordPathsJson || '[]')) as unknown;
            if (Array.isArray(parsed)) {
                porcupineKeywordPaths = parsed
                    .map((item) => String(item || '').trim())
                    .filter((item) => item.length > 0);
            }
        } catch {
            porcupineKeywordPaths = [];
        }
        if (porcupineKeywordPaths.length === 0) {
            const keywordPath = String(savedKeywordPath || '').trim();
            if (keywordPath) {
                porcupineKeywordPaths = [keywordPath];
            }
        }

        return { provider, modelPath, porcupineAccessKey, porcupineKeywordPaths };
    } catch {
        return { ...DEFAULT_COMPANION_KWS_SETTINGS };
    }
}

export async function persistCompanionKwsSettings(input: {
    provider: OnDeviceKwsProvider;
    modelPath: string;
    porcupineAccessKey: string;
    porcupineKeywordPaths: string[];
}): Promise<CompanionKwsSettings> {
    const normalized = normalizeCompanionKwsSettings(input);
    const firstKeywordPath = normalized.porcupineKeywordPaths[0] || '';

    await AsyncStorage.multiSet([
        [COMPANION_KWS_PROVIDER_STORAGE_KEY, normalized.provider],
        [COMPANION_KWS_MODEL_PATH_STORAGE_KEY, normalized.modelPath],
        [COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY, normalized.porcupineAccessKey],
        [COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY, firstKeywordPath],
        [COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY, JSON.stringify(normalized.porcupineKeywordPaths)],
    ]);

    return normalized;
}
