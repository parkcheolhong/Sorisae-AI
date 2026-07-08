/**
 * STT 캡처 루프 — startVoiceInput / stopVoiceInput + 재시작·워치독·Silero 이펙트.
 * App.tsx Phase C 분리.
 */
import { useCallback, useEffect, useRef } from 'react';
import { Alert, Platform, ToastAndroid } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as Location from 'expo-location';
import { Audio } from '../../compat/expoAvAudio';
import { FEATURE_IDS, newCorrelationId } from '../correlation/correlationId';
import {
    FACE_CONVERSATION_ECHO_GUARD_MS,
    FACE_CONVERSATION_PERMISSION_RETRY_MS,
    FACE_CONVERSATION_PLAYBACK_DRAIN_MS,
    FACE_CONVERSATION_SPOKEN_HISTORY,
    FACE_OUTPUT_ECHO_GUARD_MS,
} from '../shared/audioConversationTiming';
import { getWorldlincoTuning } from '../../services/worldlincoTuningConfig';
import { resolveSorisaeCompanionVadDefaultsFromTuning } from '../../services/worldlincoTuningConfig';
import { buildPersonaBrief } from './companionMemory';
import { buildProactiveSuggestion } from './companionCommands';
import { withFriendChatTripContext } from './companionTripSessionStore';
import {
    FACE_CONTEXT_SESSION_GAP_MS,
    applyDormantSilenceBackoff,
    COMPANION_DORMANT_MIN_SEGMENT_MS,
    SORISAE_WINDOW_MIN_SEGMENT_MS,
    handleCompanionDormantScan,
    isDormantSilenceLoop,
    isRecoverableVoiceCaptureHttpError,
    processSorisaeFriendChatTurn,
    shouldContinueFaceConversationContext,
    shouldUploadFaceConversationSegment,
    shouldDeferSorisaeSegmentStop,
    shouldSkipSorisaeSegmentUpload,
    shouldUploadDormantWakeSegment,
    shouldUploadSorisaeWindowSegment,
} from './sorisaeCaptureSegment';
import { shouldSkipSilentVoiceRelayStt } from '../shared/relayAudioGuards';
import {
    beginVoiceRelaySileroCapture,
    endVoiceRelaySileroCapture,
    isVoiceRelaySileroCaptureAvailable,
    probeVoiceRelaySileroVadSupport,
    startVoiceRelaySileroVadMonitor,
    stopVoiceRelaySileroVadMonitor,
    subscribeVoiceRelaySileroVadEvents,
} from '../../native/voiceRelaySileroVad';
import {
    isLikelyGibberishRelayTranscript,
    isLikelyRepetitionHallucination,
    isLikelySilenceHallucination,
    isLikelyVoiceRelayEcho,
    relayTextsSimilar,
} from '../shared/relayTextGuards';
import { enableConversationCaptureAudio } from '../shared/audioRouteKernel';
import { acquireVoiceCapture, type VoiceCaptureFeatureId } from '../../services/voiceCaptureLease';
import { checkPermissionStatus } from '../../hooks/usePermissionCheck';
import type { LangCode } from '../language/languageCatalog';
import type { VoiceCaptureLoopDeps } from './voiceCaptureLoopTypes';

export function useVoiceCaptureLoop(deps: VoiceCaptureLoopDeps) {
    const FACE_PLAYBACK_BARGE_IN_ARM_MS = 250;
    const sorisaeServerErrorBlockedUntilRef = useRef(0);
    const sorisaePlaybackBlockedUntilRef = useRef(0);
    const facePlaybackBargeInArmAtRef = useRef(0);
    const faceConversationSessionIdRef = useRef<string | null>(null);
    const faceConversationLastTurnRef = useRef<{
        atMs: number;
        fromLang: LangCode;
        toLang: LangCode;
        transcript: string;
        translated: string;
    } | null>(null);
    const sileroSpeechEndHoldTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const sileroLastSpeechStartAtMsRef = useRef(0);
    // 소리새 홈 대화는 말끝 미세 끊김(글리치)이 잦아 조기 stop/restart 깜박임이 생길 수 있다.
    // 디바운스를 늘려 말끝 판정을 안정화한다.
    const SORISAE_SPEECH_END_SETTLE_MS = 500;
    const SILERO_SPEECH_END_GLITCH_IGNORE_MS = 350;
    // 음성대기 8초 규정: 완전 유휴가 8초 지속될 때만 자동 복구 재시작.
    const MIC_WATCHDOG_INTERVAL_MS = 2000;
    const MIC_WATCHDOG_IDLE_RECOVER_MS = 8000;
    const MIC_WATCHDOG_IDLE_TICKS = Math.ceil(MIC_WATCHDOG_IDLE_RECOVER_MS / MIC_WATCHDOG_INTERVAL_MS);
    const {
        autoRelayDelayMs,
        fromLang,
        toLang,
        autoVoiceModeEnabled,
        faceAiMode,
        voiceSttLoading,
        interCallTurn,
        interCallVoiceAssistEnabled,
        songModeEnabled,
        aiDisplayName,
        aiDisplayNameRef,
        userInfo,
        gpsRegionHint,
        gpsCountryCode,
        lat,
        lon,
        gpsAccuracyM,
        API_BASE,
        LANGS,
        AUTO_RELAY_DUPLICATE_GUARD_MS,
        setIsVoiceRecording,
        setVoiceSttLoading,
        setInputText,
        setGpsStatus,
        setInterCallStatus,
        setInterCallVoiceAssistEnabled,
        setSongModeEnabled,
        setAutoVoiceModeEnabled,
        setResultText,
        setOffline,
        setEngine,
        setInterCallTurn,
        setInterManualText,
        setSongModeStatus,
        setTourismSafetyBanner,
        setItinerarySeedQuery,
        setItinerarySeedNonce,
        setSorisaeQaLog,
        getUiText,
        getLangLabel,
        requestPermissions,
        runTranslation,
        clearAutoVoiceTimers,
        commitInterCallRelay,
        resolveInterCallDirection,
        resolveSongHybridSource,
        resolveSongHybridTarget,
        translateTextWithRegion,
        appendSongSubtitle,
        recordTurn,
        resetPersona,
        savePersona,
        reportFaceVoiceAutoTuningMetric,
        reportConversationEchoGuardMetric,
        normalizeDetectedLangCode,
        inferSpeechLangCode,
        normalizeSpeakText,
        isTravelItineraryIntent,
        normalizeLyricLine,
        isLikelyLyricLine,
        normalizeRelayText,
        formatAutoRelayDelayLabel,
        formatStatusText,
        playFaceTranslationOutput,
        stopFacePlayback,
        stopSorisaePlayback,
        isSupportedLangCode,
        wakeCompanionVoiceCallNowRef,
        scheduleFaceConversationRestartRef,
        stopVoiceInputRef,
        faceVadControllerRef,
        recordingRef,
        voiceInputStartInFlightRef,
        voiceInputStopInFlightRef,
        voiceInputTargetRef,
        autoVoiceModeEnabledRef,
        autoVoiceStopTimerRef,
        autoVoiceRestartTimerRef,
        webSpeechRecognitionRef,
        faceConversationAudioEnabledRef,
        faceSegmentCaptureStartedAtMsRef,
        mainSorisaeRouteRef,
        sorisaeWindowOpenRef,
        companionKwsActiveRef,
        companionVoiceCallArmedRef,
        companionVoiceCallRef,
        companionDormantSilent422StreakRef,
        companionDormantRecoverBlockedUntilRef,
        companionWakeRearmAtRef,
        companionTripSessionIdRef,
        companionPersonaRef,
        faceGptConversationRef,
        faceGptSpokenEchoRef,
        faceSileroSupportedRef,
        faceSileroActiveRef,
        faceSileroCaptureActiveRef,
        faceSileroCaptureUriRef,
        faceSileroFirstSpeechAtMsRef,
        faceSpeakingRef,
        sorisaeSpeakingRef,
        setSorisaeSpeakingUi,
        sorisaeQaSeqRef,
        sorisaeVoicePlaybackSoundRef,
        faceVoicePlaybackSoundRef,
        faceSpokenHistoryRef,
        mainLastAutoVoiceRelayRef,
        interLastAutoRelayRef,
        interCallActiveRef,
        lastVoiceDrivenInputRef,
        lastFaceSpokenOutputRef,
        voiceSttLoadingRef,
        faceAiModeRef,
        faceScreenOpenRef
    } = deps;

    const playFaceTranslationOutputImmediate = playFaceTranslationOutput as (params: {
        translatedText: string;
        targetLang: LangCode;
        apiBaseUrl?: string;
        playbackSoundRef: typeof faceVoicePlaybackSoundRef;
        correlationId?: string;
        preferInstantDeviceSpeech?: boolean;
    }) => Promise<void>;

    useEffect(() => {
        if (!autoVoiceModeEnabled) {
            faceConversationSessionIdRef.current = null;
            faceConversationLastTurnRef.current = null;
        }
    }, [autoVoiceModeEnabled]);

    const startVoiceInput = useCallback(async (options: { autoMode?: boolean; target?: 'main' | 'inter_call' } = {}) => { // NOSONAR
        if (voiceInputStartInFlightRef.current || voiceInputStopInFlightRef.current || recordingRef.current) {
            return;
        }
        voiceInputStartInFlightRef.current = true;
        const effectiveAutoMode = Boolean(options.autoMode);
        const inputTarget = options.target ?? 'main';
        try {
            voiceInputTargetRef.current = inputTarget;
            if (
                inputTarget === 'main'
                && Date.now() < sorisaePlaybackBlockedUntilRef.current
            ) {
                console.log('[FACE_CONVERSATION]', JSON.stringify({
                    event: 'capture_blocked_playback_window',
                    blocked_until_ms: sorisaePlaybackBlockedUntilRef.current,
                }));
                scheduleFaceConversationRestartRef.current(null);
                return;
            }
            // 반이중 가드: 통역/소리새 음성을 출력하는 동안에는 듣기를 시작하지 않는다(발화↔듣기 겹침 방지).
            if (effectiveAutoMode
                && inputTarget === 'main'
                && sorisaeSpeakingRef.current
                && !sorisaeVoicePlaybackSoundRef.current) {
                // 재생 핸들이 없는 speaking=true 잔존 상태는 고착으로 보고 즉시 해제한다.
                sorisaeSpeakingRef.current = false;
                setSorisaeSpeakingUi?.(false);
            }
            if (effectiveAutoMode
                && inputTarget === 'main'
                && faceSpeakingRef.current
                && faceVoicePlaybackSoundRef.current) {
                faceVoicePlaybackSoundRef.current.getStatusAsync()
                    .then((status) => {
                        if (!status?.isLoaded || !status?.isPlaying) {
                            stopFacePlayback().catch(() => { /* no-op */ });
                            faceSpeakingRef.current = false;
                            console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_speaking_gate_stale_cleared' }));
                        }
                    })
                    .catch(() => {
                        stopFacePlayback().catch(() => { /* no-op */ });
                        faceSpeakingRef.current = false;
                    });
            }
            const allowFaceDuplexCapture = effectiveAutoMode
                && inputTarget === 'main'
                && faceSpeakingRef.current
                && !sorisaeSpeakingRef.current
                && !mainSorisaeRouteRef.current
                && Date.now() >= facePlaybackBargeInArmAtRef.current;
            if (allowFaceDuplexCapture) {
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'capture_duplex_arm' }));
            } else if (effectiveAutoMode && inputTarget === 'main' && (faceSpeakingRef.current || sorisaeSpeakingRef.current)) {
                const interruptedFacePlayback = faceSpeakingRef.current;
                const interruptedSorisaePlayback = sorisaeSpeakingRef.current;
                console.log('[FACE_CONVERSATION]', JSON.stringify({
                    event: 'capture_blocked_speaking',
                    face_playback: interruptedFacePlayback,
                    sorisae_playback: interruptedSorisaePlayback,
                }));
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

                    lastVoiceDrivenInputRef.current = { text: transcript, atMs: Date.now() };
                    setInputText(transcript);
                    await runTranslation(transcript, fromLang, toLang);
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

            // 이미 허용된 마이크 권한은 재요청하지 않아 permission activity 반복 표출을 막는다.
            let hasPermission = await checkPermissionStatus('RECORD_AUDIO');
            if (!hasPermission) {
                hasPermission = await requestPermissions(['RECORD_AUDIO'], '음성 입력', (msg) => {
                    setGpsStatus(`🎤 음성 입력 실패: ${msg}`);
                });
            }
            if (!hasPermission) {
                if (effectiveAutoMode && autoVoiceModeEnabledRef.current && inputTarget === 'main') {
                    autoVoiceRestartTimerRef.current = setTimeout(() => {
                        if (autoVoiceModeEnabledRef.current && !recordingRef.current) {
                            void startVoiceInput({ autoMode: true });  // NOSONAR
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
                    await enableConversationCaptureAudio();
                    faceConversationAudioEnabledRef.current = true;
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
                    bitRate: 64_000,
                },
                ios: {
                    extension: '.m4a',
                    audioQuality: Audio.IOSAudioQuality.HIGH,
                    sampleRate: 16_000,
                    numberOfChannels: 1,
                    bitRate: 64_000,
                    linearPCMBitDepth: 16,
                    linearPCMIsBigEndian: false,
                    linearPCMIsFloat: false,
                },
                web: Audio.RecordingOptionsPresets.HIGH_QUALITY.web,
                isMeteringEnabled: isFaceConversationCapture || (effectiveAutoMode && inputTarget !== 'main'),
                keepAudioActiveHint: false,
            });
            recordingRef.current = recording;
            if (inputTarget === 'main' && effectiveAutoMode) {
                faceSegmentCaptureStartedAtMsRef.current = Date.now();
            }
            if (inputTarget === 'main') {
                // 기능 완전 분리: 대면통역 화면이 열려 있으면 소리새 경로를 절대 타지 않는다.
                // (sorisae 창 상태가 남아 있어도 friend-chat 라우팅 금지)
                mainSorisaeRouteRef.current = !songModeEnabled
                    && sorisaeWindowOpenRef.current
                    && !faceScreenOpenRef.current;
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
                    setGpsStatus(
                        sorisaeWindowOpenRef.current
                            ? '🎙️ 듣는 중 · 말씀하세요'
                            : (getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역'),
                    );
                    const sorisaeVadConfig = sorisaeWindowOpenRef.current && mainSorisaeRouteRef.current
                        ? resolveSorisaeCompanionVadDefaultsFromTuning(getWorldlincoTuning())
                        : undefined;
                    await faceVadControllerRef.current.start({
                        recording,
                        config: sorisaeVadConfig,
                        onFlush: (reason) => {
                            const segmentMs = faceSegmentCaptureStartedAtMsRef.current > 0
                                ? Date.now() - faceSegmentCaptureStartedAtMsRef.current
                                : 0;
                            const snap = faceVadControllerRef.current.getSnapshot();
                            if (reason === 'max_duration'
                                && sorisaeWindowOpenRef.current
                                && mainSorisaeRouteRef.current
                                && !snap.hasSpeech
                                && !faceSileroFirstSpeechAtMsRef.current) {
                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                    event: 'vad_max_duration_skip_silent',
                                    segment_ms: segmentMs,
                                }));
                                void stopVoiceInputRef.current?.({ discardSegment: true });  // NOSONAR
                                return;
                            }
                            if (shouldDeferSorisaeSegmentStop({
                                sorisaeWindowOpen: sorisaeWindowOpenRef.current,
                                mainSorisaeRoute: mainSorisaeRouteRef.current,
                                segmentDurationMs: segmentMs,
                            })) {
                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                    event: 'vad_flush_deferred',
                                    reason,
                                    segment_ms: segmentMs,
                                    min_ms: SORISAE_WINDOW_MIN_SEGMENT_MS,
                                }));
                                return;
                            }
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
                        const stopVoiceInput = stopVoiceInputRef.current;
                        if (stopVoiceInput) {
                            stopVoiceInput().catch(() => { });
                        }
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
                        void startVoiceInput({ autoMode: true });  // NOSONAR
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
            const beginCapture = () => { // NOSONAR
                if (sorisaeWindowOpenRef.current && Date.now() < sorisaeServerErrorBlockedUntilRef.current) {
                    autoVoiceRestartTimerRef.current = setTimeout(
                        beginCapture,
                        Math.max(500, sorisaeServerErrorBlockedUntilRef.current - Date.now()),
                    );
                    return;
                }
                if (!autoVoiceModeEnabledRef.current || recordingRef.current || voiceInputStopInFlightRef.current) {
                    return;
                }
                if (Date.now() < sorisaePlaybackBlockedUntilRef.current) {
                    autoVoiceRestartTimerRef.current = setTimeout(
                        beginCapture,
                        Math.max(200, sorisaePlaybackBlockedUntilRef.current - Date.now()),
                    );
                    return;
                }
                if (sorisaeSpeakingRef.current && sorisaeVoicePlaybackSoundRef.current) {
                    void sorisaeVoicePlaybackSoundRef.current.getStatusAsync()
                        .then((status) => {
                            if (!status?.isLoaded || !status?.isPlaying) {
                                sorisaeSpeakingRef.current = false;
                                setSorisaeSpeakingUi?.(false);
                                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'sorisae_speaking_stale_cleared' }));
                            }
                        })
                        .catch(() => {
                            sorisaeSpeakingRef.current = false;
                            setSorisaeSpeakingUi?.(false);
                        });
                }
                if (faceSpeakingRef.current && faceVoicePlaybackSoundRef.current) {
                    faceVoicePlaybackSoundRef.current.getStatusAsync()
                        .then((status) => {
                            if (!status?.isLoaded || !status?.isPlaying) {
                                stopFacePlayback().catch(() => { /* no-op */ });  // NOSONAR
                                faceSpeakingRef.current = false;
                                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_speaking_gate_stale_cleared' }));
                            }
                        })
                        .catch(() => {
                            stopFacePlayback().catch(() => { /* no-op */ });
                            faceSpeakingRef.current = false;
                        });
                }
                const shouldWaitForSpeaking = sorisaeSpeakingRef.current
                    || (faceSpeakingRef.current && Date.now() < facePlaybackBargeInArmAtRef.current)
                    || (faceSpeakingRef.current && mainSorisaeRouteRef.current);
                if (shouldWaitForSpeaking) {
                    autoVoiceRestartTimerRef.current = setTimeout(beginCapture, 200);
                    return;
                }
                if (voiceInputTargetRef.current === 'main') {
                    startVoiceInput({ autoMode: true }).catch(() => { });
                }
            };
            const armRestart = () => {
                autoVoiceRestartTimerRef.current = setTimeout(beginCapture, restartDelayMs);
            };
            if (afterPlayback) {
                if (!mainSorisaeRouteRef.current) {
                    armRestart();
                    return;
                }
                Promise.race([
                    afterPlayback,
                    new Promise<void>((resolve) => setTimeout(resolve, getWorldlincoTuning().face_conversation.playback_cap_ms)),
                ]).finally(() => {
                    sorisaePlaybackBlockedUntilRef.current = Date.now() + FACE_CONVERSATION_PLAYBACK_DRAIN_MS + restartDelayMs;
                    armRestart();
                });
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
        let sorisaeSpeakingStuckTicks = 0;
        let faceSpeakingStuckTicks = 0;
        const timer = setInterval(() => {
            const dormantCompanionWaiting = mainSorisaeRouteRef.current
                && companionVoiceCallArmedRef.current
                && companionVoiceCallRef.current.phase === 'dormant'
                && !sorisaeWindowOpenRef.current;
            const dormantBackoffActive = dormantCompanionWaiting
                && Date.now() < companionDormantRecoverBlockedUntilRef.current;

            // dormant 모드 복구는 전용 워치독(아래 dormant_watchdog)만 담당한다.
            // 공통 mic watchdog이 여기서 개입하면 백오프를 무시하고 재기동 루프를 만들 수 있다.
            if (dormantCompanionWaiting || dormantBackoffActive) {
                idleTicks = 0;
                sorisaeSpeakingStuckTicks = 0;
                faceSpeakingStuckTicks = 0;
                return;
            }

            // main 캡처 타겟이 비정상적으로 inter_call 등에 남아 있으면 자동 듣기가 영구 비활성화될 수 있다.
            // 통화가 실제 활성 상태가 아닐 때만 main으로 복구해 안전하게 재시작한다.
            if (autoVoiceModeEnabledRef.current
                && !interCallActiveRef.current
                && voiceInputTargetRef.current !== 'main'
                && !recordingRef.current
                && !voiceInputStartInFlightRef.current
                && !voiceInputStopInFlightRef.current
                && !voiceSttLoadingRef.current
                && !faceSpeakingRef.current
                && !sorisaeSpeakingRef.current) {
                console.log('[FACE_CONVERSATION]', JSON.stringify({
                    event: 'voice_target_recover_main',
                    from: voiceInputTargetRef.current,
                }));
                voiceInputTargetRef.current = 'main';
                startVoiceInput({ autoMode: true, target: 'main' }).catch(() => { });
                return;
            }

            // TTS 게이트(sorisaeSpeakingRef)가 풀리지 않으면 마이크가 영구 차단될 수 있다 — 강제 해제.
            // 단, 소리새 TTS 재생 중(서버 오디오 핸들 살아 있음)에는 mic를 켜지 않는다 → 발화 끊김 방지.
            if (sorisaeWindowOpenRef.current
                && sorisaeSpeakingRef.current
                && sorisaeVoicePlaybackSoundRef.current) {
                sorisaeVoicePlaybackSoundRef.current.getStatusAsync()
                    .then((status) => {
                        if (!status?.isLoaded || !status?.isPlaying) {
                            sorisaeSpeakingRef.current = false;
                            setSorisaeSpeakingUi?.(false);
                            console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'sorisae_speaking_gate_stale_cleared' }));
                        }
                    })
                    .catch(() => {
                        sorisaeSpeakingRef.current = false;
                        setSorisaeSpeakingUi?.(false);
                    });
                sorisaeSpeakingStuckTicks = 0;
                return;
            }
            if (faceSpeakingRef.current
                && faceVoicePlaybackSoundRef.current
                && !recordingRef.current
                && !voiceSttLoadingRef.current) {
                faceVoicePlaybackSoundRef.current.getStatusAsync()
                    .then((status) => {
                        if (!status?.isLoaded || !status?.isPlaying) {
                            stopFacePlayback().catch(() => { /* no-op */ });
                            faceSpeakingRef.current = false;
                            console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_speaking_gate_stale_cleared' }));
                        }
                    })
                    .catch(() => {
                        stopFacePlayback().catch(() => { /* no-op */ });
                        faceSpeakingRef.current = false;
                    });
                faceSpeakingStuckTicks = 0;
                return;
            }
            if (sorisaeWindowOpenRef.current
                && sorisaeSpeakingRef.current
                && !recordingRef.current
                && !voiceSttLoadingRef.current
                && !faceSpeakingRef.current) {
                sorisaeSpeakingStuckTicks += 1;
                if (sorisaeSpeakingStuckTicks >= 12) {
                    sorisaeSpeakingStuckTicks = 0;
                    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'sorisae_speaking_stuck_recover' }));
                    sorisaeSpeakingRef.current = false;
                    setSorisaeSpeakingUi?.(false);
                    startVoiceInput({ autoMode: true }).catch(() => { });
                    return;
                }
            } else {
                sorisaeSpeakingStuckTicks = 0;
            }

            // faceSpeaking 플래그가 오디오 핸들 없이 고착되면 듣기 재개가 영구 차단된다.
            // 재생 핸들이 없는 상태에서 일정 시간 지속되면 강제로 해제해 복구한다.
            if (faceSpeakingRef.current
                && !faceVoicePlaybackSoundRef.current
                && !recordingRef.current
                && !voiceSttLoadingRef.current) {
                faceSpeakingStuckTicks += 1;
                if (faceSpeakingStuckTicks >= 12) {
                    faceSpeakingStuckTicks = 0;
                    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_speaking_stuck_recover' }));
                    faceSpeakingRef.current = false;
                    startVoiceInput({ autoMode: true }).catch(() => { });
                    return;
                }
            } else {
                faceSpeakingStuckTicks = 0;
            }

            const fullyIdle = autoVoiceModeEnabledRef.current
                && voiceInputTargetRef.current === 'main'
                && !recordingRef.current
                && !voiceInputStartInFlightRef.current
                && !voiceInputStopInFlightRef.current
                && !voiceSttLoadingRef.current
                && !faceSpeakingRef.current
                && !sorisaeSpeakingRef.current
                && Date.now() >= sorisaePlaybackBlockedUntilRef.current;
            if (!fullyIdle) {
                idleTicks = 0;
                return;
            }
            idleTicks += 1;
            if (idleTicks >= MIC_WATCHDOG_IDLE_TICKS) {
                idleTicks = 0;
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'mic_watchdog_recover' }));
                void startVoiceInput({ autoMode: true });
            }
        }, MIC_WATCHDOG_INTERVAL_MS);
        return () => clearInterval(timer);
    }, [autoVoiceModeEnabled, setSorisaeSpeakingUi, startVoiceInput]);

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
            // 소리새는 기존 반이중을 유지한다. 대면 통역(face)만 풀 듀플렉스 바지인을 위해
            // 재생 중에도 VAD 이벤트를 계속 받는다. 최종 바지인 확정은 RMS/file-VAD가 동반될 때만 한다.
            const blockSileroDuringSpeaking = sorisaeSpeakingRef.current
                || (faceSpeakingRef.current && Date.now() < facePlaybackBargeInArmAtRef.current)
                || (faceSpeakingRef.current && mainSorisaeRouteRef.current);
            if (blockSileroDuringSpeaking) {
                return;
            }
            if (evt.event === 'speech_start') {
                if (sileroSpeechEndHoldTimerRef.current) {
                    clearTimeout(sileroSpeechEndHoldTimerRef.current);
                    sileroSpeechEndHoldTimerRef.current = null;
                }
                sileroLastSpeechStartAtMsRef.current = Date.now();
                if (faceSileroFirstSpeechAtMsRef.current == null) {
                    faceSileroFirstSpeechAtMsRef.current = Date.now();
                }
            } else if (evt.event === 'speech_end' && faceSileroFirstSpeechAtMsRef.current != null && recordingRef.current) {
                const lastSpeechStartAt = sileroLastSpeechStartAtMsRef.current;
                const speechSpanMs = lastSpeechStartAt > 0 ? Date.now() - lastSpeechStartAt : 0;
                if (speechSpanMs > 0 && speechSpanMs < SILERO_SPEECH_END_GLITCH_IGNORE_MS) {
                    console.log('[FACE_CONVERSATION]', JSON.stringify({
                        event: 'silero_speech_end_ignored_short_span',
                        span_ms: speechSpanMs,
                        min_ms: SILERO_SPEECH_END_GLITCH_IGNORE_MS,
                    }));
                    return;
                }
                if (faceSegmentCaptureStartedAtMsRef.current > 0) {
                    const segmentMs = Date.now() - faceSegmentCaptureStartedAtMsRef.current;
                    if (sorisaeWindowOpenRef.current && mainSorisaeRouteRef.current) {
                        if (shouldDeferSorisaeSegmentStop({
                            sorisaeWindowOpen: true,
                            mainSorisaeRoute: true,
                            segmentDurationMs: segmentMs,
                        })) {
                            console.log('[FACE_CONVERSATION]', JSON.stringify({
                                event: 'silero_speech_end_deferred',
                                segment_ms: segmentMs,
                                min_ms: SORISAE_WINDOW_MIN_SEGMENT_MS,
                                route: 'sorisae',
                            }));
                            return;
                        }
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'vad_end',
                            reason: 'silero_speech_end_sorisae',
                            segment_ms: segmentMs,
                            settle_ms: SORISAE_SPEECH_END_SETTLE_MS,
                        }));
                        const speechStartAtOnEnd = sileroLastSpeechStartAtMsRef.current;
                        if (sileroSpeechEndHoldTimerRef.current) {
                            clearTimeout(sileroSpeechEndHoldTimerRef.current);
                            sileroSpeechEndHoldTimerRef.current = null;
                        }
                        sileroSpeechEndHoldTimerRef.current = setTimeout(() => {
                            sileroSpeechEndHoldTimerRef.current = null;
                            const speakingResumed = sileroLastSpeechStartAtMsRef.current > speechStartAtOnEnd;
                            if (speakingResumed || !recordingRef.current) {
                                return;
                            }
                            void stopVoiceInputRef.current?.();
                        }, SORISAE_SPEECH_END_SETTLE_MS);
                        return;
                    }
                    const dormantWakeScan = mainSorisaeRouteRef.current
                        && companionVoiceCallArmedRef.current
                        && companionVoiceCallRef.current.phase === 'dormant'
                        && !sorisaeWindowOpenRef.current
                        && !faceScreenOpenRef.current
                        && !companionKwsActiveRef.current;
                    if (dormantWakeScan && segmentMs < COMPANION_DORMANT_MIN_SEGMENT_MS) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'silero_speech_end_deferred',
                            segment_ms: segmentMs,
                            min_ms: COMPANION_DORMANT_MIN_SEGMENT_MS,
                            route: 'dormant',
                        }));
                        return;
                    }
                }
                // 실제 음성이 한 번이라도 잡힌 뒤의 말 끝에서만 자연 종료 flush.
                console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'vad_end', reason: 'silero_speech_end' }));
                void stopVoiceInputRef.current?.();
            }
        });
        return () => {
            cancelled = true;
            if (sileroSpeechEndHoldTimerRef.current) {
                clearTimeout(sileroSpeechEndHoldTimerRef.current);
                sileroSpeechEndHoldTimerRef.current = null;
            }
            unsubscribe();
        };
    }, []);

    const stopVoiceInput = useCallback(async (options: { suppressAutoRestart?: boolean; discardSegment?: boolean } = {}) => {
        if (Platform.OS === 'web') {
            const recognizer = webSpeechRecognitionRef.current;
            if (recognizer) {
                try {
                    recognizer.stop?.();
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
        if (sileroSpeechEndHoldTimerRef.current) {
            clearTimeout(sileroSpeechEndHoldTimerRef.current);
            sileroSpeechEndHoldTimerRef.current = null;
        }
        faceSileroActiveRef.current = false;
        faceSileroCaptureActiveRef.current = false;
        faceSileroCaptureUriRef.current = null;
        faceSileroFirstSpeechAtMsRef.current = null;
        setIsVoiceRecording(false);
        const activeVoiceInputTarget = voiceInputTargetRef.current;
        const shouldAutoRestart = !options.suppressAutoRestart
            && (
                activeVoiceInputTarget === 'inter_call'
                    ? interCallActiveRef.current && interCallVoiceAssistEnabled
                    : autoVoiceModeEnabledRef.current
            );
        const rec = recordingRef.current;
        recordingRef.current = null;
        let uri: string | null = null;
        let friendVoiceRmsDb: number | undefined;
        let friendVoicePeakDb: number | undefined;
        let friendVoiceSegmentMs: number | undefined;
        let friendVoiceHadSpeech = Boolean(faceSileroHadSpeechSnapshot || faceVadSnapshot?.hasSpeech);
        try {
            try {
                const st = await rec.getStatusAsync();
                if (st.isRecording) {
                    await rec.stopAndUnloadAsync();
                }
                uri = rec.getURI();
            } catch (stopErr) {
                console.warn('[VOICE_INPUT]', JSON.stringify({
                    event: 'stop_recording_failed',
                    message: stopErr instanceof Error ? stopErr.message : String(stopErr),
                }));
                try {
                    uri = rec.getURI();
                } catch {
                    uri = null;
                }
            }
            // VoIP 세션 진입 중 quiesce 로 녹음만 정리하면 된다(업로드/STT 불필요).
            if (options.suppressAutoRestart) {
                console.log('[SORISAE296_FREEZE]', JSON.stringify({
                    event: 'voip_entry_quiesce_only',
                    guard_phase: 'sorisae296_freeze_behavior',
                }));
                if (uri) {
                    await FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
                }
                await Audio.setAudioModeAsync({
                    allowsRecordingIOS: false,
                    playsInSilentModeIOS: true,
                    shouldDuckAndroid: true,
                    playThroughEarpieceAndroid: false,
                }).catch(() => { /* no-op */ });
                return;
            }
            // 오디오 모드 원상복구
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: false,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: true,
                playThroughEarpieceAndroid: false,
            });
            let facePlaybackPromise: Promise<void> | null = null;
            if (!uri) {
                scheduleFaceConversationRestartRef.current(null);
                return;
            }
            let uploadUri = uri;
            if (options.discardSegment) {
                await FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
                if (faceSileroCaptureUriSnapshot) {
                    await FileSystem.deleteAsync(faceSileroCaptureUriSnapshot, { idempotent: true }).catch(() => { /* no-op */ });
                }
                setGpsStatus(
                    sorisaeWindowOpenRef.current
                        ? '🎙️ 듣는 중 · 말씀하세요'
                        : (getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역'),
                );
                return;
            }
            // [Silero 근본 무음 게이트] 네이티브 PCM 캡처가 있으면 실제 RMS로 무음을 전송 전에 차단하고,
            // 무음이 아니면 expo m4a(미터 죽은 기기에선 무음 환각 유발) 대신 네이티브 WAV(정확한 신호)를 업로드한다.
            if (faceSileroCaptureActiveSnapshot && faceSileroCaptureUriSnapshot
                && activeVoiceInputTarget === 'main') {
                try {
                    const nativePath = faceSileroCaptureUriSnapshot.replace(/^file:\/\//, '');
                    const capture = await endVoiceRelaySileroCapture(nativePath);
                    if (capture && capture.byteCount > 0) {
                        friendVoiceRmsDb = Number.isFinite(capture.rmsDb) ? capture.rmsDb : undefined;
                        friendVoicePeakDb = Number.isFinite(capture.peakDb) ? capture.peakDb : undefined;
                        friendVoiceSegmentMs = Number.isFinite(capture.durationMs) ? Math.round(capture.durationMs) : undefined;
                        const isDormantLoop = mainSorisaeRouteRef.current && isDormantSilenceLoop({
                            sorisaeWindowOpen: sorisaeWindowOpenRef.current,
                            activeVoiceInputTarget,
                            companionKwsActive: companionKwsActiveRef.current,
                            companionPhase: companionVoiceCallRef.current.phase,
                        });
                        const fileVadHadSpeech = Boolean(faceVadSnapshot?.hasSpeech);
                        friendVoiceHadSpeech = Boolean(faceSileroHadSpeechSnapshot || fileVadHadSpeech);
                        const vadFallbackUpload = shouldUploadDormantWakeSegment({
                            sileroHadSpeech: faceSileroHadSpeechSnapshot,
                            fileVadHadSpeech,
                            rmsDb: capture.rmsDb,
                        });
                        const allowDormantUpload = isDormantLoop && vadFallbackUpload;
                        const allowSorisaeWindowUpload = sorisaeWindowOpenRef.current
                            && shouldUploadSorisaeWindowSegment({
                                sileroHadSpeech: faceSileroHadSpeechSnapshot,
                                fileVadHadSpeech,
                                rmsDb: capture.rmsDb,
                                durationMs: capture.durationMs,
                            });
                        const allowFaceConversationUpload = !mainSorisaeRouteRef.current
                            && shouldUploadFaceConversationSegment({
                                sileroHadSpeech: faceSileroHadSpeechSnapshot,
                                fileVadHadSpeech,
                                rmsDb: capture.rmsDb,
                                faceFileSpeechRmsDb: getWorldlincoTuning().face_conversation.file_speech_rms_db,
                            });
                        // Silero speech_start 미감지 시 file-growth VAD·RMS 폴백.
                        // dormant/소리새 창뿐 아니라 대면 통역(face)도 같은 신호를 실제 발화로 인정해야
                        // meter-dead 단말에서 질문이 업로드 전 단계에서 조용히 사라지지 않는다.
                        if (!faceSileroHadSpeechSnapshot
                            && !allowDormantUpload
                            && !allowSorisaeWindowUpload
                            && !allowFaceConversationUpload) {
                            const sorisaeM4aFallback = sorisaeWindowOpenRef.current && mainSorisaeRouteRef.current;
                            if (!sorisaeM4aFallback) {
                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                    event: 'segment_skip_silence_silero',
                                    had_speech: faceSileroHadSpeechSnapshot,
                                    file_vad_had_speech: fileVadHadSpeech,
                                    rms_db: Math.round(capture.rmsDb),
                                    peak_db: Math.round(capture.peakDb),
                                }));
                                if (isDormantLoop) {
                                    applyDormantSilenceBackoff({
                                        streakRef: companionDormantSilent422StreakRef,
                                        blockedUntilRef: companionDormantRecoverBlockedUntilRef,
                                    }, 'silero_skip');
                                }
                                await FileSystem.deleteAsync(faceSileroCaptureUriSnapshot, { idempotent: true }).catch(() => { /* no-op */ });
                                setGpsStatus(
                                    sorisaeWindowOpenRef.current
                                        ? '🎙️ 듣는 중 · 말씀하세요'
                                        : (getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역'),
                                );
                                if (shouldAutoRestart && activeVoiceInputTarget === 'main') {
                                    scheduleFaceConversationRestartRef.current(null);
                                }
                                return;
                            }
                            console.log('[FACE_CONVERSATION]', JSON.stringify({
                                event: 'sorisae_silero_miss_m4a_fallback',
                                had_speech: faceSileroHadSpeechSnapshot,
                                file_vad_had_speech: fileVadHadSpeech,
                                rms_db: Math.round(capture.rmsDb),
                                duration_ms: Math.round(capture.durationMs),
                            }));
                            await FileSystem.deleteAsync(faceSileroCaptureUriSnapshot, { idempotent: true }).catch(() => { /* no-op */ });
                            // uploadUri 는 expo m4a(uri) 유지 — 서버 STT에 맡긴다(SM-T225N 등 VAD 불일치 회귀 방지).
                        } else if (isDormantLoop
                            && capture.durationMs > 0
                            && capture.durationMs < COMPANION_DORMANT_MIN_SEGMENT_MS) {
                            console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
                                event: 'scan_segment_too_short',
                                duration_ms: Math.round(capture.durationMs),
                                min_ms: COMPANION_DORMANT_MIN_SEGMENT_MS,
                                file_vad_had_speech: fileVadHadSpeech,
                            }));
                            await FileSystem.deleteAsync(faceSileroCaptureUriSnapshot, { idempotent: true }).catch(() => { /* no-op */ });
                            setGpsStatus('🔔 호출 대기 · 조금 더 길게 불러 주세요');
                            if (shouldAutoRestart && activeVoiceInputTarget === 'main') {
                                scheduleFaceConversationRestartRef.current(null);
                            }
                            return;
                        } else {
                            const useNativeUpload = mainSorisaeRouteRef.current || sorisaeWindowOpenRef.current;
                            if (useNativeUpload) {
                                uploadUri = faceSileroCaptureUriSnapshot;
                            }
                            console.log('[FACE_CONVERSATION]', JSON.stringify({
                                event: useNativeUpload ? 'silero_native_capture' : 'silero_native_metrics_m4a_upload',
                                rms_db: Math.round(capture.rmsDb),
                                peak_db: Math.round(capture.peakDb),
                                duration_ms: Math.round(capture.durationMs),
                            }));
                        }
                    }
                } catch {
                    // 네이티브 캡처 실패 → expo m4a 로 폴백.
                }
            }
            if (friendVoicePeakDb == null && faceVadSnapshot && Number.isFinite(faceVadSnapshot.peakMeterDb)) {
                friendVoicePeakDb = faceVadSnapshot.peakMeterDb;
            }
            if (friendVoiceSegmentMs == null && faceSegmentCaptureStartedAtMsRef.current > 0) {
                friendVoiceSegmentMs = Math.max(0, Math.round(Date.now() - faceSegmentCaptureStartedAtMsRef.current));
            }
            setVoiceSttLoading(true);
            if (autoVoiceModeEnabledRef.current && activeVoiceInputTarget === 'main') {
                setGpsStatus(
                    mainSorisaeRouteRef.current || sorisaeWindowOpenRef.current
                        ? '🔄 답변 준비 중...'
                        : (getUiText(fromLang).faceListenProcessing ?? '🔄 번역·음성 출력 중...'),
                );
            }
            try {
                const audioBase64 = await FileSystem.readAsStringAsync(uploadUri, {
                    encoding: FileSystem.EncodingType.Base64,
                });
                if (mainSorisaeRouteRef.current && sorisaeWindowOpenRef.current) {
                    const segmentDurationMs = faceSegmentCaptureStartedAtMsRef.current > 0
                        ? Date.now() - faceSegmentCaptureStartedAtMsRef.current
                        : 0;
                    const preUploadSkip = shouldSkipSorisaeSegmentUpload({
                        segmentDurationMs,
                        audioBase64Len: audioBase64.length,
                    });
                    if (preUploadSkip.skip) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'sorisae_segment_skip_preupload',
                            reason: preUploadSkip.reason,
                            duration_ms: segmentDurationMs,
                            audio_base64_len: audioBase64.length,
                            upload_kind: uploadUri === uri ? 'm4a' : 'silero_wav',
                        }));
                        setGpsStatus('🎙️ 듣는 중 · 말씀하세요');
                        return;
                    }
                }
                if (faceVadSnapshot) {
                    const silentSkip = shouldSkipSilentVoiceRelayStt({
                        peakMeterDb: faceVadSnapshot.peakMeterDb,
                        hasSpeech: faceVadSnapshot.hasSpeech,
                        meterUnavailable: faceVadSnapshot.meterUnavailable,
                        audioBase64,
                    });
                    const allowSorisaeSilentUpload = mainSorisaeRouteRef.current
                        && sorisaeWindowOpenRef.current
                        && shouldUploadSorisaeWindowSegment({
                            sileroHadSpeech: faceSileroHadSpeechSnapshot,
                            fileVadHadSpeech: Boolean(faceVadSnapshot.hasSpeech),
                            rmsDb: silentSkip.estimatedRmsDb ?? undefined,
                            durationMs: faceSegmentCaptureStartedAtMsRef.current > 0
                                ? Date.now() - faceSegmentCaptureStartedAtMsRef.current
                                : undefined,
                        });
                    const allowFaceSilentUpload = !mainSorisaeRouteRef.current
                        && activeVoiceInputTarget === 'main'
                        && shouldUploadFaceConversationSegment({
                            sileroHadSpeech: faceSileroHadSpeechSnapshot,
                            fileVadHadSpeech: Boolean(faceVadSnapshot.hasSpeech),
                            rmsDb: silentSkip.estimatedRmsDb ?? undefined,
                            faceFileSpeechRmsDb: getWorldlincoTuning().face_conversation.file_speech_rms_db,
                        });
                    if (silentSkip.skip && !allowSorisaeSilentUpload && !allowFaceSilentUpload) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_skip_silent',
                            reason: silentSkip.reason ?? 'silent',
                            estimated_rms_db: silentSkip.estimatedRmsDb,
                        }));
                        const isDormantLoop = mainSorisaeRouteRef.current && isDormantSilenceLoop({
                            sorisaeWindowOpen: sorisaeWindowOpenRef.current,
                            activeVoiceInputTarget,
                            companionKwsActive: companionKwsActiveRef.current,
                            companionPhase: companionVoiceCallRef.current.phase,
                        });
                        if (isDormantLoop) {
                            applyDormantSilenceBackoff({
                                streakRef: companionDormantSilent422StreakRef,
                                blockedUntilRef: companionDormantRecoverBlockedUntilRef,
                            }, 'silent_skip');
                        }
                        setGpsStatus(
                            mainSorisaeRouteRef.current || sorisaeWindowOpenRef.current
                                ? '🎙️ 듣는 중 · 말씀하세요'
                                : (getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역'),
                        );
                        return;
                    }
                }
                // 반이중 하드가드(최종 방어막): 이 세그먼트를 서버로 보내기 직전에 소리새/통역 TTS가
                // 아직 재생 중(faceSpeakingRef)이면 = 마이크가 자기(또는 상대) 발화 음성을 되잡은 것이므로,
                // 서버로 보내지 않고 즉시 버린다. '발화 중 재녹취 → 텍스트 생성 → 중복 발화' 루프를 원천 차단.
                if (autoVoiceModeEnabledRef.current
                    && activeVoiceInputTarget === 'main'
                    && (faceSpeakingRef.current || sorisaeSpeakingRef.current)) {
                    const allowFaceBargeIn = faceSpeakingRef.current
                        && !sorisaeSpeakingRef.current
                        && !mainSorisaeRouteRef.current
                        && Date.now() >= facePlaybackBargeInArmAtRef.current
                        && Boolean(
                            faceVadSnapshot?.hasSpeech
                            || (typeof friendVoiceRmsDb === 'number'
                                && friendVoiceRmsDb > getWorldlincoTuning().face_conversation.file_speech_rms_db)
                        );
                    if (allowFaceBargeIn) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_barge_in_interrupt',
                            rms_db: friendVoiceRmsDb ?? null,
                            had_speech: faceVadSnapshot?.hasSpeech ?? null,
                            arm_at_ms: facePlaybackBargeInArmAtRef.current,
                        }));
                        clearAutoVoiceTimers();
                        sorisaePlaybackBlockedUntilRef.current = 0;
                        await stopFacePlayback().catch(() => { /* no-op */ });
                        faceSpeakingRef.current = false;
                    } else {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'segment_discard_while_speaking' }));
                        setGpsStatus('🔇 발화 중 입력(에코) 무시 · 발화가 끝나면 다시 들어요');
                        return;
                    }
                }
                const profileLangRaw = String(userInfo?.preferred_language || toLang).trim().toLowerCase();
                const profileLang: LangCode = isSupportedLangCode(profileLangRaw) ? profileLangRaw as LangCode : toLang;
                // 대면 통역 언어쌍은 프로필 기본언어가 아니라 화면에서 사용자가 선택한 기준(from/to)을 SSOT로 사용한다.
                // 프로필/GPS 자동 보정이 수동 상대 언어 선택을 덮어쓰면 안 된다.
                const localInterpretLang: LangCode = fromLang;
                const isFaceTranslateRoute = !songModeEnabled
                    && activeVoiceInputTarget === 'main'
                    && !mainSorisaeRouteRef.current;
                const effectiveInterpretToLang: LangCode = toLang;
                const faceContextNowMs = Date.now();
                const canContinueFaceContext = isFaceTranslateRoute && shouldContinueFaceConversationContext({
                    nowMs: faceContextNowMs,
                    lastTurnAtMs: faceConversationLastTurnRef.current?.atMs ?? 0,
                    fromLang: localInterpretLang,
                    toLang: effectiveInterpretToLang,
                    lastFromLang: faceConversationLastTurnRef.current?.fromLang ?? null,
                    lastToLang: faceConversationLastTurnRef.current?.toLang ?? null,
                });
                if (isFaceTranslateRoute && !canContinueFaceContext) {
                    faceConversationSessionIdRef.current = `face-session-${newCorrelationId(FEATURE_IDS.faceInterpret)}`;
                }
                if (isFaceTranslateRoute && localInterpretLang === effectiveInterpretToLang) {
                    console.log('[FACE_CONVERSATION]', JSON.stringify({
                        event: 'peer_language_required',
                        from: localInterpretLang,
                        requested_to: effectiveInterpretToLang,
                    }));
                    setGpsStatus(
                        getUiText(fromLang).faceConversationPeerRequired
                        ?? '상대 언어를 GPS 또는 수동 선택으로 지정해 주세요.',
                    );
                    return;
                }
                // 소리새 AI(질문/관광 안내/대화) vs 대면 통역 — 완전 분리.
                // [기능 분리 Phase1] 판정 기준은 처리 시점의 라이브 ref가 아니라 **캡처 시작 시점 스냅샷**
                // (mainSorisaeRouteRef). 세그먼트 처리 중 창이 열리고 닫혀도 경로가 뒤바뀌지 않는다(레이스 차단).
                const isFaceGptMode = !songModeEnabled
                    && activeVoiceInputTarget === 'main'
                    && mainSorisaeRouteRef.current
                    && !faceScreenOpenRef.current;
                // 소리새 홈 Q&A는 한국어 발화(from=ko)일 때 응답 언어도 ko를 우선해
                // 한국어 UI 구간에 영어가 섞여 나오는 체감을 줄인다.
                const sorisaeReplyLang: LangCode = isFaceGptMode
                    ? (localInterpretLang === 'ko' ? 'ko' : profileLang)
                    : profileLang;
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
                        ? withFriendChatTripContext({
                            audio_base64: audioBase64,
                            tts: false,
                            language: sorisaeReplyLang,
                            conversation: faceGptConversationRef.current,
                            region_hint: gpsRegionHint || undefined,
                            country_code: gpsCountryCode || undefined,
                            latitude: Number.isFinite(Number(lat)) ? Number(lat) : undefined,
                            longitude: Number.isFinite(Number(lon)) ? Number(lon) : undefined,
                            accuracy_m: gpsAccuracyM != null && Number.isFinite(gpsAccuracyM) ? gpsAccuracyM : undefined,
                            correlation_id: faceCorrelationId,
                            feature_id: FEATURE_IDS.faceInterpret,
                            persona_brief: buildPersonaBrief(companionPersonaRef.current) || undefined,
                            proactive_hint: buildProactiveSuggestion(companionPersonaRef.current) || undefined,
                            voice_rms_db: friendVoiceRmsDb,
                            voice_peak_db: friendVoicePeakDb,
                            voice_segment_ms: friendVoiceSegmentMs,
                            voice_had_speech: friendVoiceHadSpeech,
                        }, {
                            tripSessionId: companionTripSessionIdRef.current,
                            userId: userInfo?.id ?? null,
                        })
                        : autoVoiceModeEnabled
                            ? {
                                audio_base64: audioBase64,
                                mode: 'bilingual',
                                bilingual_mode: true,
                                device_tts: true,
                                lang_a: localInterpretLang,
                                lang_b: effectiveInterpretToLang,
                                from_lang: localInterpretLang,
                                to_lang: effectiveInterpretToLang,
                                region_hint: gpsRegionHint || undefined,
                                language: 'auto',
                                correlation_id: faceCorrelationId,
                                feature_id: FEATURE_IDS.faceInterpret,
                                session_id: faceConversationSessionIdRef.current,
                            }
                            : {
                                // 대면 화면의 수동 단방향: 지정 언어 고정(designated)
                                audio_base64: audioBase64,
                                mode: 'designated',
                                device_tts: true,
                                from_lang: fromLang,
                                to_lang: effectiveInterpretToLang,
                                region_hint: gpsRegionHint || undefined,
                                language: fromLang,
                                correlation_id: faceCorrelationId,
                                feature_id: FEATURE_IDS.faceInterpret,
                                session_id: faceConversationSessionIdRef.current,
                            };

                const isDormantWakeScan = mainSorisaeRouteRef.current && isDormantSilenceLoop({
                    sorisaeWindowOpen: sorisaeWindowOpenRef.current,
                    activeVoiceInputTarget,
                    companionKwsActive: companionKwsActiveRef.current,
                    companionPhase: companionVoiceCallRef.current.phase,
                });
                if (isDormantWakeScan) {
                    const segmentDurationMs = faceSegmentCaptureStartedAtMsRef.current > 0
                        ? Date.now() - faceSegmentCaptureStartedAtMsRef.current
                        : 0;
                    if (segmentDurationMs > 0 && segmentDurationMs < COMPANION_DORMANT_MIN_SEGMENT_MS) {
                        console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
                            event: 'scan_segment_too_short',
                            duration_ms: segmentDurationMs,
                            min_ms: COMPANION_DORMANT_MIN_SEGMENT_MS,
                            upload_kind: uploadUri === uri ? 'm4a' : 'silero_wav',
                        }));
                        setGpsStatus('🔔 호출 대기 · 조금 더 길게 불러 주세요');
                        return;
                    }
                }

                if (isFaceGptMode) {
                    const gpsServicesEnabled = await Location.hasServicesEnabledAsync().catch(() => true);
                    if (!gpsServicesEnabled) {
                        const blockedMessage = 'GPS가 OFF 상태입니다. 여행·근처 질문은 정확도가 떨어질 수 있어요.';
                        setTourismSafetyBanner({
                            message: blockedMessage,
                            highRiskBlocked: false,
                        });
                        setGpsStatus('⚠️ GPS OFF · 일반 대화는 계속 · 위치 질문은 부정확할 수 있음');
                    }
                }

                let requestPayload = voicePayload;
                let requestUploadKind: 'm4a' | 'silero_wav' = uploadUri === uri ? 'm4a' : 'silero_wav';
                let res = await fetch(voiceEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestPayload),
                });
                if (!res.ok
                    && res.status === 422
                    && activeVoiceInputTarget === 'main'
                    && !songModeEnabled
                    && !isFaceGptMode
                    && uploadUri === uri
                    && faceSileroCaptureUriSnapshot) {
                    try {
                        const nativeAudioBase64 = await FileSystem.readAsStringAsync(faceSileroCaptureUriSnapshot, {
                            encoding: FileSystem.EncodingType.Base64,
                        });
                        requestPayload = {
                            ...voicePayload,
                            audio_base64: nativeAudioBase64,
                        };
                        requestUploadKind = 'silero_wav';
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_retry_native_wav_after_422',
                        }));
                        res = await fetch(voiceEndpoint, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(requestPayload),
                        });
                    } catch (retryErr) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_retry_native_wav_failed',
                            message: retryErr instanceof Error ? retryErr.message : String(retryErr),
                        }));
                    }
                }
                const faceRoundtripMs = activeVoiceInputTarget === 'main' && faceSegmentCaptureStartedAtMsRef.current > 0
                    ? Date.now() - faceSegmentCaptureStartedAtMsRef.current
                    : undefined;
                if (res.ok) {
                    const data = await res.json();
                    if (activeVoiceInputTarget === 'main') {
                        companionDormantSilent422StreakRef.current = 0;
                    }
                    const transcript = String(data.transcript ?? data.original_text ?? '').trim();
                    const sttTrust = String(data.stt_trust ?? 'high').toLowerCase();
                    const transcriptLooksMeaningful = /[\uAC00-\uD7A3]/.test(transcript)
                        ? transcript.length >= 2
                        : transcript.length >= 6;
                    const sorisaeExpectedLangs = [profileLang, sorisaeReplyLang, String(data.detected_language ?? '')]
                        .map((value) => String(value || '').trim())
                        .filter(Boolean);
                    const sorisaeSuspiciousTurn = isFaceGptMode
                        && (
                            (sttTrust === 'low' && !transcriptLooksMeaningful)
                            || isLikelyGibberishRelayTranscript(transcript, sorisaeExpectedLangs)
                            || isLikelySilenceHallucination(transcript, profileLang)
                            || isLikelyRepetitionHallucination(transcript)
                        );
                    console.log('[FACE_CONVERSATION]', JSON.stringify({
                        event: 'segment_response',
                        ok: true,
                        route: isFaceGptMode ? 'sorisae' : 'translate',
                        roundtrip_ms: typeof faceRoundtripMs === 'number' ? faceRoundtripMs : null,
                        bilingual: autoVoiceModeEnabledRef.current,
                        upload_kind: requestUploadKind,
                        stt_trust: sttTrust,
                        transcript: transcript.slice(0, 120),
                        from: data.from ?? null,
                        to: data.to ?? null,
                        translated: String(data.translated ?? '').slice(0, 120),
                    }));
                    if (sorisaeSuspiciousTurn) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_skip_sorisae_low_trust',
                            stt_trust: sttTrust,
                            transcript: transcript.slice(0, 80),
                        }));
                        setGpsStatus('🎙️ 듣는 중 · 말씀하세요');
                        if (activeVoiceInputTarget === 'main') {
                            reportFaceVoiceAutoTuningMetric({ overlapDetected: true });
                        }
                        return;
                    }
                    if (activeVoiceInputTarget === 'main') {
                        reportFaceVoiceAutoTuningMetric({
                            roundtripMs: faceRoundtripMs,
                            overlapDetected: false,
                        });
                    }
                    // [Phase6.1] 음성 호출 대기(dormant): 통역 스캔 캡처를 '조용한 웨이크워드 감시'로만 쓴다.
                    // 호명("OOOO"/"소리새") 감지 시 소리새를 깨우고, 그 외 발화는 통역/표시/발화 없이 소비한다
                    // (대기 중 주변 대화가 통역되어 튀어나오지 않게 한다). 듣기는 재시작해 계속 감시.
                    const isCompanionDormantScan = !sorisaeWindowOpenRef.current
                        && companionVoiceCallArmedRef.current
                        && companionVoiceCallRef.current.phase === 'dormant'
                        && !faceScreenOpenRef.current
                        && !companionKwsActiveRef.current
                        && activeVoiceInputTarget === 'main';
                    if (isCompanionDormantScan) {
                        const scanResult = handleCompanionDormantScan({
                            transcript,
                            sttTrust,
                            aiDisplayName: aiDisplayNameRef.current,
                            faceScreenOpen: faceScreenOpenRef.current,
                            wakeRearmAtMs: companionWakeRearmAtRef.current,
                            onWake: () => { wakeCompanionVoiceCallNowRef.current(); },
                            onScheduleRestart: () => { scheduleFaceConversationRestartRef.current(null); },
                        });
                        if (scanResult !== 'continue') {
                            return;
                        }
                    }
                    // 환각 차단: meter-dead(Tab 등) 기기는 무음/잔향 구간도 STT로 전송되므로,
                    // Whisper no_speech_prob/logprob 기반 신뢰도가 낮으면(=환각) 표시·발화하지 않는다.
                    // 단, 음성 호출 대기(dormant) 스캔은 웨이크워드 감지가 최우선이므로 위에서 먼저 처리한다.
                    if (sttTrust === 'low'
                        && autoVoiceModeEnabledRef.current
                        && activeVoiceInputTarget === 'main'
                        && !isFaceGptMode) {
                        console.log('[FACE_CONVERSATION]', JSON.stringify({
                            event: 'segment_skip_low_trust',
                            transcript: transcript.slice(0, 80),
                        }));
                        setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                        return;
                    }
                    if (transcript) {
                        if (isFaceGptMode) {
                            const turn = await processSorisaeFriendChatTurn({
                                transcript,
                                data: data as Record<string, unknown>,
                                profileLang: sorisaeReplyLang,
                                aiDisplayName,
                                userId: userInfo?.id,
                                faceCorrelationId,
                                apiBaseUrl: API_BASE,
                                companionVoiceCallRef,
                                faceGptSpokenEchoRef,
                                faceGptConversationRef,
                                companionPersonaRef,
                                companionTripSessionIdRef,
                                sorisaeQaSeqRef,
                                sorisaeSpeakingRef,
                                setSorisaeSpeakingUi,
                                sorisaeVoicePlaybackSoundRef,
                                setGpsStatus,
                                setTourismSafetyBanner,
                                setItinerarySeedQuery,
                                bumpItinerarySeedNonce: () => { setItinerarySeedNonce((n) => n + 1); },
                                setSorisaeQaLog,
                                onScheduleRestart: () => { scheduleFaceConversationRestartRef.current(null); },
                                normalizeDetectedLangCode,
                                inferSpeechLangCode: inferSpeechLangCode as (text: string, fallback: string) => string,
                                normalizeSpeakText,
                                isTravelItineraryIntent,
                                playFaceTranslationOutput,
                                reportFaceVoiceAutoTuningMetric,
                                recordPersonaTurn: recordTurn,
                                resetPersonaStore: resetPersona,
                                persistPersona: savePersona,
                            });
                            if (turn.playbackPromise) {
                                facePlaybackPromise = turn.playbackPromise;
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
                                setInterCallStatus(getUiText(fromLang).interAutoRelayDuplicateSkipped ?? '중복 자동 통역을 건너뛰었습니다.');
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
                                ?? localInterpretLang;
                            const effectiveTo: LangCode = normalizeDetectedLangCode(data.to)
                                ?? (effectiveFrom === localInterpretLang ? toLang : localInterpretLang);
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
                            const outputLangEcho = effectiveFrom !== localInterpretLang
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
                                reportFaceVoiceAutoTuningMetric({ overlapDetected: true });
                                reportConversationEchoGuardMetric({ echoBlocked: true });
                                setGpsStatus(getUiText(fromLang).autoVoiceSegmentStatus ?? '🎙️ 듣는 중 · 말이 끝나면 자동 번역');
                            } else if (mainLastAutoVoiceRelayRef.current && mainLastAutoVoiceRelayRef.current.key === relayKey && Date.now() - mainLastAutoVoiceRelayRef.current.sentAt < AUTO_RELAY_DUPLICATE_GUARD_MS) {
                                setGpsStatus(getUiText(fromLang).autoVoiceDuplicateSkipped ?? '중복 자동 음성 통역을 건너뛰었습니다.');
                            } else {
                                // #2 한국어(원문) 표출: 인식한 원문은 번역 성공 여부와 무관하게 항상 표시한다.
                                lastVoiceDrivenInputRef.current = { text: transcript, atMs: Date.now() };
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
                                    faceConversationLastTurnRef.current = {
                                        atMs: faceContextNowMs,
                                        fromLang: effectiveFrom,
                                        toLang: effectiveTo,
                                        transcript,
                                        translated: effectiveTranslated,
                                    };
                                    // #1 반복발화 금지: 동일 통역문이 가드창 안에서 다시 들어오면(에코/중복)
                                    // 표시는 갱신하되 TTS 재발화는 생략한다.
                                    const spokenKey = normalizeRelayText(effectiveTranslated);
                                    const lastSpoken = lastFaceSpokenOutputRef.current;
                                    const isRepeatOutput = !!lastSpoken
                                        && lastSpoken.text === spokenKey
                                        && Date.now() - lastSpoken.at < AUTO_RELAY_DUPLICATE_GUARD_MS;
                                    if (isRepeatOutput) {
                                        setGpsStatus(getUiText(fromLang).autoVoiceDuplicateSkipped ?? '중복 자동 음성 통역을 건너뛰었습니다.');
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
                                        facePlaybackBargeInArmAtRef.current = Date.now() + FACE_PLAYBACK_BARGE_IN_ARM_MS;
                                        setGpsStatus(getUiText(fromLang).faceSpeakingStatus ?? '🔊 통역 음성 출력 중 · 듣기 멈춤');
                                        facePlaybackPromise = playFaceTranslationOutputImmediate({
                                            translatedText: effectiveTranslated,
                                            targetLang: effectiveTo,
                                            apiBaseUrl: API_BASE,
                                            playbackSoundRef: faceVoicePlaybackSoundRef,
                                            preferInstantDeviceSpeech: true,
                                            correlationId: typeof data.correlation_id === 'string' ? data.correlation_id : faceCorrelationId,
                                        }).finally(() => {
                                            reportFaceVoiceAutoTuningMetric({
                                                playbackMs: FACE_CONVERSATION_PLAYBACK_DRAIN_MS,
                                                overlapDetected: false,
                                            });
                                            // TTS 재생이 끝난 시점으로 에코 보호창을 갱신해
                                            // 재생 직후 마이크가 잡는 잔향(지연 도착 포함)을 확실히 무시한다.
                                            spokenEntry.spokenAtMs = Date.now();
                                            lastFaceSpokenOutputRef.current = { text: spokenKey, at: Date.now() };
                                            // 잔향이 가라앉도록 drain 지연 후 게이트 해제 → 그 다음에야 듣기 재개.
                                            setTimeout(() => {
                                                faceSpeakingRef.current = false;
                                                facePlaybackBargeInArmAtRef.current = 0;
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
                            const manualTo = effectiveInterpretToLang;
                            lastVoiceDrivenInputRef.current = { text: transcript, atMs: Date.now() };
                            setInputText(transcript);
                            if (translatedText) {
                                setGpsStatus(`🎯 ${getLangLabel(manualFrom)} → ${getLangLabel(manualTo)}`);
                                setResultText(translatedText);
                                setOffline(false);
                                setEngine(String(data.engine ?? 'nado-voice'));
                                faceConversationLastTurnRef.current = {
                                    atMs: faceContextNowMs,
                                    fromLang: manualFrom,
                                    toLang: manualTo,
                                    transcript,
                                    translated: translatedText,
                                };
                                if (faceConversationAudioEnabledRef.current && activeVoiceInputTarget === 'main') {
                                    faceSpeakingRef.current = true;
                                    facePlaybackBargeInArmAtRef.current = Date.now() + FACE_PLAYBACK_BARGE_IN_ARM_MS;
                                    setGpsStatus(getUiText(fromLang).faceSpeakingStatus ?? '🔊 통역 음성 출력 중 · 듣기 멈춤');
                                    facePlaybackPromise = playFaceTranslationOutputImmediate({
                                        translatedText,
                                        targetLang: manualTo,
                                        apiBaseUrl: API_BASE,
                                        playbackSoundRef: faceVoicePlaybackSoundRef,
                                        preferInstantDeviceSpeech: true,
                                        correlationId: typeof data.correlation_id === 'string' ? data.correlation_id : faceCorrelationId,
                                    }).finally(() => {
                                        setTimeout(() => {
                                            faceSpeakingRef.current = false;
                                            facePlaybackBargeInArmAtRef.current = 0;
                                        }, FACE_CONVERSATION_PLAYBACK_DRAIN_MS);
                                    });
                                }
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
                        route: mainSorisaeRouteRef.current ? 'sorisae' : 'translate',
                        upload_kind: requestUploadKind,
                        roundtrip_ms: typeof faceRoundtripMs === 'number' ? faceRoundtripMs : null,
                        detail: errorText.slice(0, 200),
                    }));
                    const isDormantScanError = mainSorisaeRouteRef.current
                        && !sorisaeWindowOpenRef.current
                        && activeVoiceInputTarget === 'main'
                        && !companionKwsActiveRef.current
                        && companionVoiceCallRef.current.phase === 'dormant';
                    if (isDormantScanError && res.status === 422) {
                        applyDormantSilenceBackoff({
                            streakRef: companionDormantSilent422StreakRef,
                            blockedUntilRef: companionDormantRecoverBlockedUntilRef,
                        }, '422');
                    }
                    if (autoVoiceModeEnabled && activeVoiceInputTarget === 'main') {
                        if (mainSorisaeRouteRef.current && (res.status === 502 || res.status === 503)) {
                            const gatewayBackoffMs = res.status === 502 ? 8000 : 5000;
                            sorisaeServerErrorBlockedUntilRef.current = Date.now() + gatewayBackoffMs;
                            setGpsStatus(
                                res.status === 502
                                    ? '⚠️ AI 서버 재시작 중(502) · 8초 후 다시 들어요'
                                    : '⚠️ AI 서버 준비 중(503) · 잠시 후 다시 말씀해 주세요',
                            );
                        } else if (mainSorisaeRouteRef.current && res.status >= 500) {
                            sorisaeServerErrorBlockedUntilRef.current = Date.now() + 4500;
                            setGpsStatus(`⚠️ AI 서버 응답 실패 (${res.status}) · 잠시 후 다시 말씀해 주세요`);
                        } else if (mainSorisaeRouteRef.current && res.status === 401) {
                            setGpsStatus('⚠️ 로그인이 필요합니다 · 다시 로그인해 주세요');
                        } else {
                            const recoverable = isRecoverableVoiceCaptureHttpError(res.status, errorText);
                            setGpsStatus(
                                recoverable || res.status === 422
                                    ? '🎙️ 듣는 중 · 말씀하세요'
                                    : mainSorisaeRouteRef.current
                                        ? `⚠️ 답변 실패 (${res.status}) · 다시 말씀해 주세요`
                                        : '🎙️ 이번 구간 오류 · 계속 듣는 중...',
                            );
                        }
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
                if (faceSileroCaptureUriSnapshot && faceSileroCaptureUriSnapshot !== uploadUri) {
                    FileSystem.deleteAsync(faceSileroCaptureUriSnapshot, { idempotent: true }).catch(() => { /* no-op */ });
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
    }, [appendSongSubtitle, autoVoiceModeEnabled, clearAutoVoiceTimers, commitInterCallRelay, fromLang, getLangLabel, getUiText, interCallTurn, interCallVoiceAssistEnabled, resolveInterCallDirection, resolveSongHybridSource, resolveSongHybridTarget, runTranslation, songModeEnabled, startVoiceInput, stopFacePlayback, stopSorisaePlayback, toLang, translateTextWithRegion, userInfo?.preferred_language]);
    return { startVoiceInput, stopVoiceInput };
}
