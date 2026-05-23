import { useCallback } from 'react';
/**
 * VoIP Full Auto 컨트롤러
 * - 앱 내부 숫자 다이얼패드 제공
 * - VoIP 시그널링 initiate 호출
 * - 기존 시스템 다이얼러 호출 제외 (in-app flow only)
 */

type VoipAutoCallInitPayload = {
    callee_phone?: string;
    callee_user_id?: number;
    callee_voice_id?: string;
    friend_id?: number;
    caller_id: string;
    session_id: string;
    mode?: string; // 'voip_full_auto'
    auto_relay?: boolean;
};

type VoipAutoCallInitResponse = {
    call_id: string;
    signaling_server: string;
    turn_servers: Array<{
        urls: string[];
        username?: string;
        credential?: string;
    }>;
    call_route?: string;
    phone_dialer_required?: boolean;
    fallback_dial_url?: string;
    user_message?: string;
    callee_app_online?: boolean;
    caller_voice_id?: string;
    callee_voice_id?: string;
    callee_user_id?: number;
    participant_role?: 'caller' | 'callee';
    display_label?: string;
    status?: string;
};

type VoipAutoController = {
    initiateVoipCall: (payload: VoipAutoCallInitPayload) => Promise<VoipAutoCallInitResponse>;
    validatePhoneNumber: (phone: string) => boolean;
};

// 로깅 헬퍼 함수
const logVoipIntent = (tag: string, message: string, details?: Record<string, any>) => {
    const timestamp = new Date().toISOString();
    const logEntry = {
        timestamp,
        tag: `[VOIP_INTENT_${tag}]`,
        message,
        details: details || {},
    };
    console.log(JSON.stringify(logEntry));
};

export function useVoipAutoController(apiBaseUrl: string, authToken: string): VoipAutoController {
    const validatePhoneNumber = useCallback((phone: string): boolean => {
        logVoipIntent('VALIDATE_START', '전화번호 유효성 검사 시작', { phone });

        const trimmed = phone.trim();
        if (!trimmed.startsWith('+')) {
            logVoipIntent('VALIDATE_FAIL', '전화번호 형식 오류: +국가번호로 시작하지 않음', { phone: trimmed });
            return false;
        }

        const digitOnly = trimmed.replace(/[^\d+]/g, '');
        const isValid = digitOnly.length >= 10 && digitOnly.length <= 15;

        logVoipIntent('VALIDATE_RESULT', '전화번호 유효성 검사 완료', {
            input: phone,
            trimmed,
            digitOnly,
            isValid,
        });

        return isValid;
    }, []);

    const initiateVoipCall = useCallback(async (payload: VoipAutoCallInitPayload): Promise<VoipAutoCallInitResponse> => {
        logVoipIntent('INITIATE_START', 'VoIP call initiate 시작', {
            callee_phone: payload.callee_phone,
            callee_user_id: payload.callee_user_id,
            callee_voice_id: payload.callee_voice_id,
            friend_id: payload.friend_id,
            caller_id: payload.caller_id,
            session_id: payload.session_id,
            mode: payload.mode || 'voip_full_auto',
            auto_relay: payload.auto_relay || false,
        });

        const hasAppTarget = Boolean(payload.callee_user_id || payload.callee_voice_id || payload.friend_id);
        if (!hasAppTarget && (!payload.callee_phone || !validatePhoneNumber(payload.callee_phone))) {
            logVoipIntent('INITIATE_VALIDATE_FAIL', 'callee_phone 유효성 실패', { callee_phone: payload.callee_phone });
            throw new Error('유효하지 않은 전화번호입니다. +국가번호 형식을 사용해주세요.');
        }

        if (!authToken) {
            logVoipIntent('INITIATE_NO_AUTH', '인증 토큰 없음', {});
            throw new Error('로그인이 필요합니다.');
        }

        try {
            logVoipIntent('INITIATE_REQUEST', 'API 요청 전송', {
                url: `${apiBaseUrl}/api/v1/voip/calls/initiate`,
                payload,
            });

            const response = await fetch(`${apiBaseUrl}/api/v1/voip/calls/initiate`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    callee_phone: payload.callee_phone,
                    callee_user_id: payload.callee_user_id,
                    callee_voice_id: payload.callee_voice_id,
                    friend_id: payload.friend_id,
                    caller_id: payload.caller_id,
                    session_id: payload.session_id,
                    mode: payload.mode || 'voip_full_auto',
                    auto_relay: payload.auto_relay ?? false,
                }),
            });

            logVoipIntent('INITIATE_RESPONSE', 'API 응답 수신', {
                status: response.status,
                statusText: response.statusText,
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const detail = data?.detail;
                const errorMessage = typeof detail === 'string'
                    ? detail
                    : typeof detail?.message === 'string'
                        ? detail.message
                        : `HTTP ${response.status}`;
                const error = new Error(`VoIP initiate 실패: ${errorMessage}`) as Error & {
                    code?: string;
                    fallbackDialUrl?: string;
                };
                if (typeof detail?.code === 'string') {
                    error.code = detail.code;
                }
                if (typeof detail?.fallback_dial_url === 'string') {
                    error.fallbackDialUrl = detail.fallback_dial_url;
                }
                logVoipIntent('INITIATE_ERROR', 'API 응답 오류', {
                    status: response.status,
                    detail: errorMessage,
                    code: error.code,
                });
                throw error;
            }

            logVoipIntent('INITIATE_SUCCESS', 'VoIP initiate 성공', {
                call_id: data.call_id,
                signaling_server: data.signaling_server,
            });

            // NOTE: Connection state logs (e.g., VOIP_CONNECTION_STATE_CONNECTED) should only be emitted
            // from voipCallClient.ts when actual WebRTC connection state changes occur.
            // Emitting them here at initiate time would be a false positive.

            return data as VoipAutoCallInitResponse;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            logVoipIntent('INITIATE_EXCEPTION', 'initiate 호출 중 예외 발생', {
                error: errorMessage,
            });
            console.log(JSON.stringify({
                timestamp: new Date().toISOString(),
                tag: '[VOIP_START_CALL_FAIL]',
                message: 'VoIP call initiate failed',
                error: errorMessage,
            }));
            throw error;
        }
    }, [validatePhoneNumber, apiBaseUrl, authToken]);

    return {
        initiateVoipCall,
        validatePhoneNumber,
    };
}
