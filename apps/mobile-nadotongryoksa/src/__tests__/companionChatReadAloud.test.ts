import { describe, expect, it } from '@jest/globals';

import {
    CHAT_READ_ALOUD_MAX_LEN,
    sanitizeChatTextForSpeech,
    shouldReadAloudIncoming,
} from '../features/sorisae/companionChatReadAloud';

describe('sanitizeChatTextForSpeech', () => {
    it('URL/마크다운/공백 정리', () => {
        expect(sanitizeChatTextForSpeech('**안녕** 봐봐 https://x.com/a')).toBe('안녕 봐봐');
        expect(sanitizeChatTextForSpeech('   여러   공백   ')).toBe('여러 공백');
    });
    it('코드블록 제거', () => {
        expect(sanitizeChatTextForSpeech('보세요 ```code here``` 끝')).toBe('보세요 끝');
    });
    it('길이 상한', () => {
        expect(sanitizeChatTextForSpeech('가'.repeat(500)).length).toBe(CHAT_READ_ALOUD_MAX_LEN);
    });
    it('읽을 게 없으면 빈 문자열', () => {
        expect(sanitizeChatTextForSpeech('https://only.link')).toBe('');
        expect(sanitizeChatTextForSpeech('')).toBe('');
    });
});

describe('shouldReadAloudIncoming', () => {
    it('토글 ON + 수신 + 낭독가능 텍스트일 때만 true', () => {
        expect(shouldReadAloudIncoming({ enabled: true, isIncoming: true, text: '안녕' })).toBe(true);
    });
    it('토글 OFF면 false', () => {
        expect(shouldReadAloudIncoming({ enabled: false, isIncoming: true, text: '안녕' })).toBe(false);
    });
    it('내 메시지(수신 아님)면 false', () => {
        expect(shouldReadAloudIncoming({ enabled: true, isIncoming: false, text: '안녕' })).toBe(false);
    });
    it('읽을 텍스트 없으면 false', () => {
        expect(shouldReadAloudIncoming({ enabled: true, isIncoming: true, text: '   ' })).toBe(false);
    });
});
