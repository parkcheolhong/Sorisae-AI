import {
    FACE_CONTEXT_SESSION_GAP_MS,
    isDormantSilenceLoop,
    isRecoverableVoiceCaptureHttpError,
    shouldContinueFaceConversationContext,
    shouldUploadFaceConversationSegment,
    shouldSkipSorisaeSegmentUpload,
    shouldUploadDormantWakeSegment,
    shouldUploadSorisaeWindowSegment,
} from '../features/sorisae/sorisaeCaptureSegment';

describe('sorisaeCaptureSegment dormant wake upload gate', () => {
    it('detects dormant silence loop only when armed dormant without KWS', () => {
        expect(isDormantSilenceLoop({
            sorisaeWindowOpen: false,
            activeVoiceInputTarget: 'main',
            companionKwsActive: false,
            companionPhase: 'dormant',
        })).toBe(true);
        expect(isDormantSilenceLoop({
            sorisaeWindowOpen: true,
            activeVoiceInputTarget: 'main',
            companionKwsActive: false,
            companionPhase: 'dormant',
        })).toBe(false);
        expect(isDormantSilenceLoop({
            sorisaeWindowOpen: false,
            activeVoiceInputTarget: 'main',
            companionKwsActive: true,
            companionPhase: 'dormant',
        })).toBe(false);
    });

    it('allows dormant upload when file VAD saw speech even if Silero missed', () => {
        expect(shouldUploadDormantWakeSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: true,
        })).toBe(true);
    });

    it('allows dormant upload on moderate RMS when both VAD paths missed edge speech', () => {
        expect(shouldUploadDormantWakeSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -46,
        })).toBe(true);
        expect(shouldUploadDormantWakeSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -50,
        })).toBe(false);
        expect(shouldUploadDormantWakeSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -49,
        })).toBe(true);
    });

    it('allows sorisae window upload on server-aligned duration even when VAD missed', () => {
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -53,
            durationMs: 2500,
        })).toBe(true);
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -56,
            durationMs: 2500,
        })).toBe(false);
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -55,
            durationMs: 2500,
        })).toBe(true);
    });

    it('allows face conversation upload when file VAD or face RMS confirms speech even if Silero missed', () => {
        expect(shouldUploadFaceConversationSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: true,
            faceFileSpeechRmsDb: -55,
        })).toBe(true);
        expect(shouldUploadFaceConversationSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -54,
            faceFileSpeechRmsDb: -55,
        })).toBe(true);
        expect(shouldUploadFaceConversationSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -56,
            faceFileSpeechRmsDb: -55,
        })).toBe(false);
    });

    it('continues face conversation context only within the short same-pair gap', () => {
        expect(shouldContinueFaceConversationContext({
            nowMs: FACE_CONTEXT_SESSION_GAP_MS,
            lastTurnAtMs: 1,
            fromLang: 'ko',
            toLang: 'ja',
            lastFromLang: 'ko',
            lastToLang: 'ja',
        })).toBe(true);
        expect(shouldContinueFaceConversationContext({
            nowMs: FACE_CONTEXT_SESSION_GAP_MS + 2,
            lastTurnAtMs: 1,
            fromLang: 'ko',
            toLang: 'ja',
            lastFromLang: 'ko',
            lastToLang: 'ja',
        })).toBe(false);
        expect(shouldContinueFaceConversationContext({
            nowMs: 5000,
            lastTurnAtMs: 1,
            fromLang: 'ko',
            toLang: 'en',
            lastFromLang: 'ko',
            lastToLang: 'ja',
        })).toBe(false);
    });

    it('allows normal 6s sorisae questions but still blocks long fallback uploads when Silero missed speech', () => {
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: true,
            rmsDb: -39,
            durationMs: 6_200,
        })).toBe(true);
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: false,
            rmsDb: -45,
            durationMs: 13_400,
        })).toBe(false);
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: false,
            fileVadHadSpeech: true,
            rmsDb: -39,
            durationMs: 8_400,
        })).toBe(false);
        expect(shouldUploadSorisaeWindowSegment({
            sileroHadSpeech: true,
            fileVadHadSpeech: false,
            rmsDb: -45,
            durationMs: 13_400,
        })).toBe(true);
    });

    it('skips sorisae upload when segment or payload is too small', () => {
        expect(shouldSkipSorisaeSegmentUpload({
            segmentDurationMs: 1500,
            audioBase64Len: 8000,
        }).skip).toBe(true);
        expect(shouldSkipSorisaeSegmentUpload({
            segmentDurationMs: 2200,
            audioBase64Len: 1000,
        }).skip).toBe(true);
        expect(shouldSkipSorisaeSegmentUpload({
            segmentDurationMs: 2200,
            audioBase64Len: 8000,
        }).skip).toBe(false);
    });

    it('treats STT no-speech 400 as recoverable', () => {
        expect(isRecoverableVoiceCaptureHttpError(422, '')).toBe(true);
        expect(isRecoverableVoiceCaptureHttpError(400, 'STT 실패: faster-whisper')).toBe(true);
        expect(isRecoverableVoiceCaptureHttpError(400, '텍스트 또는 오디오 입력이 필요합니다')).toBe(false);
    });
});
