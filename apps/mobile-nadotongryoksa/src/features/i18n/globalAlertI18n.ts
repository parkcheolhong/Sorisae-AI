/**
 * Alert.alert 전역 i18n — 네이티브 모달은 React Text 패치 밖이므로 여기서 치환한다.
 */
import { Alert, type AlertButton, type AlertOptions } from 'react-native';

import { getUiLang, translateUiSync } from './uiI18n';

function translateAlertString(value: string | undefined): string | undefined {
    if (!value || getUiLang() === 'ko') {
        return value;
    }
    return translateUiSync(value);
}

export function installGlobalAlertI18n(): void {
    const alertFn = Alert.alert as typeof Alert.alert & { __wlWrapped?: boolean };
    if (alertFn.__wlWrapped) {
        return;
    }
    const original = Alert.alert.bind(Alert);
    Alert.alert = (
        title?: string,
        message?: string,
        buttons?: AlertButton[],
        options?: AlertOptions,
    ) => original(
        translateAlertString(title),
        translateAlertString(message),
        buttons?.map((button) => ({
            ...button,
            text: typeof button.text === 'string' ? (translateAlertString(button.text) ?? button.text) : button.text,
        })),
        options,
    );
    alertFn.__wlWrapped = true;
}
