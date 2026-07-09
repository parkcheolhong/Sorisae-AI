import { describe, expect, it } from '@jest/globals';

import {
    LANGS,
    SUPPORTED_LANGUAGE_COUNT,
    getLangLabelText,
    isSupportedLangCode,
    WHISPER_LANG_MAP,
    normalizeDetectedLangCode,
    inferSpeechLangCode,
    resolveAutoTargetLang,
    resolvePreferredOutputLang,
    resolveVoipPeerTargetLang,
} from '../features/language/languageCatalog';

describe('languageCatalog — LANGS 카탈로그 무결성', () => {
    it('SUPPORTED_LANGUAGE_COUNT 는 LANGS 길이와 일치한다', () => {
        expect(SUPPORTED_LANGUAGE_COUNT).toBe(LANGS.length);
        expect(LANGS.length).toBeGreaterThanOrEqual(50);
    });

    it('언어 코드는 중복이 없다', () => {
        const codes = LANGS.map((item) => item.code);
        expect(new Set(codes).size).toBe(codes.length);
    });

    it('모든 항목은 label/code/tts 를 갖는다', () => {
        for (const item of LANGS) {
            expect(item.label.length).toBeGreaterThan(0);
            expect(item.code.length).toBeGreaterThan(0);
            expect(item.tts).toMatch(/^[a-z]{2,3}-[A-Z]{2}$/);
        }
    });
});

describe('getLangLabelText', () => {
    it('지원 코드는 라벨을 반환한다', () => {
        expect(getLangLabelText('ko')).toBe('한국어');
        expect(getLangLabelText('en')).toBe('English');
        expect(getLangLabelText('zh-tw')).toBe('繁體中文(台灣)');
        expect(getLangLabelText('zh-hk')).toBe('粵語(香港)');
    });
});

describe('isSupportedLangCode', () => {
    it('지원 코드는 true, 미지원은 false', () => {
        expect(isSupportedLangCode('ko')).toBe(true);
        expect(isSupportedLangCode('zh-tw')).toBe(true);
        expect(isSupportedLangCode('xx')).toBe(false);
        expect(isSupportedLangCode('')).toBe(false);
    });
});

describe('normalizeDetectedLangCode — 이름/별칭/로캘 → LangCode', () => {
    it('영문 언어명을 코드로 정규화한다', () => {
        expect(normalizeDetectedLangCode('Korean')).toBe('ko');
        expect(normalizeDetectedLangCode('english')).toBe('en');
        expect(normalizeDetectedLangCode('chinese_language')).toBe('zh');
    });

    it('한국어 별칭과 접미사를 정규화한다', () => {
        expect(normalizeDetectedLangCode('일본어')).toBe('ja');
        expect(normalizeDetectedLangCode('한국어')).toBe('ko');
        expect(normalizeDetectedLangCode('중국')).toBe('zh');
    });

    it('로캘/혼합 입력에서 베이스 코드를 추출한다', () => {
        expect(normalizeDetectedLangCode('en-US')).toBe('en');
        expect(normalizeDetectedLangCode('zh-CN')).toBe('zh');
        expect(normalizeDetectedLangCode('ko, en')).toBe('ko');
    });

    it('미인식/빈값은 null', () => {
        expect(normalizeDetectedLangCode('klingon')).toBeNull();
        expect(normalizeDetectedLangCode('')).toBeNull();
        expect(normalizeDetectedLangCode(null)).toBeNull();
        expect(normalizeDetectedLangCode(undefined)).toBeNull();
    });

    it('WHISPER_LANG_MAP 의 모든 값은 지원 코드다', () => {
        for (const code of Object.values(WHISPER_LANG_MAP)) {
            expect(isSupportedLangCode(code)).toBe(true);
        }
    });
});

describe('inferSpeechLangCode — 스크립트 기반 추정', () => {
    it('단일 스크립트를 정확히 추정한다', () => {
        expect(inferSpeechLangCode('안녕하세요')).toBe('ko');
        expect(inferSpeechLangCode('こんにちは')).toBe('ja');
        expect(inferSpeechLangCode('你好世界')).toBe('zh');
        expect(inferSpeechLangCode('مرحبا')).toBe('ar');
        expect(inferSpeechLangCode('नमस्ते')).toBe('hi');
        expect(inferSpeechLangCode('Здравствуйте')).toBe('ru');
        expect(inferSpeechLangCode('สวัสดี')).toBe('th');
    });

    it('라틴 특수문자로 유럽어를 추정한다', () => {
        expect(inferSpeechLangCode('¿Hola!')).toBe('es');
        expect(inferSpeechLangCode('Müller')).toBe('de');
        expect(inferSpeechLangCode('café déjà')).toBe('fr');
        expect(inferSpeechLangCode('São Paulo')).toBe('pt');
        expect(inferSpeechLangCode('Hello world')).toBe('en');
    });

    it('빈 문자열은 fallback 을 반환한다', () => {
        expect(inferSpeechLangCode('')).toBe('en');
        expect(inferSpeechLangCode('   ', 'ko')).toBe('ko');
    });
});

describe('resolveAutoTargetLang — 자동 타깃 결정', () => {
    it('타깃이 소스와 다르면 타깃을 유지한다', () => {
        expect(resolveAutoTargetLang('ko', 'en')).toBe('en');
        expect(resolveAutoTargetLang('ja', 'ko')).toBe('ko');
    });

    it('타깃이 소스와 같으면 보정한다(ko↔en, 그 외 ko)', () => {
        expect(resolveAutoTargetLang('ko', 'ko')).toBe('en');
        expect(resolveAutoTargetLang('en', 'en')).toBe('ko');
        expect(resolveAutoTargetLang('fr', 'fr')).toBe('ko');
    });
});

describe('resolveVoipPeerTargetLang — VoIP 상대 타깃 복구', () => {
    it('uses remote preferred language when it differs from my source', () => {
        expect(resolveVoipPeerTargetLang('ko', 'en', 'ja', 'JP')).toBe('ja');
    });

    it('falls back to remote country language when remote preferred is incorrectly same as my source', () => {
        expect(resolveVoipPeerTargetLang('ko', 'ko', 'ko', 'JP')).toBe('ja');
    });

    it('keeps same-language calls intact when remote country also resolves to my source language', () => {
        expect(resolveVoipPeerTargetLang('ko', 'ko', 'ko', 'KR')).toBe('en');
    });

    it('keeps designated output language stable even when spoken transcript is Korean', () => {
        const spokenDetected = inferSpeechLangCode('안녕하세요', 'ja');
        expect(spokenDetected).toBe('ko');

        const designatedOutput = resolvePreferredOutputLang('ja', 'ko');
        expect(designatedOutput).toBe('ja');

        const voipTarget = resolveVoipPeerTargetLang(designatedOutput, 'ko', 'ko', 'KR');
        expect(voipTarget).toBe('ko');
        // local designated output should not be overwritten by detected input script.
        expect(designatedOutput).toBe('ja');
    });
});

describe('resolvePreferredOutputLang — preferred_language는 출력 언어 SSOT', () => {
    it('uses preferred language as output language when supported', () => {
        expect(resolvePreferredOutputLang('ja', 'ko')).toBe('ja');
        expect(resolvePreferredOutputLang('EN', 'ko')).toBe('en');
    });

    it('falls back to current output language when preferred is missing/invalid', () => {
        expect(resolvePreferredOutputLang('', 'ko')).toBe('ko');
        expect(resolvePreferredOutputLang('xx', 'ko')).toBe('ko');
        expect(resolvePreferredOutputLang(undefined, 'ja')).toBe('ja');
    });
});
