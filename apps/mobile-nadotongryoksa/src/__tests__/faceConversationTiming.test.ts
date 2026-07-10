import { describe, expect, it } from '@jest/globals';

import {
    FACE_CONVERSATION_RESTART_MS,
    FACE_CONVERSATION_PLAYBACK_CAP_MS,
    FACE_CONVERSATION_PERMISSION_RETRY_MS,
    FACE_CONVERSATION_ECHO_GUARD_MS,
    FACE_CONVERSATION_SPOKEN_HISTORY,
    FACE_CONVERSATION_PLAYBACK_DRAIN_MS,
    FACE_OUTPUT_ECHO_GUARD_MS,
    computeFaceTtsSafetyCapMs,
} from '../features/face-interpretation/faceConversationTiming';

// [Phase5.1a] App.tsx 모놀리스에서 분리한 대면통역 타이밍 상수 회귀 가드.
// 값이 바뀌면 디바이스 에코/핑퐁 차단 동작이 변하므로 SSOT 잠금.
describe('faceConversationTiming', () => {
    it('preserves the calibrated timing values for faster face conversation turns', () => {
        expect(FACE_CONVERSATION_RESTART_MS).toBe(180);
        expect(FACE_CONVERSATION_PLAYBACK_CAP_MS).toBe(50_000);
        expect(FACE_CONVERSATION_PERMISSION_RETRY_MS).toBe(800);
        expect(FACE_CONVERSATION_ECHO_GUARD_MS).toBe(25000);
        expect(FACE_CONVERSATION_SPOKEN_HISTORY).toBe(5);
        expect(FACE_CONVERSATION_PLAYBACK_DRAIN_MS).toBe(2500);
        expect(FACE_OUTPUT_ECHO_GUARD_MS).toBe(5000);
    });

    it('keeps the output echo guard shorter than the full echo guard window', () => {
        // 출력언어 에코 가드는 상대 화자 응답을 너무 오래 막지 않도록 전체 가드창보다 짧아야 한다.
        expect(FACE_OUTPUT_ECHO_GUARD_MS).toBeLessThan(FACE_CONVERSATION_ECHO_GUARD_MS);
    });

    it('allows long guide TTS to finish before the safety failsafe fires', () => {
        // 250자 가이드 Edge TTS ≈ 40s — 과거 30s 상한이 끊김 원인.
        expect(computeFaceTtsSafetyCapMs(250)).toBeGreaterThanOrEqual(45_000);
        expect(computeFaceTtsSafetyCapMs(250)).toBeLessThanOrEqual(90_000);
    });
});
