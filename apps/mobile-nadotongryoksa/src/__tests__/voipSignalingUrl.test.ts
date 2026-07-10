import { describe, expect, it } from '@jest/globals';

import { resolveVoipSignalingServerUrl } from '../utils/voipSignalingUrl';

describe('resolveVoipSignalingServerUrl', () => {
    const apiBase = 'https://metanova1004.com';

    it('rewrites private LAN ws signaling to production wss', () => {
        const resolved = resolveVoipSignalingServerUrl(
            'ws://172.30.1.41:8000/api/v1/voip/signal?call_id=abc',
            'callee',
            apiBase,
        );
        expect(resolved).toBe('wss://metanova1004.com/api/v1/voip/signal?call_id=abc&role=callee');
    });

    it('keeps public wss signaling unchanged', () => {
        const resolved = resolveVoipSignalingServerUrl(
            'wss://metanova1004.com/api/v1/voip/signal?call_id=abc&role=caller',
            'caller',
            apiBase,
        );
        expect(resolved).toBe('wss://metanova1004.com/api/v1/voip/signal?call_id=abc&role=caller');
    });
});
