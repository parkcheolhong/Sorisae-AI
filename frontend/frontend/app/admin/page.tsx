'use client';

import * as React from 'react';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useAdminPageState } from '@/app/admin/hooks/useAdminPageState';
import { useAdminPageActions } from '@/app/admin/hooks/useAdminPageActions';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { resolveApiBaseUrl, resolveBackendDocsUrl } from '@/lib/api';
import AdminAdPreviewModal from '@/components/admin/admin-ad-preview-modal';
import AdminLlmControlSummary from '@/components/admin/admin-llm-control-summary';
import AdminManagementSection from '@/components/admin/admin-management-section';
import AdminStoryboardModal from '@/components/admin/admin-storyboard-modal';
import AdminSystemSettingsPanel from '@/components/admin/admin-system-settings-panel';
import { AdminWorldlincoTuningPanel } from '@/components/admin/admin-worldlinco-tuning-panel';
import AdminWorldlincoBillingPolicyPanel from '@/components/admin/admin-worldlinco-billing-policy-panel';
import AdminWorldlincoTourismPromoPanel from '@/components/admin/admin-worldlinco-tourism-promo-panel';
import AdminWorldlincoReferralPanel from '@/components/admin/admin-worldlinco-referral-panel';
import AdminWorldlincoSalesCommissionPanel from '@/components/admin/admin-worldlinco-sales-commission-panel';
import AdminWorldlincoRegionalPanel from '@/components/admin/admin-worldlinco-regional-panel';
import AdminWorldlincoBulkChatPanel from '@/components/admin/admin-worldlinco-bulk-chat-panel';
import AdminTravelPartnerIntegrationPanel from '@/components/admin/admin-travel-partner-integration-panel';
import AdminTravelPartnerKpiPanel from '@/components/admin/admin-travel-partner-kpi-panel';
import AdminGrafanaMonitorSection from '@/components/admin/admin-grafana-monitor-section';
import AdminPrometheusSection from '@/components/admin/admin-prometheus-section';
import AdminP50P95ChartSection from '@/components/admin/admin-p50p95-chart-section';
import AdminPerformanceSection from '@/components/admin/admin-performance-section';
import AdminLlmPathSection from '@/components/admin/admin-llm-path-section';
import AdminFastPathSection from '@/components/admin/admin-fast-path-section';
import AdminOpsSection from '@/components/admin/admin-ops-section';
import AdminAlertManagerSection from '@/components/admin/admin-alert-manager-section';
import AdminSLASection from '@/components/admin/admin-sla-section';
import AdminSubscriptionMonitorSection from '@/components/admin/admin-subscription-monitor-section';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import { buildAdminDashboardSectionsConfig } from '@/app/admin/admin-dashboard-sections-config';
import { buildAdminLauncherRailItems } from '@/app/admin/admin-rail-builders';
import { ADMIN_LEFT_SHORT_LABEL_OVERRIDES, ADMIN_RIGHT_SHORT_LABEL_OVERRIDES } from '@/app/admin/admin-rail-config';
import { resolveMarketplaceSiteHref } from '@/lib/canonical-site';
import ViewSkeleton from '@/components/ui/view-skeleton';
import { type SharedOrchestratorStageRun } from '@shared/orchestrator-stage-card-panel';
import {
    buildAdminDashboardOverviewAssembly,
    buildAdminPageHealthAnalysis,
} from '@/app/admin/admin-page-health-analysis';
import { buildAdminAutoConnectGraphAssembly } from '@/app/admin/admin-page-auto-connect-graph-assembly';
import type { AdminStageRunResponse } from '@/app/admin/admin-page-types';
import {
    buildAdminPageAdOrdersAssembly,
    buildAdminPageManualOrchestratorAssembly,
    buildAdminPageSampleProductsAssembly,
    buildAdminPageSystemSettingsAssembly,
} from '@/app/admin/admin-page-orchestrator-assemblies';
import {
    attachActiveAdminConnectionMeta,
    buildAdminAutoConnectMeta,
    readAdminAutoConnectGraphSnapshot,
    registerAdminAutoConnectGraphEvent,
} from '@/lib/admin-auto-connect';
import {
    buildCapabilityConnectionId,
    buildSettlementOrderConnectionId,
    createDashboardAutoConnectTracker,
    type AdminAutoConnectGraphSnapshot,
} from '@/lib/admin-dashboard-auto-connect';
import {
    assertAdminAdOrderFallbackContract,
    buildFallbackAdOrderMonitorSummary,
    buildFallbackAdSettlementDashboard,
} from '@/lib/admin-ad-order-fallback';
import {
    assertAdminAlertSpeechContract,
    buildAdminAlertSpeech,
    hasSpeechSynthesisActivation,
    speakAdminAlert,
} from '@/lib/admin-alert-speech';
import {
    assertAdminAdProductionAnalysisContract,
    buildAdminAdProductionStages,
    getAdminAdProductionCurrentStage,
    getAdminMotionTempoLabel,
    getAdminSceneFrameHint,
} from '@/lib/admin-ad-production-analysis';
import {
    assertAdminAutoConnectServiceContract,
} from '@/lib/admin-auto-connect-service';
import { assertAdminOrchestratorBridgeContract } from '@/lib/admin-orchestrator-bridge';
import {
    assertAdminAdOrderActionsContract,
} from '@/lib/admin-ad-order-actions';
import {
    assertAdminAdReviewStateContract,
} from '@/lib/admin-ad-review-state';
import {
    assertAdminCategoryServiceContract,
} from '@/lib/admin-category-service';
import {
    assertAdminRuntimeTypesContract,
    type AdminCostSimulatorResponse,
    type LiveLogItem,
    type LlmStatus,
} from '@/lib/admin-runtime-types';
import {
    assertAdminSampleProductServiceContract,
} from '@/lib/admin-sample-product-service';
import {
    assertAdminHealthAnalysisContract,
    formatHealthMetricLabel,
    formatHealthMetricValue,
    getHealthAlertMetrics,
    getHealthAlertRootCause,
    type HealthStatus,
} from '@/lib/admin-health-analysis';
import {
    assertAdminSystemSettingsServiceContract,
} from '@/lib/admin-system-settings-service';
import {
    cloneAdminRailSettingsDefaults,
    loadAdminRailSettings,
    saveAdminRailSettings,
    type AdminRailId,
    type AdminRailSettingsMap,
} from '@/lib/admin-rail-settings-service';
import {
    analyzeAdminThresholds,
    applyApprovedWorldlincoRecommendations,
    approveAdminThresholdTarget,
    loadAdminThresholdAnalysis,
    type AdminThresholdAnalysisResponse,
} from '@/lib/admin-threshold-analysis-service';
import {
    assertAdminManualOrchestratorContract,
} from '@/lib/admin-manual-orchestrator';
import {
    assertAdminManualOrchestratorControllerContract,
    useAdminManualOrchestratorController,
} from '@/lib/use-admin-manual-orchestrator-controller';
import {
    assertAdminAdOperationsControllerContract,
    useAdminAdOperationsController,
} from '@/lib/use-admin-ad-operations-controller';
import {
    assertAdminSystemCategoryControllerContract,
    useAdminSystemCategoryController,
} from '@/lib/use-admin-system-category-controller';
import {
    assertAdminSampleProductsControllerContract,
    useAdminSampleProductsController,
} from '@/lib/use-admin-sample-products-controller';
import {
    assertAdminAutoConnectControllerContract,
    useAdminAutoConnectController,
} from '@/lib/use-admin-auto-connect-controller';
import { assertAdminManualWorklogContract } from '@/lib/admin-manual-worklog';
import {
    assertAdminDashboardTypesContract,
    type AdminAdOrderMonitorSummary,
    type AdminAdOrderSettlementDashboard,
    type AdminAdVideoOrderItem,
    type AdminDashboardSelfRunStatus,
    type AutoRecoveryHistoryItem,
    type FocusedSelfHealingApplyResult,
    type FocusedSelfHealingPlan,
    type OrchestratorCapabilityDetailResponse,
    type OrchestratorCapabilitySummaryResponse,
    type OverviewStats,
    type RevenueStats,
    type TopProject,
} from '@/lib/admin-dashboard-types';
import {
    assertAdminDashboardUiTypesContract,
} from '@/lib/admin-dashboard-ui-types';
import {
    downloadCsvFromRows,
    formatCurrency,
    getOrchestratorActionGuide,
    normalizeStoredLiveLog,
    normalizeSystemSettingsMessage,
    pickPreferredModel,
    toFileHref,
} from '@/lib/admin-dashboard-page-helpers';
import {
    ADMIN_ACTION_TEMPLATE_LABELS,
    ADMIN_ALERT_VOICE_ENABLED_STORAGE_KEY,
    ADMIN_AUTO_RECOVERY_HISTORY_STORAGE_KEY,
    ADMIN_CATEGORY_SORT_STORAGE_KEY,
    ADMIN_DASHBOARD_PREFERENCES_STORAGE_KEY,
    ADMIN_HIDE_EMPTY_CATEGORIES_STORAGE_KEY,
    ADMIN_HUMAN_OBJECT_INTERACTION_RULES,
    ADMIN_LIVE_LOGS_STORAGE_KEY,
    ADMIN_MANUAL_ORCHESTRATOR_META_STORAGE_KEY,
    ADMIN_MANUAL_ORCHESTRATOR_STAGE_RUN_ID_STORAGE_KEY,
    ADMIN_MANUAL_ORCHESTRATOR_STATE_STORAGE_KEY,
    ADMIN_SAMPLE_SETTINGS_STORAGE_KEY,
    ADMIN_SYSTEM_SETTINGS_STATUS_SECTIONS,
    GENERATOR_ENV_KEY_MAP,
    OPTIMIZED_GENERATOR_DEFAULTS,
    OPTIMIZED_RUNTIME_ROUTE_ENV_MAP,
    OPTIMIZED_RUNTIME_ROUTE_PRESETS,
} from '@/lib/admin-dashboard-page-constants';
import {
    assertAdminApiGuardContract,
    buildApiErrorMessage,
    clearAdminApiBackoff,
    isAdminApiBackoffActive,
    setAdminApiBackoff,
} from '@/lib/admin-api-guard';
import { createAdminSessionExpiryChecker } from '@/lib/admin-auth-session';
import {
    assertAdminDashboardBootstrapContract,
} from '@/lib/admin-dashboard-bootstrap';
import {
    assertAdminBootstrapFetchContract,
    fetchWithAdminBootstrapRetry,
} from '@/lib/admin-bootstrap-fetch';
import {
    assertAdminDashboardControllerContract,
    loadAdminDashboardController,
} from '@/lib/admin-dashboard-controller';
import {
    bindAutoConnectGraphSnapshot,
} from '@/lib/admin-dashboard-actions';
import {
    assertAdminDashboardStateAssemblerContract,
} from '@/lib/admin-dashboard-state-assembler';
import {
    assertAdminDashboardSnapshotContract,
    type AdminDashboardSnapshot,
} from '@/lib/admin-dashboard-snapshot';
import {
    assertAdminAutoRecoveryContract,
    executeAdminAutomaticRecovery,
    shouldRunSelfRunAutoNormalization,
} from '@/lib/admin-auto-recovery';
import { assertAdminSelfRunAnalysisContract } from '@/lib/admin-self-run-analysis';
import {
    assertAdminSelfRunControlContract,
    approveWorkspaceSelfRunRequest,
    normalizeWorkspaceSelfRunRequest,
    retryWorkspaceSelfRunRequest,
} from '@/lib/admin-self-run-control';
import {
    ADMIN_SESSION_CHECK_INTERVAL_MS,
    ADMIN_SESSION_WARNING_WINDOW_MS,
    clearAdminToken,
    extendAdminSessionToken,
    getAdminToken,
    getAdminTokenExpiryMs,
    getRemainingSessionMinutes,
    logoutAdminSession,
} from '@/lib/admin-session';
import { hardRedirectToAdminLogin, redirectToAdminLogin } from '@/lib/admin-navigation';

assertAdminAdOrderFallbackContract();
assertAdminAlertSpeechContract();
assertAdminAdProductionAnalysisContract();
assertAdminAutoConnectServiceContract();
assertAdminOrchestratorBridgeContract();
assertAdminAdOrderActionsContract();
assertAdminAdReviewStateContract();
assertAdminCategoryServiceContract();
assertAdminHealthAnalysisContract();
assertAdminRuntimeTypesContract();
assertAdminSampleProductServiceContract();
assertAdminSystemSettingsServiceContract();
assertAdminManualOrchestratorContract();
assertAdminManualOrchestratorControllerContract();
assertAdminAdOperationsControllerContract();
assertAdminSystemCategoryControllerContract();
assertAdminSampleProductsControllerContract();
assertAdminAutoConnectControllerContract();
assertAdminManualWorklogContract();
assertAdminDashboardTypesContract();
assertAdminDashboardUiTypesContract();
assertAdminApiGuardContract();
assertAdminBootstrapFetchContract();
assertAdminDashboardBootstrapContract();
assertAdminDashboardControllerContract();
assertAdminDashboardStateAssemblerContract();
assertAdminDashboardSnapshotContract();
assertAdminAutoRecoveryContract();
assertAdminSelfRunAnalysisContract();
assertAdminSelfRunControlContract();

const initialOverview: OverviewStats = { projects: 0, users: 0, purchases: 0, reviews: 0 };
const initialRevenue: RevenueStats = { total_revenue: 0, total_purchases: 0, average_purchase_amount: 0 };
const adminPassKmcKcbDocsHref = '/admin/docs-viewer?path=docs%2Fidentity-provider-integration-contract.md';
const adminCommercialTermsDocsHref = '/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-terms-checklist.md';
const adminCommercialValuesInputHref = '/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-values-input-checklist.md';
const ADMIN_RAIL_OPERATOR_NOTES_STORAGE_KEY = 'admin-rail-operator-notes-v1';

type AdminRailActionItem = {
    id: AdminRailId;
    label: string;
    description: string;
    emergencyActionLabel: string;
};

type AdminRailSettingFieldConfig = {
    key: string;
    label: string;
    input: 'boolean' | 'number' | 'text' | 'select';
    help: string;
    min?: number;
    max?: number;
    step?: number;
    options?: Array<{ value: string; label: string }>;
};

const ADMIN_RAIL_ACTION_ITEMS: readonly AdminRailActionItem[] = [
    { id: 'sla', label: 'SLA', description: '장애 상황 관리자 Push 재전송과 SLA 패널 즉시 확인', emergencyActionLabel: '관리자 Push 재전송' },
    { id: 'list', label: '일람', description: '소리새 최신 result JSON/장애 분류를 바로 조회', emergencyActionLabel: '최신 결과 JSON 조회' },
    { id: 'ops', label: '운영', description: '운영 준비 패널 열기 + 전역 자동 모드 즉시 적용', emergencyActionLabel: '전역 자동 모드 적용' },
    { id: 'cover', label: '커버', description: 'Fast path 커버리지 패널을 즉시 열어 누락 경로 확인', emergencyActionLabel: '커버리지 패널 열기' },
    { id: 'llm', label: 'LLM', description: 'LLM 응답 경로 패널 또는 LLM 관리 페이지 이동', emergencyActionLabel: 'LLM 관리 페이지 이동' },
    { id: 'performance', label: '성능', description: '성능 최적화 패널 즉시 오픈', emergencyActionLabel: '성능 패널 열기' },
    { id: 'latency', label: '응답시간', description: 'p50/p95 패널 즉시 오픈', emergencyActionLabel: 'p50/p95 패널 열기' },
    { id: 'data', label: '데이터', description: 'Prometheus 데이터 패널 오픈 및 메트릭 확인', emergencyActionLabel: 'Prometheus 패널 열기' },
    { id: 'monitoring', label: '모니터링', description: 'Grafana 모니터링 패널 오픈 및 대시보드 새로고침', emergencyActionLabel: '모니터링 즉시 점검' },
];

const FLOW_ADM_DASH_COMMAND_ITEMS = [
    { id: 'once', label: 'verify-flow-adm-dash-playwright-once' },
    { id: 'webserver', label: 'verify-flow-adm-dash-playwright-once-webserver' },
    { id: 'npm', label: 'verify-flow-adm-dash-npm' },
    { id: 'all', label: 'FLOW-ADM-DASH 회귀 전체 실행' },
] as const;

const ADMIN_RAIL_SETTING_FIELDS: Record<AdminRailId, readonly AdminRailSettingFieldConfig[]> = {
    sla: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: 'SLA 레일 운영 여부' },
        { key: 'availability_target_percent', label: '가용성 목표(%)', input: 'number', help: '목표 SLA 가용성', min: 90, max: 100, step: 0.01 },
        { key: 'alert_on_breach', label: '위반시 알림', input: 'boolean', help: '임계치 이탈 시 알림 여부' },
        { key: 'auto_push_on_breach', label: '자동 Push', input: 'boolean', help: '위반 시 관리자 Push 재전송 허용' },
        { key: 'breach_cooldown_minutes', label: '쿨다운(분)', input: 'number', help: '연속 알림 방지 시간', min: 1, max: 240, step: 1 },
    ],
    list: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '일람 레일 운영 여부' },
        { key: 'auto_refresh_seconds', label: '자동 새로고침(초)', input: 'number', help: '결과 조회 기본 주기', min: 5, max: 600, step: 1 },
        { key: 'show_failed_only', label: '실패만 보기', input: 'boolean', help: '성공 항목을 숨기고 실패만 요약' },
        { key: 'include_raw_payload', label: '원본 payload 포함', input: 'boolean', help: 'raw JSON 전체 노출 여부' },
        { key: 'max_items', label: '최대 표시 수', input: 'number', help: '목록/배열 절단 상한', min: 1, max: 200, step: 1 },
    ],
    ops: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '운영 레일 사용 여부' },
        { key: 'auto_apply_global_mode', label: '자동 모드 즉시 적용', input: 'boolean', help: '응급조치 시 전역 자동 모드 적용' },
        { key: 'healthcheck_on_open', label: '오픈 시 헬스체크', input: 'boolean', help: '패널 오픈 후 헬스 점검 여부' },
        { key: 'allow_runtime_restart', label: '런타임 재시작 허용', input: 'boolean', help: '향후 재시작 액션 허용 플래그' },
        {
            key: 'deployment_gate_level', label: '배포 게이트', input: 'select', help: '운영 게이트 기준', options: [
                { value: 'strict', label: 'strict' },
                { value: 'standard', label: 'standard' },
                { value: 'flexible', label: 'flexible' },
            ]
        },
    ],
    cover: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '커버리지 레일 사용 여부' },
        { key: 'target_fastpath_percent', label: 'Fast path 목표(%)', input: 'number', help: '목표 커버리지 비율', min: 0, max: 100, step: 1 },
        { key: 'enforce_fastpath_guard', label: '가드 강제', input: 'boolean', help: '목표 미달 시 가드 활성화' },
        { key: 'auto_open_failures', label: '실패 자동 오픈', input: 'boolean', help: '문제 탐지 시 패널 자동 오픈' },
        { key: 'sample_size', label: '표본 수', input: 'number', help: '분석 샘플 개수', min: 1, max: 500, step: 1 },
    ],
    llm: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: 'LLM 레일 사용 여부' },
        { key: 'route_timeout_ms', label: '타임아웃(ms)', input: 'number', help: 'LLM 경로 목표 제한시간', min: 1000, max: 300000, step: 1000 },
        { key: 'prefer_fast_path', label: 'Fast path 우선', input: 'boolean', help: '경량 경로 우선 사용' },
        { key: 'auto_recover_on_timeout', label: '타임아웃 자동복구', input: 'boolean', help: '타임아웃 후 자동 복구 전략' },
        { key: 'max_retry_count', label: '최대 재시도', input: 'number', help: '자동 재시도 횟수', min: 0, max: 10, step: 1 },
    ],
    performance: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '성능 레일 사용 여부' },
        { key: 'response_budget_ms', label: '응답 예산(ms)', input: 'number', help: '전체 응답 목표', min: 50, max: 10000, step: 10 },
        { key: 'db_query_budget_ms', label: 'DB 예산(ms)', input: 'number', help: 'DB 쿼리 목표', min: 10, max: 5000, step: 10 },
        { key: 'cache_ttl_seconds', label: '캐시 TTL(초)', input: 'number', help: '권장 캐시 TTL', min: 0, max: 86400, step: 1 },
        { key: 'auto_collect_snapshot', label: '자동 스냅샷', input: 'boolean', help: '응급조치 시 스냅샷 수집' },
    ],
    latency: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '응답시간 레일 사용 여부' },
        { key: 'p50_budget_ms', label: 'p50 목표(ms)', input: 'number', help: '중앙값 목표', min: 10, max: 5000, step: 10 },
        { key: 'p95_budget_ms', label: 'p95 목표(ms)', input: 'number', help: '상위 5% 지연 목표', min: 10, max: 15000, step: 10 },
        { key: 'sampling_window_minutes', label: '샘플 윈도우(분)', input: 'number', help: '지연 분석 시간창', min: 1, max: 180, step: 1 },
        { key: 'alert_on_regression', label: '회귀 알림', input: 'boolean', help: '지연 악화 시 알림' },
    ],
    data: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '데이터 레일 사용 여부' },
        { key: 'metric_refresh_seconds', label: '메트릭 갱신(초)', input: 'number', help: '메트릭 기본 주기', min: 5, max: 600, step: 1 },
        { key: 'include_zero_metrics', label: '0값 포함', input: 'boolean', help: '0인 메트릭 포함 여부' },
        {
            key: 'selected_metric_key', label: '기본 메트릭', input: 'select', help: '기본 표시 메트릭', options: [
                { value: 'http_requests_total', label: 'http_requests_total' },
                { value: 'cache_hits_total', label: 'cache_hits_total' },
                { value: 'cache_misses_total', label: 'cache_misses_total' },
                { value: 'db_queries_total', label: 'db_queries_total' },
                { value: 'purchases_total', label: 'purchases_total' },
            ]
        },
        { key: 'max_series_points', label: '최대 포인트', input: 'number', help: '차트 시계열 포인트 상한', min: 10, max: 1000, step: 10 },
    ],
    monitoring: [
        { key: 'enabled', label: '활성화', input: 'boolean', help: '모니터링 레일 사용 여부' },
        { key: 'grafana_base_url', label: 'Grafana URL', input: 'text', help: '외부 대시보드 기본 주소' },
        { key: 'auto_refresh_seconds', label: '자동 새로고침(초)', input: 'number', help: '모니터링 갱신 주기', min: 5, max: 600, step: 1 },
        { key: 'open_external_dashboard', label: '외부 대시보드 열기', input: 'boolean', help: '응급조치 시 Grafana 새 탭 오픈' },
        {
            key: 'alert_channel', label: '알림 채널', input: 'select', help: '기본 알림 채널', options: [
                { value: 'admin', label: 'admin' },
                { value: 'slack', label: 'slack' },
                { value: 'teams', label: 'teams' },
            ]
        },
    ],
};

export default function AdminDashboardPage() {
    const router = useRouter();
    const apiBaseUrl = resolveApiBaseUrl();
    const adminApiDocsHref = useMemo(() => resolveBackendDocsUrl(apiBaseUrl), [apiBaseUrl]);
    const marketplaceHomeHref = useMemo(() => resolveMarketplaceSiteHref('/marketplace'), []);
    const marketplaceOrchestratorHref = useMemo(() => resolveMarketplaceSiteHref('/marketplace/orchestrator'), []);
    const adminCategoriesBootstrappedRef = useRef(false);
    const adminCategoryStatsBootstrappedRef = useRef(false);
    const {
        authChecked,
        setAuthChecked,
        authStatusMessage,
        setAuthStatusMessage,
        adminUser,
        setAdminUser,
        loading,
        setLoading,
        refreshing,
        setRefreshing,
        lastUpdated,
        setLastUpdated,
        error,
        setError,
        overview,
        setOverview,
        revenue,
        setRevenue,
        topProjects,
        setTopProjects,
        health,
        setHealth,
        llmStatus,
        setLlmStatus,
        projectQuery,
        setProjectQuery,
        topProjectsOpen,
        setTopProjectsOpen,
        adOrdersOpen,
        setAdOrdersOpen,
        autoRefreshEnabled,
        setAutoRefreshEnabled,
        refreshSeconds,
        setRefreshSeconds,
        systemSettingsPanelOpen,
        setSystemSettingsPanelOpen,
        liveLogsPanelOpen,
        setLiveLogsPanelOpen,
        autoConnectGraphPanelOpen,
        setAutoConnectGraphPanelOpen,
        customerOrchestratorPanelOpen,
        setCustomerOrchestratorPanelOpen,
        topProjectsPanelOpen,
        setTopProjectsPanelOpen,
        adminControlHubOpen,
        setAdminControlHubOpen,
        healthOverviewOpen,
        setHealthOverviewOpen,
        adOrdersPanelOpen,
        setAdOrdersPanelOpen,
        subscriptionMonitorPanelOpen,
        setSubscriptionMonitorPanelOpen,
        categoryPanelOpen,
        setCategoryPanelOpen,
        quickLinksPanelOpen,
        setQuickLinksPanelOpen,
        llmControlPanelOpen,
        setLlmControlPanelOpen,
        samplePanelOpen,
        setSamplePanelOpen,
        liveLogs,
        setLiveLogs,
        autoConnectGraph,
        setAutoConnectGraph,
        adVideoOrders,
        setAdVideoOrders,
        adVideoTotal,
        setAdVideoTotal,
        adOrderMonitorSummary,
        setAdOrderMonitorSummary,
        adSettlementDashboard,
        setAdSettlementDashboard,
        costSimulatorPanelOpen,
        setCostSimulatorPanelOpen,
        costSimulatorLoading,
        setCostSimulatorLoading,
        costSimulatorError,
        setCostSimulatorError,
        costSimulatorResult,
        setCostSimulatorResult,
        costSimulatorForm,
        setCostSimulatorForm,
        orchestratorCapabilitySummary,
        setOrchestratorCapabilitySummary,
        securityGuardDetail,
        setSecurityGuardDetail,
        dashboardSelfRunStatus,
        setDashboardSelfRunStatus,
        sorisaeFailureStatus,
        setSorisaeFailureStatus,
        voiceAlertEnabled,
        setVoiceAlertEnabled,
        llmPanelHeight,
        setLlmPanelHeight,
        generatorModelOverrides,
        setGeneratorModelOverrides,
        adminStageRun,
        setAdminStageRun,
        adminStageNoteDraft,
        setAdminStageNoteDraft,
        adminStageSubstepChecks,
        setAdminStageSubstepChecks,
        adminStageRevisionNote,
        setAdminStageRevisionNote,
        adminStageUpdateLoading,
        setAdminStageUpdateLoading,
        autoOpsEnabled,
        setAutoOpsEnabled,
        autoOpsLastExecutedAt,
        setAutoOpsLastExecutedAt,
        autoRecoveryHistory,
        setAutoRecoveryHistory,
        autoRecoveryRunning,
        setAutoRecoveryRunning,
        selfRunApproving,
        setSelfRunApproving,
        selfRunRetrying,
        setSelfRunRetrying,
        selfRunNormalizing,
        setSelfRunNormalizing,
        focusedSelfHealingBusy,
        setFocusedSelfHealingBusy,
        focusedSelfHealingModalOpen,
        setFocusedSelfHealingModalOpen,
        focusedSelfHealingRequestedPath,
        setFocusedSelfHealingRequestedPath,
        focusedSelfHealingReason,
        setFocusedSelfHealingReason,
        focusedSelfHealingPlan,
        setFocusedSelfHealingPlan,
        focusedSelfHealingApplyResult,
        setFocusedSelfHealingApplyResult,
        focusedSelfHealingApprovalConfirmed,
        setFocusedSelfHealingApprovalConfirmed,
        focusedSelfHealingSelectedOptionId,
        setFocusedSelfHealingSelectedOptionId,
        focusedSelfHealingMessage,
        setFocusedSelfHealingMessage,
        capabilityBootstrapReady,
        setCapabilityBootstrapReady,
    } = useAdminPageState();
    const latestDedicatedOrder = useMemo(
        () => adVideoOrders.find((order: any) => order.engine_type === 'dedicated_engine') || null,
        [adVideoOrders],
    );
    const latestDedicatedProductionStages = useMemo(
        () => buildAdminAdProductionStages(latestDedicatedOrder),
        [latestDedicatedOrder],
    );
    const latestDedicatedReadyCount = useMemo(
        () => latestDedicatedProductionStages.filter((stage) => stage.ready).length,
        [latestDedicatedProductionStages],
    );
    const latestDedicatedCurrentStage = useMemo(
        () => getAdminAdProductionCurrentStage(latestDedicatedProductionStages),
        [latestDedicatedProductionStages],
    );
    const latestDedicatedWorkReady = latestDedicatedProductionStages.length > 0 && latestDedicatedProductionStages.every((stage) => stage.ready);
    const updateCostSimulatorField = (key: keyof typeof costSimulatorForm, value: string) => {
        setCostSimulatorForm((prev: any) => ({
            ...prev,
            [key]: key === 'currency' ? value : Number(value),
        }));
    };
    const snapshotRef = useRef<AdminDashboardSnapshot | null>(null);
    const sessionWarningExpRef = useRef<number | null>(null);
    const selfRunNormalizationRef = useRef<string>('');
    const selfRunApiUnavailableRef = useRef(false);
    const autoConnectGraphApiUnavailableRef = useRef(false);
    const adMonitorApiUnavailableRef = useRef(false);
    const adSettlementApiUnavailableRef = useRef(false);
    const loadDashboardInFlightRef = useRef(false);
    const panelDeepLinkHandledRef = useRef(false);
    const lastSpokenAlertSignatureRef = useRef('');
    const autoOpsSignatureRef = useRef('');
    const autoRecoveryLastTriggeredAtRef = useRef(0);
    const thresholdRecoveryCandidateRef = useRef<{ reasons: string[]; shouldApplyWorldlinco: boolean } | null>(null);
    const applyApprovedWorldlincoThresholdRecoveryRef = useRef<() => Promise<any>>(async () => null);
    const scrollElementIntoViewIfNeeded = useCallback((selector: string) => {
        if (typeof window === 'undefined') {
            return;
        }
        const element = document.querySelector(selector) as HTMLElement | null;
        if (!element) {
            return;
        }
        const rect = element.getBoundingClientRect();
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
        const isOutOfViewport = rect.top < 64 || rect.bottom > viewportHeight;
        if (isOutOfViewport) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, []);
    const [musicPanelOpen, setMusicPanelOpen] = React.useState(false);
    const [worldlincoTuningPanelOpen, setWorldlincoTuningPanelOpen] = React.useState(false);
    const [worldlincoBillingPolicyPanelOpen, setWorldlincoBillingPolicyPanelOpen] = React.useState(false);
    const [worldlincoTourismPromoPanelOpen, setWorldlincoTourismPromoPanelOpen] = React.useState(false);
    const [worldlincoReferralPanelOpen, setWorldlincoReferralPanelOpen] = React.useState(false);
    const [worldlincoSalesCommissionPanelOpen, setWorldlincoSalesCommissionPanelOpen] = React.useState(false);
    const [worldlincoRegionalPanelOpen, setWorldlincoRegionalPanelOpen] = React.useState(false);
    const [worldlincoBulkChatPanelOpen, setWorldlincoBulkChatPanelOpen] = React.useState(false);
    const [travelPartnerIntegrationOpen, setTravelPartnerIntegrationOpen] = React.useState(false);
    const [travelPartnerKpiOpen, setTravelPartnerKpiOpen] = React.useState(false);
    const [grafanaOpen, setGrafanaOpen] = React.useState(false);
    const [prometheusOpen, setPrometheusOpen] = React.useState(false);
    const [p50p95Open, setP50p95Open] = React.useState(false);
    const [performanceOpen, setPerformanceOpen] = React.useState(false);
    const [llmPathOpen, setLlmPathOpen] = React.useState(false);
    const [fastPathOpen, setFastPathOpen] = React.useState(false);
    const [opsOpen, setOpsOpen] = React.useState(false);
    const [alertManagerOpen, setAlertManagerOpen] = React.useState(false);
    const [slaOpen, setSlaOpen] = React.useState(false);
    const [rightRailOpen, setRightRailOpen] = React.useState(true);
    const [leftRailOpen, setLeftRailOpen] = React.useState(true);
    const [musicEmotion, setMusicEmotion] = React.useState('happy');
    const [musicIntensity, setMusicIntensity] = React.useState('0.7');
    const [musicTheme, setMusicTheme] = React.useState('소리새 테마');
    const [musicCode, setMusicCode] = React.useState('def chorus():\n    return "sing"');
    const [musicCodeEmotion, setMusicCodeEmotion] = React.useState('creative');
    const [musicComposeResult, setMusicComposeResult] = React.useState<Record<string, unknown> | null>(null);
    const [musicCodeResult, setMusicCodeResult] = React.useState<Record<string, unknown> | null>(null);
    const [musicFriendResult, setMusicFriendResult] = React.useState<Record<string, unknown> | null>(null);
    const [musicMode, setMusicMode] = React.useState('');
    const [musicLoading, setMusicLoading] = React.useState(false);
    const [musicError, setMusicError] = React.useState<string | null>(null);
    const [extrasPreviewPanelOpen, setExtrasPreviewPanelOpen] = React.useState(false);
    const [extrasPreviewTarget, setExtrasPreviewTarget] = React.useState<'health' | 'catalog'>('health');
    const [extrasPreviewState, setExtrasPreviewState] = React.useState<{
        loading: boolean;
        statusCode: number | null;
        durationMs: number | null;
        fetchedAt: string | null;
        error: string | null;
        payload: unknown;
    }>({
        loading: false,
        statusCode: null,
        durationMs: null,
        fetchedAt: null,
        error: null,
        payload: null,
    });
    const [sorisaeResultJsonPanelOpen, setSorisaeResultJsonPanelOpen] = React.useState(false);
    const [sorisaeResultJsonState, setSorisaeResultJsonState] = React.useState<{
        loading: boolean;
        statusCode: number | null;
        durationMs: number | null;
        fetchedAt: string | null;
        error: string | null;
        resultJsonPath: string | null;
        payload: unknown;
    }>({
        loading: false,
        statusCode: null,
        durationMs: null,
        fetchedAt: null,
        error: null,
        resultJsonPath: null,
        payload: null,
    });
    const [railActionBusyId, setRailActionBusyId] = React.useState<string | null>(null);
    const [railActionMessage, setRailActionMessage] = React.useState<string | null>(null);
    const [railActionError, setRailActionError] = React.useState<string | null>(null);
    const [railActionPayload, setRailActionPayload] = React.useState<unknown>(null);
    const [railActionCenterOpen, setRailActionCenterOpen] = React.useState(true);
    const [railOperatorNotes, setRailOperatorNotes] = React.useState<Record<string, string>>({});
    const [railSettings, setRailSettings] = React.useState<AdminRailSettingsMap>(() => cloneAdminRailSettingsDefaults());
    const [railSettingsDraft, setRailSettingsDraft] = React.useState<AdminRailSettingsMap>(() => cloneAdminRailSettingsDefaults());
    const [railSettingsLoading, setRailSettingsLoading] = React.useState(false);
    const [railSettingsError, setRailSettingsError] = React.useState<string | null>(null);
    const [railSettingsSavingId, setRailSettingsSavingId] = React.useState<AdminRailId | null>(null);
    const [railSettingsUpdatedAt, setRailSettingsUpdatedAt] = React.useState<string | null>(null);
    const [flowAdmDashCommandBusyId, setFlowAdmDashCommandBusyId] = React.useState<string | null>(null);
    const liveLogDedupRef = React.useRef<Record<string, number>>({});
    const [thresholdAnalysis, setThresholdAnalysis] = React.useState<AdminThresholdAnalysisResponse | null>(null);
    const [thresholdAnalysisLoading, setThresholdAnalysisLoading] = React.useState(false);
    const [thresholdAnalysisError, setThresholdAnalysisError] = React.useState<string | null>(null);
    const [thresholdAnalysisRunning, setThresholdAnalysisRunning] = React.useState(false);
    const [thresholdApprovalSavingTarget, setThresholdApprovalSavingTarget] = React.useState<'rails' | 'worldlinco' | null>(null);
    const [worldlincoApprovedApplyRunning, setWorldlincoApprovedApplyRunning] = React.useState(false);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        try {
            const raw = window.localStorage.getItem(ADMIN_RAIL_OPERATOR_NOTES_STORAGE_KEY);
            if (!raw) {
                return;
            }
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') {
                setRailOperatorNotes(parsed as Record<string, string>);
            }
        } catch {
            // Ignore malformed local storage payload.
        }
    }, []);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        try {
            window.localStorage.setItem(ADMIN_RAIL_OPERATOR_NOTES_STORAGE_KEY, JSON.stringify(railOperatorNotes));
        } catch {
            // Ignore local storage write failures in locked-down browsers.
        }
    }, [railOperatorNotes]);
    const pushLiveLog = useCallback((level: LiveLogItem['level'], message: string, meta?: Partial<LiveLogItem> & { capabilityId?: string }) => {
        const dedupKey = `${level}:${message}`;
        const now = Date.now();
        const lastLoggedAt = liveLogDedupRef.current[dedupKey] || 0;
        if ((now - lastLoggedAt) < 15000) {
            return;
        }
        liveLogDedupRef.current[dedupKey] = now;
        const connectionMeta = meta?.connection_id
            ? {
                connection_id: meta.connection_id,
                flow_id: meta.flow_id || '',
                step_id: meta.step_id || '',
                action: meta.action || '',
                panel_id: meta.panel_id || 'PANEL-ADMIN-DASHBOARD',
            }
            : attachActiveAdminConnectionMeta({
                fallbackCapabilityId: meta?.capabilityId || 'dashboard',
                panelId: meta?.panel_id || 'PANEL-ADMIN-DASHBOARD',
                execution: 'observe',
            });
        setLiveLogs((prev: any) => [
            {
                id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                level,
                message,
                createdAt: new Date().toLocaleTimeString('ko-KR'),
                connection_id: connectionMeta.connection_id,
                flow_id: connectionMeta.flow_id,
                step_id: connectionMeta.step_id,
                action: connectionMeta.action,
                panel_id: connectionMeta.panel_id,
            },
            ...prev,
        ].slice(0, 30));
        registerAdminAutoConnectGraphEvent({
            meta: {
                ...connectionMeta,
                route_id: meta?.route_id || 'ROUTE-DASHBOARD',
                capability_id: meta?.capabilityId || 'dashboard',
                command_id: connectionMeta.connection_id,
            },
            source: meta?.capabilityId === 'settlement' ? 'settlement' : meta?.capabilityId ? 'orchestrator' : 'admin-dashboard',
            title: '관리자 라이브로그',
            detail: message,
            status: level === 'warning' ? 'warning' : level === 'success' ? 'success' : 'linked',
            activate: false,
        });
    }, []);
    const [runtimeMessage, setRuntimeMessage] = React.useState('');
    const appendLiveLog = useCallback((
        event: string,
        message: string,
        stage?: string,
        _timestamp?: string,
        severity: 'info' | 'success' | 'warning' | 'error' = 'info',
    ) => {
        const level = severity === 'error' ? 'warning' : severity === 'success' ? 'success' : severity === 'warning' ? 'warning' : 'info';
        pushLiveLog(level, `${event}${stage ? `:${stage}` : ''} ${message}`);
    }, [pushLiveLog]);
    const pushAssistantNotice = useCallback((title: string, content: string) => {
        pushLiveLog('info', `${title} — ${content}`);
    }, [pushLiveLog]);
    const {
        adminManualOrchestratorStepId,
        setAdminManualOrchestratorStepId,
        adminManualMeta,
        setAdminManualMeta,
        selectedAdminManualStep,
        selectedAdminManualStepState,
        previousAdminManualStep,
        nextAdminManualStep,
        completedManualStepCount,
        toggleAdminManualAction,
        toggleAdminManualStepCompleted,
        updateAdminManualStepNote,
        updateAdminManualStepField,
        addAdminManualAttachmentLink,
        removeAdminManualAttachmentLink,
        updateAdminManualStepRouteStage,
        updateAdminManualStepDuration,
        updateAdminManualExternalStageMirror,
        moveAdminManualStep,
        downloadAdminManualWorklog,
        openMarketplaceOrchestratorBridge,
        openAdminLlmOrchestratorBridge,
    } = useAdminManualOrchestratorController({
        storageKey: ADMIN_MANUAL_ORCHESTRATOR_STATE_STORAGE_KEY,
        metaStorageKey: ADMIN_MANUAL_ORCHESTRATOR_META_STORAGE_KEY,
        initialStepId: 'ARCH-001',
        latestDedicatedOrder,
        onOpenAdminLlm: () => router.push('/admin/llm'),
        onOpenMarketplaceOrchestrator: () => {
            if (marketplaceOrchestratorHref.startsWith('http://') || marketplaceOrchestratorHref.startsWith('https://')) {
                window.location.assign(marketplaceOrchestratorHref);
                return;
            }
            router.push(marketplaceOrchestratorHref);
        },
        pushLiveLog: (level, message) => pushLiveLog(level, message),
    });

    const {
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
    } = useAdminAdOperationsController({
        apiBaseUrl,
        adVideoOrders,
        adSettlementDashboard,
        buildApiErrorMessage,
        handleAdminUnauthorized: (...args) => handleAdminUnauthorized(...args),
        loadDashboard: (...args) => loadDashboard(...args),
        pushLiveLog: (...args) => pushLiveLog(...args),
        downloadCsvFromRows,
        adSettlementApiUnavailableRef,
    });
    const {
        systemSettings,
        systemSettingsDraft,
        systemSettingsOpen,
        systemSettingsLoading,
        systemSettingsSaving,
        systemSettingsFillingMissing,
        systemAutomaticApplying,
        systemSettingsMessage,
        identityProviderSettings,
        adminPasswordCurrent,
        setAdminPasswordCurrent,
        adminPasswordNext,
        setAdminPasswordNext,
        adminPasswordConfirm,
        setAdminPasswordConfirm,
        adminPasswordChanging,
        adminPasswordMessage,
        postgresPasswordNext,
        setPostgresPasswordNext,
        postgresPasswordConfirm,
        setPostgresPasswordConfirm,
        postgresPasswordSaving,
        postgresPasswordMessage,
        categories,
        selectedCategoryId,
        setSelectedCategoryId,
        categoryStats,
        categoryRecentProjects,
        categoryName,
        setCategoryName,
        categoryDescription,
        setCategoryDescription,
        categoryCreating,
        categoryUpdatingId,
        categoryDeletingId,
        editingCategoryId,
        editingCategoryName,
        setEditingCategoryName,
        editingCategoryDescription,
        setEditingCategoryDescription,
        hideEmptyCategories,
        setHideEmptyCategories,
        categorySortBy,
        setCategorySortBy,
        categoryMessage,
        loadSystemSettings,
        fillMissingSystemSettings,
        changeAdminPassword,
        updatePostgresRuntimePassword,
        updateSystemSettingValue,
        toggleSystemSettingsSection,
        saveSystemSettings,
        applyGlobalAutomaticMode,
        loadCategories,
        createCategory,
        beginEditCategory,
        cancelEditCategory,
        updateCategory,
        deleteCategory,
        loadCategoryStats,
    } = useAdminSystemCategoryController({
        apiBaseUrl,
        handleAdminUnauthorized: (...args) => handleAdminUnauthorized(...args),
        normalizeSystemSettingsMessage,
        pushLiveLog: (level, message) => pushLiveLog(level, message),
        setAutoRefreshEnabled,
        setRefreshSeconds,
        hideEmptyStorageKey: ADMIN_HIDE_EMPTY_CATEGORIES_STORAGE_KEY,
        categorySortStorageKey: ADMIN_CATEGORY_SORT_STORAGE_KEY,
    });
    const {
        sampleTemplates,
        sampleCreating,
        sampleResult,
        sampleBatchCount,
        setSampleBatchCount,
        sampleCleanupPattern,
        setSampleCleanupPattern,
        selectedCategoryStat,
        selectedCategoryDelta,
        createSampleProduct,
        createBatchSamples,
        runSampleCleanup,
    } = useAdminSampleProductsController({
        apiBaseUrl,
        categories,
        selectedCategoryId,
        setSelectedCategoryId,
        categoryStats,
        handleAdminUnauthorized: (...args) => handleAdminUnauthorized(...args),
        loadDashboard: (...args) => loadDashboard(...args),
        loadCategoryStats,
        pushLiveLog: (level, message) => pushLiveLog(level, message),
        settingsStorageKey: ADMIN_SAMPLE_SETTINGS_STORAGE_KEY,
    });
    const {
        adminCompletionHistory,
        adminTraceHistory,
        adminRetryQueueItems,
        adminConnectionLookupId,
        setAdminConnectionLookupId,
        adminConnectionLookupLoading,
        adminConnectionLookupResult,
        adminTraceFilter,
        setAdminTraceFilter,
        adminReplayQueueId,
        loadAdminCompletionHistory,
        loadAdminTraceHistory,
        loadAdminRetryQueue,
        loadAdminConnectionLookup,
        handleReplayRetryQueue,
        filteredAdminCompletionHistory,
        filteredAdminTraceHistory,
        filteredAdminRetryQueueItems,
    } = useAdminAutoConnectController({
        apiBaseUrl,
        authChecked,
        activeConnectionId: autoConnectGraph.active_connection_id || '',
        apiUnavailableRef: autoConnectGraphApiUnavailableRef,
        handleAdminUnauthorized: (...args) => handleAdminUnauthorized(...args),
        setAdminApiBackoff,
        pushLiveLog: (level, message) => pushLiveLog(level, message),
        setError,
    });
    useEffect(() => {
        try {
            localStorage.setItem(ADMIN_AUTO_RECOVERY_HISTORY_STORAGE_KEY, JSON.stringify(autoRecoveryHistory));
        } catch {
        }
    }, [autoRecoveryHistory]);

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            if (event.origin !== window.location.origin) {
                return;
            }
            if (!event.data || event.data.type !== 'admin-llm-frame-height') {
                return;
            }
            const nextHeight = Number(event.data.height);
            if (!Number.isFinite(nextHeight)) {
                return;
            }
            setLlmPanelHeight(Math.max(1400, Math.min(Math.trunc(nextHeight) + 24, 8000)));
        };

        window.addEventListener('message', handleMessage);
        return () => {
            window.removeEventListener('message', handleMessage);
        };
    }, []);

    useEffect(() => {
        try {
            const checkSessionExpiry = createAdminSessionExpiryChecker({
                token: () => getAdminToken(),
                getAdminTokenExpiryMs,
                warningWindowMs: ADMIN_SESSION_WARNING_WINDOW_MS,
                getRemainingSessionMinutes,
                sessionWarningExpRef,
                onUnauthorized: handleAdminUnauthorized,
                onAppendLiveLog: appendLiveLog,
                onRuntimeMessage: setRuntimeMessage,
                onPushAssistantNotice: pushAssistantNotice,
                extendAdminSessionToken,
            });

            void checkSessionExpiry();
            const storedDashboardPreferencesRaw = localStorage.getItem(ADMIN_DASHBOARD_PREFERENCES_STORAGE_KEY);
            const preferences = storedDashboardPreferencesRaw ? JSON.parse(storedDashboardPreferencesRaw) as {
                refreshSeconds?: number;
                autoRefreshEnabled?: boolean;
            } : {};
            if (typeof preferences.refreshSeconds === 'number') {
                setRefreshSeconds(Math.max(5, Math.min(300, preferences.refreshSeconds)));
            }
            if (typeof preferences.autoRefreshEnabled === 'boolean') {
                setAutoRefreshEnabled(preferences.autoRefreshEnabled);
            }

            const storedAutoRecoveryHistoryRaw = localStorage.getItem(ADMIN_AUTO_RECOVERY_HISTORY_STORAGE_KEY);
            if (storedAutoRecoveryHistoryRaw) {
                const parsedHistory = JSON.parse(storedAutoRecoveryHistoryRaw) as AutoRecoveryHistoryItem[];
                if (Array.isArray(parsedHistory)) {
                    setAutoRecoveryHistory(parsedHistory.slice(0, 20));
                }
            }
        } catch {
        }
    }, []);

    useEffect(() => {
        try {
            localStorage.setItem(ADMIN_LIVE_LOGS_STORAGE_KEY, JSON.stringify(liveLogs.slice(0, 30)));
        } catch {
        }
    }, [liveLogs]);

    useEffect(() => {
        try {
            localStorage.setItem(
                ADMIN_ALERT_VOICE_ENABLED_STORAGE_KEY,
                voiceAlertEnabled ? 'true' : 'false'
            );
        } catch {
        }
    }, [voiceAlertEnabled]);

    useEffect(() => {
        try {
            localStorage.setItem(
                ADMIN_DASHBOARD_PREFERENCES_STORAGE_KEY,
                JSON.stringify({
                    refreshSeconds,
                    autoRefreshEnabled,
                }),
            );
        } catch {
        }
    }, [autoRefreshEnabled, refreshSeconds]);

    useEffect(() => {
        const controller = new AbortController();
        const token = getAdminToken();
        const authUrl = '/api/proxy';
        if (!token) {
            setAuthStatusMessage('로그인 페이지로 이동 중...');
            redirectToAdminLogin(router);
            return () => {
                controller.abort();
            };
        }
        setAuthChecked(false);
        setAuthStatusMessage('관리자 인증 확인 중...');
        fetchWithAdminBootstrapRetry(authUrl, {
            headers: { Authorization: `Bearer ${token}` },
            signal: controller.signal,
            cache: 'no-store',
        }, {
            retries: 1,
            retryDelayMs: 500,
            timeoutMs: 8000,
        })
            .then(async (response) => {
                if (!response.ok) {
                    return null;
                }
                return response.json();
            })
            .then((me) => {
                if (!me || (!me.is_admin && !me.is_superuser)) {
                    setAuthStatusMessage('로그인 페이지로 이동 중...');
                    clearAdminToken();
                    setAdminUser(null);
                    setAuthChecked(false);
                    redirectToAdminLogin(router);
                    return;
                }
                setAdminUser({ username: me.username, email: me.email });
                setAuthStatusMessage('관리자 인증 확인 완료');
                setAuthChecked(true);
            })
            .catch(() => {
                setAuthStatusMessage('인증 확인 실패, 로그인 페이지로 이동 중...');
                clearAdminToken();
                setAdminUser(null);
                setAuthChecked(false);
                redirectToAdminLogin(router);
            });

        return () => {
            controller.abort();
        };
    }, [router, apiBaseUrl]);

    const handleLogout = async () => {
        try {
            const token = getAdminToken();
            if (token) {
                await logoutAdminSession(token);
            }
        } catch {
            // 서버 로그아웃 실패여도 로컬 로그아웃은 계속 진행한다.
        } finally {
            clearAdminToken();
            hardRedirectToAdminLogin();
        }
    };

    const {
        handleAdminUnauthorized,
        refreshAdminStageRun,
        updateAdminStageStatus,
        runCostSimulation,
        applyGeneratorModelOverride,
    } = useAdminPageActions({
        apiBaseUrl,
        setAdminUser,
        setAuthChecked,
        setAuthStatusMessage,
        setError,
        setAdVideoOrders,
        setAdVideoTotal,
        setAdminStageRun,
        setAdminStageSubstepChecks,
        adminStageRun,
        adminStageNoteDraft,
        adminStageRevisionNote,
        adminStageSubstepChecks,
        pushLiveLog,
        setAdminStageRevisionNote,
        setAdminStageNoteDraft,
        setAdminStageUpdateLoading,
        costSimulatorForm,
        setCostSimulatorLoading,
        setCostSimulatorError,
        setCostSimulatorResult,
        setGeneratorModelOverrides,
        generatorEnvKeyMap: GENERATOR_ENV_KEY_MAP,
        updateSystemSettingValue,
    });

    useEffect(() => {
        if (!adminStageRun?.current_stage_id) {
            return;
        }
        setAdminManualOrchestratorStepId(adminStageRun.current_stage_id);
    }, [adminStageRun?.current_stage_id, setAdminManualOrchestratorStepId]);

    useEffect(() => {
        const syncRefinerFixerStage = async () => {
            const token = getAdminToken();
            if (!token) {
                return;
            }
            try {
                const storedRunId = typeof window !== 'undefined'
                    ? localStorage.getItem(ADMIN_MANUAL_ORCHESTRATOR_STAGE_RUN_ID_STORAGE_KEY) || ''
                    : '';
                const existingStageRun = storedRunId
                    ? await refreshAdminStageRun(storedRunId)
                    : null;
                let stageRun = existingStageRun;
                if (!stageRun) {
                    const response = await fetchWithAdminBootstrapRetry(`${apiBaseUrl}/api/marketplace/customer-orchestrate/stage-runs`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify({
                            task: 'admin refiner/fixer stage mirror probe',
                            mode: 'manual_9step',
                            project_name: 'admin-refiner-fixer-stage-probe',
                        }),
                    });
                    if (response.status === 401 || response.status === 403) {
                        handleAdminUnauthorized();
                        return;
                    }
                    const payload = await response.json().catch(() => null);
                    if (!response.ok || !payload) {
                        return;
                    }
                    const createdStageRun = payload as AdminStageRunResponse;
                    stageRun = createdStageRun;
                    setAdminStageRun(createdStageRun);
                    const activeStagePayload = (createdStageRun.stages || []).find((stage) => stage.id === createdStageRun.current_stage_id);
                    const checks = Object.fromEntries(((activeStagePayload?.substeps || []).map((item) => [item.id, Boolean(item.checked)])));
                    setAdminStageSubstepChecks(checks);
                    if (typeof window !== 'undefined' && createdStageRun.run_id) {
                        localStorage.setItem(ADMIN_MANUAL_ORCHESTRATOR_STAGE_RUN_ID_STORAGE_KEY, createdStageRun.run_id);
                    }
                }
                if (!stageRun) {
                    return;
                }
                const refinerFixerStage = Array.isArray(stageRun?.stages)
                    ? stageRun.stages.find((stage: { id?: string }) => stage?.id === 'ARCH-0045')
                    : null;
                if (!stageRun?.run_id || !refinerFixerStage) {
                    return;
                }
                updateAdminManualExternalStageMirror({
                    stageRunId: String(stageRun.run_id),
                    stageId: 'ARCH-0045',
                    status: String(refinerFixerStage.status || ''),
                    label: String(refinerFixerStage.label || ''),
                    title: String(refinerFixerStage.title || ''),
                    summary: String(refinerFixerStage.summary || ''),
                    updatedAt: String(refinerFixerStage.updated_at || stageRun.updated_at || ''),
                });
            } catch {
            }
        };
        void syncRefinerFixerStage();
    }, [apiBaseUrl, handleAdminUnauthorized, refreshAdminStageRun, updateAdminManualExternalStageMirror]);

    const trackDashboardAutoConnect = useMemo(() => createDashboardAutoConnectTracker({
        registerEvent: registerAdminAutoConnectGraphEvent,
        attachMeta: attachActiveAdminConnectionMeta,
        buildMeta: buildAdminAutoConnectMeta,
    }), []);
    const retryWorkspaceSelfRun = useCallback(async (targetStage: 'diagnosis' | 'remediation' = 'remediation', sourcePath?: string | null) => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return null;
        }

        setSelfRunRetrying(true);
        try {
            return await retryWorkspaceSelfRunRequest({
                apiBaseUrl,
                token,
                approvalId: dashboardSelfRunStatus?.approval_id || null,
                sourcePath: sourcePath || null,
                targetStage,
                buildApiErrorMessage,
                onUnauthorized: () => handleAdminUnauthorized(),
                onUnsupported: (message) => {
                    if (!selfRunApiUnavailableRef.current) {
                        pushLiveLog('warning', message);
                    }
                },
                onSuccess: (message) => pushLiveLog('success', message),
                onWarning: (message) => pushLiveLog('warning', message),
                setUnavailable: (nextValue) => {
                    selfRunApiUnavailableRef.current = nextValue;
                },
            });
        } catch (error: any) {
            pushLiveLog('warning', error?.message || 'self-run 재시도에 실패했습니다.');
            return null;
        } finally {
            setSelfRunRetrying(false);
        }
    }, [apiBaseUrl, dashboardSelfRunStatus?.approval_id, handleAdminUnauthorized]);

    const normalizeWorkspaceSelfRun = useCallback(async (cleanupOnly = false) => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return null;
        }

        setSelfRunNormalizing(true);
        try {
            return await normalizeWorkspaceSelfRunRequest({
                apiBaseUrl,
                token,
                approvalId: dashboardSelfRunStatus?.approval_id || null,
                cleanupOnly,
                buildApiErrorMessage,
                onUnauthorized: () => handleAdminUnauthorized(),
                onUnsupported: (message) => {
                    if (!selfRunApiUnavailableRef.current) {
                        pushLiveLog('warning', message);
                    }
                },
                onSuccess: (message) => pushLiveLog('success', message),
                onWarning: (message) => pushLiveLog('warning', message),
                setUnavailable: (nextValue) => {
                    selfRunApiUnavailableRef.current = nextValue;
                },
            });
        } catch (error: any) {
            pushLiveLog('warning', error?.message || 'self-run 정상화에 실패했습니다.');
            return null;
        } finally {
            setSelfRunNormalizing(false);
        }
    }, [apiBaseUrl, dashboardSelfRunStatus?.approval_id, handleAdminUnauthorized]);

    const loadDashboard = useCallback(async (isRefresh = false) => {
        if (loadDashboardInFlightRef.current) {
            return;
        }
        loadDashboardInFlightRef.current = true;
        if (isRefresh) setRefreshing(true);
        else setLoading(true);
        setError(null);
        try {
            if (isRefresh && !capabilityBootstrapReady) {
                setCapabilityBootstrapReady(true);
            }
            autoConnectGraphApiUnavailableRef.current = isAdminApiBackoffActive('auto-connect-graph');
            adMonitorApiUnavailableRef.current = isAdminApiBackoffActive('ad-video-orders-monitor-summary');
            adSettlementApiUnavailableRef.current = isAdminApiBackoffActive('ad-video-orders-settlement-dashboard');
            trackDashboardAutoConnect({
                capabilityId: 'dashboard-sync',
                title: isRefresh ? '관리자 대시보드 새로고침' : '관리자 대시보드 초기 동기화',
                detail: isRefresh ? '관리자 상태 재수집 요청' : '관리자 초기 상태 동기화 요청',
                panelId: 'PANEL-ADMIN-DASHBOARD',
                status: 'queued',
                execution: 'sync',
            });

            const token = localStorage.getItem('admin_token');
            if (!token) {
                handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
                return;
            }
            const controllerResult = await loadAdminDashboardController({
                apiBaseUrl,
                token,
                previousSnapshot: snapshotRef.current,
                currentOverview: overview,
                currentRevenue: revenue,
                currentHealth: health,
                currentLlmStatus: llmStatus,
                adMonitorUnavailable: adMonitorApiUnavailableRef.current,
                adSettlementUnavailable: adSettlementApiUnavailableRef.current,
                includeCapabilityBootstrap: isRefresh || capabilityBootstrapReady,
                formatCurrency,
                buildFallbackAdOrderMonitorSummary,
                buildFallbackAdSettlementDashboard,
            });
            if (controllerResult.unauthorized) {
                setHealth(null);
                setLlmStatus(null);
                setOrchestratorCapabilitySummary(null);
                setSecurityGuardDetail(null);
                setDashboardSelfRunStatus(null);
                setSorisaeFailureStatus(null);
                handleAdminUnauthorized();
                return;
            }
            if (controllerResult.adMonitorUnavailable) {
                setAdminApiBackoff('ad-video-orders-monitor-summary');
                adMonitorApiUnavailableRef.current = true;
            } else {
                clearAdminApiBackoff('ad-video-orders-monitor-summary');
                adMonitorApiUnavailableRef.current = false;
            }
            if (controllerResult.adSettlementUnavailable) {
                setAdminApiBackoff('ad-video-orders-settlement-dashboard');
                adSettlementApiUnavailableRef.current = true;
            } else {
                clearAdminApiBackoff('ad-video-orders-settlement-dashboard');
                adSettlementApiUnavailableRef.current = false;
            }
            controllerResult.liveLogEvents.forEach((entry) => pushLiveLog(entry.level, entry.message));
            if (controllerResult.overviewData) setOverview(controllerResult.overviewData);
            if (controllerResult.revenueData) setRevenue(controllerResult.revenueData);
            if (controllerResult.topData) setTopProjects(controllerResult.topData);
            setHealth(controllerResult.healthData ?? null);
            setLlmStatus(controllerResult.llmData ?? null);
            if (controllerResult.assembledState.adVideoOrders) {
                setAdVideoTotal(Number(controllerResult.assembledState.adVideoTotal || 0));
                setAdVideoOrders(controllerResult.assembledState.adVideoOrders);
            }
            if (controllerResult.assembledState.adOrderMonitorSummary) {
                setAdOrderMonitorSummary(controllerResult.assembledState.adOrderMonitorSummary);
            }
            if (controllerResult.assembledState.adSettlementDashboard) {
                setAdSettlementDashboard(controllerResult.assembledState.adSettlementDashboard);
            }
            setOrchestratorCapabilitySummary(controllerResult.assembledState.orchestratorCapabilitySummary ?? null);
            setSecurityGuardDetail(controllerResult.assembledState.securityGuardDetail);
            setDashboardSelfRunStatus(controllerResult.assembledState.dashboardSelfRunStatus);
            setSorisaeFailureStatus(controllerResult.assembledState.sorisaeFailureStatus);
            if (controllerResult.failedMessages.length > 0) setError(controllerResult.failedMessages.join(' · '));
            snapshotRef.current = controllerResult.nextSnapshot;
            setLastUpdated(controllerResult.lastUpdated);
        } catch (error: any) {
            const message = error?.message || '관리자 대시보드 새로고침에 실패했습니다.';
            setError(message);
            pushLiveLog('warning', message, { capabilityId: 'dashboard', panel_id: 'PANEL-ADMIN-DASHBOARD' });
        } finally {
            loadDashboardInFlightRef.current = false;
            if (isRefresh) setRefreshing(false);
            else setLoading(false);
        }
    }, [apiBaseUrl, capabilityBootstrapReady, handleAdminUnauthorized]);

    const approveWorkspaceSelfRun = useCallback(async () => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return null;
        }
        if (!dashboardSelfRunStatus?.approval_id) {
            pushLiveLog('warning', '승인할 self-run approval_id가 없습니다.');
            return null;
        }

        setSelfRunApproving(true);
        try {
            const result = await approveWorkspaceSelfRunRequest({
                apiBaseUrl,
                token,
                approvalId: dashboardSelfRunStatus.approval_id,
                buildApiErrorMessage,
                onUnauthorized: () => handleAdminUnauthorized(),
                onUnsupported: (message) => {
                    if (!selfRunApiUnavailableRef.current) {
                        pushLiveLog('warning', message);
                    }
                },
                onSuccess: (message) => pushLiveLog('success', message),
                setUnavailable: (nextValue) => {
                    selfRunApiUnavailableRef.current = nextValue;
                },
            });
            await loadDashboard(true);
            return result;
        } catch (error: any) {
            pushLiveLog('warning', error?.message || 'self-run 승인 반영에 실패했습니다.');
            return null;
        } finally {
            setSelfRunApproving(false);
        }
    }, [apiBaseUrl, dashboardSelfRunStatus?.approval_id, handleAdminUnauthorized, loadDashboard, pushLiveLog]);

    const runFocusedSelfHealingPlan = useCallback(async () => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return null;
        }
        setFocusedSelfHealingBusy(true);
        try {
            const response = await fetch(`${apiBaseUrl}/api/admin/focused-self-healing/plan`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    issue_id: `heal-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-ui`,
                    requested_path: focusedSelfHealingRequestedPath,
                    reason: focusedSelfHealingReason,
                    proposal_title: '관리자 메인 화면 Focused Self-Healing',
                    proposal_summary: '메인 화면에서 tower crane 옵션을 바로 선택하기 위한 운영 흐름',
                }),
            });
            const data = await response.json().catch(() => null);
            if (!response.ok || !data) {
                throw new Error(data?.detail || 'focused self-healing plan 호출에 실패했습니다.');
            }
            setFocusedSelfHealingPlan(data as FocusedSelfHealingPlan);
            setFocusedSelfHealingApplyResult(null);
            setFocusedSelfHealingSelectedOptionId(data.options?.[0]?.option_id || '');
            setFocusedSelfHealingApprovalConfirmed(false);
            setFocusedSelfHealingMessage(`plan 완료 · proposal_id=${data.proposal_id}`);
            pushLiveLog('success', `focused self-healing plan 완료 · ${data.proposal_id}`);
            return data as FocusedSelfHealingPlan;
        } catch (error: any) {
            setFocusedSelfHealingMessage(error?.message || 'focused self-healing plan 호출에 실패했습니다.');
            pushLiveLog('warning', error?.message || 'focused self-healing plan 호출에 실패했습니다.');
            return null;
        } finally {
            setFocusedSelfHealingBusy(false);
        }
    }, [apiBaseUrl, focusedSelfHealingReason, focusedSelfHealingRequestedPath, handleAdminUnauthorized, pushLiveLog]);

    const applyFocusedSelfHealing = useCallback(async () => {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
            return null;
        }
        if (!focusedSelfHealingPlan || !focusedSelfHealingSelectedOptionId) {
            setFocusedSelfHealingMessage('먼저 focused self-healing plan 과 옵션 선택을 완료해야 합니다.');
            return null;
        }
        if (focusedSelfHealingPlan.approval_required && !focusedSelfHealingApprovalConfirmed) {
            setFocusedSelfHealingMessage('승인 필요 범위이므로 승인 스위치를 먼저 켜야 합니다.');
            return null;
        }
        setFocusedSelfHealingBusy(true);
        try {
            const response = await fetch(`${apiBaseUrl}/api/admin/focused-self-healing/apply`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    issue_id: focusedSelfHealingPlan.issue_id,
                    requested_path: focusedSelfHealingRequestedPath,
                    reason: focusedSelfHealingReason,
                    approved: focusedSelfHealingApprovalConfirmed,
                    selected_option_id: focusedSelfHealingSelectedOptionId,
                }),
            });
            const data = await response.json().catch(() => null);
            if (!response.ok || !data) {
                throw new Error(data?.detail || 'focused self-healing apply 호출에 실패했습니다.');
            }
            setFocusedSelfHealingApplyResult(data as FocusedSelfHealingApplyResult);
            setFocusedSelfHealingMessage(data.message || 'focused self-healing 실행을 큐에 등록했습니다.');
            pushLiveLog('success', data.message || 'focused self-healing 실행을 큐에 등록했습니다.');
            return data as FocusedSelfHealingApplyResult;
        } catch (error: any) {
            setFocusedSelfHealingMessage(error?.message || 'focused self-healing apply 호출에 실패했습니다.');
            pushLiveLog('warning', error?.message || 'focused self-healing apply 호출에 실패했습니다.');
            return null;
        } finally {
            setFocusedSelfHealingBusy(false);
        }
    }, [apiBaseUrl, focusedSelfHealingApprovalConfirmed, focusedSelfHealingPlan, focusedSelfHealingReason, focusedSelfHealingRequestedPath, focusedSelfHealingSelectedOptionId, handleAdminUnauthorized, pushLiveLog]);

    useEffect(() => {
        if (authChecked) loadDashboard();
    }, [authChecked, loadDashboard]);

    useEffect(() => {
        if (!authChecked || capabilityBootstrapReady) {
            return;
        }
        const timerId = window.setTimeout(() => {
            setCapabilityBootstrapReady(true);
        }, 15000);
        return () => {
            window.clearTimeout(timerId);
        };
    }, [authChecked, capabilityBootstrapReady]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        void loadSystemSettings();
    }, [authChecked, loadSystemSettings]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        if (adminCategoriesBootstrappedRef.current) {
            return;
        }
        adminCategoriesBootstrappedRef.current = true;
        void loadCategories();
    }, [authChecked, loadCategories]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        if (adminCategoryStatsBootstrappedRef.current) {
            return;
        }
        adminCategoryStatsBootstrappedRef.current = true;
        void loadCategoryStats();
    }, [authChecked, loadCategoryStats]);

    useEffect(() => {
        return bindAutoConnectGraphSnapshot({
            setAutoConnectGraph,
            readSnapshot: readAdminAutoConnectGraphSnapshot,
        });
    }, []);

    useEffect(() => {
        adMonitorApiUnavailableRef.current = isAdminApiBackoffActive('ad-video-orders-monitor-summary');
        adSettlementApiUnavailableRef.current = isAdminApiBackoffActive('ad-video-orders-settlement-dashboard');
    }, []);

    useEffect(() => {
        if (!authChecked) {
            sessionWarningExpRef.current = null;
            return;
        }

        const checkSessionExpiry = async () => {
            const currentToken = getAdminToken();
            const expiryMs = getAdminTokenExpiryMs(currentToken);

            if (!currentToken || !expiryMs) {
                return;
            }

            const remainingMs = expiryMs - Date.now();
            if (remainingMs <= 0) {
                handleAdminUnauthorized('관리자 세션 시간이 만료되었습니다. 다시 로그인하세요.');
                return;
            }

            if (remainingMs > ADMIN_SESSION_WARNING_WINDOW_MS) {
                sessionWarningExpRef.current = null;
                return;
            }

            if (sessionWarningExpRef.current === expiryMs) {
                return;
            }

            sessionWarningExpRef.current = expiryMs;
            const shouldExtend = window.confirm(
                `관리자 세션이 약 ${getRemainingSessionMinutes(expiryMs)}분 후 만료됩니다. 로그인 시간을 연장할까요?`,
            );

            if (!shouldExtend) {
                pushLiveLog('warning', '관리자 세션 연장 안내를 보류했습니다.');
                return;
            }

            try {
                await extendAdminSessionToken(currentToken);
                sessionWarningExpRef.current = null;
                pushLiveLog('success', '관리자 세션 시간을 연장했습니다.');
            } catch (error: any) {
                handleAdminUnauthorized(error?.message || '관리자 세션 연장에 실패했습니다. 다시 로그인하세요.');
            }
        };

        void checkSessionExpiry();
        const intervalId = window.setInterval(() => {
            void checkSessionExpiry();
        }, ADMIN_SESSION_CHECK_INTERVAL_MS);

        return () => {
            window.clearInterval(intervalId);
        };
    }, [authChecked, handleAdminUnauthorized]);

    useEffect(() => {
        if (!authChecked || !autoRefreshEnabled) return;

        const interval = setInterval(() => {
            loadDashboard(true);
        }, refreshSeconds * 1000);

        return () => clearInterval(interval);
    }, [authChecked, autoRefreshEnabled, refreshSeconds, loadDashboard]);

    const dashboardAnalysis = useMemo(() => buildAdminPageHealthAnalysis({
        overview,
        revenue,
        health,
        llmStatus,
        orchestratorCapabilitySummary,
        securityGuardDetail,
        dashboardSelfRunStatus,
        sorisaeFailureStatus,
        systemSettingsDisconnected: !systemSettings && !systemSettingsLoading && !!systemSettingsMessage,
        capabilityBootstrapEnabled: capabilityBootstrapReady,
        projectQuery,
        topProjects,
        formatCurrency,
    }), [dashboardSelfRunStatus, formatCurrency, health, llmStatus, orchestratorCapabilitySummary, overview, projectQuery, revenue, securityGuardDetail, sorisaeFailureStatus, systemSettings, systemSettingsLoading, systemSettingsMessage, topProjects]);
    const filteredTopProjects = useMemo(() => {
        const query = projectQuery.trim().toLowerCase();
        if (!query) return topProjects;
        return topProjects.filter((project: any) => project.title.toLowerCase().includes(query));
    }, [projectQuery, topProjects]);
    const generatorRoleOptions = useMemo(() => {
        const installedModels = systemSettings?.summary.available_models || [];
        const fallbackModels = installedModels.length > 0
            ? installedModels
            : [
                systemSettings?.summary.default_model,
                systemSettings?.summary.chat_model,
                systemSettings?.summary.voice_chat_model,
                systemSettings?.summary.reasoning_model,
                systemSettings?.summary.coding_model,
            ].filter((value): value is string => Boolean(value));
        const optimizedDefaults = {
            python_fastapi: pickPreferredModel(installedModels, OPTIMIZED_GENERATOR_DEFAULTS.reasoning, systemSettings?.summary.reasoning_model || systemSettings?.summary.default_model || ''),
            python_worker: pickPreferredModel(installedModels, OPTIMIZED_GENERATOR_DEFAULTS.coding, systemSettings?.summary.coding_model || systemSettings?.summary.default_model || ''),
            nextjs_react: pickPreferredModel(installedModels, OPTIMIZED_GENERATOR_DEFAULTS.uiux, systemSettings?.summary.chat_model || systemSettings?.summary.default_model || ''),
            node_service: pickPreferredModel(installedModels, OPTIMIZED_GENERATOR_DEFAULTS.template, systemSettings?.summary.coding_model || systemSettings?.summary.default_model || ''),
            go_service: pickPreferredModel(installedModels, OPTIMIZED_GENERATOR_DEFAULTS.reasoning, systemSettings?.summary.reasoning_model || systemSettings?.summary.default_model || ''),
            rust_service: pickPreferredModel(installedModels, OPTIMIZED_GENERATOR_DEFAULTS.ad_video, systemSettings?.summary.voice_chat_model || systemSettings?.summary.default_model || ''),
        };
        return (systemSettings?.summary.generator_profiles || []).map((profile) => {
            const defaultModel = optimizedDefaults[profile.id as keyof typeof optimizedDefaults]
                || (profile.runtime_role === 'frontend web'
                    ? (systemSettings?.summary.chat_model || systemSettings?.summary.default_model || '')
                    : (systemSettings?.summary.coding_model || systemSettings?.summary.default_model || ''));
            const selectedModel = generatorModelOverrides[profile.id] || defaultModel;
            return {
                ...profile,
                options: Array.from(new Set([defaultModel, ...fallbackModels].filter(Boolean))),
                defaultModel: selectedModel,
            };
        });
    }, [generatorModelOverrides, systemSettings]);
    const optimizedRuntimeRouteDraft = useMemo(() => {
        const availableModels = systemSettings?.summary.available_models || [];
        return Object.fromEntries(
            Object.entries(OPTIMIZED_RUNTIME_ROUTE_PRESETS).map(([routeKey, candidates]) => {
                const envKey = OPTIMIZED_RUNTIME_ROUTE_ENV_MAP[routeKey];
                const fallback = systemSettingsDraft[envKey] || systemSettings?.summary.default_model || '';
                return [routeKey, pickPreferredModel(availableModels, candidates, fallback)];
            }),
        ) as Record<string, string>;
    }, [systemSettings?.summary.available_models, systemSettings?.summary.default_model, systemSettingsDraft]);
    const adminAlertSpeech = useMemo(
        () => buildAdminAlertSpeech(dashboardAnalysis.opsAlerts, dashboardAnalysis.orchestratorProblemCards),
        [dashboardAnalysis.opsAlerts, dashboardAnalysis.orchestratorProblemCards]
    );

    const visibleCategories = useMemo(
        () => hideEmptyCategories
            ? categories.filter((category) => (categoryStats[category.id]?.total || 0) > 0)
            : categories,
        [categories, categoryStats, hideEmptyCategories],
    );
    const sortedVisibleCategories = useMemo(() => {
        const items = [...visibleCategories];
        items.sort((left, right) => {
            const leftStat = categoryStats[left.id] ?? { total: 0, today: 0, yesterday: 0, downloads: 0, revenue: 0, ratingSum: 0, ratingCount: 0, averageRating: 0, activeCount: 0, inactiveCount: 0 };
            const rightStat = categoryStats[right.id] ?? { total: 0, today: 0, yesterday: 0, downloads: 0, revenue: 0, ratingSum: 0, ratingCount: 0, averageRating: 0, activeCount: 0, inactiveCount: 0 };
            if (categorySortBy === 'name') {
                return left.name.localeCompare(right.name, 'ko');
            }
            if (categorySortBy === 'today') {
                return rightStat.today - leftStat.today || rightStat.total - leftStat.total;
            }
            if (categorySortBy === 'downloads') {
                return rightStat.downloads - leftStat.downloads || rightStat.total - leftStat.total;
            }
            if (categorySortBy === 'revenue') {
                return rightStat.revenue - leftStat.revenue || rightStat.total - leftStat.total;
            }
            if (categorySortBy === 'rating') {
                return rightStat.averageRating - leftStat.averageRating || rightStat.total - leftStat.total;
            }
            if (categorySortBy === 'active') {
                return rightStat.activeCount - leftStat.activeCount || rightStat.total - leftStat.total;
            }
            return rightStat.total - leftStat.total || left.name.localeCompare(right.name, 'ko');
        });
        return items;
    }, [categorySortBy, categoryStats, visibleCategories]);
    const systemSettingsDisconnected = !systemSettings
        && !systemSettingsLoading
        && /설정 조회 실패\((5\d\d)\)|upstream timeout/i.test(systemSettingsMessage);

    const executeAutomaticRecovery = useCallback(async (mode: 'auto' | 'manual') => {
        setAutoRecoveryRunning(true);
        try {
            let thresholdRecoveryHistory: AutoRecoveryHistoryItem | null = null;
            if (!dashboardAnalysis.selfRunFailureInsight && thresholdRecoveryCandidateRef.current) {
                const thresholdActions: string[] = [];
                if (thresholdRecoveryCandidateRef.current.shouldApplyWorldlinco) {
                    const applied = await applyApprovedWorldlincoThresholdRecoveryRef.current();
                    if (applied?.applied) {
                        thresholdActions.push('승인된 월드린코 추천값 적용');
                    }
                }
                if (mode === 'manual') {
                    await applyGlobalAutomaticMode();
                    thresholdActions.push('전역 자동 모드 재적용');
                } else {
                    thresholdActions.push('자동 모드에서는 전역 자동 모드 재적용 생략(수동 실행 전용)');
                }
                thresholdRecoveryHistory = {
                    id: `threshold-${Date.now()}`,
                    triggeredAt: new Date().toLocaleString('ko-KR', { hour12: false }),
                    mode,
                    title: '승인 임계치 기반 자동 복구',
                    category: 'generic',
                    summary: `${thresholdRecoveryCandidateRef.current.reasons.join(' · ')} · ${thresholdActions.join(' · ')}`,
                } as AutoRecoveryHistoryItem;
            }
            const recoveryResult = await executeAdminAutomaticRecovery({
                mode,
                selfRunFailureInsight: dashboardAnalysis.selfRunFailureInsight,
                dashboardSelfRunStatus,
                systemSettingsDisconnected,
                hasOrchestratorCapabilityError: dashboardAnalysis.hasOrchestratorCapabilityError,
                hasOrchestratorCapabilityWarning: dashboardAnalysis.hasOrchestratorCapabilityWarning,
                selfRunApiUnavailable: selfRunApiUnavailableRef.current,
                retryWorkspaceSelfRun,
                normalizeWorkspaceSelfRun,
            });
            if (recoveryResult.shouldOpenPanels) {
                setLiveLogsPanelOpen(true);
                setAutoConnectGraphPanelOpen(true);
                setLlmControlPanelOpen(true);
                setCustomerOrchestratorPanelOpen(true);
            }
            if (recoveryResult.shouldOpenSystemSettingsPanel) {
                setSystemSettingsPanelOpen(true);
                await loadSystemSettings();
            }
            if (recoveryResult.shouldReloadDashboard) {
                await loadDashboard(true);
            }
            setAutoOpsLastExecutedAt(recoveryResult.executedAt);
            setAutoRecoveryHistory((prev: any) => {
                const items = [recoveryResult.historyItem as AutoRecoveryHistoryItem, ...prev];
                if (thresholdRecoveryHistory) {
                    items.unshift(thresholdRecoveryHistory);
                }
                return items.slice(0, 20);
            });
        } finally {
            setAutoRecoveryRunning(false);
        }
    }, [
        dashboardSelfRunStatus?.approval_id,
        applyGlobalAutomaticMode,
        dashboardAnalysis.hasOrchestratorCapabilityError,
        dashboardAnalysis.hasOrchestratorCapabilityWarning,
        loadDashboard,
        loadSystemSettings,
        normalizeWorkspaceSelfRun,
        retryWorkspaceSelfRun,
        dashboardAnalysis.selfRunFailureInsight,
        systemSettingsDisconnected,
    ]);

    useEffect(() => {
        if (!dashboardSelfRunStatus) {
            return;
        }
        const hasSecurityGuardProblem = dashboardAnalysis.orchestratorProblemCards.some((card) => card.id === 'security-guard');
        const signature = `${dashboardSelfRunStatus.approval_id || 'latest'}:${dashboardSelfRunStatus.status}`;
        const shouldNormalize = shouldRunSelfRunAutoNormalization({
            autoOpsEnabled,
            dashboardSelfRunStatus,
            selfRunApiUnavailable: selfRunApiUnavailableRef.current,
            selfRunRetrying,
            selfRunNormalizing,
            hasSecurityGuardProblem,
            normalizationSignature: selfRunNormalizationRef.current,
            currentSignature: signature,
        });
        if (!shouldNormalize) {
            return;
        }
        selfRunNormalizationRef.current = signature;
        void normalizeWorkspaceSelfRun(false).then((result) => {
            if (result?.normalized) {
                void loadDashboard(true);
            }
        });
    }, [
        autoOpsEnabled,
        dashboardSelfRunStatus,
        loadDashboard,
        normalizeWorkspaceSelfRun,
        dashboardAnalysis.orchestratorProblemCards,
        selfRunNormalizing,
        selfRunRetrying,
    ]);

    // 헬스 상태: "ok" 또는 "healthy" 모두 초록색
    const isHealthOk = health?.status === 'ok' || health?.status === 'healthy';
    useEffect(() => {
        if (!authChecked || !voiceAlertEnabled) {
            return;
        }
        const signature = `${dashboardAnalysis.opsAlerts.map((alert) => `${alert.level}:${alert.id}:${alert.message}:${alert.action}`).join('|')}__${dashboardAnalysis.orchestratorProblemCards.map((card) => `${card.id}:${card.state}:${card.detail || card.metric}`).join('|')}`;
        if (!adminAlertSpeech || !signature) {
            return;
        }
        if (lastSpokenAlertSignatureRef.current === signature) {
            return;
        }
        if (!hasSpeechSynthesisActivation()) {
            return;
        }
        // 동일 경고를 매 refresh마다 반복 낭독하지 않도록 signature 변화가 있을 때만 읽는다.
        if (speakAdminAlert(adminAlertSpeech)) {
            lastSpokenAlertSignatureRef.current = signature;
        }
    }, [
        adminAlertSpeech,
        authChecked,
        dashboardAnalysis.opsAlerts,
        dashboardAnalysis.orchestratorProblemCards,
        voiceAlertEnabled,
    ]);

    useEffect(() => {
        if (panelDeepLinkHandledRef.current || !authChecked || typeof window === 'undefined') {
            return;
        }
        panelDeepLinkHandledRef.current = true;

        const panel = new URL(window.location.href).searchParams.get('panel');
        if (panel !== 'subscription-monitor') {
            return;
        }

        setSubscriptionMonitorPanelOpen(true);
        window.requestAnimationFrame(() => {
            window.setTimeout(() => {
                scrollElementIntoViewIfNeeded('[data-testid="admin-subscription-monitor-section"]');
            }, 60);
        });
    }, [authChecked, scrollElementIntoViewIfNeeded]);

    useEffect(() => {
        if (!autoOpsEnabled || !authChecked) return;
        if (autoRecoveryRunning) return;
        const nowTs = Date.now();
        if (nowTs - autoRecoveryLastTriggeredAtRef.current < 45000) {
            return;
        }
        const signature = [
            dashboardSelfRunStatus?.approval_id || '-',
            dashboardSelfRunStatus?.status || '-',
            dashboardAnalysis.selfRunFailureInsight?.category || '-',
            String(systemSettingsDisconnected),
            String(dashboardAnalysis.hasOrchestratorCapabilityError),
            String(dashboardAnalysis.hasOrchestratorCapabilityWarning),
            thresholdAnalysis?.safe_gate.threshold_recovery_allowed ? 'threshold-gate-open' : 'threshold-gate-closed',
            String(thresholdAnalysis?.recommendations.observation_summary.sorisae_classification || '-'),
        ].join('|');
        if (autoOpsSignatureRef.current === signature) return;
        autoOpsSignatureRef.current = signature;
        if (dashboardAnalysis.selfRunFailureInsight) {
            pushLiveLog(dashboardAnalysis.selfRunFailureInsight.severity === 'critical' ? 'warning' : 'info', `자동 진단: ${dashboardAnalysis.selfRunFailureInsight.title}`);
        }
        autoRecoveryLastTriggeredAtRef.current = nowTs;
        void executeAutomaticRecovery('auto');
    }, [
        authChecked,
        autoRecoveryRunning,
        autoOpsEnabled,
        dashboardSelfRunStatus?.approval_id,
        dashboardSelfRunStatus?.status,
        executeAutomaticRecovery,
        dashboardAnalysis.selfRunFailureInsight,
        thresholdAnalysis?.safe_gate.threshold_recovery_allowed,
        thresholdAnalysis?.recommendations.observation_summary.sorisae_classification,
    ]);

    const adminManualOrchestratorAssembly = buildAdminPageManualOrchestratorAssembly({
        adminStageRun: adminStageRun as SharedOrchestratorStageRun | null,
        adminStageNoteDraft,
        setAdminStageNoteDraft,
        adminStageSubstepChecks,
        setAdminStageSubstepChecks,
        adminStageRevisionNote,
        setAdminStageRevisionNote,
        adminStageUpdateLoading,
        updateAdminStageStatus,
        refreshAdminStageRun,
        latestDedicatedOrder: latestDedicatedOrder || null,
        selectedAdminManualStep,
        selectedAdminManualStepState,
        adminManualOrchestratorStepId,
        completedManualStepCount,
        previousAdminManualStep,
        nextAdminManualStep,
        adminManualMeta,
        setAdminManualOrchestratorStepId,
        moveAdminManualStep,
        updateAdminManualStepRouteStage,
        updateAdminManualStepDuration,
        setAdminManualMeta,
        downloadAdminManualWorklog,
        openAdminLlmOrchestratorBridge,
        openMarketplaceOrchestratorBridge,
        toggleAdminManualAction,
        toggleAdminManualStepCompleted,
        updateAdminManualStepNote,
        updateAdminManualStepField,
        addAdminManualAttachmentLink,
        removeAdminManualAttachmentLink,
        latestDedicatedProductionStages,
        latestDedicatedCurrentStage,
        latestDedicatedWorkReady,
        latestDedicatedReadyCount,
        actionTemplateLabel: ADMIN_ACTION_TEMPLATE_LABELS[latestDedicatedOrder?.action_template_key || ''] || '미지정',
        motionTempoLabel: getAdminMotionTempoLabel(latestDedicatedOrder?.motion_tempo),
        humanInteractionRules: ADMIN_HUMAN_OBJECT_INTERACTION_RULES,
        filteredAdminCompletionHistory,
        filteredAdminTraceHistory,
        filteredAdminRetryQueueItems,
        adminReplayQueueId,
        adminTraceFilter,
        loadAdminCompletionHistory,
        loadAdminTraceHistory,
        loadAdminRetryQueue,
        handleReplayRetryQueue,
        setAdminTraceFilter,
        getAdminSceneFrameHint,
    });

    const adminAdOrdersAssembly = buildAdminPageAdOrdersAssembly({
        adOrdersOpen,
        setAdOrdersOpen,
        adVideoTotal,
        adVideoOrders,
        adOrderMonitorSummary,
        adSettlementDashboard,
        adSettlementExporting,
        adMonitorApiUnavailable: adMonitorApiUnavailableRef.current,
        adSettlementApiUnavailable: adSettlementApiUnavailableRef.current,
        actionTemplateLabels: ADMIN_ACTION_TEMPLATE_LABELS,
        onRefresh: () => {
            trackDashboardAutoConnect({
                capabilityId: 'settlement-dashboard',
                title: '광고 주문 새로고침',
                detail: '광고 주문/정산 모니터링 새로고침',
                panelId: 'PANEL-ADMIN-SETTLEMENT',
                status: 'linked',
                execution: 'sync',
            });
            clearAdminApiBackoff('ad-video-orders-monitor-summary');
            clearAdminApiBackoff('ad-video-orders-settlement-dashboard');
            adMonitorApiUnavailableRef.current = false;
            adSettlementApiUnavailableRef.current = false;
            void loadDashboard(true);
        },
        onExportSettlementCsv: () => {
            trackDashboardAutoConnect({
                capabilityId: 'settlement-export',
                title: '정산 CSV 다운로드',
                detail: '광고 주문 정산 CSV 다운로드 실행',
                panelId: 'PANEL-ADMIN-SETTLEMENT',
                status: 'linked',
            });
            void exportAdSettlementCsv();
        },
        buildSettlementConnectionId: buildSettlementOrderConnectionId,
        review: {
            expandedOrderId: expandedAdReviewOrderId,
            drafts: adReviewDrafts,
            diffOnly: adReviewDiffOnly,
            statusDiffOnly: adReviewStatusDiffOnly,
            noteDiffOnly: adReviewNoteDiffOnly,
            savingId: adReviewSavingId,
            onOpenPanel: openAdReviewPanel,
            onToggleDiffOnly: toggleAdReviewDiffOnly,
            onToggleStatusDiffOnly: toggleAdReviewStatusDiffOnly,
            onToggleNoteDiffOnly: toggleAdReviewNoteDiffOnly,
            onResetFilters: resetAdReviewFilters,
            onStoryboardModalOpen: setAdStoryboardModal,
            matchesSceneFilter: matchesAdReviewSceneFilter,
            onUpdateDraft: updateAdReviewDraft,
            onSave: (order) => void handleSaveAdReview(order),
        },
        actions: {
            previewLoadingId: adPreviewLoadingId,
            retryingId: adRetryingId,
            onPreview: (order) => void handlePreviewAdOrder(order),
            onDownload: (order) => void handleDownloadAdOrder(order),
            onRetry: (order) => void handleRetryAdOrder(order),
        },
    });

    const adminDashboardOverviewAssembly = buildAdminDashboardOverviewAssembly({
        error,
        dashboardAnalysis,
        selfRunApproving,
        onApproveWorkspaceSelfRun: () => void approveWorkspaceSelfRun(),
        autoOpsEnabled,
        onAutoOpsEnabledChange: setAutoOpsEnabled,
        autoOpsLastExecutedAt,
        autoRecoveryRunning,
        onExecuteAutomaticRecovery: () => void executeAutomaticRecovery('manual'),
        onReloadDashboard: () => void loadDashboard(true),
        autoRecoveryHistory,
        buildCapabilityConnectionId,
        onOpenOrchestratorDetail: (capabilityId, detail, status) => trackDashboardAutoConnect({
            capabilityId: `orchestrator-${capabilityId}`,
            title: status === 'warning' ? '오케스트레이터 경고 상세 이동' : '오케스트레이터 상세 제어 열기',
            detail,
            panelId: 'PANEL-ADMIN-ORCHESTRATOR',
            status,
        }),
        getOrchestratorActionGuide,
        toFileHref,
        dashboardSelfRunStatus: dashboardAnalysis.normalizedDashboardSelfRunStatus,
        getHealthAlertMetrics: (alert) => {
            const metrics = getHealthAlertMetrics(alert);
            return Object.fromEntries(
                Object.entries(metrics).filter(([, value]) => typeof value === 'string' || typeof value === 'number'),
            ) as Record<string, string | number>;
        },
        getHealthAlertRootCause,
        formatHealthMetricLabel,
        formatHealthMetricValue,
        apiBaseUrl,
        onImmediateRefresh: () => {
            trackDashboardAutoConnect({
                capabilityId: 'dashboard-sync',
                title: '관리자 액션 즉시 상태 재수집',
                detail: '관리자 액션 패널에서 상태 재수집 실행',
                panelId: 'PANEL-ADMIN-DASHBOARD',
                status: 'linked',
                execution: 'sync',
            });
            clearAdminApiBackoff('ad-video-orders-monitor-summary');
            clearAdminApiBackoff('ad-video-orders-settlement-dashboard');
            adMonitorApiUnavailableRef.current = false;
            adSettlementApiUnavailableRef.current = false;
            void loadDashboard(true);
        },
        voiceAlertEnabled,
        onToggleVoiceAlertEnabled: () => setVoiceAlertEnabled((prev: any) => !prev),
        onSpeakAdminAlert: () => speakAdminAlert(adminAlertSpeech || '현재 발성할 관리자 경고가 없습니다.'),
        autoRefreshEnabled,
        onToggleAutoRefreshEnabled: () => setAutoRefreshEnabled((prev: any) => !prev),
        refreshSeconds,
        onRefreshSecondsChange: setRefreshSeconds,
        refreshing,
        lastUpdated,
        focusedSelfHealingBusy,
        focusedSelfHealingModalOpen,
        onOpenFocusedSelfHealing: () => setFocusedSelfHealingModalOpen(true),
        onCloseFocusedSelfHealing: () => setFocusedSelfHealingModalOpen(false),
        focusedSelfHealingRequestedPath,
        onFocusedSelfHealingRequestedPathChange: setFocusedSelfHealingRequestedPath,
        focusedSelfHealingReason,
        onFocusedSelfHealingReasonChange: setFocusedSelfHealingReason,
        focusedSelfHealingPlan,
        focusedSelfHealingApplyResult,
        focusedSelfHealingApprovalConfirmed,
        onFocusedSelfHealingApprovalConfirmedChange: setFocusedSelfHealingApprovalConfirmed,
        focusedSelfHealingSelectedOptionId,
        onFocusedSelfHealingSelectedOptionIdChange: setFocusedSelfHealingSelectedOptionId,
        onRunFocusedSelfHealingPlan: () => void runFocusedSelfHealingPlan(),
        onApplyFocusedSelfHealing: () => void applyFocusedSelfHealing(),
        focusedSelfHealingMessage,
    });

    const adminAutoConnectGraphAssembly = buildAdminAutoConnectGraphAssembly({
        autoConnectGraph,
        adminConnectionLookupId,
        onAdminConnectionLookupIdChange: setAdminConnectionLookupId,
        onLoadLookup: () => loadAdminConnectionLookup(),
        adminConnectionLookupLoading,
        adminConnectionLookupResult,
        adminReplayQueueId,
        onReplayRetryQueue: handleReplayRetryQueue,
        setAdminConnectionLookupId,
    });

    const adminSystemSettingsAssembly = buildAdminPageSystemSettingsAssembly({
        systemSettings,
        systemSettingsDisconnected,
        systemSettingsLoading,
        systemSettingsSaving,
        systemSettingsFillingMissing,
        systemAutomaticApplying,
        systemSettingsMessage,
        identityProviderSettings,
        generatorRoleOptions,
        optimizedRuntimeRouteDraft,
        statusSections: ADMIN_SYSTEM_SETTINGS_STATUS_SECTIONS,
        generatorEnvKeyMap: GENERATOR_ENV_KEY_MAP,
        runtimeRouteEnvMap: OPTIMIZED_RUNTIME_ROUTE_ENV_MAP,
        systemSettingsOpen,
        systemSettingsDraft,
        postgresPasswordNext,
        postgresPasswordConfirm,
        postgresPasswordSaving,
        postgresPasswordMessage,
        adminPasswordCurrent,
        adminPasswordNext,
        adminPasswordConfirm,
        adminPasswordChanging,
        adminPasswordMessage,
        onApplyGlobalAutomaticMode: applyGlobalAutomaticMode,
        onLoadSystemSettings: loadSystemSettings,
        onSaveSystemSettings: saveSystemSettings,
        onFillMissingSystemSettings: () => { void fillMissingSystemSettings(); },
        onApplyGeneratorModelOverride: applyGeneratorModelOverride,
        onToggleSystemSettingsSection: toggleSystemSettingsSection,
        onUpdateSystemSettingValue: updateSystemSettingValue,
        onPostgresPasswordNextChange: setPostgresPasswordNext,
        onPostgresPasswordConfirmChange: setPostgresPasswordConfirm,
        onUpdatePostgresRuntimePassword: updatePostgresRuntimePassword,
        onAdminPasswordCurrentChange: setAdminPasswordCurrent,
        onAdminPasswordNextChange: setAdminPasswordNext,
        onAdminPasswordConfirmChange: setAdminPasswordConfirm,
        onChangeAdminPassword: () => { void changeAdminPassword(); },
    });

    const systemSettingsHasUnsavedChanges = useMemo(() => {
        if (!systemSettings) {
            return false;
        }
        const persistedValues = systemSettings.sections.reduce<Record<string, string>>((acc, section) => {
            section.fields.forEach((field) => {
                acc[field.key] = field.value ?? '';
            });
            return acc;
        }, {});

        const allKeys = new Set<string>([
            ...Object.keys(persistedValues),
            ...Object.keys(systemSettingsDraft || {}),
        ]);

        for (const key of allKeys) {
            const persisted = String(persistedValues[key] ?? '');
            const draft = String(systemSettingsDraft?.[key] ?? '');
            if (persisted !== draft) {
                return true;
            }
        }
        return false;
    }, [systemSettings, systemSettingsDraft]);

    const loadSystemSettingsWithGuard = useCallback(() => {
        if (
            systemSettingsHasUnsavedChanges
            && typeof window !== 'undefined'
            && !window.confirm('저장되지 않은 변경사항이 있습니다. 새로고침하면 편집 중인 값이 사라집니다. 계속하시겠습니까?')
        ) {
            return;
        }
        void loadSystemSettings({ forceDraftSync: true });
    }, [loadSystemSettings, systemSettingsHasUnsavedChanges]);

    const adminSystemSettingsAssemblyWithGuard = {
        ...adminSystemSettingsAssembly,
        onLoadSystemSettings: loadSystemSettingsWithGuard,
        systemSettingsHasUnsavedChanges,
    };

    const adminSampleProductsAssembly = buildAdminPageSampleProductsAssembly({
        categories,
        selectedCategoryId,
        onSelectedCategoryIdChange: setSelectedCategoryId,
        selectedCategoryStat,
        selectedCategoryDelta,
        sampleBatchCount,
        onSampleBatchCountChange: setSampleBatchCount,
        sampleCleanupPattern,
        onSampleCleanupPatternChange: setSampleCleanupPattern,
        sampleTemplates,
        sampleCreating,
        sampleResult,
        onCreateBatchSamples: createBatchSamples,
        onRunSampleCleanup: runSampleCleanup,
        onCreateSampleProduct: createSampleProduct,
    });

    const dashboardSummaryCards = [
        {
            id: 'health-score',
            label: '자동 건강상태 점수',
            value: String(adminDashboardOverviewAssembly.automaticHealthScore ?? '-'),
            note: adminDashboardOverviewAssembly.automaticHealthLabel || '운영 상태 스냅샷',
        },
        {
            id: 'self-run-state',
            label: '최근 self-run 상태',
            value: dashboardAnalysis.normalizedDashboardSelfRunStatus?.status || '-',
            note: dashboardAnalysis.normalizedDashboardSelfRunStatus?.approval_id || '최신 approval 추적',
        },
        {
            id: 'auto-recovery',
            label: '자동 복구',
            value: autoRecoveryRunning ? '실행 중' : '대기',
            note: autoRecoveryRunning ? '실시간 복구 루프 가동' : autoRecoveryHistory?.[0]?.triggeredAt || '최근 이력 없음',
        },
        {
            id: 'llm-runtime',
            label: 'LLM 런타임',
            value: llmStatus?.loaded ? 'loaded' : 'not_loaded',
            note: llmStatus?.model_path || llmStatus?.gpu_runtime_label || '런타임 정보 대기',
        },
    ];

    const openAdminSurface = (selector: string, beforeOpen?: () => void) => {
        beforeOpen?.();

        if (typeof window === 'undefined') {
            return;
        }

        window.requestAnimationFrame(() => {
            window.setTimeout(() => {
                scrollElementIntoViewIfNeeded(selector);
            }, 60);
        });
    };

    const getMusicAuthHeaders = useCallback(() => {
        if (typeof window === 'undefined') {
            return {} as Record<string, string>;
        }
        const token = getAdminToken() || window.localStorage.getItem('admin_token') || '';
        const headers: Record<string, string> = {};
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        return headers;
    }, []);

    const readMusicResponsePayload = useCallback(async (res: Response) => {
        const raw = await res.text();
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw) as Record<string, any>;
        } catch {
            return { detail: raw };
        }
    }, []);

    const handleAdminMusicCompose = useCallback(async () => {
        setMusicLoading(true);
        setMusicError(null);
        setMusicComposeResult(null);
        try {
            const intensity = Number.parseFloat(musicIntensity);
            const response = await fetch(`${apiBaseUrl}/api/marketplace/music/compose/emotion`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getMusicAuthHeaders(),
                },
                body: JSON.stringify({
                    emotion: musicEmotion.trim() || 'happy',
                    intensity: Number.isFinite(intensity) ? intensity : 0.7,
                    theme: musicTheme.trim() || undefined,
                }),
            });
            const payload = await readMusicResponsePayload(response);
            if (!response.ok) {
                throw new Error(String(payload?.detail || `음악 생성 실패 (${response.status})`));
            }
            setMusicComposeResult((payload || null) as Record<string, unknown> | null);
            setMusicMode(String(payload?.mode || 'unknown'));
        } catch (err: any) {
            setMusicError(err?.message || '음악 생성 실패');
        } finally {
            setMusicLoading(false);
        }
    }, [apiBaseUrl, getMusicAuthHeaders, musicEmotion, musicIntensity, musicTheme, readMusicResponsePayload]);

    const handleAdminMusicComposeFromCode = useCallback(async () => {
        const code = musicCode.trim();
        if (!code) {
            setMusicError('작곡에 사용할 코드를 입력하세요.');
            return;
        }
        setMusicLoading(true);
        setMusicError(null);
        setMusicCodeResult(null);
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/music/compose/code`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getMusicAuthHeaders(),
                },
                body: JSON.stringify({
                    code,
                    emotion: musicCodeEmotion.trim() || 'creative',
                }),
            });
            const payload = await readMusicResponsePayload(response);
            if (!response.ok) {
                throw new Error(String(payload?.detail || `코드 작곡 실패 (${response.status})`));
            }
            setMusicCodeResult((payload || null) as Record<string, unknown> | null);
            setMusicMode(String(payload?.mode || 'unknown'));
        } catch (err: any) {
            setMusicError(err?.message || '코드 작곡 실패');
        } finally {
            setMusicLoading(false);
        }
    }, [apiBaseUrl, getMusicAuthHeaders, musicCode, musicCodeEmotion, readMusicResponsePayload]);

    const handleAdminMusicCollaboration = useCallback(async () => {
        setMusicLoading(true);
        setMusicError(null);
        setMusicFriendResult(null);
        try {
            const response = await fetch(`${apiBaseUrl}/api/marketplace/music/friends/demo`, {
                method: 'POST',
                headers: {
                    ...getMusicAuthHeaders(),
                },
            });
            const payload = await readMusicResponsePayload(response);
            if (!response.ok) {
                throw new Error(String(payload?.detail || `협업 연결 실패 (${response.status})`));
            }
            setMusicFriendResult((payload || null) as Record<string, unknown> | null);
            setMusicMode(String(payload?.mode || 'unknown'));
        } catch (err: any) {
            setMusicError(err?.message || '협업 연결 실패');
        } finally {
            setMusicLoading(false);
        }
    }, [apiBaseUrl, getMusicAuthHeaders, readMusicResponsePayload]);

    const runExtrasPreviewRequest = useCallback(async (target: 'health' | 'catalog', fromRail = false) => {
        const token = getAdminToken();
        if (!token) {
            setExtrasPreviewState((prev) => ({
                ...prev,
                loading: false,
                statusCode: null,
                durationMs: null,
                fetchedAt: new Date().toISOString(),
                error: '관리자 토큰 없음',
                payload: null,
            }));
            return;
        }

        setExtrasPreviewTarget(target);
        setExtrasPreviewPanelOpen(true);
        setExtrasPreviewState((prev) => ({
            ...prev,
            loading: true,
            error: null,
        }));

        const endpoint = target === 'health'
            ? `${apiBaseUrl}/api/marketplace/extras/health`
            : `${apiBaseUrl}/api/marketplace/extras/catalog`;
        const startedAt = (typeof performance !== 'undefined' ? performance.now() : Date.now());

        try {
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                cache: 'no-store',
            });

            const rawText = await response.text();
            let payload: unknown = rawText;
            try {
                payload = rawText ? JSON.parse(rawText) : null;
            } catch {
                payload = rawText;
            }

            const finishedAt = (typeof performance !== 'undefined' ? performance.now() : Date.now());
            setExtrasPreviewState({
                loading: false,
                statusCode: response.status,
                durationMs: Math.max(0, Math.round(finishedAt - startedAt)),
                fetchedAt: new Date().toISOString(),
                error: response.ok ? null : `API 응답 실패 (${response.status})`,
                payload,
            });

            if (fromRail) {
                pushLiveLog(response.ok ? 'success' : 'warning', `익스/카탈 인앱 프리뷰: ${target} (${response.status})`);
            }
        } catch (error: any) {
            const finishedAt = (typeof performance !== 'undefined' ? performance.now() : Date.now());
            setExtrasPreviewState({
                loading: false,
                statusCode: null,
                durationMs: Math.max(0, Math.round(finishedAt - startedAt)),
                fetchedAt: new Date().toISOString(),
                error: error?.message || '익스/카탈 프리뷰 조회 실패',
                payload: null,
            });
            if (fromRail) {
                pushLiveLog('warning', `익스/카탈 인앱 프리뷰 실패: ${target}`);
            }
        }
    }, [apiBaseUrl, pushLiveLog]);

    const openSorisaeResultJsonPanel = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            setSorisaeResultJsonPanelOpen(true);
            setSorisaeResultJsonState((prev) => ({
                ...prev,
                loading: false,
                statusCode: null,
                durationMs: null,
                fetchedAt: new Date().toISOString(),
                error: '관리자 토큰이 없어 결과 JSON을 불러오지 못했습니다.',
                payload: null,
            }));
            return;
        }

        setSorisaeResultJsonPanelOpen(true);
        setSorisaeResultJsonState((prev) => ({
            ...prev,
            loading: true,
            error: null,
        }));

        const startedAt = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        const endpoint = `${apiBaseUrl}/api/admin/sorisae-failure-monitor/latest/result-json`;

        try {
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                cache: 'no-store',
            });

            const rawText = await response.text();
            let parsedBody: any = null;
            try {
                parsedBody = rawText ? JSON.parse(rawText) : null;
            } catch {
                parsedBody = null;
            }

            const finishedAt = (typeof performance !== 'undefined' ? performance.now() : Date.now());
            const payloadCandidate = parsedBody?.payload ?? parsedBody ?? rawText;
            const summarizedPayload = typeof payloadCandidate === 'object' && payloadCandidate !== null
                ? {
                    classification: (payloadCandidate as any)?.classification ?? null,
                    apiFail: (payloadCandidate as any)?.apiFail ?? (payloadCandidate as any)?.api_fail ?? null,
                    uiFail: (payloadCandidate as any)?.uiFail ?? (payloadCandidate as any)?.ui_fail ?? null,
                    adminPush: (() => {
                        const adminPushPayload = (payloadCandidate as any)?.adminPush ?? (payloadCandidate as any)?.admin_push ?? null;
                        if (!adminPushPayload || typeof adminPushPayload !== 'object') {
                            return adminPushPayload;
                        }
                        const maxUsers = Math.max(1, Number(railSettings.list.max_items || 20));
                        return {
                            ...adminPushPayload,
                            users: Array.isArray((adminPushPayload as any).users)
                                ? (adminPushPayload as any).users.slice(0, maxUsers)
                                : [],
                        };
                    })(),
                }
                : payloadCandidate;
            setSorisaeResultJsonState({
                loading: false,
                statusCode: response.status,
                durationMs: Math.max(0, Math.round(finishedAt - startedAt)),
                fetchedAt: new Date().toISOString(),
                error: response.ok
                    ? null
                    : String(parsedBody?.detail || rawText || `결과 JSON 조회 실패 (${response.status})`),
                resultJsonPath: String(parsedBody?.result_json_path || ''),
                payload: railSettings.list.include_raw_payload ? payloadCandidate : summarizedPayload,
            });
        } catch (error: any) {
            const finishedAt = (typeof performance !== 'undefined' ? performance.now() : Date.now());
            setSorisaeResultJsonState({
                loading: false,
                statusCode: null,
                durationMs: Math.max(0, Math.round(finishedAt - startedAt)),
                fetchedAt: new Date().toISOString(),
                error: error?.message || '결과 JSON 조회 중 네트워크 오류가 발생했습니다.',
                resultJsonPath: null,
                payload: null,
            });
        }
    }, [apiBaseUrl, railSettings.list.include_raw_payload, railSettings.list.max_items]);

    const loadRailSettings = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            return;
        }
        setRailSettingsLoading(true);
        setRailSettingsError(null);
        try {
            const payload = await loadAdminRailSettings({
                apiBaseUrl,
                token,
            });
            setRailSettings(payload.rails);
            setRailSettingsDraft(payload.rails);
            setRailSettingsUpdatedAt(payload.updated_at || null);
        } catch (error: any) {
            if (error?.message === '__ADMIN_RAIL_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            setRailSettingsError(error?.message || '레일 설정을 불러오지 못했습니다.');
        } finally {
            setRailSettingsLoading(false);
        }
    }, [apiBaseUrl, handleAdminUnauthorized]);

    const updateRailSettingDraft = useCallback((railId: AdminRailId, key: string, value: string | number | boolean) => {
        setRailSettingsDraft((prev) => ({
            ...prev,
            [railId]: {
                ...((prev[railId] as unknown) as Record<string, unknown>),
                [key]: value,
            },
        }) as AdminRailSettingsMap);
    }, []);

    const resetRailSettingDraft = useCallback((railId: AdminRailId) => {
        const defaults = cloneAdminRailSettingsDefaults();
        setRailSettingsDraft((prev) => ({
            ...prev,
            [railId]: defaults[railId],
        }));
    }, []);

    const saveRailSettingsFor = useCallback(async (railId: AdminRailId) => {
        const token = getAdminToken();
        if (!token) {
            handleAdminUnauthorized();
            return;
        }
        setRailSettingsSavingId(railId);
        setRailSettingsError(null);
        try {
            const payload = await saveAdminRailSettings({
                apiBaseUrl,
                token,
                rails: railSettingsDraft,
            });
            setRailSettings(payload.rails);
            setRailSettingsDraft(payload.rails);
            setRailSettingsUpdatedAt(payload.updated_at || null);
            setRailActionMessage(`${ADMIN_RAIL_ACTION_ITEMS.find((item) => item.id === railId)?.label || railId} 설정을 저장했습니다.`);
        } catch (error: any) {
            if (error?.message === '__ADMIN_RAIL_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            setRailSettingsError(error?.message || '레일 설정 저장에 실패했습니다.');
        } finally {
            setRailSettingsSavingId(null);
        }
    }, [apiBaseUrl, handleAdminUnauthorized, railSettingsDraft]);

    const loadThresholdAnalysisState = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            return;
        }
        setThresholdAnalysisLoading(true);
        setThresholdAnalysisError(null);
        try {
            const payload = await loadAdminThresholdAnalysis({ apiBaseUrl, token });
            setThresholdAnalysis(payload);
        } catch (error: any) {
            if (error?.message === '__ADMIN_THRESHOLD_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            setThresholdAnalysisError(error?.message || '임계치 분석 상태를 불러오지 못했습니다.');
        } finally {
            setThresholdAnalysisLoading(false);
        }
    }, [apiBaseUrl, handleAdminUnauthorized]);

    const runThresholdAnalysis = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            handleAdminUnauthorized();
            return;
        }
        setThresholdAnalysisRunning(true);
        setThresholdAnalysisError(null);
        try {
            const payload = await analyzeAdminThresholds({
                apiBaseUrl,
                token,
                health: (health as unknown as Record<string, unknown>) || null,
                sorisaeFailure: (sorisaeFailureStatus as unknown as Record<string, unknown>) || null,
                railSettings: railSettingsDraft,
            });
            setThresholdAnalysis(payload);
            setRailActionMessage('임계치 분석 모드를 실행해 최근 관측값 기반 권장치를 계산했습니다.');
        } catch (error: any) {
            if (error?.message === '__ADMIN_THRESHOLD_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            setThresholdAnalysisError(error?.message || '임계치 분석 실행에 실패했습니다.');
        } finally {
            setThresholdAnalysisRunning(false);
        }
    }, [apiBaseUrl, handleAdminUnauthorized, health, railSettingsDraft, sorisaeFailureStatus]);

    const saveThresholdApproval = useCallback(async (target: 'rails' | 'worldlinco', approved: boolean) => {
        const token = getAdminToken();
        if (!token) {
            handleAdminUnauthorized();
            return;
        }
        setThresholdApprovalSavingTarget(target);
        setThresholdAnalysisError(null);
        try {
            const payload = await approveAdminThresholdTarget({ apiBaseUrl, token, target, approved });
            setThresholdAnalysis(payload);
            setRailActionMessage(`${target === 'rails' ? '임계치' : '월드린코 튜닝'} 승인 상태를 저장했습니다.`);
        } catch (error: any) {
            if (error?.message === '__ADMIN_THRESHOLD_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            setThresholdAnalysisError(error?.message || '승인 상태 저장에 실패했습니다.');
        } finally {
            setThresholdApprovalSavingTarget(null);
        }
    }, [apiBaseUrl, handleAdminUnauthorized]);

    const applyApprovedWorldlincoThresholdRecovery = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            handleAdminUnauthorized();
            return null;
        }
        setWorldlincoApprovedApplyRunning(true);
        setThresholdAnalysisError(null);
        try {
            const payload = await applyApprovedWorldlincoRecommendations({ apiBaseUrl, token });
            setRailActionMessage('승인된 월드린코 자동 튜닝 추천값을 실제 SSOT에 적용했습니다.');
            await loadThresholdAnalysisState();
            return payload;
        } catch (error: any) {
            if (error?.message === '__ADMIN_THRESHOLD_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return null;
            }
            setThresholdAnalysisError(error?.message || '승인된 월드린코 추천값 적용에 실패했습니다.');
            return null;
        } finally {
            setWorldlincoApprovedApplyRunning(false);
        }
    }, [apiBaseUrl, handleAdminUnauthorized, loadThresholdAnalysisState]);

    useEffect(() => {
        applyApprovedWorldlincoThresholdRecoveryRef.current = applyApprovedWorldlincoThresholdRecovery;
    }, [applyApprovedWorldlincoThresholdRecovery]);

    const railDirtyState = useMemo<Record<AdminRailId, boolean>>(() => ({
        sla: JSON.stringify(railSettings.sla) !== JSON.stringify(railSettingsDraft.sla),
        list: JSON.stringify(railSettings.list) !== JSON.stringify(railSettingsDraft.list),
        ops: JSON.stringify(railSettings.ops) !== JSON.stringify(railSettingsDraft.ops),
        cover: JSON.stringify(railSettings.cover) !== JSON.stringify(railSettingsDraft.cover),
        llm: JSON.stringify(railSettings.llm) !== JSON.stringify(railSettingsDraft.llm),
        performance: JSON.stringify(railSettings.performance) !== JSON.stringify(railSettingsDraft.performance),
        latency: JSON.stringify(railSettings.latency) !== JSON.stringify(railSettingsDraft.latency),
        data: JSON.stringify(railSettings.data) !== JSON.stringify(railSettingsDraft.data),
        monitoring: JSON.stringify(railSettings.monitoring) !== JSON.stringify(railSettingsDraft.monitoring),
    }), [railSettings, railSettingsDraft]);

    const thresholdRecoveryCandidate = useMemo(() => {
        if (!thresholdAnalysis?.safe_gate.threshold_recovery_allowed) {
            return null;
        }
        const summary = thresholdAnalysis.recommendations.observation_summary || {};
        const metrics = summary.metrics || {};
        const p95Observed = Number(metrics.p95_latency_ms || 0);
        const p95Budget = Number(thresholdAnalysis.recommendations.rails.latency.p95_budget_ms || 0);
        const cpuUsage = Number(summary.cpu_usage_percent || 0);
        const queueDepth = Number(summary.queue_depth || 0);
        const sorisaeClassification = String(summary.sorisae_classification || 'unknown');
        const reasons: string[] = [];
        if (p95Observed > 0 && p95Budget > 0 && p95Observed > p95Budget) {
            reasons.push(`p95 ${p95Observed}ms > budget ${p95Budget}ms`);
        }
        if (cpuUsage >= 85) {
            reasons.push(`cpu ${cpuUsage}%`);
        }
        if (queueDepth >= 5) {
            reasons.push(`queue ${queueDepth}`);
        }
        if (sorisaeClassification !== 'ALL_PASS' && sorisaeClassification !== 'unknown') {
            reasons.push(`sorisae ${sorisaeClassification}`);
        }
        if (reasons.length === 0) {
            return null;
        }
        return {
            reasons,
            shouldApplyWorldlinco: thresholdAnalysis.safe_gate.worldlinco_auto_apply_allowed && sorisaeClassification !== 'ALL_PASS' && sorisaeClassification !== 'unknown',
        };
    }, [thresholdAnalysis]);

    useEffect(() => {
        thresholdRecoveryCandidateRef.current = thresholdRecoveryCandidate;
    }, [thresholdRecoveryCandidate]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        void loadRailSettings();
    }, [authChecked, loadRailSettings]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        void loadThresholdAnalysisState();
    }, [authChecked, loadThresholdAnalysisState]);

    const openRailPanel = useCallback((railId: AdminRailActionItem['id']) => {
        switch (railId) {
            case 'sla':
                setSlaOpen(true);
                break;
            case 'list':
                setSorisaeResultJsonPanelOpen(true);
                break;
            case 'ops':
                setOpsOpen(true);
                break;
            case 'cover':
                setFastPathOpen(true);
                break;
            case 'llm':
                setLlmPathOpen(true);
                break;
            case 'performance':
                setPerformanceOpen(true);
                break;
            case 'latency':
                setP50p95Open(true);
                break;
            case 'data':
                setPrometheusOpen(true);
                break;
            case 'monitoring':
                setGrafanaOpen(true);
                break;
            default:
                break;
        }
    }, []);

    const runRailEmergencyAction = useCallback(async (railId: AdminRailActionItem['id']) => {
        setRailActionBusyId(railId);
        setRailActionError(null);
        setRailActionMessage(null);
        try {
            const currentSettings = railSettingsDraft[railId] as Record<string, any>;
            if (railId === 'sla') {
                if (!currentSettings.auto_push_on_breach) {
                    openRailPanel('sla');
                    setRailActionMessage('저장된 SLA 설정에서 자동 Push가 비활성화되어 있어 패널만 열었습니다.');
                    return;
                }
                const token = getAdminToken();
                if (!token) {
                    throw new Error('관리자 토큰이 없어 Push 재전송을 수행할 수 없습니다.');
                }
                const response = await fetch(`${apiBaseUrl}/api/admin/sorisae-failure-monitor/latest/push`, {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    cache: 'no-store',
                });
                const raw = await response.text();
                let payload: any = null;
                try {
                    payload = raw ? JSON.parse(raw) : null;
                } catch {
                    payload = raw;
                }
                if (!response.ok) {
                    throw new Error(String(payload?.detail || raw || `Push 재전송 실패 (${response.status})`));
                }
                setRailActionPayload(payload);
                setRailActionMessage(`관리자 Push 재전송을 완료했습니다. 쿨다운 ${currentSettings.breach_cooldown_minutes || 15}분 기준으로 운영하세요.`);
                await openSorisaeResultJsonPanel();
            } else if (railId === 'list') {
                await openSorisaeResultJsonPanel();
                setRailActionMessage(`최신 결과 JSON을 다시 조회했습니다. raw payload ${currentSettings.include_raw_payload ? '포함' : '요약'} 모드입니다.`);
            } else if (railId === 'ops') {
                openRailPanel('ops');
                if (currentSettings.auto_apply_global_mode) {
                    await applyGlobalAutomaticMode();
                    setRailActionMessage(`전역 자동 모드를 적용했습니다. 게이트 레벨=${currentSettings.deployment_gate_level || 'strict'}`);
                } else {
                    setRailActionMessage('저장된 운영 설정상 자동 적용이 꺼져 있어 패널만 열었습니다.');
                }
            } else if (railId === 'llm') {
                if (!currentSettings.enabled) {
                    setRailActionMessage('저장된 LLM 레일 설정이 비활성화되어 있어 이동하지 않았습니다.');
                } else {
                    router.push('/admin/llm');
                    setRailActionMessage(`LLM 관리 페이지로 이동했습니다. timeout=${currentSettings.route_timeout_ms || 45000}ms`);
                }
            } else if (railId === 'monitoring') {
                openRailPanel('monitoring');
                if (currentSettings.open_external_dashboard && currentSettings.grafana_base_url && typeof window !== 'undefined') {
                    window.open(String(currentSettings.grafana_base_url), '_blank', 'noopener,noreferrer');
                }
                await loadDashboard(true);
                setRailActionMessage(`모니터링 패널 오픈 + 대시보드 새로고침을 완료했습니다. refresh=${currentSettings.auto_refresh_seconds || 20}s`);
            } else if (railId === 'data') {
                openRailPanel('data');
                setRailActionMessage(`Prometheus 패널을 열었습니다. 기본 메트릭=${currentSettings.selected_metric_key || 'http_requests_total'}`);
            } else {
                openRailPanel(railId);
                setRailActionMessage('선택한 레일 패널을 즉시 열었습니다.');
            }
        } catch (error: any) {
            setRailActionError(error?.message || '레일 즉시조치 실행 중 오류가 발생했습니다.');
        } finally {
            setRailActionBusyId(null);
        }
    }, [apiBaseUrl, applyGlobalAutomaticMode, loadDashboard, openRailPanel, openSorisaeResultJsonPanel, railSettingsDraft, router]);

    const runFlowAdmDashRailCommand = useCallback(async (commandLabel: string) => {
        setFlowAdmDashCommandBusyId(commandLabel);
        setRailActionError(null);
        setRailActionMessage(null);
        try {
            const token = getAdminToken();
            if (!token) {
                throw new Error('관리자 토큰이 없어 FLOW-ADM-DASH 검증을 실행할 수 없습니다.');
            }
            // FLOW-ADM-DASH 경로 핵심: 대시보드 새로고침 + 전역 설정 API 재조회
            await loadDashboard(true);
            setSystemSettingsPanelOpen(true);
            const settingsResponse = await fetch(`${apiBaseUrl}/api/admin/system-settings`, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                cache: 'no-store',
            });
            if (settingsResponse.status === 401 || settingsResponse.status === 403) {
                handleAdminUnauthorized();
                return;
            }
            if (!settingsResponse.ok) {
                throw new Error(`전역 설정 조회 실패(${settingsResponse.status})`);
            }
            await loadSystemSettings();
            setRailActionMessage(`${commandLabel} 웹 실행 완료: 대시보드 새로고침 + 전역 설정 재조회(502 미검출).`);
        } catch (error: any) {
            setRailActionError(error?.message || `${commandLabel} 실행 중 오류가 발생했습니다.`);
        } finally {
            setFlowAdmDashCommandBusyId(null);
        }
    }, [apiBaseUrl, handleAdminUnauthorized, loadDashboard, loadSystemSettings]);

    const railPanelOpenState = useMemo<Record<AdminRailActionItem['id'], boolean>>(() => ({
        sla: slaOpen,
        list: sorisaeResultJsonPanelOpen,
        ops: opsOpen,
        cover: fastPathOpen,
        llm: llmPathOpen,
        performance: performanceOpen,
        latency: p50p95Open,
        data: prometheusOpen,
        monitoring: grafanaOpen,
    }), [
        slaOpen,
        sorisaeResultJsonPanelOpen,
        opsOpen,
        fastPathOpen,
        llmPathOpen,
        performanceOpen,
        p50p95Open,
        prometheusOpen,
        grafanaOpen,
    ]);

    const launcherLeftColumn = [
        {
            id: 'admin-control-hub',
            label: '🧩 ADMIN CONTROL HUB',
            summary: '운영자 명령 허브 · 설정 새로고침 · 전역 자동 전환',
            accent: 'slate',
            onClick: () => setAdminControlHubOpen(true),
        },
        {
            id: 'system-settings',
            label: '🧭 전역 .env 설정 패널',
            summary: '도메인 · 저장 경로 · runtime · .env 운영값',
            accent: 'cyan',
            onClick: () => setSystemSettingsPanelOpen(true),
        },
        {
            id: 'auto-connect',
            label: '🕸️ self auto-connect graph',
            summary: 'connection_id 흐름 · active graph · DB 조회',
            accent: 'blue',
            onClick: () => setAutoConnectGraphPanelOpen(true),
        },
        {
            id: 'category',
            label: '🗂️ 마켓플레이스 카테고리 관리',
            summary: '카테고리 등록 · 통계 · 최근 프로젝트',
            accent: 'blue',
            onClick: () => setCategoryPanelOpen(true),
        },
        {
            id: 'travel-kpi-dashboard',
            label: '📊 Travel Partner KPI',
            summary: 'CTR · 예약확정률 · 취소율 · 커미션 · RPS · SLA · fallback',
            accent: 'emerald',
            onClick: () => setTravelPartnerKpiOpen(true),
        },
    ] as const;

    const launcherRightColumn = [
        {
            id: 'health-overview',
            label: '🩺 관리자 자동 건강상태 / 자가진단 / 자가개선',
            summary: 'health score · self-run · 자동 복구 · focused self-healing',
            accent: 'emerald',
            onClick: () => setHealthOverviewOpen(true),
        },
        {
            id: 'ad-orders',
            label: '🎬 광고 영상 주문 모니터링',
            summary: '재시도 · 다운로드 · 정산 · 리뷰 상태',
            accent: 'amber',
            onClick: () => setAdOrdersPanelOpen(true),
        },
        {
            id: 'manual-orchestrator',
            label: '🧠 공용 단계 카드 오케스트레이터',
            summary: '관리자/고객 공통 StageCardPanel · 단계별 수동 점검 · 구조 설계',
            accent: 'emerald',
            onClick: () => setCustomerOrchestratorPanelOpen(true),
        },
        {
            id: 'worldlinco-tuning',
            label: '🌐 WorldLinco 튜닝',
            summary: 'VoIP·대면 통역 VAD/TTS 타이밍 원격 조절',
            accent: 'cyan',
            onClick: () => setWorldlincoTuningPanelOpen(true),
        },
        {
            id: 'worldlinco-billing-policy',
            label: '💳 WorldLinco 요금 정책',
            summary: '베타 무료 ↔ 유료 · 요금 중지/재개',
            accent: 'cyan',
            onClick: () => setWorldlincoBillingPolicyPanelOpen(true),
        },
        {
            id: 'worldlinco-referral',
            label: '🎁 WorldLinco 추천인 QR',
            summary: 'WL 코드 · 가입 attribution · 3% 할인',
            accent: 'cyan',
            onClick: () => setWorldlincoReferralPanelOpen(true),
        },
        {
            id: 'worldlinco-sales-commission',
            label: '💼 WorldLinco 영업 정산',
            summary: 'WS QR · 수수료 · 현지 매출 전액 · KR 폴백',
            accent: 'cyan',
            onClick: () => setWorldlincoSalesCommissionPanelOpen(true),
        },
        {
            id: 'worldlinco-regional',
            label: '🗺️ WorldLinco 지역 관리',
            summary: '지역 관리자 · 귀속 유저 · KPI',
            accent: 'cyan',
            onClick: () => setWorldlincoRegionalPanelOpen(true),
        },
        {
            id: 'worldlinco-tourism-promo',
            label: '🌏 WorldLinco 관광 홍보',
            summary: 'GPS 국가별 홈 카드 · spot 홍보',
            accent: 'cyan',
            onClick: () => setWorldlincoTourismPromoPanelOpen(true),
        },
        {
            id: 'worldlinco-bulk-chat',
            label: '📣 WorldLinco 일괄 안내',
            summary: '앱 채팅 · 국가·언어별 번역 푸시',
            accent: 'cyan',
            onClick: () => setWorldlincoBulkChatPanelOpen(true),
        },
        {
            id: 'travel-partner-integration',
            label: '🧳 Travel Partner Integration Hub',
            summary: '호텔/이동/투어 API 연결 · 라우팅 정책 · 수익 퍼널',
            accent: 'emerald',
            onClick: () => setTravelPartnerIntegrationOpen(true),
        },
        {
            id: 'music-panel',
            label: '🎵 음악 생성·작사·협업 패널',
            summary: '감정 기반 작곡 · 코드 기반 작곡 · 협업 데모 연결',
            accent: 'amber',
            onClick: () => setMusicPanelOpen(true),
        },
        {
            id: 'live-logs',
            label: '📡 운영 라이브 로그',
            summary: '최근 30건 이벤트 · connection_id · panel_id · action',
            accent: 'blue',
            onClick: () => setLiveLogsPanelOpen(true),
        },
        {
            id: 'top-projects',
            label: '🏆 상위 프로젝트',
            summary: '다운로드 기준 순위 · 가격 · 평점 반응 지표',
            accent: 'amber',
            onClick: () => setTopProjectsPanelOpen(true),
        },
        {
            id: 'sample',
            label: '🎯 원터치 샘플 생성',
            summary: '일괄 생성 · 중복 정리 · 단건 생성',
            accent: 'violet',
            onClick: () => setSamplePanelOpen(true),
        },
        {
            id: 'cost',
            label: '💸 비용 시뮬레이터',
            summary: '월 주문 · 컷 단가 · 권장 아키텍처 계산',
            accent: 'emerald',
            onClick: () => setCostSimulatorPanelOpen(true),
        },
        {
            id: 'quick-links',
            label: '⚡ 빠른 이동',
            summary: '문서 · Swagger · 마켓 · 고객 오케스트레이터',
            accent: 'slate',
            onClick: () => setQuickLinksPanelOpen(true),
        },
    ] as const;

    const openAdminSectionFromRail = useCallback((toggleTestId: string, openSection: () => void) => {
        openSection();
        if (typeof window === 'undefined') {
            return;
        }
        window.requestAnimationFrame(() => {
            window.setTimeout(() => {
                scrollElementIntoViewIfNeeded(`[data-testid="${toggleTestId}"]`);
            }, 80);
        });
    }, [scrollElementIntoViewIfNeeded]);

    const opsExtensionRailColumn = [
        {
            id: 'ops-health',
            label: '🧠 통합 건강상태 허브',
            accent: 'emerald',
            onClick: () => openAdminSectionFromRail('admin-health-overview-section', () => setHealthOverviewOpen(true)),
        },
        {
            id: 'ops-recovery',
            label: '🛠️ 복구 센터',
            accent: 'amber',
            onClick: () => router.push('/admin/recovery'),
        },
        {
            id: 'ops-logs',
            label: '📡 운영 추적 로그',
            accent: 'blue',
            onClick: () => openAdminSectionFromRail('admin-live-logs-section', () => setLiveLogsPanelOpen(true)),
        },
        {
            id: 'ops-extras-health',
            label: '🧪 Extras Health 프리뷰',
            accent: 'cyan',
            onClick: () => openAdminSectionFromRail('admin-extras-preview-section', () => {
                void runExtrasPreviewRequest('health', true);
            }),
        },
        {
            id: 'ops-extras-catalog',
            label: '🧬 Extras Catalog 프리뷰',
            accent: 'violet',
            onClick: () => openAdminSectionFromRail('admin-extras-preview-section', () => {
                void runExtrasPreviewRequest('catalog', true);
            }),
        },
        {
            id: 'ops-system-settings',
            label: '🧭 운영 설정 패널',
            accent: 'slate',
            onClick: () => setSystemSettingsPanelOpen(true),
        },
        {
            id: 'ops-flow-adm-dash',
            label: '✅ FLOW-ADM-DASH 회귀 실행',
            accent: 'emerald',
            onClick: () => {
                void runFlowAdmDashRailCommand('FLOW-ADM-DASH 회귀 전체 실행');
            },
        },
    ] as const;

    const [opsGateBadgeState, setOpsGateBadgeState] = React.useState<{
        gate4Passed: boolean;
        gate5Passed: boolean;
        checkedAt: string | null;
        loading: boolean;
        error: string | null;
    }>({
        gate4Passed: false,
        gate5Passed: false,
        checkedAt: null,
        loading: true,
        error: null,
    });

    const [controlTowerBadgeState, setControlTowerBadgeState] = React.useState<{
        overall: string;
        recommendedDomain: string;
        decideIotDomain: string;
        decideGameDomain: string;
        decideUnknownFallback: boolean;
        checkedAt: string | null;
        loading: boolean;
        error: string | null;
    }>({
        overall: 'unknown',
        recommendedDomain: '-',
        decideIotDomain: '-',
        decideGameDomain: '-',
        decideUnknownFallback: false,
        checkedAt: null,
        loading: true,
        error: null,
    });

    const loadOpsGateBadgeState = useCallback(async () => {
        const token = getAdminToken();
        if (!token) {
            setOpsGateBadgeState((prev) => ({
                ...prev,
                loading: false,
                error: '관리자 토큰 없음',
            }));
            setControlTowerBadgeState((prev) => ({
                ...prev,
                loading: false,
                error: '관리자 토큰 없음',
            }));
            return;
        }

        try {
            const headers = {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
            };

            const apiBaseCandidates: string[] = [];
            const pushApiBaseCandidate = (value?: string | null) => {
                const normalized = String(value || '').trim().replace(/\/$/, '');
                if (!normalized || apiBaseCandidates.includes(normalized)) {
                    return;
                }
                apiBaseCandidates.push(normalized);
            };

            const isDirectLocalBackendUrl = (value?: string | null) => {
                const normalized = String(value || '').trim().toLowerCase();
                return normalized.startsWith('http://localhost:8000') || normalized.startsWith('http://127.0.0.1:8000');
            };

            pushApiBaseCandidate(apiBaseUrl);

            if (typeof window !== 'undefined') {
                pushApiBaseCandidate(window.location.origin);
                const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;
                if (!isDirectLocalBackendUrl(configuredApiUrl)) {
                    pushApiBaseCandidate(configuredApiUrl);
                }
            } else {
                pushApiBaseCandidate(process.env.NEXT_PUBLIC_API_URL);
            }

            const fetchWithApiBaseFallback = async (path: string, init?: RequestInit) => {
                let lastError: unknown = null;
                for (const base of apiBaseCandidates) {
                    const url = `${base}${path}`;
                    try {
                        return await fetch(url, init);
                    } catch (error) {
                        lastError = error;
                    }
                }
                throw lastError instanceof Error ? lastError : new Error('API 호출 실패');
            };

            const gate4Paths = [
                '/api/marketplace/interpreter/health',
                '/api/marketplace/music/health',
                '/api/marketplace/extras/health',
                '/api/marketplace/extras/iot/health',
                '/api/marketplace/extras/game/health',
            ];

            const gate4Results = await Promise.allSettled(
                gate4Paths.map(async (path) => {
                    const response = await fetchWithApiBaseFallback(path, { headers, cache: 'no-store' });
                    if (!response.ok) {
                        return false;
                    }
                    const payload = await response.json().catch(() => null) as { status?: string } | null;
                    return payload?.status === 'ok';
                })
            );

            const gate4Passed = gate4Results.every((result) => result.status === 'fulfilled' && result.value === true);

            const extrasHealthResponse = await fetchWithApiBaseFallback('/api/marketplace/extras/health', { headers, cache: 'no-store' });
            const extrasHealthPayload = await extrasHealthResponse.json().catch(() => null) as {
                circuit_breakers?: {
                    iot?: { state?: string; failures?: number; threshold?: number };
                    game?: { state?: string; failures?: number; threshold?: number };
                };
            } | null;

            const cb = extrasHealthPayload?.circuit_breakers;
            const gate5Passed = Boolean(
                extrasHealthResponse.ok
                && cb
                && cb.iot?.state === 'CLOSED'
                && cb.game?.state === 'CLOSED'
                && Number(cb.iot?.failures ?? 1) === 0
                && Number(cb.game?.failures ?? 1) === 0
                && Number(cb.iot?.threshold ?? 0) === 3
                && Number(cb.game?.threshold ?? 0) === 3
            );

            setOpsGateBadgeState({
                gate4Passed,
                gate5Passed,
                checkedAt: new Date().toISOString(),
                loading: false,
                error: null,
            });

            const [controlTowerStateResponse, decideIotResponse, decideGameResponse, decideUnknownResponse] = await Promise.all([
                fetchWithApiBaseFallback('/api/marketplace/extras/control-tower/state', {
                    headers,
                    cache: 'no-store',
                }),
                fetchWithApiBaseFallback('/api/marketplace/extras/control-tower/decide', {
                    method: 'POST',
                    headers,
                    cache: 'no-store',
                    body: JSON.stringify({ intent: 'iot device light on', action: 'on' }),
                }),
                fetchWithApiBaseFallback('/api/marketplace/extras/control-tower/decide', {
                    method: 'POST',
                    headers,
                    cache: 'no-store',
                    body: JSON.stringify({ intent: 'game economy simulation', action: 'simulate' }),
                }),
                fetchWithApiBaseFallback('/api/marketplace/extras/control-tower/decide', {
                    method: 'POST',
                    headers,
                    cache: 'no-store',
                    body: JSON.stringify({ intent: 'draft ad copy', action: 'generate' }),
                }),
            ]);

            const controlTowerStatePayload = await controlTowerStateResponse.json().catch(() => null) as {
                control_tower?: { status?: string; recommended_domain?: string };
            } | null;
            const decideIotPayload = await decideIotResponse.json().catch(() => null) as {
                decision?: { selected_domain?: string };
            } | null;
            const decideGamePayload = await decideGameResponse.json().catch(() => null) as {
                decision?: { selected_domain?: string };
            } | null;
            const decideUnknownPayload = await decideUnknownResponse.json().catch(() => null) as {
                decision?: { fallback_applied?: boolean };
            } | null;

            setControlTowerBadgeState({
                overall: String(controlTowerStatePayload?.control_tower?.status ?? 'unknown'),
                recommendedDomain: String(controlTowerStatePayload?.control_tower?.recommended_domain ?? '-'),
                decideIotDomain: String(decideIotPayload?.decision?.selected_domain ?? '-'),
                decideGameDomain: String(decideGamePayload?.decision?.selected_domain ?? '-'),
                decideUnknownFallback: Boolean(decideUnknownPayload?.decision?.fallback_applied),
                checkedAt: new Date().toISOString(),
                loading: false,
                error: (
                    !controlTowerStateResponse.ok
                    || !decideIotResponse.ok
                    || !decideGameResponse.ok
                    || !decideUnknownResponse.ok
                )
                    ? '관제탑 상태 일부 실패'
                    : null,
            });
        } catch (error: any) {
            setOpsGateBadgeState((prev) => ({
                ...prev,
                loading: false,
                error: error?.message || '게이트 상태 조회 실패',
            }));
            setControlTowerBadgeState((prev) => ({
                ...prev,
                loading: false,
                error: error?.message || '관제탑 상태 조회 실패',
            }));
        }
    }, [apiBaseUrl]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }

        void loadOpsGateBadgeState();
        const intervalId = window.setInterval(() => {
            void loadOpsGateBadgeState();
        }, 15000);

        return () => {
            window.clearInterval(intervalId);
        };
    }, [authChecked, loadOpsGateBadgeState]);

    const [opsGateNow, setOpsGateNow] = React.useState(() => Date.now());
    useEffect(() => {
        const tickId = window.setInterval(() => {
            setOpsGateNow(Date.now());
        }, 5000);
        return () => {
            window.clearInterval(tickId);
        };
    }, []);

    const opsGateRailFooter = useMemo(() => {
        const allPass = opsGateBadgeState.gate4Passed && opsGateBadgeState.gate5Passed;
        const anyFail = !opsGateBadgeState.gate4Passed || !opsGateBadgeState.gate5Passed;
        const bothFail = !opsGateBadgeState.gate4Passed && !opsGateBadgeState.gate5Passed;

        const gate4Label = opsGateBadgeState.gate4Passed ? '✓ G4' : '✗ G4';
        const gate5Label = opsGateBadgeState.gate5Passed ? '✓ G5' : '✗ G5';

        let elapsedLabel = '-';
        if (opsGateBadgeState.checkedAt) {
            const diffSec = Math.floor((opsGateNow - new Date(opsGateBadgeState.checkedAt).getTime()) / 1000);
            if (diffSec < 60) {
                elapsedLabel = `${diffSec}초 전`;
            } else if (diffSec < 3600) {
                elapsedLabel = `${Math.floor(diffSec / 60)}분 전`;
            } else {
                elapsedLabel = `${Math.floor(diffSec / 3600)}시간 전`;
            }
        }

        if (opsGateBadgeState.loading && !opsGateBadgeState.checkedAt) {
            return (
                <div data-testid="admin-ops-gate-badge" className="flex flex-col items-end gap-0.5">
                    <span className="text-[10px] font-semibold text-slate-300 animate-pulse">G4/G5 확인 중...</span>
                </div>
            );
        }

        const statusTone = opsGateBadgeState.error
            ? 'text-amber-400'
            : bothFail
                ? 'text-red-400'
                : anyFail
                    ? 'text-amber-300'
                    : 'text-emerald-300';

        const borderColor = opsGateBadgeState.error
            ? 'border-amber-500/30'
            : bothFail
                ? 'border-red-500/30'
                : anyFail
                    ? 'border-amber-500/30'
                    : 'border-emerald-500/30';

        const dotColor = opsGateBadgeState.loading
            ? 'bg-slate-400 animate-pulse'
            : allPass
                ? 'bg-emerald-400'
                : anyFail
                    ? 'bg-amber-400'
                    : 'bg-red-400';

        return (
            <div
                data-testid="admin-ops-gate-badge"
                className={`flex flex-col gap-0.5 rounded px-1.5 py-1 border ${borderColor} bg-white/[0.03]`}
            >
                <div className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`} aria-hidden="true" />
                    <span className={`text-[10px] font-bold leading-none tracking-wide ${statusTone}`}>
                        {gate4Label} · {gate5Label}
                    </span>
                </div>
                <div className="flex items-center justify-between gap-1.5 pl-2.5">
                    <span className="text-[9px] text-slate-400 leading-none">
                        {opsGateBadgeState.error ? `오류: ${opsGateBadgeState.error.slice(0, 18)}` : (allPass ? '전체 정상' : '일부 실패')}
                    </span>
                    <span className="text-[9px] text-slate-500 leading-none tabular-nums">{elapsedLabel}</span>
                </div>
                <div className="mt-1 border-t border-white/10 pt-1 pl-2.5 text-[9px] leading-tight text-slate-300">
                    <div className="font-semibold text-slate-200">
                        CT {controlTowerBadgeState.overall.toUpperCase()} · REC {controlTowerBadgeState.recommendedDomain}
                    </div>
                    <div className="text-slate-400">
                        IOT {controlTowerBadgeState.decideIotDomain} · GAME {controlTowerBadgeState.decideGameDomain}
                    </div>
                    <div className="text-slate-500">
                        UNKNOWN fallback {controlTowerBadgeState.decideUnknownFallback ? 'ON' : 'OFF'}
                        {controlTowerBadgeState.error ? ` · 오류: ${controlTowerBadgeState.error.slice(0, 12)}` : ''}
                    </div>
                </div>
            </div>
        );
    }, [opsGateBadgeState, opsGateNow, controlTowerBadgeState]);

    if (!authChecked) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#0d1117] text-[#c9d1d9]">
                <div className="text-center">
                    <div className="text-3xl mb-4">🔐</div>
                    <p className="text-gray-500">{authStatusMessage}</p>
                </div>
            </div>
        );
    }

    const adminSidebar = (
        <div className="workspace-section-stack">
            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">Operator</p>
                <h3 className="workspace-card-title">운영자 세션</h3>
                <p className="workspace-card-copy">
                    {adminUser ? `${adminUser.username} (${adminUser.email})` : '운영자 인증 상태를 확인 중입니다.'}
                </p>
                <div className="workspace-chip-row">
                    <span className="workspace-chip workspace-chip-active">관리자</span>
                    <span className="workspace-chip">Round 7 synced</span>
                </div>
            </div>
            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">핵심 지표</p>
                <div className="workspace-list">
                    {dashboardSummaryCards.map((card) => (
                        <div key={card.id} className="workspace-list-item">
                            <div>
                                <strong>{card.label}</strong>
                                <span>{card.note}</span>
                            </div>
                            <strong>{card.value}</strong>
                        </div>
                    ))}
                </div>
            </div>
            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">바로 이동</p>
                <div className="workspace-list">
                    <div className="workspace-list-item"><strong>🧩 ADMIN CONTROL HUB</strong><span>운영자 명령 허브 / 설정 새로고침 / 전역 자동 전환</span></div>
                    <div className="workspace-list-item"><strong>🧭 전역 .env 설정 패널</strong><span>.env / runtime / LLM 제어</span></div>
                    <div className="workspace-list-item"><strong>관리자 수동 오케스트레이션</strong><span>장기 분석 / 구조 설계 / 공용 오케스트레이터</span></div>
                    <div className="workspace-list-item"><strong>🕸️ self auto-connect graph</strong><span>connection_id 흐름 추적</span></div>
                </div>
            </div>
        </div>
    );

    const boardSections = buildAdminDashboardSectionsConfig({
        adminControlHubOpen,
        setAdminControlHubOpen,
        systemSettings,
        dashboardAnalysis,
        setSystemSettingsPanelOpen,
        loadSystemSettings,
        applyGlobalAutomaticMode,
        healthOverviewOpen,
        setHealthOverviewOpen,
        adminDashboardOverviewAssembly,
        autoConnectGraphPanelOpen,
        setAutoConnectGraphPanelOpen,
        adminAutoConnectGraphAssembly,
        customerOrchestratorPanelOpen,
        setCustomerOrchestratorPanelOpen,
        adminManualOrchestratorAssembly,
        adOrdersPanelOpen,
        setAdOrdersPanelOpen,
        adminAdOrdersAssembly,
        categoryPanelOpen,
        setCategoryPanelOpen,
        visibleCategories,
        sortedVisibleCategories,
        categoryStats,
        categoryRecentProjects,
        categoryMessage,
        categoryUpdatingId,
        categoryDeletingId,
        loadCategories,
        updateCategory,
        cancelEditCategory,
        beginEditCategory,
        deleteCategory,
        categoryName,
        categoryDescription,
        categoryCreating,
        hideEmptyCategories,
        categorySortBy,
        setCategoryName,
        setCategoryDescription,
        createCategory,
        setHideEmptyCategories,
        setCategorySortBy,
        editingCategoryId,
        editingCategoryName,
        editingCategoryDescription,
        setEditingCategoryName,
        setEditingCategoryDescription,
        subscriptionMonitorPanelOpen,
        setSubscriptionMonitorPanelOpen,
        apiBaseUrl,
        costSimulatorPanelOpen,
        setCostSimulatorPanelOpen,
        costSimulatorForm,
        costSimulatorLoading,
        costSimulatorError,
        costSimulatorResult,
        updateCostSimulatorField,
        runCostSimulation,
        quickLinksPanelOpen,
        setQuickLinksPanelOpen,
        llmControlPanelOpen,
        setLlmControlPanelOpen,
        llmPanelHeight,
        samplePanelOpen,
        setSamplePanelOpen,
        adminSampleProductsAssembly,
        liveLogsPanelOpen,
        setLiveLogsPanelOpen,
        liveLogs,
        topProjectsPanelOpen,
        setTopProjectsPanelOpen,
        filteredTopProjects,
        formatCurrency,
    });

    return (
        <div className="admin-dark">
            <WorkspaceChrome
                brand="Workspace 4.0"
                statusLabel={refreshing ? '실시간 갱신 중' : '운영 연결 유지'}
                pageTestId="admin-workspace-page"
                compactHeader
                hideHero
                railItems={[
                    {
                        id: 'home', label: '대시보드', shortLabel: '대시', href: '/admin', active: true, accent: 'blue',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🏠</div>
                    },
                    {
                        id: 'market', label: '마켓', shortLabel: '마켓', href: marketplaceHomeHref, accent: 'emerald',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🛒</div>
                    },
                    {
                        id: 'users', label: '가입 사용자', shortLabel: '회원', href: '/admin/users', accent: 'cyan', testId: 'admin-rail-users',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">👥</div>
                    },
                    {
                        id: 'llm', label: 'LLM', shortLabel: 'LLM', href: '/admin/llm', accent: 'violet',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🤖</div>
                    },
                    {
                        id: 'docs', label: '문서', shortLabel: '문서', href: adminPassKmcKcbDocsHref, accent: 'amber',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">📘</div>
                    },
                    {
                        id: 'tourism-review', label: '관광 검수', shortLabel: '검수', href: '/admin/tourism-review', accent: 'emerald', testId: 'admin-rail-tourism-review',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🧭</div>
                    },
                    {
                        id: 'carbon', label: '탄소 측정', shortLabel: '탄소', href: '/admin/carbon', accent: 'emerald', testId: 'admin-rail-carbon',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🌱</div>
                    },
                    ...buildAdminLauncherRailItems(launcherLeftColumn, ADMIN_LEFT_SHORT_LABEL_OVERRIDES),
                ]}
                rightRailItems={[
                    {
                        id: 'grafana',
                        label: 'Grafana 모니터링',
                        shortLabel: '모니터링',
                        accent: 'cyan',
                        onClick: () => setGrafanaOpen(!grafanaOpen),
                        active: grafanaOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">📊</div>
                    },
                    {
                        id: 'prometheus',
                        label: 'Prometheus 데이터',
                        shortLabel: '데이터',
                        accent: 'blue',
                        onClick: () => setPrometheusOpen(!prometheusOpen),
                        active: prometheusOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">📈</div>
                    },
                    {
                        id: 'p50p95',
                        label: 'p50/p95 차트',
                        shortLabel: '응답시간',
                        accent: 'emerald',
                        onClick: () => setP50p95Open(!p50p95Open),
                        active: p50p95Open,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">📉</div>
                    },
                    {
                        id: 'performance',
                        label: '성능 최적화',
                        shortLabel: '성능',
                        accent: 'amber',
                        onClick: () => setPerformanceOpen(!performanceOpen),
                        active: performanceOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">⚡</div>
                    },
                    {
                        id: 'llmPath',
                        label: 'LLM path 개선',
                        shortLabel: 'LLM',
                        accent: 'violet',
                        onClick: () => setLlmPathOpen(!llmPathOpen),
                        active: llmPathOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🚀</div>
                    },
                    {
                        id: 'fastPath',
                        label: 'Fast path 커버리지',
                        shortLabel: '커버',
                        accent: 'cyan',
                        onClick: () => setFastPathOpen(!fastPathOpen),
                        active: fastPathOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🎯</div>
                    },
                    {
                        id: 'ops',
                        label: '운영 준비',
                        shortLabel: '운영',
                        accent: 'slate',
                        onClick: () => setOpsOpen(!opsOpen),
                        active: opsOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🛠️</div>
                    },
                    {
                        id: 'alertManager',
                        label: 'AlertManager 설정',
                        shortLabel: '알람',
                        accent: 'amber',
                        onClick: () => {
                            setAlertManagerOpen(true);
                            if (typeof window !== 'undefined') {
                                window.requestAnimationFrame(() => {
                                    window.setTimeout(() => {
                                        scrollElementIntoViewIfNeeded('[data-testid="admin-alertmanager-section"]');
                                    }, 80);
                                });
                            }
                        },
                        active: alertManagerOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">🚨</div>
                    },
                    {
                        id: 'sla',
                        label: 'SLA 정의',
                        shortLabel: 'SLA',
                        accent: 'emerald',
                        onClick: () => {
                            setSlaOpen(true);
                            if (typeof window !== 'undefined') {
                                window.requestAnimationFrame(() => {
                                    window.setTimeout(() => {
                                        scrollElementIntoViewIfNeeded('[data-testid="admin-sla-section"]');
                                    }, 80);
                                });
                            }
                        },
                        active: slaOpen,
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">📋</div>
                    },
                    {
                        id: 'subscription-monitor',
                        label: '구독 결제 모니터링',
                        shortLabel: '구독',
                        href: '/admin/subscription-monitor?period_days=7&status=all',
                        accent: 'violet',
                        icon: <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm">💳</div>
                    },
                    ...buildAdminLauncherRailItems(launcherRightColumn, ADMIN_RIGHT_SHORT_LABEL_OVERRIDES),
                    ...buildAdminLauncherRailItems(opsExtensionRailColumn, ADMIN_RIGHT_SHORT_LABEL_OVERRIDES),
                ]}
                rightRailFooter={opsGateRailFooter}
                rightRailOpen={rightRailOpen}
                onRightRailToggle={setRightRailOpen}
                leftRailOpen={leftRailOpen}
                onLeftRailToggle={setLeftRailOpen}
                topActions={(
                    <>
                        <Link href="/admin/tourism-review" data-testid="admin-topnav-tourism-review" aria-label="관광 데이터 사람검수 콘솔 열기" className="workspace-topbar-chip">
                            관광 검수
                        </Link>
                        <Link href="/admin/carbon" data-testid="admin-topnav-carbon" aria-label="추론 탄소 전력 측정 열기" className="workspace-topbar-chip">
                            탄소 측정
                        </Link>
                        <Link href="/admin/users" data-testid="admin-topnav-users" aria-label="회원가입 사용자 확인" className="workspace-topbar-chip">
                            가입 사용자
                        </Link>
                        <Link href={adminPassKmcKcbDocsHref} data-testid="admin-topnav-pass-kmc-kcb" aria-label="PASS KMC KCB 계약 문서 열기" className="workspace-topbar-chip">
                            PASS 문서
                        </Link>
                        <Link href={adminCommercialTermsDocsHref} data-testid="admin-topnav-commercial-terms" aria-label="상용화 계약 약관 기준 열기" className="workspace-topbar-chip">
                            계약 기준
                        </Link>
                        <Link href={adminCommercialValuesInputHref} data-testid="admin-topnav-commercial-values-input" aria-label="PASS KMC KCB 상용값 입력 체크리스트 열기" className="workspace-topbar-chip">
                            상용값 입력
                        </Link>
                        <a href={adminApiDocsHref} target="_blank" rel="noreferrer" data-testid="admin-topnav-api-docs" aria-label="API 문서 열기" className="workspace-topbar-chip">
                            API Docs
                        </a>
                        <div
                            data-testid="admin-topnav-api-connection"
                            aria-label="API 연결 상태"
                            className="workspace-topbar-chip"
                            title={isHealthOk ? '백엔드 API 연결 정상' : '백엔드 API 연결 점검 필요'}
                        >
                            <span className={isHealthOk ? 'text-emerald-300' : 'text-rose-300'}>{isHealthOk ? '●' : '○'}</span>
                            <span className="font-semibold">{isHealthOk ? 'API 연결됨' : 'API 미연결'}</span>
                        </div>
                        <div data-testid="admin-topnav-user-panel" className="workspace-topbar-chip" aria-label="로그인 사용자 정보">
                            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] opacity-70">Admin</span>
                            <span className="max-w-[130px] truncate font-semibold">{adminUser?.username || '확인 중'}</span>
                        </div>
                        <button
                            type="button"
                            onClick={() => loadDashboard(true)}
                            data-testid="admin-topnav-refresh"
                            aria-label="관리자 대시보드 새로고침"
                            className="workspace-topbar-chip"
                            disabled={refreshing}
                        >
                            {refreshing ? '⏳' : '🔄'}
                        </button>
                        <button type="button" onClick={handleLogout} data-testid="admin-topnav-logout" aria-label="로그아웃" className="workspace-ghost-button">
                            🚪
                        </button>
                    </>
                )}
            >
                <div style={{ maxWidth: '800px', margin: '0 auto', minHeight: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                        <h2 style={{ fontSize: '28px', fontWeight: 600, color: 'white', marginBottom: '8px' }}>GenSpark 스타일 AI 워크스페이스 4.0</h2>
                        <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '15px' }}>무엇이든 물어보고 만들어보세요 (관리자 전용)</p>
                    </div>
                    {sorisaeFailureStatus && (
                        <section
                            data-testid="admin-sorisae-failure-widget"
                            className="mb-6 rounded-xl border border-white/15 bg-black/35 px-4 py-4 text-white"
                        >
                            <div className="flex flex-wrap items-center gap-2">
                                <h3 className="text-sm font-semibold">소리새 장애감지</h3>
                                <span className="rounded-full border border-white/20 px-2 py-0.5 text-[11px] font-semibold tracking-wide">
                                    {sorisaeFailureStatus.classification || 'unknown'}
                                </span>
                                {sorisaeFailureStatus.admin_push?.attempted && (
                                    <span className="rounded-full border border-white/20 px-2 py-0.5 text-[11px]">
                                        관리자 push 성공 {sorisaeFailureStatus.admin_push?.success_user_count ?? 0} / {sorisaeFailureStatus.admin_push?.admin_user_count ?? 0}
                                    </span>
                                )}
                            </div>
                            <p className="mt-2 text-xs text-white/80">
                                API 실패 {sorisaeFailureStatus.api_fail ?? 0}건 · UI 실패 {sorisaeFailureStatus.ui_fail ?? 0}건
                            </p>
                            {sorisaeFailureStatus.result_json_path && (
                                <button
                                    type="button"
                                    onClick={() => void openSorisaeResultJsonPanel()}
                                    className="mt-3 inline-flex rounded-lg border border-white/20 px-3 py-1 text-xs font-semibold hover:bg-white/10"
                                    data-testid="admin-sorisae-result-json-open"
                                >
                                    결과 JSON 열기
                                </button>
                            )}
                        </section>
                    )}
                    {sorisaeResultJsonPanelOpen && (
                        <section
                            data-testid="admin-sorisae-result-json-panel"
                            className="mb-6 rounded-xl border border-cyan-400/30 bg-[#061325] px-4 py-4 text-white"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <h3 className="text-sm font-semibold">소리새 smoke_result.json 패널</h3>
                                <button
                                    type="button"
                                    onClick={() => setSorisaeResultJsonPanelOpen(false)}
                                    className="rounded-lg border border-white/20 px-2 py-0.5 text-xs hover:bg-white/10"
                                >
                                    닫기
                                </button>
                            </div>
                            <p className="mt-2 text-xs text-white/75">
                                status {sorisaeResultJsonState.statusCode ?? '-'} · latency {sorisaeResultJsonState.durationMs ?? '-'}ms
                            </p>
                            {sorisaeResultJsonState.resultJsonPath && (
                                <p className="mt-1 text-[11px] text-cyan-200/90 break-all">{sorisaeResultJsonState.resultJsonPath}</p>
                            )}
                            {sorisaeResultJsonState.loading ? (
                                <p className="mt-3 text-xs text-white/80">결과 JSON 조회 중...</p>
                            ) : sorisaeResultJsonState.error ? (
                                <p className="mt-3 text-xs text-rose-300">{sorisaeResultJsonState.error}</p>
                            ) : null}
                            <pre
                                style={{
                                    marginTop: 10,
                                    marginBottom: 0,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    background: 'rgba(9,14,22,0.96)',
                                    border: '1px solid rgba(120, 185, 255, 0.25)',
                                    borderRadius: 10,
                                    padding: 12,
                                    maxHeight: 300,
                                    overflow: 'auto',
                                    color: 'var(--workspace-text)',
                                    fontSize: 12,
                                    lineHeight: 1.45,
                                }}
                            >
                                {sorisaeResultJsonState.payload == null
                                    ? '표시할 JSON이 없습니다.'
                                    : typeof sorisaeResultJsonState.payload === 'string'
                                        ? sorisaeResultJsonState.payload
                                        : JSON.stringify(sorisaeResultJsonState.payload, null, 2)}
                            </pre>
                        </section>
                    )}
                    <section
                        data-testid="admin-threshold-analysis-mode"
                        className="mb-6 rounded-xl border border-amber-400/30 bg-[#1a1307] px-4 py-4 text-white"
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="text-sm font-semibold">임계치 분석 모드</h3>
                            <span className={`rounded-full border px-2 py-0.5 text-[11px] ${thresholdAnalysis?.safe_gate.threshold_recovery_allowed ? 'border-emerald-300/60 text-emerald-300' : 'border-amber-300/60 text-amber-200'}`}>
                                {thresholdAnalysis?.safe_gate.threshold_recovery_allowed ? '승인값만 자동복구 사용 가능' : '승인 전 자동복구 차단'}
                            </span>
                        </div>
                        <p className="mt-2 text-xs text-white/75">
                            최근 관측값으로 권장 임계치를 계산합니다. 승인 전까지는 어떤 추천 임계치도 자동복구에 사용되지 않습니다.
                        </p>
                        <p className="mt-1 text-[11px] text-white/50">
                            {thresholdAnalysisLoading
                                ? '분석 상태 조회 중...'
                                : thresholdAnalysis?.last_analyzed_at
                                    ? `최근 분석: ${thresholdAnalysis.last_analyzed_at}`
                                    : '아직 분석 기록이 없습니다.'}
                        </p>
                        {thresholdAnalysisError && (
                            <p className="mt-2 text-xs text-rose-300">{thresholdAnalysisError}</p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2">
                            <button
                                type="button"
                                onClick={() => void runThresholdAnalysis()}
                                disabled={thresholdAnalysisRunning}
                                className="rounded-lg border border-amber-300/60 px-3 py-1.5 text-xs font-semibold text-amber-100 hover:bg-amber-500/20 disabled:opacity-60"
                            >
                                {thresholdAnalysisRunning ? '분석 중...' : '최근 관측값으로 권장 임계치 계산'}
                            </button>
                            <button
                                type="button"
                                onClick={() => void saveThresholdApproval('rails', !thresholdAnalysis?.approvals.rails.approved)}
                                disabled={thresholdApprovalSavingTarget === 'rails' || !thresholdAnalysis?.recommendations.observation_summary.observations_complete}
                                className="rounded-lg border border-emerald-300/60 px-3 py-1.5 text-xs font-semibold text-emerald-100 hover:bg-emerald-500/20 disabled:opacity-60"
                            >
                                {thresholdApprovalSavingTarget === 'rails'
                                    ? '저장 중...'
                                    : thresholdAnalysis?.approvals.rails.approved
                                        ? '임계치 승인 해제'
                                        : '권장 임계치 승인'}
                            </button>
                            <button
                                type="button"
                                onClick={() => void saveThresholdApproval('worldlinco', !thresholdAnalysis?.approvals.worldlinco.approved)}
                                disabled={thresholdApprovalSavingTarget === 'worldlinco' || !thresholdAnalysis?.recommendations.observation_summary.observations_complete}
                                className="rounded-lg border border-sky-300/60 px-3 py-1.5 text-xs font-semibold text-sky-100 hover:bg-sky-500/20 disabled:opacity-60"
                            >
                                {thresholdApprovalSavingTarget === 'worldlinco'
                                    ? '저장 중...'
                                    : thresholdAnalysis?.approvals.worldlinco.approved
                                        ? '월드린코 승인 해제'
                                        : '월드린코 추천 승인'}
                            </button>
                            <button
                                type="button"
                                onClick={() => void applyApprovedWorldlincoThresholdRecovery()}
                                disabled={worldlincoApprovedApplyRunning || !thresholdAnalysis?.safe_gate.worldlinco_auto_apply_allowed}
                                className="rounded-lg border border-violet-300/60 px-3 py-1.5 text-xs font-semibold text-violet-100 hover:bg-violet-500/20 disabled:opacity-60"
                            >
                                {worldlincoApprovedApplyRunning ? '적용 중...' : '승인된 월드린코 추천값 적용'}
                            </button>
                        </div>
                        {thresholdAnalysis && (
                            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                    <p className="text-[11px] text-white/55">관측 p50 / p95</p>
                                    <p className="mt-1 text-sm font-semibold text-white">
                                        {String(thresholdAnalysis.recommendations.observation_summary.metrics?.p50_latency_ms ?? '-')}ms / {String(thresholdAnalysis.recommendations.observation_summary.metrics?.p95_latency_ms ?? '-')}ms
                                    </p>
                                </div>
                                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                    <p className="text-[11px] text-white/55">권장 p50 / p95</p>
                                    <p className="mt-1 text-sm font-semibold text-white">
                                        {thresholdAnalysis.recommendations.rails.latency.p50_budget_ms}ms / {thresholdAnalysis.recommendations.rails.latency.p95_budget_ms}ms
                                    </p>
                                </div>
                                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                    <p className="text-[11px] text-white/55">권장 응답 / DB 예산</p>
                                    <p className="mt-1 text-sm font-semibold text-white">
                                        {thresholdAnalysis.recommendations.rails.performance.response_budget_ms}ms / {thresholdAnalysis.recommendations.rails.performance.db_query_budget_ms}ms
                                    </p>
                                </div>
                                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                    <p className="text-[11px] text-white/55">안전 게이트</p>
                                    <p className="mt-1 text-sm font-semibold text-white">
                                        {thresholdAnalysis.safe_gate.reason}
                                    </p>
                                </div>
                            </div>
                        )}
                        {thresholdAnalysis && (
                            <div className="mt-3 rounded-lg border border-white/10 bg-black/20 p-3 text-[11px] leading-relaxed text-white/75">
                                <div>월드린코 추천 그룹: {Object.keys(thresholdAnalysis.recommendations.worldlinco || {}).join(', ')}</div>
                                <div>관측 완료 여부: {thresholdAnalysis.recommendations.observation_summary.observations_complete ? '완료' : '불충분'}</div>
                                <div>현재 분류: {thresholdAnalysis.recommendations.observation_summary.sorisae_classification || 'unknown'}</div>
                            </div>
                        )}
                    </section>
                    <section
                        data-testid="admin-rail-action-center"
                        className="mb-6 rounded-xl border border-indigo-400/30 bg-[#0a1228] px-4 py-4 text-white"
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="text-sm font-semibold">레일 운영 액션 센터 (즉시조치/수정/확장)</h3>
                            <div className="flex items-center gap-2">
                                <span className="rounded-full border border-white/20 px-2 py-0.5 text-[11px] text-white/80">9개 레일 실조치 활성화</span>
                                <button
                                    type="button"
                                    onClick={() => setRailActionCenterOpen((prev) => !prev)}
                                    className="rounded-full border border-indigo-300/50 px-2.5 py-1 text-[11px] text-indigo-100 hover:bg-indigo-500/20"
                                    data-testid="admin-rail-action-center-toggle-top"
                                >
                                    {railActionCenterOpen ? '위에서 접기 ▲' : '위에서 열기 ▼'}
                                </button>
                            </div>
                        </div>
                        <p className="mt-2 text-xs text-white/70">
                            각 레일에서 패널 열기, 즉시조치 실행, 운영 파라미터 저장, 운영 메모 기록이 가능합니다.
                        </p>
                        <div className="mt-3 rounded-lg border border-emerald-300/25 bg-emerald-950/20 p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-xs font-semibold text-emerald-200">FLOW-ADM-DASH 웹 실행 버튼</p>
                                <span className="rounded-full border border-emerald-300/35 px-2 py-0.5 text-[10px] text-emerald-200">
                                    레일 내 실버튼
                                </span>
                            </div>
                            <p className="mt-1 text-[11px] text-emerald-100/80">
                                브라우저에서 대시보드 새로고침과 전역 설정 재조회를 순서대로 수행합니다.
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                                {FLOW_ADM_DASH_COMMAND_ITEMS.map((command) => {
                                    const isBusy = flowAdmDashCommandBusyId === command.label;
                                    return (
                                        <button
                                            key={command.id}
                                            type="button"
                                            onClick={() => {
                                                void runFlowAdmDashRailCommand(command.label);
                                            }}
                                            disabled={Boolean(flowAdmDashCommandBusyId)}
                                            data-testid={`admin-flow-adm-dash-command-${command.id}`}
                                            className="rounded-md border border-emerald-300/40 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-100 hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {isBusy ? '실행 중...' : command.label}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                        <p className="mt-1 text-[11px] text-white/50">
                            {railSettingsLoading
                                ? '레일 설정 불러오는 중...'
                                : railSettingsUpdatedAt
                                    ? `마지막 저장: ${railSettingsUpdatedAt}`
                                    : '아직 저장된 레일 설정 파일이 없어 기본값으로 동작합니다.'}
                        </p>
                        {railActionMessage && (
                            <p className="mt-2 text-xs text-emerald-300">{railActionMessage}</p>
                        )}
                        {railActionError && (
                            <p className="mt-2 text-xs text-rose-300">{railActionError}</p>
                        )}
                        {railSettingsError && (
                            <p className="mt-2 text-xs text-rose-300">{railSettingsError}</p>
                        )}
                        {railActionCenterOpen && (
                            <>
                                <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                                    {ADMIN_RAIL_ACTION_ITEMS.map((item) => {
                                        const isBusy = railActionBusyId === item.id;
                                        const isOpen = railPanelOpenState[item.id];
                                        const isSaving = railSettingsSavingId === item.id;
                                        const isDirty = railDirtyState[item.id];
                                        const settingFields = ADMIN_RAIL_SETTING_FIELDS[item.id];
                                        const draftSettings = (railSettingsDraft[item.id] as unknown) as Record<string, string | number | boolean>;
                                        return (
                                            <article
                                                key={item.id}
                                                className="rounded-lg border border-white/15 bg-white/[0.03] p-3"
                                                data-testid={`admin-rail-action-${item.id}`}
                                            >
                                                <div className="flex items-start justify-between gap-2">
                                                    <div>
                                                        <p className="text-sm font-semibold">{item.label}</p>
                                                        <p className="mt-1 text-[11px] text-white/70">{item.description}</p>
                                                    </div>
                                                    <span className={`rounded-full border px-2 py-0.5 text-[10px] ${isOpen ? 'border-emerald-300/60 text-emerald-300' : 'border-white/20 text-white/60'}`}>
                                                        {isOpen ? 'OPEN' : 'CLOSED'}
                                                    </span>
                                                </div>
                                                <div className="mt-3 grid gap-2">
                                                    {settingFields.map((field) => {
                                                        const fieldId = `admin-rail-setting-${item.id}-${field.key}`;
                                                        const value = draftSettings[field.key];
                                                        return (
                                                            <label key={field.key} htmlFor={fieldId} className="rounded-md border border-white/10 bg-black/20 px-2.5 py-2 text-[11px] text-white/80">
                                                                <span className="block font-semibold text-white">{field.label}</span>
                                                                <span className="mt-0.5 block text-[10px] text-white/55">{field.help}</span>
                                                                {field.input === 'boolean' ? (
                                                                    <input
                                                                        id={fieldId}
                                                                        type="checkbox"
                                                                        checked={Boolean(value)}
                                                                        onChange={(event) => updateRailSettingDraft(item.id, field.key, event.target.checked)}
                                                                        className="mt-2 h-4 w-4"
                                                                    />
                                                                ) : field.input === 'select' ? (
                                                                    <select
                                                                        id={fieldId}
                                                                        value={String(value ?? '')}
                                                                        onChange={(event) => updateRailSettingDraft(item.id, field.key, event.target.value)}
                                                                        className="mt-2 w-full rounded-md border border-white/15 bg-[#050b16] px-2 py-1.5 text-[11px] text-white"
                                                                    >
                                                                        {(field.options || []).map((option) => (
                                                                            <option key={option.value} value={option.value}>{option.label}</option>
                                                                        ))}
                                                                    </select>
                                                                ) : (
                                                                    <input
                                                                        id={fieldId}
                                                                        type={field.input === 'number' ? 'number' : 'text'}
                                                                        value={field.input === 'number' ? Number(value ?? 0) : String(value ?? '')}
                                                                        min={field.min}
                                                                        max={field.max}
                                                                        step={field.step}
                                                                        onChange={(event) => updateRailSettingDraft(
                                                                            item.id,
                                                                            field.key,
                                                                            field.input === 'number' ? Number(event.target.value || 0) : event.target.value,
                                                                        )}
                                                                        className="mt-2 w-full rounded-md border border-white/15 bg-[#050b16] px-2 py-1.5 text-[11px] text-white"
                                                                    />
                                                                )}
                                                            </label>
                                                        );
                                                    })}
                                                </div>
                                                <div className="mt-3 flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => openRailPanel(item.id)}
                                                        className="rounded-lg border border-white/25 px-2.5 py-1 text-[11px] font-semibold hover:bg-white/10"
                                                    >
                                                        패널 열기
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => void runRailEmergencyAction(item.id)}
                                                        disabled={isBusy}
                                                        className="rounded-lg border border-indigo-300/60 px-2.5 py-1 text-[11px] font-semibold text-indigo-200 hover:bg-indigo-500/20 disabled:opacity-60"
                                                    >
                                                        {isBusy ? '실행 중...' : item.emergencyActionLabel}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => void saveRailSettingsFor(item.id)}
                                                        disabled={isSaving || !isDirty}
                                                        className="rounded-lg border border-emerald-300/60 px-2.5 py-1 text-[11px] font-semibold text-emerald-200 hover:bg-emerald-500/20 disabled:opacity-60"
                                                    >
                                                        {isSaving ? '저장 중...' : '설정 저장'}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => resetRailSettingDraft(item.id)}
                                                        className="rounded-lg border border-white/20 px-2.5 py-1 text-[11px] font-semibold text-white/80 hover:bg-white/10"
                                                    >
                                                        기본값 복원
                                                    </button>
                                                </div>
                                                <div className="mt-3">
                                                    <label className="text-[10px] text-white/55" htmlFor={`admin-rail-note-${item.id}`}>운영 메모</label>
                                                    <textarea
                                                        id={`admin-rail-note-${item.id}`}
                                                        value={railOperatorNotes[item.id] || ''}
                                                        onChange={(event) => {
                                                            const nextValue = event.target.value;
                                                            setRailOperatorNotes((prev) => ({
                                                                ...prev,
                                                                [item.id]: nextValue,
                                                            }));
                                                        }}
                                                        className="mt-1 w-full rounded-md border border-white/15 bg-black/35 px-2 py-1.5 text-[11px] text-white"
                                                        placeholder="이 레일의 조치 메모를 기록하세요"
                                                        rows={3}
                                                    />
                                                </div>
                                            </article>
                                        );
                                    })}
                                </div>
                                <div className="mt-3 flex justify-end">
                                    <button
                                        type="button"
                                        onClick={() => setRailActionCenterOpen(false)}
                                        className="rounded-full border border-indigo-300/50 px-2.5 py-1 text-[11px] text-indigo-100 hover:bg-indigo-500/20"
                                        data-testid="admin-rail-action-center-toggle-bottom"
                                    >
                                        아래에서 접기 ▲
                                    </button>
                                </div>
                            </>
                        )}
                        {railActionPayload != null && (
                            <pre
                                className="mt-3 max-h-56 overflow-auto rounded-lg border border-indigo-300/25 bg-black/45 p-3 text-[11px] leading-relaxed text-indigo-100"
                                data-testid="admin-rail-action-payload"
                            >
                                {typeof railActionPayload === 'string'
                                    ? railActionPayload
                                    : JSON.stringify(railActionPayload, null, 2)}
                            </pre>
                        )}
                    </section>
                    <div className="w-full">
                        <AdminLlmControlSummary llmPanelHeight={llmPanelHeight} />
                    </div>
                </div>

                <div style={{ width: '100%', paddingTop: '20px' }}>
                    <AdminManagementSection
                        title="🧭 전역 .env 설정 패널"
                        usage="프로그램 전반 운영값과 연결 설정을 중앙 관리"
                        description="도메인, 저장 경로, LLM 기본 환경값, 셀프 엔진 연동 설정을 첫 화면 핵심 카드 아래 바로 붙입니다."
                        open={systemSettingsPanelOpen}
                        onToggle={() => setSystemSettingsPanelOpen((prev: any) => !prev)}
                        toggleTestId="admin-system-settings-section"
                        windowSize="full"
                    >
                        <AdminSystemSettingsPanel {...adminSystemSettingsAssemblyWithGuard} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🌐 WorldLinco 튜닝"
                        usage="VoIP·대면 통역 VAD/에코/TTS 타이밍을 슬라이더로 원격 조절"
                        description="현재 배포 버전의 고정 기준값을 baseline 으로 유지하고, 저장 즉시 /api/marketplace/worldlinco/tuning 에 반영됩니다. 모바일은 앱 포그라운드 시 자동 fetch."
                        open={worldlincoTuningPanelOpen}
                        onToggle={() => setWorldlincoTuningPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-tuning-section"
                        windowSize="wide"
                    >
                        <AdminWorldlincoTuningPanel apiBaseUrl={apiBaseUrl} getAdminToken={getAdminToken} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="💳 WorldLinco 요금 정책"
                        usage="베타 무료 ↔ 유료 전환 · 요금 중지/재개"
                        description="로그인 사용자 무료 이용(베타)과 유료 게이트 전환, 프로모 기간·요금 징수 중지를 관리자에서 원격 제어합니다. 모바일은 /api/marketplace/worldlinco/billing-policy 를 앱 포그라운드 시 fetch 합니다."
                        open={worldlincoBillingPolicyPanelOpen}
                        onToggle={() => setWorldlincoBillingPolicyPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-billing-policy-section"
                        windowSize="wide"
                    >
                        <AdminWorldlincoBillingPolicyPanel apiBaseUrl={apiBaseUrl} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🌏 WorldLinco 국가별 관광 홍보"
                        usage="앱 홈 중앙 · 국가별 카드"
                        description="GPS 국가 + 50km 반경 spot 홍보만 앱 번역 홈 중앙에 노출됩니다. 문구는 i18n(사용자 프로그램 언어)로 반환됩니다."
                        open={worldlincoTourismPromoPanelOpen}
                        onToggle={() => setWorldlincoTourismPromoPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-tourism-promo-section"
                        windowSize="wide"                >
                        <AdminWorldlincoTourismPromoPanel apiBaseUrl={apiBaseUrl} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🎁 WorldLinco 추천인 QR"
                        usage="앱 설정 · QR/링크 초대"
                        description="사용자가 설정에서 만든 추천 QR·링크로 가입한 신규 회원을 추천인별로 집계합니다."
                        open={worldlincoReferralPanelOpen}
                        onToggle={() => setWorldlincoReferralPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-referral-section"
                        windowSize="wide"                >
                        <AdminWorldlincoReferralPanel apiBaseUrl={apiBaseUrl} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="💼 WorldLinco 영업 수수료 정산"
                        usage="지역·국가별 영업부 · QR 가입 귀속"
                        description="영업자 QR 가입 귀속 · 결제 수수료(30%/10%)를 국가·지역 영업부 지정 통장으로 자동 이체합니다."
                        open={worldlincoSalesCommissionPanelOpen}
                        onToggle={() => setWorldlincoSalesCommissionPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-sales-commission-section"
                        windowSize="wide"                >
                        <AdminWorldlincoSalesCommissionPanel apiBaseUrl={apiBaseUrl} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🗺️ WorldLinco 지역 관리자 · 유저 관리"
                        usage="국가·지역 단위 · 귀속 가입자"
                        description="지역 관리자를 등록하고 국가/지역별 영업 QR 귀속 유저·수수료 KPI를 조회합니다. 지역 관리자는 /admin/regional 에서 로그인합니다."
                        open={worldlincoRegionalPanelOpen}
                        onToggle={() => setWorldlincoRegionalPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-regional-section"
                        windowSize="wide"                >
                        <AdminWorldlincoRegionalPanel apiBaseUrl={apiBaseUrl} mode="admin" />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="📣 WorldLinco 일괄 안내"
                        usage="앱 채팅 · 국가·언어별 번역"
                        description="앱 가입자에게 번역 보관함 + 푸시로 안내를 보냅니다. 미가입자 초대는 앱 내 SNS 공유(카카오·라인)를 사용합니다."
                        open={worldlincoBulkChatPanelOpen}
                        onToggle={() => setWorldlincoBulkChatPanelOpen((prev) => !prev)}
                        toggleTestId="admin-worldlinco-bulk-chat-section"
                        windowSize="wide"                >
                        <AdminWorldlincoBulkChatPanel apiBaseUrl={apiBaseUrl} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="📊 Travel Partner KPI Dashboard"
                        usage="수익 퍼널 KPI · 파트너 SLA · fallback 비율 운영 관제"
                        description="Section 6 KPI 카드를 관리자 좌측 레일에서 즉시 열어 운영 지표를 확인합니다."
                        open={travelPartnerKpiOpen}
                        onToggle={() => setTravelPartnerKpiOpen((prev) => !prev)}
                        toggleTestId="admin-travel-partner-kpi-section"
                        windowSize="wide"                >
                        <AdminTravelPartnerKpiPanel />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🧳 Travel Partner Integration Hub"
                        usage="여행 파트너 API 연결 · 라우팅 · 수익화 운영 허브"
                        description="호텔/이동/투어 파트너 연동 로드맵과 관리자 대시보드 운영 관문입니다."
                        open={travelPartnerIntegrationOpen}
                        onToggle={() => setTravelPartnerIntegrationOpen((prev) => !prev)}
                        toggleTestId="admin-travel-partner-integration-section"
                        windowSize="wide"                >
                        <AdminTravelPartnerIntegrationPanel />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="📊 Grafana 모니터링 대시보드"
                        usage="실시간 메트릭 시각화 · 알람 연동 · 성능 추적"
                        description="Prometheus 데이터를 기반으로 한 대시보드. 실시간 시스템 메트릭과 비즈니스 메트릭을 한눈에 확인합니다."
                        open={grafanaOpen}
                        onToggle={() => setGrafanaOpen(!grafanaOpen)}
                        toggleTestId="admin-grafana-section"
                        windowSize="full"                >
                        <AdminGrafanaMonitorSection apiBaseUrl={apiBaseUrl} settings={railSettings.monitoring} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="📈 Prometheus 데이터 시각화"
                        usage="메트릭 수집 · 시계열 저장 · 쿼리 인터페이스"
                        description="모든 메트릭이 집계되는 시계열 데이터베이스. 시간별 추이를 추적하고 이상 탐지를 수행합니다."
                        open={prometheusOpen}
                        onToggle={() => setPrometheusOpen(!prometheusOpen)}
                        toggleTestId="admin-prometheus-section"
                        windowSize="full"                >
                        <AdminPrometheusSection apiBaseUrl={apiBaseUrl} settings={railSettings.data} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="📉 p50/p95 시계열 차트"
                        usage="응답 시간 백분위수 · 성능 분포 분석"
                        description="사용자 체감 성능을 정량화. p50은 중간값, p95는 상위 5% 지연을 나타냅니다."
                        open={p50p95Open}
                        onToggle={() => setP50p95Open(!p50p95Open)}
                        toggleTestId="admin-p50p95-section"
                        windowSize="wide"                >
                        <AdminP50P95ChartSection settings={railSettings.latency} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="⚡ 성능 최적화"
                        usage="응답 시간 개선 · 처리량 증대 · 병목 분석"
                        description="시스템 병목을 식별하고 최적화 기회를 제시합니다."
                        open={performanceOpen}
                        onToggle={() => setPerformanceOpen(!performanceOpen)}
                        toggleTestId="admin-performance-section"
                        windowSize="wide"                >
                        <AdminPerformanceSection settings={railSettings.performance} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🚀 LLM path 응답 시간 개선"
                        usage="추론 속도 향상 · 지연 시간 감소 · 처리량 극대화"
                        description="LLM 호출 경로의 엔드-투-엔드 성능을 분석하고 개선합니다."
                        open={llmPathOpen}
                        onToggle={() => setLlmPathOpen(!llmPathOpen)}
                        toggleTestId="admin-llmpath-section"
                        windowSize="wide"                >
                        <AdminLlmPathSection settings={railSettings.llm} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🎯 Fast path 커버리지 확대"
                        usage="직접 경로 커버리지 · 우회 경로 최소화 · 성공률 추적"
                        description="캐시 히트율과 fast path 전환율을 모니터링합니다."
                        open={fastPathOpen}
                        onToggle={() => setFastPathOpen(!fastPathOpen)}
                        toggleTestId="admin-fastpath-section"
                        windowSize="wide"                >
                        <AdminFastPathSection settings={railSettings.cover} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🛠️ 운영 준비"
                        usage="배포 준비 · 시스템 점검 · 운영 체크리스트"
                        description="본 운영 단계 이전 필수 검증 항목과 체크리스트를 관리합니다."
                        open={opsOpen}
                        onToggle={() => setOpsOpen(!opsOpen)}
                        toggleTestId="admin-ops-section"
                        windowSize="wide"                >
                        <AdminOpsSection settings={railSettings.ops} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🚨 Prometheus AlertManager 설정"
                        usage="알람 규칙 정의 · 알림 라우팅 · 에스컬레이션"
                        description="임계값 기반 알람을 설정하고 알림 전달 채널을 구성합니다."
                        open={alertManagerOpen}
                        onToggle={() => setAlertManagerOpen(!alertManagerOpen)}
                        toggleTestId="admin-alertmanager-section"
                        windowSize="wide"                >
                        <AdminAlertManagerSection settings={railSettings.sla} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="📋 SLA 정의 및 알림 구성"
                        usage="가용성 목표 · 성능 기준 · 실시간 준수 현황"
                        description="SLA 목표를 설정하고 준수 여부를 실시간으로 모니터링합니다."
                        open={slaOpen}
                        onToggle={() => setSlaOpen(!slaOpen)}
                        toggleTestId="admin-sla-section"
                        windowSize="wide"                >
                        <AdminSLASection settings={railSettings.sla} />
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🎵 음악 생성·작사·협업 패널"
                        usage="관리자 대시보드에서 music API 토큰 호출을 직접 검증"
                        description="감정 기반 작곡, 코드 기반 작곡, 협업 데모 API를 관리자 권한 토큰으로 즉시 호출하고 payload를 확인합니다."
                        open={musicPanelOpen}
                        onToggle={() => setMusicPanelOpen((prev) => !prev)}
                        toggleTestId="admin-music-panel-section"
                        windowSize="wide"                >
                        <div className="workspace-section-stack" data-testid="admin-music-panel">
                            <div className="workspace-sidebar-card">
                                <p className="workspace-card-kicker">Emotion Compose</p>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                                    <input
                                        data-testid="admin-music-emotion-input"
                                        value={musicEmotion}
                                        onChange={(event) => setMusicEmotion(event.target.value)}
                                        placeholder="emotion"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                    <input
                                        data-testid="admin-music-intensity-input"
                                        value={musicIntensity}
                                        onChange={(event) => setMusicIntensity(event.target.value)}
                                        placeholder="intensity"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                    <input
                                        data-testid="admin-music-theme-input"
                                        value={musicTheme}
                                        onChange={(event) => setMusicTheme(event.target.value)}
                                        placeholder="theme"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                </div>
                                <button
                                    type="button"
                                    data-testid="admin-music-compose-emotion-btn"
                                    onClick={handleAdminMusicCompose}
                                    disabled={musicLoading}
                                    className="workspace-topbar-chip"
                                    style={{ marginTop: 10 }}
                                >
                                    {musicLoading ? '음악 생성 중...' : '감정 기반 음악 생성'}
                                </button>
                            </div>

                            <div className="workspace-sidebar-card">
                                <p className="workspace-card-kicker">Code Compose</p>
                                <textarea
                                    data-testid="admin-music-code-input"
                                    value={musicCode}
                                    onChange={(event) => setMusicCode(event.target.value)}
                                    className="workspace-admin-command-textarea"
                                    style={{ minHeight: 80 }}
                                    placeholder="작곡 패턴으로 변환할 코드"
                                />
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, marginTop: 8 }}>
                                    <input
                                        data-testid="admin-music-code-emotion-input"
                                        value={musicCodeEmotion}
                                        onChange={(event) => setMusicCodeEmotion(event.target.value)}
                                        placeholder="emotion"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                    <button
                                        type="button"
                                        data-testid="admin-music-compose-code-btn"
                                        onClick={handleAdminMusicComposeFromCode}
                                        disabled={musicLoading}
                                        className="workspace-topbar-chip"
                                    >
                                        코드 작곡
                                    </button>
                                </div>
                                <button
                                    type="button"
                                    data-testid="admin-music-friends-demo-btn"
                                    onClick={handleAdminMusicCollaboration}
                                    disabled={musicLoading}
                                    className="workspace-topbar-chip"
                                    style={{ marginTop: 8 }}
                                >
                                    협업 데모 연결
                                </button>
                            </div>

                            <div className="workspace-sidebar-card">
                                <p className="workspace-card-kicker">Payload</p>
                                {musicMode ? <p className="workspace-card-copy" data-testid="admin-music-mode">mode: {musicMode}</p> : null}
                                {musicError ? <p className="workspace-card-copy" style={{ color: 'var(--workspace-danger)' }} data-testid="admin-music-error">{musicError}</p> : null}
                                {musicComposeResult ? (
                                    <div className="workspace-list" data-testid="admin-music-compose-result">
                                        <div className="workspace-list-item"><strong>song</strong><span>{String(musicComposeResult.song_title || '-')}</span></div>
                                        <div className="workspace-list-item"><strong>lyrics</strong><span>{String(musicComposeResult.lyrics_title || '-')}</span></div>
                                        <div className="workspace-list-item"><strong>tempo</strong><span>{String(musicComposeResult.tempo || '-')}</span></div>
                                    </div>
                                ) : null}
                                {musicCodeResult ? (
                                    <div className="workspace-list" data-testid="admin-music-code-result" style={{ marginTop: 10 }}>
                                        <div className="workspace-list-item"><strong>song</strong><span>{String(musicCodeResult.song_title || '-')}</span></div>
                                        <div className="workspace-list-item"><strong>composition</strong><span>{String(musicCodeResult.code_composition_title || '-')}</span></div>
                                        <div className="workspace-list-item"><strong>chords</strong><span>{Array.isArray(musicCodeResult.chords) ? musicCodeResult.chords.join(' → ') : '-'}</span></div>
                                    </div>
                                ) : null}
                                {musicFriendResult ? (
                                    <div className="workspace-list" data-testid="admin-music-friends-result" style={{ marginTop: 10 }}>
                                        <div className="workspace-list-item"><strong>request</strong><span>{String(musicFriendResult.request_id || '-')}</span></div>
                                        <div className="workspace-list-item"><strong>collaboration</strong><span>{String(musicFriendResult.collaboration_id || '-')}</span></div>
                                        <div className="workspace-list-item"><strong>friends</strong><span>{Array.isArray(musicFriendResult.friends_of_a) ? musicFriendResult.friends_of_a.join(', ') : '-'}</span></div>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                    </AdminManagementSection>

                    <AdminManagementSection
                        title="🧪/🧬 Extras API 인앱 프리뷰"
                        usage="새 탭 이동 없이 health/catalog 응답을 대시보드 내부에서 확인"
                        description="상태코드, 응답시간, 갱신 시각, JSON payload를 한 패널에서 확인하고 즉시 재조회할 수 있습니다."
                        open={extrasPreviewPanelOpen}
                        onToggle={() => setExtrasPreviewPanelOpen((prev) => !prev)}
                        toggleTestId="admin-extras-preview-section"
                        windowSize="wide"                >
                        <div className="workspace-section-stack" data-testid="admin-extras-preview-panel">
                            <div className="workspace-sidebar-card">
                                <p className="workspace-card-kicker">Request</p>
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                    <button
                                        type="button"
                                        data-testid="admin-extras-preview-health-btn"
                                        onClick={() => void runExtrasPreviewRequest('health')}
                                        disabled={extrasPreviewState.loading}
                                        className="workspace-topbar-chip"
                                    >
                                        health 조회
                                    </button>
                                    <button
                                        type="button"
                                        data-testid="admin-extras-preview-catalog-btn"
                                        onClick={() => void runExtrasPreviewRequest('catalog')}
                                        disabled={extrasPreviewState.loading}
                                        className="workspace-topbar-chip"
                                    >
                                        catalog 조회
                                    </button>
                                    <button
                                        type="button"
                                        data-testid="admin-extras-preview-refresh-btn"
                                        onClick={() => void runExtrasPreviewRequest(extrasPreviewTarget)}
                                        disabled={extrasPreviewState.loading}
                                        className="workspace-topbar-chip"
                                    >
                                        {extrasPreviewState.loading ? '조회 중...' : '현재 탭 재조회'}
                                    </button>
                                </div>
                                <p className="workspace-card-copy" style={{ marginTop: 10 }}>
                                    endpoint: {extrasPreviewTarget === 'health' ? '/api/marketplace/extras/health' : '/api/marketplace/extras/catalog'}
                                </p>
                            </div>

                            <div className="workspace-sidebar-card">
                                <p className="workspace-card-kicker">Response Meta</p>
                                <div className="workspace-list">
                                    <div className="workspace-list-item"><strong>status</strong><span data-testid="admin-extras-preview-status">{extrasPreviewState.statusCode ?? '-'}</span></div>
                                    <div className="workspace-list-item"><strong>latency</strong><span>{extrasPreviewState.durationMs != null ? `${extrasPreviewState.durationMs} ms` : '-'}</span></div>
                                    <div className="workspace-list-item"><strong>fetchedAt</strong><span>{extrasPreviewState.fetchedAt ? new Date(extrasPreviewState.fetchedAt).toLocaleString('ko-KR') : '-'}</span></div>
                                </div>
                                {extrasPreviewState.error ? (
                                    <p data-testid="admin-extras-preview-error" className="workspace-card-copy" style={{ marginTop: 10, color: 'var(--workspace-danger)' }}>
                                        {extrasPreviewState.error}
                                    </p>
                                ) : null}
                            </div>

                            <div className="workspace-sidebar-card">
                                <p className="workspace-card-kicker">Payload</p>
                                <pre
                                    data-testid="admin-extras-preview-payload"
                                    style={{
                                        margin: 0,
                                        whiteSpace: 'pre-wrap',
                                        wordBreak: 'break-word',
                                        background: 'rgba(9,14,22,0.96)',
                                        border: '1px solid var(--workspace-border)',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        padding: 12,
                                        maxHeight: 320,
                                        overflow: 'auto',
                                        color: 'var(--workspace-text)',
                                        fontSize: 12,
                                        lineHeight: 1.45,
                                    }}
                                >
                                    {extrasPreviewState.payload == null
                                        ? '조회 결과가 없습니다.'
                                        : typeof extrasPreviewState.payload === 'string'
                                            ? extrasPreviewState.payload
                                            : JSON.stringify(extrasPreviewState.payload, null, 2)}
                                </pre>
                            </div>
                        </div>
                    </AdminManagementSection>

                    {boardSections.filter(section => section.id !== 'llm').map((section) => (
                        <AdminManagementSection
                            key={section.id}
                            title={section.title}
                            usage={section.usage}
                            description={section.description}
                            open={section.open}
                            onToggle={section.onToggle}
                            toggleTestId={section.toggleTestId || `admin-${section.id}-section`}
                            windowSize={section.windowSize}                    >
                            {section.body}
                        </AdminManagementSection>
                    ))}
                </div>
            </WorkspaceChrome>

            <AdminAdPreviewModal
                order={adPreviewOrder}
                previewUrl={adPreviewUrl}
                previewError={adPreviewError}
                onClose={closeAdPreview}
            />

            <AdminStoryboardModal
                modal={adStoryboardModal}
                currentDiff={currentAdStoryboardModalDiff}
                currentIndex={currentAdStoryboardModalIndex}
                onClose={() => setAdStoryboardModal(null)}
                onMoveCut={moveAdStoryboardModalCut}
            />
        </div>
    );
}
