// 전화번호 정규화 키 SSOT(순수 · react-native 비의존).
// - 숫자만 남기고 국제/지역 형식 차이를 흡수하기 위해 끝 9자리를 매칭 키로 쓴다.
//   (한국 010-1234-5678 ↔ +82 10 1234 5678 ↔ 0212345678 등 형식이 달라도 끝자리로 일치).
// - deviceContacts / contactFriendMatch 등 여러 곳이 동일 규칙을 공유한다.
export function normalizePhoneKey(raw?: string | null): string {
    const digits = String(raw ?? '').replace(/[^\d]/g, '');
    if (!digits) {
        return '';
    }
    // 선행 0(국내 트렁크) 제거 후 끝 9자리 사용. 9자리 미만이면 있는 그대로.
    const trimmed = digits.replace(/^0+/, '');
    const core = trimmed.length >= 9 ? trimmed.slice(-9) : trimmed;
    return core;
}
