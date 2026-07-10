import {
    getWorldlincoTuning,
    resolveFaceVadDefaultsFromTuning,
    resolveSorisaeCompanionVadDefaultsFromTuning,
    setWorldlincoRuntimeAutoProfile,
    type WorldlincoTuningSnapshot,
} from '../services/worldlincoTuningConfig';

describe('sorisae companion voice tuning', () => {
    afterEach(() => {
        setWorldlincoRuntimeAutoProfile('default');
    });

    it('applies the face conversation conditional boundaries for longer utterances', () => {
        const tuning = {
            version: 4,
            updated_at: '2026-07-03T00:00:00Z',
            voip: {
                silero_silence_ms: 1000,
                silero_speech_ms: 120,
                silero_min_segment_ms: 3000,
                silero_min_speech_span_ms: 1700,
                silero_safety_cap_ms: 7000,
                silero_post_flush_cooldown_ms: 1000,
                remote_echo_guard_ms: 4800,
                speaker_echo_guard_ms: 5800,
                remote_listen_hold_ms: 2600,
                post_playback_guard_ms: 550,
                fairness_barge_in_ms: 7000,
                vad_silence_flush_ms: 1000,
                vad_min_segment_ms: 3000,
                vad_max_segment_ms: 7000,
                speech_meter_min_db: -52,
                file_speech_rms_db: -52,
                meter_unavailable_fixed_flush_ms: 4000,
                live_duplex_mode: 0,
            },
            face_conversation: {
                silence_flush_ms: 900,
                min_segment_ms: 1600,
                max_segment_ms: 10000,
                file_speech_rms_db: -50,
                meter_poll_every: 2,
                restart_ms: 120,
                playback_cap_ms: 50000,
            },
        } as WorldlincoTuningSnapshot;

        expect(resolveFaceVadDefaultsFromTuning(tuning)).toMatchObject({
            silenceFlushMs: 900,
            minSegmentMs: 1600,
            meterUnavailableFixedFlushMs: 2200,
            maxSegmentMs: 10000,
        });
    });

    it('applies fixed stable boundaries for sorisae home q&a', () => {
        const tuning = {
            version: 4,
            updated_at: '2026-07-03T00:00:00Z',
            voip: {
                silero_silence_ms: 1000,
                silero_speech_ms: 120,
                silero_min_segment_ms: 3000,
                silero_min_speech_span_ms: 1700,
                silero_safety_cap_ms: 7000,
                silero_post_flush_cooldown_ms: 1000,
                remote_echo_guard_ms: 4800,
                speaker_echo_guard_ms: 5800,
                remote_listen_hold_ms: 2600,
                post_playback_guard_ms: 550,
                fairness_barge_in_ms: 7000,
                vad_silence_flush_ms: 1000,
                vad_min_segment_ms: 3000,
                vad_max_segment_ms: 7000,
                speech_meter_min_db: -52,
                file_speech_rms_db: -52,
                meter_unavailable_fixed_flush_ms: 4000,
                live_duplex_mode: 0,
            },
            face_conversation: {
                silence_flush_ms: 900,
                min_segment_ms: 1600,
                max_segment_ms: 10000,
                file_speech_rms_db: -50,
                meter_poll_every: 2,
                restart_ms: 120,
                playback_cap_ms: 50000,
            },
        } as WorldlincoTuningSnapshot;

        expect(resolveSorisaeCompanionVadDefaultsFromTuning(tuning)).toMatchObject({
            silenceFlushMs: 1000,
            minSegmentMs: 1700,
            meterUnavailableFixedFlushMs: 450,
            maxSegmentMs: 6500,
        });
    });

    it('switches runtime auto profile between face and sorisae fixed boundaries', () => {
        setWorldlincoRuntimeAutoProfile('face');
        const faceSnapshot = getWorldlincoTuning();
        expect(faceSnapshot.face_conversation).toMatchObject({
            silence_flush_ms: 1000,
            min_segment_ms: 1800,
            max_segment_ms: 18000,
        });

        setWorldlincoRuntimeAutoProfile('sorisae');
        const sorisaeSnapshot = getWorldlincoTuning();
        expect(sorisaeSnapshot.face_conversation).toMatchObject({
            silence_flush_ms: 1000,
            min_segment_ms: 1700,
            max_segment_ms: 6500,
        });
    });
});