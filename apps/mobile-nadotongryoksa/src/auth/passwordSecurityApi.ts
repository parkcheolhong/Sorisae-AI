export type RecoveryStartResponse = {
    recovery_session_token: string;
    masked_target: string;
    verification_channel: string;
    dev_otp_hint?: string;
};

export type RecoveryVerifyResponse = {
    reset_token: string;
};

function extractApiErrorMessage(detail: unknown, fallback: string): string {
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
    return fallback;
}

export async function startUserPasswordRecovery(
    apiBase: string,
    email: string,
    verificationChannel: 'email' | 'phone' = 'email',
    phoneNumber?: string,
): Promise<RecoveryStartResponse> {
    const response = await fetch(`${apiBase}/api/auth/recovery/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            scope: 'user',
            user_hint: email.trim(),
            verification_channel: verificationChannel,
            phone_number: verificationChannel === 'phone' ? phoneNumber?.trim() : undefined,
        }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(extractApiErrorMessage(data.detail, `인증 코드 발송 실패 (HTTP ${response.status})`));
    }
    return data as RecoveryStartResponse;
}

export async function verifyUserPasswordRecovery(
    apiBase: string,
    recoverySessionToken: string,
    verificationCode: string,
): Promise<RecoveryVerifyResponse> {
    const response = await fetch(`${apiBase}/api/auth/recovery/verify-identity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            recovery_session_token: recoverySessionToken,
            verification_code: verificationCode.trim(),
        }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(extractApiErrorMessage(data.detail, `인증 실패 (HTTP ${response.status})`));
    }
    return data as RecoveryVerifyResponse;
}

export async function resetUserPasswordViaRecovery(
    apiBase: string,
    resetToken: string,
    newPassword: string,
): Promise<void> {
    const response = await fetch(`${apiBase}/api/auth/recovery/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            scope: 'user',
            reset_token: resetToken,
            new_password: newPassword,
        }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(extractApiErrorMessage(data.detail, `비밀번호 재설정 실패 (HTTP ${response.status})`));
    }
}

export async function changeUserPassword(
    apiBase: string,
    token: string,
    currentPassword: string,
    newPassword: string,
): Promise<void> {
    const response = await fetch(`${apiBase}/api/auth/password/change`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
        }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(extractApiErrorMessage(data.detail, `비밀번호 변경 실패 (HTTP ${response.status})`));
    }
}
