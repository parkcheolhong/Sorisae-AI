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
    const panelDeepLinkHandledRef = useRef(false);
    const lastSpokenAlertSignatureRef = useRef('');
    const autoOpsSignatureRef = useRef('');
    const [musicPanelOpen, setMusicPanelOpen] = React.useState(false);
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
    const pushLiveLog = useCallback((level: LiveLogItem['level'], message: string, meta?: Partial<LiveLogItem> & { capabilityId?: string }) => {
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
            const storedLogsRaw = localStorage.getItem(ADMIN_LIVE_LOGS_STORAGE_KEY);
            if (storedLogsRaw) {
                const parsedLogs = JSON.parse(storedLogsRaw) as LiveLogItem[];
                if (Array.isArray(parsedLogs)) {
                    setLiveLogs(
                        parsedLogs
                            .map(normalizeStoredLiveLog)
                            .filter((item): item is LiveLogItem => item !== null)
                            .slice(0, 30)
                    );
                }
            }

            const storedVoiceAlertEnabled = localStorage.getItem(ADMIN_ALERT_VOICE_ENABLED_STORAGE_KEY);
            if (storedVoiceAlertEnabled === 'false') {
                setVoiceAlertEnabled(false);
            }

            const storedDashboardPreferencesRaw = localStorage.getItem(ADMIN_DASHBOARD_PREFERENCES_STORAGE_KEY);
            if (storedDashboardPreferencesRaw) {
                const preferences = JSON.parse(storedDashboardPreferencesRaw) as {
                    refreshSeconds?: number;
                    autoRefreshEnabled?: boolean;
                };
                if (typeof preferences.refreshSeconds === 'number') {
                    setRefreshSeconds(Math.max(5, Math.min(300, preferences.refreshSeconds)));
                }
                if (typeof preferences.autoRefreshEnabled === 'boolean') {
                    setAutoRefreshEnabled(preferences.autoRefreshEnabled);
                }
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

    const handleLogout = () => {
        clearAdminToken();
        hardRedirectToAdminLogin();
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
        if (isRefresh) setRefreshing(true);
        else setLoading(true);
        setError(null);
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
            if (isRefresh) setRefreshing(false);
            else setLoading(false);
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
        if (controllerResult.healthData) setHealth(controllerResult.healthData);
        if (controllerResult.llmData) setLlmStatus(controllerResult.llmData);
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
        if (controllerResult.assembledState.orchestratorCapabilitySummary) {
            setOrchestratorCapabilitySummary(controllerResult.assembledState.orchestratorCapabilitySummary);
        }
        setSecurityGuardDetail(controllerResult.assembledState.securityGuardDetail);
        setDashboardSelfRunStatus(controllerResult.assembledState.dashboardSelfRunStatus);
        if (controllerResult.failedMessages.length > 0) setError(controllerResult.failedMessages.join(' · '));
        snapshotRef.current = controllerResult.nextSnapshot;
        setLastUpdated(controllerResult.lastUpdated);
        if (isRefresh) setRefreshing(false);
        else setLoading(false);
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
        systemSettingsDisconnected: !systemSettings && !systemSettingsLoading && !!systemSettingsMessage,
        capabilityBootstrapEnabled: capabilityBootstrapReady,
        projectQuery,
        topProjects,
        formatCurrency,
    }), [dashboardSelfRunStatus, formatCurrency, health, llmStatus, orchestratorCapabilitySummary, overview, projectQuery, revenue, securityGuardDetail, systemSettings, systemSettingsLoading, systemSettingsMessage, topProjects]);
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
            setAutoRecoveryHistory((prev: any) => [recoveryResult.historyItem as AutoRecoveryHistoryItem, ...prev].slice(0, 20));
        } finally {
            setAutoRecoveryRunning(false);
        }
    }, [
        dashboardSelfRunStatus?.approval_id,
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
                document.querySelector('[data-testid="admin-subscription-monitor-section"]')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 60);
        });
    }, [authChecked]);

    useEffect(() => {
        if (!autoOpsEnabled || !authChecked) return;
        const signature = [
            dashboardSelfRunStatus?.approval_id || '-',
            dashboardSelfRunStatus?.status || '-',
            dashboardAnalysis.selfRunFailureInsight?.category || '-',
            String(systemSettingsDisconnected),
            String(dashboardAnalysis.hasOrchestratorCapabilityError),
            String(dashboardAnalysis.hasOrchestratorCapabilityWarning),
        ].join('|');
        if (autoOpsSignatureRef.current === signature) return;
        autoOpsSignatureRef.current = signature;
        if (dashboardAnalysis.selfRunFailureInsight) {
            pushLiveLog(dashboardAnalysis.selfRunFailureInsight.severity === 'critical' ? 'warning' : 'info', `자동 진단: ${dashboardAnalysis.selfRunFailureInsight.title}`);
        }
        void executeAutomaticRecovery('auto');
    }, [
        authChecked,
        autoOpsEnabled,
        dashboardSelfRunStatus?.approval_id,
        dashboardSelfRunStatus?.status,
        executeAutomaticRecovery,
        dashboardAnalysis.selfRunFailureInsight,
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
                document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
                document.querySelector(`[data-testid="${toggleTestId}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 80);
        });
    }, []);

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
        }, 1000);
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
                    ...buildAdminLauncherRailItems(launcherLeftColumn, ADMIN_LEFT_SHORT_LABEL_OVERRIDES),
                ]}
                rightRailItems={[
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
                topActions={(
                    <>
                        <Link prefetch={false} href={marketplaceHomeHref} data-testid="admin-topnav-marketplace" aria-label="마켓플레이스 이동" className="workspace-topbar-chip">
                            마켓
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
                    <div className="w-full">
                        <AdminLlmControlSummary llmPanelHeight={llmPanelHeight} />
                    </div>
                </div>

                <AdminManagementSection
                    title="🧭 전역 .env 설정 패널"
                    usage="프로그램 전반 운영값과 연결 설정을 중앙 관리"
                    description="도메인, 저장 경로, LLM 기본 환경값, 셀프 엔진 연동 설정을 첫 화면 핵심 카드 아래 바로 붙입니다."
                    open={systemSettingsPanelOpen}
                    onToggle={() => setSystemSettingsPanelOpen((prev: any) => !prev)}
                    toggleTestId="admin-system-settings-section"
                    windowSize="full"
                    launcherHidden
                >
                    <AdminSystemSettingsPanel {...adminSystemSettingsAssembly} />
                </AdminManagementSection>

                <AdminManagementSection
                    title="🎵 음악 생성·작사·협업 패널"
                    usage="관리자 대시보드에서 music API 토큰 호출을 직접 검증"
                    description="감정 기반 작곡, 코드 기반 작곡, 협업 데모 API를 관리자 권한 토큰으로 즉시 호출하고 payload를 확인합니다."
                    open={musicPanelOpen}
                    onToggle={() => setMusicPanelOpen((prev) => !prev)}
                    toggleTestId="admin-music-panel-section"
                    windowSize="wide"
                    launcherHidden
                >
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
                    windowSize="wide"
                    launcherHidden
                >
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
                        windowSize={section.windowSize}
                        launcherHidden
                    >
                        {section.body}
                    </AdminManagementSection>
                ))}
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
