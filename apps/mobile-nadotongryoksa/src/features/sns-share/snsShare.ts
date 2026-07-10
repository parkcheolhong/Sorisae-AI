// SNS 연동 공유 SSOT.
// - 카카오톡/라인/문자 등 단말에 설치된 공유 대상(OS 공유 시트)으로 초대/메시지를 보낸다.
// - 외부 SNS SDK·OAuth 없이 React Native 표준 Share API + 설치/딥링크 URL 만으로 동작한다.
// - 메시지/URL 생성은 순수 함수로 분리해 테스트한다(부수효과는 shareChatInvite 만).
//   react-native 는 jest 변환 제외 대상이라, 순수 함수만 import 하는 테스트가 깨지지 않도록
//   Share 는 모듈 최상단에서 import 하지 않고 호출 시점에 동적 로드한다.

export const APP_DISPLAY_NAME = 'WorldLinco';
// 마켓 배포 APK 경로(앱 내 업데이트와 동일 SSOT) — 미설치 상대를 위한 설치 링크.
export const INSTALL_APK_PATH = '/api/marketplace/latest.apk';

function normalizeBase(apiBase?: string | null): string {
    return String(apiBase ?? '').replace(/\/+$/, '');
}

// 미설치 상대용 설치 링크. apiBase 가 비면 빈 문자열(링크 생략).
export function buildInstallUrl(apiBase?: string | null): string {
    const base = normalizeBase(apiBase);
    return base ? `${base}${INSTALL_APK_PATH}` : '';
}

// 앱 사용자(친구)를 바로 채팅으로 여는 딥링크. 미설치 상대에겐 무시되고 설치 링크가 안내된다.
export function buildChatDeepLink(roomId?: string | null): string {
    const trimmed = String(roomId ?? '').trim();
    return trimmed ? `worldlingo://chat/${encodeURIComponent(trimmed)}` : 'worldlingo://chat';
}

export interface ChatInviteMessageOptions {
    inviterName?: string | null;
    contactName?: string | null;
    appName?: string;
}

// 초대 본문(링크 제외). 호칭이 있으면 인사에 반영한다.
export function buildChatInviteMessage(opts: ChatInviteMessageOptions = {}): string {
    const appName = (opts.appName ?? APP_DISPLAY_NAME).trim() || APP_DISPLAY_NAME;
    const contact = String(opts.contactName ?? '').trim();
    const inviter = String(opts.inviterName ?? '').trim();
    const greeting = contact ? `${contact}님, ` : '';
    const from = inviter ? `${inviter}님이 ` : '';
    return `${greeting}${from}${appName}에서 함께 대화해요! 50개국 실시간 통번역 채팅·통화 앱입니다.`;
}

// 공유 시트에 넘길 최종 텍스트(본문 + 링크). 링크가 비면 본문만.
export function composeShareText(message: string, url?: string | null): string {
    const trimmedUrl = String(url ?? '').trim();
    if (!trimmedUrl) {
        return message;
    }
    return `${message}\n${trimmedUrl}`;
}

export interface ShareChatInviteOptions extends ChatInviteMessageOptions {
    apiBase?: string | null;
    roomId?: string | null;
    // 앱 사용자(친구) 초대면 채팅 딥링크를, 아니면 설치 링크를 우선한다.
    isAppUser?: boolean;
}

export interface ShareResult {
    shared: boolean;
}

// 표준 OS 공유 시트로 초대 메시지를 보낸다(카카오톡/라인/문자 등 사용자가 선택).
export async function shareChatInvite(opts: ShareChatInviteOptions = {}): Promise<ShareResult> {
    const message = buildChatInviteMessage(opts);
    const installUrl = buildInstallUrl(opts.apiBase);
    const url = opts.isAppUser ? buildChatDeepLink(opts.roomId) || installUrl : installUrl;
    const text = composeShareText(message, url);
    try {
        const { Share } = await import('react-native');
        const result = await Share.share({ message: text });
        return { shared: result.action === Share.sharedAction };
    } catch {
        return { shared: false };
    }
}

export interface AppPromotionMessageOptions {
    appName?: string;
    inviterName?: string | null;
}

// 프로그램 홍보 본문(링크 제외) — 불특정 다수 대상 SNS(카카오톡/라인/페북/인스타/X 등) 공유용.
// 1:1 초대(buildChatInviteMessage)와 달리 앱의 핵심 가치를 한 줄 카피로 전달한다.
export function buildAppPromotionMessage(opts: AppPromotionMessageOptions = {}): string {
    const appName = (opts.appName ?? APP_DISPLAY_NAME).trim() || APP_DISPLAY_NAME;
    const inviter = String(opts.inviterName ?? '').trim();
    const from = inviter ? `${inviter}님이 추천하는 ` : '';
    return (
        `${from}${appName} — 50개국 실시간 통번역 채팅·음성통화 앱 📞💬\n` +
        '말이 통하지 않아도 전 세계 누구와도 대화하세요. 지금 설치하고 무료로 써보세요!'
    );
}

export interface ShareAppPromotionOptions extends AppPromotionMessageOptions {
    apiBase?: string | null;
}

// 프로그램(앱) 홍보를 OS 공유 시트로 전파한다 — 사용자가 카카오톡/라인/문자/SNS 중 선택.
// 외부 SDK·광고 계정 없이 단말에 설치된 모든 공유 대상으로 즉시 홍보할 수 있다.
export async function shareAppPromotion(opts: ShareAppPromotionOptions = {}): Promise<ShareResult> {
    const message = buildAppPromotionMessage(opts);
    const installUrl = buildInstallUrl(opts.apiBase);
    const text = composeShareText(message, installUrl);
    try {
        const { Share } = await import('react-native');
        const result = await Share.share({ message: text });
        return { shared: result.action === Share.sharedAction };
    } catch {
        return { shared: false };
    }
}
