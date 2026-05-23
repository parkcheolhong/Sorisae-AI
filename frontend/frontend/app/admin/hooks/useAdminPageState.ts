// FILE-ID: HOOKS-USE-ADMIN-PAGE-STATE-TS
// SECTION-ID: HOOKS-USE-ADMIN-PAGE-STATE-MAIN
// FEATURE-ID: FEATURE-ADMIN-PAGE-STATE-MANAGEMENT
// CHUNK-ID: CHUNK-HOOKS-USE-ADMIN-PAGE-STATE-001

import { useState } from 'react';

/**
 * Groups all useState declarations for admin page into organized custom hook
 * Reduces component body from 2,409 lines to ~1,500 lines
 */
export function useAdminPageState(): any {
    // ============================================================
    // Authentication & Session State
    // ============================================================
    const [authChecked, setAuthChecked] = useState(false);
    const [authStatusMessage, setAuthStatusMessage] = useState('인증 확인 중...');
    const [adminUser, setAdminUser] = useState(null);

    // ============================================================
    // Data Loading & Refresh State
    // ============================================================
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastUpdated, setLastUpdated] = useState('');
    const [error, setError] = useState(null);

    // ============================================================
    // Dashboard Overview State
    // ============================================================
    const [overview, setOverview] = useState({ projects: 0, users: 0, purchases: 0, reviews: 0 });
    const [revenue, setRevenue] = useState({
        total_revenue: 0,
        total_purchases: 0,
        average_purchase_amount: 0,
    });
    const [topProjects, setTopProjects] = useState([]);
    const [health, setHealth] = useState(null);
    const [llmStatus, setLlmStatus] = useState(null);

    // ============================================================
    // Search & Filter State
    // ============================================================
    const [projectQuery, setProjectQuery] = useState('');

    // ============================================================
    // Panel Toggle State
    // ============================================================
    const [topProjectsOpen, setTopProjectsOpen] = useState(true);
    const [adOrdersOpen, setAdOrdersOpen] = useState(false);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
    const [refreshSeconds, setRefreshSeconds] = useState(20);
    const [systemSettingsPanelOpen, setSystemSettingsPanelOpen] = useState(false);
    const [liveLogsPanelOpen, setLiveLogsPanelOpen] = useState(false);
    const [autoConnectGraphPanelOpen, setAutoConnectGraphPanelOpen] = useState(false);
    const [customerOrchestratorPanelOpen, setCustomerOrchestratorPanelOpen] = useState(false);
    const [topProjectsPanelOpen, setTopProjectsPanelOpen] = useState(false);
    const [adminControlHubOpen, setAdminControlHubOpen] = useState(false);
    const [healthOverviewOpen, setHealthOverviewOpen] = useState(false);
    const [adOrdersPanelOpen, setAdOrdersPanelOpen] = useState(false);
    const [subscriptionMonitorPanelOpen, setSubscriptionMonitorPanelOpen] = useState(false);
    const [categoryPanelOpen, setCategoryPanelOpen] = useState(false);
    const [quickLinksPanelOpen, setQuickLinksPanelOpen] = useState(false);
    const [llmControlPanelOpen, setLlmControlPanelOpen] = useState(false);
    const [samplePanelOpen, setSamplePanelOpen] = useState(false);

    // ============================================================
    // Live Logs & Real-time Data
    // ============================================================
    const [liveLogs, setLiveLogs] = useState([]);
    const [autoConnectGraph, setAutoConnectGraph] = useState({
        active_connection_id: '',
        events: [],
    });

    // ============================================================
    // Ad Orders & Video Management
    // ============================================================
    const [adVideoOrders, setAdVideoOrders] = useState([]);
    const [adVideoTotal, setAdVideoTotal] = useState(0);
    const [adOrderMonitorSummary, setAdOrderMonitorSummary] = useState(null);
    const [adSettlementDashboard, setAdSettlementDashboard] = useState(null);

    // ============================================================
    // Cost Simulator State
    // ============================================================
    const [costSimulatorPanelOpen, setCostSimulatorPanelOpen] = useState(false);
    const [costSimulatorLoading, setCostSimulatorLoading] = useState(false);
    const [costSimulatorError, setCostSimulatorError] = useState('');
    const [costSimulatorResult, setCostSimulatorResult] = useState(null);
    const [costSimulatorForm, setCostSimulatorForm] = useState({
        monthly_orders: 100,
        cuts_per_order: 8,
        preview_runs_per_order: 3,
        approved_external_cuts_per_order: 8,
        candidates_per_cut: 1.0,
        retry_rate: 0.25,
        external_image_unit_cost: 0.12,
        external_video_unit_cost: 0.0,
        external_video_ratio: 0.0,
        local_preview_unit_cost: 0.01,
        local_stitch_unit_cost: 0.02,
        storage_unit_cost: 0.005,
        premium_ratio: 0.2,
        currency: 'USD',
    });

    // ============================================================
    // Orchestrator State
    // ============================================================
    const [orchestratorCapabilitySummary, setOrchestratorCapabilitySummary] = useState(null);
    const [securityGuardDetail, setSecurityGuardDetail] = useState(null);
    const [dashboardSelfRunStatus, setDashboardSelfRunStatus] = useState(null);

    // ============================================================
    // Audio & Voice Alert
    // ============================================================
    const [voiceAlertEnabled, setVoiceAlertEnabled] = useState(true);

    // ============================================================
    // Layout & Sizing
    // ============================================================
    const [llmPanelHeight, setLlmPanelHeight] = useState(1800);

    // ============================================================
    // Generator & Model Config
    // ============================================================
    const [generatorModelOverrides, setGeneratorModelOverrides] = useState({});

    // ============================================================
    // Admin Stage Run State
    // ============================================================
    const [adminStageRun, setAdminStageRun] = useState(null);
    const [adminStageNoteDraft, setAdminStageNoteDraft] = useState('');
    const [adminStageSubstepChecks, setAdminStageSubstepChecks] = useState({});
    const [adminStageRevisionNote, setAdminStageRevisionNote] = useState('');
    const [adminStageUpdateLoading, setAdminStageUpdateLoading] = useState(false);

    // ============================================================
    // Auto Operations & Recovery
    // ============================================================
    const [autoOpsEnabled, setAutoOpsEnabled] = useState(true);
    const [autoOpsLastExecutedAt, setAutoOpsLastExecutedAt] = useState('');
    const [autoRecoveryHistory, setAutoRecoveryHistory] = useState([]);
    const [autoRecoveryRunning, setAutoRecoveryRunning] = useState(false);

    // ============================================================
    // Self-Run Operations
    // ============================================================
    const [selfRunApproving, setSelfRunApproving] = useState(false);
    const [selfRunRetrying, setSelfRunRetrying] = useState(false);
    const [selfRunNormalizing, setSelfRunNormalizing] = useState(false);

    // ============================================================
    // Focused Self-Healing State
    // ============================================================
    const [focusedSelfHealingBusy, setFocusedSelfHealingBusy] = useState(false);
    const [focusedSelfHealingModalOpen, setFocusedSelfHealingModalOpen] = useState(false);
    const [focusedSelfHealingRequestedPath, setFocusedSelfHealingRequestedPath] = useState(
        'frontend/frontend/app/admin/page.tsx'
    );
    const [focusedSelfHealingReason, setFocusedSelfHealingReason] = useState('health score contract mismatch');
    const [focusedSelfHealingPlan, setFocusedSelfHealingPlan] = useState(null);
    const [focusedSelfHealingApplyResult, setFocusedSelfHealingApplyResult] = useState(null);
    const [focusedSelfHealingApprovalConfirmed, setFocusedSelfHealingApprovalConfirmed] = useState(false);
    const [focusedSelfHealingSelectedOptionId, setFocusedSelfHealingSelectedOptionId] = useState('');
    const [focusedSelfHealingMessage, setFocusedSelfHealingMessage] = useState('');

    // ============================================================
    // Bootstrap State
    // ============================================================
    const [capabilityBootstrapReady, setCapabilityBootstrapReady] = useState(false);

    // Return all state and setters as a single object
    return {
        // Auth
        authChecked,
        setAuthChecked,
        authStatusMessage,
        setAuthStatusMessage,
        adminUser,
        setAdminUser,

        // Loading
        loading,
        setLoading,
        refreshing,
        setRefreshing,
        lastUpdated,
        setLastUpdated,
        error,
        setError,

        // Overview
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

        // Search
        projectQuery,
        setProjectQuery,

        // Panels
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

        // Live Data
        liveLogs,
        setLiveLogs,
        autoConnectGraph,
        setAutoConnectGraph,

        // Ad Orders
        adVideoOrders,
        setAdVideoOrders,
        adVideoTotal,
        setAdVideoTotal,
        adOrderMonitorSummary,
        setAdOrderMonitorSummary,
        adSettlementDashboard,
        setAdSettlementDashboard,

        // Cost Simulator
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

        // Orchestrator
        orchestratorCapabilitySummary,
        setOrchestratorCapabilitySummary,
        securityGuardDetail,
        setSecurityGuardDetail,
        dashboardSelfRunStatus,
        setDashboardSelfRunStatus,

        // Voice
        voiceAlertEnabled,
        setVoiceAlertEnabled,

        // Layout
        llmPanelHeight,
        setLlmPanelHeight,

        // Generator
        generatorModelOverrides,
        setGeneratorModelOverrides,

        // Admin Stage
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

        // Auto Ops
        autoOpsEnabled,
        setAutoOpsEnabled,
        autoOpsLastExecutedAt,
        setAutoOpsLastExecutedAt,
        autoRecoveryHistory,
        setAutoRecoveryHistory,
        autoRecoveryRunning,
        setAutoRecoveryRunning,

        // Self-Run
        selfRunApproving,
        setSelfRunApproving,
        selfRunRetrying,
        setSelfRunRetrying,
        selfRunNormalizing,
        setSelfRunNormalizing,

        // Self-Healing
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

        // Bootstrap
        capabilityBootstrapReady,
        setCapabilityBootstrapReady,
    };
}
