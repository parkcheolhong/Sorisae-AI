'use client';

import { useState, useCallback, useEffect } from 'react';
import { MarketplaceLeftRail } from '@/components/marketplace/marketplace-rails';
import { SubscriptionStatusCard } from '@/components/marketplace/subscription-status-card';
import {
    fetchSubscriptionCatalog,
    fetchMySubscription,
    cancelSubscription,
    resumeSubscription,
    createCheckoutSession,
    SubscriptionCatalogItem,
    SubscriptionStatusResponse,
    SUBSCRIPTION_STATUS_LABEL,
} from '@/lib/subscription-service';

export default function SubscriptionPage() {
    const [catalog, setCatalog] = useState<SubscriptionCatalogItem[]>([]);
    const [selectedProductCode, setSelectedProductCode] = useState<string | null>(null);
    const [data, setData] = useState<SubscriptionStatusResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [actionMsg, setActionMsg] = useState<string | null>(null);

    // 토큰은 localStorage의 customer_token 사용
    const getToken = (): string => {
        if (typeof window === 'undefined') return '';
        return localStorage.getItem('customer_token') ?? '';
    };

    const load = useCallback(async (forcedProductCode?: string) => {
        const token = getToken();
        if (!token) {
            setError('로그인이 필요합니다.');
            return;
        }
        try {
            setError(null);
            const fetchedCatalog = await fetchSubscriptionCatalog(token);
            setCatalog(fetchedCatalog);

            const resolvedProductCode = forcedProductCode
                ?? selectedProductCode
                ?? fetchedCatalog[0]?.product_code
                ?? null;

            if (!resolvedProductCode) {
                setData(null);
                return;
            }

            setSelectedProductCode(resolvedProductCode);
            const result = await fetchMySubscription(resolvedProductCode, token);
            setData(result);
        } catch (err: any) {
            setError(err?.message ?? '구독 정보를 불러올 수 없습니다.');
        }
    }, [selectedProductCode]);

    useEffect(() => {
        if (typeof window === 'undefined') {
            void load();
            return;
        }
        const currentUrl = new URL(window.location.href);
        const productCode = currentUrl.searchParams.get('product') || undefined;
        void load(productCode);
    }, [load]);

    useEffect(() => {
        if (typeof window === 'undefined') return;

        const currentUrl = new URL(window.location.href);
        const checkoutState = currentUrl.searchParams.get('checkout');
        const checkoutProductCode = currentUrl.searchParams.get('product');
        if (!checkoutState) return;

        if (checkoutState === 'success') {
            setError(null);
            setActionMsg('결제가 완료되어 구독 상태를 새로고침했습니다.');
            void load(checkoutProductCode ?? undefined);
        } else if (checkoutState === 'cancel') {
            setError(null);
            setActionMsg('결제가 취소되었습니다. 원하시면 다시 시도해 주세요.');
        } else {
            setError('알 수 없는 결제 상태가 전달되었습니다. 다시 시도해 주세요.');
        }

        currentUrl.searchParams.delete('checkout');
        const nextUrl = `${currentUrl.pathname}${currentUrl.searchParams.toString() ? `?${currentUrl.searchParams.toString()}` : ''}`;
        window.history.replaceState({}, '', nextUrl);
    }, [load]);

    const handleCancel = useCallback(async () => {
        const token = getToken();
        if (!token) { setError('로그인이 필요합니다.'); return; }
        if (!selectedProductCode) { setError('서비스군을 먼저 선택해 주세요.'); return; }
        setLoading(true);
        setActionMsg(null);
        try {
            setError(null);
            const result = await cancelSubscription(token, selectedProductCode);
            setData(result);
            setActionMsg('구독 해지가 예약되었습니다. 현재 기간 종료 후 자동 해지됩니다.');
        } catch (err: any) {
            setError(err?.message ?? '해지 처리 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    }, [selectedProductCode]);

    const handleResume = useCallback(async () => {
        const token = getToken();
        if (!token) { setError('로그인이 필요합니다.'); return; }
        if (!selectedProductCode) { setError('서비스군을 먼저 선택해 주세요.'); return; }
        setLoading(true);
        setActionMsg(null);
        try {
            setError(null);
            const result = await resumeSubscription(token, selectedProductCode);
            setData(result);
            setActionMsg('구독이 재개되었습니다.');
        } catch (err: any) {
            setError(err?.message ?? '재개 처리 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    }, [selectedProductCode]);

    const handleStartSubscription = useCallback(async () => {
        const token = getToken();
        if (!token) { setError('로그인이 필요합니다.'); return; }
        if (!selectedProductCode) { setError('서비스군을 먼저 선택해 주세요.'); return; }
        const selectedProduct = catalog.find((item) => item.product_code === selectedProductCode) ?? null;
        const activePlan = selectedProduct?.active_plan ?? null;
        if (!activePlan?.plan_code) {
            setError('선택한 서비스군의 결제 플랜 정보를 찾을 수 없습니다.');
            return;
        }
        setLoading(true);
        setActionMsg(null);
        try {
            setError(null);
            const origin = typeof window !== 'undefined' ? window.location.origin : '';
            const session = await createCheckoutSession(
                {
                    product_code: selectedProductCode,
                    plan_code: activePlan.plan_code,
                    success_url: `${origin}/marketplace/subscription?checkout=success&product=${encodeURIComponent(selectedProductCode)}`,
                    cancel_url: `${origin}/marketplace/subscription?checkout=cancel&product=${encodeURIComponent(selectedProductCode)}`,
                },
                token,
            );
            // 체크아웃 URL 로 이동
            window.location.href = session.checkout_url;
        } catch (err: any) {
            setError(err?.message ?? '결제 페이지 연결 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    }, [catalog, selectedProductCode]);

    const handleSelectProduct = useCallback(async (productCode: string) => {
        const token = getToken();
        if (!token) {
            setError('로그인이 필요합니다.');
            return;
        }
        setSelectedProductCode(productCode);
        setActionMsg(null);
        setLoading(true);
        try {
            setError(null);
            const result = await fetchMySubscription(productCode, token);
            setData(result);
        } catch (err: any) {
            setError(err?.message ?? '구독 정보를 불러올 수 없습니다.');
        } finally {
            setLoading(false);
        }
    }, []);

    const selectedCatalogItem = catalog.find((item) => item.product_code === selectedProductCode) ?? null;

    return (
        <div className="workspace-shell">
            <MarketplaceLeftRail activeRailId="subscription" />

            <main className="workspace-stage">
                <div className="workspace-topbar">
                    <div>
                        <p className="workspace-overline">월 구독 관리</p>
                        <h1 className="workspace-page-title">구독 관리</h1>
                        <p className="workspace-page-description">
                            현재 구독 상태를 확인하고 구독을 시작·해지·재개할 수 있습니다.
                        </p>
                    </div>
                    <div className="workspace-topbar-actions">
                        <button
                            onClick={() => { void load(); }}
                            className="workspace-secondary-button"
                            style={{ fontSize: 12 }}
                            disabled={loading}
                        >
                            새로고침
                        </button>
                    </div>
                </div>

                {/* 오류 메시지 */}
                {error && (
                    <div
                        style={{
                            background: '#fef2f2',
                            border: '1px solid #fca5a5',
                            borderRadius: 8,
                            padding: '10px 16px',
                            color: '#991b1b',
                            fontSize: 13,
                            marginBottom: 20,
                        }}
                    >
                        {error}
                    </div>
                )}

                {/* 액션 결과 메시지 */}
                {actionMsg && (
                    <div
                        style={{
                            background: '#f0fdf4',
                            border: '1px solid #6ee7b7',
                            borderRadius: 8,
                            padding: '10px 16px',
                            color: '#065f46',
                            fontSize: 13,
                            marginBottom: 20,
                        }}
                    >
                        ✅ {actionMsg}
                    </div>
                )}

                {/* 구독 상태 카드 */}
                <section style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 12 }}>서비스군 월정액</h2>
                    {catalog.length > 0 ? (
                        <div
                            style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                                gap: 12,
                            }}
                        >
                            {catalog.map((item) => {
                                const selected = item.product_code === selectedProductCode;
                                const amount = item.active_plan?.amount_minor ?? 0;
                                const currency = item.active_plan?.currency ?? 'KRW';
                                const monthlyPrice = new Intl.NumberFormat('ko-KR').format(Math.max(0, amount));
                                return (
                                    <button
                                        key={item.product_code}
                                        type="button"
                                        onClick={() => { void handleSelectProduct(item.product_code); }}
                                        style={{
                                            textAlign: 'left',
                                            borderRadius: 12,
                                            border: selected ? '2px solid #111827' : '1px solid #e5e7eb',
                                            background: selected ? '#f9fafb' : '#ffffff',
                                            padding: '14px 14px',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        <div style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
                                            {item.product_name}
                                        </div>
                                        <div style={{ fontSize: 12, color: '#4b5563', minHeight: 34 }}>
                                            {item.product_description || '서비스군 월정액 구독'}
                                        </div>
                                        <div style={{ marginTop: 8, fontSize: 13, fontWeight: 700, color: '#111827' }}>
                                            월 {monthlyPrice} {currency}
                                        </div>
                                        <div style={{ marginTop: 6, fontSize: 11, color: '#6b7280' }}>
                                            상태: {SUBSCRIPTION_STATUS_LABEL[item.subscription_status] ?? item.subscription_status}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    ) : (
                        <div style={{ color: '#6b7280', fontSize: 14 }}>서비스군 정보를 불러오는 중...</div>
                    )}
                </section>

                {data && selectedCatalogItem ? (
                    <>
                        <div style={{ marginBottom: 10, fontSize: 13, color: '#374151' }}>
                            선택 서비스군: <strong>{selectedCatalogItem.product_name}</strong>
                        </div>
                    <SubscriptionStatusCard
                        data={data}
                        onCancel={handleCancel}
                        onResume={handleResume}
                        onStartSubscription={handleStartSubscription}
                        loading={loading}
                    />
                    </>
                ) : !error ? (
                    <div style={{ color: '#6b7280', fontSize: 14 }}>구독 정보를 불러오는 중...</div>
                ) : null}

                {/* 구독 기능 안내 */}
                <div style={{ marginTop: 36 }}>
                    <h2 style={{ fontSize: 15, fontWeight: 700, color: '#374151', marginBottom: 12 }}>
                        구독 혜택
                    </h2>
                    <ul style={{ fontSize: 13, color: '#6b7280', lineHeight: '2', paddingLeft: 18 }}>
                        <li>서비스군별 월정액 결제 및 개별 해지/재개</li>
                        <li>서비스군별 권한(Entitlement) 분리 적용</li>
                        <li>웹 결제(Stripe) 체크아웃 연동</li>
                        <li>결제 후 즉시 구독 상태 새로고침</li>
                        <li>구독 상태 기반 접근 제어</li>
                    </ul>
                </div>
            </main>
        </div>
    );
}
