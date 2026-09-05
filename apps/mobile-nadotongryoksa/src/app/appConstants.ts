// App.tsx 에서 분리한 앱 상수(브랜딩/버전/스토리지 키/딥링크 경로/플래그/OCR 디버그).
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { WORLDLINGO_BRAND_NAME, WORLDLINGO_ENGINE_LABEL } from '../constants/worldlincoBrand';
import type { SearchCategory } from '../features/travel-booking/types';
import type { VoipGenderOption } from '../features/profile/profileFormatters';
import type { VoiceLicenseMode, VoiceOutputScope } from './appTypes';

export const PRODUCTION_API_BASE = 'https://metanova1004.com';
export const PRODUCTION_WEB_BASE = 'https://metanova1004.com';
export const IS_WEB = Platform.OS === 'web';

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
export const APP_ENTRY_AUTH_LINK_PATH = 'auth/callback';
/** 데모 세션 임시 계정 이메일 도메인(미지정 시 worldlinco-demo.com 폴백). */
export const DEMO_SESSION_EMAIL_DOMAIN = 'worldlinco-demo.com';
export const SOCIAL_LOGIN_REDIRECT_URI = 'worldlingo://auth/callback';
export const AUTH_DEBUG_MARKER_ENABLED = __DEV__ || (process.env.EXPO_PUBLIC_AUTH_DEBUG_MARKER || '').trim() === '1';
// 실기기 자동화 검증에서 companion toggle 노출 조건(인증 완료)을 일시 완화하는 테스트 플래그.
export const FORCE_COMPANION_TOGGLE_TEST_MODE = (process.env.EXPO_PUBLIC_FORCE_COMPANION_TOGGLE_TEST_MODE || '').trim() === '1';
// 실기기 자동화 검증에서 showLogin 가드를 일시 완화하는 테스트 플래그.
export const FORCE_COMPANION_TOGGLE_SHOWLOGIN_TEST_MODE = (process.env.EXPO_PUBLIC_FORCE_COMPANION_TOGGLE_SHOWLOGIN_TEST_MODE || '').trim() === '1';
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

// 1-1 Quick Win: App.tsx 레일 허브 하드코딩 UI 토큰 분리(문자열/색상/아이콘).
export const WORLDLINCO_SECTION_ACCENT_COLORS = {
    chat: '#1E6FE0',
    song: '#7C5CFC',
    travel: '#19C37D',
};

export const WORLDLINCO_SECTION_ICONS = {
    chatVoip: '📡',
    chatPhone: '📇',
    chatMap: '🗺️',
    chatGroup: '👥',
    songHub: '🎵',
    songFile: '📂',
    travelHub: '🧭',
    travelFlight: '✈️',
    travelHotel: '🏨',
    travelNearby: '📍',
    travelItinerary: '📅',
    travelRecommend: '🗺️',
};

export const CHAT_SECTION_GATE_TITLE = '로그인 후 채팅, 친구 목록, 친구 찾기가 함께 열립니다';
export const CHAT_SECTION_GATE_BODY = '현재 상태에서는 채팅방 목록과 친구 허브가 비어 보일 수 있습니다. 로그인 후 실제 계정으로 방 목록, 그룹방, 친구 찾기, 번역 공유 흐름을 같은 레일에서 바로 검증할 수 있습니다.';
export const CHAT_SECTION_GATE_BULLETS: string[] = [
    '채팅방 목록과 번역 보관함 자동 연결',
    '친구 목록/친구 찾기 허브 동시 검증',
    'OCR/노래 번역 공유 메시지 검증',
];

export const SONG_SECTION_TEXT = {
    heroTitle: '노래 가사를 번역해서 함께 불러요',
    modeOn: 'ON',
    modeOff: 'OFF',
    modeOnSub: '가사 번역 자막 켜짐',
    modeOffSub: '탭하면 가사 번역 시작',
    modeOnBadge: '🎵 노래 모드 ON',
    modeOffBadge: '🎵 노래 모드 OFF',
    fileProcessing: '파일 처리 중',
    selectFile: '노래 파일 선택',
    selectAfterPurchase: '결제 후 파일 선택',
    resetSubtitles: '자막 초기화',
    shareLoading: '공유 중...',
    shareToChat: '💬 노래 번역을 채팅에 보내기',
};

export const APP_UPDATE_TEXT = {
    downloading: '업데이트를 내려받는 중…',
    downloadProgress: (percent: number) => `업데이트 다운로드 ${percent}%`,
    updateTitle: `${WORLDLINGO_APP_NAME} 업데이트`,
    updateInstallFailed: (errorMessage: string) => `업데이트 설치를 시작하지 못했습니다.\n${errorMessage}\n\n잠시 후 다시 시도해주세요.`,
    confirmButton: '확인',
    openingInstaller: '설치 화면을 엽니다…',
    updateAvailableBody: (remoteVersionLabel: string) => `새 버전 ${remoteVersionLabel} 이(가) 준비되었습니다.\n현재 버전: ${APP_VERSION_LABEL}\n\n지금 업그레이드하시겠어요? (앱 안에서 바로 설치됩니다)`,
    remindLater: '나중에',
    upgradeNow: '업그레이드',
};

export const AUTH_API_ERROR_TEXT = {
    loginFailed: (status: number) => `로그인 실패 (HTTP ${status})`,
    duplicateLoginBlocked: '이미 다른 기기 또는 세션에서 로그인 상태가 남아 있습니다. 현재 사용 중인 기기가 없다면 계정 복구(본인확인) 후 세션 해제 뒤 다시 시도해 주세요.',
    signupFailed: (status: number) => `회원가입 실패 (HTTP ${status})`,
    requestCodeFailed: (status: number) => `인증 코드 요청 실패 (HTTP ${status})`,
    confirmEmailFailed: (status: number) => `이메일 인증 확인 실패 (HTTP ${status})`,
    meFetchFailed: '내 정보 조회 실패',
    meSaveFailed: (status: number) => `내 정보 저장 실패 (HTTP ${status})`,
};

export const APP_ALERT_TEXT = {
    loginRequiredTitle: '로그인 필요',
    chatOpenLoginRequiredBody: '채팅을 열려면 먼저 로그인해 주세요.',
    friendFeatureLoginRequiredBody: '친구 기능을 사용하려면 먼저 로그인해 주세요.',
    friendMapLoginRequiredBody: '근처 친구 찾기를 사용하려면 먼저 로그인해 주세요.',
    chatShareLoginRequiredBody: '채팅으로 보내려면 먼저 로그인해 주세요.',
    chatOpenFailedTitle: '채팅 열기 실패',
    chatOpenFailedBody: '채팅방을 열지 못했습니다.',
    friendChatOpenFailedBody: '친구 채팅방을 열지 못했습니다.',
    chatSendFailedBody: '채팅 메시지를 전송하지 못했습니다.',
    missedVoipTitle: '부재중 보이스톡',
    missedVoipBody: (callerLabel: string) => `${callerLabel}님의 보이스톡을 받지 못했습니다.`,
    sessionSupersededTitle: '다른 기기에서 로그인됨',
    sessionSupersededBody: '다른 기기에서 로그인되어 이 기기는 로그아웃됩니다.',
    passwordChangedTitle: '비밀번호 변경 완료',
    passwordChangedBody: '새 비밀번호로 다시 로그인해 주세요.',
    peerLanguageTitle: '상대 언어',
    peerLanguageMustDifferBody: '상대 언어는 내 언어(설정 탭)와 달라야 합니다.',
    biometricTitle: '지문 로그인',
    biometricNeedCredentialBody: '먼저 이메일/비밀번호로 로그인한 뒤 설정할 수 있습니다.',
    biometricNeedPasswordBody: '비밀번호를 입력한 상태에서 다시 시도해 주세요.',
    biometricSaveFailedBody: '저장에 실패했습니다.',
    songFileProcessErrorTitle: '노래 파일 처리 오류',
    songPlaybackNeedReadyTitle: '재생 준비 필요',
    songPlaybackNeedReadyBody: '먼저 노래 파일을 선택하세요.',
    voiceSampleErrorTitle: '목소리 샘플 오류',
    voiceRecordingWaitTitle: '녹음 대기',
    voiceRecordingWaitBody: '현재 번역 마이크 녹음을 먼저 종료해 주세요.',
    microphonePermissionTitle: '마이크 권한 필요',
    microphonePermissionBody: '목소리 샘플 녹음을 위해 마이크 권한이 필요합니다.',
    voiceRecordingErrorTitle: '목소리 녹음 오류',
    fileSubtitleRequiredTitle: '파일 자막 필요',
    fileSubtitleRequiredBody: '먼저 노래 파일 번역 자막을 준비하세요.',
    voiceProfileRequiredTitle: '목소리 프로필 필요',
    voiceProfileRequiredBody: '먼저 내 목소리 샘플을 녹음하거나 업로드하세요.',
    voipIdRequiredTitle: 'ID 연결 필요',
    voipIdRequiredBody: '보이스톡은 앱 보이스 ID 또는 사용자 ID가 있는 대상만 연결할 수 있습니다.',
    voipVoiceOnlyBody: '앱 보이스 ID 대상만 보이스톡을 시작할 수 있습니다.',
    voipFailedTitle: '보이스톡 실패',
    voipFailedBody: '친구 보이스톡 시작 실패',
};

export type StandardErrorDomain = 'login' | 'translation' | 'voip';

export const STANDARD_ERROR_TEXT = {
    login: {
        default: '로그인 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.',
        network: '네트워크 상태를 확인한 뒤 다시 로그인해 주세요.',
        credential: '이메일 또는 비밀번호를 확인해 주세요.',
        server: '로그인 서버가 불안정합니다. 잠시 후 다시 시도해 주세요.',
    },
    translation: {
        default: '번역 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.',
        network: '번역 요청이 지연되고 있습니다. 네트워크 상태를 확인해 주세요.',
        server: '번역 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.',
    },
    voip: {
        default: '통화 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.',
        network: '통화 연결이 불안정합니다. 네트워크를 확인해 주세요.',
        permission: '마이크 권한을 확인한 뒤 다시 시도해 주세요.',
        peerOffline: '상대가 오프라인 상태입니다. 잠시 후 다시 시도해 주세요.',
    },
};

type StandardErrorRule = {
    pattern: RegExp;
    message: string;
};

const STANDARD_ERROR_RULES: Record<StandardErrorDomain, StandardErrorRule[]> = {
    login: [
        { pattern: /(401|403|unauthorized|invalid credential|password|비밀번호|email)/i, message: STANDARD_ERROR_TEXT.login.credential },
        { pattern: /(network|fetch|offline|timeout|timed out)/i, message: STANDARD_ERROR_TEXT.login.network },
        { pattern: /(500|502|503|504|server|internal)/i, message: STANDARD_ERROR_TEXT.login.server },
    ],
    translation: [
        { pattern: /(network|fetch|offline|timeout|timed out)/i, message: STANDARD_ERROR_TEXT.translation.network },
        { pattern: /(500|502|503|504|server|internal)/i, message: STANDARD_ERROR_TEXT.translation.server },
    ],
    voip: [
        { pattern: /(permission|record_audio|microphone|mic|권한|마이크)/i, message: STANDARD_ERROR_TEXT.voip.permission },
        { pattern: /(callee_offline|offline|not respond|not available|상대 앱이 아직 응답하지)/i, message: STANDARD_ERROR_TEXT.voip.peerOffline },
        { pattern: /(network|fetch|timeout|timed out|ice|turn|ws|socket)/i, message: STANDARD_ERROR_TEXT.voip.network },
    ],
};

export function toStandardErrorMessage(
    domain: StandardErrorDomain,
    rawMessage: string | null | undefined,
    fallback?: string,
): string {
    const normalized = String(rawMessage || '').trim();
    if (!normalized) {
        return fallback || STANDARD_ERROR_TEXT[domain].default;
    }
    const rules = STANDARD_ERROR_RULES[domain] || [];
    for (const rule of rules) {
        if (rule.pattern.test(normalized)) {
            return rule.message;
        }
    }
    return fallback || STANDARD_ERROR_TEXT[domain].default;
}
