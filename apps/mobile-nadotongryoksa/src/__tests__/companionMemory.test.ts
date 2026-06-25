import { describe, expect, it } from '@jest/globals';

import {
    PERSONA_BRIEF_MIN_TURNS,
    buildPersonaBrief,
    createEmptyPersona,
    extractInterestTokens,
    observeTurn,
    resolveTone,
    setPreferredName,
    topDomains,
    topInterests,
} from '../features/sorisae/companionMemory';
import { revivePersona } from '../features/sorisae/companionPersonaStore';

const ISO = '2026-06-24T00:00:00.000Z';

describe('observeTurn — 진화/누적', () => {
    it('빈 페르소나에서 한 턴 관측 시 turns/시각/도메인 누적', () => {
        const p = observeTurn(createEmptyPersona(), {
            transcript: '오사카 맛집 알려줘',
            domain: 'travel',
            language: 'ko',
            nowIso: ISO,
        });
        expect(p.turns).toBe(1);
        expect(p.firstSeenAt).toBe(ISO);
        expect(p.lastSeenAt).toBe(ISO);
        expect(p.language).toBe('ko');
        expect(p.domainCounts.travel).toBe(1);
    });

    it('순수성 — 입력 페르소나를 변형하지 않는다', () => {
        const base = createEmptyPersona();
        const next = observeTurn(base, { transcript: '안녕', nowIso: ISO });
        expect(base.turns).toBe(0);
        expect(next).not.toBe(base);
    });

    it('빈 transcript 는 변화 없음', () => {
        const base = observeTurn(createEmptyPersona(), { transcript: '여행', nowIso: ISO });
        const same = observeTurn(base, { transcript: '   ', nowIso: ISO });
        expect(same.turns).toBe(base.turns);
    });

    it('말투 마커로 tone 추론(존댓말/반말)', () => {
        let p = createEmptyPersona();
        p = observeTurn(p, { transcript: '안녕하세요 잘 지내세요', nowIso: ISO });
        p = observeTurn(p, { transcript: '오늘 날씨 좋네요', nowIso: ISO });
        expect(resolveTone(p)).toBe('polite');

        let c = createEmptyPersona();
        c = observeTurn(c, { transcript: '야 뭐해', nowIso: ISO });
        c = observeTurn(c, { transcript: '밥 먹자', nowIso: ISO });
        expect(resolveTone(c)).toBe('casual');
    });

    it('관심 주제 빈도 누적 + 상위 추출', () => {
        let p = createEmptyPersona();
        p = observeTurn(p, { transcript: '커피 좋아해 커피', nowIso: ISO });
        p = observeTurn(p, { transcript: '커피 한잔 하자', nowIso: ISO });
        expect(p.interests['커피']).toBeGreaterThanOrEqual(2);
        expect(topInterests(p, 3)).toContain('커피');
    });

    it('자기개방 문장만 기억할 사실로 저장(중복제거)', () => {
        let p = createEmptyPersona();
        p = observeTurn(p, { transcript: '나는 등산을 좋아해', nowIso: ISO });
        p = observeTurn(p, { transcript: '나는 등산을 좋아해', nowIso: ISO });
        p = observeTurn(p, { transcript: '오사카 맛집 알려줘', domain: 'travel', nowIso: ISO });
        expect(p.notableFacts.length).toBe(1);
        expect(p.notableFacts[0]).toContain('등산');
    });

    it('도메인 사용 빈도 상위(습관) 추출', () => {
        let p = createEmptyPersona();
        p = observeTurn(p, { transcript: '여행 일정', domain: 'travel', nowIso: ISO });
        p = observeTurn(p, { transcript: '맛집', domain: 'travel', nowIso: ISO });
        p = observeTurn(p, { transcript: '외로워', domain: 'wellbeing', nowIso: ISO });
        expect(topDomains(p, 1)).toEqual(['travel']);
    });
});

describe('extractInterestTokens', () => {
    it('불용어/짧은 토큰/숫자 제거', () => {
        const toks = extractInterestTokens('오늘 진짜 커피 마시고 123 the cat');
        expect(toks).not.toContain('오늘');
        expect(toks).not.toContain('진짜');
        expect(toks).not.toContain('the');
        expect(toks).toContain('커피');
    });
});

describe('buildPersonaBrief', () => {
    it('최소 턴 미만이면 빈 문자열', () => {
        let p = createEmptyPersona();
        p = observeTurn(p, { transcript: '커피 좋아', nowIso: ISO });
        expect(p.turns).toBeLessThan(PERSONA_BRIEF_MIN_TURNS);
        expect(buildPersonaBrief(p)).toBe('');
    });

    it('충분히 누적되면 호칭/말투/관심/사실을 압축 요약', () => {
        let p = createEmptyPersona();
        p = setPreferredName(p, '철홍');
        p = observeTurn(p, { transcript: '나는 커피를 좋아해요', domain: 'companion', nowIso: ISO });
        p = observeTurn(p, { transcript: '커피 맛집 알려줘요', domain: 'travel', nowIso: ISO });
        p = observeTurn(p, { transcript: '오늘도 커피 마셨어요', domain: 'companion', nowIso: ISO });
        const brief = buildPersonaBrief(p);
        expect(brief).toContain('철홍');
        expect(brief).toContain('커피');
        expect(brief.toLowerCase()).toContain('companion memory');
    });
});

describe('revivePersona — 영속 검증', () => {
    it('손상/구버전/비객체 → 빈 페르소나', () => {
        expect(revivePersona(null).turns).toBe(0);
        expect(revivePersona({ version: 999 }).turns).toBe(0);
        expect(revivePersona('nope' as unknown).turns).toBe(0);
    });

    it('정상 페이로드는 복원', () => {
        const p = observeTurn(createEmptyPersona(), { transcript: '커피 좋아', nowIso: ISO });
        const revived = revivePersona(JSON.parse(JSON.stringify(p)));
        expect(revived.turns).toBe(1);
        expect(revived.interests['커피']).toBe(1);
    });
});
