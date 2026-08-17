import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    createAdminAdReviewDraft,
    downloadAdminAdOrderVideo,
    previewAdminAdOrderVideo,
    retryAdminAdOrder,
    saveAdminAdOrderStoryboardReview,
    updateAdminAdReviewDraftItems,
    type AdminAdVideoOrderReviewDraft,
} from '@/lib/admin-ad-order-actions';
import {
    readAdminAdReviewFilterState,
    writeAdminAdReviewFilterState,
    findCurrentAdStoryboardModalDiff,
    findCurrentAdStoryboardModalIndex,
    matchesAdminAdReviewSceneFilter,
    moveAdminStoryboardModalCut,
    resetAdminAdReviewFilters,
    toggleAdminAdReviewFilter,
    type AdminAdReviewFilterState,
    type AdminStoryboardModalState,
} from '@/lib/admin-ad-review-state';
import { resolveAdminStoryboardPreviewSource } from '@/lib/admin-ad-production-analysis';
import { buildFallbackAdSettlementDashboard } from '@/lib/admin-ad-order-fallback';
import { buildAdminAutoConnectMeta } from '@/lib/admin-auto-connect';
import type { AdminAdOrderSettlementDashboard, AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type { LiveLogItem } from '@/lib/admin-runtime-types';

type AdOperationsPushLog = (level: LiveLogItem['level'], message: string, meta?: Partial<LiveLogItem> & { capabilityId?: string }) => void;

export type UseAdminAdOperationsControllerOptions = {
    apiBaseUrl: string;
    adVideoOrders: AdminAdVideoOrderItem[];
    adSettlementDashboard: AdminAdOrderSettlementDashboard | null;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    handleAdminUnauthorized: (message?: string) => void;
    loadDashboard: (isRefresh?: boolean) => Promise<void>;
    pushLiveLog: AdOperationsPushLog;
    downloadCsvFromRows: (filename: string, rows: string[][]) => void;
    adSettlementApiUnavailableRef: React.MutableRefObject<boolean>;
};

export function useAdminAdOperationsController(options: UseAdminAdOperationsControllerOptions) {
    const [expandedAdReviewOrderId, setExpandedAdReviewOrderId] = useState<number | null>(null);
    const [adReviewDrafts, setAdReviewDrafts] = useState<Record<number, AdminAdVideoOrderReviewDraft>>({});
    const [adReviewDiffOnly, setAdReviewDiffOnly] = useState<Record<number, boolean>>({});
    const [adReviewStatusDiffOnly, setAdReviewStatusDiffOnly] = useState<Record<number, boolean>>({});
    const [adReviewNoteDiffOnly, setAdReviewNoteDiffOnly] = useState<Record<number, boolean>>({});
    const [adReviewSavingId, setAdReviewSavingId] = useState<number | null>(null);
    const [adStoryboardModal, setAdStoryboardModal] = useState<AdminStoryboardModalState | null>(null);
    const [adPreviewLoadingId, setAdPreviewLoadingId] = useState<number | null>(null);
    const [adRetryingId, setAdRetryingId] = useState<number | null>(null);
    const [adPreviewOrder, setAdPreviewOrder] = useState<AdminAdVideoOrderItem | null>(null);
    const [adPreviewUrl, setAdPreviewUrl] = useState<string | null>(null);
    const [adPreviewError, setAdPreviewError] = useState<string | null>(null);
    const [adSettlementExporting, setAdSettlementExporting] = useState(false);

    useEffect(() => {
        try {
            const parsed = readAdminAdReviewFilterState();
            setAdReviewDiffOnly(parsed.diffOnly || {});
            setAdReviewStatusDiffOnly(parsed.statusDiffOnly || {});
            setAdReviewNoteDiffOnly(parsed.noteDiffOnly || {});
        } catch {
        }
    }, []);

    useEffect(() => {
        try {
            writeAdminAdReviewFilterState({
                diffOnly: adReviewDiffOnly,
                statusDiffOnly: adReviewStatusDiffOnly,
                noteDiffOnly: adReviewNoteDiffOnly,
            });
        } catch {
        }
    }, [adReviewDiffOnly, adReviewStatusDiffOnly, adReviewNoteDiffOnly]);

    useEffect(() => {
        return () => {
            if (adPreviewUrl) {
                window.URL.revokeObjectURL(adPreviewUrl);
            }
        };
    }, [adPreviewUrl]);

    useEffect(() => {
        if (!adStoryboardModal) {
            return;
        }

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'ArrowLeft') {
                event.preventDefault();
                moveAdStoryboardModalCut(-1);
            }
            if (event.key === 'ArrowRight') {
                event.preventDefault();
                moveAdStoryboardModalCut(1);
            }
            if (event.key === 'Escape') {
                event.preventDefault();
                setAdStoryboardModal(null);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [adStoryboardModal, options.adVideoOrders]);

    const closeAdPreview = useCallback(() => {
        setAdPreviewOrder(null);
        setAdPreviewError(null);
        setAdPreviewUrl((prev) => {
            if (prev) {
                window.URL.revokeObjectURL(prev);
            }
            return null;
        });
    }, []);

    const handlePreviewAdOrder = useCallback(async (order: AdminAdVideoOrderItem) => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return;
        }

        setAdPreviewLoadingId(order.id);
        setAdPreviewOrder(order);
        setAdPreviewError(null);
        try {
            const blob = await previewAdminAdOrderVideo({
                apiBaseUrl: options.apiBaseUrl,
                token,
                orderId: order.id,
            });
            const blobUrl = window.URL.createObjectURL(blob);
            setAdPreviewUrl((prev) => {
                if (prev) {
                    window.URL.revokeObjectURL(prev);
                }
                return blobUrl;
            });
        } catch (error: any) {
            if (error?.message === '__ADMIN_AD_ORDER_UNAUTHORIZED__') {
                options.handleAdminUnauthorized();
                return;
            }
            setAdPreviewError(error?.message || '영상 미리보기 로딩 중 오류가 발생했습니다.');
        } finally {
            setAdPreviewLoadingId(null);
        }
    }, [options]);

    const handleDownloadAdOrder = useCallback(async (order: AdminAdVideoOrderItem) => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return;
        }

        try {
            const blob = await downloadAdminAdOrderVideo({
                apiBaseUrl: options.apiBaseUrl,
                token,
                order,
                buildApiErrorMessage: options.buildApiErrorMessage,
            });
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = order.output_video_filename || order.output_filename || `ad_order_${order.id}.mp4`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(blobUrl);
            options.pushLiveLog('success', `광고 주문 #${order.id} 다운로드 완료`);
        } catch (error: any) {
            if (error?.message === '__ADMIN_AD_ORDER_UNAUTHORIZED__') {
                options.handleAdminUnauthorized();
                return;
            }
            options.pushLiveLog('warning', error?.message || `광고 주문 #${order.id} 다운로드 실패`);
        }
    }, [options]);

    const handleRetryAdOrder = useCallback(async (order: AdminAdVideoOrderItem) => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return;
        }

        setAdRetryingId(order.id);
        try {
            await retryAdminAdOrder({
                apiBaseUrl: options.apiBaseUrl,
                token,
                orderId: order.id,
                buildApiErrorMessage: options.buildApiErrorMessage,
            });
            options.pushLiveLog('success', `광고 주문 #${order.id} 재시도 시작`);
            await options.loadDashboard(true);
        } catch (error: any) {
            if (error?.message === '__ADMIN_AD_ORDER_UNAUTHORIZED__') {
                options.handleAdminUnauthorized();
                return;
            }
            options.pushLiveLog('warning', error?.message || `광고 주문 #${order.id} 재시도 실패`);
        } finally {
            setAdRetryingId(null);
        }
    }, [options]);

    const openAdReviewPanel = useCallback((order: AdminAdVideoOrderItem) => {
        setExpandedAdReviewOrderId((prev) => prev === order.id ? null : order.id);
        setAdReviewDrafts((prev) => {
            if (prev[order.id]) {
                return prev;
            }
            return {
                ...prev,
                [order.id]: createAdminAdReviewDraft(order),
            };
        });
    }, []);

    const updateAdReviewDraft = useCallback((orderId: number, cut: number, field: 'status' | 'note', value: string) => {
        setAdReviewDrafts((prev) => updateAdminAdReviewDraftItems(prev, orderId, cut, field, value));
    }, []);

    const toggleAdReviewDiffOnly = useCallback((orderId: number) => {
        setAdReviewDiffOnly((prev) => toggleAdminAdReviewFilter(prev, orderId));
    }, []);

    const toggleAdReviewStatusDiffOnly = useCallback((orderId: number) => {
        setAdReviewStatusDiffOnly((prev) => toggleAdminAdReviewFilter(prev, orderId));
    }, []);

    const toggleAdReviewNoteDiffOnly = useCallback((orderId: number) => {
        setAdReviewNoteDiffOnly((prev) => toggleAdminAdReviewFilter(prev, orderId));
    }, []);

    const resetAdReviewFilters = useCallback((orderId: number) => {
        const nextState = resetAdminAdReviewFilters(orderId, {
            diffOnly: adReviewDiffOnly,
            statusDiffOnly: adReviewStatusDiffOnly,
            noteDiffOnly: adReviewNoteDiffOnly,
        } satisfies AdminAdReviewFilterState);
        setAdReviewDiffOnly(nextState.diffOnly);
        setAdReviewStatusDiffOnly(nextState.statusDiffOnly);
        setAdReviewNoteDiffOnly(nextState.noteDiffOnly);
    }, [adReviewDiffOnly, adReviewNoteDiffOnly, adReviewStatusDiffOnly]);

    const matchesAdReviewSceneFilter = useCallback((order: AdminAdVideoOrderItem, cut: number) => {
        return matchesAdminAdReviewSceneFilter({
            order,
            cut,
            filters: {
                diffOnly: adReviewDiffOnly,
                statusDiffOnly: adReviewStatusDiffOnly,
                noteDiffOnly: adReviewNoteDiffOnly,
            },
        });
    }, [adReviewDiffOnly, adReviewNoteDiffOnly, adReviewStatusDiffOnly]);

    const moveAdStoryboardModalCut = useCallback((direction: -1 | 1) => {
        setAdStoryboardModal((prev) => moveAdminStoryboardModalCut({
            modal: prev,
            orders: options.adVideoOrders,
            direction,
            resolvePreviewSource: resolveAdminStoryboardPreviewSource,
        }));
    }, [options.adVideoOrders]);

    const currentAdStoryboardModalDiff = useMemo(
        () => findCurrentAdStoryboardModalDiff(adStoryboardModal, options.adVideoOrders),
        [adStoryboardModal, options.adVideoOrders],
    );

    const currentAdStoryboardModalIndex = useMemo(
        () => findCurrentAdStoryboardModalIndex(adStoryboardModal, options.adVideoOrders),
        [adStoryboardModal, options.adVideoOrders],
    );

    const handleSaveAdReview = useCallback(async (order: AdminAdVideoOrderItem) => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return;
        }

        setAdReviewSavingId(order.id);
        try {
            await saveAdminAdOrderStoryboardReview({
                apiBaseUrl: options.apiBaseUrl,
                token,
                orderId: order.id,
                draft: adReviewDrafts[order.id] || [],
                buildApiErrorMessage: options.buildApiErrorMessage,
            });
            options.pushLiveLog('success', `광고 주문 #${order.id} storyboard 검수 저장 완료`);
            await options.loadDashboard(true);
        } catch (error: any) {
            if (error?.message === '__ADMIN_AD_ORDER_UNAUTHORIZED__') {
                options.handleAdminUnauthorized();
                return;
            }
            options.pushLiveLog('warning', error?.message || `광고 주문 #${order.id} storyboard 검수 저장 실패`);
        } finally {
            setAdReviewSavingId(null);
        }
    }, [adReviewDrafts, options]);

    const exportAdSettlementCsv = useCallback(async () => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            options.handleAdminUnauthorized();
            return;
        }

        setAdSettlementExporting(true);
        try {
            const response = await fetch(`${options.apiBaseUrl}/api/admin/ad-video-orders/settlement-export`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (response.status === 401) {
                options.handleAdminUnauthorized();
                return;
            }
            if (response.status === 404) {
                options.adSettlementApiUnavailableRef.current = true;
                const fallbackDashboard = options.adSettlementDashboard || buildFallbackAdSettlementDashboard(options.adVideoOrders);
                options.downloadCsvFromRows('ad_video_order_settlement.csv', [
                    ['order_id', 'user_id', 'status', 'engine_type', 'render_quality', 'currency', 'prompt_tokens', 'render_tokens', 'total_tokens', 'local_cost', 'external_cost', 'storage_cost', 'total_cost', 'period_day', 'period_month', 'created_at'],
                    ...fallbackDashboard.recent_logs.map((log) => ([
                        String(log.order_id),
                        String(log.user_id),
                        log.status,
                        log.engine_type,
                        log.render_quality,
                        log.currency,
                        String(log.prompt_tokens),
                        String(log.render_tokens),
                        String(log.total_tokens),
                        String(log.local_cost),
                        String(log.external_cost),
                        String(log.storage_cost),
                        String(log.total_cost),
                        log.period_day,
                        log.period_month,
                        log.created_at,
                    ])),
                ]);
                options.pushLiveLog('info', '정산 CSV API 미지원 상태라 클라이언트 fallback CSV를 생성했습니다.', { capabilityId: 'settlement-export', panel_id: 'PANEL-ADMIN-SETTLEMENT' });
                return;
            }
            if (!response.ok) {
                throw new Error(`정산 CSV 다운로드 실패(${response.status})`);
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = 'ad_video_order_settlement.csv';
            anchor.click();
            window.URL.revokeObjectURL(url);
        } catch (error: any) {
            options.pushLiveLog('warning', error?.message || '정산 CSV 다운로드에 실패했습니다.', { capabilityId: 'settlement-export', panel_id: 'PANEL-ADMIN-SETTLEMENT' });
        } finally {
            setAdSettlementExporting(false);
        }
    }, [options]);

    const buildSettlementConnectionId = useCallback((orderId: number) => {
        return buildAdminAutoConnectMeta({
            capabilityId: `settlement-order-${orderId}`,
            execution: 'observe',
            panelId: 'PANEL-ADMIN-SETTLEMENT',
        }).connection_id;
    }, []);

    return {
        expandedAdReviewOrderId,
        adReviewDrafts,
        adReviewDiffOnly,
        adReviewStatusDiffOnly,
        adReviewNoteDiffOnly,
        adReviewSavingId,
        adStoryboardModal,
        setAdStoryboardModal,
        adPreviewLoadingId,
        adRetryingId,
        adPreviewOrder,
        adPreviewUrl,
        adPreviewError,
        adSettlementExporting,
        closeAdPreview,
        handlePreviewAdOrder,
        handleDownloadAdOrder,
        handleRetryAdOrder,
        openAdReviewPanel,
        updateAdReviewDraft,
        toggleAdReviewDiffOnly,
        toggleAdReviewStatusDiffOnly,
        toggleAdReviewNoteDiffOnly,
        resetAdReviewFilters,
        matchesAdReviewSceneFilter,
        moveAdStoryboardModalCut,
        currentAdStoryboardModalDiff,
        currentAdStoryboardModalIndex,
        handleSaveAdReview,
        exportAdSettlementCsv,
        buildSettlementConnectionId,
    };
}

export function assertAdminAdOperationsControllerContract() {
    const connectionId = buildAdminAutoConnectMeta({
        capabilityId: 'settlement-order-sample',
        execution: 'observe',
        panelId: 'PANEL-ADMIN-SETTLEMENT',
    }).connection_id;
    if (!connectionId) {
        throw new Error('admin ad operations controller contract 누락: 정산 connection id 생성 필요');
    }
}
