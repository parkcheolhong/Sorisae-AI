/**
 * useVoiceCaptureLoop 의존성 — App.tsx에서 주입.
 */
import type { MutableRefObject, RefObject } from 'react';
import type { AudioRecording, AudioSound } from '../../compat/expoAvAudio';
import type { TranslateOptions } from '../../api/translate';
import type { PermissionType } from '../../hooks/usePermissionCheck';
import type { LangCode } from '../language/languageCatalog';
import type { CompanionPersona } from './companionMemory';
import type { CompanionVoiceCallState } from './companionVoiceCall';
import type { FaceConversationVadController } from '../shared/audioControllerTypes';
import type { SorisaeQaEntry } from './types';

export type SorisaeSongSubtitleDetectedBy = 'voice' | 'script' | 'manual' | 'seed';

export type SorisaeSongSubtitleDraft = {
    source: LangCode;
    target: LangCode;
    original: string;
    translated: string;
    repeatCount: number;
    detectedBy: SorisaeSongSubtitleDetectedBy;
};

export type PlayFaceTranslationOutputFn = (params: {
    translatedText: string;
    targetLang: LangCode;
    apiBaseUrl?: string;
    playbackSoundRef: MutableRefObject<AudioSound | null>;
    preferInstantDeviceSpeech?: boolean;
    correlationId?: string;
}) => Promise<void>;

export type VoiceCaptureUserInfo = {
    id?: number;
    preferred_language?: string;
} | null;

export type VoiceCaptureLoopDeps = {
    autoRelayDelayMs: number;
    fromLang: LangCode;
    toLang: LangCode;
    autoVoiceModeEnabled: boolean;
    faceAiMode: 'translate' | 'gpt';
    voiceSttLoading: boolean;
    interCallTurn: 'from' | 'to';
    interCallVoiceAssistEnabled: boolean;
    songModeEnabled: boolean;
    aiDisplayName: string;
    aiDisplayNameRef: MutableRefObject<string>;
    userInfo: VoiceCaptureUserInfo;
    gpsRegionHint: string;
    gpsCountryCode: string;
    lat: number | string | null;
    lon: number | string | null;
    gpsAccuracyM: number | null;
    API_BASE: string;
    LANGS: ReadonlyArray<{ code: LangCode; tts?: string; label?: string }>;
    AUTO_RELAY_DUPLICATE_GUARD_MS: number;

    setIsVoiceRecording: (v: boolean) => void;
    setVoiceSttLoading: (v: boolean) => void;
    setInputText: (v: string) => void;
    setGpsStatus: (msg: string) => void;
    setInterCallStatus: (msg: string) => void;
    setInterCallVoiceAssistEnabled: (v: boolean) => void;
    setSongModeEnabled: (v: boolean) => void;
    setAutoVoiceModeEnabled: (v: boolean) => void;
    setResultText: (v: string) => void;
    setOffline: (v: boolean) => void;
    setEngine: (v: string) => void;
    setInterCallTurn: (v: 'from' | 'to') => void;
    setInterManualText: (v: string) => void;
    setSongModeStatus: (msg: string) => void;
    setTourismSafetyBanner: (banner: { message: string; highRiskBlocked: boolean } | null) => void;
    setItinerarySeedQuery: (q: string) => void;
    setItinerarySeedNonce: (updater: (n: number) => number) => void;
    setSorisaeQaLog: (updater: (prev: SorisaeQaEntry[]) => SorisaeQaEntry[]) => void;

    getUiText: (lang: LangCode) => Record<string, string | undefined>;
    getLangLabel: (code: LangCode) => string;
    requestPermissions: (
        perms: PermissionType[],
        label: string,
        onFail?: (msg: string) => void,
    ) => Promise<boolean>;
    runTranslation: (text: string, source: LangCode, target: LangCode) => Promise<void>;
    clearAutoVoiceTimers: () => void;
    commitInterCallRelay: (
        turn: 'from' | 'to',
        spokenText: string,
        translatedText: string,
        options?: { isAutoRelay?: boolean },
    ) => void;
    resolveInterCallDirection: (turn: 'from' | 'to') => {
        listenLang: LangCode;
        translateTo: LangCode;
        listenLabel: string;
        translateLabel: string;
    };
    resolveSongHybridSource: (rawDetected: string, lyric: string) => {
        lang: LangCode;
        detectedBy: SorisaeSongSubtitleDetectedBy;
    };
    resolveSongHybridTarget: (source: LangCode) => LangCode;
    translateTextWithRegion: (
        text: string,
        from: LangCode,
        to: LangCode,
        timeoutMs?: number,
        options?: TranslateOptions,
    ) => Promise<{ translated: string; offline: boolean; engine: string }>;
    appendSongSubtitle: (entry: SorisaeSongSubtitleDraft) => void;
    recordTurn: (opts: { transcript: string; answer: string; language: string }) => Promise<CompanionPersona>;
    resetPersona: () => Promise<void>;
    savePersona: (persona: CompanionPersona) => Promise<boolean>;
    reportFaceVoiceAutoTuningMetric: (opts: {
        roundtripMs?: number;
        playbackMs?: number;
        overlapDetected?: boolean;
    }) => void;
    reportConversationEchoGuardMetric: (opts: { echoBlocked?: boolean }) => void;
    normalizeDetectedLangCode: (code: unknown) => LangCode | null;
    inferSpeechLangCode: (text: string, fallback: LangCode) => LangCode;
    normalizeSpeakText: (text: string) => string;
    isTravelItineraryIntent: (text: string) => boolean;
    normalizeLyricLine: (text: string) => string;
    isLikelyLyricLine: (text: string) => boolean;
    normalizeRelayText: (text: string) => string;
    formatAutoRelayDelayLabel: (ms: number) => string;
    formatStatusText: (template: string | undefined, vars: Record<string, string>) => string;
    playFaceTranslationOutput: PlayFaceTranslationOutputFn;
    stopFacePlayback: () => Promise<void>;
    stopSorisaePlayback: () => Promise<void>;
    isSupportedLangCode: (value: string) => value is LangCode;

    wakeCompanionVoiceCallNowRef: RefObject<() => void>;
    scheduleFaceConversationRestartRef: MutableRefObject<(afterPlayback?: Promise<void> | null) => void>;
    stopVoiceInputRef: MutableRefObject<((options?: { suppressAutoRestart?: boolean; discardSegment?: boolean }) => Promise<void>) | null>;
    faceVadControllerRef: RefObject<FaceConversationVadController>;
    recordingRef: MutableRefObject<AudioRecording | null>;
    voiceInputStartInFlightRef: MutableRefObject<boolean>;
    voiceInputStopInFlightRef: MutableRefObject<boolean>;
    voiceInputTargetRef: MutableRefObject<'main' | 'inter_call'>;
    autoVoiceModeEnabledRef: MutableRefObject<boolean>;
    autoVoiceStopTimerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
    autoVoiceRestartTimerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
    webSpeechRecognitionRef: MutableRefObject<{ stop?: () => void } | null>;
    faceConversationAudioEnabledRef: MutableRefObject<boolean>;
    faceSegmentCaptureStartedAtMsRef: MutableRefObject<number>;
    mainSorisaeRouteRef: MutableRefObject<boolean>;
    sorisaeWindowOpenRef: MutableRefObject<boolean>;
    companionKwsActiveRef: MutableRefObject<boolean>;
    companionVoiceCallArmedRef: MutableRefObject<boolean>;
    companionVoiceCallRef: MutableRefObject<CompanionVoiceCallState>;
    companionDormantSilent422StreakRef: MutableRefObject<number>;
    companionDormantRecoverBlockedUntilRef: MutableRefObject<number>;
    companionWakeRearmAtRef: MutableRefObject<number>;
    companionTripSessionIdRef: MutableRefObject<string | null>;
    companionPersonaRef: MutableRefObject<CompanionPersona>;
    faceGptConversationRef: MutableRefObject<Array<{ role: string; content: string }>>;
    faceGptSpokenEchoRef: MutableRefObject<Array<{ text: string; atMs: number }>>;
    faceSileroSupportedRef: MutableRefObject<boolean>;
    faceSileroActiveRef: MutableRefObject<boolean>;
    faceSileroCaptureActiveRef: MutableRefObject<boolean>;
    faceSileroCaptureUriRef: MutableRefObject<string | null>;
    faceSileroFirstSpeechAtMsRef: MutableRefObject<number | null>;
    faceSpeakingRef: MutableRefObject<boolean>;
    sorisaeSpeakingRef: MutableRefObject<boolean>;
    setSorisaeSpeakingUi?: (speaking: boolean) => void;
    sorisaeQaSeqRef: MutableRefObject<number>;
    sorisaeVoicePlaybackSoundRef: MutableRefObject<AudioSound | null>;
    faceVoicePlaybackSoundRef: MutableRefObject<AudioSound | null>;
    faceSpokenHistoryRef: MutableRefObject<Array<{
        transcript: string;
        translated: string;
        toLang: LangCode;
        spokenAtMs: number;
    }>>;
    mainLastAutoVoiceRelayRef: MutableRefObject<{ key: string; sentAt: number } | null>;
    interLastAutoRelayRef: MutableRefObject<{ key: string; sentAt: number } | null>;
    interCallActiveRef: MutableRefObject<boolean>;
    lastVoiceDrivenInputRef: MutableRefObject<{ text: string; atMs: number } | null>;
    lastFaceSpokenOutputRef: MutableRefObject<{ text: string; at: number } | null>;
    voiceSttLoadingRef: MutableRefObject<boolean>;
    faceAiModeRef: MutableRefObject<'translate' | 'gpt'>;
    faceScreenOpenRef: MutableRefObject<boolean>;
};
