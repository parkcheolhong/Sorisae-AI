/**
 * 채팅 수신 메시지 낭독 대상 추출. [Phase6.0]
 * 텍스트 계열 메시지만 낭독하며, 뷰어 언어 번역본을 우선 사용한다.
 */
import type { ChatMessageItem } from './types';
import { sanitizeChatTextForSpeech } from '../sorisae/companionChatReadAloud';

export interface ReadAloudContent {
    text: string;
    lang: string;
}

/** 낭독 가능한 텍스트 계열 메시지 타입. */
const READABLE_MESSAGE_TYPES = new Set(['text', 'translation']);

function getEffectiveTranslatedBody(message: ChatMessageItem): string | null {
    return message.viewer_translation?.translated_body?.trim() || message.translated_body?.trim() || null;
}

export function pickReadAloudContent(message: ChatMessageItem, lang: string): ReadAloudContent {
    if (message.message_type && !READABLE_MESSAGE_TYPES.has(message.message_type)) {
        return { text: '', lang };
    }
    const translated = getEffectiveTranslatedBody(message);
    const raw = translated || message.body || '';
    return { text: sanitizeChatTextForSpeech(raw), lang };
}
