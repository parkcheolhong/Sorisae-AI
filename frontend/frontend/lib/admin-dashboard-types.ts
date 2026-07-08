export interface OverviewStats {
    projects: number;
    users: number;
    purchases: number;
    reviews: number;
    vector_search?: {
        status?: string;
        projects?: { points_count?: number; vectors_count?: number };
        reviews?: { points_count?: number; vectors_count?: number };
    };
}

export interface FocusedSelfHealingRetryPayload {
    queued: boolean;
    mode: string;
    source_path: string;
    focused_path: string;
    target_kind: string;
    directive_template: string;
    directive_scope: string;
    selected_option_id?: string | null;
    context?: Record<string, unknown> | null;
    verification_loop?: string[];
}

export interface FocusedSelfHealingApplyResult {
    issue_id: string;
    focused_path: string;
    target_source_path: string;
    category: string;
    auto_apply_allowed: boolean;
    approval_required: boolean;
    selected_option_id?: string | null;
    retry?: FocusedSelfHealingRetryPayload | null;
    message: string;
}

export interface AdminSettlementChartPoint {
    period: string;
    order_count: number;
    total_tokens: number;
    total_cost: number;
}

export interface AdminSettlementLogItem {
    order_id: number;
    user_id: number;
    status: string;
    engine_type: string;
    render_quality: string;
    currency: string;
    prompt_tokens: number;
    render_tokens: number;
    total_tokens: number;
    local_cost: number;
    external_cost: number;
    storage_cost: number;
    total_cost: number;
    period_day: string;
    period_month: string;
    created_at: string;
}

export interface AdminAdOrderSettlementDashboard {
    daily: AdminSettlementChartPoint[];
    monthly: AdminSettlementChartPoint[];
    recent_logs: AdminSettlementLogItem[];
    settlement_line: string;
}

export interface AdminMonitorRatioItem {
    key: string;
    label: string;
    count: number;
    ratio: number;
}

export interface AdminAdOrderMonitorSummary {
    totals: {
        total_orders: number;
        active_orders: number;
        completed_orders: number;
        failed_orders: number;
        completion_rate: number;
        failure_rate: number;
        average_progress: number;
        average_quality_score: number;
    };
    ratios: {
        status: AdminMonitorRatioItem[];
        engine: AdminMonitorRatioItem[];
        quality: AdminMonitorRatioItem[];
    };
    token_summary: {
        estimated_prompt_tokens: number;
        estimated_render_tokens: number;
        estimated_total_tokens: number;
        estimated_avg_tokens_per_order: number;
    };
    settlement: {
        local_cost_total: number;
        external_cost_total: number;
        storage_cost_total: number;
        total_estimated_cost: number;
        estimated_cost_per_order: number;
        settlement_line: string;
    };
}

export interface AdminSubscriptionMonitorStatusItem {
    status: string;
    count: number;
}

export interface AdminSubscriptionStateTransitionItem {
    id: number;
    subscription_id: number;
    from_status: string;
    to_status: string;
    reason_code: string;
    actor_type: string;
    created_at?: string | null;
}

export interface AdminSubscriptionWebhookFailureItem {
    id: number;
    provider: string;
    event_id: string;
    attempt_number: number;
    result: string;
    http_status?: number | null;
    error_message: string;
    created_at?: string | null;
}

export interface AdminSubscriptionMonitorSummary {
    totals: {
        total_subscriptions: number;
        active_subscriptions: number;
        failed_payment_count: number;
        refunds_count: number;
    };
    filters: {
        period_days: number;
        status?: string | null;
    };
    status_breakdown: AdminSubscriptionMonitorStatusItem[];
    recent_state_transitions: AdminSubscriptionStateTransitionItem[];
    recent_webhook_failures: AdminSubscriptionWebhookFailureItem[];
}

export interface RevenueStats {
    total_revenue: number;
    total_purchases: number;
    average_purchase_amount: number;
}

export interface TopProject {
    id: number;
    title: string;
    downloads: number;
    rating: number;
    price: number;
}

export interface AdminAdVideoOrderItem {
    id: number;
    user_id: number;
    title: string;
    image_prompt?: string | null;
    background_prompt?: string | null;
    caption_text?: string | null;
    portrait_image_prompt?: string | null;
    product_image_prompts?: string[];
    storyboard?: Array<{ cut: number; title?: string; duration_sec?: number; narration_line?: string; visual_focus?: string; scene_prompt?: string; designer_prompt?: string; motion_speed_percent?: number; source_scenario?: string; start_sec?: number; end_sec?: number; asset_source?: 'auto' | 'portrait' | 'product' | 'custom'; product_index?: number | null; asset_ref?: string | null }>;
    storyboard_review?: Array<{ cut: number; status: 'pending' | 'approved' | 'needs-fix'; note?: string }>;
    storyboard_review_history?: Array<{ changed_at?: string; changed_by?: number | null; storyboard_review?: Array<{ cut: number; status: 'pending' | 'approved' | 'needs-fix'; note?: string }>; diff?: Array<{ cut: number; previous_status?: string; current_status?: string; previous_note?: string; current_note?: string }> }>;
    voice_gender?: string;
    engine_type?: string;
    scenario_script?: string | null;
    action_template_key?: string | null;
    motion_tempo?: 'slow' | 'normal' | 'fast' | 'run' | null;
    duration_seconds?: number;
    cut_count?: number;
    render_quality?: 'standard' | 'high' | 'ultra' | string;
    status: string;
    progress_percent?: number;
    error_message?: string | null;
    output_filename?: string | null;
    output_video_filename?: string | null;
    quality_score?: number | null;
    quality_gate_passed?: boolean;
    quality_feedback?: string | null;
    face_consistency_score?: number | null;
    product_consistency_score?: number | null;
    sales_quality_decision?: 'sale_ready' | 'review_required' | 'blocked' | string | null;
    quality_checked_at?: string | null;
    created_at?: string | null;
}

export interface OrchestratorCapabilityGroupSummary {
    id: string;
    title: string;
    state: 'standby' | 'active' | 'warning' | 'error';
    summary: string;
    active_count: number;
    warning_count: number;
    error_count: number;
}

export interface OrchestratorCapabilitySummaryCard {
    id: string;
    title: string;
    group_id: string;
    state: 'standby' | 'active' | 'warning' | 'error';
    summary: string;
    metric: string;
    state_label?: string | null;
    state_reason?: string | null;
    detail?: string | null;
    evidence_digest?: {
        completion_gate_ok?: boolean | null;
        self_run_status?: string | null;
        failure_tag_count?: number;
        target_file_id_count?: number;
        operational_target_count?: number;
        operational_verified_count?: number;
    };
}

export interface OrchestratorCapabilityDetailSectionItem {
    label: string;
    value: string | number | boolean;
    note?: string | null;
}

export interface OrchestratorCapabilityDetailSection {
    id: string;
    title: string;
    items: OrchestratorCapabilityDetailSectionItem[];
}

export interface OrchestratorCapabilityDetailResponse {
    generated_at: string;
    capability: OrchestratorCapabilitySummaryCard;
    highlights: string[];
    suggested_actions: string[];
    sections: OrchestratorCapabilityDetailSection[];
    evidence_bundle?: {
        contract?: Record<string, unknown>;
        execution?: Record<string, unknown>;
        readiness?: Record<string, unknown>;
        operations?: Record<string, unknown>;
        selective_apply?: {
            target_file_ids?: string[];
            target_section_ids?: string[];
            target_feature_ids?: string[];
            target_chunk_ids?: string[];
            failure_tags?: string[];
            repair_tags?: string[];
        };
    };
    target_file_ids?: string[];
    target_section_ids?: string[];
    target_feature_ids?: string[];
    target_chunk_ids?: string[];
    failure_tags?: string[];
    repair_tags?: string[];
    expansion_experiment?: {
        work_document_title?: string;
        work_document?: string;
        focus_path?: string;
        recommended_self_run?: {
            mode?: string;
            execution_mode?: string;
            directive_template?: string;
            directive_scope?: string;
            directive_request?: string;
            endpoint?: string;
        };
    } | null;
}

export interface OrchestratorCapabilitySummaryResponse {
    generated_at: string;
    groups: OrchestratorCapabilityGroupSummary[];
    capabilities: OrchestratorCapabilitySummaryCard[];
}

export interface AdminDashboardSelfRunStatus {
    approval_id: string;
    status: 'running' | 'pending_approval' | 'failed' | 'completed' | 'no_changes' | 'applied_to_source';
    started_at?: string | null;
    finished_at?: string | null;
    directive_template?: string | null;
    directive_scope?: string | null;
    running_seconds?: number | null;
    runtime_diagnostic?: string | null;
    worker_log_path?: string | null;
    source_path?: string | null;
    analysis_path?: string | null;
    analysis_abs_path?: string | null;
    root_cause_report_path?: string | null;
    root_cause_report_abs_path?: string | null;
    python_self_diagnostic_error?: string | null;
    python_self_diagnostic_logs?: string[];
    python_compile_failed_files?: string[];
    target_file_ids?: string[];
    target_section_ids?: string[];
    target_feature_ids?: string[];
    target_chunk_ids?: string[];
    failure_tags?: string[];
    repair_tags?: string[];
}

export interface SelfRunFailureInsight {
    severity: 'warning' | 'critical';
    category: 'python_compile_fail' | 'import_error' | 'dependency' | 'timeout' | 'output_shortage' | 'unknown';
    title: string;
    reason: string;
    automatedActions: string[];
    priorityFixPaths: string[];
    guideHref: string;
}

export interface SelfRunDisplayMeta {
    label: string;
    tone: string;
    detail: string;
    healthPenalty: number;
    actionable: boolean;
}

export interface AutoRecoveryHistoryItem {
    id: string;
    triggeredAt: string;
    mode: 'auto' | 'manual';
    title: string;
    category: SelfRunFailureInsight['category'] | 'generic';
    summary: string;
    approvalId?: string;
    primaryPath?: string;
    retryQueued?: boolean;
    retryMessage?: string;
    retryStage?: 'diagnosis' | 'remediation';
    failedFiles?: string[];
    normalizationAction?: string;
    normalizationMessage?: string;
}

export interface TowerCraneOption {
    option_id: string;
    title: string;
    scope: string;
    pros: string[];
    cons: string[];
    impact_paths: string[];
    validation_plan: string[];
    risk_level: 'low' | 'medium' | 'high' | string;
    summary?: string;
}

export interface FocusedSelfHealingPlan {
    issue_id: string;
    requested_path: string;
    focused_path: string;
    target_source_path: string;
    target_kind: 'file' | 'directory' | string;
    category: string;
    auto_apply_allowed: boolean;
    approval_required: boolean;
    rationale: string;
    suggested_action: string;
    proposal_id: string;
    options: TowerCraneOption[];
    execution_contract?: {
        auto_apply?: string;
        approval_required?: string;
        verification_loop?: string[];
    };
}

export function assertAdminDashboardTypesContract() {
    const sample: AdminDashboardSelfRunStatus = {
        approval_id: 'sample',
        status: 'failed',
    };
    if (!sample.approval_id || !sample.status) {
        throw new Error('admin dashboard types contract 누락: AdminDashboardSelfRunStatus 핵심 필드 필요');
    }
}
