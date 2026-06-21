import { describe, expect, it } from '@jest/globals';

import {
    correctTtsLocaleForScriptLeak,
    detectDominantScriptLang,
} from '../utils/scriptLangResolver';
import { resolveVoipTtsLocale } from '../constants/voipLanguageLocales';

describe('detectDominantScriptLang (백엔드 9-스크립트 미러)', () => {
    it('순수 단일 스크립트를 정확히 감지한다', () => {
        expect(detectDominantScriptLang('안녕하세요')).toBe('ko');
        expect(detectDominantScriptLang('こんにちは')).toBe('ja');
        expect(detectDominantScriptLang('你好世界')).toBe('zh');
        expect(detectDominantScriptLang('Здравствуйте')).toBe('ru');
        expect(detectDominantScriptLang('مرحبا')).toBe('ar');
        expect(detectDominantScriptLang('สวัสดี')).toBe('th');
        expect(detectDominantScriptLang('שלום')).toBe('he');
        expect(detectDominantScriptLang('नमस्ते')).toBe('hi');
        expect(detectDominantScriptLang('Γειά σου')).toBe('el');
    });

    it('가나가 하나라도 있으면 한자 다수여도 일본어로 본다', () => {
        expect(detectDominantScriptLang('日本語のテスト')).toBe('ja');
        expect(detectDominantScriptLang('漢字とかな')).toBe('ja');
    });

    it('라틴/숫자/기호 등 모호 스크립트는 null', () => {
        expect(detectDominantScriptLang('Hello world')).toBeNull();
        expect(detectDominantScriptLang('12345 !?')).toBeNull();
        expect(detectDominantScriptLang('')).toBeNull();
        expect(detectDominantScriptLang('café déjà')).toBeNull();
    });

    it('혼합 스크립트는 우세(다수) 스크립트를 따른다', () => {
        // 라틴은 카운트하지 않으므로 한글이 우세
        expect(detectDominantScriptLang('OK 안녕하세요 반갑습니다')).toBe('ko');
    });
});

describe('correctTtsLocaleForScriptLeak — 대면 inferTtsLanguage 회귀 보존', () => {
    const resolve = (lang: string) => resolveVoipTtsLocale(lang);

    it('기존 5종(ko/ja/th/he/el)은 동일 로케일을 유지한다', () => {
        expect(correctTtsLocaleForScriptLeak('안녕', 'en-US', resolve)).toBe('ko-KR');
        expect(correctTtsLocaleForScriptLeak('こんにちは', 'en-US', resolve)).toBe('ja-JP');
        expect(correctTtsLocaleForScriptLeak('สวัสดี', 'en-US', resolve)).toBe('th-TH');
        expect(correctTtsLocaleForScriptLeak('שלום', 'en-US', resolve)).toBe('he-IL');
        expect(correctTtsLocaleForScriptLeak('Γειά', 'en-US', resolve)).toBe('el-GR');
    });

    it('새로 추가된 4종(zh/ru/ar/hi)도 교정한다', () => {
        expect(correctTtsLocaleForScriptLeak('你好', 'en-US', resolve)).toBe('zh-CN');
        expect(correctTtsLocaleForScriptLeak('Здравствуйте', 'en-US', resolve)).toBe('ru-RU');
        expect(correctTtsLocaleForScriptLeak('مرحبا', 'en-US', resolve)).toBe('ar-SA');
        expect(correctTtsLocaleForScriptLeak('नमस्ते', 'en-US', resolve)).toBe('hi-IN');
    });

    it('타깃 언어와 스크립트가 일치하거나 모호하면 타깃 로케일 그대로', () => {
        expect(correctTtsLocaleForScriptLeak('안녕', 'ko-KR', resolve)).toBe('ko-KR');
        expect(correctTtsLocaleForScriptLeak('Hello', 'en-US', resolve)).toBe('en-US');
        expect(correctTtsLocaleForScriptLeak('Bonjour', 'fr-FR', resolve)).toBe('fr-FR');
    });
});

describe('resolveVoipTtsLocale — 텍스트 인식 스크립트 누수 교정(하위호환)', () => {
    it('text 미지정 시 기존 langCode 매핑 동작을 유지한다', () => {
        expect(resolveVoipTtsLocale('ko')).toBe('ko-KR');
        expect(resolveVoipTtsLocale('en')).toBe('en-US');
        expect(resolveVoipTtsLocale('zh-TW')).toBe('zh-TW');
        expect(resolveVoipTtsLocale('')).toBe('ko-KR');
        expect(resolveVoipTtsLocale('xx')).toBe('en-US');
    });

    it('지정 언어와 텍스트 스크립트가 다르면 실제 스크립트 로케일로 교정한다', () => {
        // en 타깃인데 한글 텍스트가 새면 ko-KR로 발화
        expect(resolveVoipTtsLocale('en', '안녕하세요')).toBe('ko-KR');
        expect(resolveVoipTtsLocale('ja', '你好')).toBe('zh-CN');
    });

    it('지정 언어와 텍스트 스크립트가 일치하면 교정하지 않는다', () => {
        expect(resolveVoipTtsLocale('ko', '안녕하세요')).toBe('ko-KR');
        expect(resolveVoipTtsLocale('en', 'Hello there')).toBe('en-US');
    });
});
