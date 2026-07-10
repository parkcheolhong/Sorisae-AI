import {
    cleanVoiceTranscript,
    isVoiceAudioLongEnough,
    MIN_VOICE_BASE64_LEN,
    mergeTranscriptIntoDraft,
    resolveVoiceSttLangs,
} from '../features/chat/chatVoiceInput';

describe('resolveVoiceSttLangs', () => {
    it('fixes STT source to the speaker (self) language, never auto', () => {
        // 로컬 사용자가 말하므로 from 은 사용자 자신의 지정 언어로 고정한다(작동불능 회귀 방지).
        expect(resolveVoiceSttLangs('ja', 'ko').from).toBe('ja');
        expect(resolveVoiceSttLangs('EN', 'ko').from).toBe('en');
        expect(resolveVoiceSttLangs('auto', 'ko').from).not.toBe('auto');
    });

    it('uses bilingual mode when both languages are known and differ', () => {
        const r = resolveVoiceSttLangs('ko', 'ja');
        expect(r.mode).toBe('bilingual');
        expect(r.langA).toBe('ko');
        expect(r.langB).toBe('ja');
        expect(r.to).toBe('ja');
    });

    it('uses designated mode (self-fixed) when only one language is known', () => {
        const r = resolveVoiceSttLangs('ja', undefined);
        expect(r.mode).toBe('designated');
        expect(r.from).toBe('ja');
        expect(r.to).toBe('ja');
    });

    it('uses designated mode when both languages are identical', () => {
        const r = resolveVoiceSttLangs('ko', 'ko');
        expect(r.mode).toBe('designated');
        expect(r.from).toBe('ko');
    });

    it('falls back to ko when self language is empty or auto', () => {
        expect(resolveVoiceSttLangs(undefined, undefined).from).toBe('ko');
        expect(resolveVoiceSttLangs('', '').from).toBe('ko');
        expect(resolveVoiceSttLangs('auto', 'auto').from).toBe('ko');
    });
});

describe('cleanVoiceTranscript', () => {
    it('trims and collapses whitespace', () => {
        expect(cleanVoiceTranscript('  안녕   하세요  ')).toBe('안녕 하세요');
    });

    it('removes control characters', () => {
        expect(cleanVoiceTranscript('hi\u0000\u0007there')).toBe('hi there');
    });

    it('returns empty string for nullish input', () => {
        expect(cleanVoiceTranscript(undefined)).toBe('');
        expect(cleanVoiceTranscript(null)).toBe('');
    });
});

describe('mergeTranscriptIntoDraft', () => {
    it('returns transcript when draft is empty', () => {
        expect(mergeTranscriptIntoDraft('', '안녕하세요')).toBe('안녕하세요');
        expect(mergeTranscriptIntoDraft('   ', '안녕하세요')).toBe('안녕하세요');
    });

    it('appends transcript with a single space when draft has text', () => {
        expect(mergeTranscriptIntoDraft('먼저 ', '추가')).toBe('먼저 추가');
        expect(mergeTranscriptIntoDraft('먼저', '추가')).toBe('먼저 추가');
    });

    it('keeps draft unchanged when transcript is blank', () => {
        expect(mergeTranscriptIntoDraft('그대로', '   ')).toBe('그대로');
    });
});

describe('isVoiceAudioLongEnough', () => {
    it('rejects short or missing audio', () => {
        expect(isVoiceAudioLongEnough(undefined)).toBe(false);
        expect(isVoiceAudioLongEnough('')).toBe(false);
        expect(isVoiceAudioLongEnough('a'.repeat(MIN_VOICE_BASE64_LEN - 1))).toBe(false);
    });

    it('accepts audio at or above the minimum length', () => {
        expect(isVoiceAudioLongEnough('a'.repeat(MIN_VOICE_BASE64_LEN))).toBe(true);
    });
});
