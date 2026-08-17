import { describe, expect, it } from '@jest/globals';

import {
    buildVoiceId,
    buildVoipTopic,
    buildVoipWebSocketUrl,
    getDefaultVoipTurnServers,
    normalizeTurnServers,
} from '../features/voip/voipSignaling';

describe('buildVoiceId — 사용자ID→보이스ID', () => {
    it('6자리 zero-pad', () => {
        expect(buildVoiceId(7)).toBe('nado-000007');
        expect(buildVoiceId(123456)).toBe('nado-123456');
        expect(buildVoiceId(1234567)).toBe('nado-1234567');
    });
});

describe('buildVoipTopic — 보이스ID→토픽', () => {
    it('영숫자 외 문자를 _ 로 치환하고 소문자화', () => {
        expect(buildVoipTopic('nado-000007')).toBe('worldlingo_voip_nado_000007');
        expect(buildVoipTopic('  NADO-00 7 ')).toBe('worldlingo_voip_nado_00_7');
    });
});

describe('buildVoipWebSocketUrl — ws(s) URL 빌더', () => {
    it('http→ws, https→wss 로 변환하고 query 를 붙인다', () => {
        expect(buildVoipWebSocketUrl('http://localhost:8000', '/api/v1/voip/presence', { token: 'abc' }))
            .toBe('ws://localhost:8000/api/v1/voip/presence?token=abc');
        expect(buildVoipWebSocketUrl('https://api.example.com/', '/ws'))
            .toBe('wss://api.example.com/ws');
    });

    it('query 가 없으면 ? 를 붙이지 않는다', () => {
        expect(buildVoipWebSocketUrl('http://h', '/p')).toBe('ws://h/p');
    });
});

describe('TURN 서버 기본값/정규화', () => {
    it('getDefaultVoipTurnServers 는 STUN-only 3개', () => {
        const servers = getDefaultVoipTurnServers();
        expect(servers).toHaveLength(3);
        expect(servers[0].urls[0]).toMatch(/^stun:/);
    });

    it('비배열/빈/무효 입력은 기본값으로 폴백', () => {
        expect(normalizeTurnServers(null)).toHaveLength(3);
        expect(normalizeTurnServers([])).toHaveLength(3);
        expect(normalizeTurnServers([{ urls: [] }, 'x', null])).toHaveLength(3);
    });

    it('유효 항목은 urls/username/credential 을 보존', () => {
        const result = normalizeTurnServers([
            { urls: ['turn:t.example.com:3478', ''], username: 'u', credential: 'c' },
            { urls: 'not-array' },
        ]);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ urls: ['turn:t.example.com:3478'], username: 'u', credential: 'c' });
    });
});
