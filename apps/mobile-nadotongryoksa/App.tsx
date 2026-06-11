import * as Speech from 'expo-speech';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import Constants from 'expo-constants';
import { StatusBar } from 'expo-status-bar';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    Animated,
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
    View,
} from 'react-native';
import { translateText } from './src/api/translate';
import { CallModeEntryCard } from './src/features/call-mode/CallModeEntryCard';
import { CallModePolicyBanner } from './src/features/call-mode/CallModePolicyBanner';
import { useCallModeController } from './src/features/call-mode/useCallModeController';
import { usePstnAssistController } from './src/features/pstn-assist/usePstnAssistController';
import { useVoipAutoController } from './src/features/voip-auto/useVoipAutoController';
import { VoIPCallScreen } from './src/screens/VoIPCallScreen';
import { PhoneDialer } from './src/components/PhoneDialer';
import { CallInitResponse } from './src/services/voipCallClient';
import { usePermissionCheck } from './src/hooks/usePermissionCheck';
import { FriendFolderScreen } from './src/features/friends/FriendFolderScreen';

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
    naver_map_url: string;
};

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

type UserInfo = {
    id: number;
    email: string;
    username?: string;
};

const API_BASE: string =
    (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
    'http://10.0.2.2:8000';

const APP_VERSION_LABEL = `v${Constants.expoConfig?.version ?? '1.0.6'} · build ${String(Constants.nativeBuildVersion ?? Constants.expoConfig?.android?.versionCode ?? '7')}`;
const VERSION_CHECK_KEY = 'app_latest_version_check';
const VERSION_IGNORE_KEY = 'app_version_ignore';
const VOIP_TEST_DEFAULT_PHONE = '+82-1577-2600';

const CATEGORY_OPTIONS: Array<{ label: string; value: SearchCategory }> = [
    { label: '전체', value: 'all' },
    { label: '호텔', value: 'hotel' },
    { label: '공항', value: 'airport' },
    { label: '식당', value: 'restaurant' },
    { label: '관광명소', value: 'attraction' },
];

const RADIUS_OPTIONS: Array<{ label: string; value: number }> = [
    { label: '1km', value: 1000 },
    { label: '3km', value: 3000 },
    { label: '5km', value: 5000 },
    { label: '10km', value: 10000 },
    { label: '20km', value: 20000 },
];

const AUTO_RELAY_DELAY_OPTIONS_MS = [2000, 2500, 3000] as const;
const AUTO_RELAY_DUPLICATE_GUARD_MS = 8000;

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

function todayPlus(days: number): string {
    const now = new Date();
    now.setDate(now.getDate() + days);
    return now.toISOString().slice(0, 10);
}

async function checkForAppUpdate() {
    try {
        const ignored = await AsyncStorage.getItem(VERSION_IGNORE_KEY);
        if (ignored) {
            return; // 사용자가 업데이트 확인을 비활성화했음
        }

        const response = await fetch(`${API_BASE}/api/marketplace/projects?skip=0&limit=50`);
        if (!response.ok) return;

        const data = await response.json();
        const nadoProject = data.projects?.find(
            (p: any) => p.title?.includes('나도통역사') || p.title?.includes('신세계소리새')
        );

        if (nadoProject?.demo_url) {
            const lastCheck = await AsyncStorage.getItem(VERSION_CHECK_KEY);
            if (!lastCheck || Date.now() - parseInt(lastCheck) > 86400000) { // 24시간마다 체크
                await AsyncStorage.setItem(VERSION_CHECK_KEY, Date.now().toString());
                // 업데이트 알림 표시
                Alert.alert(
                    '신세계소리새 통번역 앱 업데이트',
                    '새 버전이 사용 가능합니다. 지금 다운로드하시겠어요?',
                    [
                        {
                            text: '나중에',
                            onPress: () => { },
                            style: 'cancel',
                        },
                        {
                            text: '다운로드',
                            onPress: () => {
                                Linking.openURL(nadoProject.demo_url).catch((err) =>
                                    console.error('APK 다운로드 실패:', err)
                                );
                            },
                            style: 'default',
                        },
                    ]
                );
            }
        }
    } catch (err) {
        // 버전 체크 실패는 무시
        console.error('버전 체크 오류:', err);
    }
}

async function callLoginApi(email: string, password: string): Promise<string> {
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `로그인 실패 (HTTP ${res.status})`);
    return data.access_token as string;
}

async function callMeApi(token: string): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('내 정보 조회 실패');
    return res.json();
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
    const response = await fetch(`${API_BASE}/api/marketplace/nadotongryoksa/lbs/nearby?${query.toString()}`);
    if (!response.ok) throw new Error(`주변검색 실패: HTTP ${response.status}`);
    const payload = await response.json();
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
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    return result;
}

async function callCreatePurchaseApi(token: string, amount: number): Promise<PurchaseResult> {
    const res = await fetch(`${API_BASE}/api/marketplace/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ project_id: 0, amount, payment_method: 'card' }),
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
// 지원 언어 목록 (24개국어)
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
] as const;

type LangCode = (typeof LANGS)[number]['code'];

function getLangLabelText(code: LangCode): string {
    return LANGS.find((item) => item.code === code)?.label ?? code;
}

type HybridGpsMode = 'satellite' | 'hybrid' | 'wifi_fallback';

type HybridGpsResult = {
    latitude: number;
    longitude: number;
    accuracy: number | null;
    mode: HybridGpsMode;
    qualityScore: number;
};

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

function inferTtsLanguage(text: string, fallback: string): string {
    if (/[\uac00-\ud7a3]/.test(text)) return 'ko-KR';
    if (/[\u3040-\u30ff]/.test(text)) return 'ja-JP';
    if (/[\u4e00-\u9fff]/.test(text)) return fallback === 'zh-TW' ? 'zh-TW' : 'zh-CN';
    if (/[\u0600-\u06ff]/.test(text)) return 'ar-SA';
    if (/[\u0900-\u097f]/.test(text)) return 'hi-IN';
    if (/[\u0400-\u04ff]/.test(text)) return 'ru-RU';
    if (/[\u0e00-\u0e7f]/.test(text)) return 'th-TH';
    if (/[A-Za-z]/.test(text)) return 'en-US';
    return fallback;
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

function resolveSongFileTargetLang(currentSource: LangCode, currentTarget: LangCode): LangCode {
    if (currentSource === 'ko') return 'ko';
    if (currentTarget !== currentSource) return currentTarget;
    return resolveAutoTargetLang(currentSource, currentTarget);
}

// ─────────────────────────────────────────────
// UI 텍스트 다국어 사전 (24개국어)
// ─────────────────────────────────────────────
const UI_TEXT: Record<string, {
    sourceLang: string; targetLang: string; inputPlaceholder: string;
    swap: string; translate: string; resultPlaceholder: string;
    inputRequired: string; inputRequiredMsg: string; errorMsg: string;
    offlineMsg: string; subtitle: string; footer: string; offlineBadge: string;
    autoVoiceSegmentStatus?: string;
    autoVoiceDuplicateSkipped?: string;
    autoVoiceDetected?: string;
    autoVoiceModeStopped?: string;
    autoVoiceModeStarted?: string;
    interAutoRelayDuplicateSkipped?: string;
    interAutoRelayPending?: string;
}> = {
    ko: { sourceLang: '원본 언어', targetLang: '번역 언어', inputPlaceholder: '번역할 텍스트를 입력하세요', swap: '⇄ 언어 스왑', translate: '번역', resultPlaceholder: '번역 결과가 여기에 표시됩니다', inputRequired: '입력 필요', inputRequiredMsg: '번역할 텍스트를 입력하세요.', errorMsg: '[오류] 번역에 실패했습니다. 잠시 후 다시 시도하세요.', offlineMsg: '📡 오프라인 모드 — 인터넷 연결 시 전체 통역 가능', subtitle: '여행 통번역 · 50개국어', footer: '나도통역사 v1.0 · NadoTranslator AI\n50개국어 지원', offlineBadge: '🔴 오프라인', autoVoiceSegmentStatus: '🎙️ 자동 음성 번역: {delay} 구간으로 처리합니다.', autoVoiceDuplicateSkipped: '↺ 같은 문장 자동 번역은 중복 전송을 방지하기 위해 생략했습니다.', autoVoiceDetected: '🎙️ 자동 감지: {from} → {to}', autoVoiceModeStopped: '🎙️ 자동 음성 번역 모드를 종료했습니다.', autoVoiceModeStarted: '🎙️ 자동 음성 번역 모드 시작 ({delay} 간격)', interAutoRelayDuplicateSkipped: '↺ 같은 문장 자동 중계는 중복 전송을 방지하기 위해 생략했습니다.', interAutoRelayPending: '⏱️ {delay} 무입력 시 자동 중계 전송' },
    en: { sourceLang: 'Source Language', targetLang: 'Target Language', inputPlaceholder: 'Enter text to translate', swap: '⇄ Swap', translate: 'Translate', resultPlaceholder: 'Translation will appear here', inputRequired: 'Input required', inputRequiredMsg: 'Please enter text to translate.', errorMsg: '[Error] Translation failed. Please try again.', offlineMsg: '📡 Offline mode — Full translation available with internet', subtitle: 'AI Interpreter · 24 Languages', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Languages Supported', offlineBadge: '🔴 Offline', autoVoiceSegmentStatus: '🎙️ Auto voice translation: processing in {delay} chunks.', autoVoiceDuplicateSkipped: '↺ Duplicate sentence skipped to prevent repeated auto translation.', autoVoiceDetected: '🎙️ Auto-detected: {from} → {to}', autoVoiceModeStopped: '🎙️ Auto voice translation mode has stopped.', autoVoiceModeStarted: '🎙️ Auto voice translation mode started ({delay} interval)', interAutoRelayDuplicateSkipped: '↺ Duplicate sentence skipped to prevent repeated auto relay.', interAutoRelayPending: '⏱️ Auto relay after {delay} of no input' },
    zh: { sourceLang: '源语言', targetLang: '目标语言', inputPlaceholder: '请输入要翻译的文本', swap: '⇄ 切换语言', translate: '翻译', resultPlaceholder: '翻译结果将显示在这里', inputRequired: '需要输入', inputRequiredMsg: '请输入要翻译的文本。', errorMsg: '[错误] 翻译失败，请稍后重试。', offlineMsg: '📡 离线模式 — 联网后可使用完整翻译', subtitle: 'AI 翻译 · 24种语言', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n支持24种语言', offlineBadge: '🔴 离线' },
    'zh-tw': { sourceLang: '來源語言', targetLang: '目標語言', inputPlaceholder: '請輸入要翻譯的文字', swap: '⇄ 切換語言', translate: '翻譯', resultPlaceholder: '翻譯結果將顯示在這裡', inputRequired: '需要輸入', inputRequiredMsg: '請輸入要翻譯的文字。', errorMsg: '[錯誤] 翻譯失敗，請稍後再試。', offlineMsg: '📡 離線模式 — 連網後可使用完整翻譯', subtitle: 'AI 翻譯 · 24種語言', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n支援24種語言', offlineBadge: '🔴 離線' },
    ja: { sourceLang: '翻訳元言語', targetLang: '翻訳先言語', inputPlaceholder: '翻訳するテキストを入力してください', swap: '⇄ 言語スワップ', translate: '翻訳', resultPlaceholder: '翻訳結果がここに表示されます', inputRequired: '入力が必要です', inputRequiredMsg: '翻訳するテキストを入力してください。', errorMsg: '[エラー] 翻訳に失敗しました。後でもう一度お試しください。', offlineMsg: '📡 オフラインモード — インターネット接続後に完全翻訳可能', subtitle: 'AI 通訳 · 24言語', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24言語対応', offlineBadge: '🔴 オフライン' },
    es: { sourceLang: 'Idioma de origen', targetLang: 'Idioma de destino', inputPlaceholder: 'Ingrese el texto a traducir', swap: '⇄ Cambiar', translate: 'Traducir', resultPlaceholder: 'La traducción aparecerá aquí', inputRequired: 'Entrada requerida', inputRequiredMsg: 'Por favor ingrese el texto a traducir.', errorMsg: '[Error] La traducción falló. Inténtelo de nuevo.', offlineMsg: '📡 Modo sin conexión — Traducción completa disponible con internet', subtitle: 'Intérprete AI · 24 Idiomas', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Idiomas', offlineBadge: '🔴 Sin conexión' },
    fr: { sourceLang: 'Langue source', targetLang: 'Langue cible', inputPlaceholder: 'Entrez le texte à traduire', swap: '⇄ Permuter', translate: 'Traduire', resultPlaceholder: 'La traduction apparaîtra ici', inputRequired: 'Saisie requise', inputRequiredMsg: 'Veuillez entrer le texte à traduire.', errorMsg: '[Erreur] La traduction a échoué. Veuillez réessayer.', offlineMsg: '📡 Mode hors ligne — Traduction complète disponible avec internet', subtitle: 'Interprète AI · 24 Langues', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Langues', offlineBadge: '🔴 Hors ligne' },
    de: { sourceLang: 'Quellsprache', targetLang: 'Zielsprache', inputPlaceholder: 'Text zum Übersetzen eingeben', swap: '⇄ Tauschen', translate: 'Übersetzen', resultPlaceholder: 'Übersetzung erscheint hier', inputRequired: 'Eingabe erforderlich', inputRequiredMsg: 'Bitte geben Sie den zu übersetzenden Text ein.', errorMsg: '[Fehler] Übersetzung fehlgeschlagen. Bitte versuchen Sie es erneut.', offlineMsg: '📡 Offline-Modus — Vollständige Übersetzung mit Internet verfügbar', subtitle: 'KI-Dolmetscher · 24 Sprachen', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Sprachen', offlineBadge: '🔴 Offline' },
    pt: { sourceLang: 'Idioma de origem', targetLang: 'Idioma de destino', inputPlaceholder: 'Digite o texto para traduzir', swap: '⇄ Trocar', translate: 'Traduzir', resultPlaceholder: 'A tradução aparecerá aqui', inputRequired: 'Entrada necessária', inputRequiredMsg: 'Por favor, insira o texto para traduzir.', errorMsg: '[Erro] A tradução falhou. Por favor, tente novamente.', offlineMsg: '📡 Modo offline — Tradução completa disponível com internet', subtitle: 'Intérprete AI · 24 Idiomas', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Idiomas', offlineBadge: '🔴 Offline' },
    ru: { sourceLang: 'Исходный язык', targetLang: 'Целевой язык', inputPlaceholder: 'Введите текст для перевода', swap: '⇄ Поменять', translate: 'Перевести', resultPlaceholder: 'Перевод появится здесь', inputRequired: 'Ввод обязателен', inputRequiredMsg: 'Пожалуйста, введите текст для перевода.', errorMsg: '[Ошибка] Перевод не удался. Попробуйте ещё раз.', offlineMsg: '📡 Офлайн-режим — Полный перевод доступен при наличии интернета', subtitle: 'AI Переводчик · 24 Языка', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 языка', offlineBadge: '🔴 Офлайн' },
    ar: { sourceLang: 'اللغة المصدر', targetLang: 'اللغة الهدف', inputPlaceholder: 'أدخل النص للترجمة', swap: '⇄ تبديل', translate: 'ترجمة', resultPlaceholder: 'ستظهر الترجمة هنا', inputRequired: 'مطلوب إدخال', inputRequiredMsg: 'الرجاء إدخال النص للترجمة.', errorMsg: '[خطأ] فشلت الترجمة. يرجى المحاولة مرة أخرى.', offlineMsg: '📡 وضع عدم الاتصال — الترجمة الكاملة متاحة مع الإنترنت', subtitle: 'مترجم AI · 24 لغة', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 لغة مدعومة', offlineBadge: '🔴 غير متصل' },
    hi: { sourceLang: 'स्रोत भाषा', targetLang: 'लक्ष्य भाषा', inputPlaceholder: 'अनुवाद के लिए पाठ दर्ज करें', swap: '⇄ स्वैप', translate: 'अनुवाद करें', resultPlaceholder: 'अनुवाद यहाँ दिखाई देगा', inputRequired: 'इनपुट आवश्यक', inputRequiredMsg: 'कृपया अनुवाद के लिए पाठ दर्ज करें।', errorMsg: '[त्रुटि] अनुवाद विफल हुआ। कृपया पुनः प्रयास करें।', offlineMsg: '📡 ऑफ़लाइन मोड — इंटरनेट के साथ पूर्ण अनुवाद उपलब्ध', subtitle: 'AI दुभाषिया · 24 भाषाएँ', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 भाषाएँ समर्थित', offlineBadge: '🔴 ऑफ़लाइन' },
    it: { sourceLang: 'Lingua di origine', targetLang: 'Lingua di destinazione', inputPlaceholder: 'Inserisci il testo da tradurre', swap: '⇄ Scambia', translate: 'Traduci', resultPlaceholder: 'La traduzione apparirà qui', inputRequired: 'Input richiesto', inputRequiredMsg: 'Inserisci il testo da tradurre.', errorMsg: '[Errore] Traduzione fallita. Riprovare.', offlineMsg: '📡 Modalità offline — Traduzione completa disponibile con internet', subtitle: 'Interprete AI · 24 Lingue', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Lingue', offlineBadge: '🔴 Offline' },
    tr: { sourceLang: 'Kaynak Dil', targetLang: 'Hedef Dil', inputPlaceholder: 'Çevrilecek metni girin', swap: '⇄ Değiştir', translate: 'Çevir', resultPlaceholder: 'Çeviri burada görünecek', inputRequired: 'Giriş gerekli', inputRequiredMsg: 'Lütfen çevrilecek metni girin.', errorMsg: '[Hata] Çeviri başarısız. Lütfen tekrar deneyin.', offlineMsg: '📡 Çevrimdışı mod — İnternet ile tam çeviri mevcut', subtitle: 'AI Tercüman · 24 Dil', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Dil Destekleniyor', offlineBadge: '🔴 Çevrimdışı' },
    vi: { sourceLang: 'Ngôn ngữ nguồn', targetLang: 'Ngôn ngữ đích', inputPlaceholder: 'Nhập văn bản cần dịch', swap: '⇄ Hoán đổi', translate: 'Dịch', resultPlaceholder: 'Bản dịch sẽ hiển thị ở đây', inputRequired: 'Cần nhập liệu', inputRequiredMsg: 'Vui lòng nhập văn bản cần dịch.', errorMsg: '[Lỗi] Dịch thất bại. Vui lòng thử lại.', offlineMsg: '📡 Chế độ ngoại tuyến — Dịch đầy đủ khi có internet', subtitle: 'Phiên dịch AI · 24 Ngôn ngữ', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Ngôn ngữ', offlineBadge: '🔴 Ngoại tuyến' },
    th: { sourceLang: 'ภาษาต้นทาง', targetLang: 'ภาษาปลายทาง', inputPlaceholder: 'ป้อนข้อความที่ต้องการแปล', swap: '⇄ สลับ', translate: 'แปล', resultPlaceholder: 'ผลการแปลจะแสดงที่นี่', inputRequired: 'ต้องการข้อมูล', inputRequiredMsg: 'กรุณาป้อนข้อความที่ต้องการแปล', errorMsg: '[ข้อผิดพลาด] การแปลล้มเหลว โปรดลองอีกครั้ง', offlineMsg: '📡 โหมดออฟไลน์ — แปลเต็มรูปแบบเมื่อมีอินเทอร์เน็ต', subtitle: 'AI ล่าม · 24 ภาษา', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 ภาษา', offlineBadge: '🔴 ออฟไลน์' },
    id: { sourceLang: 'Bahasa Sumber', targetLang: 'Bahasa Tujuan', inputPlaceholder: 'Masukkan teks untuk diterjemahkan', swap: '⇄ Tukar', translate: 'Terjemahkan', resultPlaceholder: 'Terjemahan akan muncul di sini', inputRequired: 'Input diperlukan', inputRequiredMsg: 'Silakan masukkan teks untuk diterjemahkan.', errorMsg: '[Kesalahan] Terjemahan gagal. Silakan coba lagi.', offlineMsg: '📡 Mode offline — Terjemahan lengkap tersedia dengan internet', subtitle: 'Penerjemah AI · 24 Bahasa', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Bahasa', offlineBadge: '🔴 Offline' },
    ms: { sourceLang: 'Bahasa Sumber', targetLang: 'Bahasa Sasaran', inputPlaceholder: 'Masukkan teks untuk diterjemah', swap: '⇄ Tukar', translate: 'Terjemah', resultPlaceholder: 'Terjemahan akan muncul di sini', inputRequired: 'Input diperlukan', inputRequiredMsg: 'Sila masukkan teks untuk diterjemah.', errorMsg: '[Ralat] Terjemahan gagal. Sila cuba lagi.', offlineMsg: '📡 Mod luar talian — Terjemahan penuh tersedia dengan internet', subtitle: 'Penterjemah AI · 24 Bahasa', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Bahasa', offlineBadge: '🔴 Luar Talian' },
    nl: { sourceLang: 'Brontaal', targetLang: 'Doeltaal', inputPlaceholder: 'Voer tekst in om te vertalen', swap: '⇄ Wisselen', translate: 'Vertalen', resultPlaceholder: 'Vertaling verschijnt hier', inputRequired: 'Invoer vereist', inputRequiredMsg: 'Voer de te vertalen tekst in.', errorMsg: '[Fout] Vertaling mislukt. Probeer opnieuw.', offlineMsg: '📡 Offlinemodus — Volledige vertaling beschikbaar met internet', subtitle: 'AI Tolk · 24 Talen', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Talen', offlineBadge: '🔴 Offline' },
    pl: { sourceLang: 'Język źródłowy', targetLang: 'Język docelowy', inputPlaceholder: 'Wprowadź tekst do tłumaczenia', swap: '⇄ Zamień', translate: 'Tłumacz', resultPlaceholder: 'Tłumaczenie pojawi się tutaj', inputRequired: 'Wymagane wprowadzenie', inputRequiredMsg: 'Wprowadź tekst do tłumaczenia.', errorMsg: '[Błąd] Tłumaczenie nie powiodło się. Spróbuj ponownie.', offlineMsg: '📡 Tryb offline — Pełne tłumaczenie dostępne z internetem', subtitle: 'Tłumacz AI · 24 Języki', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Języki', offlineBadge: '🔴 Offline' },
    uk: { sourceLang: 'Вихідна мова', targetLang: 'Цільова мова', inputPlaceholder: 'Введіть текст для перекладу', swap: '⇄ Замінити', translate: 'Перекласти', resultPlaceholder: "Переклад з'явиться тут", inputRequired: 'Потрібне введення', inputRequiredMsg: 'Будь ласка, введіть текст для перекладу.', errorMsg: '[Помилка] Переклад не вдався. Спробуйте ще раз.', offlineMsg: '📡 Офлайн-режим — Повний переклад доступний при наявності інтернету', subtitle: 'AI Перекладач · 24 Мови', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 мови', offlineBadge: '🔴 Офлайн' },
    sv: { sourceLang: 'Källspråk', targetLang: 'Målspråk', inputPlaceholder: 'Ange text att översätta', swap: '⇄ Byt', translate: 'Översätt', resultPlaceholder: 'Översättning visas här', inputRequired: 'Inmatning krävs', inputRequiredMsg: 'Ange texten som ska översättas.', errorMsg: '[Fel] Översättning misslyckades. Försök igen.', offlineMsg: '📡 Offlineläge — Full översättning tillgänglig med internet', subtitle: 'AI Tolk · 24 Språk', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Språk', offlineBadge: '🔴 Offline' },
    no: { sourceLang: 'Kildespråk', targetLang: 'Målspråk', inputPlaceholder: 'Skriv inn tekst å oversette', swap: '⇄ Bytt', translate: 'Oversett', resultPlaceholder: 'Oversettelse vises her', inputRequired: 'Inndata kreves', inputRequiredMsg: 'Skriv inn tekst å oversette.', errorMsg: '[Feil] Oversettelse mislyktes. Prøv igjen.', offlineMsg: '📡 Frakoblet modus — Full oversettelse tilgengelig med internett', subtitle: 'AI Tolk · 24 Språk', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Språk', offlineBadge: '🔴 Frakoblet' },
    da: { sourceLang: 'Kildesprog', targetLang: 'Målsprog', inputPlaceholder: 'Indtast tekst til oversættelse', swap: '⇄ Skift', translate: 'Oversæt', resultPlaceholder: 'Oversættelse vises her', inputRequired: 'Indtastning påkrævet', inputRequiredMsg: 'Indtast tekst til oversættelse.', errorMsg: '[Fejl] Oversættelse mislykkedes. Prøv igen.', offlineMsg: '📡 Offlinetilstand — Fuld oversættelse tilgængelig med internet', subtitle: 'AI Tolk · 24 Sprog', footer: 'NadoTranslator v1.0 · NadoTranslator AI\n24 Sprog', offlineBadge: '🔴 Offline' },
};

function getUiText(lang: string) {
    const fallback = UI_TEXT['en'];
    const selected = UI_TEXT[lang] ?? fallback;
    return {
        ...selected,
        autoVoiceSegmentStatus: selected.autoVoiceSegmentStatus ?? fallback.autoVoiceSegmentStatus ?? '🎙️ Auto voice translation: processing in {delay} chunks.',
        autoVoiceDuplicateSkipped: selected.autoVoiceDuplicateSkipped ?? fallback.autoVoiceDuplicateSkipped ?? '↺ Duplicate sentence skipped to prevent repeated auto translation.',
        autoVoiceDetected: selected.autoVoiceDetected ?? fallback.autoVoiceDetected ?? '🎙️ Auto-detected: {from} → {to}',
        autoVoiceModeStopped: selected.autoVoiceModeStopped ?? fallback.autoVoiceModeStopped ?? '🎙️ Auto voice translation mode has stopped.',
        autoVoiceModeStarted: selected.autoVoiceModeStarted ?? fallback.autoVoiceModeStarted ?? '🎙️ Auto voice translation mode started ({delay} interval)',
        interAutoRelayDuplicateSkipped: selected.interAutoRelayDuplicateSkipped ?? fallback.interAutoRelayDuplicateSkipped ?? '↺ Duplicate sentence skipped to prevent repeated auto relay.',
        interAutoRelayPending: selected.interAutoRelayPending ?? fallback.interAutoRelayPending ?? '⏱️ Auto relay after {delay} of no input',
    };
}

// ─────────────────────────────────────────────
// 색상 팔레트 (나도통역사 다크 테마)
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
    const [inputText, setInputText] = useState('');
    const [resultText, setResultText] = useState('');
    const [loading, setLoading] = useState(false);
    const [offline, setOffline] = useState(false);
    const [engine, setEngine] = useState('');
    const [langPickerFor, setLangPickerFor] = useState<'from' | 'to' | null>(null);
    const pulseAnim = useRef(new Animated.Value(1)).current;
    const { selectedCallMode, callModeLabel, setCallMode } = useCallModeController();

    // 로그인/내정보
    const [token, setToken] = useState('');
    const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
    const [showLogin, setShowLogin] = useState(false);
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPw, setLoginPw] = useState('');
    const [loginLoading, setLoginLoading] = useState(false);
    const [loginError, setLoginError] = useState('');
    const [showMyInfo, setShowMyInfo] = useState(false);
    const [myPurchases, setMyPurchases] = useState<Array<{ id: number; amount: number; status: string; payment_method: string }> | null>(null);
    const [myPurchasesLoading, setMyPurchasesLoading] = useState(false);
    const [showVoipTester, setShowVoipTester] = useState(false);
    const [showFriendFolder, setShowFriendFolder] = useState(false);
    const [voipPhone, setVoipPhone] = useState(VOIP_TEST_DEFAULT_PHONE);
    const [voipInitLoading, setVoipInitLoading] = useState(false);
    const [voipInitError, setVoipInitError] = useState('');
    const [voipCallInitResponse, setVoipCallInitResponse] = useState<CallInitResponse | null>(null);
    const { initiateVoipCall, validatePhoneNumber } = useVoipAutoController(API_BASE, token);

    const logUiPressProbe = useCallback((event: string, details: Record<string, unknown> = {}) => {
        const payload = {
            event,
            timestamp: new Date().toISOString(),
            token_ready: Boolean(token),
            user_ready: Boolean(userInfo),
            show_login: showLogin,
            show_voip_tester: showVoipTester,
            selected_call_mode: selectedCallMode,
            ...details,
        };
        console.log('[UI_PRESS_PROBE]', JSON.stringify(payload));
    }, [selectedCallMode, showLogin, showVoipTester, token, userInfo]);

    // 주변 검색
    const [lat, setLat] = useState('37.5665');
    const [lon, setLon] = useState('126.9780');
    const [nearbyCategory, setNearbyCategory] = useState<SearchCategory>('all');
    const [radiusM, setRadiusM] = useState(5000);
    const [nearbyLoading, setNearbyLoading] = useState(false);
    const [nearbyError, setNearbyError] = useState('');
    const [nearbyPlaces, setNearbyPlaces] = useState<NearbyPlace[]>([]);
    const [selectedBookingPlaceId, setSelectedBookingPlaceId] = useState('');

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
    const [interCallActive, setInterCallActive] = useState(false);
    const [interCallTurn, setInterCallTurn] = useState<'from' | 'to'>('from');
    const [interCallStatus, setInterCallStatus] = useState('');
    const [interCallPhone, setInterCallPhone] = useState('');
    const [interCallLog, setInterCallLog] = useState<Array<{ turn: 'from' | 'to'; text: string; translated: string }>>([]);
    const [interManualText, setInterManualText] = useState('');
    const [autoRelayDelayMs, setAutoRelayDelayMs] = useState<number>(2500);
    const interCallActiveRef = useRef(false);
    const interManualAutoRelayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const interLastAutoRelayRef = useRef<{ key: string; sentAt: number } | null>(null);

    // ── 음성 입력 (BT 하이브리드 MIC) ──
    const [autoVoiceModeEnabled, setAutoVoiceModeEnabled] = useState(false);
    const [isVoiceRecording, setIsVoiceRecording] = useState(false);
    const [voiceSttLoading, setVoiceSttLoading] = useState(false);
    const recordingRef = useRef<Audio.Recording | null>(null);
    const webSpeechRecognitionRef = useRef<any>(null);
    const autoVoiceStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const autoVoiceRestartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const stopVoiceInputRef = useRef<((options?: { suppressAutoRestart?: boolean }) => Promise<void>) | null>(null);
    const mainLastAutoVoiceRelayRef = useRef<{ key: string; sentAt: number } | null>(null);
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
    const songFileSoundRef = useRef<Audio.Sound | null>(null);
    const voicePreviewSoundRef = useRef<Audio.Sound | null>(null);
    const [voiceConsent, setVoiceConsent] = useState<VoiceConsentResponse | null>(null);
    const [voiceProfile, setVoiceProfile] = useState<VoiceProfileResponse | null>(null);
    const [voiceProfileLoading, setVoiceProfileLoading] = useState(false);
    const [voiceProfileRecording, setVoiceProfileRecording] = useState(false);
    const [voiceProfileStatus, setVoiceProfileStatus] = useState('');
    const [voicePreview, setVoicePreview] = useState<VoicePreviewResponse | null>(null);
    const [voiceLicenseMode, setVoiceLicenseMode] = useState<VoiceLicenseMode>('private_preview_unverified');
    const [voiceOutputScope, setVoiceOutputScope] = useState<VoiceOutputScope>('private_preview');
    const [voiceRightsAcknowledged, setVoiceRightsAcknowledged] = useState(false);
    const voiceProfileRecordingRef = useRef<Audio.Recording | null>(null);

    const selectedBookingPlace = nearbyPlaces.find((item) => item.id === selectedBookingPlaceId) ?? null;
    const activeSongFileSegment = songFileSegments.find((segment) => songFilePlaybackMs >= segment.start_ms && songFilePlaybackMs <= segment.end_ms) ?? null;
    const translationRequestSeqRef = useRef(0);
    const latestTranslationMetaRef = useRef<{ source: LangCode; target: LangCode; translated: string } | null>(null);
    const [translationEpoch, setTranslationEpoch] = useState(0);

    const runTranslation = useCallback(async (text: string, source: LangCode, target: LangCode) => {
        const requestId = ++translationRequestSeqRef.current;
        setLoading(true);
        setResultText('');
        try {
            const result = await translateText(text, source, target);
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
        } catch {
            if (requestId !== translationRequestSeqRef.current) {
                return;
            }
            const ui = getUiText(source);
            setResultText(ui.errorMsg);
            latestTranslationMetaRef.current = null;
            setTranslationEpoch((prev) => prev + 1);
        } finally {
            if (requestId === translationRequestSeqRef.current) {
                setLoading(false);
            }
        }
    }, []);

    // 앱 시작 시 버전 체크
    useEffect(() => {
        checkForAppUpdate().catch((err) => console.error('앱 버전 체크 오류:', err));
    }, []);

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
    }, [fromLang, loadSongFileSound, songFileLoading, toLang]);

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
            setToken(tk);
            setUserInfo(me);
            setShowLogin(false);
            setLoginEmail('');
            setLoginPw('');
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
    }, [logUiPressProbe, loginEmail, loginPw]);

    const handlePressLoginButton = useCallback(() => {
        logUiPressProbe('LOGIN_BUTTON_PRESS', { source: 'header_account_row' });
        setShowLogin(true);
    }, [logUiPressProbe]);

    const handleLogout = useCallback(() => {
        setToken('');
        setUserInfo(null);
        setShowMyInfo(false);
        setMyPurchases(null);
    }, []);

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

    const handleOpenVoipTester = useCallback(() => {
        logUiPressProbe('VOIP_OPEN_PRESS', {
            source: 'shared_handler',
        });
        if (!token || !userInfo) {
            logUiPressProbe('VOIP_OPEN_BLOCKED_LOGIN_REQUIRED');
            setShowLogin(true);
            setVoipInitError('VoIP 테스트는 로그인 후 사용할 수 있습니다.');
            return;
        }

        setCallMode('voip_full_auto');
        setVoipInitError('');
        setVoipCallInitResponse(null);
        setVoipPhone(bookingResult?.support_phone || selectedBookingPlace?.phone || VOIP_TEST_DEFAULT_PHONE);
        setShowVoipTester(true);
        logUiPressProbe('VOIP_OPEN_SUCCESS');
    }, [bookingResult?.support_phone, logUiPressProbe, selectedBookingPlace?.phone, setCallMode, token, userInfo]);

    const handleHeaderVoipLaunchPress = useCallback(() => {
        logUiPressProbe('VOIP_LAUNCH_BUTTON_PRESS', { source: 'header_version_row' });
        handleOpenVoipTester();
    }, [handleOpenVoipTester, logUiPressProbe]);

    const handleInlineVoipOpenPress = useCallback(() => {
        logUiPressProbe('VOIP_LAUNCH_BUTTON_PRESS', { source: 'voip_section_inline_button' });
        handleOpenVoipTester();
    }, [handleOpenVoipTester, logUiPressProbe]);

    const handleStartVoipCall = useCallback(async () => {
        logUiPressProbe('VOIP_START_CALL_PRESS', {
            phone: voipPhone.trim() || VOIP_TEST_DEFAULT_PHONE,
        });
        if (!token || !userInfo) {
            logUiPressProbe('VOIP_START_CALL_BLOCKED_LOGIN_REQUIRED');
            setShowLogin(true);
            setVoipInitError('VoIP 테스트는 로그인 후 사용할 수 있습니다.');
            return;
        }

        // Per-feature 권한 체크: 마이크
        const { requestPermissions, setPermissionError } = usePermissionCheck();
        const hasPermission = await requestPermissions(['RECORD_AUDIO'], 'VoIP 통화', (msg) => {
            setVoipInitError(msg);
            logUiPressProbe('VOIP_START_CALL_BLOCKED_PERMISSION', { permission: 'RECORD_AUDIO' });
        });
        if (!hasPermission) {
            return;
        }

        const phone = voipPhone.trim() || VOIP_TEST_DEFAULT_PHONE;
        if (!validatePhoneNumber(phone)) {
            logUiPressProbe('VOIP_START_CALL_BLOCKED_INVALID_PHONE', { phone });
            setVoipInitError('전화번호는 +국가번호 형식이어야 합니다.');
            return;
        }

        setVoipInitLoading(true);
        setVoipInitError('');
        try {
            const payload = await initiateVoipCall({
                callee_phone: phone,
                caller_id: userInfo.username || userInfo.email || 'mobile-demo',
                session_id: bookingResult?.confirmation_id || 'mobile-voip-test-session',
                mode: 'voip_full_auto',
                auto_relay: false,
            });
            setVoipCallInitResponse(payload as CallInitResponse);
            logUiPressProbe('VOIP_START_CALL_SUCCESS', {
                call_id: (payload as any)?.call_id ?? null,
                signaling_server: (payload as any)?.signaling_server ?? null,
                turn_servers_count: Array.isArray((payload as any)?.turn_servers) ? (payload as any).turn_servers.length : null,
            });
        } catch (error: any) {
            setVoipInitError(error?.message || 'VoIP 테스트 시작 실패');
            logUiPressProbe('VOIP_START_CALL_FAIL', {
                error: error?.message || 'VoIP 테스트 시작 실패',
            });
        } finally {
            setVoipInitLoading(false);
        }
    }, [bookingResult?.confirmation_id, initiateVoipCall, logUiPressProbe, token, userInfo, validatePhoneNumber, voipPhone]);

    const handleCloseVoipTester = useCallback(() => {
        setVoipCallInitResponse(null);
        setVoipInitError('');
        setVoipInitLoading(false);
        setShowVoipTester(false);
    }, []);

    const handleSearchNearby = useCallback(async () => {
        if (!lat.trim() || !lon.trim()) {
            setNearbyError('위도와 경도를 입력해 주세요.');
            return;
        }
        setNearbyLoading(true);
        setNearbyError('');
        setBookingResult(null);
        try {
            const places = await callNearbyPlacesApi({
                lat,
                lon,
                category: nearbyCategory,
                radiusM,
                targetLang: toLang,
            });
            setNearbyPlaces(places);
            const firstBookablePlace =
                places.find((place) => place.category === 'hotel' && place.booking_supported)
                ?? places.find((place) => place.category === 'airport' && place.booking_supported);
            setSelectedBookingPlaceId(firstBookablePlace?.id || '');
            if (!places.length) {
                setNearbyError('현재 반경에서 찾은 장소가 없습니다. 반경을 넓혀 보세요.');
            }
        } catch (e: any) {
            setNearbyPlaces([]);
            setSelectedBookingPlaceId('');
            setNearbyError(e?.message || '주변검색 중 오류가 발생했습니다.');
        } finally {
            setNearbyLoading(false);
        }
    }, [lat, lon, nearbyCategory, radiusM, toLang]);

    const handleReserveBooking = useCallback(async () => {
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
        } catch (e: any) {
            setBookingError(e?.message || '예약 요청에 실패했습니다.');
        } finally {
            setBookingLoading(false);
        }
    }, [selectedBookingPlace, token, bookingName, checkinDate, checkoutDate, guests, roomCount, bookingNote, toLang]);

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

    const scoreLocationQuality = useCallback((accuracy: number | null): number => {
        if (accuracy === null) return 35;
        if (accuracy <= 15) return 96;
        if (accuracy <= 30) return 88;
        if (accuracy <= 60) return 74;
        if (accuracy <= 120) return 58;
        return 40;
    }, []);

    const detectHybridGpsMode = useCallback((accuracy: number | null): HybridGpsMode => {
        if (accuracy === null) return 'wifi_fallback';
        if (accuracy <= 25) return 'satellite';
        if (accuracy <= 90) return 'hybrid';
        return 'wifi_fallback';
    }, []);

    const resolveHybridLocation = useCallback(async (): Promise<HybridGpsResult> => {
        const withTimeout = async <T,>(promise: Promise<T>, ms: number): Promise<T> => {
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
        };

        const servicesEnabled = await Location.hasServicesEnabledAsync();
        if (!servicesEnabled) {
            const last = await Location.getLastKnownPositionAsync();
            if (!last) {
                throw new Error('gps-unavailable');
            }
            const lastAccuracy = last.coords.accuracy ?? null;
            return {
                latitude: last.coords.latitude,
                longitude: last.coords.longitude,
                accuracy: lastAccuracy,
                mode: 'wifi_fallback',
                qualityScore: scoreLocationQuality(lastAccuracy),
            };
        }

        // 1) 위성(GNSS) 우선 고정밀 시도
        try {
            const p1 = await withTimeout(
                Location.getCurrentPositionAsync({
                    accuracy: Location.Accuracy.Highest,
                    mayShowUserSettingsDialog: false,
                }),
                9000,
            );
            const accuracy = p1.coords.accuracy ?? null;
            return {
                latitude: p1.coords.latitude,
                longitude: p1.coords.longitude,
                accuracy,
                mode: detectHybridGpsMode(accuracy),
                qualityScore: scoreLocationQuality(accuracy),
            };
        } catch {
            // no-op: 다음 단계로 폴백
        }

        // 2) 하이브리드(네트워크+GNSS 보조) 표준 정밀 시도
        try {
            const p2 = await withTimeout(
                Location.getCurrentPositionAsync({
                    accuracy: Location.Accuracy.Balanced,
                    mayShowUserSettingsDialog: false,
                }),
                7000,
            );
            const accuracy = p2.coords.accuracy ?? null;
            return {
                latitude: p2.coords.latitude,
                longitude: p2.coords.longitude,
                accuracy,
                mode: detectHybridGpsMode(accuracy),
                qualityScore: scoreLocationQuality(accuracy),
            };
        } catch {
            // no-op: 다음 단계로 폴백
        }

        // 3) WF(와이파이/기지국) 기반 마지막 위치 폴백
        const last = await Location.getLastKnownPositionAsync();
        if (!last) {
            throw new Error('gps-unavailable');
        }
        const lastAccuracy = last.coords.accuracy ?? null;
        return {
            latitude: last.coords.latitude,
            longitude: last.coords.longitude,
            accuracy: lastAccuracy,
            mode: 'wifi_fallback',
            qualityScore: scoreLocationQuality(lastAccuracy),
        };
    }, [detectHybridGpsMode, scoreLocationQuality]);

    const { openDialPad, startPstnAssistDialFlow } = usePstnAssistController();

    const handleDetectLangByGPS = useCallback(async (silent = false) => {
        setGpsLangLoading(true);
        setGpsStatus('GPS/WF 하이브리드 위치 확인 중...');
        try {
            // Per-feature 권한 체크: 위치
            const { requestPermissions } = usePermissionCheck();
            const hasPermission = await requestPermissions(['ACCESS_FINE_LOCATION'], '근처 검색 기능', (msg) => {
                setGpsStatus('위치 권한이 없어 현재 위치를 확인할 수 없습니다.');
            });
            if (!hasPermission) {
                if (!silent) {
                    Alert.alert('위치 권한 필요', '현재 위치 확인과 주변 서비스(호텔, 공항, 식당)를 사용하려면 위치 권한이 필요합니다.');
                }
                return;
            }

            const resolved = await resolveHybridLocation();
            setLat(resolved.latitude.toFixed(6));
            setLon(resolved.longitude.toFixed(6));
            const geocoded = await Location.reverseGeocodeAsync({
                latitude: resolved.latitude,
                longitude: resolved.longitude,
            });
            const countryCode = (geocoded?.[0]?.isoCountryCode ?? '').toUpperCase();
            const modeLabel =
                resolved.mode === 'satellite'
                    ? '🛰️ Satellite'
                    : resolved.mode === 'hybrid'
                        ? '🌐 Hybrid'
                        : '📶 WF Fallback';
            const accText = resolved.accuracy !== null ? `${resolved.accuracy.toFixed(0)}m` : 'N/A';

            setGpsStatus(`${modeLabel} · 품질 ${resolved.qualityScore}점 · 정확도 ${accText} · 현재 위치: ${countryCode || 'UNKNOWN'}`);
        } catch {
            setGpsStatus('GPS/WF 하이브리드 위치 확인 실패 - 권한/신호 상태를 확인해 주세요.');
            if (!silent) {
                Alert.alert('위치 확인 실패', '현재 위치 확인에 실패했습니다. 공항, 호텔예약, 먹거리, 서비스 기능은 직접 검색으로 계속 사용할 수 있습니다.');
            }
        } finally {
            setGpsLangLoading(false);
        }
    }, [getLangLabel, resolveHybridLocation]);

    useEffect(() => {
        if (Platform.OS !== 'web') {
            void handleDetectLangByGPS(true);
        }
    }, [handleDetectLangByGPS]);

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
    }, []);

    // ── BT 하이브리드 음성 입력 ──
    // BT 이어폰 연결 시 → Android MODE_IN_COMMUNICATION → SCO 자동 활성화 → 이어폰 MIC 사용
    // BT 이어폰 미연결 시 → 폰 내장 MIC 사용 (현재 동작 그대로 유지)
    const startVoiceInput = useCallback(async (options: { autoMode?: boolean } = {}) => {
        try {
            const effectiveAutoMode = options.autoMode ?? autoVoiceModeEnabled;
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
                    const detectedTo = resolveAutoTargetLang(detectedFrom, toLang);
                    setFromLang(detectedFrom);
                    setToLang(detectedTo);
                    setInputText(transcript);
                    await runTranslation(transcript, detectedFrom, detectedTo);
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
            const { requestPermissions } = usePermissionCheck();
            const hasPermission = await requestPermissions(['RECORD_AUDIO'], '음성 입력', (msg) => {
                setGpsStatus(`🎤 음성 입력 실패: ${msg}`);
            });
            if (!hasPermission) {
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
            const { recording } = await Audio.Recording.createAsync({
                android: {
                    extension: '.m4a',
                    outputFormat: 2,     // MPEG_4
                    audioEncoder: 3,     // AAC
                    sampleRate: 16000,
                    numberOfChannels: 1,
                    bitRate: 64000,
                },
                ios: {
                    extension: '.wav',
                    audioQuality: 127,   // HIGH
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
            recordingRef.current = recording;
            setIsVoiceRecording(true);
            if (effectiveAutoMode) {
                clearAutoVoiceTimers();
                setGpsStatus(formatStatusText(getUiText(fromLang).autoVoiceSegmentStatus, { delay: formatAutoRelayDelayLabel(autoRelayDelayMs) }));
                autoVoiceStopTimerRef.current = setTimeout(() => {
                    void stopVoiceInputRef.current?.();
                }, autoRelayDelayMs);
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
            setGpsStatus(`🎤 음성 입력 실패: ${detail}`);
            Alert.alert('녹음 오류', detail);
        }
    }, [autoRelayDelayMs, autoVoiceModeEnabled, clearAutoVoiceTimers, fromLang, runTranslation, toLang]);

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

        if (!recordingRef.current) return;
        clearAutoVoiceTimers();
        setIsVoiceRecording(false);
        const shouldAutoRestart = autoVoiceModeEnabled && !options.suppressAutoRestart;
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
            if (!uri) return;
            setVoiceSttLoading(true);
            try {
                const audioBase64 = await FileSystem.readAsStringAsync(uri, {
                    encoding: FileSystem.EncodingType.Base64,
                });
                const res = await fetch(`${API_BASE}/api/llm/voice/orchestrate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ audio_base64: audioBase64, agent_key: 'reasoner', tts: false }),
                });
                if (res.ok) {
                    const data = await res.json();
                    const transcript = String(data.transcript ?? '').trim();
                    if (transcript) {
                        if (songModeEnabled) {
                            const filteredLyric = normalizeLyricLine(transcript);
                            if (!isLikelyLyricLine(filteredLyric)) {
                                setSongModeStatus('🎵 가사 구간이 아니거나 배경 노이즈가 커서 이번 구간은 건너뛰었습니다.');
                            } else {
                                const rawDetected = data.detected_language ? String(data.detected_language) : '';
                                const sourceInfo = resolveSongHybridSource(rawDetected, filteredLyric);
                                const targetLang = resolveSongHybridTarget(sourceInfo.lang);
                                const translated = await translateText(
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
                        } else {
                            // ── 언어 자동 감지 → 패널 자동 표기 → 번역 ──
                            const detectedFrom: LangCode = normalizeDetectedLangCode(data.detected_language)
                                ?? inferSpeechLangCode(transcript, 'en');
                            const detectedTo = resolveAutoTargetLang(detectedFrom, toLang);
                            const relayKey = `${detectedFrom}:${detectedTo}:${normalizeRelayText(transcript)}`;
                            setFromLang(detectedFrom);
                            setToLang(detectedTo);
                            setInputText(transcript);
                            if (autoVoiceModeEnabled && mainLastAutoVoiceRelayRef.current && mainLastAutoVoiceRelayRef.current.key === relayKey && Date.now() - mainLastAutoVoiceRelayRef.current.sentAt < AUTO_RELAY_DUPLICATE_GUARD_MS) {
                                setGpsStatus(getUiText(fromLang).autoVoiceDuplicateSkipped);
                            } else {
                                setGpsStatus(formatStatusText(getUiText(fromLang).autoVoiceDetected, {
                                    from: getLangLabel(detectedFrom),
                                    to: getLangLabel(detectedTo),
                                }));
                                if (autoVoiceModeEnabled) {
                                    setLoading(true);
                                    setResultText('');
                                    try {
                                        const translated = await translateText(transcript, detectedFrom, detectedTo);
                                        setResultText(translated.translated);
                                        setOffline(translated.offline);
                                        setEngine(translated.engine);
                                        mainLastAutoVoiceRelayRef.current = { key: relayKey, sentAt: Date.now() };
                                        speakWithLang(translated.translated, detectedTo);
                                    } catch {
                                        Alert.alert(getUiText(fromLang).errorMsg);
                                    } finally {
                                        setLoading(false);
                                    }
                                } else {
                                    await runTranslation(transcript, detectedFrom, detectedTo);
                                }
                            }
                        }
                    }
                }
            } finally {
                setVoiceSttLoading(false);
                // 임시 파일 삭제
                FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
                if (shouldAutoRestart && !recordingRef.current) {
                    autoVoiceRestartTimerRef.current = setTimeout(() => {
                        if (!recordingRef.current && autoVoiceModeEnabled) {
                            void startVoiceInput({ autoMode: true });
                        }
                    }, 300);
                }
            }
        } catch {
            setVoiceSttLoading(false);
        }
    }, [appendSongSubtitle, autoVoiceModeEnabled, clearAutoVoiceTimers, fromLang, getLangLabel, resolveSongHybridSource, resolveSongHybridTarget, runTranslation, songModeEnabled, speakWithLang, startVoiceInput, toLang]);

    useEffect(() => {
        stopVoiceInputRef.current = stopVoiceInput;
    }, [stopVoiceInput]);

    useEffect(() => {
        if (!autoVoiceModeEnabled) {
            clearAutoVoiceTimers();
        }
    }, [autoVoiceModeEnabled, clearAutoVoiceTimers]);

    useEffect(() => {
        return () => {
            clearAutoVoiceTimers();
        };
    }, [clearAutoVoiceTimers]);

    const handleToggleAutoVoiceMode = useCallback(async () => {
        if (autoVoiceModeEnabled) {
            setAutoVoiceModeEnabled(false);
            setGpsStatus(getUiText(fromLang).autoVoiceModeStopped);
            if (recordingRef.current) {
                await stopVoiceInput({ suppressAutoRestart: true });
            }
            return;
        }

        setAutoVoiceModeEnabled(true);
        setGpsStatus(formatStatusText(getUiText(fromLang).autoVoiceModeStarted, { delay: formatAutoRelayDelayLabel(autoRelayDelayMs) }));
        if (!recordingRef.current) {
            await startVoiceInput({ autoMode: true });
        }
    }, [autoRelayDelayMs, autoVoiceModeEnabled, fromLang, startVoiceInput, stopVoiceInput]);

    const relayInterCallManual = useCallback(async (turn: 'from' | 'to', spokenText: string, options: { isAutoRelay?: boolean } = {}) => {
        const trimmedText = spokenText.trim();
        if (!trimmedText) return;
        const dedupeKey = `${turn}:${normalizeRelayText(trimmedText)}`;
        if (options.isAutoRelay && interLastAutoRelayRef.current && interLastAutoRelayRef.current.key === dedupeKey && Date.now() - interLastAutoRelayRef.current.sentAt < AUTO_RELAY_DUPLICATE_GUARD_MS) {
            setInterCallStatus(getUiText(fromLang).interAutoRelayDuplicateSkipped);
            setInterManualText('');
            return;
        }
        const listenLang = turn === 'from' ? fromLang : toLang;
        const translateTo = turn === 'from' ? toLang : fromLang;
        setInterCallStatus('🔄 번역 중...');
        try {
            const translated = await translateText(trimmedText, listenLang, translateTo);
            setInterCallLog((prev) => [...prev.slice(-19), { turn, text: trimmedText, translated: translated.translated }]);
            setInterCallStatus(`🔊 ${getLangLabel(translateTo)}로 송출 중...`);
            speakWithLang(translated.translated, translateTo);
            setInterCallTurn(turn === 'from' ? 'to' : 'from');
            setInterManualText('');
            if (options.isAutoRelay) {
                interLastAutoRelayRef.current = { key: dedupeKey, sentAt: Date.now() };
            }
        } catch {
            setInterCallStatus('통역 통화 처리 중 오류가 발생했습니다.');
        }
    }, [fromLang, toLang, getLangLabel, speakWithLang]);

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
        const listenLang = turn === 'from' ? fromLang : toLang;
        const translateTo = turn === 'from' ? toLang : fromLang;
        const listenTts = LANGS.find((l) => l.code === listenLang)?.tts ?? 'en-US';
        setInterCallTurn(turn);
        setInterCallStatus(`🎤 ${getLangLabel(listenLang)}로 말하세요...`);

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
            setInterCallStatus('🔄 번역 중...');
            try {
                const translated = await translateText(spokenText, listenLang, translateTo);
                setInterCallLog((prev) => [...prev.slice(-19), { turn, text: spokenText, translated: translated.translated }]);
                setInterCallStatus(`🔊 ${getLangLabel(translateTo)}로 송출 중...`);
                const targetTts = LANGS.find((l) => l.code === translateTo)?.tts ?? 'en-US';
                const UtteranceCtor = webAny.window.SpeechSynthesisUtterance;
                if (!UtteranceCtor) {
                    setInterCallStatus('브라우저 TTS를 사용할 수 없습니다.');
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
                setInterCallStatus('통역 통화 처리 중 오류가 발생했습니다.');
            }
        };
        recognizer.onerror = () => {
            if (interCallActiveRef.current) {
                setInterCallStatus('음성 인식 오류. 다시 시도하세요.');
            }
        };
        recognizer.start();
    }, [fromLang, toLang, getLangLabel]);

    const handleInterCallToggle = useCallback(async () => {
        if (interCallActiveRef.current) {
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
                setInterCallStatus('📞 다이얼 패드가 열렸습니다. 통화 연결 후 수동 통역 모드를 사용하세요.');
            } else {
                setInterCallStatus('📞 모바일 수동 통역 모드: 전화번호를 입력하거나 호텔을 선택하면 다이얼 패드를 열 수 있습니다.');
            }
        }
    }, [startInterCallCycleWeb, interCallPhone, bookingResult, selectedBookingPlace, startPstnAssistDialFlow]);

    const currentFromLabel = getLangLabel(fromLang);
    const currentToLabel = getLangLabel(toLang);

    const handleSelectLanguage = useCallback((code: LangCode) => {
        if (langPickerFor === 'from') {
            setFromLang(code);
        }
        if (langPickerFor === 'to') {
            setToLang(code);
        }
        setLangPickerFor(null);
    }, [langPickerFor]);

    return (
        <SafeAreaView style={styles.root}>
            <StatusBar style="light" />
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
                {/* ── 헤더 + 로그인(내정보) ── */}
                <View style={styles.header}>
                    <Text style={styles.title}>나도통역사</Text>
                    <Text style={styles.subtitle}>{getUiText(fromLang).subtitle}</Text>
                    <View style={styles.versionPillRow}>
                        <View style={styles.versionPill}>
                            <Text style={styles.versionPillText}>{APP_VERSION_LABEL}</Text>
                        </View>
                        <Pressable style={styles.voipLaunchBtn} onPress={handleHeaderVoipLaunchPress}>
                            <Text style={styles.voipLaunchBtnText}>📞 VoIP 테스트</Text>
                        </Pressable>
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
                                <Pressable style={styles.myInfoBtn} onPress={() => setShowMyInfo((v) => !v)}>
                                    <Text style={styles.myInfoBtnText}>👤 {userInfo.username || userInfo.email.split('@')[0]}</Text>
                                </Pressable>
                                <Pressable style={styles.myInfoBtn} onPress={() => setShowFriendFolder(true)}>
                                    <Text style={styles.myInfoBtnText}>👥 친구</Text>
                                </Pressable>
                                <Pressable style={styles.logoutBtn} onPress={handleLogout}>
                                    <Text style={styles.logoutBtnText}>로그아웃</Text>
                                </Pressable>
                            </>
                        ) : (
                            <Pressable style={styles.loginBtn} onPress={handlePressLoginButton}>
                                <Text style={styles.loginBtnText}>🔐 로그인</Text>
                            </Pressable>
                        )}
                    </View>
                    {showMyInfo && userInfo && (
                        <View style={styles.myInfoPanel}>
                            <Text style={styles.myInfoTitle}>내 정보</Text>
                            <Text style={styles.myInfoText}>이메일: {userInfo.email}</Text>
                            <Text style={styles.myInfoText}>ID: {userInfo.id}</Text>
                            <Pressable style={styles.inlineActionBtn} onPress={handleShowPurchases}>
                                <Text style={styles.inlineActionBtnText}>{myPurchasesLoading ? '⏳ 불러오는 중...' : myPurchases !== null ? '📋 내역 닫기' : '📋 구매/예약 내역'}</Text>
                            </Pressable>
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

                <View style={styles.sectionCard}>
                    <Text style={styles.sectionTitle}>📞 VoIP 진입 테스트</Text>
                    <Text style={styles.sectionSub}>버전 문자열과 함께 바로 보이스톡 연결 화면을 띄워 실제 통화 진입 플로우를 확인합니다.</Text>
                    <CallModeEntryCard selectedMode={selectedCallMode} onSelect={setCallMode} />
                    <CallModePolicyBanner />
                    <Text style={styles.songModeMetaText}>현재 통화 모드: {callModeLabel}</Text>
                    <View style={styles.voipQuickMetaRow}>
                        <Text style={styles.voipQuickMetaText}>현재 버전: {APP_VERSION_LABEL}</Text>
                        <Text style={styles.voipQuickMetaText}>상태: {token ? '로그인 완료' : '로그인 필요'}</Text>
                    </View>
                    <Pressable style={styles.inlineActionBtn} onPress={handleInlineVoipOpenPress}>
                        <Text style={styles.inlineActionBtnText}>VoIP 화면 열기</Text>
                    </Pressable>
                </View>

                <Modal
                    visible={showVoipTester}
                    transparent
                    animationType="fade"
                    onRequestClose={handleCloseVoipTester}
                >
                    <View style={styles.voipModalOverlay}>
                        <View style={styles.voipModalCard}>
                            {voipCallInitResponse ? (
                                <View style={styles.voipModalScreenWrap}>
                                    <VoIPCallScreen
                                        callInitResponse={voipCallInitResponse}
                                        calleePhone={voipPhone.trim() || VOIP_TEST_DEFAULT_PHONE}
                                        apiBaseUrl={API_BASE}
                                        authToken={token}
                                        localSourceLang={fromLang}
                                        localTargetLang={toLang}
                                        onHangup={handleCloseVoipTester}
                                    />
                                </View>
                            ) : (
                                <PhoneDialer
                                    onCallInitiated={(phoneNumber) => {
                                        setVoipPhone(phoneNumber);
                                        // Trigger call initiation on next render cycle
                                        setTimeout(() => handleStartVoipCall(), 0);
                                    }}
                                    onCancel={handleCloseVoipTester}
                                    isLoading={voipInitLoading}
                                    defaultPhone={voipPhone || VOIP_TEST_DEFAULT_PHONE}
                                />
                            )}
                        </View>
                    </View>
                </Modal>

                <Modal
                    visible={showFriendFolder}
                    transparent
                    animationType="slide"
                    onRequestClose={() => setShowFriendFolder(false)}
                >
                    <View style={styles.voipModalOverlay}>
                        <View style={[styles.voipModalCard, { paddingTop: 0 }]}>
                            <View style={styles.modalCloseRow}>
                                <Pressable onPress={() => setShowFriendFolder(false)} style={styles.friendModalCloseBtn}>
                                    <Text style={styles.friendModalCloseBtnText}>✕ 닫기</Text>
                                </Pressable>
                            </View>
                            {userInfo ? (
                                <FriendFolderScreen userId={userInfo.id} token={token ?? ''} />
                            ) : null}
                        </View>
                    </View>
                </Modal>

                {/* ── 원본 언어 ── */}
                <View style={styles.labelRow}>
                    <Text style={styles.label}>{getUiText(fromLang).sourceLang}</Text>
                    <Pressable style={styles.gpsBtn} onPress={() => { void handleDetectLangByGPS(false); }}>
                        <Text style={styles.gpsBtnText}>{gpsLangLoading ? '⏳ 위치 확인 중...' : '📍 현재 위치 확인'}</Text>
                    </Pressable>
                </View>
                {gpsStatus ? <Text style={styles.gpsStatusText}>{gpsStatus}</Text> : null}
                <Pressable style={styles.langPickerTrigger} onPress={() => setLangPickerFor('from')}>
                    <Text style={styles.langPickerValue}>{currentFromLabel}</Text>
                    <Text style={styles.langPickerHint}>선택</Text>
                </Pressable>

                {/* ── 입력 영역 ── */}
                <View style={styles.inputBox}>
                    <TextInput
                        style={styles.textInput}
                        multiline
                        placeholder={getUiText(fromLang).inputPlaceholder}
                        placeholderTextColor={C.sub}
                        value={inputText}
                        onChangeText={setInputText}
                    />
                    <View style={styles.inputBtnRow}>
                        {/* 음성 입력 버튼: 모바일/웹 공통 */}
                        <Pressable
                            style={[styles.voiceMicBtn, isVoiceRecording && styles.voiceMicBtnActive]}
                            onPress={isVoiceRecording ? () => { void stopVoiceInput({ suppressAutoRestart: true }); } : () => { void startVoiceInput(); }}
                            disabled={voiceSttLoading}
                        >
                            <Text style={styles.speakIcon}>
                                {voiceSttLoading ? '⏳' : isVoiceRecording ? '⏹️' : '🎤'}
                            </Text>
                        </Pressable>
                        {inputText.length > 0 && (
                            <Pressable style={styles.speakBtn} onPress={() => handleSpeak(inputText, fromLang)}>
                                <Text style={styles.speakIcon}>🔊</Text>
                            </Pressable>
                        )}
                    </View>
                </View>

                {/* ── 스왑 버튼(수동 번역 버튼 숨김) ── */}
                <View style={styles.actionRow}>
                    <Pressable style={styles.swapBtn} onPress={handleSwap}>
                        <Text style={styles.swapText}>{getUiText(fromLang).swap}</Text>
                    </Pressable>
                </View>

                {Platform.OS !== 'web' && (
                    <View style={styles.autoVoiceModeWrap}>
                        <Pressable
                            style={[styles.inlineActionBtn, autoVoiceModeEnabled && styles.inlineActionBtnActive]}
                            onPress={() => { void handleToggleAutoVoiceMode(); }}
                        >
                            <Text style={[styles.inlineActionBtnText, autoVoiceModeEnabled && styles.inlineActionBtnTextActive]}>
                                {autoVoiceModeEnabled ? '🎙️ 자동 음성 번역 ON' : '🎙️ 자동 음성 번역 OFF'}
                            </Text>
                        </Pressable>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                            {AUTO_RELAY_DELAY_OPTIONS_MS.map((optionMs) => (
                                <Pressable
                                    key={`main-auto-relay-${optionMs}`}
                                    style={[styles.railBtn, autoRelayDelayMs === optionMs && styles.railBtnActive]}
                                    onPress={() => setAutoRelayDelayMs(optionMs)}
                                >
                                    <Text style={[styles.railBtnText, autoRelayDelayMs === optionMs && styles.railBtnTextActive]}>
                                        {formatAutoRelayDelayLabel(optionMs)}
                                    </Text>
                                </Pressable>
                            ))}
                        </ScrollView>
                    </View>
                )}

                {/* ── 번역 언어 ── */}
                <Text style={styles.label}>{getUiText(fromLang).targetLang}</Text>
                <Pressable style={styles.langPickerTrigger} onPress={() => setLangPickerFor('to')}>
                    <Text style={styles.langPickerValue}>{currentToLabel}</Text>
                    <Text style={styles.langPickerHint}>선택</Text>
                </Pressable>

                <Modal
                    visible={langPickerFor !== null}
                    transparent
                    animationType="fade"
                    onRequestClose={() => setLangPickerFor(null)}
                >
                    <Pressable style={styles.langModalOverlay} onPress={() => setLangPickerFor(null)}>
                        <Pressable style={styles.langModalCard} onPress={() => { }}>
                            <Text style={styles.langModalTitle}>
                                {langPickerFor === 'from' ? getUiText(fromLang).sourceLang : getUiText(fromLang).targetLang}
                            </Text>
                            <ScrollView style={styles.langModalList}>
                                {LANGS.map((l) => {
                                    const active = langPickerFor === 'from' ? fromLang === l.code : toLang === l.code;
                                    return (
                                        <Pressable
                                            key={`lang-option-${l.code}`}
                                            style={[styles.langModalOption, active && styles.langModalOptionActive]}
                                            onPress={() => handleSelectLanguage(l.code)}
                                        >
                                            <Text style={[styles.langModalOptionText, active && styles.langModalOptionTextActive]}>
                                                {l.label}
                                            </Text>
                                            {active ? <Text style={styles.langModalCheck}>✓</Text> : null}
                                        </Pressable>
                                    );
                                })}
                            </ScrollView>
                            <Pressable style={styles.langModalCloseBtn} onPress={() => setLangPickerFor(null)}>
                                <Text style={styles.langModalCloseText}>닫기</Text>
                            </Pressable>
                        </Pressable>
                    </Pressable>
                </Modal>

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

                {/* ── 오프라인 안내 ── */}
                {offline && (
                    <View style={styles.offlineBanner}>
                        <Text style={styles.offlineText}>
                            {getUiText(fromLang).offlineMsg}
                        </Text>
                    </View>
                )}

                <View style={styles.sectionCard}>
                    <Text style={styles.sectionTitle}>🎵 노래 전용 모드</Text>
                    <Text style={styles.sectionSub}>가사 필터링 · 구간 반복 감지 · 24개국 양방 가사번역 자막 · 음성/문자 기반 언어 자동 감지</Text>
                    <View style={styles.songModeActionRow}>
                        <Pressable style={[styles.interToggleBtn, songModeEnabled && styles.interToggleBtnActive]} onPress={() => setSongModeEnabled((prev) => !prev)}>
                            <Text style={[styles.interToggleText, songModeEnabled && styles.interToggleTextActive]}>
                                {songModeEnabled ? '🎵 노래 모드 ON' : '🎵 노래 모드 OFF'}
                            </Text>
                        </Pressable>
                        <Pressable style={[styles.inlineGhostBtn, songFileLoading && styles.inlineGhostBtnDisabled]} onPress={handlePickSongFile} disabled={songFileLoading}>
                            <Text style={styles.inlineGhostBtnText}>{songFileLoading ? '파일 처리 중' : '노래 파일 선택'}</Text>
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

                {/* 통역 통화 모드 */}
                <View style={styles.sectionCard}>
                    <Text style={styles.sectionTitle}>📞 통역 통화 모드</Text>
                    <Text style={styles.sectionSub}>{getLangLabel(fromLang)} ⇄ {getLangLabel(toLang)}</Text>
                    <Pressable style={[styles.interToggleBtn, interCallActive && styles.interToggleBtnActive]} onPress={handleInterCallToggle}>
                        <Text style={[styles.interToggleText, interCallActive && styles.interToggleTextActive]}>
                            {interCallActive ? '📵 통역 통화 종료' : '📞 통역 통화 시작'}
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

                {/* 주변 검색 레일 */}
                <View style={styles.sectionCard}>
                    <Text style={styles.sectionTitle}>📍 주변 검색</Text>
                    <Text style={styles.sectionSub}>좌표/카테고리/반경을 선택해 주변 장소를 조회합니다.</Text>

                    <View style={styles.coordRow}>
                        <View style={styles.coordField}>
                            <Text style={styles.coordLabel}>위도</Text>
                            <TextInput style={styles.compactInput} value={lat} onChangeText={setLat} />
                        </View>
                        <View style={styles.coordField}>
                            <Text style={styles.coordLabel}>경도</Text>
                            <TextInput style={styles.compactInput} value={lon} onChangeText={setLon} />
                        </View>
                    </View>

                    <Text style={styles.label}>카테고리</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                        {CATEGORY_OPTIONS.map((item) => (
                            <Pressable
                                key={item.value}
                                style={[styles.railBtn, nearbyCategory === item.value && styles.railBtnActive]}
                                onPress={() => setNearbyCategory(item.value)}
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
                            >
                                <Text style={[styles.railBtnText, radiusM === item.value && styles.railBtnTextActive]}>{item.label}</Text>
                            </Pressable>
                        ))}
                    </ScrollView>

                    <Pressable style={[styles.translateBtn, nearbyLoading && styles.translateBtnDisabled]} onPress={handleSearchNearby} disabled={nearbyLoading}>
                        {nearbyLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>주변 장소 찾기</Text>}
                    </Pressable>

                    {nearbyError ? <Text style={styles.errorText}>{nearbyError}</Text> : null}

                    {nearbyPlaces.length > 0 && (
                        <View style={styles.nearbyListWrap}>
                            {nearbyPlaces.map((place) => (
                                <View key={place.id} style={styles.placeItem}>
                                    <Text style={styles.placeName}>{place.name}</Text>
                                    <Text style={styles.placeMeta}>{place.category_label} · {formatDistance(place.distance_m)} · ★ {Number(place.rating).toFixed(1)}</Text>
                                    <Text style={styles.placeAddr}>{place.address}</Text>
                                    <View style={styles.placeActionRow}>
                                        <Pressable style={styles.inlineActionBtn} onPress={() => Linking.openURL(place.google_maps_url)}>
                                            <Text style={styles.inlineActionBtnText}>Google 지도</Text>
                                        </Pressable>
                                        {place.booking_supported && (place.category === 'hotel' || place.category === 'airport') && (
                                            <Pressable style={[styles.inlineActionBtn, selectedBookingPlaceId === place.id && styles.inlineActionBtnActive]} onPress={() => setSelectedBookingPlaceId(place.id)}>
                                                <Text style={[styles.inlineActionBtnText, selectedBookingPlaceId === place.id && styles.inlineActionBtnTextActive]}>예약 선택</Text>
                                            </Pressable>
                                        )}
                                    </View>
                                </View>
                            ))}
                        </View>
                    )}
                </View>

                {/* 여행 예약 레일 */}
                <View style={styles.sectionCard}>
                    <Text style={styles.sectionTitle}>🧳 여행 예약</Text>
                    <Text style={styles.sectionSub}>예약 가능한 호텔/공항을 선택해 예약 요청을 진행합니다.</Text>

                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                        {nearbyPlaces
                            .filter((place) => (place.category === 'hotel' || place.category === 'airport') && place.booking_supported)
                            .map((place) => (
                                <Pressable
                                    key={`booking-rail-${place.id}`}
                                    style={[styles.hotelRailBtn, selectedBookingPlaceId === place.id && styles.hotelRailBtnActive]}
                                    onPress={() => setSelectedBookingPlaceId(place.id)}
                                >
                                    <Text style={styles.hotelRailName}>{place.name}</Text>
                                    <Text style={styles.hotelRailMeta}>{place.category_label} · {place.price_tier} · ★ {Number(place.rating).toFixed(1)}</Text>
                                </Pressable>
                            ))}
                    </ScrollView>

                    {selectedBookingPlace ? (
                        <View style={styles.selectedHotelBox}>
                            <Text style={styles.selectedHotelName}>{selectedBookingPlace.name}</Text>
                            <Text style={styles.placeAddr}>{selectedBookingPlace.address}</Text>
                            {selectedBookingPlace.phone ? (
                                <Pressable style={styles.inlineActionBtn} onPress={() => { void openDialPad(selectedBookingPlace.phone); }}>
                                    <Text style={styles.inlineActionBtnText}>📞 {selectedBookingPlace.category === 'airport' ? '공항 예약센터' : '호텔'} 전화 예약</Text>
                                </Pressable>
                            ) : null}
                        </View>
                    ) : (
                        <Text style={styles.sectionSub}>주변검색 결과에서 예약 가능한 호텔/공항을 먼저 선택하세요.</Text>
                    )}

                    <TextInput style={styles.compactInput} placeholder="예약자명" placeholderTextColor={C.sub} value={bookingName} onChangeText={setBookingName} />
                    <View style={styles.coordRow}>
                        <View style={styles.coordField}>
                            <Text style={styles.coordLabel}>체크인(YYYY-MM-DD)</Text>
                            <TextInput style={styles.compactInput} value={checkinDate} onChangeText={setCheckinDate} />
                        </View>
                        <View style={styles.coordField}>
                            <Text style={styles.coordLabel}>체크아웃(YYYY-MM-DD)</Text>
                            <TextInput style={styles.compactInput} value={checkoutDate} onChangeText={setCheckoutDate} />
                        </View>
                    </View>
                    <View style={styles.coordRow}>
                        <View style={styles.coordField}>
                            <Text style={styles.coordLabel}>인원</Text>
                            <TextInput style={styles.compactInput} keyboardType="number-pad" value={String(guests)} onChangeText={(v) => setGuests(Math.max(1, Number(v) || 1))} />
                        </View>
                        <View style={styles.coordField}>
                            <Text style={styles.coordLabel}>객실 수</Text>
                            <TextInput style={styles.compactInput} keyboardType="number-pad" value={String(roomCount)} onChangeText={(v) => setRoomCount(Math.max(1, Number(v) || 1))} />
                        </View>
                    </View>
                    <TextInput
                        style={[styles.compactInput, styles.noteInput]}
                        multiline
                        placeholder="추가 요청사항 (예: 금연실, 늦은 체크인)"
                        placeholderTextColor={C.sub}
                        value={bookingNote}
                        onChangeText={setBookingNote}
                    />

                    <Pressable style={[styles.translateBtn, (bookingLoading || !selectedBookingPlace) && styles.translateBtnDisabled]} onPress={handleReserveBooking} disabled={bookingLoading || !selectedBookingPlace}>
                        {bookingLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>예약 요청 보내기</Text>}
                    </Pressable>

                    {bookingError ? <Text style={styles.errorText}>{bookingError}</Text> : null}

                    {bookingResult && (
                        <View style={styles.successBox}>
                            <Text style={styles.successTitle}>예약 확인번호 {bookingResult.confirmation_id}</Text>
                            <Text style={styles.successText}>{bookingResult.booking_message}</Text>
                            <Text style={styles.successText}>{bookingResult.translated_message}</Text>
                            {bookingResult.support_phone ? (
                                <Pressable style={styles.inlineActionBtn} onPress={() => { void openDialPad(bookingResult.support_phone); }}>
                                    <Text style={styles.inlineActionBtnText}>📞 예약센터 통화</Text>
                                </Pressable>
                            ) : null}
                        </View>
                    )}
                </View>

                {/* 결제 레일 */}
                {bookingResult && (
                    <View style={styles.sectionCard}>
                        <Text style={styles.sectionTitle}>💳 결제</Text>
                        <Text style={styles.sectionSub}>
                            결제 예정 금액: {(Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000)) * roomCount * 80000).toLocaleString('ko-KR')}원
                        </Text>
                        {payError ? <Text style={styles.errorText}>{payError}</Text> : null}
                        {purchaseResult ? (
                            <View style={styles.successBox}>
                                <Text style={styles.successTitle}>구매 ID: {purchaseResult.id} · 상태: {purchaseResult.status}</Text>
                                {payUrl ? (
                                    <Pressable style={styles.inlineActionBtn} onPress={() => Linking.openURL(payUrl)}>
                                        <Text style={styles.inlineActionBtnText}>결제 페이지 열기</Text>
                                    </Pressable>
                                ) : (
                                    <Text style={styles.sectionSub}>결제 URL을 불러오는 중...</Text>
                                )}
                            </View>
                        ) : (
                            <Pressable style={[styles.translateBtn, (!token || payLoading) && styles.translateBtnDisabled]} onPress={handlePayment} disabled={!token || payLoading}>
                                {payLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>{token ? '결제 진행하기' : '로그인 후 결제'}</Text>}
                            </Pressable>
                        )}
                    </View>
                )}

                {/* ── 앱 정보 ── */}
                <View style={styles.footer}>
                    <Text style={styles.footerText}>
                        {getUiText(fromLang).footer.replace('\\n', '\n')}
                    </Text>
                </View>

            </ScrollView>

            <Modal visible={showLogin} transparent animationType="fade" onRequestClose={() => setShowLogin(false)}>
                <View style={styles.loginOverlay}>
                    <View style={styles.loginModal}>
                        <Text style={styles.loginModalTitle}>🔐 로그인</Text>
                        <TextInput
                            style={styles.compactInput}
                            placeholder="이메일"
                            placeholderTextColor={C.sub}
                            autoCapitalize="none"
                            keyboardType="email-address"
                            value={loginEmail}
                            onChangeText={setLoginEmail}
                        />
                        <TextInput
                            style={styles.compactInput}
                            placeholder="비밀번호"
                            placeholderTextColor={C.sub}
                            secureTextEntry
                            value={loginPw}
                            onChangeText={setLoginPw}
                        />
                        {loginError ? <Text style={styles.errorText}>{loginError}</Text> : null}
                        <View style={styles.modalActionRow}>
                            <Pressable style={[styles.translateBtn, loginLoading && styles.translateBtnDisabled, styles.modalMainBtn]} onPress={handleLogin} disabled={loginLoading}>
                                {loginLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>로그인</Text>}
                            </Pressable>
                            <Pressable style={styles.modalCloseBtn} onPress={() => setShowLogin(false)}>
                                <Text style={styles.logoutBtnText}>닫기</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
            </Modal>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: C.bg },
    scroll: { padding: 16, paddingBottom: 40 },
    header: { alignItems: 'center', marginBottom: 20, paddingTop: 8 },
    title: { fontSize: 30, fontWeight: '800', color: '#58c9ff', letterSpacing: 0.5 },
    subtitle: { fontSize: 14, color: C.sub, marginTop: 4 },
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
        paddingHorizontal: 12,
        paddingVertical: 7,
    },
    voipLaunchBtnText: { color: '#dff7e7', fontSize: 12, fontWeight: '800' },
    badge: {
        marginTop: 8,
        backgroundColor: C.badge,
        paddingHorizontal: 10,
        paddingVertical: 3,
        borderRadius: 12,
    },
    badgeText: { fontSize: 12, color: C.sub },
    accountRow: { marginTop: 10, flexDirection: 'row', gap: 8 },
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
    langPickerTrigger: {
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        paddingHorizontal: 12,
        paddingVertical: 12,
        marginBottom: 6,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    langPickerValue: { color: C.text, fontSize: 15, fontWeight: '700' },
    langPickerHint: { color: C.sub, fontSize: 13 },
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
        padding: 12,
        marginTop: 8,
        minHeight: 120,
    },
    resultBox: { minHeight: 120 },
    textInput: { flex: 1, color: C.text, fontSize: 16, minHeight: 80, textAlignVertical: 'top' },
    resultText: { color: C.text, fontSize: 16 },
    resultPlaceholder: { color: C.sub, fontSize: 16 },
    speakBtn: { alignSelf: 'flex-end', marginTop: 6 },
    speakIcon: { fontSize: 20 },
    inputBtnRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 },
    voiceMicBtn: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, backgroundColor: C.badge },
    voiceMicBtnActive: { backgroundColor: '#7c1d1d' },
    actionRow: { flexDirection: 'row', gap: 10, marginTop: 12 },
    swapBtn: {
        flex: 1,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        paddingVertical: 12,
        alignItems: 'center',
    },
    swapText: { color: C.sub, fontSize: 14, fontWeight: '600' },
    translateBtn: {
        flex: 2,
        backgroundColor: C.green,
        borderRadius: 10,
        paddingVertical: 12,
        alignItems: 'center',
    },
    translateBtnDisabled: { opacity: 0.6 },
    translateBtnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
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
        marginTop: 16,
        backgroundColor: C.surface,
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 12,
        padding: 12,
    },
    sectionTitle: { color: '#f8fbff', fontSize: 17, fontWeight: '800' },
    sectionSub: { color: C.sub, fontSize: 12, marginTop: 4, marginBottom: 10, lineHeight: 18 },
    voipQuickMetaRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
    voipQuickMetaText: { color: '#91f2b3', fontSize: 12, fontWeight: '700' },
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
        paddingHorizontal: 10,
        paddingVertical: 9,
        marginBottom: 10,
        fontSize: 14,
    },
    noteInput: { minHeight: 78, textAlignVertical: 'top' },
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
    nearbyListWrap: { marginTop: 6, gap: 8 },
    placeItem: {
        backgroundColor: '#0f1623',
        borderWidth: 1,
        borderColor: C.border,
        borderRadius: 10,
        padding: 10,
    },
    placeName: { color: '#e6edf3', fontWeight: '800', fontSize: 14 },
    placeMeta: { color: '#79c0ff', fontSize: 12, marginTop: 4 },
    placeAddr: { color: C.sub, fontSize: 12, marginTop: 4, lineHeight: 17 },
    placeActionRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
    inlineActionBtn: {
        backgroundColor: '#0d2a4a',
        borderWidth: 1,
        borderColor: '#35506c',
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 7,
    },
    inlineActionBtnActive: { backgroundColor: '#153020', borderColor: '#2d6b43' },
    inlineActionBtnText: { color: '#79c0ff', fontSize: 12, fontWeight: '700' },
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
        ...StyleSheet.absoluteFillObject,
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
    loginModalTitle: { color: '#58c9ff', fontSize: 17, fontWeight: '800', marginBottom: 10 },
    modalActionRow: { flexDirection: 'row', gap: 8, marginTop: 6 },
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
    voipModalTitle: { color: '#f8fbff', fontSize: 20, fontWeight: '900', marginBottom: 8 },
    voipModalSub: { color: C.sub, fontSize: 13, lineHeight: 18, marginBottom: 12 },
    footer: { marginTop: 30, alignItems: 'center' },
    footerText: { color: C.sub, fontSize: 11, textAlign: 'center', lineHeight: 18 },
    modalCloseRow: { flexDirection: 'row', justifyContent: 'flex-end', padding: 10 },
    friendModalCloseBtn: { paddingHorizontal: 12, paddingVertical: 6, backgroundColor: '#1e2533', borderRadius: 8 },
    friendModalCloseBtnText: { color: '#94a3b8', fontSize: 13 },
});
