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
    Linking,
    Modal,
    PermissionsAndroid,
    Platform,
    Pressable,
    SafeAreaView,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    ToastAndroid,
    Vibration,
    View,
} from 'react-native';
import WebView, { type WebViewMessageEvent } from 'react-native-webview';
import { translateImage, translateText, synthesizeSpeech, type TranslateOptions } from './src/api/translate';
import { isTravelItineraryIntent } from './src/api/tourismAnswer';
import { FEATURE_IDS, newCorrelationId } from './src/features/correlation/correlationId';
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
import type { ChatRoomSummary } from './src/features/chat/types';
import TravelItineraryPanel from './src/features/travel-itinerary/TravelItineraryPanel';
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
import { registerVoipDevice } from './src/services/voipPresence';
import { createVoipMessagingAdapter } from './src/services/voipMessagingAdapter';
import { ensureVoipIncomingNotificationChannel, showIncomingVoipLocalNotification } from './src/services/voipIncomingNotifications';
import { ensureChatMessageNotificationChannel } from './src/services/chatIncomingNotifications';
import {
    areVoipNotificationsEnabled,
    isVoipIncomingAlertNativeAvailable,
    openVoipNotificationSettings,
    startNativeIncomingVoipAlert,
    stopNativeIncomingVoipAlert,
} from './src/native/voipIncomingAlert';
import { acceptIncomingCall } from './src/services/voipPresence';
import { enableVoipAudio, disableVoipAudio } from './src/native/voipAudio';
import { CallInitResponse, type TURNServer } from './src/services/voipCallClient';
import { getVoIPToneService } from './src/services/voipToneService';
import { parsePersistedGpsSnapshot, serializePersistedGpsSnapshot } from './src/utils/hybridGpsCache';
import { detectHybridGpsMode, scoreLocationQuality, type HybridGpsMode } from './src/utils/hybridGps';
import {
    WORLDLINGO_BRAND_NAME,
    WORLDLINGO_ENGINE_LABEL,
    matchesWorldLincoProjectTitle,
} from './src/constants/worldlincoBrand';
import { resolveVoipTtsLocale } from './src/constants/voipLanguageLocales';
import { correctTtsLocaleForScriptLeak } from './src/utils/scriptLangResolver';
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
} from './src/features/voip-voice-relay/voiceRelayOrchestrator';
import { getWorldlincoTuning, hydrateWorldlincoTuningFromStorage, refreshWorldlincoTuning } from './src/services/worldlincoTuningConfig';

type MonetizationPlanKey = 'voip_lite' | 'voip_pro' | 'song_pass';

type SectionRailKey = 'chat' | 'voip' | 'song-mode' | 'travel-booking';
type VoipGenderOption = 'male' | 'female' | 'unknown';
type VoipParticipantProfile = {
    nickname: string;
    genderLabel: string;
    countryCode: string;
    countryName: string;
    voiceId: string;
    countryFlag: string;
    preferredLanguage?: string;
};

type DevicePhoneContact = {
    id: string;
    name: string;
    phone: string;
    label: string;
};

type SearchCategory = 'all' | 'hotel' | 'airport' | 'restaurant' | 'attraction';

type NearbyPlace = {
    id: string;
    category: 'hotel' | 'airport' | 'restaurant' | 'attraction';
    category_label: string;
    name: string;
    address: string;
    distance_m: number;
    rating: number;
    price_tier: string;
    booking_supported: boolean;
    phone: string;
    summary: string;
    latitude: number;
    longitude: number;
    google_maps_url: string;
}

type BookingResponse = {
    confirmation_id: string;
    booking_message: string;
    translated_message: string;
    place_name: string;
    support_phone: string;
    google_maps_url: string;
};

type PurchaseResult = {
    id: number;
    project_id: number;
    buyer_id: number;
    amount: number;
    status: string;
    payment_method: string;
};

type StoredActiveVoipSession = {
    callId: string;
    railSection?: SectionRailKey | null;
    acceptedParticipantRole?: 'caller' | 'callee' | null;
    acceptedAt?: string | null;
};

type CallModeAuditEvent = {
    id: number | string;
    event_type: string;
    requested_mode: string | null;
    resolved_mode: string | null;
    call_route?: string | null;
    status?: string | null;
    error_code?: string | null;
    created_at: string;
};

const TERMINAL_VOIP_STATUSES = new Set([
    'cancelled',
    'canceled',
    'completed',
    'ended',
    'failed',
    'no_answer',
    'rejected',
    'busy',
    'callee_offline',
    'timeout',
]);

const SECTION_RAIL_ITEMS: Array<{ key: SectionRailKey; label: string; icon: string }> = [
    { key: 'chat', label: '채팅', icon: '💬' },
    { key: 'voip', label: '통화', icon: '📞' },
    { key: 'song-mode', label: '노래', icon: '🎵' },
    { key: 'travel-booking', label: '예약', icon: '🧭' },
];

function buildSectionRailSelector(section: SectionRailKey): string {
    return `worldlinco-section-rail-${section}-button`;
}

function normalizeCallModeCandidate(mode?: string | null): CallMode | null {
    if (mode === 'pstn_assist' || mode === 'voip_full_auto') {
        return mode;
    }
    return null;
}

function resolveCallModeFromPayload(payload: Partial<CallInitResponse>): CallMode {
    const resolvedMode = normalizeCallModeCandidate(payload.resolved_mode);
    if (resolvedMode) {
        return resolvedMode;
    }

    const requestedMode = normalizeCallModeCandidate(payload.requested_mode);
    if (requestedMode) {
        return requestedMode;
    }

    if (payload.call_route === 'app_webrtc' || payload.phone_dialer_required === false || payload.auto_relay_applied) {
        return 'voip_full_auto';
    }

    return 'pstn_assist';
}

type TranslationStatusRoute = 'PSTN' | 'VOIP';
type TranslationStatusPhase = 'READY' | 'LISTEN' | 'TRANSLATE' | 'SPEAK' | 'ERROR' | 'INFO';

function formatUnifiedCallModeText(requestedMode?: string | null, resolvedMode?: string | null): string {
    return `[통번역 모드] ${requestedMode || 'null'} -> ${resolvedMode || 'null'}`;
}

function formatUnifiedTranslationStatus(route: TranslationStatusRoute, phase: TranslationStatusPhase, detail: string): string {
    return `[통번역 ${route}/${phase}] ${detail}`;
}

function isTerminalVoipStatus(status?: string | null): boolean {
    return Boolean(status && TERMINAL_VOIP_STATUSES.has(status));
}

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

const MONETIZATION_PLAN_CONFIG: Record<MonetizationPlanKey, {
    amount: number;
    title: string;
    shortLabel: string;
    billingLabel: string;
    usageLabel: string;
    formulaLabel: string;
    description: string;
}> = {
    voip_lite: {
        amount: 9900,
        title: 'VoIP Premium Lite',
        shortLabel: 'Lite',
        billingLabel: '월 9,900원',
        usageLabel: '월 60분 통역 통화 권장',
        formulaLabel: '기준 원가식: (월 고정비 + 통역분당변동비 x 60분) / 60분',
        description: '가벼운 여행/상담용 실시간 통역 통화를 위한 월정액입니다.',
    },
    voip_pro: {
        amount: 19900,
        title: 'VoIP Premium Pro',
        shortLabel: 'Pro',
        billingLabel: '월 19,900원',
        usageLabel: '월 300분 통역 통화 권장',
        formulaLabel: '기준 원가식: (월 고정비 + 통역분당변동비 x 300분) / 300분',
        description: '상시 통화가 필요한 고객 상담/업무형 통역 사용자를 위한 월정액입니다.',
    },
    song_pass: {
        amount: 2900,
        title: 'Song Translation Pass',
        shortLabel: '1곡',
        billingLabel: '건당 2,900원',
        usageLabel: '노래 파일 1건 처리',
        formulaLabel: '기준 원가식: 업로드/자막처리/검수 계산량을 1곡 기준으로 회수',
        description: '노래 번역은 사용 편차가 커서 건당 과금으로 분리합니다.',
    },
};

const PREMIUM_PURCHASE_STATUSES = new Set(['paid', 'completed', 'success', 'succeeded', 'approved']);

function isPurchaseSettled(status: string | null | undefined): boolean {
    return PREMIUM_PURCHASE_STATUSES.has(String(status || '').trim().toLowerCase());
}

function resolvePlanKeyFromPurchase(amount: number): MonetizationPlanKey | null {
    const planEntries = Object.entries(MONETIZATION_PLAN_CONFIG) as Array<[MonetizationPlanKey, typeof MONETIZATION_PLAN_CONFIG[MonetizationPlanKey]]>;
    const matchedEntry = planEntries.find(([, config]) => config.amount === amount);
    return matchedEntry ? matchedEntry[0] : null;
}

function collectOwnedPlanKeys(purchases: Array<{ id: number; amount: number; status: string; payment_method: string }> | null): Set<MonetizationPlanKey> {
    const ownedPlans = new Set<MonetizationPlanKey>();
    if (!purchases) {
        return ownedPlans;
    }
    for (const purchase of purchases) {
        if (!isPurchaseSettled(purchase.status)) {
            continue;
        }
        const planKey = resolvePlanKeyFromPurchase(Number(purchase.amount));
        if (planKey) {
            ownedPlans.add(planKey);
        }
    }
    return ownedPlans;
}

type UserInfo = {
    id: number;
    email: string;
    username?: string;
    preferred_language?: string;
    country_code?: string | null;
};

type SignupPayload = {
    username: string;
    email: string;
    password: string;
    preferred_language: string;
    country_code?: string | null;
    full_name?: string;
    phone_number?: string;
    verificationChannel?: 'email' | 'phone';
    member_type: 'individual';
};

type UserProfileUpdatePayload = {
    preferred_language: string;
    country_code?: string | null;
};

type AuthModalMode = 'login' | 'signup';

const API_BASE: string =
    (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
    'http://10.0.2.2:8000';

const WORLDLINGO_APP_NAME = WORLDLINGO_BRAND_NAME;
const APP_VERSION_NUMBER = String(
    Constants.expoConfig?.version
    ?? Constants.nativeAppVersion
    ?? '1.0.68',
);
const APP_BUILD_NUMBER = String(
    Constants.expoConfig?.android?.versionCode
    ?? Constants.nativeBuildVersion
    ?? '98',
);
const APP_VERSION_LABEL = `v${APP_VERSION_NUMBER} · build ${APP_BUILD_NUMBER}`;
const APP_FOOTER_BRAND = `${WORLDLINGO_BRAND_NAME} v${APP_VERSION_NUMBER} · ${WORLDLINGO_ENGINE_LABEL}`;
const APP_FOOTER_BRAND_KO = `${WORLDLINGO_BRAND_NAME} v${APP_VERSION_NUMBER} · ${WORLDLINGO_ENGINE_LABEL}`;
const LATEST_APK_METADATA_PATH = '/api/marketplace/latest-apk-metadata';
const VERSION_CHECK_KEY = 'app_latest_version_check';
const VERSION_IGNORE_KEY = 'app_version_ignore';
const AUTH_STORAGE_KEY = 'nadot_auth_state';
const ACTIVE_VOIP_CALL_STORAGE_KEY = 'nadot_active_voip_call_v1';
const VOIP_VALIDATION_FRIEND_CALL_BYPASS_KEY = 'nadot_voip_validation_friend_call_bypass_v1';
// 실험/베타: VoIP 통역 지정 언어를 백엔드 프로필 고정값 대신 이 단말에서 직접 선택(로컬 오버라이드).
// 값이 있으면 currentVoipPreferredLanguage가 백엔드 preferred_language보다 우선 사용한다.
const VOIP_LOCAL_LANG_STORAGE_KEY = 'nadot_voip_local_lang_v1';
const RELEASE_CHANNEL = (process.env.EXPO_PUBLIC_RELEASE_CHANNEL || '').trim().toLowerCase();
// 사이드로드(마켓 직접 배포) 단말은 항상 인앱 자동 업데이트를 켠다.
// EXPO_PUBLIC_DISABLE_UPDATE_PROMPT=1 로만 비활성화 가능.
const ENABLE_IN_APP_UPDATE_PROMPT =
    (process.env.EXPO_PUBLIC_DISABLE_UPDATE_PROMPT || '').trim() !== '1';
// 사용자가 "나중에"를 누른 빌드 번호 저장 → 같은 빌드는 재알림하지 않되, 더 새 빌드가 올라오면 다시 알린다.
const VERSION_SNOOZE_BUILD_KEY = 'app_update_snooze_build_v1';
const VOIP_DEFAULT_PHONE_PREFIX = '+82-';
const VOIP_INCOMING_LINK_SCHEMES = ['worldlingo', 'worldlinco', 'com.parkcheolhong.worldlinco'];
const VOIP_INCOMING_LINK_PATH = 'voip/incoming';
const APP_ENTRY_RAIL_LINK_PATH = 'rail/open';
const APP_ENTRY_VOIP_LINK_PATH = 'voip/open';
const APP_ENTRY_CHAT_LINK_PATH = 'chat/open';
const DEMO_SESSION_EMAIL_DOMAIN = 'instant-demo.worldlinco.dev';
const AUTH_DEBUG_MARKER_ENABLED = __DEV__ || (process.env.EXPO_PUBLIC_AUTH_DEBUG_MARKER || '').trim() === '1';
const OCR_DEBUG_IMAGE_URI =
    (process.env.EXPO_PUBLIC_OCR_DEBUG_IMAGE_URI || '').trim() ||
    (String(Constants.expoConfig?.extra?.ocrDebugImageUri || '')).trim();
const OCR_DEBUG_IMAGE_NAME = (process.env.EXPO_PUBLIC_OCR_DEBUG_IMAGE_NAME || '').trim();
const FIREBASE_ANDROID_OPTIONS = {
    apiKey: 'AIzaSyA90Rs93geo1Sz94HmdHL94X34r7eH8wGo',
    appId: '1:409873234227:android:094e3ebdb0001592b0a646',
    messagingSenderId: '409873234227',
    projectId: 'studio-9080238625-9cec3',
    storageBucket: 'studio-9080238625-9cec3.firebasestorage.app',
};
const buildVoiceId = (userId: number) => `nado-${String(userId).padStart(6, '0')}`;

const buildVoipTopic = (voiceId: string) =>
    `worldlingo_voip_${voiceId.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_')}`;

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

const parseVersionTriplet = (value: string): number[] => {
    const raw = String(value || '').trim();
    const match = raw.match(/^(\d+)\.(\d+)\.(\d+)$/);
    if (!match) {
        return [0, 0, 0];
    }
    return match.slice(1).map((item) => Number.parseInt(item, 10));
};

const parseBuildNumber = (value: string): number => {
    const parsed = Number.parseInt(String(value || '').trim(), 10);
    return Number.isFinite(parsed) ? parsed : 0;
};

const compareSemanticVersions = (left: string, right: string): number => {
    const leftParts = parseVersionTriplet(left);
    const rightParts = parseVersionTriplet(right);
    for (let index = 0; index < 3; index += 1) {
        if (leftParts[index] > rightParts[index]) {
            return 1;
        }
        if (leftParts[index] < rightParts[index]) {
            return -1;
        }
    }
    return 0;
};

const isRemoteApkNewer = (
    currentVersion: string,
    currentBuild: string,
    remoteVersion?: string | null,
    remoteBuild?: string | null,
): boolean => {
    const normalizedRemoteVersion = String(remoteVersion || '').trim();
    if (!normalizedRemoteVersion) {
        return false;
    }
    const versionComparison = compareSemanticVersions(normalizedRemoteVersion, currentVersion);
    if (versionComparison > 0) {
        return true;
    }
    if (versionComparison < 0) {
        return false;
    }
    return parseBuildNumber(remoteBuild || '') > parseBuildNumber(currentBuild);
};

const resolveLatestApkMetadataUrl = (updateUrl: string): string => {
    if (/\/latest\.apk(?:[?#].*)?$/i.test(updateUrl)) {
        return updateUrl.replace(/\/latest\.apk(?:[?#].*)?$/i, '/latest-apk-metadata');
    }
    return `${API_BASE.replace(/\/$/, '')}${LATEST_APK_METADATA_PATH}`;
};

const buildVoipWebSocketUrl = (apiBase: string, path: string, query: Record<string, string> = {}) => {
    const normalizedBase = apiBase.replace(/\/$/, '');
    const wsBase = normalizedBase.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:');
    const searchParams = new URLSearchParams(query);
    const queryString = searchParams.toString();
    return `${wsBase}${path}${queryString ? `?${queryString}` : ''}`;
};

function buildInstantDemoCredentials(seed: string) {
    const normalizedSeed = seed.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 10) || 'guestdemo';
    return {
        email: `instant-${normalizedSeed}@${DEMO_SESSION_EMAIL_DOMAIN}`,
        username: `instant_${normalizedSeed}`,
        password: `WorldLinco!${normalizedSeed}A1`,
    };
}
function parseSectionRailKey(value: string | null | undefined): SectionRailKey | null {
    switch (String(value || '').trim().toLowerCase()) {
        case 'chat':
            return 'chat';
        case 'voip':
            return 'voip';
        case 'song':
        case 'song-mode':
            return 'song-mode';
        case 'travel':
        case 'travel-booking':
            return 'travel-booking';
        default:
            return null;
    }
}

type AppEntryDeepLinkTarget =
    | { type: 'rail'; section: SectionRailKey }
    | { type: 'chat'; roomId: string }
    | { type: 'voip'; action: 'open' | 'validation' | 'demo' | 'incoming'; callId?: string; calleeVoiceId?: string; forceRetry?: boolean; preferredLanguage?: string; calleePreferredLanguage?: string };

function parseAppEntryDeepLink(url: string): AppEntryDeepLinkTarget | null {
    try {
        const parsed = new URL(url);
        const scheme = parsed.protocol.replace(':', '').toLowerCase();
        if (!VOIP_INCOMING_LINK_SCHEMES.includes(scheme)) {
            return null;
        }

        const resolvedPath = `${parsed.hostname}${parsed.pathname}`.replace(/^\/+/, '').toLowerCase();
        if (resolvedPath === APP_ENTRY_RAIL_LINK_PATH) {
            const section = parseSectionRailKey(parsed.searchParams.get('section'));
            return section ? { type: 'rail', section } : null;
        }

        if (resolvedPath === APP_ENTRY_CHAT_LINK_PATH) {
            const roomId = String(parsed.searchParams.get('room_id') || '').trim();
            return roomId ? { type: 'chat', roomId } : null;
        }

        if (resolvedPath !== APP_ENTRY_VOIP_LINK_PATH) {
            return null;
        }

        const action = String(parsed.searchParams.get('action') || 'open').trim().toLowerCase();
        const callId = String(parsed.searchParams.get('call_id') || '').trim() || undefined;
        const calleeVoiceId = String(parsed.searchParams.get('callee_voice_id') || '').trim() || undefined;
        const preferredLanguage = String(parsed.searchParams.get('preferred_language') || parsed.searchParams.get('source_lang') || '').trim().toLowerCase() || undefined;
        const calleePreferredLanguage = String(parsed.searchParams.get('callee_preferred_language') || parsed.searchParams.get('target_lang') || '').trim().toLowerCase() || undefined;
        const forceRetry = String(parsed.searchParams.get('force') || '').trim() === '1'
            || String(parsed.searchParams.get('retry') || '').trim() === '1';
        if (action === 'incoming') {
            return callId ? { type: 'voip', action: 'incoming', callId } : null;
        }
        if (action === 'validation') {
            return { type: 'voip', action: 'validation', calleeVoiceId, forceRetry, preferredLanguage, calleePreferredLanguage };
        }
        if (action === 'demo') {
            return { type: 'voip', action: 'demo', forceRetry, preferredLanguage, calleePreferredLanguage };
        }
        return { type: 'voip', action: 'open', calleeVoiceId, forceRetry, preferredLanguage, calleePreferredLanguage };
    } catch {
        return null;
    }
}

const CATEGORY_OPTIONS: Array<{ label: string; value: SearchCategory }> = [
    { label: '전체', value: 'all' },
    { label: '호텔', value: 'hotel' },
    { label: '공항', value: 'airport' },
    { label: '식당', value: 'restaurant' },
    { label: '관광명소', value: 'attraction' },
];

const RADIUS_OPTIONS: Array<{ label: string; value: number }> = [
    { label: '5km', value: 5000 },
    { label: '30km', value: 30000 },
    { label: '50km', value: 50000 },
    { label: '70km', value: 70000 },
    { label: '100km', value: 100000 },
];

const AUTO_RELAY_DELAY_OPTIONS_MS = [2000, 2500, 3000] as const;
const DEFAULT_AUTO_RELAY_DELAY_MS = 2500;
/** 여행 대면 통역 — TTS 후 다음 마이크 재개 지연 */
const FACE_CONVERSATION_RESTART_MS = 250;
const FACE_CONVERSATION_PLAYBACK_CAP_MS = 10000;
const FACE_CONVERSATION_PERMISSION_RETRY_MS = 800;
/**
 * 여행 대면 통역 — TTS 재생물이 마이크로 되돌아와 재번역되는 핑퐁 에코를 차단하는 보호창.
 * STT 왕복이 10초 이상 걸릴 수 있어, 에코가 가드창을 지나 도착하지 않도록 넉넉히 잡는다.
 */
const FACE_CONVERSATION_ECHO_GUARD_MS = 25000;
/** 에코 비교 대상으로 보관할 최근 발화 개수. */
const FACE_CONVERSATION_SPOKEN_HISTORY = 5;
/**
 * 여행 대면 통역 — TTS 재생 완료 후 잔향이 가라앉을 때까지 듣기를 막는 drain 지연.
 * 이 시간 동안 반이중 게이트(faceSpeakingRef)를 유지해 스피커 잔향을 다시 잡지 않도록 한다.
 */
const FACE_CONVERSATION_PLAYBACK_DRAIN_MS = 1500;
/**
 * 여행 대면 통역 — 방금 발화한 '출력 언어'로 입력이 되돌아올 때 자기 TTS 에코로 보고 무시하는 창.
 * 재생 종료 직후 마이크가 잡는 잔향(역번역 루프)을 끊는 용도. 실제 상대 화자 응답을 너무 오래
 * 막지 않도록 짧게 잡는다(반이중 게이트 drain 직후의 첫 캡처 잔향만 차단).
 */
const FACE_OUTPUT_ECHO_GUARD_MS = 5000;
const TRANSLATION_REQUEST_TIMEOUT_MS = 30_000;
const AUTO_RELAY_DUPLICATE_GUARD_MS = 8000;
const VOIP_GENDER_OPTIONS: Array<{ value: VoipGenderOption; label: string }> = [
    { value: 'male', label: '남성' },
    { value: 'female', label: '여성' },
    { value: 'unknown', label: '미설정' },
];

function formatVoipGenderLabel(gender: VoipGenderOption): string {
    switch (gender) {
        case 'male':
            return '남성';
        case 'female':
            return '여성';
        default:
            return '미설정';
    }
}

function formatDiscoveryGenderLabel(gender?: DiscoveryGender | VoipGenderOption): string {
    switch (gender) {
        case 'male':
            return '남성';
        case 'female':
            return '여성';
        case 'other':
            return '기타';
        default:
            return '미설정';
    }
}

function resolveDiscoveryGenderFromProfile(gender: VoipGenderOption): DiscoveryGender {
    if (gender === 'male' || gender === 'female') {
        return gender;
    }
    return 'unknown';
}

function resolveLocaleCountryCode(): string {
    const locale = Intl.DateTimeFormat().resolvedOptions().locale || 'ko-KR';
    const localeSegments = locale.split(/[-_]/);
    const rawRegion = localeSegments[localeSegments.length - 1] || 'KR';
    return rawRegion.toUpperCase();
}

function resolveCountryName(countryCode: string): string {
    return COUNTRY_NAME_MAP[countryCode.toUpperCase()] ?? countryCode.toUpperCase();
}

function resolveCountryFlag(countryCode: string): string {
    const code = countryCode.toUpperCase();
    if (!/^[A-Z]{2}$/.test(code)) {
        return '🌐';
    }
    return String.fromCodePoint(...Array.from(code).map((char) => 127397 + char.charCodeAt(0)));
}

function resolveLanguageLabel(languageCode?: string | null): string {
    const normalized = String(languageCode || '').trim().toLowerCase();
    if (!normalized) {
        return '미설정';
    }
    const match = LANGS.find((item) => item.code === normalized);
    return match ? `${match.label} (${match.code.toUpperCase()})` : normalized.toUpperCase();
}

function getDefaultVoipTurnServers(): TURNServer[] {
    return [
        { urls: ['stun:stun.l.google.com:19302'] },
        { urls: ['stun:stun1.l.google.com:19302'] },
        { urls: ['stun:stun.cloudflare.com:3478'] },
    ];
}

function normalizeTurnServers(rawValue: unknown): TURNServer[] {
    if (!Array.isArray(rawValue)) {
        return getDefaultVoipTurnServers();
    }
    const normalized = rawValue
        .map((entry): TURNServer | null => {
            if (!entry || typeof entry !== 'object') {
                return null;
            }
            const candidate = entry as { urls?: unknown; username?: unknown; credential?: unknown };
            const urls = Array.isArray(candidate.urls)
                ? candidate.urls.filter((url): url is string => typeof url === 'string' && Boolean(url.trim()))
                : [];
            if (!urls.length) {
                return null;
            }
            return {
                urls,
                username: typeof candidate.username === 'string' ? candidate.username : undefined,
                credential: typeof candidate.credential === 'string' ? candidate.credential : undefined,
            };
        })
        .filter((entry): entry is TURNServer => entry !== null);

    return normalized.length ? normalized : getDefaultVoipTurnServers();
}

function parseIncomingVoipDeepLink(url: string): (CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null {
    try {
        const parsed = new URL(url);
        const scheme = parsed.protocol.replace(':', '').toLowerCase();
        if (!VOIP_INCOMING_LINK_SCHEMES.includes(scheme)) {
            return null;
        }

        const resolvedPath = `${parsed.hostname}${parsed.pathname}`.replace(/^\/+/, '').toLowerCase();
        if (resolvedPath !== VOIP_INCOMING_LINK_PATH) {
            return null;
        }

        const callId = parsed.searchParams.get('call_id') || '';
        const signalingServer = parsed.searchParams.get('signaling_server') || '';
        if (!callId || !signalingServer) {
            return null;
        }

        const explicitParticipantRole = parsed.searchParams.get('participant_role');
        let inferredParticipantRole: 'caller' | 'callee' = explicitParticipantRole === 'callee' ? 'callee' : 'caller';
        if (explicitParticipantRole !== 'callee') {
            try {
                const signalingUrl = new URL(signalingServer);
                inferredParticipantRole = signalingUrl.searchParams.get('role') === 'callee' ? 'callee' : 'caller';
            } catch {
                inferredParticipantRole = 'caller';
            }
        }

        let turnServers: unknown = getDefaultVoipTurnServers();
        const encodedTurnServers = parsed.searchParams.get('turn_servers');
        if (encodedTurnServers) {
            try {
                turnServers = JSON.parse(encodedTurnServers);
            } catch {
                turnServers = getDefaultVoipTurnServers();
            }
        }

        return {
            call_id: callId,
            signaling_server: signalingServer,
            turn_servers: normalizeTurnServers(turnServers),
            call_route: parsed.searchParams.get('call_route') || 'app_webrtc',
            user_message: parsed.searchParams.get('user_message') || undefined,
            callee_app_online: parsed.searchParams.get('callee_app_online') === 'true',
            caller_voice_id: parsed.searchParams.get('caller_voice_id') || undefined,
            callee_voice_id: parsed.searchParams.get('callee_voice_id') || undefined,
            participant_role: inferredParticipantRole,
            display_label: parsed.searchParams.get('display_label') || undefined,
            display_language: parsed.searchParams.get('display_language') || undefined,
            display_country_code: parsed.searchParams.get('display_country_code') || undefined,
            status: parsed.searchParams.get('status') || undefined,
            caller_label: parsed.searchParams.get('caller_label') || undefined,
        };
    } catch {
        return null;
    }
}

function formatAutoRelayDelayLabel(ms: number): string {
    return Number.isInteger(ms / 1000) ? `${ms / 1000}초` : `${(ms / 1000).toFixed(1)}초`;
}

function normalizeRelayText(text: string): string {
    return text
        .trim()
        .toLowerCase()
        .replace(/\s+/g, ' ');
}

function formatStatusText(template: string, values: Record<string, string>): string {
    return template.replace(/\{(\w+)\}/g, (_whole, key: string) => values[key] ?? '');
}

function formatDistance(distanceM: number): string {
    return distanceM >= 1000 ? `${(distanceM / 1000).toFixed(1)}km` : `${distanceM}m`;
}

function escapeMapLabel(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function buildNearbyMapHtml(params: {
    centerLat: number;
    centerLon: number;
    places: NearbyPlace[];
    selectedPlaceId: string;
}): string {
    const places = params.places.map((place) => ({
        id: place.id,
        name: escapeMapLabel(place.name),
        address: escapeMapLabel(place.address),
        categoryLabel: escapeMapLabel(place.category_label),
        distanceLabel: formatDistance(place.distance_m),
        lat: place.latitude,
        lon: place.longitude,
        googleMapsUrl: place.google_maps_url,
        bookingSupported: place.booking_supported,
        reservable: place.booking_supported && (place.category === 'hotel' || place.category === 'airport'),
    }));

    return `<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        html, body, #map { height: 100%; margin: 0; padding: 0; background: #08111b; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .leaflet-container { background: linear-gradient(180deg, #0b1622 0%, #071018 100%); }
        .leaflet-popup-content-wrapper, .leaflet-popup-tip { background: #0f1b2a; color: #e6edf3; }
        .leaflet-popup-content { margin: 10px 12px; line-height: 1.4; }
        .map-popup-title { font-weight: 700; font-size: 13px; }
        .map-popup-meta { font-size: 11px; color: #8fd3ff; margin-top: 4px; }
        .map-popup-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .map-popup-btn {
            border: 0;
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 11px;
            font-weight: 700;
            color: #e6edf3;
            background: #1d4ed8;
        }
        .map-popup-btn.secondary { background: #0d2a4a; color: #79c0ff; border: 1px solid #35506c; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const postToApp = (payload) => {
            if (window.ReactNativeWebView && typeof window.ReactNativeWebView.postMessage === 'function') {
                window.ReactNativeWebView.postMessage(JSON.stringify(payload));
            }
        };
        const center = [${JSON.stringify(params.centerLat)}, ${JSON.stringify(params.centerLon)}];
        const places = ${JSON.stringify(places)};
        const selectedPlaceId = ${JSON.stringify(params.selectedPlaceId)};
        const map = L.map('map', {
            zoomControl: false,
            attributionControl: true,
        }).setView(center, places.length ? 12 : 11);
        // ODbL/OSM 타일 정책상 출처표기 필수. Leaflet 프리픽스는 숨기고 OSM 크레딧만 노출.
        map.attributionControl.setPrefix('');

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors (ODbL)',
        }).addTo(map);

        const bounds = [];
        const selectedMarkerStyle = { radius: 10, color: '#ffd166', weight: 3, fillColor: '#ff7b00', fillOpacity: 0.95 };
        const defaultMarkerStyle = { radius: 8, color: '#7dd3fc', weight: 2, fillColor: '#1d4ed8', fillOpacity: 0.92 };

        const userMarker = L.circleMarker(center, {
            radius: 9,
            color: '#9be8b3',
            weight: 3,
            fillColor: '#22c55e',
            fillOpacity: 0.9,
        }).addTo(map).bindPopup('<div class="map-popup-title">현재 위치</div>');
        bounds.push(center);

        document.addEventListener('click', (event) => {
            const target = event.target;
            if (!(target instanceof HTMLElement)) {
                return;
            }
            const button = target.closest('.map-popup-btn');
            if (!button) {
                return;
            }
            const action = button.getAttribute('data-action');
            const placeId = button.getAttribute('data-place-id');
            const googleMapsUrl = button.getAttribute('data-google-maps-url');
            if (!action || !placeId) {
                return;
            }
            postToApp({
                type: 'nearby-map-action',
                action,
                placeId,
                googleMapsUrl,
            });
        });

        let selectedMarker = null;
        places.forEach((place) => {
            const point = [place.lat, place.lon];
                                accessibilityRole="button"
                                accessibilityLabel={buildSectionRailSelector(item.key)}
                                testID={buildSectionRailSelector(item.key)}
            bounds.push(point);
            const popupHtml = '<div class="map-popup-title">' + place.name + '</div>'
                + '<div class="map-popup-meta">' + place.categoryLabel + ' · ' + place.distanceLabel + '<br/>' + place.address + '</div>'
                + '<div class="map-popup-actions">'
                + '<button type="button" class="map-popup-btn secondary" data-action="focus" data-place-id="' + place.id + '">선택</button>'
                + '<button type="button" class="map-popup-btn" data-action="route" data-place-id="' + place.id + '" data-google-maps-url="' + place.googleMapsUrl + '">길찾기</button>'
                + (place.reservable
                    ? '<button type="button" class="map-popup-btn secondary" data-action="book" data-place-id="' + place.id + '">예약 선택</button>'
                    : '')
                + '</div>';
            const marker = L.circleMarker(point, place.id === selectedPlaceId ? selectedMarkerStyle : defaultMarkerStyle)
                .addTo(map)
                .bindPopup(popupHtml);
            marker.on('click', () => {
                postToApp({ type: 'nearby-map-action', action: 'focus', placeId: place.id, googleMapsUrl: place.googleMapsUrl });
            });
            if (place.id === selectedPlaceId) {
                selectedMarker = marker;
            }
        });

        if (bounds.length > 1) {
            map.fitBounds(bounds, { padding: [26, 26] });
        }

        if (selectedMarker) {
            selectedMarker.openPopup();
        } else {
            userMarker.openPopup();
        }
    </script>
</body>
</html>`;
}

function todayPlus(days: number): string {
    const now = new Date();
    now.setDate(now.getDate() + days);
    return now.toISOString().slice(0, 10);
}

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

function extractApiErrorMessage(detail: unknown, fallback: string): string {
    if (typeof detail === 'string' && detail.trim()) {
        return detail.trim();
    }
    if (Array.isArray(detail)) {
        const messages = detail
            .map((item) => {
                if (typeof item === 'string') {
                    return item.trim();
                }
                if (item && typeof item === 'object') {
                    const { msg } = item as { msg?: unknown };
                    if (typeof msg === 'string' && msg.trim()) {
                        return msg.trim();
                    }
                }
                return '';
            })
            .filter(Boolean);
        if (messages.length > 0) {
            return messages.join(', ');
        }
    }
    if (detail && typeof detail === 'object') {
        const candidate =
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).detail ??
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).message ??
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).error ??
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).msg;
        if (typeof candidate === 'string' && candidate.trim()) {
            return candidate.trim();
        }
    }
    return fallback;
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

type SignupRequestCodeResponse = {
    signupSessionToken: string;
    verificationChannel: string;
    maskedTarget: string;
    expiresAt: string;
    devOtpHint?: string;
};

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

function summarizeAuthToken(token: string): string {
    const normalized = token.trim();
    if (!normalized) {
        return 'empty';
    }

    if (normalized.length <= 12) {
        return `len:${normalized.length}:${normalized}`;
    }

    return `len:${normalized.length}:${normalized.slice(0, 6)}...${normalized.slice(-6)}`;
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
        limit: '8',
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
const LANGS = [
    { label: '한국어', code: 'ko', tts: 'ko-KR' },
    { label: 'English', code: 'en', tts: 'en-US' },
    { label: '中文(简体)', code: 'zh', tts: 'zh-CN' },
    { label: '繁體中文', code: 'zh-tw', tts: 'zh-TW' },
    { label: '日本語', code: 'ja', tts: 'ja-JP' },
    { label: 'Español', code: 'es', tts: 'es-ES' },
    { label: 'Français', code: 'fr', tts: 'fr-FR' },
    { label: 'Deutsch', code: 'de', tts: 'de-DE' },
    { label: 'Português', code: 'pt', tts: 'pt-BR' },
    { label: 'Русский', code: 'ru', tts: 'ru-RU' },
    { label: 'العربية', code: 'ar', tts: 'ar-SA' },
    { label: 'हिन्दी', code: 'hi', tts: 'hi-IN' },
    { label: 'Italiano', code: 'it', tts: 'it-IT' },
    { label: 'Türkçe', code: 'tr', tts: 'tr-TR' },
    { label: 'Tiếng Việt', code: 'vi', tts: 'vi-VN' },
    { label: 'ภาษาไทย', code: 'th', tts: 'th-TH' },
    { label: 'Bahasa Indonesia', code: 'id', tts: 'id-ID' },
    { label: 'Bahasa Melayu', code: 'ms', tts: 'ms-MY' },
    { label: 'Nederlands', code: 'nl', tts: 'nl-NL' },
    { label: 'Polski', code: 'pl', tts: 'pl-PL' },
    { label: 'Українська', code: 'uk', tts: 'uk-UA' },
    { label: 'Svenska', code: 'sv', tts: 'sv-SE' },
    { label: 'Norsk', code: 'no', tts: 'nb-NO' },
    { label: 'Dansk', code: 'da', tts: 'da-DK' },
    { label: 'Suomi', code: 'fi', tts: 'fi-FI' },
    { label: 'Čeština', code: 'cs', tts: 'cs-CZ' },
    { label: 'Română', code: 'ro', tts: 'ro-RO' },
    { label: 'Magyar', code: 'hu', tts: 'hu-HU' },
    { label: 'Ελληνικά', code: 'el', tts: 'el-GR' },
    { label: 'עברית', code: 'he', tts: 'he-IL' },
    { label: 'Български', code: 'bg', tts: 'bg-BG' },
    { label: 'Hrvatski', code: 'hr', tts: 'hr-HR' },
    { label: 'Srpski', code: 'sr', tts: 'sr-RS' },
    { label: 'Slovenčina', code: 'sk', tts: 'sk-SK' },
    { label: 'Slovenščina', code: 'sl', tts: 'sl-SI' },
    { label: 'Lietuvių', code: 'lt', tts: 'lt-LT' },
    { label: 'Latviešu', code: 'lv', tts: 'lv-LV' },
    { label: 'Eesti', code: 'et', tts: 'et-EE' },
    { label: 'فارسی', code: 'fa', tts: 'fa-IR' },
    { label: 'اردو', code: 'ur', tts: 'ur-PK' },
    { label: 'বাংলা', code: 'bn', tts: 'bn-BD' },
    { label: 'தமிழ்', code: 'ta', tts: 'ta-IN' },
    { label: 'తెలుగు', code: 'te', tts: 'te-IN' },
    { label: 'മലയാളം', code: 'ml', tts: 'ml-IN' },
    { label: 'ગુજરાતી', code: 'gu', tts: 'gu-IN' },
    { label: 'मराठी', code: 'mr', tts: 'mr-IN' },
    { label: 'Filipino', code: 'fil', tts: 'fil-PH' },
    { label: 'Kiswahili', code: 'sw', tts: 'sw-KE' },
    { label: 'Català', code: 'ca', tts: 'ca-ES' },
    { label: 'አማርኛ', code: 'am', tts: 'am-ET' },
] as const;

type LangCode = (typeof LANGS)[number]['code'];
const SUPPORTED_LANGUAGE_COUNT = LANGS.length;
const SIGNUP_COUNTRY_OPTIONS = [
    { code: 'KR', label: '대한민국' },
    { code: 'US', label: '미국' },
    { code: 'JP', label: '일본' },
    { code: 'CN', label: '중국' },
    { code: 'TW', label: '대만' },
    { code: 'HK', label: '홍콩' },
    { code: 'VN', label: '베트남' },
    { code: 'TH', label: '태국' },
    { code: 'PH', label: '필리핀' },
    { code: 'ID', label: '인도네시아' },
    { code: 'MY', label: '말레이시아' },
    { code: 'SG', label: '싱가포르' },
    { code: 'FR', label: '프랑스' },
    { code: 'DE', label: '독일' },
    { code: 'GB', label: '영국' },
    { code: 'CA', label: '캐나다' },
    { code: 'AU', label: '호주' },
    { code: 'NZ', label: '뉴질랜드' },
    { code: 'IE', label: '아일랜드' },
    { code: 'IT', label: '이탈리아' },
    { code: 'ES', label: '스페인' },
    { code: 'MX', label: '멕시코' },
    { code: 'AR', label: '아르헨티나' },
    { code: 'CL', label: '칠레' },
    { code: 'CO', label: '콜롬비아' },
    { code: 'PE', label: '페루' },
    { code: 'PT', label: '포르투갈' },
    { code: 'BR', label: '브라질' },
    { code: 'RU', label: '러시아' },
    { code: 'SA', label: '사우디아라비아' },
    { code: 'AE', label: '아랍에미리트' },
    { code: 'EG', label: '이집트' },
    { code: 'QA', label: '카타르' },
    { code: 'KW', label: '쿠웨이트' },
    { code: 'IN', label: '인도' },
    { code: 'PK', label: '파키스탄' },
    { code: 'BD', label: '방글라데시' },
    { code: 'TR', label: '튀르키예' },
    { code: 'NL', label: '네덜란드' },
    { code: 'PL', label: '폴란드' },
    { code: 'UA', label: '우크라이나' },
    { code: 'SE', label: '스웨덴' },
    { code: 'NO', label: '노르웨이' },
    { code: 'DK', label: '덴마크' },
    { code: 'FI', label: '핀란드' },
    { code: 'CZ', label: '체코' },
    { code: 'RO', label: '루마니아' },
    { code: 'HU', label: '헝가리' },
    { code: 'GR', label: '그리스' },
    { code: 'IL', label: '이스라엘' },
] as const;
type SignupCountryCode = (typeof SIGNUP_COUNTRY_OPTIONS)[number]['code'];
type SignupSelectionModal = 'language' | 'country' | null;
const SIGNUP_COUNTRY_OPTION_CODES: SignupCountryCode[] = SIGNUP_COUNTRY_OPTIONS.map((item) => item.code);
const COUNTRY_NAME_MAP: Record<string, string> = {
    ...(Object.fromEntries(SIGNUP_COUNTRY_OPTIONS.map((item) => [item.code, item.label])) as Record<string, string>),
    BE: '벨기에',
    CH: '스위스',
    AT: '오스트리아',
    MO: '마카오',
    CY: '키프로스',
    BA: '보스니아 헤르체고비나',
    ME: '몬테네그로',
    SK: '슬로바키아',
    SI: '슬로베니아',
    LT: '리투아니아',
    LV: '라트비아',
    EE: '에스토니아',
    IR: '이란',
    AF: '아프가니스탄',
    LK: '스리랑카',
    ET: '에티오피아',
    KE: '케냐',
    TZ: '탄자니아',
    UG: '우간다',
    MD: '몰도바',
    RS: '세르비아',
};

function isSupportedSignupCountryCode(value: string): value is SignupCountryCode {
    return SIGNUP_COUNTRY_OPTIONS.some((item) => item.code === value);
}

function normalizeSignupCountryCode(value: string | null | undefined): SignupCountryCode {
    const normalized = String(value || '').trim().toUpperCase();
    return isSupportedSignupCountryCode(normalized) ? normalized : 'KR';
}

function resolveSignupCountryFromLang(languageCode: LangCode): SignupCountryCode {
    const matchedCountry = SIGNUP_COUNTRY_OPTIONS.find((item) => resolveLangFromCountry(item.code) === languageCode);
    return matchedCountry?.code ?? 'KR';
}

function getLangLabelText(code: LangCode): string {
    return LANGS.find((item) => item.code === code)?.label ?? code;
}

function isSupportedLangCode(value: string): value is LangCode {
    return LANGS.some((item) => item.code === value);
}

type HybridGpsResult = {
    latitude: number;
    longitude: number;
    accuracy: number | null;
    mode: HybridGpsMode;
    qualityScore: number;
    source: 'gps_high' | 'gps_balanced' | 'gps_low' | 'last_known' | 'adb_override' | 'persisted_last_success';
    servicesEnabled: boolean;
    overrideCountryCode?: string;
    overrideRegionHint?: string;
};

const ADB_GPS_OVERRIDE_PATH = 'file:///storage/emulated/0/Android/media/com.parkcheolhong.worldlinco/worldlingo_mock_location.json';
const GPS_DEBUG_TRACE_FILE_PATH = `${FileSystem.documentDirectory ?? FileSystem.cacheDirectory ?? 'file:///data/user/0/com.parkcheolhong.worldlinco/files/'}gps-fallback-debug.log`;
const GPS_PERSISTED_FALLBACK_KEY = 'gps_fallback_last_success_v1';

const GPS_REGION_COORDINATE_FALLBACKS = [
    { countryCode: 'KR', regionHint: 'jeju', latitude: 33.4996, longitude: 126.5312 },
    { countryCode: 'CN', regionHint: 'guangdong', latitude: 23.1291, longitude: 113.2644 },
    { countryCode: 'JP', regionHint: 'kansai', latitude: 34.6937, longitude: 135.5023 },
    { countryCode: 'IN', regionHint: 'bihar', latitude: 25.5941, longitude: 85.1376 },
    { countryCode: 'IT', regionHint: 'naples', latitude: 40.8518, longitude: 14.2681 },
] as const;

const COUNTRY_LANG_MAP: Partial<Record<string, LangCode>> = {
    KR: 'ko',
    US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', SG: 'en', PH: 'en',
    CN: 'zh',
    TW: 'zh-tw', HK: 'zh-tw', MO: 'zh-tw',
    JP: 'ja',
    ES: 'es', MX: 'es', AR: 'es', CL: 'es', CO: 'es', PE: 'es',
    FR: 'fr', BE: 'fr', CH: 'fr',
    DE: 'de', AT: 'de',
    PT: 'pt', BR: 'pt',
    RU: 'ru',
    SA: 'ar', AE: 'ar', EG: 'ar', QA: 'ar', KW: 'ar',
    IN: 'hi',
    IT: 'it',
    TR: 'tr',
    VN: 'vi',
    TH: 'th',
    ID: 'id',
    MY: 'ms',
    NL: 'nl',
    PL: 'pl',
    UA: 'uk',
    SE: 'sv',
    NO: 'no',
    DK: 'da',
    FI: 'fi',
    CZ: 'cs',
    RO: 'ro', MD: 'ro',
    HU: 'hu',
    GR: 'el', CY: 'el',
    IL: 'he',
    BG: 'bg',
    HR: 'hr',
    RS: 'sr', BA: 'sr', ME: 'sr',
    SK: 'sk',
    SI: 'sl',
    LT: 'lt',
    LV: 'lv',
    EE: 'et',
    IR: 'fa', AF: 'fa',
    PK: 'ur',
    BD: 'bn',
    LK: 'ta',
    ET: 'am',
    KE: 'sw', TZ: 'sw', UG: 'sw',
};

function resolveLangFromCountry(countryCode: string): LangCode | null {
    return COUNTRY_LANG_MAP[countryCode.toUpperCase()] ?? null;
}

const DIALECT_REGION_HINT_KEYWORDS: Record<string, Array<{ hint: string; keywords: string[] }>> = {
    KR: [
        { hint: 'jeju', keywords: ['jeju', '제주'] },
        { hint: 'busan', keywords: ['busan', '부산'] },
        { hint: 'gyeongsang', keywords: ['daegu', '울산', 'gyeongsang', '경상', '포항', '창원'] },
        { hint: 'jeolla', keywords: ['gwangju', '전주', 'jeolla', '전라', '목포', '순천'] },
        { hint: 'seoul', keywords: ['seoul', '서울', 'incheon', '인천', 'gyeonggi', '경기', 'suwon', '수원'] },
    ],
    CN: [
        { hint: 'guangdong', keywords: ['guangzhou', 'shenzhen', 'dongguan', 'foshan', 'guangdong', '광동', '广东', '廣東'] },
        { hint: 'sichuan', keywords: ['chengdu', 'mianyang', 'sichuan', '사천', '四川'] },
        { hint: 'dongbei', keywords: ['liaoning', 'jilin', 'heilongjiang', 'dongbei', '东北', '瀋陽', 'shenyang', 'harbin'] },
        { hint: 'shanghai', keywords: ['shanghai', '상하이', '上海'] },
        { hint: 'beijing', keywords: ['beijing', '베이징', '北京', 'tianjin', '天津'] },
    ],
    JP: [
        { hint: 'kansai', keywords: ['osaka', 'kyoto', 'nara', 'kobe', 'wakayama', 'kansai', '간사이', '関西', '大阪', '京都'] },
        { hint: 'hakata', keywords: ['fukuoka', 'hakata', '후쿠오카', '博多', '福岡'] },
        { hint: 'tohoku', keywords: ['sendai', 'aomori', 'akita', 'iwate', 'yamagata', 'tohoku', '도호쿠', '東北', '仙台'] },
        { hint: 'okinawa', keywords: ['okinawa', '오키나와', '沖縄', 'naha', '나하'] },
        { hint: 'tokyo', keywords: ['tokyo', '도쿄', '東京', 'yokohama', '요코하마', 'kanagawa', '가나가와'] },
    ],
    IN: [
        { hint: 'delhi', keywords: ['delhi', 'new delhi', 'ncr', 'दिल्ली'] },
        { hint: 'mumbai', keywords: ['mumbai', 'bombay', 'maharashtra', 'मुंबई', 'pune', 'पुणे'] },
        { hint: 'bihar', keywords: ['bihar', 'patna', 'पटना', 'बिहार'] },
        { hint: 'punjab', keywords: ['punjab', 'amritsar', 'ludhiana', 'पंजाब'] },
        { hint: 'uttar-pradesh', keywords: ['uttar pradesh', 'uttar-pradesh', 'lucknow', 'kanpur', 'वाराणसी', 'varanasi'] },
    ],
    IT: [
        { hint: 'rome', keywords: ['rome', 'roma', 'lazio'] },
        { hint: 'milan', keywords: ['milan', 'milano', 'lombardy', 'lombardia'] },
        { hint: 'naples', keywords: ['naples', 'napoli', 'campania'] },
        { hint: 'sicily', keywords: ['sicily', 'sicilia', 'palermo', 'catania'] },
        { hint: 'venice', keywords: ['venice', 'venezia', 'veneto', 'padova'] },
    ],
};

function resolveGpsDialectRegionHint(
    countryCode: string,
    geocoded: Partial<Location.LocationGeocodedAddress> | null,
): string | null {
    const regionProfiles = DIALECT_REGION_HINT_KEYWORDS[countryCode.toUpperCase()];
    if (!regionProfiles?.length || !geocoded) {
        return null;
    }

    const haystack = [
        geocoded.region,
        geocoded.city,
        geocoded.district,
        geocoded.subregion,
        geocoded.street,
        geocoded.name,
    ]
        .map((value) => String(value || '').trim().toLowerCase())
        .filter(Boolean)
        .join(' | ');

    if (!haystack) {
        return null;
    }

    const matchedRegion = regionProfiles.find(({ keywords }) => keywords.some((keyword) => haystack.includes(keyword.toLowerCase())));
    return matchedRegion?.hint ?? null;
}

function resolveGpsCoordinateFallback(latitude: number, longitude: number): { countryCode: string; regionHint: string } | null {
    const matched = GPS_REGION_COORDINATE_FALLBACKS.find((candidate) => {
        const latitudeDelta = Math.abs(candidate.latitude - latitude);
        const longitudeDelta = Math.abs(candidate.longitude - longitude);
        return latitudeDelta <= 0.35 && longitudeDelta <= 0.35;
    });

    return matched
        ? {
            countryCode: matched.countryCode,
            regionHint: matched.regionHint,
        }
        : null;
}

function resolveRegionHintForSourceLanguage(
    sourceLang: LangCode,
    countryCode: string,
    regionHint: string,
): string | undefined {
    if (!countryCode || !regionHint) {
        return undefined;
    }
    return resolveLangFromCountry(countryCode) === sourceLang ? regionHint : undefined;
}

type SongSubtitleEntry = {
    id: string;
    original: string;
    translated: string;
    source: LangCode;
    target: LangCode;
    repeatCount: number;
    detectedBy: 'voice' | 'script' | 'manual' | 'seed';
};

type SongFileJobStatus = {
    job_id: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    stage: string;
    progress: number;
    message: string;
    source_language: string;
    target_language: string;
    segment_count: number;
    quality_score: number;
    error_message?: string | null;
};

type SongFileTimelineSegment = {
    id: string;
    index: number;
    start_ms: number;
    end_ms: number;
    original: string;
    translated: string;
    source_language: string;
    target_language: string;
    confidence: number;
    detected_by: 'voice' | 'script' | 'manual' | 'seed';
    edited_by_user?: boolean;
    quality_flags?: string[];
};

type SongFileTimeline = {
    job_id: string;
    source_language: string;
    target_language: string;
    duration_ms: number;
    segment_count: number;
    quality_score: number;
    segments: SongFileTimelineSegment[];
};

type VoiceLicenseMode = 'self_created' | 'licensed' | 'public_domain' | 'private_preview_unverified' | 'policy_approved_distribution';
type VoiceOutputScope = 'private_preview' | 'user_saved_preview' | 'policy_review_export' | 'policy_approved_export';

type VoiceConsentResponse = {
    consent_id: string;
    user_id: string;
    consent_version: string;
    allow_private_preview: boolean;
    allow_export_for_licensed_audio: boolean;
    status: 'active' | 'revoked';
    created_at: string;
};

type VoiceProfileResponse = {
    voice_profile_id: string;
    profile_label: string;
    sample_duration_ms: number;
    sample_quality_score: number;
    encrypted: boolean;
    status: 'active' | 'revoked' | 'deleted';
};

type VoicePreviewResponse = {
    preview_id: string;
    gate_status: 'allowed' | 'review_required' | 'blocked';
    policy_allowed: boolean;
    effective_output_scope: VoiceOutputScope;
    message: string;
    segment_count: number;
    duration_ms: number;
    preview_text: string;
    preview_audio_base64?: string | null;
    preview_audio_format?: string | null;
    preview_audio_available?: boolean;
};

const WHISPER_LANG_MAP: Record<string, LangCode> = {
    chinese: 'zh', mandarin: 'zh', china: 'zh', chinese_language: 'zh', 중국: 'zh', 중국어: 'zh', 중문: 'zh', zh: 'zh',
    japanese: 'ja', japan: 'ja', 일본: 'ja', 일본어: 'ja', 일어: 'ja', ja: 'ja',
    korean: 'ko', korea: 'ko', southkorea: 'ko', 한국: 'ko', 한국어: 'ko', 한글: 'ko', ko: 'ko',
    english: 'en', american: 'en', america: 'en', usa: 'en', us: 'en', england: 'en', britain: 'en', 미국: 'en', 영국: 'en', 영어: 'en', 영문: 'en', en: 'en',
    spanish: 'es', spain: 'es', 스페인: 'es', 스페인어: 'es', es: 'es',
    french: 'fr', france: 'fr', 프랑스: 'fr', 프랑스어: 'fr', fr: 'fr',
    german: 'de', germany: 'de', 독일: 'de', 독일어: 'de', de: 'de',
    portuguese: 'pt', portugal: 'pt', brazil: 'pt', 포르투갈: 'pt', 브라질: 'pt', 포르투갈어: 'pt', pt: 'pt',
    russian: 'ru', russia: 'ru', 러시아: 'ru', 러시아어: 'ru', ru: 'ru',
    arabic: 'ar', saudi: 'ar', 사우디: 'ar', 아랍: 'ar', 아랍어: 'ar', ar: 'ar',
    hindi: 'hi', india: 'hi', 인도: 'hi', 힌디어: 'hi', hi: 'hi',
    italian: 'it', italy: 'it', 이탈리아: 'it', 이탈리아어: 'it', it: 'it',
    turkish: 'tr', turkey: 'tr', 터키: 'tr', 터키어: 'tr', tr: 'tr',
    thai: 'th', thailand: 'th', 태국: 'th', 태국어: 'th', th: 'th',
    vietnamese: 'vi', vietnam: 'vi', 베트남: 'vi', 베트남어: 'vi', vi: 'vi',
    indonesian: 'id', indonesia: 'id', 인도네시아: 'id', 인도네시아어: 'id', id: 'id',
    malay: 'ms', malaysia: 'ms', 말레이시아: 'ms', 말레이어: 'ms', ms: 'ms',
    dutch: 'nl', netherlands: 'nl', 네덜란드: 'nl', 네덜란드어: 'nl', nl: 'nl',
    polish: 'pl', poland: 'pl', 폴란드: 'pl', 폴란드어: 'pl', pl: 'pl',
    ukrainian: 'uk', ukraine: 'uk', 우크라이나: 'uk', 우크라이나어: 'uk', uk: 'uk',
    swedish: 'sv', sweden: 'sv', 스웨덴: 'sv', 스웨덴어: 'sv', sv: 'sv',
    norwegian: 'no', norway: 'no', 노르웨이: 'no', 노르웨이어: 'no', no: 'no',
    danish: 'da', denmark: 'da', 덴마크: 'da', 덴마크어: 'da', da: 'da',
    finnish: 'fi', finland: 'fi', 핀란드: 'fi', 핀란드어: 'fi', fi: 'fi',
    czech: 'cs', czechia: 'cs', cesky: 'cs', 체코: 'cs', 체코어: 'cs', cs: 'cs',
    romanian: 'ro', romania: 'ro', 루마니아: 'ro', 루마니아어: 'ro', ro: 'ro',
    hungarian: 'hu', hungary: 'hu', 헝가리: 'hu', 헝가리어: 'hu', hu: 'hu',
    greek: 'el', greece: 'el', 그리스: 'el', 그리스어: 'el', el: 'el',
    hebrew: 'he', israel: 'he', 이스라엘: 'he', 히브리어: 'he', he: 'he',
    bulgarian: 'bg', bulgaria: 'bg', 불가리아: 'bg', 불가리아어: 'bg', bg: 'bg',
    croatian: 'hr', croatia: 'hr', 크로아티아: 'hr', 크로아티아어: 'hr', hr: 'hr',
    serbian: 'sr', serbia: 'sr', 세르비아: 'sr', 세르비아어: 'sr', sr: 'sr',
    slovak: 'sk', slovakia: 'sk', 슬로바키아: 'sk', 슬로바키아어: 'sk', sk: 'sk',
    slovenian: 'sl', slovenia: 'sl', 슬로베니아: 'sl', 슬로베니아어: 'sl', sl: 'sl',
    lithuanian: 'lt', lithuania: 'lt', 리투아니아: 'lt', 리투아니아어: 'lt', lt: 'lt',
    latvian: 'lv', latvia: 'lv', 라트비아: 'lv', 라트비아어: 'lv', lv: 'lv',
    estonian: 'et', estonia: 'et', 에스토니아: 'et', 에스토니아어: 'et', et: 'et',
    persian: 'fa', farsi: 'fa', iran: 'fa', 페르시아어: 'fa', 이란: 'fa', fa: 'fa',
    urdu: 'ur', pakistan: 'ur', 파키스탄: 'ur', 우르두어: 'ur', ur: 'ur',
    bengali: 'bn', bangla: 'bn', bangladesh: 'bn', 벵골어: 'bn', 방글라데시: 'bn', bn: 'bn',
    tamil: 'ta', tamilnadu: 'ta', 타밀어: 'ta', ta: 'ta',
    telugu: 'te', 텔루구어: 'te', te: 'te',
    malayalam: 'ml', 말라얄람어: 'ml', ml: 'ml',
    gujarati: 'gu', 구자라트어: 'gu', gu: 'gu',
    marathi: 'mr', 마라티어: 'mr', mr: 'mr',
    filipino: 'fil', tagalog: 'fil', 필리핀어: 'fil', 타갈로그어: 'fil', fil: 'fil',
    swahili: 'sw', kiswahili: 'sw', 케냐: 'sw', 스와힐리어: 'sw', sw: 'sw',
    catalan: 'ca', catalonia: 'ca', 카탈루냐어: 'ca', ca: 'ca',
    amharic: 'am', ethiopia: 'am', 에티오피아: 'am', 암하라어: 'am', am: 'am',
};

const SONG_FILE_JOB_POLL_INTERVAL_MS = 1500;
const SONG_FILE_JOB_MAX_WAIT_MS = 6 * 60 * 1000;
const VOICE_LICENSE_OPTIONS: Array<{ value: VoiceLicenseMode; label: string }> = [
    { value: 'private_preview_unverified', label: '권리 확인 전' },
    { value: 'self_created', label: '직접 만든 곡' },
    { value: 'licensed', label: '라이선스 보유' },
    { value: 'public_domain', label: '공개 허용' },
    { value: 'policy_approved_distribution', label: '운영 승인' },
];
const VOICE_OUTPUT_SCOPE_OPTIONS: Array<{ value: VoiceOutputScope; label: string }> = [
    { value: 'private_preview', label: '개인 preview' },
    { value: 'user_saved_preview', label: '내 보관함' },
    { value: 'policy_review_export', label: 'export 심사' },
    { value: 'policy_approved_export', label: '승인 export' },
];

function normalizeDetectedLangCode(value: unknown): LangCode | null {
    const raw = String(value ?? '').trim().toLowerCase().replace('_', '-');
    if (!raw) return null;
    const compact = raw.split(/[\s,;/]+/)[0];
    const base = compact.split('-')[0];
    const normalizedCompact = compact.replace(/[^\p{L}-]/gu, '');
    const strippedCompact = normalizedCompact.replace(/(language|lang|나라|국가|언어|국어|말|어|으로|로)$/u, '');
    const strippedBase = base.replace(/(language|lang|나라|국가|언어|국어|말|어|으로|로)$/u, '');
    return WHISPER_LANG_MAP[compact]
        ?? WHISPER_LANG_MAP[base]
        ?? WHISPER_LANG_MAP[normalizedCompact]
        ?? WHISPER_LANG_MAP[strippedCompact]
        ?? WHISPER_LANG_MAP[strippedBase]
        ?? null;
}

function normalizeLyricLine(text: string): string {
    return text
        .replace(/\[[^\]]*\]/g, ' ')
        .replace(/\([^\)]*\)/g, ' ')
        .replace(/[♪♫♬]/g, ' ')
        .replace(/\s*\/\s*/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function isLikelyLyricLine(text: string): boolean {
    const value = normalizeLyricLine(text);
    if (value.length < 2) return false;
    if (/^\d+$/.test(value)) return false;
    return /[A-Za-z\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff\u0600-\u06ff\u0900-\u097f\u0400-\u04ff\u0e00-\u0e7f]/.test(value);
}

function isRepeatedLyricSegment(current: string, previous: string): boolean {
    const a = normalizeLyricLine(current).toLowerCase();
    const b = normalizeLyricLine(previous).toLowerCase();
    if (!a || !b) return false;
    return a === b || a.includes(b) || b.includes(a);
}

function normalizeSongFileLang(value: string, fallback: LangCode): LangCode {
    return normalizeDetectedLangCode(value) ?? fallback;
}

function formatSongFileTime(ms: number): string {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

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

function normalizeSpeakText(text: string): string {
    return text
        .replace(/\(offline\)/gi, '')
        .replace(/\[offline\]/gi, '')
        .trim();
}

// 발화 로케일 SSOT(50개국 정확 발화의 핵심).
// 라틴·키릴·아랍·데바나가리·한자처럼 여러 언어가 공유하는 스크립트를 '스크립트만'으로
// 추정하면 스페인어/베트남어=영어, 우크라이나어=러시아어, 일본어(한자)=중국어처럼
// 50개국 언어가 엉뚱한 음성으로 뭉개진다. 따라서 지정 타깃 언어 로케일(fallback)을 신뢰하고,
// 번역문이 '단일 언어 전용' 스크립트(한글/가나/타이/히브리/그리스)로 샌 경우에만 그 언어로 교정한다.
function inferTtsLanguage(text: string, fallback: string): string {
    const target = fallback && fallback.includes('-') ? fallback : 'en-US';
    // (G5) 스크립트 누수 교정 단일 SSOT 위임 — 백엔드 9-스크립트 로직과 동일하며,
    // 기존 5종(ko/ja/th/he/el)은 동일 로케일을 유지하고 zh/ru/ar/hi 4종을 추가 커버한다.
    return correctTtsLocaleForScriptLeak(text, target, (lang) => resolveVoipTtsLocale(lang));
}

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

function inferSpeechLangCode(text: string, fallback: LangCode = 'en'): LangCode {
    const value = text.trim();
    if (!value) return fallback;

    if (/[\uac00-\ud7a3]/.test(value)) return 'ko';
    if (/[\u3040-\u30ff]/.test(value)) return 'ja';
    if (/[\u4e00-\u9fff]/.test(value)) return 'zh';
    if (/[\u0600-\u06ff]/.test(value)) return 'ar';
    if (/[\u0900-\u097f]/.test(value)) return 'hi';
    if (/[\u0400-\u04ff]/.test(value)) return 'ru';
    if (/[\u0e00-\u0e7f]/.test(value)) return 'th';

    const lower = value.toLowerCase();
    if (/[¿¡ñ]/.test(lower)) return 'es';
    if (/[äöüß]/.test(lower)) return 'de';
    if (/[ğşıİıç]/.test(value)) return 'tr';
    if (/[àâçéèêëîïôûùüÿœæ]/.test(lower)) return 'fr';
    if (/[ãõ]/.test(lower)) return 'pt';
    if (/[a-z]/.test(lower)) return 'en';

    return fallback;
}

function resolveAutoTargetLang(source: LangCode, currentTarget: LangCode): LangCode {
    if (currentTarget !== source) return currentTarget;
    if (source === 'ko') return 'en';
    if (source === 'en') return 'ko';
    return 'ko';
}

function resolveVoipRemoteLanguageHint(...values: Array<string | null | undefined>): LangCode | null {
    for (const value of values) {
        const normalized = String(value || '').trim().toLowerCase();
        if (isSupportedLangCode(normalized)) {
            return normalized;
        }
    }
    return null;
}

function resolveSongFileTargetLang(currentSource: LangCode, currentTarget: LangCode): LangCode {
    if (currentSource === 'ko') return 'ko';
    if (currentTarget !== currentSource) return currentTarget;
    return resolveAutoTargetLang(currentSource, currentTarget);
}

// ─────────────────────────────────────────────
// UI 텍스트 다국어 사전 (기본 번역 UI 사전 + 나머지 언어는 영어 fallback)
// ─────────────────────────────────────────────
const UI_TEXT: Record<string, {
    sourceLang: string; targetLang: string; inputPlaceholder: string;
    swap: string; translate: string; resultPlaceholder: string;
    inputRequired: string; inputRequiredMsg: string; errorMsg: string;
    offlineMsg: string; subtitle: string; footer: string; offlineBadge: string;
    ocrTitle?: string;
    ocrSubtitle?: string;
    ocrPickImage?: string;
    ocrLoading?: string;
    ocrExtractedTitle?: string;
    ocrTranslatedTitle?: string;
    ocrSelectedFile?: string;
    ocrErrorMsg?: string;
    autoVoiceSegmentStatus?: string;
    autoVoiceDuplicateSkipped?: string;
    autoVoiceDetected?: string;
    autoVoiceModeStopped?: string;
    autoVoiceModeStarted?: string;
    manualVoiceOnlyNotice?: string;
    manualLanguageHint?: string;
    profileLanguageLabel?: string;
    profileLanguageHint?: string;
    peerLanguageLabel?: string;
    peerLanguageHint?: string;
    faceConversationOn?: string;
    faceConversationOff?: string;
    faceConversationPeerRequired?: string;
    faceListenProcessing?: string;
    faceSpeakingStatus?: string;
    faceVadHint?: string;
    interAutoRelayDuplicateSkipped?: string;
    interAutoRelayPending?: string;
}> = {
    ko: { sourceLang: '원본 언어', targetLang: '번역 언어', inputPlaceholder: '번역할 텍스트를 입력하세요', swap: '⇄ 언어 스왑', translate: '번역', resultPlaceholder: '번역 결과가 여기에 표시됩니다', inputRequired: '입력 필요', inputRequiredMsg: '번역할 텍스트를 입력하세요.', errorMsg: '[오류] 번역에 실패했습니다. 잠시 후 다시 시도하세요.', offlineMsg: '📡 오프라인 모드 — 인터넷 연결 시 전체 통역 가능', subtitle: '여행 통번역 · 24개국어', footer: `${APP_FOOTER_BRAND_KO}\n24개국어 지원`, offlineBadge: '🔴 오프라인', ocrTitle: '이미지 OCR 번역', ocrSubtitle: '메뉴판, 표지판, 영수증 이미지를 선택하면 텍스트를 추출해 바로 번역합니다.', ocrPickImage: '🖼️ 이미지 선택', ocrLoading: 'OCR 추출 중...', ocrExtractedTitle: 'OCR 추출 텍스트', ocrTranslatedTitle: 'OCR 번역 결과', ocrSelectedFile: '선택 파일: {file}', ocrErrorMsg: '이미지 OCR 처리에 실패했습니다. 잠시 후 다시 시도하세요.', autoVoiceSegmentStatus: '🎙️ 듣는 중 · 말이 끝나면 자동 번역', autoVoiceDuplicateSkipped: '↺ 같은 문장 자동 번역은 중복 전송을 방지하기 위해 생략했습니다.', autoVoiceDetected: '🎙️ 자동 감지: {from} → {to}', autoVoiceModeStopped: '🎙️ 대화 통역을 종료했습니다.', autoVoiceModeStarted: '🎙️ 대화 통역 시작 · 말 끝날 때까지 듣습니다', manualVoiceOnlyNotice: '🎙️ 대화 통역 OFF — 텍스트 입력만 사용합니다.', manualLanguageHint: 'GPS 우선 · 필요 시 수동', profileLanguageLabel: '내 언어 (프로필)', profileLanguageHint: '프로필 저장값', peerLanguageLabel: '상대 언어 (GPS/수동)', peerLanguageHint: 'GPS 우선 · 필요 시 수동', faceConversationOn: '🎙️ 대화 통역 ON', faceConversationOff: '대화 통역 OFF', faceConversationPeerRequired: '상대 언어를 GPS 또는 수동 선택으로 지정해 주세요.', faceListenProcessing: '🔄 번역·음성 출력 중...', faceSpeakingStatus: '🔊 통역 음성 출력 중 · 듣기 멈춤', faceVadHint: 'VoIP와 같이 말이 끝날 때까지 마이크가 켜져 있습니다.', interAutoRelayDuplicateSkipped: '↺ 같은 문장 자동 중계는 중복 전송을 방지하기 위해 생략했습니다.', interAutoRelayPending: '⏱️ {delay} 무입력 시 자동 중계 전송' },
    en: { sourceLang: 'Source Language', targetLang: 'Target Language', inputPlaceholder: 'Enter text to translate', swap: '⇄ Swap', translate: 'Translate', resultPlaceholder: 'Translation will appear here', inputRequired: 'Input required', inputRequiredMsg: 'Please enter text to translate.', errorMsg: '[Error] Translation failed. Please try again.', offlineMsg: '📡 Offline mode — Full translation available with internet', subtitle: 'Travel Interpreter · 24 Languages', footer: `${APP_FOOTER_BRAND}\n24 Languages Supported`, offlineBadge: '🔴 Offline', ocrTitle: 'Image OCR Translation', ocrSubtitle: 'Pick a menu, sign, or receipt image to extract text and translate it immediately.', ocrPickImage: '🖼️ Pick image', ocrLoading: 'Running OCR...', ocrExtractedTitle: 'OCR Extracted Text', ocrTranslatedTitle: 'OCR Translation Result', ocrSelectedFile: 'Selected file: {file}', ocrErrorMsg: 'Image OCR failed. Please try again.', autoVoiceSegmentStatus: '🎙️ Listening · auto-translate when you finish speaking', autoVoiceDuplicateSkipped: '↺ Duplicate sentence skipped to prevent repeated auto translation.', autoVoiceDetected: '🎙️ Auto-detected: {from} → {to}', autoVoiceModeStopped: '🎙️ Face conversation mode stopped.', autoVoiceModeStarted: '🎙️ Conversation started · listening until you finish speaking', manualVoiceOnlyNotice: '🎙️ Face conversation OFF — text input only.', manualLanguageHint: 'GPS first · manual override', profileLanguageLabel: 'My language (profile)', profileLanguageHint: 'Saved in profile', peerLanguageLabel: 'Peer language (GPS/manual)', peerLanguageHint: 'GPS first · manual override', faceConversationOn: '🎙️ Conversation ON', faceConversationOff: 'Conversation OFF', faceConversationPeerRequired: 'Set the peer language via GPS or manual selection.', faceListenProcessing: '🔄 Translating & speaking...', faceSpeakingStatus: '🔊 Speaking translation · listening paused', faceVadHint: 'Like VoIP — the mic stays on until you finish speaking.', interAutoRelayDuplicateSkipped: '↺ Duplicate sentence skipped to prevent repeated auto relay.', interAutoRelayPending: '⏱️ Auto relay after {delay} of no input' },
    zh: { sourceLang: '源语言', targetLang: '目标语言', inputPlaceholder: '请输入要翻译的文本', swap: '⇄ 切换语言', translate: '翻译', resultPlaceholder: '翻译结果将显示在这里', inputRequired: '需要输入', inputRequiredMsg: '请输入要翻译的文本。', errorMsg: '[错误] 翻译失败，请稍后重试。', offlineMsg: '📡 离线模式 — 联网后可使用完整翻译', subtitle: 'AI 翻译 · 24种语言', footer: `${APP_FOOTER_BRAND}\n支持24种语言`, offlineBadge: '🔴 离线' },
    'zh-tw': { sourceLang: '來源語言', targetLang: '目標語言', inputPlaceholder: '請輸入要翻譯的文字', swap: '⇄ 切換語言', translate: '翻譯', resultPlaceholder: '翻譯結果將顯示在這裡', inputRequired: '需要輸入', inputRequiredMsg: '請輸入要翻譯的文字。', errorMsg: '[錯誤] 翻譯失敗，請稍後再試。', offlineMsg: '📡 離線模式 — 連網後可使用完整翻譯', subtitle: 'AI 翻譯 · 24種語言', footer: `${APP_FOOTER_BRAND}\n支援24種語言`, offlineBadge: '🔴 離線' },
    ja: { sourceLang: '翻訳元言語', targetLang: '翻訳先言語', inputPlaceholder: '翻訳するテキストを入力してください', swap: '⇄ 言語スワップ', translate: '翻訳', resultPlaceholder: '翻訳結果がここに表示されます', inputRequired: '入力が必要です', inputRequiredMsg: '翻訳するテキストを入力してください。', errorMsg: '[エラー] 翻訳に失敗しました。後でもう一度お試しください。', offlineMsg: '📡 オフラインモード — インターネット接続後に完全翻訳可能', subtitle: 'AI 通訳 · 24言語', footer: `${APP_FOOTER_BRAND}\n24言語対応`, offlineBadge: '🔴 オフライン' },
    es: { sourceLang: 'Idioma de origen', targetLang: 'Idioma de destino', inputPlaceholder: 'Ingrese el texto a traducir', swap: '⇄ Cambiar', translate: 'Traducir', resultPlaceholder: 'La traducción aparecerá aquí', inputRequired: 'Entrada requerida', inputRequiredMsg: 'Por favor ingrese el texto a traducir.', errorMsg: '[Error] La traducción falló. Inténtelo de nuevo.', offlineMsg: '📡 Modo sin conexión — Traducción completa disponible con internet', subtitle: 'Intérprete AI · 24 Idiomas', footer: `${APP_FOOTER_BRAND}\n24 Idiomas`, offlineBadge: '🔴 Sin conexión' },
    fr: { sourceLang: 'Langue source', targetLang: 'Langue cible', inputPlaceholder: 'Entrez le texte à traduire', swap: '⇄ Permuter', translate: 'Traduire', resultPlaceholder: 'La traduction apparaîtra ici', inputRequired: 'Saisie requise', inputRequiredMsg: 'Veuillez entrer le texte à traduire.', errorMsg: '[Erreur] La traduction a échoué. Veuillez réessayer.', offlineMsg: '📡 Mode hors ligne — Traduction complète disponible avec internet', subtitle: 'Interprète AI · 24 Langues', footer: `${APP_FOOTER_BRAND}\n24 Langues`, offlineBadge: '🔴 Hors ligne' },
    de: { sourceLang: 'Quellsprache', targetLang: 'Zielsprache', inputPlaceholder: 'Text zum Übersetzen eingeben', swap: '⇄ Tauschen', translate: 'Übersetzen', resultPlaceholder: 'Übersetzung erscheint hier', inputRequired: 'Eingabe erforderlich', inputRequiredMsg: 'Bitte geben Sie den zu übersetzenden Text ein.', errorMsg: '[Fehler] Übersetzung fehlgeschlagen. Bitte versuchen Sie es erneut.', offlineMsg: '📡 Offline-Modus — Vollständige Übersetzung mit Internet verfügbar', subtitle: 'KI-Dolmetscher · 24 Sprachen', footer: `${APP_FOOTER_BRAND}\n24 Sprachen`, offlineBadge: '🔴 Offline' },
    pt: { sourceLang: 'Idioma de origem', targetLang: 'Idioma de destino', inputPlaceholder: 'Digite o texto para traduzir', swap: '⇄ Trocar', translate: 'Traduzir', resultPlaceholder: 'A tradução aparecerá aqui', inputRequired: 'Entrada necessária', inputRequiredMsg: 'Por favor, insira o texto para traduzir.', errorMsg: '[Erro] A tradução falhou. Por favor, tente novamente.', offlineMsg: '📡 Modo offline — Tradução completa disponível com internet', subtitle: 'Intérprete AI · 24 Idiomas', footer: `${APP_FOOTER_BRAND}\n24 Idiomas`, offlineBadge: '🔴 Offline' },
    ru: { sourceLang: 'Исходный язык', targetLang: 'Целевой язык', inputPlaceholder: 'Введите текст для перевода', swap: '⇄ Поменять', translate: 'Перевести', resultPlaceholder: 'Перевод появится здесь', inputRequired: 'Ввод обязателен', inputRequiredMsg: 'Пожалуйста, введите текст для перевода.', errorMsg: '[Ошибка] Перевод не удался. Попробуйте ещё раз.', offlineMsg: '📡 Офлайн-режим — Полный перевод доступен при наличии интернета', subtitle: 'AI Переводчик · 24 Языка', footer: `${APP_FOOTER_BRAND}\n24 языка`, offlineBadge: '🔴 Офлайн' },
    ar: { sourceLang: 'اللغة المصدر', targetLang: 'اللغة الهدف', inputPlaceholder: 'أدخل النص للترجمة', swap: '⇄ تبديل', translate: 'ترجمة', resultPlaceholder: 'ستظهر الترجمة هنا', inputRequired: 'مطلوب إدخال', inputRequiredMsg: 'الرجاء إدخال النص للترجمة.', errorMsg: '[خطأ] فشلت الترجمة. يرجى المحاولة مرة أخرى.', offlineMsg: '📡 وضع عدم الاتصال — الترجمة الكاملة متاحة مع الإنترنت', subtitle: 'مترجم AI · 24 لغة', footer: `${APP_FOOTER_BRAND}\n24 لغة مدعومة`, offlineBadge: '🔴 غير متصل' },
    hi: { sourceLang: 'स्रोत भाषा', targetLang: 'लक्ष्य भाषा', inputPlaceholder: 'अनुवाद के लिए पाठ दर्ज करें', swap: '⇄ स्वैप', translate: 'अनुवाद करें', resultPlaceholder: 'अनुवाद यहाँ दिखाई देगा', inputRequired: 'इनपुट आवश्यक', inputRequiredMsg: 'कृपया अनुवाद के लिए पाठ दर्ज करें।', errorMsg: '[त्रुटि] अनुवाद विफल हुआ। कृपया पुनः प्रयास करें।', offlineMsg: '📡 ऑफ़लाइन मोड — इंटरनेट के साथ पूर्ण अनुवाद उपलब्ध', subtitle: 'AI दुभाषिया · 24 भाषाएँ', footer: `${APP_FOOTER_BRAND}\n24 भाषाएँ समर्थित`, offlineBadge: '🔴 ऑफ़लाइन' },
    it: { sourceLang: 'Lingua di origine', targetLang: 'Lingua di destinazione', inputPlaceholder: 'Inserisci il testo da tradurre', swap: '⇄ Scambia', translate: 'Traduci', resultPlaceholder: 'La traduzione apparirà qui', inputRequired: 'Input richiesto', inputRequiredMsg: 'Inserisci il testo da tradurre.', errorMsg: '[Errore] Traduzione fallita. Riprovare.', offlineMsg: '📡 Modalità offline — Traduzione completa disponibile con internet', subtitle: 'Interprete AI · 24 Lingue', footer: `${APP_FOOTER_BRAND}\n24 Lingue`, offlineBadge: '🔴 Offline' },
    tr: { sourceLang: 'Kaynak Dil', targetLang: 'Hedef Dil', inputPlaceholder: 'Çevrilecek metni girin', swap: '⇄ Değiştir', translate: 'Çevir', resultPlaceholder: 'Çeviri burada görünecek', inputRequired: 'Giriş gerekli', inputRequiredMsg: 'Lütfen çevrilecek metni girin.', errorMsg: '[Hata] Çeviri başarısız. Lütfen tekrar deneyin.', offlineMsg: '📡 Çevrimdışı mod — İnternet ile tam çeviri mevcut', subtitle: 'AI Tercüman · 24 Dil', footer: `${APP_FOOTER_BRAND}\n24 Dil Destekleniyor`, offlineBadge: '🔴 Çevrimdışı' },
    vi: { sourceLang: 'Ngôn ngữ nguồn', targetLang: 'Ngôn ngữ đích', inputPlaceholder: 'Nhập văn bản cần dịch', swap: '⇄ Hoán đổi', translate: 'Dịch', resultPlaceholder: 'Bản dịch sẽ hiển thị ở đây', inputRequired: 'Cần nhập liệu', inputRequiredMsg: 'Vui lòng nhập văn bản cần dịch.', errorMsg: '[Lỗi] Dịch thất bại. Vui lòng thử lại.', offlineMsg: '📡 Chế độ ngoại tuyến — Dịch đầy đủ khi có internet', subtitle: 'Phiên dịch AI · 24 Ngôn ngữ', footer: `${APP_FOOTER_BRAND}\n24 Ngôn ngữ`, offlineBadge: '🔴 Ngoại tuyến' },
    th: { sourceLang: 'ภาษาต้นทาง', targetLang: 'ภาษาปลายทาง', inputPlaceholder: 'ป้อนข้อความที่ต้องการแปล', swap: '⇄ สลับ', translate: 'แปล', resultPlaceholder: 'ผลการแปลจะแสดงที่นี่', inputRequired: 'ต้องการข้อมูล', inputRequiredMsg: 'กรุณาป้อนข้อความที่ต้องการแปล', errorMsg: '[ข้อผิดพลาด] การแปลล้มเหลว โปรดลองอีกครั้ง', offlineMsg: '📡 โหมดออฟไลน์ — แปลเต็มรูปแบบเมื่อมีอินเทอร์เน็ต', subtitle: 'AI ล่าม · 24 ภาษา', footer: `${APP_FOOTER_BRAND}\n24 ภาษา`, offlineBadge: '🔴 ออฟไลน์' },
    id: { sourceLang: 'Bahasa Sumber', targetLang: 'Bahasa Tujuan', inputPlaceholder: 'Masukkan teks untuk diterjemahkan', swap: '⇄ Tukar', translate: 'Terjemahkan', resultPlaceholder: 'Terjemahan akan muncul di sini', inputRequired: 'Input diperlukan', inputRequiredMsg: 'Silakan masukkan teks untuk diterjemahkan.', errorMsg: '[Kesalahan] Terjemahan gagal. Silakan coba lagi.', offlineMsg: '📡 Mode offline — Terjemahan lengkap tersedia dengan internet', subtitle: 'Penerjemah AI · 24 Bahasa', footer: `${APP_FOOTER_BRAND}\n24 Bahasa`, offlineBadge: '🔴 Offline' },
    ms: { sourceLang: 'Bahasa Sumber', targetLang: 'Bahasa Sasaran', inputPlaceholder: 'Masukkan teks untuk diterjemah', swap: '⇄ Tukar', translate: 'Terjemah', resultPlaceholder: 'Terjemahan akan muncul di sini', inputRequired: 'Input diperlukan', inputRequiredMsg: 'Sila masukkan teks untuk diterjemah.', errorMsg: '[Ralat] Terjemahan gagal. Sila cuba lagi.', offlineMsg: '📡 Mod luar talian — Terjemahan penuh tersedia dengan internet', subtitle: 'Penterjemah AI · 24 Bahasa', footer: `${APP_FOOTER_BRAND}\n24 Bahasa`, offlineBadge: '🔴 Luar Talian' },
    nl: { sourceLang: 'Brontaal', targetLang: 'Doeltaal', inputPlaceholder: 'Voer tekst in om te vertalen', swap: '⇄ Wisselen', translate: 'Vertalen', resultPlaceholder: 'Vertaling verschijnt hier', inputRequired: 'Invoer vereist', inputRequiredMsg: 'Voer de te vertalen tekst in.', errorMsg: '[Fout] Vertaling mislukt. Probeer opnieuw.', offlineMsg: '📡 Offlinemodus — Volledige vertaling beschikbaar met internet', subtitle: 'AI Tolk · 24 Talen', footer: `${APP_FOOTER_BRAND}\n24 Talen`, offlineBadge: '🔴 Offline' },
    pl: { sourceLang: 'Język źródłowy', targetLang: 'Język docelowy', inputPlaceholder: 'Wprowadź tekst do tłumaczenia', swap: '⇄ Zamień', translate: 'Tłumacz', resultPlaceholder: 'Tłumaczenie pojawi się tutaj', inputRequired: 'Wymagane wprowadzenie', inputRequiredMsg: 'Wprowadź tekst do tłumaczenia.', errorMsg: '[Błąd] Tłumaczenie nie powiodło się. Spróbuj ponownie.', offlineMsg: '📡 Tryb offline — Pełne tłumaczenie dostępne z internetem', subtitle: 'Tłumacz AI · 24 Języki', footer: `${APP_FOOTER_BRAND}\n24 Języki`, offlineBadge: '🔴 Offline' },
    uk: { sourceLang: 'Вихідна мова', targetLang: 'Цільова мова', inputPlaceholder: 'Введіть текст для перекладу', swap: '⇄ Замінити', translate: 'Перекласти', resultPlaceholder: "Переклад з'явиться тут", inputRequired: 'Потрібне введення', inputRequiredMsg: 'Будь ласка, введіть текст для перекладу.', errorMsg: '[Помилка] Переклад не вдався. Спробуйте ще раз.', offlineMsg: '📡 Офлайн-режим — Повний переклад доступний при наявності інтернету', subtitle: 'AI Перекладач · 24 Мови', footer: `${APP_FOOTER_BRAND}\n24 мови`, offlineBadge: '🔴 Офлайн' },
    sv: { sourceLang: 'Källspråk', targetLang: 'Målspråk', inputPlaceholder: 'Ange text att översätta', swap: '⇄ Byt', translate: 'Översätt', resultPlaceholder: 'Översättning visas här', inputRequired: 'Inmatning krävs', inputRequiredMsg: 'Ange texten som ska översättas.', errorMsg: '[Fel] Översättning misslyckades. Försök igen.', offlineMsg: '📡 Offlineläge — Full översättning tillgänglig med internet', subtitle: 'AI Tolk · 24 Språk', footer: `${APP_FOOTER_BRAND}\n24 Språk`, offlineBadge: '🔴 Offline' },
    no: { sourceLang: 'Kildespråk', targetLang: 'Målspråk', inputPlaceholder: 'Skriv inn tekst å oversette', swap: '⇄ Bytt', translate: 'Oversett', resultPlaceholder: 'Oversettelse vises her', inputRequired: 'Inndata kreves', inputRequiredMsg: 'Skriv inn tekst å oversette.', errorMsg: '[Feil] Oversettelse mislyktes. Prøv igjen.', offlineMsg: '📡 Frakoblet modus — Full oversettelse tilgengelig med internett', subtitle: 'AI Tolk · 24 Språk', footer: `${APP_FOOTER_BRAND}\n24 Språk`, offlineBadge: '🔴 Frakoblet' },
    da: { sourceLang: 'Kildesprog', targetLang: 'Målsprog', inputPlaceholder: 'Indtast tekst til oversættelse', swap: '⇄ Skift', translate: 'Oversæt', resultPlaceholder: 'Oversættelse vises her', inputRequired: 'Indtastning påkrævet', inputRequiredMsg: 'Indtast tekst til oversættelse.', errorMsg: '[Fejl] Oversættelse mislykkedes. Prøv igen.', offlineMsg: '📡 Offlinetilstand — Fuld oversættelse tilgængelig med internet', subtitle: 'AI Tolk · 24 Sprog', footer: `${APP_FOOTER_BRAND}\n24 Sprog`, offlineBadge: '🔴 Offline' },
};

function getUiText(lang: string) {
    const fallback = UI_TEXT['en'];
    const selected = UI_TEXT[lang] ?? fallback;
    const applyLanguageCount = (value: string) => value.replace(/24/g, String(SUPPORTED_LANGUAGE_COUNT));
    return {
        ...selected,
        subtitle: applyLanguageCount(selected.subtitle),
        footer: applyLanguageCount(selected.footer),
        ocrTitle: selected.ocrTitle ?? fallback.ocrTitle ?? 'Image OCR Translation',
        ocrSubtitle: selected.ocrSubtitle ?? fallback.ocrSubtitle ?? 'Pick an image to extract text and translate it.',
        ocrPickImage: selected.ocrPickImage ?? fallback.ocrPickImage ?? '🖼️ Pick image',
        ocrLoading: selected.ocrLoading ?? fallback.ocrLoading ?? 'Running OCR...',
        ocrExtractedTitle: selected.ocrExtractedTitle ?? fallback.ocrExtractedTitle ?? 'OCR Extracted Text',
        ocrTranslatedTitle: selected.ocrTranslatedTitle ?? fallback.ocrTranslatedTitle ?? 'OCR Translation Result',
        ocrSelectedFile: selected.ocrSelectedFile ?? fallback.ocrSelectedFile ?? 'Selected file: {file}',
        ocrErrorMsg: selected.ocrErrorMsg ?? fallback.ocrErrorMsg ?? 'Image OCR failed. Please try again.',
        autoVoiceSegmentStatus: selected.autoVoiceSegmentStatus ?? fallback.autoVoiceSegmentStatus ?? '🎙️ Auto voice translation: processing in {delay} chunks.',
        autoVoiceDuplicateSkipped: selected.autoVoiceDuplicateSkipped ?? fallback.autoVoiceDuplicateSkipped ?? '↺ Duplicate sentence skipped to prevent repeated auto translation.',
        autoVoiceDetected: selected.autoVoiceDetected ?? fallback.autoVoiceDetected ?? '🎙️ Auto-detected: {from} → {to}',
        autoVoiceModeStopped: selected.autoVoiceModeStopped ?? fallback.autoVoiceModeStopped ?? '🎙️ Auto voice translation mode has stopped.',
        autoVoiceModeStarted: selected.autoVoiceModeStarted ?? fallback.autoVoiceModeStarted ?? '🎙️ Auto voice translation mode started ({delay} interval)',
        manualVoiceOnlyNotice: selected.manualVoiceOnlyNotice ?? fallback.manualVoiceOnlyNotice ?? '🎤 Recording starts only when you press the mic. Select both source and target languages manually.',
        manualLanguageHint: selected.manualLanguageHint ?? fallback.manualLanguageHint ?? 'Manual selection',
        profileLanguageLabel: selected.profileLanguageLabel ?? fallback.profileLanguageLabel ?? 'My language (profile)',
        profileLanguageHint: selected.profileLanguageHint ?? fallback.profileLanguageHint ?? 'Saved in profile',
        peerLanguageLabel: selected.peerLanguageLabel ?? fallback.peerLanguageLabel ?? 'Peer language (GPS/manual)',
        peerLanguageHint: selected.peerLanguageHint ?? fallback.peerLanguageHint ?? 'GPS first · manual override',
        faceConversationOn: selected.faceConversationOn ?? fallback.faceConversationOn ?? '🎙️ Conversation ON',
        faceConversationOff: selected.faceConversationOff ?? fallback.faceConversationOff ?? 'Conversation OFF',
        faceConversationPeerRequired: selected.faceConversationPeerRequired ?? fallback.faceConversationPeerRequired ?? 'Set the peer language via GPS or manual selection.',
        faceListenProcessing: selected.faceListenProcessing ?? fallback.faceListenProcessing ?? '🔄 Translating & speaking...',
        faceSpeakingStatus: selected.faceSpeakingStatus ?? fallback.faceSpeakingStatus ?? '🔊 Speaking translation · listening paused',
        faceVadHint: selected.faceVadHint ?? fallback.faceVadHint ?? 'The mic stays on until you finish speaking.',
        interAutoRelayDuplicateSkipped: selected.interAutoRelayDuplicateSkipped ?? fallback.interAutoRelayDuplicateSkipped ?? '↺ Duplicate sentence skipped to prevent repeated auto relay.',
        interAutoRelayPending: selected.interAutoRelayPending ?? fallback.interAutoRelayPending ?? '⏱️ Auto relay after {delay} of no input',
    };
}

// ─────────────────────────────────────────────
// 색상 팔레트 (WorldLinco 다크 테마)
// ─────────────────────────────────────────────
const C = {
    bg: '#0b0f16',
    surface: '#151b23',
    border: '#21262d',
    accent: '#2a7cff',
    green: '#31c45d',
    text: '#e6edf3',
    sub: '#8b949e',
    badge: '#1a2535',
};

// ─────────────────────────────────────────────
// 컴포넌트
// ─────────────────────────────────────────────
export default function App() {
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
    const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
    const [authHydrated, setAuthHydrated] = useState(false);
    const [showLogin, setShowLogin] = useState(false);
    const [authModalMode, setAuthModalMode] = useState<AuthModalMode>('login');
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPw, setLoginPw] = useState('');
    const [signupUsername, setSignupUsername] = useState('');
    const [signupFullName, setSignupFullName] = useState('');
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
        setVoipLocalLangOverride(code);
        setVoipLangModalVisible(false);
        void AsyncStorage.setItem(VOIP_LOCAL_LANG_STORAGE_KEY, code).catch(() => { });
    }, []);
    const handleClearVoipLocalLang = useCallback(() => {
        setVoipLocalLangOverride(null);
        setVoipLangModalVisible(false);
        void AsyncStorage.removeItem(VOIP_LOCAL_LANG_STORAGE_KEY).catch(() => { });
    }, []);
    const [voipAutoCallVoiceId, setVoipAutoCallVoiceId] = useState<string | null>(null);
    const [selectedChatRoom, setSelectedChatRoom] = useState<ChatRoomSummary | null>(null);
    const [chatRefreshKey, setChatRefreshKey] = useState(0);
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
        console.log('[AUTH_INPUT_PROBE]', JSON.stringify({
            event,
            timestamp,
            show_login: showLogin,
            focus_field: authDebugFocusField,
            email_length: loginEmail.length,
            password_length: loginPw.length,
            ...details,
        }));
    }, [authDebugFocusField, loginEmail.length, loginPw.length, showLogin]);

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
                const seed = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}${attempt}`;
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
    const [nearbyCategory, setNearbyCategory] = useState<SearchCategory>('all');
    const [radiusM, setRadiusM] = useState(5000);
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

    const selectedNearbyPlace = nearbyPlaces.find((item) => item.id === selectedNearbyPlaceId) ?? nearbyPlaces[0] ?? null;
    const selectedBookingPlace = nearbyPlaces.find((item) => item.id === selectedBookingPlaceId) ?? null;
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
                void postIncomingVoipLocalNotification(
                    callId,
                    callerVoiceId,
                    callerLabel,
                    'VOIP_INCOMING_ALERT_NOTIFICATION_REASSERTED',
                );
                if (isVoipIncomingAlertNativeAvailable()) {
                    void startNativeIncomingVoipAlert(callId, callerLabel ?? callerVoiceId ?? '친구');
                } else if (Platform.OS !== 'web') {
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
            try {
                getVoIPToneService().playRingingTone();
                logUiPressProbe('VOIP_INCOMING_ALERT_TONE_REQUESTED', { call_id: callId });
            } catch (error: any) {
                logUiPressProbe('VOIP_INCOMING_ALERT_TONE_FAILED', {
                    call_id: callId,
                    error_message: error?.message || 'unknown',
                });
            }

            if (Platform.OS !== 'web') {
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
                const nativeStarted = await startNativeIncomingVoipAlert(callId, callerLabelText);
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
                if (response.status === 404 && pendingIncomingVoipCallRef.current?.call_id) {
                    await resolveStalePendingIncomingCall(source, 'pending_call_missing');
                }
                return;
            }

            const payload = await response.json() as (CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null;
            if (!payload?.call_id || !payload.signaling_server) {
                if (pendingIncomingVoipCallRef.current?.call_id) {
                    await resolveStalePendingIncomingCall(source, 'empty_pending_payload');
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
    }, [logUiPressProbe, loginEmail, loginPw, signupCountryCode, signupFullName, signupPhone, signupPreferredLanguage, signupUsername, signupVerificationChannel]);

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
            setAuthModalMode('login');
            setSignupUsername('');
            setSignupFullName('');
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
    }, [applyAuthenticatedSession, logUiPressProbe, loginEmail, loginPw, resetSignupProfileDraft, signupCountryCode, signupFullName, signupOtpCode, signupPreferredLanguage, signupSessionToken]);

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
    }, [loginEmail, renderSignupProfileSelectors, signupFullName, signupMaskedTarget, signupOtpCode, signupPhone, signupStep, signupUsername, signupVerificationChannel]);

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
        void handleShareMessageToChat({
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
        void persistVoipValidationFriendCallBypass(false);
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
            if (payload.participant_role === 'callee' && payload.status === 'connecting' && !isStoredAcceptedSession) {
                await requestEndVoipCall(API_BASE, token, payload.call_id, 'stale_connecting_resume');
                await clearStoredActiveVoipSession();
                logUiPressProbe('VOIP_ACTIVE_CALL_RESUME_ENDED_STALE_CONNECTING', {
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

    const handleStartFriendVoiceCall = useCallback(async (friend: Friend) => {
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
            const firstBookablePlace =
                places.find((place) => place.category === 'hotel' && place.booking_supported)
                ?? places.find((place) => place.category === 'airport' && place.booking_supported);
            setSelectedBookingPlaceId(firstBookablePlace?.id || '');
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
            void Linking.openURL(payload.googleMapsUrl);
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
        const attemptId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

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

    const handleDetectLangByGPS = useCallback(async (silent = false) => {
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
        void faceVadControllerRef.current.stop();
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
            // 반이중 가드: 통역 음성을 출력하는 동안에는 듣기를 시작하지 않는다(발화↔듣기 겹침 방지).
            if (effectiveAutoMode && inputTarget === 'main' && faceSpeakingRef.current) {
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
                // 반이중 보장: 아직 통역 음성이 재생 중(잔향 drain 포함)이면 듣기를 켜지 않고 잠시 후 재확인한다.
                if (faceSpeakingRef.current) {
                    autoVoiceRestartTimerRef.current = setTimeout(beginCapture, 200);
                    return;
                }
                if (voiceInputTargetRef.current === 'main') {
                    void startVoiceInput({ autoMode: true });
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
                const profileLangRaw = String(userInfo?.preferred_language || fromLang).trim().toLowerCase();
                const profileLang: LangCode = isSupportedLangCode(profileLangRaw) ? profileLangRaw as LangCode : fromLang;
                // 대면 화면 '친구 모드': 음성을 전용 친구 채팅 경로로 보내 자연스러운 '답변'을 받는다(번역 아님).
                // 노래 모드/통화중계(inter_call)와는 독립이며, main 타깃에서만 적용한다.
                const isFaceGptMode = !songModeEnabled
                    && activeVoiceInputTarget === 'main'
                    && faceAiModeRef.current === 'gpt';
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
                        correlation_id: faceCorrelationId,
                        feature_id: FEATURE_IDS.faceInterpret,
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
                    if (transcript) {
                        if (isFaceGptMode) {
                            // 친구 모드: 번역/에코 로직을 타지 않고 LLM 답변을 그대로 표시 + 음성 출력.
                            const answer = String(data.response_text ?? '').trim();
                            setInputText(transcript);
                            // 소리새 AI 발화 중 '여행 일정/장소 찾기' 의도일 때만 패널 입력으로 자동 연결(생성은 사용자 탭).
                            // 일상 잡담·일반 질문은 패널을 건드리지 않는다.
                            if (isTravelItineraryIntent(transcript)) {
                                setItinerarySeedQuery(transcript);
                                setItinerarySeedNonce((n) => n + 1);
                            }
                            if (answer) {
                                setResultText(answer);
                                setOffline(false);
                                setEngine('worldlinco-sorisae-ai');
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
                                const speakText = normalizeSpeakText(answer);
                                if (speakText) {
                                    // 답변 언어를 추정해(스크립트 기반) 그 나라의 현지 뉴럴 보이스로 발화한다.
                                    // 서버가 보낸 neural 오디오(data.audio_base64)를 우선 재생하고,
                                    // 없으면 답변 언어로 재합성, 그래도 실패하면 단말 TTS로 폴백(playFaceTranslationOutput).
                                    const replyLangCode = inferSpeechLangCode(speakText, profileLang);
                                    // 반이중: 친구 답변 발화 중에는 듣기를 멈춘다(자기 음성 재캡처 방지).
                                    faceSpeakingRef.current = true;
                                    setGpsStatus('🐦 소리새 AI 답변 음성 출력 중 · 듣기 멈춤');
                                    facePlaybackPromise = playFaceTranslationOutput({
                                        translatedText: answer,
                                        targetLang: replyLangCode,
                                        audioBase64: typeof data.audio_base64 === 'string' ? data.audio_base64 : null,
                                        audioFormat: typeof data.audio_format === 'string' ? data.audio_format : null,
                                        apiBaseUrl: API_BASE,
                                        playbackSoundRef: faceVoicePlaybackSoundRef,
                                        correlationId: typeof data.correlation_id === 'string' ? data.correlation_id : faceCorrelationId,
                                    }).finally(() => {
                                        setTimeout(() => {
                                            faceSpeakingRef.current = false;
                                        }, FACE_CONVERSATION_PLAYBACK_DRAIN_MS);
                                    });
                                } else {
                                    setGpsStatus('🐦 소리새 AI 답변 완료');
                                }
                            } else {
                                setGpsStatus('🐦 소리새 AI 응답이 비어 있습니다 · 다시 말씀해 주세요');
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
                                const translated = await translateTextWithRegion(
                                    transcript,
                                    listenLang,
                                    translateTo,
                                );
                                commitInterCallRelay(relayTurn, transcript, translated.translated, { isAutoRelay: true });
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
                                });
                                if (result.echo) {
                                    echoCheck = result;
                                    break;
                                }
                            }
                            const repetitionEcho = isLikelyRepetitionHallucination(transcript)
                                || isLikelyRepetitionHallucination(translatedText);
                            // #1 대기 침묵 중 자가 발화 차단: 무음 구간 Whisper 환각(아웃트로/필러 계열)은
                            // 최근 발화 이력 유무와 무관하게 항상 잡음으로 처리한다. (사용자 요청 — 침묵 중
                            // 혼자 발성하는 문제가 심각하므로, 단발 인사/필러 오차단 위험을 감수하고 우선 차단.)
                            const silenceEcho = isLikelySilenceHallucination(transcript, effectiveFrom)
                                || isLikelySilenceHallucination(translatedText, effectiveTo);
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
        setAutoVoiceModeEnabled(true);
        setGpsStatus(getUiText(fromLang).autoVoiceModeStarted ?? '🎙️ 대화 통역 시작 · 말 끝날 때까지 듣습니다');
        voiceInputTargetRef.current = 'main';
        void startVoiceInput({ autoMode: true });
    }, [autoVoiceModeEnabled, fromLang, getUiText, startVoiceInput, stopVoiceInput, toLang, userInfo?.preferred_language]);

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
            handleSelectInterCallContact(resolvedContact);
        } catch (error: any) {
            setInterCallContactError(error?.message || '단말 전화번호 저장소를 열지 못했습니다.');
        } finally {
            setInterCallContactLoading(false);
        }
    }, [handleSelectInterCallContact]);

    const currentFromLabel = getLangLabel(fromLang);
    const currentToLabel = getLangLabel(toLang);
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
    const showIncomingVoipFixedPanel = false;
    const showIncomingVoipBanner = false;
    const showAuthDebugFloating = AUTH_DEBUG_MARKER_ENABLED && !isVoipDockAttentionVisible && !isVoipRailSectionVisible;

    useEffect(() => {
        activeRailSectionRef.current = activeRailSection;
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
        void stopVoiceInput({ suppressAutoRestart: true });
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
        <SafeAreaView style={styles.root}>
            <StatusBar style="light" />
            <ScrollView
                ref={scrollViewRef}
                contentContainerStyle={styles.scroll}
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
                            <View style={styles.inlineAuthHeaderRow}>
                                <Text style={styles.inlineAuthTitle}>상단 빠른 로그인</Text>
                                <Pressable
                                    style={styles.inlineAuthModeChip}
                                    onPress={toggleAuthModalMode}
                                    accessibilityLabel="worldlinco-inline-auth-mode-toggle"
                                    testID="worldlinco-inline-auth-mode-toggle"
                                >
                                    <Text style={styles.inlineAuthModeChipText}>{authModalMode === 'login' ? '회원가입 전환' : '로그인 전환'}</Text>
                                </Pressable>
                            </View>
                        <Text style={styles.inlineAuthHint}>
                            {authModalMode === 'signup'
                                ? signupStep === 'verify'
                                    ? `${signupMaskedTarget || loginEmail.trim()}으로 인증 코드를 보냈습니다. 프로필 언어·국가를 확인한 뒤 코드를 입력해 주세요.`
                                    : '이메일 또는 전화로 본인 확인 후 가입이 완료됩니다. 프로필 언어·국가(국기)는 VoIP 통역 기준으로 저장됩니다.'
                                : '여행 통번역과 레일 서비스 사용을 위해 여기서 바로 로그인합니다.'}
                        </Text>
                            {authModalMode === 'signup' ? renderSignupAuthFields() : null}
                            {authModalMode !== 'signup' || signupStep === 'form' ? (
                                <>
                                    <TextInput
                                        style={styles.compactInput}
                                        placeholder="이메일"
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
                                    <TextInput
                                        style={styles.compactInput}
                                        placeholder="비밀번호"
                                        placeholderTextColor={C.sub}
                                        secureTextEntry
                                        showSoftInputOnFocus
                                        accessibilityLabel="worldlinco-auth-password-input"
                                        testID="worldlinco-auth-password-input"
                                        value={loginPw}
                                        onFocus={handleLoginPasswordFocus}
                                        onBlur={() => { handleLoginFieldBlur('PASSWORD'); }}
                                        onChangeText={handleLoginPasswordChange}
                                    />
                                </>
                            ) : null}
                            {loginError ? <Text style={styles.errorText}>{loginError}</Text> : null}
                            {authModalMode === 'login' ? (
                                <View style={styles.inlineAuthUtilityRow}>
                                    <Pressable onPress={openPasswordRecovery} testID="worldlinco-auth-forgot-password-inline">
                                        <Text style={styles.authUtilityLinkText}>비밀번호 찾기</Text>
                                    </Pressable>
                                    {biometricLoginReady && biometricLoginEnabled ? (
                                        <Pressable onPress={() => { void handleBiometricLogin(); }} disabled={biometricLoginBusy} testID="worldlinco-auth-biometric-login-inline">
                                            <Text style={styles.authUtilityLinkText}>{biometricLoginBusy ? '지문 확인 중...' : '👆 지문 로그인'}</Text>
                                        </Pressable>
                                    ) : null}
                                </View>
                            ) : null}
                            {demoSessionMessage ? <Text style={styles.inlineAuthStatus}>{demoSessionMessage}</Text> : null}
                            <View style={styles.inlineAuthActionRow}>
                                <Pressable
                                    style={[styles.inlineActionBtn, demoSessionLoading && styles.inlineGhostBtnDisabled]}
                                    onPress={() => { void handleStartInstantDemoSession('chat'); }}
                                    disabled={demoSessionLoading || loginLoading}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-demo-session-start-button"
                                    testID="worldlinco-demo-session-start-button"
                                >
                                    <Text style={styles.inlineActionBtnText}>{demoSessionLoading ? '데모 연결 중...' : '데모 세션 시작'}</Text>
                                </Pressable>
                                <Pressable
                                    style={[styles.translateBtn, loginLoading && styles.translateBtnDisabled, styles.inlineAuthSubmitBtn]}
                                    onPress={authModalMode === 'login' ? handleLogin : handleSignupSubmit}
                                    disabled={loginLoading}
                                    accessibilityRole="button"
                                    accessibilityLabel={authModalMode === 'login' ? 'worldlinco-auth-login-submit-button' : 'worldlinco-auth-signup-submit-button'}
                                    testID={authModalMode === 'login' ? 'worldlinco-auth-login-submit-button' : 'worldlinco-auth-signup-submit-button'}
                                >
                                    {loginLoading ? (
                                        <ActivityIndicator color="#fff" size="small" />
                                    ) : (
                                        <Text style={styles.translateBtnText}>{signupSubmitLabel}</Text>
                                    )}
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
                ) : (
                    <View style={styles.workspaceShell}>
                        <View style={styles.workspaceHeaderCard}>
                            <Text style={styles.workspaceHeaderTitle}>단일 작업창</Text>
                            <Text style={styles.workspaceHeaderBody}>
                                현재 화면에는 번역 홈 또는 선택한 레일 하나만 표시합니다. 모든 진입 버튼은 아래 상단 바에 고정합니다.
                            </Text>
                            <View style={styles.workspaceRailGrid}>
                                <Pressable
                                    style={[styles.workspaceRailCard, activeRailSection === null && styles.workspaceRailCardActive]}
                                    onPress={() => {
                                        setActiveRailSection(null);
                                        setIsRailMenuOpen(false);
                                    }}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-translate-home-button"
                                    testID="worldlinco-translate-home-button"
                                >
                                    <Text style={styles.workspaceRailIcon}>🏠</Text>
                                    <Text style={styles.workspaceRailTitle}>번역 홈</Text>
                                    <Text style={styles.workspaceRailMeta} numberOfLines={1}>대면 통역</Text>
                                </Pressable>
                                {SECTION_RAIL_ITEMS.map((item) => (
                                    <Pressable
                                        key={`workspace-${item.key}`}
                                        style={[styles.workspaceRailCard, activeRailSection === item.key && styles.workspaceRailCardActive]}
                                        onPress={() => handlePressSectionRail(item.key)}
                                        accessibilityRole="button"
                                        accessibilityLabel={buildSectionRailSelector(item.key)}
                                        testID={buildSectionRailSelector(item.key)}
                                    >
                                        <Text style={styles.workspaceRailIcon}>{item.icon}</Text>
                                        <Text style={styles.workspaceRailTitle}>{item.key === 'voip' ? '📞 VoIP 테스트' : item.label}</Text>
                                        <Text style={styles.workspaceRailMeta} numberOfLines={1}>
                                            {item.key === 'chat'
                                                ? '채팅/친구'
                                                : item.key === 'voip'
                                                    ? '통역 통화'
                                                    : item.key === 'song-mode'
                                                        ? '노래 번역'
                                                        : '주변/예약'}
                                        </Text>
                                    </Pressable>
                                ))}
                            </View>
                        </View>
                    </View>
                )}

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
                                testID="worldlinco-voip-incoming-accept"
                                accessibilityLabel="수신 보이스톡 받기"
                            >
                                <Text style={styles.inlineActionBtnText}>받기</Text>
                            </Pressable>
                            <Pressable
                                style={styles.inlineGhostBtn}
                                onPress={() => { void handleRejectIncomingVoipCall(); }}
                                testID="worldlinco-voip-incoming-reject"
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
                    <View style={styles.voipModalOverlay}>
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
                                            void handleStartFriendVoiceCall(friend);
                                        }}
                                    />
                                </View>
                            ) : null}
                        </View>
                    </View>
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
                    <View style={styles.voipModalOverlay}>
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
                    </View>
                </Modal>

                {isTranslateWorkspaceVisible ? (
                    <>
                        <View style={styles.travelModeBanner}>
                            <Text style={styles.travelModeTitle}>여행 대면 통역 전용 화면</Text>
                            <Text style={styles.travelModeBody}>
                                이 홈 화면은 여행 중 서로 마주 보고 대화하는 번역 작업만 다룹니다. 채팅, VoIP, 노래, 예약은 상단 고정 레일에서 각각 독립 창으로 이동합니다.
                            </Text>
                        </View>

                        <View style={styles.translationHub}>
                            {Platform.OS !== 'web' ? (
                                <View style={styles.faceAiModeRow}>
                                    <Pressable
                                        style={[styles.faceAiModeBtn, faceAiMode === 'translate' && styles.faceAiModeBtnActive]}
                                        onPress={() => setFaceAiMode('translate')}
                                        accessibilityRole="button"
                                        accessibilityLabel="worldlinco-face-mode-translate"
                                        testID="worldlinco-face-mode-translate"
                                    >
                                        <Text style={[styles.faceAiModeText, faceAiMode === 'translate' && styles.faceAiModeTextActive]}>🌐 통역</Text>
                                    </Pressable>
                                    <Pressable
                                        style={[styles.faceAiModeBtn, faceAiMode === 'gpt' && styles.faceAiModeBtnActive]}
                                        onPress={() => setFaceAiMode('gpt')}
                                        accessibilityRole="button"
                                        accessibilityLabel="worldlinco-face-mode-gpt"
                                        testID="worldlinco-face-mode-gpt"
                                    >
                                        <Text style={[styles.faceAiModeText, faceAiMode === 'gpt' && styles.faceAiModeTextActive]}>🐦 소리새 AI</Text>
                                    </Pressable>
                                </View>
                            ) : null}

                            {Platform.OS !== 'web' && faceAiMode === 'gpt' ? (
                                <Text style={styles.faceVadHintText}>
                                    🐦 소리새 AI — 말한 내용을 번역하지 않고 소리새 AI가 자연스럽게 답해줍니다(음성+화면).
                                </Text>
                            ) : null}

                            {Platform.OS !== 'web' ? (
                                <Pressable
                                    style={[styles.faceConversationToggleBtn, autoVoiceModeEnabled && styles.faceConversationToggleBtnActive]}
                                    onPress={() => { void handleToggleFaceConversation(); }}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-face-conversation-toggle"
                                    testID="worldlinco-face-conversation-toggle"
                                >
                                    <Text style={[styles.faceConversationToggleText, autoVoiceModeEnabled && styles.faceConversationToggleTextActive]}>
                                        {autoVoiceModeEnabled
                                            ? (faceAiMode === 'gpt' ? '🎙️ 소리새 AI 대화 ON' : getUiText(fromLang).faceConversationOn ?? '🎙️ 대화 통역 ON')
                                            : (faceAiMode === 'gpt' ? '🎙️ 소리새 AI 대화 OFF' : getUiText(fromLang).faceConversationOff ?? '대화 통역 OFF')}
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
                        <Text style={styles.sectionTitle}>💬 채팅 + 친구 허브</Text>
                        <Text style={styles.sectionSub}>채팅방, 친구 목록, 친구 찾기를 채팅 레일 안에서 독립적으로 여는 허브입니다.</Text>
                        {token && userInfo ? (
                            selectedChatRoom ? (
                                <ChatRoomScreen
                                    apiBaseUrl={API_BASE}
                                    token={token}
                                    userId={userInfo.id}
                                    room={selectedChatRoom}
                                    visible={isChatRailSectionVisible}
                                    refreshKey={chatRefreshKey}
                                    onBack={() => {
                                        setSelectedChatRoom(null);
                                        setChatRefreshKey((prev) => prev + 1);
                                    }}
                                    onRoomChanged={() => setChatRefreshKey((prev) => prev + 1)}
                                />
                            ) : (
                                <>
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
                                    />
                                    <View style={styles.sectionCard}>
                                        <Text style={styles.sectionTitle}>👥 친구 / 친구 찾기</Text>
                                        <Text style={styles.sectionSub}>채팅 흐름을 끊지 않고 같은 레일에서 친구 목록과 주변 친구 찾기를 엽니다.</Text>
                                        <View style={styles.socialHubRow}>
                                            <Pressable
                                                style={[styles.socialHubBtn, showFriendFolder && styles.socialHubBtnActive]}
                                                onPress={() => handlePressFriendEntry('friend-folder')}
                                                accessibilityRole="button"
                                                accessibilityLabel="친구 목록 열기"
                                                testID="worldlinco-chat-friend-folder-open"
                                            >
                                                <Text style={styles.socialHubIcon}>👥</Text>
                                                <Text style={styles.socialHubTitle}>친구</Text>
                                                <Text style={styles.socialHubMeta}>친구 목록과 보이스톡 대상을 확인합니다.</Text>
                                            </Pressable>
                                            <View style={styles.socialHubBtnPassive}>
                                                <Text style={styles.socialHubIcon}>🗺️</Text>
                                                <Text style={styles.socialHubTitle}>주변 친구 자동 감지</Text>
                                                <Text style={styles.socialHubMeta}>앱 사용자를 거리순으로 표시합니다. km 제한 없이 백그라운드에서 감지·알림합니다.</Text>
                                            </View>
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
                                </>
                            )
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
                        <Text style={styles.sectionTitle}>💬 채팅 중심 통역 허브</Text>
                        <Text style={styles.sectionSub}>기본 사용은 채팅/번역채팅으로 두고, 실시간 VoIP 통역 통화는 프리미엄 구독으로 분리합니다.</Text>
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
                                        testID="worldlinco-voip-incoming-accept"
                                        accessibilityLabel="수신 보이스톡 받기"
                                    >
                                        <Text style={styles.inlineActionBtnText}>받기</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.inlineGhostBtn}
                                        onPress={() => { void handleRejectIncomingVoipCall(); }}
                                        testID="worldlinco-voip-incoming-reject"
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
                                                        void refreshVoipAudit(voipAuditCallId, { showLoading: true, force: true });
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
                        <Text style={styles.sectionTitle}>🎵 노래 전용 모드</Text>
                        <Text style={styles.sectionSub}>{`가사 필터링 · 구간 반복 감지 · ${SUPPORTED_LANGUAGE_COUNT}개국 양방 가사번역 자막 · 음성/문자 기반 언어 자동 감지`}</Text>
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
                                <Text style={styles.sectionTitle}>📍 주변 검색</Text>
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
                                        <Pressable style={styles.inlineGhostBtn} onPress={() => { void handleOpenInterCallContactPicker(); }}>
                                            <Text style={styles.inlineGhostBtnText}>{interCallContactLoading ? '전화번호 저장소 여는 중...' : '전화번호 저장소 열기'}</Text>
                                        </Pressable>
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

            {showIncomingVoipFixedPanel && pendingIncomingVoipCall ? (
                <View style={styles.voipIncomingFixedPanel} pointerEvents="box-none">
                    <View style={styles.voipIncomingFixedCard}>
                        <Text style={styles.voipIncomingFixedTitle}>수신 보이스톡</Text>
                        <Text style={styles.voipIncomingFixedCaller} numberOfLines={2}>
                            {pendingIncomingVoipCall.caller_label || pendingIncomingVoipCall.display_label || pendingIncomingVoipCall.caller_voice_id || '상대방'}
                        </Text>
                        {voipInitError ? <Text style={styles.errorText}>{voipInitError}</Text> : null}
                        <View style={styles.voipIncomingFixedActions}>
                            <Pressable
                                style={styles.voipIncomingAcceptBtn}
                                onPressIn={() => {
                                    logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_IN', {
                                        source_variant: 'fixed_panel',
                                        pending_call_id: pendingIncomingVoipCall.call_id,
                                    });
                                }}
                                onPressOut={() => {
                                    logUiPressProbe('VOIP_INCOMING_ACCEPT_PRESS_OUT', {
                                        source_variant: 'fixed_panel',
                                        pending_call_id: pendingIncomingVoipCall.call_id,
                                    });
                                }}
                                onPress={() => handleIncomingAcceptPress('fixed_panel')}
                                accessibilityRole="button"
                                accessibilityLabel="수신 보이스톡 받기"
                                testID="worldlinco-voip-incoming-accept"
                            >
                                <Text style={styles.voipIncomingAcceptBtnText}>받기</Text>
                            </Pressable>
                            <Pressable
                                style={styles.voipIncomingRejectBtn}
                                onPress={() => { void handleRejectIncomingVoipCall(); }}
                                accessibilityRole="button"
                                accessibilityLabel="수신 보이스톡 거절"
                            >
                                <Text style={styles.voipIncomingRejectBtnText}>거절</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
            ) : null}

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

            <Modal visible={showLogin} transparent animationType="fade" onRequestClose={() => setShowLogin(false)}>
                <View style={styles.loginOverlay}>
                    <View style={styles.loginModal} accessibilityLabel="worldlinco-login-modal" testID="worldlinco-login-modal">
                        <Text style={styles.loginModalTitle}>{authModalMode === 'login' ? '🔐 로그인' : '🆕 회원가입'}</Text>
                        <Text style={styles.loginModeHint}>
                            {authModalMode === 'login'
                                ? '기존 계정으로 바로 로그인합니다.'
                                : signupStep === 'verify'
                                    ? `${signupMaskedTarget || loginEmail.trim()}으로 인증 코드를 보냈습니다. 6자리 코드 입력 후 가입이 완료됩니다.`
                                    : `이메일 또는 전화로 본인 확인 후 가입합니다. 프로필 ${getLangLabelText(signupPreferredLanguage)} / ${resolveCountryFlag(signupCountryCode)} ${signupCountryCode} 는 VoIP·채팅 통역 기준으로 저장됩니다.`}
                        </Text>
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
                                <TextInput
                                    style={styles.compactInput}
                                    placeholder="이메일"
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
                                <TextInput
                                    style={styles.compactInput}
                                    placeholder="비밀번호"
                                    placeholderTextColor={C.sub}
                                    secureTextEntry
                                    showSoftInputOnFocus
                                    accessibilityLabel="worldlinco-auth-password-input"
                                    testID="worldlinco-auth-password-input"
                                    value={loginPw}
                                    onFocus={handleLoginPasswordFocus}
                                    onBlur={() => { handleLoginFieldBlur('PASSWORD'); }}
                                    onChangeText={handleLoginPasswordChange}
                                />
                            </>
                        ) : null}
                        {loginError ? <Text style={styles.errorText}>{loginError}</Text> : null}
                        {authModalMode === 'login' ? (
                            <View style={styles.inlineAuthUtilityRow}>
                                <Pressable onPress={openPasswordRecovery} testID="worldlinco-auth-forgot-password-modal">
                                    <Text style={styles.authUtilityLinkText}>비밀번호 찾기</Text>
                                </Pressable>
                                {biometricLoginReady && biometricLoginEnabled ? (
                                    <Pressable onPress={() => { void handleBiometricLogin(); }} disabled={biometricLoginBusy} testID="worldlinco-auth-biometric-login-modal">
                                        <Text style={styles.authUtilityLinkText}>{biometricLoginBusy ? '지문 확인 중...' : '👆 지문 로그인'}</Text>
                                    </Pressable>
                                ) : null}
                            </View>
                        ) : null}
                        <Pressable
                            style={styles.authModeToggleBtn}
                            onPress={toggleAuthModalMode}
                            accessibilityLabel="worldlinco-modal-auth-mode-toggle"
                            testID="worldlinco-modal-auth-mode-toggle"
                        >
                            <Text style={styles.authModeToggleText}>
                                {authModalMode === 'login' ? '계정이 없으면 회원가입' : '이미 계정이 있으면 로그인'}
                            </Text>
                        </Pressable>
                        <View style={styles.modalActionRow}>
                            <Pressable
                                style={[styles.inlineActionBtn, demoSessionLoading && styles.inlineGhostBtnDisabled]}
                                onPress={() => { void handleStartInstantDemoSession('chat'); }}
                                disabled={demoSessionLoading || loginLoading}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-demo-session-start-button"
                                testID="worldlinco-demo-session-start-button"
                            >
                                <Text style={styles.inlineActionBtnText}>{demoSessionLoading ? '데모 연결 중...' : '데모 세션 시작'}</Text>
                            </Pressable>
                            <Pressable
                                style={[styles.translateBtn, loginLoading && styles.translateBtnDisabled, styles.modalMainBtn]}
                                onPress={authModalMode === 'login' ? handleLogin : handleSignupSubmit}
                                disabled={loginLoading}
                                accessibilityRole="button"
                                accessibilityLabel={authModalMode === 'login' ? 'worldlinco-auth-login-submit-button' : 'worldlinco-auth-signup-submit-button'}
                                testID={authModalMode === 'login' ? 'worldlinco-auth-login-submit-button' : 'worldlinco-auth-signup-submit-button'}
                            >
                                {loginLoading ? (
                                    <ActivityIndicator color="#fff" size="small" />
                                ) : (
                                    <Text style={styles.translateBtnText}>{signupSubmitLabel}</Text>
                                )}
                            </Pressable>
                            <Pressable
                                style={styles.modalCloseBtn}
                                onPress={() => {
                                    setAuthModalMode('login');
                                    setLoginError('');
                                    setShowLogin(false);
                                }}
                            >
                                <Text style={styles.logoutBtnText}>닫기</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
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
                        <Text style={styles.loginModalTitle}>📇 일반통화 연락처</Text>
                        <Text style={styles.loginModeHint}>기기 연락처에서 번호를 불러와 일반 통역 통화 입력칸에 바로 채웁니다.</Text>
                        {interCallContactError ? <Text style={styles.errorText}>{interCallContactError}</Text> : null}
                        <ScrollView style={styles.contactPickerList} contentContainerStyle={styles.contactPickerListBody}>
                            {(interCallContactOptions ?? []).map((contact) => (
                                <Pressable
                                    key={`inter-contact-${contact.id}`}
                                    style={styles.contactPickerRow}
                                    onPress={() => handleSelectInterCallContact(contact)}
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
                            <Pressable style={styles.inlineGhostBtn} onPress={() => { void handleOpenInterCallContactPicker(); }}>
                                <Text style={styles.inlineGhostBtnText}>{interCallContactLoading ? '새로고침 중...' : '다시 불러오기'}</Text>
                            </Pressable>
                            <Pressable style={styles.modalCloseBtn} onPress={() => setInterCallContactPickerVisible(false)}>
                                <Text style={styles.logoutBtnText}>닫기</Text>
                            </Pressable>
                        </View>
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
                onCompleted={(payload) => { void handlePasswordSecurityCompleted(payload); }}
            />

            <DataSourcesModal visible={showDataSources} onClose={() => setShowDataSources(false)} />
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: C.bg },
    scroll: { padding: 10, paddingBottom: 108 },
    lobbyShell: { gap: 14, marginBottom: 18 },
    lobbyHeroCard: {
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#2a4e70',
        borderRadius: 18,
        padding: 16,
        gap: 8,
    },
    lobbyHeroEyebrow: { color: '#8fd5ff', fontSize: 12, fontWeight: '800', textTransform: 'uppercase' },
    lobbyHeroTitle: { color: '#eef7ff', fontSize: 21, fontWeight: '900', lineHeight: 29 },
    lobbyHeroBody: { color: '#a9bfd4', fontSize: 13, lineHeight: 20 },
    lobbyPreviewGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
    lobbyPreviewCard: {
        width: '48%',
        minHeight: 108,
        backgroundColor: '#101a26',
        borderWidth: 1,
        borderColor: '#27405f',
        borderRadius: 14,
        padding: 10,
        gap: 4,
    },
    lobbyPreviewIcon: { fontSize: 18 },
    lobbyPreviewTitle: { color: '#eef7ff', fontSize: 13, fontWeight: '800' },
    lobbyPreviewBody: { color: '#9eb3c9', fontSize: 11, lineHeight: 16 },
    workspaceShell: { marginBottom: 12 },
    workspaceHeaderCard: {
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#34526f',
        borderRadius: 12,
        padding: 8,
        gap: 6,
    },
    workspaceHeaderTitle: { color: '#eef7ff', fontSize: 11, fontWeight: '900' },
    workspaceHeaderBody: { color: '#a9bfd4', fontSize: 8, lineHeight: 11 },
    workspaceRailGrid: { flexDirection: 'row', flexWrap: 'nowrap', gap: 4, justifyContent: 'space-between' },
    workspaceRailCard: {
        width: '19%',
        minHeight: 38,
        backgroundColor: '#111927',
        borderWidth: 1,
        borderColor: '#2a3a52',
        borderRadius: 10,
        paddingHorizontal: 4,
        paddingVertical: 5,
        gap: 2,
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    workspaceRailCardActive: { backgroundColor: '#163452', borderColor: '#58c9ff' },
    workspaceRailIcon: { fontSize: 8 },
    workspaceRailTitle: { color: '#eef7ff', fontSize: 7, fontWeight: '800', textAlign: 'center' },
    workspaceRailMeta: { color: '#9eb3c9', fontSize: 6, lineHeight: 7, textAlign: 'center' },
    translationHub: { position: 'relative', marginBottom: 14 },
    header: { alignItems: 'center', marginBottom: 14, paddingTop: 6 },
    title: { fontSize: 24, fontWeight: '800', color: '#58c9ff', letterSpacing: 0.3 },
    subtitle: { fontSize: 12, color: C.sub, marginTop: 2 },
    travelModeBanner: {
        marginBottom: 16,
        backgroundColor: '#101a26',
        borderWidth: 1,
        borderColor: '#2a4e70',
        borderRadius: 18,
        padding: 14,
        gap: 10,
    },
    travelModeTitle: { color: '#eaf6ff', fontSize: 16, fontWeight: '800' },
    travelModeBody: { color: '#a9bfd4', fontSize: 13, lineHeight: 19 },
    travelModeActionRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
    versionPillRow: { marginTop: 10, flexDirection: 'row', gap: 8, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' },
    versionPill: {
        backgroundColor: '#10263a',
        borderWidth: 1,
        borderColor: '#2c6ea6',
        borderRadius: 999,
        paddingHorizontal: 12,
        paddingVertical: 7,
    },
    versionPillText: { color: '#a9dbff', fontSize: 12, fontWeight: '800' },
    voipLaunchBtn: {
        backgroundColor: '#153020',
        borderWidth: 1,
        borderColor: '#2d6b43',
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 6,
    },
    voipLaunchBtnText: { color: '#dff7e7', fontSize: 11, fontWeight: '800' },
    badge: {
        marginTop: 8,
        backgroundColor: C.badge,
        paddingHorizontal: 10,
        paddingVertical: 3,
        borderRadius: 12,
    },
    badgeText: { fontSize: 12, color: C.sub },
    accountRow: {
        marginTop: 10,
        flexDirection: 'row',
        gap: 8,
    },
    inlineAuthPanel: {
        marginTop: 12,
        width: '100%',
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#27405f',
        borderRadius: 14,
        padding: 12,
    },
    inlineAuthHeaderRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 8,
        marginBottom: 6,
    },
    inlineAuthTitle: { color: '#eaf6ff', fontSize: 15, fontWeight: '800' },
    inlineAuthHint: { color: C.sub, fontSize: 12, lineHeight: 18, marginBottom: 10 },
    inlineAuthModeChip: {
        backgroundColor: '#152638',
        borderWidth: 1,
        borderColor: '#35506d',
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 6,
    },
    inlineAuthModeChipText: { color: '#8fd5ff', fontSize: 11, fontWeight: '700' },
    inlineAuthStatus: {
        color: '#79c0ff',
        fontSize: 12,
        lineHeight: 18,
        marginBottom: 8,
    },
    authDebugPanel: {
        width: '100%',
        marginTop: 10,
        padding: 10,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#5c4b18',
        backgroundColor: '#1f1a0c',
        gap: 3,
    },
    authDebugTitle: {
        color: '#ffd76b',
        fontSize: 11,
        fontWeight: '800',
    },
    authDebugLine: {
        color: '#f7e7b1',
        fontSize: 11,
        lineHeight: 16,
    },
    authDebugFloating: {
        position: 'absolute',
        top: 18,
        right: 16,
        width: 280,
        padding: 10,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#5c4b18',
        backgroundColor: 'rgba(31, 26, 12, 0.92)',
        zIndex: 30,
    },
    authDebugActionBtn: {
        marginTop: 8,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: '#9a7a1a',
        backgroundColor: '#35270a',
        paddingHorizontal: 10,
        paddingVertical: 9,
        alignItems: 'center',
    },
    authDebugActionBtnText: {
        color: '#ffe08c',
        fontSize: 12,
        fontWeight: '800',
    },
    inlineAuthActionRow: {
        flexDirection: 'row',
        gap: 8,
        flexWrap: 'wrap',
        alignItems: 'center',
    },
    inlineAuthUtilityRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 10,
        marginTop: 2,
    },
    authUtilityLinkText: {
        color: '#8fd5ff',
        fontSize: 12,
        fontWeight: '700',
    },
    myInfoActionRow: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
        marginTop: 8,
    },
    inlineAuthSubmitBtn: {
        flex: 1,
        minWidth: 120,
    },
    sectionRailDock: {
        position: 'absolute',
        left: 16,
        right: 16,
        bottom: 14,
        alignItems: 'center',
        gap: 8,
    },
    sectionRail: {
        backgroundColor: 'rgba(8, 12, 20, 0.92)',
        position: 'relative',
        borderWidth: 1,
        borderColor: '#263041',
        borderRadius: 18,
        paddingVertical: 8,
        paddingHorizontal: 10,
        gap: 10,
    },
    sectionRailBadge: {
        position: 'absolute',
        top: 6,
        right: 6,
        borderRadius: 999,
        backgroundColor: '#c2410c',
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderWidth: 1,
        borderColor: '#fdba74',
        zIndex: 2,
    },
    sectionRailBadgeText: { color: '#fff7ed', fontSize: 9, fontWeight: '900' },
    sectionRailToggleBtn: {
        minWidth: 118,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        backgroundColor: 'rgba(8, 12, 20, 0.96)',
        borderWidth: 1,
        borderColor: '#2f4d72',
        borderRadius: 999,
        paddingHorizontal: 14,
        paddingVertical: 9,
    },
    sectionRailToggleBtnActive: { borderColor: '#58c9ff', backgroundColor: '#10263a' },
    sectionRailToggleIcon: { color: '#dbeaff', fontSize: 13, fontWeight: '800' },
    sectionRailToggleText: { color: '#dbeaff', fontSize: 12, fontWeight: '800' },
    sectionRailBtn: {
        width: 54,
        minHeight: 50,
        borderRadius: 12,
        backgroundColor: '#121a27',
        borderWidth: 1,
        borderColor: '#2a3a52',
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 6,
        gap: 3,
    },
    sectionRailBtnActive: { backgroundColor: '#163452', borderColor: '#58c9ff' },
    sectionRailIcon: { fontSize: 15 },
    sectionRailLabel: { color: '#dbeaff', fontSize: 9, fontWeight: '700' },
    sectionCardActive: { borderColor: '#58c9ff', shadowColor: '#58c9ff', shadowOpacity: 0.18, shadowRadius: 12 },
    railOverlayScrim: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 10, 18, 0.44)',
        borderRadius: 22,
        paddingHorizontal: 14,
        paddingTop: 92,
        paddingBottom: 18,
        justifyContent: 'flex-start',
        alignItems: 'center',
    },
    railOverlayCard: {
        width: '92%',
        minHeight: 248,
        backgroundColor: 'rgba(15, 24, 37, 0.96)',
        borderWidth: 1,
        borderColor: '#3c5979',
        borderRadius: 20,
        paddingHorizontal: 16,
        paddingVertical: 16,
        gap: 10,
        shadowColor: '#000',
        shadowOpacity: 0.24,
        shadowRadius: 18,
        shadowOffset: { width: 0, height: 10 },
    },
    railOverlayHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
    railOverlayTitle: { color: '#eef7ff', fontSize: 18, fontWeight: '800', flex: 1 },
    railOverlayCloseBtn: {
        width: 52,
        height: 52,
        borderRadius: 26,
        backgroundColor: '#182434',
        borderWidth: 1,
        borderColor: '#35506d',
        alignItems: 'center',
        justifyContent: 'center',
    },
    railOverlayCloseText: { color: '#dbeaff', fontSize: 22, fontWeight: '800' },
    railOverlayBodyText: { color: '#a9bfd6', fontSize: 14, lineHeight: 22 },
    railOverlayActionRow: { flexDirection: 'row', gap: 10, flexWrap: 'wrap', marginTop: 4 },
    railOverlayActionBtn: {
        backgroundColor: '#1f7ae0',
        borderRadius: 12,
        paddingHorizontal: 14,
        paddingVertical: 10,
        minHeight: 44,
        alignItems: 'center',
        justifyContent: 'center',
    },
    railOverlayActionText: { color: '#f7fbff', fontSize: 13, fontWeight: '800' },
    railOverlayGhostBtn: {
        backgroundColor: '#182434',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#35506d',
        paddingHorizontal: 14,
        paddingVertical: 10,
        minHeight: 44,
        alignItems: 'center',
        justifyContent: 'center',
    },
    railOverlayGhostText: { color: '#dbeaff', fontSize: 13, fontWeight: '700' },
    socialHubRow: { flexDirection: 'row', gap: 12, marginTop: 8 },
    interCallQuickRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginTop: 8 },
    interCallHint: { color: '#8b949e', fontSize: 12, lineHeight: 18, marginTop: 6 },
    socialHubBtn: {
        flex: 1,
        minHeight: 112,
        borderRadius: 14,
        borderWidth: 1,
        borderColor: '#2a3a52',
        backgroundColor: '#111927',
        paddingHorizontal: 10,
        paddingVertical: 10,
        gap: 4,
    },
    socialHubBtnActive: { borderColor: '#58c9ff', backgroundColor: '#13283c' },
    socialHubIcon: { fontSize: 19 },
    socialHubTitle: { color: '#eef7ff', fontSize: 14, fontWeight: '800' },
    socialHubMeta: { color: '#9eb3c9', fontSize: 11, lineHeight: 16 },
    loginBtn: {
        backgroundColor: '#0d2a4a',
        borderWidth: 1,
        borderColor: '#2a7cff',
        borderRadius: 10,
        paddingHorizontal: 12,
        paddingVertical: 8,
    },
    loginBtnText: { color: '#79c0ff', fontWeight: '700', fontSize: 13 },
    myInfoBtn: {
        backgroundColor: '#153020',
        borderWidth: 1,
        borderColor: '#2d6b43',
        borderRadius: 10,
        paddingHorizontal: 10,
        paddingVertical: 8,
    },
    myInfoBtnText: { color: '#effff3', fontWeight: '700', fontSize: 12 },
    logoutBtn: {
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        paddingHorizontal: 10,
        paddingVertical: 8,
    },
    logoutBtnText: { color: C.sub, fontWeight: '700', fontSize: 12 },
    myInfoPanel: {
        marginTop: 10,
        width: '100%',
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
    },
    myInfoTitle: { color: '#f8fbff', fontWeight: '800', marginBottom: 6 },
    myInfoText: { color: C.sub, fontSize: 12, marginBottom: 4 },
    purchaseListWrap: {
        marginTop: 8,
        backgroundColor: '#0d1117',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: C.border,
        padding: 8,
        gap: 4,
    },
    purchaseItemText: { color: C.sub, fontSize: 12 },
    labelRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 },
    label: { fontSize: 12, color: C.sub, marginBottom: 8 },
    gpsStatusText: { color: '#79c0ff', fontSize: 12, marginTop: 2, marginBottom: 8 },
    gpsBtn: {
        backgroundColor: '#0d2a4a',
        borderWidth: 1,
        borderColor: '#35506c',
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 6,
    },
    gpsBtnText: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
    gpsAutoBadge: { color: '#79c0ff', fontSize: 11, fontWeight: '700' },
    langAutoChip: {
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        paddingHorizontal: 10,
        paddingVertical: 9,
        marginBottom: 4,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    langAutoChipValue: { color: C.text, fontSize: 13, fontWeight: '700' },
    langAutoChipHint: { color: '#6ee7b7', fontSize: 11, fontWeight: '700' },
    autoVoiceModeStatus: { color: C.sub, fontSize: 12, lineHeight: 18 },
    socialHubBtnPassive: {
        flex: 1,
        backgroundColor: '#101826',
        borderWidth: 1,
        borderColor: '#2a3444',
        borderRadius: 12,
        padding: 12,
        minHeight: 92,
    },
    langPickerValue: { color: C.text, fontSize: 13, fontWeight: '700' },
    langPickerHint: { color: C.sub, fontSize: 11 },
    langModalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        justifyContent: 'center',
        paddingHorizontal: 20,
    },
    langModalCard: {
        backgroundColor: '#111927',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: C.border,
        padding: 12,
        maxHeight: '78%',
    },
    langModalTitle: { color: '#f8fbff', fontSize: 16, fontWeight: '800', marginBottom: 10 },
    langModalList: { maxHeight: 380 },
    langModalOption: {
        paddingVertical: 11,
        paddingHorizontal: 10,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: C.border,
        marginBottom: 8,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#0f1623',
    },
    langModalOptionActive: {
        borderColor: C.accent,
        backgroundColor: '#16253a',
    },
    langModalOptionText: { color: C.text, fontSize: 14 },
    langModalOptionTextActive: { color: '#79c0ff', fontWeight: '800' },
    langModalCheck: { color: '#79c0ff', fontWeight: '800', fontSize: 16 },
    langModalCloseBtn: {
        alignSelf: 'flex-end',
        marginTop: 6,
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 8,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
    },
    langModalCloseText: { color: C.sub, fontWeight: '700' },
    inputBox: {
        backgroundColor: C.surface,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: C.border,
        padding: 10,
        marginTop: 6,
        minHeight: 96,
    },
    resultBox: { minHeight: 96 },
    resultActionRow: { marginTop: 8, flexDirection: 'row', justifyContent: 'flex-end' },
    ocrCard: {
        marginTop: 12,
        backgroundColor: '#0f1623',
        borderRadius: 10,
        borderWidth: 1,
        borderColor: C.border,
        padding: 12,
        gap: 8,
    },
    ocrTitle: { color: '#f8fbff', fontSize: 15, fontWeight: '800' },
    ocrSubtitle: { color: C.sub, fontSize: 12, lineHeight: 18 },
    ocrPreviewBox: {
        marginTop: 4,
        backgroundColor: '#101b2c',
        borderWidth: 1,
        borderColor: '#27405f',
        borderRadius: 8,
        padding: 10,
        gap: 6,
    },
    textInput: { flex: 1, color: C.text, fontSize: 14, minHeight: 68, textAlignVertical: 'top' },
    resultText: { color: C.text, fontSize: 14 },
    resultPlaceholder: { color: C.sub, fontSize: 14 },
    speakBtn: { alignSelf: 'flex-end', marginTop: 6 },
    speakIcon: { fontSize: 20 },
    inputBtnRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 },
    voiceMicBtn: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, backgroundColor: C.badge },
    voiceMicBtnActive: { backgroundColor: '#7c1d1d' },
    actionRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
    swapBtn: {
        flex: 1,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        paddingVertical: 10,
        alignItems: 'center',
    },
    swapText: { color: C.sub, fontSize: 12, fontWeight: '600' },
    translateBtn: {
        flex: 2,
        backgroundColor: C.green,
        borderRadius: 10,
        paddingVertical: 10,
        alignItems: 'center',
    },
    translateBtnDisabled: { opacity: 0.6 },
    translateBtnText: { color: '#fff', fontSize: 14, fontWeight: '800' },
    offlineBanner: {
        backgroundColor: '#2a1a00',
        borderRadius: 8,
        padding: 10,
        marginTop: 10,
        borderWidth: 1,
        borderColor: '#5a3a00',
    },
    offlineText: { color: '#f0b050', fontSize: 12 },
    sectionCard: {
        marginTop: 12,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
    },
    voipRailWorkspaceCard: {
        marginTop: 10,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#27405f',
        borderRadius: 12,
        padding: 10,
        gap: 6,
    },
    voipIncomingBanner: {
        marginTop: 14,
        backgroundColor: '#102033',
        borderWidth: 1,
        borderColor: '#3a6a93',
        borderRadius: 14,
        padding: 14,
        gap: 8,
    },
    voipActiveCallBanner: {
        marginTop: 14,
        backgroundColor: '#112616',
        borderWidth: 1,
        borderColor: '#2f7d46',
        borderRadius: 14,
        padding: 14,
        gap: 8,
    },
    voipIncomingBannerHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 10,
        flexWrap: 'wrap',
    },
    voipIncomingBannerTitle: { color: '#f8fbff', fontSize: 16, fontWeight: '900' },
    voipIncomingBannerBody: { color: '#dbeaff', fontSize: 12, lineHeight: 18 },
    voipIncomingBannerMetaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    voipIncomingBannerMeta: { color: '#9fc3e6', fontSize: 11, fontWeight: '700' },
    voipIncomingFixedPanel: {
        position: 'absolute',
        top: 70,
        left: 14,
        right: 14,
        zIndex: 80,
        elevation: 20,
    },
    voipIncomingFixedCard: {
        backgroundColor: '#102033',
        borderWidth: 2,
        borderColor: '#58c9ff',
        borderRadius: 12,
        padding: 14,
        gap: 8,
        shadowColor: '#000',
        shadowOpacity: 0.35,
        shadowRadius: 14,
        shadowOffset: { width: 0, height: 6 },
    },
    voipIncomingFixedTitle: { color: '#f8fbff', fontSize: 18, fontWeight: '900' },
    voipIncomingFixedCaller: { color: '#dbeaff', fontSize: 14, fontWeight: '700', lineHeight: 20 },
    voipIncomingFixedActions: { flexDirection: 'row', gap: 10 },
    voipIncomingAcceptBtn: {
        flex: 1,
        backgroundColor: '#1d7f45',
        borderRadius: 10,
        paddingVertical: 13,
        alignItems: 'center',
    },
    voipIncomingRejectBtn: {
        flex: 1,
        backgroundColor: '#3f1f1f',
        borderRadius: 10,
        paddingVertical: 13,
        alignItems: 'center',
    },
    voipIncomingAcceptBtnText: { color: '#eafff1', fontSize: 16, fontWeight: '900' },
    voipIncomingRejectBtnText: { color: '#fecaca', fontSize: 16, fontWeight: '900' },
    voipIncomingRailCard: {
        marginTop: 12,
        backgroundColor: '#0f1d30',
        borderWidth: 1,
        borderColor: '#3b658d',
        borderRadius: 14,
        padding: 14,
        gap: 8,
    },
    voipRailLiveScreenWrap: {
        marginTop: 10,
        backgroundColor: '#0b1320',
        borderWidth: 1,
        borderColor: '#2a415e',
        borderRadius: 14,
        padding: 8,
        gap: 6,
        overflow: 'hidden',
        minHeight: 500,
    },
    voipPersistentCallHiddenHost: {
        height: 1,
        opacity: 0.01,
        overflow: 'hidden',
        marginTop: 0,
    },
    voipPersistentCallHiddenScreenWrap: {
        height: 1,
        overflow: 'hidden',
    },
    sectionTitle: { color: '#f8fbff', fontSize: 15, fontWeight: '800' },
    sectionSub: { color: C.sub, fontSize: 11, marginTop: 3, marginBottom: 8, lineHeight: 16 },
    voipQuickMetaRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
    voipQuickMetaText: { color: '#91f2b3', fontSize: 12, fontWeight: '700' },
    voipLocalLangCard: {
        borderRadius: 14,
        borderWidth: 1,
        borderColor: '#2c4a6b',
        backgroundColor: '#0c1626',
        padding: 12,
        marginBottom: 10,
        gap: 6,
    },
    voipLocalLangTitle: { color: '#f1f7ff', fontSize: 14, fontWeight: '800' },
    voipLocalLangSub: { color: '#89a2c1', fontSize: 11, lineHeight: 16 },
    voipLocalLangTrigger: {
        minHeight: 54,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#31445f',
        backgroundColor: '#0d1623',
        paddingHorizontal: 14,
        paddingVertical: 10,
        marginTop: 4,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
    },
    voipLocalLangValue: { color: '#f8fbff', fontSize: 15, fontWeight: '800' },
    voipLocalLangMeta: { color: '#89a2c1', fontSize: 11, marginTop: 4 },
    voipLocalLangHint: { color: '#58c9ff', fontSize: 13, fontWeight: '800' },
    voipLocalLangResetBtn: { alignSelf: 'flex-start', paddingVertical: 4 },
    voipLocalLangResetText: { color: '#ffb38a', fontSize: 12, fontWeight: '700' },
    premiumHubRow: { gap: 10 },
    monetizationCard: {
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#27405f',
        borderRadius: 14,
        padding: 14,
        gap: 8,
        marginBottom: 10,
    },
    monetizationCardPrimary: {
        borderColor: '#2d8cff',
        backgroundColor: '#101b2c',
    },
    connectionStateCard: {
        borderColor: '#365777',
        backgroundColor: '#0d1726',
    },
    connectionStateTitle: {
        color: '#f5fbff',
        fontSize: 16,
        fontWeight: '800',
    },
    connectionStateBody: {
        color: '#bfd6ea',
        fontSize: 13,
        lineHeight: 20,
    },
    connectionStateHeaderRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 8,
    },
    connectionStateBadge: {
        color: '#ffd28f',
        backgroundColor: '#3b2c12',
        borderWidth: 1,
        borderColor: '#7c5b22',
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 5,
        overflow: 'hidden',
        fontSize: 11,
        fontWeight: '800',
    },
    connectionStateBadgeReady: {
        color: '#9be8b3',
        backgroundColor: '#14301d',
        borderColor: '#2d6b43',
    },
    connectionStateBulletList: {
        gap: 4,
    },
    connectionStateBullet: {
        color: '#d7e7f7',
        fontSize: 12,
        lineHeight: 18,
    },
    connectionStateActionRow: {
        flexDirection: 'row',
        gap: 8,
        flexWrap: 'wrap',
        alignItems: 'center',
    },
    monetizationBadge: {
        alignSelf: 'flex-start',
        backgroundColor: '#183453',
        color: '#d8ecff',
        fontSize: 11,
        fontWeight: '800',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 999,
        overflow: 'hidden',
    },
    monetizationTitle: { color: '#f8fbff', fontSize: 18, fontWeight: '800' },
    monetizationBody: { color: '#b3c6db', fontSize: 13, lineHeight: 20 },
    monetizationMetricRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
    monetizationMetric: {
        color: '#9be7b0',
        fontSize: 12,
        fontWeight: '700',
    },
    planGrid: { gap: 10 },
    planCard: {
        backgroundColor: '#111927',
        borderWidth: 1,
        borderColor: '#31465f',
        borderRadius: 12,
        padding: 12,
        gap: 6,
    },
    planCardOwned: {
        borderColor: '#2dd4bf',
        backgroundColor: '#0f2a29',
    },
    planTitle: { color: '#eef7ff', fontSize: 15, fontWeight: '800' },
    planPrice: { color: '#91f2b3', fontSize: 14, fontWeight: '800' },
    planUsage: { color: '#dbeaff', fontSize: 12, lineHeight: 18 },
    planFormula: { color: '#8fb2d1', fontSize: 11, lineHeight: 17 },
    premiumStatusText: {
        color: '#79c0ff',
        fontSize: 12,
        lineHeight: 18,
        marginBottom: 8,
    },
    songPayCard: {
        borderColor: '#4b6b2e',
        backgroundColor: '#151d14',
    },
    songModeActionRow: { flexDirection: 'row', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    inlineGhostBtn: {
        paddingHorizontal: 12,
        paddingVertical: 10,
        borderRadius: 10,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
    },
    inlineGhostBtnDisabled: { opacity: 0.55 },
    inlineGhostBtnText: { color: C.sub, fontWeight: '700', fontSize: 12 },
    songModeMetaText: { color: C.sub, fontSize: 12, lineHeight: 18, marginBottom: 4 },
    songModeStatusText: {
        marginTop: 4,
        marginBottom: 8,
        color: '#79c0ff',
        fontSize: 12,
        lineHeight: 18,
    },
    songSubtitleWrap: {
        marginTop: 6,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
        gap: 8,
    },
    songSubtitlePlaceholder: { color: C.sub, fontSize: 12, lineHeight: 18 },
    songSubtitleItem: {
        backgroundColor: '#131d2c',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#22344f',
        padding: 10,
        gap: 4,
    },
    songSubtitleOriginal: { color: '#f8fbff', fontSize: 14, fontWeight: '700' },
    songSubtitleTranslated: { color: '#91f2b3', fontSize: 14, lineHeight: 20 },
    songSubtitleMeta: { color: '#79c0ff', fontSize: 11 },
    songFileJobBox: {
        marginTop: 8,
        marginBottom: 8,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#22344f',
        borderRadius: 10,
        padding: 10,
        gap: 8,
    },
    songFileJobHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
    songFileNameText: { color: '#f8fbff', fontSize: 13, fontWeight: '800', flex: 1 },
    songFileProgressText: { color: '#91f2b3', fontSize: 12, fontWeight: '800' },
    songFileProgressTrack: { height: 6, borderRadius: 999, backgroundColor: '#1b2940', overflow: 'hidden' },
    songFileProgressFill: { height: 6, borderRadius: 999, backgroundColor: '#2dd4bf' },
    songFileControlRow: { flexDirection: 'row', alignItems: 'center', gap: 10, flexWrap: 'wrap' },
    voicePreviewPanel: {
        marginTop: 8,
        marginBottom: 8,
        backgroundColor: '#0b1422',
        borderWidth: 1,
        borderColor: '#2a415e',
        borderRadius: 10,
        padding: 10,
        gap: 8,
    },
    voicePreviewHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
    voiceAckRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 9,
    },
    voiceAckMark: {
        width: 20,
        height: 20,
        borderRadius: 4,
        borderWidth: 1,
        borderColor: '#79c0ff',
        color: '#91f2b3',
        textAlign: 'center',
        lineHeight: 18,
        fontWeight: '800',
    },
    voiceAckText: { color: C.sub, fontSize: 12, lineHeight: 17, flex: 1 },
    voicePreviewResultBox: {
        backgroundColor: '#101b2c',
        borderWidth: 1,
        borderColor: '#27405f',
        borderRadius: 8,
        padding: 8,
        gap: 6,
    },
    songFileTimelineWrap: {
        marginTop: 8,
        marginBottom: 8,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
        gap: 8,
    },
    songFileTimelineTitle: { color: '#f8fbff', fontSize: 14, fontWeight: '800' },
    songFileExportRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
    songFileExportBtn: {
        paddingHorizontal: 10,
        paddingVertical: 7,
        borderRadius: 8,
        backgroundColor: '#132033',
        borderWidth: 1,
        borderColor: '#27405f',
    },
    songFileExportText: { color: '#91f2b3', fontSize: 11, fontWeight: '800' },
    songFileSegmentItem: {
        backgroundColor: '#131d2c',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#22344f',
        padding: 10,
        gap: 6,
    },
    songFileSegmentItemActive: { borderColor: '#91f2b3', backgroundColor: '#13251d' },
    songFileSegmentInput: {
        minHeight: 52,
        backgroundColor: '#0b1220',
        borderWidth: 1,
        borderColor: '#27405f',
        color: '#91f2b3',
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 8,
        fontSize: 14,
        lineHeight: 20,
        textAlignVertical: 'top',
    },
    songFileSegmentFooter: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
    songFileSaveBtn: {
        paddingHorizontal: 10,
        paddingVertical: 7,
        borderRadius: 8,
        backgroundColor: '#123524',
        borderWidth: 1,
        borderColor: '#1f6f48',
    },
    songFileSaveText: { color: '#91f2b3', fontSize: 11, fontWeight: '800' },
    songFileExportPreview: {
        color: C.sub,
        fontSize: 11,
        lineHeight: 16,
        backgroundColor: '#0b1220',
        borderRadius: 8,
        padding: 10,
    },
    coordRow: { flexDirection: 'row', gap: 10 },
    coordField: { flex: 1 },
    coordLabel: { color: C.sub, fontSize: 11, marginBottom: 5 },
    compactInput: {
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        color: C.text,
        borderRadius: 10,
        paddingHorizontal: 9,
        paddingVertical: 7,
        marginBottom: 8,
        fontSize: 12,
    },
    noteInput: { minHeight: 64, textAlignVertical: 'top' },
    railRow: { gap: 8, paddingRight: 8, marginBottom: 8 },
    railBtn: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 20,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
    },
    railBtnActive: { backgroundColor: '#2a7cff', borderColor: '#2a7cff' },
    railBtnText: { color: C.sub, fontSize: 13, fontWeight: '600' },
    railBtnTextActive: { color: '#fff' },
    bookingSelectionBanner: {
        marginTop: 8,
        backgroundColor: '#102416',
        borderWidth: 1,
        borderColor: '#215c36',
        borderRadius: 10,
        paddingHorizontal: 10,
        paddingVertical: 8,
        gap: 4,
    },
    bookingSelectionBannerTitle: { color: '#9be8b3', fontSize: 11, fontWeight: '800' },
    bookingSelectionBannerPlace: { color: '#dff7e7', fontSize: 13, fontWeight: '800' },
    bookingSelectionBannerMeta: { color: '#b9d9c5', fontSize: 11, lineHeight: 15 },
    bookingSelectionBannerStatic: { color: '#b8f1c2', fontSize: 12, fontWeight: '800', marginTop: 2 },
    bookingSelectionBannerNotice: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
    nearbyMapWrap: {
        marginTop: 8,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        overflow: 'hidden',
    },
    nearbyMapHeaderRow: {
        paddingHorizontal: 12,
        paddingTop: 10,
        paddingBottom: 8,
        gap: 3,
        backgroundColor: '#0b1320',
        borderBottomWidth: 1,
        borderBottomColor: C.border,
    },
    nearbyMapTitle: { color: '#e6edf3', fontWeight: '800', fontSize: 13 },
    nearbyMapSubtitle: { color: '#79c0ff', fontSize: 12 },
    nearbyMapWebView: {
        height: 140,
        backgroundColor: '#08111b',
    },
    nearbyListWrap: { marginTop: 6, gap: 8 },
    placeItem: {
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 8,
    },
    placeItemActive: { borderColor: '#58c9ff', backgroundColor: '#0f1d2c' },
    placeName: { color: '#e6edf3', fontWeight: '800', fontSize: 13 },
    placeMeta: { color: '#79c0ff', fontSize: 11, marginTop: 3 },
    placeAddr: { color: C.sub, fontSize: 11, marginTop: 3, lineHeight: 15 },
    placeActionRow: { flexDirection: 'row', gap: 6, marginTop: 6 },
    inlineActionBtn: {
        backgroundColor: '#0d2a4a',
        borderWidth: 1,
        borderColor: '#35506c',
        borderRadius: 8,
        paddingHorizontal: 8,
        paddingVertical: 6,
    },
    inlineActionBtnActive: { backgroundColor: '#153020', borderColor: '#2d6b43' },
    inlineActionBtnText: { color: '#79c0ff', fontSize: 11, fontWeight: '700' },
    inlineActionBtnTextActive: { color: '#9be8b3' },
    autoVoiceModeWrap: { marginBottom: 10, gap: 6 },
    hotelRailBtn: {
        width: 170,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
    },
    hotelRailBtnActive: { borderColor: '#31c45d', backgroundColor: '#12261a' },
    hotelRailName: { color: '#e6edf3', fontWeight: '800', fontSize: 13 },
    hotelRailMeta: { color: '#8b949e', fontSize: 11, marginTop: 4 },
    selectedHotelBox: {
        backgroundColor: '#102416',
        borderWidth: 1,
        borderColor: '#215c36',
        borderRadius: 10,
        padding: 10,
        marginBottom: 10,
    },
    selectedHotelName: { color: '#dff7e7', fontWeight: '800', marginBottom: 4 },
    selectedHotelStatic: { color: '#b8f1c2', fontSize: 12, fontWeight: '800', marginTop: 2 },
    selectedHotelNotice: { color: '#79c0ff', fontSize: 12, fontWeight: '700', marginTop: 6, marginBottom: 6 },
    successBox: {
        marginTop: 10,
        backgroundColor: '#102416',
        borderWidth: 1,
        borderColor: '#215c36',
        borderRadius: 10,
        padding: 10,
        gap: 6,
    },
    successTitle: { color: '#9be8b3', fontWeight: '800', fontSize: 13 },
    successText: { color: '#dff7e7', fontSize: 12, lineHeight: 17 },
    errorText: {
        marginTop: 8,
        backgroundColor: '#2a1616',
        borderWidth: 1,
        borderColor: '#5e2727',
        borderRadius: 8,
        color: '#ffb4b4',
        paddingHorizontal: 10,
        paddingVertical: 8,
        fontSize: 12,
    },
    interToggleBtn: {
        backgroundColor: '#0d2a4a',
        borderWidth: 1,
        borderColor: '#35506c',
        borderRadius: 10,
        paddingVertical: 12,
        alignItems: 'center',
    },
    interToggleBtnActive: {
        backgroundColor: '#3a1020',
        borderColor: '#c43131',
    },
    interToggleText: { color: '#79c0ff', fontWeight: '800', fontSize: 15 },
    interToggleTextActive: { color: '#ffb4b4' },
    faceConversationToggleBtn: {
        backgroundColor: '#0d2a4a',
        borderWidth: 1,
        borderColor: '#35506c',
        borderRadius: 10,
        paddingVertical: 12,
        alignItems: 'center',
        marginBottom: 10,
    },
    faceConversationToggleBtnActive: {
        backgroundColor: '#12261a',
        borderColor: '#31c45d',
    },
    faceConversationToggleText: { color: '#79c0ff', fontWeight: '800', fontSize: 15 },
    faceConversationToggleTextActive: { color: '#9be8b3' },
    faceVadHintText: { marginTop: 8, marginBottom: 4, color: '#8b949e', fontSize: 12, lineHeight: 18 },
    faceAiModeRow: { flexDirection: 'row', gap: 8, marginBottom: 10 },
    faceAiModeBtn: {
        flex: 1,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: '#35506c',
        borderRadius: 10,
        paddingVertical: 10,
        alignItems: 'center',
    },
    faceAiModeBtnActive: { borderColor: '#58c9ff', backgroundColor: '#102233' },
    faceAiModeText: { color: '#8b949e', fontWeight: '800', fontSize: 14 },
    faceAiModeTextActive: { color: '#9ad8ff' },
    interPanel: {
        marginTop: 10,
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
    },
    interStatus: {
        color: '#79c0ff',
        fontSize: 13,
        marginBottom: 8,
    },
    loginOverlay: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: '#0009',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 16,
    },
    loginModal: {
        width: '100%',
        maxWidth: 420,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 14,
        padding: 14,
    },
    shareTargetModal: {
        width: '88%',
        maxWidth: 400,
        backgroundColor: '#0f1724',
        borderRadius: 22,
        padding: 18,
        borderWidth: 1,
        borderColor: '#21486a',
        gap: 12,
    },
    shareTargetHint: { color: C.sub, fontSize: 13, lineHeight: 19 },
    shareTargetList: { gap: 10 },
    shareTargetBadgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
    shareTargetCard: {
        gap: 4,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: '#28425f',
        backgroundColor: '#111b28',
        padding: 14,
    },
    shareTargetTitle: { color: '#f8fbff', fontSize: 14, fontWeight: '800' },
    shareTargetMeta: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
    shareTargetPreview: { color: '#c9d1d9', fontSize: 12, lineHeight: 18 },
    mediaMetaCard: {
        flexDirection: 'row',
        gap: 12,
        alignItems: 'center',
        marginTop: 8,
        marginBottom: 8,
        padding: 12,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: '#243244',
        backgroundColor: '#0f1723',
    },
    mediaThumbBox: {
        width: 64,
        height: 64,
        borderRadius: 14,
        backgroundColor: '#10263a',
        borderWidth: 1,
        borderColor: '#2f4d72',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
    },
    mediaThumbEmoji: { fontSize: 24 },
    mediaThumbCaption: { color: '#dbeaff', fontSize: 10, fontWeight: '800' },
    mediaMetaBody: { flex: 1, gap: 6 },
    mediaMetaTitle: { color: '#f8fbff', fontSize: 13, fontWeight: '800' },
    mediaBadgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
    mediaBadge: {
        borderRadius: 999,
        backgroundColor: '#17324d',
        paddingHorizontal: 10,
        paddingVertical: 5,
    },
    mediaBadgeText: { color: '#79c0ff', fontSize: 11, fontWeight: '800' },
    loginModalTitle: { color: '#58c9ff', fontSize: 17, fontWeight: '800', marginBottom: 10 },
    loginModeHint: { color: C.sub, fontSize: 12, lineHeight: 18, marginBottom: 10 },
    signupProfileLabel: { color: '#dbeaff', fontSize: 12, fontWeight: '800', marginBottom: 6 },
    signupChannelRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
    signupChannelBtn: {
        flex: 1,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#3a4560',
        backgroundColor: '#151822',
        paddingVertical: 10,
        alignItems: 'center',
    },
    signupChannelBtnActive: {
        borderColor: '#4a8cff',
        backgroundColor: '#1a2840',
    },
    signupChannelBtnText: { color: '#dbeaff', fontSize: 12, fontWeight: '700' },
    signupPickerTrigger: {
        minHeight: 58,
        borderRadius: 14,
        borderWidth: 1,
        borderColor: '#31445f',
        backgroundColor: '#0d1623',
        paddingHorizontal: 14,
        paddingVertical: 12,
        marginBottom: 10,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
    },
    signupPickerValue: { color: '#f8fbff', fontSize: 14, fontWeight: '800' },
    signupPickerMeta: { color: '#89a2c1', fontSize: 11, marginTop: 4 },
    signupPickerHint: { color: '#58c9ff', fontSize: 12, fontWeight: '800' },
    signupModalSub: { color: '#89a2c1', fontSize: 12, lineHeight: 18, marginTop: -4, marginBottom: 12 },
    signupProfileHint: { color: '#9fb0c8', fontSize: 12, lineHeight: 18, marginTop: -2, marginBottom: 8 },
    authModeToggleBtn: {
        alignSelf: 'flex-start',
        marginTop: 2,
        marginBottom: 4,
        paddingVertical: 6,
    },
    authModeToggleText: { color: '#8fd5ff', fontSize: 13, fontWeight: '700' },
    modalActionRow: { flexDirection: 'row', gap: 8, marginTop: 6 },
    contactPickerList: { maxHeight: 320, marginTop: 8 },
    contactPickerListBody: { gap: 8, paddingBottom: 4 },
    contactPickerRow: {
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#28405d',
        backgroundColor: '#111a28',
        paddingHorizontal: 12,
        paddingVertical: 12,
        gap: 4,
    },
    contactPickerName: { color: '#eef7ff', fontSize: 14, fontWeight: '800' },
    contactPickerMeta: { color: '#9fb8d1', fontSize: 12 },
    contactPickerEmpty: { color: '#8b949e', fontSize: 12, paddingVertical: 12 },
    modalMainBtn: { flex: 1 },
    modalCloseBtn: {
        flex: 1,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        justifyContent: 'center',
        alignItems: 'center',
    },
    voipModalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(4, 8, 16, 0.92)',
        padding: 12,
        justifyContent: 'center',
    },
    voipModalCard: {
        flex: 1,
        borderRadius: 18,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: '#2a415e',
        backgroundColor: '#0b1320',
    },
    voipModalScreenWrap: { flex: 1, minHeight: 520 },
    voipLobbyWrap: { flex: 1 },
    voipLobbyScroll: { flex: 1 },
    voipLobbyBody: { paddingHorizontal: 18, paddingBottom: 22 },
    voipProfileCard: {
        borderWidth: 1,
        borderColor: '#2a415e',
        backgroundColor: '#101a2a',
        borderRadius: 14,
        padding: 16,
        marginBottom: 14,
    },
    voipProfileTitle: { color: '#f8fbff', fontSize: 22, fontWeight: '900', marginBottom: 10 },
    voipProfileMeta: { color: '#dbeaff', fontSize: 14, lineHeight: 22, marginBottom: 4 },
    voipLobbySectionLabel: { color: '#9fb0c8', fontSize: 12, fontWeight: '800', marginBottom: 8 },
    voipGenderRow: { flexDirection: 'row', gap: 8, marginBottom: 14 },
    voipGenderChip: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 999,
        borderWidth: 1,
        borderColor: '#28415c',
        backgroundColor: '#101a2a',
    },
    voipGenderChipActive: { borderColor: '#58c9ff', backgroundColor: '#13304b' },
    voipGenderChipText: { color: '#dbeaff', fontSize: 12, fontWeight: '700' },
    voipGenderChipTextActive: { color: '#f8fbff' },
    voipLobbyActionRow: { flexDirection: 'row', gap: 10, flexWrap: 'wrap', marginTop: 8 },
    voipLobbyLoading: { marginTop: 8 },
    voipLobbyModeText: { color: '#9fb0c8', fontSize: 12, fontWeight: '700', marginTop: 6, marginBottom: 12 },
    voipLobbyFlowHint: { color: '#c9d1d9', fontSize: 12, lineHeight: 18, marginBottom: 8 },
    voipLobbyPstnHint: { color: '#9fb0c8', fontSize: 12, lineHeight: 18, maxWidth: 560 },
    voipAuditCard: {
        marginTop: 16,
        borderWidth: 1,
        borderColor: '#2a415e',
        backgroundColor: '#101a2a',
        borderRadius: 14,
        padding: 14,
        gap: 8,
    },
    voipAuditHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
    voipAuditTitle: { color: '#f8fbff', fontSize: 15, fontWeight: '800' },
    voipAuditHint: { color: '#9fb0c8', fontSize: 11, lineHeight: 16 },
    voipAuditEventRow: {
        backgroundColor: '#0b1320',
        borderWidth: 1,
        borderColor: '#22344f',
        borderRadius: 10,
        paddingHorizontal: 10,
        paddingVertical: 8,
        gap: 3,
    },
    voipAuditEventTitle: { color: '#dbeaff', fontSize: 12, fontWeight: '800' },
    voipAuditEventMeta: { color: '#9fb0c8', fontSize: 11, lineHeight: 16 },
    voipAuditEmptyText: { color: '#9fb0c8', fontSize: 12, lineHeight: 18 },
    voipModalTitle: { color: '#f8fbff', fontSize: 20, fontWeight: '900', marginBottom: 8 },
    voipModalSub: { color: C.sub, fontSize: 13, lineHeight: 18, marginBottom: 12 },
    footer: { marginTop: 30, alignItems: 'center' },
    footerText: { color: C.sub, fontSize: 11, textAlign: 'center', lineHeight: 18 },
    dataSourcesLink: { marginTop: 8, paddingVertical: 4, paddingHorizontal: 8 },
    dataSourcesLinkText: { color: '#79c0ff', fontSize: 12, fontWeight: '700', textDecorationLine: 'underline' },
    modalCloseRow: { flexDirection: 'row', justifyContent: 'flex-end', padding: 10 },
    friendModalCloseBtn: { paddingHorizontal: 12, paddingVertical: 6, backgroundColor: '#1e2533', borderRadius: 8 },
    friendModalCloseBtnText: { color: '#94a3b8', fontSize: 13 },
    friendModalBody: { flex: 1, minHeight: 0 },
});
