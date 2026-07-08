// 채팅 마이크 입력 훅: 녹음 → 서버 STT(voiceTranslate.original_text) → 입력칸 채움.
// - 수동 모드: 토글 한 번이면 녹음 시작, 다시 누르면 정지 후 인식 → onTranscript 로 결과 전달.
// - 핸즈프리(연속) 모드: 마이크를 켜두고 말이 끝나면(무음 감지) 자동으로 인식한 뒤 곧바로 다시
//   듣기 시작한다. 매 발화마다 마이크를 다시 누를 필요가 없다(소리새 자동 대화와 동일한 UX).
// - 부수효과(녹음/파일/네트워크)만 담당하고, 결정 로직은 chatVoiceInput.ts 순수 헬퍼를 재사용한다.
import { useCallback, useEffect, useRef, useState } from 'react';

import { Audio, type AudioRecording } from '../../compat/expoAvAudio';
import FileSystem from '../../compat/expoLegacyFileSystem';
import { voiceTranslate } from '../../api/translate';
import {
    cleanVoiceTranscript,
    isVoiceAudioLongEnough,
    resolveVoiceSttLangs,
} from './chatVoiceInput';

export type ChatVoiceInputStatus = 'idle' | 'recording' | 'transcribing';

export interface UseChatVoiceInputResult {
    status: ChatVoiceInputStatus;
    error: string | null;
    handsFree: boolean;
    toggle: () => void;
    toggleHandsFree: () => void;
    cancel: () => void;
}

// 검증된 대면/VoIP 통역 캡처와 동일한 16kHz 모노 m4a — Whisper STT 정확도 SSOT.
// isMeteringEnabled: 핸즈프리 무음 감지를 위해 입력 레벨(dBFS) 미터링을 켠다.
const RECORDING_OPTIONS = {
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
    web: { mimeType: 'audio/webm', bitsPerSecond: 128_000 },
};

// 핸즈프리 무음 기반 VAD 튜닝(단말 미터링 dBFS 기준, 음수일수록 조용함).
const HANDS_FREE = {
    pollMs: 150,            // 미터링 폴링 주기
    speechDb: -40,          // 이 레벨보다 크면 '발화 중'으로 간주
    silenceDb: -50,         // 이 레벨 이하가 유지되면 '무음'으로 간주
    silenceHoldMs: 1100,    // 발화 후 무음이 이만큼 지속되면 한 문장 종료로 컷
    minSpeechMs: 350,       // 너무 짧은 잡음은 무시
    maxUtteranceMs: 12_000, // 한 발화 최대 길이(안전 상한)
};

export function useChatVoiceInput(
    selfLang: string | null | undefined,
    counterpartLang: string | null | undefined,
    onTranscript: (text: string) => void,
    // [설정 SSOT] 전역 "채팅 자동 듣기"가 켜져 있으면 채팅방 진입 시 핸즈프리 루프를 자동 시작한다.
    autoStartHandsFree = false,
): UseChatVoiceInputResult {
    const [status, setStatus] = useState<ChatVoiceInputStatus>('idle');
    const [error, setError] = useState<string | null>(null);
    const [handsFree, setHandsFree] = useState(false);
    const recordingRef = useRef<AudioRecording | null>(null);
    const cancelledRef = useRef(false);
    const aliveRef = useRef(true);
    const handsFreeRef = useRef(false);
    const handsFreeLoopActiveRef = useRef(false);
    // 핸즈프리를 누가 시작했는지 추적: 'auto'(전역 자동듣기 설정) | 'manual'(사용자 토글) | null(정지).
    // → 자동듣기 설정을 끄면 'auto' 로 시작된 루프만 따라서 정지하고, 사용자가 직접 켠 루프는 건드리지 않는다.
    const handsFreeSourceRef = useRef<'auto' | 'manual' | null>(null);
    // 콜백/STT가 항상 최신 언어를 쓰도록 ref 미러링(핸즈프리 루프가 오래 살아있어도 안전).
    const langRef = useRef({ selfLang, counterpartLang });
    const onTranscriptRef = useRef(onTranscript);
    useEffect(() => { langRef.current = { selfLang, counterpartLang }; }, [selfLang, counterpartLang]);
    useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);

    useEffect(() => {
        aliveRef.current = true;
        return () => {
            aliveRef.current = false;
            handsFreeRef.current = false;
            const recording = recordingRef.current;
            recordingRef.current = null;
            if (recording) {
                recording.stopAndUnloadAsync().catch(() => { /* no-op */ });
            }
        };
    }, []);

    // 녹음 파일을 서버 STT로 보내 텍스트를 얻는다(수동/핸즈프리 공용). 반환: 인식 텍스트 또는 null.
    const transcribe = useCallback(async (uri: string): Promise<string | null> => {
        const base64Audio = await FileSystem.readAsStringAsync(uri, {
            encoding: FileSystem.EncodingType.Base64,
        });
        if (!isVoiceAudioLongEnough(base64Audio)) {
            return null;
        }
        const { selfLang: sLang, counterpartLang: cLang } = langRef.current;
        const { from, to, langA, langB, mode } = resolveVoiceSttLangs(sLang, cLang);
        const result = await voiceTranslate(base64Audio, from, to, undefined, mode === 'bilingual' ? 'auto' : from, {
            deviceTts: false,
            mode,
            langA,
            langB,
        });
        return cleanVoiceTranscript(result.original_text);
    }, []);

    const start = useCallback(async () => {
        setError(null);
        try {
            const permission = await Audio.requestPermissionsAsync();
            if (!permission.granted) {
                if (aliveRef.current) {
                    setError('마이크 권한이 필요합니다.');
                }
                return;
            }
            await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
            cancelledRef.current = false;
            const { recording } = await Audio.Recording.createAsync(RECORDING_OPTIONS);
            recordingRef.current = recording;
            if (aliveRef.current) {
                setStatus('recording');
            }
        } catch {
            recordingRef.current = null;
            if (aliveRef.current) {
                setError('녹음을 시작할 수 없습니다.');
                setStatus('idle');
            }
        }
    }, []);

    const finalize = useCallback(async () => {
        const recording = recordingRef.current;
        recordingRef.current = null;
        if (!recording) {
            if (aliveRef.current) {
                setStatus('idle');
            }
            return;
        }

        let uri: string | null = null;
        try {
            await recording.stopAndUnloadAsync();
            uri = recording.getURI();
        } catch {
            uri = null;
        }

        const cleanup = () => {
            if (uri) {
                FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
            }
        };

        if (cancelledRef.current || !uri) {
            cleanup();
            if (aliveRef.current) {
                setStatus('idle');
            }
            return;
        }

        if (aliveRef.current) {
            setStatus('transcribing');
        }
        try {
            const text = await transcribe(uri);
            if (text) {
                onTranscriptRef.current(text);
            } else if (aliveRef.current) {
                setError('녹음이 너무 짧거나 음성을 인식하지 못했습니다.');
            }
        } catch (e) {
            const message = e instanceof Error ? e.message : String(e);
            console.warn('[CHAT_VOICE_STT_FAIL]', message);
            if (aliveRef.current) {
                // 서버가 "음성이 감지되지 않았습니다"(422) 등 구체 메시지를 주면 그대로 노출해 진단 가능.
                setError(message && message.length <= 60 ? message : '음성 인식에 실패했습니다. 다시 시도해 주세요.');
            }
        } finally {
            cleanup();
            if (aliveRef.current) {
                setStatus('idle');
            }
        }
    }, [transcribe]);

    // 핸즈프리 한 발화 캡처: 녹음 시작 → 무음/최대길이 감지 시 정지 → uri 반환(없으면 null).
    const captureUtterance = useCallback(async (): Promise<string | null> => {
        await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
        const { recording } = await Audio.Recording.createAsync(RECORDING_OPTIONS);
        recordingRef.current = recording;
        if (aliveRef.current) setStatus('recording');

        const startedAt = Date.now();
        let firstSpeechAt: number | null = null;
        let lastVoiceAt = 0;

        // 무음/최대길이까지 폴링.
        // eslint-disable-next-line no-constant-condition
        while (true) {
            await new Promise((resolve) => setTimeout(resolve, HANDS_FREE.pollMs));
            if (!handsFreeRef.current || !aliveRef.current || cancelledRef.current) break;
            let metering = -160;
            let durationMillis = Date.now() - startedAt;
            try {
                const st = await recording.getStatusAsync();
                if (typeof st.metering === 'number') metering = st.metering;
                if (typeof st.durationMillis === 'number') durationMillis = st.durationMillis;
            } catch {
                // 상태 조회 실패 시 다음 폴링에서 재시도.
            }
            const now = Date.now();
            if (metering > HANDS_FREE.speechDb) {
                if (firstSpeechAt == null) firstSpeechAt = now;
                lastVoiceAt = now;
            }
            const hadSpeech = firstSpeechAt != null && (lastVoiceAt - firstSpeechAt) >= 0;
            const silenceElapsed = lastVoiceAt > 0 && (now - lastVoiceAt) >= HANDS_FREE.silenceHoldMs;
            const longEnough = firstSpeechAt != null && (now - firstSpeechAt) >= HANDS_FREE.minSpeechMs;
            if (hadSpeech && longEnough && silenceElapsed) break;       // 자연스러운 문장 끝 컷
            if (durationMillis >= HANDS_FREE.maxUtteranceMs) break;     // 최대 길이 컷
        }

        recordingRef.current = null;
        let uri: string | null = null;
        try {
            await recording.stopAndUnloadAsync();
            uri = recording.getURI();
        } catch {
            uri = null;
        }
        // 발화가 한 번도 감지되지 않았으면(대기 중 종료/무음) STT 호출 없이 폐기.
        if (firstSpeechAt == null) {
            if (uri) FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
            return null;
        }
        return uri;
    }, []);

    const runHandsFreeLoop = useCallback(async () => {
        if (handsFreeLoopActiveRef.current) return;
        handsFreeLoopActiveRef.current = true;
        try {
            const permission = await Audio.requestPermissionsAsync();
            if (!permission.granted) {
                if (aliveRef.current) setError('마이크 권한이 필요합니다.');
                handsFreeRef.current = false;
                if (aliveRef.current) setHandsFree(false);
                return;
            }
            cancelledRef.current = false;
            while (handsFreeRef.current && aliveRef.current) {
                let uri: string | null = null;
                try {
                    uri = await captureUtterance();
                } catch {
                    uri = null;
                }
                if (!handsFreeRef.current || !aliveRef.current) {
                    if (uri) FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
                    break;
                }
                if (!uri) {
                    // 무음만 있었으면 곧바로 다시 듣기(마이크는 계속 연결 상태 유지).
                    if (aliveRef.current) setStatus('recording');
                    continue;
                }
                if (aliveRef.current) setStatus('transcribing');
                try {
                    const text = await transcribe(uri);
                    if (text) {
                        onTranscriptRef.current(text);
                        if (aliveRef.current) setError(null);
                    }
                } catch (e) {
                    const message = e instanceof Error ? e.message : String(e);
                    console.warn('[CHAT_VOICE_STT_FAIL]', message);
                    if (aliveRef.current) {
                        setError(message && message.length <= 60 ? message : '음성 인식에 실패했습니다. 계속 듣는 중…');
                    }
                } finally {
                    FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
                }
            }
        } finally {
            handsFreeLoopActiveRef.current = false;
            recordingRef.current = null;
            if (aliveRef.current) setStatus('idle');
        }
    }, [captureUtterance, transcribe]);

    // 핸즈프리 정지 SSOT: 루프 종료 플래그 + 진행 중 녹음 정지. 정지/취소/자동듣기 OFF 가 모두 재사용.
    const stopHandsFree = useCallback(() => {
        handsFreeRef.current = false;
        handsFreeSourceRef.current = null;
        setHandsFree(false);
        cancelledRef.current = true;
        const recording = recordingRef.current;
        recordingRef.current = null;
        if (recording) {
            recording.stopAndUnloadAsync().catch(() => { /* no-op */ });
        }
    }, []);

    const toggleHandsFree = useCallback(() => {
        if (handsFreeRef.current) {
            stopHandsFree();
            return;
        }
        // [버그 수정] 수동 녹음 중 전환 시 경합 제거: 과거엔 finalize()를 fire-and-forget 한 뒤
        // 곧바로 runHandsFreeLoop()가 새 녹음을 createAsync 해서 두 녹음이 겹치고 recordingRef 가
        // 덮어써졌다. → finalize()(정지·언로드 완료)를 await 한 뒤 핸즈프리 루프를 시작한다.
        const begin = () => {
            setError(null);
            handsFreeRef.current = true;
            handsFreeSourceRef.current = 'manual';
            setHandsFree(true);
            void runHandsFreeLoop();
        };
        if (status === 'recording') {
            cancelledRef.current = true;
            void (async () => {
                await finalize();
                if (!aliveRef.current) return;
                begin();
            })();
            return;
        }
        begin();
    }, [status, finalize, runHandsFreeLoop, stopHandsFree]);

    // 전역 설정으로 자동 듣기가 켜져 있으면 마운트 직후(또는 설정 ON 전환 시) 핸즈프리를 1회 자동 시작.
    const autoStartedRef = useRef(false);
    useEffect(() => {
        if (!autoStartHandsFree) {
            // [버그 수정] 자동듣기 설정을 끄면, 자동으로 시작했던 핸즈프리 루프도 실제로 정지해야 한다.
            // (과거엔 플래그만 리셋하고 루프는 계속 돌아 마이크가 켜진 채 desync 됐다.)
            // 단, 사용자가 직접 켠('manual') 루프는 설정 변경으로 끄지 않는다.
            autoStartedRef.current = false;
            if (handsFreeRef.current && handsFreeSourceRef.current === 'auto') {
                stopHandsFree();
            }
            return;
        }
        if (autoStartedRef.current || handsFreeRef.current) return;
        autoStartedRef.current = true;
        setError(null);
        handsFreeRef.current = true;
        handsFreeSourceRef.current = 'auto';
        setHandsFree(true);
        void runHandsFreeLoop();
    }, [autoStartHandsFree, runHandsFreeLoop, stopHandsFree]);

    const toggle = useCallback(() => {
        if (handsFreeRef.current) {
            // 핸즈프리가 켜져 있으면 일반 토글은 핸즈프리 종료로 동작.
            toggleHandsFree();
            return;
        }
        if (status === 'recording') {
            void finalize();
        } else if (status === 'idle') {
            void start();  // NOSONAR
        }
    }, [status, start, finalize, toggleHandsFree]);

    const cancel = useCallback(() => {
        cancelledRef.current = true;
        handsFreeRef.current = false;
        handsFreeSourceRef.current = null;
        setHandsFree(false);
        if (status === 'recording') {
            void finalize();
        }
    }, [status, finalize]);

    return { status, error, handsFree, toggle, toggleHandsFree, cancel };
}
