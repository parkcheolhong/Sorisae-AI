'use client';

import {
    SubscriptionStatusResponse,
    SubscriptionStatus,
    SUBSCRIPTION_STATUS_LABEL,
    SUBSCRIPTION_STATUS_VARIANT,
    isAccessAllowed,
} from '@/lib/subscription-service';

// ─── 배지 색상 맵 ──────────────────────────────────────────────────────────────

const BADGE_STYLE: Record<'success' | 'warning' | 'danger' | 'neutral', React.CSSProperties> = {
    success: { background: '#d1fae5', color: '#065f46', border: '1px solid #6ee7b7' },
    warning: { background: '#fef3c7', color: '#92400e', border: '1px solid #fbbf24' },
    danger: { background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5' },
    neutral: { background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db' },
};

type Props = {
    data: SubscriptionStatusResponse;
    onCancel: () => void;
    onResume: () => void;
    onStartSubscription: () => void;
    loading: boolean;
};

export function SubscriptionStatusCard({
    data,
    onCancel,
    onResume,
    onStartSubscription,
    loading,
}: Props) {
    const status = data.subscription_status as SubscriptionStatus;
    const variant = SUBSCRIPTION_STATUS_VARIANT[status] ?? 'neutral';
    const label = SUBSCRIPTION_STATUS_LABEL[status] ?? status;
    const allowed = isAccessAllowed(status);

    const periodEndFormatted = data.period_end
        ? new Date(data.period_end).toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        })
        : null;

    return (
        <div
            style={{
                background: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: 12,
                padding: '24px 28px',
                maxWidth: 580,
            }}
        >
            {/* 상태 배지 + 헤더 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                <span
                    style={{
                        ...BADGE_STYLE[variant],
                        borderRadius: 20,
                        padding: '3px 12px',
                        fontSize: 12,
                        fontWeight: 700,
                        letterSpacing: 0.3,
                    }}
                >
                    {label}
                </span>
                {data.cancel_at_period_end && (
                    <span
                        style={{
                            ...BADGE_STYLE['warning'],
                            borderRadius: 20,
                            padding: '3px 10px',
                            fontSize: 11,
                        }}
                    >
                        기간 종료 후 해지 예약
                    </span>
                )}
            </div>

            {/* 플랜 + 기간 정보 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 24px', marginBottom: 20 }}>
                <InfoRow label="제품" value={data.product_code ?? '-'} />
                <InfoRow label="플랜" value={data.plan_code ?? '-'} />
                <InfoRow label="기간 종료" value={periodEndFormatted ?? '-'} />
                <InfoRow
                    label="기기"
                    value={
                        data.device_limit > 0
                            ? `${data.active_device_count} / ${data.device_limit}`
                            : '-'
                    }
                />
            </div>

            {/* 유예 기간 경고 */}
            {status === 'grace_period' && (
                <div
                    style={{
                        background: '#fffbeb',
                        border: '1px solid #fbbf24',
                        borderRadius: 8,
                        padding: '10px 14px',
                        fontSize: 13,
                        color: '#92400e',
                        marginBottom: 20,
                    }}
                >
                    ⚠️ 결제가 실패하여 유예 기간 중입니다. 결제 수단을 확인해 주세요.
                </div>
            )}

            {/* 접근 제한 알림 */}
            {!allowed && status !== 'none' && (
                <div
                    style={{
                        background: '#fef2f2',
                        border: '1px solid #fca5a5',
                        borderRadius: 8,
                        padding: '10px 14px',
                        fontSize: 13,
                        color: '#991b1b',
                        marginBottom: 20,
                    }}
                >
                    ⛔ 현재 구독 상태로는 서비스 이용이 제한됩니다.
                </div>
            )}

            {/* 액션 버튼 */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {status === 'none' && (
                    <button
                        className="workspace-primary-button"
                        onClick={onStartSubscription}
                        disabled={loading}
                    >
                        구독 시작
                    </button>
                )}
                {(status === 'active' || status === 'trialing' || status === 'grace_period') &&
                    !data.cancel_at_period_end && (
                        <button
                            className="workspace-secondary-button"
                            onClick={onCancel}
                            disabled={loading}
                            style={{ color: '#dc2626' }}
                        >
                            {loading ? '처리 중…' : '구독 해지 예약'}
                        </button>
                    )}
                {data.cancel_at_period_end && (
                    <button
                        className="workspace-primary-button"
                        onClick={onResume}
                        disabled={loading}
                    >
                        {loading ? '처리 중…' : '해지 취소 (재개)'}
                    </button>
                )}
                {(status === 'canceled' || status === 'past_due' || status === 'suspended' || status === 'refunded') && (
                    <button
                        className="workspace-primary-button"
                        onClick={onStartSubscription}
                        disabled={loading}
                    >
                        다시 구독하기
                    </button>
                )}
            </div>
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{value}</div>
        </div>
    );
}
