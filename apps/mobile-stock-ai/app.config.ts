import type { ExpoConfig } from 'expo/config';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

const OWNER = 'parkcheolhong';
const APP_NAME = 'Stock AI Mobile';
const APP_SLUG = 'stock-ai-mobile';
const BUNDLE_ID = 'com.codeai.stockai';
const DEFAULT_API_URL = 'http://10.0.2.2:3010';

const FALLBACK_EAS_PROJECT_ID = '8c9c1cd3-3d79-41a4-be25-eef38d5808d0';
const DEFAULT_MAX_STOP_LOSS_PERCENT = 2;
const MAX_STOP_LOSS_PERCENT = 100;

function isPlaceholderProjectId(value: string): boolean {
    return /^0{8}-0{4}-0{4}-0{4}-0{12}$/.test(value.trim());
}

function readLocalProjectId(baseDir: string): string {
    try {
        const projectFile = join(baseDir, 'eas-project-id.json');
        if (!existsSync(projectFile)) {
            return '';
        }

        const parsed = JSON.parse(readFileSync(projectFile, 'utf-8')) as { projectId?: string };
        const value = String(parsed.projectId ?? '').trim();
        return value && !isPlaceholderProjectId(value) ? value : '';
    } catch {
        return '';
    }
}

function pickProjectId(env: NodeJS.ProcessEnv, baseDir: string): string {
    const envId = String(env.EXPO_PROJECT_ID ?? env.EAS_PROJECT_ID ?? '').trim();
    if (envId && !isPlaceholderProjectId(envId)) {
        return envId;
    }

    const localId = readLocalProjectId(baseDir);
    if (localId) {
        return localId;
    }

    return FALLBACK_EAS_PROJECT_ID;
}

function pickMaxStopLossPercent(env: NodeJS.ProcessEnv): number {
    const raw = String(env.EXPO_PUBLIC_MAX_STOP_LOSS_PERCENT ?? '').trim();
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
        return DEFAULT_MAX_STOP_LOSS_PERCENT;
    }

    return parsed > 0 && parsed <= MAX_STOP_LOSS_PERCENT
        ? parsed
        : DEFAULT_MAX_STOP_LOSS_PERCENT;
}

const resolvedProjectId = pickProjectId(process.env, __dirname);
const maxStopLossPercent = pickMaxStopLossPercent(process.env);

const config: ExpoConfig = {
    name: APP_NAME,
    slug: APP_SLUG,
    owner: OWNER,
    version: '1.0.0',
    orientation: 'portrait',
    platforms: ['ios', 'android'],
    userInterfaceStyle: 'dark',
    assetBundlePatterns: ['**/*'],
    plugins: [
        'expo-asset',
        [
            'expo-build-properties',
            {
                android: {
                    kotlinVersion: '1.9.25',
                },
            },
        ],
    ],
    ios: {
        supportsTablet: true,
        bundleIdentifier: BUNDLE_ID,
    },
    android: {
        package: BUNDLE_ID,
    },
    updates: {
        url: `https://u.expo.dev/${resolvedProjectId}`,
    },
    runtimeVersion: {
        policy: 'appVersion',
    },
    extra: {
        apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? DEFAULT_API_URL,
        maxStopLossPercent,
        eas: {
            projectId: resolvedProjectId,
        },
    },
};

export default config;