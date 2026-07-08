import * as Speech from 'expo-speech';
import { Audio, type AudioSound, type AudioRecording } from './src/compat/expoAvAudio';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';
import Constants from 'expo-constants';
import { StatusBar } from 'expo-status-bar';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import firebase from '@react-native-firebase/app';
import messaging from '@react-native-firebase/messaging';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    Animated,
    AppState,
    BackHandler,
    Dimensions,
    Image,
    ImageBackground,
    Linking,
    Modal,
    PanResponder,
    PermissionsAndroid,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    ToastAndroid,
    Vibration,
    View,
} from 'react-native';
import * as ReactNativeExports from 'react-native';
import { SafeAreaView, SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import WebView, { type WebViewMessageEvent } from 'react-native-webview';
import { translateImage, translateText, synthesizeSpeech, type TranslateOptions } from './src/api/translate';
import { isTravelItineraryIntent } from './src/api/tourismAnswer';
import { FEATURE_IDS, newCorrelationId } from './src/features/correlation/correlationId';
import {
    SECTION_RAIL_ITEMS,
    buildSectionRailSelector,
    parseSectionRailKey,
    type SectionRailKey,
} from './src/features/navigation/sectionRegistry';
import {
    fetchLatestApkMetadata,
    isRemoteApkNewer as isRemoteApkBuildNewer,
    downloadAndInstallLatestApk,
} from './src/features/app-update/appUpdate';
import { CallModePolicyBanner } from './src/features/call-mode/CallModePolicyBanner';
import { NetworkTestBanner } from './src/components/NetworkTestBanner';
import type { CallMode } from './src/features/call-mode/types';
import { useCallModeController } from './src/features/call-mode/useCallModeController';
import { ChatRoomListScreen } from './src/features/chat/screens/ChatRoomListScreen';
import { ChatRoomScreen } from './src/features/chat/screens/ChatRoomScreen';
import { createDirectChatRoom, ensureSelfChatRoom, getChatRoomDetail, listChatRooms, sendChatRoomMessage } from './src/features/chat/api';
import { getFriends } from './src/api/friends';
import { buildFriendPhoneIndex, resolveContactChatAction } from './src/features/contacts/contactFriendMatch';
import { ContactsDirectoryModal } from './src/features/contacts/ContactsDirectoryModal';
import { loadDeviceContacts, type DeviceContact } from './src/services/deviceContacts';
import { shareChatInvite } from './src/features/sns-share/snsShare';
import type { ChatRoomSummary } from './src/features/chat/types';
import TravelItineraryPanel from './src/features/travel-itinerary/TravelItineraryPanel';
import { normalizeLyricLine, isLikelyLyricLine, isRepeatedLyricSegment, formatSongFileTime } from './src/features/song/songText';
import { normalizeSongFileLang, resolveSongFileTargetLang } from './src/features/song/songLang';
import {
    LANGS,
    type LangCode,
    SUPPORTED_LANGUAGE_COUNT,
    getLangLabelText,
    isSupportedLangCode,
    WHISPER_LANG_MAP,
    normalizeDetectedLangCode,
    inferSpeechLangCode,
    resolveAutoTargetLang,
} from './src/features/language/languageCatalog';
import { normalizeEchoText, echoOverlapRatio } from './src/features/sorisae/sorisaeEcho';
import { buildPersonaBrief, createEmptyPersona, setPreferredName, type CompanionPersona } from './src/features/sorisae/companionMemory';
import { loadPersona, recordTurn, resetPersona, savePersona } from './src/features/sorisae/companionPersonaStore';
import { parseCompanionCommand } from './src/features/sorisae/companionCommands';
import {
    COMPANION_VOICE_CALL_IDLE_MS,
    armCompanionVoiceCall,
    createCompanionVoiceCallState,
    disarmCompanionVoiceCall,
    matchCompanionWakeWord,
    markCompanionVoiceCallActivity,
    shouldCompanionVoiceCallSleep,
    sleepCompanionVoiceCall,
    wakeCompanionVoiceCall,
    type CompanionVoiceCallState,
} from './src/features/sorisae/companionVoiceCall';
import {
    DEFAULT_AI_DISPLAY_NAME,
    isValidAiName,
    loadAiDisplayName,
    resolveAiDisplayName,
    saveAiName,
} from './src/features/sorisae/companionIdentity';
import {
    FACE_CONVERSATION_RESTART_MS,
    FACE_CONVERSATION_PLAYBACK_CAP_MS,
    FACE_CONVERSATION_PERMISSION_RETRY_MS,
    FACE_CONVERSATION_ECHO_GUARD_MS,
    FACE_CONVERSATION_SPOKEN_HISTORY,
    FACE_CONVERSATION_PLAYBACK_DRAIN_MS,
    FACE_OUTPUT_ECHO_GUARD_MS,
} from './src/features/face-interpretation/faceConversationTiming';
import type { SearchCategory, NearbyPlace, BookingResponse } from './src/features/travel-booking/types';
import { formatDistance, escapeMapLabel, buildNearbyMapHtml, todayPlus } from './src/features/travel-booking/travelBooking';
import { SettingsScreen } from './src/features/settings/SettingsScreen';
import { loadGlobalSettings, useGlobalSettings } from './src/features/settings/globalSettings';
import { FriendFolderScreen } from './src/features/friends/FriendFolderScreen';
import { FriendMapDiscoveryScreen } from './src/features/friends/FriendMapDiscoveryScreen';
import { useAutoNearbyFriendDiscovery } from './src/features/friends/useAutoNearbyFriendDiscovery';
import type { AcceptedFriendActionPayload, DiscoveryGender, Friend } from './src/features/friends/types';
import { usePstnAssistController } from './src/features/pstn-assist/usePstnAssistController';
import { useVoipAutoController } from './src/features/voip-auto/useVoipAutoController';
import { usePermissionCheck } from './src/hooks/usePermissionCheck';
import { useNetworkDiagnostics } from './src/hooks/useNetworkDiagnostics';
import { PhoneDialer } from './src/components/PhoneDialer';
import { PasswordSecurityModal } from './src/components/PasswordSecurityModal';
import { DataSourcesModal } from './src/components/DataSourcesModal';
import {
    authenticateWithBiometric,
    isBiometricAvailable,
    isBiometricLoginEnabled,
    loadBiometricCredentials,
    saveBiometricCredentials,
    setBiometricLoginEnabled,
} from './src/auth/biometricGate';
import { VoipCallErrorBoundary } from './src/components/VoipCallErrorBoundary';
import { VoIPCallScreen } from './src/screens/VoIPCallScreen';
import { useVoipIncomingCalls } from './src/features/voip-auto/useVoipIncomingCalls';
import { registerVoipDevice, unregisterVoipDevice, fetchRecentMissedCalls } from './src/services/voipPresence';
import { announceServerVoice, buildAnnouncement } from './src/utils/voiceAnnounce';
import { createVoipMessagingAdapter } from './src/services/voipMessagingAdapter';
import { dismissIncomingVoipLocalNotification, ensureVoipIncomingNotificationChannel, showIncomingVoipLocalNotification } from './src/services/voipIncomingNotifications';
import { ensureChatMessageNotificationChannel } from './src/services/chatIncomingNotifications';
import {
    areVoipNotificationsEnabled,
    isVoipIncomingAlertNativeAvailable,
    openVoipNotificationSettings,
    startNativeIncomingVoipAlert,
    stopNativeIncomingVoipAlert,
    type IncomingAlertSoundMode,
} from './src/native/voipIncomingAlert';
import { acceptIncomingCall } from './src/services/voipPresence';
import { enableVoipAudio, disableVoipAudio } from './src/native/voipAudio';
import { CallInitResponse, type TURNServer } from './src/services/voipCallClient';
import { getVoIPToneService } from './src/services/voipToneService';
import { acquireVoiceCapture, revokeCurrentVoiceCapture, type VoiceCaptureFeatureId } from './src/services/voiceCaptureLease';
import { parsePersistedGpsSnapshot, serializePersistedGpsSnapshot } from './src/utils/hybridGpsCache';
import { detectHybridGpsMode, scoreLocationQuality, type HybridGpsMode } from './src/utils/hybridGps';
import {
    WORLDLINGO_BRAND_NAME,
    WORLDLINGO_ENGINE_LABEL,
    matchesWorldLincoProjectTitle,
} from './src/constants/worldlincoBrand';
import { normalizeSpeakText, inferTtsLanguage } from './src/features/tts/ttsText';
import { resolveWorldLincoProjectId } from './src/utils/worldlincoProject';
import {
    isIncomingRingVoipStatus,
    isResumableIncomingVoipStatus,
    shouldDeferCalleeResumeToIncomingAccept,
} from './src/utils/voipIncomingCallStatus';
import { toClientNetworkContext } from './src/utils/networkDiagnostics';
import { createFaceConversationVadController } from './src/features/face-conversation/faceConversationVadController';
import { shouldSkipSilentVoiceRelayStt } from './src/features/voip-voice-relay/voiceRelayAudioMetrics';
import {
    beginVoiceRelaySileroCapture,
    endVoiceRelaySileroCapture,
    isVoiceRelaySileroCaptureAvailable,
    probeVoiceRelaySileroVadSupport,
    startVoiceRelaySileroVadMonitor,
    stopVoiceRelaySileroVadMonitor,
    subscribeVoiceRelaySileroVadEvents,
} from './src/native/voiceRelaySileroVad';
import {
    isLikelyVoiceRelayEcho,
    isLikelyRepetitionHallucination,
    isLikelySilenceHallucination,
    relayTextsSimilar,
    normalizeRelayText,
    formatAutoRelayDelayLabel,
} from './src/features/voip-voice-relay/voiceRelayOrchestrator';
import { getWorldlincoTuning, hydrateWorldlincoTuningFromStorage, refreshWorldlincoTuning } from './src/services/worldlincoTuningConfig';
import {
    MONETIZATION_PLAN_CONFIG,
    collectOwnedPlanKeys,
    type MonetizationPlanKey,
} from './src/features/monetization/monetization';
import {
    resolveCountryFlag,
    resolveLocaleCountryCode,
    resolveLanguageLabel,
    formatVoipGenderLabel,
    formatDiscoveryGenderLabel,
    resolveDiscoveryGenderFromProfile,
    type VoipGenderOption,
} from './src/features/profile/profileFormatters';
import {
    normalizeCallModeCandidate,
    resolveCallModeFromPayload,
    formatUnifiedCallModeText,
    formatUnifiedTranslationStatus,
    isTerminalVoipStatus,
    type TranslationStatusRoute,
    type TranslationStatusPhase,
} from './src/features/call-mode/callModeHelpers';
import { resolveLangFromCountry } from './src/features/country/countryLanguage';
import {
    SIGNUP_COUNTRY_OPTIONS,
    SIGNUP_COUNTRY_OPTION_CODES,
    COUNTRY_NAME_MAP,
    normalizeSignupCountryCode,
    resolveSignupCountryFromLang,
    resolveCountryName,
    type SignupCountryCode,
} from './src/features/country/countryCatalog';
import {
    resolveGpsDialectRegionHint,
    resolveGpsCoordinateFallback,
    resolveRegionHintForSourceLanguage,
} from './src/features/country/regionHints';
import { formatStatusText, extractApiErrorMessage, summarizeAuthToken } from './src/features/shared/textFormat';
import {
    buildVoiceId,
    buildVoipTopic,
    buildVoipWebSocketUrl,
    getDefaultVoipTurnServers,
    normalizeTurnServers,
} from './src/features/voip/voipSignaling';
import { translateUiSync, useUiI18nTick, getUiLang, setUiLang } from './src/features/i18n/uiI18n';
import { C, SECTION_TAB_COLORS } from './src/app/appTheme';
import { styles } from './App.styles';
import { parseAppEntryDeepLink, parseIncomingVoipDeepLink } from './src/app/appDeepLinks';
import type {
    VoipParticipantProfile,
    DevicePhoneContact,
    PurchaseResult,
    StoredActiveVoipSession,
    CallModeAuditEvent,
    UserInfo,
    SignupPayload,
    UserProfileUpdatePayload,
    AuthModalMode,
    AppEntryDeepLinkTarget,
    SignupRequestCodeResponse,
    SignupSelectionModal,
    HybridGpsResult,
    SongSubtitleEntry,
    SongFileJobStatus,
    SongFileTimelineSegment,
    SongFileTimeline,
    VoiceLicenseMode,
    VoiceOutputScope,
    VoiceConsentResponse,
    VoiceProfileResponse,
    VoicePreviewResponse,
} from './src/app/appTypes';
import { getUiText } from './src/app/appUiText';
import {
    API_BASE,
    WORLDLINGO_APP_NAME,
    APP_VERSION_NUMBER,
    APP_BUILD_NUMBER,
    APP_VERSION_LABEL,
    APP_FOOTER_BRAND,
    APP_FOOTER_BRAND_KO,
    VERSION_CHECK_KEY,
    VERSION_IGNORE_KEY,
    AUTH_STORAGE_KEY,
    WORLDLINCO_SETTINGS_STORAGE_KEY,
    ACTIVE_VOIP_CALL_STORAGE_KEY,
    VOIP_VALIDATION_FRIEND_CALL_BYPASS_KEY,
    VOIP_LOCAL_LANG_STORAGE_KEY,
    RELEASE_CHANNEL,
    ENABLE_IN_APP_UPDATE_PROMPT,
    VERSION_SNOOZE_BUILD_KEY,
    VOIP_DEFAULT_PHONE_PREFIX,
    VOIP_INCOMING_LINK_SCHEMES,
    VOIP_INCOMING_LINK_PATH,
    APP_ENTRY_RAIL_LINK_PATH,
    APP_ENTRY_VOIP_LINK_PATH,
    APP_ENTRY_CHAT_LINK_PATH,
    DEMO_SESSION_EMAIL_DOMAIN,
    AUTH_DEBUG_MARKER_ENABLED,
    OCR_DEBUG_IMAGE_URI,
    OCR_DEBUG_IMAGE_NAME,
    CATEGORY_OPTIONS,
    RADIUS_OPTIONS,
    VOIP_GENDER_OPTIONS,
    VOICE_LICENSE_OPTIONS,
    VOICE_OUTPUT_SCOPE_OPTIONS,
} from './src/app/appConstants';

// [전역 글꼴 확대] "대체적으로 글씨가 작다"는 피드백 반영. 화면마다 하드코딩된 수백 개의
// fontSize 를 일괄 키우는 대신, Text/TextInput 의 render 를 한 번만 패치해 명시적으로
// fontSize 가 지정된 경우에만 일정 배율로 확대한다. (fontSize 미지정 Text 는 부모 상속을
// 유지해 중첩 Text 레이아웃이 깨지지 않도록 건드리지 않음.) 배율(GLOBAL_FONT_SCALE)만
// 바꾸면 전역으로 조정된다.
const GLOBAL_FONT_SCALE = 1.18;
// [전역 다국어] 한글 문자열 children 을 지정 언어로 치환(uiLang !== 'ko'). 캐시에 없으면 원문을
// 보여주고 백그라운드 번역 후 tick 으로 다시 그린다. TextInput 은 사용자 입력값이라 번역하지 않는다.
const translateChildrenDeep = (children: any): any => {
    if (typeof children === 'string') {
        return translateUiSync(children);
    }
    if (Array.isArray(children)) {
        let changed = false;
        const next = children.map((child) => {
            if (typeof child === 'string') {
                const t = translateUiSync(child);
                if (t !== child) changed = true;
                return t;
            }
            return child;
        });
        return changed ? next : children;
    }
    return children;
};
// 이 RN/React 버전에서 Text/TextInput 은 .render 가 없는 "일반 함수 컴포넌트"라 .render monkeypatch 가
// 무시된다(글꼴 패치도 무효였음). 그래서 react-native 모듈의 Text/TextInput export 자체를 래퍼 함수
// 컴포넌트로 교체한다. 모든 파일의 `import { Text } from 'react-native'` 는 동일한 모듈 객체의 프로퍼티를
// 지연 참조하므로, 여기서 한 번 교체하면 앱 전역에 적용된다. 래퍼는 진짜 컴포넌트라 useUiI18nTick() 훅으로
// 번역 도착 시 자동 리렌더가 가능하다.
(() => {
    const installWrapper = (key: 'Text' | 'TextInput', translate: boolean) => {
        const ns: any = ReactNativeExports as any;
        const Orig: any = ns[key];
        if (typeof Orig !== 'function' || Orig.__wlWrapped) return;
        const Wrapped: any = function WlTextWrapper(props: any) {
            useUiI18nTick();
            let children = props.children;
            if (translate && getUiLang() !== 'ko' && children != null) {
                children = translateChildrenDeep(children);
            }
            const flat = StyleSheet.flatten(props.style) as { fontSize?: number } | undefined;
            const nextStyle = flat && typeof flat.fontSize === 'number'
                ? [props.style, { fontSize: Math.round(flat.fontSize * GLOBAL_FONT_SCALE) }]
                : props.style;
            return React.createElement(Orig, { ...props, style: nextStyle, children });
        };
        Wrapped.__wlWrapped = true;
        Wrapped.displayName = `Wl(${key})`;
        const assign = (target: any) => {
            if (!target) return;
            try {
                target[key] = Wrapped;
                if (target[key] === Wrapped) return;
            } catch { /* fall through to defineProperty */ }
            try { Object.defineProperty(target, key, { configurable: true, get: () => Wrapped }); } catch { /* no-op */ }
        };
        assign(ns);
        try { assign(require('react-native')); } catch { /* no-op */ }
    };
    installWrapper('Text', true);
    installWrapper('TextInput', false);
})();

// [기능 분리 Phase5.7] SectionRailKey/SECTION_RAIL_ITEMS/buildSectionRailSelector/
// parseSectionRailKey 는 src/features/navigation/sectionRegistry.ts 단일 레지스트리에서
// 파생(자동 넘버링 + 자동 연결, 상단 import 참조).

// [기능 분리 Phase5.4] SearchCategory/NearbyPlace/BookingResponse 타입은
// src/features/travel-booking/types.ts 로 추출(상단 import 참조).

// [기능 분리 Phase5.6d] TERMINAL_VOIP_STATUSES + 콜모드/통번역 상태 헬퍼는
// src/features/call-mode/callModeHelpers.ts 로 추출(상단 import 참조).

const PENDING_INCOMING_RING_MAX_MS = 65_000;

async function requestEndVoipCall(
    apiBase: string,
    token: string,
    callId: string,
    callQuality: string,
): Promise<void> {
    try {
        await fetch(`${apiBase}/api/v1/voip/calls/${callId}/end`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                duration_sec: 0,
                call_quality: callQuality,
            }),
        });
    } catch (error) {
        console.warn('[VoIP] Failed to end stale call cleanly', error);
    }
}

async function fetchVoipCallResumeSnapshot(
    apiBase: string,
    authToken: string,
    callId: string,
): Promise<CallInitResponse | null> {
    try {
        const response = await fetch(
            `${apiBase}/api/v1/voip/calls/active-current?last_call_id=${encodeURIComponent(callId)}`,
            { headers: { Authorization: `Bearer ${authToken}` } },
        );
        if (!response.ok) {
            return null;
        }
        const payload = await response.json() as CallInitResponse | null;
        if (!payload?.call_id) {
            return null;
        }
        return payload;
    } catch {
        return null;
    }
}

const FIREBASE_ANDROID_OPTIONS = {
    apiKey: 'AIzaSyA90Rs93geo1Sz94HmdHL94X34r7eH8wGo',
    appId: '1:409873234227:android:094e3ebdb0001592b0a646',
    messagingSenderId: '409873234227',
    projectId: 'studio-9080238625-9cec3',
    storageBucket: 'studio-9080238625-9cec3.firebasestorage.app',
};
const ensureFirebaseDefaultApp = async (): Promise<boolean> => {
    if (firebase.apps.length > 0) {
        return true;
    }

    try {
        await firebase.initializeApp(FIREBASE_ANDROID_OPTIONS);
    } catch (error) {
        if (firebase.apps.length > 0) {
            return true;
        }
        console.log('[VoIPFCM] firebase bootstrap failed', error);
        return false;
    }

    return firebase.apps.length > 0;
};

const voipMessagingAdapter = createVoipMessagingAdapter(ensureFirebaseDefaultApp);

// [기능 분리 정리] 인앱 업데이트 버전 비교/메타 URL 헬퍼는 `src/features/app-update/appUpdate.ts`
// (메타데이터 기반 isRemoteApkNewer + LATEST_APK_METADATA_PATH) 로 단일화됨.
// App.tsx 로컬 중복본(parseVersionTriplet/parseBuildNumber/compareSemanticVersions/
// isRemoteApkNewer(string)/resolveLatestApkMetadataUrl)은 호출처가 없어 제거(SSOT 통합).

function buildInstantDemoCredentials(seed: string) {
    const normalizedSeed = seed.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 10) || 'guestdemo';
    return {
        email: `instant-${normalizedSeed}@${DEMO_SESSION_EMAIL_DOMAIN}`,
        username: `instant_${normalizedSeed}`,
        password: `WorldLinco!${normalizedSeed}A1`,
    };
}

let nonceCounter = 0;

function nextNonceTag(): string {
    nonceCounter = (nonceCounter + 1) % 0x100000;
    return `${Date.now().toString(36)}${nonceCounter.toString(36)}`;
}

const AUTO_RELAY_DELAY_OPTIONS_MS = [2000, 2500, 3000] as const;
const DEFAULT_AUTO_RELAY_DELAY_MS = 2500;
// [기능 분리 Phase5.1a] 대면통역 타이밍 상수(FACE_CONVERSATION_*/FACE_OUTPUT_ECHO_GUARD_MS)는
// src/features/face-interpretation/faceConversationTiming.ts 로 추출(상단 import 참조).
const TRANSLATION_REQUEST_TIMEOUT_MS = 30_000;
const AUTO_RELAY_DUPLICATE_GUARD_MS = 8000;

// [기능 분리 Phase5.6c] 국기/로케일/언어 라벨 + 성별 라벨 헬퍼는
// src/features/profile/profileFormatters.ts 로 추출(상단 import 참조).
// [기능 분리 Phase5.6e-2] resolveCountryName 은 country 카탈로그로 추출
// (src/features/country/countryCatalog.ts, 상단 import 참조).

// [기능 분리 Phase5.6g] buildVoiceId/buildVoipTopic/buildVoipWebSocketUrl/
// getDefaultVoipTurnServers/normalizeTurnServers 는 src/features/voip/voipSignaling.ts 로 추출(상단 import 참조).

// [기능 분리 Phase5.1a] formatAutoRelayDelayLabel/normalizeRelayText 는 음성릴레이 공용 유틸로
// src/features/voip-voice-relay/voiceRelayOrchestrator.ts 로 통합(상단 import 참조).
// [기능 분리 Phase5.2] normalizeEchoText/echoOverlapRatio 는
// src/features/sorisae/sorisaeEcho.ts 로 추출(상단 import 참조).

// [기능 분리 Phase5.4] formatDistance/escapeMapLabel/buildNearbyMapHtml/todayPlus 는
// src/features/travel-booking/travelBooking.ts 로 추출(상단 import 참조).
// 인앱 자동 업데이트: 마켓에 올린 빌드를 단말이 스스로 감지 → "업그레이드"를 누르면
// 곧장 새 APK 를 내려받아 시스템 설치 화면으로 연결한다. (브라우저로 빠지지 않음)
async function runApkInAppInstall() {
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

async function checkForAppUpdate() {
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

async function callLoginApi(email: string, password: string): Promise<string> {
    console.log('[AUTH_FLOW]', JSON.stringify({
        event: 'LOGIN_API_REQUEST',
        endpoint: `${API_BASE}/api/auth/login`,
        email: email.trim().toLowerCase(),
    }));
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
    });
    const data = await res.json().catch(() => ({}));
    console.log('[AUTH_FLOW]', JSON.stringify({
        event: res.ok ? 'LOGIN_API_SUCCESS' : 'LOGIN_API_FAIL',
        endpoint: `${API_BASE}/api/auth/login`,
        email: email.trim().toLowerCase(),
        status: res.status,
    }));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `로그인 실패 (HTTP ${res.status})`));
    return data.access_token as string;
}

async function callSignupApi(payload: SignupPayload): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `회원가입 실패 (HTTP ${res.status})`));
    return data as UserInfo;
}

async function callSignupRequestCodeApi(payload: SignupPayload): Promise<SignupRequestCodeResponse> {
    const res = await fetch(`${API_BASE}/api/auth/signup/request-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ...payload,
            verificationChannel: payload.verificationChannel || 'email',
        }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `인증 코드 요청 실패 (HTTP ${res.status})`));
    return data as SignupRequestCodeResponse;
}

async function callSignupConfirmApi(
    signupSessionToken: string,
    verificationCode: string,
    profile: Pick<SignupPayload, 'preferred_language' | 'country_code' | 'full_name'>,
): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/signup/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            signupSessionToken,
            verificationCode,
            preferred_language: profile.preferred_language,
            country_code: profile.country_code,
            full_name: profile.full_name,
        }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `이메일 인증 확인 실패 (HTTP ${res.status})`));
    return data as UserInfo;
}

async function callMeApi(token: string): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('내 정보 조회 실패');
    return res.json();
}

async function callUpdateMeApi(token: string, payload: UserProfileUpdatePayload): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `내 정보 저장 실패 (HTTP ${res.status})`));
    return data as UserInfo;
}

async function loadStoredAuthState(): Promise<{ token: string; userInfo: UserInfo } | null> {
    const raw = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw) as { token?: string; userInfo?: UserInfo };
        if (!parsed.token || !parsed.userInfo?.id || !parsed.userInfo?.email) {
            return null;
        }
        return {
            token: parsed.token,
            userInfo: parsed.userInfo,
        };
    } catch {
        return null;
    }
}

async function saveStoredAuthState(token: string, userInfo: UserInfo): Promise<void> {
    await AsyncStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({ token, userInfo }),
    );
}

async function clearStoredAuthState(): Promise<void> {
    await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
}

async function loadStoredActiveVoipSession(): Promise<StoredActiveVoipSession | null> {
    const raw = await AsyncStorage.getItem(ACTIVE_VOIP_CALL_STORAGE_KEY);
    if (!raw) {
        return null;
    }

    try {
        const parsed = JSON.parse(raw) as StoredActiveVoipSession | string;
        if (typeof parsed === 'string') {
            const normalized = parsed.trim();
            return normalized ? { callId: normalized } : null;
        }

        const normalizedCallId = typeof parsed.callId === 'string' ? parsed.callId.trim() : '';
        if (!normalizedCallId) {
            return null;
        }

        return {
            callId: normalizedCallId,
            railSection: parsed.railSection ?? null,
            acceptedParticipantRole: parsed.acceptedParticipantRole === 'caller' || parsed.acceptedParticipantRole === 'callee'
                ? parsed.acceptedParticipantRole
                : null,
            acceptedAt: typeof parsed.acceptedAt === 'string' && parsed.acceptedAt.trim() ? parsed.acceptedAt : null,
        };
    } catch {
        const normalized = raw.trim();
        return normalized ? { callId: normalized } : null;
    }
}

async function saveStoredActiveVoipSession(
    callId: string,
    railSection?: SectionRailKey | null,
    acceptedParticipantRole?: 'caller' | 'callee' | null,
): Promise<void> {
    await AsyncStorage.setItem(
        ACTIVE_VOIP_CALL_STORAGE_KEY,
        JSON.stringify({
            callId: callId.trim(),
            railSection: 'voip',
            acceptedParticipantRole: acceptedParticipantRole ?? null,
            acceptedAt: acceptedParticipantRole ? new Date().toISOString() : null,
        } satisfies StoredActiveVoipSession),
    );
}

function isStoredAcceptedCalleeVoipSession(storedSession: StoredActiveVoipSession | null, callId: string): boolean {
    return storedSession?.callId === callId
        && storedSession.acceptedParticipantRole === 'callee'
        && typeof storedSession.acceptedAt === 'string'
        && storedSession.acceptedAt.length > 0;
}

function isRuntimeAcceptedCalleeVoipSession(
    storedSession: StoredActiveVoipSession | null,
    callId: string,
    acceptedCallId: string | null,
): boolean {
    return acceptedCallId === callId || isStoredAcceptedCalleeVoipSession(storedSession, callId);
}

async function clearStoredActiveVoipSession(): Promise<void> {
    await AsyncStorage.removeItem(ACTIVE_VOIP_CALL_STORAGE_KEY);
}

async function callNearbyPlacesApi(params: {
    lat: string;
    lon: string;
    category: SearchCategory;
    radiusM: number;
    targetLang: string;
}): Promise<NearbyPlace[]> {
    const query = new URLSearchParams({
        lat: params.lat,
        lon: params.lon,
        category: params.category,
        radius_m: String(params.radiusM),
        target_lang: params.targetLang,
        limit: '12',
    });
    const requestUrl = `${API_BASE}/api/marketplace/nadotongryoksa/lbs/nearby?${query.toString()}`;
    console.log('[TRAVEL_NEARBY_PROBE]', JSON.stringify({
        event: 'NEARBY_REQUEST',
        request_url: requestUrl,
        lat: params.lat,
        lon: params.lon,
        category: params.category,
        radius_m: params.radiusM,
        target_lang: params.targetLang,
    }));
    const response = await fetch(requestUrl);
    console.log('[TRAVEL_NEARBY_PROBE]', JSON.stringify({
        event: 'NEARBY_RESPONSE',
        status: response.status,
        ok: response.ok,
    }));
    if (!response.ok) throw new Error(`주변검색 실패: HTTP ${response.status}`);
    const payload = await response.json();
    console.log('[TRAVEL_NEARBY_PROBE]', JSON.stringify({
        event: 'NEARBY_PAYLOAD',
        total: Array.isArray(payload.places) ? payload.places.length : 0,
        first_place_id: Array.isArray(payload.places) && payload.places.length > 0 ? payload.places[0]?.id ?? null : null,
    }));
    return Array.isArray(payload.places) ? payload.places : [];
}

async function callBookingApi(token: string, payload: {
    placeId: string;
    customerName: string;
    checkinDate: string;
    checkoutDate: string;
    guests: number;
    roomCount: number;
    note: string;
    targetLang: string;
}): Promise<BookingResponse> {
    console.log('[TRAVEL_BOOKING_PROBE]', JSON.stringify({
        event: 'BOOKING_API_REQUEST',
        place_id: payload.placeId,
        customer_name: payload.customerName,
        checkin_date: payload.checkinDate,
        checkout_date: payload.checkoutDate,
        guests: payload.guests,
        room_count: payload.roomCount,
        target_lang: payload.targetLang,
    }));
    const response = await fetch(`${API_BASE}/api/marketplace/nadotongryoksa/lbs/bookings`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            place_id: payload.placeId,
            customer_name: payload.customerName,
            checkin_date: payload.checkinDate,
            checkout_date: payload.checkoutDate,
            guests: payload.guests,
            room_count: payload.roomCount,
            note: payload.note,
            target_lang: payload.targetLang,
        }),
    });
    const result = await response.json().catch(() => ({}));
    console.log('[TRAVEL_BOOKING_PROBE]', JSON.stringify({
        event: response.ok ? 'BOOKING_API_SUCCESS' : 'BOOKING_API_FAIL',
        status: response.status,
        place_id: payload.placeId,
        confirmation_id: typeof result?.confirmation_id === 'string' ? result.confirmation_id : null,
        detail: typeof result?.detail === 'string' ? result.detail : null,
    }));
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    return result;
}

async function callCreatePurchaseApi(token: string, amount: number): Promise<PurchaseResult> {
    const projectId = await resolveWorldLincoProjectId(API_BASE);
    const res = await fetch(`${API_BASE}/api/marketplace/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ project_id: projectId, amount, payment_method: 'card' }),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(result.detail || `구매 생성 실패 HTTP ${res.status}`);
    return result;
}

async function callInitiatePaymentApi(token: string, purchaseId: number): Promise<{ payment_url: string }> {
    const res = await fetch(`${API_BASE}/api/marketplace/purchase/${purchaseId}/pay`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(result.detail || `결제 초기화 실패 HTTP ${res.status}`);
    return result;
}

async function callMyPurchasesApi(token: string): Promise<Array<{ id: number; amount: number; status: string; payment_method: string }>> {
    const res = await fetch(`${API_BASE}/api/marketplace/purchases`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items ?? []);
}

// ─────────────────────────────────────────────
// 지원 언어 목록 (50개국어)
// ─────────────────────────────────────────────
// [기능 분리 Phase5.5 선행] LANGS/LangCode/SUPPORTED_LANGUAGE_COUNT 는
// src/features/language/languageCatalog.ts 로 추출(상단 import 참조).
// [기능 분리 Phase5.6e-2] 가입/프로필 국가 카탈로그(SIGNUP_COUNTRY_OPTIONS/SignupCountryCode/
// SIGNUP_COUNTRY_OPTION_CODES/COUNTRY_NAME_MAP + isSupportedSignupCountryCode/
// normalizeSignupCountryCode/resolveSignupCountryFromLang/resolveCountryName)는
// src/features/country/countryCatalog.ts 로 추출(상단 import 참조).

// [기능 분리 Phase5.5 선행] getLangLabelText/isSupportedLangCode 는
// src/features/language/languageCatalog.ts 로 추출(상단 import 참조).

const ADB_GPS_OVERRIDE_PATH = 'file:///storage/emulated/0/Android/media/com.parkcheolhong.worldlinco/worldlingo_mock_location.json';
const GPS_DEBUG_TRACE_FILE_PATH = `${FileSystem.documentDirectory ?? FileSystem.cacheDirectory ?? 'file:///data/user/0/com.parkcheolhong.worldlinco/files/'}gps-fallback-debug.log`;
const GPS_PERSISTED_FALLBACK_KEY = 'gps_fallback_last_success_v1';

// [기능 분리 Phase5.6e-3] GPS/방언 리전 힌트(GPS_REGION_COORDINATE_FALLBACKS/
// DIALECT_REGION_HINT_KEYWORDS + resolveGpsDialectRegionHint/resolveGpsCoordinateFallback/
// resolveRegionHintForSourceLanguage)는 src/features/country/regionHints.ts 로 추출(상단 import 참조).

// [기능 분리 Phase5.5 선행] WHISPER_LANG_MAP 은
// src/features/language/languageCatalog.ts 로 추출(상단 import 참조).

const SONG_FILE_JOB_POLL_INTERVAL_MS = 1500;
const SONG_FILE_JOB_MAX_WAIT_MS = 6 * 60 * 1000;

// [기능 분리 Phase5.5 선행] normalizeDetectedLangCode 는
// src/features/language/languageCatalog.ts 로 추출(상단 import 참조).
// [기능 분리 Phase5] 노래 번역 순수 텍스트 헬퍼는 src/features/song/songText.ts,
// 언어 헬퍼(normalizeSongFileLang / resolveSongFileTargetLang)는 src/features/song/songLang.ts 로 추출됨.

function delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function parseApiResponse<T>(response: Response): Promise<T> {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        const message = typeof payload.detail === 'string' ? payload.detail : `HTTP ${response.status}`;
        throw new Error(message);
    }
    return payload as T;
}

async function callCreateSongFileJob(asset: DocumentPicker.DocumentPickerAsset, targetLanguage: LangCode): Promise<SongFileJobStatus> {
    const formData = new FormData();
    const fileName = asset.name || `song-${Date.now()}.mp3`;
    const mimeType = asset.mimeType || 'application/octet-stream';
    if (asset.file) {
        formData.append('file', asset.file as unknown as Blob);
    } else {
        formData.append('file', { uri: asset.uri, name: fileName, type: mimeType } as unknown as Blob);
    }
    formData.append('target_language', targetLanguage);
    formData.append('source_language', 'auto');
    formData.append('quality', 'advanced');
    formData.append('mode', 'subtitle');

    // ===== REQUEST TIMING =====
    const requestStartTime = Date.now();
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs`, {
        method: 'POST',
        body: formData,
    });
    const requestEndTime = Date.now();
    const requestDurationMs = requestEndTime - requestStartTime;

    const result = await parseApiResponse<SongFileJobStatus>(response);
    console.log(`[MOBILE_API] POST song-translation/jobs: ${requestDurationMs}ms`);

    return result;
}

async function callSongFileJobStatus(jobId: string): Promise<SongFileJobStatus> {
    // ===== POLLING TIMING =====
    const pollStartTime = Date.now();
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}`);
    const pollEndTime = Date.now();
    const pollDurationMs = pollEndTime - pollStartTime;

    const result = await parseApiResponse<SongFileJobStatus>(response);

    // Log when status changes significantly
    if (result.status === 'completed' || result.status === 'failed') {
        console.log(`[MOBILE_API] GET song-translation/jobs/${jobId}: ${pollDurationMs}ms [${result.status}]`);
    }

    return result;
}

async function callSongFileTimeline(jobId: string): Promise<SongFileTimeline> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}/subtitles`);
    return parseApiResponse<SongFileTimeline>(response);
}

async function callPatchSongFileSegment(jobId: string, segmentId: string, translated: string): Promise<SongFileTimelineSegment> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}/segments/${encodeURIComponent(segmentId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ translated }),
    });
    const payload = await parseApiResponse<{ segment: SongFileTimelineSegment }>(response);
    return payload.segment;
}

async function callExportSongFileTimeline(jobId: string, format: 'srt' | 'vtt' | 'lrc' | 'json'): Promise<string> {
    const query = new URLSearchParams({ format });
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}/export?${query.toString()}`);
    const text = await response.text();
    if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
    return text;
}

async function callCreateVoiceConsent(): Promise<VoiceConsentResponse> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/voice-consents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            consent_version: '2026-05-voice-v1',
            voice_owner: 'self',
            allow_private_preview: true,
            allow_export_for_licensed_audio: true,
            user_id: 'mobile-user',
        }),
    });
    return parseApiResponse<VoiceConsentResponse>(response);
}

async function callCreateVoiceProfile(asset: DocumentPicker.DocumentPickerAsset, consentId: string): Promise<VoiceProfileResponse> {
    const formData = new FormData();
    const fileName = asset.name || `voice-sample-${Date.now()}.m4a`;
    const mimeType = asset.mimeType || 'audio/m4a';
    if (asset.file) {
        formData.append('sample', asset.file as unknown as Blob);
    } else {
        formData.append('sample', { uri: asset.uri, name: fileName, type: mimeType } as unknown as Blob);
    }
    formData.append('consent_id', consentId);
    formData.append('profile_label', '내 목소리');
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/voice-profiles`, {
        method: 'POST',
        body: formData,
    });
    return parseApiResponse<VoiceProfileResponse>(response);
}

async function callDeleteVoiceProfile(profileId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/voice-profiles/${encodeURIComponent(profileId)}`, {
        method: 'DELETE',
    });
    await parseApiResponse<{ deleted: boolean }>(response);
}

async function callCreateVoicePreview(params: {
    jobId: string;
    voiceProfileId: string;
    licenseMode: VoiceLicenseMode;
    outputScope: VoiceOutputScope;
    rightsAcknowledged: boolean;
}): Promise<VoicePreviewResponse> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(params.jobId)}/voice-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            voice_profile_id: params.voiceProfileId,
            license_mode: params.licenseMode,
            preview_mode: 'translated_lyric_voice',
            output_scope: params.outputScope,
            rights_acknowledged: params.rightsAcknowledged,
            approval_id: params.licenseMode === 'policy_approved_distribution' ? 'mobile-admin-approved' : undefined,
        }),
    });
    return parseApiResponse<VoicePreviewResponse>(response);
}

// [기능 분리 Phase5.5 선행] normalizeSpeakText/inferTtsLanguage 는
// src/features/tts/ttsText.ts 로 추출(상단 import 참조). 로케일 교정은 scriptLangResolver/voipLanguageLocales 위임.

async function stopFaceVoicePlayback(playbackSoundRef: React.MutableRefObject<AudioSound | null>): Promise<void> {
    Speech.stop();
    if (!playbackSoundRef.current) return;
    try {
        await playbackSoundRef.current.stopAsync();
        await playbackSoundRef.current.unloadAsync();
    } catch {
        // no-op
    }
    playbackSoundRef.current = null;
}

async function playFaceTranslationOutput(options: {
    translatedText: string;
    targetLang: LangCode;
    audioBase64?: string | null;
    audioFormat?: string | null;
    apiBaseUrl?: string;
    playbackSoundRef: React.MutableRefObject<AudioSound | null>;
    // V.2 ID 백본 — 대면 통역도 동일 상관 ID로 기능 ID 자동 매핑→셀프 서빙→전송→음성 발화를 자동 연결한다.
    correlationId?: string;
}): Promise<void> {
    const speakText = normalizeSpeakText(options.translatedText);
    if (!speakText) return;

    await stopFaceVoicePlayback(options.playbackSoundRef);
    Speech.stop();

    const lang = LANGS.find((item) => item.code === options.targetLang);
    const fallbackTts = lang?.tts ?? 'ko-KR';
    // 발화 로케일은 SSOT(inferTtsLanguage)로 결정 — 지정 타깃 언어 로케일을 신뢰하고
    // 단일 언어 전용 스크립트로 번역문이 샌 경우에만 교정한다(50개국 정확 발화).
    const detectedTts = inferTtsLanguage(speakText, fallbackTts);
    // 안전 상한(safety cap): onDone이 끝까지 책임지게 하고, 타임아웃은 onDone이
    // 영영 안 올 때만 쓰는 넉넉한 상한이어야 한다. 과거엔 length*70ms로 너무 짧게 잡아
    // 실제 TTS가 더 길 때 타임아웃이 먼저 끝나 → 듣기가 재개되어 TTS 꼬리를 다시 녹음(에코)했다.
    const safetyCapMs = Math.min(30_000, Math.max(6_000, speakText.length * 220 + 4_000));

    try {
        await Audio.setAudioModeAsync({
            allowsRecordingIOS: false,
            playsInSilentModeIOS: true,
            shouldDuckAndroid: true,
            playThroughEarpieceAndroid: false,
        });
    } catch {
        // no-op
    }

    // 우선순위 1: 서버 뉴럴 TTS(Edge neural). 단말 음성팩 의존을 제거해 50개국 일관 발음·
    // 자연스러운 톤을 보장한다(라틴어권=영어, 한자=중국어 같은 단말 음성팩 한계 회피).
    // 릴레이로 이미 오디오가 왔으면 그걸 쓰고, 없으면 대상 언어로 직접 합성 요청. 실패 시 디바이스 TTS 폴백.
    let serverAudioBase64: string | undefined =
        options.audioBase64 && String(options.audioFormat || '').startsWith('audio/')
            ? options.audioBase64
            : undefined;
    let serverAudioFormat: string | undefined =
        serverAudioBase64 ? String(options.audioFormat) : undefined;
    if (!serverAudioBase64) {
        try {
            // 타임아웃을 넉넉히(12s) — 6s에선 네트워크/edge-tts 지연 시 단말 TTS(붙여 읽기)로 폴백됐다.
            const synth = await synthesizeSpeech(
                speakText,
                options.targetLang,
                options.apiBaseUrl ?? API_BASE,
                12000,
                { correlationId: options.correlationId, featureId: FEATURE_IDS.faceInterpret },
            );
            if (synth?.audioBase64 && String(synth.audioFormat || '').startsWith('audio/')) {
                serverAudioBase64 = synth.audioBase64;
                serverAudioFormat = synth.audioFormat;
            } else {
                console.log('[FACE_TTS]', JSON.stringify({ event: 'server_tts_unavailable', delivery: synth?.ttsDelivery ?? 'null', target: options.targetLang }));
            }
        } catch (err) {
            // 합성 실패 → 디바이스 TTS 폴백
            console.log('[FACE_TTS]', JSON.stringify({ event: 'server_tts_error', target: options.targetLang, message: err instanceof Error ? err.message : 'synth_failed' }));
        }
    }

    let playedServerAudio = false;
    if (serverAudioBase64) {
        try {
            const ext = String(serverAudioFormat || '').includes('wav') ? 'wav' : 'mp3';
            const baseDir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory ?? '';
            const fileUri = `${baseDir}face_tts_out_${Date.now()}.${ext}`;
            await FileSystem.writeAsStringAsync(fileUri, serverAudioBase64, {
                encoding: FileSystem.EncodingType.Base64,
            });
            const { sound } = await Audio.Sound.createAsync(
                { uri: fileUri },
                { shouldPlay: true, volume: 1.0 },
            );
            options.playbackSoundRef.current = sound;
            await new Promise<void>((resolve) => {
                const failsafe = setTimeout(resolve, safetyCapMs);
                sound.setOnPlaybackStatusUpdate((status) => {
                    if (status.isLoaded === false) {
                        clearTimeout(failsafe);
                        resolve();
                        return;
                    }
                    if (status.didJustFinish) {
                        clearTimeout(failsafe);
                        resolve();
                    }
                });
            });
            await stopFaceVoicePlayback(options.playbackSoundRef);
            // 즉시 삭제 금지: ExoPlayer(media3)가 unload 직후에도 백그라운드로 소스 파일을 읽어
            // FileNotFoundException(ENOENT)을 던지며 발화가 중간에 끊기던 문제가 있었다.
            // 핸들이 완전히 해제되도록 충분히 지연 후 정리한다.
            const ttsFileToCleanup = fileUri;
            setTimeout(() => {
                FileSystem.deleteAsync(ttsFileToCleanup, { idempotent: true }).catch(() => { /* no-op */ });
            }, 5000);
            playedServerAudio = true;
            console.log('[FACE_TTS]', JSON.stringify({ event: 'played', delivery: 'server_audio', target: options.targetLang }));
        } catch (err) {
            await stopFaceVoicePlayback(options.playbackSoundRef);
            playedServerAudio = false;
            console.log('[FACE_TTS]', JSON.stringify({ event: 'server_audio_play_error', target: options.targetLang, message: err instanceof Error ? err.message : 'play_failed' }));
        }
    }

    // 우선순위 2: 디바이스 TTS 폴백 (서버 합성 불가/실패 시)
    if (!playedServerAudio) {
        console.log('[FACE_TTS]', JSON.stringify({ event: 'played', delivery: 'device_speech', locale: detectedTts, target: options.targetLang }));
        await Promise.race([
            new Promise<void>((resolve) => {
                Speech.speak(speakText, {
                    language: detectedTts,
                    rate: 1.05,
                    volume: 1.0,
                    onDone: () => resolve(),
                    onStopped: () => resolve(),
                    onError: () => resolve(),
                });
            }),
            new Promise<void>((resolve) => setTimeout(resolve, safetyCapMs)),
        ]);

        // onDone이 스피커 버퍼 플러시보다 약간 빠를 수 있어, 실제 발화 종료를 한 번 더 확인한다.
        try {
            for (let i = 0; i < 20; i += 1) {
                const stillSpeaking = await Speech.isSpeakingAsync();
                if (!stillSpeaking) break;
                await new Promise<void>((resolve) => setTimeout(resolve, 150));
            }
        } catch {
            // no-op
        }
    }
}

// [기능 분리 Phase5.5 선행] inferSpeechLangCode/resolveAutoTargetLang 는
// src/features/language/languageCatalog.ts 로 추출(상단 import 참조).

function resolveVoipRemoteLanguageHint(...values: Array<string | null | undefined>): LangCode | null {
    for (const value of values) {
        const normalized = String(value || '').trim().toLowerCase();
        if (isSupportedLangCode(normalized)) {
            return normalized;
        }
    }
    return null;
}

// [기능 분리 Phase5.3/5.5] resolveSongFileTargetLang 는
// src/features/song/songLang.ts 로 추출(상단 import 참조).

// ─────────────────────────────────────────────
// 전역 배경 — 소리새 하늘색 그라데이션 (assets/sky-bg.png)
// ─────────────────────────────────────────────
const SKY_BG = require('./assets/sky-bg.png');
const LOGIN_MASCOT = require('./assets/login-mascot.png');

function AppInner() {
    const insets = useSafeAreaInsets();
    const [fromLang, setFromLang] = useState<LangCode>('ko');
    const [toLang, setToLang] = useState<LangCode>('en');
    const [gpsCountryCode, setGpsCountryCode] = useState('');
    const [gpsRegionHint, setGpsRegionHint] = useState('');
    const [inputText, setInputText] = useState('');
    const [resultText, setResultText] = useState('');
    const [loading, setLoading] = useState(false);
    const [ocrLoading, setOcrLoading] = useState(false);
    const [ocrImageName, setOcrImageName] = useState('');
    const [ocrExtractedText, setOcrExtractedText] = useState('');
    const [ocrTranslatedText, setOcrTranslatedText] = useState('');
    const [ocrError, setOcrError] = useState('');
    const ocrDebugInjectedRef = useRef(false);
    const [offline, setOffline] = useState(false);
    const [engine, setEngine] = useState('');
    const [langPickerFor, setLangPickerFor] = useState<'from' | 'to' | null>(null);
    const pulseAnim = useRef(new Animated.Value(1)).current;
    const {
        selectedCallMode,
        callModeLabel,
        setCallMode,
        voipValidationOverride,
        setVoipValidationOverride,
        showVoipTester,
        setShowVoipTester,
        showFriendFolder,
        setShowFriendFolder,
        interCallActive,
        setInterCallActive,
        interCallTurn,
        setInterCallTurn,
        interCallStatus,
        setInterCallStatus,
        interCallPhone,
        setInterCallPhone,
        interCallContactPickerVisible,
        setInterCallContactPickerVisible,
        interCallContactLoading,
        setInterCallContactLoading,
        interCallContactError,
        setInterCallContactError,
        interCallContactOptions,
        setInterCallContactOptions,
        interCallLog,
        setInterCallLog,
        interManualText,
        setInterManualText,
        voipCallInitResponse,
        setVoipCallInitResponse,
        pendingIncomingVoipCall,
        setPendingIncomingVoipCall,
        voipAuditCallId,
        setVoipAuditCallId,
        voipAuditEvents,
        setVoipAuditEvents,
        voipAuditLoading,
        setVoipAuditLoading,
        voipAuditError,
        setVoipAuditError,
        voipIdentity,
        setVoipIdentity,
        voipActiveProfile,
        setVoipActiveProfile,
    } = useCallModeController();

    // 로그인/내정보
    const [token, setToken] = useState('');
    const tokenRef = useRef('');
    useEffect(() => {
        tokenRef.current = token;
    }, [token]);
    // 단일 세션: 다른 단말/웹에서 로그인되면 이 단말은 401 → 자동 로그아웃 처리에 사용.
    const handleLogoutRef = useRef<null | (() => void)>(null);
    const sessionSupersededHandledRef = useRef(false);
    const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
    const [authHydrated, setAuthHydrated] = useState(false);
    const [showLogin, setShowLogin] = useState(false);
    const [authModalMode, setAuthModalMode] = useState<AuthModalMode>('login');
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPw, setLoginPw] = useState('');
    const [showLoginPw, setShowLoginPw] = useState(false);
    const [signupUsername, setSignupUsername] = useState('');
    const [signupFullName, setSignupFullName] = useState('');
    // [Phase6.0] 가입 필수: 나의 AI 이름 → "OOOO AI" 표시명으로 자동 치환(온디바이스 SSOT).
    const [signupAiName, setSignupAiName] = useState('');
    const [aiDisplayName, setAiDisplayName] = useState<string>(DEFAULT_AI_DISPLAY_NAME);
    const [signupPreferredLanguage, setSignupPreferredLanguage] = useState<LangCode>('ko');
    const [signupCountryCode, setSignupCountryCode] = useState<SignupCountryCode>('KR');
    const [signupSelectionModal, setSignupSelectionModal] = useState<SignupSelectionModal>(null);
    const [signupStep, setSignupStep] = useState<'form' | 'verify'>('form');
    const [signupSessionToken, setSignupSessionToken] = useState('');
    const [signupMaskedTarget, setSignupMaskedTarget] = useState('');
    const [signupOtpCode, setSignupOtpCode] = useState('');
    const [signupVerificationChannel, setSignupVerificationChannel] = useState<'email' | 'phone'>('email');
    const [signupPhone, setSignupPhone] = useState('');
    const [loginLoading, setLoginLoading] = useState(false);
    const [loginError, setLoginError] = useState('');
    const [demoSessionLoading, setDemoSessionLoading] = useState(false);
    const [demoSessionError, setDemoSessionError] = useState('');
    const [demoSessionMessage, setDemoSessionMessage] = useState('');
    const [lastUiProbeEvent, setLastUiProbeEvent] = useState('APP_BOOT');
    const [railDebugLastPressed, setRailDebugLastPressed] = useState('NONE');
    const [railDebugLastApplied, setRailDebugLastApplied] = useState('home@BOOT');
    const [authDebugSubmitPressed, setAuthDebugSubmitPressed] = useState(false);
    const [authDebugFocusField, setAuthDebugFocusField] = useState<'NONE' | 'EMAIL' | 'PASSWORD'>('NONE');
    const [authDebugLastInputEvent, setAuthDebugLastInputEvent] = useState('APP_BOOT');
    const [showPasswordSecurity, setShowPasswordSecurity] = useState(false);
    const [passwordSecurityMode, setPasswordSecurityMode] = useState<'recover' | 'change'>('recover');
    const [biometricLoginReady, setBiometricLoginReady] = useState(false);
    const [biometricLoginEnabled, setBiometricLoginEnabledState] = useState(false);
    const [biometricLoginBusy, setBiometricLoginBusy] = useState(false);
    const [showMyInfo, setShowMyInfo] = useState(false);
    const [profilePreferredLanguage, setProfilePreferredLanguage] = useState<LangCode>('ko');
    const [profileCountryCode, setProfileCountryCode] = useState<SignupCountryCode>('KR');
    const [profileSelectionModal, setProfileSelectionModal] = useState<SignupSelectionModal>(null);
    const [profileSaving, setProfileSaving] = useState(false);
    const [profileMessage, setProfileMessage] = useState('');
    const [myPurchases, setMyPurchases] = useState<Array<{ id: number; amount: number; status: string; payment_method: string }> | null>(null);
    const [myPurchasesLoading, setMyPurchasesLoading] = useState(false);
    const [premiumStatusMessage, setPremiumStatusMessage] = useState('');
    const ownedPlanKeys = collectOwnedPlanKeys(myPurchases);
    const activeVoipPlan = ownedPlanKeys.has('voip_pro') ? 'voip_pro' : ownedPlanKeys.has('voip_lite') ? 'voip_lite' : null;
    const hasSongPass = ownedPlanKeys.has('song_pass');
    const authDebugState = !authHydrated ? 'HYDRATING' : userInfo ? 'AUTHENTICATED' : token ? 'TOKEN_ONLY' : 'ANONYMOUS';
    const authDebugUser = userInfo ? `${userInfo.id}|${userInfo.email}` : 'none';
    const authDebugSurface = showLogin ? 'MODAL' : 'INLINE';
    const authDebugSubmitMode = authModalMode === 'login' ? 'LOGIN' : 'SIGNUP';
    const authDebugEmailFilled = Boolean(loginEmail.trim());
    const authDebugPasswordFilled = Boolean(loginPw.trim());
    const authDebugEmailLength = loginEmail.length;
    const authDebugPasswordLength = loginPw.length;
    const authDebugSubmitPressedLabel = authDebugSubmitPressed ? 'PRESSED' : 'IDLE';
    const isInstantDemoSession = Boolean(userInfo?.email?.endsWith(`@${DEMO_SESSION_EMAIL_DOMAIN}`));
    const effectiveVoipPlan = activeVoipPlan ?? (isInstantDemoSession ? 'voip_lite' : null);
    const deriveSignupCountryCode = useCallback((): SignupCountryCode => {
        return normalizeSignupCountryCode(userInfo?.country_code || gpsCountryCode || resolveLocaleCountryCode());
    }, [gpsCountryCode, userInfo?.country_code]);
    const deriveSignupPreferredLanguage = useCallback((countryCode: string) => {
        const savedPreferredLanguage = String(userInfo?.preferred_language || '').trim().toLowerCase();
        if (isSupportedLangCode(savedPreferredLanguage)) {
            return savedPreferredLanguage;
        }
        return resolveLangFromCountry(countryCode) || fromLang;
    }, [fromLang, userInfo?.preferred_language]);
    const resetSignupProfileDraft = useCallback(() => {
        const nextCountryCode = deriveSignupCountryCode();
        setSignupCountryCode(nextCountryCode);
        setSignupPreferredLanguage(deriveSignupPreferredLanguage(nextCountryCode));
        setSignupSelectionModal(null);
        setSignupStep('form');
        setSignupSessionToken('');
        setSignupMaskedTarget('');
        setSignupOtpCode('');
        setSignupVerificationChannel('email');
        setSignupPhone('');
    }, [deriveSignupCountryCode, deriveSignupPreferredLanguage]);
    useEffect(() => {
        if (!showMyInfo || !userInfo) {
            return;
        }
        const nextCountryCode = normalizeSignupCountryCode(userInfo.country_code);
        const normalizedPreferredLanguage = String(userInfo.preferred_language || '').trim().toLowerCase();
        const nextPreferredLanguage = isSupportedLangCode(normalizedPreferredLanguage)
            ? normalizedPreferredLanguage
            : deriveSignupPreferredLanguage(nextCountryCode);
        setProfileCountryCode(nextCountryCode);
        setProfilePreferredLanguage(nextPreferredLanguage);
        setProfileSelectionModal(null);
        setProfileMessage('');
    }, [deriveSignupPreferredLanguage, showMyInfo, userInfo]);
    // [전역 다국어] 번역 캐시가 갱신되거나 uiLang 이 바뀌면 tick 이 올라간다. 모놀리식 루트가 이를
    // 구독해 인라인 Text 트리를 한꺼번에 다시 그린다 → 전역 Text 패치가 최신 uiLang/캐시로 치환.
    useUiI18nTick();
    // [전역 다국어 — 언어 자동설정 우선순위]
    //  · 지정언어(preferred_language)가 있으면 그것을 사용한다 → "한번 지정하면 재접속에도 그 언어로".
    //  · 지정이 없으면(미가입/미지정) GPS 국가 → 언어로 자동감지(1순위). GPS 없으면 단말 로케일 국가.
    //  결과적으로 단말 설치 즉시 자국어처럼 보이고, 지정 시 그 언어가 영속된다.
    useEffect(() => {
        const designated = String(userInfo?.preferred_language || '').trim().toLowerCase();
        if (designated && isSupportedLangCode(designated)) {
            void setUiLang(designated);
            return;
        }
        const country = String(gpsCountryCode || resolveLocaleCountryCode() || '').trim();
        const gpsLang = country ? String(resolveLangFromCountry(country) || '').trim().toLowerCase() : '';
        if (gpsLang && isSupportedLangCode(gpsLang)) {
            void setUiLang(gpsLang);
        }
    }, [userInfo?.preferred_language, gpsCountryCode]);
    const [showFriendMapDiscovery, setShowFriendMapDiscovery] = useState(false);
    // VoIP 지정 언어 로컬 오버라이드(백엔드 고정 해제). null이면 백엔드 프로필 언어 사용.
    const [voipLocalLangOverride, setVoipLocalLangOverride] = useState<LangCode | null>(null);
    const [voipLangModalVisible, setVoipLangModalVisible] = useState(false);
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const saved = String((await AsyncStorage.getItem(VOIP_LOCAL_LANG_STORAGE_KEY)) || '').trim().toLowerCase();
                if (!cancelled && isSupportedLangCode(saved)) {
                    setVoipLocalLangOverride(saved);
                }
            } catch {
                // ignore — fall back to backend profile language
            }
        })();
        return () => { cancelled = true; };
    }, []);
    const handleSelectVoipLocalLang = useCallback((code: LangCode) => {
        // 1) 즉시 로컬 반영(오프라인/지연에도 통화 언어가 곧바로 바뀌도록).
        setVoipLocalLangOverride(code);
        setVoipLangModalVisible(false);
        void AsyncStorage.setItem(VOIP_LOCAL_LANG_STORAGE_KEY, code).catch(() => { });
        // 2) 백엔드 실시간 저장: 통역 지정 언어를 프로필 preferred_language 로 즉시 PATCH →
        //    상대 단말이 읽는 언어까지 한 번에 일관 적용(별도 "프로필 저장" 단계 불필요).
        if (token && userInfo) {
            void (async () => {
                try {
                    const updated = await callUpdateMeApi(token, { preferred_language: code });
                    setUserInfo(updated);
                    await saveStoredAuthState(token, updated);
                    console.log('[VoIP][lang] preferred_language synced to backend', code);
                } catch (error: any) {
                    console.warn('[VoIP][lang] backend sync failed (local override still active)', error?.message || error);
                }
            })();
        }
    }, [token, userInfo]);
    const handleClearVoipLocalLang = useCallback(() => {
        setVoipLocalLangOverride(null);
        setVoipLangModalVisible(false);
        void AsyncStorage.removeItem(VOIP_LOCAL_LANG_STORAGE_KEY).catch(() => { });
    }, []);
    const [voipAutoCallVoiceId, setVoipAutoCallVoiceId] = useState<string | null>(null);
    const [selectedChatRoom, setSelectedChatRoom] = useState<ChatRoomSummary | null>(null);
    const [chatRefreshKey, setChatRefreshKey] = useState(0);
    const [groupComposerSignal, setGroupComposerSignal] = useState(0);
    const [chatShareLoading, setChatShareLoading] = useState(false);
    const [shareTargetVisible, setShareTargetVisible] = useState(false);
    const [shareTargetOptions, setShareTargetOptions] = useState<ChatRoomSummary[]>([]);
    const [shareTargetError, setShareTargetError] = useState('');
    const [pendingChatShare, setPendingChatShare] = useState<{
        messageType: string;
        body: string;
        translatedBody?: string | null;
        sourceLang?: string | null;
        targetLang?: string | null;
        failureTitle: string;
    } | null>(null);
    const [voipPhone, setVoipPhone] = useState(VOIP_DEFAULT_PHONE_PREFIX);
    const [showPhoneDialerModal, setShowPhoneDialerModal] = useState(false);
    // [Phase5.12] 단말 전화번호부 디렉터리(일반전화통역/VoIP/채팅 연동) 표시 여부.
    const [contactsDirectoryVisible, setContactsDirectoryVisible] = useState(false);
    const [showDataSources, setShowDataSources] = useState(false);
    const [voipInitLoading, setVoipInitLoading] = useState(false);
    const [voipInitError, setVoipInitError] = useState('');
    const [voipStatusMessage, setVoipStatusMessage] = useState('');
    const [voipProfileGender, setVoipProfileGender] = useState<VoipGenderOption>('unknown');
    const voipPresenceSocketRef = useRef<WebSocket | null>(null);
    const voipTopicRef = useRef<string | null>(null);
    const pendingIncomingPollInFlightRef = useRef(false);
    const voipAuditFetchInFlightRef = useRef(false);
    const acceptedIncomingVoipCallIdRef = useRef<string | null>(null);
    const acceptingIncomingVoipCallRef = useRef(false);
    const acceptingIncomingVoipCallIdRef = useRef<string | null>(null);
    const pendingIncomingVoipCallRef = useRef<(CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null>(null);
    const voipCallInitResponseRef = useRef<CallInitResponse | null>(null);
    const activeRailSectionRef = useRef<SectionRailKey | null>(null);
    const voipCallInitiatingRef = useRef(false);
    const friendCallDispatchKeyRef = useRef<string | null>(null);
    const friendCallDispatchAtRef = useRef(0);
    const voipValidationFriendCallBypassRef = useRef(false);
    const consumedAppEntryDeepLinkUrlRef = useRef('');
    const notificationDisabledPromptShownRef = useRef(false);
    const consumedValidationAutoCallKeyRef = useRef('');
    const voipAutoCallCalleeLanguageRef = useRef<LangCode | null>(null);
    const canUseFullAutoVoipWithoutPurchasePrompt = Boolean(effectiveVoipPlan || voipValidationOverride || isInstantDemoSession);
    const [acceptingIncomingVoipCallId, setAcceptingIncomingVoipCallId] = useState<string | null>(null);
    const { initiateVoipCall, validatePhoneNumber } = useVoipAutoController(API_BASE, token);
    const networkDiagnostics = useNetworkDiagnostics(Boolean(token));
    const { requestPermissions } = usePermissionCheck();
    const { openDialPad, startPstnAssistDialFlow } = usePstnAssistController();

    const logUiPressProbe = useCallback((event: string, details: Record<string, unknown> = {}) => {
        const timestamp = new Date().toISOString();
        setLastUiProbeEvent(`${event}@${timestamp}`);
        const payload = {
            event,
            timestamp,
            token_ready: Boolean(token),
            user_ready: Boolean(userInfo),
            show_login: showLogin,
            show_voip_tester: showVoipTester,
            selected_call_mode: selectedCallMode,
            ...details,
        };
        console.log('[UI_PRESS_PROBE]', JSON.stringify(payload));
    }, [selectedCallMode, showLogin, showVoipTester, token, userInfo]);

    const lastNetworkLabelRef = useRef<string | null>(null);
    useEffect(() => {
        const nextLabel = networkDiagnostics.label;
        if (lastNetworkLabelRef.current === nextLabel) {
            return;
        }
        const previousLabel = lastNetworkLabelRef.current;
        lastNetworkLabelRef.current = nextLabel;
        logUiPressProbe('NETWORK_TRANSPORT_CHANGED', {
            ...toClientNetworkContext(networkDiagnostics),
            previous_label: previousLabel,
        });
    }, [logUiPressProbe, networkDiagnostics]);

    const emitUnifiedTranslationStatus = useCallback((
        target: 'pstn' | 'voip',
        phase: TranslationStatusPhase,
        detail: string,
        details: Record<string, unknown> = {},
    ) => {
        const route: TranslationStatusRoute = target === 'pstn' ? 'PSTN' : 'VOIP';
        const message = formatUnifiedTranslationStatus(route, phase, detail);
        if (target === 'pstn') {
            setInterCallStatus(message);
        } else {
            setVoipStatusMessage(message);
        }
        logUiPressProbe('TRANSLATION_STATUS', {
            target,
            route,
            phase,
            detail,
            message,
            ...details,
        });
        console.log('[TRANSLATION_STATUS]', JSON.stringify({
            target,
            route,
            phase,
            detail,
            message,
            ...details,
        }));
    }, [logUiPressProbe]);

    const setIncomingVoipAcceptInFlight = useCallback((callId: string | null) => {
        acceptingIncomingVoipCallRef.current = Boolean(callId);
        acceptingIncomingVoipCallIdRef.current = callId;
        setAcceptingIncomingVoipCallId(callId);
    }, []);

    const logAuthInputProbe = useCallback((event: string, details: Record<string, unknown> = {}) => {
        const timestamp = new Date().toISOString();
        setAuthDebugLastInputEvent(`${event}@${timestamp}`);
        const sanitizedDetails = Object.fromEntries(
            Object.entries(details).map(([key, value]) => {
                if (/(password|passwd|token|secret|otp)/i.test(key)) {
                    return [key, '[REDACTED]'];
                }
                return [key, value];
            }),
        );
        console.log('[AUTH_INPUT_PROBE]', JSON.stringify({
            event,
            timestamp,
            show_login: showLogin,
            focus_field: authDebugFocusField,
            email_length: loginEmail.length,
            ...sanitizedDetails,
        }));
    }, [authDebugFocusField, loginEmail.length, showLogin]);

    useEffect(() => {
        setAuthDebugSubmitPressed(false);
    }, [loginEmail, loginPw, showLogin, authModalMode]);

    const handleLoginEmailFocus = useCallback(() => {
        setAuthDebugFocusField('EMAIL');
        logAuthInputProbe('EMAIL_FOCUS');
    }, [logAuthInputProbe]);

    const handleLoginPasswordFocus = useCallback(() => {
        setAuthDebugFocusField('PASSWORD');
        logAuthInputProbe('PASSWORD_FOCUS');
    }, [logAuthInputProbe]);

    const handleLoginFieldBlur = useCallback((field: 'EMAIL' | 'PASSWORD') => {
        setAuthDebugFocusField('NONE');
        logAuthInputProbe(`${field}_BLUR`);
    }, [logAuthInputProbe]);

    const handleLoginEmailChange = useCallback((nextValue: string) => {
        setLoginEmail(nextValue);
        logAuthInputProbe('EMAIL_CHANGE', { next_length: nextValue.length });
    }, [logAuthInputProbe]);

    const handleLoginPasswordChange = useCallback((nextValue: string) => {
        setLoginPw(nextValue);
        logAuthInputProbe('PASSWORD_CHANGE', { next_length: nextValue.length });
    }, [logAuthInputProbe]);

    const summarizeIncomingVoipPayload = useCallback((payload: Partial<CallInitResponse> & { caller_voice_id?: string } | null | undefined) => ({
        mode_compact: `${payload?.requested_mode ?? 'null'}->${payload?.resolved_mode ?? 'null'}`,
        relay_compact: `${payload?.auto_relay_requested == null ? 'null' : payload.auto_relay_requested ? '1' : '0'}/${payload?.auto_relay_applied == null ? 'null' : payload.auto_relay_applied ? '1' : '0'}`,
        key_compact: payload && typeof payload === 'object' ? Object.keys(payload).sort().join('|') : 'null',
        caller_voice_id: payload?.caller_voice_id ?? null,
    }), []);

    const applyAuthenticatedSession = useCallback((nextToken: string, nextUserInfo: UserInfo) => {
        setToken(nextToken);
        setUserInfo(nextUserInfo);
        setShowLogin(false);
        setLoginEmail('');
        setLoginPw('');
        setLoginError('');
        setDemoSessionError('');
        const preferred = nextUserInfo.preferred_language?.trim().toLowerCase();
        if (preferred && isSupportedLangCode(preferred)) {
            setFromLang(preferred);
            setToLang((currentTarget) => resolveAutoTargetLang(preferred, currentTarget));
            // [전역 다국어] 회원가입/프로필 지정 언어로 앱 전체 UI 표기 전환.
            void setUiLang(preferred);
        }
    }, []);

    const openVoipTesterPanel = useCallback(() => {
        setVoipInitError('');
        setVoipCallInitResponse(null);
        setVoipPhone('');
        setVoipActiveProfile(null);
        setVoipAuditCallId('');
        setVoipAuditEvents([]);
        setVoipAuditError('');
        setShowVoipTester(true);
    }, []);

    const openLoginModalForSource = useCallback((source: string) => {
        logUiPressProbe('LOGIN_BUTTON_PRESS', { source });
        setAuthModalMode('login');
        setLoginError('');
        setShowLogin(true);
    }, [logUiPressProbe]);

    const openPasswordRecovery = useCallback(() => {
        setPasswordSecurityMode('recover');
        setShowPasswordSecurity(true);
        setShowLogin(false);
    }, []);

    const openPasswordChange = useCallback(() => {
        setPasswordSecurityMode('change');
        setShowPasswordSecurity(true);
    }, []);

    const handleBiometricLogin = useCallback(async () => {
        setBiometricLoginBusy(true);
        setLoginError('');
        try {
            const credentials = await loadBiometricCredentials();
            if (!credentials) {
                setLoginError('저장된 지문 로그인 정보가 없습니다. 이메일/비밀번호로 로그인 후 설정해 주세요.');
                return;
            }
            const tk = await callLoginApi(credentials.email, credentials.password);
            const me = await callMeApi(tk);
            applyAuthenticatedSession(tk, me);
        } catch (e: any) {
            setLoginError(e?.message || '지문 로그인에 실패했습니다.');
        } finally {
            setBiometricLoginBusy(false);
        }
    }, [applyAuthenticatedSession]);

    const handleToggleBiometricLogin = useCallback(async () => {
        if (biometricLoginEnabled) {
            await setBiometricLoginEnabled(false);
            setBiometricLoginEnabledState(false);
            setProfileMessage('지문 빠른 로그인을 해제했습니다.');
            return;
        }
        if (!loginEmail.trim() && !userInfo?.email) {
            Alert.alert('지문 로그인', '먼저 이메일/비밀번호로 로그인한 뒤 설정할 수 있습니다.');
            return;
        }
        const email = userInfo?.email || loginEmail.trim();
        const password = loginPw.trim();
        if (!password) {
            Alert.alert('지문 로그인', '비밀번호를 입력한 상태에서 다시 시도해 주세요.');
            return;
        }
        const ok = await authenticateWithBiometric('지문 빠른 로그인을 설정합니다');
        if (!ok) {
            return;
        }
        try {
            await saveBiometricCredentials({ email, password });
            setBiometricLoginEnabledState(true);
            setProfileMessage('지문으로 빠른 로그인을 사용할 수 있습니다.');
        } catch (e: any) {
            Alert.alert('지문 로그인', e?.message || '저장에 실패했습니다.');
        }
    }, [biometricLoginEnabled, loginEmail, loginPw, userInfo?.email]);

    const toggleAuthModalMode = useCallback(() => {
        setAuthModalMode((prev) => {
            const nextMode = prev === 'login' ? 'signup' : 'login';
            if (nextMode === 'signup') {
                resetSignupProfileDraft();
            }
            return nextMode;
        });
        setSignupStep('form');
        setSignupSessionToken('');
        setSignupMaskedTarget('');
        setSignupOtpCode('');
        setLoginError('');
    }, [resetSignupProfileDraft]);

    const handleStartInstantDemoSession = useCallback(async (targetSection: SectionRailKey) => {
        setDemoSessionLoading(true);
        setDemoSessionError('');
        setDemoSessionMessage('데모 세션을 준비하는 중입니다. 임시 계정을 생성하고 실제 토큰을 연결합니다.');
        setLoginError('');
        console.log('[AUTH_FLOW]', JSON.stringify({
            event: 'DEMO_SESSION_START',
            target_section: targetSection,
        }));

        const demoCountryCode = (gpsCountryCode || resolveLocaleCountryCode() || 'KR').trim().toUpperCase();

        try {
            let lastError: Error | null = null;

            for (let attempt = 0; attempt < 2; attempt += 1) {
                const seed = `${nextNonceTag()}${attempt}`;
                const demoCreds = buildInstantDemoCredentials(seed);

                try {
                    await callSignupApi({
                        username: demoCreds.username,
                        email: demoCreds.email,
                        password: demoCreds.password,
                        preferred_language: userInfo?.preferred_language || fromLang,
                        country_code: demoCountryCode,
                        full_name: 'WorldLinco Demo',
                        member_type: 'individual',
                    });
                    const nextToken = await callLoginApi(demoCreds.email, demoCreds.password);
                    const nextUserInfo = await callMeApi(nextToken);
                    console.log('[AUTH_FLOW]', JSON.stringify({
                        event: 'DEMO_SESSION_APPLIED',
                        user_id: nextUserInfo.id,
                        user_email: nextUserInfo.email,
                        target_section: targetSection,
                    }));
                    applyAuthenticatedSession(nextToken, nextUserInfo);
                    setDemoSessionMessage('데모 세션이 연결되었습니다. 채팅, 그룹방, 예약, VoIP 진입을 바로 검증할 수 있습니다.');
                    setPremiumStatusMessage('데모 세션에서는 VoIP tester가 임시 개방됩니다. 실제 과금 상태와는 별도로 UI 연결 검증만 빠르게 확인합니다.');
                    setSelectedChatRoom(null);
                    setChatRefreshKey((prev) => prev + 1);
                    setActiveRailSection(targetSection);

                    setShowFriendFolder(false);
                    setShowFriendMapDiscovery(false);

                    if (targetSection === 'voip') {
                        openVoipTesterPanel();
                    }

                    lastError = null;
                    break;
                } catch (error: any) {
                    lastError = error instanceof Error ? error : new Error(error?.message || '데모 세션 생성 실패');
                }
            }

            if (lastError) {
                throw lastError;
            }
        } catch (error: any) {
            const message = error?.message || '데모 세션 준비에 실패했습니다.';
            console.log('[AUTH_FLOW]', JSON.stringify({
                event: 'DEMO_SESSION_FAIL',
                target_section: targetSection,
                error: message,
            }));
            setDemoSessionError(message);
            setDemoSessionMessage('');
            setLoginError(message);
        } finally {
            setDemoSessionLoading(false);
        }
    }, [applyAuthenticatedSession, fromLang, gpsCountryCode, openVoipTesterPanel, userInfo?.preferred_language]);

    const renderSectionConnectionCard = (config: {
        sectionKey: SectionRailKey;
        title: string;
        body: string;
        bullets: string[];
        loginSource: string;
    }) => (
        <View style={styles.connectionStateCard}>
            <Text style={styles.connectionStateTitle}>{config.title}</Text>
            <Text style={styles.connectionStateBody}>{config.body}</Text>
            <View style={styles.connectionStateBulletList}>
                {config.bullets.map((bullet) => (
                    <Text key={`${config.sectionKey}-${bullet}`} style={styles.connectionStateBullet}>{`• ${bullet}`}</Text>
                ))}
            </View>
            {demoSessionMessage ? <Text style={styles.premiumStatusText}>{demoSessionMessage}</Text> : null}
            {demoSessionError ? <Text style={styles.errorText}>{demoSessionError}</Text> : null}
            <View style={styles.connectionStateActionRow}>
                <Pressable
                    style={[styles.inlineActionBtn, demoSessionLoading && styles.inlineGhostBtnDisabled]}
                    onPress={() => { void handleStartInstantDemoSession(config.sectionKey); }}
                    disabled={demoSessionLoading}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-demo-session-start-button"
                    testID="worldlinco-demo-session-start-button"
                >
                    <Text style={styles.inlineActionBtnText}>{demoSessionLoading ? '데모 연결 중...' : '데모 세션 시작'}</Text>
                </Pressable>
                <Pressable style={styles.inlineGhostBtn} onPress={() => openLoginModalForSource(config.loginSource)}>
                    <Text style={styles.inlineGhostBtnText}>로그인/회원가입</Text>
                </Pressable>
            </View>
        </View>
    );

    // 주변 검색
    const [lat, setLat] = useState('37.5665');
    const [lon, setLon] = useState('126.9780');
    // 소리새 AI 친구 모드 G-3: 현재 GPS 정확도(m). 너무 거칠면 서버가 '근처' 그라운딩에서 좌표를 제외.
    const [gpsAccuracyM, setGpsAccuracyM] = useState<number | null>(null);
    const [nearbyCategory, setNearbyCategory] = useState<SearchCategory>('all');
    const [radiusM, setRadiusM] = useState(100000);
    const [nearbyLoading, setNearbyLoading] = useState(false);
    const [nearbyError, setNearbyError] = useState('');
    const [nearbyPlaces, setNearbyPlaces] = useState<NearbyPlace[]>([]);
    const [selectedNearbyPlaceId, setSelectedNearbyPlaceId] = useState('');
    const [selectedBookingPlaceId, setSelectedBookingPlaceId] = useState('');
    const [bookingSelectionNotice, setBookingSelectionNotice] = useState('');
    const bookingSelectionNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // 예약
    const [bookingName, setBookingName] = useState('');
    const [checkinDate, setCheckinDate] = useState(todayPlus(1));
    const [checkoutDate, setCheckoutDate] = useState(todayPlus(2));
    const [guests, setGuests] = useState(2);
    const [roomCount, setRoomCount] = useState(1);
    const [bookingNote, setBookingNote] = useState('');
    const [bookingLoading, setBookingLoading] = useState(false);
    const [bookingError, setBookingError] = useState('');
    const [bookingResult, setBookingResult] = useState<BookingResponse | null>(null);

    // 결제
    const [payLoading, setPayLoading] = useState(false);
    const [payError, setPayError] = useState('');
    const [purchaseResult, setPurchaseResult] = useState<PurchaseResult | null>(null);
    const [payUrl, setPayUrl] = useState('');

    // GPS/WF 위치 확인
    const [gpsLangLoading, setGpsLangLoading] = useState(false);
    const [gpsStatus, setGpsStatus] = useState('');

    // 통역 통화 모드
    const [autoRelayDelayMs, setAutoRelayDelayMs] = useState<number>(2500);
    const interCallActiveRef = useRef(false);
    const interManualAutoRelayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const interLastAutoRelayRef = useRef<{ key: string; sentAt: number } | null>(null);
    const [interCallVoiceAssistEnabled, setInterCallVoiceAssistEnabled] = useState(false);

    // ── 음성 입력 (BT 하이브리드 MIC) ──
    const [autoVoiceModeEnabled, setAutoVoiceModeEnabled] = useState(false);
    const [isVoiceRecording, setIsVoiceRecording] = useState(false);
    const [voiceSttLoading, setVoiceSttLoading] = useState(false);
    // [자동 듣기 워치독] 인터벌 콜백에서 STT 처리 중 여부를 ref로 읽기 위해 state를 미러링.
    const voiceSttLoadingRef = useRef(false);
    const recordingRef = useRef<AudioRecording | null>(null);
    const voiceInputTargetRef = useRef<'main' | 'inter_call'>('main');
    const voiceInputStartInFlightRef = useRef(false);
    const voiceInputStopInFlightRef = useRef(false);
    const webSpeechRecognitionRef = useRef<any>(null);
    const autoVoiceStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const autoVoiceRestartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const autoVoiceModeEnabledRef = useRef(false);
    const scheduleFaceConversationRestartRef = useRef<(afterPlayback?: Promise<void> | null) => void>(() => { /* no-op */ });
    const stopVoiceInputRef = useRef<((options?: { suppressAutoRestart?: boolean }) => Promise<void>) | null>(null);
    const faceVadControllerRef = useRef(createFaceConversationVadController());
    // [Silero 근본 무음 게이트] 단말 진폭 미터가 죽은 기기(meter_unavailable)에서 file-growth VAD는
    // 무음과 발화를 구분하지 못해 Whisper 환각이 발화로 누수된다. VoIP 경로처럼 Silero 네이티브 VAD를
    // 대면/소리새 AI capture에 병행 가동해, 실제 음성(speech_start) 발생 + 네이티브 PCM 실제 RMS로
    // 무음 세그먼트를 전송 전에 차단한다. 네이티브 모듈 미가용/실패 시 기존 expo 경로로 폴백한다.
    const faceSileroSupportedRef = useRef<boolean>(false);
    const faceSileroActiveRef = useRef<boolean>(false);
    const faceSileroCaptureActiveRef = useRef<boolean>(false);
    const faceSileroCaptureUriRef = useRef<string | null>(null);
    const faceSileroFirstSpeechAtMsRef = useRef<number | null>(null);
    const mainLastAutoVoiceRelayRef = useRef<{ key: string; sentAt: number } | null>(null);
    /** 최근 기기가 발화한 통역문/원문 이력. 마이크로 되돌아온 TTS(지연 도착 포함)를 재번역하는 핑퐁 에코를 차단한다. */
    const faceSpokenHistoryRef = useRef<Array<{ transcript: string; translated: string; toLang: LangCode; spokenAtMs: number }>>([]);
    /**
     * 반이중(half-duplex) 게이트: 통역 음성을 출력(TTS)하는 동안 true.
     * true인 동안에는 절대 듣기(녹음)를 시작하지 않아 발화와 듣기가 겹치지 않는다.
     * 재생 완료 후 잔향이 가라앉도록 drain 지연을 둔 뒤 false로 해제한다.
     */
    const faceSpeakingRef = useRef(false);
    // [2-5 AEC/NS] 대면 통역 capture가 통신 오디오 모드(MODE_IN_COMMUNICATION)를 직접 켰는지 추적.
    // 우리가 켠 경우에만 해제해, VoIP 통화 화면이 설정한 통화 오디오 모드를 망가뜨리지 않는다.
    const faceVoipAudioEnabledRef = useRef(false);
    /** 직전에 발화(TTS)한 통역문. 동일 출력이 가드창 안에서 반복 발화되는 것을 차단한다. */
    const lastFaceSpokenOutputRef = useRef<{ text: string; at: number } | null>(null);
    /**
     * 대면 화면 사용 용도: 'translate'(통역 — 상대 언어로 번역) | 'gpt'(친구 모드 — 자연스러운 AI 친구 대화).
     * 기본은 통역. 친구 모드는 음성을 전용 친구 채팅 경로(/voice/friend-chat)로 보내
     * 따뜻하고 자연스러운 답변을 받아 화면 표시 + 음성(TTS)으로 읽어준다(번역/에코 로직을 타지 않음).
     */
    const [faceAiMode, setFaceAiMode] = useState<'translate' | 'gpt'>('translate');
    const faceAiModeRef = useRef<'translate' | 'gpt'>('translate');
    /** 친구 모드 멀티턴 메모리 — 최근 대화(role/content)를 누적해 자연스러운 맥락 유지. */
    const faceGptConversationRef = useRef<Array<{ role: string; content: string }>>([]);
    /**
     * [Phase5.8] 진화형 동반자 페르소나(온디바이스). 세션을 넘는 성격·습관·관심 기억을
     * 보관하고, 친구챗 요청 시 압축 브리프를 주입한다(서버 영속화 0). 마운트 시 1회 로드.
     */
    const companionPersonaRef = useRef<CompanionPersona>(createEmptyPersona());
    useEffect(() => {
        let alive = true;
        loadPersona().then((p) => { if (alive) companionPersonaRef.current = p; }).catch(() => {});
        // [Phase6.0] 저장된 "나의 AI 이름" → "OOOO AI" 표시명 복원(없으면 기본 "소리새 AI").
        loadAiDisplayName().then((name) => { if (alive) setAiDisplayName(name); }).catch(() => {});
        return () => { alive = false; };
    }, []);
    // 캡처 루프 콜백이 최신 AI 이름을 웨이크워드 후보 산출에 쓰도록 ref 미러 유지.
    useEffect(() => { aiDisplayNameRef.current = aiDisplayName; }, [aiDisplayName]);
    /**
     * 친구 모드 자기에코 차단 — 방금 소리새 AI가 발화(TTS)한 답변 텍스트를 보관한다.
     * 다음 전사(STT)가 이 답변과 충분히 겹치면 '마이크가 자기 음성을 다시 주워담은 것'으로 보고
     * 그 턴을 버려, 혼자 묻고 혼자 답하는 무한 루프를 끊는다.
     */
    const faceGptSpokenEchoRef = useRef<Array<{ text: string; atMs: number }>>([]);
    /** 소리새 AI 질문/답변 표출 로그(좌=질문/입력언어, 우=답변/출력언어). */
    const [sorisaeQaLog, setSorisaeQaLog] = useState<Array<{
        id: number; question: string; questionLang: string; answer: string; answerLang: string; atMs: number;
    }>>([]);
    const sorisaeQaSeqRef = useRef(0);
    /** 소리새 AI 전용 창(대면 통역창과 분리) — 움직이는 플로팅 심볼로 열고 닫는다. */
    const [sorisaeWindowOpen, setSorisaeWindowOpen] = useState(false);
    /**
     * 소리새 창 활성 ref(처리 분기의 단일 진실원천).
     * 음성 세그먼트를 '소리새(질문/관광/대화)'로 보낼지 '대면 통역'으로 보낼지는
     * faceAiMode 상태(비동기·레이스 위험) 가 아니라 **이 ref(창 열림 여부)** 로만 판정한다.
     * → 소리새 창이 열려있으면 항상 friend-chat, 닫혀있으면 항상 voice-translate(완전 분리).
     */
    const sorisaeWindowOpenRef = useRef(false);
    /**
     * [기능 분리 Phase1] 소리새↔대면통역 완전 격리용 전용 자원.
     * - mainSorisaeRouteRef: 이 세그먼트를 소리새로 보낼지의 **캡처 시작 시점 스냅샷**.
     *   처리 시점에 라이브 ref(sorisaeWindowOpenRef)를 다시 읽으면 창 개폐 레이스로 경로가 뒤바뀐다.
     * - sorisaeSpeakingRef: 소리새 전용 반이중 게이트(대면 faceSpeakingRef와 분리).
     * - sorisaeVoicePlaybackSoundRef: 소리새 전용 TTS 재생 핸들(대면 faceVoicePlaybackSoundRef와 분리).
     */
    const mainSorisaeRouteRef = useRef(false);
    const sorisaeSpeakingRef = useRef(false);
    const sorisaeVoicePlaybackSoundRef = useRef<AudioSound | null>(null);
    /**
     * [Phase6.1] 소리새 음성 호출형(웨이크워드) — 로그인 상태에서 이름을 부르면 깨어나고,
     * 3분 무활동이면 자동으로 잠든다. dormant(웨이크워드 대기) 동안엔 통역 캡처 루프의
     * 전사를 가로채 이름 호명만 감시하고, awake 진입 시 소리새 창을 연다(SSOT는 순수 상태기계).
     */
    const [companionVoiceCallArmed, setCompanionVoiceCallArmed] = useState(false);
    const companionVoiceCallRef = useRef<CompanionVoiceCallState>(createCompanionVoiceCallState());
    const companionVoiceCallArmedRef = useRef(false);
    useEffect(() => { companionVoiceCallArmedRef.current = companionVoiceCallArmed; }, [companionVoiceCallArmed]);
    /** 캡처 루프 콜백에서 최신 AI 표시명을 읽기 위한 ref 미러. */
    const aiDisplayNameRef = useRef(DEFAULT_AI_DISPLAY_NAME);
    /** 웨이크워드 감지 시 호출할 '깨우기' 루틴(나중에 정의되는 콜백을 ref 로 가리켜 캡처 루프에서 호출). */
    const wakeCompanionVoiceCallNowRef = useRef<() => void>(() => {});
    /** 플로팅 심볼 위치(드래그 이동) — 화면 우측 상단 1/3 지점 기본값(아래로 너무 가지 않게). */
    const sorisaeBtnPos = useRef(new Animated.ValueXY({
        x: Dimensions.get('window').width - 74,
        y: Math.round(Dimensions.get('window').height * 0.32),
    })).current;
    /** 이번 제스처가 '드래그'였는지(이동량 임계 초과). false면 '탭'으로 보고 창을 연다. */
    const sorisaeDragMovedRef = useRef(false);
    const sorisaePanResponder = useRef(
        PanResponder.create({
            onStartShouldSetPanResponder: () => true,
            onMoveShouldSetPanResponder: (_e, g) => Math.abs(g.dx) > 4 || Math.abs(g.dy) > 4,
            onPanResponderGrant: () => {
                sorisaeDragMovedRef.current = false;
                sorisaeBtnPos.extractOffset();
            },
            onPanResponderMove: (e, g) => {
                if (Math.abs(g.dx) > 4 || Math.abs(g.dy) > 4) {
                    sorisaeDragMovedRef.current = true;
                }
                Animated.event(
                    [null, { dx: sorisaeBtnPos.x, dy: sorisaeBtnPos.y }],
                    { useNativeDriver: false },
                )(e, g);
            },
            onPanResponderRelease: () => {
                sorisaeBtnPos.flattenOffset();
                // 거의 안 움직였으면 '탭' → 소리새 AI 전용 창 열기.
                if (!sorisaeDragMovedRef.current) {
                    sorisaeWindowOpenRef.current = true;
                    setSorisaeWindowOpen(true);
                }
            },
        }),
    ).current;
    /** 소리새 AI 음성 인식 결과 → AI 여행 일정 패널 입력 자동 연결(seed). nonce 로 동일 발화 재주입도 트리거. */
    const [itinerarySeedQuery, setItinerarySeedQuery] = useState('');
    const [itinerarySeedNonce, setItinerarySeedNonce] = useState(0);
    const [songModeEnabled, setSongModeEnabled] = useState(false);
    const [songModeStatus, setSongModeStatus] = useState('');
    const [songSubtitles, setSongSubtitles] = useState<SongSubtitleEntry[]>([]);
    const songSubtitleSeqRef = useRef(0);
    const [songFileLoading, setSongFileLoading] = useState(false);
    const [songFileName, setSongFileName] = useState('');
    const [songFileJob, setSongFileJob] = useState<SongFileJobStatus | null>(null);
    const [songFileSegments, setSongFileSegments] = useState<SongFileTimelineSegment[]>([]);
    const [songFilePlaybackMs, setSongFilePlaybackMs] = useState(0);
    const [songFilePlaying, setSongFilePlaying] = useState(false);
    const [songFileExportPreview, setSongFileExportPreview] = useState('');
    const songFileSoundRef = useRef<AudioSound | null>(null);
    const voicePreviewSoundRef = useRef<AudioSound | null>(null);
    const faceVoicePlaybackSoundRef = useRef<AudioSound | null>(null);
    const incomingVoipAlertActiveRef = useRef(false);
    const incomingVoipAlertCallIdRef = useRef<string | null>(null);
    const incomingVoipVibrationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const incomingVoipVibrationMaxTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    // 월드링코 설정: 수신 알림 소리/진동/무음. ref 는 startIncomingVoipAlert 콜백에서 최신값을 읽기 위함.
    const [incomingAlertSoundMode, setIncomingAlertSoundMode] = useState<IncomingAlertSoundMode>('sound');
    const incomingAlertSoundModeRef = useRef<IncomingAlertSoundMode>('sound');
    const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
    // [설정 탭] 전역 토글 + 사용설명서 풀스크린(APP_DESIGN 2-6). 프로필 모달(isSettingsModalOpen)과 별개.
    const [settingsTabOpen, setSettingsTabOpen] = useState(false);
    const globalSettings = useGlobalSettings();

    useEffect(() => {
        // 설정값을 단말에서 1회 로드(소리/진동/무음).
        void (async () => {
            try {
                const raw = await AsyncStorage.getItem(WORLDLINCO_SETTINGS_STORAGE_KEY);
                if (!raw) return;
                const parsed = JSON.parse(raw) as { incomingAlertSoundMode?: IncomingAlertSoundMode };
                const mode = parsed?.incomingAlertSoundMode;
                if (mode === 'sound' || mode === 'vibrate' || mode === 'silent') {
                    setIncomingAlertSoundMode(mode);
                    incomingAlertSoundModeRef.current = mode;
                }
            } catch {
                // 손상된 설정은 기본값(sound)으로 무시.
            }
        })();
    }, []);

    const updateIncomingAlertSoundMode = useCallback((mode: IncomingAlertSoundMode) => {
        setIncomingAlertSoundMode(mode);
        incomingAlertSoundModeRef.current = mode;
        void AsyncStorage.setItem(
            WORLDLINCO_SETTINGS_STORAGE_KEY,
            JSON.stringify({ incomingAlertSoundMode: mode }),
        ).catch(() => { /* best-effort 저장 */ });
    }, []);

    // ── 설정 모달: 내정보(국가·언어) ──
    const [settingsProfileSaving, setSettingsProfileSaving] = useState(false);
    const [settingsProfileError, setSettingsProfileError] = useState('');
    const [settingsProfileSuccess, setSettingsProfileSuccess] = useState('');
    const [settingsCountryPickerOpen, setSettingsCountryPickerOpen] = useState(false);
    const [settingsLangPickerOpen, setSettingsLangPickerOpen] = useState(false);

    const openSettingsModal = useCallback(() => {
        setSettingsProfileError('');
        setSettingsProfileSuccess('');
        setSettingsCountryPickerOpen(false);
        setSettingsLangPickerOpen(false);
        setIsSettingsModalOpen(true);
    }, []);

    const handleSettingsChangeCountry = useCallback((code: string) => {
        setSettingsCountryPickerOpen(false);
        setSettingsProfileError('');
        setSettingsProfileSuccess('');
        if (!token || !userInfo) {
            setSettingsProfileError('로그인 후 변경할 수 있습니다.');
            return;
        }
        setSettingsProfileSaving(true);
        void (async () => {
            try {
                const updated = await callUpdateMeApi(token, { country_code: code } as UserProfileUpdatePayload);
                setUserInfo(updated);
                await saveStoredAuthState(token, updated);
                setSettingsProfileSuccess('국가가 저장되었습니다.');
            } catch (error: any) {
                setSettingsProfileError(error?.message || '국가 저장에 실패했습니다.');
            } finally {
                setSettingsProfileSaving(false);
            }
        })();
    }, [token, userInfo]);

    const handleSettingsChangeLanguage = useCallback((code: string) => {
        setSettingsLangPickerOpen(false);
        setSettingsProfileError('');
        setSettingsProfileSuccess('');
        if (!token || !userInfo) {
            setSettingsProfileError('로그인 후 변경할 수 있습니다.');
            return;
        }
        setSettingsProfileSaving(true);
        void (async () => {
            try {
                const updated = await callUpdateMeApi(token, { preferred_language: code });
                setUserInfo(updated);
                await saveStoredAuthState(token, updated);
                setSettingsProfileSuccess('통역/번역 언어가 저장되었습니다.');
            } catch (error: any) {
                setSettingsProfileError(error?.message || '언어 저장에 실패했습니다.');
            } finally {
                setSettingsProfileSaving(false);
            }
        })();
    }, [token, userInfo]);

    const handleOpenPasswordChangeFromSettings = useCallback(() => {
        // 기존 비밀번호 변경 모달을 재사용한다(중복 구현 방지).
        setIsSettingsModalOpen(false);
        openPasswordChange();
    }, [openPasswordChange]);
    const [voiceConsent, setVoiceConsent] = useState<VoiceConsentResponse | null>(null);
    const [voiceProfile, setVoiceProfile] = useState<VoiceProfileResponse | null>(null);
    const [voiceProfileLoading, setVoiceProfileLoading] = useState(false);
    const [voiceProfileRecording, setVoiceProfileRecording] = useState(false);
    const [voiceProfileStatus, setVoiceProfileStatus] = useState('');
    const [voicePreview, setVoicePreview] = useState<VoicePreviewResponse | null>(null);
    const [voiceLicenseMode, setVoiceLicenseMode] = useState<VoiceLicenseMode>('private_preview_unverified');
    const [voiceOutputScope, setVoiceOutputScope] = useState<VoiceOutputScope>('private_preview');
    const [voiceRightsAcknowledged, setVoiceRightsAcknowledged] = useState(false);
    const voiceProfileRecordingRef = useRef<AudioRecording | null>(null);
    // 통화 입력란 예약처 전화 자동삽입의 직전 값(사용자 수동 입력 보존 판단용).
    const lastAutoFilledPhoneRef = useRef('');

    const selectedNearbyPlace = nearbyPlaces.find((item) => item.id === selectedNearbyPlaceId) ?? nearbyPlaces[0] ?? null;
    const selectedBookingPlace = nearbyPlaces.find((item) => item.id === selectedBookingPlaceId) ?? null;
    // [예약처 자동삽입] 통화 입력란에 채울 전화번호(구조화 예약 선택과 분리).
    // 우선순위: 선택된 예약 호텔 전화 → 주변검색 결과 중 전화 있는 첫 장소 → 예약 확정 지원전화.
    // 식당/명소 등 예약불가 장소여도 '전화 연결'은 가능해야 하므로 전화 자동삽입은 카테고리를 가리지 않는다.
    const bookingAutoFillPhone = String(
        selectedBookingPlace?.phone
        || nearbyPlaces.find((place) => String(place.phone || '').trim().length > 0)?.phone
        || bookingResult?.support_phone
        || '',
    ).trim();
    useEffect(() => {
        if (!bookingAutoFillPhone) {
            return;
        }
        const current = String(interCallPhone || '').trim();
        // 사용자가 직접 입력/수정한 번호는 덮어쓰지 않는다. (비어있거나 직전 자동삽입값과 동일할 때만 갱신)
        if (current && current !== lastAutoFilledPhoneRef.current) {
            return;
        }
        if (current === bookingAutoFillPhone) {
            lastAutoFilledPhoneRef.current = bookingAutoFillPhone;
            return;
        }
        lastAutoFilledPhoneRef.current = bookingAutoFillPhone;
        setInterCallPhone(bookingAutoFillPhone);
    }, [bookingAutoFillPhone, interCallPhone, setInterCallPhone]);
    const nearbyCenterLat = Number.parseFloat(lat);
    const nearbyCenterLon = Number.parseFloat(lon);
    const nearbyMapHtml = nearbyPlaces.length > 0 && Number.isFinite(nearbyCenterLat) && Number.isFinite(nearbyCenterLon)
        ? buildNearbyMapHtml({
            centerLat: nearbyCenterLat,
            centerLon: nearbyCenterLon,
            places: nearbyPlaces,
            selectedPlaceId: selectedNearbyPlace?.id || '',
        })
        : '';
    const activeSongFileSegment = songFileSegments.find((segment) => songFilePlaybackMs >= segment.start_ms && songFilePlaybackMs <= segment.end_ms) ?? null;
    const translationRequestSeqRef = useRef(0);
    const latestTranslationMetaRef = useRef<{ source: LangCode; target: LangCode; translated: string } | null>(null);
    const [translationEpoch, setTranslationEpoch] = useState(0);
    const currentVoipPreferredLanguage = (() => {
        // 로컬 직접 지정(실험/베타)이 있으면 백엔드 고정 언어보다 우선한다.
        if (voipLocalLangOverride && isSupportedLangCode(voipLocalLangOverride)) {
            return voipLocalLangOverride;
        }
        const normalized = String(userInfo?.preferred_language || '').trim().toLowerCase();
        return isSupportedLangCode(normalized) ? normalized : fromLang;
    })();
    const isVoipLangLocallyOverridden = Boolean(voipLocalLangOverride && isSupportedLangCode(voipLocalLangOverride));
    const currentVoipCountryCode = String(userInfo?.country_code || '').trim().toUpperCase() || resolveLocaleCountryCode();
    const currentVoipProfile: VoipParticipantProfile = {
        nickname: userInfo?.username || userInfo?.email.split('@')[0] || '게스트',
        genderLabel: formatVoipGenderLabel(voipProfileGender),
        countryCode: currentVoipCountryCode,
        countryName: resolveCountryName(currentVoipCountryCode),
        voiceId: voipIdentity || (userInfo ? buildVoiceId(userInfo.id) : 'voice-id-waiting'),
        countryFlag: resolveCountryFlag(currentVoipCountryCode),
        preferredLanguage: currentVoipPreferredLanguage,
    };
    const remoteVoipPreferredLanguage = (() => {
        const normalized = String(
            voipActiveProfile?.preferredLanguage
            || voipCallInitResponse?.display_language
            || pendingIncomingVoipCall?.display_language
            || '',
        ).trim().toLowerCase();
        return isSupportedLangCode(normalized) ? normalized : null;
    })();
    const effectiveVoipSourceLang: LangCode = currentVoipPreferredLanguage;
    const effectiveVoipTargetLang: LangCode = remoteVoipPreferredLanguage && remoteVoipPreferredLanguage !== effectiveVoipSourceLang
        ? remoteVoipPreferredLanguage
        : resolveAutoTargetLang(effectiveVoipSourceLang, toLang);

    const clearBookingSelectionNoticeTimer = useCallback(() => {
        if (bookingSelectionNoticeTimerRef.current) {
            clearTimeout(bookingSelectionNoticeTimerRef.current);
            bookingSelectionNoticeTimerRef.current = null;
        }
    }, []);

    const showBookingSelectionFeedback = useCallback((message: string) => {
        setBookingSelectionNotice(message);
        clearBookingSelectionNoticeTimer();
        bookingSelectionNoticeTimerRef.current = setTimeout(() => {
            setBookingSelectionNotice('');
            bookingSelectionNoticeTimerRef.current = null;
        }, 12000);
        if (Platform.OS === 'android') {
            ToastAndroid.show(message, ToastAndroid.SHORT);
        }
    }, [clearBookingSelectionNoticeTimer]);

    const selectBookingPlace = useCallback((placeId: string, sourceLabel: '지도' | '목록', focusTravelSection = false) => {
        const place = nearbyPlaces.find((item) => item.id === placeId);
        if (!place) {
            return;
        }
        setSelectedNearbyPlaceId(placeId);
        setSelectedBookingPlaceId(placeId);
        if (focusTravelSection) {
            setActiveRailSection('travel-booking');
        }
        showBookingSelectionFeedback(`${sourceLabel}에서 ${place.name} 예약 대상으로 선택됨`);
    }, [nearbyPlaces, showBookingSelectionFeedback]);

    useEffect(() => () => {
        clearBookingSelectionNoticeTimer();
    }, [clearBookingSelectionNoticeTimer]);

    const buildVoipRemoteProfile = useCallback((
        label: string | undefined,
        voiceId: string | undefined,
        displayCountryCode: string | undefined,
        displayLanguage: string | undefined,
    ): VoipParticipantProfile => {
        const countryCode = (displayCountryCode || 'UN').toUpperCase();
        return {
            nickname: label || voiceId || '보이스톡 상대',
            genderLabel: '미설정',
            countryCode,
            countryName: displayCountryCode ? resolveCountryName(displayCountryCode) : '국가 미상',
            voiceId: voiceId || label || 'unknown-voice-id',
            countryFlag: displayCountryCode ? resolveCountryFlag(displayCountryCode) : '🌐',
            preferredLanguage: displayLanguage || undefined,
        };
    }, []);

    const populateIncomingVoipPresentation = useCallback((
        normalizedPayload: CallInitResponse,
        payload: Partial<CallInitResponse> & { caller_label?: string; caller_voice_id?: string },
    ) => {
        setVoipActiveProfile(buildVoipRemoteProfile(
            payload.caller_label || normalizedPayload.display_label || payload.caller_voice_id || '수신 보이스톡',
            payload.caller_voice_id || normalizedPayload.display_label,
            normalizedPayload.display_country_code,
            normalizedPayload.display_language,
        ));
        setVoipPhone(payload.caller_label || normalizedPayload.display_label || payload.caller_voice_id || '수신 통화');
        setVoipInitError('');
        setVoipInitLoading(false);
        setVoipAuditCallId(normalizedPayload.call_id);
        setVoipAuditEvents([]);
        setVoipAuditError('');
        setShowFriendFolder(false);
        setShowVoipTester(true);
    }, [buildVoipRemoteProfile]);

    const activateAcceptedIncomingVoipCall = useCallback((
        acceptedPayload: CallInitResponse & { caller_label?: string; caller_voice_id?: string },
        source: string,
    ) => {
        const callerLanguageHint = resolveVoipRemoteLanguageHint(
            acceptedPayload.display_language,
            pendingIncomingVoipCallRef.current?.display_language,
        );
        const normalizedAcceptedPayload = callerLanguageHint
            ? { ...acceptedPayload, display_language: callerLanguageHint }
            : acceptedPayload;
        populateIncomingVoipPresentation(normalizedAcceptedPayload, normalizedAcceptedPayload);
        const calleePayload: CallInitResponse = {
            ...normalizedAcceptedPayload,
            participant_role: 'callee',
        };
        logUiPressProbe('VOIP_INCOMING_CALL_ACCEPTED', {
            source,
            call_id: calleePayload.call_id,
            caller_voice_id: calleePayload.caller_voice_id ?? null,
            requested_mode: calleePayload.requested_mode ?? null,
            resolved_mode: calleePayload.resolved_mode ?? null,
            auto_relay_requested: calleePayload.auto_relay_requested ?? null,
            auto_relay_applied: calleePayload.auto_relay_applied ?? null,
            callee_source_lang: currentVoipPreferredLanguage,
            callee_target_lang: calleePayload.display_language ?? null,
        });
        setPendingIncomingVoipCall(null);
        setActiveRailSection('voip');
        setCallMode(resolveCallModeFromPayload(calleePayload));
        setShowVoipTester(true);
        setVoipCallInitResponse(calleePayload);
        setIncomingVoipAcceptInFlight(null);
        void saveStoredActiveVoipSession(calleePayload.call_id, 'voip', 'callee');
    }, [currentVoipPreferredLanguage, logUiPressProbe, populateIncomingVoipPresentation, setCallMode, setIncomingVoipAcceptInFlight]);

    const stopIncomingVoipAlert = useCallback((source: string) => {
        if (incomingVoipVibrationIntervalRef.current) {
            clearInterval(incomingVoipVibrationIntervalRef.current);
            incomingVoipVibrationIntervalRef.current = null;
        }
        if (incomingVoipVibrationMaxTimerRef.current) {
            clearTimeout(incomingVoipVibrationMaxTimerRef.current);
            incomingVoipVibrationMaxTimerRef.current = null;
        }
        const wasActive = incomingVoipAlertActiveRef.current;
        incomingVoipAlertActiveRef.current = false;
        incomingVoipAlertCallIdRef.current = null;
        void stopNativeIncomingVoipAlert();
        // Expo 로컬 착신 알림도 반드시 내린다 — 안 내리면 systemui 가 알림 링톤을 계속 재생해
        // 받기/끊기 후에도 수신 벨이 멈추지 않는다(누적된 과거 알림까지 채널 기준 정리).
        void dismissIncomingVoipLocalNotification();
        getVoIPToneService().stopAll();
        if (Platform.OS !== 'web') {
            Vibration.cancel();
        }
        if (wasActive) {
            logUiPressProbe('VOIP_INCOMING_ALERT_STOPPED', {
                source,
                active_call_id: voipCallInitResponseRef.current?.call_id ?? null,
            });
        }
    }, [logUiPressProbe]);

    const postIncomingVoipLocalNotification = useCallback(async (
        callId: string,
        callerVoiceId?: string | null,
        callerLabel?: string | null,
        probeEvent: 'VOIP_INCOMING_ALERT_NOTIFICATION_POSTED' | 'VOIP_INCOMING_ALERT_NOTIFICATION_REASSERTED' = 'VOIP_INCOMING_ALERT_NOTIFICATION_POSTED',
    ) => {
        if (Platform.OS !== 'android') {
            return;
        }
        try {
            await showIncomingVoipLocalNotification({
                type: 'incoming_call',
                call_id: callId,
                caller_voice_id: callerVoiceId ?? undefined,
                caller_label: callerLabel ?? callerVoiceId ?? '친구',
                status: 'ringing',
            });
            logUiPressProbe(probeEvent, { call_id: callId, app_state: AppState.currentState });
        } catch (error: any) {
            logUiPressProbe('VOIP_INCOMING_ALERT_NOTIFICATION_FAILED', {
                call_id: callId,
                error_message: error?.message || 'unknown',
                app_state: AppState.currentState,
            });
        }
    }, [logUiPressProbe]);

    const startIncomingVoipAlert = useCallback((
        callId: string,
        callerVoiceId?: string | null,
        callerLabel?: string | null,
        options?: { reassert?: boolean },
    ) => {
        if (incomingVoipAlertActiveRef.current) {
            if (options?.reassert || incomingVoipAlertCallIdRef.current === callId) {
                logUiPressProbe('VOIP_INCOMING_ALERT_REASSERT', {
                    call_id: callId,
                    caller_voice_id: callerVoiceId ?? null,
                    app_state: AppState.currentState,
                });
                // reassert 시에는 Expo 로컬 알림을 다시 게시하지 않는다.
                // 최초 1회 게시한 알림(고정 식별자)이 그대로 유지되며, 재게시하면 MAX 채널에서
                // 링톤이 매번 재생되어 "0.5~2.5초마다 따라 우는" 영구 벨의 원인이 된다.
                // 네이티브 착신 알림은 startNativeIncomingVoipAlert(멱등)가 유지한다.
                if (isVoipIncomingAlertNativeAvailable()) {
                    void startNativeIncomingVoipAlert(callId, callerLabel ?? callerVoiceId ?? '친구', incomingAlertSoundModeRef.current);
                } else if (Platform.OS !== 'web' && incomingAlertSoundModeRef.current !== 'silent') {
                    try {
                        Vibration.vibrate(800);
                    } catch {
                        // no-op
                    }
                }
            }
            return;
        }
        incomingVoipAlertActiveRef.current = true;
        incomingVoipAlertCallIdRef.current = callId;
        logUiPressProbe('VOIP_INCOMING_ALERT_STARTED', {
            call_id: callId,
            caller_voice_id: callerVoiceId ?? null,
            app_state: AppState.currentState,
        });

        void postIncomingVoipLocalNotification(callId, callerVoiceId, callerLabel);

        const playJsIncomingAlertFallback = () => {
            const alertMode = incomingAlertSoundModeRef.current;
            if (alertMode === 'sound') {
                try {
                    getVoIPToneService().playRingingTone();
                    logUiPressProbe('VOIP_INCOMING_ALERT_TONE_REQUESTED', { call_id: callId });
                } catch (error: any) {
                    logUiPressProbe('VOIP_INCOMING_ALERT_TONE_FAILED', {
                        call_id: callId,
                        error_message: error?.message || 'unknown',
                    });
                }
            }

            if (Platform.OS !== 'web' && alertMode !== 'silent') {
                try {
                    const pulseIncomingVibration = () => {
                        if (!incomingVoipAlertActiveRef.current) {
                            return;
                        }
                        Vibration.vibrate(800);
                    };
                    pulseIncomingVibration();
                    incomingVoipVibrationIntervalRef.current = setInterval(pulseIncomingVibration, 3000);
                    incomingVoipVibrationMaxTimerRef.current = setTimeout(() => {
                        stopIncomingVoipAlert('incoming_vibration_max_duration');
                    }, PENDING_INCOMING_RING_MAX_MS);
                    logUiPressProbe('VOIP_INCOMING_ALERT_VIBRATION_REQUESTED', { call_id: callId });
                } catch (error: any) {
                    logUiPressProbe('VOIP_INCOMING_ALERT_VIBRATION_FAILED', {
                        call_id: callId,
                        error_message: error?.message || 'unknown',
                    });
                }
            }
        };

        const callerLabelText = callerLabel ?? callerVoiceId ?? '친구';
        if (isVoipIncomingAlertNativeAvailable()) {
            void (async () => {
                const nativeStarted = await startNativeIncomingVoipAlert(callId, callerLabelText, incomingAlertSoundModeRef.current);
                logUiPressProbe(nativeStarted
                    ? 'VOIP_INCOMING_ALERT_NATIVE_STARTED'
                    : 'VOIP_INCOMING_ALERT_NATIVE_FAILED', {
                    call_id: callId,
                    app_state: AppState.currentState,
                });
                if (!nativeStarted) {
                    playJsIncomingAlertFallback();
                }
            })();
        } else {
            playJsIncomingAlertFallback();
        }
    }, [logUiPressProbe, postIncomingVoipLocalNotification, stopIncomingVoipAlert]);

    const applyIncomingVoipPayload = useCallback((payload: Partial<CallInitResponse> & { caller_label?: string; caller_voice_id?: string }, source: string) => {
        const fallbackCallMode = resolveCallModeFromPayload(payload);
        let inferredParticipantRole: 'caller' | 'callee' = payload.participant_role === 'callee' ? 'callee' : 'caller';
        if (payload.participant_role !== 'callee' && payload.signaling_server) {
            try {
                const signalingUrl = new URL(payload.signaling_server);
                inferredParticipantRole = signalingUrl.searchParams.get('role') === 'callee' ? 'callee' : 'caller';
            } catch {
                inferredParticipantRole = 'caller';
            }
        }
        const normalizedPayload: CallInitResponse = {
            call_id: payload.call_id || '',
            signaling_server: payload.signaling_server || '',
            turn_servers: normalizeTurnServers(payload.turn_servers),
            call_route: payload.call_route || 'app_webrtc',
            phone_dialer_required: payload.phone_dialer_required,
            fallback_dial_url: payload.fallback_dial_url,
            user_message: payload.user_message,
            callee_app_online: payload.callee_app_online,
            caller_user_id: payload.caller_user_id,
            caller_voice_id: payload.caller_voice_id,
            callee_voice_id: payload.callee_voice_id,
            callee_user_id: payload.callee_user_id,
            participant_role: inferredParticipantRole,
            display_label: payload.display_label,
            display_language: payload.display_language,
            display_country_code: payload.display_country_code,
            status: payload.status,
            requested_mode: normalizeCallModeCandidate(payload.requested_mode) ?? fallbackCallMode,
            resolved_mode: normalizeCallModeCandidate(payload.resolved_mode) ?? normalizeCallModeCandidate(payload.requested_mode) ?? fallbackCallMode,
            auto_relay_requested: payload.auto_relay_requested ?? false,
            auto_relay_applied: payload.auto_relay_applied ?? false,
            error_code: payload.error_code,
        };

        if (!normalizedPayload.call_id || !normalizedPayload.signaling_server) {
            logUiPressProbe('VOIP_INCOMING_CALL_IGNORED', { source, reason: 'missing_call_payload' });
            return;
        }

        // 자기가 건 통화를 수신 통화로 오인하지 않는다. 발신 직후 세션이 등록되기 전(active session
        // 억제 이전) 타이밍에 발신자의 수신 폴링이 자기 통화를 되받아 발신측에서도 신호음이 울리는
        // 회귀를 차단한다. 발신자 식별은 user_id(숫자) 우선, voice_id(nado-XXXXXX) 보조로 비교한다.
        const myUserId = userInfo?.id ?? null;
        const myVoiceId = myUserId != null ? buildVoiceId(myUserId) : null;
        const payloadCallerUserId = payload.caller_user_id ?? normalizedPayload.caller_user_id ?? null;
        const payloadCallerVoiceId = (payload.caller_voice_id ?? normalizedPayload.caller_voice_id ?? null);
        const selfOriginated = (
            (myUserId != null && payloadCallerUserId != null && Number(payloadCallerUserId) === Number(myUserId))
            || (!!myVoiceId && !!payloadCallerVoiceId && payloadCallerVoiceId === myVoiceId)
        );
        if (selfOriginated) {
            stopIncomingVoipAlert('self_originated_outgoing_call');
            setPendingIncomingVoipCall(null);
            logUiPressProbe('VOIP_INCOMING_CALL_IGNORED', {
                source,
                reason: 'self_originated_outgoing_call',
                call_id: normalizedPayload.call_id,
                caller_user_id: payloadCallerUserId ?? null,
                caller_voice_id: payloadCallerVoiceId ?? null,
            });
            return;
        }

        const activeCallId = voipCallInitResponseRef.current?.call_id ?? null;
        const acceptedCallId = acceptedIncomingVoipCallIdRef.current;
        if (
            activeCallId === normalizedPayload.call_id
            || acceptedCallId === normalizedPayload.call_id
        ) {
            logUiPressProbe('VOIP_INCOMING_CALL_SUPPRESSED_ACTIVE_SESSION', {
                source,
                call_id: normalizedPayload.call_id,
                active_call_id: activeCallId,
                accepted_call_id: acceptedCallId,
                status: normalizedPayload.status ?? null,
                caller_voice_id: payload.caller_voice_id ?? null,
            });
            return;
        }

        const existingPendingCall = pendingIncomingVoipCallRef.current;
        if (
            existingPendingCall?.call_id === normalizedPayload.call_id
            && existingPendingCall.signaling_server === normalizedPayload.signaling_server
            && (existingPendingCall.status ?? null) === (normalizedPayload.status ?? null)
            && (existingPendingCall.caller_voice_id ?? null) === (payload.caller_voice_id ?? null)
            && !voipCallInitResponseRef.current
        ) {
            if (isIncomingRingVoipStatus(normalizedPayload.status)) {
                logUiPressProbe('VOIP_INCOMING_CALL_DUPLICATE_REAPPLIED', {
                    source,
                    call_id: normalizedPayload.call_id,
                    status: normalizedPayload.status ?? null,
                    caller_voice_id: payload.caller_voice_id ?? null,
                });
                populateIncomingVoipPresentation(normalizedPayload, payload);
                setVoipCallInitResponse(null);
                setPendingIncomingVoipCall({
                    ...normalizedPayload,
                    caller_label: payload.caller_label,
                    caller_voice_id: payload.caller_voice_id,
                });
                startIncomingVoipAlert(
                    normalizedPayload.call_id,
                    payload.caller_voice_id ?? null,
                    payload.caller_label ?? null,
                    { reassert: true },
                );
                return;
            }

            logUiPressProbe('VOIP_INCOMING_CALL_DUPLICATE_SKIPPED', {
                source,
                call_id: normalizedPayload.call_id,
                status: normalizedPayload.status ?? null,
                caller_voice_id: payload.caller_voice_id ?? null,
            });
            return;
        }

        if (
            inferredParticipantRole === 'callee'
            && !isIncomingRingVoipStatus(normalizedPayload.status)
        ) {
            stopIncomingVoipAlert('non_ring_incoming_payload');
            logUiPressProbe('VOIP_INCOMING_CALL_IGNORED', {
                source,
                reason: 'non_ring_incoming_status',
                call_id: normalizedPayload.call_id,
                status: normalizedPayload.status ?? null,
                caller_voice_id: payload.caller_voice_id ?? null,
            });
            if (
                token
                && normalizedPayload.status === 'connecting'
                && acceptedIncomingVoipCallIdRef.current !== normalizedPayload.call_id
            ) {
                void requestEndVoipCall(API_BASE, token, normalizedPayload.call_id, 'stale_non_ring_session');
            }
            return;
        }

        const ownVoiceId = userInfo ? buildVoiceId(userInfo.id) : null;
        const isSelfIncomingPayload = Boolean(
            userInfo
            && (
                normalizedPayload.caller_user_id === userInfo.id
                || (ownVoiceId && normalizedPayload.caller_voice_id === ownVoiceId)
            )
        );
        if (isSelfIncomingPayload) {
            stopIncomingVoipAlert('self_incoming_payload');
            setPendingIncomingVoipCall(null);
            logUiPressProbe('VOIP_INCOMING_CALL_IGNORED', {
                source,
                reason: 'self_incoming_payload',
                call_id: normalizedPayload.call_id,
                caller_user_id: normalizedPayload.caller_user_id ?? null,
                caller_voice_id: normalizedPayload.caller_voice_id ?? null,
                own_voice_id: ownVoiceId,
            });
            return;
        }

        const compactSummary = summarizeIncomingVoipPayload({
            ...normalizedPayload,
            caller_voice_id: payload.caller_voice_id,
        });

        logUiPressProbe('VOIP_INCOMING_CALL_APPLIED', {
            source,
            call_id: normalizedPayload.call_id,
            ...compactSummary,
        });
        populateIncomingVoipPresentation(normalizedPayload, payload);
        setVoipCallInitResponse(null);
        setPendingIncomingVoipCall({
            ...normalizedPayload,
            caller_label: payload.caller_label,
            caller_voice_id: payload.caller_voice_id,
        });
    }, [API_BASE, logUiPressProbe, populateIncomingVoipPresentation, startIncomingVoipAlert, stopIncomingVoipAlert, summarizeIncomingVoipPayload, token, userInfo]);

    const handleFcmIncomingCall = useCallback(
        (callInit: CallInitResponse, callerLabel: string) => {
            applyIncomingVoipPayload(
                { ...callInit, caller_label: callerLabel },
                'fcm_push',
            );
        },
        [applyIncomingVoipPayload],
    );

    const handleOpenChatRoom = useCallback((room: ChatRoomSummary) => {
        setSelectedChatRoom(room);
        setActiveRailSection('chat');
        setShowFriendFolder(false);
        setShowFriendMapDiscovery(false);
    }, []);

    const handleOpenChatRoomById = useCallback(async (roomId: string, source: string) => {
        if (!token || !userInfo) {
            Alert.alert('로그인 필요', '채팅을 열려면 먼저 로그인해 주세요.');
            return;
        }
        try {
            const detail = await getChatRoomDetail(API_BASE, token, roomId);
            const summary: ChatRoomSummary = {
                room_id: detail.room_id,
                room_type: detail.room_type as ChatRoomSummary['room_type'],
                title: detail.title,
                member_count: detail.members.length,
                member_limit: detail.member_limit,
                allow_member_invites: detail.allow_member_invites,
                can_invite_members: detail.can_invite_members,
                unread_count: 0,
                last_message_preview: '',
                last_message_at: new Date().toISOString(),
                counterpart: detail.counterpart,
            };
            handleOpenChatRoom(summary);
            setChatRefreshKey((prev) => prev + 1);
            logUiPressProbe('CHAT_DEEP_LINK_OPEN', { source, room_id: roomId });
        } catch (error: unknown) {
            Alert.alert('채팅 열기 실패', error instanceof Error ? error.message : '채팅방을 열지 못했습니다.');
            logUiPressProbe('CHAT_DEEP_LINK_OPEN_FAILED', {
                source,
                room_id: roomId,
                error_message: error instanceof Error ? error.message : 'unknown',
            });
        }
    }, [API_BASE, handleOpenChatRoom, logUiPressProbe, token, userInfo]);

    useVoipIncomingCalls({
        apiBaseUrl: API_BASE,
        authToken: token || '',
        messaging: Platform.OS === 'android' ? voipMessagingAdapter : null,
        onIncomingCall: handleFcmIncomingCall,
        onIncomingCallPayload: applyIncomingVoipPayload,
        onChatMessageOpened: handleOpenChatRoomById,
    });

    const autoAcceptIncomingVoipDeepLink = useCallback(async (
        payload: CallInitResponse & { caller_label?: string; caller_voice_id?: string },
        source: string,
    ) => {
        if (payload.participant_role !== 'callee') {
            applyIncomingVoipPayload(payload, source);
            return;
        }
        if (acceptingIncomingVoipCallRef.current) {
            return;
        }

        acceptedIncomingVoipCallIdRef.current = payload.call_id;
        setIncomingVoipAcceptInFlight(payload.call_id);
        const alertWasActive = incomingVoipAlertActiveRef.current;
        stopIncomingVoipAlert(`${source}_deep_link_auto_accept`);

        logUiPressProbe('VOIP_INCOMING_DEEP_LINK_AUTO_ACCEPT_START', {
            source,
            call_id: payload.call_id,
            caller_voice_id: payload.caller_voice_id ?? null,
            alert_was_active: alertWasActive,
        });

        const hasPermission = await requestPermissions(['RECORD_AUDIO'], 'VoIP 수신 통화', (msg) => {
            setVoipInitError(msg);
            logUiPressProbe('VOIP_INCOMING_DEEP_LINK_AUTO_ACCEPT_BLOCKED_PERMISSION', {
                source,
                permission: 'RECORD_AUDIO',
                call_id: payload.call_id,
            });
        });
        if (!hasPermission) {
            setIncomingVoipAcceptInFlight(null);
            applyIncomingVoipPayload(payload, `${source}_permission_blocked`);
            return;
        }

        logUiPressProbe('VOIP_INCOMING_DEEP_LINK_AUTO_ACCEPT_PERMISSION_GRANTED', {
            source,
            call_id: payload.call_id,
            caller_voice_id: payload.caller_voice_id ?? null,
        });

        let mergedPayload: CallInitResponse & { caller_label?: string; caller_voice_id?: string } = {
            ...payload,
            participant_role: 'callee',
        };
        if (token) {
            try {
                const acceptedFromServer = await acceptIncomingCall(API_BASE, token, payload.call_id);
                const callerLanguageHint = resolveVoipRemoteLanguageHint(
                    payload.display_language,
                    pendingIncomingVoipCallRef.current?.display_language,
                    acceptedFromServer.display_language,
                );
                mergedPayload = {
                    ...payload,
                    ...acceptedFromServer,
                    participant_role: 'callee',
                    caller_label: payload.caller_label,
                    caller_voice_id: payload.caller_voice_id ?? acceptedFromServer.caller_voice_id,
                    display_language: callerLanguageHint ?? acceptedFromServer.display_language,
                };
                logUiPressProbe('VOIP_INCOMING_ACCEPT_API_OK', {
                    source: `${source}_deep_link_auto_accept`,
                    call_id: mergedPayload.call_id,
                    display_language: mergedPayload.display_language ?? null,
                    signaling_server: mergedPayload.signaling_server ?? null,
                    status: mergedPayload.status ?? null,
                });
            } catch (acceptError: any) {
                const snapshot = await fetchVoipCallResumeSnapshot(API_BASE, token, payload.call_id);
                logUiPressProbe('VOIP_INCOMING_ACCEPT_API_FAIL', {
                    source: `${source}_deep_link_auto_accept`,
                    call_id: payload.call_id,
                    error_message: acceptError?.message || 'unknown',
                    snapshot_call_id: snapshot?.call_id ?? null,
                    snapshot_display_language: snapshot?.display_language ?? null,
                });
                if (snapshot?.call_id) {
                    const callerLanguageHint = resolveVoipRemoteLanguageHint(
                        payload.display_language,
                        pendingIncomingVoipCallRef.current?.display_language,
                        snapshot.display_language,
                    );
                    mergedPayload = {
                        ...payload,
                        ...snapshot,
                        participant_role: 'callee',
                        caller_label: payload.caller_label,
                        caller_voice_id: payload.caller_voice_id ?? snapshot.caller_voice_id,
                        display_language: callerLanguageHint ?? snapshot.display_language,
                    };
                }
            }
        }

        activateAcceptedIncomingVoipCall(mergedPayload, `${source}_deep_link_auto_accept`);
    }, [API_BASE, activateAcceptedIncomingVoipCall, applyIncomingVoipPayload, logUiPressProbe, requestPermissions, setIncomingVoipAcceptInFlight, stopIncomingVoipAlert, token]);

    const dismissPendingIncomingAsMissed = useCallback((
        source: string,
        reason: string,
        pendingCall: (CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null,
    ) => {
        if (!pendingCall?.call_id) {
            return;
        }

        stopIncomingVoipAlert(`${source}:${reason}`);

        const callerLabel = pendingCall.caller_label
            || pendingCall.display_label
            || pendingCall.caller_voice_id
            || '상대';
        logUiPressProbe('VOIP_PENDING_CALL_DISMISSED_MISSED', {
            source,
            reason,
            call_id: pendingCall.call_id,
            caller_voice_id: pendingCall.caller_voice_id ?? null,
            accept_in_flight_call_id: acceptingIncomingVoipCallIdRef.current,
        });
        acceptedIncomingVoipCallIdRef.current = null;
        setIncomingVoipAcceptInFlight(null);
        void clearStoredActiveVoipSession();
        setPendingIncomingVoipCall(null);
        if (Platform.OS === 'android') {
            ToastAndroid.show(`${callerLabel}님의 부재중 보이스톡`, ToastAndroid.SHORT);
        } else {
            Alert.alert('부재중 보이스톡', `${callerLabel}님의 보이스톡을 받지 못했습니다.`);
        }
    }, [logUiPressProbe, setIncomingVoipAcceptInFlight, stopIncomingVoipAlert]);

    const resolveStalePendingIncomingCall = useCallback(async (
        source: string,
        reason: string,
    ): Promise<boolean> => {
        const localPending = pendingIncomingVoipCallRef.current;
        if (!localPending?.call_id || !token) {
            return false;
        }

        const snapshot = await fetchVoipCallResumeSnapshot(API_BASE, token, localPending.call_id);
        if (snapshot?.call_id === localPending.call_id && isIncomingRingVoipStatus(snapshot.status)) {
            logUiPressProbe('VOIP_PENDING_CALL_CLEAR_SKIPPED', {
                source,
                reason: 'server_still_ringing',
                call_id: localPending.call_id,
                status: snapshot.status ?? null,
                caller_voice_id: localPending.caller_voice_id ?? null,
            });
            return false;
        }

        if (snapshot?.call_id === localPending.call_id && snapshot.status === 'connecting') {
            await requestEndVoipCall(API_BASE, token, localPending.call_id, 'stale_pending_connecting');
            stopIncomingVoipAlert(`${source}:${reason}`);
            setPendingIncomingVoipCall(null);
            logUiPressProbe('VOIP_PENDING_CALL_CLEARED_STALE_CONNECTING', {
                source,
                reason,
                call_id: localPending.call_id,
                status: snapshot.status ?? null,
                caller_voice_id: localPending.caller_voice_id ?? null,
            });
            return true;
        }

        dismissPendingIncomingAsMissed(source, reason, localPending);
        return true;
    }, [API_BASE, dismissPendingIncomingAsMissed, logUiPressProbe, stopIncomingVoipAlert, token]);

    const fetchPendingIncomingVoipCall = useCallback(async (source: string) => {
        if (!token || !userInfo) {
            return;
        }
        if (pendingIncomingPollInFlightRef.current) {
            return;
        }
        if (voipCallInitResponseRef.current?.call_id) {
            return;
        }

        pendingIncomingPollInFlightRef.current = true;
        try {
            const tokenSummary = summarizeAuthToken(token);
            console.log('[VoIPPendingIncoming]', JSON.stringify({
                event: 'REQUEST_START',
                source,
                token_summary: tokenSummary,
                user_id: userInfo.id,
                has_pending_call: Boolean(pendingIncomingVoipCallRef.current?.call_id),
                has_active_call: Boolean(voipCallInitResponseRef.current?.call_id),
            }));
            const response = await fetch(`${API_BASE}/api/v1/voip/calls/pending-incoming`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            console.log('[VoIPPendingIncoming]', JSON.stringify({
                event: 'REQUEST_RESULT',
                source,
                token_summary: tokenSummary,
                user_id: userInfo.id,
                status: response.status,
                ok: response.ok,
            }));
            if (!response.ok) {
                if (response.status !== 404) {
                    console.log('[VoIPPendingIncoming] fetch failed', response.status);
                }
                if (response.status === 401) {
                    // 다른 단말/웹에서 로그인 → 이 세션 만료. 한 번만 로그아웃 처리.
                    const superseded = response.headers.get('X-Session-Superseded') === '1';
                    if (superseded && !sessionSupersededHandledRef.current) {
                        sessionSupersededHandledRef.current = true;
                        console.log('[VoIPPendingIncoming] session superseded → logout');
                        try {
                            Alert.alert('다른 기기에서 로그인됨', '다른 기기에서 로그인되어 이 기기는 로그아웃됩니다.');
                        } catch {
                            // no-op
                        }
                        handleLogoutRef.current?.();
                    }
                    return;
                }
                if (response.status === 404 && pendingIncomingVoipCallRef.current?.call_id) {
                    await resolveStalePendingIncomingCall(source, 'pending_call_missing');
                }
                return;
            }

            const payload = await response.json() as (CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null;
            if (!payload?.call_id || !payload.signaling_server) {
                if (pendingIncomingVoipCallRef.current?.call_id) {
                    await resolveStalePendingIncomingCall(source, 'empty_pending_payload');
                } else if (incomingVoipAlertActiveRef.current) {
                    // 워치독: 백엔드에 대기 통화가 없고(=빈 페이로드) 활성 통화도 없는데(상단 early-return 보장)
                    // 착신 벨/톤이 아직 살아있으면 고아 링(orphan ring)이다. 강제 정지한다.
                    stopIncomingVoipAlert('watchdog_no_pending_no_active');
                }
                return;
            }

            if (isTerminalVoipStatus(payload.status)) {
                dismissPendingIncomingAsMissed(source, 'terminal_pending_status', payload);
                return;
            }

            if (payload.call_id === acceptedIncomingVoipCallIdRef.current) {
                logUiPressProbe('VOIP_PENDING_CALL_SUPPRESSED_AFTER_ACCEPT', {
                    source,
                    call_id: payload.call_id,
                    caller_voice_id: payload.caller_voice_id ?? null,
                });
                setTimeout(() => {
                    logUiPressProbe('VOIP_PENDING_CALL_CLEARED', {
                        source,
                        reason: 'accepted_call_already_active',
                        call_id: payload.call_id,
                        caller_voice_id: payload.caller_voice_id ?? null,
                    });
                }, 0);
                setPendingIncomingVoipCall(null);
                return;
            }

            logUiPressProbe('VOIP_PENDING_CALL_FETCHED', {
                source,
                call_id: payload.call_id,
                status: payload.status ?? null,
                caller_voice_id: payload.caller_voice_id ?? null,
            });

            const storedSession = await loadStoredActiveVoipSession();
            if (storedSession?.callId === payload.call_id) {
                if (payload.participant_role === 'callee' && isRuntimeAcceptedCalleeVoipSession(
                    storedSession,
                    payload.call_id,
                    acceptedIncomingVoipCallIdRef.current,
                )) {
                    logUiPressProbe('VOIP_PENDING_CALL_RESTORE_SKIPPED_ACCEPTED_SESSION', {
                        source,
                        call_id: payload.call_id,
                        status: payload.status ?? null,
                        caller_voice_id: payload.caller_voice_id ?? null,
                    });
                    return;
                }

                if (payload.participant_role === 'callee' && !isRuntimeAcceptedCalleeVoipSession(
                    storedSession,
                    payload.call_id,
                    acceptedIncomingVoipCallIdRef.current,
                )) {
                    await clearStoredActiveVoipSession();
                    logUiPressProbe('VOIP_PENDING_CALL_RESTORE_DEFERRED_TO_ACCEPT', {
                        source,
                        call_id: payload.call_id,
                        caller_voice_id: payload.caller_voice_id ?? null,
                    });
                    applyIncomingVoipPayload(payload, source);
                    return;
                }

                const restoredRailSection = storedSession.railSection ?? 'voip';
                const fallbackCallMode = resolveCallModeFromPayload(payload);
                const restoredPayload: CallInitResponse = {
                    call_id: payload.call_id,
                    signaling_server: payload.signaling_server,
                    turn_servers: normalizeTurnServers(payload.turn_servers),
                    call_route: payload.call_route || 'app_webrtc',
                    phone_dialer_required: payload.phone_dialer_required,
                    fallback_dial_url: payload.fallback_dial_url,
                    user_message: payload.user_message,
                    callee_app_online: payload.callee_app_online,
                    caller_voice_id: payload.caller_voice_id,
                    callee_voice_id: payload.callee_voice_id,
                    callee_user_id: payload.callee_user_id,
                    participant_role: payload.participant_role === 'callee' ? 'callee' : 'caller',
                    display_label: payload.display_label,
                    display_language: payload.display_language,
                    display_country_code: payload.display_country_code,
                    status: 'connecting',
                    requested_mode: normalizeCallModeCandidate(payload.requested_mode) ?? fallbackCallMode,
                    resolved_mode: normalizeCallModeCandidate(payload.resolved_mode) ?? normalizeCallModeCandidate(payload.requested_mode) ?? fallbackCallMode,
                    auto_relay_requested: payload.auto_relay_requested ?? false,
                    auto_relay_applied: payload.auto_relay_applied ?? false,
                    error_code: payload.error_code,
                };

                logUiPressProbe('VOIP_PENDING_CALL_RESTORED_FROM_ACCEPTED_SESSION', {
                    source,
                    call_id: payload.call_id,
                    restored_rail_section: restoredRailSection,
                    caller_voice_id: payload.caller_voice_id ?? null,
                });
                setCallMode(restoredPayload.resolved_mode === 'voip_full_auto' ? 'voip_full_auto' : 'pstn_assist');
                setVoipActiveProfile(buildVoipRemoteProfile(
                    payload.caller_label || restoredPayload.display_label || payload.caller_voice_id || '수신 보이스톡',
                    payload.caller_voice_id || restoredPayload.display_label,
                    restoredPayload.display_country_code,
                    restoredPayload.display_language,
                ));
                setVoipPhone(payload.caller_label || restoredPayload.display_label || payload.caller_voice_id || '수신 통화');
                setVoipInitError('');
                setVoipInitLoading(false);
                setVoipAuditCallId(restoredPayload.call_id);
                setVoipAuditEvents([]);
                setVoipAuditError('');
                setShowFriendFolder(false);
                setPendingIncomingVoipCall(null);
                setVoipCallInitResponse(restoredPayload);
                setShowVoipTester(true);
                setActiveRailSection(restoredRailSection);
                return;
            }

            applyIncomingVoipPayload(payload, source);
        } catch (error) {
            console.log('[VoIPPendingIncoming] fetch failed', error);
        } finally {
            pendingIncomingPollInFlightRef.current = false;
        }
    }, [API_BASE, applyIncomingVoipPayload, buildVoipRemoteProfile, dismissPendingIncomingAsMissed, logUiPressProbe, resolveStalePendingIncomingCall, token, userInfo, voipCallInitResponse]);

    const refreshVoipAudit = useCallback(async (callId: string, options?: { showLoading?: boolean; force?: boolean }) => {
        const showLoading = options?.showLoading ?? true;
        const force = options?.force ?? false;
        if (!token) {
            setVoipAuditEvents([]);
            setVoipAuditError('');
            return [] as CallModeAuditEvent[];
        }
        if (voipAuditFetchInFlightRef.current && !force) {
            return [] as CallModeAuditEvent[];
        }

        voipAuditFetchInFlightRef.current = true;
        if (showLoading) {
            setVoipAuditLoading(true);
        }
        setVoipAuditError('');
        try {
            const response = await fetch(`${API_BASE}/api/v1/voip/calls/${callId}/audit`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const payload = await response.json();
            const events = Array.isArray(payload) ? (payload as CallModeAuditEvent[]) : [];
            setVoipAuditEvents(events);
            return events;
        } catch (error: any) {
            const message = error?.message || 'VoIP 감사 로그 조회 실패';
            setVoipAuditError(message);
            return [] as CallModeAuditEvent[];
        } finally {
            voipAuditFetchInFlightRef.current = false;
            if (showLoading) {
                setVoipAuditLoading(false);
            }
        }
    }, [token]);

    const resolveActiveRegionHint = useCallback((source: LangCode) => {
        return resolveRegionHintForSourceLanguage(source, gpsCountryCode, gpsRegionHint);
    }, [gpsCountryCode, gpsRegionHint]);

    const translateTextWithRegion = useCallback((
        text: string,
        source: LangCode,
        target: LangCode,
        timeoutMs = 8000,
        options: TranslateOptions = {},
    ) => {
        return translateText(text, source, target, timeoutMs, {
            ...options,
            regionHint: options.regionHint ?? resolveActiveRegionHint(source),
        });
    }, [resolveActiveRegionHint]);

    const runTranslation = useCallback(async (text: string, source: LangCode, target: LangCode) => {
        const requestId = ++translationRequestSeqRef.current;
        setLoading(true);
        setResultText('');
        try {
            const translatePromise = translateTextWithRegion(text, source, target);
            const timeoutPromise = new Promise<never>((_, reject) => {
                setTimeout(() => reject(new Error('translation_timeout')), TRANSLATION_REQUEST_TIMEOUT_MS);
            });
            const result = await Promise.race([translatePromise, timeoutPromise]);
            if (requestId !== translationRequestSeqRef.current) {
                return;
            }
            setResultText(result.translated);
            setOffline(result.offline);
            setEngine(result.engine);
            latestTranslationMetaRef.current = {
                source,
                target,
                translated: result.translated,
            };
            setTranslationEpoch((prev) => prev + 1);
        } catch (error) {
            if (requestId !== translationRequestSeqRef.current) {
                return;
            }
            const ui = getUiText(source);
            const timedOut = error instanceof Error && error.message === 'translation_timeout';
            setResultText(timedOut ? '[오류] 번역 응답 시간이 초과되었습니다.' : ui.errorMsg);
            latestTranslationMetaRef.current = null;
            setTranslationEpoch((prev) => prev + 1);
        } finally {
            if (requestId === translationRequestSeqRef.current) {
                setLoading(false);
            }
        }
    }, [translateTextWithRegion]);

    // [설정 SSOT] 앱 시작 시 전역 설정을 1회 로드 → 각 화면이 getGlobalSettings()로 기본값을 읽는다.
    useEffect(() => {
        loadGlobalSettings().catch(() => { /* 기본값 사용 */ });
    }, []);

    // 앱 시작 시 + 포그라운드 복귀 시 버전 체크.
    // (마켓에 새 빌드를 올린 뒤 앱을 다시 켜지 않아도, 앱으로 돌아오면 스스로 감지해 업그레이드를 띄운다.)
    useEffect(() => {
        checkForAppUpdate().catch((err) => console.error('앱 버전 체크 오류:', err));
        let lastCheckedAt = Date.now();
        const sub = AppState.addEventListener('change', (state) => {
            if (state !== 'active') {
                return;
            }
            // 과도한 호출 방지: 포그라운드 복귀가 잦아도 30초 내 재확인은 생략.
            if (Date.now() - lastCheckedAt < 30_000) {
                return;
            }
            lastCheckedAt = Date.now();
            checkForAppUpdate().catch((err) => console.error('앱 버전 체크 오류(foreground):', err));
        });
        return () => sub.remove();
    }, []);

    useEffect(() => {
        void hydrateWorldlincoTuningFromStorage()
            .then(() => refreshWorldlincoTuning(API_BASE))
            .catch((err) => console.error('[WORLDLINGCO_TUNING] bootstrap failed', err));
        const sub = AppState.addEventListener('change', (state) => {
            if (state === 'active') {
                void refreshWorldlincoTuning(API_BASE);
            }
        });
        return () => sub.remove();
    }, []);

    useEffect(() => {
        let cancelled = false;

        (async () => {
            try {
                const storedAuth = await loadStoredAuthState();
                if (!cancelled && storedAuth) {
                    console.log('[AUTH_FLOW]', JSON.stringify({
                        event: 'AUTH_STORAGE_RESTORE_FOUND',
                        user_id: storedAuth.userInfo.id,
                        user_email: storedAuth.userInfo.email,
                    }));
                    try {
                        const me = await callMeApi(storedAuth.token);
                        if (!cancelled) {
                            console.log('[AUTH_FLOW]', JSON.stringify({
                                event: 'AUTH_STORAGE_RESTORE_APPLIED',
                                user_id: me.id,
                                user_email: me.email,
                            }));
                            applyAuthenticatedSession(storedAuth.token, me);
                        }
                    } catch (error) {
                        console.log('[AuthStorage] restore invalid, clearing stored auth', error);
                        await clearStoredAuthState();
                    }
                }
            } finally {
                if (!cancelled) {
                    setAuthHydrated(true);
                }
            }
        })().catch(() => {
            if (!cancelled) {
                setAuthHydrated(true);
            }
        });

        return () => {
            cancelled = true;
        };
    }, [applyAuthenticatedSession]);

    useEffect(() => {
        if (!authHydrated) {
            return;
        }

        if (token && userInfo) {
            saveStoredAuthState(token, userInfo).catch((error) => {
                console.log('[AuthStorage] save failed', error);
            });
            return;
        }

        clearStoredAuthState().catch((error) => {
            console.log('[AuthStorage] clear failed', error);
        });
    }, [authHydrated, token, userInfo]);

    useEffect(() => {
        void (async () => {
            setBiometricLoginReady(await isBiometricAvailable());
            setBiometricLoginEnabledState(await isBiometricLoginEnabled());
        })();
    }, [authHydrated, userInfo?.id]);

    // 착신/채팅 알림 채널은 **로그인 여부와 무관**하게 앱 시작 시 무조건 생성한다.
    // (미로그인 상태에서 푸시가 도착해도 high-importance 채널이 있어야 벨/전체화면 알림이 정상 동작.)
    useEffect(() => {
        if (Platform.OS !== 'android') {
            return;
        }
        void (async () => {
            try {
                await ensureVoipIncomingNotificationChannel();
                await ensureChatMessageNotificationChannel();
            } catch (error) {
                console.log('[VoIPFCM] startup notification channel failed', error);
            }
        })();
    }, []);

    useEffect(() => {
        if (!authHydrated) {
            return;
        }

        let cancelled = false;

        const syncVoipTopic = async () => {
            const nextTopic = userInfo ? buildVoipTopic(buildVoiceId(userInfo.id)) : null;
            const previousTopic = voipTopicRef.current;

            if (previousTopic && previousTopic !== nextTopic) {
                try {
                    await messaging().unsubscribeFromTopic(previousTopic);
                } catch (error) {
                    console.log('[VoIPFCM] unsubscribe failed', error);
                }
                if (!cancelled) {
                    voipTopicRef.current = null;
                }
            }

            if (!nextTopic) {
                return;
            }

            if (Platform.OS === 'android') {
                const firebaseReady = await ensureFirebaseDefaultApp();
                if (!firebaseReady) {
                    return;
                }
            }

            try {
                await messaging().registerDeviceForRemoteMessages();
            } catch (error) {
                console.log('[VoIPFCM] register device failed', error);
            }

            try {
                await ensureVoipIncomingNotificationChannel();
                await ensureChatMessageNotificationChannel();
            } catch (error) {
                console.log('[VoIPFCM] notification channel failed', error);
            }

            try {
                await messaging().subscribeToTopic(nextTopic);
                const pushToken = await messaging().getToken().catch(() => '');
                if (pushToken && token) {
                    await registerVoipDevice(API_BASE, token, pushToken);
                }
                if (!cancelled) {
                    voipTopicRef.current = nextTopic;
                    logUiPressProbe('VOIP_FCM_TOPIC_READY', {
                        topic: nextTopic,
                        push_token_present: Boolean(pushToken),
                    });
                }
            } catch (error) {
                console.log('[VoIPFCM] subscribe failed', error);
            }
        };

        void syncVoipTopic();

        return () => {
            cancelled = true;
        };
    }, [authHydrated, logUiPressProbe, token, userInfo]);

    // 부재중 전화 음성 안내: 로그인 상태에서 앱이 활성화될 때 최근 부재중 통화를 조회해
    // 아직 안내하지 않은 신규 건만 음성으로 알린다. 안내한 id는 AsyncStorage에 저장해 중복 안내를 막는다.
    useEffect(() => {
        if (!authHydrated || !token || !userInfo) {
            return;
        }
        let cancelled = false;
        const ANNOUNCED_KEY = 'worldlinco_announced_missed_calls_v1';

        const announceMissedCalls = async () => {
            try {
                const missed = await fetchRecentMissedCalls(API_BASE, token);
                console.log('[MISSED_CALL]', JSON.stringify({ event: 'fetch', count: missed.length }));
                if (cancelled || missed.length === 0) {
                    return;
                }
                let announcedIds: number[] = [];
                try {
                    const raw = await AsyncStorage.getItem(ANNOUNCED_KEY);
                    if (raw) {
                        const parsed = JSON.parse(raw);
                        if (Array.isArray(parsed)) {
                            announcedIds = parsed
                                .map((v: unknown) => Number(v))
                                .filter((v) => Number.isFinite(v));
                        }
                    }
                } catch {
                    // no-op
                }
                const announcedSet = new Set(announcedIds);
                const nowMs = Date.now();
                // 아직 안내 안 했고 최근 24시간 이내인 건만 안내(오래된 부재중 누적 스팸 방지).
                const fresh = missed.filter((m) => {
                    if (announcedSet.has(m.id)) {
                        return false;
                    }
                    const t = Date.parse(m.createdAt);
                    return !Number.isFinite(t) || (nowMs - t) < 24 * 60 * 60 * 1000;
                });
                // 조회된 모든 id를 안내완료로 기록(다음 활성화 때 재안내 방지). 최근 200건만 유지.
                const nextAnnounced = Array.from(
                    new Set([...announcedIds, ...missed.map((m) => m.id)]),
                ).slice(-200);
                await AsyncStorage.setItem(ANNOUNCED_KEY, JSON.stringify(nextAnnounced));
                if (cancelled || fresh.length === 0) {
                    return;
                }
                const latest = fresh[0];
                // 수신자 지정 언어(preferred_language)로 안내. 서버 뉴럴 TTS(폴백 단말 TTS).
                const prefLang = String(userInfo?.preferred_language || 'ko').trim().toLowerCase() || 'ko';
                const announceText = await buildAnnouncement(
                    fresh.length === 1 ? 'missedCall' : 'missedCallMulti',
                    prefLang,
                    latest.callerLabel,
                );
                console.log('[MISSED_CALL]', JSON.stringify({ event: 'announce', fresh: fresh.length, lang: prefLang }));
                await announceServerVoice(announceText, prefLang);
            } catch (err) {
                console.warn('[VoIP] 부재중 전화 안내 실패', err);
            }
        };

        void announceMissedCalls();
        const subscription = AppState.addEventListener('change', (nextState) => {
            if (nextState === 'active') {
                void announceMissedCalls();
            }
        });
        return () => {
            cancelled = true;
            subscription.remove();
        };
    }, [authHydrated, token, userInfo]);

    useEffect(() => {
        if (!authHydrated || !token || !userInfo) {
            return;
        }
        void (async () => {
            const enabled = await areVoipNotificationsEnabled();
            logUiPressProbe('VOIP_NOTIFICATION_PERMISSION_STATUS', {
                notifications_enabled: enabled,
            });
            if (!enabled) {
                logUiPressProbe('VOIP_NOTIFICATION_PERMISSION_DISABLED', {
                    action: 'open_settings_recommended',
                });
                if (!notificationDisabledPromptShownRef.current) {
                    notificationDisabledPromptShownRef.current = true;
                    Alert.alert(
                        '알림이 꺼져 있습니다',
                        '보이스톡·채팅 알림을 받으려면 설정에서 "알림 표시"를 켜 주세요.',
                        [
                            { text: '나중에', style: 'cancel' },
                            {
                                text: '설정 열기',
                                onPress: () => {
                                    void openVoipNotificationSettings();
                                },
                            },
                        ],
                    );
                }
            }
        })();
    }, [authHydrated, logUiPressProbe, token, userInfo]);

    useEffect(() => {
        return () => {
            songFileSoundRef.current?.unloadAsync().catch(() => { /* no-op */ });
            songFileSoundRef.current = null;
            voicePreviewSoundRef.current?.unloadAsync().catch(() => { /* no-op */ });
            voicePreviewSoundRef.current = null;
            voiceProfileRecordingRef.current?.stopAndUnloadAsync().catch(() => { /* no-op */ });
            voiceProfileRecordingRef.current = null;
        };
    }, []);

    useEffect(() => {
        const pendingCallId = pendingIncomingVoipCall?.call_id;
        const pendingStatus = pendingIncomingVoipCall?.status;
        if (!pendingCallId || voipCallInitResponse?.call_id || !isIncomingRingVoipStatus(pendingStatus)) {
            stopIncomingVoipAlert('no_pending_or_active_call');
            return;
        }

        startIncomingVoipAlert(
            pendingCallId,
            pendingIncomingVoipCall.caller_voice_id ?? null,
            pendingIncomingVoipCall.caller_label ?? null,
        );
    }, [
        pendingIncomingVoipCall?.call_id,
        pendingIncomingVoipCall?.caller_label,
        pendingIncomingVoipCall?.caller_voice_id,
        pendingIncomingVoipCall?.status,
        startIncomingVoipAlert,
        stopIncomingVoipAlert,
        voipCallInitResponse?.call_id,
    ]);

    useEffect(() => {
        if (!pendingIncomingVoipCall?.call_id || voipCallInitResponse?.call_id) {
            return;
        }

        if (acceptingIncomingVoipCallId === pendingIncomingVoipCall.call_id) {
            logUiPressProbe('VOIP_PENDING_CALL_RING_TIMEOUT_PAUSED_ACCEPTING', {
                call_id: pendingIncomingVoipCall.call_id,
                caller_voice_id: pendingIncomingVoipCall.caller_voice_id ?? null,
            });
            return;
        }

        const ringTimer = setTimeout(() => {
            if (acceptingIncomingVoipCallIdRef.current === pendingIncomingVoipCall.call_id) {
                logUiPressProbe('VOIP_PENDING_CALL_RING_TIMEOUT_ABORTED_ACCEPTING', {
                    call_id: pendingIncomingVoipCall.call_id,
                    caller_voice_id: pendingIncomingVoipCall.caller_voice_id ?? null,
                });
                return;
            }
            void resolveStalePendingIncomingCall('incoming_ring_timeout', 'local_ring_timeout');
        }, PENDING_INCOMING_RING_MAX_MS);

        return () => clearTimeout(ringTimer);
    }, [acceptingIncomingVoipCallId, logUiPressProbe, pendingIncomingVoipCall?.call_id, pendingIncomingVoipCall?.caller_voice_id, resolveStalePendingIncomingCall, voipCallInitResponse?.call_id]);

    useEffect(() => {
        return () => {
            stopIncomingVoipAlert('app_unmount');
        };
    }, [stopIncomingVoipAlert]);

    useEffect(() => {
        if (!token || !userInfo) {
            return;
        }
        if (voipCallInitResponse) {
            return;
        }

        void fetchPendingIncomingVoipCall('pending_call_initial');
        const pollTimer = setInterval(() => {
            void fetchPendingIncomingVoipCall('pending_call_poll');
        }, pendingIncomingVoipCallRef.current?.call_id ? 800 : 2500);
        const appStateSubscription = AppState.addEventListener('change', (nextState) => {
            if (nextState === 'active') {
                void fetchPendingIncomingVoipCall('pending_call_active');
            } else if (nextState === 'background' || nextState === 'inactive') {
                void fetchPendingIncomingVoipCall('pending_call_background');
            }
        });

        return () => {
            clearInterval(pollTimer);
            appStateSubscription.remove();
        };
    }, [fetchPendingIncomingVoipCall, token, userInfo, voipCallInitResponse]);

    // ===== AUTO TRANSLATE: inputText → Auto Translation After Delay =====
    const autoTranslateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const lastAutoTranslateRef = useRef<{ text: string; fromLang: LangCode; toLang: LangCode; translatedAt: number } | null>(null);

    useEffect(() => {
        // Cancel pending timer
        if (autoTranslateTimerRef.current) {
            clearTimeout(autoTranslateTimerRef.current);
            autoTranslateTimerRef.current = null;
        }

        // Skip if no input text
        const trimmed = inputText.trim();
        if (!trimmed) {
            return;
        }

        // Prevent duplicate auto translations (same text + same language pair within 5 seconds)
        const textNorm = normalizeRelayText(trimmed);
        if (lastAutoTranslateRef.current) {
            const sameText = normalizeRelayText(lastAutoTranslateRef.current.text) === textNorm;
            const sameLangPair = lastAutoTranslateRef.current.fromLang === fromLang && lastAutoTranslateRef.current.toLang === toLang;
            const recentTranslation = Date.now() - lastAutoTranslateRef.current.translatedAt < 5000;
            if (sameText && sameLangPair && recentTranslation) {
                return;
            }
        }

        // Schedule auto translation after delay
        autoTranslateTimerRef.current = setTimeout(async () => {
            try {
                lastAutoTranslateRef.current = {
                    text: trimmed,
                    fromLang,
                    toLang,
                    translatedAt: Date.now(),
                };

                // Trigger auto translation
                await runTranslation(trimmed, fromLang, toLang);
            } catch {
                // Silent fail: don't disrupt user experience
            }
        }, autoRelayDelayMs);

        return () => {
            if (autoTranslateTimerRef.current) {
                clearTimeout(autoTranslateTimerRef.current);
                autoTranslateTimerRef.current = null;
            }
        };
    }, [inputText, fromLang, toLang, autoRelayDelayMs, runTranslation]);

    // ===== AUTO VOICE OUTPUT: resultText → Voice Preview or TTS =====
    const autoVoiceTranslationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const lastAutoVoiceTranslateRef = useRef<{ text: string; translatedAt: number; lang: string } | null>(null);

    useEffect(() => {
        // Cancel pending timer
        if (autoVoiceTranslationTimerRef.current) {
            clearTimeout(autoVoiceTranslationTimerRef.current);
            autoVoiceTranslationTimerRef.current = null;
        }

        // Skip if no result text
        if (!resultText.trim()) {
            return;
        }

        // Speak only when the result belongs to the latest translation for current target language.
        const latestMeta = latestTranslationMetaRef.current;
        const resultNorm = normalizeRelayText(resultText);
        const latestNorm = normalizeRelayText(latestMeta?.translated ?? '');
        if (!latestMeta || latestMeta.target !== toLang || latestNorm !== resultNorm) {
            return;
        }

        // Prevent duplicate auto translations (same text + same language within 5 seconds)
        const textNorm = resultNorm;
        if (lastAutoVoiceTranslateRef.current) {
            const sameText = normalizeRelayText(lastAutoVoiceTranslateRef.current.text) === textNorm;
            const sameLang = lastAutoVoiceTranslateRef.current.lang === toLang;
            const recentTranslation = Date.now() - lastAutoVoiceTranslateRef.current.translatedAt < 5000;
            if (sameText && sameLang && recentTranslation) {
                return;
            }
        }

        // Schedule auto voice translation after delay
        autoVoiceTranslationTimerRef.current = setTimeout(async () => {
            try {
                lastAutoVoiceTranslateRef.current = {
                    text: resultText,
                    translatedAt: Date.now(),
                    lang: toLang,
                };

                const canUseVoicePreview = !!voiceProfile && !!songFileJob && songFileJob.status === 'completed';

                if (canUseVoicePreview && songFileJob && voiceProfile) {
                    // Song translation mode: generate policy-aware voice preview audio.
                    const preview = await callCreateVoicePreview({
                        jobId: songFileJob.job_id,
                        voiceProfileId: voiceProfile.voice_profile_id,
                        licenseMode: voiceLicenseMode,
                        outputScope: voiceOutputScope,
                        rightsAcknowledged: voiceRightsAcknowledged,
                    });

                    if (preview && preview.preview_audio_available && preview.preview_audio_base64) {
                        try {
                            await voicePreviewSoundRef.current?.unloadAsync().catch(() => { /* no-op */ });
                            voicePreviewSoundRef.current = null;

                            const normalizedFormat = (preview.preview_audio_format ?? '').toLowerCase();
                            const extension = normalizedFormat.includes('mpeg') || normalizedFormat.includes('mp3') ? 'mp3' : 'wav';
                            const baseDir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory;

                            if (baseDir) {
                                const fileUri = `${baseDir}voice-preview-auto-${preview.preview_id}.${extension}`;
                                await FileSystem.writeAsStringAsync(fileUri, preview.preview_audio_base64, {
                                    encoding: FileSystem.EncodingType.Base64,
                                });
                                const { sound } = await Audio.Sound.createAsync(
                                    { uri: fileUri },
                                    { shouldPlay: true }
                                );
                                voicePreviewSoundRef.current = sound;
                            }
                        } catch {
                            // Silent fallback: skip preview playback on error.
                        }
                    }
                } else {
                    // 대면 자동음성(bilingual) 모드에서는 playFaceTranslationOutput가 서버 뉴럴 TTS로
                    // 발화를 전담한다. 이 일반 자동발화(디바이스 Expo TTS)가 함께 돌면 같은 문장을
                    // 두 번 발화(1차 디바이스 + 2차 서버 오디오)하므로 대면 모드에서는 건너뛴다.
                    // 수동 번역(autoVoiceMode=false)·노래 미리듣기(voice preview 분기)는 영향 없음.
                    if (autoVoiceModeEnabledRef.current) {
                        return;
                    }
                    // Default mode: speak translated text directly via Expo TTS.
                    const speakText = normalizeSpeakText(resultText);
                    if (speakText) {
                        const lang = LANGS.find((item) => item.code === toLang);
                        const fallbackTts = lang?.tts ?? 'ko-KR';
                        const detectedTts = inferTtsLanguage(speakText, fallbackTts);

                        // Cancel previous TTS before starting new one to avoid language overlap
                        try {
                            await Speech.stop();
                        } catch {
                            // no-op
                        }

                        // Log TTS invocation with language tag
                        const logTag = `[AUTO_VOICE_TTS_${Date.now()}]`;
                        console.log(logTag, { speakText, toLang, detectedTts, timestamp: new Date().toISOString() });

                        Speech.speak(speakText, { language: detectedTts, rate: 0.9 });
                    }
                }
            } catch {
                // Silent fail: don't disrupt user experience on auto voice generation failure
            }
        }, autoRelayDelayMs);

        return () => {
            if (autoVoiceTranslationTimerRef.current) {
                clearTimeout(autoVoiceTranslationTimerRef.current);
                autoVoiceTranslationTimerRef.current = null;
            }
        };
    }, [resultText, translationEpoch, autoRelayDelayMs, songFileJob, voiceProfile, voiceLicenseMode, voiceOutputScope, voiceRightsAcknowledged, toLang]);

    // ── 번역 실행 ──
    const handleTranslate = useCallback(async () => {
        const ui = getUiText(fromLang);
        const trimmed = inputText.trim();
        if (!trimmed) {
            Alert.alert(ui.inputRequired, ui.inputRequiredMsg);
            return;
        }
        await runTranslation(trimmed, fromLang, toLang);
    }, [inputText, fromLang, toLang, runTranslation]);

    const runImageOcrWithAsset = useCallback(async (asset: { uri: string; name?: string | null; mimeType?: string | null }) => {
        const ui = getUiText(fromLang);
        setOcrError('');
        setOcrTranslatedText('');
        try {
            setOcrLoading(true);
            setOcrImageName(asset.name || 'ocr-image.jpg');

            const result = await translateImage(
                asset,
                fromLang,
                toLang,
                resolveActiveRegionHint(fromLang),
            );
            const effectiveSource = isSupportedLangCode(result.from) ? result.from : fromLang;
            const effectiveTarget = isSupportedLangCode(result.to) ? result.to : toLang;
            setInputText(result.original_text);
            setResultText(result.translated);
            setOffline(result.offline);
            setEngine(result.engine);
            setOcrExtractedText(result.original_text);
            setOcrTranslatedText(result.translated);
            if (effectiveSource !== fromLang) {
                setFromLang(effectiveSource);
            }
            if (effectiveTarget !== toLang) {
                setToLang(effectiveTarget);
            }
            latestTranslationMetaRef.current = {
                source: effectiveSource,
                target: effectiveTarget,
                translated: result.translated,
            };
            setTranslationEpoch((prev) => prev + 1);

            if (Platform.OS === 'android') {
                ToastAndroid.show(`${result.file_name} OCR 번역 완료`, ToastAndroid.SHORT);
            }
        } catch (error: any) {
            setOcrTranslatedText('');
            setOcrError(error?.message || ui.ocrErrorMsg);
        } finally {
            setOcrLoading(false);
        }
    }, [fromLang, resolveActiveRegionHint, toLang]);

    const handlePickImageOcr = useCallback(async () => {
        if (ocrLoading) {
            return;
        }

        const picked = await DocumentPicker.getDocumentAsync({
            type: ['image/*'],
            copyToCacheDirectory: true,
            multiple: false,
        });
        if (picked.canceled || !picked.assets?.length) {
            return;
        }

        const asset = picked.assets[0];
        await runImageOcrWithAsset(asset);
    }, [ocrLoading, runImageOcrWithAsset]);

    useEffect(() => {
        if (!__DEV__ || !OCR_DEBUG_IMAGE_URI || ocrDebugInjectedRef.current) {
            return;
        }
        ocrDebugInjectedRef.current = true;
        const debugAsset = {
            uri: OCR_DEBUG_IMAGE_URI,
            name: OCR_DEBUG_IMAGE_NAME || OCR_DEBUG_IMAGE_URI.split('/').pop() || 'ocr-debug-image.jpg',
            mimeType: 'image/jpeg',
        };
        void runImageOcrWithAsset(debugAsset);
    }, [runImageOcrWithAsset]);

    const appendSongSubtitle = useCallback((payload: Omit<SongSubtitleEntry, 'id'>) => {
        setSongSubtitles((prev) => {
            const last = prev[prev.length - 1];
            if (last && isRepeatedLyricSegment(payload.original, last.original)) {
                return [
                    ...prev.slice(0, -1),
                    {
                        ...last,
                        translated: payload.translated,
                        repeatCount: last.repeatCount + 1,
                    },
                ];
            }
            songSubtitleSeqRef.current += 1;
            return [
                ...prev.slice(-5),
                {
                    ...payload,
                    id: `song-subtitle-${songSubtitleSeqRef.current}`,
                },
            ];
        });
    }, []);

    const resolveSongHybridSource = useCallback((rawDetectedLanguage: string, transcript: string): { lang: LangCode; detectedBy: SongSubtitleEntry['detectedBy'] } => {
        const mapped = normalizeDetectedLangCode(rawDetectedLanguage);
        if (mapped) {
            return { lang: mapped, detectedBy: 'voice' };
        }
        const inferred = inferSpeechLangCode(transcript, fromLang);
        if (inferred) {
            return { lang: inferred, detectedBy: 'script' };
        }
        return { lang: fromLang, detectedBy: 'manual' };
    }, [fromLang]);

    const resolveSongHybridTarget = useCallback((source: LangCode): LangCode => {
        if (toLang !== source) return toLang;
        return resolveAutoTargetLang(source, toLang);
    }, [toLang]);

    const loadSongFileSound = useCallback(async (asset: DocumentPicker.DocumentPickerAsset) => {
        await songFileSoundRef.current?.unloadAsync().catch(() => { /* no-op */ });
        songFileSoundRef.current = null;
        setSongFilePlaybackMs(0);
        setSongFilePlaying(false);
        const { sound } = await Audio.Sound.createAsync(
            { uri: asset.uri },
            { shouldPlay: false },
            (status) => {
                if (!status.isLoaded) return;
                setSongFilePlaybackMs(status.positionMillis ?? 0);
                setSongFilePlaying(Boolean(status.isPlaying));
            },
        );
        await sound.setProgressUpdateIntervalAsync(500);
        songFileSoundRef.current = sound;
    }, []);

    const handlePickSongFile = useCallback(async () => {
        if (songFileLoading) return;
        if (!token) {
            setShowLogin(true);
            setSongModeStatus('🎵 노래 번역 결제는 로그인 후 사용할 수 있습니다.');
            return;
        }
        if (!hasSongPass) {
            setActiveRailSection('song-mode');
            setPremiumStatusMessage('노래 번역은 건당 Song Translation Pass 결제가 필요합니다.');
            setSongModeStatus('🎵 노래 번역은 건당 결제 후 사용할 수 있습니다.');
            return;
        }
        try {
            const picked = await DocumentPicker.getDocumentAsync({
                type: ['audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/x-wav', 'audio/flac', 'audio/*'],
                copyToCacheDirectory: true,
                multiple: false,
            });
            if (picked.canceled || !picked.assets?.length) return;
            const asset = picked.assets[0];
            setSongModeEnabled(true);
            setSongFileLoading(true);
            setSongFileName(asset.name || '선택한 노래 파일');
            setSongFileJob(null);
            setSongFileSegments([]);
            setSongFileExportPreview('');
            setSongModeStatus('🎵 노래 파일을 업로드하고 백엔드 자막 작업을 시작합니다.');

            await loadSongFileSound(asset).catch(() => {
                setSongModeStatus('🎵 파일 업로드는 계속 진행합니다. 이 기기에서 미리 재생할 수 없는 형식일 수 있습니다.');
            });

            const fileTargetLang = resolveSongFileTargetLang(fromLang, toLang);
            const createdJob = await callCreateSongFileJob(asset, fileTargetLang);
            setSongFileJob(createdJob);
            let latestJob = createdJob;
            const pollStartedAt = Date.now();
            while (Date.now() - pollStartedAt < SONG_FILE_JOB_MAX_WAIT_MS) {
                if (latestJob.status === 'completed' || latestJob.status === 'failed') break;
                await delay(SONG_FILE_JOB_POLL_INTERVAL_MS);
                latestJob = await callSongFileJobStatus(createdJob.job_id);
                setSongFileJob(latestJob);
                setSongModeStatus(`🎵 ${latestJob.message} (${latestJob.progress}%)`);
            }

            if (latestJob.status !== 'completed') {
                throw new Error(latestJob.error_message || '3분 이상 노래 파일 자막 작업이 아직 완료되지 않았습니다. 잠시 후 다시 선택하거나 상태를 확인해 주세요.');
            }

            const timeline = await callSongFileTimeline(createdJob.job_id);
            setSongFileSegments(timeline.segments);
            const detectedSource = normalizeSongFileLang(timeline.source_language, fromLang);
            const detectedTarget = normalizeSongFileLang(timeline.target_language, toLang);
            setFromLang(detectedSource);
            setToLang(detectedTarget);
            setSongModeStatus(`🎵 파일 자막 준비: ${getLangLabelText(detectedSource)} → ${getLangLabelText(detectedTarget)} · ${timeline.segment_count}개 구간 · 품질 ${(timeline.quality_score * 100).toFixed(0)}%`);
        } catch (error) {
            const message = error instanceof Error ? error.message : '노래 파일 처리에 실패했습니다.';
            setSongModeStatus(`🎵 파일 자막 오류: ${message}`);
            Alert.alert('노래 파일 처리 오류', message);
        } finally {
            setSongFileLoading(false);
        }
    }, [fromLang, hasSongPass, loadSongFileSound, songFileLoading, toLang, token]);

    const handleToggleSongFilePlayback = useCallback(async () => {
        const sound = songFileSoundRef.current;
        if (!sound) {
            Alert.alert('재생 준비 필요', '먼저 노래 파일을 선택하세요.');
            return;
        }
        const status = await sound.getStatusAsync();
        if (!status.isLoaded) return;
        if (status.isPlaying) {
            await sound.pauseAsync();
        } else {
            await sound.playAsync();
        }
    }, []);

    const handleSongFileSegmentTextChange = useCallback((segmentId: string, translated: string) => {
        setSongFileSegments((prev) => prev.map((segment) => segment.id === segmentId ? { ...segment, translated } : segment));
    }, []);

    const handleSaveSongFileSegment = useCallback(async (segment: SongFileTimelineSegment) => {
        if (!songFileJob) return;
        try {
            const updatedSegment = await callPatchSongFileSegment(songFileJob.job_id, segment.id, segment.translated);
            setSongFileSegments((prev) => prev.map((item) => item.id === updatedSegment.id ? updatedSegment : item));
            setSongModeStatus(`🎵 ${formatSongFileTime(updatedSegment.start_ms)} 구간 번역을 저장했습니다.`);
        } catch (error) {
            const message = error instanceof Error ? error.message : '자막 편집 저장 실패';
            setSongModeStatus(`🎵 자막 편집 오류: ${message}`);
        }
    }, [songFileJob]);

    const handleExportSongFileTimeline = useCallback(async (format: 'srt' | 'vtt' | 'lrc' | 'json') => {
        if (!songFileJob) return;
        try {
            const exported = await callExportSongFileTimeline(songFileJob.job_id, format);
            setSongFileExportPreview(exported.slice(0, 900));
            setSongModeStatus(`🎵 ${format.toUpperCase()} 자막 내보내기 미리보기를 생성했습니다.`);
        } catch (error) {
            const message = error instanceof Error ? error.message : '자막 내보내기 실패';
            setSongModeStatus(`🎵 자막 내보내기 오류: ${message}`);
        }
    }, [songFileJob]);

    const ensureVoiceConsent = useCallback(async (): Promise<VoiceConsentResponse> => {
        if (voiceConsent?.status === 'active') return voiceConsent;
        const createdConsent = await callCreateVoiceConsent();
        setVoiceConsent(createdConsent);
        return createdConsent;
    }, [voiceConsent]);

    const handlePickVoiceSample = useCallback(async () => {
        if (voiceProfileLoading) return;
        setVoiceProfileLoading(true);
        setVoiceProfileStatus('내 목소리 사용 동의를 확인하고 샘플 파일을 준비합니다.');
        try {
            const consent = await ensureVoiceConsent();
            const picked = await DocumentPicker.getDocumentAsync({
                type: ['audio/mpeg', 'audio/mp4', 'audio/m4a', 'audio/wav', 'audio/x-wav', 'audio/webm', 'audio/*'],
                copyToCacheDirectory: true,
                multiple: false,
            });
            if (picked.canceled || !picked.assets?.length) {
                setVoiceProfileStatus('샘플 선택이 취소되었습니다.');
                return;
            }
            const createdProfile = await callCreateVoiceProfile(picked.assets[0], consent.consent_id);
            setVoiceProfile(createdProfile);
            setVoicePreview(null);
            setVoiceProfileStatus(`목소리 프로필 준비됨 · 품질 ${(createdProfile.sample_quality_score * 100).toFixed(0)}% · 암호화 저장`);
        } catch (error) {
            const message = error instanceof Error ? error.message : '목소리 샘플 업로드 실패';
            setVoiceProfileStatus(message);
            Alert.alert('목소리 샘플 오류', message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [ensureVoiceConsent, voiceProfileLoading]);

    const handleToggleVoiceSampleRecording = useCallback(async () => {
        if (voiceProfileLoading) return;
        if (isVoiceRecording) {
            Alert.alert('녹음 대기', '현재 번역 마이크 녹음을 먼저 종료해 주세요.');
            return;
        }
        if (!voiceProfileRecording) {
            try {
                const { granted } = await Audio.requestPermissionsAsync();
                if (!granted) {
                    Alert.alert('마이크 권한 필요', '목소리 샘플 녹음을 위해 마이크 권한이 필요합니다.');
                    return;
                }
                await Audio.setAudioModeAsync({
                    allowsRecordingIOS: true,
                    playsInSilentModeIOS: true,
                    staysActiveInBackground: false,
                    shouldDuckAndroid: false,
                    playThroughEarpieceAndroid: false,
                });
                const { recording } = await Audio.Recording.createAsync({
                    android: {
                        extension: '.m4a',
                        outputFormat: 2,
                        audioEncoder: 3,
                        sampleRate: 16000,
                        numberOfChannels: 1,
                        bitRate: 64000,
                    },
                    ios: {
                        extension: '.wav',
                        audioQuality: 127,
                        sampleRate: 16000,
                        numberOfChannels: 1,
                        bitRate: 128000,
                        linearPCMBitDepth: 16,
                        linearPCMIsBigEndian: false,
                        linearPCMIsFloat: false,
                    },
                    web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
                    isMeteringEnabled: false,
                    keepAudioActiveHint: false,
                });
                voiceProfileRecordingRef.current = recording;
                setVoiceProfileRecording(true);
                setVoiceProfileStatus('목소리 샘플 녹음 중입니다. 20초 이상 또렷하게 읽어 주세요.');
            } catch {
                setVoiceProfileStatus('목소리 샘플 녹음을 시작할 수 없습니다.');
            }
            return;
        }

        const recording = voiceProfileRecordingRef.current;
        if (!recording) return;
        voiceProfileRecordingRef.current = null;
        setVoiceProfileRecording(false);
        setVoiceProfileLoading(true);
        try {
            await recording.stopAndUnloadAsync();
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: false,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: true,
                playThroughEarpieceAndroid: false,
            });
            const uri = recording.getURI();
            if (!uri) throw new Error('녹음 파일을 찾을 수 없습니다.');
            const consent = await ensureVoiceConsent();
            const createdProfile = await callCreateVoiceProfile({
                uri,
                name: Platform.OS === 'ios' ? 'voice-sample.wav' : 'voice-sample.m4a',
                mimeType: Platform.OS === 'ios' ? 'audio/wav' : 'audio/m4a',
            } as DocumentPicker.DocumentPickerAsset, consent.consent_id);
            setVoiceProfile(createdProfile);
            setVoicePreview(null);
            setVoiceProfileStatus(`녹음 샘플 프로필 준비됨 · 품질 ${(createdProfile.sample_quality_score * 100).toFixed(0)}%`);
            FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
        } catch (error) {
            const message = error instanceof Error ? error.message : '목소리 녹음 업로드 실패';
            setVoiceProfileStatus(message);
            Alert.alert('목소리 녹음 오류', message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [ensureVoiceConsent, isVoiceRecording, voiceProfileLoading, voiceProfileRecording]);

    const handleDeleteVoiceProfile = useCallback(async () => {
        if (!voiceProfile) return;
        setVoiceProfileLoading(true);
        try {
            await callDeleteVoiceProfile(voiceProfile.voice_profile_id);
            setVoiceProfile(null);
            setVoicePreview(null);
            setVoiceProfileStatus('목소리 프로필과 서버 샘플이 삭제되었습니다.');
        } catch (error) {
            const message = error instanceof Error ? error.message : '목소리 프로필 삭제 실패';
            setVoiceProfileStatus(message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [voiceProfile]);

    const handleCreateVoicePreview = useCallback(async () => {
        if (!songFileJob || songFileJob.status !== 'completed') {
            Alert.alert('파일 자막 필요', '먼저 노래 파일 번역 자막을 준비하세요.');
            return;
        }
        if (!voiceProfile) {
            Alert.alert('목소리 프로필 필요', '먼저 내 목소리 샘플을 녹음하거나 업로드하세요.');
            return;
        }
        setVoiceProfileLoading(true);
        setVoiceProfileStatus('번역가사 voice preview 정책 게이트를 확인합니다.');
        try {
            const preview = await callCreateVoicePreview({
                jobId: songFileJob.job_id,
                voiceProfileId: voiceProfile.voice_profile_id,
                licenseMode: voiceLicenseMode,
                outputScope: voiceOutputScope,
                rightsAcknowledged: voiceRightsAcknowledged,
            });
            setVoicePreview(preview);
            setVoiceProfileStatus(`${preview.message} · ${preview.effective_output_scope}`);
        } catch (error) {
            const message = error instanceof Error ? error.message : '번역가사 voice preview 실패';
            setVoiceProfileStatus(message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [songFileJob, voiceLicenseMode, voiceOutputScope, voiceProfile, voiceRightsAcknowledged]);

    const handleSpeakVoicePreview = useCallback(async () => {
        if (!voicePreview?.preview_text) return;
        if (voicePreview.preview_audio_available && voicePreview.preview_audio_base64) {
            try {
                await voicePreviewSoundRef.current?.unloadAsync().catch(() => { /* no-op */ });
                voicePreviewSoundRef.current = null;
                const normalizedFormat = (voicePreview.preview_audio_format ?? '').toLowerCase();
                const extension = normalizedFormat.includes('mpeg') || normalizedFormat.includes('mp3') ? 'mp3' : 'wav';
                const baseDir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory;
                if (baseDir) {
                    const fileUri = `${baseDir}voice-preview-${voicePreview.preview_id}.${extension}`;
                    await FileSystem.writeAsStringAsync(fileUri, voicePreview.preview_audio_base64, {
                        encoding: FileSystem.EncodingType.Base64,
                    });
                    const { sound } = await Audio.Sound.createAsync({ uri: fileUri }, { shouldPlay: true });
                    voicePreviewSoundRef.current = sound;
                    return;
                }
            } catch {
                // Fallback to Expo speech when binary playback fails.
            }
        }
        const previewLine = voicePreview.preview_text.split('\n').find((line) => line.trim()) ?? voicePreview.preview_text;
        const speakText = normalizeSpeakText(previewLine.slice(0, 450));
        if (!speakText) return;
        const lang = LANGS.find((item) => item.code === toLang);
        const fallbackTts = lang?.tts ?? 'ko-KR';
        Speech.speak(speakText, { language: inferTtsLanguage(speakText, fallbackTts), rate: 0.9 });
    }, [toLang, voicePreview]);

    // ── 언어 스왑 ──
    const handleSwap = () => {
        setFromLang(toLang);
        setToLang(fromLang);
        setInputText(resultText);
        setResultText(inputText);
    };

    // ── TTS 읽기 ──
    const handleSpeak = (text: string, langCode: LangCode) => {
        const speakText = normalizeSpeakText(text);
        if (!speakText) return;
        const lang = LANGS.find((l) => l.code === langCode);
        const fallbackTts = lang?.tts ?? 'ko-KR';
        const detectedTts = inferTtsLanguage(speakText, fallbackTts);
        Speech.speak(speakText, { language: detectedTts, rate: 0.9 });
    };

    const handleLogin = useCallback(async () => {
        setAuthDebugSubmitPressed(true);
        logUiPressProbe('LOGIN_SUBMIT_PRESS', {
            email_filled: Boolean(loginEmail.trim()),
            password_filled: Boolean(loginPw.trim()),
        });
        if (!loginEmail.trim() || !loginPw.trim()) {
            setLoginError('이메일과 비밀번호를 입력하세요.');
            return;
        }
        setLoginLoading(true);
        setLoginError('');
        try {
            const tk = await callLoginApi(loginEmail.trim(), loginPw);
            const me = await callMeApi(tk);
            console.log('[AUTH_FLOW]', JSON.stringify({
                event: 'LOGIN_SESSION_APPLIED',
                user_id: me.id,
                user_email: me.email,
            }));
            applyAuthenticatedSession(tk, me);
            setDemoSessionMessage('');
            logUiPressProbe('LOGIN_SUBMIT_SUCCESS', {
                user_id: me.id,
                user_email: me.email,
            });
        } catch (e: any) {
            setLoginError(e?.message || '로그인 실패');
            logUiPressProbe('LOGIN_SUBMIT_FAIL', {
                error: e?.message || '로그인 실패',
            });
        } finally {
            setLoginLoading(false);
        }
    }, [applyAuthenticatedSession, logUiPressProbe, loginEmail, loginPw]);

    const handleSignupRequestCode = useCallback(async () => {
        const normalizedUsername = signupUsername.trim();
        const normalizedEmail = loginEmail.trim();
        const normalizedPassword = loginPw.trim();
        const normalizedCountryCode = signupCountryCode.trim().toUpperCase();
        const preferredLanguage = signupPreferredLanguage;

        logUiPressProbe('SIGNUP_REQUEST_CODE_PRESS', {
            username_filled: Boolean(normalizedUsername),
            email_filled: Boolean(normalizedEmail),
            password_filled: Boolean(normalizedPassword),
            preferred_language: preferredLanguage,
            country_code: normalizedCountryCode,
        });

        if (!normalizedUsername || !normalizedEmail || !normalizedPassword) {
            setLoginError('사용자명, 이메일, 비밀번호를 입력하세요.');
            return;
        }
        // [Phase6.0] 나의 AI 이름은 가입 필수 — 이후 "OOOO AI" 표시명으로 자동 치환된다.
        if (!isValidAiName(signupAiName)) {
            setLoginError('나의 AI 이름을 입력하세요. (예: 토토 → "토토 AI")');
            return;
        }
        if (!normalizedEmail.includes('@')) {
            setLoginError('올바른 이메일 형식을 입력하세요.');
            return;
        }
        if (normalizedPassword.length < 8) {
            setLoginError('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        const trimmedPhone = signupPhone.trim();
        if (signupVerificationChannel === 'phone') {
            if (!trimmedPhone) {
                setLoginError('전화 인증을 선택한 경우 +국가번호 형식 연락처를 입력하세요.');
                return;
            }
            if (!trimmedPhone.startsWith('+')) {
                setLoginError('전화번호는 +82-10-1234-5678 형식으로 입력하세요.');
                return;
            }
        }

        setLoginLoading(true);
        setLoginError('');
        try {
            const response = await callSignupRequestCodeApi({
                username: normalizedUsername,
                email: normalizedEmail,
                password: normalizedPassword,
                full_name: signupFullName.trim() || undefined,
                preferred_language: preferredLanguage,
                country_code: normalizedCountryCode || undefined,
                phone_number: trimmedPhone || undefined,
                verificationChannel: signupVerificationChannel,
                member_type: 'individual',
            });
            setSignupSessionToken(response.signupSessionToken);
            setSignupMaskedTarget(response.maskedTarget);
            if (response.devOtpHint) {
                setSignupOtpCode(response.devOtpHint);
            }
            setSignupStep('verify');
            setLoginError('');
            logUiPressProbe('SIGNUP_REQUEST_CODE_SUCCESS', {
                masked_target: response.maskedTarget,
                verification_channel: response.verificationChannel,
            });
        } catch (e: any) {
            setLoginError(e?.message || '인증 코드 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.');
            logUiPressProbe('SIGNUP_REQUEST_CODE_FAIL', {
                error: e?.message || '이메일 인증 요청 실패',
            });
        } finally {
            setLoginLoading(false);
        }
    }, [logUiPressProbe, loginEmail, loginPw, signupAiName, signupCountryCode, signupFullName, signupPhone, signupPreferredLanguage, signupUsername, signupVerificationChannel]);

    const handleSignupConfirm = useCallback(async () => {
        const normalizedEmail = loginEmail.trim();
        const normalizedPassword = loginPw.trim();
        const preferredLanguage = signupPreferredLanguage;
        const normalizedCountryCode = signupCountryCode.trim().toUpperCase();
        const trimmedOtp = signupOtpCode.trim();

        logUiPressProbe('SIGNUP_CONFIRM_PRESS', {
            otp_filled: trimmedOtp.length >= 6,
            email_filled: Boolean(normalizedEmail),
        });

        if (!signupSessionToken || trimmedOtp.length < 6) {
            setLoginError('6자리 인증 코드를 입력하세요.');
            return;
        }

        setLoginLoading(true);
        setLoginError('');
        try {
            const signedUpUser = await callSignupConfirmApi(signupSessionToken, trimmedOtp, {
                preferred_language: preferredLanguage,
                country_code: normalizedCountryCode || undefined,
                full_name: signupFullName.trim() || undefined,
            });
            const tk = await callLoginApi(normalizedEmail, normalizedPassword);
            const me = await callMeApi(tk);
            const mergedUserInfo: UserInfo = {
                ...me,
                preferred_language: me.preferred_language || signedUpUser.preferred_language || preferredLanguage,
                country_code: me.country_code || signedUpUser.country_code || normalizedCountryCode || null,
            };
            applyAuthenticatedSession(tk, mergedUserInfo);
            await saveStoredAuthState(tk, mergedUserInfo);
            // [Phase6.0] 가입 시 등록한 "나의 AI 이름" 영속 → 즉시 "OOOO AI" 표시명으로 치환.
            if (isValidAiName(signupAiName)) {
                await saveAiName(signupAiName);
                setAiDisplayName(resolveAiDisplayName(signupAiName));
            }
            setAuthModalMode('login');
            setSignupUsername('');
            setSignupFullName('');
            setSignupAiName('');
            resetSignupProfileDraft();
            setDemoSessionMessage('');
            logUiPressProbe('SIGNUP_SUBMIT_SUCCESS', {
                user_id: me.id,
                user_email: me.email,
            });
        } catch (e: any) {
            setLoginError(e?.message || '회원가입 실패');
            logUiPressProbe('SIGNUP_SUBMIT_FAIL', {
                error: e?.message || '회원가입 실패',
            });
        } finally {
            setLoginLoading(false);
        }
    }, [applyAuthenticatedSession, logUiPressProbe, loginEmail, loginPw, resetSignupProfileDraft, signupAiName, signupCountryCode, signupFullName, signupOtpCode, signupPreferredLanguage, signupSessionToken]);

    const handleSignupSubmit = useCallback(async () => {
        if (signupStep === 'verify') {
            await handleSignupConfirm();
            return;
        }
        await handleSignupRequestCode();
    }, [handleSignupConfirm, handleSignupRequestCode, signupStep]);

    const signupSubmitLabel = authModalMode === 'login'
        ? '로그인'
        : signupStep === 'verify'
            ? '인증 후 가입 완료'
            : signupVerificationChannel === 'phone'
                ? '전화 인증 코드 받기'
                : '이메일 인증 코드 받기';

    const handleSelectSignupLanguage = useCallback((code: LangCode) => {
        setSignupPreferredLanguage(code);
        setSignupCountryCode(resolveSignupCountryFromLang(code));
        setSignupSelectionModal(null);
    }, []);

    const handleSelectSignupCountry = useCallback((code: SignupCountryCode) => {
        setSignupCountryCode(code);
        const mappedLanguage = resolveLangFromCountry(code);
        if (mappedLanguage) {
            setSignupPreferredLanguage(mappedLanguage);
        }
        setSignupSelectionModal(null);
    }, []);

    const handleSelectProfileLanguage = useCallback((code: LangCode) => {
        setProfilePreferredLanguage(code);
        setProfileCountryCode(resolveSignupCountryFromLang(code));
        setProfileSelectionModal(null);
    }, []);

    const handleSelectProfileCountry = useCallback((code: SignupCountryCode) => {
        setProfileCountryCode(code);
        const mappedLanguage = resolveLangFromCountry(code);
        if (mappedLanguage) {
            setProfilePreferredLanguage(mappedLanguage);
        }
        setProfileSelectionModal(null);
    }, []);

    const handleSaveMyProfile = useCallback(async () => {
        if (!token || !userInfo) {
            setProfileMessage('로그인 후 프로필 기본값을 저장할 수 있습니다.');
            return;
        }

        setProfileSaving(true);
        setProfileMessage('');
        try {
            const updatedUserInfo = await callUpdateMeApi(token, {
                preferred_language: profilePreferredLanguage,
                country_code: profileCountryCode,
            });
            setUserInfo(updatedUserInfo);
            await saveStoredAuthState(token, updatedUserInfo);
            setProfileMessage('프로필 기본값 저장됨. 이후 채팅/VoIP 기본 언어 계산에 바로 반영됩니다.');
            setChatRefreshKey((prev) => prev + 1);
        } catch (error: any) {
            setProfileMessage(error?.message || '프로필 기본값 저장 실패');
        } finally {
            setProfileSaving(false);
        }
    }, [profileCountryCode, profilePreferredLanguage, token, userInfo]);

    const renderSignupProfileSelectors = useCallback(() => (
        <>
            <Text style={styles.signupProfileLabel}>회원 기본 언어</Text>
            <Pressable
                style={styles.signupPickerTrigger}
                onPress={() => setSignupSelectionModal('language')}
                accessibilityLabel="worldlinco-signup-language-picker-trigger"
                testID="worldlinco-signup-language-picker-trigger"
            >
                <View>
                    <Text style={styles.signupPickerValue}>{getLangLabelText(signupPreferredLanguage)}</Text>
                    <Text style={styles.signupPickerMeta}>50개 언어 전체에서 선택</Text>
                </View>
                <Text style={styles.signupPickerHint}>열기</Text>
            </Pressable>
            <Text style={styles.signupProfileLabel}>프로필 국가</Text>
            <Pressable
                style={styles.signupPickerTrigger}
                onPress={() => setSignupSelectionModal('country')}
                accessibilityLabel="worldlinco-signup-country-picker-trigger"
                testID="worldlinco-signup-country-picker-trigger"
            >
                <View>
                    <Text style={styles.signupPickerValue}>{resolveCountryFlag(signupCountryCode)} {resolveCountryName(signupCountryCode)}</Text>
                    <Text style={styles.signupPickerMeta}>50개국 서비스 프로필에서 선택</Text>
                </View>
                <Text style={styles.signupPickerHint}>열기</Text>
            </Pressable>
            <Text style={styles.signupProfileHint}>
                VoIP 보이스톡·채팅 통역은 이 프로필의 사용 언어 {getLangLabelText(signupPreferredLanguage)} / 국가 {resolveCountryFlag(signupCountryCode)} {signupCountryCode} 를 상대 연결 기준으로 사용합니다. OTP 인증 단계에서도 변경할 수 있습니다.
            </Text>
            <Modal
                visible={signupSelectionModal !== null}
                transparent
                animationType="fade"
                onRequestClose={() => setSignupSelectionModal(null)}
            >
                <Pressable style={styles.langModalOverlay} onPress={() => setSignupSelectionModal(null)}>
                    <Pressable style={styles.langModalCard} onPress={() => { }} testID="worldlinco-signup-selection-modal">
                        <Text style={styles.langModalTitle}>
                            {signupSelectionModal === 'language' ? '회원 기본 언어 선택' : '프로필 국가 선택'}
                        </Text>
                        <Text style={styles.signupModalSub}>
                            {signupSelectionModal === 'language'
                                ? `지원 언어 ${SUPPORTED_LANGUAGE_COUNT}개 전체를 열어서 선택합니다.`
                                : `서비스 국가 ${SIGNUP_COUNTRY_OPTION_CODES.length}개 전체를 열어서 선택합니다.`}
                        </Text>
                        <ScrollView style={styles.langModalList}>
                            {signupSelectionModal === 'language'
                                ? LANGS.map((language) => {
                                    const active = signupPreferredLanguage === language.code;
                                    return (
                                        <Pressable
                                            key={`signup-language-option-${language.code}`}
                                            style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                            onPress={() => handleSelectSignupLanguage(language.code)}
                                            accessibilityLabel={`worldlinco-signup-language-${language.code}`}
                                            testID={`worldlinco-signup-language-${language.code}`}
                                        >
                                            <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>
                                                {language.label}
                                            </Text>
                                            {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                        </Pressable>
                                    );
                                })
                                : SIGNUP_COUNTRY_OPTIONS.map((country) => {
                                    const active = signupCountryCode === country.code;
                                    return (
                                        <Pressable
                                            key={`signup-country-option-${country.code}`}
                                            style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                            onPress={() => handleSelectSignupCountry(country.code)}
                                            accessibilityLabel={`worldlinco-signup-country-${country.code}`}
                                            testID={`worldlinco-signup-country-${country.code}`}
                                        >
                                            <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>
                                                {resolveCountryFlag(country.code)} {country.label}
                                            </Text>
                                            {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                        </Pressable>
                                    );
                                })}
                        </ScrollView>
                        <Pressable
                            style={styles.langModalCloseBtn}
                            onPress={() => setSignupSelectionModal(null)}
                            testID="worldlinco-signup-selection-close"
                        >
                            <Text style={styles.langModalCloseText}>닫기</Text>
                        </Pressable>
                    </Pressable>
                </Pressable>
            </Modal>
        </>
    ), [handleSelectSignupCountry, handleSelectSignupLanguage, signupCountryCode, signupPreferredLanguage, signupSelectionModal]);

    const renderSignupAuthFields = useCallback(() => {
        return (
            <>
                {signupStep === 'form' ? (
                    <>
                        <View style={styles.signupChannelRow}>
                            <Pressable
                                style={[styles.signupChannelBtn, signupVerificationChannel === 'email' && styles.signupChannelBtnActive]}
                                onPress={() => setSignupVerificationChannel('email')}
                                testID="worldlinco-signup-channel-email"
                            >
                                <Text style={styles.signupChannelBtnText}>이메일 인증</Text>
                            </Pressable>
                            <Pressable
                                style={[styles.signupChannelBtn, signupVerificationChannel === 'phone' && styles.signupChannelBtnActive]}
                                onPress={() => setSignupVerificationChannel('phone')}
                                testID="worldlinco-signup-channel-phone"
                            >
                                <Text style={styles.signupChannelBtnText}>전화 인증</Text>
                            </Pressable>
                        </View>
                        <TextInput
                            style={styles.compactInput}
                            placeholder="사용자명"
                            placeholderTextColor={C.sub}
                            autoCapitalize="none"
                            showSoftInputOnFocus
                            value={signupUsername}
                            onChangeText={setSignupUsername}
                        />
                        <TextInput
                            style={styles.compactInput}
                            placeholder="이름(선택)"
                            placeholderTextColor={C.sub}
                            showSoftInputOnFocus
                            value={signupFullName}
                            onChangeText={setSignupFullName}
                        />
                        <TextInput
                            style={styles.compactInput}
                            placeholder='나의 AI 이름 (필수, 예: 토토)'
                            placeholderTextColor={C.sub}
                            showSoftInputOnFocus
                            maxLength={20}
                            value={signupAiName}
                            onChangeText={setSignupAiName}
                            accessibilityLabel="worldlinco-signup-ai-name-input"
                            testID="worldlinco-signup-ai-name-input"
                        />
                        <Text style={styles.inlineAuthHint}>
                            {isValidAiName(signupAiName)
                                ? `이 AI를 "${resolveAiDisplayName(signupAiName)}"(으)로 부릅니다.`
                                : '나의 AI 이름을 등록하면 소리새 AI가 "OOOO AI"로 바뀝니다.'}
                        </Text>
                        <TextInput
                            style={styles.compactInput}
                            placeholder={signupVerificationChannel === 'phone' ? '연락처 (+82-10-1234-5678, 필수)' : '연락처 (+82, VoIP·친구용 권장)'}
                            placeholderTextColor={C.sub}
                            keyboardType="phone-pad"
                            showSoftInputOnFocus
                            value={signupPhone}
                            onChangeText={setSignupPhone}
                            testID="worldlinco-signup-phone-input"
                        />
                    </>
                ) : (
                    <>
                        <Text style={styles.inlineAuthHint}>
                            {signupMaskedTarget || loginEmail.trim()} 으로 인증 코드를 보냈습니다. 아래 프로필 언어·국가를 확인한 뒤 6자리 코드를 입력해 주세요.
                        </Text>
                        <TextInput
                            style={styles.compactInput}
                            placeholder="6자리 인증 코드"
                            placeholderTextColor={C.sub}
                            keyboardType="number-pad"
                            maxLength={6}
                            showSoftInputOnFocus
                            value={signupOtpCode}
                            onChangeText={setSignupOtpCode}
                            accessibilityLabel="worldlinco-signup-otp-input"
                            testID="worldlinco-signup-otp-input"
                        />
                        <Pressable
                            style={styles.authModeToggleBtn}
                            onPress={() => {
                                setSignupStep('form');
                                setSignupOtpCode('');
                                setLoginError('');
                            }}
                            accessibilityLabel="worldlinco-signup-back-to-form"
                            testID="worldlinco-signup-back-to-form"
                        >
                            <Text style={styles.authModeToggleText}>입력 다시하기</Text>
                        </Pressable>
                    </>
                )}
                {renderSignupProfileSelectors()}
            </>
        );
    }, [loginEmail, renderSignupProfileSelectors, signupAiName, signupFullName, signupMaskedTarget, signupOtpCode, signupPhone, signupStep, signupUsername, signupVerificationChannel]);

    const handlePressLoginButton = useCallback(() => {
        openLoginModalForSource('header_account_row');
    }, [openLoginModalForSource]);

    const handlePressFriendEntry = useCallback((target: 'friend-folder' | 'friend-map') => {
        if (!userInfo) {
            Alert.alert('로그인 필요', '친구 기능을 사용하려면 먼저 로그인해 주세요.');
            logUiPressProbe('LOGIN_BUTTON_PRESS', { source: target });
            setShowLogin(true);
            return;
        }

        setActiveRailSection('chat');

        if (target === 'friend-folder') {
            setShowFriendFolder((prev) => {
                const next = !prev;
                if (next) {
                    setShowFriendMapDiscovery(false);
                }
                return next;
            });
            return;
        }

        setShowFriendMapDiscovery((prev) => {
            const next = !prev;
            if (next) {
                setShowFriendFolder(false);
            }
            return next;
        });
    }, [logUiPressProbe, userInfo]);

    const handleOpenFriendMapFromFolder = useCallback(() => {
        if (!userInfo) {
            Alert.alert('로그인 필요', '근처 친구 찾기를 사용하려면 먼저 로그인해 주세요.');
            return;
        }
        setActiveRailSection('chat');
        setShowFriendFolder(false);
        setShowFriendMapDiscovery(true);
        logUiPressProbe('FRIEND_ADD_MAP_DISCOVERY', { source: 'friend_folder_hub' });
    }, [logUiPressProbe, userInfo]);

    const handleDispatchChatShare = useCallback(async (room: ChatRoomSummary, params: {
        messageType: string;
        body: string;
        translatedBody?: string | null;
        sourceLang?: string | null;
        targetLang?: string | null;
        failureTitle: string;
    }) => {
        setChatShareLoading(true);
        try {
            await sendChatRoomMessage(API_BASE, token, room.room_id, {
                messageType: params.messageType,
                body: params.body,
                translatedBody: params.translatedBody ?? null,
                sourceLang: params.sourceLang ?? null,
                targetLang: params.targetLang ?? null,
            });
            setSelectedChatRoom(room);
            setActiveRailSection('chat');
            setChatRefreshKey((prev) => prev + 1);
            setPendingChatShare(null);
            setShareTargetOptions([]);
            setShareTargetVisible(false);
        } catch (error: unknown) {
            Alert.alert(params.failureTitle, error instanceof Error ? error.message : '채팅 메시지를 전송하지 못했습니다.');
        } finally {
            setChatShareLoading(false);
        }
    }, [token]);

    const handleShareMessageToChat = useCallback(async (params: {
        messageType: string;
        body: string;
        translatedBody?: string | null;
        sourceLang?: string | null;
        targetLang?: string | null;
        emptyTitle: string;
        emptyMessage: string;
        failureTitle: string;
    }) => {
        if (!token || !userInfo) {
            Alert.alert('로그인 필요', '채팅으로 보내려면 먼저 로그인해 주세요.');
            setShowLogin(true);
            return;
        }

        const body = params.body.trim();
        const translatedBody = params.translatedBody?.trim() || null;
        if (!body && !translatedBody) {
            Alert.alert(params.emptyTitle, params.emptyMessage);
            return;
        }

        setChatShareLoading(true);
        setShareTargetError('');
        try {
            const [selfRoom, recentRooms] = await Promise.all([
                ensureSelfChatRoom(API_BASE, token),
                listChatRooms(API_BASE, token),
            ]);
            const nextTargets: ChatRoomSummary[] = [];
            if (selectedChatRoom) {
                nextTargets.push(selectedChatRoom);
            }
            if (!nextTargets.some((room) => room.room_id === selfRoom.room_id)) {
                nextTargets.push(selfRoom);
            }
            for (const recentRoom of recentRooms) {
                if (recentRoom.room_type !== 'group' || recentRoom.title === '번역 보관함') {
                    continue;
                }
                if (nextTargets.some((room) => room.room_id === recentRoom.room_id)) {
                    continue;
                }
                nextTargets.push(recentRoom);
                if (nextTargets.length >= 6) {
                    break;
                }
            }
            setPendingChatShare({
                messageType: params.messageType,
                body: body || translatedBody || '',
                translatedBody,
                sourceLang: params.sourceLang ?? null,
                targetLang: params.targetLang ?? null,
                failureTitle: params.failureTitle,
            });
            setShareTargetOptions(nextTargets);
            setShareTargetVisible(true);
        } catch (error: unknown) {
            setShareTargetError(error instanceof Error ? error.message : '공유 대상을 준비하지 못했습니다.');
        } finally {
            setChatShareLoading(false);
        }
    }, [selectedChatRoom, token, userInfo]);

    const handleSelectShareTarget = useCallback(async (room: ChatRoomSummary) => {
        if (!pendingChatShare) {
            return;
        }
        await handleDispatchChatShare(room, pendingChatShare);
    }, [handleDispatchChatShare, pendingChatShare]);

    const handleShareTranslationToChat = useCallback(async () => {
        void handleShareMessageToChat({
            messageType: 'translation',
            body: inputText,
            translatedBody: resultText,
            sourceLang: fromLang,
            targetLang: toLang,
            emptyTitle: '공유할 번역 없음',
            emptyMessage: '먼저 번역 결과를 만든 뒤 채팅으로 보낼 수 있습니다.',
            failureTitle: '채팅 공유 실패',
        });
    }, [fromLang, handleShareMessageToChat, inputText, resultText, toLang]);

    const handleShareOcrToChat = useCallback(async () => {
        void handleShareMessageToChat({  // NOSONAR
            messageType: 'ocr',
            body: ocrExtractedText,
            translatedBody: ocrTranslatedText,
            sourceLang: null,
            targetLang: toLang,
            emptyTitle: '공유할 OCR 결과 없음',
            emptyMessage: '먼저 이미지 OCR 결과를 만든 뒤 채팅으로 보낼 수 있습니다.',
            failureTitle: 'OCR 채팅 공유 실패',
        });
    }, [handleShareMessageToChat, ocrExtractedText, ocrTranslatedText, toLang]);

    const handleShareSongToChat = useCallback(async () => {
        const previewSegments = songFileSegments.slice(0, 6);
        const sourcePreview = previewSegments
            .map((segment) => `[${formatSongFileTime(segment.start_ms)}] ${segment.original}`)
            .join('\n');
        const translatedPreview = previewSegments
            .map((segment) => `[${formatSongFileTime(segment.start_ms)}] ${segment.translated || segment.original}`)
            .join('\n');
        const fallbackTranslated = songFileExportPreview.trim() || voicePreview?.preview_text?.trim() || null;
        const body = [
            songFileName ? `파일: ${songFileName}` : null,
            songFileJob ? `상태: ${songFileJob.message}` : null,
            sourcePreview || null,
        ].filter(Boolean).join('\n');
        void handleShareMessageToChat({
            messageType: 'song_translation',
            body,
            translatedBody: translatedPreview || fallbackTranslated,
            sourceLang: previewSegments[0]?.source_language || fromLang,
            targetLang: previewSegments[0]?.target_language || resolveSongFileTargetLang(fromLang, toLang),
            emptyTitle: '공유할 노래 번역 없음',
            emptyMessage: '먼저 노래 파일 번역 결과를 만든 뒤 채팅으로 보낼 수 있습니다.',
            failureTitle: '노래 번역 공유 실패',
        });
    }, [fromLang, handleShareMessageToChat, songFileExportPreview, songFileJob, songFileName, songFileSegments, toLang, voicePreview?.preview_text]);

    const handleLogout = useCallback(() => {
        // 이 단말의 착신 푸시 구독/토큰을 해제 → 로그아웃한 단말이 더 이상 착신 벨을 울리지 않게 한다.
        // (다기기 로그인 시 'A폰에서 로그아웃했는데 A가 계속 울림' 방지)
        const logoutToken = tokenRef.current;
        const logoutTopic = voipTopicRef.current;
        void (async () => {
            try {
                const pushToken = await messaging().getToken().catch(() => '');
                if (pushToken && logoutToken) {
                    await unregisterVoipDevice(API_BASE, logoutToken, pushToken);
                }
                if (logoutTopic) {
                    await messaging().unsubscribeFromTopic(logoutTopic).catch(() => undefined);
                }
            } catch (error) {
                console.log('[VoIPFCM] logout unregister failed', error);
            } finally {
                voipTopicRef.current = null;
            }
        })();
        voipPresenceSocketRef.current?.close();
        voipPresenceSocketRef.current = null;
        setToken('');
        setUserInfo(null);
        setLoginEmail('');
        setLoginPw('');
        setLoginError('');
        setDemoSessionMessage('');
        setDemoSessionError('');
        setAuthModalMode('login');
        setSignupUsername('');
        setSignupFullName('');
        setVoipIdentity('');
        setShowMyInfo(false);
        setProfileSelectionModal(null);
        setProfileMessage('');
        setShowFriendFolder(false);
        setShowFriendMapDiscovery(false);
        setSelectedChatRoom(null);
        setMyPurchases(null);
        clearStoredAuthState().catch((error) => {
            console.log('[AuthStorage] clear failed', error);
        });
    }, []);

    useEffect(() => {
        handleLogoutRef.current = handleLogout;
    }, [handleLogout]);

    // 로그인되면 세션-만료 1회성 가드를 초기화(다음 supersede 감지 가능하도록).
    useEffect(() => {
        if (token) {
            sessionSupersededHandledRef.current = false;
        }
    }, [token]);

    const handlePasswordSecurityCompleted = useCallback(async (payload: { email: string; newPassword?: string; mustRelogin?: boolean }) => {
        if (!payload.mustRelogin || !payload.newPassword) {
            return;
        }
        handleLogout();
        setLoginEmail(payload.email);
        setLoginPw(payload.newPassword);
        setAuthModalMode('login');
        setShowLogin(true);
        setLoginError('');
        Alert.alert('비밀번호 변경 완료', '새 비밀번호로 다시 로그인해 주세요.');
    }, [handleLogout]);

    useEffect(() => {
        if (!token || !userInfo) {
            voipPresenceSocketRef.current?.close();
            voipPresenceSocketRef.current = null;
            setVoipIdentity('');
            return;
        }

        const identity = buildVoiceId(userInfo.id);
        setVoipIdentity(identity);
        const tokenSummary = summarizeAuthToken(token);

        let disposed = false;
        let currentSocket: WebSocket | null = null;
        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

        const clearReconnectTimer = () => {
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        const releaseSocket = (socket: WebSocket | null) => {
            if (!socket) {
                return;
            }
            socket.onopen = null;
            socket.onmessage = null;
            socket.onerror = null;
            socket.onclose = null;
            if (voipPresenceSocketRef.current === socket) {
                voipPresenceSocketRef.current = null;
            }
            if (currentSocket === socket) {
                currentSocket = null;
            }
            try {
                socket.close();
            } catch {
                // Ignore shutdown races during reconnect.
            }
        };

        const scheduleReconnect = (reason: string) => {
            if (disposed || reconnectTimer) {
                return;
            }
            logUiPressProbe('VOIP_PRESENCE_RETRY_SCHEDULED', {
                voice_id: identity,
                token_summary: tokenSummary,
                reason,
            });
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connectPresence(`retry:${reason}`);
            }, 1500);
        };

        const connectPresence = (reason: string) => {
            if (disposed) {
                return;
            }

            if (currentSocket && (currentSocket.readyState === WebSocket.CONNECTING || currentSocket.readyState === WebSocket.OPEN)) {
                logUiPressProbe('VOIP_PRESENCE_CONNECT_SKIPPED', {
                    voice_id: identity,
                    token_summary: tokenSummary,
                    reason,
                    ready_state: currentSocket.readyState,
                });
                return;
            }

            clearReconnectTimer();
            releaseSocket(currentSocket);

            const url = buildVoipWebSocketUrl(API_BASE, '/api/v1/voip/presence', { token });
            logUiPressProbe('VOIP_PRESENCE_CONNECT_ATTEMPT', {
                voice_id: identity,
                token_summary: tokenSummary,
                reason,
                api_base: API_BASE,
            });

            let socket: WebSocket;
            try {
                socket = new WebSocket(url);
            } catch (error: any) {
                logUiPressProbe('VOIP_PRESENCE_CONSTRUCTOR_FAIL', {
                    voice_id: identity,
                    token_summary: tokenSummary,
                    reason,
                    error: error?.message || 'presence socket constructor failed',
                });
                scheduleReconnect('constructor_fail');
                return;
            }

            currentSocket = socket;
            voipPresenceSocketRef.current = socket;

            socket.onopen = () => {
                if (disposed || currentSocket !== socket) {
                    return;
                }
                clearReconnectTimer();
                logUiPressProbe('VOIP_PRESENCE_CONNECTED', {
                    voice_id: identity,
                    token_summary: tokenSummary,
                    reason,
                });
            };

            socket.onmessage = (event) => {
                try {
                    const rawData = typeof event.data === 'string' ? event.data : '';
                    const payload = JSON.parse(event.data);
                    if (payload?.type === 'presence_ready') {
                        setVoipIdentity(payload.voice_id || identity);
                        return;
                    }
                    if (payload?.type === 'incoming_call_ended') {
                        const localPending = pendingIncomingVoipCallRef.current;
                        if (localPending?.call_id && payload.call_id === localPending.call_id) {
                            logUiPressProbe('VOIP_INCOMING_CALL_ENDED', {
                                call_id: payload.call_id,
                                reason: payload.reason ?? null,
                                caller_voice_id: localPending.caller_voice_id ?? null,
                            });
                            dismissPendingIncomingAsMissed(
                                'presence_socket',
                                String(payload.reason || 'caller_ended'),
                                localPending,
                            );
                        }
                        return;
                    }
                    if (payload?.type === 'incoming_call') {
                        const compactSummary = summarizeIncomingVoipPayload(payload as Partial<CallInitResponse> & { caller_voice_id?: string });
                        logUiPressProbe('VOIP_INCOMING_CALL_RAW_FLAGS', {
                            call_id: payload.call_id ?? null,
                            raw_length: rawData.length || null,
                            raw_has_requested_mode: rawData.includes('"requested_mode"'),
                            raw_has_resolved_mode: rawData.includes('"resolved_mode"'),
                            raw_has_auto_relay_requested: rawData.includes('"auto_relay_requested"'),
                            raw_has_auto_relay_applied: rawData.includes('"auto_relay_applied"'),
                        });
                        logUiPressProbe('VOIP_INCOMING_CALL_MODE', {
                            call_id: payload.call_id ?? null,
                            mode_compact: compactSummary.mode_compact,
                            relay_compact: compactSummary.relay_compact,
                        });
                        logUiPressProbe('VOIP_INCOMING_CALL_KEYS', {
                            call_id: payload.call_id ?? null,
                            key_compact: compactSummary.key_compact,
                        });
                        logUiPressProbe('VOIP_INCOMING_CALL_RECEIVED', {
                            call_id: payload.call_id ?? null,
                            ...compactSummary,
                        });
                        applyIncomingVoipPayload(payload as CallInitResponse & { caller_label?: string; caller_voice_id?: string }, 'presence_socket');
                    }
                } catch (error) {
                    console.log('[VoIPPresence] parse failed', error);
                }
            };

            socket.onerror = () => {
                if (disposed || currentSocket !== socket) {
                    return;
                }
                logUiPressProbe('VOIP_PRESENCE_ERROR', {
                    voice_id: identity,
                    token_summary: tokenSummary,
                    reason,
                });
            };

            socket.onclose = (event) => {
                if (currentSocket === socket) {
                    currentSocket = null;
                }
                if (voipPresenceSocketRef.current === socket) {
                    voipPresenceSocketRef.current = null;
                }
                logUiPressProbe('VOIP_PRESENCE_CLOSED', {
                    voice_id: identity,
                    token_summary: tokenSummary,
                    reason,
                    code: event.code,
                });
                if (!disposed) {
                    scheduleReconnect(`close:${event.code}`);
                }
            };
        };

        connectPresence('effect_start');

        const appStateSubscription = AppState.addEventListener('change', (nextState) => {
            if (nextState !== 'active') {
                return;
            }
            if (!currentSocket || currentSocket.readyState === WebSocket.CLOSED || currentSocket.readyState === WebSocket.CLOSING) {
                connectPresence('app_active');
            }
        });

        return () => {
            disposed = true;
            clearReconnectTimer();
            appStateSubscription.remove();
            releaseSocket(currentSocket);
        };
    }, [applyIncomingVoipPayload, dismissPendingIncomingAsMissed, logUiPressProbe, summarizeIncomingVoipPayload, token, userInfo]);

    const handleShowPurchases = useCallback(async () => {
        if (!token) {
            setShowLogin(true);
            return;
        }
        if (myPurchases !== null) {
            setMyPurchases(null);
            return;
        }
        setMyPurchasesLoading(true);
        try {
            const list = await callMyPurchasesApi(token);
            setMyPurchases(list);
        } catch {
            setMyPurchases([]);
        } finally {
            setMyPurchasesLoading(false);
        }
    }, [myPurchases, token]);

    const loadPurchasesSnapshot = useCallback(async (forceRefresh = false) => {
        if (!token) {
            return null;
        }
        if (!forceRefresh && myPurchases !== null) {
            return myPurchases;
        }
        setMyPurchasesLoading(true);
        try {
            const list = await callMyPurchasesApi(token);
            setMyPurchases(list);
            return list;
        } catch {
            setMyPurchases([]);
            return [] as Array<{ id: number; amount: number; status: string; payment_method: string }>;
        } finally {
            setMyPurchasesLoading(false);
        }
    }, [myPurchases, token]);

    const persistVoipValidationFriendCallBypass = useCallback(async (enabled: boolean) => {
        try {
            if (enabled) {
                await AsyncStorage.setItem(VOIP_VALIDATION_FRIEND_CALL_BYPASS_KEY, '1');
                return;
            }
            await AsyncStorage.removeItem(VOIP_VALIDATION_FRIEND_CALL_BYPASS_KEY);
        } catch {
            // Best-effort persistence only for validation reruns.
        }
    }, []);

    const handlePremiumPurchase = useCallback(async (planKey: MonetizationPlanKey) => {
        if (!token) {
            setShowLogin(true);
            setPremiumStatusMessage('프리미엄 구매는 로그인 후 진행할 수 있습니다.');
            return;
        }
        const plan = MONETIZATION_PLAN_CONFIG[planKey];
        setPayLoading(true);
        setPayError('');
        setPremiumStatusMessage(`${plan.title} 결제를 준비하는 중입니다.`);
        try {
            const purchase = await callCreatePurchaseApi(token, plan.amount);
            setPurchaseResult(purchase);
            const payData = await callInitiatePaymentApi(token, purchase.id);
            setPayUrl(payData.payment_url);
            setPremiumStatusMessage(`${plan.title} 결제 링크를 열 수 있습니다.`);
            await loadPurchasesSnapshot(true);
        } catch (error: any) {
            const message = error?.message || '프리미엄 결제 준비에 실패했습니다.';
            setPayError(message);
            setPremiumStatusMessage(message);
        } finally {
            setPayLoading(false);
        }
    }, [loadPurchasesSnapshot, token]);

    const ensureVoipPremiumAccess = useCallback(async (source: string, allowValidationOverride = false) => {
        if (!token || !userInfo) {
            setShowLogin(true);
            setVoipInitError('VoIP 프리미엄은 로그인 후 사용할 수 있습니다.');
            logUiPressProbe('VOIP_PREMIUM_GATE_LOGIN_REQUIRED', { source });
            return false;
        }

        if (allowValidationOverride) {
            setPremiumStatusMessage('정합성 검증 전용 VoIP 테스트를 진행합니다. 구매 상태는 변경되지 않으며 실제 번역/통역 결과 확인만 허용합니다.');
            logUiPressProbe('VOIP_PREMIUM_GATE_VALIDATION_OVERRIDE', { source });
            return true;
        }

        if (isInstantDemoSession) {
            return true;
        }

        const purchases = await loadPurchasesSnapshot();
        const ownedPlans = collectOwnedPlanKeys(purchases);
        if (!ownedPlans.has('voip_lite') && !ownedPlans.has('voip_pro')) {
            setActiveRailSection('voip');
            setPremiumStatusMessage('VoIP 통역 통화는 Lite 또는 Pro 월정액이 필요합니다.');
            setVoipInitError('VoIP 통역 통화는 Lite 또는 Pro 월정액이 필요합니다.');
            logUiPressProbe('VOIP_PREMIUM_GATE_BLOCKED', { source });
            return false;
        }

        return true;
    }, [isInstantDemoSession, loadPurchasesSnapshot, logUiPressProbe, token, userInfo]);

    const handleOpenVoipTester = useCallback(() => {
        logUiPressProbe('VOIP_OPEN_PRESS', {
            source: 'shared_handler',
        });
        if (selectedCallMode !== 'pstn_assist' && (!token || !userInfo)) {
            logUiPressProbe('VOIP_OPEN_BLOCKED_LOGIN_REQUIRED');
            setShowLogin(true);
            setVoipInitError('VoIP 테스트는 로그인 후 사용할 수 있습니다.');
            return;
        }

        if (selectedCallMode !== 'pstn_assist' && !effectiveVoipPlan) {
            setActiveRailSection('voip');
            setPremiumStatusMessage('VoIP 통역 통화는 Lite 또는 Pro 월정액이 필요합니다.');
            setVoipInitError('VoIP 통역 통화는 Lite 또는 Pro 월정액이 필요합니다.');
            logUiPressProbe('VOIP_OPEN_BLOCKED_PREMIUM_REQUIRED');
            return;
        }

        setVoipValidationOverride(false);
        voipValidationFriendCallBypassRef.current = false;
        void persistVoipValidationFriendCallBypass(false);  // NOSONAR
        openVoipTesterPanel();
        logUiPressProbe('VOIP_OPEN_SUCCESS');
    }, [effectiveVoipPlan, logUiPressProbe, openVoipTesterPanel, persistVoipValidationFriendCallBypass, selectedCallMode, token, userInfo]);

    const handleVoipValidationOpenPress = useCallback(() => {
        if (!token || !userInfo) {
            setShowLogin(true);
            setPremiumStatusMessage('실 번역/통역 정합성 테스트는 로그인된 검증 계정으로 진행할 수 있습니다.');
            return;
        }

        setActiveRailSection('voip');
        setVoipValidationOverride(true);
        voipValidationFriendCallBypassRef.current = true;
        void persistVoipValidationFriendCallBypass(true);
        setPremiumStatusMessage('정합성 검증용 VoIP 테스트를 엽니다. 구매 없이도 실제 번역/통역 결과를 점검할 수 있습니다.');
        setVoipInitError('');
        logUiPressProbe('VOIP_VALIDATION_OPEN_PRESS', { source: 'voip_section_validation_button' });
        openVoipTesterPanel();
    }, [logUiPressProbe, openVoipTesterPanel, persistVoipValidationFriendCallBypass, token, userInfo]);

    const handleOpenServiceRail = useCallback((section: SectionRailKey = 'chat') => {
        setIsRailMenuOpen(true);
        setActiveRailSection(section);
        logUiPressProbe('SECTION_RAIL_OPEN', { source: 'front_translation_surface', section });
    }, [logUiPressProbe]);

    const handleHeaderVoipLaunchPress = useCallback(() => {
        handleOpenServiceRail('voip');
    }, [handleOpenServiceRail]);

    const handleInlineVoipOpenPress = useCallback(() => {
        logUiPressProbe('VOIP_LAUNCH_BUTTON_PRESS', { source: 'voip_section_inline_button' });
        handleOpenVoipTester();
    }, [handleOpenVoipTester, logUiPressProbe]);

    const handleAppEntryDeepLink = useCallback((target: AppEntryDeepLinkTarget, source: string) => {
        if (target.type === 'rail') {
            logUiPressProbe('APP_ENTRY_DEEP_LINK_RAIL_OPEN', { source, section: target.section });
            handleOpenServiceRail(target.section);
            return;
        }

        if (target.type === 'chat') {
            void handleOpenChatRoomById(target.roomId, source);
            return;
        }

        if (target.action === 'incoming') {
            logUiPressProbe('APP_ENTRY_DEEP_LINK_VOIP_INCOMING', {
                source,
                call_id: target.callId ?? null,
            });
            setActiveRailSection('voip');
            void fetchPendingIncomingVoipCall(`deeplink_${source}`);
            return;
        }

        const normalizedPreferredLanguage = String(target.preferredLanguage || '').trim().toLowerCase();
        if (normalizedPreferredLanguage && isSupportedLangCode(normalizedPreferredLanguage)) {
            setFromLang(normalizedPreferredLanguage);
            setToLang((currentTarget) => resolveAutoTargetLang(normalizedPreferredLanguage, currentTarget));
            setUserInfo((prev) => (prev ? { ...prev, preferred_language: normalizedPreferredLanguage } : prev));
            logUiPressProbe('VOIP_DEEPLINK_PREFERRED_LANGUAGE_APPLIED', {
                source,
                preferred_language: normalizedPreferredLanguage,
            });
        }

        logUiPressProbe('APP_ENTRY_DEEP_LINK_VOIP_OPEN', { source, action: target.action });
        setActiveRailSection('voip');

        if (target.action === 'validation') {
            if (target.calleeVoiceId) {
                const normalizedCalleeVoiceId = target.calleeVoiceId.trim().toLowerCase();
                const validationAutoCallKey = `validation:${normalizedCalleeVoiceId}`;
                if (!target.forceRetry && consumedValidationAutoCallKeyRef.current === validationAutoCallKey) {
                    logUiPressProbe('VOIP_VALIDATION_AUTO_CALL_SKIPPED_ALREADY_CONSUMED', {
                        source,
                        callee_voice_id: target.calleeVoiceId,
                        active_call_id: voipCallInitResponseRef.current?.call_id ?? null,
                    });
                    if (voipCallInitResponseRef.current || pendingIncomingVoipCallRef.current) {
                        setShowFriendFolder(false);
                        setVoipAutoCallVoiceId(null);
                        setActiveRailSection('voip');
                        setShowVoipTester(true);
                    }
                    return;
                }
                if (voipCallInitResponseRef.current || pendingIncomingVoipCallRef.current) {
                    consumedValidationAutoCallKeyRef.current = validationAutoCallKey;
                    logUiPressProbe('VOIP_VALIDATION_AUTO_CALL_SKIPPED_ACTIVE_CALL', {
                        source,
                        callee_voice_id: target.calleeVoiceId,
                        active_call_id: voipCallInitResponseRef.current?.call_id ?? null,
                        pending_call_id: pendingIncomingVoipCallRef.current?.call_id ?? null,
                    });
                    setShowFriendFolder(false);
                    setVoipAutoCallVoiceId(null);
                    setActiveRailSection('voip');
                    setShowVoipTester(true);
                    return;
                }

                const ownVoiceId = userInfo ? buildVoiceId(userInfo.id) : null;
                if (ownVoiceId && normalizedCalleeVoiceId === ownVoiceId.toLowerCase()) {
                    setVoipInitError('자기 자신의 보이스 ID로는 통화할 수 없습니다. 친구 보이스 ID를 지정해 주세요.');
                    logUiPressProbe('VOIP_VALIDATION_AUTO_CALL_REJECTED_SELF', {
                        source,
                        callee_voice_id: target.calleeVoiceId,
                        own_voice_id: ownVoiceId,
                        auth_ready: Boolean(token && userInfo),
                    });
                    return;
                }

                setVoipValidationOverride(true);
                voipValidationFriendCallBypassRef.current = true;
                void persistVoipValidationFriendCallBypass(true);
                setPremiumStatusMessage('정합성 검증용 친구 자동 통화를 준비합니다. 친구 목록에서 대상 보이스 ID를 찾으면 즉시 통화를 시도합니다.');
                setVoipInitError('');
                logUiPressProbe('VOIP_VALIDATION_OPEN_PRESS', {
                    source: 'app_entry_deep_link_validation_auto_call',
                    auth_ready: Boolean(token && userInfo),
                });
                logUiPressProbe('VOIP_VALIDATION_AUTO_CALL_DEEPLINK', {
                    source,
                    callee_voice_id: target.calleeVoiceId,
                    callee_preferred_language: target.calleePreferredLanguage ?? null,
                    auth_ready: Boolean(token && userInfo),
                });
                consumedValidationAutoCallKeyRef.current = validationAutoCallKey;
                voipAutoCallCalleeLanguageRef.current = isSupportedLangCode(String(target.calleePreferredLanguage || '').trim().toLowerCase())
                    ? String(target.calleePreferredLanguage).trim().toLowerCase() as LangCode
                    : null;
                setVoipAutoCallVoiceId(target.calleeVoiceId);
                setSelectedChatRoom(null);
                setShowVoipTester(false);
                handleOpenServiceRail('chat');
                setShowFriendFolder(true);
                setShowFriendMapDiscovery(false);
                return;
            }

            handleVoipValidationOpenPress();
            return;
        }

        if (target.action === 'demo') {
            void handleStartInstantDemoSession('voip');
            return;
        }

        handleOpenVoipTester();
    }, [handleOpenChatRoomById, handleOpenServiceRail, handleOpenVoipTester, handleStartInstantDemoSession, handleVoipValidationOpenPress, fetchPendingIncomingVoipCall, logUiPressProbe, persistVoipValidationFriendCallBypass, setShowFriendFolder, setShowFriendMapDiscovery, token, userInfo]);

    useEffect(() => {
        let active = true;

        const consumeIncomingUrl = (url: string | null, source: string) => {
            if (!url) {
                return;
            }
            const payload = parseIncomingVoipDeepLink(url);
            if (payload) {
                void autoAcceptIncomingVoipDeepLink(payload, source);
                return;
            }

            const entryTarget = parseAppEntryDeepLink(url);
            if (!entryTarget) {
                return;
            }

            if (url === consumedAppEntryDeepLinkUrlRef.current) {
                const allowRetry = entryTarget.type === 'voip' && Boolean(entryTarget.forceRetry);
                if (!allowRetry) {
                    logUiPressProbe('APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED', { source, url });
                    return;
                }
                logUiPressProbe('APP_ENTRY_DEEP_LINK_FORCE_RETRY', { source, url });
            }

            consumedAppEntryDeepLinkUrlRef.current = url;
            handleAppEntryDeepLink(entryTarget, source);
        };

        const refreshInitialUrl = (source: string) => {
            Linking.getInitialURL()
                .then((url) => {
                    if (active) {
                        consumeIncomingUrl(url, source);
                    }
                })
                .catch((error) => {
                    console.log('[VoIPDeepLink] initial url failed', error);
                });
        };

        refreshInitialUrl('initial_url');

        const subscription = Linking.addEventListener('url', (event) => {
            consumeIncomingUrl(event.url, 'runtime_url');
        });

        const appStateSubscription = AppState.addEventListener('change', (nextState) => {
            if (nextState === 'active') {
                refreshInitialUrl('active_initial_url');
            }
        });

        return () => {
            active = false;
            subscription.remove();
            appStateSubscription.remove();
        };
    }, [autoAcceptIncomingVoipDeepLink, handleAppEntryDeepLink]);

    const handlePhoneOnlyDialFallback = useCallback(async (phone: string, source: string, reason?: string) => {
        logUiPressProbe('VOIP_PHONE_ONLY_DIAL_FALLBACK_START', { phone, source, reason: reason || null });
        const dialOpened = await openDialPad(phone);
        logUiPressProbe('VOIP_PHONE_ONLY_DIAL_FALLBACK_RESULT', { phone, source, dial_opened: dialOpened });
        setVoipCallInitResponse(null);
        setVoipAuditCallId('');
        setVoipAuditEvents([]);
        if (dialOpened) {
            setVoipInitError('');
            setVoipInitLoading(false);
            setShowVoipTester(false);
            return true;
        }
        setVoipInitError(reason || '전화번호 전용 통화는 시스템 전화앱 연결이 필요하지만 다이얼러를 열지 못했습니다.');
        return false;
    }, [logUiPressProbe, openDialPad]);

    const handleStartVoipCall = useCallback(async () => {
        logUiPressProbe('VOIP_START_CALL_PRESS', {
            phone: voipPhone.trim(),
        });
        const phone = voipPhone.trim();
        if (!validatePhoneNumber(phone)) {
            logUiPressProbe('VOIP_START_CALL_BLOCKED_INVALID_PHONE', { phone });
            setVoipInitError('전화번호는 +국가번호 형식이어야 합니다.');
            return;
        }

        const hasPremium = await ensureVoipPremiumAccess('handleStartVoipCall', voipValidationOverride);
        if (!hasPremium) {
            return;
        }

        if (!token || !userInfo) {
            logUiPressProbe('VOIP_START_CALL_BLOCKED_LOGIN_REQUIRED');
            setShowLogin(true);
            setVoipInitError('VoIP 테스트는 로그인 후 사용할 수 있습니다.');
            return;
        }

        // Per-feature 권한 체크: 마이크
        const hasPermission = await requestPermissions(['RECORD_AUDIO'], 'VoIP 통화', (msg) => {
            setVoipInitError(msg);
            logUiPressProbe('VOIP_START_CALL_BLOCKED_PERMISSION', { permission: 'RECORD_AUDIO' });
        });
        if (!hasPermission) {
            return;
        }

        setVoipInitLoading(true);
        setVoipInitError('');
        emitUnifiedTranslationStatus('voip', 'READY', 'VoIP 통번역 통화 세션을 준비합니다.', {
            source: 'handleStartVoipCall',
            phone,
        });
        try {
            logUiPressProbe('VOIP_NETWORK_SNAPSHOT', {
                ...toClientNetworkContext(networkDiagnostics),
                source: 'handleStartVoipCall',
            });
            const payload = await initiateVoipCall({
                callee_phone: phone,
                caller_id: userInfo.username || userInfo.email || 'mobile-demo',
                session_id: bookingResult?.confirmation_id || 'mobile-voip-test-session',
                mode: 'voip_full_auto',
                auto_relay: true,
                caller_preferred_language: currentVoipPreferredLanguage,
                client_network_context: toClientNetworkContext(networkDiagnostics),
            });
            if ((payload as any)?.phone_dialer_required) {
                await handlePhoneOnlyDialFallback(
                    phone,
                    'voip_initiate_phone_dialer_required',
                    (payload as any)?.user_message,
                );
                return;
            }
            setVoipActiveProfile(buildVoipRemoteProfile(
                (payload as any)?.display_label || (payload as any)?.callee_voice_id || phone,
                (payload as any)?.callee_voice_id,
                (payload as any)?.display_country_code,
                (payload as any)?.display_language,
            ));
            setVoipPhone((payload as any)?.display_label || (payload as any)?.callee_voice_id || phone);
            setVoipCallInitResponse(payload as CallInitResponse);
            if ((payload as any)?.call_id) {
                setVoipAuditCallId((payload as any).call_id);
                await refreshVoipAudit((payload as any).call_id);
            }
            logUiPressProbe('VOIP_START_CALL_SUCCESS', {
                call_id: (payload as any)?.call_id ?? null,
                signaling_server: (payload as any)?.signaling_server ?? null,
                turn_servers_count: Array.isArray((payload as any)?.turn_servers) ? (payload as any).turn_servers.length : null,
            });
            emitUnifiedTranslationStatus('voip', 'INFO', 'VoIP 통번역 세션이 연결되었습니다.', {
                source: 'handleStartVoipCall',
                call_id: (payload as any)?.call_id ?? null,
            });
        } catch (error: any) {
            setVoipInitError(error?.message || 'VoIP 테스트 시작 실패');
            emitUnifiedTranslationStatus('voip', 'ERROR', error?.message || 'VoIP 테스트 시작 실패', {
                source: 'handleStartVoipCall',
            });
            logUiPressProbe('VOIP_START_CALL_FAIL', {
                error: error?.message || 'VoIP 테스트 시작 실패',
            });
        } finally {
            setVoipInitLoading(false);
        }
    }, [bookingResult?.confirmation_id, buildVoipRemoteProfile, currentVoipPreferredLanguage, emitUnifiedTranslationStatus, ensureVoipPremiumAccess, handlePhoneOnlyDialFallback, initiateVoipCall, logUiPressProbe, networkDiagnostics, requestPermissions, selectedCallMode, token, userInfo, validatePhoneNumber, voipPhone, voipValidationOverride]);

    const handleCloseVoipTester = useCallback(() => {
        setPendingIncomingVoipCall(null);
        setVoipCallInitResponse(null);
        setVoipInitError('');
        setVoipStatusMessage('');
        setVoipInitLoading(false);
        setVoipActiveProfile(null);
        setVoipAuditCallId('');
        setVoipAuditEvents([]);
        setVoipAuditError('');
        setVoipValidationOverride(false);
        setShowVoipTester(false);
    }, []);

    const handleReturnToVoipDialer = useCallback((auditEvents?: CallModeAuditEvent[]) => {
        if (auditEvents) {
            setVoipAuditEvents(auditEvents);
            setVoipAuditError('');
        }
        setIncomingVoipAcceptInFlight(null);
        acceptedIncomingVoipCallIdRef.current = null;
        stopIncomingVoipAlert('return_to_voip_dialer');
        setPendingIncomingVoipCall(null);
        if (voipCallInitResponse?.participant_role === 'callee') {
            setVoipCallInitResponse(null);
            setVoipInitError('');
            setVoipStatusMessage('');
            setVoipInitLoading(false);
            setVoipActiveProfile(null);
            setShowVoipTester(false);
            return;
        }
        setVoipCallInitResponse(null);
        setVoipInitError('');
        setVoipStatusMessage('');
        setVoipInitLoading(false);
        setVoipActiveProfile(null);
        setShowVoipTester(true);
    }, [setIncomingVoipAcceptInFlight, stopIncomingVoipAlert, voipCallInitResponse?.participant_role]);

    const handleAcceptIncomingVoipCall = useCallback(async (sourceVariant: string = 'unknown') => {
        if (!pendingIncomingVoipCall) {
            return;
        }

        const acceptedPayload = pendingIncomingVoipCall;

        acceptedIncomingVoipCallIdRef.current = acceptedPayload.call_id;
        setIncomingVoipAcceptInFlight(acceptedPayload.call_id);
        const alertWasActive = incomingVoipAlertActiveRef.current;
        stopIncomingVoipAlert('manual_accept_tap');
        logUiPressProbe('VOIP_INCOMING_ACCEPT_HANDLER_START', {
            source_variant: sourceVariant,
            call_id: acceptedPayload.call_id,
            caller_voice_id: acceptedPayload.caller_voice_id ?? null,
            pending_call_id: pendingIncomingVoipCallRef.current?.call_id ?? null,
            active_call_id: voipCallInitResponseRef.current?.call_id ?? null,
            accepting_call_id: acceptingIncomingVoipCallIdRef.current,
        });
        logUiPressProbe('VOIP_INCOMING_ALERT_STOPPED_ON_ACCEPT_TAP', {
            call_id: acceptedPayload.call_id,
            caller_voice_id: acceptedPayload.caller_voice_id ?? null,
            alert_was_active: alertWasActive,
        });

        const hasPermission = await requestPermissions(['RECORD_AUDIO'], 'VoIP 수신 통화', (msg) => {
            setVoipInitError(msg);
            logUiPressProbe('VOIP_INCOMING_CALL_ACCEPT_BLOCKED_PERMISSION', {
                permission: 'RECORD_AUDIO',
                call_id: acceptedPayload.call_id,
            });
        });
        if (!hasPermission) {
            setIncomingVoipAcceptInFlight(null);
            return;
        }

        logUiPressProbe('VOIP_INCOMING_ACCEPT_PERMISSION_GRANTED', {
            call_id: acceptedPayload.call_id,
            caller_voice_id: acceptedPayload.caller_voice_id ?? null,
        });

        let mergedAcceptedPayload: CallInitResponse & { caller_label?: string; caller_voice_id?: string } = {
            ...acceptedPayload,
            participant_role: 'callee',
        };

        if (token) {
            try {
                const acceptedFromServer = await acceptIncomingCall(API_BASE, token, acceptedPayload.call_id);
                const callerLanguageHint = resolveVoipRemoteLanguageHint(
                    acceptedPayload.display_language,
                    pendingIncomingVoipCallRef.current?.display_language,
                    acceptedFromServer.display_language,
                );
                mergedAcceptedPayload = {
                    ...acceptedPayload,
                    ...acceptedFromServer,
                    participant_role: 'callee',
                    caller_label: acceptedPayload.caller_label,
                    caller_voice_id: acceptedPayload.caller_voice_id ?? acceptedFromServer.caller_voice_id,
                    display_language: callerLanguageHint ?? acceptedFromServer.display_language,
                };
                logUiPressProbe('VOIP_INCOMING_ACCEPT_API_OK', {
                    call_id: mergedAcceptedPayload.call_id,
                    display_language: mergedAcceptedPayload.display_language ?? null,
                    signaling_server: mergedAcceptedPayload.signaling_server ?? null,
                    status: mergedAcceptedPayload.status ?? null,
                });
            } catch (acceptError: any) {
                const snapshot = await fetchVoipCallResumeSnapshot(API_BASE, token, acceptedPayload.call_id);
                logUiPressProbe('VOIP_INCOMING_ACCEPT_API_FAIL', {
                    call_id: acceptedPayload.call_id,
                    error_message: acceptError?.message || 'unknown',
                    snapshot_call_id: snapshot?.call_id ?? null,
                    snapshot_status: snapshot?.status ?? null,
                });
                if (!snapshot?.call_id || !isResumableIncomingVoipStatus(snapshot.status)) {
                    setIncomingVoipAcceptInFlight(null);
                    dismissPendingIncomingAsMissed('manual_accept', 'call_no_longer_active', acceptedPayload);
                    return;
                }
                mergedAcceptedPayload = {
                    ...acceptedPayload,
                    ...snapshot,
                    participant_role: 'callee',
                    caller_label: acceptedPayload.caller_label,
                    caller_voice_id: acceptedPayload.caller_voice_id ?? snapshot.caller_voice_id,
                };
            }
        }

        logUiPressProbe('VOIP_INCOMING_ALERT_STOPPED_ON_ACCEPT', {
            call_id: mergedAcceptedPayload.call_id,
            caller_voice_id: mergedAcceptedPayload.caller_voice_id ?? null,
        });

        activateAcceptedIncomingVoipCall(mergedAcceptedPayload, 'manual_accept');
    }, [API_BASE, activateAcceptedIncomingVoipCall, dismissPendingIncomingAsMissed, logUiPressProbe, pendingIncomingVoipCall, requestPermissions, setIncomingVoipAcceptInFlight, stopIncomingVoipAlert, token]);

    const handleIncomingAcceptPress = useCallback((sourceVariant: string) => {
        logUiPressProbe('VOIP_INCOMING_ACCEPT_ON_PRESS', {
            source_variant: sourceVariant,
            pending_call_id: pendingIncomingVoipCallRef.current?.call_id ?? null,
            active_call_id: voipCallInitResponseRef.current?.call_id ?? null,
        });
        void handleAcceptIncomingVoipCall(sourceVariant);
    }, [handleAcceptIncomingVoipCall, logUiPressProbe]);

    const handleRejectIncomingVoipCall = useCallback(async () => {
        if (!pendingIncomingVoipCall) {
            return;
        }

        logUiPressProbe('VOIP_INCOMING_CALL_REJECTED', {
            call_id: pendingIncomingVoipCall.call_id,
            caller_voice_id: pendingIncomingVoipCall.caller_voice_id ?? null,
        });

        stopIncomingVoipAlert('manual_reject');
        if (token) {
            try {
                await fetch(`${API_BASE}/api/v1/voip/calls/${pendingIncomingVoipCall.call_id}/end`, {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        duration_sec: 0,
                        call_quality: 'rejected',
                    }),
                });
            } catch (error) {
                console.warn('[VoIP] Failed to reject incoming call cleanly', error);
            }
        }

        setPendingIncomingVoipCall(null);
        acceptedIncomingVoipCallIdRef.current = null;
        setIncomingVoipAcceptInFlight(null);
        setVoipCallInitResponse(null);
        setVoipInitError('');
        setVoipInitLoading(false);
        setVoipActiveProfile(null);
        setVoipAuditCallId('');
        setVoipAuditEvents([]);
        setVoipAuditError('');
        setShowVoipTester(false);
    }, [pendingIncomingVoipCall, logUiPressProbe, setIncomingVoipAcceptInFlight, stopIncomingVoipAlert, token]);

    const fetchActiveVoipCallResume = useCallback(async (source: string) => {
        if (!token || !userInfo || pendingIncomingVoipCallRef.current || voipCallInitResponseRef.current || voipCallInitiatingRef.current || acceptingIncomingVoipCallRef.current) {
            return;
        }

        try {
            const storedSession = await loadStoredActiveVoipSession();
            const lastCallId = storedSession?.callId ?? null;
            const restoredRailSection: SectionRailKey = 'voip';
            const query = lastCallId ? `?last_call_id=${encodeURIComponent(lastCallId)}` : '';
            const response = await fetch(`${API_BASE}/api/v1/voip/calls/active-current${query}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    await clearStoredActiveVoipSession();
                    logUiPressProbe('VOIP_ACTIVE_CALL_RESUME_SKIPPED_AUTH', {
                        source,
                        status: response.status,
                        last_call_id: lastCallId,
                    });
                    return;
                }
                throw new Error(`활성 통화 복구 실패 (HTTP ${response.status})`);
            }

            const payload = await response.json();
            if (pendingIncomingVoipCallRef.current || voipCallInitResponseRef.current || acceptingIncomingVoipCallRef.current) {
                return;
            }
            if (!payload?.call_id) {
                await clearStoredActiveVoipSession();
                return;
            }

            if (isTerminalVoipStatus(payload.status)) {
                await clearStoredActiveVoipSession();
                logUiPressProbe('VOIP_ACTIVE_CALL_RESUME_SKIPPED_TERMINAL_STATUS', {
                    source,
                    call_id: payload.call_id,
                    participant_role: payload.participant_role ?? null,
                    status: payload.status ?? null,
                });
                return;
            }

            if (payload.participant_role === 'caller') {
                await clearStoredActiveVoipSession();
                return;
            }

            const isStoredAcceptedSession = payload.participant_role === 'callee'
                ? isRuntimeAcceptedCalleeVoipSession(storedSession, payload.call_id, acceptedIncomingVoipCallIdRef.current)
                : storedSession?.callId === payload.call_id;
            const shouldDeferActiveResumeToAccept = payload.participant_role === 'callee'
                && shouldDeferCalleeResumeToIncomingAccept(payload.status, isStoredAcceptedSession);
            // 이 단말이 명시적으로 '받기'한 적 없는 callee 통화가 connecting/active 로 복구되려 하면
            // 자동 응답(손 안 댔는데 받아짐)의 원인이 된다. 단, 여기서 서버에 종료(requestEndVoipCall)를
            // 호출하면 '실제로 걸려오는 통화'까지 끊어버려 받기/거절 팝업이 안 뜨고 못 받는 회귀가 난다.
            // 그러므로 **로컬 복구만 건너뛰고(자동응답 차단)** 통화 자체는 살려둔다. 실제 착신이면
            // pending 폴링/푸시가 ringing 으로 받기/거절 UI를 띄우고, 발신자 종료 시엔 취소푸시/폴링이
            // 벨을 멈추고 부재중 처리한다.
            if (
                payload.participant_role === 'callee'
                && !isStoredAcceptedSession
                && (payload.status === 'connecting' || payload.status === 'active')
            ) {
                await clearStoredActiveVoipSession();
                logUiPressProbe('VOIP_ACTIVE_CALL_RESUME_SKIPPED_UNACCEPTED', {
                    source,
                    call_id: payload.call_id,
                    participant_role: payload.participant_role ?? null,
                    status: payload.status ?? null,
                });
                return;
            }
            if (shouldDeferActiveResumeToAccept) {
                await clearStoredActiveVoipSession();
                logUiPressProbe('VOIP_ACTIVE_CALL_RESUME_DEFERRED_TO_ACCEPT', {
                    source,
                    call_id: payload.call_id,
                    participant_role: payload.participant_role ?? null,
                    status: payload.status ?? null,
                });
                applyIncomingVoipPayload(payload as CallInitResponse, `${source}_pending_accept`);
                return;
            }

            logUiPressProbe('VOIP_ACTIVE_CALL_RESTORED', {
                source,
                call_id: payload.call_id,
                participant_role: payload.participant_role ?? null,
                status: payload.status ?? null,
                restored_rail_section: restoredRailSection,
            });
            setCallMode(resolveCallModeFromPayload(payload as Partial<CallInitResponse>));
            setVoipCallInitResponse(payload as CallInitResponse);
            setActiveRailSection('voip');
            setShowVoipTester(true);
            setPendingIncomingVoipCall(null);
            setVoipInitError('');
            setVoipAuditCallId(payload.call_id);
            await saveStoredActiveVoipSession(
                payload.call_id,
                'voip',
                payload.participant_role === 'caller' || payload.participant_role === 'callee' ? payload.participant_role : null,
            );
            await refreshVoipAudit(payload.call_id);
        } catch (error: any) {
            console.log('[VoIP][Diag] Active call resume skipped', {
                source,
                message: error instanceof Error ? error.message : String(error),
            });
        }
    }, [API_BASE, applyIncomingVoipPayload, logUiPressProbe, pendingIncomingVoipCall, refreshVoipAudit, setCallMode, token, userInfo, voipCallInitResponse]);

    const restoreVoipRailState = useCallback((source: string) => {
        if (!pendingIncomingVoipCall && !voipCallInitResponse) {
            return;
        }

        const restoredRailSection: SectionRailKey = 'voip';

        logUiPressProbe('VOIP_RAIL_STATE_RESTORE', {
            source,
            active_call_id: voipCallInitResponse?.call_id ?? null,
            pending_call_id: pendingIncomingVoipCall?.call_id ?? null,
            accepting_call_id: acceptingIncomingVoipCallIdRef.current,
            active_section: restoredRailSection,
        });
        setShowFriendFolder(false);
        setShowFriendMapDiscovery(false);
        setVoipAutoCallVoiceId(null);
        setActiveRailSection('voip');
        setIsRailMenuOpen(false);
        setShowVoipTester(true);
    }, [logUiPressProbe, pendingIncomingVoipCall, voipCallInitResponse]);

    const handleCloseFriendFolder = useCallback((source: string) => {
        setShowFriendFolder(false);
        setVoipAutoCallVoiceId(null);
        setVoipValidationOverride(false);
        voipValidationFriendCallBypassRef.current = false;
        void persistVoipValidationFriendCallBypass(false);
        logUiPressProbe('FRIEND_FOLDER_CLOSE', { source });
        if (voipCallInitResponseRef.current || pendingIncomingVoipCallRef.current) {
            restoreVoipRailState(`friend_folder_close_${source}`);
        }
    }, [logUiPressProbe, persistVoipValidationFriendCallBypass, restoreVoipRailState]);

    const handleStartFriendVoiceCall = useCallback(async (friend: Friend) => {  // NOSONAR
        if (!token || !userInfo) {
            setShowLogin(true);
            return;
        }

        const persistedValidationFriendCallBypass = await AsyncStorage.getItem(VOIP_VALIDATION_FRIEND_CALL_BYPASS_KEY);
        const validationFriendCallBypass = voipValidationFriendCallBypassRef.current || persistedValidationFriendCallBypass === '1';
        const allowValidationOverride = voipValidationOverride
            || validationFriendCallBypass
            || Boolean(voipAutoCallVoiceId)
            || showFriendFolder
            || showVoipTester;

        const hasPremium = await ensureVoipPremiumAccess(
            'handleStartFriendVoiceCall',
            allowValidationOverride,
        );
        if (!hasPremium) {
            return;
        }

        if (validationFriendCallBypass) {
            voipValidationFriendCallBypassRef.current = false;
            void persistVoipValidationFriendCallBypass(false);
        }

        if (!friend.friendUserId && !friend.friendVoiceId) {
            Alert.alert('ID 연결 필요', '보이스톡은 앱 보이스 ID 또는 사용자 ID가 있는 대상만 연결할 수 있습니다.');
            return;
        }

        const hasPermission = await requestPermissions(['RECORD_AUDIO'], 'VoIP 통화', (msg) => {
            setVoipInitError(msg);
            logUiPressProbe('VOIP_FRIEND_CALL_BLOCKED_PERMISSION', { permission: 'RECORD_AUDIO' });
        });
        if (!hasPermission) {
            return;
        }

        const dispatchKey = `${friend.id}:${friend.friendVoiceId ?? friend.friendUserId ?? 'unknown'}`;
        const dispatchNow = Date.now();
        if (
            friendCallDispatchKeyRef.current === dispatchKey
            && dispatchNow - friendCallDispatchAtRef.current < 8000
        ) {
            logUiPressProbe('VOIP_FRIEND_CALL_DISPATCH_SUPPRESSED', {
                friend_id: friend.id,
                friend_voice_id: friend.friendVoiceId ?? null,
                dispatch_key: dispatchKey,
            });
            return;
        }
        friendCallDispatchKeyRef.current = dispatchKey;
        friendCallDispatchAtRef.current = dispatchNow;

        setVoipInitLoading(true);
        setVoipInitError('');
        setShowFriendFolder(false);
        setActiveRailSection('voip');
        setShowVoipTester(true);
        voipCallInitiatingRef.current = true;
        setVoipPhone(friend.friendUsername || friend.friendVoiceId || friend.friendPhone || '친구 보이스톡');
        setVoipActiveProfile({
            nickname: friend.friendUsername || '친구',
            genderLabel: formatDiscoveryGenderLabel(friend.friendGender),
            countryCode: friend.friendCountryCode || 'UN',
            countryName: friend.friendCountryCode ? resolveCountryName(friend.friendCountryCode) : '국가 미상',
            voiceId: friend.friendVoiceId || `friend-${friend.id}`,
            countryFlag: friend.friendCountryFlag || (friend.friendCountryCode ? resolveCountryFlag(friend.friendCountryCode) : '🌐'),
            preferredLanguage: friend.friendPreferredLanguage || voipAutoCallCalleeLanguageRef.current || undefined,
        });

        try {
            logUiPressProbe('VOIP_NETWORK_SNAPSHOT', {
                ...toClientNetworkContext(networkDiagnostics),
                source: 'handleStartFriendVoiceCall',
                friend_id: friend.id,
            });
            const payload = await initiateVoipCall({
                callee_phone: friend.friendPhone,
                callee_user_id: friend.friendUserId ?? undefined,
                callee_voice_id: friend.friendVoiceId ?? undefined,
                friend_id: friend.id,
                caller_id: userInfo.username || userInfo.email || 'mobile-demo',
                session_id: bookingResult?.confirmation_id || `friend-voice-${friend.id}`,
                mode: 'voip_full_auto',
                auto_relay: true,
                caller_preferred_language: currentVoipPreferredLanguage,
                callee_preferred_language: friend.friendPreferredLanguage || voipAutoCallCalleeLanguageRef.current || undefined,
                client_network_context: toClientNetworkContext(networkDiagnostics),
            });
            if ((payload as any)?.phone_dialer_required) {
                setVoipInitError((payload as any)?.user_message || '보이스톡은 더 이상 전화번호 다이얼 패드를 사용하지 않습니다.');
                setShowVoipTester(false);
                Alert.alert('ID 연결 필요', (payload as any)?.user_message || '앱 보이스 ID 대상만 보이스톡을 시작할 수 있습니다.');
                return;
            }
            if ((payload as any)?.status === 'callee_offline') {
                setVoipInitError((payload as any)?.user_message || '상대 앱이 아직 응답하지 않았습니다. 앱이 열리면 자동으로 통화가 이어집니다.');
                logUiPressProbe('VOIP_FRIEND_CALL_PENDING_DELIVERY', {
                    friend_id: friend.id,
                    call_id: (payload as any)?.call_id ?? null,
                    callee_voice_id: friend.friendVoiceId ?? null,
                });
            }
            setVoipCallInitResponse(payload as CallInitResponse);
            const resolvedCalleeLanguage = String(
                (payload as any)?.display_language
                || friend.friendPreferredLanguage
                || voipAutoCallCalleeLanguageRef.current
                || '',
            ).trim().toLowerCase();
            if (resolvedCalleeLanguage) {
                setVoipActiveProfile((prev) => (prev ? {
                    ...prev,
                    preferredLanguage: resolvedCalleeLanguage,
                } : prev));
            }
            if ((payload as any)?.call_id) {
                setVoipAuditCallId((payload as any).call_id);
                await refreshVoipAudit((payload as any).call_id);
            }
            logUiPressProbe('VOIP_FRIEND_CALL_SUCCESS', {
                friend_id: friend.id,
                call_id: (payload as any)?.call_id ?? null,
                callee_voice_id: friend.friendVoiceId ?? null,
            });
            setVoipAutoCallVoiceId(null);
            voipAutoCallCalleeLanguageRef.current = null;
            setVoipValidationOverride(false);
            if (friend.friendVoiceId) {
                consumedValidationAutoCallKeyRef.current = `validation:${friend.friendVoiceId.trim().toLowerCase()}`;
            }
        } catch (error: any) {
            setVoipInitError(error?.message || '친구 보이스톡 시작 실패');
            setShowVoipTester(false);
            setVoipActiveProfile(null);
            Alert.alert('보이스톡 실패', error?.message || '친구 보이스톡 시작 실패');
            logUiPressProbe('VOIP_FRIEND_CALL_FAIL', {
                friend_id: friend.id,
                error: error?.message || '친구 보이스톡 시작 실패',
            });
        } finally {
            voipCallInitiatingRef.current = false;
            setVoipInitLoading(false);
        }
    }, [bookingResult?.confirmation_id, currentVoipPreferredLanguage, ensureVoipPremiumAccess, initiateVoipCall, logUiPressProbe, networkDiagnostics, persistVoipValidationFriendCallBypass, refreshVoipAudit, requestPermissions, showFriendFolder, showVoipTester, token, userInfo, voipAutoCallVoiceId, voipValidationOverride]);

    const handleFriendAcceptedFromDiscovery = useCallback(async (payload?: AcceptedFriendActionPayload) => {
        setShowFriendMapDiscovery(false);
        setActiveRailSection('chat');
        setChatRefreshKey((prev) => prev + 1);

        if (!payload || payload.action === 'friend-folder') {
            setSelectedChatRoom(null);
            setShowFriendFolder(true);
            logUiPressProbe('FRIEND_DISCOVERY_ACCEPT_FLOW', {
                action: payload?.action ?? 'friend-folder',
                friend_id: payload?.friend.id ?? null,
                friend_user_id: payload?.friend.friendUserId ?? null,
            });
            return;
        }

        if (payload.action === 'chat') {
            if (!token || !payload.friend.friendUserId) {
                setSelectedChatRoom(null);
                setShowFriendFolder(true);
                return;
            }

            try {
                const room = await createDirectChatRoom(API_BASE, token, payload.friend.friendUserId);
                setSelectedChatRoom(room);
                setShowFriendFolder(false);
                logUiPressProbe('FRIEND_DISCOVERY_ACCEPT_CHAT_OPENED', {
                    friend_id: payload.friend.id,
                    friend_user_id: payload.friend.friendUserId,
                    room_id: room.room_id,
                });
            } catch (error: any) {
                setSelectedChatRoom(null);
                setShowFriendFolder(true);
                Alert.alert('채팅 열기 실패', error?.message || '친구 채팅방을 열지 못했습니다.');
            }
            return;
        }

        setSelectedChatRoom(null);
        setShowFriendFolder(false);
        logUiPressProbe('FRIEND_DISCOVERY_ACCEPT_VOIP_START', {
            friend_id: payload.friend.id,
            friend_user_id: payload.friend.friendUserId ?? null,
            friend_voice_id: payload.friend.friendVoiceId ?? null,
        });
        await handleStartFriendVoiceCall(payload.friend);
    }, [handleStartFriendVoiceCall, logUiPressProbe, token]);

    useEffect(() => {
        if (!pendingIncomingVoipCall && !voipCallInitResponse) {
            return;
        }

        const appStateSubscription = AppState.addEventListener('change', (nextState) => {
            if (nextState === 'active') {
                restoreVoipRailState('app_state_active_restore');
            }
        });

        return () => {
            appStateSubscription.remove();
        };
    }, [pendingIncomingVoipCall, restoreVoipRailState, voipCallInitResponse]);

    useEffect(() => {
        pendingIncomingVoipCallRef.current = pendingIncomingVoipCall;
        voipCallInitResponseRef.current = voipCallInitResponse;
    }, [pendingIncomingVoipCall, voipCallInitResponse]);

    useEffect(() => {
        if (!token || !userInfo || pendingIncomingVoipCall || voipCallInitResponse) {
            return;
        }

        void fetchActiveVoipCallResume('app_launch_resume');
        const appStateSubscription = AppState.addEventListener('change', (nextState) => {
            if (nextState === 'active') {
                void fetchActiveVoipCallResume('app_state_resume');
            }
        });

        return () => {
            appStateSubscription.remove();
        };
    }, [fetchActiveVoipCallResume, pendingIncomingVoipCall, token, userInfo, voipCallInitResponse]);

    useEffect(() => {
        if (voipCallInitResponse?.call_id) {
            const acceptedParticipantRole = voipCallInitResponse.participant_role === 'caller'
                ? 'caller'
                : voipCallInitResponse.participant_role === 'callee' && acceptedIncomingVoipCallIdRef.current === voipCallInitResponse.call_id
                    ? 'callee'
                    : null;
            void saveStoredActiveVoipSession(voipCallInitResponse.call_id, 'voip', acceptedParticipantRole);
            return;
        }
        void clearStoredActiveVoipSession();
    }, [voipCallInitResponse?.call_id]);

    const handleSearchNearby = useCallback(async () => {
        if (!lat.trim() || !lon.trim()) {
            setNearbyError('위도와 경도를 입력해 주세요.');
            return;
        }
        setNearbyLoading(true);
        setNearbyError('');
        setBookingResult(null);
        setBookingSelectionNotice('');
        clearBookingSelectionNoticeTimer();
        try {
            const places = await callNearbyPlacesApi({
                lat,
                lon,
                category: nearbyCategory,
                radiusM,
                targetLang: toLang,
            });
            setNearbyPlaces(places);
            setSelectedNearbyPlaceId(places[0]?.id || '');
            // [버그 수정] 구조화 예약(POST /bookings)은 호텔 카테고리만 백엔드가 허용한다.
            // 과거엔 '전화번호 있는 첫 장소'(식당/명소/공항)까지 예약 장소로 지정해 제출 시 항상 400 이 났다.
            // → 구조화 예약 선택은 '예약 가능 호텔'만 지정한다(없으면 미선택 → 예약 폼/배너 비활성).
            //   주변검색만으로 통화 입력란에 번호를 채우는 동작은 아래 bookingAutoFillPhone 효과가 별도로 담당한다.
            const firstBookableHotel = places.find(
                (place) => place.category === 'hotel' && place.booking_supported,
            );
            setSelectedBookingPlaceId(firstBookableHotel?.id || '');
            if (!places.length) {
                setNearbyError('현재 반경에서 찾은 장소가 없습니다. 반경을 넓혀 보세요.');
            }
        } catch (e: any) {
            setNearbyPlaces([]);
            setSelectedNearbyPlaceId('');
            setSelectedBookingPlaceId('');
            setNearbyError(e?.message || '주변검색 중 오류가 발생했습니다.');
        } finally {
            setNearbyLoading(false);
        }
    }, [clearBookingSelectionNoticeTimer, lat, lon, nearbyCategory, radiusM, toLang]);

    const handleNearbyMapMessage = useCallback((event: WebViewMessageEvent) => {
        let payload: { type?: string; action?: string; placeId?: string; googleMapsUrl?: string } | null = null;
        try {
            payload = JSON.parse(event.nativeEvent.data);
        } catch {
            return;
        }
        if (!payload || payload.type !== 'nearby-map-action' || !payload.placeId) {
            return;
        }

        setSelectedNearbyPlaceId(payload.placeId);
        if (payload.action === 'route' && payload.googleMapsUrl) {
            if (Platform.OS === 'android') {
                ToastAndroid.show('Google 지도로 이동합니다.', ToastAndroid.SHORT);
            }
            void Linking.openURL(payload.googleMapsUrl);  // NOSONAR
            return;
        }
        if (payload.action === 'book') {
            selectBookingPlace(payload.placeId, '지도', true);
        }
    }, [selectBookingPlace]);

    const handleReserveBooking = useCallback(async () => {
        logUiPressProbe('TRAVEL_BOOKING_SUBMIT_PRESS', {
            selected_place_id: selectedBookingPlace?.id ?? null,
            selected_place_name: selectedBookingPlace?.name ?? null,
            booking_name_filled: Boolean(bookingName.trim()),
            checkin_date: checkinDate || null,
            checkout_date: checkoutDate || null,
            guests,
            room_count: roomCount,
        });
        if (!selectedBookingPlace) {
            setBookingError('예약할 장소(호텔/공항)를 먼저 선택하세요.');
            return;
        }
        if (!token) {
            setShowLogin(true);
            setBookingError('예약은 로그인 후 사용할 수 있습니다.');
            return;
        }
        if (!bookingName.trim() || !checkinDate || !checkoutDate) {
            setBookingError('예약자명과 체크인/체크아웃 날짜를 입력하세요.');
            return;
        }
        setBookingLoading(true);
        setBookingError('');
        setBookingResult(null);
        try {
            const payload = await callBookingApi(token, {
                placeId: selectedBookingPlace.id,
                customerName: bookingName.trim(),
                checkinDate,
                checkoutDate,
                guests,
                roomCount,
                note: bookingNote,
                targetLang: toLang,
            });
            setBookingResult(payload);
            logUiPressProbe('TRAVEL_BOOKING_SUBMIT_SUCCESS', {
                selected_place_id: selectedBookingPlace.id,
                confirmation_id: payload.confirmation_id,
                support_phone: payload.support_phone || null,
            });
        } catch (e: any) {
            setBookingError(e?.message || '예약 요청에 실패했습니다.');
            logUiPressProbe('TRAVEL_BOOKING_SUBMIT_FAIL', {
                selected_place_id: selectedBookingPlace.id,
                message: e?.message || '예약 요청에 실패했습니다.',
            });
        } finally {
            setBookingLoading(false);
        }
    }, [selectedBookingPlace, token, bookingName, checkinDate, checkoutDate, guests, roomCount, bookingNote, toLang, logUiPressProbe]);

    const handlePayment = useCallback(async () => {
        if (!bookingResult || !selectedBookingPlace) {
            setPayError('예약을 먼저 완료해 주세요.');
            return;
        }
        if (!token) {
            setShowLogin(true);
            setPayError('결제는 로그인 후 사용할 수 있습니다.');
            return;
        }
        setPayLoading(true);
        setPayError('');
        try {
            const nights = Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000));
            const amount = nights * roomCount * 80000;
            const purchase = await callCreatePurchaseApi(token, amount);
            setPurchaseResult(purchase);
            const payData = await callInitiatePaymentApi(token, purchase.id);
            setPayUrl(payData.payment_url);
            if (payData.payment_url) {
                await Linking.openURL(payData.payment_url);
            }
        } catch (e: any) {
            setPayError(e?.message || '결제 초기화에 실패했습니다.');
        } finally {
            setPayLoading(false);
        }
    }, [bookingResult, selectedBookingPlace, token, checkinDate, checkoutDate, roomCount]);

    const getLangLabel = useCallback((code: LangCode) => {
        return LANGS.find((l) => l.code === code)?.label ?? code;
    }, []);

    const withTimeout = useCallback(async <T,>(promise: Promise<T>, ms: number): Promise<T> => {
        let timeoutHandle: ReturnType<typeof setTimeout> | null = null;
        const timeoutPromise = new Promise<T>((_, reject) => {
            timeoutHandle = setTimeout(() => reject(new Error('gps-timeout')), ms);
        });
        try {
            return await Promise.race([promise, timeoutPromise]);
        } finally {
            if (timeoutHandle) {
                clearTimeout(timeoutHandle);
            }
        }
    }, []);

    const appendGpsDebugTrace = useCallback(async (event: string, payload: Record<string, unknown> = {}) => {
        if (!__DEV__) {
            return;
        }

        const entry = JSON.stringify({
            ts: new Date().toISOString(),
            event,
            ...payload,
        });

        console.log('[GPS_DEBUG_TRACE]', entry);

        try {
            const info = await FileSystem.getInfoAsync(GPS_DEBUG_TRACE_FILE_PATH);
            const prefix = info.exists ? '\n' : '';
            await FileSystem.writeAsStringAsync(GPS_DEBUG_TRACE_FILE_PATH, `${prefix}${entry}`, {
                encoding: FileSystem.EncodingType.UTF8,
            });
        } catch {
        }
    }, []);

    const resolveHybridLocation = useCallback(async (): Promise<HybridGpsResult> => {
        const attemptId = `${Date.now()}-${nextNonceTag()}`;

        const persistSuccessfulLocation = async (result: HybridGpsResult) => {
            if (result.source === 'adb_override') {
                return;
            }

            try {
                await AsyncStorage.setItem(
                    GPS_PERSISTED_FALLBACK_KEY,
                    serializePersistedGpsSnapshot({
                        latitude: result.latitude,
                        longitude: result.longitude,
                        accuracy: result.accuracy,
                        overrideCountryCode: result.overrideCountryCode,
                        overrideRegionHint: result.overrideRegionHint,
                        recordedAt: Date.now(),
                    }),
                );
                await appendGpsDebugTrace('persisted-location-saved', {
                    attemptId,
                    source: result.source,
                    accuracy: result.accuracy,
                    latitude: result.latitude,
                    longitude: result.longitude,
                });
            } catch (error: any) {
                await appendGpsDebugTrace('persisted-location-save-error', {
                    attemptId,
                    source: result.source,
                    message: error?.message ?? String(error),
                });
            }
        };

        const getPersistedFallback = async (servicesEnabled: boolean): Promise<HybridGpsResult | null> => {
            try {
                const rawSnapshot = await AsyncStorage.getItem(GPS_PERSISTED_FALLBACK_KEY);
                const persistedSnapshot = parsePersistedGpsSnapshot(rawSnapshot);
                if (!persistedSnapshot) {
                    await appendGpsDebugTrace('persisted-location-miss', {
                        attemptId,
                        servicesEnabled,
                        hasRawSnapshot: Boolean(rawSnapshot),
                    });
                    return null;
                }

                await appendGpsDebugTrace('persisted-location-hit', {
                    attemptId,
                    servicesEnabled,
                    latitude: persistedSnapshot.latitude,
                    longitude: persistedSnapshot.longitude,
                    accuracy: persistedSnapshot.accuracy,
                    recordedAt: persistedSnapshot.recordedAt,
                });
                return {
                    latitude: persistedSnapshot.latitude,
                    longitude: persistedSnapshot.longitude,
                    accuracy: persistedSnapshot.accuracy,
                    mode: 'wifi_fallback',
                    qualityScore: scoreLocationQuality(persistedSnapshot.accuracy),
                    source: 'persisted_last_success',
                    servicesEnabled,
                    overrideCountryCode: persistedSnapshot.overrideCountryCode,
                    overrideRegionHint: persistedSnapshot.overrideRegionHint,
                };
            } catch (error: any) {
                await appendGpsDebugTrace('persisted-location-error', {
                    attemptId,
                    servicesEnabled,
                    message: error?.message ?? String(error),
                });
                return null;
            }
        };

        const traceLastKnownSnapshot = async (phase: string, servicesEnabled: boolean) => {
            try {
                const snapshot = await Location.getLastKnownPositionAsync({
                    maxAge: 30 * 60 * 1000,
                    requiredAccuracy: 3000,
                });
                await appendGpsDebugTrace('last-known-snapshot', {
                    attemptId,
                    phase,
                    servicesEnabled,
                    hasSnapshot: Boolean(snapshot),
                    latitude: snapshot?.coords.latitude ?? null,
                    longitude: snapshot?.coords.longitude ?? null,
                    accuracy: snapshot?.coords.accuracy ?? null,
                    mocked: snapshot?.mocked ?? null,
                    timestamp: snapshot?.timestamp ?? null,
                });
            } catch (error: any) {
                await appendGpsDebugTrace('last-known-snapshot-error', {
                    attemptId,
                    phase,
                    servicesEnabled,
                    message: error?.message ?? String(error),
                });
            }
        };

        const getAdbLocationOverride = async (): Promise<HybridGpsResult | null> => {
            if (Platform.OS !== 'android') {
                return null;
            }

            try {
                const info = await FileSystem.getInfoAsync(ADB_GPS_OVERRIDE_PATH);
                if (!info.exists) {
                    await appendGpsDebugTrace('adb-override-miss', { attemptId, path: ADB_GPS_OVERRIDE_PATH });
                    return null;
                }

                const raw = await FileSystem.readAsStringAsync(ADB_GPS_OVERRIDE_PATH);
                const parsed = JSON.parse(raw) as {
                    latitude?: number | string;
                    longitude?: number | string;
                    accuracy?: number | string;
                    countryCode?: string;
                    regionHint?: string;
                };
                const latitude = Number(parsed.latitude);
                const longitude = Number(parsed.longitude);
                if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
                    return null;
                }

                const accuracy = Number.isFinite(Number(parsed.accuracy)) ? Number(parsed.accuracy) : 5;
                await appendGpsDebugTrace('adb-override-hit', {
                    attemptId,
                    latitude,
                    longitude,
                    accuracy,
                    countryCode: parsed.countryCode ?? null,
                    regionHint: parsed.regionHint ?? null,
                });
                return {
                    latitude,
                    longitude,
                    accuracy,
                    mode: detectHybridGpsMode(accuracy),
                    qualityScore: scoreLocationQuality(accuracy),
                    source: 'adb_override',
                    servicesEnabled: true,
                    overrideCountryCode: typeof parsed.countryCode === 'string' ? parsed.countryCode.trim().toUpperCase() : undefined,
                    overrideRegionHint: typeof parsed.regionHint === 'string' ? parsed.regionHint.trim().toLowerCase() : undefined,
                };
            } catch (error: any) {
                await appendGpsDebugTrace('adb-override-error', {
                    attemptId,
                    message: error?.message ?? String(error),
                });
                return null;
            }
        };

        const getMockLocationSample = async (
            accuracy: Location.LocationAccuracy,
            source: HybridGpsResult['source'],
            timeoutMs: number,
            mayShowUserSettingsDialog: boolean,
            servicesEnabled: boolean,
        ): Promise<HybridGpsResult | null> => {
            if (Platform.OS !== 'android') {
                return null;
            }

            let timeoutHandle: ReturnType<typeof setTimeout> | null = null;
            let subscription: Location.LocationSubscription | null = null;

            try {
                return await new Promise<HybridGpsResult | null>((resolve) => {
                    let settled = false;
                    const finish = (value: HybridGpsResult | null) => {
                        if (settled) {
                            return;
                        }
                        settled = true;
                        if (timeoutHandle) {
                            clearTimeout(timeoutHandle);
                            timeoutHandle = null;
                        }
                        subscription?.remove();
                        resolve(value);
                    };

                    timeoutHandle = setTimeout(() => finish(null), timeoutMs);

                    void Location.watchPositionAsync(
                        {
                            accuracy,
                            distanceInterval: 0,
                            timeInterval: 0,
                            mayShowUserSettingsDialog,
                        },
                        (position) => {
                            if (!position.mocked) {
                                return;
                            }

                            const sampledAccuracy = position.coords.accuracy ?? null;
                            void appendGpsDebugTrace('mock-location-sample', {
                                attemptId,
                                source,
                                servicesEnabled,
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: sampledAccuracy,
                            });
                            finish({
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: sampledAccuracy,
                                mode: detectHybridGpsMode(sampledAccuracy),
                                qualityScore: scoreLocationQuality(sampledAccuracy),
                                source,
                                servicesEnabled,
                            });
                        },
                    )
                        .then((nextSubscription) => {
                            subscription = nextSubscription;
                        })
                        .catch(() => finish(null));
                });
            } finally {
                if (timeoutHandle) {
                    clearTimeout(timeoutHandle);
                }
            }
        };

        const getLastKnownFallback = async (servicesEnabled: boolean): Promise<HybridGpsResult | null> => {
            try {
                const last = await Location.getLastKnownPositionAsync({
                    maxAge: 30 * 60 * 1000,
                    requiredAccuracy: 3000,
                });
                if (last) {
                    const lastAccuracy = last.coords.accuracy ?? null;
                    await appendGpsDebugTrace('last-known-hit', {
                        attemptId,
                        servicesEnabled,
                        latitude: last.coords.latitude,
                        longitude: last.coords.longitude,
                        accuracy: lastAccuracy,
                        timestamp: last.timestamp,
                        mocked: last.mocked ?? null,
                    });
                    return {
                        latitude: last.coords.latitude,
                        longitude: last.coords.longitude,
                        accuracy: lastAccuracy,
                        mode: 'wifi_fallback',
                        qualityScore: scoreLocationQuality(lastAccuracy),
                        source: 'last_known',
                        servicesEnabled,
                    };
                }
                await appendGpsDebugTrace('last-known-miss', {
                    attemptId,
                    servicesEnabled,
                });
            } catch (error: any) {
                await appendGpsDebugTrace('last-known-error', {
                    attemptId,
                    servicesEnabled,
                    message: error?.message ?? String(error),
                });
            }
            return getPersistedFallback(servicesEnabled);
        };

        await appendGpsDebugTrace('resolve-start', { attemptId, platform: Platform.OS });

        const adbOverride = await getAdbLocationOverride();
        if (adbOverride) {
            await appendGpsDebugTrace('resolve-return', {
                attemptId,
                source: adbOverride.source,
                mode: adbOverride.mode,
                accuracy: adbOverride.accuracy,
            });
            return adbOverride;
        }

        const servicesEnabled = await Location.hasServicesEnabledAsync();
        await appendGpsDebugTrace('services-enabled', { attemptId, servicesEnabled });
        if (!servicesEnabled) {
            await traceLastKnownSnapshot('services-disabled-before-fallback', false);
            const lastFallback = await getLastKnownFallback(false);
            if (lastFallback) {
                await appendGpsDebugTrace('resolve-return', {
                    attemptId,
                    source: lastFallback.source,
                    mode: lastFallback.mode,
                    accuracy: lastFallback.accuracy,
                });
                return lastFallback;
            }
            await appendGpsDebugTrace('resolve-throw', {
                attemptId,
                reason: 'gps-services-disabled',
            });
            throw new Error('gps-services-disabled');
        }

        // 1) 위성(GNSS) 우선 고정밀 시도
        try {
            const mockedHigh = await getMockLocationSample(Location.Accuracy.Highest, 'gps_high', 2200, false, servicesEnabled);
            if (mockedHigh) {
                await persistSuccessfulLocation(mockedHigh);
                return mockedHigh;
            }
            const p1 = await withTimeout(
                Location.getCurrentPositionAsync({
                    accuracy: Location.Accuracy.Highest,
                    mayShowUserSettingsDialog: false,
                }),
                9000,
            );
            const accuracy = p1.coords.accuracy ?? null;
            await appendGpsDebugTrace('current-position-success', {
                attemptId,
                source: 'gps_high',
                accuracy,
                latitude: p1.coords.latitude,
                longitude: p1.coords.longitude,
                timestamp: p1.timestamp,
            });
            await traceLastKnownSnapshot('after-gps-high-success', servicesEnabled);
            const gpsHighResult: HybridGpsResult = {
                latitude: p1.coords.latitude,
                longitude: p1.coords.longitude,
                accuracy,
                mode: detectHybridGpsMode(accuracy),
                qualityScore: scoreLocationQuality(accuracy),
                source: 'gps_high',
                servicesEnabled,
            };
            await persistSuccessfulLocation(gpsHighResult);
            return gpsHighResult;
        } catch (error: any) {
            await appendGpsDebugTrace('current-position-error', {
                attemptId,
                source: 'gps_high',
                message: error?.message ?? String(error),
            });
            // no-op: 다음 단계로 폴백
        }

        // 2) 하이브리드(네트워크+GNSS 보조) 표준 정밀 시도
        try {
            const mockedBalanced = await getMockLocationSample(Location.Accuracy.Balanced, 'gps_balanced', 1800, false, servicesEnabled);
            if (mockedBalanced) {
                await persistSuccessfulLocation(mockedBalanced);
                return mockedBalanced;
            }
            const p2 = await withTimeout(
                Location.getCurrentPositionAsync({
                    accuracy: Location.Accuracy.Balanced,
                    mayShowUserSettingsDialog: false,
                }),
                7000,
            );
            const accuracy = p2.coords.accuracy ?? null;
            await appendGpsDebugTrace('current-position-success', {
                attemptId,
                source: 'gps_balanced',
                accuracy,
                latitude: p2.coords.latitude,
                longitude: p2.coords.longitude,
                timestamp: p2.timestamp,
            });
            await traceLastKnownSnapshot('after-gps-balanced-success', servicesEnabled);
            const gpsBalancedResult: HybridGpsResult = {
                latitude: p2.coords.latitude,
                longitude: p2.coords.longitude,
                accuracy,
                mode: detectHybridGpsMode(accuracy),
                qualityScore: scoreLocationQuality(accuracy),
                source: 'gps_balanced',
                servicesEnabled,
            };
            await persistSuccessfulLocation(gpsBalancedResult);
            return gpsBalancedResult;
        } catch (error: any) {
            await appendGpsDebugTrace('current-position-error', {
                attemptId,
                source: 'gps_balanced',
                message: error?.message ?? String(error),
            });
            // no-op: 다음 단계로 폴백
        }

        // 3) 저전력/네트워크 제공자까지 허용해 실내 Wi-Fi 환경에서 마지막 실시간 시도
        try {
            const mockedLow = await getMockLocationSample(Location.Accuracy.Lowest, 'gps_low', 1800, true, servicesEnabled);
            if (mockedLow) {
                await persistSuccessfulLocation(mockedLow);
                return mockedLow;
            }
            const p3 = await withTimeout(
                Location.getCurrentPositionAsync({
                    accuracy: Location.Accuracy.Lowest,
                    mayShowUserSettingsDialog: true,
                }),
                5000,
            );
            const accuracy = p3.coords.accuracy ?? null;
            await appendGpsDebugTrace('current-position-success', {
                attemptId,
                source: 'gps_low',
                accuracy,
                latitude: p3.coords.latitude,
                longitude: p3.coords.longitude,
                timestamp: p3.timestamp,
            });
            await traceLastKnownSnapshot('after-gps-low-success', servicesEnabled);
            const gpsLowResult: HybridGpsResult = {
                latitude: p3.coords.latitude,
                longitude: p3.coords.longitude,
                accuracy,
                mode: 'wifi_fallback',
                qualityScore: scoreLocationQuality(accuracy),
                source: 'gps_low',
                servicesEnabled,
            };
            await persistSuccessfulLocation(gpsLowResult);
            return gpsLowResult;
        } catch (error: any) {
            await appendGpsDebugTrace('current-position-error', {
                attemptId,
                source: 'gps_low',
                message: error?.message ?? String(error),
            });
            // no-op: 마지막 위치 폴백으로 진행
        }

        // 4) WF(와이파이/기지국) 기반 마지막 위치 폴백
        await traceLastKnownSnapshot('before-final-fallback', true);
        const lastFallback = await getLastKnownFallback(true);
        if (lastFallback) {
            await persistSuccessfulLocation(lastFallback);
            await appendGpsDebugTrace('resolve-return', {
                attemptId,
                source: lastFallback.source,
                mode: lastFallback.mode,
                accuracy: lastFallback.accuracy,
            });
            return lastFallback;
        }
        await appendGpsDebugTrace('resolve-throw', {
            attemptId,
            reason: 'gps-unavailable',
        });
        throw new Error('gps-unavailable');
    }, [appendGpsDebugTrace, withTimeout]);

    const handleDetectLangByGPS = useCallback(async (silent = false) => {  // NOSONAR
        setGpsLangLoading(true);
        if (!silent) setGpsStatus('위치 권한 확인 중...');
        try {
            const currentPermission = await Location.getForegroundPermissionsAsync();
            let finalPermission = currentPermission;
            if (currentPermission.status !== 'granted') {
                if (silent) return;
                finalPermission = await Location.requestForegroundPermissionsAsync();
            }

            if (finalPermission.status !== 'granted') {
                const deniedMessage = finalPermission.canAskAgain === false
                    ? `위치 권한이 차단되어 있습니다. Android 설정에서 ${WORLDLINGO_APP_NAME} 위치 권한을 허용해 주세요.`
                    : '현재 위치 확인과 주변 서비스 검색을 위해 위치 권한이 필요합니다.';
                setGpsStatus(`위치 권한 미허용 · ${deniedMessage}`);
                if (!silent) {
                    Alert.alert('위치 권한 필요', deniedMessage, [
                        ...(finalPermission.canAskAgain === false ? [{ text: '설정 열기', onPress: () => Linking.openSettings() }] : []),
                        { text: '확인', style: 'cancel' },
                    ]);
                }
                return;
            }

            setGpsStatus('GPS/Wi-Fi/기지국 위치 확인 중...');
            const resolved = await resolveHybridLocation();
            setLat(resolved.latitude.toFixed(6));
            setLon(resolved.longitude.toFixed(6));
            setGpsAccuracyM(Number.isFinite(Number(resolved.accuracy)) ? Number(resolved.accuracy) : null);
            const coordinateFallback = resolveGpsCoordinateFallback(resolved.latitude, resolved.longitude);
            let countryCode = resolved.overrideCountryCode ?? coordinateFallback?.countryCode ?? '';
            let regionHint = resolved.overrideRegionHint ?? coordinateFallback?.regionHint ?? '';
            if (!countryCode || !regionHint) {
                try {
                    const geocoded = await withTimeout(
                        Location.reverseGeocodeAsync({
                            latitude: resolved.latitude,
                            longitude: resolved.longitude,
                        }),
                        4000,
                    );
                    const geocodedAddress = geocoded?.[0] ?? null;
                    if (!countryCode) {
                        countryCode = (geocodedAddress?.isoCountryCode ?? '').toUpperCase() || coordinateFallback?.countryCode || '';
                    }
                    if (!regionHint) {
                        regionHint = countryCode
                            ? resolveGpsDialectRegionHint(countryCode, geocodedAddress) ?? ''
                            : '';
                        if (!regionHint) {
                            regionHint = coordinateFallback?.regionHint ?? '';
                        }
                    }
                } catch {
                    if (!countryCode) {
                        countryCode = coordinateFallback?.countryCode ?? '';
                    }
                    if (!regionHint) {
                        regionHint = coordinateFallback?.regionHint ?? '';
                    }
                }
            }
            setGpsCountryCode(countryCode);
            setGpsRegionHint(regionHint);
            const detectedLang = countryCode ? resolveLangFromCountry(countryCode) : null;
            const profileLangRaw = String(userInfo?.preferred_language || fromLang).trim().toLowerCase();
            const profileLang = isSupportedLangCode(profileLangRaw) ? profileLangRaw as LangCode : fromLang;
            if (detectedLang && isSupportedLangCode(detectedLang) && detectedLang !== profileLang) {
                setToLang(detectedLang);
            }
            const modeLabel =
                resolved.mode === 'satellite'
                    ? 'Satellite GPS'
                    : resolved.mode === 'hybrid'
                        ? 'Hybrid GPS/Wi-Fi'
                        : resolved.mode === 'wifi_fallback'
                            ? 'WF Fallback'
                            : resolved.source === 'adb_override'
                                ? 'ADB Mock GPS'
                                : 'Cached Wi-Fi/Cell';
            const accText = resolved.accuracy !== null ? `${resolved.accuracy.toFixed(0)}m` : 'N/A';
            const langText = detectedLang ? ` · 추천 ${getLangLabel(detectedLang)}` : '';
            const regionText = regionHint ? ` · 지역 ${regionHint}` : '';

            setGpsStatus(`${modeLabel} · 품질 ${resolved.qualityScore}점 · 정확도 ${accText} · 좌표 ${resolved.latitude.toFixed(5)}, ${resolved.longitude.toFixed(5)} · 국가 ${countryCode || 'UNKNOWN'}${langText}${regionText}`);
        } catch (error: any) {
            setGpsCountryCode('');
            setGpsRegionHint('');
            const reason = error?.message === 'gps-services-disabled'
                ? '단말 위치 서비스가 꺼져 있고 저장된 마지막 위치도 없습니다.'
                : error?.message === 'gps-unavailable'
                    ? 'GPS/Wi-Fi/기지국 제공자에서 현재 위치와 마지막 위치를 모두 받지 못했습니다.'
                    : '위치 제공자 응답 시간이 초과되었거나 단말 위치 제공자가 응답하지 않았습니다.';
            setGpsStatus(`위치 확인 실패 · ${reason}`);
            if (!silent) {
                Alert.alert('위치 확인 실패', `${reason}\n\nAndroid 위치 서비스와 앱 위치 권한을 확인한 뒤 다시 눌러 주세요.`);
            }
        } finally {
            setGpsLangLoading(false);
        }
    }, [fromLang, getLangLabel, resolveHybridLocation, userInfo?.preferred_language]);

    useEffect(() => {
        if (Platform.OS !== 'web') {
            void handleDetectLangByGPS(true);
        }
    }, [handleDetectLangByGPS]);

    useEffect(() => {
        const preferred = String(userInfo?.preferred_language || '').trim().toLowerCase();
        if (!isSupportedLangCode(preferred)) {
            return;
        }
        setFromLang(preferred);
        setToLang((currentTarget) => (
            currentTarget !== preferred ? currentTarget : resolveAutoTargetLang(preferred, currentTarget)
        ));
    }, [userInfo?.preferred_language]);

    const speakWithLang = useCallback((text: string, langCode: LangCode) => {
        const speakText = normalizeSpeakText(text);
        if (!speakText) return;
        const lang = LANGS.find((l) => l.code === langCode);
        const fallbackTts = lang?.tts ?? 'ko-KR';
        Speech.speak(speakText, { language: fallbackTts, rate: 0.9 });
    }, []);

    const clearAutoVoiceTimers = useCallback(() => {
        if (autoVoiceStopTimerRef.current) {
            clearTimeout(autoVoiceStopTimerRef.current);
            autoVoiceStopTimerRef.current = null;
        }
        if (autoVoiceRestartTimerRef.current) {
            clearTimeout(autoVoiceRestartTimerRef.current);
            autoVoiceRestartTimerRef.current = null;
        }
        void faceVadControllerRef.current.stop();  // NOSONAR
    }, []);

    const resolveInterCallDirection = useCallback((turn: 'from' | 'to') => {
        const listenLang = turn === 'from' ? fromLang : toLang;
        const translateTo = turn === 'from' ? toLang : fromLang;
        return {
            listenLang,
            translateTo,
            listenLabel: getLangLabel(listenLang),
            translateLabel: getLangLabel(translateTo),
        };
    }, [fromLang, getLangLabel, toLang]);

    const commitInterCallRelay = useCallback((turn: 'from' | 'to', spokenText: string, translatedText: string, options: { isAutoRelay?: boolean } = {}) => {
        const { translateTo, translateLabel } = resolveInterCallDirection(turn);
        const relayKey = `${turn}:${normalizeRelayText(spokenText)}`;
        setInterCallLog((prev) => [...prev.slice(-19), { turn, text: spokenText, translated: translatedText }]);
        emitUnifiedTranslationStatus('pstn', 'SPEAK', `${translateLabel} 송출`, {
            turn,
            translate_to: translateTo,
            auto_relay: Boolean(options.isAutoRelay),
        });
        speakWithLang(translatedText, translateTo);
        setInterCallTurn(turn === 'from' ? 'to' : 'from');
        setInterManualText('');
        if (options.isAutoRelay) {
            interLastAutoRelayRef.current = { key: relayKey, sentAt: Date.now() };
        }
    }, [emitUnifiedTranslationStatus, resolveInterCallDirection, speakWithLang]);

    // ── BT 하이브리드 음성 입력 ──
    // BT 이어폰 연결 시 → Android MODE_IN_COMMUNICATION → SCO 자동 활성화 → 이어폰 MIC 사용
    // BT 이어폰 미연결 시 → 폰 내장 MIC 사용 (현재 동작 그대로 유지)
    const startVoiceInput = useCallback(async (options: { autoMode?: boolean; target?: 'main' | 'inter_call' } = {}) => {
        if (voiceInputStartInFlightRef.current || voiceInputStopInFlightRef.current || recordingRef.current) {
            return;
        }
        voiceInputStartInFlightRef.current = true;
        const effectiveAutoMode = Boolean(options.autoMode);
        const inputTarget = options.target ?? 'main';
        try {
            voiceInputTargetRef.current = inputTarget;
            // 반이중 가드: 통역/소리새 음성을 출력하는 동안에는 듣기를 시작하지 않는다(발화↔듣기 겹침 방지).
            if (effectiveAutoMode && inputTarget === 'main' && (faceSpeakingRef.current || sorisaeSpeakingRef.current)) {
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'capture_blocked_speaking' }));
                scheduleFaceConversationRestartRef.current(null);
                return;
            }
            if (Platform.OS === 'web') {
                const webAny = globalThis as any;
                const speechCtor = webAny.window?.SpeechRecognition || webAny.window?.webkitSpeechRecognition;
                if (!speechCtor) {
                    Alert.alert('마이크 지원 불가', '현재 브라우저는 음성 인식을 지원하지 않습니다. Chrome 또는 Edge 최신 버전을 사용해 주세요.');
                    return;
                }

                const recognizer = new speechCtor();
                const listenTts = LANGS.find((l) => l.code === fromLang)?.tts ?? 'en-US';
                recognizer.lang = listenTts;
                recognizer.interimResults = false;
                recognizer.maxAlternatives = 1;

                webSpeechRecognitionRef.current = recognizer;
                setIsVoiceRecording(true);
                setVoiceSttLoading(true);

                recognizer.onresult = async (event: any) => {
                    const transcript = String(event?.results?.[0]?.[0]?.transcript ?? '').trim();
                    setVoiceSttLoading(false);
                    setIsVoiceRecording(false);
                    webSpeechRecognitionRef.current = null;
                    if (!transcript) return;

                    const detectedFrom = inferSpeechLangCode(transcript, fromLang);
                    setFromLang(detectedFrom);
                    setInputText(transcript);
                    await runTranslation(transcript, detectedFrom, toLang);
                };

                recognizer.onerror = (event: any) => {
                    const detail = event?.error ? `브라우저 음성 인식 오류(${event.error})` : '브라우저 음성 인식 오류';
                    console.error('[VOICE_INPUT_START_ERROR_WEB]', event);
                    setVoiceSttLoading(false);
                    setIsVoiceRecording(false);
                    webSpeechRecognitionRef.current = null;
                    setGpsStatus(`🎤 음성 입력 실패: ${detail}`);
                    Alert.alert('녹음 오류', detail);
                };

                recognizer.onend = () => {
                    setVoiceSttLoading(false);
                    setIsVoiceRecording(false);
                    webSpeechRecognitionRef.current = null;
                };

                recognizer.start();
                return;
            }

            // Per-feature 권한 체크: 마이크 (음성 입력)
            const hasPermission = await requestPermissions(['RECORD_AUDIO'], '음성 입력', (msg) => {
                setGpsStatus(`🎤 음성 입력 실패: ${msg}`);
            });
            if (!hasPermission) {
                if (effectiveAutoMode && autoVoiceModeEnabledRef.current && inputTarget === 'main') {
                    autoVoiceRestartTimerRef.current = setTimeout(() => {
                        if (autoVoiceModeEnabledRef.current && !recordingRef.current) {
                            void startVoiceInput({ autoMode: true });
                        }
                    }, FACE_CONVERSATION_PERMISSION_RETRY_MS);
                }
                return;
            }

            // Android: playThroughEarpieceAndroid: false → STREAM_VOICE_CALL 경로 → BT HFP SCO 자동 활성화
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                staysActiveInBackground: false,
                shouldDuckAndroid: false,
                playThroughEarpieceAndroid: false,
            });
            const isFaceConversationCapture = effectiveAutoMode && inputTarget === 'main' && autoVoiceModeEnabledRef.current;
            // [2-5 AEC/NS] 대면·스피커폰 자동 통역 capture는 OEM 하드웨어 음향 에코 제거(AEC)+
            // 노이즈 억제(NS)가 필요하다. AudioManager.MODE_IN_COMMUNICATION 은 AudioRecord 생성
            // *이전* 에 설정돼야 활성화되므로 createAsync 직전에 적용한다(setAudioModeAsync 이후 재적용).
            // 효과: 자기 스피커로 낸 통역 TTS를 자기 마이크가 다시 줍는 '핑퐁 자기에코'를 하드웨어에서 상쇄.
            if (effectiveAutoMode) {
                try {
                    await enableVoipAudio(true, false);
                    faceVoipAudioEnabledRef.current = true;
                } catch {
                    // 네이티브 모듈 미가용/실패 시 무시(소프트웨어 가드로 폴백).
                }
            }
            const { recording } = await Audio.Recording.createAsync({
                android: {
                    extension: '.m4a',
                    outputFormat: Audio.AndroidOutputFormat.MPEG_4,
                    audioEncoder: Audio.AndroidAudioEncoder.AAC,
                    sampleRate: 16_000,
                    numberOfChannels: 1,
                    bitRate: 32_000,
                },
                ios: {
                    extension: '.m4a',
                    audioQuality: Audio.IOSAudioQuality.MEDIUM,
                    sampleRate: 16_000,
                    numberOfChannels: 1,
                    bitRate: 32_000,
                    linearPCMBitDepth: 16,
                    linearPCMIsBigEndian: false,
                    linearPCMIsFloat: false,
                },
                web: Audio.RecordingOptionsPresets.HIGH_QUALITY.web,
                isMeteringEnabled: isFaceConversationCapture || (effectiveAutoMode && inputTarget !== 'main'),
                keepAudioActiveHint: false,
            });
            recordingRef.current = recording;
            if (inputTarget === 'main') {
                // [기능 분리 Phase1] 라우팅 스냅샷: 이 세그먼트의 목적지(소리새 vs 대면통역)를
                // 캡처 시작 시점에 고정한다. 이후 창이 열리고 닫혀도 이번 세그먼트는 처음 결정대로 처리.
                mainSorisaeRouteRef.current = !songModeEnabled && sorisaeWindowOpenRef.current;
            }
            // [기능 분리 Phase2] 마이크 단일 소유 lease 획득(R1). 모든 음성 캡처가 거치는 단일 지점.
            // 다른 음성 기능이 캡처 중이었다면 그 기능은 revoke 콜백으로 자동 정지된다(동시 점유 차단).
            {
                const leaseFeature: VoiceCaptureFeatureId =
                    inputTarget === 'inter_call'
                        ? 'inter_call'
                        : songModeEnabled
                        ? 'song'
                        : sorisaeWindowOpenRef.current
                        ? 'sorisae'
                        : 'face';
                acquireVoiceCapture(leaseFeature, () => {
                    void stopVoiceInputRef.current?.({ suppressAutoRestart: true });
                    if (leaseFeature === 'inter_call') {
                        setInterCallVoiceAssistEnabled(false);
                    } else if (leaseFeature === 'song') {
                        setSongModeEnabled(false);
                    } else {
                        setAutoVoiceModeEnabled(false);
                    }
                });
            }
            setIsVoiceRecording(true);
            if (effectiveAutoMode) {
                clearAutoVoiceTimers();
                const isFaceConversation = inputTarget === 'main' && autoVoiceModeEnabledRef.current;
                if (inputTarget === 'inter_call') {
                    setInterCallStatus(`🎙️ 스피커폰 통역 보조 수신 중... ${formatAutoRelayDelayLabel(autoRelayDelayMs)} 후 자동 처리합니다.`);
                } else if (isFaceConversation) {
                    setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                    await faceVadControllerRef.current.start({
                        recording,
                        onFlush: (reason) => {
                            console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'vad_end', reason }));
                            void stopVoiceInputRef.current?.();
                        },
                        isStillActive: () => autoVoiceModeEnabledRef.current
                            && voiceInputTargetRef.current === 'main'
                            && Boolean(recordingRef.current),
                    });
                    // [Silero 근본 무음 게이트] expo 녹음과 병행으로 Silero 네이티브 VAD+PCM 캡처를 가동.
                    // 무음 세그먼트(speech_start 미발생/실제 RMS 낮음)는 stopVoiceInput에서 전송 차단된다.
                    // 미지원/실패 시 조용히 폴백(기존 expo m4a + file-growth VAD 그대로).
                    faceSileroActiveRef.current = false;
                    faceSileroCaptureActiveRef.current = false;
                    faceSileroCaptureUriRef.current = null;
                    faceSileroFirstSpeechAtMsRef.current = null;
                    if (faceSileroSupportedRef.current) {
                        try {
                            const monitorStarted = await startVoiceRelaySileroVadMonitor();
                            if (monitorStarted) {
                                faceSileroActiveRef.current = true;
                                if (isVoiceRelaySileroCaptureAvailable()) {
                                    const captureStarted = await beginVoiceRelaySileroCapture();
                                    if (captureStarted) {
                                        const baseDir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory ?? '';
                                        faceSileroCaptureUriRef.current = `${baseDir}face_silero_${Date.now()}.wav`;
                                        faceSileroCaptureActiveRef.current = true;
                                    }
                                }
                            }
                        } catch {
                            faceSileroActiveRef.current = false;
                            faceSileroCaptureActiveRef.current = false;
                            faceSileroCaptureUriRef.current = null;
                        }
                    }
                } else {
                    setGpsStatus(formatStatusText(getUiText(fromLang).autoVoiceSegmentStatus, { delay: formatAutoRelayDelayLabel(autoRelayDelayMs) }));
                }
                if (!isFaceConversation) {
                    const listenDurationMs = autoRelayDelayMs;
                    autoVoiceStopTimerRef.current = setTimeout(() => {
                        void stopVoiceInputRef.current?.();
                    }, listenDurationMs);
                }
            }
        } catch (error: any) {
            const rawMessage = typeof error?.message === 'string' ? error.message : '';
            const normalized = rawMessage.toLowerCase();
            let detail = rawMessage || '원인 불명';
            if (Platform.OS === 'web') {
                if (normalized.includes('permission') || normalized.includes('denied') || normalized.includes('notallowed')) {
                    detail = '브라우저 마이크 권한이 차단되어 있습니다. 주소창의 사이트 권한에서 마이크를 허용해 주세요.';
                } else if (normalized.includes('notfound') || normalized.includes('device')) {
                    detail = '마이크 장치를 찾지 못했습니다. 입력 장치 연결 상태를 확인해 주세요.';
                } else if (normalized.includes('secure') || normalized.includes('https')) {
                    detail = '보안 컨텍스트가 필요합니다. localhost 또는 HTTPS 환경에서 실행해 주세요.';
                }
            }
            console.error('[VOICE_INPUT_START_ERROR]', error);
            setIsVoiceRecording(false);
            setVoiceSttLoading(false);
            setGpsStatus(`🎤 음성 입력 실패: ${detail}`);
            if (effectiveAutoMode && autoVoiceModeEnabledRef.current && inputTarget === 'main') {
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'capture_start_retry', detail }));
                autoVoiceRestartTimerRef.current = setTimeout(() => {
                    if (autoVoiceModeEnabledRef.current && !recordingRef.current) {
                        void startVoiceInput({ autoMode: true });
                    }
                }, FACE_CONVERSATION_PERMISSION_RETRY_MS);
            } else {
                Alert.alert('녹음 오류', detail);
            }
        } finally {
            voiceInputStartInFlightRef.current = false;
        }
    }, [autoRelayDelayMs, clearAutoVoiceTimers, fromLang, getUiText, requestPermissions, runTranslation, toLang]);

    useEffect(() => {
        autoVoiceModeEnabledRef.current = autoVoiceModeEnabled;
    }, [autoVoiceModeEnabled]);

    useEffect(() => {
        faceAiModeRef.current = faceAiMode;
        // 모드 전환 시 친구 모드 멀티턴 메모리를 초기화해 매번 깨끗한 대화로 시작한다.
        faceGptConversationRef.current = [];
    }, [faceAiMode]);

    useEffect(() => {
        scheduleFaceConversationRestartRef.current = (afterPlayback) => {
            if (!autoVoiceModeEnabledRef.current || recordingRef.current) {
                return;
            }
            clearAutoVoiceTimers();
            const restartDelayMs = getWorldlincoTuning().face_conversation.restart_ms;
            const beginCapture = () => {
                if (!autoVoiceModeEnabledRef.current || recordingRef.current || voiceInputStopInFlightRef.current) {
                    return;
                }
                // 반이중 보장: 아직 통역/소리새 음성이 재생 중(잔향 drain 포함)이면 듣기를 켜지 않고 잠시 후 재확인한다.
                if (faceSpeakingRef.current || sorisaeSpeakingRef.current) {
                    autoVoiceRestartTimerRef.current = setTimeout(beginCapture, 200);
                    return;
                }
                if (voiceInputTargetRef.current === 'main') {
                    void startVoiceInput({ autoMode: true });  // NOSONAR
                }
            };
            const armRestart = () => {
                autoVoiceRestartTimerRef.current = setTimeout(beginCapture, restartDelayMs);
            };
            if (afterPlayback) {
                void Promise.race([
                    afterPlayback,
                    new Promise<void>((resolve) => setTimeout(resolve, getWorldlincoTuning().face_conversation.playback_cap_ms)),
                ]).finally(armRestart);
                return;
            }
            armRestart();
        };
    }, [clearAutoVoiceTimers, startVoiceInput]);

    // voiceSttLoading 상태를 ref에 미러링(워치독 인터벌에서 최신값 읽기용).
    useEffect(() => { voiceSttLoadingRef.current = voiceSttLoading; }, [voiceSttLoading]);

    // [자동 듣기 마이크 워치독] 자동 음성 모드(대면 통역/소리새 대화)에서 한 턴이 끝난 뒤
    // 정상 재시작 타이머가 어떤 이유로든(레이스·예외) 누락되면 마이크가 "끊긴" 채 사용자가 다시
    // 눌러야 하는 번거로움이 생긴다. 이를 막기 위한 백스톱: 파이프라인이 '완전히 유휴'(녹음·시작/정지
    // in-flight·STT 처리·통역/소리새 발화 모두 없음)인 상태가 약 5초간 지속되면 듣기를 자동 재개한다.
    // 정상 흐름은 재시작 지연(restart_ms<1s)이 짧아 5초 연속 유휴가 생기지 않으므로 정상 동작과 충돌하지 않는다.
    useEffect(() => {
        if (Platform.OS === 'web' || !autoVoiceModeEnabled) return undefined;
        let idleTicks = 0;
        const timer = setInterval(() => {
            const fullyIdle = autoVoiceModeEnabledRef.current
                && voiceInputTargetRef.current === 'main'
                && !recordingRef.current
                && !voiceInputStartInFlightRef.current
                && !voiceInputStopInFlightRef.current
                && !voiceSttLoadingRef.current
                && !faceSpeakingRef.current
                && !sorisaeSpeakingRef.current;
            if (!fullyIdle) {
                idleTicks = 0;
                return;
            }
            idleTicks += 1;
            if (idleTicks >= 2) {
                idleTicks = 0;
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'mic_watchdog_recover' }));
                void startVoiceInput({ autoMode: true });
            }
        }, 2500);
        return () => clearInterval(timer);
    }, [autoVoiceModeEnabled, startVoiceInput]);

    // [Silero 근본 무음 게이트] 지원 여부 1회 프로브 + 음성 시작/끝 이벤트 구독.
    // speech_start: 이 세그먼트에 실제 음성이 있었음을 기록(무음 차단의 핵심 신호).
    // speech_end: 말이 끝나면 즉시 flush(자연스러운 문장 경계 컷, file-growth max_duration 대기 불필요).
    useEffect(() => {
        let cancelled = false;
        void probeVoiceRelaySileroVadSupport().then((supported) => {
            if (!cancelled) {
                faceSileroSupportedRef.current = supported;
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'silero_probe', supported }));
            }
        });
        const unsubscribe = subscribeVoiceRelaySileroVadEvents((evt) => {
            if (!faceSileroActiveRef.current || voiceInputTargetRef.current !== 'main') {
                return;
            }
            // 반이중: 소리새/통역 TTS 발화 중에는 VAD 이벤트(자기 음성)를 일절 무시한다.
            if (faceSpeakingRef.current || sorisaeSpeakingRef.current) {
                return;
            }
            if (evt.event === 'speech_start') {
                if (faceSileroFirstSpeechAtMsRef.current == null) {
                    faceSileroFirstSpeechAtMsRef.current = Date.now();
                }
            } else if (evt.event === 'speech_end') {
                // 실제 음성이 한 번이라도 잡힌 뒤의 말 끝에서만 자연 종료 flush.
                if (faceSileroFirstSpeechAtMsRef.current != null && recordingRef.current) {
                    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'vad_end', reason: 'silero_speech_end' }));
                    void stopVoiceInputRef.current?.();
                }
            }
        });
        return () => {
            cancelled = true;
            unsubscribe();
        };
    }, []);

    const stopVoiceInput = useCallback(async (options: { suppressAutoRestart?: boolean } = {}) => {
        if (Platform.OS === 'web') {
            const recognizer = webSpeechRecognitionRef.current;
            if (recognizer) {
                try {
                    recognizer.stop();
                } catch {
                    // no-op
                }
            }
            webSpeechRecognitionRef.current = null;
            setIsVoiceRecording(false);
            setVoiceSttLoading(false);
            return;
        }

        if (voiceInputStopInFlightRef.current || !recordingRef.current) {
            if (
                !voiceInputStopInFlightRef.current
                && !recordingRef.current
                && !options.suppressAutoRestart
                && autoVoiceModeEnabledRef.current
                && voiceInputTargetRef.current === 'main'
            ) {
                scheduleFaceConversationRestartRef.current(null);
            }
            return;
        }
        voiceInputStopInFlightRef.current = true;
        clearAutoVoiceTimers();
        const faceVadSnapshot = autoVoiceModeEnabledRef.current && voiceInputTargetRef.current === 'main'
            ? faceVadControllerRef.current.getSnapshot()
            : null;
        if (faceVadSnapshot) {
            await faceVadControllerRef.current.stop();
        }
        // [Silero 근본 무음 게이트] 현재 세그먼트의 Silero 상태를 고정(stop 이후 ref가 초기화될 수 있으므로).
        const faceSileroActiveSnapshot = faceSileroActiveRef.current;
        const faceSileroCaptureActiveSnapshot = faceSileroCaptureActiveRef.current;
        const faceSileroCaptureUriSnapshot = faceSileroCaptureUriRef.current;
        const faceSileroHadSpeechSnapshot = faceSileroFirstSpeechAtMsRef.current != null;
        if (faceSileroActiveSnapshot) {
            await stopVoiceRelaySileroVadMonitor();
        }
        faceSileroActiveRef.current = false;
        faceSileroCaptureActiveRef.current = false;
        faceSileroCaptureUriRef.current = null;
        faceSileroFirstSpeechAtMsRef.current = null;
        setIsVoiceRecording(false);
        const activeVoiceInputTarget = voiceInputTargetRef.current;
        const shouldAutoRestart = !options.suppressAutoRestart && (
            activeVoiceInputTarget === 'inter_call'
                ? interCallActiveRef.current && interCallVoiceAssistEnabled
                : autoVoiceModeEnabled
        );
        const rec = recordingRef.current;
        recordingRef.current = null;
        try {
            await rec.stopAndUnloadAsync();
            // 오디오 모드 원상복구
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: false,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: true,
                playThroughEarpieceAndroid: false,
            });
            const uri = rec.getURI();
            let facePlaybackPromise: Promise<void> | null = null;
            if (!uri) {
                scheduleFaceConversationRestartRef.current(null);
                return;
            }
            // [Silero 근본 무음 게이트] 네이티브 PCM 캡처가 있으면 실제 RMS로 무음을 전송 전에 차단하고,
            // 무음이 아니면 expo m4a(미터 죽은 기기에선 무음 환각 유발) 대신 네이티브 WAV(정확한 신호)를 업로드한다.
            let uploadUri = uri;
            if (faceSileroCaptureActiveSnapshot && faceSileroCaptureUriSnapshot
                && activeVoiceInputTarget === 'main') {
                try {
                    const nativePath = faceSileroCaptureUriSnapshot.replace(/^file:\/\//, '');
                    const capture = await endVoiceRelaySileroCapture(nativePath);
                    if (capture && capture.byteCount > 0) {
                        // 핵심 신호 = Silero VAD가 이 세그먼트에서 실제 음성(speech_start)을 한 번이라도
                        // 감지했는지. 미감지면 무음/잡음 → Whisper 환각 유발이므로 전송 전에 차단한다.
                        // (RMS 바닥 조건은 약한 실제 발화를 오차단할 수 있어 게이트에 쓰지 않고 로깅만 한다.)
                        if (!faceSileroHadSpeechSnapshot) {
                            console.log('[FACE_CONVERSATION]', JSON.stringify({
                                event: 'segment_skip_silence_silero',
                                had_speech: faceSileroHadSpeechSnapshot,
                                rms_db: Math.round(capture.rmsDb),
                                peak_db: Math.round(capture.peakDb),
                            }));
                            await FileSystem.deleteAsync(faceSileroCaptureUriSnapshot, { idempotent: true }).catch(() => { /* no-op */ });
                            setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                            return;
                        }
                        uploadUri = faceSileroCaptureUriSnapshot;
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'silero_native_capture',
                            rms_db: Math.round(capture.rmsDb),
                            peak_db: Math.round(capture.peakDb),
                            duration_ms: Math.round(capture.durationMs),
                        }));
                    }
                } catch {
                    // 네이티브 캡처 실패 → expo m4a 로 폴백.
                }
            }
            setVoiceSttLoading(true);
            if (autoVoiceModeEnabledRef.current && activeVoiceInputTarget === 'main') {
                setGpsStatus(getUiText(fromLang).faceListenProcessing ?? '🔄 번역·음성 출력 중...');
            }
            try {
                const audioBase64 = await FileSystem.readAsStringAsync(uploadUri, {
                    encoding: FileSystem.EncodingType.Base64,
                });
                if (faceVadSnapshot) {
                    const silentSkip = shouldSkipSilentVoiceRelayStt({
                        peakMeterDb: faceVadSnapshot.peakMeterDb,
                        hasSpeech: faceVadSnapshot.hasSpeech,
                        meterUnavailable: faceVadSnapshot.meterUnavailable,
                        audioBase64,
                    });
                    if (silentSkip.skip) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_skip_silent',
                            reason: silentSkip.reason ?? 'silent',
                            estimated_rms_db: silentSkip.estimatedRmsDb,
                        }));
                        setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                        return;
                    }
                }
                // 반이중 하드가드(최종 방어막): 이 세그먼트를 서버로 보내기 직전에 소리새/통역 TTS가
                // 아직 재생 중(faceSpeakingRef)이면 = 마이크가 자기(또는 상대) 발화 음성을 되잡은 것이므로,
                // 서버로 보내지 않고 즉시 버린다. '발화 중 재녹취 → 텍스트 생성 → 중복 발화' 루프를 원천 차단.
                if (autoVoiceModeEnabledRef.current
                    && activeVoiceInputTarget === 'main'
                    && (faceSpeakingRef.current || sorisaeSpeakingRef.current)) {
                    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'segment_discard_while_speaking' }));
                    setGpsStatus('🔇 발화 중 입력(에코) 무시 · 발화가 끝나면 다시 들어요');
                    return;
                }
                const profileLangRaw = String(userInfo?.preferred_language || fromLang).trim().toLowerCase();
                const profileLang: LangCode = isSupportedLangCode(profileLangRaw) ? profileLangRaw as LangCode : fromLang;
                // 소리새 AI(질문/관광 안내/대화) vs 대면 통역 — 완전 분리.
                // [기능 분리 Phase1] 판정 기준은 처리 시점의 라이브 ref가 아니라 **캡처 시작 시점 스냅샷**
                // (mainSorisaeRouteRef). 세그먼트 처리 중 창이 열리고 닫혀도 경로가 뒤바뀌지 않는다(레이스 차단).
                const isFaceGptMode = !songModeEnabled
                    && activeVoiceInputTarget === 'main'
                    && mainSorisaeRouteRef.current;
                // 채널 분리(V.2) — 통역=face/voice-translate, 친구 모드=voice/friend-chat(경량·독립),
                // 노래 모드=voice/orchestrate. 한쪽 회귀가 다른쪽을 깨뜨리지 못하게 라우트를 격리한다.
                const voiceEndpoint = songModeEnabled
                    ? `${API_BASE}/api/llm/voice/orchestrate`
                    : isFaceGptMode
                    ? `${API_BASE}/api/llm/voice/friend-chat`
                    : `${API_BASE}/api/llm/face/voice-translate`;
                // V.2 ID 백본 — 대면 통역 캡처의 고유 상관 ID를 1회 발급해
                // 기능 ID 자동 매핑→셀프 서빙→전송(딜리버리)→음성 발화 전 구간을 묶는다.
                const faceCorrelationId = newCorrelationId(FEATURE_IDS.faceInterpret);
                const voicePayload = songModeEnabled
                    ? { audio_base64: audioBase64, agent_key: 'reasoner', tts: false }
                    : isFaceGptMode
                    ? {
                        // 친구 모드: STT→친구 페르소나 LLM 답변. 발음은 서버 Edge neural TTS로 답변 언어의
                        // 현지 보이스(ko-KR/ja-JP/zh-CN/en-US 등)로 합성받아 50개국 자연 발음을 보장한다(tts:true).
                        // conversation 으로 멀티턴 맥락을 유지해 자연스러운 친구 대화를 만든다.
                        // 전 세계 여행 안내/찾기 특화 — 현재 GPS 위치를 보내 '여기/근처' 질의를 현지 기준으로 처리.
                        audio_base64: audioBase64,
                        tts: true,
                        language: profileLang,
                        conversation: faceGptConversationRef.current,
                        region_hint: gpsRegionHint || undefined,
                        country_code: gpsCountryCode || undefined,
                        latitude: Number.isFinite(Number(lat)) ? Number(lat) : undefined,
                        longitude: Number.isFinite(Number(lon)) ? Number(lon) : undefined,
                        accuracy_m: gpsAccuracyM != null && Number.isFinite(gpsAccuracyM) ? gpsAccuracyM : undefined,
                        correlation_id: faceCorrelationId,
                        feature_id: FEATURE_IDS.faceInterpret,
                        // [Phase5.8] 진화형 동반자: 온디바이스 누적 페르소나 브리프 주입(없으면 빈 문자열 → 서버 무시).
                        persona_brief: buildPersonaBrief(companionPersonaRef.current) || undefined,
                    }
                    : autoVoiceModeEnabled
                        ? {
                            // 여행 대면 통역 채널(bilingual): 자동 언어 감지 + GPS 힌트
                            audio_base64: audioBase64,
                            mode: 'bilingual',
                            bilingual_mode: true,
                            device_tts: true,
                            lang_a: profileLang,
                            lang_b: toLang,
                            from_lang: profileLang,
                            to_lang: toLang,
                            region_hint: gpsRegionHint || undefined,
                            language: 'auto',
                            correlation_id: faceCorrelationId,
                            feature_id: FEATURE_IDS.faceInterpret,
                        }
                        : {
                            // 대면 화면의 수동 단방향: 지정 언어 고정(designated)
                            audio_base64: audioBase64,
                            mode: 'designated',
                            device_tts: true,
                            from_lang: fromLang,
                            to_lang: toLang,
                            region_hint: gpsRegionHint || undefined,
                            language: fromLang,
                            correlation_id: faceCorrelationId,
                            feature_id: FEATURE_IDS.faceInterpret,
                        };
                const res = await fetch(voiceEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(voicePayload),
                });
                if (res.ok) {
                    const data = await res.json();
                    const transcript = String(data.transcript ?? data.original_text ?? '').trim();
                    const sttTrust = String(data.stt_trust ?? 'high').toLowerCase();
                    console.log('[FACE_CONVERSATION]', JSON.stringify({
                        event: 'segment_response',
                        ok: true,
                        route: isFaceGptMode ? 'sorisae' : 'translate',
                        bilingual: autoVoiceModeEnabledRef.current,
                        stt_trust: sttTrust,
                        transcript: transcript.slice(0, 120),
                        from: data.from ?? null,
                        to: data.to ?? null,
                        translated: String(data.translated ?? '').slice(0, 120),
                    }));
                    // 환각 차단: meter-dead(Tab 등) 기기는 무음/잔향 구간도 STT로 전송되므로,
                    // Whisper no_speech_prob/logprob 기반 신뢰도가 낮으면(=환각) 표시·발화하지 않는다.
                    // 이것이 "대기 중 혼잣말"과 "한국어인데 영문 환각 표기"의 핵심 차단막이다.
                    if (sttTrust === 'low'
                        && autoVoiceModeEnabledRef.current
                        && activeVoiceInputTarget === 'main') {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_skip_low_trust',
                            transcript: transcript.slice(0, 80),
                        }));
                        setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                        return;
                    }
                    // [Phase6.1] 음성 호출 대기(dormant): 통역 스캔 캡처를 '조용한 웨이크워드 감시'로만 쓴다.
                    // 호명("OOOO"/"소리새") 감지 시 소리새를 깨우고, 그 외 발화는 통역/표시/발화 없이 소비한다
                    // (대기 중 주변 대화가 통역되어 튀어나오지 않게 한다). 듣기는 재시작해 계속 감시.
                    if (companionVoiceCallArmedRef.current
                        && !sorisaeWindowOpenRef.current
                        && companionVoiceCallRef.current.phase === 'dormant'
                        && activeVoiceInputTarget === 'main') {
                        if (transcript && matchCompanionWakeWord(transcript, aiDisplayNameRef.current)) {
                            console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
                                event: 'wake',
                                transcript: transcript.slice(0, 60),
                            }));
                            wakeCompanionVoiceCallNowRef.current();
                        } else {
                            console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
                                event: 'scan_idle',
                                transcript: transcript.slice(0, 40),
                            }));
                        }
                        scheduleFaceConversationRestartRef.current(null);
                        return;
                    }
                    if (transcript) {
                        if (isFaceGptMode) {
                            // [Phase6.1] 음성 호출형 대화 중에는 사용자 발화 1건마다 활동시각을 갱신해
                            // 3분 무활동 자동 종료 타이머를 리셋한다(대화가 이어지는 한 잠들지 않음).
                            if (companionVoiceCallRef.current.phase === 'awake') {
                                companionVoiceCallRef.current = markCompanionVoiceCallActivity(
                                    companionVoiceCallRef.current,
                                    Date.now(),
                                );
                            }
                            // 자기에코 차단(무한 자문자답 루프 차단) — 방금 소리새 AI가 발화한 답변을
                            // 마이크가 다시 주워담아 전사된 것이면, 새 답변을 만들지 말고 이번 턴을 버린다.
                            // (영어로 답하다 자기 음성을 되받아 또 말하고… 하는 핑퐁의 근본 차단막.)
                            const echoNowMs = Date.now();
                            const normIncoming = normalizeEchoText(transcript);
                            const recentSpokenEcho = faceGptSpokenEchoRef.current.filter(
                                (e) => echoNowMs - e.atMs < FACE_CONVERSATION_ECHO_GUARD_MS,
                            );
                            faceGptSpokenEchoRef.current = recentSpokenEcho;
                            const isSelfEcho = normIncoming.length >= 4
                                && recentSpokenEcho.some((e) => echoOverlapRatio(e.text, normIncoming) >= 0.7);
                            if (isSelfEcho) {
                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                    event: 'gpt_self_echo_skip',
                                    transcript: transcript.slice(0, 80),
                                }));
                                setGpsStatus(`🐦 ${aiDisplayName} 자기 음성(에코) 무시 · 계속 듣는 중`);
                                // 기존 무-uri 패턴과 동일하게 restart 를 다시 걸어 듣기 루프를 유지한다.
                                scheduleFaceConversationRestartRef.current(null);
                                return;
                            }
                            // [Phase5.9] 온디바이스 메모리 제어 명령("나를 잊어줘"/"~라고 불러줘") 처리.
                            // 발화에서 결정적으로 감지해 단말 페르소나를 직접 갱신한다(서버 미저장, 무회귀).
                            const companionCmd = parseCompanionCommand(transcript);
                            if (companionCmd.type === 'reset') {
                                companionPersonaRef.current = createEmptyPersona();
                                resetPersona().catch(() => {});
                            } else if (companionCmd.type === 'set_name' && companionCmd.name) {
                                const named = setPreferredName(companionPersonaRef.current, companionCmd.name);
                                companionPersonaRef.current = named;
                                savePersona(named).catch(() => {});
                            }
                            // 친구 모드: 번역/에코 로직을 타지 않고 LLM 답변을 그대로 표시 + 음성 출력.
                            const answer = String(data.response_text ?? '').trim();
                            // [기능 분리 Phase1] 소리새는 대면 통역 패널 상태(inputText/resultText/engine)에 쓰지 않는다.
                            // (이 setter들은 자동 번역·자동 TTS 이펙트를 깨워 소리새 발화가 대면 통역으로 새는 원인이었다.)
                            // 소리새 표출은 전용 sorisaeQaLog 로만 한다.
                            // 소리새 AI 발화 중 '여행 일정/장소 찾기' 의도일 때만 패널 입력으로 자동 연결(생성은 사용자 탭).
                            // 일상 잡담·일반 질문은 패널을 건드리지 않는다.
                            if (isTravelItineraryIntent(transcript)) {
                                setItinerarySeedQuery(transcript);
                                setItinerarySeedNonce((n) => n + 1);
                            }
                            if (answer) {
                                // 멀티턴 메모리 갱신: 서버가 누적·정리한 conversation 을 우선 사용,
                                // 없으면 로컬에서 이번 턴을 직접 누적(최근 20개 메시지 유지).
                                const serverConv = Array.isArray(data.conversation) ? data.conversation : null;
                                if (serverConv && serverConv.length) {
                                    faceGptConversationRef.current = serverConv
                                        .filter((m: any) => m && (m.role === 'user' || m.role === 'assistant') && m.content)
                                        .map((m: any) => ({ role: String(m.role), content: String(m.content) }))
                                        .slice(-20);
                                } else {
                                    faceGptConversationRef.current = [
                                        ...faceGptConversationRef.current,
                                        { role: 'user', content: transcript },
                                        { role: 'assistant', content: answer },
                                    ].slice(-20);
                                }
                                // [Phase5.8] 진화형 동반자 기억 갱신(온디바이스, 베스트에포트).
                                // 사용자 발화에서 성격·말투·관심·도메인 습관을 누적한다(응답에는 영향 없음).
                                // 메모리 제어 명령(reset/호칭) 턴은 관심사로 누적하지 않는다.
                                if (companionCmd.type === 'none') {
                                    recordTurn({ transcript, answer, language: profileLang })
                                        .then((p) => { companionPersonaRef.current = p; })
                                        .catch(() => {});
                                }
                                const speakText = normalizeSpeakText(answer);
                                if (speakText) {
                                    // 답변 언어를 추정해(스크립트 기반) 그 나라의 현지 뉴럴 보이스로 발화한다.
                                    // 서버가 보낸 neural 오디오(data.audio_base64)를 우선 재생하고,
                                    // 없으면 답변 언어로 재합성, 그래도 실패하면 단말 TTS로 폴백(playFaceTranslationOutput).
                                    const replyLangCode = inferSpeechLangCode(speakText, profileLang);
                                    // 자기에코 이력 기록 — 이 답변이 마이크로 되돌아오면 다음 턴에서 무시한다.
                                    faceGptSpokenEchoRef.current = [
                                        ...faceGptSpokenEchoRef.current,
                                        { text: normalizeEchoText(answer), atMs: Date.now() },
                                    ].slice(-FACE_CONVERSATION_SPOKEN_HISTORY);
                                    // Q/A 로그(좌=질문/입력언어, 우=답변/출력언어) — 질문·답변·언어를 구분해 표출.
                                    {
                                        const qLangRaw = normalizeDetectedLangCode(data.detected_language) ?? profileLang;
                                        const qSeq = (sorisaeQaSeqRef.current += 1);
                                        setSorisaeQaLog((prev) => [
                                            ...prev,
                                            {
                                                id: qSeq,
                                                question: transcript,
                                                questionLang: String(qLangRaw),
                                                answer,
                                                answerLang: String(replyLangCode),
                                                atMs: Date.now(),
                                            },
                                        ].slice(-50));
                                    }
                                    // 반이중: 친구 답변 발화 중에는 듣기를 멈춘다(자기 음성 재캡처 방지).
                                    // [기능 분리 Phase1] 소리새 전용 speakingRef/재생 핸들 사용(대면통역과 분리).
                                    sorisaeSpeakingRef.current = true;
                                    setGpsStatus(`🐦 ${aiDisplayName} 답변 음성 출력 중 · 듣기 멈춤`);
                                    facePlaybackPromise = playFaceTranslationOutput({
                                        translatedText: answer,
                                        targetLang: replyLangCode,
                                        audioBase64: typeof data.audio_base64 === 'string' ? data.audio_base64 : null,
                                        audioFormat: typeof data.audio_format === 'string' ? data.audio_format : null,
                                        apiBaseUrl: API_BASE,
                                        playbackSoundRef: sorisaeVoicePlaybackSoundRef,
                                        correlationId: typeof data.correlation_id === 'string' ? data.correlation_id : faceCorrelationId,
                                    }).finally(() => {
                                        setTimeout(() => {
                                            sorisaeSpeakingRef.current = false;
                                        }, FACE_CONVERSATION_PLAYBACK_DRAIN_MS);
                                    });
                                } else {
                                    setGpsStatus(`🐦 ${aiDisplayName} 답변 완료`);
                                }
                            } else {
                                setGpsStatus(`🐦 ${aiDisplayName} 응답이 비어 있습니다 · 다시 말씀해 주세요`);
                            }
                        } else if (songModeEnabled) {
                            const filteredLyric = normalizeLyricLine(transcript);
                            if (!isLikelyLyricLine(filteredLyric)) {
                                setSongModeStatus('🎵 가사 구간이 아니거나 배경 노이즈가 커서 이번 구간은 건너뛰었습니다.');
                            } else {
                                const rawDetected = data.detected_language ? String(data.detected_language) : '';
                                const sourceInfo = resolveSongHybridSource(rawDetected, filteredLyric);
                                const targetLang = resolveSongHybridTarget(sourceInfo.lang);
                                const translated = await translateTextWithRegion(
                                    filteredLyric,
                                    sourceInfo.lang,
                                    targetLang,
                                    12000,
                                    { serviceMode: 'lyrics' },
                                );
                                setInputText(filteredLyric);
                                setResultText(translated.translated);
                                setOffline(translated.offline);
                                setEngine(translated.engine);
                                setSongModeStatus(`🎵 가사 자막: ${getLangLabel(sourceInfo.lang)} → ${getLangLabel(targetLang)} · ${sourceInfo.detectedBy === 'voice' ? '음성감지' : sourceInfo.detectedBy === 'script' ? '문자패턴' : '기본값'} 하이브리드`);
                                appendSongSubtitle({
                                    original: filteredLyric,
                                    translated: translated.translated,
                                    source: sourceInfo.lang,
                                    target: targetLang,
                                    repeatCount: 1,
                                    detectedBy: sourceInfo.detectedBy,
                                });
                            }
                        } else if (activeVoiceInputTarget === 'inter_call') {
                            const relayTurn = interCallTurn;
                            const dedupeKey = `${relayTurn}:${normalizeRelayText(transcript)}`;
                            const translatedText = String(data.translated ?? '').trim();
                            if (interLastAutoRelayRef.current && interLastAutoRelayRef.current.key === dedupeKey && Date.now() - interLastAutoRelayRef.current.sentAt < AUTO_RELAY_DUPLICATE_GUARD_MS) {
                                setInterCallStatus(getUiText(fromLang).interAutoRelayDuplicateSkipped);
                            } else if (translatedText) {
                                commitInterCallRelay(relayTurn, transcript, translatedText, { isAutoRelay: true });
                            } else {
                                const { listenLang, translateTo } = resolveInterCallDirection(relayTurn);
                                // [버그 수정] 번역 실패 시 '원문을 상대 언어 음성으로' 송출하던 문제 방지.
                                // 폴백 번역이 비거나(=실패) 동일언어가 아닌데 원문과 똑같으면(=무번역 에코)
                                // TTS 를 생략하고 상태만 알린다. 사용자가 잘못된 언어의 원문 음성을 듣지 않게 한다.
                                let fallbackTranslated = '';
                                try {
                                    const translated = await translateTextWithRegion(
                                        transcript,
                                        listenLang,
                                        translateTo,
                                    );
                                    fallbackTranslated = String(translated.translated ?? '').trim();
                                } catch {
                                    fallbackTranslated = '';
                                }
                                const sameLang = listenLang === translateTo;
                                const looksUntranslated = !sameLang
                                    && !!fallbackTranslated
                                    && normalizeRelayText(fallbackTranslated) === normalizeRelayText(transcript);
                                if (fallbackTranslated && !looksUntranslated) {
                                    commitInterCallRelay(relayTurn, transcript, fallbackTranslated, { isAutoRelay: true });
                                } else {
                                    setInterCallStatus('번역에 실패했습니다. 다시 말씀해 주세요.');
                                }
                            }
                        } else if (autoVoiceModeEnabled) {
                            const translatedText = String(data.translated ?? '').trim();
                            const effectiveFrom: LangCode = normalizeDetectedLangCode(data.from)
                                ?? normalizeDetectedLangCode(data.detected_language)
                                ?? profileLang;
                            const effectiveTo: LangCode = normalizeDetectedLangCode(data.to)
                                ?? (effectiveFrom === profileLang ? toLang : profileLang);
                            const relayKey = `${effectiveFrom}:${effectiveTo}:${normalizeRelayText(transcript)}`;
                            // 핑퐁 에코 차단: 최근 기기가 발화한 통역문/원문이 마이크로 되돌아와
                            // 양방향(lang_a↔lang_b)으로 재번역되는 무한 루프를 끊는다.
                            // STT 왕복 지연으로 에코가 늦게 도착할 수 있어 이력 전체를 가드창 안에서 비교한다.
                            const echoNowMs = Date.now();
                            const recentSpoken = faceSpokenHistoryRef.current.filter(
                                (entry) => echoNowMs - entry.spokenAtMs < FACE_CONVERSATION_ECHO_GUARD_MS,
                            );
                            faceSpokenHistoryRef.current = recentSpoken;
                            let echoCheck: { echo: boolean; reason?: string } = { echo: false };
                            for (const entry of recentSpoken) {
                                const result = isLikelyVoiceRelayEcho({
                                    transcript,
                                    translatedText,
                                    nowMs: echoNowMs,
                                    recentLocalTranslated: entry.translated,
                                    recentLocalSentAtMs: entry.spokenAtMs,
                                    recentRemoteTranscript: entry.transcript,
                                    recentRemoteAtMs: entry.spokenAtMs,
                                    // 대면통역 이력 사전필터와 동일한 25s 창으로 통일(20~25s 에코 누락 방지).
                                    guardWindowMs: FACE_CONVERSATION_ECHO_GUARD_MS,
                                });
                                if (result.echo) {
                                    echoCheck = result;
                                    break;
                                }
                            }
                            const repetitionEcho = isLikelyRepetitionHallucination(transcript)
                                || isLikelyRepetitionHallucination(translatedText);
                            // #1 대기 침묵 중 자가 발화 차단: 무음 구간 Whisper 환각(아웃트로/필러 계열) 차단.
                            // [버그 수정] 과거엔 셰이프만 보고 항상 차단해 '감사합니다/Thank you/안녕하세요' 같은
                            // 실제 핵심 여행 인사말까지 통역 누락됐다. → VAD가 '발화 없음'을 확증할 때만 차단한다.
                            //  - 메터 사용 가능 + hasSpeech=false → 진짜 무음 구간 환각 → 차단(정상)
                            //  - 메터 사용 가능 + hasSpeech=true  → 실제 발화 → 인사말도 통과(수정 핵심)
                            //  - 메터 미가용(Tab 등) → 위의 stt_trust=='low' 게이트가 환각을 이미 거른다.
                            const vadConfirmsSilence = !!faceVadSnapshot
                                && faceVadSnapshot.meterUnavailable !== true
                                && faceVadSnapshot.hasSpeech === false;
                            const silenceShape = isLikelySilenceHallucination(transcript, effectiveFrom)
                                || isLikelySilenceHallucination(translatedText, effectiveTo);
                            const silenceEcho = silenceShape && vadConfirmsSilence;
                            // #2 자기 TTS 에코 차단(핑퐁): 방금 기기가 발화한 '출력 언어'로 입력이 되돌아오면
                            // (= 화자 본인 언어가 아닌 방향) 자기 음성 잔향으로 보고 짧은 창에서 무시한다.
                            // → "일본어 발화 후 한국어 재발화"(에코→역번역) 루프를 끊는다.
                            // 화자 본인 언어(profileLang) 입력은 절대 막지 않는다.
                            // (G2) STT 라벨 단독 의존은 상대의 정상 발화까지 오차단할 위험 → F1 공유 텍스트
                            // 유사도(relayTextsSimilar: CJK 바이그램 Dice≥0.55)를 AND 조건으로 추가한다.
                            // '그 언어로 되돌아옴' + '방금 발화한 출력문과 실제로 닮음'일 때만 에코로 보고,
                            // 닮지 않은 새 발화(상대 정상 차례)는 통과시킨다.
                            const outputLangEcho = effectiveFrom !== profileLang
                                && recentSpoken.some((entry) => entry.toLang === effectiveFrom
                                    && echoNowMs - entry.spokenAtMs < FACE_OUTPUT_ECHO_GUARD_MS
                                    && (relayTextsSimilar(transcript, entry.translated)
                                        || (!!translatedText && relayTextsSimilar(translatedText, entry.translated))));
                            // 부분 일치 에코: 새 인식문이 최근 발화한 통역문/원문의 일부(끝마디 등)거나
                            // 그 반대로 포함관계면 TTS 잔향 재녹음으로 보고 건너뛴다.
                            const normNew = normalizeRelayText(transcript);
                            const normNewTr = normalizeRelayText(translatedText);
                            const containsEcho = (hay: string, needle: string) => needle.length >= 6 && hay.includes(needle);
                            const substringEcho = recentSpoken.some((entry) => {
                                const spokenTr = normalizeRelayText(entry.translated);
                                const spokenSrc = normalizeRelayText(entry.transcript);
                                return containsEcho(spokenTr, normNew)
                                    || containsEcho(normNew, spokenTr)
                                    || containsEcho(spokenSrc, normNew)
                                    || (!!normNewTr && (containsEcho(spokenTr, normNewTr) || containsEcho(spokenSrc, normNewTr)));
                            });
                            if (echoCheck.echo || repetitionEcho || silenceEcho || substringEcho || outputLangEcho) {
                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                    event: 'segment_skip_echo',
                                    reason: echoCheck.reason
                                        ?? (repetitionEcho ? 'repetition_hallucination' : (silenceEcho ? 'silence_hallucination' : (substringEcho ? 'substring_echo' : (outputLangEcho ? 'output_lang_echo' : 'echo')))),
                                    transcript: transcript.slice(0, 80),
                                }));
                                setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                            } else if (mainLastAutoVoiceRelayRef.current && mainLastAutoVoiceRelayRef.current.key === relayKey && Date.now() - mainLastAutoVoiceRelayRef.current.sentAt < AUTO_RELAY_DUPLICATE_GUARD_MS) {
                                setGpsStatus(getUiText(fromLang).autoVoiceDuplicateSkipped);
                            } else {
                                // #2 한국어(원문) 표출: 인식한 원문은 번역 성공 여부와 무관하게 항상 표시한다.
                                setInputText(transcript);
                                // 번역문이 비면 폴백 번역을 시도해 '원문만 뜨고 끝'을 막는다.
                                let effectiveTranslated = translatedText;
                                if (!effectiveTranslated) {
                                    try {
                                        const fb = await translateTextWithRegion(transcript, effectiveFrom, effectiveTo);
                                        effectiveTranslated = String(fb.translated ?? '').trim();
                                    } catch {
                                        // no-op
                                    }
                                }
                                if (!effectiveTranslated) {
                                    setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                                } else {
                                    setResultText(effectiveTranslated);
                                    setOffline(false);
                                    setEngine(String(data.engine ?? 'nado-voice'));
                                    mainLastAutoVoiceRelayRef.current = { key: relayKey, sentAt: Date.now() };
                                    // #1 반복발화 금지: 동일 통역문이 가드창 안에서 다시 들어오면(에코/중복)
                                    // 표시는 갱신하되 TTS 재발화는 생략한다.
                                    const spokenKey = normalizeRelayText(effectiveTranslated);
                                    const lastSpoken = lastFaceSpokenOutputRef.current;
                                    const isRepeatOutput = !!lastSpoken
                                        && lastSpoken.text === spokenKey
                                        && Date.now() - lastSpoken.at < AUTO_RELAY_DUPLICATE_GUARD_MS;
                                    if (isRepeatOutput) {
                                        setGpsStatus(getUiText(fromLang).autoVoiceDuplicateSkipped);
                                    } else {
                                        setGpsStatus(formatStatusText(getUiText(fromLang).autoVoiceDetected, {
                                            from: getLangLabel(effectiveFrom),
                                            to: getLangLabel(effectiveTo),
                                        }));
                                        lastFaceSpokenOutputRef.current = { text: spokenKey, at: Date.now() };
                                        const spokenEntry = {
                                            transcript,
                                            translated: effectiveTranslated,
                                            toLang: effectiveTo,
                                            spokenAtMs: Date.now(),
                                        };
                                        faceSpokenHistoryRef.current = [
                                            ...faceSpokenHistoryRef.current,
                                            spokenEntry,
                                        ].slice(-FACE_CONVERSATION_SPOKEN_HISTORY);
                                        // 반이중: 발화 시작과 동시에 게이트를 닫아 재생 중 듣기 재개를 차단한다.
                                        faceSpeakingRef.current = true;
                                        setGpsStatus(getUiText(fromLang).faceSpeakingStatus ?? '🔊 통역 음성 출력 중 · 듣기 멈춤');
                                        facePlaybackPromise = playFaceTranslationOutput({
                                            translatedText: effectiveTranslated,
                                            targetLang: effectiveTo,
                                            apiBaseUrl: API_BASE,
                                            playbackSoundRef: faceVoicePlaybackSoundRef,
                                            correlationId: typeof data.correlation_id === 'string' ? data.correlation_id : faceCorrelationId,
                                        }).finally(() => {
                                            // TTS 재생이 끝난 시점으로 에코 보호창을 갱신해
                                            // 재생 직후 마이크가 잡는 잔향(지연 도착 포함)을 확실히 무시한다.
                                            spokenEntry.spokenAtMs = Date.now();
                                            lastFaceSpokenOutputRef.current = { text: spokenKey, at: Date.now() };
                                            // 잔향이 가라앉도록 drain 지연 후 게이트 해제 → 그 다음에야 듣기 재개.
                                            setTimeout(() => {
                                                faceSpeakingRef.current = false;
                                                spokenEntry.spokenAtMs = Date.now();
                                            }, FACE_CONVERSATION_PLAYBACK_DRAIN_MS);
                                        });
                                        if (Platform.OS === 'android') {
                                            ToastAndroid.show(`${getLangLabel(effectiveFrom)} → ${getLangLabel(effectiveTo)}`, ToastAndroid.SHORT);
                                        }
                                    }
                                }
                            }
                        } else {
                            const translatedText = String(data.translated ?? '').trim();
                            const detectedFrom: LangCode = normalizeDetectedLangCode(data.detected_language)
                                ?? inferSpeechLangCode(transcript, fromLang);
                            const manualFrom = detectedFrom;
                            const manualTo = toLang;
                            setInputText(transcript);
                            if (translatedText) {
                                setGpsStatus(`🎯 ${getLangLabel(manualFrom)} → ${getLangLabel(manualTo)}`);
                                setResultText(translatedText);
                                setOffline(false);
                                setEngine(String(data.engine ?? 'nado-voice'));
                            } else {
                                setGpsStatus(`🎯 ${getLangLabel(manualFrom)} → ${getLangLabel(manualTo)}`);
                                await runTranslation(transcript, manualFrom, manualTo);
                            }
                        }
                    }
                } else {
                    const errorText = await res.text();
                    console.log('[FACE_CONVERSATION]', JSON.stringify({
                        event: 'segment_response',
                        ok: false,
                        status: res.status,
                        detail: errorText.slice(0, 200),
                    }));
                    if (autoVoiceModeEnabled && activeVoiceInputTarget === 'main') {
                        setGpsStatus(res.status === 422
                            ? '🎙️ 음성 미감지 · 계속 듣는 중...'
                            : '🎙️ 이번 구간 오류 · 계속 듣는 중...');
                    } else {
                        throw new Error(errorText || `voice request failed (${res.status})`);
                    }
                }
            } finally {
                setVoiceSttLoading(false);
                FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
                if (uploadUri !== uri) {
                    FileSystem.deleteAsync(uploadUri, { idempotent: true }).catch(() => { /* no-op */ });
                }
                if (shouldAutoRestart) {
                    if (activeVoiceInputTarget === 'inter_call' && interCallActiveRef.current && interCallVoiceAssistEnabled) {
                        autoVoiceRestartTimerRef.current = setTimeout(() => {
                            if (!recordingRef.current) {
                                void startVoiceInput({ autoMode: true, target: 'inter_call' });
                            }
                        }, 400);
                    } else if (activeVoiceInputTarget === 'main') {
                        scheduleFaceConversationRestartRef.current(facePlaybackPromise);
                    }
                }
            }
        } catch (error) {
            setVoiceSttLoading(false);
            if (autoVoiceModeEnabledRef.current && voiceInputTargetRef.current === 'main') {
                const message = error instanceof Error ? error.message : '음성 처리 오류';
                console.error('[FACE_CONVERSATION]', JSON.stringify({ event: 'segment_error', message }));
                setGpsStatus(`🎙️ ${message} · 계속 듣는 중...`);
                if (!options.suppressAutoRestart) {
                    scheduleFaceConversationRestartRef.current(null);
                }
            }
        } finally {
            if (!shouldAutoRestart) {
                voiceInputTargetRef.current = 'main';
            }
            voiceInputStopInFlightRef.current = false;
        }
    }, [appendSongSubtitle, autoVoiceModeEnabled, clearAutoVoiceTimers, commitInterCallRelay, fromLang, getLangLabel, getUiText, interCallTurn, interCallVoiceAssistEnabled, resolveInterCallDirection, resolveSongHybridSource, resolveSongHybridTarget, runTranslation, songModeEnabled, startVoiceInput, toLang, translateTextWithRegion, userInfo?.preferred_language]);

    useEffect(() => {
        stopVoiceInputRef.current = stopVoiceInput;
    }, [stopVoiceInput]);

    useEffect(() => {
        if (!autoVoiceModeEnabled) {
            clearAutoVoiceTimers();
            void stopFaceVoicePlayback(faceVoicePlaybackSoundRef);
            faceSpokenHistoryRef.current = [];
            faceGptSpokenEchoRef.current = [];
            mainLastAutoVoiceRelayRef.current = null;
            faceSpeakingRef.current = false;
            lastFaceSpokenOutputRef.current = null;
            // [Silero] 자동음성 종료 시 네이티브 VAD 모니터도 정리(마이크 점유 해제).
            if (faceSileroActiveRef.current) {
                faceSileroActiveRef.current = false;
                faceSileroCaptureActiveRef.current = false;
                faceSileroCaptureUriRef.current = null;
                faceSileroFirstSpeechAtMsRef.current = null;
                void stopVoiceRelaySileroVadMonitor();
            }
            // [2-5 AEC/NS] 대면 통역이 직접 켠 경우에만 통신 모드를 해제한다.
            // (VoIP 통화 화면이 설정한 통화 오디오 모드를 가로채 끊지 않도록 ref로 가드)
            if (faceVoipAudioEnabledRef.current) {
                faceVoipAudioEnabledRef.current = false;
                void disableVoipAudio();
            }
        }
    }, [autoVoiceModeEnabled, clearAutoVoiceTimers]);

    useEffect(() => {
        return () => {
            clearAutoVoiceTimers();
        };
    }, [clearAutoVoiceTimers]);

    const handleToggleFaceConversation = useCallback(async () => {
        const profileLangRaw = String(userInfo?.preferred_language || fromLang).trim().toLowerCase();
        const profileLang: LangCode = isSupportedLangCode(profileLangRaw) ? profileLangRaw as LangCode : fromLang;
        if (autoVoiceModeEnabled) {
            if (recordingRef.current) {
                await stopVoiceInput({ suppressAutoRestart: true });
            }
            await stopFaceVoicePlayback(faceVoicePlaybackSoundRef);
            setAutoVoiceModeEnabled(false);
            setGpsStatus(getUiText(fromLang).autoVoiceModeStopped ?? '🎙️ 대화 통역을 종료했습니다.');
            return;
        }
        if (Platform.OS === 'web') {
            Alert.alert('대면 통역', '자동 대화 통역은 모바일 앱에서 사용할 수 있습니다.');
            return;
        }
        if (toLang === profileLang) {
            Alert.alert('상대 언어 필요', getUiText(fromLang).faceConversationPeerRequired ?? '상대 언어를 GPS 또는 수동 선택으로 지정해 주세요.');
            return;
        }
        // 대면 통역 화면은 '통역' 단일 모드 — 소리새(gpt) 모드가 메인 캡처 루프로 새지 않게 강제.
        faceAiModeRef.current = 'translate';
        setFaceAiMode('translate');
        setAutoVoiceModeEnabled(true);
        setGpsStatus(getUiText(fromLang).autoVoiceModeStarted ?? '🎙️ 대화 통역 시작 · 말 끝날 때까지 듣습니다');
        voiceInputTargetRef.current = 'main';
        void startVoiceInput({ autoMode: true });  // NOSONAR
    }, [autoVoiceModeEnabled, fromLang, getUiText, startVoiceInput, stopVoiceInput, toLang, userInfo?.preferred_language]);

    /**
     * 소리새 AI 전용 대화 토글(통역창과 분리). 통역모드의 '상대 언어 필요' 제약을 받지 않고
     * 항상 친구(gpt) 경로로 동작하며, 반이중·자기에코 가드는 공용 캡처 루프 로직을 그대로 재사용한다.
     */
    const handleToggleSorisaeConversation = useCallback(async () => {
        if (Platform.OS === 'web') {
            Alert.alert(aiDisplayName, `${aiDisplayName} 음성 대화는 모바일 앱에서 사용할 수 있습니다.`);
            return;
        }
        // 소리새 모드 강제(통역 경로로 새지 않게).
        faceAiModeRef.current = 'gpt';
        setFaceAiMode('gpt');
        if (autoVoiceModeEnabled) {
            if (recordingRef.current) {
                await stopVoiceInput({ suppressAutoRestart: true });
            }
            await stopFaceVoicePlayback(sorisaeVoicePlaybackSoundRef);
            sorisaeSpeakingRef.current = false;
            setAutoVoiceModeEnabled(false);
            setGpsStatus(`🐦 ${aiDisplayName} 대화를 종료했습니다.`);
            return;
        }
        setAutoVoiceModeEnabled(true);
        setGpsStatus(`🐦 ${aiDisplayName} 대화 시작 · 말이 끝나면 자동으로 답해요`);
        voiceInputTargetRef.current = 'main';
        void startVoiceInput({ autoMode: true });
    }, [autoVoiceModeEnabled, startVoiceInput, stopVoiceInput]);

    /** 소리새 AI 전용 창 닫기 — 진행 중인 대화/재생을 정리하고 닫는다. */
    const closeSorisaeWindow = useCallback(async () => {
        if (recordingRef.current && voiceInputTargetRef.current === 'main') {
            await stopVoiceInput({ suppressAutoRestart: true });
        }
        // [기능 분리 Phase1] 소리새 전용 재생/발화 게이트도 함께 정리.
        await stopFaceVoicePlayback(sorisaeVoicePlaybackSoundRef);
        sorisaeSpeakingRef.current = false;
        if (autoVoiceModeEnabled) {
            await stopFaceVoicePlayback(faceVoicePlaybackSoundRef);
            setAutoVoiceModeEnabled(false);
        }
        // 대면 통역 화면은 '통역' 단일 모드로 복귀(소리새 모드가 메인 캡처 루프로 새지 않게).
        sorisaeWindowOpenRef.current = false;
        faceAiModeRef.current = 'translate';
        setFaceAiMode('translate');
        setSorisaeWindowOpen(false);
    }, [autoVoiceModeEnabled, stopVoiceInput]);

    // 소리새 전용 창 열림/닫힘을 ref(처리 분기 SSOT)에 즉시 반영 + gpt 모드 고정.
    // 창이 열리면 진행 중이던 대면 통역 캡처를 멈춰 두 경로가 겹치지 않게 한다(완전 분리).
    useEffect(() => {
        sorisaeWindowOpenRef.current = sorisaeWindowOpen;
        if (sorisaeWindowOpen) {
            faceAiModeRef.current = 'gpt';
            setFaceAiMode('gpt');
            if (companionVoiceCallRef.current.phase === 'awake') {
                // [Phase6.1] 음성 호출로 깨어난 경우: 사용자가 창 안 마이크를 누르지 않아도
                // 곧바로 대화하도록 gpt 모드로 듣기를 이어간다(통역 스캔 캡처 → 소리새 대화 캡처 전환).
                voiceInputTargetRef.current = 'main';
                if (!autoVoiceModeEnabledRef.current) {
                    setAutoVoiceModeEnabled(true);
                }
                if (!recordingRef.current) {
                    void startVoiceInput({ autoMode: true });
                }
                void stopFaceVoicePlayback(faceVoicePlaybackSoundRef);
            } else {
                // [기능 분리 Phase1] 단일-활성 강제: 창을 열면 진행 중이던 대면 통역 세션을 **완전히** 정지한다.
                // autoVoiceMode를 끄지 않으면 재시작 루프가 메인 캡처를 되살려, 대면 발화가 소리새 경로로 새거나
                // 그 반대로 엉킨다. 소리새 듣기는 창 안의 마이크 버튼(handleToggleSorisaeConversation)으로 따로 시작한다.
                if (recordingRef.current) {
                    void stopVoiceInput({ suppressAutoRestart: true });  // NOSONAR
                }
                if (autoVoiceModeEnabledRef.current) {
                    setAutoVoiceModeEnabled(false);
                }
                void stopFaceVoicePlayback(faceVoicePlaybackSoundRef);
            }
        }
    }, [sorisaeWindowOpen, startVoiceInput, stopVoiceInput]);

    /**
     * [Phase6.1] 음성 호출형 — 웨이크워드 감지 시 깨우기 루틴.
     * 소리새 창을 열고 gpt 대화 모드로 전환한다(실제 듣기 재개는 위 창-오픈 이펙트가 처리).
     */
    const wakeCompanionVoiceCallNow = useCallback(() => {
        companionVoiceCallRef.current = wakeCompanionVoiceCall(companionVoiceCallRef.current, Date.now());
        faceAiModeRef.current = 'gpt';
        sorisaeWindowOpenRef.current = true;
        setFaceAiMode('gpt');
        setSorisaeWindowOpen(true);
        setGpsStatus(`🐦 ${aiDisplayName} 깨어났어요! 말씀하세요 · 3분 무응답이면 잠들어요`);
    }, [aiDisplayName]);
    useEffect(() => { wakeCompanionVoiceCallNowRef.current = wakeCompanionVoiceCallNow; }, [wakeCompanionVoiceCallNow]);

    /**
     * [Phase6.1] 음성 호출 대기 토글 — armed(dormant) 동안 통역 캡처 루프를 웨이크워드 스캐너로 가동한다.
     * (소리새 창이 닫혀 있어야 전사가 통역 경로로 흘러 웨이크워드를 감지할 수 있다.)
     */
    const handleToggleCompanionVoiceCall = useCallback(async () => {
        if (Platform.OS === 'web') {
            Alert.alert(aiDisplayName, `${aiDisplayName} 음성 호출은 모바일 앱에서 사용할 수 있습니다.`);
            return;
        }
        if (companionVoiceCallArmedRef.current) {
            companionVoiceCallRef.current = disarmCompanionVoiceCall(companionVoiceCallRef.current);
            companionVoiceCallArmedRef.current = false;
            setCompanionVoiceCallArmed(false);
            if (recordingRef.current && voiceInputTargetRef.current === 'main' && !sorisaeWindowOpenRef.current) {
                await stopVoiceInput({ suppressAutoRestart: true });
                setAutoVoiceModeEnabled(false);
            }
            setGpsStatus(`🐦 ${aiDisplayName} 음성 호출 대기를 종료했습니다.`);
            return;
        }
        // 무장: 통역 단일 모드(스캔)로 듣기 시작.
        companionVoiceCallRef.current = armCompanionVoiceCall(companionVoiceCallRef.current);
        companionVoiceCallArmedRef.current = true;
        setCompanionVoiceCallArmed(true);
        faceAiModeRef.current = 'translate';
        setFaceAiMode('translate');
        voiceInputTargetRef.current = 'main';
        setAutoVoiceModeEnabled(true);
        if (!recordingRef.current) {
            void startVoiceInput({ autoMode: true });
        }
        setGpsStatus(`🔔 음성 호출 대기 중 · "${aiDisplayName}" 또는 "소리새"라고 부르면 깨어나요`);
    }, [aiDisplayName, startVoiceInput, stopVoiceInput]);

    /**
     * [Phase6.1] 3분 무활동 자동 종료 — awake 인 동안 주기적으로 검사해, 마지막 활동 후
     * COMPANION_VOICE_CALL_IDLE_MS(3분) 경과 시 소리새 창을 닫고 dormant(다시 부르면 깨어남)로 복귀한다.
     */
    useEffect(() => {
        if (!sorisaeWindowOpen || !companionVoiceCallArmed) return undefined;
        const timer = setInterval(() => {
            if (!shouldCompanionVoiceCallSleep(companionVoiceCallRef.current, Date.now())) return;
            companionVoiceCallRef.current = sleepCompanionVoiceCall(companionVoiceCallRef.current);
            setGpsStatus(`😴 ${aiDisplayName}가 3분 무응답으로 잠들었어요 · 다시 부르면 깨어나요`);
            void (async () => {
                // 창/캡처를 완전히 정리한 뒤, 음성 호출 대기(통역 스캔 캡처)를 재가동한다(stop↔start 레이스 차단).
                await closeSorisaeWindow();
                if (!companionVoiceCallArmedRef.current) return;
                faceAiModeRef.current = 'translate';
                setFaceAiMode('translate');
                voiceInputTargetRef.current = 'main';
                setAutoVoiceModeEnabled(true);
                if (!recordingRef.current) {
                    void startVoiceInput({ autoMode: true });  // NOSONAR
                }
            })();
        }, 15_000);
        return () => clearInterval(timer);
    }, [sorisaeWindowOpen, companionVoiceCallArmed, aiDisplayName, closeSorisaeWindow, startVoiceInput]);

    const handleToggleInterCallVoiceAssist = useCallback(async () => {
        const isInterCallRecording = voiceInputTargetRef.current === 'inter_call' && (recordingRef.current || isVoiceRecording || voiceSttLoading);
        if (interCallVoiceAssistEnabled || isInterCallRecording) {
            setInterCallVoiceAssistEnabled(false);
            if (recordingRef.current && voiceInputTargetRef.current === 'inter_call') {
                await stopVoiceInput({ suppressAutoRestart: true });
            }
            emitUnifiedTranslationStatus('pstn', 'INFO', '스피커폰 통역 보조를 종료했습니다. 필요하면 텍스트 입력으로 이어가세요.');
            return;
        }
        setInterCallVoiceAssistEnabled(true);
        emitUnifiedTranslationStatus('pstn', 'READY', `스피커폰 통역 보조 준비 중 (${formatAutoRelayDelayLabel(autoRelayDelayMs)} 간격)`);
    }, [autoRelayDelayMs, emitUnifiedTranslationStatus, interCallVoiceAssistEnabled, isVoiceRecording, stopVoiceInput, voiceSttLoading]);

    const relayInterCallManual = useCallback(async (turn: 'from' | 'to', spokenText: string, options: { isAutoRelay?: boolean } = {}) => {
        const trimmedText = spokenText.trim();
        if (!trimmedText) return;
        const dedupeKey = `${turn}:${normalizeRelayText(trimmedText)}`;
        if (options.isAutoRelay && interLastAutoRelayRef.current && interLastAutoRelayRef.current.key === dedupeKey && Date.now() - interLastAutoRelayRef.current.sentAt < AUTO_RELAY_DUPLICATE_GUARD_MS) {
            setInterCallStatus(getUiText(fromLang).interAutoRelayDuplicateSkipped);
            setInterManualText('');
            return;
        }
        const { listenLang, translateTo } = resolveInterCallDirection(turn);
        emitUnifiedTranslationStatus('pstn', 'TRANSLATE', `${getLangLabel(listenLang)} -> ${getLangLabel(translateTo)}`, {
            turn,
            auto_relay: Boolean(options.isAutoRelay),
        });
        try {
            const translated = await translateTextWithRegion(
                trimmedText,
                listenLang,
                translateTo,
            );
            commitInterCallRelay(turn, trimmedText, translated.translated, options);
        } catch {
            emitUnifiedTranslationStatus('pstn', 'ERROR', '통역 통화 처리 중 오류가 발생했습니다.', { turn });
        }
    }, [commitInterCallRelay, emitUnifiedTranslationStatus, fromLang, getLangLabel, getUiText, resolveInterCallDirection, translateTextWithRegion]);

    const clearInterManualAutoRelayTimer = useCallback(() => {
        if (interManualAutoRelayTimerRef.current) {
            clearTimeout(interManualAutoRelayTimerRef.current);
            interManualAutoRelayTimerRef.current = null;
        }
    }, []);

    useEffect(() => {
        return () => {
            clearInterManualAutoRelayTimer();
        };
    }, [clearInterManualAutoRelayTimer]);

    useEffect(() => {
        if (Platform.OS === 'web' || !interCallActive || !interCallActiveRef.current) {
            clearInterManualAutoRelayTimer();
            return;
        }

        const pendingText = interManualText.trim();
        if (!pendingText) {
            clearInterManualAutoRelayTimer();
            return;
        }

        setInterCallStatus(formatStatusText(getUiText(fromLang).interAutoRelayPending, { delay: formatAutoRelayDelayLabel(autoRelayDelayMs) }));
        clearInterManualAutoRelayTimer();
        interManualAutoRelayTimerRef.current = setTimeout(() => {
            void relayInterCallManual(interCallTurn, pendingText, { isAutoRelay: true });
            interManualAutoRelayTimerRef.current = null;
        }, autoRelayDelayMs);

        return () => {
            clearInterManualAutoRelayTimer();
        };
    }, [
        clearInterManualAutoRelayTimer,
        interCallActive,
        interCallTurn,
        interManualText,
        fromLang,
        autoRelayDelayMs,
        relayInterCallManual,
    ]);

    const startInterCallCycleWeb = useCallback((turn: 'from' | 'to') => {
        const webAny = globalThis as any;
        if (!interCallActiveRef.current || !webAny?.window) return;
        const { listenLang, translateTo, listenLabel, translateLabel } = resolveInterCallDirection(turn);
        const listenTts = LANGS.find((l) => l.code === listenLang)?.tts ?? 'en-US';
        setInterCallTurn(turn);
        emitUnifiedTranslationStatus('pstn', 'LISTEN', `${listenLabel} 입력 대기`, { turn });

        const SpeechRecognitionCtor = webAny.window.SpeechRecognition || webAny.window.webkitSpeechRecognition;
        if (!SpeechRecognitionCtor) {
            setInterCallStatus('이 환경은 음성 인식을 지원하지 않아 수동 통역 모드로 전환됩니다.');
            return;
        }
        const recognizer = new SpeechRecognitionCtor();
        recognizer.lang = listenTts;
        recognizer.interimResults = false;
        recognizer.onresult = async (event: any) => {
            const spokenText = event.results?.[0]?.[0]?.transcript ?? '';
            if (!interCallActiveRef.current) return;
            emitUnifiedTranslationStatus('pstn', 'TRANSLATE', `${listenLabel} -> ${translateLabel}`, { turn });
            try {
                const translated = await translateTextWithRegion(
                    spokenText,
                    listenLang,
                    translateTo,
                );
                setInterCallLog((prev) => [...prev.slice(-19), { turn, text: spokenText, translated: translated.translated }]);
                emitUnifiedTranslationStatus('pstn', 'SPEAK', `${translateLabel} 송출`, { turn });
                const targetTts = LANGS.find((l) => l.code === translateTo)?.tts ?? 'en-US';
                const UtteranceCtor = webAny.window.SpeechSynthesisUtterance;
                if (!UtteranceCtor) {
                    emitUnifiedTranslationStatus('pstn', 'ERROR', '브라우저 TTS를 사용할 수 없습니다.', { turn });
                    return;
                }
                const utter = new UtteranceCtor(translated.translated);
                utter.lang = targetTts;
                utter.rate = 0.9;
                utter.onend = () => {
                    if (interCallActiveRef.current) {
                        startInterCallCycleWeb(turn === 'from' ? 'to' : 'from');
                    }
                };
                webAny.window.speechSynthesis.cancel();
                webAny.window.speechSynthesis.speak(utter);
            } catch {
                emitUnifiedTranslationStatus('pstn', 'ERROR', '통역 통화 처리 중 오류가 발생했습니다.', { turn });
            }
        };
        recognizer.onerror = () => {
            if (interCallActiveRef.current) {
                emitUnifiedTranslationStatus('pstn', 'ERROR', '음성 인식 오류. 다시 시도하세요.', { turn });
            }
        };
        recognizer.start();
    }, [emitUnifiedTranslationStatus, resolveInterCallDirection, translateTextWithRegion]);

    const handleInterCallToggle = useCallback(async () => {
        if (interCallActiveRef.current) {
            setInterCallVoiceAssistEnabled(false);
            if (recordingRef.current && voiceInputTargetRef.current === 'inter_call') {
                await stopVoiceInput({ suppressAutoRestart: true });
            }
            interCallActiveRef.current = false;
            setInterCallActive(false);
            setInterCallStatus('');
            setInterManualText('');
            return;
        }
        interCallActiveRef.current = true;
        setInterCallActive(true);
        setInterCallLog([]);
        setInterCallTurn('from');
        if (Platform.OS === 'web') {
            startInterCallCycleWeb('from');
        } else {
            const { dialOpened } = await startPstnAssistDialFlow({
                interCallPhone,
                bookingSupportPhone: bookingResult?.support_phone,
                selectedBookingPhone: selectedBookingPlace?.phone,
            });
            if (dialOpened) {
                setInterCallVoiceAssistEnabled(true);
                emitUnifiedTranslationStatus('pstn', 'READY', `${SUPPORTED_LANGUAGE_COUNT}개국어 자동 전달 모드 시작`, {
                    dial_opened: true,
                });
            } else {
                emitUnifiedTranslationStatus('pstn', 'ERROR', '전화번호를 입력하거나 호텔을 선택하면 다이얼패드를 열 수 있습니다.', {
                    dial_opened: false,
                });
            }
        }
    }, [bookingResult, emitUnifiedTranslationStatus, interCallPhone, selectedBookingPlace, setInterCallActive, setInterManualText, startInterCallCycleWeb, startPstnAssistDialFlow, stopVoiceInput]);

    useEffect(() => {
        if (Platform.OS === 'web' || !interCallActive || !interCallVoiceAssistEnabled || recordingRef.current || voiceInputStartInFlightRef.current || voiceInputStopInFlightRef.current) {
            return;
        }
        void startVoiceInput({ autoMode: true, target: 'inter_call' });
    }, [interCallActive, interCallVoiceAssistEnabled, startVoiceInput]);

    const handleSelectInterCallContact = useCallback((contact: DevicePhoneContact) => {
        setInterCallPhone(contact.phone);
        setInterCallContactPickerVisible(false);
        setInterCallStatus(`📇 ${contact.name} 번호를 단말 전화번호 저장소에서 선택했습니다. 통역 통화 시작을 누르면 시스템 전화앱으로 이어집니다.`);
    }, []);

    // [Phase5.11] 연락처에서 직접 채팅 시작/초대 — 번호가 앱 친구면 채팅방을 열고,
    // 미가입이면 SNS(카카오톡/라인/문자) 공유로 초대한다. 일반통화/번호 채우기는 기존 흐름 유지.
    const handleOpenChatFromContact = useCallback(async (contact: DevicePhoneContact) => {
        const inviterName = userInfo?.username || userInfo?.email?.split('@')[0] || '';
        if (!token || !userInfo?.id) {
            void shareChatInvite({ apiBase: API_BASE, contactName: contact.name, inviterName });
            return;
        }
        try {
            const { friends } = await getFriends(userInfo.id, token);
            const index = buildFriendPhoneIndex(friends);
            const action = resolveContactChatAction(index, [contact.phone]);
            if (action.kind === 'chat' && action.friend.friendUserId != null) {
                const room = await createDirectChatRoom(API_BASE, token, action.friend.friendUserId);
                setSelectedChatRoom(room);
                setShowFriendFolder(false);
                setInterCallStatus(`💬 ${contact.name}님과의 채팅방을 열었습니다.`);
                logUiPressProbe('CONTACT_CHAT_OPENED', {
                    friend_user_id: action.friend.friendUserId,
                    room_id: room.room_id,
                });
                return;
            }
            const { shared } = await shareChatInvite({ apiBase: API_BASE, contactName: contact.name, inviterName });
            setInterCallStatus(
                shared
                    ? `📨 ${contact.name}님에게 채팅 초대를 보냈습니다.`
                    : `📨 ${contact.name}님은 아직 미가입입니다. 초대 공유를 취소했습니다.`,
            );
            logUiPressProbe('CONTACT_CHAT_INVITE_SHARED', { shared });
        } catch (error: any) {
            Alert.alert('채팅 시작 실패', error?.message || '연락처로 채팅을 시작하지 못했습니다.');
        }
    }, [logUiPressProbe, token, userInfo?.email, userInfo?.id, userInfo?.username]);

    // 연락처 선택 후 무엇을 할지(채팅/초대 · 일반통화 번호 채우기) 묻는다.
    const presentContactActionChooser = useCallback((contact: DevicePhoneContact) => {
        Alert.alert(
            contact.name,
            `${contact.phone}\n무엇을 할까요?`,
            [
                { text: '💬 채팅/초대', onPress: () => { void handleOpenChatFromContact(contact); } },
                { text: '📞 일반통화', onPress: () => { handleSelectInterCallContact(contact); } },
                { text: '취소', style: 'cancel' },
            ],
            { cancelable: true },
        );
    }, [handleOpenChatFromContact, handleSelectInterCallContact]);

    // [Phase5.12] 연락처 디렉터리 — 친구(가입자) 목록 로더(미로그인/실패 시 빈 배열).
    const loadFriendsForDirectory = useCallback(async (): Promise<Friend[]> => {
        if (!token || !userInfo?.id) {
            return [];
        }
        try {
            const { friends } = await getFriends(userInfo.id, token);
            return friends;
        } catch {
            return [];
        }
    }, [token, userInfo?.id]);

    // [Phase5.12] 📞 일반전화 통역 — 단말 전화앱 발신 + 자동 통역 보조 시작(가입 여부 무관).
    const handleRegularCallContact = useCallback(async (contact: DeviceContact) => {
        setContactsDirectoryVisible(false);
        setInterCallPhone(contact.phone);
        logUiPressProbe('CONTACT_DIRECTORY_REGULAR_CALL', { phone: contact.phone });
        if (Platform.OS === 'web') {
            interCallActiveRef.current = true;
            setInterCallActive(true);
            setInterCallLog([]);
            setInterCallTurn('from');
            startInterCallCycleWeb('from');
            return;
        }
        interCallActiveRef.current = true;
        setInterCallActive(true);
        setInterCallLog([]);
        setInterCallTurn('from');
        const { dialOpened } = await startPstnAssistDialFlow({
            interCallPhone: contact.phone,
            bookingSupportPhone: bookingResult?.support_phone,
            selectedBookingPhone: selectedBookingPlace?.phone,
        });
        if (dialOpened) {
            setInterCallVoiceAssistEnabled(true);
            setInterCallStatus(`📞 ${contact.name}님께 일반전화 통역 발신 — 통화 중 자동 통역이 전달됩니다.`);
        } else {
            interCallActiveRef.current = false;
            setInterCallActive(false);
            setInterCallStatus('전화앱을 열지 못했습니다. 번호를 확인해 주세요.');
        }
    }, [bookingResult?.support_phone, logUiPressProbe, selectedBookingPlace?.phone, startInterCallCycleWeb, startPstnAssistDialFlow]);

    // [Phase5.12] 📡 VoIP — 앱 친구일 때 친구 보이스톡으로 발신.
    const handleVoipCallContact = useCallback((contact: DeviceContact, friend: Friend) => {
        setContactsDirectoryVisible(false);
        logUiPressProbe('CONTACT_DIRECTORY_VOIP_CALL', { friend_user_id: friend.friendUserId ?? null });
        void handleStartFriendVoiceCall(friend);  // NOSONAR
    }, [handleStartFriendVoiceCall, logUiPressProbe]);

    // [Phase5.12] 💬 채팅 — 친구면 채팅방을 열고, 미가입이면 SNS 초대.
    const handleChatContact = useCallback(async (contact: DeviceContact, friend: Friend | null) => {
        setContactsDirectoryVisible(false);
        const inviterName = userInfo?.username || userInfo?.email?.split('@')[0] || '';
        if (friend && friend.friendUserId != null && token) {
            try {
                const room = await createDirectChatRoom(API_BASE, token, friend.friendUserId);
                setSelectedChatRoom(room);
                setShowFriendFolder(false);
                setActiveRailSection('chat');
                setInterCallStatus(`💬 ${contact.name}님과의 채팅방을 열었습니다.`);
                logUiPressProbe('CONTACT_DIRECTORY_CHAT_OPENED', {
                    friend_user_id: friend.friendUserId,
                    room_id: room.room_id,
                });
                return;
            } catch (error: any) {
                Alert.alert('채팅 시작 실패', error?.message || '연락처로 채팅을 시작하지 못했습니다.');
                return;
            }
        }
        const { shared } = await shareChatInvite({ apiBase: API_BASE, contactName: contact.name, inviterName });
        setInterCallStatus(
            shared
                ? `📨 ${contact.name}님에게 채팅 초대를 보냈습니다.`
                : `📨 ${contact.name}님은 아직 미가입입니다. 초대 공유를 취소했습니다.`,
        );
        logUiPressProbe('CONTACT_DIRECTORY_CHAT_INVITE_SHARED', { shared });
    }, [logUiPressProbe, token, userInfo?.email, userInfo?.username]);

    const handlePhoneDialerInitiated = useCallback(async (phone: string) => {
        const normalized = phone.trim();
        setShowPhoneDialerModal(false);
        setInterCallPhone(normalized);
        setVoipPhone(normalized);
        logUiPressProbe('PHONE_DIALER_INITIATED', {
            phone: normalized,
            call_mode: selectedCallMode,
        });
        if (Platform.OS === 'web') {
            Alert.alert('다이얼패드', '웹에서는 시스템 전화앱 연동을 사용할 수 없습니다.');
            return;
        }
        const dialOpened = await openDialPad(normalized);
        if (dialOpened) {
            setInterCallStatus('📞 다이얼패드 번호로 시스템 전화앱을 열었습니다. 통화 후 수동 통역 모드를 사용하세요.');
        } else {
            setInterCallContactError('다이얼패드에서 선택한 번호로 전화앱을 열지 못했습니다.');
        }
    }, [logUiPressProbe, openDialPad, selectedCallMode, setInterCallPhone, setInterCallContactError, setInterCallStatus, setVoipPhone]);

    const handleOpenInterCallContactPicker = useCallback(async () => {
        if (Platform.OS === 'web') {
            Alert.alert('전화번호 저장소 열기', '웹에서는 단말 전화번호 저장소를 직접 열 수 없습니다. 모바일 앱에서 사용하세요.');
            return;
        }

        setInterCallContactLoading(true);
        setInterCallContactError('');

        try {
            const Contacts = await import('expo-contacts');
            const permission = await Contacts.requestPermissionsAsync();
            if (permission.status !== 'granted') {
                setInterCallContactError('연락처 권한이 없어 단말 전화번호 저장소를 열 수 없습니다.');
                return;
            }

            const pickedContact = await Contacts.presentContactPickerAsync();
            if (!pickedContact) {
                setInterCallStatus('📇 단말 전화번호 저장소 열기를 취소했습니다.');
                return;
            }

            const phoneNumber = pickedContact.phoneNumbers?.find((phone) => Boolean(phone.number?.trim()));
            if (!phoneNumber?.number?.trim()) {
                setInterCallContactError('선택한 연락처에 사용할 전화번호가 없습니다.');
                return;
            }

            const resolvedContact = {
                id: pickedContact.id ?? `${pickedContact.name || 'contact'}-${phoneNumber.number.trim()}`,
                name: pickedContact.name?.trim() || '이름 없음',
                phone: phoneNumber.number.trim(),
                label: phoneNumber.label || '연락처 번호',
            } satisfies DevicePhoneContact;

            setInterCallContactOptions([]);
            setInterCallContactPickerVisible(false);
            presentContactActionChooser(resolvedContact);
        } catch (error: any) {
            setInterCallContactError(error?.message || '단말 전화번호 저장소를 열지 못했습니다.');
        } finally {
            setInterCallContactLoading(false);
        }
    }, [presentContactActionChooser]);

    const currentFromLabel = getLangLabel(fromLang);
    const currentToLabel = getLangLabel(toLang);
    // [홈 런처] 대면통역 히어로 카드의 국기 표시용 언어→국기 매핑(목업 #1).
    const langFlag = (code: string): string => {
        const m: Record<string, string> = {
            ko: '🇰🇷', en: '🇺🇸', ja: '🇯🇵', zh: '🇨🇳', 'zh-cn': '🇨🇳', 'zh-tw': '🇹🇼',
            es: '🇪🇸', fr: '🇫🇷', de: '🇩🇪', it: '🇮🇹', pt: '🇵🇹', ru: '🇷🇺', ar: '🇸🇦',
            hi: '🇮🇳', th: '🇹🇭', vi: '🇻🇳', id: '🇮🇩', tr: '🇹🇷', nl: '🇳🇱', pl: '🇵🇱',
            uk: '🇺🇦', ms: '🇲🇾', tl: '🇵🇭', mn: '🇲🇳', km: '🇰🇭', ne: '🇳🇵',
        };
        return m[(code || '').toLowerCase()] ?? '🌐';
    };
    const homeFromFlag = langFlag(fromLang);
    const homeToFlag = langFlag(toLang);
    // [홈 런처] 정밀 번역 도구(직접 입력/OCR) 접힘 상태 — 기본 접힘으로 홈을 깔끔한 런처로 유지.
    const [homeToolsExpanded, setHomeToolsExpanded] = useState(false);
    // [대면통역 전용 화면(mockup #2)] 상단 상대언어(180° 회전) + 하단 내언어 + 중앙 펄스 마이크.
    const [faceScreenOpen, setFaceScreenOpen] = useState(false);
    // [VoIP 통화화면 디자인 미리보기(mockup #3)] 실통화 없이 연결된 통화 UI를 검증.
    const [voipPreviewOpen, setVoipPreviewOpen] = useState(false);
    const [activeRailSection, setActiveRailSection] = useState<SectionRailKey | null>(null);
    const [isRailMenuOpen, setIsRailMenuOpen] = useState(false);
    const isChatRailSectionVisible = activeRailSection === 'chat';
    const hasPendingIncomingVoip = !!pendingIncomingVoipCall && !voipCallInitResponse;
    const isVoipRailSectionVisible = activeRailSection === 'voip' || hasPendingIncomingVoip;
    const isSongRailSectionVisible = activeRailSection === 'song-mode';
    const isTravelRailSectionVisible = activeRailSection === 'travel-booking';
    const scrollViewRef = useRef<ScrollView | null>(null);
    const railSectionOffsetRef = useRef<Record<SectionRailKey, number>>({
        chat: 0,
        voip: 0,
        'song-mode': 0,
        'travel-booking': 0,
    });
    const isVoipRailLobbyVisible = isVoipRailSectionVisible && showVoipTester && !voipCallInitResponse && !pendingIncomingVoipCall;
    const isVoipRailActiveCallVisible = isVoipRailSectionVisible && !!voipCallInitResponse;
    const isVoipDockAttentionVisible = !!voipCallInitResponse || hasPendingIncomingVoip;
    const showIncomingVoipRailCard = hasPendingIncomingVoip;
    const showIncomingVoipBanner = false;
    const showAuthDebugFloating = AUTH_DEBUG_MARKER_ENABLED && !isVoipDockAttentionVisible && !isVoipRailSectionVisible;

    useEffect(() => {
        activeRailSectionRef.current = activeRailSection;
    }, [activeRailSection]);

    // [기능 분리 Phase4] 단일-활성 강제: 기능(레일)이 바뀌면 직전 음성 기능의 마이크 캡처를
    // 정지(quiesce)시킨다. 비활성 기능이 백그라운드에서 계속 듣는 것을 막아 기능 간 간섭을 차단한다.
    // (대면통역/소리새/일반전화/노래만 lease 대상 — VOIP 통화는 WebRTC 자체 경로라 무관.)
    useEffect(() => {
        revokeCurrentVoiceCapture(`rail:${activeRailSection ?? 'home'}`);
    }, [activeRailSection]);

    useEffect(() => {
        if (!isVoipDockAttentionVisible || activeRailSection === 'voip') {
            return;
        }

        restoreVoipRailState('incoming_or_active_auto_focus');
    }, [activeRailSection, isVoipDockAttentionVisible, restoreVoipRailState]);

    useEffect(() => {
        setRailDebugLastApplied(`${activeRailSection ?? 'home'}@${new Date().toISOString()}`);
    }, [activeRailSection]);

    const scrollToRailSection = useCallback((sectionKey: SectionRailKey, animated = true) => {
        const nextOffset = railSectionOffsetRef.current[sectionKey];
        const topRevealInset = sectionKey === 'voip' && hasPendingIncomingVoip ? 168 : 16;
        scrollViewRef.current?.scrollTo({
            y: Math.max(0, nextOffset - topRevealInset),
            animated,
        });
    }, [hasPendingIncomingVoip]);

    useEffect(() => {
        if (!activeRailSection) {
            return;
        }

        const frameId = requestAnimationFrame(() => {
            scrollToRailSection(activeRailSection);
        });

        return () => cancelAnimationFrame(frameId);
    }, [activeRailSection, scrollToRailSection]);

    const handleSelectLanguage = useCallback((code: LangCode) => {
        if (langPickerFor === 'from') {
            if (!userInfo) {
                setFromLang(code);
            }
        }
        if (langPickerFor === 'to') {
            setToLang(code);
        }
        setLangPickerFor(null);
    }, [langPickerFor, userInfo]);

    const handlePressSectionRail = useCallback((key: SectionRailKey) => {
        const previousSection = activeRailSectionRef.current;
        const nextSection = previousSection === key ? null : key;
        const timestamp = new Date().toISOString();
        setRailDebugLastPressed(`${key}:${previousSection ?? 'home'}->${nextSection ?? 'home'}@${timestamp}`);
        logUiPressProbe('SECTION_RAIL_PRESS', {
            key,
            previous_section: previousSection ?? 'home',
            next_section: nextSection ?? 'home',
        });
        setActiveRailSection(nextSection);
        setIsRailMenuOpen(false);
    }, [logUiPressProbe]);

    const isLoggedIn = Boolean(userInfo);
    const isLobbyVisible = !isLoggedIn;
    const isTranslateWorkspaceVisible = isLoggedIn && activeRailSection === null;

    useAutoNearbyFriendDiscovery({
        enabled: authHydrated && isLoggedIn && Platform.OS !== 'web',
        token: token ?? null,
        userId: userInfo?.id ?? null,
        nickname: userInfo?.username || userInfo?.email.split('@')[0] || 'traveler',
        gender: voipProfileGender === 'male' || voipProfileGender === 'female' ? voipProfileGender : 'other',
        countryCode: gpsCountryCode || userInfo?.country_code || '',
        onFriendAccepted: () => setChatRefreshKey((prev) => prev + 1),
    });

    useEffect(() => {
        const preferred = String(userInfo?.preferred_language || fromLang).trim().toLowerCase();
        const profileLang: LangCode = isSupportedLangCode(preferred) ? preferred as LangCode : fromLang;
        if (!autoVoiceModeEnabled || toLang !== profileLang) {
            return;
        }
        void stopVoiceInput({ suppressAutoRestart: true });  // NOSONAR
        setAutoVoiceModeEnabled(false);
        setGpsStatus(getUiText(fromLang).faceConversationPeerRequired ?? '상대 언어를 GPS 또는 수동 선택으로 지정해 주세요.');
    }, [autoVoiceModeEnabled, fromLang, getUiText, stopVoiceInput, toLang, userInfo?.preferred_language]);

    useEffect(() => {
        if (!isTranslateWorkspaceVisible && autoVoiceModeEnabled) {
            void stopVoiceInput({ suppressAutoRestart: true });
            setAutoVoiceModeEnabled(false);
        }
    }, [autoVoiceModeEnabled, isTranslateWorkspaceVisible, stopVoiceInput]);

    useEffect(() => {
        if (!isTranslateWorkspaceVisible || !autoVoiceModeEnabled || Platform.OS === 'web' || recordingRef.current) {
            return;
        }
        void startVoiceInput({ autoMode: true });
    }, [autoVoiceModeEnabled, isTranslateWorkspaceVisible, startVoiceInput]);

    return (
        <ImageBackground source={SKY_BG} resizeMode="cover" style={styles.skyBg}>
        <SafeAreaView style={styles.root} edges={['top', 'left', 'right']}>
            <StatusBar style="dark" />
            <ScrollView
                ref={scrollViewRef}
                contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 96 }]}
                keyboardShouldPersistTaps="handled"
            >
                {/* ── 헤더 + 로그인(내정보) ── */}
                <View style={styles.header}>
                    <Text style={styles.title}>{WORLDLINGO_APP_NAME}</Text>
                    <Text style={styles.subtitle}>{getUiText(fromLang).subtitle}</Text>
                    <View style={styles.versionPillRow}>
                        <View style={styles.versionPill}>
                            <Text style={styles.versionPillText}>{APP_VERSION_LABEL}</Text>
                        </View>
                        {isLoggedIn ? (
                            <Pressable
                                style={styles.voipLaunchBtn}
                                onPress={() => {
                                    setActiveRailSection(null);
                                    setIsRailMenuOpen(false);
                                }}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-translate-home-button"
                                testID="worldlinco-translate-home-button"
                            >
                                <Text style={styles.voipLaunchBtnText}>번역 홈</Text>
                            </Pressable>
                        ) : (
                            <Pressable style={styles.voipLaunchBtn} onPress={handlePressLoginButton}>
                                <Text style={styles.voipLaunchBtnText}>로그인 / 회원가입</Text>
                            </Pressable>
                        )}
                    </View>
                    {engine ? (
                        <View style={styles.badge}>
                            <Text style={styles.badgeText}>
                                {offline ? getUiText(fromLang).offlineBadge : `🟢 ${engine}`}
                            </Text>
                        </View>
                    ) : null}
                    <View style={styles.accountRow}>
                        {userInfo ? (
                            <>
                                <Pressable
                                    style={styles.myInfoBtn}
                                    onPress={() => setShowMyInfo((v) => !v)}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-my-info-toggle"
                                    testID="worldlinco-my-info-toggle"
                                >
                                    <Text style={styles.myInfoBtnText}>👤 {userInfo.username || userInfo.email.split('@')[0]}</Text>
                                </Pressable>
                                <Pressable style={styles.logoutBtn} onPress={handleLogout}>
                                    <Text style={styles.logoutBtnText}>로그아웃</Text>
                                </Pressable>
                            </>
                        ) : (
                            <Pressable
                                style={styles.loginBtn}
                                onPress={handlePressLoginButton}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-header-login-button"
                                testID="worldlinco-header-login-button"
                            >
                                <Text style={styles.loginBtnText}>🔐 로그인</Text>
                            </Pressable>
                        )}
                    </View>
                    {showAuthDebugFloating ? (
                        <View
                            pointerEvents="none"
                            style={styles.authDebugPanel}
                            accessibilityLabel={`AUTH_DEBUG_STATE:${authDebugState}`}
                            testID="auth-debug-panel"
                        >
                            <Text style={styles.authDebugTitle}>AUTH DEBUG</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_STATE:{authDebugState}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_USER:{authDebugUser}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_LAST_PROBE:{lastUiProbeEvent}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_RAIL_LAST_PRESSED:{railDebugLastPressed}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_RAIL_LAST_APPLIED:{railDebugLastApplied}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_SURFACE:{authDebugSurface}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_SUBMIT_MODE:{authDebugSubmitMode}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_EMAIL_FILLED:{authDebugEmailFilled ? '1' : '0'}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_PASSWORD_FILLED:{authDebugPasswordFilled ? '1' : '0'}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_FOCUS_FIELD:{authDebugFocusField}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_LAST_INPUT_EVENT:{authDebugLastInputEvent}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_EMAIL_LEN:{authDebugEmailLength}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_PASSWORD_LEN:{authDebugPasswordLength}</Text>
                            <Text style={styles.authDebugLine}>AUTH_DEBUG_SUBMIT_PRESSED:{authDebugSubmitPressedLabel}</Text>
                        </View>
                    ) : null}
                    {!userInfo ? (
                        <View style={styles.inlineAuthPanel} accessibilityLabel="worldlinco-inline-auth-panel" testID="worldlinco-inline-auth-panel">
                            <Text style={styles.inlineAuthTitle}>로그인이 필요해요</Text>
                            <Text style={styles.inlineAuthHint}>
                                여행 통번역·레일 서비스를 쓰려면 로그인하세요. 로그인·회원가입은 전용 화면에서 한 번에 진행됩니다.
                            </Text>
                            {demoSessionMessage ? <Text style={styles.inlineAuthStatus}>{demoSessionMessage}</Text> : null}
                            <View style={styles.inlineAuthActionRow}>
                                <Pressable
                                    style={[styles.inlineActionBtn, demoSessionLoading && styles.inlineGhostBtnDisabled]}
                                    onPress={() => { void handleStartInstantDemoSession('chat'); }}
                                    disabled={demoSessionLoading || loginLoading}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-demo-session-start-button-inline"
                                    testID="worldlinco-demo-session-start-button-inline"
                                >
                                    <Text style={styles.inlineActionBtnText}>{demoSessionLoading ? '데모 연결 중...' : '데모 세션 시작'}</Text>
                                </Pressable>
                                <Pressable
                                    style={[styles.translateBtn, styles.inlineAuthSubmitBtn]}
                                    onPress={() => { setAuthModalMode('login'); setLoginError(''); setShowLogin(true); }}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-inline-open-login-button"
                                    testID="worldlinco-inline-open-login-button"
                                >
                                    <Text style={styles.translateBtnText}>로그인 / 회원가입</Text>
                                </Pressable>
                            </View>
                        </View>
                    ) : null}
                    {showMyInfo && userInfo && (
                        <View style={styles.myInfoPanel} testID="worldlinco-my-info-panel">
                            <Text style={styles.myInfoTitle}>내 정보</Text>
                            <Text style={styles.myInfoText}>이메일: {userInfo.email}</Text>
                            <Text style={styles.myInfoText}>ID: {userInfo.id}</Text>
                            <Text style={styles.myInfoText}>보이스 ID: {voipIdentity || buildVoiceId(userInfo.id)}</Text>
                            <Text style={styles.myInfoText}>기본 언어: {getLangLabelText(profilePreferredLanguage)} ({profilePreferredLanguage.toUpperCase()})</Text>
                            <Text style={styles.myInfoText}>기본 국가: {resolveCountryFlag(profileCountryCode)} {resolveCountryName(profileCountryCode)} ({profileCountryCode})</Text>
                            <Text style={styles.signupProfileLabel}>로그인 후 프로필 기본 언어</Text>
                            <Pressable
                                style={styles.signupPickerTrigger}
                                onPress={() => setProfileSelectionModal('language')}
                                accessibilityLabel="worldlinco-myinfo-language-picker-trigger"
                                testID="worldlinco-myinfo-language-picker-trigger"
                            >
                                <View>
                                    <Text style={styles.signupPickerValue}>{getLangLabelText(profilePreferredLanguage)}</Text>
                                    <Text style={styles.signupPickerMeta}>채팅/VoIP 기본 언어로 사용</Text>
                                </View>
                                <Text style={styles.signupPickerHint}>열기</Text>
                            </Pressable>
                            <Text style={styles.signupProfileLabel}>로그인 후 프로필 국가</Text>
                            <Pressable
                                style={styles.signupPickerTrigger}
                                onPress={() => setProfileSelectionModal('country')}
                                accessibilityLabel="worldlinco-myinfo-country-picker-trigger"
                                testID="worldlinco-myinfo-country-picker-trigger"
                            >
                                <View>
                                    <Text style={styles.signupPickerValue}>{resolveCountryFlag(profileCountryCode)} {resolveCountryName(profileCountryCode)}</Text>
                                    <Text style={styles.signupPickerMeta}>국가 프로필과 지역 힌트에 사용</Text>
                                </View>
                                <Text style={styles.signupPickerHint}>열기</Text>
                            </Pressable>
                            <Text style={styles.signupProfileHint}>
                                로그인 후에도 프로필 언어/국가를 바꿀 수 있어야 채팅 자동 번역과 VoIP 통역 기본값이 실제 사용자 상태를 따라갑니다.
                            </Text>
                            <Pressable
                                style={[styles.inlineActionBtn, profileSaving && { opacity: 0.7 }]}
                                onPress={() => { void handleSaveMyProfile(); }}
                                disabled={profileSaving}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-myinfo-save-button"
                                testID="worldlinco-myinfo-save-button"
                            >
                                <Text style={styles.inlineActionBtnText}>{profileSaving ? '저장 중...' : '프로필 기본값 저장'}</Text>
                            </Pressable>
                            {profileMessage ? (
                                <Text style={styles.myInfoText}>{profileMessage}</Text>
                            ) : null}
                            <View style={styles.myInfoActionRow}>
                                <Pressable style={styles.inlineGhostBtn} onPress={openPasswordChange} testID="worldlinco-password-change-open">
                                    <Text style={styles.inlineGhostBtnText}>🔒 비밀번호 변경</Text>
                                </Pressable>
                                {biometricLoginReady ? (
                                    <Pressable style={styles.inlineGhostBtn} onPress={() => { void handleToggleBiometricLogin(); }} testID="worldlinco-biometric-login-toggle">
                                        <Text style={styles.inlineGhostBtnText}>{biometricLoginEnabled ? '👆 지문 로그인 해제' : '👆 지문 빠른 로그인 설정'}</Text>
                                    </Pressable>
                                ) : null}
                            </View>
                            <Pressable style={styles.inlineActionBtn} onPress={handleShowPurchases}>
                                <Text style={styles.inlineActionBtnText}>{myPurchasesLoading ? '⏳ 불러오는 중...' : myPurchases !== null ? '📋 내역 닫기' : '📋 구매/예약 내역'}</Text>
                            </Pressable>
                            <Modal
                                visible={profileSelectionModal !== null}
                                transparent
                                animationType="fade"
                                onRequestClose={() => setProfileSelectionModal(null)}
                            >
                                <Pressable style={styles.langModalOverlay} onPress={() => setProfileSelectionModal(null)}>
                                    <Pressable style={styles.langModalCard} onPress={() => { }} testID="worldlinco-myinfo-selection-modal">
                                        <Text style={styles.langModalTitle}>
                                            {profileSelectionModal === 'language' ? '프로필 기본 언어 선택' : '프로필 국가 선택'}
                                        </Text>
                                        <Text style={styles.signupModalSub}>
                                            {profileSelectionModal === 'language'
                                                ? `지원 언어 ${SUPPORTED_LANGUAGE_COUNT}개 전체를 열어서 선택합니다.`
                                                : `서비스 국가 ${SIGNUP_COUNTRY_OPTION_CODES.length}개 전체를 열어서 선택합니다.`}
                                        </Text>
                                        <ScrollView style={styles.langModalList}>
                                            {profileSelectionModal === 'language'
                                                ? LANGS.map((lang) => (
                                                    (() => {
                                                        const active = lang.code === profilePreferredLanguage;
                                                        return (
                                                            <Pressable
                                                                key={`myinfo-lang-${lang.code}`}
                                                                style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                                                onPress={() => handleSelectProfileLanguage(lang.code)}
                                                                testID={`worldlinco-myinfo-language-${lang.code}`}
                                                            >
                                                                <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>{lang.label}</Text>
                                                                {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                                            </Pressable>
                                                        );
                                                    })()
                                                ))
                                                : SIGNUP_COUNTRY_OPTION_CODES.map((countryCode) => (
                                                    (() => {
                                                        const active = countryCode === profileCountryCode;
                                                        return (
                                                            <Pressable
                                                                key={`myinfo-country-${countryCode}`}
                                                                style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                                                onPress={() => handleSelectProfileCountry(countryCode)}
                                                                testID={`worldlinco-myinfo-country-${countryCode}`}
                                                            >
                                                                <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>{resolveCountryFlag(countryCode)} {resolveCountryName(countryCode)}</Text>
                                                                {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                                            </Pressable>
                                                        );
                                                    })()
                                                ))}
                                        </ScrollView>
                                        <Pressable
                                            style={styles.langModalCloseBtn}
                                            onPress={() => setProfileSelectionModal(null)}
                                            testID="worldlinco-myinfo-selection-close"
                                        >
                                            <Text style={styles.langModalCloseText}>닫기</Text>
                                        </Pressable>
                                    </Pressable>
                                </Pressable>
                            </Modal>
                            {myPurchases !== null && (
                                <View style={styles.purchaseListWrap}>
                                    {myPurchases.length === 0 ? (
                                        <Text style={styles.purchaseItemText}>구매 내역이 없습니다.</Text>
                                    ) : (
                                        myPurchases.map((item) => (
                                            <Text key={`purchase-${item.id}`} style={styles.purchaseItemText}>#{item.id} · {Number(item.amount).toLocaleString('ko-KR')}원 · {item.status}</Text>
                                        ))
                                    )}
                                </View>
                            )}
                        </View>
                    )}
                </View>

                {isLobbyVisible ? (
                    <View style={styles.lobbyShell}>
                        <View style={styles.lobbyHeroCard}>
                            <Text style={styles.lobbyHeroEyebrow}>WorldLinco Lobby</Text>
                            <Text style={styles.lobbyHeroTitle}>로그인 또는 회원가입 후 레일별 개별 창으로 전환됩니다.</Text>
                            <Text style={styles.lobbyHeroBody}>
                                로비는 인증만 담당합니다. 로그인 후에는 번역 홈, 채팅, VoIP, 노래, 예약이 각각 단일 작업창으로 열립니다.
                            </Text>
                        </View>
                        <View style={styles.lobbyPreviewGrid}>
                            <View style={styles.lobbyPreviewCard}>
                                <Text style={styles.lobbyPreviewIcon}>💬</Text>
                                <Text style={styles.lobbyPreviewTitle}>채팅 레일</Text>
                                <Text style={styles.lobbyPreviewBody}>채팅방, 친구, 친구 찾기를 한 창으로 묶어 엽니다.</Text>
                            </View>
                            <View style={styles.lobbyPreviewCard}>
                                <Text style={styles.lobbyPreviewIcon}>📞</Text>
                                <Text style={styles.lobbyPreviewTitle}>VoIP 레일</Text>
                                <Text style={styles.lobbyPreviewBody}>통화 준비, 수신, 활성 통화를 독립 화면으로 유지합니다.</Text>
                            </View>
                            <View style={styles.lobbyPreviewCard}>
                                <Text style={styles.lobbyPreviewIcon}>🎵</Text>
                                <Text style={styles.lobbyPreviewTitle}>노래 레일</Text>
                                <Text style={styles.lobbyPreviewBody}>노래 파일, 자막, voice preview를 한 화면에서 다룹니다.</Text>
                            </View>
                            <View style={styles.lobbyPreviewCard}>
                                <Text style={styles.lobbyPreviewIcon}>🧳</Text>
                                <Text style={styles.lobbyPreviewTitle}>예약 레일</Text>
                                <Text style={styles.lobbyPreviewBody}>주변 검색과 예약/결제를 여행 예약 창으로 분리합니다.</Text>
                            </View>
                        </View>
                    </View>
                ) : null}

                {showIncomingVoipBanner && pendingIncomingVoipCall ? (
                    <View style={styles.voipIncomingBanner}>
                        <View style={styles.voipIncomingBannerHeader}>
                            <Text style={styles.voipIncomingBannerTitle}>수신 보이스톡 대기</Text>
                            <Pressable onPress={() => restoreVoipRailState('incoming_banner_open')} style={styles.inlineGhostBtn}>
                                <Text style={styles.inlineGhostBtnText}>VoIP 레일 열기</Text>
                            </Pressable>
                        </View>
                        <Text style={styles.voipIncomingBannerBody}>
                            {pendingIncomingVoipCall.caller_label || pendingIncomingVoipCall.display_label || pendingIncomingVoipCall.caller_voice_id || '상대방'} 님이 통화를 요청했습니다. 앱을 다시 열거나 다른 레일에 있어도 이 배너와 VoIP 레일에서 바로 이어받을 수 있습니다.
                        </Text>
                        <View style={styles.voipIncomingBannerMetaRow}>
                            <Text style={styles.voipIncomingBannerMeta}>call_id: {pendingIncomingVoipCall.call_id}</Text>
                            <Text style={styles.voipIncomingBannerMeta}>{formatUnifiedCallModeText(pendingIncomingVoipCall.requested_mode, pendingIncomingVoipCall.resolved_mode)}</Text>
                        </View>
                        {voipStatusMessage ? <Text style={styles.songModeMetaText}>{voipStatusMessage}</Text> : null}
                        {voipInitError ? <Text style={styles.errorText}>{voipInitError}</Text> : null}
                        <View style={styles.voipLobbyActionRow}>
                            <Pressable
                                style={styles.inlineActionBtn}
                                onPressIn={() => {
                                    logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_IN', {
                                        source_variant: 'incoming_banner',
                                        pending_call_id: pendingIncomingVoipCall.call_id,
                                    });
                                }}
                                onPressOut={() => {
                                    logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_OUT', {
                                        source_variant: 'incoming_banner',
                                        pending_call_id: pendingIncomingVoipCall.call_id,
                                    });
                                }}
                                onPress={() => handleIncomingAcceptPress('incoming_banner')}
                                testID="worldlinco-voip-incoming-accept-banner"
                                accessibilityLabel="수신 보이스톡 받기"
                            >
                                <Text style={styles.inlineActionBtnText}>받기</Text>
                            </Pressable>
                            <Pressable
                                style={styles.inlineGhostBtn}
                                onPress={() => { void handleRejectIncomingVoipCall(); }}
                                testID="worldlinco-voip-incoming-reject-banner"
                                accessibilityLabel="수신 보이스톡 거절"
                            >
                                <Text style={styles.inlineGhostBtnText}>거절</Text>
                            </Pressable>
                        </View>
                    </View>
                ) : null}

                <Modal
                    visible={showFriendFolder}
                    transparent
                    animationType="slide"
                    onRequestClose={() => handleCloseFriendFolder('modal_request_close')}
                >
                    <ImageBackground source={SKY_BG} resizeMode="cover" style={styles.voipModalOverlay}>
                        <View style={[styles.voipModalCard, { paddingTop: 0 }]}>
                            <View style={styles.modalCloseRow}>
                                <Pressable onPress={() => handleCloseFriendFolder('modal_close_button')} style={styles.friendModalCloseBtn}>
                                    <Text style={styles.friendModalCloseBtnText}>✕ 닫기</Text>
                                </Pressable>
                            </View>
                            {userInfo ? (
                                <View style={styles.friendModalBody}>
                                    <FriendFolderScreen
                                        userId={userInfo.id}
                                        token={token ?? ''}
                                        currentUserEmail={userInfo.email}
                                        visible={showFriendFolder}
                                        autoCallVoiceId={voipAutoCallVoiceId}
                                        onAutoCallConsumed={() => setVoipAutoCallVoiceId(null)}
                                        onOpenMapDiscovery={handleOpenFriendMapFromFolder}
                                        onFriendSelected={(friend) => {
                                            setVoipAutoCallVoiceId(null);
                                            logUiPressProbe('VOIP_FRIEND_SELECTED', {
                                                friend_id: friend.id,
                                                friend_name: friend.friendUsername,
                                                friend_phone: friend.friendPhone ?? null,
                                                friend_voice_id: friend.friendVoiceId ?? null,
                                            });
                                            void handleStartFriendVoiceCall(friend);  // NOSONAR
                                        }}
                                    />
                                </View>
                            ) : null}
                        </View>
                    </ImageBackground>
                </Modal>

                <Modal
                    visible={showPhoneDialerModal}
                    animationType="slide"
                    onRequestClose={() => setShowPhoneDialerModal(false)}
                >
                    <PhoneDialer
                        defaultPhone={interCallPhone || voipPhone || '+82-'}
                        onCallInitiated={(phone) => { void handlePhoneDialerInitiated(phone); }}
                        onCancel={() => setShowPhoneDialerModal(false)}
                    />
                </Modal>

                <Modal
                    visible={showFriendMapDiscovery}
                    transparent
                    animationType="slide"
                    onRequestClose={() => setShowFriendMapDiscovery(false)}
                >
                    <ImageBackground source={SKY_BG} resizeMode="cover" style={styles.voipModalOverlay}>
                        <View style={[styles.voipModalCard, { paddingTop: 0 }]}>
                            <View style={styles.modalCloseRow}>
                                <Pressable onPress={() => setShowFriendMapDiscovery(false)} style={styles.friendModalCloseBtn}>
                                    <Text style={styles.friendModalCloseBtnText}>✕ 닫기</Text>
                                </Pressable>
                            </View>
                            {userInfo ? (
                                <FriendMapDiscoveryScreen
                                    token={token ?? ''}
                                    nickname={userInfo.username || userInfo.email.split('@')[0]}
                                    gender={resolveDiscoveryGenderFromProfile(voipProfileGender)}
                                    autoMode
                                    onFriendAccepted={handleFriendAcceptedFromDiscovery}
                                />
                            ) : null}
                        </View>
                    </ImageBackground>
                </Modal>

                {isTranslateWorkspaceVisible ? (
                    <>
                        {/* ── 홈 런처 (mockup #1) ── */}
                        <View style={styles.homeGreetingWrap}>
                            <Text style={styles.homeGreeting}>안녕하세요! 👋</Text>
                            <Text style={styles.homeGreetingSub}>오늘도 좋은 하루 보내세요.</Text>
                        </View>

                        <Pressable
                            style={styles.faceHeroCard}
                            onPress={() => setFaceScreenOpen(true)}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-home-face-hero"
                            testID="worldlinco-home-face-hero"
                        >
                            <Text style={styles.faceHeroTitle}>대면 통역</Text>
                            <Text style={styles.faceHeroSub}>Face-to-face Interpretation</Text>
                            <View style={styles.faceHeroFlagRow}>
                                <View style={styles.faceHeroLangCol}>
                                    <Text style={styles.faceHeroFlag}>{homeFromFlag}</Text>
                                    <Text style={styles.faceHeroLangLabel}>{currentFromLabel}</Text>
                                </View>
                                <Text style={styles.faceHeroSwap}>⇄</Text>
                                <View style={styles.faceHeroLangCol}>
                                    <Text style={styles.faceHeroFlag}>{homeToFlag}</Text>
                                    <Text style={styles.faceHeroLangLabel}>{currentToLabel}</Text>
                                </View>
                            </View>
                            <View style={[styles.faceHeroMic, autoVoiceModeEnabled && styles.faceHeroMicActive]}>
                                <Text style={styles.faceHeroMicIcon}>🎙️</Text>
                            </View>
                            <Text style={styles.faceHeroCta}>
                                {autoVoiceModeEnabled ? '대화 통역 ON · 탭하여 끄기' : '탭하여 시작'}
                            </Text>
                        </Pressable>

                        <View style={styles.homeQuickRow}>
                            <Pressable
                                style={styles.homeQuickBtn}
                                onPress={() => setActiveRailSection('voip')}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-home-quick-voip"
                                testID="worldlinco-home-quick-voip"
                            >
                                <Text style={styles.homeQuickIcon}>📞</Text>
                                <View style={{ flex: 1 }}>
                                    <Text style={styles.homeQuickTitle}>통화하기</Text>
                                    <Text style={styles.homeQuickSub}>AI 통역 통화</Text>
                                </View>
                            </Pressable>
                            <Pressable
                                style={styles.homeQuickBtn}
                                onPress={() => setActiveRailSection('chat')}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-home-quick-chat"
                                testID="worldlinco-home-quick-chat"
                            >
                                <Text style={styles.homeQuickIcon}>💬</Text>
                                <View style={{ flex: 1 }}>
                                    <Text style={styles.homeQuickTitle}>채팅하기</Text>
                                    <Text style={styles.homeQuickSub}>실시간 번역 채팅</Text>
                                </View>
                            </Pressable>
                        </View>

                        <Pressable
                            style={styles.homeFavRow}
                            onPress={() => setHomeToolsExpanded((v) => !v)}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-home-tools-toggle"
                            testID="worldlinco-home-tools-toggle"
                        >
                            <Text style={styles.homeFavIcon}>⭐</Text>
                            <View style={{ flex: 1 }}>
                                <Text style={styles.homeFavTitle}>정밀 번역 도구</Text>
                                <Text style={styles.homeFavSub}>직접 입력·이미지(OCR) 번역을 펼쳐보세요</Text>
                            </View>
                            <Text style={styles.homeFavChevron}>{homeToolsExpanded ? '∧' : '〉'}</Text>
                        </Pressable>

                        {homeToolsExpanded ? (
                        <>
                        <View style={styles.translationHub}>
                            {Platform.OS !== 'web' ? (
                                <Pressable
                                    style={[styles.faceConversationToggleBtn, autoVoiceModeEnabled && styles.faceConversationToggleBtnActive]}
                                    onPress={() => { void handleToggleFaceConversation(); }}  // NOSONAR
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-face-conversation-toggle"
                                    testID="worldlinco-face-conversation-toggle"
                                >
                                    <Text style={[styles.faceConversationToggleText, autoVoiceModeEnabled && styles.faceConversationToggleTextActive]}>
                                        {autoVoiceModeEnabled
                                            ? (getUiText(fromLang).faceConversationOn ?? '🎙️ 대화 통역 ON')
                                            : (getUiText(fromLang).faceConversationOff ?? '대화 통역 OFF')}
                                    </Text>
                                </Pressable>
                            ) : null}

                            {Platform.OS !== 'web' && autoVoiceModeEnabled ? (
                                <Text style={styles.faceVadHintText}>
                                    {getUiText(fromLang).faceVadHint ?? 'VoIP와 같이 말이 끝날 때까지 마이크가 켜져 있습니다.'}
                                </Text>
                            ) : null}

                            <View style={styles.labelRow}>
                                <Text style={styles.label}>{getUiText(fromLang).profileLanguageLabel ?? '내 언어 (프로필)'}</Text>
                                <Text style={styles.gpsAutoBadge}>{gpsLangLoading ? '📍 위치 확인 중' : '🎙️ 자동 감지'}</Text>
                            </View>
                            {gpsStatus ? <Text style={styles.gpsStatusText}>{gpsStatus}</Text> : null}
                            <View style={styles.langAutoChip}>
                                <Text style={styles.langAutoChipValue}>{currentFromLabel}</Text>
                                <Text style={styles.langAutoChipHint}>{getUiText(fromLang).profileLanguageHint ?? '프로필 저장값'}</Text>
                            </View>

                            {/* ── 입력 영역 ── */}
                            <View style={styles.inputBox}>
                                <TextInput
                                    style={styles.textInput}
                                    multiline
                                    placeholder={getUiText(fromLang).inputPlaceholder}
                                    placeholderTextColor={C.sub}
                                    showSoftInputOnFocus
                                    value={inputText}
                                    onChangeText={setInputText}
                                />
                                {inputText.length > 0 ? (
                                    <View style={styles.inputBtnRow}>
                                        <Pressable style={styles.speakBtn} onPress={() => handleSpeak(inputText, fromLang)}>
                                            <Text style={styles.speakIcon}>🔊</Text>
                                        </Pressable>
                                    </View>
                                ) : null}
                            </View>

                            {!userInfo ? (
                                <View style={styles.actionRow}>
                                    <Pressable style={styles.swapBtn} onPress={handleSwap}>
                                        <Text style={styles.swapText}>{getUiText(fromLang).swap}</Text>
                                    </Pressable>
                                </View>
                            ) : null}

                            {Platform.OS !== 'web' && !autoVoiceModeEnabled ? (
                                <View style={styles.autoVoiceModeWrap}>
                                    <Text style={styles.autoVoiceModeStatus}>{getUiText(fromLang).manualVoiceOnlyNotice}</Text>
                                </View>
                            ) : null}
                        </View>

                        <View>
                            {/* ── 상대 언어 ── */}
                            <Text style={styles.label}>{getUiText(fromLang).peerLanguageLabel ?? '상대 언어 (GPS/수동)'}</Text>
                            <Pressable style={styles.langAutoChip} onPress={() => setLangPickerFor('to')}>
                                <Text style={styles.langAutoChipValue}>{currentToLabel}</Text>
                                <Text style={styles.langAutoChipHint}>{getUiText(fromLang).peerLanguageHint ?? 'GPS 우선 · 필요 시 수동'}</Text>
                            </Pressable>

                            {/* ── 결과 영역 ── */}
                            <View style={[styles.inputBox, styles.resultBox]}>
                                <Text style={resultText ? styles.resultText : styles.resultPlaceholder}>
                                    {resultText || getUiText(fromLang).resultPlaceholder}
                                </Text>
                                {resultText.length > 0 && (
                                    <Pressable style={styles.speakBtn} onPress={() => handleSpeak(resultText, toLang)}>
                                        <Text style={styles.speakIcon}>🔊</Text>
                                    </Pressable>
                                )}
                            </View>
                            <View style={styles.ocrCard}>
                                <Text style={styles.ocrTitle}>{getUiText(fromLang).ocrTitle}</Text>
                                <Text style={styles.ocrSubtitle}>{getUiText(fromLang).ocrSubtitle}</Text>
                                <Pressable
                                    style={[styles.inlineActionBtn, ocrLoading && styles.inlineGhostBtnDisabled]}
                                    onPress={handlePickImageOcr}
                                    disabled={ocrLoading}
                                >
                                    {ocrLoading ? <ActivityIndicator color="#79c0ff" size="small" /> : <Text style={styles.inlineActionBtnText}>{getUiText(fromLang).ocrPickImage}</Text>}
                                </Pressable>
                                {ocrImageName ? (
                                    <View style={styles.mediaMetaCard}>
                                        <View style={styles.mediaThumbBox}>
                                            <Text style={styles.mediaThumbEmoji}>🖼️</Text>
                                            <Text style={styles.mediaThumbCaption}>IMG</Text>
                                        </View>
                                        <View style={styles.mediaMetaBody}>
                                            <Text style={styles.mediaMetaTitle}>{ocrImageName}</Text>
                                            <View style={styles.mediaBadgeRow}>
                                                <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{getLangLabel(fromLang)}</Text></View>
                                                <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{getLangLabel(toLang)}</Text></View>
                                                <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>OCR</Text></View>
                                            </View>
                                            <Text style={styles.songModeMetaText}>{getUiText(fromLang).ocrSelectedFile.replace('{file}', ocrImageName)}</Text>
                                        </View>
                                    </View>
                                ) : null}
                                {ocrError ? <Text style={styles.errorText}>{ocrError}</Text> : null}
                                {ocrExtractedText ? (
                                    <View style={styles.ocrPreviewBox}>
                                        <Text style={styles.successTitle}>{getUiText(fromLang).ocrExtractedTitle}</Text>
                                        <Text style={styles.successText}>{ocrExtractedText}</Text>
                                    </View>
                                ) : null}
                                {ocrTranslatedText ? (
                                    <View style={styles.ocrPreviewBox}>
                                        <Text style={styles.successTitle}>{getUiText(fromLang).ocrTranslatedTitle}</Text>
                                        <Text style={styles.successText}>{ocrTranslatedText}</Text>
                                    </View>
                                ) : null}
                            </View>

                            {/* ── 오프라인 안내 ── */}
                            {offline && (
                                <View style={styles.offlineBanner}>
                                    <Text style={styles.offlineText}>
                                        {getUiText(fromLang).offlineMsg}
                                    </Text>
                                </View>
                            )}

                        </View>
                        </>
                        ) : null}
                    </>
                ) : null}

                {isChatRailSectionVisible ? (
                    <View
                        accessibilityLabel="worldlinco-section-rail-chat"
                        testID="worldlinco-section-rail-chat"
                        onLayout={(event) => {
                            railSectionOffsetRef.current.chat = event.nativeEvent.layout.y;
                            if (activeRailSection === 'chat') {
                                scrollToRailSection('chat');
                            }
                        }}
                        style={[styles.sectionCard, activeRailSection === 'chat' && styles.sectionCardActive]}
                    >
                        <Text style={[styles.sectionTitle, { color: '#1E6FE0' }]}>💬 채팅 + 친구 허브</Text>
                        {token && userInfo ? (
                                <>
                                    {/* 빠른 작업(액션 타일)을 목록 위로 올려 한눈에 접근 — 사용 편의 우선(APP_DESIGN 6) */}
                                    <View style={styles.sectionCard}>
                                        <View style={styles.hubHeroRow}>
                                            <View style={[styles.hubHeroIcon, { backgroundColor: '#1E6FE0' }]}><Text style={styles.hubHeroEmoji}>💬</Text></View>
                                            <Text style={styles.hubHeroTitle}>친구와 실시간 번역 대화</Text>
                                        </View>
                                        <View style={styles.actionTileGrid2}>
                                            <Pressable
                                                style={styles.gridTile}
                                                onPress={() => setContactsDirectoryVisible(true)}
                                                accessibilityRole="button"
                                                accessibilityLabel="전화번호로 찾기"
                                                testID="worldlinco-chat-action-phone"
                                            >
                                                <View style={[styles.gridTileIcon, { backgroundColor: '#1E6FE0' }]}><Text style={styles.gridTileEmoji}>📇</Text></View>
                                                <Text style={styles.gridTileLabel}>전화번호로 찾기</Text>
                                                <Text style={styles.gridTileSub}>번호로 친구 추가</Text>
                                            </Pressable>
                                            <Pressable
                                                style={styles.gridTile}
                                                onPress={() => handleOpenFriendMapFromFolder()}
                                                accessibilityRole="button"
                                                accessibilityLabel="지도로 찾기"
                                                testID="worldlinco-chat-action-map"
                                            >
                                                <View style={[styles.gridTileIcon, { backgroundColor: '#1E6FE0' }]}><Text style={styles.gridTileEmoji}>🗺️</Text></View>
                                                <Text style={styles.gridTileLabel}>지도로 찾기</Text>
                                                <Text style={styles.gridTileSub}>주변 친구 탐색</Text>
                                            </Pressable>
                                            <Pressable
                                                style={[styles.gridTile, showFriendFolder && styles.gridTileActive]}
                                                onPress={() => handlePressFriendEntry('friend-folder')}
                                                accessibilityRole="button"
                                                accessibilityLabel="채팅하기"
                                                testID="worldlinco-chat-friend-folder-open"
                                            >
                                                <View style={[styles.gridTileIcon, { backgroundColor: '#1E6FE0' }]}><Text style={styles.gridTileEmoji}>💬</Text></View>
                                                <Text style={styles.gridTileLabel}>채팅하기</Text>
                                                <Text style={styles.gridTileSub}>1:1 대화</Text>
                                            </Pressable>
                                            <Pressable
                                                style={styles.gridTile}
                                                onPress={() => {
                                                    // 타일은 채팅 허브 내부에서만 노출되므로 레일 토글 없이 그룹 작성기만 펼친다.
                                                    setShowFriendFolder(false);
                                                    setGroupComposerSignal((n) => n + 1);
                                                }}
                                                accessibilityRole="button"
                                                accessibilityLabel="단체채팅 만들기"
                                                testID="worldlinco-chat-action-group"
                                            >
                                                <View style={[styles.gridTileIcon, { backgroundColor: '#1E6FE0' }]}><Text style={styles.gridTileEmoji}>👥</Text></View>
                                                <Text style={styles.gridTileLabel}>단체채팅</Text>
                                                <Text style={styles.gridTileSub}>그룹 만들기</Text>
                                            </Pressable>
                                        </View>
                                        {showFriendMapDiscovery && userInfo ? (
                                            <View style={styles.sectionCard}>
                                                <Text style={styles.sectionTitle}>🗺️ 주변 친구 찾기</Text>
                                                <Text style={styles.sectionSub}>근처 사용자 탐색과 친구 수락 흐름을 채팅 레일 안에서 이어갑니다.</Text>
                                                <FriendMapDiscoveryScreen
                                                    token={token}
                                                    nickname={userInfo.username || userInfo.email.split('@')[0]}
                                                    gender={resolveDiscoveryGenderFromProfile(voipProfileGender)}
                                                    autoMode
                                                    onFriendAccepted={handleFriendAcceptedFromDiscovery}
                                                />
                                            </View>
                                        ) : null}
                                    </View>
                                    <ChatRoomListScreen
                                        apiBaseUrl={API_BASE}
                                        token={token}
                                        userId={userInfo.id}
                                        visible={isChatRailSectionVisible}
                                        refreshKey={chatRefreshKey}
                                        onOpenRoom={handleOpenChatRoom}
                                        autoCallVoiceId={showFriendFolder ? null : voipAutoCallVoiceId}
                                        onAutoCallConsumed={() => setVoipAutoCallVoiceId(null)}
                                        onStartFriendVoiceCall={(friend) => void handleStartFriendVoiceCall(friend)}
                                        openGroupSignal={groupComposerSignal}
                                    />
                                </>
                        ) : (
                            renderSectionConnectionCard({
                                sectionKey: 'chat',
                                title: '로그인 후 채팅, 친구 목록, 친구 찾기가 함께 열립니다',
                                body: '현재 상태에서는 채팅방 목록과 친구 허브가 비어 보일 수 있습니다. 데모 세션을 연결하면 실제 토큰으로 방 목록, 그룹방, 친구 찾기, 번역 공유 흐름을 같은 레일에서 바로 검증할 수 있습니다.',
                                bullets: ['채팅방 목록과 번역 보관함 자동 연결', '친구 목록/친구 찾기 허브 동시 검증', 'OCR/노래 번역 공유 메시지 검증'],
                                loginSource: 'chat_section_gate',
                            })
                        )}
                    </View>
                ) : null}

                {voipCallInitResponse && !isVoipRailSectionVisible ? (
                    <View style={styles.voipActiveCallBanner}>
                        <View style={styles.voipIncomingBannerHeader}>
                            <Text style={styles.voipIncomingBannerTitle}>실시간 VoIP 통화 유지 중</Text>
                            <Pressable onPress={() => restoreVoipRailState('active_call_banner_return')} style={styles.inlineActionBtn}>
                                <Text style={styles.inlineActionBtnText}>통화 화면 복귀</Text>
                            </Pressable>
                        </View>
                        <Text style={styles.voipIncomingBannerBody}>
                            현재 통화는 백그라운드로 유지되고 있습니다. 다른 레일을 보다가도 VoIP 레일로 돌아오면 같은 통화 화면 상태를 이어서 확인할 수 있습니다.
                        </Text>
                        <View style={styles.voipIncomingBannerMetaRow}>
                            <Text style={styles.voipIncomingBannerMeta}>call_id: {voipCallInitResponse.call_id}</Text>
                            <Text style={styles.voipIncomingBannerMeta}>{formatUnifiedCallModeText(voipCallInitResponse.requested_mode, voipCallInitResponse.resolved_mode)}</Text>
                        </View>
                    </View>
                ) : null}

                {voipCallInitResponse ? (
                    <View
                        onLayout={(event) => {
                            if (isVoipRailSectionVisible) {
                                railSectionOffsetRef.current.voip = event.nativeEvent.layout.y;
                            }
                        }}
                        style={isVoipRailSectionVisible ? styles.voipRailLiveScreenWrap : styles.voipPersistentCallHiddenHost}
                        pointerEvents={isVoipRailSectionVisible ? 'auto' : 'none'}
                    >
                        {isVoipRailSectionVisible ? (
                            <>
                                <Text style={styles.sectionTitle}>📞 실시간 VoIP 통화</Text>
                                <Text style={styles.sectionSub}>활성 통화 화면을 유지한 채 다른 레일로 이동했다가 다시 돌아와도 같은 세션을 이어서 보여줍니다.</Text>
                            </>
                        ) : null}
                        <View style={isVoipRailSectionVisible ? styles.voipModalScreenWrap : styles.voipPersistentCallHiddenScreenWrap}>
                            <VoipCallErrorBoundary
                                key={voipCallInitResponse.call_id}
                                onRecover={handleReturnToVoipDialer}
                            >
                                <VoIPCallScreen
                                    callInitResponse={voipCallInitResponse}
                                    calleePhone={voipActiveProfile?.nickname || voipCallInitResponse.display_label || voipPhone.trim() || '보이스톡 연결'}
                                    participantProfile={voipActiveProfile ?? undefined}
                                    apiBaseUrl={API_BASE}
                                    authToken={token}
                                    localSourceLang={effectiveVoipSourceLang}
                                    localTargetLang={effectiveVoipTargetLang}
                                    regionHint={resolveActiveRegionHint(effectiveVoipSourceLang)}
                                    onHangup={handleReturnToVoipDialer}
                                />
                            </VoipCallErrorBoundary>
                        </View>
                    </View>
                ) : null}

                {isVoipRailSectionVisible ? (
                    <View
                        onLayout={(event) => {
                            if (!voipCallInitResponse) {
                                railSectionOffsetRef.current.voip = event.nativeEvent.layout.y;
                            }
                            if (activeRailSection === 'voip') {
                                scrollToRailSection('voip');
                            }
                        }}
                        style={[styles.sectionCard, activeRailSection === 'voip' && styles.sectionCardActive]}
                    >
                        <View style={styles.hubHeroRow}>
                            <View style={[styles.hubHeroIcon, { backgroundColor: '#0B2E5E' }]}><Text style={styles.hubHeroEmoji}>📞</Text></View>
                            <Text style={styles.hubHeroTitle}>통역 통화로 언어 장벽 없이</Text>
                        </View>
                        <View style={styles.voipTileList}>
                            <Pressable
                                style={styles.voipTile}
                                onPress={() => setContactsDirectoryVisible(true)}
                                accessibilityRole="button"
                                accessibilityLabel="통역통화 걸기"
                                testID="worldlinco-voip-action-interpret-call"
                            >
                                <View style={[styles.actionTileIcon, { backgroundColor: '#0B2E5E' }]}><Text style={styles.actionTileEmoji}>📞</Text></View>
                                <View style={styles.actionTileTextWrap}>
                                    <Text style={styles.actionTileLabel}>통역통화 걸기</Text>
                                    <Text style={styles.actionTileSub}>상대 선택 후 실시간 통역</Text>
                                </View>
                                <Text style={styles.voipTileChevron}>›</Text>
                            </Pressable>
                            <Pressable
                                style={styles.voipTile}
                                onPress={() => setShowPhoneDialerModal(true)}
                                accessibilityRole="button"
                                accessibilityLabel="일반전화 PSTN"
                                testID="worldlinco-voip-action-pstn"
                            >
                                <View style={[styles.actionTileIcon, { backgroundColor: '#0B2E5E' }]}><Text style={styles.actionTileEmoji}>☎️</Text></View>
                                <View style={styles.actionTileTextWrap}>
                                    <Text style={styles.actionTileLabel}>일반전화 (PSTN)</Text>
                                    <Text style={styles.actionTileSub}>번호로 바로 걸기</Text>
                                </View>
                                <Text style={styles.voipTileChevron}>›</Text>
                            </Pressable>
                        </View>
                        <Pressable
                            style={styles.voipPreviewLink}
                            onPress={() => setVoipPreviewOpen(true)}
                            accessibilityRole="button"
                            accessibilityLabel="통화화면 디자인 미리보기"
                            testID="worldlinco-voip-design-preview"
                        >
                            <Text style={styles.voipPreviewLinkText}>🎨 통화화면 미리보기</Text>
                        </Pressable>
                        <CallModePolicyBanner />
                        <NetworkTestBanner snapshot={networkDiagnostics} showFieldTestHints={AUTH_DEBUG_MARKER_ENABLED} />
                        <Text style={styles.songModeMetaText}>현재 통화 모드: {callModeLabel}</Text>
                        <View style={styles.voipQuickMetaRow}>
                            <Text style={styles.voipQuickMetaText}>현재 버전: {APP_VERSION_LABEL}</Text>
                            <Text style={styles.voipQuickMetaText}>상태: {token ? '로그인 완료' : '로그인 필요'}</Text>
                            <Text style={styles.voipQuickMetaText}>VoIP 플랜: {effectiveVoipPlan ? (isInstantDemoSession && !activeVoipPlan ? '데모 세션' : MONETIZATION_PLAN_CONFIG[effectiveVoipPlan].shortLabel) : '미가입'}</Text>
                        </View>
                        <View style={styles.voipLocalLangCard}>
                            <Text style={styles.voipLocalLangTitle}>🌐 통역 지정 언어(이 단말)</Text>
                            <Text style={styles.voipLocalLangSub}>
                                내가 말하고 받을 언어를 이 단말에서 직접 지정합니다. 지정한 언어만 흡수하고 그 외 언어는 잡음으로 무시합니다. 상대 언어는 통화 중 자동으로 학습됩니다. 지원 {SUPPORTED_LANGUAGE_COUNT}개 언어.
                            </Text>
                            <Pressable
                                style={styles.voipLocalLangTrigger}
                                onPress={() => setVoipLangModalVisible(true)}
                                accessibilityLabel="worldlinco-voip-local-lang-trigger"
                                testID="worldlinco-voip-local-lang-trigger"
                            >
                                <View>
                                    <Text style={styles.voipLocalLangValue}>{getLangLabelText(effectiveVoipSourceLang)}</Text>
                                    <Text style={styles.voipLocalLangMeta}>
                                        {isVoipLangLocallyOverridden ? '로컬 직접 지정됨' : `백엔드 프로필 기본값(${getLangLabelText(currentVoipPreferredLanguage)})`}
                                    </Text>
                                </View>
                                <Text style={styles.voipLocalLangHint}>변경</Text>
                            </Pressable>
                            {isVoipLangLocallyOverridden ? (
                                <Pressable
                                    style={styles.voipLocalLangResetBtn}
                                    onPress={handleClearVoipLocalLang}
                                    accessibilityLabel="worldlinco-voip-local-lang-reset"
                                    testID="worldlinco-voip-local-lang-reset"
                                >
                                    <Text style={styles.voipLocalLangResetText}>백엔드 프로필 언어로 되돌리기</Text>
                                </Pressable>
                            ) : null}
                        </View>
                        <Modal
                            visible={voipLangModalVisible}
                            transparent
                            animationType="fade"
                            onRequestClose={() => setVoipLangModalVisible(false)}
                        >
                            <Pressable style={styles.langModalOverlay} onPress={() => setVoipLangModalVisible(false)}>
                                <Pressable style={styles.langModalCard} onPress={() => { }} testID="worldlinco-voip-local-lang-modal">
                                    <Text style={styles.langModalTitle}>통역 지정 언어 선택</Text>
                                    <Text style={styles.signupModalSub}>지원 언어 {SUPPORTED_LANGUAGE_COUNT}개 전체에서 이 단말이 사용할 언어를 선택합니다.</Text>
                                    <ScrollView style={styles.langModalList}>
                                        {LANGS.map((language) => {
                                            const active = effectiveVoipSourceLang === language.code;
                                            return (
                                                <Pressable
                                                    key={`voip-local-language-option-${language.code}`}
                                                    style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                                    onPress={() => handleSelectVoipLocalLang(language.code)}
                                                    accessibilityLabel={`worldlinco-voip-local-language-${language.code}`}
                                                    testID={`worldlinco-voip-local-language-${language.code}`}
                                                >
                                                    <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>
                                                        {language.label}
                                                    </Text>
                                                    {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                                </Pressable>
                                            );
                                        })}
                                    </ScrollView>
                                    <Pressable
                                        style={styles.langModalCloseBtn}
                                        onPress={() => setVoipLangModalVisible(false)}
                                        testID="worldlinco-voip-local-lang-close"
                                    >
                                        <Text style={styles.langModalCloseText}>닫기</Text>
                                    </Pressable>
                                </Pressable>
                            </Pressable>
                        </Modal>
                        {showIncomingVoipRailCard ? (
                            <View style={styles.voipIncomingRailCard}>
                                <Text style={styles.sectionTitle}>📲 수신 보이스톡</Text>
                                <Text style={styles.sectionSub}>수신 프롬프트를 모달 대신 VoIP 레일 상단 카드로 고정했습니다. 여기서 바로 수락하거나 거절할 수 있습니다.</Text>
                                <View style={styles.voipProfileCard}>
                                    <Text style={styles.voipProfileTitle}>{voipActiveProfile?.countryFlag || '🌐'} {voipActiveProfile?.nickname || pendingIncomingVoipCall.caller_label || pendingIncomingVoipCall.display_label || pendingIncomingVoipCall.caller_voice_id || '수신 통화'}</Text>
                                    <Text style={styles.voipProfileMeta}>발신자: {pendingIncomingVoipCall.caller_label || pendingIncomingVoipCall.display_label || pendingIncomingVoipCall.caller_voice_id || '알 수 없음'}</Text>
                                    <Text style={styles.voipProfileMeta}>보이스 ID: {pendingIncomingVoipCall.caller_voice_id || pendingIncomingVoipCall.display_label || 'unknown-voice-id'}</Text>
                                    <Text style={styles.voipProfileMeta}>call_id: {pendingIncomingVoipCall.call_id}</Text>
                                    <Text style={styles.voipProfileMeta}>{formatUnifiedCallModeText(pendingIncomingVoipCall.requested_mode, pendingIncomingVoipCall.resolved_mode)}</Text>
                                    <Text style={styles.voipProfileMeta}>relay: {pendingIncomingVoipCall.auto_relay_requested ? '1' : '0'}/{pendingIncomingVoipCall.auto_relay_applied ? '1' : '0'}</Text>
                                </View>
                                {voipStatusMessage ? <Text style={styles.songModeMetaText}>{voipStatusMessage}</Text> : null}
                                {voipInitError ? <Text style={styles.errorText}>{voipInitError}</Text> : null}
                                <View style={styles.voipLobbyActionRow}>
                                    <Pressable
                                        style={styles.inlineActionBtn}
                                        onPressIn={() => {
                                            logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_IN', {
                                                source_variant: 'rail_card',
                                                pending_call_id: pendingIncomingVoipCall.call_id,
                                            });
                                        }}
                                        onPressOut={() => {
                                            logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_OUT', {
                                                source_variant: 'rail_card',
                                                pending_call_id: pendingIncomingVoipCall.call_id,
                                            });
                                        }}
                                        onPress={() => handleIncomingAcceptPress('rail_card')}
                                        testID="worldlinco-voip-incoming-accept-rail"
                                        accessibilityLabel="수신 보이스톡 받기"
                                    >
                                        <Text style={styles.inlineActionBtnText}>받기</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.inlineGhostBtn}
                                        onPress={() => { void handleRejectIncomingVoipCall(); }}
                                        testID="worldlinco-voip-incoming-reject-rail"
                                        accessibilityLabel="수신 보이스톡 거절"
                                    >
                                        <Text style={styles.inlineGhostBtnText}>거절</Text>
                                    </Pressable>
                                </View>
                            </View>
                        ) : null}
                        {isVoipRailLobbyVisible ? (
                            <View style={styles.voipRailWorkspaceCard}>
                                <Text style={styles.sectionTitle}>📞 VoIP 준비 화면</Text>
                                <Text style={styles.sectionSub}>통화 시작 전 설정, 친구 진입, 최근 감사 로그를 이 레일 안에서 확인합니다.</Text>
                                <Text style={styles.voipLobbyModeText}>현재 통화 모드: {callModeLabel}</Text>
                                <Text style={styles.voipLobbyFlowHint}>순서: 채팅 레일에서 친구 등록 또는 수락 → 친구 목록 선택 → 보이스톡 시작</Text>
                                <View style={styles.voipLobbyActionRow}>
                                    <Pressable
                                        style={styles.inlineActionBtn}
                                        onPress={() => {
                                            setShowFriendFolder(true);
                                            setShowFriendMapDiscovery(false);
                                        }}
                                        testID="worldlinco-voip-lobby-friend-folder-open"
                                        accessibilityLabel="친구 목록 열기"
                                    >
                                        <Text style={styles.inlineActionBtnText}>친구 목록 열기</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.inlineGhostBtn}
                                        onPress={() => {
                                            setActiveRailSection('chat');
                                            setShowFriendFolder(false);
                                            setShowFriendMapDiscovery(true);
                                        }}
                                    >
                                        <Text style={styles.inlineGhostBtnText}>친구 찾기 열기</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.inlineGhostBtn}
                                        onPress={handleCloseVoipTester}
                                        testID="worldlinco-voip-lobby-close"
                                        accessibilityLabel="준비 화면 닫기"
                                    >
                                        <Text style={styles.inlineGhostBtnText}>준비 화면 닫기</Text>
                                    </Pressable>
                                </View>
                                <View style={styles.voipProfileCard}>
                                    <Text style={styles.voipProfileTitle}>{currentVoipProfile.countryFlag} {currentVoipProfile.nickname}</Text>
                                    <Text style={styles.voipProfileMeta}>닉네임: {currentVoipProfile.nickname}</Text>
                                    <Text style={styles.voipProfileMeta}>기본 언어: {resolveLanguageLabel(currentVoipProfile.preferredLanguage)}</Text>
                                    <Text style={styles.voipProfileMeta}>보이스 ID: {currentVoipProfile.voiceId}</Text>
                                </View>
                                {voipInitError ? <Text style={styles.errorText}>{voipInitError}</Text> : null}
                                {voipInitLoading ? <ActivityIndicator color="#58c9ff" size="small" style={styles.voipLobbyLoading} /> : null}
                                {voipAuditCallId || voipAuditEvents.length ? (
                                    <View style={styles.voipAuditCard}>
                                        <View style={styles.voipAuditHeaderRow}>
                                            <Text style={styles.voipAuditTitle}>최근 통화 감사 로그</Text>
                                            {voipAuditCallId ? (
                                                <Pressable
                                                    style={styles.inlineGhostBtn}
                                                    onPress={() => {
                                                        void refreshVoipAudit(voipAuditCallId, { showLoading: true, force: true });  // NOSONAR
                                                    }}
                                                >
                                                    <Text style={styles.inlineGhostBtnText}>{voipAuditLoading ? '갱신 중...' : '새로고침'}</Text>
                                                </Pressable>
                                            ) : null}
                                        </View>
                                        {voipAuditError ? <Text style={styles.errorText}>{voipAuditError}</Text> : null}
                                        {voipAuditEvents.length ? voipAuditEvents.map((event) => (
                                            <View key={`rail-audit-${event.id}-${event.created_at}`} style={styles.voipAuditEventRow}>
                                                <Text style={styles.voipAuditEventTitle}>{event.event_type}</Text>
                                                <Text style={styles.voipAuditEventMeta}>{formatUnifiedCallModeText(event.requested_mode, event.resolved_mode)}{event.call_route ? ` · ${event.call_route}` : ''}</Text>
                                                <Text style={styles.voipAuditEventMeta}>{event.created_at}{event.status ? ` · 상태 ${event.status}` : ''}{event.error_code ? ` · 오류 ${event.error_code}` : ''}</Text>
                                            </View>
                                        )) : (
                                            <Text style={styles.voipAuditEmptyText}>{voipAuditLoading ? '감사 로그를 불러오는 중입니다.' : '통화를 시작하면 감사 로그가 여기에 표시됩니다.'}</Text>
                                        )}
                                    </View>
                                ) : null}
                            </View>
                        ) : null}
                        {!token || !userInfo ? renderSectionConnectionCard({
                            sectionKey: 'voip',
                            title: '로그인 없이도 데모 세션으로 VoIP 진입을 열 수 있습니다',
                            body: '비로그인 상태에서는 VoIP tester가 막혀 데드엔드처럼 보입니다. 데모 세션을 시작하면 실제 인증 토큰을 연결하고, UI 검증용으로 VoIP tester를 임시 개방합니다.',
                            bullets: ['VoIP tester 모달 즉시 오픈', '통화 모드 카드와 다이얼 입력 검증', '예약/채팅과 같은 계정으로 연속 확인'],
                            loginSource: 'voip_section_gate',
                        }) : null}
                        <View style={styles.premiumHubRow}>
                            <View style={[styles.monetizationCard, styles.monetizationCardPrimary]}>
                                <Text style={styles.monetizationBadge}>기본 중심</Text>
                                <Text style={styles.monetizationTitle}>번역 채팅</Text>
                                <Text style={styles.monetizationBody}>운영비가 가장 낮고, 사용자를 가장 오래 붙잡을 수 있는 기본 상품입니다.</Text>
                                <View style={styles.monetizationMetricRow}>
                                    <Text style={styles.monetizationMetric}>원가 우선순위 1</Text>
                                    <Text style={styles.monetizationMetric}>문자 번역 호출 중심</Text>
                                </View>
                                <Pressable style={styles.inlineActionBtn} onPress={() => setActiveRailSection(null)}>
                                    <Text style={styles.inlineActionBtnText}>현재 번역 화면으로 돌아가기</Text>
                                </Pressable>
                            </View>
                            <View style={styles.monetizationCard}>
                                <Text style={styles.monetizationBadge}>프리미엄</Text>
                                <Text style={styles.monetizationTitle}>VoIP 통역 통화</Text>
                                <Text style={styles.monetizationBody}>TURN, 세션 유지, 음성 통역 비용이 커서 Lite/Pro 월정액에서만 열어줍니다.</Text>
                                <View style={styles.planGrid}>
                                    {(['voip_lite', 'voip_pro'] as MonetizationPlanKey[]).map((planKey) => {
                                        const plan = MONETIZATION_PLAN_CONFIG[planKey];
                                        const owned = ownedPlanKeys.has(planKey);
                                        return (
                                            <View key={`plan-${planKey}`} style={[styles.planCard, owned && styles.planCardOwned]}>
                                                <Text style={styles.planTitle}>{plan.title}</Text>
                                                <Text style={styles.planPrice}>{plan.billingLabel}</Text>
                                                <Text style={styles.planUsage}>{plan.usageLabel}</Text>
                                                <Text style={styles.planFormula}>{plan.formulaLabel}</Text>
                                                <Pressable
                                                    style={[styles.inlineActionBtn, owned && styles.inlineActionBtnActive]}
                                                    onPress={owned ? handleInlineVoipOpenPress : () => { void handlePremiumPurchase(planKey); }}
                                                >
                                                    <Text style={[styles.inlineActionBtnText, owned && styles.inlineActionBtnTextActive]}>{owned ? 'VoIP 열기' : `${plan.shortLabel} 결제`}</Text>
                                                </Pressable>
                                            </View>
                                        );
                                    })}
                                </View>
                                {token && userInfo && !activeVoipPlan ? (
                                    <Pressable
                                        style={styles.inlineGhostBtn}
                                        onPress={handleVoipValidationOpenPress}
                                        testID="worldlinco-voip-validation-open"
                                        accessibilityLabel="정합성 테스트 열기"
                                    >
                                        <Text style={styles.inlineGhostBtnText}>정합성 테스트 열기</Text>
                                    </Pressable>
                                ) : null}
                            </View>
                        </View>
                        {premiumStatusMessage ? <Text style={styles.premiumStatusText}>{premiumStatusMessage}</Text> : null}
                        {voipStatusMessage ? <Text style={styles.songModeMetaText}>{voipStatusMessage}</Text> : null}
                        {payError ? <Text style={styles.errorText}>{payError}</Text> : null}
                        {payUrl ? (
                            <Pressable style={styles.inlineGhostBtn} onPress={() => Linking.openURL(payUrl)}>
                                <Text style={styles.inlineGhostBtnText}>결제 링크 열기</Text>
                            </Pressable>
                        ) : null}
                    </View>
                ) : null}

                {isSongRailSectionVisible ? (
                    <View
                        onLayout={(event) => {
                            railSectionOffsetRef.current['song-mode'] = event.nativeEvent.layout.y;
                            if (activeRailSection === 'song-mode') {
                                scrollToRailSection('song-mode');
                            }
                        }}
                        style={[styles.sectionCard, activeRailSection === 'song-mode' && styles.sectionCardActive]}
                    >
                        <View style={styles.hubHeroRow}>
                            <View style={[styles.hubHeroIcon, { backgroundColor: '#7C5CFC' }]}><Text style={styles.hubHeroEmoji}>🎵</Text></View>
                            <Text style={styles.hubHeroTitle}>노래 가사를 번역해서 함께 불러요</Text>
                        </View>
                        <View style={styles.actionTileGrid2}>
                            <Pressable
                                style={[styles.gridTile, songModeEnabled && styles.gridTileActive]}
                                onPress={() => setSongModeEnabled((prev) => !prev)}
                                accessibilityRole="button"
                                accessibilityLabel="노래 모드 토글"
                                testID="worldlinco-song-action-toggle"
                            >
                                <View style={[styles.gridTileIcon, { backgroundColor: '#7C5CFC' }]}><Text style={styles.gridTileEmoji}>🎵</Text></View>
                                <Text style={styles.gridTileLabel}>노래 모드 {songModeEnabled ? 'ON' : 'OFF'}</Text>
                                <Text style={styles.gridTileSub}>{songModeEnabled ? '가사 번역 자막 켜짐' : '탭하면 가사 번역 시작'}</Text>
                            </Pressable>
                            <Pressable
                                style={styles.gridTile}
                                onPress={hasSongPass ? handlePickSongFile : () => { void handlePremiumPurchase('song_pass'); }}
                                accessibilityRole="button"
                                accessibilityLabel="노래 파일 선택"
                                testID="worldlinco-song-action-file"
                            >
                                <View style={[styles.gridTileIcon, { backgroundColor: '#7C5CFC' }]}><Text style={styles.gridTileEmoji}>📂</Text></View>
                                <Text style={styles.gridTileLabel}>노래 파일 선택</Text>
                                <Text style={styles.gridTileSub}>{hasSongPass ? '파일에서 가사 번역' : '1곡 결제 후 이용'}</Text>
                            </Pressable>
                        </View>
                        <View style={[styles.monetizationCard, styles.songPayCard]}>
                            <Text style={styles.monetizationBadge}>건당 과금</Text>
                            <Text style={styles.monetizationTitle}>{MONETIZATION_PLAN_CONFIG.song_pass.title}</Text>
                            <Text style={styles.monetizationBody}>{MONETIZATION_PLAN_CONFIG.song_pass.description}</Text>
                            <Text style={styles.planPrice}>{MONETIZATION_PLAN_CONFIG.song_pass.billingLabel}</Text>
                            <Text style={styles.planFormula}>{MONETIZATION_PLAN_CONFIG.song_pass.formulaLabel}</Text>
                            <Pressable style={[styles.inlineActionBtn, hasSongPass && styles.inlineActionBtnActive]} onPress={hasSongPass ? handlePickSongFile : () => { void handlePremiumPurchase('song_pass'); }}>
                                <Text style={[styles.inlineActionBtnText, hasSongPass && styles.inlineActionBtnTextActive]}>{hasSongPass ? '노래 파일 선택' : '1곡 결제하기'}</Text>
                            </Pressable>
                        </View>
                        <View style={styles.songModeActionRow}>
                            <Pressable style={[styles.interToggleBtn, songModeEnabled && styles.interToggleBtnActive]} onPress={() => setSongModeEnabled((prev) => !prev)}>
                                <Text style={[styles.interToggleText, songModeEnabled && styles.interToggleTextActive]}>
                                    {songModeEnabled ? '🎵 노래 모드 ON' : '🎵 노래 모드 OFF'}
                                </Text>
                            </Pressable>
                            <Pressable style={[styles.inlineGhostBtn, (songFileLoading || !hasSongPass) && styles.inlineGhostBtnDisabled]} onPress={handlePickSongFile} disabled={songFileLoading || !hasSongPass}>
                                <Text style={styles.inlineGhostBtnText}>{songFileLoading ? '파일 처리 중' : hasSongPass ? '노래 파일 선택' : '결제 후 파일 선택'}</Text>
                            </Pressable>
                            <Pressable style={styles.inlineGhostBtn} onPress={() => {
                                setSongSubtitles([]);
                                setSongFileSegments([]);
                                setSongFileJob(null);
                                setSongFileExportPreview('');
                            }}>
                                <Text style={styles.inlineGhostBtnText}>자막 초기화</Text>
                            </Pressable>
                        </View>
                        <Text style={styles.songModeMetaText}>
                            소스: 음성인식 + 문자패턴 자동 판정
                        </Text>
                        <Text style={styles.songModeMetaText}>
                            마이크 타겟: 현재 번역 언어 우선, 소스와 같으면 자동 추천 ({getLangLabel(toLang)})
                        </Text>
                        <Text style={styles.songModeMetaText}>
                            파일 타겟: 자국어 자막 우선 ({getLangLabel(resolveSongFileTargetLang(fromLang, toLang))})
                        </Text>
                        {songModeStatus ? <Text style={styles.songModeStatusText}>{songModeStatus}</Text> : null}
                        {songFileJob ? (
                            <View style={styles.songFileJobBox}>
                                <View style={styles.mediaMetaCard}>
                                    <View style={styles.mediaThumbBox}>
                                        <Text style={styles.mediaThumbEmoji}>🎵</Text>
                                        <Text style={styles.mediaThumbCaption}>{songFileName.split('.').pop()?.slice(0, 4).toUpperCase() || 'SONG'}</Text>
                                    </View>
                                    <View style={styles.mediaMetaBody}>
                                        <Text style={styles.mediaMetaTitle}>{songFileName || '선택한 노래 파일'}</Text>
                                        <View style={styles.mediaBadgeRow}>
                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{songFileSegments.length}구간</Text></View>
                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{getLangLabel(fromLang)}</Text></View>
                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{getLangLabel(resolveSongFileTargetLang(fromLang, toLang))}</Text></View>
                                        </View>
                                        <Text style={styles.songModeMetaText}>{songFileJob.stage} · {songFileJob.message}</Text>
                                    </View>
                                </View>
                                <View style={styles.songFileJobHeader}>
                                    <Text style={styles.songFileNameText}>{songFileName || '선택한 노래 파일'}</Text>
                                    <Text style={styles.songFileProgressText}>{songFileJob.progress}%</Text>
                                </View>
                                <Text style={styles.songSubtitleMeta}>{songFileJob.stage} · {songFileJob.message}</Text>
                                <View style={styles.songFileProgressTrack}>
                                    <View style={[styles.songFileProgressFill, { width: `${Math.max(4, Math.min(100, songFileJob.progress))}%` }]} />
                                </View>
                                <View style={styles.songFileControlRow}>
                                    <Pressable style={styles.inlineGhostBtn} onPress={handleToggleSongFilePlayback}>
                                        <Text style={styles.inlineGhostBtnText}>{songFilePlaying ? '일시정지' : '재생'}</Text>
                                    </Pressable>
                                    <Pressable
                                        style={[styles.inlineActionBtn, chatShareLoading && styles.inlineGhostBtnDisabled]}
                                        onPress={() => { void handleShareSongToChat(); }}
                                        disabled={chatShareLoading}
                                    >
                                        <Text style={styles.inlineActionBtnText}>{chatShareLoading ? '공유 중...' : '💬 노래 번역을 채팅에 보내기'}</Text>
                                    </Pressable>
                                    <Text style={styles.songSubtitleMeta}>현재 {formatSongFileTime(songFilePlaybackMs)} {activeSongFileSegment ? `· ${activeSongFileSegment.index}번 자막` : ''}</Text>
                                </View>
                            </View>
                        ) : null}
                        <View style={styles.voicePreviewPanel}>
                            <View style={styles.voicePreviewHeaderRow}>
                                <Text style={styles.songFileTimelineTitle}>내 목소리 번역가사 preview</Text>
                                <Text style={styles.songSubtitleMeta}>{voiceConsent ? '동의 확인됨' : '동의 대기'}</Text>
                            </View>
                            <Text style={styles.songSubtitleMeta}>
                                기본은 개인 preview이며, 권리 확인과 정책 승인 후 공유/export 경로가 열립니다.
                            </Text>
                            <View style={styles.songModeActionRow}>
                                <Pressable style={[styles.inlineGhostBtn, voiceProfileLoading && styles.inlineGhostBtnDisabled]} onPress={handleToggleVoiceSampleRecording} disabled={voiceProfileLoading}>
                                    <Text style={styles.inlineGhostBtnText}>{voiceProfileRecording ? '샘플 녹음 종료' : '샘플 녹음'}</Text>
                                </Pressable>
                                <Pressable style={[styles.inlineGhostBtn, voiceProfileLoading && styles.inlineGhostBtnDisabled]} onPress={handlePickVoiceSample} disabled={voiceProfileLoading || voiceProfileRecording}>
                                    <Text style={styles.inlineGhostBtnText}>{voiceProfileLoading ? '처리 중' : '샘플 파일 업로드'}</Text>
                                </Pressable>
                                {voiceProfile ? (
                                    <Pressable style={styles.inlineGhostBtn} onPress={handleDeleteVoiceProfile}>
                                        <Text style={styles.inlineGhostBtnText}>프로필 삭제</Text>
                                    </Pressable>
                                ) : null}
                            </View>
                            {voiceProfile ? (
                                <Text style={styles.songModeMetaText}>
                                    프로필: {voiceProfile.profile_label} · 품질 {(voiceProfile.sample_quality_score * 100).toFixed(0)}% · {voiceProfile.encrypted ? '암호화 저장' : '저장 대기'}
                                </Text>
                            ) : (
                                <Text style={styles.songModeMetaText}>샘플 녹음 또는 파일 업로드 후 voice profile이 생성됩니다.</Text>
                            )}
                            <Text style={styles.songModeMetaText}>권리 모드</Text>
                            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                {VOICE_LICENSE_OPTIONS.map((option) => (
                                    <Pressable
                                        key={`voice-license-${option.value}`}
                                        style={[styles.railBtn, voiceLicenseMode === option.value && styles.railBtnActive]}
                                        onPress={() => setVoiceLicenseMode(option.value)}
                                    >
                                        <Text style={[styles.railBtnText, voiceLicenseMode === option.value && styles.railBtnTextActive]}>{option.label}</Text>
                                    </Pressable>
                                ))}
                            </ScrollView>
                            <Text style={styles.songModeMetaText}>출력 범위</Text>
                            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                {VOICE_OUTPUT_SCOPE_OPTIONS.map((option) => (
                                    <Pressable
                                        key={`voice-output-${option.value}`}
                                        style={[styles.railBtn, voiceOutputScope === option.value && styles.railBtnActive]}
                                        onPress={() => setVoiceOutputScope(option.value)}
                                    >
                                        <Text style={[styles.railBtnText, voiceOutputScope === option.value && styles.railBtnTextActive]}>{option.label}</Text>
                                    </Pressable>
                                ))}
                            </ScrollView>
                            <Pressable style={styles.voiceAckRow} onPress={() => setVoiceRightsAcknowledged((value) => !value)}>
                                <Text style={styles.voiceAckMark}>{voiceRightsAcknowledged ? '✓' : ''}</Text>
                                <Text style={styles.voiceAckText}>권리 보유/허가 여부와 사용자 책임 고지를 확인했습니다.</Text>
                            </Pressable>
                            <View style={styles.songModeActionRow}>
                                <Pressable style={[styles.inlineActionBtn, (!voiceProfile || !songFileJob || songFileJob.status !== 'completed' || voiceProfileLoading) && styles.inlineGhostBtnDisabled]} onPress={handleCreateVoicePreview} disabled={!voiceProfile || !songFileJob || songFileJob.status !== 'completed' || voiceProfileLoading}>
                                    <Text style={styles.inlineActionBtnText}>번역가사 preview 생성</Text>
                                </Pressable>
                                {voicePreview?.preview_text ? (
                                    <Pressable style={styles.inlineGhostBtn} onPress={handleSpeakVoicePreview}>
                                        <Text style={styles.inlineGhostBtnText}>preview 듣기</Text>
                                    </Pressable>
                                ) : null}
                            </View>
                            {voiceProfileStatus ? <Text style={styles.songModeStatusText}>{voiceProfileStatus}</Text> : null}
                            {voicePreview ? (
                                <View style={styles.voicePreviewResultBox}>
                                    <Text style={styles.songSubtitleMeta}>{voicePreview.gate_status} · {voicePreview.effective_output_scope} · {voicePreview.segment_count}개 구간</Text>
                                    <Text style={styles.songFileExportPreview}>{voicePreview.preview_text.slice(0, 900)}</Text>
                                </View>
                            ) : null}
                        </View>
                        {songFileSegments.length > 0 ? (
                            <View style={styles.songFileTimelineWrap}>
                                <Text style={styles.songFileTimelineTitle}>파일 번역 자막 편집</Text>
                                <View style={styles.songFileExportRow}>
                                    {(['srt', 'vtt', 'lrc', 'json'] as const).map((format) => (
                                        <Pressable key={format} style={styles.songFileExportBtn} onPress={() => handleExportSongFileTimeline(format)}>
                                            <Text style={styles.songFileExportText}>{format.toUpperCase()}</Text>
                                        </Pressable>
                                    ))}
                                </View>
                                {songFileSegments.map((segment) => {
                                    const active = activeSongFileSegment?.id === segment.id;
                                    const sourceLang = normalizeSongFileLang(segment.source_language, fromLang);
                                    const targetLang = normalizeSongFileLang(segment.target_language, toLang);
                                    return (
                                        <View key={segment.id} style={[styles.songFileSegmentItem, active && styles.songFileSegmentItemActive]}>
                                            <Text style={styles.songSubtitleMeta}>{formatSongFileTime(segment.start_ms)} - {formatSongFileTime(segment.end_ms)} · {getLangLabel(sourceLang)} → {getLangLabel(targetLang)} · {(segment.confidence * 100).toFixed(0)}%</Text>
                                            <Text style={styles.songSubtitleOriginal}>{segment.original}</Text>
                                            <TextInput
                                                style={styles.songFileSegmentInput}
                                                value={segment.translated}
                                                multiline
                                                onChangeText={(text) => handleSongFileSegmentTextChange(segment.id, text)}
                                            />
                                            <View style={styles.songFileSegmentFooter}>
                                                <Text style={styles.songSubtitleMeta}>{segment.edited_by_user ? '사용자 편집됨' : segment.detected_by}</Text>
                                                <Pressable style={styles.songFileSaveBtn} onPress={() => handleSaveSongFileSegment(segment)}>
                                                    <Text style={styles.songFileSaveText}>저장</Text>
                                                </Pressable>
                                            </View>
                                        </View>
                                    );
                                })}
                                {songFileExportPreview ? (
                                    <Text style={styles.songFileExportPreview}>{songFileExportPreview}</Text>
                                ) : null}
                            </View>
                        ) : null}
                        <View style={styles.songSubtitleWrap}>
                            {songSubtitles.length === 0 ? (
                                <Text style={styles.songSubtitlePlaceholder}>노래 모드를 켠 뒤 마이크 버튼으로 가사 한 구간을 캡처하거나 노래 파일을 선택하면 번역 자막이 여기에 누적됩니다.</Text>
                            ) : (
                                songSubtitles.map((entry) => (
                                    <View key={entry.id} style={styles.songSubtitleItem}>
                                        <Text style={styles.songSubtitleOriginal}>
                                            {entry.original}
                                            {entry.repeatCount > 1 ? `  x${entry.repeatCount}` : ''}
                                        </Text>
                                        <Text style={styles.songSubtitleTranslated}>{entry.translated}</Text>
                                        <Text style={styles.songSubtitleMeta}>{getLangLabel(entry.source)} → {getLangLabel(entry.target)} · {entry.detectedBy}</Text>
                                    </View>
                                ))
                            )}
                        </View>
                    </View>
                ) : null}

                {isTravelRailSectionVisible ? (
                    <>

                        {/* 주변 검색 레일 */}
                            <View
                                onLayout={(event) => {
                                    railSectionOffsetRef.current['travel-booking'] = event.nativeEvent.layout.y;
                                    if (activeRailSection === 'travel-booking') {
                                        scrollToRailSection('travel-booking');
                                    }
                                }}
                                style={styles.sectionCard}
                            >
                                <View style={styles.hubHeroRow}>
                                    <View style={[styles.hubHeroIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.hubHeroEmoji}>🧭</Text></View>
                                    <Text style={styles.hubHeroTitle}>여행을 한 곳에서 예약하세요</Text>
                                </View>
                                <View style={styles.bookingTileGrid}>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('airport')}
                                        accessibilityRole="button"
                                        accessibilityLabel="항공권"
                                        testID="worldlinco-booking-action-flight"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>✈️</Text></View>
                                        <Text style={styles.bookingTileLabel}>항공권</Text>
                                        <Text style={styles.bookingTileSub}>비행기 예약</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('hotel')}
                                        accessibilityRole="button"
                                        accessibilityLabel="호텔"
                                        testID="worldlinco-booking-action-hotel"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>🏨</Text></View>
                                        <Text style={styles.bookingTileLabel}>호텔</Text>
                                        <Text style={styles.bookingTileSub}>숙소 예약</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('all')}
                                        accessibilityRole="button"
                                        accessibilityLabel="주변 검색"
                                        testID="worldlinco-booking-action-nearby"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>📍</Text></View>
                                        <Text style={styles.bookingTileLabel}>주변 검색</Text>
                                        <Text style={styles.bookingTileSub}>맛집·관광</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('attraction')}
                                        accessibilityRole="button"
                                        accessibilityLabel="일정"
                                        testID="worldlinco-booking-action-itinerary"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>📅</Text></View>
                                        <Text style={styles.bookingTileLabel}>일정</Text>
                                        <Text style={styles.bookingTileSub}>여행 타임라인</Text>
                                    </Pressable>
                                </View>
                                <Pressable
                                    style={styles.bookingNearbyCard}
                                    onPress={handleSearchNearby}
                                    accessibilityRole="button"
                                    accessibilityLabel="주변 추천"
                                    testID="worldlinco-booking-nearby-recommend"
                                >
                                    <View style={styles.bookingNearbyThumb}><Text style={styles.bookingNearbyThumbEmoji}>🗺️</Text></View>
                                    <View style={styles.bookingNearbyBody}>
                                        <Text style={styles.bookingNearbyTitle}>주변 추천</Text>
                                        <Text style={styles.bookingNearbySub}>현재 위치 주변의 맛집과 관광지를 추천해 드려요.</Text>
                                    </View>
                                    <Text style={styles.voipTileChevron}>›</Text>
                                </Pressable>
                                <Text style={[styles.sectionTitle, { color: '#19C37D', marginTop: 18 }]}>📍 주변 검색</Text>
                                <Text style={styles.sectionSub}>좌표/카테고리/반경을 선택해 주변 장소를 조회합니다.</Text>

                                <View style={styles.coordRow}>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>위도</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={lat}
                                            onChangeText={setLat}
                                            accessibilityLabel="worldlinco-travel-lat-input"
                                            testID="worldlinco-travel-lat-input"
                                        />
                                    </View>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>경도</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={lon}
                                            onChangeText={setLon}
                                            accessibilityLabel="worldlinco-travel-lon-input"
                                            testID="worldlinco-travel-lon-input"
                                        />
                                    </View>
                                </View>

                                <Text style={styles.label}>카테고리</Text>
                                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                    {CATEGORY_OPTIONS.map((item) => (
                                        <Pressable
                                            key={item.value}
                                            style={[styles.railBtn, nearbyCategory === item.value && styles.railBtnActive]}
                                            onPress={() => setNearbyCategory(item.value)}
                                            accessibilityLabel={`worldlinco-travel-category-${item.value}`}
                                            testID={`worldlinco-travel-category-${item.value}`}
                                        >
                                            <Text style={[styles.railBtnText, nearbyCategory === item.value && styles.railBtnTextActive]}>{item.label}</Text>
                                        </Pressable>
                                    ))}
                                </ScrollView>

                                <Text style={styles.label}>검색 반경</Text>
                                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                    {RADIUS_OPTIONS.map((item) => (
                                        <Pressable
                                            key={item.value}
                                            style={[styles.railBtn, radiusM === item.value && styles.railBtnActive]}
                                            onPress={() => setRadiusM(item.value)}
                                            accessibilityLabel={`worldlinco-travel-radius-${item.value}`}
                                            testID={`worldlinco-travel-radius-${item.value}`}
                                        >
                                            <Text style={[styles.railBtnText, radiusM === item.value && styles.railBtnTextActive]}>{item.label}</Text>
                                        </Pressable>
                                    ))}
                                </ScrollView>

                                <Pressable
                                    style={[styles.translateBtn, nearbyLoading && styles.translateBtnDisabled]}
                                    onPress={handleSearchNearby}
                                    disabled={nearbyLoading}
                                    accessibilityLabel="worldlinco-travel-search-button"
                                    testID="worldlinco-travel-search-button"
                                >
                                    {nearbyLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>주변 장소 찾기</Text>}
                                </Pressable>

                                <TravelItineraryPanel
                                    latitude={Number.parseFloat(lat)}
                                    longitude={Number.parseFloat(lon)}
                                    language={toLang}
                                    regionHint={gpsRegionHint || resolveActiveRegionHint(fromLang)}
                                    countryCode={gpsCountryCode}
                                    apiBase={API_BASE}
                                    seedQuery={itinerarySeedQuery}
                                    seedNonce={itinerarySeedNonce}
                                />

                                {nearbyError ? <Text style={styles.errorText}>{nearbyError}</Text> : null}

                                {selectedBookingPlace ? (
                                    <View style={styles.bookingSelectionBanner}>
                                        <Text style={styles.bookingSelectionBannerTitle}>선택된 예약 장소</Text>
                                        <Text style={styles.bookingSelectionBannerPlace}>{selectedBookingPlace.name}</Text>
                                        <Text style={styles.bookingSelectionBannerMeta}>
                                            {selectedBookingPlace.category_label} · {formatDistance(selectedBookingPlace.distance_m)} · 아래 예약 카드에 즉시 반영됩니다.
                                        </Text>
                                        <Text style={styles.bookingSelectionBannerStatic}>예약 선택 완료 · 예약 폼에 반영됨</Text>
                                        {bookingSelectionNotice ? (
                                            <Text style={styles.bookingSelectionBannerNotice}>{bookingSelectionNotice}</Text>
                                        ) : null}
                                    </View>
                                ) : null}

                                {nearbyPlaces.length > 0 && (
                                    <View style={styles.nearbyMapWrap} pointerEvents="none">
                                        <View style={styles.nearbyMapHeaderRow}>
                                            <Text style={styles.nearbyMapTitle}>지도 미리보기</Text>
                                            <Text style={styles.nearbyMapSubtitle}>{selectedNearbyPlace?.name || '검색 결과'}</Text>
                                        </View>
                                        {nearbyMapHtml ? (
                                            <WebView
                                                originWhitelist={['*']}
                                                source={{ html: nearbyMapHtml }}
                                                style={styles.nearbyMapWebView}
                                                scrollEnabled={false}
                                                nestedScrollEnabled
                                                onMessage={handleNearbyMapMessage}
                                            />
                                        ) : null}
                                    </View>
                                )}

                                {nearbyPlaces.length > 0 && (
                                    <View style={styles.nearbyListWrap}>
                                        {nearbyPlaces.map((place) => (
                                            <Pressable
                                                key={place.id}
                                                style={[styles.placeItem, selectedNearbyPlace?.id === place.id && styles.placeItemActive]}
                                                onPress={() => setSelectedNearbyPlaceId(place.id)}
                                                accessibilityLabel={`worldlinco-travel-place-${place.id}`}
                                                testID={`worldlinco-travel-place-${place.id}`}
                                            >
                                                <Text style={styles.placeName}>{place.name}</Text>
                                                <Text style={styles.placeMeta}>{place.category_label} · {formatDistance(place.distance_m)} · ★ {Number(place.rating).toFixed(1)}</Text>
                                                <Text style={styles.placeAddr}>{place.address}</Text>
                                                <View style={styles.placeActionRow}>
                                                    <Pressable
                                                        style={[styles.inlineActionBtn, selectedNearbyPlace?.id === place.id && styles.inlineActionBtnActive]}
                                                        onPress={() => setSelectedNearbyPlaceId(place.id)}
                                                    >
                                                        <Text style={[styles.inlineActionBtnText, selectedNearbyPlace?.id === place.id && styles.inlineActionBtnTextActive]}>지도에서 보기</Text>
                                                    </Pressable>
                                                    <Pressable style={styles.inlineActionBtn} onPress={() => {
                                                        setSelectedNearbyPlaceId(place.id);
                                                        Linking.openURL(place.google_maps_url);
                                                    }}>
                                                        <Text style={styles.inlineActionBtnText}>Google 지도</Text>
                                                    </Pressable>
                                                    {place.booking_supported && (place.category === 'hotel' || place.category === 'airport') && (
                                                        <Pressable
                                                            style={[styles.inlineActionBtn, selectedBookingPlaceId === place.id && styles.inlineActionBtnActive]}
                                                            onPress={() => selectBookingPlace(place.id, '목록')}
                                                            accessibilityLabel={`worldlinco-travel-booking-select-${place.id}`}
                                                            testID={`worldlinco-travel-booking-select-${place.id}`}
                                                        >
                                                            <Text style={[styles.inlineActionBtnText, selectedBookingPlaceId === place.id && styles.inlineActionBtnTextActive]}>예약 선택</Text>
                                                        </Pressable>
                                                    )}
                                                </View>
                                            </Pressable>
                                        ))}
                                    </View>
                                )}
                            </View>

                        {/* 여행 예약 레일 */}
                            <View
                                style={[styles.sectionCard, activeRailSection === 'travel-booking' && styles.sectionCardActive]}
                            >
                                <Text style={styles.sectionTitle}>🧳 여행 예약</Text>
                                <Text style={styles.sectionSub}>예약 가능한 호텔/공항을 선택해 예약 요청을 진행합니다.</Text>
                                <View style={styles.sectionCard}>
                                    <Text style={styles.sectionTitle}>☎ 예약 섹션 일반 통화 모드</Text>
                                    <Text style={styles.sectionSub}>{getLangLabel(fromLang)} ⇄ {getLangLabel(toLang)} · {SUPPORTED_LANGUAGE_COUNT}개국어 자동 전달</Text>
                                    <Pressable style={[styles.interToggleBtn, interCallActive && styles.interToggleBtnActive]} onPress={handleInterCallToggle}>
                                        <Text style={[styles.interToggleText, interCallActive && styles.interToggleTextActive]}>
                                            {interCallActive ? '📵 일반 통화 종료' : '📞 일반 통화 + 자동 전달 시작'}
                                        </Text>
                                    </Pressable>

                                    <TextInput
                                        style={styles.compactInput}
                                        placeholder="통역 통화 전화번호 (예: 01012345678)"
                                        placeholderTextColor={C.sub}
                                        keyboardType="phone-pad"
                                        value={interCallPhone}
                                        onChangeText={setInterCallPhone}
                                    />
                                    <View style={styles.interCallQuickRow}>
                                        <Pressable
                                            style={styles.inlineGhostBtn}
                                            onPress={() => setShowPhoneDialerModal(true)}
                                            accessibilityLabel="다이얼패드 열기"
                                            testID="worldlinco-phone-dialer-open"
                                        >
                                            <Text style={styles.inlineGhostBtnText}>다이얼패드 열기</Text>
                                        </Pressable>
                                        {interCallPhone ? (
                                            <Pressable style={styles.inlineGhostBtn} onPress={() => setInterCallPhone('')}>
                                                <Text style={styles.inlineGhostBtnText}>전화번호 비우기</Text>
                                            </Pressable>
                                        ) : null}
                                    </View>
                                    <Text style={styles.interCallHint}>일반통화는 여행 예약 섹션에서 관리하며, 통화가 열리면 {SUPPORTED_LANGUAGE_COUNT}개국어 자동 전달 보조가 시작됩니다. 단말 전화번호 저장소에서 선택한 번호 또는 직접 입력한 번호를 시스템 전화앱으로 넘겨 통역을 이어갑니다.</Text>

                                    {interCallActive && (
                                        <View style={styles.interPanel}>
                                            <Text style={styles.interStatus}>{interCallStatus || '통화 대기 중...'}</Text>
                                            {Platform.OS !== 'web' && (
                                                <>
                                                    <Text style={styles.sectionSub}>
                                                        {interCallTurn === 'from'
                                                            ? `👤 ${getLangLabel(fromLang)} 발화 입력`
                                                            : `🤝 ${getLangLabel(toLang)} 발화 입력`}
                                                    </Text>
                                                    <Pressable
                                                        style={styles.inlineActionBtn}
                                                        onPress={() => { void handleToggleInterCallVoiceAssist(); }}
                                                        accessibilityLabel="worldlinco-inter-call-voice-assist-toggle"
                                                        testID="worldlinco-inter-call-voice-assist-toggle"
                                                    >
                                                        <Text style={styles.inlineActionBtnText}>
                                                            {voiceInputTargetRef.current === 'inter_call' && (isVoiceRecording || voiceSttLoading)
                                                                ? '⏹️ 스피커폰 통역 보조 중지'
                                                                : interCallVoiceAssistEnabled
                                                                    ? '⏳ 스피커폰 통역 보조 준비 중'
                                                                    : '🎙️ 스피커폰 통역 보조 시작'}
                                                        </Text>
                                                    </Pressable>
                                                    <Text style={styles.sectionSub}>스피커폰으로 상대 음성을 들리게 한 뒤 이 보조를 켜면 주변 음성을 구간별로 받아 번역 후 TTS로 재송출합니다.</Text>
                                                    <Text style={styles.sectionSub}>자동 전송 간격: {formatAutoRelayDelayLabel(autoRelayDelayMs)}</Text>
                                                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                                        {AUTO_RELAY_DELAY_OPTIONS_MS.map((optionMs) => (
                                                            <Pressable
                                                                key={`inter-auto-relay-${optionMs}`}
                                                                style={[styles.railBtn, autoRelayDelayMs === optionMs && styles.railBtnActive]}
                                                                onPress={() => setAutoRelayDelayMs(optionMs)}
                                                            >
                                                                <Text style={[styles.railBtnText, autoRelayDelayMs === optionMs && styles.railBtnTextActive]}>
                                                                    {formatAutoRelayDelayLabel(optionMs)}
                                                                </Text>
                                                            </Pressable>
                                                        ))}
                                                    </ScrollView>
                                                    <TextInput
                                                        style={[styles.compactInput, styles.noteInput]}
                                                        multiline
                                                        placeholder="들린 내용을 입력하세요"
                                                        placeholderTextColor={C.sub}
                                                        value={interManualText}
                                                        onChangeText={setInterManualText}
                                                    />
                                                    <Pressable
                                                        style={styles.inlineActionBtn}
                                                        onPress={() => relayInterCallManual(interCallTurn, interManualText)}
                                                    >
                                                        <Text style={styles.inlineActionBtnText}>즉시 전송</Text>
                                                    </Pressable>
                                                </>
                                            )}

                                            {interCallLog.length > 0 && (
                                                <View style={styles.nearbyListWrap}>
                                                    {[...interCallLog].reverse().map((entry, idx) => (
                                                        <View key={`inter-${idx}`} style={styles.placeItem}>
                                                            <Text style={styles.placeMeta}>
                                                                {entry.turn === 'from' ? getLangLabel(fromLang) : getLangLabel(toLang)}
                                                            </Text>
                                                            <Text style={styles.placeName}>{entry.text}</Text>
                                                            <Text style={styles.successText}>→ {entry.translated}</Text>
                                                        </View>
                                                    ))}
                                                </View>
                                            )}
                                        </View>
                                    )}
                                </View>

                                {!token || !userInfo ? renderSectionConnectionCard({
                                    sectionKey: 'travel-booking',
                                    title: '예약 요청은 계정 연결 후 바로 검증됩니다',
                                    body: '주변 결과는 로그인 없이도 둘러볼 수 있지만, 예약 요청과 결제 흐름은 계정 기반으로 저장됩니다. 데모 세션을 연결하면 예약 폼과 결과 카드까지 한 번에 확인할 수 있습니다.',
                                    bullets: ['예약 폼 입력과 요청 전송', '예약 결과 카드 및 지원번호 확인', '동일 계정으로 결제 흐름 이어서 검증'],
                                    loginSource: 'travel_booking_section_gate',
                                }) : null}

                                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                    {nearbyPlaces
                                        .filter((place) => (place.category === 'hotel' || place.category === 'airport') && place.booking_supported)
                                        .map((place) => (
                                            <Pressable
                                                key={`booking-rail-${place.id}`}
                                                style={[styles.hotelRailBtn, selectedBookingPlaceId === place.id && styles.hotelRailBtnActive]}
                                                onPress={() => selectBookingPlace(place.id, '목록')}
                                                accessibilityLabel={`worldlinco-travel-booking-rail-${place.id}`}
                                                testID={`worldlinco-travel-booking-rail-${place.id}`}
                                            >
                                                <Text style={styles.hotelRailName}>{place.name}</Text>
                                                <Text style={styles.hotelRailMeta}>{place.category_label} · {place.price_tier} · ★ {Number(place.rating).toFixed(1)}</Text>
                                            </Pressable>
                                        ))}
                                </ScrollView>

                                {selectedBookingPlace ? (
                                    <View
                                        style={styles.selectedHotelBox}
                                        accessibilityLabel="worldlinco-travel-booking-selected-place"
                                        testID="worldlinco-travel-booking-selected-place"
                                    >
                                        <Text style={styles.selectedHotelName}>{selectedBookingPlace.name}</Text>
                                        <Text style={styles.placeAddr}>{selectedBookingPlace.address}</Text>
                                        <Text style={styles.selectedHotelStatic}>예약 선택 완료 · 예약 폼에 반영됨</Text>
                                        {bookingSelectionNotice ? (
                                            <Text style={styles.selectedHotelNotice}>{bookingSelectionNotice}</Text>
                                        ) : null}
                                        {selectedBookingPlace.phone ? (
                                            <Pressable
                                                style={styles.inlineActionBtn}
                                                onPress={() => { void openDialPad(selectedBookingPlace.phone); }}
                                                accessibilityLabel={selectedBookingPlace.category === 'airport'
                                                    ? 'worldlinco-travel-booking-airport-call-button'
                                                    : 'worldlinco-travel-booking-hotel-call-button'}
                                                testID={selectedBookingPlace.category === 'airport'
                                                    ? 'worldlinco-travel-booking-airport-call-button'
                                                    : 'worldlinco-travel-booking-hotel-call-button'}
                                            >
                                                <Text style={styles.inlineActionBtnText}>📞 {selectedBookingPlace.category === 'airport' ? '공항 예약센터' : '호텔'} 전화 예약</Text>
                                            </Pressable>
                                        ) : null}
                                    </View>
                                ) : (
                                    <Text style={styles.sectionSub}>주변검색 결과에서 예약 가능한 호텔/공항을 먼저 선택하세요.</Text>
                                )}

                                <TextInput
                                    style={styles.compactInput}
                                    placeholder="예약자명"
                                    placeholderTextColor={C.sub}
                                    value={bookingName}
                                    onChangeText={setBookingName}
                                    accessibilityLabel="worldlinco-travel-booking-name-input"
                                    testID="worldlinco-travel-booking-name-input"
                                />
                                <View style={styles.coordRow}>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>체크인(YYYY-MM-DD)</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={checkinDate}
                                            onChangeText={setCheckinDate}
                                            accessibilityLabel="worldlinco-travel-booking-checkin-input"
                                            testID="worldlinco-travel-booking-checkin-input"
                                        />
                                    </View>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>체크아웃(YYYY-MM-DD)</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={checkoutDate}
                                            onChangeText={setCheckoutDate}
                                            accessibilityLabel="worldlinco-travel-booking-checkout-input"
                                            testID="worldlinco-travel-booking-checkout-input"
                                        />
                                    </View>
                                </View>
                                <View style={styles.coordRow}>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>인원</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            keyboardType="number-pad"
                                            value={String(guests)}
                                            onChangeText={(v) => setGuests(Math.max(1, Number(v) || 1))}
                                            accessibilityLabel="worldlinco-travel-booking-guests-input"
                                            testID="worldlinco-travel-booking-guests-input"
                                        />
                                    </View>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>객실 수</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            keyboardType="number-pad"
                                            value={String(roomCount)}
                                            onChangeText={(v) => setRoomCount(Math.max(1, Number(v) || 1))}
                                            accessibilityLabel="worldlinco-travel-booking-roomcount-input"
                                            testID="worldlinco-travel-booking-roomcount-input"
                                        />
                                    </View>
                                </View>
                                <TextInput
                                    style={[styles.compactInput, styles.noteInput]}
                                    multiline
                                    placeholder="추가 요청사항 (예: 금연실, 늦은 체크인)"
                                    placeholderTextColor={C.sub}
                                    value={bookingNote}
                                    onChangeText={setBookingNote}
                                    accessibilityLabel="worldlinco-travel-booking-note-input"
                                    testID="worldlinco-travel-booking-note-input"
                                />

                                <Pressable
                                    style={[styles.translateBtn, (bookingLoading || !selectedBookingPlace) && styles.translateBtnDisabled]}
                                    onPress={handleReserveBooking}
                                    disabled={bookingLoading || !selectedBookingPlace}
                                    accessibilityLabel="worldlinco-travel-booking-submit-button"
                                    testID="worldlinco-travel-booking-submit-button"
                                >
                                    {bookingLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>예약 요청 보내기</Text>}
                                </Pressable>

                                {bookingError ? <Text style={styles.errorText}>{bookingError}</Text> : null}

                                {bookingResult && (
                                    <View
                                        style={styles.successBox}
                                        accessibilityLabel="worldlinco-travel-booking-result"
                                        testID="worldlinco-travel-booking-result"
                                    >
                                        <Text style={styles.successTitle}>예약 확인번호 {bookingResult.confirmation_id}</Text>
                                        <Text style={styles.successText}>{bookingResult.booking_message}</Text>
                                        <Text style={styles.successText}>{bookingResult.translated_message}</Text>
                                        {bookingResult.support_phone ? (
                                            <Pressable
                                                style={styles.inlineActionBtn}
                                                onPress={() => { void openDialPad(bookingResult.support_phone); }}
                                                accessibilityLabel="worldlinco-travel-booking-support-call-button"
                                                testID="worldlinco-travel-booking-support-call-button"
                                            >
                                                <Text style={styles.inlineActionBtnText}>📞 예약센터 통화</Text>
                                            </Pressable>
                                        ) : null}
                                    </View>
                                )}
                            </View>

                        {/* 결제 레일 */}
                        {bookingResult && (
                            <View
                                style={styles.sectionCard}
                                accessibilityLabel="worldlinco-travel-payment-card"
                                testID="worldlinco-travel-payment-card"
                            >
                                <Text style={styles.sectionTitle}>💳 결제</Text>
                                <Text style={styles.sectionSub}>
                                    결제 예정 금액: {(Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000)) * roomCount * 80000).toLocaleString('ko-KR')}원
                                </Text>
                                {payError ? <Text style={styles.errorText}>{payError}</Text> : null}
                                {purchaseResult ? (
                                    <View
                                        style={styles.successBox}
                                        accessibilityLabel="worldlinco-travel-payment-result"
                                        testID="worldlinco-travel-payment-result"
                                    >
                                        <Text style={styles.successTitle}>구매 ID: {purchaseResult.id} · 상태: {purchaseResult.status}</Text>
                                        {payUrl ? (
                                            <Pressable
                                                style={styles.inlineActionBtn}
                                                onPress={() => Linking.openURL(payUrl)}
                                                accessibilityLabel="worldlinco-travel-payment-open-url-button"
                                                testID="worldlinco-travel-payment-open-url-button"
                                            >
                                                <Text style={styles.inlineActionBtnText}>결제 페이지 열기</Text>
                                            </Pressable>
                                        ) : (
                                            <Text style={styles.sectionSub}>결제 URL을 불러오는 중...</Text>
                                        )}
                                    </View>
                                ) : (
                                    <Pressable
                                        style={[styles.translateBtn, (!token || payLoading) && styles.translateBtnDisabled]}
                                        onPress={handlePayment}
                                        disabled={!token || payLoading}
                                        accessibilityLabel="worldlinco-travel-payment-submit-button"
                                        testID="worldlinco-travel-payment-submit-button"
                                    >
                                        {payLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>{token ? '결제 진행하기' : '로그인 후 결제'}</Text>}
                                    </Pressable>
                                )}
                            </View>
                        )}

                    </>
                ) : null}

                {isTranslateWorkspaceVisible ? (
                    <>

                        {/* ── 앱 정보 ── */}
                        <View style={styles.footer}>
                            <Text style={styles.footerText}>
                                {getUiText(fromLang).footer.replace('\\n', '\n')}
                            </Text>
                            <Pressable
                                onPress={() => setShowDataSources(true)}
                                accessibilityLabel="worldlinco-open-data-sources"
                                testID="worldlinco-open-data-sources"
                                style={styles.dataSourcesLink}
                            >
                                <Text style={styles.dataSourcesLinkText}>데이터 출처 · 라이선스</Text>
                            </Pressable>
                        </View>

                    </>
                ) : null}
            </ScrollView>

            {/* 하단 고정 탭바(APP_DESIGN 1-2) — 채팅/통화/노래/예약/설정. 화면 전환 시 고정되어 맥락 유지. */}
            {!!userInfo && !showLogin && !voipCallInitResponse && !hasPendingIncomingVoip ? (
                <View style={[styles.bottomTabBar, { paddingBottom: insets.bottom, height: 58 + insets.bottom }]}>
                    {SECTION_RAIL_ITEMS.map((item) => {
                        const active = activeRailSection === item.key;
                        const color = SECTION_TAB_COLORS[item.key] || '#1E6FE0';
                        return (
                            <Pressable
                                key={`tab-${item.key}`}
                                style={styles.bottomTabItem}
                                onPress={() => handlePressSectionRail(item.key)}
                                accessibilityRole="button"
                                accessibilityLabel={buildSectionRailSelector(item.key)}
                                testID={buildSectionRailSelector(item.key)}
                            >
                                <Text style={[styles.bottomTabIcon, active ? { color } : null]}>{item.icon}</Text>
                                <Text style={[styles.bottomTabLabel, active ? { color, fontWeight: '800' } : null]}>{item.label}</Text>
                            </Pressable>
                        );
                    })}
                    <Pressable
                        style={styles.bottomTabItem}
                        onPress={() => setSettingsTabOpen(true)}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-bottom-tab-settings"
                        testID="worldlinco-bottom-tab-settings"
                    >
                        <Text style={[styles.bottomTabIcon, settingsTabOpen ? { color: '#41506b' } : null]}>⚙️</Text>
                        <Text style={[styles.bottomTabLabel, settingsTabOpen ? { color: '#41506b', fontWeight: '800' } : null]}>설정</Text>
                    </Pressable>
                </View>
            ) : null}

            {/* 소리새 AI 플로팅 심볼(드래그 이동) — 대면 통역창과 분리된 진입점.
                탭하면 소리새 AI 전용 창이 열린다. 로그인 상태·비통화 중에만 표시. */}
            {Platform.OS !== 'web' && !!userInfo && !showLogin && !voipCallInitResponse
                && !hasPendingIncomingVoip && !sorisaeWindowOpen && globalSettings.sorisaeFab ? (
                <Animated.View
                    {...sorisaePanResponder.panHandlers}
                    style={[
                        styles.sorisaeFab,
                        { transform: sorisaeBtnPos.getTranslateTransform() },
                    ]}
                >
                    <Text style={styles.sorisaeFabIcon}>🐦</Text>
                </Animated.View>
            ) : null}

            {/* [Phase6.1] 소리새 음성 호출 대기 토글 — 켜두면 이름("OOOO"/"소리새")을 부르는 것만으로
                소리새가 깨어나 대화하고, 3분 무응답이면 자동으로 잠든다. 로그인·비통화 중에만 노출. */}
            {Platform.OS !== 'web' && !!userInfo && !showLogin && !voipCallInitResponse
                && !hasPendingIncomingVoip && !sorisaeWindowOpen ? (
                <Pressable
                    onPress={() => { void handleToggleCompanionVoiceCall(); }}  // NOSONAR
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-companion-voicecall-toggle"
                    testID="worldlinco-companion-voicecall-toggle"
                    style={[styles.sorisaeCallChip, { bottom: insets.bottom + 72 }, companionVoiceCallArmed ? styles.sorisaeCallChipOn : null]}
                >
                    <Text style={styles.sorisaeCallChipText}>
                        {companionVoiceCallArmed ? `🔔 "${aiDisplayName}" 부르면 깨어나요 · 대기 끄기` : '📞 음성 호출 대기 켜기'}
                    </Text>
                </Pressable>
            ) : null}

            {/* VoIP 통화화면 디자인 미리보기(mockup #3) — 실통화 없이 연결된 UI 검증 */}
            <Modal
                visible={voipPreviewOpen}
                animationType="slide"
                statusBarTranslucent
                onRequestClose={() => setVoipPreviewOpen(false)}
            >
                <ImageBackground source={SKY_BG} resizeMode="cover" style={{ flex: 1 }}>
                    <VoIPCallScreen
                        previewMode
                        callInitResponse={{ call_id: 'preview', signaling_server: '', turn_servers: [] }}
                        calleePhone="David Miller"
                        participantProfile={{ nickname: 'David Miller', genderLabel: '남성', countryName: '미국', voiceId: 'preview', countryFlag: '🇺🇸', preferredLanguage: effectiveVoipTargetLang }}
                        apiBaseUrl={API_BASE}
                        authToken={token}
                        localSourceLang={effectiveVoipSourceLang}
                        localTargetLang={effectiveVoipTargetLang}
                        regionHint={resolveActiveRegionHint(effectiveVoipSourceLang)}
                        onHangup={() => setVoipPreviewOpen(false)}
                    />
                </ImageBackground>
            </Modal>

            {/* 채팅방 전체화면(mockup #4) — 임베드 대신 풀스크린 Modal로 분리해 몰입감·SafeArea 확보 */}
            <Modal
                visible={!!selectedChatRoom}
                animationType="slide"
                statusBarTranslucent
                onRequestClose={() => {
                    setSelectedChatRoom(null);
                    setChatRefreshKey((prev) => prev + 1);
                }}
            >
                <ImageBackground source={SKY_BG} resizeMode="cover" style={{ flex: 1 }}>
                    <SafeAreaView style={{ flex: 1, backgroundColor: 'transparent' }} edges={['top', 'left', 'right']}>
                        <StatusBar style="dark" />
                        {selectedChatRoom ? (
                            <ScrollView
                                style={{ flex: 1 }}
                                contentContainerStyle={{ padding: 10, paddingBottom: insets.bottom + 24 }}
                                keyboardShouldPersistTaps="handled"
                            >
                                <ChatRoomScreen
                                    apiBaseUrl={API_BASE}
                                    token={token}
                                    userId={userInfo!.id}
                                    room={selectedChatRoom}
                                    visible={!!selectedChatRoom}
                                    refreshKey={chatRefreshKey}
                                    onBack={() => {
                                        setSelectedChatRoom(null);
                                        setChatRefreshKey((prev) => prev + 1);
                                    }}
                                    onRoomChanged={() => setChatRefreshKey((prev) => prev + 1)}
                                />
                            </ScrollView>
                        ) : null}
                    </SafeAreaView>
                </ImageBackground>
            </Modal>

            {/* 설정 탭(⚙️) 전체화면(APP_DESIGN 2-6) — 전역 토글 + 기능별 사용설명서 */}
            <Modal
                visible={settingsTabOpen}
                animationType="slide"
                statusBarTranslucent
                onRequestClose={() => setSettingsTabOpen(false)}
            >
                <ImageBackground source={SKY_BG} resizeMode="cover" style={{ flex: 1 }}>
                    <SafeAreaView style={{ flex: 1, backgroundColor: 'transparent' }} edges={['top', 'left', 'right', 'bottom']}>
                        <StatusBar style="dark" />
                        <SettingsScreen
                            onClose={() => setSettingsTabOpen(false)}
                            onOpenProfile={() => { setSettingsTabOpen(false); openSettingsModal(); }}
                            appVersion={APP_VERSION_NUMBER}
                            buildNumber={APP_BUILD_NUMBER}
                            userLang={fromLang}
                        />
                    </SafeAreaView>
                </ImageBackground>
            </Modal>

            {/* 대면통역 전용 화면(mockup #2): 상단 상대언어(180° 회전) + 중앙 펄스 마이크 + 하단 내언어 */}
            <Modal
                visible={faceScreenOpen}
                animationType="slide"
                statusBarTranslucent
                onRequestClose={() => {
                    setFaceScreenOpen(false);
                    if (autoVoiceModeEnabled && Platform.OS !== 'web') { void handleToggleFaceConversation(); }
                }}
            >
                <ImageBackground source={SKY_BG} resizeMode="cover" style={styles.skyBg}>
                <SafeAreaView style={styles.faceScreenRoot} edges={['top', 'left', 'right']}>
                    <View style={styles.faceScreenHeader}>
                        <Text style={styles.faceScreenLogo}>🎙️ WorldLinco</Text>
                        <Pressable
                            style={styles.faceScreenLangPill}
                            onPress={() => setLangPickerFor('to')}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-face-screen-lang"
                        >
                            <Text style={styles.faceScreenLangPillText}>{currentFromLabel} ⇄ {currentToLabel}</Text>
                        </Pressable>
                        <Pressable
                            onPress={() => {
                                setFaceScreenOpen(false);
                                if (autoVoiceModeEnabled && Platform.OS !== 'web') { void handleToggleFaceConversation(); }
                            }}
                            style={styles.faceScreenClose}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-face-screen-close"
                            testID="worldlinco-face-screen-close"
                        >
                            <Text style={styles.faceScreenCloseText}>✕</Text>
                        </Pressable>
                    </View>

                    <View style={styles.faceScreenBody}>
                        {/* 상단: 상대 언어 (180° 회전, 마주 앉은 상대가 읽음) */}
                        <View style={styles.facePeerHalf}>
                            <View style={styles.faceRotated}>
                                <Text style={styles.facePeerLangLabel}>{homeToFlag} {currentToLabel}</Text>
                                <Text style={styles.facePeerText}>
                                    {resultText || '상대에게 보여줄 번역이 여기에 표시됩니다.'}
                                </Text>
                            </View>
                        </View>

                        {/* 하단: 내 언어 (정방향) */}
                        <View style={styles.faceMeHalf}>
                            <View style={styles.faceTapHint}>
                                <Text style={styles.faceTapHintText}>
                                    👆 {autoVoiceModeEnabled ? '듣는 중 · 말이 끝나면 자동 번역' : '말하려면 탭하세요'}
                                </Text>
                            </View>
                            <Text style={styles.faceMeText}>
                                {inputText || '내가 말한 내용이 여기에 표시됩니다.'}
                            </Text>
                            <Text style={styles.faceMeLangLabel}>{homeFromFlag} {currentFromLabel}</Text>
                        </View>

                        {/* 중앙: 펄스 코랄 마이크 (경계선에 겹침) */}
                        <View style={styles.faceMicWrap} pointerEvents="box-none">
                            <Pressable
                                onPress={() => { if (Platform.OS !== 'web') { void handleToggleFaceConversation(); } }}
                                style={[styles.faceMicBtn, autoVoiceModeEnabled && styles.faceMicBtnActive]}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-face-screen-mic"
                                testID="worldlinco-face-screen-mic"
                            >
                                <Text style={styles.faceMicIconBig}>🎙️</Text>
                            </Pressable>
                        </View>
                    </View>

                    <View style={[styles.faceTabBar, { paddingBottom: 8 + insets.bottom }]}>
                        <View style={styles.faceTabItem}><Text style={styles.faceTabIcon}>🧑‍🤝‍🧑</Text><Text style={styles.faceTabLabelActive}>대면 통역</Text></View>
                        <Pressable style={styles.faceTabItem} onPress={() => { setFaceScreenOpen(false); setActiveRailSection('chat'); }}>
                            <Text style={styles.faceTabIcon}>💬</Text><Text style={styles.faceTabLabel}>대화 모드</Text>
                        </Pressable>
                        <Pressable style={styles.faceTabItem} onPress={() => { setFaceScreenOpen(false); setHomeToolsExpanded(true); }}>
                            <Text style={styles.faceTabIcon}>📖</Text><Text style={styles.faceTabLabel}>문장 모음</Text>
                        </Pressable>
                        <Pressable style={styles.faceTabItem} onPress={() => { setFaceScreenOpen(false); setIsSettingsModalOpen(true); }}>
                            <Text style={styles.faceTabIcon}>⚙️</Text><Text style={styles.faceTabLabel}>설정</Text>
                        </Pressable>
                    </View>
                </SafeAreaView>
                </ImageBackground>
            </Modal>

            {/* 소리새 AI 전용 창(대면 통역과 완전 분리) — 질문/답변 좌우 구분 + 마이크 토글. */}
            <Modal
                visible={sorisaeWindowOpen}
                animationType="slide"
                statusBarTranslucent
                onRequestClose={() => { void closeSorisaeWindow(); }}
            >
                <ImageBackground source={SKY_BG} resizeMode="cover" style={styles.skyBg}>
                <SafeAreaView style={styles.sorisaeWindowRoot}>
                    <View style={styles.sorisaeWindowHeader}>
                        <Text style={styles.sorisaeWindowTitle}>🐦 {aiDisplayName}</Text>
                        <Pressable
                            onPress={() => { void closeSorisaeWindow(); }}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-sorisae-window-close"
                            testID="worldlinco-sorisae-window-close"
                            style={styles.sorisaeWindowCloseBtn}
                        >
                            <Text style={styles.sorisaeWindowCloseText}>✕ 닫기</Text>
                        </Pressable>
                    </View>
                    <Text style={styles.sorisaeWindowHint}>
                        대면 통역창과 분리된 {aiDisplayName} 대화 창입니다. 마이크를 켜고 말하면 답해줍니다(발화 중에는 듣기가 멈춥니다).
                    </Text>
                    {gpsStatus ? <Text style={styles.sorisaeWindowStatus}>{gpsStatus}</Text> : null}
                    <ScrollView style={styles.sorisaeWindowScroll} contentContainerStyle={{ paddingBottom: 16 }}>
                        {sorisaeQaLog.length === 0 ? (
                            <Text style={styles.sorisaeWindowEmpty}>아직 대화가 없습니다. 아래 마이크를 켜고 말씀해 보세요.</Text>
                        ) : (
                            sorisaeQaLog.map((qa) => (
                                <View key={qa.id} style={styles.sorisaeQaTurn}>
                                    <View style={styles.sorisaeQaQuestionRow}>
                                        <View style={styles.sorisaeQaBubbleQuestion}>
                                            <Text style={styles.sorisaeQaRoleLabel}>
                                                🙋 질문 · {getLangLabel(qa.questionLang as LangCode)}
                                            </Text>
                                            <Text style={styles.sorisaeQaQuestionText}>{qa.question}</Text>
                                        </View>
                                    </View>
                                    <View style={styles.sorisaeQaAnswerRow}>
                                        <View style={styles.sorisaeQaBubbleAnswer}>
                                            <Text style={styles.sorisaeQaRoleLabelAnswer}>
                                                🐦 답변 · {getLangLabel(qa.answerLang as LangCode)}
                                            </Text>
                                            <Text style={styles.sorisaeQaAnswerText}>{qa.answer}</Text>
                                        </View>
                                    </View>
                                </View>
                            ))
                        )}
                    </ScrollView>
                    <View style={styles.sorisaeWindowFooter}>
                        {sorisaeQaLog.length > 0 ? (
                            <Pressable
                                onPress={() => setSorisaeQaLog([])}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-sorisae-window-clear"
                                style={styles.sorisaeWindowClearBtn}
                            >
                                <Text style={styles.sorisaeWindowClearText}>대화 지우기</Text>
                            </Pressable>
                        ) : null}
                        <Pressable
                            onPress={() => { void handleToggleSorisaeConversation(); }}  // NOSONAR
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-sorisae-window-mic"
                            testID="worldlinco-sorisae-window-mic"
                            style={[styles.sorisaeWindowMicBtn, autoVoiceModeEnabled && styles.sorisaeWindowMicBtnActive]}
                        >
                            <Text style={[styles.sorisaeWindowMicText, autoVoiceModeEnabled && styles.sorisaeWindowMicTextActive]}>
                                {autoVoiceModeEnabled ? '🎧 자동 듣는 중 · 끄기' : `🎙️ ${aiDisplayName} 대화 시작`}
                            </Text>
                        </Pressable>
                    </View>
                </SafeAreaView>
                </ImageBackground>
            </Modal>

            {/* 수신 팝업 모달(앱 전역): 수신 통화가 있고 통화가 아직 활성화되지 않았을 때 팝업으로
                뜨고, 받기/거절을 누르면 사라진다. 어느 레일/화면에 있어도 항상 위에 표시된다. */}
            <Modal
                visible={hasPendingIncomingVoip}
                transparent
                animationType="fade"
                statusBarTranslucent
                onRequestClose={() => { void handleRejectIncomingVoipCall(); }}
            >
                {pendingIncomingVoipCall ? (
                    <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.62)', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
                        <View style={styles.voipIncomingFixedCard}>
                            <Text style={styles.voipIncomingFixedTitle}>📞 수신 보이스톡</Text>
                            <Text style={styles.voipIncomingFixedCaller} numberOfLines={2}>
                                {pendingIncomingVoipCall.caller_label || pendingIncomingVoipCall.display_label || pendingIncomingVoipCall.caller_voice_id || '상대방'}
                            </Text>
                            {voipInitError ? <Text style={styles.errorText}>{voipInitError}</Text> : null}
                            <View style={styles.voipIncomingFixedActions}>
                                <Pressable
                                    style={styles.voipIncomingAcceptBtn}
                                    onPressIn={() => {
                                        logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_IN', {
                                            source_variant: 'popup_modal',
                                            pending_call_id: pendingIncomingVoipCall.call_id,
                                        });
                                    }}
                                    onPressOut={() => {
                                        logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_OUT', {
                                            source_variant: 'popup_modal',
                                            pending_call_id: pendingIncomingVoipCall.call_id,
                                        });
                                    }}
                                    onPress={() => handleIncomingAcceptPress('popup_modal')}
                                    accessibilityRole="button"
                                    accessibilityLabel="수신 보이스톡 받기"
                                    testID="worldlinco-voip-incoming-accept-popup"
                                >
                                    <Text style={styles.voipIncomingAcceptBtnText}>받기</Text>
                                </Pressable>
                                <Pressable
                                    style={styles.voipIncomingRejectBtn}
                                    onPress={() => { void handleRejectIncomingVoipCall(); }}
                                    accessibilityRole="button"
                                    accessibilityLabel="수신 보이스톡 거절"
                                    testID="worldlinco-voip-incoming-reject-popup"
                                >
                                    <Text style={styles.voipIncomingRejectBtnText}>거절</Text>
                                </Pressable>
                            </View>
                        </View>
                    </View>
                ) : null}
            </Modal>

            {showAuthDebugFloating ? (
                <View
                    pointerEvents="none"
                    style={styles.authDebugFloating}
                    accessibilityLabel={`AUTH_DEBUG_STATE:${authDebugState}`}
                    testID="auth-debug-floating-panel"
                >
                    <Text style={styles.authDebugTitle}>AUTH DEBUG</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_STATE:{authDebugState}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_USER:{authDebugUser}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_LAST_PROBE:{lastUiProbeEvent}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_RAIL_LAST_PRESSED:{railDebugLastPressed}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_RAIL_LAST_APPLIED:{railDebugLastApplied}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_SURFACE:{authDebugSurface}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_SUBMIT_MODE:{authDebugSubmitMode}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_EMAIL_FILLED:{authDebugEmailFilled ? '1' : '0'}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_PASSWORD_FILLED:{authDebugPasswordFilled ? '1' : '0'}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_FOCUS_FIELD:{authDebugFocusField}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_LAST_INPUT_EVENT:{authDebugLastInputEvent}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_EMAIL_LEN:{authDebugEmailLength}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_PASSWORD_LEN:{authDebugPasswordLength}</Text>
                    <Text style={styles.authDebugLine}>AUTH_DEBUG_SUBMIT_PRESSED:{authDebugSubmitPressedLabel}</Text>
                    {!userInfo && !showLogin ? (
                        <Pressable
                            style={styles.authDebugActionBtn}
                            onPress={() => openLoginModalForSource('floating_auth_debug')}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-auth-open-login-modal-button"
                            testID="worldlinco-auth-open-login-modal-button"
                        >
                            <Text style={styles.authDebugActionBtnText}>로그인 패널 열기</Text>
                        </Pressable>
                    ) : null}
                </View>
            ) : null}

            <Modal visible={shareTargetVisible} transparent animationType="fade" onRequestClose={() => setShareTargetVisible(false)}>
                <View style={styles.loginOverlay}>
                    <View style={styles.shareTargetModal}>
                        <Text style={styles.loginModalTitle}>공유 대상 선택</Text>
                        <Text style={styles.shareTargetHint}>현재 방과 번역 보관함 중 어디에 메시지를 남길지 선택합니다.</Text>
                        {shareTargetError ? <Text style={styles.errorText}>{shareTargetError}</Text> : null}
                        <View style={styles.shareTargetList}>
                            {shareTargetOptions.map((room) => {
                                const isCurrentRoom = !!selectedChatRoom && selectedChatRoom.room_id === room.room_id;
                                const isSelfRoom = room.title === '번역 보관함';
                                return (
                                    <Pressable
                                        key={`share-target-${room.room_id}`}
                                        style={[styles.shareTargetCard, chatShareLoading && styles.inlineGhostBtnDisabled]}
                                        onPress={() => { void handleSelectShareTarget(room); }}
                                        disabled={chatShareLoading}
                                    >
                                        <Text style={styles.shareTargetTitle}>{room.title}</Text>
                                        <Text style={styles.shareTargetMeta}>
                                            {isCurrentRoom ? '현재 방' : isSelfRoom ? '번역 보관함' : room.room_type}
                                        </Text>
                                        <View style={styles.shareTargetBadgeRow}>
                                            {room.room_type === 'group' ? (
                                                <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>그룹방</Text></View>
                                            ) : null}
                                            {room.member_count ? (
                                                <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{room.member_count}명</Text></View>
                                            ) : null}
                                            {room.allow_member_invites ? (
                                                <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>멤버 초대 허용</Text></View>
                                            ) : null}
                                        </View>
                                        <Text style={styles.shareTargetPreview}>{room.last_message_preview || '새 메시지로 공유됩니다.'}</Text>
                                    </Pressable>
                                );
                            })}
                        </View>
                        <View style={styles.modalActionRow}>
                            <Pressable
                                style={[styles.translateBtn, chatShareLoading && styles.translateBtnDisabled, styles.modalMainBtn]}
                                onPress={() => {
                                    const defaultRoom = shareTargetOptions[0];
                                    if (defaultRoom) {
                                        void handleSelectShareTarget(defaultRoom);
                                    }
                                }}
                                disabled={chatShareLoading || shareTargetOptions.length === 0}
                            >
                                <Text style={styles.translateBtnText}>{chatShareLoading ? '보내는 중...' : '첫 번째 대상으로 바로 보내기'}</Text>
                            </Pressable>
                            <Pressable
                                style={styles.modalCloseBtn}
                                onPress={() => {
                                    setShareTargetVisible(false);
                                    setPendingChatShare(null);
                                    setShareTargetOptions([]);
                                    setShareTargetError('');
                                }}
                            >
                                <Text style={styles.logoutBtnText}>닫기</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
            </Modal>

            <Modal visible={showLogin} animationType="slide" onRequestClose={() => { setAuthModalMode('login'); setLoginError(''); setShowLogin(false); }}>
                <ImageBackground source={SKY_BG} resizeMode="cover" style={styles.loginScreen}>
                    <View style={styles.loginScreenHeader}>
                        <View style={{ flex: 1 }} />
                        <Pressable
                            style={styles.loginScreenClose}
                            onPress={() => { setAuthModalMode('login'); setLoginError(''); setShowLogin(false); }}
                            accessibilityLabel="worldlinco-login-close"
                            testID="worldlinco-login-close"
                        >
                            <Text style={styles.loginScreenCloseText}>✕</Text>
                        </Pressable>
                    </View>
                    <ScrollView contentContainerStyle={styles.loginScreenBody} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
                        {authModalMode === 'login' ? (
                            <View style={styles.loginHero}>
                                <Image source={LOGIN_MASCOT} style={styles.loginHeroMascot} resizeMode="contain" />
                                <Text style={styles.loginHeroBrand}>WorldLinco</Text>
                                <Text style={styles.loginHeroTagline}>언어의 벽을 넘어, 세상을 연결합니다</Text>
                            </View>
                        ) : null}
                        <View style={styles.loginCard} accessibilityLabel="worldlinco-login-modal" testID="worldlinco-login-modal">
                        {authModalMode === 'signup' ? (
                            <>
                                <Text style={styles.loginModalTitle}>🆕 회원가입</Text>
                                <Text style={styles.loginModeHint}>
                                    {signupStep === 'verify'
                                        ? `${signupMaskedTarget || loginEmail.trim()}으로 인증 코드를 보냈습니다. 6자리 코드 입력 후 가입이 완료됩니다.`
                                        : `이메일 또는 전화로 본인 확인 후 가입합니다. 프로필 ${getLangLabelText(signupPreferredLanguage)} / ${resolveCountryFlag(signupCountryCode)} ${signupCountryCode} 는 VoIP·채팅 통역 기준으로 저장됩니다.`}
                                </Text>
                            </>
                        ) : null}
                        {showAuthDebugFloating ? (
                            <View style={styles.authDebugPanel} accessibilityLabel={`AUTH_DEBUG_STATE:${authDebugState}`} testID="auth-debug-modal-panel">
                                <Text style={styles.authDebugTitle}>AUTH DEBUG</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_STATE:{authDebugState}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_USER:{authDebugUser}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_LAST_PROBE:{lastUiProbeEvent}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_RAIL_LAST_PRESSED:{railDebugLastPressed}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_RAIL_LAST_APPLIED:{railDebugLastApplied}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_SURFACE:MODAL</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_SUBMIT_MODE:{authDebugSubmitMode}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_EMAIL_FILLED:{authDebugEmailFilled ? '1' : '0'}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_PASSWORD_FILLED:{authDebugPasswordFilled ? '1' : '0'}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_FOCUS_FIELD:{authDebugFocusField}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_LAST_INPUT_EVENT:{authDebugLastInputEvent}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_EMAIL_LEN:{authDebugEmailLength}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_PASSWORD_LEN:{authDebugPasswordLength}</Text>
                                <Text style={styles.authDebugLine}>AUTH_DEBUG_SUBMIT_PRESSED:{authDebugSubmitPressedLabel}</Text>
                            </View>
                        ) : null}
                        {authModalMode === 'signup' ? renderSignupAuthFields() : null}
                        {authModalMode !== 'signup' || signupStep === 'form' ? (
                            <>
                                <Text style={styles.loginFieldLabel}>이메일</Text>
                                <View style={styles.loginInputRow}>
                                    <Text style={styles.loginInputIcon}>✉️</Text>
                                    <TextInput
                                        style={styles.loginInput}
                                        placeholder="이메일을 입력하세요"
                                        placeholderTextColor={C.sub}
                                        autoCapitalize="none"
                                        keyboardType="email-address"
                                        showSoftInputOnFocus
                                        accessibilityLabel="worldlinco-auth-email-input"
                                        testID="worldlinco-auth-email-input"
                                        value={loginEmail}
                                        onFocus={handleLoginEmailFocus}
                                        onBlur={() => { handleLoginFieldBlur('EMAIL'); }}
                                        onChangeText={handleLoginEmailChange}
                                    />
                                </View>
                                <Text style={styles.loginFieldLabel}>비밀번호</Text>
                                <View style={styles.loginInputRow}>
                                    <Text style={styles.loginInputIcon}>🔒</Text>
                                    <TextInput
                                        style={styles.loginInput}
                                        placeholder="비밀번호를 입력하세요"
                                        placeholderTextColor={C.sub}
                                        secureTextEntry={!showLoginPw}
                                        showSoftInputOnFocus
                                        accessibilityLabel="worldlinco-auth-password-input"
                                        testID="worldlinco-auth-password-input"
                                        value={loginPw}
                                        onFocus={handleLoginPasswordFocus}
                                        onBlur={() => { handleLoginFieldBlur('PASSWORD'); }}
                                        onChangeText={handleLoginPasswordChange}
                                    />
                                    <Pressable
                                        onPress={() => setShowLoginPw((v) => !v)}
                                        style={styles.loginInputEye}
                                        accessibilityLabel="worldlinco-auth-password-visibility"
                                        testID="worldlinco-auth-password-visibility"
                                    >
                                        <Text style={styles.loginInputEyeText}>{showLoginPw ? '🙈' : '👁'}</Text>
                                    </Pressable>
                                </View>
                            </>
                        ) : null}
                        {loginError ? <Text style={styles.errorText}>{loginError}</Text> : null}
                        <Pressable
                            style={[styles.loginPrimaryBtn, loginLoading && styles.translateBtnDisabled]}
                            onPress={authModalMode === 'login' ? handleLogin : handleSignupSubmit}
                            disabled={loginLoading}
                            accessibilityRole="button"
                            accessibilityLabel={authModalMode === 'login' ? 'worldlinco-auth-login-submit-button' : 'worldlinco-auth-signup-submit-button'}
                            testID={authModalMode === 'login' ? 'worldlinco-auth-login-submit-button' : 'worldlinco-auth-signup-submit-button'}
                        >
                            {loginLoading ? (
                                <ActivityIndicator color="#fff" size="small" />
                            ) : (
                                <Text style={styles.loginPrimaryBtnText}>{signupSubmitLabel}</Text>
                            )}
                        </Pressable>
                        {authModalMode === 'login' ? (
                            <View style={styles.loginUtilityRow}>
                                {biometricLoginReady && biometricLoginEnabled ? (
                                    <Pressable style={styles.loginUtilityItem} onPress={() => { void handleBiometricLogin(); }} disabled={biometricLoginBusy} testID="worldlinco-auth-biometric-login-modal">
                                        <Text style={styles.loginUtilityIcon}>👆</Text>
                                        <Text style={styles.authUtilityLinkText}>{biometricLoginBusy ? '지문 확인 중...' : '생체인증'}</Text>
                                    </Pressable>
                                ) : <View />}
                                <Pressable onPress={openPasswordRecovery} testID="worldlinco-auth-forgot-password-modal">
                                    <Text style={styles.authUtilityLinkText}>비밀번호 찾기</Text>
                                </Pressable>
                            </View>
                        ) : null}
                        <View style={styles.loginDivider} />
                        <View style={styles.loginSignupRow}>
                            <Text style={styles.loginSignupHint}>{authModalMode === 'login' ? '계정이 없으신가요?' : '이미 계정이 있으신가요?'}</Text>
                            <Pressable
                                onPress={toggleAuthModalMode}
                                accessibilityLabel="worldlinco-modal-auth-mode-toggle"
                                testID="worldlinco-modal-auth-mode-toggle"
                            >
                                <Text style={styles.loginSignupLink}>{authModalMode === 'login' ? '회원가입' : '로그인'}</Text>
                            </Pressable>
                        </View>
                        <Pressable
                            style={[styles.loginDemoBtn, demoSessionLoading && styles.inlineGhostBtnDisabled]}
                            onPress={() => { void handleStartInstantDemoSession('chat'); }}  // NOSONAR
                            disabled={demoSessionLoading || loginLoading}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-demo-session-start-button"
                            testID="worldlinco-demo-session-start-button"
                        >
                            <Text style={styles.loginDemoBtnText}>{demoSessionLoading ? '데모 연결 중...' : '데모 세션 둘러보기'}</Text>
                        </Pressable>
                        </View>
                    </ScrollView>
                </ImageBackground>
            </Modal>

            <Modal
                visible={langPickerFor !== null}
                transparent
                animationType="fade"
                onRequestClose={() => setLangPickerFor(null)}
            >
                <View style={styles.loginOverlay}>
                    <View style={styles.loginModal}>
                        <Text style={styles.loginModalTitle}>
                            {langPickerFor === 'from'
                                ? `${getUiText(fromLang).sourceLang} 선택`
                                : `${getUiText(fromLang).peerLanguageLabel ?? getUiText(fromLang).targetLang} 선택`}
                        </Text>
                        <Text style={styles.loginModeHint}>
                            {langPickerFor === 'from'
                                ? (userInfo ? '내 언어는 프로필 설정에서 변경합니다.' : getUiText(fromLang).manualVoiceOnlyNotice)
                                : getUiText(fromLang).peerLanguageHint ?? getUiText(fromLang).manualLanguageHint}
                        </Text>
                        <ScrollView style={styles.contactPickerList} contentContainerStyle={styles.contactPickerListBody}>
                            {LANGS.map((lang) => {
                                const active = (langPickerFor === 'from' ? fromLang : toLang) === lang.code;
                                return (
                                    <Pressable
                                        key={`travel-lang-${langPickerFor}-${lang.code}`}
                                        style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                        onPress={() => handleSelectLanguage(lang.code)}
                                    >
                                        <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>{lang.label}</Text>
                                    </Pressable>
                                );
                            })}
                        </ScrollView>
                        <View style={styles.modalActionRow}>
                            <Pressable style={styles.modalCloseBtn} onPress={() => setLangPickerFor(null)}>
                                <Text style={styles.logoutBtnText}>닫기</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
            </Modal>

            <Modal
                visible={interCallContactPickerVisible}
                transparent
                animationType="fade"
                onRequestClose={() => setInterCallContactPickerVisible(false)}
            >
                <View style={styles.loginOverlay}>
                    <View style={styles.loginModal}>
                        <Text style={styles.loginModalTitle}>📇 연락처 연동</Text>
                        <Text style={styles.loginModeHint}>기기 연락처를 불러와 채팅·VoIP·일반통화에 연결합니다. 연락처 선택 후 채팅/초대 또는 일반통화를 고르세요.</Text>
                        {interCallContactError ? <Text style={styles.errorText}>{interCallContactError}</Text> : null}
                        <ScrollView style={styles.contactPickerList} contentContainerStyle={styles.contactPickerListBody}>
                            {(interCallContactOptions ?? []).map((contact) => (
                                <Pressable
                                    key={`inter-contact-${contact.id}`}
                                    style={styles.contactPickerRow}
                                    onPress={() => presentContactActionChooser(contact)}
                                >
                                    <Text style={styles.contactPickerName}>{contact.name}</Text>
                                    <Text style={styles.contactPickerMeta}>{contact.label} · {contact.phone}</Text>
                                </Pressable>
                            ))}
                            {!interCallContactLoading && interCallContactOptions.length === 0 ? (
                                <Text style={styles.contactPickerEmpty}>표시할 연락처가 없습니다.</Text>
                            ) : null}
                        </ScrollView>
                        <View style={styles.modalActionRow}>
                            <Pressable style={styles.inlineGhostBtn} onPress={() => { void handleOpenInterCallContactPicker(); }}>  // NOSONAR
                                <Text style={styles.inlineGhostBtnText}>{interCallContactLoading ? '새로고침 중...' : '다시 불러오기'}</Text>
                            </Pressable>
                            <Pressable style={styles.modalCloseBtn} onPress={() => setInterCallContactPickerVisible(false)}>
                                <Text style={styles.logoutBtnText}>닫기</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
            </Modal>

            <ContactsDirectoryModal
                visible={contactsDirectoryVisible}
                onClose={() => setContactsDirectoryVisible(false)}
                apiBase={API_BASE}
                inviterName={userInfo?.username || userInfo?.email?.split('@')[0] || ''}
                loadFriends={loadFriendsForDirectory}
                onRegularCall={(contact) => { void handleRegularCallContact(contact); }}
                onVoipCall={handleVoipCallContact}
                onChat={(contact, friend) => { void handleChatContact(contact, friend); }}
            />

            {userInfo ? (
                <Pressable
                    style={styles.settingsGearButton}
                    onPress={openSettingsModal}
                    accessibilityRole="button"
                    accessibilityLabel="월드링코 설정 열기"
                    testID="worldlinco-settings-gear"
                    hitSlop={8}
                >
                    <Text style={styles.settingsGearIcon}>⚙️</Text>
                </Pressable>
            ) : null}

            <Modal
                visible={isSettingsModalOpen}
                transparent
                animationType="slide"
                statusBarTranslucent
                onRequestClose={() => setIsSettingsModalOpen(false)}
            >
                <View style={styles.settingsOverlay}>
                    <View style={styles.settingsCard}>
                        <View style={styles.settingsHeaderRow}>
                            <Text style={styles.settingsTitle}>⚙️ 월드링코 설정</Text>
                            <Pressable
                                onPress={() => setIsSettingsModalOpen(false)}
                                accessibilityRole="button"
                                accessibilityLabel="설정 닫기"
                                testID="worldlinco-settings-close"
                                hitSlop={8}
                            >
                                <Text style={styles.settingsCloseText}>✕</Text>
                            </Pressable>
                        </View>

                        <ScrollView style={styles.settingsScroll} keyboardShouldPersistTaps="handled">
                            {/* 1) 소리/진동/무음 */}
                            <Text style={styles.settingsSectionTitle}>🔔 수신 알림</Text>
                            <Text style={styles.settingsSectionSub}>보이스톡/채팅 수신 시 울림 방식을 선택합니다.</Text>
                            <View style={styles.settingsSegmentRow}>
                                {([
                                    { mode: 'sound' as IncomingAlertSoundMode, label: '🔊 소리' },
                                    { mode: 'vibrate' as IncomingAlertSoundMode, label: '📳 진동' },
                                    { mode: 'silent' as IncomingAlertSoundMode, label: '🔕 무음' },
                                ]).map((item) => {
                                    const active = incomingAlertSoundMode === item.mode;
                                    return (
                                        <Pressable
                                            key={`alert-mode-${item.mode}`}
                                            style={[styles.settingsSegment, active && styles.settingsSegmentActive]}
                                            onPress={() => updateIncomingAlertSoundMode(item.mode)}
                                            accessibilityRole="button"
                                            accessibilityLabel={`수신 알림 ${item.label}`}
                                            testID={`worldlinco-settings-alert-${item.mode}`}
                                        >
                                            <Text style={[styles.settingsSegmentText, active && styles.settingsSegmentTextActive]}>{item.label}</Text>
                                        </Pressable>
                                    );
                                })}
                            </View>

                            {/* 2) 내정보(국가/언어) */}
                            <Text style={[styles.settingsSectionTitle, { marginTop: 18 }]}>🌐 내 정보</Text>
                            <Text style={styles.settingsSectionSub}>{userInfo?.email || ''}</Text>
                            <Pressable
                                style={styles.settingsRow}
                                onPress={() => { setSettingsCountryPickerOpen((v) => !v); setSettingsLangPickerOpen(false); }}
                                testID="worldlinco-settings-country-toggle"
                            >
                                <Text style={styles.settingsRowLabel}>국가</Text>
                                <Text style={styles.settingsRowValue}>
                                    {(SIGNUP_COUNTRY_OPTIONS.find((c) => c.code === (userInfo?.country_code || ''))?.label)
                                        || COUNTRY_NAME_MAP[String(userInfo?.country_code || '')]
                                        || userInfo?.country_code
                                        || '미설정'} ▾
                                </Text>
                            </Pressable>
                            {settingsCountryPickerOpen ? (
                                <ScrollView style={styles.settingsPickerList} nestedScrollEnabled>
                                    {SIGNUP_COUNTRY_OPTIONS.map((c) => {
                                        const active = c.code === (userInfo?.country_code || '');
                                        return (
                                            <Pressable
                                                key={`settings-country-${c.code}`}
                                                style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                                onPress={() => handleSettingsChangeCountry(c.code)}
                                                testID={`worldlinco-settings-country-${c.code}`}
                                            >
                                                <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>{c.label} ({c.code})</Text>
                                                {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                            </Pressable>
                                        );
                                    })}
                                </ScrollView>
                            ) : null}
                            <Pressable
                                style={styles.settingsRow}
                                onPress={() => { setSettingsLangPickerOpen((v) => !v); setSettingsCountryPickerOpen(false); }}
                                testID="worldlinco-settings-language-toggle"
                            >
                                <Text style={styles.settingsRowLabel}>통역/번역 언어</Text>
                                <Text style={styles.settingsRowValue}>
                                    {(LANGS.find((l) => l.code === (userInfo?.preferred_language || ''))?.label)
                                        || userInfo?.preferred_language
                                        || '미설정'} ▾
                                </Text>
                            </Pressable>
                            {settingsLangPickerOpen ? (
                                <ScrollView style={styles.settingsPickerList} nestedScrollEnabled>
                                    {LANGS.map((l) => {
                                        const active = l.code === (userInfo?.preferred_language || '');
                                        return (
                                            <Pressable
                                                key={`settings-lang-${l.code}`}
                                                style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                                onPress={() => handleSettingsChangeLanguage(l.code)}
                                                testID={`worldlinco-settings-language-${l.code}`}
                                            >
                                                <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>{l.label}</Text>
                                                {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                            </Pressable>
                                        );
                                    })}
                                </ScrollView>
                            ) : null}
                            {settingsProfileSaving ? <Text style={styles.settingsSectionSub}>저장 중...</Text> : null}
                            {settingsProfileError ? <Text style={styles.errorText}>{settingsProfileError}</Text> : null}
                            {settingsProfileSuccess ? <Text style={styles.successText}>{settingsProfileSuccess}</Text> : null}

                            {/* 3) 비밀번호 변경 */}
                            <Text style={[styles.settingsSectionTitle, { marginTop: 18 }]}>🔒 보안</Text>
                            <Pressable
                                style={styles.settingsActionBtn}
                                onPress={handleOpenPasswordChangeFromSettings}
                                testID="worldlinco-settings-password-change"
                            >
                                <Text style={styles.settingsActionBtnText}>비밀번호 변경</Text>
                            </Pressable>
                        </ScrollView>

                        <Pressable
                            style={styles.settingsDoneBtn}
                            onPress={() => setIsSettingsModalOpen(false)}
                            testID="worldlinco-settings-done"
                        >
                            <Text style={styles.settingsDoneBtnText}>완료</Text>
                        </Pressable>
                    </View>
                </View>
            </Modal>

            <PasswordSecurityModal
                visible={showPasswordSecurity}
                mode={passwordSecurityMode}
                apiBase={API_BASE}
                authToken={token || undefined}
                defaultEmail={userInfo?.email || loginEmail}
                onClose={() => setShowPasswordSecurity(false)}
                onCompleted={(payload) => { void handlePasswordSecurityCompleted(payload); }}  // NOSONAR
            />

            <DataSourcesModal visible={showDataSources} onClose={() => setShowDataSources(false)} />
        </SafeAreaView>
        </ImageBackground>
    );
}

export default function App() {
    return (
        <SafeAreaProvider>
            <AppInner />
        </SafeAreaProvider>
    );
}
