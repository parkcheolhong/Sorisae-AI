import {
    APP_DISPLAY_NAME,
    buildAppPromotionMessage,
    buildChatDeepLink,
    buildChatInviteMessage,
    buildInstallUrl,
    composeShareText,
    INSTALL_APK_PATH,
} from '../features/sns-share/snsShare';

describe('buildInstallUrl', () => {
    it('joins apiBase and the apk path, trimming trailing slashes', () => {
        expect(buildInstallUrl('https://api.example.com/')).toBe(`https://api.example.com${INSTALL_APK_PATH}`);
        expect(buildInstallUrl('https://api.example.com')).toBe(`https://api.example.com${INSTALL_APK_PATH}`);
    });

    it('returns empty string when apiBase is missing', () => {
        expect(buildInstallUrl(undefined)).toBe('');
        expect(buildInstallUrl('')).toBe('');
    });
});

describe('buildChatDeepLink', () => {
    it('builds a room deep link when roomId is given', () => {
        expect(buildChatDeepLink('room-123')).toBe('worldlingo://chat/room-123');
    });

    it('falls back to the chat root without a roomId', () => {
        expect(buildChatDeepLink(undefined)).toBe('worldlingo://chat');
        expect(buildChatDeepLink('')).toBe('worldlingo://chat');
    });
});

describe('buildChatInviteMessage', () => {
    it('includes the app name by default', () => {
        expect(buildChatInviteMessage()).toContain(APP_DISPLAY_NAME);
    });

    it('greets the contact and credits the inviter when provided', () => {
        const msg = buildChatInviteMessage({ contactName: '철수', inviterName: '영희' });
        expect(msg.startsWith('철수님, ')).toBe(true);
        expect(msg).toContain('영희님이 ');
    });
});

describe('buildAppPromotionMessage', () => {
    it('includes the app name and a value proposition', () => {
        const msg = buildAppPromotionMessage();
        expect(msg).toContain(APP_DISPLAY_NAME);
        expect(msg).toContain('통번역');
    });

    it('credits the inviter as a recommender when provided', () => {
        const msg = buildAppPromotionMessage({ inviterName: '영희' });
        expect(msg).toContain('영희님이 추천하는');
    });
});

describe('composeShareText', () => {
    it('appends the url on a new line when present', () => {
        expect(composeShareText('초대합니다', 'https://x')).toBe('초대합니다\nhttps://x');
    });

    it('returns the message alone when url is blank', () => {
        expect(composeShareText('초대합니다', '')).toBe('초대합니다');
        expect(composeShareText('초대합니다', undefined)).toBe('초대합니다');
    });
});
