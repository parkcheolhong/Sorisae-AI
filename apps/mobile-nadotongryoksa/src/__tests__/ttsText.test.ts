import { describe, expect, it } from '@jest/globals';

import { normalizeSpeakText, inferTtsLanguage } from '../features/tts/ttsText';

describe('normalizeSpeakText — 발화 직전 정규화', () => {
    it('(offline)/[offline] 마커를 대소문자 무관 제거하고 트림한다', () => {
        expect(normalizeSpeakText('안녕하세요 (offline)')).toBe('안녕하세요');
        expect(normalizeSpeakText('[OFFLINE] hello')).toBe('hello');
        expect(normalizeSpeakText('  여행 (Offline) 안내  ')).toBe('여행  안내');
    });

    it('마커가 없으면 트림만 한다', () => {
        expect(normalizeSpeakText('  hello world  ')).toBe('hello world');
    });
});

describe('inferTtsLanguage — 발화 로케일 SSOT 위임', () => {
    it('단일 언어 전용 스크립트가 새면 그 언어로 교정한다', () => {
        // en 타깃인데 한글/가나가 새면 해당 로케일로 발화(scriptLangResolver SSOT)
        expect(inferTtsLanguage('안녕하세요', 'en-US')).toBe('ko-KR');
        expect(inferTtsLanguage('こんにちは', 'en-US')).toBe('ja-JP');
        expect(inferTtsLanguage('สวัสดี', 'en-US')).toBe('th-TH');
        expect(inferTtsLanguage('שלום', 'en-US')).toBe('he-IL');
        expect(inferTtsLanguage('Γειά', 'en-US')).toBe('el-GR');
    });

    it('타깃과 스크립트가 일치하거나 모호하면 타깃 로케일을 유지한다', () => {
        expect(inferTtsLanguage('안녕', 'ko-KR')).toBe('ko-KR');
        expect(inferTtsLanguage('Hello', 'en-US')).toBe('en-US');
        expect(inferTtsLanguage('Bonjour', 'fr-FR')).toBe('fr-FR');
    });

    it('로케일 형식이 아닌 fallback 은 en-US 로 기본 처리한다', () => {
        expect(inferTtsLanguage('Hello', 'en')).toBe('en-US');
        expect(inferTtsLanguage('Hello', '')).toBe('en-US');
    });
});
