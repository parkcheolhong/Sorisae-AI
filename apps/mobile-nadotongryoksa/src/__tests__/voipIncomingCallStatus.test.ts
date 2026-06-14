import { describe, expect, it } from '@jest/globals';
import {
    isIncomingRingVoipStatus,
    isResumableIncomingVoipStatus,
    shouldDeferCalleeResumeToIncomingAccept,
} from '../utils/voipIncomingCallStatus';

describe('voipIncomingCallStatus', () => {
    it('treats only ringing and initiated as incoming ring states', () => {
        expect(isIncomingRingVoipStatus('ringing')).toBe(true);
        expect(isIncomingRingVoipStatus('initiated')).toBe(true);
        expect(isIncomingRingVoipStatus('connecting')).toBe(false);
        expect(isIncomingRingVoipStatus('active')).toBe(false);
        expect(isIncomingRingVoipStatus('callee_offline')).toBe(false);
    });

    it('keeps connecting and active as resumable but not ring states', () => {
        expect(isResumableIncomingVoipStatus('connecting')).toBe(true);
        expect(isResumableIncomingVoipStatus('active')).toBe(true);
        expect(isIncomingRingVoipStatus('connecting')).toBe(false);
    });

    it('defers callee resume to accept only for pre-accept ring states', () => {
        expect(shouldDeferCalleeResumeToIncomingAccept('ringing', false)).toBe(true);
        expect(shouldDeferCalleeResumeToIncomingAccept('connecting', false)).toBe(false);
        expect(shouldDeferCalleeResumeToIncomingAccept('ringing', true)).toBe(false);
    });
});
