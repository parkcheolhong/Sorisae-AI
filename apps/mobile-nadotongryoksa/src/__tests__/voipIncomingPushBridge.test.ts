import { describe, expect, it } from '@jest/globals';
import { parseIncomingCallFcmData, shouldPersistIncomingFcmData } from '../services/voipIncomingPushBridge';

describe('voipIncomingPushBridge', () => {
    it('parses full FCM incoming_call data', () => {
        const parsed = parseIncomingCallFcmData({
            type: 'incoming_call',
            call_id: 'call-abc123',
            signaling_server: 'wss://example.com/signal?call_id=call-abc123&role=callee',
            caller_voice_id: 'nado-000226',
            caller_label: 'Tab User',
            status: 'ringing',
        });
        expect(parsed?.call_id).toBe('call-abc123');
        expect(parsed?.participant_role).toBe('callee');
        expect(parsed?.signaling_server).toContain('call-abc123');
        expect(parsed?.caller_label).toBe('Tab User');
    });

    it('detects persistable incoming_call payloads', () => {
        expect(shouldPersistIncomingFcmData({ type: 'incoming_call', call_id: 'call-x' })).toBe(true);
        expect(shouldPersistIncomingFcmData({ type: 'other', call_id: 'call-x' })).toBe(false);
    });
});
