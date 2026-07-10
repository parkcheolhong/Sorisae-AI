import { describe, expect, it, jest } from '@jest/globals';
import { emitVoipCallEnded, subscribeVoipCallEnded } from '../services/voipCallSignals';

describe('voipCallSignals', () => {
    it('notifies subscribers when a call ends', () => {
        const listener = jest.fn();
        const unsubscribe = subscribeVoipCallEnded(listener);

        emitVoipCallEnded('call-123');

        expect(listener).toHaveBeenCalledTimes(1);
        expect(listener).toHaveBeenCalledWith('call-123');

        unsubscribe();
        emitVoipCallEnded('call-123');

        expect(listener).toHaveBeenCalledTimes(1);
    });
});