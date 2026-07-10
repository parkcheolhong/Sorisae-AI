import {
    buildFriendPhoneIndex,
    matchFriendByPhones,
    resolveContactChatAction,
} from '../features/contacts/contactFriendMatch';
import type { Friend } from '../features/friends/types';

function makeFriend(over: Partial<Friend>): Friend {
    return {
        id: 1,
        userId: 100,
        friendUserId: 200,
        friendUsername: 'tester',
        friendEmail: 't@example.com',
        addedAt: '2026-01-01T00:00:00Z',
        ...over,
    };
}

describe('buildFriendPhoneIndex', () => {
    it('indexes only friends that are app users (friendUserId present)', () => {
        const index = buildFriendPhoneIndex([
            makeFriend({ friendUserId: 200, friendPhone: '010-1234-5678' }),
            makeFriend({ id: 2, friendUserId: null, friendPhone: '010-9999-8888' }),
        ]);
        expect(index.size).toBe(1);
        // 미가입(friendUserId=null) 연락처는 매칭되지 않는다.
        expect(matchFriendByPhones(index, ['010-9999-8888'])).toBeNull();
    });

    it('matches across different phone formats via normalized key', () => {
        const friend = makeFriend({ friendPhone: '+82 10-1234-5678' });
        const index = buildFriendPhoneIndex([friend]);
        const matched = matchFriendByPhones(index, ['010-1234-5678']);
        expect(matched).toBe(friend);
    });
});

describe('resolveContactChatAction', () => {
    it('returns chat action when a phone matches an app friend', () => {
        const friend = makeFriend({ friendPhone: '01012345678' });
        const index = buildFriendPhoneIndex([friend]);
        const action = resolveContactChatAction(index, ['010-1234-5678']);
        expect(action.kind).toBe('chat');
        expect(action.kind === 'chat' && action.friend).toBe(friend);
    });

    it('returns invite action when no friend matches', () => {
        const index = buildFriendPhoneIndex([makeFriend({ friendPhone: '01011112222' })]);
        const action = resolveContactChatAction(index, ['010-3333-4444']);
        expect(action.kind).toBe('invite');
    });
});
