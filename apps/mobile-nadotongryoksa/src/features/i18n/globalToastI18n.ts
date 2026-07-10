/**
 * ToastAndroid.show 전역 i18n — 네이티브 토스트는 React Text 패치 밖이므로 여기서 치환한다.
 */
import { Platform, ToastAndroid } from 'react-native';

import { getUiLang, translateUiSync } from './uiI18n';

function translateToastString(value: string): string {
    if (!value || getUiLang() === 'ko') {
        return value;
    }
    return translateUiSync(value);
}

export function installGlobalToastI18n(): void {
    if (Platform.OS !== 'android') {
        return;
    }
    const toastFn = ToastAndroid.show as typeof ToastAndroid.show & { __wlWrapped?: boolean };
    if (toastFn.__wlWrapped) {
        return;
    }
    const original = ToastAndroid.show.bind(ToastAndroid);
    ToastAndroid.show = (message: string, duration: number) => original(translateToastString(message), duration);
    toastFn.__wlWrapped = true;
}
