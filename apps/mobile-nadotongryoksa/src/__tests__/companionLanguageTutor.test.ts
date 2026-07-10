import { describe, expect, it } from '@jest/globals';

import {
    TUTOR_SUPPORTED_LANGUAGE_COUNT,
    buildLanguagePair,
    buildLanguagePairLabel,
    detectLanguageTutorIntent,
    resolveTargetLanguageFromText,
} from '../features/sorisae/companionLanguageTutor';

describe('detectLanguageTutorIntent', () => {
    it('교습 의도 발화를 감지', () => {
        expect(detectLanguageTutorIntent('고마워 일본어로 뭐라고 해?')).toBe(true);
        expect(detectLanguageTutorIntent('how do you say hello in french')).toBe(true);
        expect(detectLanguageTutorIntent('이거 영어로 번역해줘')).toBe(true);
    });

    it('일상 대화는 교습으로 오인하지 않음', () => {
        expect(detectLanguageTutorIntent('오늘 점심 뭐 먹지')).toBe(false);
        expect(detectLanguageTutorIntent('')).toBe(false);
    });
});

describe('resolveTargetLanguageFromText — 50개국', () => {
    it("한국어 'X어로' 패턴", () => {
        expect(resolveTargetLanguageFromText('일본어로 뭐라고 해')).toBe('ja');
        expect(resolveTargetLanguageFromText('프랑스어로 알려줘')).toBe('fr');
        expect(resolveTargetLanguageFromText('베트남어로는 어떻게 말해')).toBe('vi');
    });

    it("영어 'in X' 패턴", () => {
        expect(resolveTargetLanguageFromText('how do you say hello in spanish')).toBe('es');
        expect(resolveTargetLanguageFromText('say thank you in german')).toBe('de');
    });

    it('대상 언어가 없으면 null', () => {
        expect(resolveTargetLanguageFromText('그냥 잡담이야')).toBeNull();
        expect(resolveTargetLanguageFromText('')).toBeNull();
    });
});

describe('buildLanguagePair / Label', () => {
    it('지정↔대상 언어쌍 구성', () => {
        const pair = buildLanguagePair('ko', 'ja');
        expect(pair.sourceLang).toBe('ko');
        expect(pair.targetLang).toBe('ja');
        expect(pair.sourceLabel).toBe('한국어');
        expect(pair.targetLabel).toBe('日本語');
    });

    it('동일 언어면 보정(ko↔en)', () => {
        expect(buildLanguagePair('ko', 'ko').targetLang).toBe('en');
        expect(buildLanguagePair('en', 'en').targetLang).toBe('ko');
    });

    it('표시 라벨', () => {
        expect(buildLanguagePairLabel('ko', 'ja')).toBe('한국어 ↔ 日本語');
    });

    it('50개국 지원 카운트 노출', () => {
        expect(TUTOR_SUPPORTED_LANGUAGE_COUNT).toBeGreaterThanOrEqual(50);
    });
});
