/**
 * VoIP Call Screen Component
 * Manages in-call UI: timer, mute, speaker, hangup buttons
 * Integrates with VoIPCallClient for WebRTC connection
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    ActivityIndicator,
    Linking,
    ScrollView,
    TextInput,
    Platform,
    useWindowDimensions,
} from 'react-native';
import { Audio } from '../compat/expoAvAudio';
import FileSystem from '../compat/expoLegacyFileSystem';
import * as Speech from 'expo-speech';
import Constants from 'expo-constants';
import { VoIPCallClient, CallInitResponse, VoIPChatMessage, VoIPVoiceTranslationMessage } from '../services/voipCallClient';
import { getVoIPToneService } from '../services/voipToneService';
import { resolveVoipTtsLocale } from '../constants/voipLanguageLocales';
import { translateText, voiceTranslate } from '../api/translate';
import { resolveVoipSignalingServerUrl } from '../utils/voipSignalingUrl';
import {
    collapseRepeatedRelayPhrases,
    createInitialVoiceRelaySegmentState,
    createVoiceRelayUtteranceId,
    evaluateVoiceRelaySegmentDecision,
    isLikelyVoiceRelayEcho,
    isLikelySilenceHallucination,
    isLikelyGibberishRelayTranscript,
    isLikelyRepetitionHallucination,
    isVoiceRelaySilenceCapture,
    nextVoiceRelaySegmentStateAfterFlush,
    normalizeRelayText,
    shouldRejectRemoteVoiceRelayPlayback,
    updateVoiceRelaySegmentSpeechState,
    updateVoiceRelaySegmentSpeechStateFromFileRms,
    VOICE_RELAY_MAX_SPEAK_CHARS,
    VOICE_RELAY_VAD_DEFAULTS,
    resolveVoiceRelayFixedFlushDelayMs,
    type VoiceRelaySegmentState,
} from '../features/voip-voice-relay/voiceRelayOrchestrator';
import {
    applyLocalRelayTurn,
    applyRemoteRelayTurn,
    createInitialVoiceRelayTurnSnapshot,
    estimateVoiceRelayPlaybackMs,
    isVoiceRelayListenActive,
    markRemotePlaybackFinished,
    shouldDeferVoiceRelayFlush,
    shouldPlayRemoteVoiceRelay,
    shouldSendVoiceRelaySegment,
    shouldStartVoiceRelayCapture,
    type VoiceRelayTurnSnapshot,
} from '../features/voip-voice-relay/voiceRelayTurnController';
import {
    DESIGNATED_LANGUAGE_MISMATCH_MESSAGE,
    detectedLanguageMatchesDesignated,
    textMatchesDesignatedLanguage,
} from '../features/translation/designatedLanguage';
import {
    estimateRecordingRmsDb,
    mapFileRmsToPseudoMeterDb,
    shouldSkipSilentVoiceRelayStt,
} from '../features/voip-voice-relay/voiceRelayAudioMetrics';
import {
    probeVoiceRelaySileroVadSupport,
    startVoiceRelaySileroVadMonitor,
    stopVoiceRelaySileroVadMonitor,
    subscribeVoiceRelaySileroVadEvents,
    VOICE_RELAY_SILERO_DEFAULTS,
} from '../native/voiceRelaySileroVad';
import {
    resolveSileroSafetyCapDelayMs,
    shouldFlushOnSileroSpeechEnd,
    shouldFlushSileroSafetyCap,
} from '../features/voip-voice-relay/voiceRelaySegmentBoundary';
import { VoiceRelayPlaybackQueue } from '../features/voip-voice-relay/voiceRelayPlaybackQueue';
import type { VoiceRelayChunkMeta, VoiceRelayPlaybackItem } from '../features/voip-voice-relay/types';

type CallChatEntry = {
    id: string;
    fromRole: 'caller' | 'callee';
    text: string;
    sentAt: string;
    clientSentAt?: string;
    isLocal: boolean;
    sourceLang: string;
    targetLang: string;
    translatedText: string;
    translationState: 'pending' | 'done' | 'failed';
    translationEngine?: string;
    translationOffline?: boolean;
    messageId?: string;
    roomId?: string;
    senderLabel?: string;
    senderVoiceId?: string;
};

type CallModeAuditEvent = {
    id: number;
    event_type: string;
    requested_mode: string;
    resolved_mode: string;
    auto_relay_requested: boolean;
    auto_relay_applied: boolean;
    call_route?: string;
    status?: string;
    error_code?: string;
    duration_sec?: number;
    call_quality?: string;
    created_at: string;
    metadata: Record<string, unknown>;
};

type CallVoiceRelayEntry = {
    id: string;
    fromRole: 'caller' | 'callee';
    transcript: string;
    translatedText: string;
    sourceLang: string;
    targetLang: string;
    sentAt: string;
    isLocal: boolean;
    audioUrl?: string;
    audioBase64?: string;
    audioFormat?: string;
};

const CALL_CONNECT_TIMEOUT_MS = 60_000;
const VOICE_RELAY_DUPLICATE_GUARD_MS = 12_000;
const VOICE_RELAY_REMOTE_PLAYBACK_DEDUPE_MS = 4_000;
const VOICE_RELAY_SUPPRESS_MIN_MS = 900;
const VOICE_RELAY_SUPPRESS_CHAR_MS = 45;
const VOICE_RELAY_REMOTE_ECHO_GUARD_MS = 4_000;
const VOICE_RELAY_SPEAKER_ECHO_GUARD_MS = 5_500;
const VOICE_RELAY_SPEECH_METER_MIN_DB = -48;
const VOICE_RELAY_MIN_AUDIO_BASE64_LEN = 3_500;
const VOICE_RELAY_RESTART_DELAY_MS = 220;
const VOICE_RELAY_PLAYBACK_SUPPRESS_MAX_MS = 4_500;
const VOICE_RELAY_METER_UNAVAILABLE_POLLS = 5;
const VOICE_RELAY_REMOTE_ECHO_DEDUPE_MS = 12_000;
const VOICE_RELAY_CONNECTED_GRACE_MS = 3_000;
const REMOTE_AUDIO_DETECT_WARN_MS = 45_000;

const buildVoiceRelayRecordingOptions = (): Audio.RecordingOptions => ({
    isMeteringEnabled: true,
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
});
interface VoIPCallScreenProps {
    callInitResponse: CallInitResponse;
    calleePhone: string;
    participantProfile?: {
        nickname: string;
        genderLabel: string;
        countryName: string;
        voiceId: string;
        countryFlag: string;
        preferredLanguage?: string;
    };
    onHangup: (auditEvents?: CallModeAuditEvent[]) => void;
    apiBaseUrl: string;
    authToken: string;
    localSourceLang: string;
    localTargetLang: string;
    regionHint?: string;
}

export const VoIPCallScreen: React.FC<VoIPCallScreenProps> = ({
    callInitResponse,
    calleePhone,
    participantProfile,
    onHangup,
    apiBaseUrl,
    authToken,
    localSourceLang,
    localTargetLang,
    regionHint,
}) => {
    const { height: windowHeight, width: windowWidth } = useWindowDimensions();
    const isCompactHeight = windowHeight < 780;
    const isVeryCompactHeight = windowHeight < 700;
    const isNarrowWidth = windowWidth < 370;
    const headerPaddingVertical = isVeryCompactHeight ? 12 : isCompactHeight ? 16 : 20;
    const sectionPaddingBottom = isVeryCompactHeight ? 8 : 12;
    const timerFontSize = isVeryCompactHeight ? 38 : isCompactHeight ? 46 : 56;
    const chatCardMaxHeight = isVeryCompactHeight ? 220 : isCompactHeight ? 280 : 360;
    const chatInputMaxHeight = isVeryCompactHeight ? 76 : 96;
    const controlsPaddingBottom = Platform.OS === 'ios'
        ? (isVeryCompactHeight ? 14 : 20)
        : (isVeryCompactHeight ? 12 : 20);
    const hangupButtonMinHeight = isVeryCompactHeight ? 52 : 56;
    const controlButtonMinHeight = isVeryCompactHeight ? 62 : isCompactHeight ? 68 : 76;
    const participantRole = callInitResponse.participant_role || 'caller';
    const appBuildCode = Number(Constants.expoConfig?.android?.versionCode ?? Constants.nativeBuildVersion ?? 0);
    const appVersionName = String(Constants.expoConfig?.version ?? Constants.nativeAppVersion ?? '');
    const voiceRelayServerReady = Boolean(
        callInitResponse.auto_relay_applied || callInitResponse.resolved_mode === 'voip_full_auto',
    );

    useEffect(() => {
        console.log('[VoIPScreen] Voice relay readiness:', {
            callId: callInitResponse.call_id,
            requestedMode: callInitResponse.requested_mode,
            resolvedMode: callInitResponse.resolved_mode,
            autoRelayRequested: callInitResponse.auto_relay_requested,
            autoRelayApplied: callInitResponse.auto_relay_applied,
            voiceRelayServerReady,
        });
    }, [
        callInitResponse.auto_relay_applied,
        callInitResponse.auto_relay_requested,
        callInitResponse.call_id,
        callInitResponse.requested_mode,
        callInitResponse.resolved_mode,
        voiceRelayServerReady,
    ]);

    const [voipClient, setVoipClient] = useState<VoIPCallClient | null>(null);
    const [connectionState, setConnectionState] = useState<string>('connecting');
    const [callDuration, setCallDuration] = useState<number>(0);
    const [isMuted, setIsMuted] = useState<boolean>(false);
    const [isSpeakerOn, setIsSpeakerOn] = useState<boolean>(false);
    const isSpeakerOnRef = useRef<boolean>(false);
    const [hasRemoteAudio, setHasRemoteAudio] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [chatDraft, setChatDraft] = useState<string>('');
    const [chatError, setChatError] = useState<string | null>(null);
    const [chatEntries, setChatEntries] = useState<CallChatEntry[]>([]);
    const [voiceRelayEnabled, setVoiceRelayEnabled] = useState<boolean>(false);
    const [voiceRelaySuggestionVisible, setVoiceRelaySuggestionVisible] = useState<boolean>(false);
    const [voiceRelayRecording, setVoiceRelayRecording] = useState<boolean>(false);
    const [voiceRelayBusy, setVoiceRelayBusy] = useState<boolean>(false);
    const [voiceRelayMeterDead, setVoiceRelayMeterDead] = useState<boolean>(false);
    const [voiceRelayListenWaiting, setVoiceRelayListenWaiting] = useState<boolean>(false);
    const [voiceRelaySileroActive, setVoiceRelaySileroActive] = useState<boolean>(false);
    const [voiceRelayError, setVoiceRelayError] = useState<string | null>(null);
    const [voiceRelayEntries, setVoiceRelayEntries] = useState<CallVoiceRelayEntry[]>([]);
    const [lastRelayDeliveryHint, setLastRelayDeliveryHint] = useState<string | null>(null);
    const [lastTranslationProbe, setLastTranslationProbe] = useState<string>('');
    const [auditEvents, setAuditEvents] = useState<CallModeAuditEvent[]>([]);
    const [auditManualRefreshing, setAuditManualRefreshing] = useState<boolean>(false);
    const [auditError, setAuditError] = useState<string | null>(null);
    const auditEventsRef = useRef<CallModeAuditEvent[]>([]);
    const loadAuditEventsRef = useRef<(options?: { showLoading?: boolean; force?: boolean }) => Promise<CallModeAuditEvent[]>>(() => Promise.resolve([]));
    const startVoiceRelaySegmentRef = useRef<() => Promise<void>>(async () => {});
    const flushVoiceRelaySegmentRef = useRef<(reason: string, isFinal: boolean) => Promise<void>>(async () => {});
    const isVoiceRelayCallReadyRef = useRef<() => boolean>(() => false);
    const auditFetchInFlightRef = useRef<boolean>(false);
    const auditLoadedCallIdRef = useRef<string | null>(null);
    const apiBaseUrlRef = useRef(apiBaseUrl);
    const authTokenRef = useRef(authToken);
    const callIdRef = useRef(callInitResponse.call_id);
    apiBaseUrlRef.current = apiBaseUrl;
    authTokenRef.current = authToken;
    callIdRef.current = callInitResponse.call_id;
    auditEventsRef.current = auditEvents;
    const hasLoggedConnectedRef = useRef<boolean>(false);
    const timeoutAutoReturnRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const forcedTerminalStateRef = useRef<'failed' | null>(null);
    const connectionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const remoteAudioTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voipClientRef = useRef<VoIPCallClient | null>(null);
    const voiceRelayRecordingRef = useRef<Audio.Recording | null>(null);
    const voiceRelayPlaybackRef = useRef<Audio.Sound | null>(null);
    const voiceRelayPlaybackFileRef = useRef<string | null>(null);
    const voiceRelayStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayRestartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayProcessingRef = useRef<boolean>(false);
    const voiceRelayEnabledRef = useRef<boolean>(false);
    const voiceRelaySuggestionShownRef = useRef<boolean>(false);
    const voiceRelayAutoStartedRef = useRef<boolean>(false);
    const voiceRelaySuppressUntilRef = useRef<number>(0);
    const lastVoiceRelayKeyRef = useRef<string>('');
    const lastVoiceRelayAtRef = useRef<number>(0);
    const lastRemoteRelayTranscriptRef = useRef<string>('');
    const lastRemoteRelayAtRef = useRef<number>(0);
    const lastRemotePlaybackKeyRef = useRef<string>('');
    const lastRemotePlaybackAtRef = useRef<number>(0);
    const voiceRelayPeakMeteringRef = useRef<number>(-160);
    const connectedAtRef = useRef<number | null>(null);
    const voiceRelayMeterPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const voiceRelayFixedFlushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayMeterPollMissesRef = useRef<number>(0);
    const voiceRelayMeterUnavailableRef = useRef<boolean>(false);
    const voiceRelayFileRmsPollTickRef = useRef<number>(0);
    const voiceRelaySileroActiveRef = useRef<boolean>(false);
    const voiceRelaySileroSupportedRef = useRef<boolean>(false);
    const voiceRelaySileroFirstSpeechAtMsRef = useRef<number | null>(null);
    const voiceRelaySileroLastFlushAtMsRef = useRef<number | null>(null);
    const voiceRelayLastFlushReasonRef = useRef<string | null>(null);
    const voiceRelayLastFlushHadSpeechRef = useRef<boolean>(false);
    const voiceRelayLastSegmentDurationMsRef = useRef<number>(0);
    const voiceRelayTurnRef = useRef<VoiceRelayTurnSnapshot>(createInitialVoiceRelayTurnSnapshot());
    const voiceRelayAbortGenerationRef = useRef<number>(0);
    const scheduleVoiceRelayCaptureRetryRef = useRef<(retryReason: string) => void>(() => {});
    const lastLocalRelayTranslatedRef = useRef<string>('');
    const lastLocalRelaySentAtRef = useRef<number>(0);
    const lastRemotePlaybackTranslatedRef = useRef<string>('');
    const lastRemotePlaybackTranslatedAtRef = useRef<number>(0);

    const restoreWebRtcMicIfVoiceRelayInactive = useCallback(async (reason: string) => {
        if (voiceRelayEnabledRef.current) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_WEBRTC_LOCAL_AUDIO_KEEP_SUSPENDED',
                call_id: callInitResponse.call_id,
                reason,
                timestamp: new Date().toISOString(),
            }));
            return;
        }
        try {
            await voipClientRef.current?.restoreLocalAudioAfterVoiceRelay();
        } catch (restoreErr) {
            console.warn('[VoIPScreen] Failed to restore WebRTC mic after voice relay', restoreErr);
        }
    }, [callInitResponse.call_id]);
    const voiceRelayRecordingRemoteSuppressedRef = useRef<boolean>(false);
    const hasRemoteAudioRef = useRef<boolean>(false);
    const remoteAudioSuppressedRef = useRef<boolean>(false);
    const chatScrollRef = useRef<ScrollView | null>(null);
    const voiceRelaySegmentStateRef = useRef<VoiceRelaySegmentState>(
        createInitialVoiceRelaySegmentState(Date.now()),
    );
    const voiceRelayUtteranceIdRef = useRef<string>(
        createVoiceRelayUtteranceId(callInitResponse.call_id),
    );
    const voiceRelayChunkMetaRef = useRef<Pick<VoiceRelayChunkMeta, 'utteranceId' | 'chunkIndex' | 'isFinal'> | null>(null);
    const voiceRelayFlushInProgressRef = useRef<boolean>(false);
    const voiceRelaySeqRef = useRef<number>(0);
    const voiceRelayPlaybackQueueRef = useRef<VoiceRelayPlaybackQueue | null>(null);
    const errorRef = useRef<string | null>(null);
    const voipCallInitHandlersRef = useRef<{
        syncRemoteAudioState: () => boolean;
        appendChatEntry: (entry: CallChatEntry) => void;
        appendVoiceRelayEntry: (entry: CallVoiceRelayEntry) => void;
        resolveChatLanguagePair: (isLocalSpeaker: boolean) => { sourceLang: string; targetLang: string };
        enqueueVoiceRelayPlayback: (item: VoiceRelayPlaybackItem) => void;
        nextVoiceRelaySeqId: () => number;
        stopVoiceRelaySegment: (processSegment: boolean) => Promise<void>;
        stopVoiceRelayPlayback: () => Promise<void>;
        participantRole: 'caller' | 'callee';
        localSourceLang: string;
        localTargetLang: string;
    } | null>(null);

    useEffect(() => {
        errorRef.current = error;
    }, [error]);

    const isVoiceRelayCallReady = useCallback((): boolean => {
        if (connectionState !== 'connected') {
            return false;
        }
        if (hasRemoteAudio) {
            return true;
        }
        const activeClient = voipClientRef.current;
        if (activeClient?.hasRemoteAudioTrack?.()) {
            return true;
        }
        return (
            connectedAtRef.current != null
            && Date.now() - connectedAtRef.current >= VOICE_RELAY_CONNECTED_GRACE_MS
        );
    }, [connectionState, hasRemoteAudio]);

    isVoiceRelayCallReadyRef.current = isVoiceRelayCallReady;

    const syncRemoteAudioState = useCallback((): boolean => {
        const activeClient = voipClientRef.current;
        const state = activeClient?.getConnectionState?.() ?? 'connecting';
        if (state !== 'connected') {
            connectedAtRef.current = null;
            setHasRemoteAudio(false);
            return false;
        }
        if (connectedAtRef.current == null) {
            connectedAtRef.current = Date.now();
        }
        const detected = activeClient?.hasRemoteAudioTrack?.() ?? false;
        const graceReady = Date.now() - connectedAtRef.current >= VOICE_RELAY_CONNECTED_GRACE_MS;
        const ready = detected || graceReady;
        setHasRemoteAudio(ready);
        return ready;
    }, []);

    const loadAuditEvents = useCallback(async (options?: { showLoading?: boolean; force?: boolean }): Promise<CallModeAuditEvent[]> => {
        const showLoading = options?.showLoading ?? false;
        const force = options?.force ?? false;
        if (auditFetchInFlightRef.current && !force) {
            return auditEventsRef.current;
        }

        auditFetchInFlightRef.current = true;
        if (showLoading) {
            setAuditManualRefreshing(true);
        }
        setAuditError(null);
        try {
            const response = await fetch(`${apiBaseUrlRef.current}/api/v1/voip/calls/${callIdRef.current}/audit`, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${authTokenRef.current}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`audit fetch failed: HTTP ${response.status}`);
            }

            const payload = await response.json();
            const events = Array.isArray(payload) ? (payload as CallModeAuditEvent[]) : [];
            setAuditEvents(events);
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_CALL_MODE_AUDIT_LOADED',
                call_id: callIdRef.current,
                event_count: events.length,
                event_types: events.map((event) => event.event_type),
                show_loading: showLoading,
                timestamp: new Date().toISOString(),
            }));
            return events;
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setAuditError(message);
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_CALL_MODE_AUDIT_FAILED',
                call_id: callIdRef.current,
                error_message: message,
                timestamp: new Date().toISOString(),
            }));
            return [];
        } finally {
            auditFetchInFlightRef.current = false;
            if (showLoading) {
                setAuditManualRefreshing(false);
            }
        }
    }, []);

    loadAuditEventsRef.current = loadAuditEvents;

    const updateChatTranslation = useCallback((entryId: string, patch: Partial<CallChatEntry>) => {
        setChatEntries((prev) => prev.map((entry) => (entry.id === entryId ? { ...entry, ...patch } : entry)));
    }, []);

    const resolveChatLanguagePair = useCallback((isLocal: boolean) => {
        if (isLocal) {
            return { sourceLang: localSourceLang, targetLang: localTargetLang };
        }
        return { sourceLang: localTargetLang, targetLang: localSourceLang };
    }, [localSourceLang, localTargetLang]);

    const translateChatEntry = useCallback(async (entryId: string, text: string, sourceLang: string, targetLang: string) => {
        if (!text.trim()) {
            updateChatTranslation(entryId, { translatedText: '', translationState: 'failed' });
            return;
        }

        if (sourceLang === targetLang) {
            updateChatTranslation(entryId, {
                translatedText: text,
                translationState: 'done',
                translationEngine: 'same-language',
                translationOffline: false,
            });
            return;
        }

        try {
            const probePayload = {
                event: 'VOIP_CHAT_TRANSLATE_REQUEST',
                call_id: callInitResponse.call_id,
                source_lang: sourceLang,
                target_lang: targetLang,
                region_hint: regionHint || null,
                text_preview: text.trim().slice(0, 80),
                timestamp: new Date().toISOString(),
            };
            const probeText = JSON.stringify(probePayload);
            console.log('[UI_PRESS_PROBE]', probeText);
            setLastTranslationProbe(probeText);

            const result = await translateText(text, sourceLang, targetLang, 8000, { regionHint });
            updateChatTranslation(entryId, {
                translatedText: result.translated,
                translationState: 'done',
                translationEngine: result.engine,
                translationOffline: result.offline,
            });
        } catch {
            updateChatTranslation(entryId, {
                translatedText: text,
                translationState: 'failed',
                translationEngine: 'failed',
                translationOffline: true,
            });
        }
    }, [callInitResponse.call_id, regionHint, updateChatTranslation]);

    const appendChatEntry = useCallback((entry: CallChatEntry) => {
        let shouldTranslate = false;
        let translateEntryId: string | null = null;
        setChatEntries((prev) => {
            const matchedIndex = prev.findIndex((item) => {
                if (entry.messageId && item.messageId && item.messageId === entry.messageId) {
                    return true;
                }

                if (entry.clientSentAt) {
                    return item.fromRole === entry.fromRole
                        && item.text === entry.text
                        && (item.clientSentAt === entry.clientSentAt || item.sentAt === entry.clientSentAt);
                }

                return item.fromRole === entry.fromRole && item.sentAt === entry.sentAt && item.text === entry.text;
            });

            if (matchedIndex >= 0) {
                const existing = prev[matchedIndex];
                const mergedEntry: CallChatEntry = {
                    ...existing,
                    ...entry,
                    id: existing.id,
                    clientSentAt: entry.clientSentAt ?? existing.clientSentAt,
                };
                const next = [...prev];
                next[matchedIndex] = mergedEntry;
                if (!mergedEntry.isLocal && mergedEntry.translationState === 'pending' && !mergedEntry.translatedText) {
                    shouldTranslate = true;
                    translateEntryId = mergedEntry.id;
                }
                return next;
            }

            shouldTranslate = !entry.isLocal && entry.translationState === 'pending' && !entry.translatedText;
            translateEntryId = entry.id;
            return [...prev, entry];
        });

        if (shouldTranslate && translateEntryId) {
            void translateChatEntry(translateEntryId, entry.text, entry.sourceLang, entry.targetLang);
        }
    }, [translateChatEntry]);

    const appendVoiceRelayEntry = useCallback((entry: CallVoiceRelayEntry) => {
        setVoiceRelayEntries((prev) => {
            if (prev.some((item) => item.fromRole === entry.fromRole && item.sentAt === entry.sentAt && item.transcript === entry.transcript)) {
                return prev;
            }
            return [...prev, entry].slice(-6);
        });
    }, []);

    const resolveVoiceRelayAudioUrl = useCallback((audioUrl?: string) => {
        if (!audioUrl) {
            return undefined;
        }
        if (/^https?:\/\//i.test(audioUrl)) {
            return audioUrl;
        }
        if (audioUrl.startsWith('/')) {
            return `${apiBaseUrl}${audioUrl}`;
        }
        return `${apiBaseUrl}/${audioUrl.replace(/^\/+/, '')}`;
    }, [apiBaseUrl]);

    const resolveTtsLanguage = useCallback((langCode: string) => {
        return resolveVoipTtsLocale(langCode);
    }, []);

    const clearVoiceRelayTimers = useCallback(() => {
        if (voiceRelayStopTimerRef.current) {
            clearTimeout(voiceRelayStopTimerRef.current);
            voiceRelayStopTimerRef.current = null;
        }
        if (voiceRelayRestartTimerRef.current) {
            clearTimeout(voiceRelayRestartTimerRef.current);
            voiceRelayRestartTimerRef.current = null;
        }
        if (voiceRelayMeterPollRef.current) {
            clearInterval(voiceRelayMeterPollRef.current);
            voiceRelayMeterPollRef.current = null;
        }
        if (voiceRelayFixedFlushTimerRef.current) {
            clearTimeout(voiceRelayFixedFlushTimerRef.current);
            voiceRelayFixedFlushTimerRef.current = null;
        }
    }, []);

    const stopVoiceRelaySileroMonitor = useCallback(async (reason: string) => {
        if (!voiceRelaySileroActiveRef.current) {
            return;
        }
        voiceRelaySileroActiveRef.current = false;
        setVoiceRelaySileroActive(false);
        await stopVoiceRelaySileroVadMonitor();
        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_VOICE_RELAY_SILERO_STOPPED',
            call_id: callInitResponse.call_id,
            reason,
            timestamp: new Date().toISOString(),
        }));
    }, [callInitResponse.call_id]);

    const startVoiceRelaySileroMonitor = useCallback(async () => {
        if (!voiceRelaySileroSupportedRef.current || voiceRelaySileroActiveRef.current) {
            return;
        }
        try {
            const started = await startVoiceRelaySileroVadMonitor(
                VOICE_RELAY_SILERO_DEFAULTS.silenceMs,
                VOICE_RELAY_SILERO_DEFAULTS.speechMs,
            );
            if (!started) {
                return;
            }
            voiceRelaySileroActiveRef.current = true;
            setVoiceRelaySileroActive(true);
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SILERO_STARTED',
                call_id: callInitResponse.call_id,
                silence_ms: VOICE_RELAY_SILERO_DEFAULTS.silenceMs,
                speech_ms: VOICE_RELAY_SILERO_DEFAULTS.speechMs,
                timestamp: new Date().toISOString(),
            }));
        } catch (err) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SILERO_START_FAILED',
                call_id: callInitResponse.call_id,
                error_message: err instanceof Error ? err.message : String(err),
                timestamp: new Date().toISOString(),
            }));
        }
    }, [callInitResponse.call_id]);

    const stopVoiceRelayPlayback = useCallback(async () => {
        const sound = voiceRelayPlaybackRef.current;
        voiceRelayPlaybackRef.current = null;
        if (!sound) {
            if (voiceRelayPlaybackFileRef.current) {
                try {
                    await FileSystem.deleteAsync(voiceRelayPlaybackFileRef.current, { idempotent: true });
                } catch {
                    // ignore temp cleanup failures
                }
                voiceRelayPlaybackFileRef.current = null;
            }
            return;
        }
        try {
            await sound.stopAsync();
        } catch {
            // ignore stop failures during cleanup
        }
        try {
            await sound.unloadAsync();
        } catch {
            // ignore unload failures during cleanup
        }
        if (voiceRelayPlaybackFileRef.current) {
            try {
                await FileSystem.deleteAsync(voiceRelayPlaybackFileRef.current, { idempotent: true });
            } catch {
                // ignore temp cleanup failures
            }
            voiceRelayPlaybackFileRef.current = null;
        }
    }, []);

    const setRemoteAudioSuppressed = useCallback((suppressed: boolean) => {
        const client = voipClientRef.current;
        if (remoteAudioSuppressedRef.current === suppressed) {
            return;
        }
        remoteAudioSuppressedRef.current = suppressed;
        client?.setRemoteAudioEnabled(!suppressed);
        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_REMOTE_AUDIO_SUPPRESSION',
            call_id: callInitResponse.call_id,
            suppressed,
            timestamp: new Date().toISOString(),
        }));
    }, [callInitResponse.call_id]);

    const releaseRemoteAudioSuppressionIfAllowed = useCallback(() => {
        if (voiceRelayServerReady && voiceRelayEnabledRef.current) {
            return;
        }
        setRemoteAudioSuppressed(false);
    }, [setRemoteAudioSuppressed, voiceRelayServerReady]);

    const finishRemoteVoiceRelayPlayback = useCallback(() => {
        voiceRelayTurnRef.current = markRemotePlaybackFinished(voiceRelayTurnRef.current);
        releaseRemoteAudioSuppressionIfAllowed();
    }, [releaseRemoteAudioSuppressionIfAllowed]);

    const resolvePlaybackExtension = useCallback((audioFormat?: string) => {
        const normalized = String(audioFormat || '').toLowerCase();
        if (normalized.includes('mpeg') || normalized.includes('mp3')) {
            return 'mp3';
        }
        if (normalized.includes('ogg')) {
            return 'ogg';
        }
        if (normalized.includes('aac')) {
            return 'aac';
        }
        return 'wav';
    }, []);

    const playVoiceRelayOutput = useCallback(async (audioUrl: string | undefined, audioBase64: string | undefined, audioFormat: string | undefined, translatedText: string, targetLang: string) => {
        const collapsedText = collapseRepeatedRelayPhrases(translatedText.trim());
        if (!collapsedText || isLikelyRepetitionHallucination(translatedText) || isLikelyRepetitionHallucination(collapsedText)) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_PLAYBACK_SKIPPED',
                call_id: callInitResponse.call_id,
                reason: 'repetition_hallucination',
                translated_length: translatedText.trim().length,
                timestamp: new Date().toISOString(),
            }));
            finishRemoteVoiceRelayPlayback();
            scheduleVoiceRelayCaptureRetryRef.current('playback_complete');
            return;
        }

        const normalizedText = collapsedText.slice(0, VOICE_RELAY_MAX_SPEAK_CHARS);
        const playbackMs = estimateVoiceRelayPlaybackMs(normalizedText, isSpeakerOnRef.current);
        voiceRelaySuppressUntilRef.current = Date.now() + playbackMs + 700;

        await stopVoiceRelayPlayback();
        Speech.stop();
        setRemoteAudioSuppressed(true);
        lastRemotePlaybackTranslatedRef.current = normalizeRelayText(translatedText);
        lastRemotePlaybackTranslatedAtRef.current = Date.now();

        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_VOICE_RELAY_PLAYBACK',
            call_id: callInitResponse.call_id,
            target_lang: targetLang,
            translated_text: normalizedText.slice(0, 120),
            translated_length: normalizedText.length,
            tts_delivery: 'device_speech',
            speaker_on: isSpeakerOnRef.current,
            timestamp: new Date().toISOString(),
        }));

        try {
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: true,
                playThroughEarpieceAndroid: !isSpeakerOnRef.current,
                staysActiveInBackground: false,
            });
        } catch {
            // ignore audio mode failures before device TTS
        }

        await new Promise<void>((resolve) => {
            Speech.speak(normalizedText, {
                language: resolveTtsLanguage(targetLang),
                rate: 0.92,
                pitch: 1.0,
                volume: 1.0,
                onDone: () => {
                    finishRemoteVoiceRelayPlayback();
                    scheduleVoiceRelayCaptureRetryRef.current('playback_complete');
                    resolve();
                },
                onStopped: () => {
                    finishRemoteVoiceRelayPlayback();
                    scheduleVoiceRelayCaptureRetryRef.current('playback_complete');
                    resolve();
                },
                onError: () => {
                    finishRemoteVoiceRelayPlayback();
                    scheduleVoiceRelayCaptureRetryRef.current('playback_complete');
                    resolve();
                },
            });
        });
    }, [callInitResponse.call_id, finishRemoteVoiceRelayPlayback, resolveTtsLanguage, setRemoteAudioSuppressed, stopVoiceRelayPlayback]);

    const enqueueVoiceRelayPlayback = useCallback((item: VoiceRelayPlaybackItem) => {
        if (!voiceRelayPlaybackQueueRef.current) {
            voiceRelayPlaybackQueueRef.current = new VoiceRelayPlaybackQueue(async (queued) => {
                await playVoiceRelayOutput(
                    queued.audioUrl,
                    queued.audioBase64,
                    queued.audioFormat,
                    queued.translatedText,
                    queued.targetLang,
                );
            });
        }
        voiceRelayPlaybackQueueRef.current.enqueue(item);
    }, [playVoiceRelayOutput]);

    const nextVoiceRelaySeqId = useCallback((): number => {
        voiceRelaySeqRef.current += 1;
        return voiceRelaySeqRef.current;
    }, []);

    const scheduleVoiceRelayCaptureRetry = useCallback((retryReason: string) => {
        if (!voiceRelayEnabledRef.current) {
            return;
        }
        if (voiceRelayRestartTimerRef.current) {
            clearTimeout(voiceRelayRestartTimerRef.current);
            voiceRelayRestartTimerRef.current = null;
        }
        const waitMs = Math.max(
            250,
            voiceRelayTurnRef.current.remoteListenUntilMs - Date.now(),
            voiceRelayTurnRef.current.remotePlaybackUntilMs - Date.now(),
            voiceRelaySuppressUntilRef.current - Date.now(),
        );
        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_VOICE_RELAY_CAPTURE_RETRY_SCHEDULED',
            call_id: callInitResponse.call_id,
            retry_reason: retryReason,
            wait_ms: waitMs,
            timestamp: new Date().toISOString(),
        }));
        setVoiceRelayListenWaiting(
            retryReason === 'remote_listen_active'
            || retryReason === 'remote_audio_suppressed'
            || retryReason === 'echo_suppression_window'
            || retryReason === 'playback_complete',
        );
        voiceRelayRestartTimerRef.current = setTimeout(() => {
            voiceRelayRestartTimerRef.current = null;
            setVoiceRelayListenWaiting(false);
            void startVoiceRelaySegmentRef.current();
        }, waitMs);
    }, [callInitResponse.call_id]);

    useEffect(() => {
        scheduleVoiceRelayCaptureRetryRef.current = scheduleVoiceRelayCaptureRetry;
    }, [scheduleVoiceRelayCaptureRetry]);

    const processVoiceRelaySegment = useCallback(async (uri: string) => {
        const segmentStartedAt = Date.now();
        const abortGeneration = voiceRelayAbortGenerationRef.current;

        const shouldAbortRelayProcessing = () => (
            abortGeneration !== voiceRelayAbortGenerationRef.current
            || isVoiceRelayListenActive(voiceRelayTurnRef.current)
        );

        try {
            if (Date.now() < voiceRelaySuppressUntilRef.current || shouldAbortRelayProcessing()) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: shouldAbortRelayProcessing() ? 'listen_or_abort' : 'echo_suppression_window',
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const base64Audio = await FileSystem.readAsStringAsync(uri, {
                encoding: FileSystem.EncodingType.Base64,
            });
            if (shouldAbortRelayProcessing()) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'aborted_before_stt',
                    timestamp: new Date().toISOString(),
                }));
                return;
            }
            if (!base64Audio || base64Audio.length < VOICE_RELAY_MIN_AUDIO_BASE64_LEN) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'audio_payload_too_small',
                    audio_base64_length: base64Audio?.length || 0,
                    segment_duration_ms: voiceRelayLastSegmentDurationMsRef.current,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            if (voiceRelayLastSegmentDurationMsRef.current < VOICE_RELAY_VAD_DEFAULTS.minSegmentMs - 400) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'segment_duration_too_short',
                    segment_duration_ms: voiceRelayLastSegmentDurationMsRef.current,
                    min_segment_ms: VOICE_RELAY_VAD_DEFAULTS.minSegmentMs,
                    flush_reason: voiceRelayLastFlushReasonRef.current,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const meterUnavailable = voiceRelayMeterUnavailableRef.current;
            const flushReason = voiceRelayLastFlushReasonRef.current;
            const flushHadSpeech = voiceRelayLastFlushHadSpeechRef.current;
            const silentSkip = shouldSkipSilentVoiceRelayStt({
                peakMeterDb: voiceRelayPeakMeteringRef.current,
                hasSpeech: voiceRelaySegmentStateRef.current.hasSpeech,
                meterUnavailable,
                audioBase64: base64Audio,
            });
            if (silentSkip.skip) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: silentSkip.reason || 'silent_segment',
                    peak_meter_db: voiceRelayPeakMeteringRef.current,
                    estimated_file_rms_db: silentSkip.estimatedRmsDb,
                    flush_reason: flushReason,
                    meter_unavailable: meterUnavailable,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const sendDecision = shouldSendVoiceRelaySegment({
                participantRole,
                turn: voiceRelayTurnRef.current,
                meterUnavailable,
                flushHadSpeech,
                flushReason,
                peakMeterDb: voiceRelayPeakMeteringRef.current,
                hasRemoteAudio: hasRemoteAudioRef.current,
                remoteAudioSuppressed: remoteAudioSuppressedRef.current,
            });
            if (!sendDecision.allowed) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: sendDecision.reason || 'segment_send_blocked',
                    flush_reason: flushReason,
                    peak_meter_db: voiceRelayPeakMeteringRef.current,
                    meter_unavailable: meterUnavailable,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            voiceRelayProcessingRef.current = true;
            setVoiceRelayBusy(true);
            setVoiceRelayError(null);

            const probePayload = {
                event: 'VOIP_VOICE_TRANSLATE_REQUEST',
                call_id: callInitResponse.call_id,
                source_lang: localSourceLang,
                target_lang: localTargetLang,
                region_hint: regionHint || null,
                audio_base64_length: base64Audio.length,
                timestamp: new Date().toISOString(),
            };
            const probeText = JSON.stringify(probePayload);
            console.log('[UI_PRESS_PROBE]', probeText);
            setLastTranslationProbe(probeText);

            const translateStartedAt = Date.now();
            const result = await voiceTranslate(base64Audio, localSourceLang, localTargetLang, regionHint, 'auto');
            if (shouldAbortRelayProcessing()) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'aborted_after_stt',
                    timestamp: new Date().toISOString(),
                }));
                return;
            }
            const translateDurationMs = Date.now() - translateStartedAt;
            const rawTranscript = String(result.original_text || '').trim();
            const rawTranslatedText = String(result.translated || '').trim();
            if (
                isLikelyRepetitionHallucination(rawTranscript)
                || isLikelyRepetitionHallucination(rawTranslatedText)
            ) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'repetition_hallucination',
                    transcript_length: rawTranscript.length,
                    translated_length: rawTranslatedText.length,
                    flush_reason: voiceRelayLastFlushReasonRef.current,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }
            const transcript = collapseRepeatedRelayPhrases(rawTranscript);
            let translatedText = collapseRepeatedRelayPhrases(rawTranslatedText);
            const detectedLang = String(result.detected_language || result.from || localSourceLang).trim();
            if (
                !detectedLanguageMatchesDesignated(detectedLang, localSourceLang)
                || !textMatchesDesignatedLanguage(transcript, localSourceLang)
            ) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'designated_language_mismatch',
                    designated_lang: localSourceLang,
                    detected_lang: detectedLang,
                    transcript,
                    timestamp: new Date().toISOString(),
                }));
                setVoiceRelayError(DESIGNATED_LANGUAGE_MISMATCH_MESSAGE);
                return;
            }
            const relaySourceLang = localSourceLang;
            const relayTargetLang = localTargetLang;
            const chunkMeta = voiceRelayChunkMetaRef.current ?? {
                utteranceId: voiceRelayUtteranceIdRef.current,
                chunkIndex: voiceRelaySegmentStateRef.current.chunkIndex,
                isFinal: true,
            };
            const relayChunkMeta = {
                ...chunkMeta,
                isFinal: true,
                chunkIndex: 0,
            };
            const seqId = nextVoiceRelaySeqId();
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_TRANSLATE_RESULT',
                call_id: callInitResponse.call_id,
                source_lang: relaySourceLang,
                target_lang: relayTargetLang,
                detected_lang: detectedLang,
                transcript_length: transcript.length,
                translated_length: translatedText.length,
                translate_duration_ms: translateDurationMs,
                segment_duration_ms: Date.now() - segmentStartedAt,
                utterance_id: relayChunkMeta.utteranceId,
                chunk_index: relayChunkMeta.chunkIndex,
                is_final: relayChunkMeta.isFinal,
                seq_id: seqId,
                has_audio_url: !!result.audio_url,
                has_audio_base64: !!result.audio_base64,
                audio_format: result.audio_format || null,
                tts_delivery: result.tts_delivery || null,
                timestamp: new Date().toISOString(),
            }));

            if (!transcript || !translatedText) {
                console.warn('[VoIPScreen] Voice relay translate returned empty payload', {
                    callId: callInitResponse.call_id,
                    sourceLang: localSourceLang,
                    targetLang: localTargetLang,
                    transcriptLength: transcript.length,
                    translatedLength: translatedText.length,
                });
                setVoiceRelayError('음성 통역 결과가 비어 있습니다. 다시 시도해 주세요.');
                return;
            }

            if (String(result.stt_trust || 'high').toLowerCase() === 'low') {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'low_stt_trust',
                    transcript,
                    translated_text: translatedText,
                    stt_avg_logprob: result.stt_avg_logprob ?? null,
                    flush_reason: voiceRelayLastFlushReasonRef.current,
                    peak_meter_db: voiceRelayPeakMeteringRef.current,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const silenceCapture = isVoiceRelaySilenceCapture(
                voiceRelayMeterUnavailableRef.current,
                voiceRelayPeakMeteringRef.current,
                voiceRelaySegmentStateRef.current.hasSpeech,
            );
            if (isLikelySilenceHallucination(transcript, relaySourceLang) && silenceCapture) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'silence_hallucination',
                    transcript,
                    source_lang: localSourceLang,
                    peak_meter_db: voiceRelayPeakMeteringRef.current,
                    flush_reason: voiceRelayLastFlushReasonRef.current,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const relayLangScope = [relaySourceLang, relayTargetLang, localSourceLang, localTargetLang];
            if (silenceCapture && isLikelyGibberishRelayTranscript(transcript, relayLangScope)) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'gibberish_transcript',
                    transcript,
                    translated_text: translatedText,
                    source_lang: relaySourceLang,
                    target_lang: relayTargetLang,
                    peak_meter_db: voiceRelayPeakMeteringRef.current,
                    flush_reason: voiceRelayLastFlushReasonRef.current,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            if (silenceCapture && isLikelyGibberishRelayTranscript(translatedText, relayLangScope)) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'gibberish_translation',
                    transcript,
                    translated_text: translatedText,
                    source_lang: relaySourceLang,
                    target_lang: relayTargetLang,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const normalizedTranscript = normalizeRelayText(transcript);
            const remoteEchoAgeMs = Date.now() - lastRemoteRelayAtRef.current;
            if (
                lastRemoteRelayTranscriptRef.current
                && remoteEchoAgeMs < VOICE_RELAY_REMOTE_ECHO_DEDUPE_MS
                && (
                    normalizedTranscript === lastRemoteRelayTranscriptRef.current
                    || normalizedTranscript.includes(lastRemoteRelayTranscriptRef.current)
                    || lastRemoteRelayTranscriptRef.current.includes(normalizedTranscript)
                )
            ) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'remote_echo_dedupe',
                    transcript,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            if (
                relaySourceLang !== relayTargetLang
                && normalizeRelayText(transcript) === normalizeRelayText(translatedText)
            ) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'identity_translation',
                    source_lang: relaySourceLang,
                    target_lang: relayTargetLang,
                    detected_lang: detectedLang,
                    transcript,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const dedupeKey = `${normalizeRelayText(transcript)}::${normalizeRelayText(translatedText)}::${relayTargetLang}`;
            const now = Date.now();
            if (lastVoiceRelayKeyRef.current === dedupeKey && now - lastVoiceRelayAtRef.current < VOICE_RELAY_DUPLICATE_GUARD_MS) {
                return;
            }

            lastVoiceRelayKeyRef.current = dedupeKey;
            lastVoiceRelayAtRef.current = now;

            const echoDecision = isLikelyVoiceRelayEcho({
                transcript,
                translatedText,
                nowMs: now,
                recentLocalTranslated: lastLocalRelayTranslatedRef.current,
                recentLocalSentAtMs: lastLocalRelaySentAtRef.current,
                recentRemotePlaybackTranslated: lastRemotePlaybackTranslatedRef.current,
                recentRemotePlaybackAtMs: lastRemotePlaybackTranslatedAtRef.current,
                recentRemoteTranscript: lastRemoteRelayTranscriptRef.current,
                recentRemoteAtMs: lastRemoteRelayAtRef.current,
            });
            if (echoDecision.echo) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: echoDecision.reason || 'relay_echo',
                    transcript,
                    translated_text: translatedText,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const sentAt = new Date().toISOString();
            appendVoiceRelayEntry({
                id: `voice-local-${sentAt}`,
                fromRole: participantRole,
                transcript,
                translatedText,
                sourceLang: relaySourceLang,
                targetLang: relayTargetLang,
                sentAt,
                isLocal: true,
                audioUrl: result.audio_url,
                audioBase64: result.audio_base64,
                audioFormat: result.audio_format,
            });
            appendChatEntry({
                id: `voice-chat-${sentAt}`,
                fromRole: participantRole,
                text: transcript,
                sentAt,
                isLocal: true,
                sourceLang: relaySourceLang,
                targetLang: relayTargetLang,
                translatedText,
                translationState: 'done',
                translationEngine: result.engine,
            });

            const sent = voipClientRef.current?.sendVoiceTranslation({
                transcript,
                translatedText,
                sourceLang: relaySourceLang,
                targetLang: relayTargetLang,
                sentAt,
                seqId,
                utteranceId: relayChunkMeta.utteranceId,
                chunkIndex: relayChunkMeta.chunkIndex,
                isFinal: relayChunkMeta.isFinal,
                detectedLang,
                captureTrust: String(result.stt_trust || 'high'),
            });

            if (sent) {
                setLastRelayDeliveryHint(`전달됨 · ${transcript.slice(0, 40)} → ${translatedText.slice(0, 40)}`);
                lastLocalRelayTranslatedRef.current = normalizeRelayText(translatedText);
                lastLocalRelaySentAtRef.current = Date.now();
                voiceRelayTurnRef.current = applyLocalRelayTurn({
                    turn: voiceRelayTurnRef.current,
                    nowMs: Date.now(),
                    translatedText,
                });
                voiceRelayUtteranceIdRef.current = createVoiceRelayUtteranceId(callInitResponse.call_id);
                voiceRelaySegmentStateRef.current = createInitialVoiceRelaySegmentState(Date.now(), 0);
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SENT',
                    call_id: callInitResponse.call_id,
                    transcript,
                    translated_text: translatedText,
                    utterance_id: relayChunkMeta.utteranceId,
                    chunk_index: relayChunkMeta.chunkIndex,
                    is_final: relayChunkMeta.isFinal,
                    seq_id: seqId,
                    relay_duration_ms: Date.now() - segmentStartedAt,
                    timestamp: new Date().toISOString(),
                }));
            }

            if (!sent) {
                console.warn('[VoIPScreen] Voice relay send blocked', {
                    callId: callInitResponse.call_id,
                    sourceLang: localSourceLang,
                    targetLang: localTargetLang,
                    transcriptLength: transcript.length,
                    translatedLength: translatedText.length,
                    signaling: voipClientRef.current?.getSignalingStateSnapshot() ?? null,
                });
                setVoiceRelayError('음성 통역 relay 채널이 아직 연결되지 않았습니다.');
            }
            voiceRelayChunkMetaRef.current = null;
        } catch (err) {
            const message = err instanceof Error ? err.message : '실시간 음성 통역 처리에 실패했습니다.';
            const isSilenceRejected = message.includes('음성이 감지되지 않았습니다');
            const isTooShort = message.includes('너무 짧습니다');
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: isSilenceRejected ? 'VOIP_VOICE_TRANSLATE_REJECTED' : 'VOIP_VOICE_TRANSLATE_FAILED',
                call_id: callInitResponse.call_id,
                error_message: message,
                timestamp: new Date().toISOString(),
            }));
            if (isTooShort) {
                setVoiceRelayError(`녹음 ${voiceRelayLastSegmentDurationMsRef.current}ms — 조금 더 길게 말해 주세요.`);
            } else if (!isSilenceRejected) {
                setVoiceRelayError(message);
            }
        } finally {
            voiceRelayProcessingRef.current = false;
            voiceRelayLastFlushReasonRef.current = null;
            setVoiceRelayBusy(false);
            if (voiceRelayEnabledRef.current) {
                scheduleVoiceRelayCaptureRetry('segment_complete');
            }
            try {
                await FileSystem.deleteAsync(uri, { idempotent: true });
            } catch {
                // ignore temp cleanup failures
            }
        }
    }, [appendChatEntry, appendVoiceRelayEntry, callInitResponse.call_id, localSourceLang, localTargetLang, nextVoiceRelaySeqId, participantRole, regionHint, scheduleVoiceRelayCaptureRetry]);

    const stopVoiceRelaySegment = useCallback(async (processSegment: boolean) => {
        clearVoiceRelayTimers();
        await stopVoiceRelaySileroMonitor(processSegment ? 'segment_flush' : 'segment_stop');

        const recording = voiceRelayRecordingRef.current;
        voiceRelayRecordingRef.current = null;
        setVoiceRelayRecording(false);
        if (!recording) {
            return;
        }

        try {
            await recording.stopAndUnloadAsync();
            const uri = recording.getURI();
            if (voiceRelayRecordingRemoteSuppressedRef.current) {
                voiceRelayRecordingRemoteSuppressedRef.current = false;
                if (!voiceRelayPlaybackRef.current) {
                    releaseRemoteAudioSuppressionIfAllowed();
                }
            }
            if (uri && processSegment) {
                await processVoiceRelaySegment(uri);
            } else if (uri) {
                await FileSystem.deleteAsync(uri, { idempotent: true });
            }
        } catch (err) {
            console.warn('[VoIPScreen] Failed to stop voice relay segment', err);
        } finally {
            if (voiceRelayRecordingRemoteSuppressedRef.current) {
                voiceRelayRecordingRemoteSuppressedRef.current = false;
                if (!voiceRelayPlaybackRef.current) {
                    releaseRemoteAudioSuppressionIfAllowed();
                }
            }
            try {
                await restoreWebRtcMicIfVoiceRelayInactive('segment_stop');
            } catch (restoreErr) {
                console.warn('[VoIPScreen] Failed to restore WebRTC mic after voice relay segment', restoreErr);
            }
        }
    }, [clearVoiceRelayTimers, processVoiceRelaySegment, releaseRemoteAudioSuppressionIfAllowed, restoreWebRtcMicIfVoiceRelayInactive, stopVoiceRelaySileroMonitor]);

    const flushVoiceRelaySegment = useCallback(async (reason: string, isFinal: boolean) => {
        if (voiceRelayFlushInProgressRef.current || !voiceRelayRecordingRef.current) {
            return;
        }

        voiceRelayFlushInProgressRef.current = true;
        voiceRelayLastFlushReasonRef.current = reason;
        voiceRelayLastFlushHadSpeechRef.current = voiceRelaySegmentStateRef.current.hasSpeech;
        voiceRelayLastSegmentDurationMsRef.current = Math.max(
            0,
            Date.now() - voiceRelaySegmentStateRef.current.segmentStartedAtMs,
        );

        const deferDecision = shouldDeferVoiceRelayFlush({
            participantRole,
            turn: voiceRelayTurnRef.current,
            reason,
            meterUnavailable: voiceRelayMeterUnavailableRef.current,
            flushHadSpeech: voiceRelayLastFlushHadSpeechRef.current,
            hasRemoteAudio: hasRemoteAudioRef.current,
            remoteAudioSuppressed: remoteAudioSuppressedRef.current,
        });
        if (deferDecision.defer) {
            voiceRelayFlushInProgressRef.current = false;
            voiceRelayLastFlushReasonRef.current = null;
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SEGMENT_FLUSH_DEFERRED',
                call_id: callInitResponse.call_id,
                reason,
                skip_reason: deferDecision.skipReason || 'flush_deferred',
                meter_unavailable: voiceRelayMeterUnavailableRef.current,
                timestamp: new Date().toISOString(),
            }));
            return;
        }

        voiceRelayChunkMetaRef.current = {
            utteranceId: voiceRelayUtteranceIdRef.current,
            chunkIndex: 0,
            isFinal: true,
        };
        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_VOICE_RELAY_SEGMENT_FLUSH',
            call_id: callInitResponse.call_id,
            reason,
            is_final: isFinal,
            peak_meter_db: voiceRelayPeakMeteringRef.current,
            meter_unavailable: voiceRelayMeterUnavailableRef.current,
            timestamp: new Date().toISOString(),
        }));

        try {
            await stopVoiceRelaySegment(true);
            if (reason === 'silence') {
                voiceRelaySileroLastFlushAtMsRef.current = Date.now();
            }
            voiceRelaySileroFirstSpeechAtMsRef.current = null;
            voiceRelaySegmentStateRef.current = nextVoiceRelaySegmentStateAfterFlush(
                voiceRelaySegmentStateRef.current,
                isFinal,
                Date.now(),
            );
            if (isFinal) {
                voiceRelayUtteranceIdRef.current = createVoiceRelayUtteranceId(callInitResponse.call_id);
            }
        } finally {
            voiceRelayFlushInProgressRef.current = false;
        }
    }, [callInitResponse.call_id, participantRole, stopVoiceRelaySegment]);

    flushVoiceRelaySegmentRef.current = flushVoiceRelaySegment;

    useEffect(() => {
        let active = true;
        void probeVoiceRelaySileroVadSupport().then((supported) => {
            if (active) {
                voiceRelaySileroSupportedRef.current = supported;
            }
        });
        return () => {
            active = false;
        };
    }, []);

    useEffect(() => {
        const unsubscribe = subscribeVoiceRelaySileroVadEvents((event) => {
            if (!voiceRelayEnabledRef.current || !voiceRelayRecordingRef.current) {
                return;
            }
            const nowMs = Date.now();
            if (event.event === 'speech_start') {
                if (voiceRelaySileroFirstSpeechAtMsRef.current == null) {
                    voiceRelaySileroFirstSpeechAtMsRef.current = nowMs;
                }
                voiceRelaySegmentStateRef.current = updateVoiceRelaySegmentSpeechState(
                    voiceRelaySegmentStateRef.current,
                    -40,
                    nowMs,
                );
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SILERO_SPEECH_START',
                    call_id: callInitResponse.call_id,
                    silence_duration_ms: event.silenceDurationMs,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }
            if (event.event !== 'speech_end' || voiceRelayFlushInProgressRef.current) {
                return;
            }
            const segmentDurationMs = nowMs - voiceRelaySegmentStateRef.current.segmentStartedAtMs;
            const speechSpanMs = voiceRelaySileroFirstSpeechAtMsRef.current != null
                ? nowMs - voiceRelaySileroFirstSpeechAtMsRef.current
                : null;
            voiceRelaySegmentStateRef.current = {
                ...voiceRelaySegmentStateRef.current,
                hasSpeech: true,
                lastSpeechAtMs: nowMs,
            };
            const boundaryDecision = shouldFlushOnSileroSpeechEnd({
                segmentDurationMs,
                speechSpanMs,
                lastSileroFlushAtMs: voiceRelaySileroLastFlushAtMsRef.current,
                nowMs,
            });
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SILERO_SPEECH_END',
                call_id: callInitResponse.call_id,
                segment_duration_ms: segmentDurationMs,
                speech_span_ms: speechSpanMs,
                silence_duration_ms: event.silenceDurationMs,
                flush: boundaryDecision.flush,
                defer_reason: boundaryDecision.deferReason || null,
                timestamp: new Date().toISOString(),
            }));
            if (!boundaryDecision.flush) {
                return;
            }
            void flushVoiceRelaySegmentRef.current('silence', true);
        });
        return () => {
            unsubscribe();
            void stopVoiceRelaySileroVadMonitor();
            voiceRelaySileroActiveRef.current = false;
            setVoiceRelaySileroActive(false);
        };
    }, [callInitResponse.call_id]);

    const scheduleVoiceRelayFixedFlush = useCallback(() => {
        if (voiceRelayFixedFlushTimerRef.current) {
            clearTimeout(voiceRelayFixedFlushTimerRef.current);
            voiceRelayFixedFlushTimerRef.current = null;
        }

        const meterUnavailable = voiceRelayMeterUnavailableRef.current;
        const segmentStartedAtMs = voiceRelaySegmentStateRef.current.segmentStartedAtMs;
        const flushDelayMs = voiceRelaySileroActiveRef.current
            ? resolveSileroSafetyCapDelayMs(segmentStartedAtMs)
            : resolveVoiceRelayFixedFlushDelayMs(meterUnavailable);
        const elapsedMs = Date.now() - segmentStartedAtMs;
        const waitMs = elapsedMs < VOICE_RELAY_VAD_DEFAULTS.minSegmentMs
            ? Math.max(
                VOICE_RELAY_VAD_DEFAULTS.minSegmentMs - elapsedMs,
                VOICE_RELAY_VAD_DEFAULTS.meterPollMs,
            )
            : flushDelayMs;

        voiceRelayFixedFlushTimerRef.current = setTimeout(() => {
            voiceRelayFixedFlushTimerRef.current = null;
            void (async () => {
                if (!voiceRelayEnabledRef.current || !voiceRelayRecordingRef.current || voiceRelayFlushInProgressRef.current) {
                    return;
                }

                const elapsed = Date.now() - voiceRelaySegmentStateRef.current.segmentStartedAtMs;
                const minReadyMs = VOICE_RELAY_VAD_DEFAULTS.minSegmentMs + 250;
                if (elapsed < minReadyMs) {
                    scheduleVoiceRelayFixedFlush();
                    return;
                }

                if (voiceRelaySileroActiveRef.current) {
                    const hasSpeech = voiceRelaySegmentStateRef.current.hasSpeech
                        || voiceRelaySileroFirstSpeechAtMsRef.current != null;
                    if (shouldFlushSileroSafetyCap({
                        segmentDurationMs: elapsed,
                        hasSpeech,
                    })) {
                        await flushVoiceRelaySegment('max_duration', true);
                        return;
                    }
                    scheduleVoiceRelayFixedFlush();
                    return;
                }

                await flushVoiceRelaySegment('fixed_interval', true);
            })();
        }, waitMs);
    }, [flushVoiceRelaySegment]);

    const startVoiceRelaySegment = useCallback(async () => {
        if (Platform.OS === 'web') {
            setVoiceRelayError('웹에서는 통화 중 실시간 음성 통역 녹음을 지원하지 않습니다.');
            setVoiceRelayEnabled(false);
            return;
        }
        const callReady = isVoiceRelayCallReady();
        if (!voiceRelayEnabledRef.current || !callReady || voiceRelayRecordingRef.current || voiceRelayProcessingRef.current) {
            if (!voiceRelayEnabledRef.current) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_START_SKIPPED',
                    call_id: callInitResponse.call_id,
                    reason: 'voice_relay_disabled',
                    connection_state: connectionState,
                    timestamp: new Date().toISOString(),
                }));
            } else if (voiceRelayEnabledRef.current) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_START_BLOCKED',
                    call_id: callInitResponse.call_id,
                    reason: !callReady
                        ? 'call_not_ready'
                        : voiceRelayRecordingRef.current
                            ? 'recording_in_progress'
                            : 'segment_processing_in_progress',
                    connection_state: connectionState,
                    has_remote_audio: hasRemoteAudio,
                    signaling: voipClientRef.current?.getSignalingStateSnapshot() ?? null,
                    timestamp: new Date().toISOString(),
                }));
            }
            return;
        }
        if (Date.now() < voiceRelaySuppressUntilRef.current) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_START_BLOCKED',
                call_id: callInitResponse.call_id,
                reason: 'echo_suppression_window',
                suppress_remaining_ms: Math.max(0, voiceRelaySuppressUntilRef.current - Date.now()),
                remote_audio_suppressed: remoteAudioSuppressedRef.current,
                timestamp: new Date().toISOString(),
            }));
            scheduleVoiceRelayCaptureRetry('echo_suppression_window');
            return;
        }
        const captureDecision = shouldStartVoiceRelayCapture({
            participantRole,
            turn: voiceRelayTurnRef.current,
        });
        if (!captureDecision.allowed) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_START_BLOCKED',
                call_id: callInitResponse.call_id,
                reason: captureDecision.reason || 'remote_listen_active',
                timestamp: new Date().toISOString(),
            }));
            scheduleVoiceRelayCaptureRetry(captureDecision.reason || 'remote_listen_active');
            return;
        }
        if (remoteAudioSuppressedRef.current && !voiceRelayRecordingRemoteSuppressedRef.current) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_START_BLOCKED',
                call_id: callInitResponse.call_id,
                reason: 'remote_audio_suppressed',
                suppress_remaining_ms: Math.max(0, voiceRelaySuppressUntilRef.current - Date.now()),
                remote_audio_suppressed: remoteAudioSuppressedRef.current,
                timestamp: new Date().toISOString(),
            }));
            scheduleVoiceRelayCaptureRetry('remote_audio_suppressed');
            return;
        }

        try {
            const permission = await Audio.requestPermissionsAsync();
            if (!permission.granted) {
                setVoiceRelayError('마이크 권한이 없어 실시간 음성 통역을 시작할 수 없습니다.');
                setVoiceRelayEnabled(false);
                return;
            }

            voipClientRef.current?.suspendLocalAudioForVoiceRelay();

            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: false,
                playThroughEarpieceAndroid: !isSpeakerOn,
                staysActiveInBackground: false,
            });

            voiceRelayPeakMeteringRef.current = -160;
            voiceRelayMeterPollMissesRef.current = 0;
            voiceRelayMeterUnavailableRef.current = false;
            voiceRelayFileRmsPollTickRef.current = 0;
            setVoiceRelayMeterDead(false);
            setVoiceRelayListenWaiting(false);
            voiceRelayLastFlushReasonRef.current = null;
            voiceRelaySileroFirstSpeechAtMsRef.current = null;
            voiceRelaySegmentStateRef.current = createInitialVoiceRelaySegmentState(
                Date.now(),
                voiceRelaySegmentStateRef.current.chunkIndex,
            );
            const recording = new Audio.Recording();
            await recording.prepareToRecordAsync(buildVoiceRelayRecordingOptions());
            await recording.startAsync();

            voiceRelayRecordingRef.current = recording;
            setVoiceRelayRecording(true);
            voiceRelayRecordingRemoteSuppressedRef.current = true;
            setRemoteAudioSuppressed(true);
            setVoiceRelayError(null);
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SEGMENT_STARTED',
                call_id: callInitResponse.call_id,
                connection_state: connectionState,
                source_lang: localSourceLang,
                target_lang: localTargetLang,
                timestamp: new Date().toISOString(),
            }));

            voiceRelayMeterPollRef.current = setInterval(() => {
                void (async () => {
                    const activeRecording = voiceRelayRecordingRef.current;
                    if (!activeRecording || voiceRelayFlushInProgressRef.current) {
                        return;
                    }
                    try {
                        const status = await activeRecording.getStatusAsync();
                        if (!status.isRecording) {
                            return;
                        }
                        const meteringUnavailableSample = typeof status.metering !== 'number'
                            || status.metering <= -159;
                        if (meteringUnavailableSample) {
                            voiceRelayMeterPollMissesRef.current += 1;
                            if (
                                voiceRelayMeterPollMissesRef.current >= VOICE_RELAY_METER_UNAVAILABLE_POLLS
                                && !voiceRelayMeterUnavailableRef.current
                            ) {
                                voiceRelayMeterUnavailableRef.current = true;
                                setVoiceRelayMeterDead(true);
                                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                    event: 'VOIP_VOICE_RELAY_METER_UNAVAILABLE',
                                    call_id: callInitResponse.call_id,
                                    poll_misses: voiceRelayMeterPollMissesRef.current,
                                    last_meter_db: typeof status.metering === 'number' ? status.metering : null,
                                    file_rms_vad: true,
                                    timestamp: new Date().toISOString(),
                                }));
                            }

                            if (voiceRelayMeterUnavailableRef.current && !voiceRelaySileroActiveRef.current) {
                                voiceRelayFileRmsPollTickRef.current += 1;
                                if (
                                    voiceRelayFileRmsPollTickRef.current
                                    >= VOICE_RELAY_VAD_DEFAULTS.meterUnavailableFilePollEvery
                                ) {
                                    voiceRelayFileRmsPollTickRef.current = 0;
                                    const recordingUri = activeRecording.getURI();
                                    if (recordingUri) {
                                        try {
                                            const partialBase64 = await FileSystem.readAsStringAsync(recordingUri, {
                                                encoding: FileSystem.EncodingType.Base64,
                                            });
                                            const fileRmsDb = estimateRecordingRmsDb(partialBase64);
                                            const nowMs = Date.now();
                                            const priorHasSpeech = voiceRelaySegmentStateRef.current.hasSpeech;
                                            voiceRelaySegmentStateRef.current = updateVoiceRelaySegmentSpeechStateFromFileRms(
                                                voiceRelaySegmentStateRef.current,
                                                fileRmsDb,
                                                nowMs,
                                            );
                                            if (!priorHasSpeech && voiceRelaySegmentStateRef.current.hasSpeech) {
                                                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                                    event: 'VOIP_VOICE_RELAY_FILE_RMS_SPEECH',
                                                    call_id: callInitResponse.call_id,
                                                    estimated_file_rms_db: fileRmsDb,
                                                    timestamp: new Date().toISOString(),
                                                }));
                                            }
                                            const pseudoMeterDb = mapFileRmsToPseudoMeterDb(fileRmsDb);
                                            const fileDecision = evaluateVoiceRelaySegmentDecision(
                                                voiceRelaySegmentStateRef.current,
                                                nowMs,
                                                pseudoMeterDb,
                                            );
                                            if (fileDecision.action === 'flush') {
                                                await flushVoiceRelaySegment(
                                                    fileDecision.reason,
                                                    fileDecision.isFinal,
                                                );
                                            }
                                        } catch {
                                            // Partial m4a reads can fail while the recorder is still writing.
                                        }
                                    }
                                }
                            }
                            return;
                        }

                        voiceRelayMeterPollMissesRef.current = 0;
                        voiceRelayPeakMeteringRef.current = Math.max(
                            voiceRelayPeakMeteringRef.current,
                            status.metering,
                        );
                        const now = Date.now();
                        voiceRelaySegmentStateRef.current = updateVoiceRelaySegmentSpeechState(
                            voiceRelaySegmentStateRef.current,
                            status.metering,
                            now,
                        );
                        const decision = evaluateVoiceRelaySegmentDecision(
                            voiceRelaySegmentStateRef.current,
                            now,
                            status.metering,
                        );
                        if (voiceRelaySileroActiveRef.current || decision.action !== 'flush') {
                            return;
                        }

                        await flushVoiceRelaySegment(decision.reason, decision.isFinal);
                    } catch {
                        voiceRelayFlushInProgressRef.current = false;
                    }
                })();
            }, VOICE_RELAY_VAD_DEFAULTS.meterPollMs);
            await startVoiceRelaySileroMonitor();
            scheduleVoiceRelayFixedFlush();
        } catch (err) {
            const message = err instanceof Error ? err.message : '실시간 음성 통역 녹음을 시작하지 못했습니다.';
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SEGMENT_START_FAILED',
                call_id: callInitResponse.call_id,
                error_message: message,
                connection_state: connectionState,
                timestamp: new Date().toISOString(),
            }));
            setVoiceRelayError(message);
            setVoiceRelayEnabled(false);
            try {
                await restoreWebRtcMicIfVoiceRelayInactive('segment_start_failed');
            } catch (restoreErr) {
                console.warn('[VoIPScreen] Failed to restore WebRTC mic after relay start failure', restoreErr);
            }
        }
    }, [callInitResponse.call_id, clearVoiceRelayTimers, connectionState, flushVoiceRelaySegment, hasRemoteAudio, isVoiceRelayCallReady, isSpeakerOn, localSourceLang, localTargetLang, restoreWebRtcMicIfVoiceRelayInactive, scheduleVoiceRelayCaptureRetry, scheduleVoiceRelayFixedFlush, startVoiceRelaySileroMonitor, stopVoiceRelaySegment]);

    startVoiceRelaySegmentRef.current = startVoiceRelaySegment;

    const handleVoiceRelayToggle = useCallback(() => {
        setVoiceRelayError(null);
        setVoiceRelaySuggestionVisible(false);
        setVoiceRelayEnabled((prev) => !prev);
    }, []);

    const failCallAndStopTone = useCallback(async (message: string) => {
        forcedTerminalStateRef.current = 'failed';
        getVoIPToneService().stopAll();
        if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
            connectionTimeoutRef.current = null;
        }
        if (remoteAudioTimeoutRef.current) {
            clearTimeout(remoteAudioTimeoutRef.current);
            remoteAudioTimeoutRef.current = null;
        }
        setError(message);
        setConnectionState('failed');
        await voipClientRef.current?.hangup();
    }, []);

    useEffect(() => {
        voipCallInitHandlersRef.current = {
            syncRemoteAudioState,
            appendChatEntry,
            appendVoiceRelayEntry,
            resolveChatLanguagePair,
            enqueueVoiceRelayPlayback,
            nextVoiceRelaySeqId,
            stopVoiceRelaySegment,
            stopVoiceRelayPlayback,
            participantRole,
            localSourceLang,
            localTargetLang,
        };
    }, [
        appendChatEntry,
        appendVoiceRelayEntry,
        enqueueVoiceRelayPlayback,
        localSourceLang,
        localTargetLang,
        nextVoiceRelaySeqId,
        participantRole,
        resolveChatLanguagePair,
        stopVoiceRelayPlayback,
        stopVoiceRelaySegment,
        syncRemoteAudioState,
    ]);

    // Initialize VoIP client and establish connection
    useEffect(() => {
        const initializeCall = async () => {
            let client: VoIPCallClient | null = null;
            try {
                const signalingServerUrl = resolveVoipSignalingServerUrl(
                    callInitResponse.signaling_server,
                    participantRole,
                    apiBaseUrl,
                );

                client = new VoIPCallClient({
                    callId: callInitResponse.call_id,
                    signalingServerUrl,
                    turnServers: callInitResponse.turn_servers,
                    mediaConstraints: {
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true,
                        },
                        video: false,
                    },
                });

                // Initialize peer connection
                await client.initializePeerConnection();

                // Connect to signaling server
                await client.connectSignaling();

                // Get local audio stream
                await client.getLocalStream();

                if (participantRole === 'caller') {
                    await client.createAndSendOffer();
                }

                voipClientRef.current = client;
                const boundClient = client;
                setVoipClient(client);
                setConnectionState(client.getConnectionState());

                // Register state change callback
                boundClient.onStateChange((state: string) => {
                    const handlers = voipCallInitHandlersRef.current;
                    console.log('[VoIPScreen] State change callback:', state);
                    if (forcedTerminalStateRef.current) {
                        setConnectionState(forcedTerminalStateRef.current);
                        return;
                    }
                    setConnectionState(state);
                    if (state === 'connected') {
                        if (connectedAtRef.current == null) {
                            connectedAtRef.current = Date.now();
                        }
                        handlers?.syncRemoteAudioState();
                    } else if (state === 'failed' || state === 'disconnected') {
                        connectedAtRef.current = null;
                    }
                    if (state === 'connected' && connectionTimeoutRef.current) {
                        clearTimeout(connectionTimeoutRef.current);
                        connectionTimeoutRef.current = null;
                    }
                    if (state === 'connected' && !boundClient.hasRemoteAudioTrack() && !remoteAudioTimeoutRef.current) {
                        remoteAudioTimeoutRef.current = setTimeout(() => {
                            if (!boundClient.hasRemoteAudioTrack()) {
                                console.warn('[VoIPScreen] Remote audio track not detected via callback; keeping call active for voice relay');
                                handlers?.syncRemoteAudioState();
                            }
                            remoteAudioTimeoutRef.current = null;
                        }, REMOTE_AUDIO_DETECT_WARN_MS);
                    }
                    if ((state === 'failed' || state === 'disconnected') && !errorRef.current) {
                        setError(state === 'failed'
                            ? '통화 연결에 실패했습니다. 네트워크 또는 서버 상태를 확인해주세요.'
                            : '통화 연결이 끊어졌습니다.');
                    }
                });

                boundClient.onRemoteStream((stream: any) => {
                    const audioTracks = stream?.getAudioTracks?.() ?? [];
                    const hasStreamAudio = audioTracks.some((track: any) => track?.enabled !== false && track?.readyState !== 'ended');
                    const hasReceiverAudio = boundClient.hasRemoteAudioTrack();
                    const hasAudio = hasStreamAudio || hasReceiverAudio;
                    console.log('[VoIPScreen] Remote stream update:', {
                        hasAudio,
                        hasStreamAudio,
                        hasReceiverAudio,
                        audioTrackCount: audioTracks.length,
                    });
                    setHasRemoteAudio(hasAudio);
                    if (hasAudio && remoteAudioTimeoutRef.current) {
                        clearTimeout(remoteAudioTimeoutRef.current);
                        remoteAudioTimeoutRef.current = null;
                    }
                });

                boundClient.onChatMessageRejected((detail: string) => {
                    setChatError(detail);
                });

                boundClient.onChatMessage((message: VoIPChatMessage) => {
                    const handlers = voipCallInitHandlersRef.current;
                    if (!handlers) {
                        return;
                    }
                    const text = typeof message.text === 'string' ? message.text.trim() : '';
                    if (!text) {
                        return;
                    }

                    const fromRole = message.from_role === 'callee' ? 'callee' : 'caller';
                    if (fromRole !== handlers.participantRole) {
                        getVoIPToneService().playMessageTone();
                    }
                    const translationPair = handlers.resolveChatLanguagePair(fromRole === handlers.participantRole);
                    const translatedText = typeof message.translated_text === 'string' ? message.translated_text.trim() : '';
                    const translationStatus = typeof message.translation_status === 'string' ? message.translation_status.trim().toLowerCase() : '';
                    const hasServerTranslation = translatedText.length > 0;
                    handlers.appendChatEntry({
                        id: message.message_id || `${fromRole}-${message.sent_at || Date.now()}-${text}`,
                        fromRole,
                        text,
                        sentAt: message.sent_at || new Date().toISOString(),
                        clientSentAt: message.client_sent_at,
                        isLocal: fromRole === handlers.participantRole,
                        sourceLang: message.source_lang || translationPair.sourceLang,
                        targetLang: message.target_lang || translationPair.targetLang,
                        translatedText,
                        translationState: hasServerTranslation
                            ? 'done'
                            : translationStatus === 'failed'
                                ? 'failed'
                                : 'pending',
                        translationEngine: hasServerTranslation ? 'server-voip-chat' : undefined,
                        translationOffline: false,
                        messageId: message.message_id,
                        roomId: message.room_id,
                        senderLabel: message.sender_label,
                        senderVoiceId: message.sender_voice_id,
                    });
                    setChatError(null);
                });

                boundClient.onVoiceTranslation((message: VoIPVoiceTranslationMessage) => {
                    const handlers = voipCallInitHandlersRef.current;
                    if (!handlers) {
                        return;
                    }
                    const transcript = typeof message.transcript === 'string' ? message.transcript.trim() : '';
                    const translatedText = typeof message.translated_text === 'string' ? message.translated_text.trim() : '';
                    if (!transcript || !translatedText) {
                        return;
                    }

                    const fromRole = message.from_role === 'callee' ? 'callee' : 'caller';
                    const isLocal = fromRole === handlers.participantRole;
                    const langPair = handlers.resolveChatLanguagePair(isLocal);
                    const relaySourceLang = message.source_lang || langPair.sourceLang;
                    const relayTargetLang = message.target_lang || langPair.targetLang;

                    if (!isLocal) {
                        voiceRelayAbortGenerationRef.current += 1;
                        voiceRelayProcessingRef.current = false;

                        const relayLangScope = [
                            relaySourceLang,
                            relayTargetLang,
                            handlers.localSourceLang,
                            handlers.localTargetLang,
                        ];
                        const remoteReject = shouldRejectRemoteVoiceRelayPlayback({
                            captureTrust: typeof message.capture_trust === 'string' ? message.capture_trust : null,
                            transcript,
                            translatedText,
                            sourceLang: relaySourceLang,
                            targetLang: relayTargetLang,
                            langScope: relayLangScope,
                        });
                        if (remoteReject.reject) {
                            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                event: 'VOIP_VOICE_RELAY_SKIP',
                                call_id: callInitResponse.call_id,
                                reason: remoteReject.reason || 'remote_hallucination',
                                transcript,
                                translated_text: translatedText,
                                source_lang: relaySourceLang,
                                capture_trust: message.capture_trust || null,
                                timestamp: new Date().toISOString(),
                            }));
                            return;
                        }

                        const echoDecision = isLikelyVoiceRelayEcho({
                            transcript,
                            translatedText,
                            recentLocalTranslated: lastLocalRelayTranslatedRef.current,
                            recentLocalSentAtMs: lastLocalRelaySentAtRef.current,
                            recentRemotePlaybackTranslated: lastRemotePlaybackTranslatedRef.current,
                            recentRemotePlaybackAtMs: lastRemotePlaybackTranslatedAtRef.current,
                            recentRemoteTranscript: lastRemoteRelayTranscriptRef.current,
                            recentRemoteAtMs: lastRemoteRelayAtRef.current,
                        });
                        if (echoDecision.echo) {
                            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                event: 'VOIP_VOICE_RELAY_SKIP',
                                call_id: callInitResponse.call_id,
                                reason: echoDecision.reason || 'relay_echo',
                                transcript,
                                translated_text: translatedText,
                                timestamp: new Date().toISOString(),
                            }));
                            return;
                        }

                        if (handlers.participantRole === 'caller' && fromRole === 'callee') {
                            const now = Date.now();
                            const localNorm = lastLocalRelayTranslatedRef.current;
                            const remoteNorm = normalizeRelayText(translatedText);
                            if (now - lastLocalRelaySentAtRef.current < 15_000 && localNorm) {
                                const localWords = localNorm.split(' ').filter((word) => word.length > 2);
                                const remoteWords = new Set(remoteNorm.split(' '));
                                const overlap = localWords.filter((word) => remoteWords.has(word)).length;
                                const similar = localNorm === remoteNorm
                                    || localNorm.includes(remoteNorm)
                                    || remoteNorm.includes(localNorm)
                                    || (localWords.length > 0 && overlap / localWords.length >= 0.5);
                                if (similar) {
                                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                        event: 'VOIP_VOICE_RELAY_SKIP',
                                        call_id: callInitResponse.call_id,
                                        reason: 'acoustic_echo_relay',
                                        transcript,
                                        translated_text: translatedText,
                                        timestamp: new Date().toISOString(),
                                    }));
                                    return;
                                }
                            }
                        }
                    }

                    handlers.appendVoiceRelayEntry({
                        id: `voice-${fromRole}-${message.sent_at || Date.now()}-${transcript}`,
                        fromRole,
                        transcript,
                        translatedText,
                        sourceLang: relaySourceLang,
                        targetLang: relayTargetLang,
                        sentAt: message.sent_at || new Date().toISOString(),
                        isLocal,
                        audioUrl: message.audio_url,
                        audioBase64: message.audio_base64,
                        audioFormat: message.audio_format,
                    });
                    handlers.appendChatEntry({
                        id: `voice-chat-${fromRole}-${message.sent_at || Date.now()}-${transcript}`,
                        fromRole,
                        text: transcript,
                        sentAt: message.sent_at || new Date().toISOString(),
                        isLocal,
                        sourceLang: relaySourceLang,
                        targetLang: relayTargetLang,
                        translatedText,
                        translationState: 'done',
                        translationEngine: 'nado-voice-relay',
                    });

                    if (!isLocal) {
                        const playbackDecision = shouldPlayRemoteVoiceRelay({
                            participantRole: handlers.participantRole,
                            fromRole,
                            relaySourceLang,
                            relayTargetLang,
                            localSourceLang: handlers.localSourceLang,
                            localTargetLang: handlers.localTargetLang,
                        });
                        if (!playbackDecision.allowed) {
                            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                event: 'VOIP_VOICE_RELAY_PLAYBACK_SKIPPED',
                                call_id: callInitResponse.call_id,
                                reason: playbackDecision.reason || 'remote_playback_blocked',
                                from_role: fromRole,
                                source_lang: relaySourceLang,
                                target_lang: relayTargetLang,
                                transcript,
                                timestamp: new Date().toISOString(),
                            }));
                            return;
                        }

                        const relayKey = `${normalizeRelayText(transcript)}::${normalizeRelayText(translatedText)}`;
                        const now = Date.now();
                        if (
                            lastRemotePlaybackKeyRef.current === relayKey
                            && now - lastRemotePlaybackAtRef.current < VOICE_RELAY_REMOTE_PLAYBACK_DEDUPE_MS
                        ) {
                            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                event: 'VOIP_VOICE_RELAY_SKIP',
                                call_id: callInitResponse.call_id,
                                reason: 'remote_relay_dedupe',
                                transcript,
                                translated_text: translatedText,
                                timestamp: new Date().toISOString(),
                            }));
                            return;
                        }
                        lastRemotePlaybackKeyRef.current = relayKey;
                        lastRemotePlaybackAtRef.current = now;
                    }

                    if (!isLocal) {
                        voiceRelayTurnRef.current = applyRemoteRelayTurn({
                            turn: voiceRelayTurnRef.current,
                            nowMs: Date.now(),
                            translatedText,
                            speakerOn: isSpeakerOnRef.current,
                        });
                        voiceRelayAbortGenerationRef.current += 1;
                        voiceRelayProcessingRef.current = false;
                        void handlers.stopVoiceRelaySegment(false);
                        const echoGuardMs = isSpeakerOnRef.current
                            ? VOICE_RELAY_SPEAKER_ECHO_GUARD_MS
                            : VOICE_RELAY_REMOTE_ECHO_GUARD_MS;
                        voiceRelaySuppressUntilRef.current = Date.now() + echoGuardMs;
                        lastRemoteRelayTranscriptRef.current = normalizeRelayText(transcript);
                        lastRemoteRelayAtRef.current = voiceRelayTurnRef.current.lastRemoteRelayAtMs;
                        getVoIPToneService().playMessageTone();
                        const seqId = typeof message.seq_id === 'number' && Number.isFinite(message.seq_id)
                            ? message.seq_id
                            : handlers.nextVoiceRelaySeqId();
                        handlers.enqueueVoiceRelayPlayback({
                            seqId,
                            utteranceId: message.utterance_id || `remote-${seqId}`,
                            chunkIndex: typeof message.chunk_index === 'number' ? message.chunk_index : 0,
                            isFinal: message.is_final !== false,
                            translatedText,
                            targetLang: relayTargetLang,
                        });
                        setLastRelayDeliveryHint(`수신 · ${translatedText.slice(0, 48)}`);
                    }
                });

                // Stop ringing/wingback after 60 seconds if the call never reaches a live media path.
                connectionTimeoutRef.current = setTimeout(() => {
                    const state = boundClient.getConnectionState();
                    if (state !== 'connected') {
                        console.warn('[VoIPScreen] Connection timeout after 60s, state:', state);
                        void failCallAndStopTone('60초 내에 연결되지 않았습니다. 네트워크 상태를 확인해주세요.');
                    }
                }, CALL_CONNECT_TIMEOUT_MS);
            } catch (err) {
                const reason = err instanceof Error
                    ? err.message.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'initialization_exception'
                    : 'initialization_exception';
                const signalingSnapshot = client?.getSignalingStateSnapshot?.() ?? {
                    hasSocket: false,
                    socketState: 'null',
                    connectionState: 'connecting',
                    hasRemoteAudio: false,
                };
                console.warn('[VoIPScreen] Initialization failed', err);
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_CONNECTION_FAIL_CONTEXT',
                    call_id: callInitResponse.call_id,
                    state: 'failed',
                    reason,
                    signaling_server: resolveVoipSignalingServerUrl(
                        callInitResponse.signaling_server,
                        participantRole,
                        apiBaseUrl,
                    ),
                    turn_servers_count: Array.isArray(callInitResponse.turn_servers)
                        ? callInitResponse.turn_servers.length
                        : 0,
                    participant_role: participantRole,
                    has_remote_audio: false,
                    signaling: signalingSnapshot,
                    timestamp: new Date().toISOString(),
                }));
                setError(err instanceof Error ? err.message : String(err));
                setConnectionState('failed');
            }
        };

        initializeCall();

        return () => {
            // Cleanup on unmount
            forcedTerminalStateRef.current = null;
            if (timeoutAutoReturnRef.current) {
                clearTimeout(timeoutAutoReturnRef.current);
                timeoutAutoReturnRef.current = null;
            }
            getVoIPToneService().stopAll();
            const cleanupHandlers = voipCallInitHandlersRef.current;
            void cleanupHandlers?.stopVoiceRelaySegment(false);
            void cleanupHandlers?.stopVoiceRelayPlayback();
            voiceRelayPlaybackQueueRef.current?.clear();
            setRemoteAudioSuppressed(false);
            Speech.stop();
            voipClientRef.current?.hangup();
            voipClientRef.current = null;
            if (connectionTimeoutRef.current) {
                clearTimeout(connectionTimeoutRef.current);
            }
            if (remoteAudioTimeoutRef.current) {
                clearTimeout(remoteAudioTimeoutRef.current);
            }
        };
    }, [
        apiBaseUrl,
        callInitResponse.call_id,
        callInitResponse.signaling_server,
        callInitResponse.turn_servers,
        failCallAndStopTone,
        participantRole,
    ]);

    useEffect(() => {
        if (voiceRelayServerReady && voiceRelayEnabled && connectionState === 'connected') {
            setRemoteAudioSuppressed(true);
        }
    }, [connectionState, setRemoteAudioSuppressed, voiceRelayEnabled, voiceRelayServerReady]);

    useEffect(() => {
        isSpeakerOnRef.current = isSpeakerOn;
    }, [isSpeakerOn]);

    useEffect(() => {
        hasRemoteAudioRef.current = hasRemoteAudio;
    }, [hasRemoteAudio]);

    useEffect(() => {
        chatScrollRef.current?.scrollToEnd({ animated: false });
    }, [chatEntries]);

    useEffect(() => {
        voiceRelayEnabledRef.current = voiceRelayEnabled;
    }, [voiceRelayEnabled]);

    useEffect(() => {
        if (
            voiceRelayServerReady
            && !voiceRelayAutoStartedRef.current
            && connectionState === 'connected'
            && !voiceRelayEnabled
        ) {
            voiceRelayAutoStartedRef.current = true;
            voiceRelaySuggestionShownRef.current = true;
            setVoiceRelaySuggestionVisible(false);
            setVoiceRelayError(null);
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_AUTO_ENABLED',
                call_id: callInitResponse.call_id,
                voice_relay_server_ready: voiceRelayServerReady,
                timestamp: new Date().toISOString(),
            }));
            setVoiceRelayEnabled(true);
        }
    }, [callInitResponse.call_id, connectionState, voiceRelayEnabled, voiceRelayServerReady]);

    useEffect(() => {
        if (
            !voiceRelayServerReady
            &&
            !voiceRelaySuggestionShownRef.current
            && connectionState === 'connected'
            && hasRemoteAudio
            && !voiceRelayEnabled
        ) {
            voiceRelaySuggestionShownRef.current = true;
            setVoiceRelaySuggestionVisible(true);
        }
    }, [connectionState, hasRemoteAudio, voiceRelayEnabled, voiceRelayServerReady]);

    useEffect(() => {
        if (connectionState === 'failed' || connectionState === 'disconnected') {
            if (voiceRelayEnabledRef.current) {
                setVoiceRelayEnabled(false);
            }
            setVoiceRelaySuggestionVisible(false);
            void stopVoiceRelaySegment(false);
            return;
        }

        if (!voiceRelayEnabled) {
            void stopVoiceRelaySegment(false);
            void restoreWebRtcMicIfVoiceRelayInactive('voice_relay_disabled');
            return;
        }

        const scheduleCaptureRestart = (delayMs: number) => {
            voiceRelayRestartTimerRef.current = setTimeout(() => {
                void startVoiceRelaySegmentRef.current();
            }, delayMs);
        };

        if (Date.now() < voiceRelaySuppressUntilRef.current) {
            scheduleCaptureRestart(Math.max(250, voiceRelaySuppressUntilRef.current - Date.now()));
            return () => {
                if (voiceRelayRestartTimerRef.current) {
                    clearTimeout(voiceRelayRestartTimerRef.current);
                    voiceRelayRestartTimerRef.current = null;
                }
            };
        }

        if (isVoiceRelayListenActive(voiceRelayTurnRef.current)) {
            scheduleCaptureRestart(Math.max(
                250,
                Math.max(
                    voiceRelayTurnRef.current.remoteListenUntilMs,
                    voiceRelayTurnRef.current.remotePlaybackUntilMs,
                ) - Date.now(),
            ));
            return () => {
                if (voiceRelayRestartTimerRef.current) {
                    clearTimeout(voiceRelayRestartTimerRef.current);
                    voiceRelayRestartTimerRef.current = null;
                }
            };
        }

        if (connectionState === 'connected' && isVoiceRelayCallReadyRef.current() && !voiceRelayRecording && !voiceRelayBusy) {
            scheduleCaptureRestart(VOICE_RELAY_RESTART_DELAY_MS);
        }

        return () => {
            if (voiceRelayRestartTimerRef.current) {
                clearTimeout(voiceRelayRestartTimerRef.current);
                voiceRelayRestartTimerRef.current = null;
            }
        };
    }, [connectionState, restoreWebRtcMicIfVoiceRelayInactive, stopVoiceRelaySegment, voiceRelayBusy, voiceRelayEnabled, voiceRelayRecording]);

    useEffect(() => {
        const callId = callInitResponse.call_id;
        if (!callId || auditLoadedCallIdRef.current === callId) {
            return;
        }
        auditLoadedCallIdRef.current = callId;
        void loadAuditEventsRef.current({ showLoading: false });
    }, [callInitResponse.call_id]);

    useEffect(() => {
        if (connectionState !== 'connected') {
            return;
        }

        const interval = setInterval(() => {
            void loadAuditEventsRef.current({ showLoading: false });
        }, 30000);

        return () => clearInterval(interval);
    }, [connectionState]);

    // Call duration timer
    useEffect(() => {
        if (connectionState !== 'connected') return;

        const interval = setInterval(() => {
            setCallDuration((prev) => prev + 1);
        }, 1000);

        return () => clearInterval(interval);
    }, [connectionState]);

    // Monitor connection state
    useEffect(() => {
        if (!voipClient) return;

        const stateCheckInterval = setInterval(() => {
            if (forcedTerminalStateRef.current) {
                setConnectionState(forcedTerminalStateRef.current);
                return;
            }
            const state = voipClient.getConnectionState();
            setConnectionState(state);
            if (state === 'connected') {
                syncRemoteAudioState();
            }

            // If connection failed, clear timeout and show error
            if (state === 'failed' || state === 'disconnected') {
                if (connectionTimeoutRef.current) {
                    clearTimeout(connectionTimeoutRef.current);
                    connectionTimeoutRef.current = null;
                }
                if (remoteAudioTimeoutRef.current) {
                    clearTimeout(remoteAudioTimeoutRef.current);
                    remoteAudioTimeoutRef.current = null;
                }
                if (!error) {
                    setError(state === 'failed'
                        ? '통화 연결에 실패했습니다. 네트워크 또는 서버 상태를 확인해주세요.'
                        : '통화 연결이 끊어졌습니다.');
                }
            }

            // Clear timeout if connected
            if (state === 'connected' && connectionTimeoutRef.current) {
                clearTimeout(connectionTimeoutRef.current);
                connectionTimeoutRef.current = null;
            }
        }, 500);

        return () => clearInterval(stateCheckInterval);
    }, [voipClient, error, syncRemoteAudioState]);

    useEffect(() => {
        const payload = {
            event: 'VOIP_CONNECTION_STATE_UPDATE',
            call_id: callInitResponse.call_id,
            state: connectionState,
            timestamp: new Date().toISOString(),
        };
        console.log('[UI_PRESS_PROBE]', JSON.stringify(payload));

        if (connectionState === 'connected' && !hasLoggedConnectedRef.current) {
            hasLoggedConnectedRef.current = true;
            console.log(
                '[UI_PRESS_PROBE]',
                JSON.stringify({
                    event: 'VOIP_CONNECTION_STATE_CONNECTED',
                    call_id: callInitResponse.call_id,
                    state: connectionState,
                    timestamp: new Date().toISOString(),
                }),
            );
        }
    }, [connectionState, callInitResponse.call_id]);

    // VoIP Tone Management: In this screen (post-accept), only caller hears wingback while waiting.
    // Callee-side ringing must not continue after accept.
    useEffect(() => {
        const toneService = getVoIPToneService();

        const participantRole = callInitResponse.participant_role || 'caller';
        if (connectionState === 'failed' || connectionState === 'disconnected') {
            console.log('[VoIPScreen] Stopping tone - call ended');
            toneService.stopAll();
            return;
        }

        if (connectionState === 'connected') {
            // Stop tone immediately after accept/answer transition, even before remote audio arrives.
            console.log('[VoIPScreen] Stopping tone - call accepted/connected');
            toneService.stopAll();
            return;
        }

        if (participantRole === 'caller' && connectionState === 'connecting') {
            console.log('[VoIPScreen] Playing ringback tone...');
            toneService.playRingbackTone();
        } else {
            // In-call screen for callee should stay silent while waiting for media path.
            toneService.stopAll();
        }

        return () => {
            // Don't stop tone on unmount - let it play until explicit stop
        };
    }, [callInitResponse.participant_role, connectionState, hasRemoteAudio]);

    const handleMuteToggle = useCallback(() => {
        if (voiceRelayEnabledRef.current) {
            setVoiceRelayError('실시간 음성 통역 중에는 WebRTC 원음 경로가 꺼져 있습니다. 통역을 중지하면 일반 음성 버튼을 사용할 수 있습니다.');
            return;
        }
        if (voipClient) {
            const nextMuted = !isMuted;
            voipClient.setLocalAudioEnabled(!nextMuted);
            setIsMuted(nextMuted);
        }
    }, [voipClient, isMuted]);

    const handleSpeakerToggle = useCallback(async () => {
        const nextSpeakerOn = !isSpeakerOn;
        try {
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: false,
                playThroughEarpieceAndroid: !nextSpeakerOn,
                staysActiveInBackground: false,
            });
            setIsSpeakerOn(nextSpeakerOn);
            isSpeakerOnRef.current = nextSpeakerOn;
        } catch (err) {
            console.error('[VoIPScreen] Failed to toggle speaker route', err);
        }
    }, [isSpeakerOn]);

    const handleHangup = useCallback(async () => {
        // Stop tone on hangup
        const toneService = getVoIPToneService();
        toneService.stopAll();
        await stopVoiceRelaySegment(false);
        await stopVoiceRelayPlayback();
        setRemoteAudioSuppressed(false);
        Speech.stop();
        setVoiceRelayEnabled(false);
        voiceRelayEnabledRef.current = false;
        await restoreWebRtcMicIfVoiceRelayInactive('hangup');

        if (voipClient) {
            await voipClient.hangup();

            // Log call end
            try {
                await fetch(`${apiBaseUrl}/api/v1/voip/calls/${callInitResponse.call_id}/end`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        duration_sec: callDuration,
                        call_quality: connectionState === 'connected' ? 'good' : 'poor',
                    }),
                });
            } catch (err) {
                console.error('[VoIPScreen] Failed to log call end', err);
            }
        }

        const finalAuditEvents = await loadAuditEvents({ showLoading: false, force: true });
        onHangup(finalAuditEvents);
    }, [voipClient, callDuration, connectionState, callInitResponse, apiBaseUrl, authToken, onHangup, loadAuditEvents, restoreWebRtcMicIfVoiceRelayInactive, stopVoiceRelayPlayback, stopVoiceRelaySegment]);

    useEffect(() => {
        if (timeoutAutoReturnRef.current) {
            clearTimeout(timeoutAutoReturnRef.current);
            timeoutAutoReturnRef.current = null;
        }
    }, [error]);

    const handleSendChat = useCallback(() => {
        const text = chatDraft.trim();
        if (!text) {
            return;
        }
        if (!textMatchesDesignatedLanguage(text, localSourceLang)) {
            setChatError(DESIGNATED_LANGUAGE_MISMATCH_MESSAGE);
            return;
        }

        const sentAt = new Date().toISOString();
        if (!voipClient || !voipClient.sendChatMessage(text, sentAt)) {
            setChatError('채팅 채널이 아직 연결되지 않았습니다. 잠시 후 다시 시도하세요.');
            return;
        }

        appendChatEntry({
            id: `${participantRole}-${sentAt}-${text}`,
            fromRole: participantRole,
            text,
            sentAt,
            clientSentAt: sentAt,
            isLocal: true,
            sourceLang: localSourceLang,
            targetLang: localTargetLang,
            translatedText: '',
            translationState: 'pending',
        });
        setChatDraft('');
        setChatError(null);
    }, [appendChatEntry, chatDraft, localSourceLang, localTargetLang, participantRole, voipClient]);

    const formatDuration = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const formatRelayTime = (timestamp: string): string => {
        const parsed = new Date(timestamp);
        if (Number.isNaN(parsed.getTime())) {
            return '';
        }
        return `${parsed.getHours().toString().padStart(2, '0')}:${parsed.getMinutes().toString().padStart(2, '0')}`;
    };

    const handleOpenSettings = useCallback(async () => {
        try {
            await Linking.openSettings();
        } catch (err) {
            console.error('[VoIPScreen] Failed to open settings', err);
        }
    }, []);

    if (error) {
        return (
            <SafeAreaView style={styles.container}>
                <View style={styles.errorContainer}>
                    <Text style={styles.errorTitle}>통화 연결 실패</Text>
                    <Text style={styles.errorMessage}>{error}</Text>
                    {error.includes('60초 내에 연결되지 않았습니다') ? (
                        <Text style={styles.errorAutoReturnHint}>자동 복귀를 막았습니다. 현재 화면에서 상태를 확인한 뒤 직접 돌아가세요.</Text>
                    ) : null}
                    <TouchableOpacity style={styles.button} onPress={handleOpenSettings}>
                        <Text style={styles.buttonText}>권한 설정 열기</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.button} onPress={() => { void handleHangup(); }}>
                        <Text style={styles.buttonText}>돌아가기</Text>
                    </TouchableOpacity>
                </View>
            </SafeAreaView>
        );
    }

    const remoteDisplayName = participantProfile?.nickname || calleePhone || '상대';
    const latestVoiceChatEntry = chatEntries.length ? chatEntries[chatEntries.length - 1] : null;
    const chatSection = (
        <View style={[styles.chatSection, { paddingBottom: sectionPaddingBottom }]}>
            <View style={styles.chatHeaderRow}>
                <Text style={styles.chatTitle}>
                    실시간 쌍언어 채팅
                    {appBuildCode ? ` · build ${appBuildCode}` : ''}
                </Text>
                <Text style={styles.chatHint}>
                    음성 통역 결과가 원문과 번역문 쌍으로 여기에 표시됩니다.
                    {appVersionName ? ` (v${appVersionName})` : ''}
                </Text>
            </View>
            {voiceRelayBusy ? (
                <View style={styles.chatLiveBanner}>
                    <ActivityIndicator color="#7dd3fc" size="small" />
                    <Text style={styles.chatLiveBannerText}>음성 통역 처리 중… 약 3~7초 후 채팅에 반영됩니다.</Text>
                </View>
            ) : null}
            {!voiceRelayBusy && voiceRelayRecording ? (
                <View style={styles.chatLiveBanner}>
                    <Text style={styles.chatLiveBannerRecordingDot}>●</Text>
                    <Text style={styles.chatLiveBannerText}>
                        {voiceRelaySileroActive
                            ? 'Silero VAD · 녹음 중 — 말을 멈추면 자동 번역·전송합니다.'
                            : voiceRelayMeterDead
                                ? '파일 RMS 음성 감지 · 녹음 중 — 말을 멈추면 자동 번역·전송합니다.'
                                : '마이크 수신 중 — 말을 멈추면 자동으로 번역·전송합니다.'}
                    </Text>
                </View>
            ) : null}
            {!voiceRelayBusy && !voiceRelayRecording && voiceRelayListenWaiting ? (
                <View style={styles.chatLiveBanner}>
                    <Text style={styles.chatLiveBannerText}>상대 통역 수신 중 — 잠시 후 마이크가 다시 켜집니다.</Text>
                </View>
            ) : null}
            {voiceRelayError ? (
                <View style={styles.chatLiveBannerError}>
                    <Text style={styles.chatLiveBannerErrorText}>{voiceRelayError}</Text>
                </View>
            ) : null}
            {lastRelayDeliveryHint ? (
                <View style={styles.chatLatestPreview}>
                    <Text style={styles.chatLatestPreviewLabel}>속기·통역 전달</Text>
                    <Text style={styles.chatLatestPreviewTranslated}>{lastRelayDeliveryHint}</Text>
                </View>
            ) : null}
            {latestVoiceChatEntry?.translatedText ? (
                <View style={styles.chatLatestPreview}>
                    <Text style={styles.chatLatestPreviewLabel}>최근 통역</Text>
                    <Text style={styles.chatLatestPreviewOriginal}>{latestVoiceChatEntry.text}</Text>
                    <Text style={styles.chatLatestPreviewTranslated}>{latestVoiceChatEntry.translatedText}</Text>
                </View>
            ) : null}
            <View style={[
                styles.chatCard,
                chatEntries.length ? styles.chatCardActive : null,
                { maxHeight: chatCardMaxHeight },
            ]}>
                <ScrollView
                    ref={chatScrollRef}
                    style={styles.chatLog}
                    contentContainerStyle={styles.chatLogContent}
                    keyboardShouldPersistTaps="handled"
                >
                    {chatEntries.length ? chatEntries.map((entry) => {
                        const senderLabel = entry.fromRole === participantRole ? '나' : remoteDisplayName;
                        const translationLabel = `${entry.sourceLang.toUpperCase()} → ${entry.targetLang.toUpperCase()}`;
                        const translationPending = entry.translationState === 'pending';
                        const translationFailed = entry.translationState === 'failed';
                        const showTranslationPanel = translationPending || translationFailed || !!entry.translatedText;
                        return (
                            <View
                                key={entry.id}
                                style={[
                                    styles.chatBubbleWrap,
                                    entry.isLocal ? styles.chatBubbleWrapLocal : styles.chatBubbleWrapRemote,
                                ]}
                            >
                                <Text style={styles.chatSenderLabel}>{senderLabel}</Text>
                                <View style={[styles.chatBubble, entry.isLocal ? styles.chatBubbleLocal : styles.chatBubbleRemote]}>
                                    <Text style={styles.chatBubbleText}>{entry.text}</Text>
                                    {showTranslationPanel ? (
                                        <>
                                            <View style={styles.chatTranslationDivider} />
                                            <Text style={styles.chatTranslationLabel}>자동 번역 · {translationLabel}</Text>
                                            <Text style={styles.chatTranslationText}>
                                                {translationPending
                                                    ? '번역 중...'
                                                    : translationFailed
                                                        ? '번역을 불러오지 못했습니다. 원문을 표시합니다.'
                                                        : entry.translatedText}
                                            </Text>
                                            {!translationPending && entry.translationEngine ? (
                                                <Text style={styles.chatTranslationMeta}>
                                                    {entry.translationOffline ? 'offline' : entry.translationEngine}
                                                </Text>
                                            ) : null}
                                        </>
                                    ) : null}
                                </View>
                            </View>
                        );
                    }                    ) : (
                        <Text style={styles.chatEmptyText}>
                            아직 통역/채팅이 없습니다. 통화 연결 후 3초 이상 말하면 한국어·영어 쌍이 여기에 표시됩니다.
                        </Text>
                    )}
                </ScrollView>

                <View style={[styles.chatComposerRow, isNarrowWidth && styles.chatComposerRowCompact]}>
                    <TextInput
                        value={chatDraft}
                        onChangeText={setChatDraft}
                        style={[styles.chatInput, { maxHeight: chatInputMaxHeight }, isNarrowWidth && styles.chatInputCompact]}
                        placeholder="메시지를 입력하세요"
                        placeholderTextColor="#7b8aa0"
                        multiline
                        maxLength={280}
                        editable={connectionState !== 'failed' && connectionState !== 'disconnected'}
                    />
                    <TouchableOpacity
                        style={[styles.chatSendButton, isNarrowWidth && styles.chatSendButtonCompact, !chatDraft.trim() && styles.chatSendButtonDisabled]}
                        onPress={handleSendChat}
                        disabled={!chatDraft.trim()}
                    >
                        <Text style={styles.chatSendButtonText}>전송</Text>
                    </TouchableOpacity>
                </View>
                {chatError ? <Text style={styles.chatErrorText}>{chatError}</Text> : null}
            </View>
        </View>
    );

    return (
        <SafeAreaView style={styles.container}>
            <View style={[styles.header, { paddingVertical: headerPaddingVertical }]}>
                <Text style={[styles.calleePhone, isCompactHeight && styles.calleePhoneCompact, isVeryCompactHeight && styles.calleePhoneVeryCompact]}>{participantProfile ? `${participantProfile.countryFlag} ${participantProfile.nickname}` : calleePhone}</Text>
                {participantProfile ? (
                    <View style={[styles.participantMetaWrap, isCompactHeight && styles.participantMetaWrapCompact]}>
                        <Text style={[styles.participantMetaText, isCompactHeight && styles.participantMetaTextCompact]}>닉네임: {participantProfile.nickname}</Text>
                        <Text style={[styles.participantMetaText, isCompactHeight && styles.participantMetaTextCompact]}>성별: {participantProfile.genderLabel}</Text>
                        <Text style={[styles.participantMetaText, isCompactHeight && styles.participantMetaTextCompact]}>국가: {participantProfile.countryName}</Text>
                        <Text style={[styles.participantMetaText, isCompactHeight && styles.participantMetaTextCompact]}>언어: {participantProfile.preferredLanguage ? participantProfile.preferredLanguage.toUpperCase() : '미설정'}</Text>
                        <Text style={[styles.participantMetaText, isCompactHeight && styles.participantMetaTextCompact]}>보이스 ID: {participantProfile.voiceId}</Text>
                    </View>
                ) : null}
                <Text
                    style={[
                        styles.connectionState,
                        connectionState === 'connected' ? styles.stateConnected
                            : (connectionState === 'failed' || connectionState === 'disconnected') ? styles.stateFailed
                                : styles.stateConnecting,
                    ]}
                >
                    {connectionState === 'connected' && hasRemoteAudio ? '통화 중'
                        : connectionState === 'connected' ? '음성 연결 대기'
                            : connectionState === 'failed' ? '연결 실패'
                                : connectionState === 'disconnected' ? '연결 끊김'
                                    : '연결 중...'}
                </Text>
                {connectionState === 'connected' && !hasRemoteAudio ? (
                    <Text style={styles.audioPendingText}>상대 음성 수신 대기 중</Text>
                ) : null}
            </View>

            <View style={styles.mainContent}>
                <ScrollView
                    style={styles.contentScroll}
                    contentContainerStyle={[styles.contentScrollContent, { paddingBottom: sectionPaddingBottom }]}
                    keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.timerContainer}>
                        <Text style={[styles.timer, { fontSize: timerFontSize }]}>{formatDuration(callDuration)}</Text>
                    </View>

                    {chatSection}

                    <View style={[styles.auditSection, { paddingBottom: sectionPaddingBottom }]}>
                        <View style={styles.auditHeaderRow}>
                            <Text style={styles.auditTitle}>통화 모드 감사 로그</Text>
                            <TouchableOpacity
                                style={styles.auditRefreshButton}
                                onPress={() => { void loadAuditEvents({ showLoading: true, force: true }); }}
                                testID="worldlinco-voip-audit-refresh"
                                accessibilityLabel="통화 모드 감사 로그 새로고침"
                            >
                                <Text style={styles.auditRefreshButtonText}>{auditManualRefreshing ? '갱신 중...' : '새로고침'}</Text>
                            </TouchableOpacity>
                        </View>
                        <Text style={styles.auditHint}>call_id 기준으로 /api/v1/voip/calls/{'{'}call_id{'}'}/audit 응답을 바로 표시합니다.</Text>
                        <View style={styles.auditCard}>
                            {auditError ? <Text style={styles.auditErrorText}>{auditError}</Text> : null}
                            {auditEvents.length ? auditEvents.map((event) => (
                                <View key={`${event.id}-${event.created_at}`} style={styles.auditEventRow}>
                                    <Text style={styles.auditEventTitle}>{event.event_type}</Text>
                                    <Text style={styles.auditEventMeta}>
                                        {event.requested_mode}{' -> '}{event.resolved_mode}
                                        {event.call_route ? ` · ${event.call_route}` : ''}
                                    </Text>
                                    <Text style={styles.auditEventMeta}>
                                        {event.created_at}
                                        {event.status ? ` · 상태 ${event.status}` : ''}
                                        {event.error_code ? ` · 오류 ${event.error_code}` : ''}
                                    </Text>
                                    <Text style={styles.auditEventMeta}>
                                        auto_relay {event.auto_relay_requested ? '요청' : '미요청'} / {event.auto_relay_applied ? '적용' : '미적용'}
                                        {typeof event.duration_sec === 'number' ? ` · ${event.duration_sec}s` : ''}
                                        {event.call_quality ? ` · ${event.call_quality}` : ''}
                                    </Text>
                                </View>
                            )) : (
                                <Text style={styles.auditEmptyText}>{auditEvents.length === 0 && !auditError ? '아직 감사 로그가 없습니다.' : ''}</Text>
                            )}
                        </View>
                    </View>

                    <View style={[styles.voiceRelaySection, { paddingBottom: sectionPaddingBottom }]}>
                        {voiceRelaySuggestionVisible ? (
                            <View style={styles.voiceRelaySuggestionCard}>
                                <Text style={styles.voiceRelaySuggestionTitle}>실시간 음성 통역을 켤까요?</Text>
                                <Text style={styles.voiceRelaySuggestionBody}>통화가 연결됐습니다. 지금 켜면 다음 음성 구간부터 자동으로 2.2초 단위 통역을 이어갑니다.</Text>
                                <View style={styles.voiceRelaySuggestionActions}>
                                    <TouchableOpacity style={styles.voiceRelaySuggestionDismissButton} onPress={() => setVoiceRelaySuggestionVisible(false)}>
                                        <Text style={styles.voiceRelaySuggestionDismissText}>나중에</Text>
                                    </TouchableOpacity>
                                    <TouchableOpacity style={styles.voiceRelaySuggestionStartButton} onPress={handleVoiceRelayToggle}>
                                        <Text style={styles.voiceRelaySuggestionStartText}>지금 켜기</Text>
                                    </TouchableOpacity>
                                </View>
                            </View>
                        ) : null}
                        <View style={[styles.voiceRelayHeaderRow, isNarrowWidth && styles.voiceRelayHeaderRowCompact]}>
                            <View style={styles.voiceRelayHeaderCopy}>
                                <Text style={styles.voiceRelayTitle}>실시간 음성 통역</Text>
                                <Text style={styles.voiceRelayHint}>음성 통역 ON 시 결과는 위 「실시간 쌍언어 채팅」에 원문·번역문으로 표시됩니다.</Text>
                            </View>
                            <TouchableOpacity
                                style={[styles.voiceRelayToggleButton, voiceRelayEnabled && styles.voiceRelayToggleButtonActive]}
                                onPress={handleVoiceRelayToggle}
                                disabled={connectionState === 'failed' || connectionState === 'disconnected'}
                            >
                                <Text style={styles.voiceRelayToggleButtonText}>{voiceRelayEnabled ? '중지' : '시작'}</Text>
                            </TouchableOpacity>
                        </View>
                        <View style={styles.voiceRelayCard}>
                            <Text style={styles.voiceRelayStatusText}>
                                {voiceRelayEnabled
                                    ? voiceRelayRecording
                                        ? voiceRelaySileroActive
                                            ? 'Silero VAD로 음성 끝 감지 · 녹음 중입니다.'
                                            : voiceRelayMeterDead
                                                ? '파일 RMS로 음성 감지 · 녹음 중입니다.'
                                                : '지금 음성을 듣고 있습니다.'
                                        : voiceRelayBusy
                                            ? '통역 및 전송 중입니다.'
                                        : voiceRelayListenWaiting
                                            ? '상대 통역 재생/수신 중 — 곧 마이크가 재개됩니다.'
                                            : connectionState === 'connected' && hasRemoteAudio
                                                ? '다음 음성 구간을 대기 중입니다.'
                                                : '상대 음성 경로가 열리면 시작 준비 상태로 대기합니다.'
                                    : voiceRelayServerReady
                                        ? '서버 relay 경로가 준비됐습니다. 연결 직후 자동 통역 시작을 대기 중입니다.'
                                        : '실시간 음성 통역이 꺼져 있습니다.'}
                            </Text>
                            <Text style={styles.voiceRelayDiagnosticsText}>현재 지역 힌트: {regionHint || '없음'}</Text>
                            {lastTranslationProbe ? <Text style={styles.voiceRelayPayloadText}>{lastTranslationProbe}</Text> : null}
                            {voiceRelayError ? <Text style={styles.voiceRelayErrorText}>{voiceRelayError}</Text> : null}
                            {voiceRelayEntries.length ? voiceRelayEntries.slice(-3).reverse().map((entry) => {
                                const speakerLabel = entry.fromRole === participantRole ? '나' : remoteDisplayName;
                                return (
                                    <View key={entry.id} style={styles.voiceRelayEntryRow}>
                                        <View style={styles.voiceRelayEntryHeader}>
                                            <Text style={styles.voiceRelaySpeaker}>{speakerLabel}</Text>
                                            <Text style={styles.voiceRelayTime}>{formatRelayTime(entry.sentAt)}</Text>
                                        </View>
                                        <Text style={styles.voiceRelayTranscript}>{entry.transcript}</Text>
                                        <Text style={styles.voiceRelayTranslationMeta}>{entry.sourceLang.toUpperCase()} → {entry.targetLang.toUpperCase()}</Text>
                                        <Text style={styles.voiceRelayTranslated}>{entry.translatedText}</Text>
                                    </View>
                                );
                            }) : (
                                <Text style={styles.voiceRelayEmptyText}>음성 통역 결과는 위 실시간 채팅 카드에 쌍언어로 표시됩니다.</Text>
                            )}
                        </View>
                    </View>

                    {((connectionState !== 'connected' && connectionState !== 'failed' && connectionState !== 'disconnected') || (connectionState === 'connected' && !hasRemoteAudio)) && (
                        <View style={styles.statusContainer}>
                            <ActivityIndicator color="#FF6B6B" size="large" />
                            <Text style={styles.statusText}>{connectionState === 'connected' ? '상대 음성 경로 확인 중...' : '음성 경로 연결 중...'}</Text>
                        </View>
                    )}
                </ScrollView>

                <View style={[styles.controlsContainer, { paddingBottom: controlsPaddingBottom }, isCompactHeight && styles.controlsContainerCompact]}>
                    <TouchableOpacity style={[styles.hangupPrimaryButton, { minHeight: hangupButtonMinHeight }, isCompactHeight && styles.hangupPrimaryButtonCompact]} onPress={handleHangup}>
                        <Text style={styles.hangupPrimaryIcon}>📵</Text>
                        <Text style={[styles.hangupPrimaryText, isCompactHeight && styles.hangupPrimaryTextCompact]}>통화 종료</Text>
                    </TouchableOpacity>

                    <View style={[styles.secondaryControlsRow, isNarrowWidth && styles.secondaryControlsRowCompact]}>
                        {/* Mute Button */}
                        <TouchableOpacity
                            style={[styles.controlButton, { minHeight: controlButtonMinHeight }, isCompactHeight && styles.controlButtonCompact, isMuted && styles.controlButtonActive]}
                            onPress={handleMuteToggle}
                            disabled={connectionState !== 'connected' || !hasRemoteAudio}
                        >
                            <Text style={styles.controlButtonText}>{isMuted ? '🔇' : '🎤'}</Text>
                            <Text style={[styles.controlButtonLabel, isCompactHeight && styles.controlButtonLabelCompact]}>{isMuted ? '음소거 중' : '음성'}</Text>
                        </TouchableOpacity>

                        {/* Speaker Button */}
                        <TouchableOpacity
                            style={[styles.controlButton, { minHeight: controlButtonMinHeight }, isCompactHeight && styles.controlButtonCompact, isSpeakerOn && styles.controlButtonActive]}
                            onPress={handleSpeakerToggle}
                            disabled={connectionState !== 'connected' || !hasRemoteAudio}
                        >
                            <Text style={styles.controlButtonText}>{isSpeakerOn ? '🔊' : '📞'}</Text>
                            <Text style={[styles.controlButtonLabel, isCompactHeight && styles.controlButtonLabelCompact]}>{isSpeakerOn ? '스피커' : '수화기'}</Text>
                        </TouchableOpacity>

                    </View>
                </View>
            </View>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#1a1a1a',
    },
    mainContent: {
        flex: 1,
    },
    contentScroll: {
        flex: 1,
    },
    contentScrollContent: {
        flexGrow: 1,
        paddingBottom: 16,
    },
    header: {
        paddingVertical: 20,
        paddingHorizontal: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#333',
        alignItems: 'center',
    },
    calleePhone: {
        fontSize: 20,
        fontWeight: '600',
        color: '#fff',
        marginBottom: 8,
    },
    calleePhoneCompact: {
        fontSize: 18,
        marginBottom: 6,
    },
    calleePhoneVeryCompact: {
        fontSize: 16,
    },
    participantMetaWrap: {
        width: '100%',
        backgroundColor: '#101a2a',
        borderWidth: 1,
        borderColor: '#2a415e',
        borderRadius: 12,
        paddingHorizontal: 14,
        paddingVertical: 12,
        marginBottom: 10,
    },
    participantMetaWrapCompact: {
        paddingHorizontal: 12,
        paddingVertical: 10,
        marginBottom: 8,
    },
    participantMetaText: {
        color: '#dbeaff',
        fontSize: 13,
        lineHeight: 20,
    },
    participantMetaTextCompact: {
        fontSize: 12,
        lineHeight: 18,
    },
    connectionState: {
        fontSize: 12,
        fontWeight: '500',
    },
    stateConnected: {
        color: '#4CAF50',
    },
    stateConnecting: {
        color: '#FF9800',
    },
    stateFailed: {
        color: '#FF6B6B',
    },
    audioPendingText: {
        marginTop: 6,
        fontSize: 12,
        color: '#FF9800',
    },
    auditSection: {
        paddingHorizontal: 16,
        paddingBottom: 12,
    },
    auditHeaderRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 6,
    },
    auditTitle: {
        color: '#fff',
        fontSize: 15,
        fontWeight: '700',
    },
    auditHint: {
        color: '#8ea3bf',
        fontSize: 11,
        marginBottom: 8,
    },
    auditRefreshButton: {
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 10,
        backgroundColor: '#172332',
        borderWidth: 1,
        borderColor: '#2a415e',
    },
    auditRefreshButtonText: {
        color: '#b8d6ff',
        fontSize: 11,
        fontWeight: '700',
    },
    auditCard: {
        backgroundColor: '#101923',
        borderRadius: 16,
        borderWidth: 1,
        borderColor: '#223247',
        padding: 12,
        gap: 8,
    },
    auditEventRow: {
        borderRadius: 12,
        backgroundColor: '#162435',
        paddingHorizontal: 10,
        paddingVertical: 9,
        gap: 3,
    },
    auditEventTitle: {
        color: '#eef6ff',
        fontSize: 13,
        fontWeight: '700',
    },
    auditEventMeta: {
        color: '#9fb7d6',
        fontSize: 11,
        lineHeight: 16,
    },
    auditEmptyText: {
        color: '#7f8ea3',
        fontSize: 12,
        lineHeight: 18,
    },
    auditErrorText: {
        color: '#ff9a9a',
        fontSize: 12,
        lineHeight: 18,
    },
    voiceRelaySection: {
        paddingHorizontal: 16,
        paddingBottom: 12,
    },
    voiceRelayHeaderRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 12,
        marginBottom: 8,
    },
    voiceRelayHeaderRowCompact: {
        alignItems: 'flex-start',
        flexWrap: 'wrap',
    },
    voiceRelaySuggestionCard: {
        backgroundColor: '#1b2530',
        borderRadius: 16,
        borderWidth: 1,
        borderColor: '#35506e',
        padding: 12,
        marginBottom: 10,
        gap: 8,
    },
    voiceRelaySuggestionTitle: {
        color: '#eef6ff',
        fontSize: 13,
        fontWeight: '700',
    },
    voiceRelaySuggestionBody: {
        color: '#b7cae2',
        fontSize: 12,
        lineHeight: 18,
    },
    voiceRelaySuggestionActions: {
        flexDirection: 'row',
        justifyContent: 'flex-end',
        gap: 8,
    },
    voiceRelaySuggestionDismissButton: {
        paddingHorizontal: 10,
        paddingVertical: 8,
        borderRadius: 10,
        backgroundColor: '#101923',
        borderWidth: 1,
        borderColor: '#31465f',
    },
    voiceRelaySuggestionDismissText: {
        color: '#d6e4f5',
        fontSize: 12,
        fontWeight: '600',
    },
    voiceRelaySuggestionStartButton: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 10,
        backgroundColor: '#2f6b3f',
        borderWidth: 1,
        borderColor: '#60b46d',
    },
    voiceRelaySuggestionStartText: {
        color: '#f4fff6',
        fontSize: 12,
        fontWeight: '700',
    },
    voiceRelayHeaderCopy: {
        flex: 1,
    },
    voiceRelayTitle: {
        color: '#fff',
        fontSize: 15,
        fontWeight: '700',
    },
    voiceRelayHint: {
        marginTop: 4,
        color: '#8ea3bf',
        fontSize: 12,
    },
    voiceRelayToggleButton: {
        paddingHorizontal: 14,
        paddingVertical: 9,
        borderRadius: 12,
        backgroundColor: '#172332',
        borderWidth: 1,
        borderColor: '#2a415e',
    },
    voiceRelayToggleButtonActive: {
        backgroundColor: '#235b2f',
        borderColor: '#4CAF50',
    },
    voiceRelayToggleButtonText: {
        color: '#eef6ff',
        fontSize: 12,
        fontWeight: '700',
    },
    voiceRelayCard: {
        backgroundColor: '#101923',
        borderRadius: 18,
        borderWidth: 1,
        borderColor: '#223247',
        padding: 12,
        gap: 8,
    },
    voiceRelayStatusText: {
        color: '#dbeaff',
        fontSize: 12,
        lineHeight: 18,
    },
    voiceRelayDiagnosticsText: {
        color: '#8bd7ff',
        fontSize: 11,
        lineHeight: 16,
    },
    voiceRelayPayloadText: {
        color: '#8ea3bf',
        fontSize: 10,
        lineHeight: 15,
    },
    voiceRelayErrorText: {
        color: '#ff9a9a',
        fontSize: 12,
        lineHeight: 18,
    },
    voiceRelayEmptyText: {
        color: '#7f8ea3',
        fontSize: 12,
        lineHeight: 18,
    },
    voiceRelayEntryRow: {
        backgroundColor: '#162435',
        borderRadius: 12,
        paddingHorizontal: 10,
        paddingVertical: 9,
        gap: 4,
    },
    voiceRelayEntryHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 8,
    },
    voiceRelaySpeaker: {
        color: '#b8d6ff',
        fontSize: 11,
        fontWeight: '700',
    },
    voiceRelayTime: {
        color: '#7f8ea3',
        fontSize: 10,
    },
    voiceRelayTranscript: {
        color: '#eef6ff',
        fontSize: 13,
        lineHeight: 18,
    },
    voiceRelayTranslationMeta: {
        color: '#8ea3bf',
        fontSize: 10,
    },
    voiceRelayTranslated: {
        color: '#7dd3fc',
        fontSize: 13,
        lineHeight: 18,
        fontWeight: '600',
    },
    timerContainer: {
        paddingTop: 12,
        paddingBottom: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    timer: {
        fontSize: 56,
        fontWeight: '300',
        color: '#fff',
        fontVariant: ['tabular-nums'],
    },
    chatSection: {
        paddingHorizontal: 16,
        paddingBottom: 12,
    },
    chatHeaderRow: {
        marginBottom: 8,
    },
    chatTitle: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '700',
    },
    chatHint: {
        marginTop: 4,
        color: '#8ea3bf',
        fontSize: 12,
    },
    chatCard: {
        backgroundColor: '#101923',
        borderRadius: 18,
        borderWidth: 1,
        borderColor: '#223247',
        padding: 12,
    },
    chatCardActive: {
        borderColor: '#3b82f6',
        shadowColor: '#3b82f6',
        shadowOpacity: 0.25,
        shadowRadius: 8,
        elevation: 4,
    },
    chatLiveBanner: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: '#132033',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#2a4566',
        paddingHorizontal: 12,
        paddingVertical: 10,
        marginBottom: 8,
    },
    chatLiveBannerText: {
        flex: 1,
        color: '#cfe8ff',
        fontSize: 12,
        lineHeight: 18,
    },
    chatLiveBannerRecordingDot: {
        color: '#ef4444',
        fontSize: 14,
        fontWeight: '700',
    },
    chatLiveBannerError: {
        backgroundColor: '#3a1414',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#7f1d1d',
        paddingHorizontal: 12,
        paddingVertical: 10,
        marginBottom: 8,
    },
    chatLiveBannerErrorText: {
        color: '#fecaca',
        fontSize: 12,
        lineHeight: 18,
    },
    chatLatestPreview: {
        backgroundColor: '#0f1a28',
        borderRadius: 14,
        borderWidth: 1,
        borderColor: '#35507a',
        paddingHorizontal: 12,
        paddingVertical: 10,
        marginBottom: 8,
    },
    chatLatestPreviewLabel: {
        color: '#93c5fd',
        fontSize: 11,
        fontWeight: '700',
        marginBottom: 6,
    },
    chatLatestPreviewOriginal: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
        lineHeight: 20,
    },
    chatLatestPreviewTranslated: {
        marginTop: 6,
        color: '#bfdbfe',
        fontSize: 14,
        lineHeight: 20,
    },
    chatLog: {
        minHeight: 96,
    },
    chatLogContent: {
        gap: 10,
        paddingBottom: 12,
    },
    chatEmptyText: {
        color: '#7f8ea3',
        fontSize: 13,
        lineHeight: 20,
    },
    chatBubbleWrap: {
        maxWidth: '86%',
    },
    chatBubbleWrapLocal: {
        alignSelf: 'flex-end',
    },
    chatBubbleWrapRemote: {
        alignSelf: 'flex-start',
    },
    chatSenderLabel: {
        color: '#8ea3bf',
        fontSize: 11,
        marginBottom: 4,
    },
    chatBubble: {
        borderRadius: 16,
        paddingHorizontal: 12,
        paddingVertical: 10,
    },
    chatBubbleLocal: {
        backgroundColor: '#2d8cff',
    },
    chatBubbleRemote: {
        backgroundColor: '#1d2938',
    },
    chatBubbleText: {
        color: '#fff',
        fontSize: 14,
        lineHeight: 20,
        fontWeight: '600',
    },
    chatTranslationDivider: {
        height: 1,
        backgroundColor: 'rgba(255,255,255,0.16)',
        marginVertical: 8,
    },
    chatTranslationLabel: {
        color: '#b8d6ff',
        fontSize: 11,
        fontWeight: '700',
        marginBottom: 4,
    },
    chatTranslationText: {
        color: '#eef6ff',
        fontSize: 13,
        lineHeight: 18,
    },
    chatTranslationMeta: {
        color: '#9fb7d6',
        fontSize: 10,
        marginTop: 6,
    },
    chatComposerRow: {
        flexDirection: 'row',
        gap: 10,
        alignItems: 'flex-end',
        borderTopWidth: 1,
        borderTopColor: '#223247',
        paddingTop: 12,
    },
    chatComposerRowCompact: {
        flexWrap: 'wrap',
    },
    chatInput: {
        flex: 1,
        minHeight: 44,
        maxHeight: 96,
        backgroundColor: '#172332',
        borderRadius: 14,
        paddingHorizontal: 14,
        paddingVertical: 10,
        color: '#fff',
        fontSize: 14,
    },
    chatInputCompact: {
        minWidth: '100%',
    },
    chatSendButton: {
        minWidth: 68,
        height: 44,
        borderRadius: 14,
        backgroundColor: '#2d8cff',
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 14,
    },
    chatSendButtonCompact: {
        width: '100%',
    },
    chatSendButtonDisabled: {
        backgroundColor: '#3b4c61',
    },
    chatSendButtonText: {
        color: '#fff',
        fontSize: 13,
        fontWeight: '700',
    },
    chatErrorText: {
        marginTop: 8,
        color: '#ff9a9a',
        fontSize: 12,
    },
    controlsContainer: {
        paddingTop: 12,
        paddingBottom: 20,
        paddingHorizontal: 16,
        gap: 12,
        borderTopWidth: 1,
        borderTopColor: '#333',
        backgroundColor: '#1a1a1a',
    },
    controlsContainerCompact: {
        paddingTop: 10,
        gap: 10,
    },
    hangupPrimaryButton: {
        minHeight: 56,
        borderRadius: 18,
        backgroundColor: '#d64545',
        borderWidth: 1,
        borderColor: '#ff8f8f',
        paddingHorizontal: 18,
        paddingVertical: 14,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
    },
    hangupPrimaryButtonCompact: {
        paddingVertical: 12,
    },
    hangupPrimaryIcon: {
        fontSize: 22,
    },
    hangupPrimaryText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '700',
    },
    hangupPrimaryTextCompact: {
        fontSize: 15,
    },
    secondaryControlsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        gap: 12,
    },
    secondaryControlsRowCompact: {
        gap: 8,
    },
    controlButton: {
        flex: 1,
        minHeight: 76,
        borderRadius: 18,
        backgroundColor: '#333',
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 8,
        paddingVertical: 10,
    },
    controlButtonCompact: {
        paddingVertical: 8,
    },
    controlButtonActive: {
        backgroundColor: '#FF6B6B',
    },
    controlButtonText: {
        fontSize: 24,
        marginBottom: 4,
    },
    controlButtonLabel: {
        fontSize: 10,
        color: '#aaa',
        marginTop: 4,
        textAlign: 'center',
    },
    controlButtonLabelCompact: {
        fontSize: 9,
        marginTop: 2,
    },
    hangupButton: {
        backgroundColor: '#FF6B6B',
    },
    hangupButtonText: {
        fontSize: 24,
    },
    statusContainer: {
        paddingBottom: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    statusText: {
        fontSize: 12,
        color: '#FF9800',
        marginTop: 8,
    },
    errorContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 20,
    },
    errorTitle: {
        fontSize: 20,
        fontWeight: '600',
        color: '#FF6B6B',
        marginBottom: 12,
    },
    errorMessage: {
        fontSize: 14,
        color: '#aaa',
        textAlign: 'center',
        marginBottom: 20,
    },
    errorAutoReturnHint: {
        fontSize: 13,
        color: '#9fb3c8',
        textAlign: 'center',
        marginTop: -6,
        marginBottom: 18,
    },
    button: {
        paddingHorizontal: 20,
        paddingVertical: 12,
        backgroundColor: '#FF6B6B',
        borderRadius: 8,
    },
    buttonText: {
        fontSize: 14,
        fontWeight: '600',
        color: '#fff',
    },
});
