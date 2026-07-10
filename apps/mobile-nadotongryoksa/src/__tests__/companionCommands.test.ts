import { describe, expect, it } from '@jest/globals';

import {
    PROACTIVE_SUGGESTION_MIN_TURNS,
    buildProactiveSuggestion,
    parseCompanionCommand,
} from '../features/sorisae/companionCommands';
import { createEmptyPersona, observeTurn } from '../features/sorisae/companionMemory';

const ISO = '2026-06-24T00:00:00.000Z';

describe('parseCompanionCommand', () => {
    it('기억 초기화 명령(reset)', () => {
        expect(parseCompanionCommand('나를 잊어줘').type).toBe('reset');
        expect(parseCompanionCommand('내 기억 다 지워').type).toBe('reset');
        expect(parseCompanionCommand('forget me').type).toBe('reset');
        expect(parseCompanionCommand('reset my memory').type).toBe('reset');
    });

    it('호칭 설정 명령(set_name)', () => {
        const ko = parseCompanionCommand('나를 철홍이라고 불러줘');
        expect(ko.type).toBe('set_name');
        expect(ko.name).toBe('철홍');

        const en = parseCompanionCommand('call me Captain');
        expect(en.type).toBe('set_name');
        expect(en.name).toBe('Captain');
    });

    it('일반 발화는 none', () => {
        expect(parseCompanionCommand('오늘 날씨 좋다').type).toBe('none');
        expect(parseCompanionCommand('').type).toBe('none');
    });

    it('reset 이 set_name 보다 우선', () => {
        expect(parseCompanionCommand('나를 잊어줘').type).toBe('reset');
    });
});

describe('buildProactiveSuggestion', () => {
    it('누적이 적으면 null', () => {
        let p = createEmptyPersona();
        p = observeTurn(p, { transcript: '여행 가고 싶다', domain: 'travel', nowIso: ISO });
        expect(p.turns).toBeLessThan(PROACTIVE_SUGGESTION_MIN_TURNS);
        expect(buildProactiveSuggestion(p)).toBeNull();
    });

    it('충분히 누적되면 주 도메인 맞춤 제안', () => {
        let p = createEmptyPersona();
        for (let i = 0; i < PROACTIVE_SUGGESTION_MIN_TURNS; i += 1) {
            p = observeTurn(p, { transcript: '여행 일정 짜자', domain: 'travel', nowIso: ISO });
        }
        const s = buildProactiveSuggestion(p);
        expect(s).toBeTruthy();
        expect(s).toContain('여행');
    });
});
