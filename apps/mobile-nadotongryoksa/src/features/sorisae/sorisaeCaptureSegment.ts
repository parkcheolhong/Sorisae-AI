/**
 * 소리새·웨이크워드(dormant) 경로 — STT 세그먼트 처리 헬퍼.
 * App.tsx / useVoiceCaptureLoop 공용.
 */
import type { MutableRefObject } from 'react';
import type { AudioSound } from '../../compat/expoAvAudio';
import type { LangCode } from '../language/languageCatalog';

import {
    FACE_CONVERSATION_ECHO_GUARD_MS,
    FACE_CONVERSATION_PLAYBACK_DRAIN_MS,
    FACE_CONVERSATION_SPOKEN_HISTORY,
} from '../shared/audioConversationTiming';
import { createEmptyPersona, setPreferredName, type CompanionPersona } from './companionMemory';
import { parseCompanionCommand } from './companionCommands';
import { matchCompanionWakeWord, markCompanionVoiceCallActivity, type CompanionVoiceCallState } from './companionVoiceCall';
import { saveCompanionTripSessionId } from './companionTripSessionStore';
import { normalizeEchoText, echoOverlapRatio } from './sorisaeEcho';
import type { SorisaeMapContext, SorisaeQaEntry } from './types';
import type { playFaceTranslationOutput } from '../../app/appFaceVoicePlayback';

export type DormantSilenceBackoffRefs = {
    streakRef: MutableRefObject<number>;
    blockedUntilRef: MutableRefObject<number>;
};

export function isDormantSilenceLoop(params: {
    sorisaeWindowOpen: boolean;
    activeVoiceInputTarget: string;
    companionKwsActive: boolean;
    companionPhase: CompanionVoiceCallState['phase'];
}): boolean {
    return !params.sorisaeWindowOpen
        && params.activeVoiceInputTarget === 'main'
        && !params.companionKwsActive
        && params.companionPhase === 'dormant';
}

/**
 * dormant 웨이크 스캔 최소 길이.
 * 너무 길면 짧은 호출어("소리새")가 지속적으로 버려져 대기 감지가 둔해진다.
 */
export const COMPANION_DORMANT_MIN_SEGMENT_MS = 1700;
/**
 * 소리새 홈 Q&A 최소 세그먼트.
 * 지나치게 큰 값은 질문 자체가 서버 STT/TTS 경로에 오르기 전에 드롭되는 회귀를 만든다.
 * 소리새 전용 안정 경계와 같은 컷오프로 맞춰 짧은 질문도 응답 발화까지 이어지게 한다.
 */
export const SORISAE_WINDOW_MIN_SEGMENT_MS = 1700;
// 6초 안팎의 자연 질문은 Silero miss 단말에서도 살려야 한다.
// 너무 낮은 상한(5s)은 정상 질문까지 전송 전 단계에서 버린다.
export const SORISAE_WINDOW_SILERO_MISS_MAX_UPLOAD_MS = 8000;
export const FACE_CONTEXT_SESSION_GAP_MS = 18_000;

/** expo m4a 빈/손상 업로드 차단 — VoIPCallScreen VOICE_RELAY_MIN_AUDIO_BASE64_LEN 과 동일. */
export const SORISAE_MIN_AUDIO_BASE64_LEN = 3_500;

export function shouldDeferSorisaeSegmentStop(params: {
    sorisaeWindowOpen: boolean;
    mainSorisaeRoute: boolean;
    segmentDurationMs: number;
}): boolean {
    return params.sorisaeWindowOpen
        && params.mainSorisaeRoute
        && params.segmentDurationMs > 0
        && params.segmentDurationMs < SORISAE_WINDOW_MIN_SEGMENT_MS;
}

export function shouldSkipSorisaeSegmentUpload(params: {
    segmentDurationMs: number;
    audioBase64Len: number;
}): { skip: boolean; reason?: string } {
    if (params.segmentDurationMs > 0 && params.segmentDurationMs < SORISAE_WINDOW_MIN_SEGMENT_MS) {
        return { skip: true, reason: 'segment_too_short' };
    }
    if (params.audioBase64Len < SORISAE_MIN_AUDIO_BASE64_LEN) {
        return { skip: true, reason: 'audio_too_small' };
    }
    return { skip: false };
}

/** 422·STT 무음 400은 자동 듣기 루프가 계속되도록 UI 경고를 띄우지 않는다. */
export function isRecoverableVoiceCaptureHttpError(status: number, detail: string): boolean {
    if (status === 422) {
        return true;
    }
    if (status !== 400) {
        return false;
    }
    const msg = detail.toLowerCase();
    return (
        msg.includes('stt')
        || msg.includes('음성')
        || msg.includes('녹음')
        || msg.includes('no speech')
        || msg.includes('no stt')
    );
}

/**
 * dormant 웨이크 스캔: Silero speech_start가 없어도 file-growth VAD·RMS로 실제 발화면 업로드한다.
 * (SM-T225N 등 Silero·file VAD 불일치 단말에서 "소리새" 호명이 전송 전에 버려지는 회귀 방지)
 */
export function shouldUploadDormantWakeSegment(params: {
    sileroHadSpeech: boolean;
    fileVadHadSpeech: boolean;
    rmsDb?: number;
}): boolean {
    if (params.sileroHadSpeech) {
        return true;
    }
    if (params.fileVadHadSpeech) {
        return true;
    }
    return typeof params.rmsDb === 'number' && params.rmsDb > -50;
}

/**
 * 소리새 창 Q&A — Silero·file VAD 불일치 단말에서도 발화를 서버 STT로 넘긴다.
 * (dormant 웨이크보다 관대: 창을 연 상태면 사용자 발화를 버리지 않는다.)
 */
export function shouldUploadSorisaeWindowSegment(params: {
    sileroHadSpeech: boolean;
    fileVadHadSpeech: boolean;
    rmsDb?: number;
    durationMs?: number;
}): boolean {
    if (params.sileroHadSpeech) {
        return true;
    }
    const durationMs = typeof params.durationMs === 'number' ? params.durationMs : 0;
    // Silero speech_start 없이 길게 열린 세그먼트는 meter-dead/file-growth 오탐일 가능성이 높다.
    // 소리새 창에서는 이런 장시간 fallback 업로드를 막아 자연어 오인식과 422 왕복을 줄인다.
    if (durationMs >= SORISAE_WINDOW_SILERO_MISS_MAX_UPLOAD_MS) {
        return false;
    }
    if (params.fileVadHadSpeech) {
        return true;
    }
    // 녹음 길이만으로 업로드 금지 — max_duration 무음 10초가 Whisper 환각→422 루프를 만든다.
    if (typeof params.rmsDb === 'number' && params.rmsDb > -56) {
        return true;
    }
    return false;
}

/**
 * 대면 통역(face) 자동 듣기 경로.
 * Silero speech_start 가 누락된 meter-dead 단말에서도 file-growth VAD 또는 RMS가 발화를 가리키면
 * 서버 STT로 세그먼트를 올린다. 그렇지 않으면 정상 발화가 업로드 전 단계에서 조용히 버려진다.
 */
export function shouldUploadFaceConversationSegment(params: {
    sileroHadSpeech: boolean;
    fileVadHadSpeech: boolean;
    rmsDb?: number;
    faceFileSpeechRmsDb: number;
}): boolean {
    if (params.sileroHadSpeech) {
        return true;
    }
    if (params.fileVadHadSpeech) {
        return true;
    }
    return typeof params.rmsDb === 'number' && params.rmsDb > params.faceFileSpeechRmsDb;
}

export function shouldContinueFaceConversationContext(params: {
    nowMs: number;
    lastTurnAtMs: number;
    fromLang: string;
    toLang: string;
    lastFromLang?: string | null;
    lastToLang?: string | null;
}): boolean {
    if (!params.lastTurnAtMs || params.lastTurnAtMs <= 0) {
        return false;
    }
    if (params.nowMs - params.lastTurnAtMs > FACE_CONTEXT_SESSION_GAP_MS) {
        return false;
    }
    return params.fromLang === params.lastFromLang && params.toLang === params.lastToLang;
}

export function applyDormantSilenceBackoff(
    refs: DormantSilenceBackoffRefs,
    source: string,
): void {
    const nextStreak = Math.min(8, refs.streakRef.current + 1);
    refs.streakRef.current = nextStreak;
    const backoffMs = Math.min(12_000, 1200 + (nextStreak * 900));
    refs.blockedUntilRef.current = Date.now() + backoffMs;
    console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
        event: 'dormant_silence_backoff',
        streak: nextStreak,
        backoff_ms: backoffMs,
        source,
    }));
}

export type CompanionDormantScanResult = 'wake' | 'idle' | 'continue';

/** dormant 스캔 모드에서 웨이크워드·유휴 소비 처리. */
export function handleCompanionDormantScan(params: {
    transcript: string;
    sttTrust: string;
    aiDisplayName: string;
    faceScreenOpen: boolean;
    wakeRearmAtMs: number;
    onWake: () => void;
    onScheduleRestart: () => void;
}): CompanionDormantScanResult {
    if (Date.now() < params.wakeRearmAtMs) {
        console.log('[COMPANION_VOICE_CALL]', JSON.stringify({ event: 'scan_guard_after_close' }));
        params.onScheduleRestart();
        return 'idle';
    }
    if (params.transcript && matchCompanionWakeWord(params.transcript, params.aiDisplayName)) {
        console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
            event: 'wake',
            stt_trust: params.sttTrust,
            transcript: params.transcript.slice(0, 60),
        }));
        params.onWake();
        params.onScheduleRestart();
        return 'wake';
    }
    if (!params.faceScreenOpen) {
        console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
            event: 'scan_idle',
            transcript: params.transcript.slice(0, 40),
        }));
        params.onScheduleRestart();
        return 'idle';
    }
    return 'continue';
}

export type FriendChatTurnContext = {
    transcript: string;
    data: Record<string, unknown>;
    profileLang: string;
    aiDisplayName: string;
    userId?: number;
    faceCorrelationId: string;
    apiBaseUrl: string;
    companionVoiceCallRef: MutableRefObject<CompanionVoiceCallState>;
    faceGptSpokenEchoRef: MutableRefObject<Array<{ text: string; atMs: number }>>;
    faceGptConversationRef: MutableRefObject<Array<{ role: string; content: string }>>;
    companionPersonaRef: MutableRefObject<CompanionPersona>;
    companionTripSessionIdRef: MutableRefObject<string | null>;
    sorisaeQaSeqRef: MutableRefObject<number>;
    sorisaeSpeakingRef: MutableRefObject<boolean>;
    setSorisaeSpeakingUi?: (speaking: boolean) => void;
    sorisaeVoicePlaybackSoundRef: MutableRefObject<{ unloadAsync?: () => Promise<void> } | null>;
    setGpsStatus: (msg: string) => void;
    setTourismSafetyBanner: (banner: { message: string; highRiskBlocked: boolean } | null) => void;
    setItinerarySeedQuery: (q: string) => void;
    bumpItinerarySeedNonce: () => void;
    setSorisaeQaLog: (updater: (prev: SorisaeQaEntry[]) => SorisaeQaEntry[]) => void;
    onScheduleRestart: () => void;
    normalizeDetectedLangCode: (code: unknown) => string | null;
    inferSpeechLangCode: (text: string, fallback: string) => string;
    normalizeSpeakText: (text: string) => string;
    isTravelItineraryIntent: (text: string) => boolean;
    playFaceTranslationOutput: typeof playFaceTranslationOutput;
    reportFaceVoiceAutoTuningMetric: (opts: { playbackMs?: number; overlapDetected?: boolean; roundtripMs?: number }) => void;
    recordPersonaTurn: (opts: { transcript: string; answer: string; language: string }) => Promise<CompanionPersona>;
    resetPersonaStore: () => Promise<void>;
    persistPersona: (persona: CompanionPersona) => Promise<boolean>;
};

/** friend-chat 응답 1턴 처리. handled=false면 self-echo로 스킵됨. */
export async function processSorisaeFriendChatTurn(
    ctx: FriendChatTurnContext,
): Promise<{ handled: boolean; playbackPromise: Promise<void> | null }> {
    const { transcript } = ctx;
    if (ctx.companionVoiceCallRef.current.phase === 'awake') {
        ctx.companionVoiceCallRef.current = markCompanionVoiceCallActivity(
            ctx.companionVoiceCallRef.current,
            Date.now(),
        );
    }

    const echoNowMs = Date.now();
    const normIncoming = normalizeEchoText(transcript);
    const recentSpokenEcho = ctx.faceGptSpokenEchoRef.current.filter(
        (e) => echoNowMs - e.atMs < FACE_CONVERSATION_ECHO_GUARD_MS,
    );
    ctx.faceGptSpokenEchoRef.current = recentSpokenEcho;
    const isSelfEcho = normIncoming.length >= 4
        && recentSpokenEcho.some((e) => echoOverlapRatio(e.text, normIncoming) >= 0.7);
    if (isSelfEcho) {
        console.log('[FACE_CONVERSATION]', JSON.stringify({
            event: 'gpt_self_echo_skip',
            transcript: transcript.slice(0, 80),
        }));
        ctx.setGpsStatus(`🐦 ${ctx.aiDisplayName} 자기 음성(에코) 무시 · 계속 듣는 중`);
        ctx.onScheduleRestart();
        return { handled: true, playbackPromise: null };
    }

    const companionCmd = parseCompanionCommand(transcript);
    if (companionCmd.type === 'reset') {
        ctx.companionPersonaRef.current = createEmptyPersona();
        Promise.resolve(ctx.resetPersonaStore()).catch(() => { });
    } else if (companionCmd.type === 'set_name' && companionCmd.name) {
        const named = setPreferredName(ctx.companionPersonaRef.current, companionCmd.name);
        ctx.companionPersonaRef.current = named;
        Promise.resolve(ctx.persistPersona(named)).catch(() => { });
    }

    const answer = String(ctx.data.response_text ?? ctx.data.answer ?? ctx.data.reply ?? '').trim();
    const mapContext = typeof ctx.data.map_context === 'object' && ctx.data.map_context !== null
        ? ctx.data.map_context as SorisaeMapContext
        : null;
    const safetyAlert = Boolean(ctx.data.safety_alert);
    const safetyAlertMessage = String(ctx.data.safety_alert_message ?? '').trim();
    const highRiskBlocked = Boolean(ctx.data.high_risk_mode_blocked);

    if (safetyAlert && safetyAlertMessage) {
        ctx.setTourismSafetyBanner({ message: safetyAlertMessage, highRiskBlocked });
    } else {
        ctx.setTourismSafetyBanner(null);
    }

    if (ctx.isTravelItineraryIntent(transcript)) {
        ctx.setItinerarySeedQuery(transcript);
        ctx.bumpItinerarySeedNonce();
    }

    if (!answer) {
        ctx.setTourismSafetyBanner(null);
        ctx.setGpsStatus(`🐦 ${ctx.aiDisplayName} 응답이 비어 있습니다 · 다시 말씀해 주세요`);
        ctx.onScheduleRestart();
        return { handled: true, playbackPromise: null };
    }

    const resolvedTripSessionId = String(ctx.data.trip_session_id ?? '').trim();
    if (resolvedTripSessionId && ctx.userId) {
        ctx.companionTripSessionIdRef.current = resolvedTripSessionId;
        Promise.resolve(saveCompanionTripSessionId(ctx.userId, resolvedTripSessionId)).catch(() => { });
    }

    const serverConv = Array.isArray(ctx.data.conversation) ? ctx.data.conversation : null;
    if (serverConv && serverConv.length) {
        ctx.faceGptConversationRef.current = serverConv
            .filter((m: unknown) => {
                const row = m as { role?: string; content?: string };
                return row && (row.role === 'user' || row.role === 'assistant') && row.content;
            })
            .map((m: unknown) => {
                const row = m as { role: string; content: string };
                return { role: String(row.role), content: String(row.content) };
            })
            .slice(-20);
    } else {
        ctx.faceGptConversationRef.current = [
            ...ctx.faceGptConversationRef.current,
            { role: 'user', content: transcript },
            { role: 'assistant', content: answer },
        ].slice(-20);
    }

    if (companionCmd.type === 'none') {
        void ctx.recordPersonaTurn({ transcript, answer, language: ctx.profileLang })
            .then((p) => { ctx.companionPersonaRef.current = p; })
            .catch(() => { });
    }

    const speakText = ctx.normalizeSpeakText(answer);
    if (!speakText) {
        ctx.setGpsStatus(`🐦 ${ctx.aiDisplayName} 답변 완료`);
        ctx.onScheduleRestart();
        return { handled: true, playbackPromise: null };
    }

    const replyLangCode = ctx.profileLang;
    ctx.faceGptSpokenEchoRef.current = [
        ...ctx.faceGptSpokenEchoRef.current,
        { text: normalizeEchoText(answer), atMs: Date.now() },
    ].slice(-FACE_CONVERSATION_SPOKEN_HISTORY);

    const qLangRaw = ctx.normalizeDetectedLangCode(ctx.data.detected_language) ?? ctx.profileLang;
    const qSeq = (ctx.sorisaeQaSeqRef.current += 1);
    ctx.setSorisaeQaLog((prev) => [
        ...prev,
        {
            id: qSeq,
            question: transcript,
            questionLang: String(qLangRaw),
            answer,
            answerLang: String(replyLangCode),
            atMs: Date.now(),
            mapContext,
        },
    ].slice(-50));

    ctx.sorisaeSpeakingRef.current = true;
    ctx.setSorisaeSpeakingUi?.(true);
    ctx.setGpsStatus(`🐦 ${ctx.aiDisplayName} 답변 음성 출력 중 · 듣기 멈춤`);
    const prioritySpeech = safetyAlertMessage ? `${safetyAlertMessage} ${answer}`.trim() : answer;
    // 서버 Edge neural TTS 합성 경로 사용(null,null 은 단말 TTS 강제 → 로봇 음·끊김).
    const playbackPromise = ctx.playFaceTranslationOutput({
        translatedText: prioritySpeech,
        targetLang: replyLangCode as unknown as LangCode,
        apiBaseUrl: ctx.apiBaseUrl,
        playbackSoundRef: ctx.sorisaeVoicePlaybackSoundRef as unknown as MutableRefObject<AudioSound | null>,
        correlationId: typeof ctx.data.correlation_id === 'string' ? ctx.data.correlation_id : ctx.faceCorrelationId,
    }).catch((err: unknown) => {
        const message = err instanceof Error ? err.message : String(err);
        console.error('[FACE_CONVERSATION]', JSON.stringify({
            event: 'sorisae_tts_playback_failed',
            message: message.slice(0, 200),
        }));
        ctx.setGpsStatus(`🐦 ${ctx.aiDisplayName} 음성 출력 실패 · 다시 말씀해 주세요`);
    }).finally(() => {
        ctx.reportFaceVoiceAutoTuningMetric({
            playbackMs: FACE_CONVERSATION_PLAYBACK_DRAIN_MS,
            overlapDetected: false,
        });
        setTimeout(() => {
            // 이전 발화의 drain 타이머가 더 최신 발화의 speaking 상태를 풀지 않게 한다.
            if (ctx.sorisaeQaSeqRef.current !== qSeq) {
                return;
            }
            ctx.sorisaeSpeakingRef.current = false;
            ctx.setSorisaeSpeakingUi?.(false);
        }, FACE_CONVERSATION_PLAYBACK_DRAIN_MS);
    });

    return { handled: true, playbackPromise };
}
