// 단말 연락처 ↔ 앱 친구(사용자) 매칭 순수 헬퍼.
// - 연락처 전화번호를 정규화 키로 친구 목록과 대조해, 채팅을 바로 열 수 있는 앱 사용자인지 판별한다.
// - 매칭되면 채팅(친구), 아니면 SNS 초대로 분기한다.
import { normalizePhoneKey } from '../../services/phoneKey';
import type { Friend } from '../friends/types';

// 친구 전화번호 → 친구. friendUserId 가 있어야(앱 사용자) 채팅을 열 수 있다.
export function buildFriendPhoneIndex(friends: Friend[]): Map<string, Friend> {
    const index = new Map<string, Friend>();
    for (const friend of friends) {
        if (friend.friendUserId == null) {
            continue;
        }
        const key = normalizePhoneKey(friend.friendPhone);
        if (key && !index.has(key)) {
            index.set(key, friend);
        }
    }
    return index;
}

// 연락처 번호(여러 개 가능)로 친구를 찾는다. 가장 먼저 일치하는 친구를 반환.
export function matchFriendByPhones(
    index: Map<string, Friend>,
    phones: Array<string | null | undefined>,
): Friend | null {
    for (const phone of phones) {
        const key = normalizePhoneKey(phone);
        if (key) {
            const friend = index.get(key);
            if (friend) {
                return friend;
            }
        }
    }
    return null;
}

export type ContactChatAction =
    | { kind: 'chat'; friend: Friend }
    | { kind: 'invite' };

// 연락처에 대해 채팅(앱 친구) 또는 초대(미가입) 중 무엇을 할지 결정.
export function resolveContactChatAction(
    index: Map<string, Friend>,
    phones: Array<string | null | undefined>,
): ContactChatAction {
    const friend = matchFriendByPhones(index, phones);
    if (friend && friend.friendUserId != null) {
        return { kind: 'chat', friend };
    }
    return { kind: 'invite' };
}
