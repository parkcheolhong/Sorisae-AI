import { describe, expect, it } from '@jest/globals';

import {
    collapseRepeatedRelayPhrases,
    createInitialVoiceRelaySegmentState,
    evaluateVoiceRelaySegmentDecision,
    isLikelyGibberishRelayTranscript,
    isLikelyRepetitionHallucination,
    isLikelyVoiceRelayEcho,
    isLikelySilenceHallucination,
    isVoiceRelaySilenceCapture,
    nextVoiceRelaySegmentStateAfterFlush,
    shouldRejectRemoteVoiceRelayPlayback,
    updateVoiceRelaySegmentSpeechState,
    updateVoiceRelaySegmentSpeechStateFromFileRms,
    VOICE_RELAY_VAD_DEFAULTS,
    resolveVoiceRelayFixedFlushDelayMs,
} from '../features/voip-voice-relay/voiceRelayOrchestrator';
import { VoiceRelayPlaybackQueue } from '../features/voip-voice-relay/voiceRelayPlaybackQueue';

describe('voiceRelayOrchestrator', () => {
    it('waits for minimum duration before silence flush', () => {
        const startedAt = 1_000;
        let state = createInitialVoiceRelaySegmentState(startedAt);
        state = updateVoiceRelaySegmentSpeechState(state, -30, startedAt + 400);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + VOICE_RELAY_VAD_DEFAULTS.minSegmentMs - 1,
            -80,
        );

        expect(decision.action).toBe('continue');
    });

    it('flushes short utterances after silence threshold', () => {
        const startedAt = 2_000;
        let state = createInitialVoiceRelaySegmentState(startedAt);
        state = updateVoiceRelaySegmentSpeechState(state, -30, startedAt + 500);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + 500 + VOICE_RELAY_VAD_DEFAULTS.silenceFlushMs + VOICE_RELAY_VAD_DEFAULTS.minSegmentMs,
            -80,
        );

        expect(decision).toEqual({
            action: 'flush',
            reason: 'silence',
            isFinal: true,
        });
    });

    it('flushes long utterances in chunks before final silence', () => {
        const startedAt = 3_000;
        let state = createInitialVoiceRelaySegmentState(startedAt);
        state = updateVoiceRelaySegmentSpeechState(state, -30, startedAt + 500);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + VOICE_RELAY_VAD_DEFAULTS.maxSegmentMs,
            -30,
        );

        expect(decision).toEqual({
            action: 'flush',
            reason: 'max_duration',
            isFinal: false,
        });
    });

    it('ignores max duration flush when no speech was captured', () => {
        const startedAt = 3_000;
        const state = createInitialVoiceRelaySegmentState(startedAt);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + VOICE_RELAY_VAD_DEFAULTS.maxSegmentMs,
            -160,
        );

        expect(decision.action).toBe('continue');
    });

    it('collapses repeated relay phrases', () => {
        expect(collapseRepeatedRelayPhrases('hello everyone. hello everyone. hello everyone.')).toBe('hello everyone');
        expect(collapseRepeatedRelayPhrases('안녕하세요, 여러분. 안녕하세요, 여러분. 안녕하세요, 여러분.')).toBe('안녕하세요, 여러분');
        expect(collapseRepeatedRelayPhrases(
            Array.from({ length: 6 }, () => '안녕하세요 여러분').join(' '),
        )).toBe('안녕하세요 여러분');
        expect(collapseRepeatedRelayPhrases(
            Array.from({ length: 5 }, () => 'Hello everyone').join(' '),
        )).toBe('Hello everyone');
    });

    it('detects repetition hallucinations from looped playback pickup', () => {
        const repeatedKo = Array.from({ length: 20 }, () => '안녕하세요 여러분').join(' ');
        const repeatedEn = Array.from({ length: 20 }, () => 'Hello everyone').join(' ');
        expect(isLikelyRepetitionHallucination(repeatedKo)).toBe(true);
        expect(isLikelyRepetitionHallucination(repeatedEn)).toBe(true);
        expect(isLikelyRepetitionHallucination('고맙습니다. 땡큐.')).toBe(false);
    });

    it('rejects remote playback when repetition hallucination is detected', () => {
        const repeatedEn = Array.from({ length: 12 }, () => 'Hello everyone').join(' ');
        expect(shouldRejectRemoteVoiceRelayPlayback({
            captureTrust: 'high',
            transcript: repeatedEn,
            translatedText: repeatedEn,
            sourceLang: 'ko',
            targetLang: 'en',
            langScope: ['ko', 'en'],
        }).reason).toBe('repetition_hallucination');
    });

    it('detects common silence hallucinations', () => {
        expect(isLikelySilenceHallucination('You', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('Hello', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('안녕하세요', 'ko')).toBe(true);
        expect(isLikelySilenceHallucination('Hello there', 'en')).toBe(false);
        expect(isVoiceRelaySilenceCapture(true, -160, false)).toBe(true);
    });

    it('detects Japanese/Korean silence outro hallucinations', () => {
        // Whisper 가 무음 구간에서 흔히 뱉는 일본어 아웃트로 환각.
        expect(isLikelySilenceHallucination('ご視聴ありがとうございました', 'ja')).toBe(true);
        expect(isLikelySilenceHallucination('ご視聴ありがとうございました。', 'ja')).toBe(true);
        expect(isLikelySilenceHallucination('ありがとうございます', 'ja')).toBe(true);
        expect(isLikelySilenceHallucination('チャンネル登録お願いします', 'ja')).toBe(true);
        // 한국어 번역/직접 환각 아웃트로.
        expect(isLikelySilenceHallucination('시청해 주셔서 감사합니다', 'ko')).toBe(true);
        expect(isLikelySilenceHallucination('감사합니다', 'ko')).toBe(true);
        // 근접무음에서 반복 생성돼 상대에게 중복 발화되던 메타 단어 환각("통역 문장").
        expect(isLikelySilenceHallucination('통역 문장', 'ko')).toBe(true);
        expect(isLikelySilenceHallucination('통역문장.', 'ko')).toBe(true);
        // 실제 대화는 통과해야 한다.
        expect(isLikelySilenceHallucination('会議の時間を教えてください', 'ja')).toBe(false);
        expect(isLikelySilenceHallucination('지금 어디에 계세요', 'ko')).toBe(false);
        expect(isLikelySilenceHallucination('통역 부탁드립니다 문장이 길어요', 'ko')).toBe(false);
    });

    it('detects multilingual youtube-outro hallucinations regardless of detected lang', () => {
        // STT가 무음/메아리를 no/sv/da 등으로 오탐지하며 뱉는 아웃트로 환각.
        // (예: "Takk for att du så med." → 통역 경로에서 영어로 발화되던 문제)
        expect(isLikelySilenceHallucination('Takk for att du så med.', 'no')).toBe(true);
        expect(isLikelySilenceHallucination('Takk for att du så med.', 'en')).toBe(true);
        // Whisper가 만든 깨진 변형도 차단.
        expect(isLikelySilenceHallucination('Takk for ating med.', 'no')).toBe(true);
        // 정상 노르웨이어 감사 표현은 통과.
        expect(isLikelySilenceHallucination('Takk for hjelpen', 'no')).toBe(false);
        expect(isLikelySilenceHallucination('Takk for maten', 'no')).toBe(false);
        expect(isLikelySilenceHallucination('Tack för att du tittade', 'sv')).toBe(true);
        expect(isLikelySilenceHallucination('Thanks for watching', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('Vielen Dank fürs Zuschauen', 'de')).toBe(true);
        expect(isLikelySilenceHallucination('Merci d\'avoir regardé', 'fr')).toBe(true);
        // 실제 대화는 통과.
        expect(isLikelySilenceHallucination('Takk, hvor er stasjonen?', 'no')).toBe(false);
    });

    it('detects subtitle/translation credit hallucinations (idle-mic Whisper artifacts)', () => {
        // 무발화 상태에서 마이크가 무음을 녹음 → Whisper가 자막 크레딧 환각 생성 → 발화되던 근원.
        expect(isLikelySilenceHallucination('Teksting av Nicolai Winther', 'no')).toBe(true);
        expect(isLikelySilenceHallucination('Undertekster av NRK', 'no')).toBe(true);
        expect(isLikelySilenceHallucination('Untertitel im Auftrag des ZDF', 'de')).toBe(true);
        expect(isLikelySilenceHallucination('Sous-titres par Amara', 'fr')).toBe(true);
        expect(isLikelySilenceHallucination('Subtítulos por la comunidad', 'es')).toBe(true);
        expect(isLikelySilenceHallucination('字幕提供', 'ja')).toBe(true);
        // 실제 대화는 통과.
        expect(isLikelySilenceHallucination('Hvor mye koster billetten?', 'no')).toBe(false);
    });

    it('detects youtube intro/channel hallucinations (idle-mic Whisper artifacts)', () => {
        expect(isLikelySilenceHallucination('Hello everyone, welcome back to my channel, today I will show you how to make a cake', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('please like and subscribe', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('In this video we will travel', 'en')).toBe(true);
        // 실제 대화는 통과(‘my friend’ 등은 막지 않음).
        expect(isLikelySilenceHallucination('I want to visit my friend in Tokyo', 'en')).toBe(false);
        expect(isLikelySilenceHallucination('Where is the nearest subway station?', 'en')).toBe(false);
    });

    it('rejects Georgian and repeated-symbol Whisper gibberish', () => {
        const georgianSpam = 'ლლლლლლლლლლლლლლლლლლლლლლ: ლლლლლლლლლლლლლლლლლლლლლლ:';
        expect(isLikelyGibberishRelayTranscript(georgianSpam, ['ko', 'en'])).toBe(true);
        expect(isLikelyGibberishRelayTranscript('aaaaBBBB', ['ko', 'en'])).toBe(true);
        expect(isLikelyGibberishRelayTranscript('고맙습니다', ['ko', 'en'])).toBe(false);
        expect(isLikelyGibberishRelayTranscript('Thank you.', ['ko', 'en'])).toBe(false);
    });

    it('detects playback pickup echo for callee send', () => {
        const echo = isLikelyVoiceRelayEcho({
            transcript: 'Now do the test.',
            translatedText: 'Now do the test.',
            nowMs: 10_000,
            recentRemotePlaybackTranslated: 'Now do the test.',
            recentRemotePlaybackAtMs: 9_000,
        });
        expect(echo.echo).toBe(true);
        expect(echo.reason).toBe('playback_pickup_echo');
    });

    it('detects spaceless CJK self-echo even when STT re-transcribes it imperfectly', () => {
        // 대면 모드: 방금 기기가 'わかりました、そうですね' 를 발화 → 마이크가 잔향을
        // 다시 잡아 STT가 미세하게 다르게('わかりましたそうですね') 받아써도 에코로 잡아야 한다.
        const echo = isLikelyVoiceRelayEcho({
            transcript: 'わかりましたそうですね',
            translatedText: '알겠습니다 그렇네요',
            nowMs: 5_000,
            recentLocalTranslated: 'わかりました、そうですね。',
            recentLocalSentAtMs: 4_000,
        });
        expect(echo.echo).toBe(true);
        expect(echo.reason).toBe('local_relay_echo');
    });

    it('does not flag a distinct CJK human reply as echo', () => {
        // 서로 다른 사람의 정상 응답은 막지 않는다(과차단 방지).
        const result = isLikelyVoiceRelayEcho({
            transcript: '今日はいい天気ですね',
            translatedText: '오늘은 날씨가 좋네요',
            nowMs: 5_000,
            recentLocalTranslated: 'わかりました、そうですね。',
            recentLocalSentAtMs: 4_000,
        });
        expect(result.echo).toBe(false);
    });

    it('rejects low-trust remote playback but keeps trusted thanks', () => {
        expect(shouldRejectRemoteVoiceRelayPlayback({
            captureTrust: 'low',
            transcript: '고맙습니다',
            translatedText: 'Thank you.',
            sourceLang: 'ko',
            targetLang: 'en',
            langScope: ['ko', 'en'],
        }).reject).toBe(true);

        expect(shouldRejectRemoteVoiceRelayPlayback({
            captureTrust: 'high',
            transcript: '고맙습니다',
            translatedText: 'Thank you.',
            sourceLang: 'ko',
            targetLang: 'en',
            langScope: ['ko', 'en'],
        }).reject).toBe(false);
    });

    it('marks speech from file RMS when Android metering is dead', () => {
        const startedAt = 2_000;
        const next = updateVoiceRelaySegmentSpeechStateFromFileRms(
            createInitialVoiceRelaySegmentState(startedAt),
            -45,
            startedAt + 900,
        );
        expect(next.hasSpeech).toBe(true);
        expect(next.lastSpeechAtMs).toBe(startedAt + 900);
    });

    it('uses longer auto flush when Android metering is unavailable', () => {
        expect(resolveVoiceRelayFixedFlushDelayMs(true)).toBe(
            VOICE_RELAY_VAD_DEFAULTS.meterUnavailableFixedFlushMs,
        );
        expect(resolveVoiceRelayFixedFlushDelayMs(false)).toBe(
            VOICE_RELAY_VAD_DEFAULTS.maxSegmentMs,
        );
    });

    it('increments chunk index for non-final flushes', () => {
        const nextState = nextVoiceRelaySegmentStateAfterFlush(
            createInitialVoiceRelaySegmentState(4_000, 1),
            false,
            16_500,
        );

        expect(nextState.chunkIndex).toBe(2);
        expect(nextState.hasSpeech).toBe(false);
    });
});

describe('voiceRelayPlaybackQueue', () => {
    it('plays queued items in seq_id order', async () => {
        const played: number[] = [];
        const queue = new VoiceRelayPlaybackQueue(async (item) => {
            played.push(item.seqId);
        });

        queue.enqueue({
            seqId: 1,
            utteranceId: 'u1',
            chunkIndex: 0,
            isFinal: true,
            translatedText: 'one',
            targetLang: 'en',
        });
        queue.enqueue({
            seqId: 2,
            utteranceId: 'u1',
            chunkIndex: 0,
            isFinal: true,
            translatedText: 'two',
            targetLang: 'en',
        });

        await new Promise((resolve) => setTimeout(resolve, 50));
        expect(played).toEqual([1, 2]);
    });
});
