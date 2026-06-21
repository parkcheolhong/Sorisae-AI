// 인앱 자동 업데이트 — 마켓플레이스에 올린 빌드본을 설치된 단말이 스스로 감지하고,
// "업그레이드"를 누르면 곧장 새 APK 를 내려받아 시스템 설치 화면으로 연결한다.
// 매번 마켓에 들어가 수동으로 받을 필요가 없도록, 단말이 알아서 최신 빌드를 찾아간다.
//
// 백엔드 SSOT (로그인 불필요):
//   - GET /api/marketplace/latest-apk-metadata  → 최신 버전 메타(versionName/buildNumber)
//   - GET /api/marketplace/latest.apk           → 최신 APK 바이너리(고정 URL)
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as IntentLauncher from 'expo-intent-launcher';

export const LATEST_APK_METADATA_PATH = '/api/marketplace/latest-apk-metadata';
export const LATEST_APK_DOWNLOAD_PATH = '/api/marketplace/latest.apk';

const APK_MIME_TYPE = 'application/vnd.android.package-archive';
// FLAG_GRANT_READ_URI_PERMISSION — content:// URI 를 시스템 설치기에 읽기 허용.
const FLAG_GRANT_READ_URI_PERMISSION = 1;
const ACTION_INSTALL_PACKAGE = 'android.intent.action.INSTALL_PACKAGE';
const ACTION_VIEW = 'android.intent.action.VIEW';

export interface LatestApkMetadata {
    versionName: string | null;
    buildNumber: number | null;
    downloadPath: string | null;
    publishedAt: string | null;
    sizeBytes: number | null;
    apkFilename: string | null;
}

const normalizeBase = (apiBase: string): string => apiBase.replace(/\/+$/, '');

/** 최신 APK 메타데이터 조회 (캐시 무효화). */
export async function fetchLatestApkMetadata(apiBase: string): Promise<LatestApkMetadata | null> {
    try {
        const url = `${normalizeBase(apiBase)}${LATEST_APK_METADATA_PATH}`;
        const response = await fetch(url, {
            headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
        });
        if (!response.ok) {
            return null;
        }
        const data = await response.json().catch(() => null);
        if (!data || typeof data !== 'object') {
            return null;
        }
        const rawBuild = (data as Record<string, unknown>).build_number;
        const parsedBuild = Number.parseInt(String(rawBuild ?? ''), 10);
        return {
            versionName: data.version_name != null ? String(data.version_name).trim() : null,
            buildNumber: Number.isFinite(parsedBuild) ? parsedBuild : null,
            downloadPath: data.download_path != null ? String(data.download_path) : null,
            publishedAt: data.published_at != null ? String(data.published_at) : null,
            sizeBytes:
                typeof data.size_bytes === 'number'
                    ? data.size_bytes
                    : Number.parseInt(String(data.size_bytes ?? ''), 10) || null,
            apkFilename: data.apk_filename != null ? String(data.apk_filename) : null,
        };
    } catch {
        return null;
    }
}

const parseTriplet = (value: string): number[] => {
    const match = String(value || '').trim().match(/^(\d+)\.(\d+)\.(\d+)/);
    if (!match) {
        return [0, 0, 0];
    }
    return match.slice(1, 4).map((part) => Number.parseInt(part, 10) || 0);
};

const compareSemver = (left: string, right: string): number => {
    const a = parseTriplet(left);
    const b = parseTriplet(right);
    for (let i = 0; i < 3; i += 1) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
};

/** 원격 빌드가 현재 설치본보다 최신인지 판정. buildNumber(versionCode) 를 1차 기준으로 본다. */
export function isRemoteApkNewer(
    currentVersion: string,
    currentBuild: number,
    remote: LatestApkMetadata | null,
): boolean {
    if (!remote) {
        return false;
    }
    // versionCode 가 둘 다 있으면 그것만으로 판정(가장 신뢰 가능한 단조 증가값).
    if (typeof remote.buildNumber === 'number' && Number.isFinite(currentBuild) && currentBuild > 0) {
        if (remote.buildNumber !== currentBuild) {
            return remote.buildNumber > currentBuild;
        }
    }
    if (!remote.versionName) {
        return false;
    }
    const versionDelta = compareSemver(remote.versionName, currentVersion);
    if (versionDelta !== 0) {
        return versionDelta > 0;
    }
    return typeof remote.buildNumber === 'number' && remote.buildNumber > currentBuild;
}

export interface DownloadAndInstallOptions {
    onProgress?: (ratio: number) => void;
}

export interface DownloadAndInstallResult {
    ok: boolean;
    error?: string;
}

/**
 * 최신 APK 를 내려받아 시스템 패키지 설치 화면으로 연결한다.
 * Android 전용. 다운로드 진행률은 onProgress 로 0~1 콜백.
 */
export async function downloadAndInstallLatestApk(
    apiBase: string,
    options: DownloadAndInstallOptions = {},
): Promise<DownloadAndInstallResult> {
    if (Platform.OS !== 'android') {
        return { ok: false, error: '안드로이드에서만 인앱 설치가 지원됩니다.' };
    }

    const downloadUrl = `${normalizeBase(apiBase)}${LATEST_APK_DOWNLOAD_PATH}`;
    const baseDir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory;
    if (!baseDir) {
        return { ok: false, error: '저장 공간을 찾을 수 없습니다.' };
    }
    // 매 시도마다 새 파일명 → 이전 잔여물/캐시 충돌 방지.
    const targetUri = `${baseDir}worldlinco-update-${Date.now()}.apk`;

    try {
        const downloadResumable = FileSystem.createDownloadResumable(
            downloadUrl,
            targetUri,
            {},
            (progress) => {
                if (options.onProgress && progress.totalBytesExpectedToWrite > 0) {
                    const ratio =
                        progress.totalBytesWritten / progress.totalBytesExpectedToWrite;
                    options.onProgress(Math.max(0, Math.min(1, ratio)));
                }
            },
        );

        const result = await downloadResumable.downloadAsync();
        if (!result || !result.uri) {
            return { ok: false, error: 'APK 다운로드에 실패했습니다.' };
        }

        const info = await FileSystem.getInfoAsync(result.uri);
        if (!info.exists || (typeof info.size === 'number' && info.size < 1024)) {
            return { ok: false, error: '내려받은 파일이 손상되었습니다. 다시 시도해주세요.' };
        }

        // content:// URI 로 변환해야 Android 7+ 시스템 설치기가 접근 가능.
        const contentUri = await FileSystem.getContentUriAsync(result.uri);

        // 1차: INSTALL_PACKAGE (설치 전용 화면). 일부 단말/버전에서 미해결 시 VIEW 로 폴백.
        try {
            await IntentLauncher.startActivityAsync(ACTION_INSTALL_PACKAGE, {
                data: contentUri,
                flags: FLAG_GRANT_READ_URI_PERMISSION,
                type: APK_MIME_TYPE,
            });
            return { ok: true };
        } catch {
            await IntentLauncher.startActivityAsync(ACTION_VIEW, {
                data: contentUri,
                flags: FLAG_GRANT_READ_URI_PERMISSION,
                type: APK_MIME_TYPE,
            });
            return { ok: true };
        }
    } catch (error) {
        return {
            ok: false,
            error: error instanceof Error ? error.message : '업데이트 설치 중 오류가 발생했습니다.',
        };
    }
}
