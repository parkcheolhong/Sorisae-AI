/**
 * [기능 분리 Phase6.0] 수신 채팅 읽어주기(read-aloud) — 순수 결정/정리 + 토글 영속.
 *
 * 사용자 명령(토글 ON)일 때만, 상대가 보낸 새 메시지를 음성으로 읽어준다.
 *  - sanitizeChatTextForSpeech: URL/마크다운/과도한 공백 제거 + 길이 상한(낭독 적합화).
 *  - shouldReadAloudIncoming: 토글 ON + 수신(내 메시지 아님) + 낭독 가능한 텍스트일 때만 true.
 * 실제 발화(expo-speech)와 메시지 수신 배선은 호출부(ChatRoomScreen)가 담당한다(디바이스 검증 동반).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

export const CHAT_READ_ALOUD_STORAGE_KEY = 'worldlinco_chat_read_aloud_enabled_v1';
export const CHAT_READ_ALOUD_MAX_LEN = 220;

/** 낭독용 텍스트 정리. 읽을 게 없으면 빈 문자열. */
export function sanitizeChatTextForSpeech(text: string | null | undefined): string {
    let s = String(text ?? '');
    s = s.replace(/https?:\/\/\S+/gi, ' ');          // URL 제거(읽지 않음)
    s = s.replace(/```[\s\S]*?```/g, ' ');            // 코드블록 제거
    s = s.replace(/[*_`#>~|]+/g, ' ');                // 마크다운 기호 제거
    s = s.replace(/\s+/g, ' ').trim();
    return s.slice(0, CHAT_READ_ALOUD_MAX_LEN).trim();
}

export interface ReadAloudDecisionInput {
    enabled: boolean;
    isIncoming: boolean;
    text: string | null | undefined;
}

/** 이번 수신 메시지를 읽어줄지 판정(순수). */
export function shouldReadAloudIncoming(input: ReadAloudDecisionInput): boolean {
    if (!input.enabled || !input.isIncoming) return false;
    return sanitizeChatTextForSpeech(input.text).length > 0;
}

const readAloudListeners = new Set<(enabled: boolean) => void>();

export function subscribeChatReadAloudEnabled(listener: (enabled: boolean) => void): () => void {
    readAloudListeners.add(listener);
    return () => {
        readAloudListeners.delete(listener);
    };
}

export async function loadChatReadAloudEnabled(): Promise<boolean> {
    try {
        return (await AsyncStorage.getItem(CHAT_READ_ALOUD_STORAGE_KEY)) === '1';
    } catch {
        return false;
    }
}

export async function saveChatReadAloudEnabled(enabled: boolean): Promise<boolean> {
    try {
        await AsyncStorage.setItem(CHAT_READ_ALOUD_STORAGE_KEY, enabled ? '1' : '0');
        readAloudListeners.forEach((fn) => {
            try { fn(enabled); } catch { /* no-op */ }
        });
        return true;
    } catch {
        return false;
    }
}
