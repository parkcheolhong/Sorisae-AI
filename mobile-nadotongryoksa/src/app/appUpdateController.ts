// App.tsx 에서 분리한 인앱 APK 업데이트 컨트롤러(부수효과: Alert/Toast).
import { Alert, Platform, ToastAndroid } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
    fetchLatestApkMetadata,
    isRemoteApkNewer as isRemoteApkBuildNewer,
    downloadAndInstallLatestApk,
} from '../features/app-update/appUpdate';
import {
    API_BASE,
    WORLDLINGO_APP_NAME,
    APP_VERSION_NUMBER,
    APP_BUILD_NUMBER,
    APP_VERSION_LABEL,
    ENABLE_IN_APP_UPDATE_PROMPT,
    VERSION_IGNORE_KEY,
    VERSION_SNOOZE_BUILD_KEY,
} from './appConstants';

export async function runApkInAppInstall() {
    const showProgress = (label: string) => {
        if (Platform.OS === 'android') {
            ToastAndroid.show(label, ToastAndroid.SHORT);
        }
    };
    showProgress('업데이트를 내려받는 중…');
    let lastShown = 0;
    const result = await downloadAndInstallLatestApk(API_BASE, {
        onProgress: (ratio) => {
            const pct = Math.round(ratio * 100);
            // 25% 단위로만 토스트 → 과도한 알림 방지
            if (pct >= lastShown + 25 && pct < 100) {
                lastShown = pct;
                showProgress(`업데이트 다운로드 ${pct}%`);
            }
        },
    });
    if (!result.ok) {
        Alert.alert(
            `${WORLDLINGO_APP_NAME} 업데이트`,
            `업데이트 설치를 시작하지 못했습니다.\n${result.error ?? ''}\n\n잠시 후 다시 시도해주세요.`,
            [{ text: '확인', style: 'default' }],
        );
    } else {
        showProgress('설치 화면을 엽니다…');
    }
}

export async function checkForAppUpdate() {
    try {
        if (!ENABLE_IN_APP_UPDATE_PROMPT) {
            return;
        }

        const ignored = await AsyncStorage.getItem(VERSION_IGNORE_KEY);
        if (ignored === '1') {
            return; // 사용자가 업데이트 확인을 영구 비활성화했음
        }

        // 마켓플레이스 SSOT 메타데이터를 직접 조회 (projects/demo_url 의존 제거).
        const metadata = await fetchLatestApkMetadata(API_BASE);
        if (!metadata) {
            return;
        }
        const currentBuild = Number.parseInt(APP_BUILD_NUMBER, 10) || 0;
        if (!isRemoteApkBuildNewer(APP_VERSION_NUMBER, currentBuild, metadata)) {
            return;
        }

        // 같은 빌드를 이미 "나중에"로 스누즈했으면 재알림하지 않는다.
        const snoozed = await AsyncStorage.getItem(VERSION_SNOOZE_BUILD_KEY);
        if (snoozed && metadata.buildNumber != null && Number.parseInt(snoozed, 10) === metadata.buildNumber) {
            return;
        }

        const remoteVersionLabel = `v${String(metadata.versionName ?? '').trim()} · build ${String(metadata.buildNumber ?? '').trim()}`;
        Alert.alert(
            `${WORLDLINGO_APP_NAME} 업데이트`,
            `새 버전 ${remoteVersionLabel} 이(가) 준비되었습니다.\n현재 버전: ${APP_VERSION_LABEL}\n\n지금 업그레이드하시겠어요? (앱 안에서 바로 설치됩니다)`,
            [
                {
                    text: '나중에',
                    style: 'cancel',
                    onPress: () => {
                        if (metadata.buildNumber != null) {
                            AsyncStorage.setItem(VERSION_SNOOZE_BUILD_KEY, String(metadata.buildNumber)).catch(
                                () => { /* no-op */ },
                            );
                        }
                    },
                },
                {
                    text: '업그레이드',
                    style: 'default',
                    onPress: () => {
                        runApkInAppInstall().catch((err) =>
                            console.error('인앱 업데이트 실패:', err),
                        );
                    },
                },
            ],
        );
    } catch (err) {
        // 버전 체크 실패는 무시
        console.error('버전 체크 오류:', err);
    }
}
