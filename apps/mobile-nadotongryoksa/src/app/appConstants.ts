// App.tsx 에서 분리한 앱 상수(브랜딩/버전/스토리지 키/딥링크 경로/플래그/OCR 디버그).
import Constants from 'expo-constants';
import { WORLDLINGO_BRAND_NAME, WORLDLINGO_ENGINE_LABEL } from '../constants/worldlincoBrand';
import type { SearchCategory } from '../features/travel-booking/types';
import type { VoipGenderOption } from '../features/profile/profileFormatters';
import type { VoiceLicenseMode, VoiceOutputScope } from './appTypes';

export const PRODUCTION_API_BASE = 'https://metanova1004.com';
export const PRODUCTION_WEB_BASE = 'https://metanova1004.com';

function normalizeApiBaseUrl(raw: string): string {
    const trimmed = String(raw || '').trim().replace(/\/+$/, '');
    if (!trimmed) {
        return PRODUCTION_API_BASE;
    }
    if (!/^https?:\/\//i.test(trimmed)) {
        return PRODUCTION_API_BASE;
    }
    // 릴리스 APK: 로컬/에뮬레이터·사설 LAN 은 운영 URL로 강제 (container-dev 채널만 예외)
    const releaseChannel = String(process.env.EXPO_PUBLIC_RELEASE_CHANNEL || '').trim().toLowerCase();
    const isContainerDev = releaseChannel === 'container-dev';
    if (!__DEV__ && !isContainerDev) {
        if (/\/\/(10\.0\.2\.2|127\.0\.0\.1|localhost)(:\d+)?(\/|$)/i.test(trimmed)) {
            return PRODUCTION_API_BASE;
        }
        if (/\/\/(172\.|10\.|192\.168\.)/i.test(trimmed)) {
            return PRODUCTION_API_BASE;
        }
    } else if (!__DEV__ && /\/\/(10\.0\.2\.2|127\.0\.0\.1|localhost)(:\d+)?(\/|$)/i.test(trimmed)) {
        return PRODUCTION_API_BASE;
    }
    return trimmed;
}

export const API_BASE: string = normalizeApiBaseUrl(
    (process.env.EXPO_PUBLIC_API_BASE_URL || '').trim()
    || String(Constants.expoConfig?.extra?.apiBaseUrl || '').trim()
    || PRODUCTION_API_BASE,
);

export const WORLDLINGO_APP_NAME = WORLDLINGO_BRAND_NAME;
export const APP_VERSION_NUMBER = String(
    Constants.expoConfig?.version
    ?? Constants.nativeAppVersion
    ?? '1.0.68',
);
export const APP_BUILD_NUMBER = String(
    Constants.expoConfig?.android?.versionCode
    ?? Constants.nativeBuildVersion
    ?? '98',
);
export const APP_VERSION_LABEL = `v${APP_VERSION_NUMBER} · build ${APP_BUILD_NUMBER}`;
export const APP_FOOTER_BRAND = `${WORLDLINGO_BRAND_NAME} v${APP_VERSION_NUMBER} · ${WORLDLINGO_ENGINE_LABEL}`;
export const APP_FOOTER_BRAND_KO = `${WORLDLINGO_BRAND_NAME} v${APP_VERSION_NUMBER} · ${WORLDLINGO_ENGINE_LABEL}`;
export const VERSION_CHECK_KEY = 'app_latest_version_check';
export const VERSION_IGNORE_KEY = 'app_version_ignore';
export const AUTH_STORAGE_KEY = 'nadot_auth_state';
// 월드링코 설정(소리/진동/무음 등)을 단말에 저장하는 키.
export const WORLDLINCO_SETTINGS_STORAGE_KEY = 'worldlinco_settings_v1';
export const ACTIVE_VOIP_CALL_STORAGE_KEY = 'nadot_active_voip_call_v1';
export const VOIP_VALIDATION_FRIEND_CALL_BYPASS_KEY = 'nadot_voip_validation_friend_call_bypass_v1';
// VoIP/채팅/통역 "내 언어" SSOT는 설정 탭(국가·언어) → fromLang. 단말 로컬 오버라이드는 사용하지 않는다.
export const VOIP_LOCAL_LANG_STORAGE_KEY = 'nadot_voip_local_lang_v1';
/** 로그인 후 백그라운드 웨이크워드(홈 호명) — 기본 켬. 홈에서 자동 대기 후 호출어로 소리새를 깨운다. */
export const COMPANION_HOME_WAKE_ENABLED = true;

export const COMPANION_KWS_MODEL_PATH_STORAGE_KEY = 'nadot_companion_kws_model_path_v1';
export const COMPANION_KWS_PROVIDER_STORAGE_KEY = 'nadot_companion_kws_provider_v1';
export const COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY = 'nadot_companion_kws_porcupine_access_key_v1';
export const COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY = 'nadot_companion_kws_porcupine_keyword_path_v1';
export const COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY = 'nadot_companion_kws_porcupine_keyword_paths_v1';
export const DEFAULT_COMPANION_KWS_MODEL_PATH =
    (process.env.EXPO_PUBLIC_VOSK_MODEL_PATH || '').trim()
    || String(Constants.expoConfig?.extra?.voskModelPath || '').trim();
export const RELEASE_CHANNEL = (process.env.EXPO_PUBLIC_RELEASE_CHANNEL || '').trim().toLowerCase();
// 사이드로드(마켓 직접 배포) 단말은 항상 인앱 자동 업데이트를 켠다.
// EXPO_PUBLIC_DISABLE_UPDATE_PROMPT=1 로만 비활성화 가능.
export const ENABLE_IN_APP_UPDATE_PROMPT =
    (process.env.EXPO_PUBLIC_DISABLE_UPDATE_PROMPT || '').trim() !== '1';
// 사용자가 "나중에"를 누른 빌드 번호 저장 → 같은 빌드는 재알림하지 않되, 더 새 빌드가 올라오면 다시 알린다.
export const VERSION_SNOOZE_BUILD_KEY = 'app_update_snooze_build_v1';
// 앱 빌드가 바뀔 때 기기별로 남아 있던 VoIP 임시 상태를 1회 정리하기 위한 마이그레이션 마커.
export const APP_RUNTIME_BUILD_MARKER_KEY = 'worldlinco_runtime_build_marker_v1';
export const VOIP_DEFAULT_PHONE_PREFIX = '+82-';
export const VOIP_INCOMING_LINK_SCHEMES = ['worldlingo', 'worldlinco', 'com.parkcheolhong.worldlinco'];
export const VOIP_INCOMING_LINK_PATH = 'voip/incoming';
export const APP_ENTRY_RAIL_LINK_PATH = 'rail/open';
export const APP_ENTRY_VOIP_LINK_PATH = 'voip/open';
export const APP_ENTRY_CHAT_LINK_PATH = 'chat/open';
export const APP_ENTRY_INVITE_LINK_PATH = 'invite';
export const APP_ENTRY_SALES_LINK_PATH = 'sales';
export const DEMO_SESSION_EMAIL_DOMAIN = 'instant-demo.worldlinco.dev';
export const AUTH_DEBUG_MARKER_ENABLED = __DEV__ || (process.env.EXPO_PUBLIC_AUTH_DEBUG_MARKER || '').trim() === '1';
export const OCR_DEBUG_IMAGE_URI =
    (process.env.EXPO_PUBLIC_OCR_DEBUG_IMAGE_URI || '').trim() ||
    (String(Constants.expoConfig?.extra?.ocrDebugImageUri || '')).trim();
export const OCR_DEBUG_IMAGE_NAME = (process.env.EXPO_PUBLIC_OCR_DEBUG_IMAGE_NAME || '').trim();

// App.tsx 에서 분리한 도메인 옵션 배열(선택 UI 소스).
export const CATEGORY_OPTIONS: Array<{ label: string; value: SearchCategory }> = [
    { label: '전체', value: 'all' },
    { label: '호텔', value: 'hotel' },
    { label: '공항', value: 'airport' },
    { label: '식당', value: 'restaurant' },
    { label: '관광명소', value: 'attraction' },
];

export const RADIUS_OPTIONS: Array<{ label: string; value: number }> = [
    { label: '5km', value: 5000 },
    { label: '20km', value: 20000 },
    { label: '30km', value: 30000 },
    { label: '50km', value: 50000 },
    { label: '100km', value: 100000 },
    { label: '500km', value: 500000 },
];

export const VOIP_GENDER_OPTIONS: Array<{ value: VoipGenderOption; label: string }> = [
    { value: 'male', label: '남성' },
    { value: 'female', label: '여성' },
    { value: 'unknown', label: '미설정' },
];

export const VOICE_LICENSE_OPTIONS: Array<{ value: VoiceLicenseMode; label: string }> = [
    { value: 'private_preview_unverified', label: '권리 확인 전' },
    { value: 'self_created', label: '직접 만든 곡' },
    { value: 'licensed', label: '라이선스 보유' },
    { value: 'public_domain', label: '공개 허용' },
    { value: 'policy_approved_distribution', label: '운영 승인' },
];

export const VOICE_OUTPUT_SCOPE_OPTIONS: Array<{ value: VoiceOutputScope; label: string }> = [
    { value: 'private_preview', label: '개인 preview' },
    { value: 'user_saved_preview', label: '내 보관함' },
    { value: 'policy_review_export', label: 'export 심사' },
    { value: 'policy_approved_export', label: '승인 export' },
];
