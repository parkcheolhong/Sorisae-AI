/**
 * 소리새 음성 파이프 — 대화 토글 · 창 닫기 · 웨이크워드(KWS) · 3분 무활동.
 * App.tsx 캡처 루프와 ref로 연결; VoIP/armable 이펙트는 App에 유지.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Platform } from 'react-native';
import type { MutableRefObject, RefObject } from 'react';
import type { AudioRecording, AudioSound } from '../../compat/expoAvAudio';

import {
    COMPANION_KWS_MODEL_PATH_STORAGE_KEY,
    COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY,
    COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY,
    COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY,
    COMPANION_KWS_PROVIDER_STORAGE_KEY,
    DEFAULT_COMPANION_KWS_MODEL_PATH,
} from '../../app/appConstants';
import {
    isOnDeviceKwsNativeAvailable,
    type OnDeviceKwsProvider,
    probeOnDeviceKwsSupport,
    startOnDeviceKws,
    stopOnDeviceKws,
    subscribeOnDeviceKwsEvents,
} from '../../native/onDeviceKws';
import { resolveAiDisplayName } from './companionIdentity';
import {
    armCompanionVoiceCall,
    createCompanionVoiceCallState,
    disarmCompanionVoiceCall,
    markCompanionVoiceCallActivity,
    shouldCompanionVoiceCallSleep,
    sleepCompanionVoiceCall,
    wakeCompanionVoiceCall,
    type CompanionVoiceCallState,
} from './companionVoiceCall';
import type {
    SorisaeRuntimeAdapter,
    SorisaePlaybackSoundRef,
} from './runtimeAdapter';

const DEFAULT_VOSK_MODEL_DIR_CANDIDATES = [
    '/sdcard/Download/vosk-model-small-ko',
    '/storage/emulated/0/Download/vosk-model-small-ko',
    '/sdcard/Download/vosk-model-ko',
    '/storage/emulated/0/Download/vosk-model-ko',
    '/sdcard/Download/model',
    '/storage/emulated/0/Download/model',
] as const;

export type SorisaeVoicePipelineDeps = {
    aiDisplayName: string;
    aiDisplayNameRef: RefObject<string>;
    autoVoiceModeEnabled: boolean;
    setAutoVoiceModeEnabled: (v: boolean) => void;
    autoVoiceModeEnabledRef: RefObject<boolean>;
    faceAiModeRef: MutableRefObject<'translate' | 'gpt'>;
    setFaceAiMode: (v: 'translate' | 'gpt') => void;
    recordingRef: RefObject<AudioRecording | null>;
    voiceInputTargetRef: MutableRefObject<string>;
    runtimeAdapter: SorisaeRuntimeAdapter;
    sorisaeVoicePlaybackSoundRef: SorisaePlaybackSoundRef;
    faceVoicePlaybackSoundRef: SorisaePlaybackSoundRef;
    sorisaeSpeakingRef: MutableRefObject<boolean>;
    sorisaeWindowOpen: boolean;
    setSorisaeWindowOpen: (v: boolean) => void;
    sorisaeWindowOpenRef: MutableRefObject<boolean>;
    faceScreenOpenRef: MutableRefObject<boolean>;
    setGpsStatus: (msg: string) => void;
    scheduleFaceConversationRestartRef: RefObject<(afterPlayback?: Promise<void> | null) => void>;
    voiceInputStartInFlightRef: RefObject<boolean>;
};

export function useSorisaeVoicePipeline(deps: SorisaeVoicePipelineDeps) {
    const {
        aiDisplayName,
        aiDisplayNameRef,
        autoVoiceModeEnabled,
        setAutoVoiceModeEnabled,
        autoVoiceModeEnabledRef,
        faceAiModeRef,
        setFaceAiMode,
        recordingRef,
        voiceInputTargetRef,
        runtimeAdapter,
        sorisaeVoicePlaybackSoundRef,
        faceVoicePlaybackSoundRef,
        sorisaeSpeakingRef,
        sorisaeWindowOpen,
        setSorisaeWindowOpen,
        sorisaeWindowOpenRef,
        faceScreenOpenRef,
        setGpsStatus,
        scheduleFaceConversationRestartRef,
        voiceInputStartInFlightRef,
    } = deps;

    const [companionVoiceCallArmed, setCompanionVoiceCallArmed] = useState(false);
    const companionVoiceCallRef = useRef<CompanionVoiceCallState>(createCompanionVoiceCallState());
    const companionVoiceCallArmedRef = useRef(false);
    useEffect(() => { companionVoiceCallArmedRef.current = companionVoiceCallArmed; }, [companionVoiceCallArmed]);

    const companionKwsActiveRef = useRef(false);
    const companionKwsUnsubscribeRef = useRef<(() => void) | null>(null);
    const companionKwsProviderRef = useRef<OnDeviceKwsProvider>('vosk');
    const companionKwsModelPathRef = useRef(DEFAULT_COMPANION_KWS_MODEL_PATH);
    const companionKwsPorcupineAccessKeyRef = useRef('');
    const companionKwsPorcupineKeywordPathsRef = useRef<string[]>([]);
    const [companionKwsProvider, setCompanionKwsProvider] = useState<OnDeviceKwsProvider>('vosk');
    const [companionKwsModelPath, setCompanionKwsModelPath] = useState(DEFAULT_COMPANION_KWS_MODEL_PATH);
    const [companionKwsPorcupineAccessKey, setCompanionKwsPorcupineAccessKey] = useState('');
    const [companionKwsPorcupineKeywordPaths, setCompanionKwsPorcupineKeywordPaths] = useState<string[]>([]);
    const companionWakeRearmAtRef = useRef(0);
    const companionDormantSilent422StreakRef = useRef(0);
    const companionDormantRecoverBlockedUntilRef = useRef(0);
    const sorisaeConversationRequestedRef = useRef(false);

    const wakeCompanionVoiceCallNowRef = useRef<() => void>(() => { });
    const startCompanionDormantListeningRef = useRef<() => Promise<void>>(async () => { });

    useEffect(() => {
        void Promise.all([
            AsyncStorage.getItem(COMPANION_KWS_MODEL_PATH_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PROVIDER_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY),
            AsyncStorage.getItem(COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY),
        ])
            .then(([savedModelPath, savedProvider, savedAccessKey, savedKeywordPath, savedKeywordPathsJson]) => {
                const path = String(savedModelPath || '').trim();
                if (path) {
                    companionKwsModelPathRef.current = path;
                    setCompanionKwsModelPath(path);
                }
                const provider = String(savedProvider || '').trim().toLowerCase();
                if (provider === 'vosk' || provider === 'porcupine') {
                    const typedProvider = provider as OnDeviceKwsProvider;
                    companionKwsProviderRef.current = typedProvider;
                    setCompanionKwsProvider(typedProvider);
                }
                const accessKey = String(savedAccessKey || '').trim();
                if (accessKey) {
                    companionKwsPorcupineAccessKeyRef.current = accessKey;
                    setCompanionKwsPorcupineAccessKey(accessKey);
                }
                let keywordPaths: string[] = [];
                try {
                    const parsed = JSON.parse(String(savedKeywordPathsJson || '[]')) as unknown;
                    if (Array.isArray(parsed)) {
                        keywordPaths = parsed
                            .map((item) => String(item || '').trim())
                            .filter((item) => item.length > 0);
                    }
                } catch {
                    keywordPaths = [];
                }
                if (keywordPaths.length === 0) {
                    const keywordPath = String(savedKeywordPath || '').trim();
                    if (keywordPath) {
                        keywordPaths = [keywordPath];
                    }
                }
                if (keywordPaths.length > 0) {
                    companionKwsPorcupineKeywordPathsRef.current = keywordPaths;
                    setCompanionKwsPorcupineKeywordPaths(keywordPaths);
                }
            })
            .catch(() => { /* no-op */ });
    }, []);

    const handleToggleSorisaeConversation = useCallback(async () => {
        if (Platform.OS === 'web') {
            Alert.alert(aiDisplayName, `${aiDisplayName} 음성 대화는 모바일 앱에서 사용할 수 있습니다.`);
            return;
        }
        faceAiModeRef.current = 'gpt';
        setFaceAiMode('gpt');
        if (autoVoiceModeEnabled) {
            if (recordingRef.current) {
                await runtimeAdapter.stopVoiceInput({ suppressAutoRestart: true });
            }
            await runtimeAdapter.stopPlayback(sorisaeVoicePlaybackSoundRef);
            sorisaeSpeakingRef.current = false;
            sorisaeConversationRequestedRef.current = false;
            autoVoiceModeEnabledRef.current = false;
            setAutoVoiceModeEnabled(false);
            setGpsStatus(`🐦 ${aiDisplayName} 대화를 종료했습니다.`);
            return;
        }
        sorisaeConversationRequestedRef.current = true;
        autoVoiceModeEnabledRef.current = true;
        setAutoVoiceModeEnabled(true);
        setGpsStatus(`🐦 ${aiDisplayName} 대화 시작 · 말이 끝나면 자동으로 답해요`);
        voiceInputTargetRef.current = 'main';
        void runtimeAdapter.startVoiceInput({ autoMode: true });
    }, [
        aiDisplayName,
        autoVoiceModeEnabled,
        faceAiModeRef,
        recordingRef,
        setAutoVoiceModeEnabled,
        setFaceAiMode,
        setGpsStatus,
        sorisaeSpeakingRef,
        sorisaeVoicePlaybackSoundRef,
        runtimeAdapter,
        voiceInputTargetRef,
    ]);

    const closeSorisaeWindow = useCallback(async () => {
        if (recordingRef.current && voiceInputTargetRef.current === 'main') {
            await runtimeAdapter.stopVoiceInput({ suppressAutoRestart: true });
        }
        await runtimeAdapter.stopPlayback(sorisaeVoicePlaybackSoundRef);
        sorisaeSpeakingRef.current = false;
        sorisaeConversationRequestedRef.current = false;
        if (autoVoiceModeEnabled) {
            await runtimeAdapter.stopPlayback(faceVoicePlaybackSoundRef);
            autoVoiceModeEnabledRef.current = false;
            setAutoVoiceModeEnabled(false);
        }
        if (companionVoiceCallArmedRef.current) {
            if (companionVoiceCallRef.current.phase === 'awake') {
                companionVoiceCallRef.current = sleepCompanionVoiceCall(companionVoiceCallRef.current);
            }
            companionWakeRearmAtRef.current = Date.now() + 2_000;
        }
        sorisaeWindowOpenRef.current = false;
        faceAiModeRef.current = 'translate';
        setFaceAiMode('translate');
        setSorisaeWindowOpen(false);
    }, [
        autoVoiceModeEnabled,
        faceAiModeRef,
        faceVoicePlaybackSoundRef,
        recordingRef,
        setAutoVoiceModeEnabled,
        setFaceAiMode,
        setSorisaeWindowOpen,
        sorisaeSpeakingRef,
        sorisaeVoicePlaybackSoundRef,
        sorisaeWindowOpenRef,
        runtimeAdapter,
        voiceInputTargetRef,
    ]);

    const sorisaeWindowMicBootstrappedRef = useRef(false);
    const runtimeAdapterRef = useRef(runtimeAdapter);
    useEffect(() => { runtimeAdapterRef.current = runtimeAdapter; }, [runtimeAdapter]);

    useEffect(() => {
        sorisaeWindowOpenRef.current = sorisaeWindowOpen;
        if (!sorisaeWindowOpen) {
            sorisaeWindowMicBootstrappedRef.current = false;
            return;
        }
        // 창이 열린 뒤 startVoiceInput/stopVoiceInput 콜백 identity가 바뀔 때마다
        // effect가 재실행되며 녹음을 300ms마다 끊던 회귀를 edge-trigger 1회 부트스트랩으로 차단.
        if (sorisaeWindowMicBootstrappedRef.current) {
            return;
        }
        sorisaeWindowMicBootstrappedRef.current = true;
        sorisaeConversationRequestedRef.current = true;
        faceAiModeRef.current = 'gpt';
        setFaceAiMode('gpt');
        void (async () => {
            if (recordingRef.current && voiceInputTargetRef.current === 'main') {
                await runtimeAdapterRef.current.stopVoiceInput({ suppressAutoRestart: true });
            }
            void runtimeAdapterRef.current.stopPlayback(faceVoicePlaybackSoundRef);  // NOSONAR
            sorisaeSpeakingRef.current = false;
            voiceInputTargetRef.current = 'main';
            if (!autoVoiceModeEnabledRef.current) {
                autoVoiceModeEnabledRef.current = true;
                setAutoVoiceModeEnabled(true);
            }
            setGpsStatus(`🎙️ ${aiDisplayName} · 말씀하세요`);
            if (!recordingRef.current && !voiceInputStartInFlightRef.current) {
                void runtimeAdapterRef.current.startVoiceInput({ autoMode: true });
            } else {
                scheduleFaceConversationRestartRef.current(null);
            }
        })();
    }, [
        aiDisplayName,
        sorisaeWindowOpen,
        autoVoiceModeEnabledRef,
        faceAiModeRef,
        faceVoicePlaybackSoundRef,
        recordingRef,
        scheduleFaceConversationRestartRef,
        setAutoVoiceModeEnabled,
        setFaceAiMode,
        setGpsStatus,
        sorisaeSpeakingRef,
        sorisaeWindowOpenRef,
        voiceInputStartInFlightRef,
        voiceInputTargetRef,
    ]);

    useEffect(() => {
        if (!sorisaeWindowOpen || !sorisaeConversationRequestedRef.current || autoVoiceModeEnabled) {
            return;
        }
        const timer = setTimeout(() => {
            if (!sorisaeWindowOpenRef.current
                || !sorisaeConversationRequestedRef.current
                || autoVoiceModeEnabledRef.current
                || recordingRef.current
                || voiceInputStartInFlightRef.current
                || sorisaeSpeakingRef.current) {
                return;
            }
            autoVoiceModeEnabledRef.current = true;
            setAutoVoiceModeEnabled(true);
            voiceInputTargetRef.current = 'main';
            void runtimeAdapterRef.current.startVoiceInput({ autoMode: true });  // NOSONAR
        }, 900);
        return () => clearTimeout(timer);
    }, [
        autoVoiceModeEnabled,
        recordingRef,
        setAutoVoiceModeEnabled,
        sorisaeSpeakingRef,
        sorisaeWindowOpen,
        sorisaeWindowOpenRef,
        voiceInputStartInFlightRef,
        voiceInputTargetRef,
    ]);

    const wakeCompanionVoiceCallNow = useCallback(() => {
        if (faceScreenOpenRef.current) {
            console.log('[COMPANION_VOICE_CALL]', JSON.stringify({ event: 'wake_ignored_face_screen_open' }));
            return;
        }
        if (!companionVoiceCallArmedRef.current) {
            companionVoiceCallArmedRef.current = true;
            setCompanionVoiceCallArmed(true);
        }
        companionVoiceCallRef.current = wakeCompanionVoiceCall(companionVoiceCallRef.current, Date.now());
        companionWakeRearmAtRef.current = 0;
        faceAiModeRef.current = 'gpt';
        sorisaeWindowOpenRef.current = true;
        setFaceAiMode('gpt');
        setSorisaeWindowOpen(true);
        setGpsStatus(`🐦 ${aiDisplayName} 깨어났어요! 말씀하세요 · 3분 무응답이면 잠들어요`);
    }, [aiDisplayName, faceAiModeRef, faceScreenOpenRef, setFaceAiMode, setGpsStatus, setSorisaeWindowOpen, sorisaeWindowOpenRef]);
    useEffect(() => { wakeCompanionVoiceCallNowRef.current = wakeCompanionVoiceCallNow; }, [wakeCompanionVoiceCallNow]);

    const stopCompanionNativeKws = useCallback(async () => {
        companionKwsUnsubscribeRef.current?.();
        companionKwsUnsubscribeRef.current = null;
        companionKwsActiveRef.current = false;
        await stopOnDeviceKws();
    }, []);

    const resolveAvailableKwsModelPath = useCallback(async (preferredPath?: string): Promise<string> => {
        const candidates = [
            String(preferredPath || '').trim(),
            String(companionKwsModelPathRef.current || '').trim(),
            DEFAULT_COMPANION_KWS_MODEL_PATH,
            ...DEFAULT_VOSK_MODEL_DIR_CANDIDATES,
        ].filter((value, index, list) => value.length > 0 && list.indexOf(value) === index);

        for (const candidate of candidates) {
            try {
                const info = await FileSystem.getInfoAsync(candidate);
                if (info.exists && info.isDirectory) {
                    return candidate;
                }
            } catch {
                // try next candidate
            }
        }
        return '';
    }, []);

    const saveCompanionKwsSettings = useCallback(async ({
        provider,
        modelPath,
        porcupineAccessKey,
        porcupineKeywordPaths,
    }: {
        provider: OnDeviceKwsProvider;
        modelPath: string;
        porcupineAccessKey: string;
        porcupineKeywordPaths: string[];
    }) => {
        const normalizedModelPath = String(modelPath || '').trim();
        const normalizedPorcupineAccessKey = String(porcupineAccessKey || '').trim();
        const normalizedPorcupineKeywordPaths = (porcupineKeywordPaths || [])
            .map((path) => String(path || '').trim())
            .filter((path) => path.length > 0);
        const normalizedFirstKeywordPath = normalizedPorcupineKeywordPaths[0] || '';

        await AsyncStorage.multiSet([
            [COMPANION_KWS_PROVIDER_STORAGE_KEY, provider],
            [COMPANION_KWS_MODEL_PATH_STORAGE_KEY, normalizedModelPath],
            [COMPANION_KWS_PORCUPINE_ACCESS_KEY_STORAGE_KEY, normalizedPorcupineAccessKey],
            [COMPANION_KWS_PORCUPINE_KEYWORD_PATH_STORAGE_KEY, normalizedFirstKeywordPath],
            [COMPANION_KWS_PORCUPINE_KEYWORD_PATHS_STORAGE_KEY, JSON.stringify(normalizedPorcupineKeywordPaths)],
        ]);

        companionKwsProviderRef.current = provider;
        companionKwsModelPathRef.current = normalizedModelPath;
        companionKwsPorcupineAccessKeyRef.current = normalizedPorcupineAccessKey;
        companionKwsPorcupineKeywordPathsRef.current = normalizedPorcupineKeywordPaths;

        setCompanionKwsProvider(provider);
        setCompanionKwsModelPath(normalizedModelPath);
        setCompanionKwsPorcupineAccessKey(normalizedPorcupineAccessKey);
        setCompanionKwsPorcupineKeywordPaths(normalizedPorcupineKeywordPaths);

        if (companionVoiceCallArmedRef.current && !sorisaeWindowOpenRef.current) {
            await stopCompanionNativeKws();
            await startCompanionDormantListeningRef.current();
        }
    }, [sorisaeWindowOpenRef, stopCompanionNativeKws]);

    const startCompanionNativeKws = useCallback(async (): Promise<boolean> => {
        const logKwsSkip = (reason: string) => {
            console.log('[COMPANION_KWS]', JSON.stringify({ event: 'native_skip', reason }));
        };
        if (Platform.OS !== 'android' || !isOnDeviceKwsNativeAvailable()) {
            logKwsSkip('native_unavailable');
            return false;
        }
        const provider = companionKwsProviderRef.current;
        const configuredModelPath = String(companionKwsModelPathRef.current || DEFAULT_COMPANION_KWS_MODEL_PATH).trim();
        const modelPath = provider === 'vosk'
            ? await resolveAvailableKwsModelPath(configuredModelPath)
            : configuredModelPath;
        const porcupineAccessKey = String(companionKwsPorcupineAccessKeyRef.current || '').trim();
        const porcupineKeywordPaths = companionKwsPorcupineKeywordPathsRef.current
            .map((path) => String(path || '').trim())
            .filter((path) => path.length > 0);

        if (provider === 'vosk' && modelPath && modelPath !== companionKwsModelPathRef.current) {
            companionKwsModelPathRef.current = modelPath;
            setCompanionKwsModelPath(modelPath);
            AsyncStorage.setItem(COMPANION_KWS_MODEL_PATH_STORAGE_KEY, modelPath).catch((error) => {
                console.warn('[COMPANION_KWS] failed to persist model path', error);
            });
        }

        if (provider === 'vosk' && !modelPath) {
            logKwsSkip('missing_vosk_model_path');
            return false;
        }
        if (provider === 'porcupine' && (!porcupineAccessKey || porcupineKeywordPaths.length === 0)) {
            logKwsSkip('missing_porcupine_credentials');
            return false;
        }
        const supported = await probeOnDeviceKwsSupport();
        if (!supported) {
            logKwsSkip('probe_unsupported');
            return false;
        }
        await stopCompanionNativeKws();

        const unsubscribe = subscribeOnDeviceKwsEvents((event) => {
            if (event?.event !== 'wake') {
                if (event?.event === 'error' && event.message) {
                    console.log('[COMPANION_KWS]', JSON.stringify({
                        event: 'native_error',
                        message: event.message,
                    }));
                }
                return;
            }
            if (Date.now() < companionWakeRearmAtRef.current) {
                return;
            }
            if (faceScreenOpenRef.current) {
                console.log('[COMPANION_KWS]', JSON.stringify({
                    event: 'native_wake_ignored_face_screen_open',
                    keyword: event.keyword ?? '',
                    transcript: String(event.transcript ?? '').slice(0, 80),
                }));
                return;
            }
            console.log('[COMPANION_KWS]', JSON.stringify({
                event: 'native_wake',
                keyword: event.keyword ?? '',
                transcript: String(event.transcript ?? '').slice(0, 80),
            }));
            wakeCompanionVoiceCallNowRef.current();
            void stopCompanionNativeKws();  // NOSONAR
        });

        const aiName = resolveAiDisplayName(aiDisplayNameRef.current);
        const started = await startOnDeviceKws({
            provider,
            modelPath,
            accessKey: provider === 'porcupine' ? porcupineAccessKey : undefined,
            keywordPaths: provider === 'porcupine' ? porcupineKeywordPaths : undefined,
            sensitivities: provider === 'porcupine' ? porcupineKeywordPaths.map(() => 0.65) : undefined,
            keywords: [aiName, '소리새'],
            sampleRate: 16_000,
        });
        if (!started) {
            unsubscribe();
            logKwsSkip('native_start_failed');
            return false;
        }
        console.log('[COMPANION_KWS]', JSON.stringify({
            event: 'native_started',
            provider,
            has_model_path: modelPath.length > 0,
            keyword_path_count: porcupineKeywordPaths.length,
        }));
        companionKwsUnsubscribeRef.current = unsubscribe;
        companionKwsActiveRef.current = true;
        return true;
    }, [aiDisplayNameRef, faceScreenOpenRef, resolveAvailableKwsModelPath, stopCompanionNativeKws]);

    const startCompanionDormantListening = useCallback(async () => {
        const nativeStarted = await startCompanionNativeKws();
        if (nativeStarted) {
            if (recordingRef.current && voiceInputTargetRef.current === 'main') {
                await runtimeAdapter.stopVoiceInput({ suppressAutoRestart: true });
            }
            setAutoVoiceModeEnabled(false);
            const providerLabel = companionKwsProviderRef.current === 'porcupine' ? 'Porcupine' : 'Vosk';
            setGpsStatus(`🔔 온디바이스 호출 대기(${providerLabel}) · "${aiDisplayName}" 또는 "소리새"라고 부르면 깨어나요`);
            return;
        }
        voiceInputTargetRef.current = 'main';
        setAutoVoiceModeEnabled(true);
        if (!recordingRef.current) {
            void runtimeAdapter.startVoiceInput({ autoMode: true });
        }
        const provider = companionKwsProviderRef.current;
        const configHint = provider === 'vosk'
            ? 'Vosk 모델 경로 미설정으로 일반 듣기 모드로 대기합니다.'
            : '호출어 엔진 구성이 없어 일반 듣기 모드로 대기합니다.';
        setGpsStatus(`🔔 음성 호출 대기 중 · ${configHint} "${aiDisplayName}" 또는 "소리새"라고 부르면 깨어나요`);
    }, [
        aiDisplayName,
        recordingRef,
        setAutoVoiceModeEnabled,
        setGpsStatus,
        startCompanionNativeKws,
        runtimeAdapter,
        voiceInputTargetRef,
    ]);
    useEffect(() => { startCompanionDormantListeningRef.current = startCompanionDormantListening; }, [startCompanionDormantListening]);

    useEffect(() => () => {
        stopCompanionNativeKws().catch(() => {
            console.warn('[SORISAE_COMPANION] native KWS cleanup stop failed');
        });
    }, [stopCompanionNativeKws]);

    const setCompanionVoiceCallArmedState = useCallback(async (nextArmed: boolean) => {
        if (Platform.OS === 'web') {
            Alert.alert(aiDisplayName, `${aiDisplayName} 음성 호출은 모바일 앱에서 사용할 수 있습니다.`);
            return;
        }
        if (nextArmed === companionVoiceCallArmedRef.current) {
            return;
        }
        if (!nextArmed) {
            await stopCompanionNativeKws();
            companionVoiceCallRef.current = disarmCompanionVoiceCall(companionVoiceCallRef.current);
            companionVoiceCallArmedRef.current = false;
            setCompanionVoiceCallArmed(false);
            if (recordingRef.current && voiceInputTargetRef.current === 'main' && !sorisaeWindowOpenRef.current) {
                await runtimeAdapter.stopVoiceInput({ suppressAutoRestart: true });
                setAutoVoiceModeEnabled(false);
            }
            if (!sorisaeWindowOpenRef.current) {
                setGpsStatus(`🐦 ${aiDisplayName} 음성 호출 대기를 종료했습니다.`);
            }
            return;
        }
        companionVoiceCallRef.current = armCompanionVoiceCall(companionVoiceCallRef.current);
        companionVoiceCallArmedRef.current = true;
        setCompanionVoiceCallArmed(true);
        companionDormantSilent422StreakRef.current = 0;
        companionDormantRecoverBlockedUntilRef.current = 0;
        faceAiModeRef.current = 'translate';
        setFaceAiMode('translate');
        await startCompanionDormantListening();
    }, [
        aiDisplayName,
        faceAiModeRef,
        recordingRef,
        setAutoVoiceModeEnabled,
        setFaceAiMode,
        setGpsStatus,
        sorisaeWindowOpenRef,
        startCompanionDormantListening,
        stopCompanionNativeKws,
        runtimeAdapter,
        voiceInputTargetRef,
        companionDormantSilent422StreakRef,
        companionDormantRecoverBlockedUntilRef,
    ]);

    const handleToggleCompanionVoiceCall = useCallback(async () => {
        await setCompanionVoiceCallArmedState(!companionVoiceCallArmedRef.current);
    }, [setCompanionVoiceCallArmedState]);

    useEffect(() => {
        if (!sorisaeWindowOpen || !companionVoiceCallArmed) return undefined;
        const timer = setInterval(() => {
            if (!shouldCompanionVoiceCallSleep(companionVoiceCallRef.current, Date.now())) return;
            companionVoiceCallRef.current = sleepCompanionVoiceCall(companionVoiceCallRef.current);
            setGpsStatus(`😴 ${aiDisplayName}가 3분 무응답으로 잠들었어요 · 다시 부르면 깨어나요`);
            void closeSorisaeWindow();
        }, 15_000);
        return () => clearInterval(timer);
    }, [aiDisplayName, closeSorisaeWindow, companionVoiceCallArmed, setGpsStatus, sorisaeWindowOpen]);

    return {
        handleToggleSorisaeConversation,
        closeSorisaeWindow,
        wakeCompanionVoiceCallNowRef,
        startCompanionDormantListeningRef,
        companionVoiceCallArmed,
        companionVoiceCallArmedRef,
        companionVoiceCallRef,
        companionKwsActiveRef,
        companionWakeRearmAtRef,
        companionDormantSilent422StreakRef,
        companionDormantRecoverBlockedUntilRef,
        companionKwsProvider,
        companionKwsModelPath,
        companionKwsPorcupineAccessKey,
        companionKwsPorcupineKeywordPaths,
        saveCompanionKwsSettings,
        handleToggleCompanionVoiceCall,
        setCompanionVoiceCallArmedState,
        stopCompanionNativeKws,
        setCompanionVoiceCallArmed,
    };
}
