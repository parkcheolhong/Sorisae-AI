import { useCallback, useState } from 'react';
import { Alert, Linking, PermissionsAndroid, Platform } from 'react-native';
import { Audio } from 'expo-av';
import * as Location from 'expo-location';

export type PermissionType = 'RECORD_AUDIO' | 'ACCESS_FINE_LOCATION' | 'ACCESS_COARSE_LOCATION' | 'POST_NOTIFICATIONS';

/**
 * Per-feature 권한 체크 훅
 * 각 기능에서 필요한 권한을 요청하고, 결과를 반환합니다.
 *
 * @param permissions 필요한 권한 배열
 * @param featureName 기능명 (에러 메시지에 사용)
 * @returns {Promise<boolean>} 권한 승인 여부 (true=승인, false=거부)
 *
 * @example
 * const [hasPermission, requestPermission] = usePermissionCheck(
 *   ['RECORD_AUDIO'],
 *   'VoIP 통화'
 * );
 * 
 * const startCall = async () => {
 *   if (await requestPermission()) {
 *     // 통화 시작
 *   }
 * };
 */
export function usePermissionCheck() {
    const [permissionError, setPermissionError] = useState('');

    const requestPermissions = useCallback(
        async (
            requiredPermissions: PermissionType[],
            featureName: string,
            onError?: (message: string) => void,
        ): Promise<boolean> => {
            setPermissionError('');

            try {
                if (requiredPermissions.some((permission) => permission === 'ACCESS_FINE_LOCATION' || permission === 'ACCESS_COARSE_LOCATION')) {
                    try {
                        const current = await Location.getForegroundPermissionsAsync();
                        const result = current.status === 'granted'
                            ? current
                            : await Location.requestForegroundPermissionsAsync();
                        if (result.status !== 'granted') {
                            const message = `${featureName}을(를) 위해 위치 권한이 필요합니다.`;
                            setPermissionError(message);
                            if (onError) onError(message);

                            Alert.alert(
                                '위치 권한 필요',
                                result.canAskAgain === false
                                    ? `${message}\nAndroid 설정에서 WorldLingo 위치 권한을 허용해 주세요.`
                                    : message,
                                [
                                    ...(result.canAskAgain === false ? [{ text: '설정 열기', onPress: () => Linking.openSettings() }] : []),
                                    { text: '확인', style: 'cancel' },
                                ],
                            );
                            return false;
                        }
                    } catch (error) {
                        console.error('Location permission request failed:', error);
                        return false;
                    }
                }

                for (const permission of requiredPermissions) {
                    let granted = false;

                    switch (permission) {
                        case 'RECORD_AUDIO': {
                            try {
                                const result = await Audio.requestPermissionsAsync();
                                granted = result.granted;
                                if (!granted) {
                                    const message = `${featureName}을(를) 위해 마이크 권한이 필요합니다.`;
                                    setPermissionError(message);
                                    if (onError) onError(message);

                                    // 한 번 이상 거부했으므로 설정 오픈 권유
                                    Alert.alert(
                                        '마이크 권한 필요',
                                        message,
                                        [
                                            { text: '설정 열기', onPress: () => Linking.openSettings() },
                                            { text: '취소', style: 'cancel' },
                                        ],
                                    );
                                    return false;
                                }
                            } catch (error) {
                                console.error('Audio permission request failed:', error);
                                return false;
                            }
                            break;
                        }

                        case 'ACCESS_FINE_LOCATION':
                        case 'ACCESS_COARSE_LOCATION': {
                            granted = true;
                            break;
                        }

                        case 'POST_NOTIFICATIONS': {
                            // Android 13+에서만 필요
                            if (Platform.OS === 'android' && Number(Platform.Version) >= 33) {
                                try {
                                    const notificationPermission = (PermissionsAndroid.PERMISSIONS as any)
                                        .POST_NOTIFICATIONS;
                                    if (notificationPermission) {
                                        const result = await PermissionsAndroid.request(
                                            notificationPermission,
                                            {
                                                title: '알림 권한 요청',
                                                message: `${featureName}을(를) 위해 알림 권한이 필요합니다.`,
                                                buttonPositive: '허가',
                                                buttonNegative: '거부',
                                            },
                                        );
                                        granted = result === PermissionsAndroid.RESULTS.GRANTED;
                                        if (!granted) {
                                            const message = `${featureName}을(를) 위해 알림 권한이 필요합니다.`;
                                            setPermissionError(message);
                                            if (onError) onError(message);
                                            return false;
                                        }
                                    } else {
                                        // POST_NOTIFICATIONS 권한이 없으면 그냥 진행 (API 30 이하)
                                        granted = true;
                                    }
                                } catch (error) {
                                    console.error('Notification permission request failed:', error);
                                    return false;
                                }
                            } else {
                                // Android 12 이하는 권한 필요 없음
                                granted = true;
                            }
                            break;
                        }

                        default:
                            console.warn(`Unknown permission type: ${permission}`);
                            return false;
                    }

                    // 한 개 권한이 거부되면 즉시 false 반환
                    if (!granted) {
                        return false;
                    }
                }

                // 모든 권한 승인됨
                return true;
            } catch (error) {
                console.error('Unexpected permission check error:', error);
                return false;
            }
        },
        [],
    );

    return {
        requestPermissions,
        permissionError,
        setPermissionError,
    };
}

/**
 * 단순 권한 체크 (dialog 없이 현재 상태만 확인)
 * @param permission 권한 타입
 * @returns 현재 권한 상태
 */
export async function checkPermissionStatus(permission: PermissionType): Promise<boolean> {
    try {
        switch (permission) {
            case 'RECORD_AUDIO': {
                const result = await Audio.getPermissionsAsync();
                return result.granted;
            }
            case 'ACCESS_FINE_LOCATION': {
                const result = await Location.getForegroundPermissionsAsync();
                return result.status === 'granted';
            }
            case 'ACCESS_COARSE_LOCATION': {
                const result = await Location.getForegroundPermissionsAsync();
                return result.status === 'granted';
            }
            case 'POST_NOTIFICATIONS': {
                if (Platform.OS === 'android' && Number(Platform.Version) >= 33) {
                    try {
                        const notificationPermission = (PermissionsAndroid.PERMISSIONS as any)
                            .POST_NOTIFICATIONS;
                        if (notificationPermission) {
                            return await PermissionsAndroid.check(notificationPermission);
                        }
                    } catch (error) {
                        console.error('Failed to check notification permission:', error);
                    }
                }
                return true; // Android 12 이하는 true
            }
            default:
                return false;
        }
    } catch (error) {
        console.error(`Failed to check ${permission} status:`, error);
        return false;
    }
}
