import { describe, expect, it } from '@jest/globals';

import {
    estimatePcm16MonoRmsDb,
    mapFileRmsToPseudoMeterDb,
    shouldSkipSilentVoiceRelayStt,
} from '../features/voip-voice-relay/voiceRelayAudioMetrics';

describe('voiceRelayAudioMetrics', () => {
    it('detects silent PCM segments', () => {
        const silent = new Int16Array(1600);
        expect(estimatePcm16MonoRmsDb(silent)).toBeLessThan(-100);
    });

    it('skips STT for meter-dead silent capture', () => {
        const decision = shouldSkipSilentVoiceRelayStt({
            peakMeterDb: -160,
            hasSpeech: false,
            meterUnavailable: true,
            audioBase64: 'AAAA',
        });
        expect(decision.skip).toBe(true);
        expect(decision.reason).toBe('silent_capture_no_meter');
    });

    it('skips STT for meter-dead silence even when AAC proxy RMS is high', () => {
        const noisyProxy = Buffer.from(new Uint8Array(512).map((_, index) => (index * 17 + 64) % 256)).toString('base64');
        const decision = shouldSkipSilentVoiceRelayStt({
            peakMeterDb: -160,
            hasSpeech: false,
            meterUnavailable: true,
            audioBase64: noisyProxy,
        });
        expect(decision.skip).toBe(true);
        expect(decision.reason).toBe('silent_capture_no_meter');
    });

    it('allows STT when WAV PCM RMS is above threshold', () => {
        const loud = new Int16Array(1600);
        for (let index = 0; index < loud.length; index += 1) {
            loud[index] = 4000;
        }
        const rmsDb = estimatePcm16MonoRmsDb(loud);
        expect(rmsDb).toBeGreaterThan(-40);

        const wavHeader = new Uint8Array(44);
        wavHeader[0] = 0x52;
        wavHeader[1] = 0x49;
        wavHeader[2] = 0x46;
        wavHeader[3] = 0x46;
        wavHeader[8] = 0x57;
        wavHeader[9] = 0x41;
        wavHeader[10] = 0x56;
        wavHeader[11] = 0x45;
        wavHeader[36] = 0x64;
        wavHeader[37] = 0x61;
        wavHeader[38] = 0x74;
        wavHeader[39] = 0x61;
        const pcmBytes = new Uint8Array(44 + loud.length * 2);
        pcmBytes.set(wavHeader);
        const pcmView = new DataView(pcmBytes.buffer);
        pcmView.setUint32(40, loud.length * 2, true);
        for (let index = 0; index < loud.length; index += 1) {
            pcmView.setInt16(44 + index * 2, loud[index], true);
        }
        const base64 = Buffer.from(pcmBytes).toString('base64');

        const decision = shouldSkipSilentVoiceRelayStt({
            peakMeterDb: -160,
            hasSpeech: false,
            meterUnavailable: true,
            audioBase64: base64,
        });
        expect(decision.skip).toBe(false);
    });

    it('maps loud file RMS to pseudo speech meter', () => {
        expect(mapFileRmsToPseudoMeterDb(-40)).toBe(-40);
        expect(mapFileRmsToPseudoMeterDb(-90)).toBe(-160);
    });
});
