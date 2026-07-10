import 'react-native';

declare module 'react-native' {
    interface TextProps {
        /** featureUiCatalog/settings 카탈로그 문자열 — 전역 Text i18n 패치를 건너뛴다. */
        wlLocalized?: boolean;
        /** 레거시 alias — wlLocalized 와 동일 */
        noI18n?: boolean;
    }

    interface TextInputProps {
        wlLocalized?: boolean;
        noI18n?: boolean;
    }
}
