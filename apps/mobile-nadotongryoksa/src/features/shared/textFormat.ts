/**
 * [기능 분리 Phase5.6f] 공용 텍스트/API 유틸 SSOT.
 *
 * App.tsx 인라인의 범용 문자열 헬퍼(템플릿 치환/API 에러 메시지 추출/토큰 요약)를 분리한다.
 * 특정 기능에 속하지 않는 순수 유틸 — 단위 테스트로 회귀 가드.
 */

/** `{key}` 플레이스홀더를 values 로 치환(누락 키는 빈 문자열). */
export function formatStatusText(template: string, values: Record<string, string>): string {
    return template.replace(/\{(\w+)\}/g, (_whole, key: string) => values[key] ?? '');
}

/** FastAPI/서버 에러 응답(detail: string|array|object)에서 사람이 읽을 메시지를 추출(없으면 fallback). */
export function extractApiErrorMessage(detail: unknown, fallback: string): string {
    if (typeof detail === 'string' && detail.trim()) {
        return detail.trim();
    }
    if (Array.isArray(detail)) {
        const messages = detail
            .map((item) => {
                if (typeof item === 'string') {
                    return item.trim();
                }
                if (item && typeof item === 'object') {
                    const { msg } = item as { msg?: unknown };
                    if (typeof msg === 'string' && msg.trim()) {
                        return msg.trim();
                    }
                }
                return '';
            })
            .filter(Boolean);
        if (messages.length > 0) {
            return messages.join(', ');
        }
    }
    if (detail && typeof detail === 'object') {
        const candidate =
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).detail ??
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).message ??
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).error ??
            (detail as { detail?: unknown; message?: unknown; error?: unknown; msg?: unknown }).msg;
        if (typeof candidate === 'string' && candidate.trim()) {
            return candidate.trim();
        }
    }
    return fallback;
}

/** 인증 토큰을 로그-안전한 요약 문자열로 변환(길이 + 앞뒤 6자만 노출). */
export function summarizeAuthToken(token: string): string {
    const normalized = token.trim();
    if (!normalized) {
        return 'empty';
    }

    if (normalized.length <= 12) {
        return `len:${normalized.length}:${normalized}`;
    }

    return `len:${normalized.length}:${normalized.slice(0, 6)}...${normalized.slice(-6)}`;
}
