// @ts-nocheck
import type { ExpoConfig } from 'expo/config';

declare function require(name: string): any;
declare const __dirname: string;
declare const process: {
    env: Record<string, string | undefined>;
};

const { existsSync, readFileSync } = require('fs') as {
    existsSync: (path: string) => boolean;
    readFileSync: (path: string, encoding: string) => string;
};
const { join } = require('path') as {
    join: (...parts: string[]) => string;
};

const FALLBACK_EAS_PROJECT_ID = '8c9c1cd3-3d79-41a4-be25-eef38d5808d0';
const DEFAULT_MAX_STOP_LOSS_PERCENT = 2;

function isPlaceholderProjectId(value: string): boolean {
    return /^0{8}-0{4}-0{4}-0{4}-0{12}$/.test(value.trim());
}

function readLocalProjectId(): string {
    try {
        const projectFile = join(__dirname, 'eas-project-id.json');
        if (!existsSync(projectFile)) {
            return '';
        }

        const parsed = JSON.parse(readFileSync(projectFile, 'utf-8')) as { projectId?: string };
        const value = String(parsed?.projectId || '').trim();
        return value && !isPlaceholderProjectId(value) ? value : '';
    } catch {
        return '';
    }
}

function pickProjectId(): string {
    const fromEnv = String(process.env.EXPO_PROJECT_ID || process.env.EAS_PROJECT_ID || '').trim();
    if (fromEnv && !isPlaceholderProjectId(fromEnv)) {
        return fromEnv;
    }

    const fromLocal = readLocalProjectId();
    if (fromLocal) {
        return fromLocal;
    }

    return FALLBACK_EAS_PROJECT_ID;
}

function pickMaxStopLossPercent(): number {
    const raw = String(process.env.EXPO_PUBLIC_MAX_STOP_LOSS_PERCENT || '').trim();
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_STOP_LOSS_PERCENT;
}

const resolvedProjectId =
    pickProjectId();

const maxStopLossPercent = pickMaxStopLossPercent();

const config: ExpoConfig = {
    name: 'Stock AI Mobile',
    slug: 'stock-ai-mobile',
    owner: 'parkcheolhong',
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
        bundleIdentifier: 'com.codeai.stockai',
    },
    android: {
        package: 'com.codeai.stockai',
    },
    updates: {
        url: `https://u.expo.dev/${resolvedProjectId}`,
    },
    runtimeVersion: {
        policy: 'appVersion',
    },
    extra: {
        apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://10.0.2.2:3010',
        maxStopLossPercent,
        eas: {
            projectId: resolvedProjectId,
        },
    },
};

export default config;
