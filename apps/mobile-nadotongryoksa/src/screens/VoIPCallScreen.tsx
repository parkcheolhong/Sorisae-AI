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
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import * as Speech from 'expo-speech';
import { VoIPCallClient, CallInitResponse, VoIPChatMessage, VoIPVoiceTranslationMessage } from '../services/voipCallClient';
import { getVoIPToneService } from '../services/voipToneService';
import { translateText, voiceTranslate } from '../api/translate';

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
const VOICE_RELAY_SEGMENT_MS = 1_800;
const VOICE_RELAY_DUPLICATE_GUARD_MS = 3_000;
const VOICE_RELAY_SUPPRESS_MIN_MS = 1_200;
const VOICE_RELAY_SUPPRESS_CHAR_MS = 55;
const TTS_LANGUAGE_MAP: Record<string, string> = {
    ar: 'ar-SA',
    de: 'de-DE',
    en: 'en-US',
    es: 'es-ES',
    fr: 'fr-FR',
    hi: 'hi-IN',
    id: 'id-ID',
    it: 'it-IT',
    ja: 'ja-JP',
    ko: 'ko-KR',
    pt: 'pt-PT',
    ru: 'ru-RU',
    th: 'th-TH',
    tr: 'tr-TR',
    vi: 'vi-VN',
    zh: 'zh-CN',
    'zh-cn': 'zh-CN',
    'zh-tw': 'zh-TW',
};

const normalizeRelayText = (value: string): string => value.trim().replace(/\s+/g, ' ').toLowerCase();

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
    const [hasRemoteAudio, setHasRemoteAudio] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [chatDraft, setChatDraft] = useState<string>('');
    const [chatError, setChatError] = useState<string | null>(null);
    const [chatEntries, setChatEntries] = useState<CallChatEntry[]>([]);
    const [voiceRelayEnabled, setVoiceRelayEnabled] = useState<boolean>(false);
    const [voiceRelaySuggestionVisible, setVoiceRelaySuggestionVisible] = useState<boolean>(false);
    const [voiceRelayRecording, setVoiceRelayRecording] = useState<boolean>(false);
    const [voiceRelayBusy, setVoiceRelayBusy] = useState<boolean>(false);
    const [voiceRelayError, setVoiceRelayError] = useState<string | null>(null);
    const [voiceRelayEntries, setVoiceRelayEntries] = useState<CallVoiceRelayEntry[]>([]);
    const [lastTranslationProbe, setLastTranslationProbe] = useState<string>('');
    const [auditEvents, setAuditEvents] = useState<CallModeAuditEvent[]>([]);
    const [auditLoading, setAuditLoading] = useState<boolean>(false);
    const [auditError, setAuditError] = useState<string | null>(null);
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
    const remoteAudioSuppressedRef = useRef<boolean>(false);
    const chatScrollRef = useRef<ScrollView | null>(null);

    const loadAuditEvents = useCallback(async (): Promise<CallModeAuditEvent[]> => {
        setAuditLoading(true);
        setAuditError(null);
        try {
            const response = await fetch(`${apiBaseUrl}/api/v1/voip/calls/${callInitResponse.call_id}/audit`, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`audit fetch failed: HTTP ${response.status}`);
            }

            const payload = await response.json();
            const events = Array.isArray(payload) ? (payload as CallModeAuditEvent[]) : [];
            setAuditEvents(events);
            return events;
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setAuditError(message);
            return auditEvents;
        } finally {
            setAuditLoading(false);
        }
    }, [apiBaseUrl, authToken, callInitResponse.call_id, auditEvents]);

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
        const normalized = langCode.trim().toLowerCase();
        return TTS_LANGUAGE_MAP[normalized] || langCode || 'ko-KR';
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
    }, []);

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
        if (!client || remoteAudioSuppressedRef.current === suppressed) {
            return;
        }
        remoteAudioSuppressedRef.current = suppressed;
        client.setRemoteAudioEnabled(!suppressed);
        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_REMOTE_AUDIO_SUPPRESSION',
            call_id: callInitResponse.call_id,
            suppressed,
            timestamp: new Date().toISOString(),
        }));
    }, [callInitResponse.call_id]);

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
        const normalizedText = translatedText.trim();
        if (!normalizedText) {
            return;
        }

        voiceRelaySuppressUntilRef.current = Date.now() + Math.max(VOICE_RELAY_SUPPRESS_MIN_MS, normalizedText.length * VOICE_RELAY_SUPPRESS_CHAR_MS);

        await stopVoiceRelayPlayback();
        Speech.stop();
        setRemoteAudioSuppressed(true);

        let playbackUri = resolveVoiceRelayAudioUrl(audioUrl);
        if (!playbackUri && audioBase64) {
            const extension = resolvePlaybackExtension(audioFormat);
            const tempPath = `${FileSystem.cacheDirectory || FileSystem.documentDirectory}voice-relay-${Date.now()}.${extension}`;
            try {
                await FileSystem.writeAsStringAsync(tempPath, audioBase64, {
                    encoding: FileSystem.EncodingType.Base64,
                });
                voiceRelayPlaybackFileRef.current = tempPath;
                playbackUri = tempPath;
            } catch (err) {
                console.warn('[VoIPScreen] Failed to persist translated audio payload', err);
            }
        }

        if (playbackUri) {
            try {
                const { sound } = await Audio.Sound.createAsync(
                    { uri: playbackUri },
                    { shouldPlay: true, isLooping: false, volume: 1.0 },
                );
                voiceRelayPlaybackRef.current = sound;
                sound.setOnPlaybackStatusUpdate((status) => {
                    if (!status.isLoaded || status.didJustFinish) {
                        setRemoteAudioSuppressed(false);
                        void stopVoiceRelayPlayback();
                    }
                });
                return;
            } catch (err) {
                console.warn('[VoIPScreen] Failed to play translated audio payload, falling back to TTS', err);
            }
        }

        Speech.speak(normalizedText, {
            language: resolveTtsLanguage(targetLang),
            rate: 0.9,
            onDone: () => setRemoteAudioSuppressed(false),
            onStopped: () => setRemoteAudioSuppressed(false),
            onError: () => setRemoteAudioSuppressed(false),
        });
    }, [resolvePlaybackExtension, resolveTtsLanguage, resolveVoiceRelayAudioUrl, setRemoteAudioSuppressed, stopVoiceRelayPlayback]);

    const processVoiceRelaySegment = useCallback(async (uri: string) => {
        voiceRelayProcessingRef.current = true;
        setVoiceRelayBusy(true);
        setVoiceRelayError(null);

        try {
            const base64Audio = await FileSystem.readAsStringAsync(uri, {
                encoding: FileSystem.EncodingType.Base64,
            });
            if (!base64Audio) {
                setVoiceRelayError('녹음된 음성 데이터를 읽지 못했습니다.');
                return;
            }

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

            const result = await voiceTranslate(base64Audio, localSourceLang, localTargetLang, regionHint);
            const transcript = String(result.original_text || '').trim();
            const translatedText = String(result.translated || '').trim();
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_TRANSLATE_RESULT',
                call_id: callInitResponse.call_id,
                source_lang: localSourceLang,
                target_lang: localTargetLang,
                transcript_length: transcript.length,
                translated_length: translatedText.length,
                has_audio_url: !!result.audio_url,
                has_audio_base64: !!result.audio_base64,
                audio_format: result.audio_format || null,
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

            const dedupeKey = `${normalizeRelayText(transcript)}::${normalizeRelayText(translatedText)}::${localTargetLang}`;
            const now = Date.now();
            if (lastVoiceRelayKeyRef.current === dedupeKey && now - lastVoiceRelayAtRef.current < VOICE_RELAY_DUPLICATE_GUARD_MS) {
                return;
            }

            lastVoiceRelayKeyRef.current = dedupeKey;
            lastVoiceRelayAtRef.current = now;

            const sentAt = new Date().toISOString();
            appendVoiceRelayEntry({
                id: `voice-local-${sentAt}`,
                fromRole: participantRole,
                transcript,
                translatedText,
                sourceLang: localSourceLang,
                targetLang: localTargetLang,
                sentAt,
                isLocal: true,
                audioUrl: result.audio_url,
                audioBase64: result.audio_base64,
                audioFormat: result.audio_format,
            });

            const sent = voipClientRef.current?.sendVoiceTranslation({
                transcript,
                translatedText,
                sourceLang: localSourceLang,
                targetLang: localTargetLang,
                audioUrl: result.audio_url,
                audioBase64: result.audio_base64,
                audioFormat: result.audio_format,
                sentAt,
            });

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
        } catch (err) {
            setVoiceRelayError(err instanceof Error ? err.message : '실시간 음성 통역 처리에 실패했습니다.');
        } finally {
            voiceRelayProcessingRef.current = false;
            setVoiceRelayBusy(false);
            try {
                await FileSystem.deleteAsync(uri, { idempotent: true });
            } catch {
                // ignore temp cleanup failures
            }
        }
    }, [appendVoiceRelayEntry, callInitResponse.call_id, localSourceLang, localTargetLang, participantRole, regionHint]);

    const stopVoiceRelaySegment = useCallback(async (processSegment: boolean) => {
        clearVoiceRelayTimers();

        const recording = voiceRelayRecordingRef.current;
        voiceRelayRecordingRef.current = null;
        setVoiceRelayRecording(false);
        if (!recording) {
            return;
        }

        try {
            await recording.stopAndUnloadAsync();
            const uri = recording.getURI();
            if (uri && processSegment) {
                await processVoiceRelaySegment(uri);
            } else if (uri) {
                await FileSystem.deleteAsync(uri, { idempotent: true });
            }
        } catch (err) {
            console.warn('[VoIPScreen] Failed to stop voice relay segment', err);
        }
    }, [clearVoiceRelayTimers, processVoiceRelaySegment]);

    const startVoiceRelaySegment = useCallback(async () => {
        if (Platform.OS === 'web') {
            setVoiceRelayError('웹에서는 통화 중 실시간 음성 통역 녹음을 지원하지 않습니다.');
            setVoiceRelayEnabled(false);
            return;
        }
        if (!voiceRelayEnabledRef.current || connectionState !== 'connected' || !hasRemoteAudio || voiceRelayRecordingRef.current || voiceRelayProcessingRef.current) {
            return;
        }

        try {
            const permission = await Audio.requestPermissionsAsync();
            if (!permission.granted) {
                setVoiceRelayError('마이크 권한이 없어 실시간 음성 통역을 시작할 수 없습니다.');
                setVoiceRelayEnabled(false);
                return;
            }

            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: false,
                playThroughEarpieceAndroid: !isSpeakerOn,
                staysActiveInBackground: false,
            });

            const recording = new Audio.Recording();
            await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
            await recording.startAsync();

            voiceRelayRecordingRef.current = recording;
            setVoiceRelayRecording(true);
            setVoiceRelayError(null);

            voiceRelayStopTimerRef.current = setTimeout(() => {
                void stopVoiceRelaySegment(true);
            }, VOICE_RELAY_SEGMENT_MS);
        } catch (err) {
            setVoiceRelayError(err instanceof Error ? err.message : '실시간 음성 통역 녹음을 시작하지 못했습니다.');
            setVoiceRelayEnabled(false);
        }
    }, [connectionState, hasRemoteAudio, isSpeakerOn, stopVoiceRelaySegment]);

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

    // Initialize VoIP client and establish connection
    useEffect(() => {
        const initializeCall = async () => {
            try {
                // Permission already requested in parent (App.tsx)
                // No need to request again here

                const client = new VoIPCallClient({
                    callId: callInitResponse.call_id,
                    signalingServerUrl: callInitResponse.signaling_server,
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
                setVoipClient(client);
                setConnectionState(client.getConnectionState());

                // Register state change callback
                client.onStateChange((state: string) => {
                    console.log('[VoIPScreen] State change callback:', state);
                    if (forcedTerminalStateRef.current) {
                        setConnectionState(forcedTerminalStateRef.current);
                        return;
                    }
                    setConnectionState(state);
                    if (state === 'connected' && connectionTimeoutRef.current) {
                        clearTimeout(connectionTimeoutRef.current);
                        connectionTimeoutRef.current = null;
                    }
                    if (state === 'connected' && !client.hasRemoteAudioTrack() && !remoteAudioTimeoutRef.current) {
                        remoteAudioTimeoutRef.current = setTimeout(() => {
                            if (!client.hasRemoteAudioTrack()) {
                                console.warn('[VoIPScreen] Remote audio timeout after connection');
                                void failCallAndStopTone('상대 음성 경로가 연결되지 않았습니다. 번호를 확인하거나 다시 걸어주세요.');
                            }
                        }, 30000);
                    }
                    if ((state === 'failed' || state === 'disconnected') && !error) {
                        setError(state === 'failed'
                            ? '통화 연결에 실패했습니다. 네트워크 또는 서버 상태를 확인해주세요.'
                            : '통화 연결이 끊어졌습니다.');
                    }
                });

                client.onRemoteStream((stream: any) => {
                    const audioTracks = stream?.getAudioTracks?.() ?? [];
                    const hasAudio = audioTracks.some((track: any) => track?.enabled !== false && track?.readyState !== 'ended');
                    console.log('[VoIPScreen] Remote stream update:', { hasAudio, audioTrackCount: audioTracks.length });
                    setHasRemoteAudio(hasAudio);
                    if (hasAudio && remoteAudioTimeoutRef.current) {
                        clearTimeout(remoteAudioTimeoutRef.current);
                        remoteAudioTimeoutRef.current = null;
                    }
                });

                client.onChatMessage((message: VoIPChatMessage) => {
                    const text = typeof message.text === 'string' ? message.text.trim() : '';
                    if (!text) {
                        return;
                    }

                    const fromRole = message.from_role === 'callee' ? 'callee' : 'caller';
                    if (fromRole !== participantRole) {
                        getVoIPToneService().playMessageTone();
                    }
                    const translationPair = resolveChatLanguagePair(fromRole === participantRole);
                    const translatedText = typeof message.translated_text === 'string' ? message.translated_text.trim() : '';
                    const translationStatus = typeof message.translation_status === 'string' ? message.translation_status.trim().toLowerCase() : '';
                    const hasServerTranslation = translatedText.length > 0;
                    appendChatEntry({
                        id: message.message_id || `${fromRole}-${message.sent_at || Date.now()}-${text}`,
                        fromRole,
                        text,
                        sentAt: message.sent_at || new Date().toISOString(),
                        clientSentAt: message.client_sent_at,
                        isLocal: fromRole === participantRole,
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

                client.onVoiceTranslation((message: VoIPVoiceTranslationMessage) => {
                    const transcript = typeof message.transcript === 'string' ? message.transcript.trim() : '';
                    const translatedText = typeof message.translated_text === 'string' ? message.translated_text.trim() : '';
                    if (!transcript || !translatedText) {
                        return;
                    }

                    const fromRole = message.from_role === 'callee' ? 'callee' : 'caller';
                    const isLocal = fromRole === participantRole;
                    appendVoiceRelayEntry({
                        id: `voice-${fromRole}-${message.sent_at || Date.now()}-${transcript}`,
                        fromRole,
                        transcript,
                        translatedText,
                        sourceLang: message.source_lang || (isLocal ? localSourceLang : localTargetLang),
                        targetLang: message.target_lang || (isLocal ? localTargetLang : localSourceLang),
                        sentAt: message.sent_at || new Date().toISOString(),
                        isLocal,
                        audioUrl: message.audio_url,
                        audioBase64: message.audio_base64,
                        audioFormat: message.audio_format,
                    });

                    if (!isLocal) {
                        getVoIPToneService().playMessageTone();
                        void stopVoiceRelaySegment(false);
                        void playVoiceRelayOutput(
                            message.audio_url,
                            message.audio_base64,
                            message.audio_format,
                            translatedText,
                            message.target_lang || localSourceLang,
                        );
                    }
                });

                // Stop ringing/wingback after 60 seconds if the call never reaches a live media path.
                connectionTimeoutRef.current = setTimeout(() => {
                    const state = client.getConnectionState();
                    if (state !== 'connected') {
                        console.warn('[VoIPScreen] Connection timeout after 60s, state:', state);
                        void failCallAndStopTone('60초 내에 연결되지 않았습니다. 네트워크 상태를 확인해주세요.');
                    }
                }, CALL_CONNECT_TIMEOUT_MS);
            } catch (err) {
                console.warn('[VoIPScreen] Initialization failed', err);
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
            void stopVoiceRelaySegment(false);
            void stopVoiceRelayPlayback();
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
    }, [appendChatEntry, appendVoiceRelayEntry, callInitResponse.call_id, callInitResponse.participant_role, callInitResponse.signaling_server, callInitResponse.turn_servers, localSourceLang, localTargetLang, participantRole, playVoiceRelayOutput, resolveChatLanguagePair, stopVoiceRelayPlayback, stopVoiceRelaySegment]);

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
            setVoiceRelayEnabled(true);
        }
    }, [connectionState, voiceRelayEnabled, voiceRelayServerReady]);

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
            return;
        }

        if (Date.now() < voiceRelaySuppressUntilRef.current) {
            voiceRelayRestartTimerRef.current = setTimeout(() => {
                void startVoiceRelaySegment();
            }, Math.max(250, voiceRelaySuppressUntilRef.current - Date.now()));
            return () => {
                if (voiceRelayRestartTimerRef.current) {
                    clearTimeout(voiceRelayRestartTimerRef.current);
                    voiceRelayRestartTimerRef.current = null;
                }
            };
        }

        if (connectionState === 'connected' && hasRemoteAudio && !voiceRelayRecording && !voiceRelayBusy) {
            voiceRelayRestartTimerRef.current = setTimeout(() => {
                void startVoiceRelaySegment();
            }, 350);
        }

        return () => {
            if (voiceRelayRestartTimerRef.current) {
                clearTimeout(voiceRelayRestartTimerRef.current);
                voiceRelayRestartTimerRef.current = null;
            }
        };
    }, [connectionState, hasRemoteAudio, startVoiceRelaySegment, stopVoiceRelaySegment, voiceRelayBusy, voiceRelayEnabled, voiceRelayRecording]);

    useEffect(() => {
        void loadAuditEvents();
    }, [loadAuditEvents]);

    // Call duration timer
    useEffect(() => {
        if (connectionState !== 'connected' || !hasRemoteAudio) return;

        const interval = setInterval(() => {
            setCallDuration((prev) => prev + 1);
        }, 1000);

        return () => clearInterval(interval);
    }, [connectionState, hasRemoteAudio]);

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
    }, [voipClient, error]);

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
            console.log('[VoIPScreen] Playing wingback tone...');
            toneService.playwingbackTone();
        } else {
            // In-call screen for callee should stay silent while waiting for media path.
            toneService.stopAll();
        }

        return () => {
            // Don't stop tone on unmount - let it play until explicit stop
        };
    }, [callInitResponse.participant_role, connectionState, hasRemoteAudio]);

    const handleMuteToggle = useCallback(() => {
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

        const finalAuditEvents = await loadAuditEvents();
        onHangup(finalAuditEvents);
    }, [voipClient, callDuration, connectionState, callInitResponse, apiBaseUrl, authToken, onHangup, loadAuditEvents, stopVoiceRelayPlayback, stopVoiceRelaySegment]);

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
    const chatSection = (
        <View style={[styles.chatSection, { paddingBottom: sectionPaddingBottom }]}>
            <View style={styles.chatHeaderRow}>
                <Text style={styles.chatTitle}>실시간 채팅</Text>
                <Text style={styles.chatHint}>통화 중 짧은 텍스트를 바로 주고받을 수 있습니다.</Text>
            </View>
            <View style={[styles.chatCard, { maxHeight: chatCardMaxHeight }]}>
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
                    }) : (
                        <Text style={styles.chatEmptyText}>아직 채팅이 없습니다. 통화 중 필요한 문장을 바로 보내보세요.</Text>
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

                    {isCompactHeight ? chatSection : null}

                    <View style={[styles.auditSection, { paddingBottom: sectionPaddingBottom }]}>
                        <View style={styles.auditHeaderRow}>
                            <Text style={styles.auditTitle}>통화 모드 감사 로그</Text>
                            <TouchableOpacity style={styles.auditRefreshButton} onPress={() => { void loadAuditEvents(); }}>
                                <Text style={styles.auditRefreshButtonText}>{auditLoading ? '갱신 중...' : '새로고침'}</Text>
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
                                <Text style={styles.auditEmptyText}>{auditLoading ? '감사 로그를 불러오는 중입니다.' : '아직 감사 로그가 없습니다.'}</Text>
                            )}
                        </View>
                    </View>

                    <View style={[styles.voiceRelaySection, { paddingBottom: sectionPaddingBottom }]}>
                        {voiceRelaySuggestionVisible ? (
                            <View style={styles.voiceRelaySuggestionCard}>
                                <Text style={styles.voiceRelaySuggestionTitle}>실시간 음성 통역을 켤까요?</Text>
                                <Text style={styles.voiceRelaySuggestionBody}>통화가 연결됐습니다. 지금 켜면 다음 음성 구간부터 자동으로 3초 단위 통역을 이어갑니다.</Text>
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
                                <Text style={styles.voiceRelayHint}>{voiceRelayServerReady ? '자동 통역 모드에서는 통화 연결 후 음성 경로가 열리면 바로 통역을 시작합니다.' : '기본값은 수동 시작이며, 통화 연결 후 1회만 켜기 제안을 표시합니다.'}</Text>
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
                                        ? '지금 음성을 듣고 있습니다.'
                                        : voiceRelayBusy
                                            ? '통역 및 전송 중입니다.'
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
                                <Text style={styles.voiceRelayEmptyText}>통역된 음성이 아직 없습니다. 시작을 누른 뒤 최근 3개 구간만 여기에 표시됩니다.</Text>
                            )}
                        </View>
                    </View>

                    {!isCompactHeight ? chatSection : null}

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
