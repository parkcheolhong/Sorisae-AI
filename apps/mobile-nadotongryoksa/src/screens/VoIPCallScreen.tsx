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
import {
    enableVoipAudio,
    disableVoipAudio,
    setVoipSpeakerphone,
    isVoipTtsPlayerNativeAvailable,
    playVoiceCallTts,
    stopVoiceCallTts,
} from '../native/voipAudio';
import { translateText, voiceTranslate, synthesizeSpeech } from '../api/translate';
import { FEATURE_IDS, newCorrelationId, deterministicCorrelationId } from '../features/correlation/correlationId';
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
    relayTextsSimilar,
    shouldRejectRemoteVoiceRelayPlayback,
    updateVoiceRelaySegmentSpeechState,
    VOICE_RELAY_MAX_SPEAK_CHARS,
    VOICE_RELAY_VAD_DEFAULTS,
    resolveVoiceRelayFixedFlushDelayMs,
    type VoiceRelaySegmentState,
} from '../features/voip-voice-relay/voiceRelayOrchestrator';
import {
    applyLocalRelayTurn,
    applyRemoteRelayTurn,
    buildRemoteRelayDedupeKeys,
    createInitialVoiceRelayTurnSnapshot,
    estimateVoiceRelayPlaybackMs,
    isVoiceRelayListenActive,
    markRemotePlaybackDrained,
    markRemotePlaybackFinished,
    shouldDedupeRemoteVoiceRelay,
    shouldDeferVoiceRelayFlush,
    shouldPlayRemoteVoiceRelay,
    shouldSendVoiceRelaySegment,
    shouldStartVoiceRelayCapture,
    type RemoteRelayDedupeRecord,
    type VoiceRelayTurnSnapshot,
} from '../features/voip-voice-relay/voiceRelayTurnController';
import {
    DESIGNATED_LANGUAGE_MISMATCH_MESSAGE,
    textMatchesDesignatedLanguage,
} from '../features/translation/designatedLanguage';
import {
    shouldSkipSilentVoiceRelayStt,
} from '../features/voip-voice-relay/voiceRelayAudioMetrics';
import {
    beginVoiceRelaySileroCapture,
    endVoiceRelaySileroCapture,
    isVoiceRelaySileroCaptureAvailable,
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
import {
    getWorldlincoTuning,
    resolveSileroBoundaryFromTuning,
} from '../services/worldlincoTuningConfig';
import type { VoiceRelayChunkMeta, VoiceRelayPlaybackItem } from '../features/voip-voice-relay/types';
import { VoiceRelayPlaybackQueue } from '../features/voip-voice-relay/voiceRelayPlaybackQueue';

// 재생 종료 후 마이크 재무장까지의 에코 꼬리(실측 종료 시점 기준). 시작 시점에 추정으로
// 박아둔 억제창과 무관하게, 실제 재생이 끝나는 순간을 기준으로만 적용해
// "발화 끝 ↔ 마이크 열림" 타이밍을 정확히 일치시킨다.
//  - 네이티브(HW AEC, USAGE_VOICE_COMMUNICATION): 스피커 출력이 마이크 참조 루프에서
//    상쇄되므로 짧게(턴 컨트롤러 postPlaybackGuardMs=550 이 사실상의 가드).
//  - expo/디바이스 폴백(AEC 미정합): TTS 꼬리가 스피커→마이크로 샐 수 있어 보수적 꼬리 유지.
const VOICE_RELAY_NATIVE_ECHO_TAIL_MS = 250;
const VOICE_RELAY_FALLBACK_ECHO_TAIL_MS = 700;

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

// 연속 캡처 큐 파이프라이닝용 세그먼트 스냅샷.
// 캡처(녹음)와 처리(STT/번역/딜리버리)를 분리하면, 큐 워커가 세그먼트를 처리하는 사이
// 캡처 루프가 다음 세그먼트로 공유 ref 들을 덮어쓴다. 따라서 한 세그먼트의 판정/메타데이터는
// flush 시점에 여기로 고정(snapshot)해 워커로 전달한다(스테일 ref 방지).
type VoiceRelaySegmentSnapshot = {
    segmentDurationMs: number;
    meterUnavailable: boolean;
    flushReason: string | null;
    flushHadSpeech: boolean;
    peakMeterDb: number;
    hasSpeech: boolean;
    sileroActive: boolean;
    sileroHadSpeech: boolean;
    chunkMeta: { utteranceId: string; chunkIndex: number; isFinal: boolean };
};

const CALL_CONNECT_TIMEOUT_MS = 60_000;
const VOICE_RELAY_DUPLICATE_GUARD_MS = 12_000;
const VOICE_RELAY_SUPPRESS_MIN_MS = 900;
const VOICE_RELAY_SUPPRESS_CHAR_MS = 45;
const getVoiceRelayEchoGuards = () => {
    const tuning = getWorldlincoTuning().voip;
    return {
        remote: tuning.remote_echo_guard_ms,
        speaker: tuning.speaker_echo_guard_ms,
    };
};
const VOICE_RELAY_SPEECH_METER_MIN_DB = -48;
const VOICE_RELAY_MIN_AUDIO_BASE64_LEN = 3_500;
const VOICE_RELAY_RESTART_DELAY_MS = 220;
const VOICE_RELAY_PLAYBACK_SUPPRESS_MAX_MS = 4_500;
const VOICE_RELAY_METER_UNAVAILABLE_POLLS = 5;
const VOICE_RELAY_REMOTE_ECHO_DEDUPE_MS = 12_000;
const VOICE_RELAY_CONNECTED_GRACE_MS = 3_000;
const REMOTE_AUDIO_DETECT_WARN_MS = 45_000;
// 리드인 트리밍: Silero 가용 시 STT 녹음을 speech_start 까지 지연(arm)해 발화 전
// 무음이 업로드 파일에 들어가지 않게 한다. 이 시간 내 발화가 없으면 안전하게 즉시
// 녹음을 시작(레거시 fixed_flush/file-RMS 경로)해 기존 동작으로 폴백한다.
const VOICE_RELAY_LEADIN_ARM_TIMEOUT_MS = 9_000;

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
    // 번역 릴레이는 통역 음성을 또렷이 들어야 하므로 스피커를 기본 ON으로 둔다.
    // (이어피스는 음량이 작아 "음량이 너무 작다"는 문제가 발생) 사용자는 화면에서 수화기로 토글 가능.
    const [isSpeakerOn, setIsSpeakerOn] = useState<boolean>(true);
    const isSpeakerOnRef = useRef<boolean>(true);
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
    const voiceRelayNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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
    // G10(A-1): TTS 를 통화 렌더 경로(네이티브 AudioTrack/USAGE_VOICE_COMMUNICATION)로 재생해
    // HW AEC 참조 루프에 합류시킨다. 기본 on, 네이티브 미가용/실패 시 expo-av 폴백(무회귀).
    const voiceCallTtsNativeEnabledRef = useRef<boolean>(true);
    // 네이티브 통화-렌더 TTS 재생 중 표시(expo Sound ref 는 null 이므로 별도 추적해 억제 유지).
    const voiceRelayNativeTtsActiveRef = useRef<boolean>(false);
    const voiceRelayStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayRestartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayProcessingRef = useRef<boolean>(false);
    // 연속 캡처 큐(파이프라이닝): 한 세그먼트를 STT/번역/렌더하는 동안에도 마이크를 다시 열어
    // 다음 발화를 잃지 않도록, 녹음이 끝난 세그먼트는 이 FIFO 큐에 적재하고 별도 워커가 순차
    // 처리한다. 캡처(녹음)와 처리(서빙/딜리버리)를 분리해 "렌더 중 음성 잘림 + 템 김"을 없앤다.
    const voiceRelaySegmentQueueRef = useRef<{ uri: string; snapshot: VoiceRelaySegmentSnapshot }[]>([]);
    const voiceRelayQueueWorkerActiveRef = useRef<boolean>(false);
    const voiceRelayEnabledRef = useRef<boolean>(false);
    const voiceRelaySuggestionShownRef = useRef<boolean>(false);
    const voiceRelayAutoStartedRef = useRef<boolean>(false);
    const voiceRelaySuppressUntilRef = useRef<number>(0);
    // Layer 1(에코 뿌리 차단): 상대 TTS가 실제로 재생 중인 동안 true. 추정 재생창(estimate)이 아니라
    // 실제 onDone/onStopped/onError 까지 마이크 재무장을 보류해 ① 장문 TTS 끊김(B)과
    // ② 내 마이크가 상대 TTS를 주워 한글로 음차하는 에코(A)를 동시에 차단한다.
    const voiceRelayTtsActiveRef = useRef<boolean>(false);
    const lastVoiceRelayKeyRef = useRef<string>('');
    const lastVoiceRelayAtRef = useRef<number>(0);
    const lastRemoteRelayTranscriptRef = useRef<string>('');
    const lastRemoteRelayAtRef = useRef<number>(0);
    // 상대(피어)가 실제로 보내온 릴레이의 source_lang을 기억한다. 지정 언어 모드에서 피어의
    // source_lang은 피어의 고정 지정 언어이므로 신뢰할 수 있다. 콜리(callee)가 콜러의 언어를
    // 시그널링으로 전달받지 못해 localTargetLang이 잘못된 기본값(예: en)으로 떨어질 때, 수신한
    // 릴레이에서 상대 언어를 학습해 내 번역 타깃을 보정한다(자가 치유).
    const observedRemoteRelaySourceLangRef = useRef<string>('');
    const lastRemotePlaybackKeyRef = useRef<string>('');
    const lastRemotePlaybackAtRef = useRef<number>(0);
    const lastRemoteRelayDedupeRef = useRef<RemoteRelayDedupeRecord | null>(null);
    const voiceRelayPeakMeteringRef = useRef<number>(-160);
    const connectedAtRef = useRef<number | null>(null);
    const voiceRelayMeterPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const voiceRelayFixedFlushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayMeterPollMissesRef = useRef<number>(0);
    const voiceRelayMeterUnavailableRef = useRef<boolean>(false);
    const voiceRelayFileRmsPollTickRef = useRef<number>(0);
    // 파일 증가율(bytes/sec) 기반 발화 활동 판정 — meter-dead 기기에서 무음(말 끝)을 추정한다.
    // (AAC 바이트 RMS는 음량과 무관해 무음에도 speech로 오판 → 반복 환각 유발. 증가율로 대체)
    const voiceRelayPrevFileSizeRef = useRef<number>(0);
    const voiceRelayPrevFilePollMsRef = useRef<number>(0);
    const voiceRelayPeakGrowthBpsRef = useRef<number>(0);
    const voiceRelayGrowthSpeechActiveRef = useRef<boolean>(false);
    const voiceRelaySileroActiveRef = useRef<boolean>(false);
    const voiceRelaySileroSupportedRef = useRef<boolean>(false);
    const voiceRelaySileroFirstSpeechAtMsRef = useRef<number | null>(null);
    // 마이크 컨텐션 해소: Silero 네이티브 AudioRecord 의 PCM 을 세그먼트 WAV 로 직접 캡처한다.
    // (삼성 MultiRecord 차단으로 expo-audio 레코더가 무음만 받던 문제 해결)
    const voiceRelayNativeCaptureActiveRef = useRef<boolean>(false);
    const voiceRelayNativeCaptureUriRef = useRef<string | null>(null);
    // 리드인 트리밍 상태: armed=발화 대기 중(녹음 미시작), bypassArm=speech_start/타임아웃에
    // 의한 즉시 녹음 재진입(게이팅·arm 재실행 생략).
    const voiceRelayArmedForSpeechRef = useRef<boolean>(false);
    const voiceRelayArmedAtMsRef = useRef<number>(0);
    const voiceRelayArmTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const voiceRelayBypassArmRef = useRef<boolean>(false);
    // speech_start 로 인한 재진입(실발화 트리거)과 arm 타임아웃 재진입(무음 폴백)을 구분한다.
    const voiceRelayLeadInTriggeredRef = useRef<boolean>(false);
    const voiceRelaySileroLastFlushAtMsRef = useRef<number | null>(null);
    const voiceRelayLastFlushReasonRef = useRef<string | null>(null);
    const voiceRelayLastFlushHadSpeechRef = useRef<boolean>(false);
    const voiceRelayLastSegmentDurationMsRef = useRef<number>(0);
    const voiceRelayTurnRef = useRef<VoiceRelayTurnSnapshot>(createInitialVoiceRelayTurnSnapshot());
    const voiceRelayAbortGenerationRef = useRef<number>(0);
    const scheduleVoiceRelayCaptureRetryRef = useRef<(retryReason: string) => void>(() => {});
    // 반이중 하드 가드: 상대 재생이 도착하면 로컬 녹음을 stop 하는데, 그 teardown(stopAndUnloadAsync)
    // 완료 promise 를 보관한다. 재생(playVoiceRelayOutput)은 이 promise 를 await 한 뒤에만 시작해,
    // 녹음 미해제 상태로 AudioTrack 이 통화 입력 스트림과 충돌해 무음으로 죽는 레이스를 차단한다.
    const voiceRelaySegmentStopInFlightRef = useRef<Promise<unknown> | null>(null);
    const stopVoiceRelaySegmentRef = useRef<(processSegment: boolean) => Promise<void>>(async () => {});
    const lastLocalRelayTranslatedRef = useRef<string>('');
    // 발신측이 직접 인식한 "원문 전사"(자기 언어). 라운드트립 에코(상대 폰이 내 TTS 를
    // 다시 잡아 재번역해 되돌려보낸 것)를 잡으려면, 들어온 번역문을 내 번역문이 아니라
    // 내 원문 전사와 같은 언어로 비교해야 한다.
    const lastLocalRelayTranscriptRef = useRef<string>('');
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
    // 일부 기기(예: 특정 Galaxy)에서 WebRTC ontrack/onRemoteStream 콜백이 누락되면, 늦게 도착한
    // 원격 오디오 트랙이 한 번도 mute 되지 않아 원음(WebRTC)+번역 TTS 가 겹쳐 재생된다(이중 발화).
    // syncRemoteAudioState 폴링이 트랙을 감지하면 ref 동일성 가드를 우회해 client mute 를 강제
    // 재적용하는데, 그 1회성 재적용을 로그로 남기기 위한 플래그.
    const remoteTrackForceSuppressedRef = useRef<boolean>(false);
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
        // ontrack/onRemoteStream 콜백 누락 보정: 통역 모드에서 원격 트랙이 폴링으로 감지되면,
        // setRemoteAudioSuppressed 의 ref 동일성 가드(이미 true 면 client 호출 생략) 때문에
        // 늦게 도착한 트랙이 mute 되지 못하는 누수가 있다. 여기서 client mute 를 직접·강제
        // 재적용해 원음 누수를 막는다. 통역 모드는 원음을 끝까지 차단하므로(release 무시)
        // 멱등 재적용이며 정상 통화엔 무해하다. (대면 경로 무접촉 · VOIP 수신 억제 국한)
        if (detected && voiceRelayEnabledRef.current) {
            remoteAudioSuppressedRef.current = true;
            activeClient?.setRemoteAudioEnabled?.(false);
            if (!remoteTrackForceSuppressedRef.current) {
                remoteTrackForceSuppressedRef.current = true;
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_REMOTE_AUDIO_SUPPRESSION',
                    call_id: callIdRef.current,
                    suppressed: true,
                    forced: true,
                    source: 'sync_detected_track',
                    timestamp: new Date().toISOString(),
                }));
            }
        }
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

    const resolveTtsLanguage = useCallback((langCode: string, text?: string) => {
        return resolveVoipTtsLocale(langCode, text);
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
        if (voiceRelayArmTimeoutRef.current) {
            clearTimeout(voiceRelayArmTimeoutRef.current);
            voiceRelayArmTimeoutRef.current = null;
        }
        voiceRelayArmedForSpeechRef.current = false;
        if (voiceRelayMeterPollRef.current) {
            clearInterval(voiceRelayMeterPollRef.current);
            voiceRelayMeterPollRef.current = null;
        }
        if (voiceRelayFixedFlushTimerRef.current) {
            clearTimeout(voiceRelayFixedFlushTimerRef.current);
            voiceRelayFixedFlushTimerRef.current = null;
        }
        if (voiceRelayNoticeTimerRef.current) {
            clearTimeout(voiceRelayNoticeTimerRef.current);
            voiceRelayNoticeTimerRef.current = null;
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
            const sileroBoundary = resolveSileroBoundaryFromTuning();
            const started = await startVoiceRelaySileroVadMonitor(
                sileroBoundary.silenceMs,
                sileroBoundary.speechMs,
            );
            if (!started) {
                return;
            }
            voiceRelaySileroActiveRef.current = true;
            setVoiceRelaySileroActive(true);
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SILERO_STARTED',
                call_id: callInitResponse.call_id,
                silence_ms: sileroBoundary.silenceMs,
                speech_ms: sileroBoundary.speechMs,
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
        // G10(A-1): 네이티브 통화-렌더 TTS 가 진행 중이면 함께 중단(다음 발화/종료 전 정리).
        if (voiceRelayNativeTtsActiveRef.current) {
            voiceRelayNativeTtsActiveRef.current = false;
            await stopVoiceCallTts();
        }
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
        // 통역 모드에서는 WebRTC 원어를 끝까지 차단 (serverReady 플래그와 무관).
        if (voiceRelayEnabledRef.current) {
            return;
        }
        setRemoteAudioSuppressed(false);
    }, [setRemoteAudioSuppressed]);

    const finishRemoteVoiceRelayPlayback = useCallback(() => {
        // 재생 큐가 모두 비었으면(이 발화가 마지막) listen hold 를 짧은 에코 가드까지 당겨
        // 듣기만 하던 쪽이 즉시 턴을 잡도록 한다(한쪽 일방 구동/다른 쪽 반복 루프 해소).
        // 큐에 후속 재생이 남아 있으면 기존 동작(remotePlaybackUntilMs 만 클램프)을 유지한다.
        const queueDrained = (voiceRelayPlaybackQueueRef.current?.pendingCount ?? 0) === 0;
        voiceRelayTurnRef.current = queueDrained
            ? markRemotePlaybackDrained(voiceRelayTurnRef.current)
            : markRemotePlaybackFinished(voiceRelayTurnRef.current);
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

    const playVoiceRelayOutput = useCallback(async (audioUrl: string | undefined, audioBase64: string | undefined, audioFormat: string | undefined, translatedText: string, targetLang: string, correlationId?: string) => {
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

        // 반이중 하드 가드: 진행 중이던 로컬 녹음의 teardown(stopAndUnloadAsync)이 완료될 때까지
        // 재생을 시작하지 않는다. (마이크 동시 오픈 시 수신 핸들러의 stop 과 재생 시작이 레이스 →
        // AudioRecord 가 통화 입력 스트림을 쥔 채 AudioTrack 출력이 충돌해 재생이 무음으로 죽는 문제 차단.)
        const pendingSegmentStop = voiceRelaySegmentStopInFlightRef.current;
        if (pendingSegmentStop) {
            voiceRelaySegmentStopInFlightRef.current = null;
            try {
                await pendingSegmentStop;
            } catch {
                // stop 실패는 무시 — 아래에서 잔존 녹음을 한 번 더 해제 시도한다.
            }
        }
        // 그래도 녹음이 남아 있으면(예: 핸들러 경로 외 진입) 직접 해제 후 재생.
        if (voiceRelayRecordingRef.current) {
            try {
                await stopVoiceRelaySegmentRef.current(false);
            } catch {
                // ignore
            }
        }

        // 원어(WebRTC) 즉시 차단 — TTS 전에 스피커로 상대 음성이 새는 것 방지
        setRemoteAudioSuppressed(true);
        await stopVoiceRelayPlayback();
        Speech.stop();
        lastRemotePlaybackTranslatedRef.current = normalizeRelayText(translatedText);
        lastRemotePlaybackTranslatedAtRef.current = Date.now();

        console.log('[UI_PRESS_PROBE]', JSON.stringify({
            event: 'VOIP_VOICE_RELAY_PLAYBACK',
            call_id: callInitResponse.call_id,
            correlation_id: correlationId || null,
            target_lang: targetLang,
            translated_text: normalizedText.slice(0, 120),
            translated_length: normalizedText.length,
            tts_delivery: 'pending',
            speaker_on: isSpeakerOnRef.current,
            timestamp: new Date().toISOString(),
        }));

        try {
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: true,
                // 통역 통화는 탁자에 둔 폰을 가정 → 항상 라우드스피커. (이어피스 라우팅 금지)
                playThroughEarpieceAndroid: false,
                staysActiveInBackground: false,
            });
            // 근거(하드 증거): 통화 중 AudioManager 가 MODE_IN_COMMUNICATION↔NORMAL 로 깜빡이고,
            // MODE_IN_COMMUNICATION 의 출력 경로가 '이어피스'라서, 그 구간에 USAGE_MEDIA(TTS)까지
            // 이어피스로 빠져 탁자 위 폰에선 무음이 된다. 재생 직전 라우드스피커를 강제(speaker=true)하고
            // 통화 스트림 음량을 최대화해, 어느 모드에서든 TTS 가 내장 스피커로 또렷이 나오게 한다.
            await setVoipSpeakerphone(true);
            await enableVoipAudio(true, true);
        } catch {
            // ignore audio mode failures before device TTS
        }
        setRemoteAudioSuppressed(true);

        // Layer 1: 실제 TTS 재생 동안 마이크 재무장을 막는다. 추정 재생창과 무관하게
        // 재생 완료에서만 해제해, 장문 TTS가 끝까지 재생되고(B 끊김 해소)
        // 그 사이 마이크가 상대 TTS를 주워 음차하는 에코(A)도 차단한다.
        voiceRelayTtsActiveRef.current = true;
        let ttsSettled = false;
        // 네이티브(HW AEC) 통화-렌더로 실제 재생됐는지 — settleOnce 의 에코 꼬리 결정에 쓴다.
        let nativeRenderDelivered = false;
        // 실제 재생은 길이에 비례하므로 추정 상한이 아니라 넉넉한 실측 기반 failsafe(최대 20s)로만 보호한다.
        // (콜백 누락 시에도 마이크 재무장이 영구 차단되지 않게 한다.)
        const ttsFailsafeMs = Math.min(20_000, Math.max(4_000, normalizedText.length * 120));
        const settleOnce = () => {
            if (ttsSettled) {
                return;
            }
            ttsSettled = true;
            voiceRelayTtsActiveRef.current = false;
            // 정밀 재무장: 시작 시점에 추정(playbackMs+700)으로 박아둔 억제창을, '실제 재생 종료'
            // 시점 기준 짧은 에코 꼬리로 collapse 한다. 추정이 실제보다 길면 마이크가 최대 수초
            // 늦게 열리던 타이밍 불일치(발화 끝 ↔ 마이크 열림)를 제거해, 재무장이 발화 종료와
            // 일치하게 한다. (turn 컨트롤러는 markRemotePlaybackDrained 로 이미 실측 collapse됨.)
            voiceRelaySuppressUntilRef.current = Date.now() + (
                nativeRenderDelivered
                    ? VOICE_RELAY_NATIVE_ECHO_TAIL_MS
                    : VOICE_RELAY_FALLBACK_ECHO_TAIL_MS
            );
            finishRemoteVoiceRelayPlayback();
            scheduleVoiceRelayCaptureRetryRef.current('playback_complete');
        };

        // 우선순위 1: 서버 뉴럴 TTS(Edge neural). 단말 음성팩 의존을 제거해 50개국 일관 발음·
        // 자연스러운 톤을 확보한다(로봇 음성·한글 음차 문제 해결). 릴레이로 이미 오디오가 왔으면
        // 그걸 쓰고, 없으면 수신측이 대상 언어로 직접 합성 요청한다. 실패 시 디바이스 TTS로 폴백(무회귀).
        let serverAudioBase64: string | undefined;
        let serverAudioFormat: string | undefined;
        if (audioBase64 && String(audioFormat || '').startsWith('audio/')) {
            serverAudioBase64 = audioBase64;
            serverAudioFormat = audioFormat;
        } else {
            try {
                // V.2 ID 백본 — 발화 단계가 출처 상관 ID에 스스로 붙도록 전달.
                const synth = await synthesizeSpeech(
                    normalizedText,
                    targetLang,
                    apiBaseUrlRef.current,
                    undefined,
                    { correlationId, featureId: FEATURE_IDS.voipVoiceRelay },
                );
                if (synth?.audioBase64 && String(synth.audioFormat || '').startsWith('audio/')) {
                    serverAudioBase64 = synth.audioBase64;
                    serverAudioFormat = synth.audioFormat;
                }
            } catch {
                // 합성 실패 → 디바이스 TTS 폴백
            }
        }

        let playedServerAudio = false;
        if (serverAudioBase64) {
            const ext = resolvePlaybackExtension(serverAudioFormat);
            const fileUri = `${FileSystem.cacheDirectory}voice_relay_out_${Date.now()}.${ext}`;
            try {
                await FileSystem.writeAsStringAsync(fileUri, serverAudioBase64, {
                    encoding: FileSystem.EncodingType.Base64,
                });
                voiceRelayPlaybackFileRef.current = fileUri;
            } catch {
                voiceRelayPlaybackFileRef.current = null;
            }

            // G10(A-1) 우선 경로: 통화 렌더(네이티브 AudioTrack/USAGE_VOICE_COMMUNICATION)로 재생해
            // HW AEC 참조 루프에 합류 → 마이크가 자기 TTS 를 재캡처하지 못하게 한다(굶김/자가에코 차단).
            if (
                voiceRelayPlaybackFileRef.current
                && voiceCallTtsNativeEnabledRef.current
                && isVoipTtsPlayerNativeAvailable()
            ) {
                voiceRelayNativeTtsActiveRef.current = true;
                try {
                    const nativePath = (voiceRelayPlaybackFileRef.current as string).replace(/^file:\/\//, '');
                    const nativePlayed = await playVoiceCallTts(nativePath);
                    voiceRelayNativeTtsActiveRef.current = false;
                    if (nativePlayed) {
                        playedServerAudio = true;
                        nativeRenderDelivered = true;
                        if (voiceRelayPlaybackFileRef.current) {
                            try {
                                await FileSystem.deleteAsync(voiceRelayPlaybackFileRef.current, { idempotent: true });
                            } catch {
                                // ignore temp cleanup failures
                            }
                            voiceRelayPlaybackFileRef.current = null;
                        }
                        console.log('[UI_PRESS_PROBE]', JSON.stringify({
                            event: 'VOIP_VOICE_RELAY_PLAYBACK_DELIVERED',
                            call_id: callInitResponse.call_id,
                            correlation_id: correlationId || null,
                            target_lang: targetLang,
                            tts_delivery: 'server_audio_voicecall_native',
                            timestamp: new Date().toISOString(),
                        }));
                    }
                } catch {
                    voiceRelayNativeTtsActiveRef.current = false;
                }
            }

            // 폴백: 네이티브 통화-렌더 미가용/실패 시 기존 expo-av 경로(USAGE_MEDIA, 무회귀).
            if (!playedServerAudio && voiceRelayPlaybackFileRef.current) {
                try {
                    const { sound } = await Audio.Sound.createAsync(
                        { uri: voiceRelayPlaybackFileRef.current },
                        { shouldPlay: true, volume: 1.0 },
                    );
                    voiceRelayPlaybackRef.current = sound;
                    await new Promise<void>((resolve) => {
                        const failsafe = setTimeout(resolve, ttsFailsafeMs);
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
                    await stopVoiceRelayPlayback();
                    playedServerAudio = true;
                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                        event: 'VOIP_VOICE_RELAY_PLAYBACK_DELIVERED',
                        call_id: callInitResponse.call_id,
                        correlation_id: correlationId || null,
                        target_lang: targetLang,
                        tts_delivery: 'server_audio',
                        timestamp: new Date().toISOString(),
                    }));
                } catch {
                    await stopVoiceRelayPlayback();
                    playedServerAudio = false;
                }
            }
        }

        // 우선순위 2: 디바이스 TTS 폴백 (서버 합성 불가/실패 시 기존 동작 유지)
        if (!playedServerAudio) {
            await new Promise<void>((resolve) => {
                const failsafe = setTimeout(resolve, ttsFailsafeMs);
                const done = () => {
                    clearTimeout(failsafe);
                    resolve();
                };
                Speech.speak(normalizedText, {
                    language: resolveTtsLanguage(targetLang, normalizedText),
                    rate: 1.05,
                    pitch: 1.0,
                    volume: 1.0,
                    onDone: done,
                    onStopped: done,
                    onError: done,
                });
            });
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_PLAYBACK_DELIVERED',
                call_id: callInitResponse.call_id,
                target_lang: targetLang,
                tts_delivery: 'device_speech',
                timestamp: new Date().toISOString(),
            }));
        }

        settleOnce();
    }, [callInitResponse.call_id, finishRemoteVoiceRelayPlayback, resolvePlaybackExtension, resolveTtsLanguage, setRemoteAudioSuppressed, stopVoiceRelayPlayback]);

    const enqueueVoiceRelayPlayback = useCallback((item: VoiceRelayPlaybackItem) => {
        if (!voiceRelayPlaybackQueueRef.current) {
            voiceRelayPlaybackQueueRef.current = new VoiceRelayPlaybackQueue(async (queued) => {
                await playVoiceRelayOutput(
                    queued.audioUrl,
                    queued.audioBase64,
                    queued.audioFormat,
                    queued.translatedText,
                    queued.targetLang,
                    queued.correlationId,
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

    // 지정 언어 안내는 막히는 팝업이 아니라 잠깐 떴다 스스로 사라지는 안내로만 노출한다.
    // (다시 지정 언어로 말하면 다음 세그먼트가 정상 처리되며 안내도 갱신/해제된다.)
    const flashVoiceRelayNotice = useCallback((message: string, durationMs = 3200) => {
        setVoiceRelayError(message);
        if (voiceRelayNoticeTimerRef.current) {
            clearTimeout(voiceRelayNoticeTimerRef.current);
        }
        voiceRelayNoticeTimerRef.current = setTimeout(() => {
            voiceRelayNoticeTimerRef.current = null;
            setVoiceRelayError((cur) => (cur === message ? null : cur));
        }, durationMs);
    }, []);

    const processVoiceRelaySegment = useCallback(async (uri: string, snapshot: VoiceRelaySegmentSnapshot) => {
        const segmentStartedAt = Date.now();
        const abortGeneration = voiceRelayAbortGenerationRef.current;
        // V.2 ID 백본 — 이 캡처 세그먼트의 고유 상관 ID를 1회 발급해
        // 기능 ID 자동 매핑(STT) → 셀프 서빙(번역) → 전송(딜리버리, 릴레이) → 음성 발화까지
        // 동일 ID로 자동 연결한다.
        const segmentCorrelationId = newCorrelationId(FEATURE_IDS.voipVoiceRelay);

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
                    segment_duration_ms: snapshot.segmentDurationMs,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            if (snapshot.segmentDurationMs < VOICE_RELAY_VAD_DEFAULTS.minSegmentMs - 400) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'segment_duration_too_short',
                    segment_duration_ms: snapshot.segmentDurationMs,
                    min_segment_ms: VOICE_RELAY_VAD_DEFAULTS.minSegmentMs,
                    flush_reason: snapshot.flushReason,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            const meterUnavailable = snapshot.meterUnavailable;
            const flushReason = snapshot.flushReason;
            const flushHadSpeech = snapshot.flushHadSpeech;
            const silentSkip = shouldSkipSilentVoiceRelayStt({
                peakMeterDb: snapshot.peakMeterDb,
                hasSpeech: snapshot.hasSpeech,
                meterUnavailable,
                audioBase64: base64Audio,
            });
            if (silentSkip.skip) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: silentSkip.reason || 'silent_segment',
                    peak_meter_db: snapshot.peakMeterDb,
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
                peakMeterDb: snapshot.peakMeterDb,
                hasRemoteAudio: hasRemoteAudioRef.current,
                remoteAudioSuppressed: remoteAudioSuppressedRef.current,
            });
            if (!sendDecision.allowed) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: sendDecision.reason || 'segment_send_blocked',
                    flush_reason: flushReason,
                    peak_meter_db: snapshot.peakMeterDb,
                    meter_unavailable: meterUnavailable,
                    silero_had_speech: snapshot.sileroHadSpeech,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            if (snapshot.sileroActive && !flushHadSpeech) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'silero_no_speech_detected',
                    flush_reason: flushReason,
                    segment_duration_ms: snapshot.segmentDurationMs,
                    timestamp: new Date().toISOString(),
                }));
                return;
            }

            voiceRelayProcessingRef.current = true;
            setVoiceRelayBusy(true);
            setVoiceRelayError(null);

            // 콜리가 시그널링으로 콜러 언어를 못 받아 localTargetLang이 잘못 떨어진 경우
            // (예: ko→en), 수신한 상대 릴레이에서 학습한 실제 상대 언어로 번역 타깃을 보정한다.
            const observedRemoteLang = observedRemoteRelaySourceLangRef.current.trim().toLowerCase();
            const effectiveTargetLang = observedRemoteLang && observedRemoteLang !== localSourceLang
                ? observedRemoteLang
                : localTargetLang;

            const probePayload = {
                event: 'VOIP_VOICE_TRANSLATE_REQUEST',
                call_id: callInitResponse.call_id,
                source_lang: localSourceLang,
                target_lang: effectiveTargetLang,
                region_hint: regionHint || null,
                audio_base64_length: base64Audio.length,
                timestamp: new Date().toISOString(),
            };
            const probeText = JSON.stringify(probePayload);
            console.log('[UI_PRESS_PROBE]', probeText);
            setLastTranslationProbe(probeText);

            const translateStartedAt = Date.now();
            // VoIP 통역 통화(designated, 언어 락): 이 기기 화자의 언어(localSourceLang)를 명시 전달해
            // STT를 해당 언어로 고정한다. 같은 방/스피커폰에서 상대 언어가 섞여 들어와도 내 지정 언어로만
            // 인식·중계하여 "양 언어가 모두 흡수되는" 혼선과 에코 루프를 막는다.
            const result = await voiceTranslate(
                base64Audio,
                localSourceLang,
                effectiveTargetLang,
                regionHint,
                localSourceLang,
                {
                    mode: 'designated',
                    correlationId: segmentCorrelationId,
                    featureId: FEATURE_IDS.voipVoiceRelay,
                    utteranceId: snapshot.chunkMeta.utteranceId,
                    // V.2 Session Core — 통화 단위 세션 키(call_id)로 언어쌍·맥락 누적.
                    // 서버는 COMM_V2_SESSION_CORE off면 무시(no-op).
                    sessionId: callInitResponse.call_id,
                },
            );
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
            // 지정 언어 락: 인식문이 내 지정 언어(localSourceLang) 스크립트와 맞지 않으면 거부한다.
            // (상대 언어/잡음이 섞여 들어온 경우 — 같은 방 스피커폰 교차픽업을 차단)
            if (!textMatchesDesignatedLanguage(transcript, localSourceLang)) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_SKIP',
                    call_id: callInitResponse.call_id,
                    reason: 'designated_language_mismatch',
                    designated_lang: localSourceLang,
                    detected_lang: detectedLang,
                    transcript,
                    timestamp: new Date().toISOString(),
                }));
                // 막히는 팝업 대신 잠깐 안내만 노출하고 듣기는 계속 유지한다.
                flashVoiceRelayNotice(DESIGNATED_LANGUAGE_MISMATCH_MESSAGE);
                return;
            }
            // 지정 언어 모드: 릴레이 방향은 항상 고정(내 언어 → 상대 언어).
            const relaySourceLang = localSourceLang;
            const relayTargetLang = effectiveTargetLang;
            const chunkMeta = snapshot.chunkMeta;
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
            // [V2 감정 E2] 서버가 동봉한 원문↔출력(TTS) 감정을 로그캣에 emit → 평가 하니스(eval/worldlinco)가
            // 감정 보존도(E2) 메트릭을 실데이터로 산출. 서버 COMM_V2_EMOTION_PROBE off면 result.emotion 없음 → 생략.
            if (
                result.emotion &&
                typeof result.emotion.src_arousal === 'number' &&
                typeof result.emotion.out_arousal === 'number'
            ) {
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_EMOTION_PROBE',
                    call_id: callInitResponse.call_id,
                    src_arousal: result.emotion.src_arousal,
                    src_valence: result.emotion.src_valence,
                    src_label: result.emotion.src_label ?? null,
                    out_arousal: result.emotion.out_arousal,
                    out_valence: result.emotion.out_valence,
                    out_label: result.emotion.out_label ?? null,
                    seq_id: seqId,
                    utterance_id: relayChunkMeta.utteranceId,
                    timestamp: new Date().toISOString(),
                }));
            }

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

            // G7: meter-dead(미터 −160dB) 시 RMS 기반 무음/에코 억제가 무력화되고, max_duration
            // flush로 직전 재생한 상대 TTS가 통째로 재캡처돼 designated(from 고정) STT를 거쳐
            // 되먹임(재번역→재전송)되는 누수가 있었다. 미터가 죽었을 때만, 캡처문/번역문이 직전
            // 재생한 상대 출력과 텍스트로 닮으면(타이밍 무관) 차단한다. 정상 신규 발화는 직전
            // 재생문과 닮지 않아 통과하므로 오차단 위험이 없다. (대면 경로 미접촉 · VOIP 국한)
            if (meterUnavailable && lastRemotePlaybackTranslatedRef.current) {
                const playedRemote = lastRemotePlaybackTranslatedRef.current;
                if (relayTextsSimilar(translatedText, playedRemote) || relayTextsSimilar(transcript, playedRemote)) {
                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                        event: 'VOIP_VOICE_RELAY_SKIP',
                        call_id: callInitResponse.call_id,
                        reason: 'meter_dead_remote_playback_echo',
                        transcript,
                        translated_text: translatedText,
                        recent_remote_playback: playedRemote.slice(0, 80),
                        timestamp: new Date().toISOString(),
                    }));
                    return;
                }
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

            // 서버가 echo 한 상관 ID를 우선 사용(STT/번역 로그와 동일 ID). 없으면 캡처 ID로 폴백.
            const relayCorrelationId = result.correlation_id || segmentCorrelationId;
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
                correlationId: relayCorrelationId,
            });

            if (sent) {
                setLastRelayDeliveryHint(`전달됨 · ${transcript.slice(0, 40)} → ${translatedText.slice(0, 40)}`);
                lastLocalRelayTranslatedRef.current = normalizeRelayText(translatedText);
                lastLocalRelayTranscriptRef.current = normalizeRelayText(transcript);
                lastLocalRelaySentAtRef.current = Date.now();
                voiceRelayTurnRef.current = applyLocalRelayTurn({
                    turn: voiceRelayTurnRef.current,
                    nowMs: Date.now(),
                    translatedText,
                });
                // 연속 캡처: utteranceId 회전/세그먼트 상태 리셋은 캡처 루프(flush)가 소유하므로
                // 큐 워커에서는 건드리지 않는다(진행 중인 다음 세그먼트 상태 훼손 방지).
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
        } catch (err) {
            const message = err instanceof Error ? err.message : '실시간 음성 통역 처리에 실패했습니다.';
            const isSilenceRejected = message.includes('음성이 감지되지 않았습니다');
            const isTooShort = message.includes('너무 짧습니다');
            const isDesignatedMismatch = message.includes('지정 언어와 다른 언어');
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: isSilenceRejected ? 'VOIP_VOICE_TRANSLATE_REJECTED' : 'VOIP_VOICE_TRANSLATE_FAILED',
                call_id: callInitResponse.call_id,
                error_message: message,
                timestamp: new Date().toISOString(),
            }));
            if (isTooShort) {
                setVoiceRelayError(`녹음 ${snapshot.segmentDurationMs}ms — 조금 더 길게 말해 주세요.`);
            } else if (isDesignatedMismatch) {
                // 막히는 팝업 대신 잠깐 안내만 노출하고 듣기는 계속 유지한다.
                flashVoiceRelayNotice(DESIGNATED_LANGUAGE_MISMATCH_MESSAGE);
            } else if (!isSilenceRejected) {
                setVoiceRelayError(message);
            }
        } finally {
            voiceRelayProcessingRef.current = false;
            // flush_reason 은 캡처 루프(flush)가 세그먼트마다 새로 설정/리셋하므로, 큐 워커에서는
            // null 로 덮어쓰지 않는다(진행 중인 다음 세그먼트의 flush_reason 훼손 방지).
            setVoiceRelayBusy(false);
            // 연속 캡처 큐: 재무장(re-arm)은 녹음 종료 직후 stopVoiceRelaySegment 에서 이미
            // 트리거하므로, 여기서는 캡처가 멈춰 있을 때만 안전망으로 재무장한다(중복 무해).
            if (voiceRelayEnabledRef.current
                && !voiceRelayRecordingRef.current
                && !voiceRelayArmedForSpeechRef.current
                && voiceRelaySegmentQueueRef.current.length === 0) {
                scheduleVoiceRelayCaptureRetry('segment_complete');
            }
            try {
                await FileSystem.deleteAsync(uri, { idempotent: true });
            } catch {
                // ignore temp cleanup failures
            }
        }
    }, [appendChatEntry, appendVoiceRelayEntry, callInitResponse.call_id, flashVoiceRelayNotice, localSourceLang, localTargetLang, nextVoiceRelaySeqId, participantRole, regionHint, scheduleVoiceRelayCaptureRetry]);

    // 연속 캡처 큐 워커: 적재된 세그먼트를 FIFO 로 하나씩 직렬 처리한다(순서/백엔드 부하 보호).
    // 캡처 루프와 독립적으로 동작하므로, 처리 중에도 다음 발화 녹음이 계속된다.
    const drainVoiceRelaySegmentQueue = useCallback(async () => {
        if (voiceRelayQueueWorkerActiveRef.current) {
            return;
        }
        voiceRelayQueueWorkerActiveRef.current = true;
        try {
            while (voiceRelaySegmentQueueRef.current.length > 0) {
                const item = voiceRelaySegmentQueueRef.current.shift();
                if (!item) {
                    continue;
                }
                try {
                    await processVoiceRelaySegment(item.uri, item.snapshot);
                } catch (err) {
                    console.warn('[VoIPScreen] voice relay queue worker error', err);
                }
            }
        } finally {
            voiceRelayQueueWorkerActiveRef.current = false;
        }
    }, [processVoiceRelaySegment]);

    const enqueueVoiceRelaySegment = useCallback((uri: string, snapshot: VoiceRelaySegmentSnapshot) => {
        voiceRelaySegmentQueueRef.current.push({ uri, snapshot });
        void drainVoiceRelaySegmentQueue();
    }, [drainVoiceRelaySegmentQueue]);

    const stopVoiceRelaySegment = useCallback(async (processSegment: boolean) => {
        clearVoiceRelayTimers();
        // 하드 스톱(처리 안 함=비활성/행업/턴 전환)에서는 미전송 버퍼 큐를 비운다.
        if (!processSegment) {
            voiceRelaySegmentQueueRef.current = [];
        }
        await stopVoiceRelaySileroMonitor(processSegment ? 'segment_flush' : 'segment_stop');

        const recording = voiceRelayRecordingRef.current;
        voiceRelayRecordingRef.current = null;
        setVoiceRelayRecording(false);
        if (!recording) {
            return;
        }

        const nativeCaptureActive = voiceRelayNativeCaptureActiveRef.current;
        const nativeCaptureUri = voiceRelayNativeCaptureUriRef.current;
        voiceRelayNativeCaptureActiveRef.current = false;
        voiceRelayNativeCaptureUriRef.current = null;

        try {
            await recording.stopAndUnloadAsync();
            const m4aUri = recording.getURI();
            if (voiceRelayRecordingRemoteSuppressedRef.current) {
                voiceRelayRecordingRemoteSuppressedRef.current = false;
                if (!voiceRelayPlaybackRef.current && !voiceRelayNativeTtsActiveRef.current) {
                    releaseRemoteAudioSuppressionIfAllowed();
                }
            }

            // Silero PCM 캡처가 활성이면, 무음 m4a 대신 네이티브가 export 한 WAV 를 업로드한다.
            let uploadUri = m4aUri;
            if (nativeCaptureActive && nativeCaptureUri) {
                const nativePath = nativeCaptureUri.replace(/^file:\/\//, '');
                const capture = await endVoiceRelaySileroCapture(nativePath);
                if (capture && capture.byteCount > 0) {
                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                        event: 'VOIP_VOICE_RELAY_NATIVE_CAPTURE',
                        call_id: callInitResponse.call_id,
                        byte_count: capture.byteCount,
                        duration_ms: Math.round(capture.durationMs),
                        peak_db: Math.round(capture.peakDb),
                        rms_db: Math.round(capture.rmsDb),
                        process_segment: processSegment,
                        timestamp: new Date().toISOString(),
                    }));
                    // 실제 마이크 레벨(네이티브 산출)로 게이팅을 보정한다(죽은 메터 대체).
                    voiceRelayPeakMeteringRef.current = Math.max(
                        voiceRelayPeakMeteringRef.current,
                        capture.peakDb,
                    );
                    voiceRelayMeterUnavailableRef.current = false;
                    uploadUri = nativeCaptureUri;
                    // 무음 m4a 는 버린다.
                    if (m4aUri) {
                        await FileSystem.deleteAsync(m4aUri, { idempotent: true });
                    }
                }
            }

            if (uploadUri && processSegment) {
                // 연속 캡처: 처리를 큐에 위임(비차단)하고 즉시 다음 캡처를 재무장한다.
                // STT/번역/렌더가 끝날 때까지 마이크를 막지 않아 다음 발화 유실/템 김을 없앤다.
                // 이 세그먼트의 판정/메타데이터는 지금(flush 직후) 고정해 워커로 넘긴다(스테일 ref 방지).
                const chunkMeta = voiceRelayChunkMetaRef.current ?? {
                    utteranceId: voiceRelayUtteranceIdRef.current,
                    chunkIndex: voiceRelaySegmentStateRef.current.chunkIndex,
                    isFinal: true,
                };
                const snapshot: VoiceRelaySegmentSnapshot = {
                    segmentDurationMs: voiceRelayLastSegmentDurationMsRef.current,
                    meterUnavailable: voiceRelayMeterUnavailableRef.current,
                    flushReason: voiceRelayLastFlushReasonRef.current,
                    flushHadSpeech: voiceRelayLastFlushHadSpeechRef.current,
                    peakMeterDb: voiceRelayPeakMeteringRef.current,
                    hasSpeech: voiceRelaySegmentStateRef.current.hasSpeech,
                    sileroActive: voiceRelaySileroActiveRef.current,
                    sileroHadSpeech: voiceRelaySileroFirstSpeechAtMsRef.current != null,
                    chunkMeta: {
                        utteranceId: chunkMeta.utteranceId,
                        chunkIndex: chunkMeta.chunkIndex,
                        isFinal: chunkMeta.isFinal,
                    },
                };
                enqueueVoiceRelaySegment(uploadUri, snapshot);
                if (voiceRelayEnabledRef.current) {
                    scheduleVoiceRelayCaptureRetry('segment_buffered');
                }
            } else if (uploadUri) {
                await FileSystem.deleteAsync(uploadUri, { idempotent: true });
            }
        } catch (err) {
            console.warn('[VoIPScreen] Failed to stop voice relay segment', err);
        } finally {
            if (voiceRelayRecordingRemoteSuppressedRef.current) {
                voiceRelayRecordingRemoteSuppressedRef.current = false;
                if (!voiceRelayPlaybackRef.current && !voiceRelayNativeTtsActiveRef.current) {
                    releaseRemoteAudioSuppressionIfAllowed();
                }
            }
            try {
                await restoreWebRtcMicIfVoiceRelayInactive('segment_stop');
            } catch (restoreErr) {
                console.warn('[VoIPScreen] Failed to restore WebRTC mic after voice relay segment', restoreErr);
            }
        }
    }, [clearVoiceRelayTimers, enqueueVoiceRelaySegment, scheduleVoiceRelayCaptureRetry, releaseRemoteAudioSuppressionIfAllowed, restoreWebRtcMicIfVoiceRelayInactive, stopVoiceRelaySileroMonitor]);
    stopVoiceRelaySegmentRef.current = stopVoiceRelaySegment;

    const flushVoiceRelaySegment = useCallback(async (reason: string, isFinal: boolean) => {
        if (voiceRelayFlushInProgressRef.current || !voiceRelayRecordingRef.current) {
            return;
        }

        voiceRelayFlushInProgressRef.current = true;
        voiceRelayLastFlushReasonRef.current = reason;
        voiceRelayLastFlushHadSpeechRef.current = voiceRelaySileroActiveRef.current
            ? voiceRelaySileroFirstSpeechAtMsRef.current != null
            : voiceRelaySegmentStateRef.current.hasSpeech;
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
            if (!voiceRelayEnabledRef.current) {
                return;
            }
            const nowMs = Date.now();
            if (event.event === 'speech_start') {
                // 리드인 트리밍: 발화 대기(armed) 중이면 지금 STT 녹음을 시작한다.
                // 발화 전 무음이 업로드 파일에 포함되지 않아 서버 STT 무음 거부를 막는다.
                if (voiceRelayArmedForSpeechRef.current && !voiceRelayRecordingRef.current) {
                    voiceRelayArmedForSpeechRef.current = false;
                    if (voiceRelayArmTimeoutRef.current) {
                        clearTimeout(voiceRelayArmTimeoutRef.current);
                        voiceRelayArmTimeoutRef.current = null;
                    }
                    const armWaitMs = voiceRelayArmedAtMsRef.current > 0
                        ? Math.max(0, nowMs - voiceRelayArmedAtMsRef.current)
                        : 0;
                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                        event: 'VOIP_VOICE_RELAY_LEADIN_TRIMMED',
                        call_id: callInitResponse.call_id,
                        arm_wait_ms: armWaitMs,
                        silence_duration_ms: event.silenceDurationMs,
                        timestamp: new Date().toISOString(),
                    }));
                    voiceRelayLeadInTriggeredRef.current = true;
                    voiceRelayBypassArmRef.current = true;
                    void startVoiceRelaySegmentRef.current();
                    return;
                }
                if (!voiceRelayRecordingRef.current) {
                    return;
                }
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
            if (event.event !== 'speech_end' || voiceRelayFlushInProgressRef.current || !voiceRelayRecordingRef.current) {
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
            const sileroBoundary = resolveSileroBoundaryFromTuning();
            const boundaryDecision = shouldFlushOnSileroSpeechEnd({
                segmentDurationMs,
                speechSpanMs,
                lastSileroFlushAtMs: voiceRelaySileroLastFlushAtMsRef.current,
                nowMs,
                config: sileroBoundary,
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
                    const sileroBoundary = resolveSileroBoundaryFromTuning();
                    const hasSileroSpeech = voiceRelaySileroFirstSpeechAtMsRef.current != null;
                    if (shouldFlushSileroSafetyCap({
                        segmentDurationMs: elapsed,
                        hasSpeech: hasSileroSpeech,
                        config: sileroBoundary,
                    })) {
                        await flushVoiceRelaySegment('max_duration', true);
                        return;
                    }
                    if (!hasSileroSpeech) {
                        scheduleVoiceRelayFixedFlush();
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
        const bypassArm = voiceRelayBypassArmRef.current;
        voiceRelayBypassArmRef.current = false;
        if (!bypassArm) {
        const callReady = isVoiceRelayCallReady();
        // 연속 캡처: 처리(voiceRelayProcessingRef) 중이어도 마이크 재무장을 허용한다.
        // 처리는 별도 큐 워커가 담당하므로 캡처를 막지 않는다. (자기 에코 방지용 재생 가드는 유지)
        if (!voiceRelayEnabledRef.current || !callReady || voiceRelayRecordingRef.current || voiceRelayArmedForSpeechRef.current) {
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
                        : 'recording_in_progress',
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
        // Layer 1: 상대 TTS가 실제 재생 중이면(추정창 만료와 무관) 재무장하지 않는다.
        // onDone 시 'playback_complete' 로 재무장이 다시 스케줄된다.
        if (voiceRelayTtsActiveRef.current) {
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_START_BLOCKED',
                call_id: callInitResponse.call_id,
                reason: 'remote_tts_active',
                timestamp: new Date().toISOString(),
            }));
            scheduleVoiceRelayCaptureRetry('remote_tts_active');
            return;
        }
        const captureDecision = shouldStartVoiceRelayCapture({
            participantRole,
            turn: voiceRelayTurnRef.current,
            fairnessBargeInMs: getWorldlincoTuning().voip.fairness_barge_in_ms,
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
        if (captureDecision.bargeIn) {
            // 공정성 캡 발동: 상대 연속 발화로 굶주린 로컬이 턴을 강제로 회수했다(에코/활성재생 무관).
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_FAIRNESS_BARGE_IN',
                call_id: callInitResponse.call_id,
                starved_ms: Math.round(captureDecision.starvedMs ?? 0),
                timestamp: new Date().toISOString(),
            }));
        }
        }

        try {
            // 재무장 셋업 단계별 경량 타이밍 측정(동작 무변경) — 발화↔마이크 청취 텀의
            // 진짜 병목(permission/mode/enableVoipAudio/Silero) 핀포인트용.
            const rearmT0 = Date.now();
            const permission = await Audio.requestPermissionsAsync();
            if (!permission.granted) {
                setVoiceRelayError('마이크 권한이 없어 실시간 음성 통역을 시작할 수 없습니다.');
                setVoiceRelayEnabled(false);
                return;
            }
            const tPermMs = Date.now() - rearmT0;

            voipClientRef.current?.suspendLocalAudioForVoiceRelay();
            const tSuspendMs = Date.now() - rearmT0 - tPermMs;

            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: false,
                playThroughEarpieceAndroid: !isSpeakerOn,
                staysActiveInBackground: false,
            });
            const tSetModeMs = Date.now() - rearmT0 - tPermMs - tSuspendMs;
            // 녹음 시작 *전에* 통신 모드를 강제한다. 삼성 등 OEM 의 하드웨어 에코 제거(AEC)는
            // AudioManager.MODE_IN_COMMUNICATION 이 AudioRecord 생성 전에 설정돼야 활성화된다.
            // (docs/worldlinco-v2/MOBILE_CALL_TRANSLATION_ARCHITECTURE.md §2)
            await enableVoipAudio(isSpeakerOn, true);
            const tEnableVoipMs = Date.now() - rearmT0 - tPermMs - tSuspendMs - tSetModeMs;

            // 리드인 트리밍: Silero(자체 AudioRecord)를 먼저 켠다. bypass 재진입이 아니고
            // Silero 가 실제로 동작하면, 발화(speech_start) 전까지 STT 녹음을 보류(arm)해
            // 발화 전 무음이 업로드 파일에 포함되지 않게 한다. (서버 STT 무음 거부 방지)
            if (!bypassArm) {
                const tBeforeSileroMs = Date.now() - rearmT0;
                await startVoiceRelaySileroMonitor();
                const tSileroMs = Date.now() - rearmT0 - tBeforeSileroMs;
                console.log('[UI_PRESS_PROBE]', JSON.stringify({
                    event: 'VOIP_VOICE_RELAY_REARM_TIMING',
                    call_id: callInitResponse.call_id,
                    total_ms: Date.now() - rearmT0,
                    perm_ms: tPermMs,
                    suspend_ms: tSuspendMs,
                    set_mode_ms: tSetModeMs,
                    enable_voip_ms: tEnableVoipMs,
                    silero_ms: tSileroMs,
                    timestamp: new Date().toISOString(),
                }));
                if (voiceRelaySileroActiveRef.current) {
                    voiceRelayArmedForSpeechRef.current = true;
                    voiceRelayArmedAtMsRef.current = Date.now();
                    voiceRelayLeadInTriggeredRef.current = false;
                    setVoiceRelayListenWaiting(true);
                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                        event: 'VOIP_VOICE_RELAY_SEGMENT_ARMED',
                        call_id: callInitResponse.call_id,
                        connection_state: connectionState,
                        arm_timeout_ms: VOICE_RELAY_LEADIN_ARM_TIMEOUT_MS,
                        timestamp: new Date().toISOString(),
                    }));
                    if (voiceRelayArmTimeoutRef.current) {
                        clearTimeout(voiceRelayArmTimeoutRef.current);
                    }
                    voiceRelayArmTimeoutRef.current = setTimeout(() => {
                        voiceRelayArmTimeoutRef.current = null;
                        if (
                            voiceRelayArmedForSpeechRef.current
                            && !voiceRelayRecordingRef.current
                            && voiceRelayEnabledRef.current
                        ) {
                            // 발화가 없었음: 무음 폴백으로 즉시 녹음 시작(레거시 경로가 인계).
                            voiceRelayArmedForSpeechRef.current = false;
                            voiceRelayLeadInTriggeredRef.current = false;
                            voiceRelayBypassArmRef.current = true;
                            void startVoiceRelaySegmentRef.current();
                        }
                    }, VOICE_RELAY_LEADIN_ARM_TIMEOUT_MS);
                    return;
                }
            }
            voiceRelayArmedForSpeechRef.current = false;

            voiceRelayPeakMeteringRef.current = -160;
            voiceRelayMeterPollMissesRef.current = 0;
            voiceRelayMeterUnavailableRef.current = false;
            voiceRelayFileRmsPollTickRef.current = 0;
            voiceRelayPrevFileSizeRef.current = 0;
            voiceRelayPrevFilePollMsRef.current = 0;
            voiceRelayPeakGrowthBpsRef.current = 0;
            voiceRelayGrowthSpeechActiveRef.current = false;
            setVoiceRelayMeterDead(false);
            setVoiceRelayListenWaiting(false);
            voiceRelayLastFlushReasonRef.current = null;
            const leadInTrimmed = voiceRelayLeadInTriggeredRef.current;
            voiceRelayLeadInTriggeredRef.current = false;
            const recordStartMs = Date.now();
            const armWaitMs = voiceRelayArmedAtMsRef.current > 0
                ? Math.max(0, recordStartMs - voiceRelayArmedAtMsRef.current)
                : 0;
            voiceRelayArmedAtMsRef.current = 0;
            voiceRelaySegmentStateRef.current = createInitialVoiceRelaySegmentState(
                recordStartMs,
                voiceRelaySegmentStateRef.current.chunkIndex,
            );
            if (leadInTrimmed) {
                // 리드인 트리밍 경유: 발화가 이미 진행 중이므로 녹음 시작=발화 시작으로 본다.
                // (speechSpan 이 0 으로 잡혀 speech_end 가 'speech_span_too_short' 로 디퍼되는 것 방지)
                voiceRelaySileroFirstSpeechAtMsRef.current = recordStartMs;
                voiceRelaySegmentStateRef.current = {
                    ...voiceRelaySegmentStateRef.current,
                    hasSpeech: true,
                    lastSpeechAtMs: recordStartMs,
                };
            } else {
                voiceRelaySileroFirstSpeechAtMsRef.current = null;
            }
            const recording = new Audio.Recording();
            await recording.prepareToRecordAsync(buildVoiceRelayRecordingOptions());
            await recording.startAsync();

            voiceRelayRecordingRef.current = recording;
            setVoiceRelayRecording(true);
            voiceRelayRecordingRemoteSuppressedRef.current = true;
            setRemoteAudioSuppressed(true);
            setVoiceRelayError(null);

            // 마이크 컨텐션 해소: Silero 가 활성(자체 AudioRecord 가 실제 마이크를 점유)인 경우,
            // expo-audio 레코더(삼성 MultiRecord 차단으로 무음)가 아니라 Silero 스트림 PCM 을
            // 세그먼트 오디오로 캡처한다. expo 레코더는 flush 타이머/라이프사이클 드라이버로만 유지.
            voiceRelayNativeCaptureActiveRef.current = false;
            voiceRelayNativeCaptureUriRef.current = null;
            if (voiceRelaySileroActiveRef.current && isVoiceRelaySileroCaptureAvailable()) {
                const captureStarted = await beginVoiceRelaySileroCapture();
                if (captureStarted) {
                    voiceRelayNativeCaptureActiveRef.current = true;
                    voiceRelayNativeCaptureUriRef.current =
                        `${FileSystem.cacheDirectory}voice_relay_seg_${recordStartMs}.wav`;
                }
            }
            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                event: 'VOIP_VOICE_RELAY_SEGMENT_STARTED',
                call_id: callInitResponse.call_id,
                connection_state: connectionState,
                source_lang: localSourceLang,
                target_lang: localTargetLang,
                lead_in_trimmed: leadInTrimmed,
                arm_wait_ms: armWaitMs,
                native_capture: voiceRelayNativeCaptureActiveRef.current,
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
                                            // meter-dead 기기: AAC 바이트 RMS는 음량과 무관해 무음도 speech로 오판하므로,
                                            // 녹음 파일의 증가율(bytes/sec)로 발화/무음을 추정한다(대면 통역과 동일 방식).
                                            const info = await FileSystem.getInfoAsync(recordingUri);
                                            const size = info.exists && typeof info.size === 'number' ? info.size : 0;
                                            const nowMs = Date.now();
                                            if (voiceRelayPrevFilePollMsRef.current > 0 && size > 0) {
                                                const dtSec = Math.max(0.001, (nowMs - voiceRelayPrevFilePollMsRef.current) / 1000);
                                                const growthBps = Math.max(0, (size - voiceRelayPrevFileSizeRef.current) / dtSec);
                                                // 발화 중 최고 증가율을 추적(완만한 감쇠)해 상대 임계값을 만든다.
                                                voiceRelayPeakGrowthBpsRef.current = Math.max(
                                                    voiceRelayPeakGrowthBpsRef.current * 0.9,
                                                    growthBps,
                                                );
                                                // 32kbps AAC 발화 바닥값 + 발화 정점 대비 상대 임계값.
                                                const SPEECH_FLOOR_BPS = 1800;
                                                const relThreshold = voiceRelayPeakGrowthBpsRef.current * 0.5;
                                                const speechNow = voiceRelayPeakGrowthBpsRef.current >= SPEECH_FLOOR_BPS
                                                    && growthBps >= Math.max(SPEECH_FLOOR_BPS * 0.6, relThreshold);
                                                const priorHasSpeech = voiceRelaySegmentStateRef.current.hasSpeech;
                                                const pseudoMeterDb = speechNow ? -40 : -160;
                                                voiceRelayPeakMeteringRef.current = Math.max(
                                                    voiceRelayPeakMeteringRef.current,
                                                    pseudoMeterDb,
                                                );
                                                voiceRelaySegmentStateRef.current = updateVoiceRelaySegmentSpeechState(
                                                    voiceRelaySegmentStateRef.current,
                                                    pseudoMeterDb,
                                                    nowMs,
                                                );
                                                if (speechNow !== voiceRelayGrowthSpeechActiveRef.current) {
                                                    voiceRelayGrowthSpeechActiveRef.current = speechNow;
                                                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                                        event: speechNow
                                                            ? 'VOIP_VOICE_RELAY_FILE_GROWTH_SPEECH'
                                                            : 'VOIP_VOICE_RELAY_FILE_GROWTH_SILENCE',
                                                        call_id: callInitResponse.call_id,
                                                        growth_bps: Math.round(growthBps),
                                                        peak_bps: Math.round(voiceRelayPeakGrowthBpsRef.current),
                                                        timestamp: new Date().toISOString(),
                                                    }));
                                                }
                                                if (!priorHasSpeech && voiceRelaySegmentStateRef.current.hasSpeech) {
                                                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                                        event: 'VOIP_VOICE_RELAY_FILE_RMS_SPEECH',
                                                        call_id: callInitResponse.call_id,
                                                        growth_bps: Math.round(growthBps),
                                                        timestamp: new Date().toISOString(),
                                                    }));
                                                }
                                                const fileDecision = evaluateVoiceRelaySegmentDecision(
                                                    voiceRelaySegmentStateRef.current,
                                                    nowMs,
                                                    pseudoMeterDb,
                                                );
                                                if (fileDecision.action === 'flush') {
                                                    voiceRelayPrevFileSizeRef.current = size;
                                                    voiceRelayPrevFilePollMsRef.current = nowMs;
                                                    await flushVoiceRelaySegment(
                                                        fileDecision.reason,
                                                        fileDecision.isFinal,
                                                    );
                                                    return;
                                                }
                                            }
                                            voiceRelayPrevFileSizeRef.current = size;
                                            voiceRelayPrevFilePollMsRef.current = nowMs;
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
                        // opt-in QoS 보고(off-path·fail-open·멱등) — 연결 성공 시 표본 보고 시작.
                        // 실패해도 통화에 무영향(리포터 내부 try/catch). hangup() 에서 자동 정지.
                        boundClient.startStatsReporter({
                            apiBaseUrl: apiBaseUrlRef.current,
                            authToken: authTokenRef.current,
                            role: participantRole,
                        });
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
                    if (fromRole !== handlers.participantRole && !voiceRelayEnabledRef.current) {
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
                        // 반이중 턴테이킹: 상대가 발화를 시작하면 내 쪽 버퍼 큐(미전송분)는 비운다.
                        // (지연 전달되는 교차발화/에코 방지 — 기존 in-flight abort 와 동일한 의도)
                        voiceRelaySegmentQueueRef.current = [];

                        // 상대가 실제로 보내온 source_lang(피어의 고정 지정 언어)을 학습한다.
                        // 이후 내가 발화할 때 이 언어를 번역 타깃으로 사용해, 콜리가 콜러 언어를
                        // 시그널링으로 못 받은 경우의 ko→en 같은 오역 타깃을 자가 보정한다.
                        const learnedRemoteLang = String(message.source_lang || '').trim().toLowerCase();
                        if (learnedRemoteLang && learnedRemoteLang !== handlers.localSourceLang) {
                            observedRemoteRelaySourceLangRef.current = learnedRemoteLang;
                        }

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

                        // 라운드트립 에코 차단(양방향): 상대 폰이 "내가 방금 보낸 발화"의 TTS 를
                        // 다시 마이크로 잡아 재번역해 되돌려보내면, 들어온 번역문이 내 원문 전사와
                        // 같은 언어로 되돌아온다. 이를 비교해 내 발화가 나에게 되울려 발화되는 것을 막는다.
                        // (과거에는 caller 전용 + 내 '번역문'(상대 언어)과 비교해 언어가 달라 무력했다.)
                        {
                            const now = Date.now();
                            const localTranscriptNorm = lastLocalRelayTranscriptRef.current;
                            const remoteNorm = normalizeRelayText(translatedText);
                            if (now - lastLocalRelaySentAtRef.current < 15_000 && localTranscriptNorm && remoteNorm) {
                                // (G3 정합) 인라인 단어겹침 재구현 제거 → 공유 SSOT relayTextsSimilar 사용.
                                // 공유 헬퍼는 ===/includes/단어겹침 + F1 CJK 문자 바이그램(Dice≥0.55)까지
                                // 포함하므로, 띄어쓰기 없는 일본어 등 라운드트립 자가 에코도 차단된다.
                                const similar = relayTextsSimilar(localTranscriptNorm, remoteNorm);
                                if (similar) {
                                    console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                        event: 'VOIP_VOICE_RELAY_SKIP',
                                        call_id: callInitResponse.call_id,
                                        reason: 'roundtrip_self_echo',
                                        from_role: fromRole,
                                        transcript,
                                        translated_text: translatedText,
                                        local_transcript: localTranscriptNorm,
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

                        const now = Date.now();
                        const dedupeKeys = buildRemoteRelayDedupeKeys({
                            utteranceId: message.utterance_id,
                            chunkIndex: typeof message.chunk_index === 'number' ? message.chunk_index : 0,
                            normalizedTranscript: normalizeRelayText(transcript),
                            normalizedTranslated: normalizeRelayText(translatedText),
                            targetLang: relayTargetLang,
                        });
                        const dedupeDecision = shouldDedupeRemoteVoiceRelay({
                            keys: dedupeKeys,
                            previous: lastRemoteRelayDedupeRef.current,
                            nowMs: now,
                        });
                        if (dedupeDecision.dedupe) {
                            console.log('[UI_PRESS_PROBE]', JSON.stringify({
                                event: 'VOIP_VOICE_RELAY_SKIP',
                                call_id: callInitResponse.call_id,
                                reason: dedupeDecision.reason || 'remote_relay_dedupe',
                                utterance_id: message.utterance_id || null,
                                chunk_index: typeof message.chunk_index === 'number' ? message.chunk_index : 0,
                                transcript,
                                translated_text: translatedText,
                                timestamp: new Date().toISOString(),
                            }));
                            return;
                        }
                        lastRemoteRelayDedupeRef.current = {
                            utteranceKey: dedupeKeys.utteranceKey,
                            textKey: dedupeKeys.textKey,
                            atMs: now,
                        };
                        lastRemotePlaybackKeyRef.current = dedupeKeys.textKey;
                        lastRemotePlaybackAtRef.current = now;
                    }

                    if (!isLocal) {
                        setRemoteAudioSuppressed(true);
                        voiceRelayTurnRef.current = applyRemoteRelayTurn({
                            turn: voiceRelayTurnRef.current,
                            nowMs: Date.now(),
                            translatedText,
                            speakerOn: isSpeakerOnRef.current,
                        });
                        voiceRelayAbortGenerationRef.current += 1;
                        voiceRelayProcessingRef.current = false;
                        // 반이중: 상대 재생이 시작되면 내 버퍼 큐(미전송분)도 비워 교차발화/에코를 막는다.
                        voiceRelaySegmentQueueRef.current = [];
                        // stop teardown(stopAndUnloadAsync) 완료 promise 를 보관 → 재생 시작 전 await.
                        // (마이크 동시 오픈 시 녹음 미해제 상태로 재생이 시작돼 무음으로 죽던 레이스 차단.)
                        voiceRelaySegmentStopInFlightRef.current = handlers.stopVoiceRelaySegment(false);
                        const echoGuards = getVoiceRelayEchoGuards();
                        const echoGuardMs = isSpeakerOnRef.current
                            ? echoGuards.speaker
                            : echoGuards.remote;
                        voiceRelaySuppressUntilRef.current = Date.now() + echoGuardMs;
                        lastRemoteRelayTranscriptRef.current = normalizeRelayText(transcript);
                        lastRemoteRelayAtRef.current = voiceRelayTurnRef.current.lastRemoteRelayAtMs;
                        const seqId = typeof message.seq_id === 'number' && Number.isFinite(message.seq_id)
                            ? message.seq_id
                            : handlers.nextVoiceRelaySeqId();
                        // V.2 ID 백본 — 송신측 상관 ID를 그대로 이어받아 발화가 출처 ID에 스스로 붙는다.
                        // ID가 누락된 레거시 메시지는 콘텐츠 기반 결정적 ID로 보정한다(랜덤 폴백 금지:
                        // 같은 발화의 재전송이 서로 다른 ID가 되어 중복제거·순서 상관이 깨지는 것을 차단).
                        const remoteCorrelationId = message.correlation_id
                            || deterministicCorrelationId(
                                FEATURE_IDS.voipVoiceRelay,
                                `${normalizeRelayText(translatedText)}|${relayTargetLang}`,
                            );
                        const remoteUtteranceId = message.utterance_id || remoteCorrelationId;
                        handlers.enqueueVoiceRelayPlayback({
                            seqId,
                            utteranceId: remoteUtteranceId,
                            chunkIndex: typeof message.chunk_index === 'number' ? message.chunk_index : 0,
                            isFinal: message.is_final !== false,
                            translatedText,
                            targetLang: relayTargetLang,
                            correlationId: remoteCorrelationId,
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
            remoteTrackForceSuppressedRef.current = false;
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
        // 통역 모드에서는 서버 준비 여부와 무관하게, 연결되는 즉시 원음(WebRTC)을 영구 차단한다.
        // serverReady 를 조건에 넣으면 connected~serverReady 사이에 원격 트랙이 enabled 상태로
        // 도착해 원음이 새는 윈도우가 생기므로 제외한다. (재적용은 client.ontrack 에서 보장)
        if (voiceRelayEnabled && connectionState === 'connected') {
            setRemoteAudioSuppressed(true);
        }
    }, [connectionState, setRemoteAudioSuppressed, voiceRelayEnabled]);

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

        // build 157: 재무장을 번역 완료(voiceRelayBusy=false)에 직렬로 묶지 않는다.
        // 큐 워커(번역/전송)는 독립이고 네이티브 캡처는 flush 시점에 이미 해제되므로,
        // 녹음 종료 직후 마이크를 재무장해 번역과 병렬로 다음 발화를 받는다(설계 의도 L1829).
        // 과거엔 voiceRelayBusy 의존성이 재실행→클린업으로 segment_buffered 재무장 타이머를
        // 죽여, 재무장이 SENT(번역 완료) 뒤로 ~1.3s 밀렸다(원거리 실측 build 156).
        if (connectionState === 'connected' && isVoiceRelayCallReadyRef.current() && !voiceRelayRecording) {
            scheduleCaptureRestart(VOICE_RELAY_RESTART_DELAY_MS);
        }

        return () => {
            if (voiceRelayRestartTimerRef.current) {
                clearTimeout(voiceRelayRestartTimerRef.current);
                voiceRelayRestartTimerRef.current = null;
            }
        };
    }, [connectionState, restoreWebRtcMicIfVoiceRelayInactive, stopVoiceRelaySegment, voiceRelayEnabled, voiceRelayRecording]);

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
            // 통신 모드를 유지한 채 출력만 내장 스피커/수화기로 전환한다.
            await setVoipSpeakerphone(nextSpeakerOn);
            setIsSpeakerOn(nextSpeakerOn);
            isSpeakerOnRef.current = nextSpeakerOn;
        } catch (err) {
            console.error('[VoIPScreen] Failed to toggle speaker route', err);
        }
    }, [isSpeakerOn]);

    useEffect(() => {
        // 화면이 정상 종료(handleHangup) 없이 언마운트되더라도 통신 모드를 반드시 복원한다.
        return () => {
            void disableVoipAudio();
        };
    }, []);

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
        // 통화 종료 시 일반 오디오 모드로 복원(통신 모드/스피커폰 해제).
        await disableVoipAudio();

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
            {voiceRelayEnabled && voiceRelayBusy && !voiceRelayRecording ? (
                <View style={styles.chatLiveBanner}>
                    <ActivityIndicator color="#7dd3fc" size="small" />
                    <Text style={styles.chatLiveBannerText}>음성 감지됨 · 번역 처리 중… (3~7초)</Text>
                </View>
            ) : null}
            {voiceRelayEnabled && voiceRelayRecording ? (
                <View style={styles.chatLiveBanner}>
                    <Text style={styles.chatLiveBannerRecordingDot}>●</Text>
                    <Text style={styles.chatLiveBannerText}>
                        {voiceRelaySileroActive
                            ? '마이크 듣는 중 · 말이 끝나면 자동 번역'
                            : voiceRelayMeterDead
                                ? '마이크 듣는 중 · 음성 감지 후 자동 번역'
                                : '마이크 듣는 중 · 말이 끝나면 자동 번역'}
                    </Text>
                </View>
            ) : null}
            {voiceRelayEnabled && !voiceRelayBusy && !voiceRelayRecording && voiceRelayListenWaiting ? (
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
