/**
 * chatNarratorLanguage 재구성 모듈 검증 — 국가별 나레이터 언어 결정.
 */
import { resolveChatNarratorLang } from '../features/chat/chatNarratorLanguage';

describe('resolveChatNarratorLang 국가별 설정', () => {
    it('선호 언어가 있으면 최우선 사용', () => {
        expect(resolveChatNarratorLang({ countryCode: 'KR', preferredLanguage: 'en', viewerOutputLang: 'ko' })).toBe('en');
        expect(resolveChatNarratorLang({ countryCode: 'US', preferredLanguage: 'ja', viewerOutputLang: 'en' })).toBe('ja');
    });

    it('선호 언어가 없으면 국가 대표 언어', () => {
        expect(resolveChatNarratorLang({ countryCode: 'KR', viewerOutputLang: 'en' })).toBe('ko');
        expect(resolveChatNarratorLang({ countryCode: 'US', viewerOutputLang: 'ko' })).toBe('en');
        expect(resolveChatNarratorLang({ countryCode: 'JP', viewerOutputLang: 'ko' })).toBe('ja');
    });

    it('미지원 선호언어 + 미등록 국가는 영어 정책 폴백', () => {
        expect(resolveChatNarratorLang({ countryCode: 'XX', preferredLanguage: 'zz', viewerOutputLang: 'fr' })).toBe('en');
    });

    it('아무 값도 없으면 국가 정책 기본(en)', () => {
        expect(resolveChatNarratorLang({})).toBe('en');
        expect(resolveChatNarratorLang({ countryCode: '', preferredLanguage: '', viewerOutputLang: '' })).toBe('en');
    });

    it('대소문자·공백 정규화', () => {
        expect(resolveChatNarratorLang({ preferredLanguage: ' EN ' })).toBe('en');
        expect(resolveChatNarratorLang({ countryCode: 'jp' })).toBe('ja');
    });
});
