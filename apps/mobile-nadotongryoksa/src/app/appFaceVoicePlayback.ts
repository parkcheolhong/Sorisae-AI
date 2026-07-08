// App.tsx 에서 분리한 대면통역 오디오 출력(서버 뉴럴 TTS → 디바이스 TTS 폴백).
import type React from 'react';
import * as Speech from 'expo-speech';
import * as FileSystem from 'expo-file-system/legacy';
import { Audio, type AudioSound } from '../compat/expoAvAudio';
import { synthesizeSpeech } from '../api/translate';
import { normalizeSpeakText, inferTtsLanguage } from '../features/tts/ttsText';
import { LANGS, type LangCode } from '../features/language/languageCatalog';
import { FEATURE_IDS } from '../features/correlation/correlationId';
import { API_BASE } from './appConstants';
import { computeFaceTtsSafetyCapMs } from '../features/face-interpretation/faceConversationTiming';
import {
    disableFaceConversationAudio,
    enableFaceConversationPlaybackAudio,
} from '../features/face-interpretation/faceConversationAudioRoute';
import { isVoipSessionActive } from '../services/voipSessionGuard';
import { speakDeviceTextInstant } from '../utils/instantDeviceSpeech';

export async function stopFaceVoicePlayback(playbackSoundRef: React.MutableRefObject<AudioSound | null>): Promise<void> {
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

export async function playFaceTranslationOutput(options: {
    translatedText: string;
    targetLang: LangCode;
    audioBase64?: string | null;
    audioFormat?: string | null;
    apiBaseUrl?: string;
    playbackSoundRef: React.MutableRefObject<AudioSound | null>;
    preferInstantDeviceSpeech?: boolean;
    // V.2 ID 백본 — 대면 통역도 동일 상관 ID로 기능 ID 자동 매핑→셀프 서빙→전송→음성 발화를 자동 연결한다.
    correlationId?: string;
}): Promise<void> {
    const speakText = normalizeSpeakText(options.translatedText);
    if (!speakText) return;

    // VoIP 통화 중에는 대면통역/소리새가 오디오 모드를 다시 건드리지 않도록 즉시 차단한다.
    if (isVoipSessionActive()) {
        console.log('[FACE_TTS]', JSON.stringify({ event: 'skip_voip_session_active', target: options.targetLang }));
        return;
    }

    await stopFaceVoicePlayback(options.playbackSoundRef);
    Speech.stop();

    const lang = LANGS.find((item) => item.code === options.targetLang);
    const fallbackTts = lang?.tts ?? 'ko-KR';
    // 발화 로케일은 SSOT(inferTtsLanguage)로 결정 — 지정 타깃 언어 로케일을 신뢰하고
    // 단일 언어 전용 스크립트로 번역문이 샌 경우에만 교정한다(50개국 정확 발화).
    const detectedTts = inferTtsLanguage(speakText, fallbackTts);
    const deviceRate = detectedTts.startsWith('ko') || detectedTts.startsWith('ja') ? 0.97 : 1.0;
    // 안전 상한(safety cap): onDone이 끝까지 책임지게 하고, 타임아웃은 onDone이
    // 영영 안 올 때만 쓰는 넉넉한 상한이어야 한다. 과거엔 length*70ms로 너무 짧게 잡아
    // 실제 TTS가 더 길 때 타임아웃이 먼저 끝나 → 듣기가 재개되어 TTS 꼬리를 다시 녹음(에코)했다.
    const safetyCapMs = computeFaceTtsSafetyCapMs(speakText.length);

    try {
        await enableFaceConversationPlaybackAudio();
    } catch {
        // no-op
    }

    try {
        await Audio.setAudioModeAsync({
            allowsRecordingIOS: false,
            playsInSilentModeIOS: true,
            // 녹음 duck 과 겹치면 스피커 출력이 순간 끊기는 증상이 난다(소리새 TTS 끊김).
            shouldDuckAndroid: false,
            playThroughEarpieceAndroid: false,
        });
    } catch {
        // no-op
    }

    if (options.preferInstantDeviceSpeech) {
        console.log('[FACE_TTS]', JSON.stringify({
            event: 'played',
            delivery: 'device_speech_instant',
            locale: detectedTts,
            target: options.targetLang,
        }));
        await speakDeviceTextInstant({
            text: speakText,
            language: detectedTts,
            rate: deviceRate,
            shouldDuckAndroid: false,
            playThroughEarpieceAndroid: false,
        });
        await disableFaceConversationAudio().catch(() => { /* no-op */ });
        return;
    }

    // 우선순위 1: 서버 뉴럴 TTS(Edge neural). 단말 음성팩 의존을 제거해 50개국 일관 발음·
    // 자연스러운 톤을 보장한다(라틴어권=영어, 한자=중국어 같은 단말 음성팩 한계 회피).
    // 릴레이로 이미 오디오가 왔으면 그걸 쓰고, 없으면 대상 언어로 직접 합성 요청. 실패 시 디바이스 TTS 폴백.
    // 명시적 null(null/null)은 서버 합성을 건너뛰고 단말 발화를 우선하라는 신호다.
    const bypassServerSynthesis = options.audioBase64 === null && options.audioFormat === null;
    let serverAudioBase64: string | undefined = bypassServerSynthesis
        ? undefined
        : (options.audioBase64 && String(options.audioFormat || '').startsWith('audio/')
            ? options.audioBase64
            : undefined);
    let serverAudioFormat: string | undefined = serverAudioBase64
        ? String(options.audioFormat)
        : undefined;
    if (!bypassServerSynthesis && !serverAudioBase64) {
        try {
            // 가이드 답변(40s+) 합성·다운로드까지 여유(30s).
            const synth = await synthesizeSpeech(
                speakText,
                options.targetLang,
                options.apiBaseUrl ?? API_BASE,
                30_000,
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
                let sawLoaded = false;
                sound.setOnPlaybackStatusUpdate((status) => {
                    if (status.isLoaded) {
                        sawLoaded = true;
                        if (status.didJustFinish) {
                            clearTimeout(failsafe);
                            resolve();
                        }
                        return;
                    }
                    // isLoaded=false 는 일시 버퍼링/상태 글리치일 수 있다.
                    // 여기서 resolve 하면 재생이 아직 끝나지 않았는데 마이크가 재개되어
                    // 소리새 발화가 중간에 끊기거나 자기 음성을 다시 주워 환청 루프가 생길 수 있다.
                    // didJustFinish 또는 failsafe 만 종료 신호로 인정한다.
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
                    rate: deviceRate,
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

    try {
        await disableFaceConversationAudio();
    } catch {
        // no-op
    }
}
