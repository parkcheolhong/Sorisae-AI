import type { UserInfo } from '../app/appTypes';

export function shouldForceHideLoginModal({
    token,
    userInfo,
}: {
    token: string;
    userInfo: UserInfo | null;
}): boolean {
    // 로그인 섹션은 만료/오래된 세션 상태로 강제 숨김 처리하지 않는다.
    // 앱은 사용자가 명시적으로 로그인 모달을 열거나 닫는 방식으로만 제어해야 한다.
    return false;
}
