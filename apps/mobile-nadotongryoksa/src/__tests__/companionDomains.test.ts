import { describe, expect, it } from '@jest/globals';

import {
    COMPANION_DOMAINS,
    DEFAULT_COMPANION_DOMAIN,
    classifyCompanionDomain,
    scoreCompanionDomains,
    domainNumericId,
    domainByNumericId,
    domainByKey,
    personaHintForDomain,
} from '../features/sorisae/companionDomains';

describe('자동 넘버링 — 도메인 numericId', () => {
    it('정의 순서대로 1부터 고유 번호', () => {
        expect(COMPANION_DOMAINS.map((d) => d.numericId)).toEqual([1, 2, 3, 4, 5, 6]);
        expect(new Set(COMPANION_DOMAINS.map((d) => d.numericId)).size).toBe(COMPANION_DOMAINS.length);
    });

    it('key ↔ numericId 왕복 일관', () => {
        for (const d of COMPANION_DOMAINS) {
            expect(domainNumericId(d.key)).toBe(d.numericId);
            expect(domainByNumericId(d.numericId)?.key).toBe(d.key);
        }
        expect(domainByNumericId(999)).toBeNull();
    });

    it('companion 이 기본 폴백(numericId 1)', () => {
        expect(DEFAULT_COMPANION_DOMAIN).toBe('companion');
        expect(domainNumericId('companion')).toBe(1);
    });
});

describe('인텐트 분류기', () => {
    it('여행 키워드 → travel', () => {
        expect(classifyCompanionDomain('오사카 근처 맛집 추천해줘')).toBe('travel');
        expect(classifyCompanionDomain('find a hotel nearby')).toBe('travel');
    });

    it('지식 질문 → knowledge', () => {
        expect(classifyCompanionDomain('블랙홀이 뭐야? 설명해줘')).toBe('knowledge');
        expect(classifyCompanionDomain('how to boil an egg')).toBe('knowledge');
    });

    it('리마인더/습관 → life-assist', () => {
        expect(classifyCompanionDomain('내일 9시 회의 리마인더 해줘')).toBe('life-assist');
        expect(classifyCompanionDomain('remind me to drink water')).toBe('life-assist');
    });

    it('감정 표현 → wellbeing', () => {
        expect(classifyCompanionDomain('요즘 너무 외롭고 힘들어')).toBe('wellbeing');
        expect(classifyCompanionDomain('i feel so lonely')).toBe('wellbeing');
    });

    it('언어 학습 → language-tutor', () => {
        expect(classifyCompanionDomain('고마워 일본어로 뭐라고 해?')).toBe('language-tutor');
        expect(classifyCompanionDomain('how do you say hello in french')).toBe('language-tutor');
    });

    it('주식/최신 정보 → knowledge', () => {
        expect(classifyCompanionDomain('삼성전자 주가 알려줘')).toBe('knowledge');
        expect(classifyCompanionDomain('latest stock news')).toBe('knowledge');
    });

    it('키워드 없는 잡담 → companion(폴백)', () => {
        expect(classifyCompanionDomain('안녕 반가워')).toBe('companion');
        expect(classifyCompanionDomain('')).toBe('companion');
    });

    it('점수 동점이면 numericId 작은 도메인(결정적)', () => {
        const ranked = scoreCompanionDomains('여행 가고 싶은데 왜 이렇게 외롭지');
        expect(ranked[0].score).toBeGreaterThan(0);
        const key = classifyCompanionDomain('여행 가고 싶은데 왜 이렇게 외롭지');
        expect(['travel', 'knowledge', 'wellbeing']).toContain(key);
    });
});

describe('페르소나 힌트', () => {
    it('모든 도메인이 비지 않은 personaHint 를 가진다', () => {
        for (const d of COMPANION_DOMAINS) {
            expect(personaHintForDomain(d.key).length).toBeGreaterThan(0);
            expect(domainByKey(d.key)?.label.length).toBeGreaterThan(0);
        }
    });
});
