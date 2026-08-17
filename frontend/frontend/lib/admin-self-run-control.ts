export type AdminDashboardSelfRunStatusLike = {
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
};

export function buildSelfRunUnsupportedMessage(apiPath: string) {
    return `${apiPath} 미지원 · 실행 중 백엔드가 최신 관리자 self-run API를 아직 로드하지 않았습니다. 백엔드 재시작 또는 배포 동기화가 필요합니다.`;
}

export function assertAdminSelfRunControlContract() {
    const sample: AdminDashboardSelfRunStatusLike = {
        approval_id: 'sample',
        status: 'failed',
        runtime_diagnostic: '',
        python_compile_failed_files: [],
    };
    const requiredKeys = ['approval_id', 'status'];
    const missing = requiredKeys.filter((key) => !(key in sample));
    if (missing.length > 0) {
        throw new Error(`admin self-run control contract 누락: ${missing.join(', ')}`);
    }
}

export async function retryWorkspaceSelfRunRequest(options: {
    apiBaseUrl: string;
    token: string;
    approvalId?: string | null;
    sourcePath?: string | null;
    targetStage: 'diagnosis' | 'remediation';
    fetchImpl?: typeof fetch;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    onUnauthorized: () => void;
    onUnsupported: (message: string) => void;
    onSuccess: (message: string) => void;
    onWarning: (message: string) => void;
    setUnavailable: (nextValue: boolean) => void;
}) {
    const fetcher = options.fetchImpl || fetch;
    const apiPath = '/api/admin/workspace-self-run-record/retry';
    const response = await fetcher(`${options.apiBaseUrl}${apiPath}`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            approval_id: options.approvalId || null,
            source_path: options.sourcePath || null,
            target_stage: options.targetStage,
            reason: '관리자 대시보드에서 Python 디버그 self-run 재시도를 요청했습니다.',
        }),
    });

    if (response.status === 401) {
        options.onUnauthorized();
        return null;
    }
    if (response.status === 404) {
        const message = buildSelfRunUnsupportedMessage(apiPath);
        options.onUnsupported(message);
        options.setUnavailable(true);
        return { queued: false, unsupported: true, message };
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(options.buildApiErrorMessage(apiPath, response.status, data?.detail || data?.message, 'self-run 재시도에 실패했습니다.'));
    }

    options.setUnavailable(false);
    options.onSuccess(data?.message || 'self-run 재시도를 큐에 등록했습니다.');
    return data;
}

export async function normalizeWorkspaceSelfRunRequest(options: {
    apiBaseUrl: string;
    token: string;
    approvalId?: string | null;
    cleanupOnly: boolean;
    fetchImpl?: typeof fetch;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    onUnauthorized: () => void;
    onUnsupported: (message: string) => void;
    onSuccess: (message: string) => void;
    onWarning: (message: string) => void;
    setUnavailable: (nextValue: boolean) => void;
}) {
    const fetcher = options.fetchImpl || fetch;
    const apiPath = '/api/admin/workspace-self-run-record/normalize';
    const response = await fetcher(`${options.apiBaseUrl}${apiPath}`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            approval_id: options.approvalId || null,
            cleanup_only: options.cleanupOnly,
        }),
    });

    if (response.status === 401) {
        options.onUnauthorized();
        return null;
    }
    if (response.status === 404) {
        const message = buildSelfRunUnsupportedMessage(apiPath);
        options.onUnsupported(message);
        options.setUnavailable(true);
        return { normalized: false, action: 'unsupported', message };
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(options.buildApiErrorMessage(apiPath, response.status, data?.detail || data?.message, 'self-run 정상화에 실패했습니다.'));
    }

    if (data?.action === 'blocked') {
        options.setUnavailable(false);
        options.onWarning(data?.message || 'self-run 정상화 재실행이 승인 게이트에 의해 차단되었습니다.');
        return data;
    }

    options.setUnavailable(false);
    options.onSuccess(data?.message || 'self-run 정상화를 수행했습니다.');
    return data;
}

export async function approveWorkspaceSelfRunRequest(options: {
    apiBaseUrl: string;
    token: string;
    approvalId: string;
    fetchImpl?: typeof fetch;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    onUnauthorized: () => void;
    onUnsupported: (message: string) => void;
    onSuccess: (message: string) => void;
    setUnavailable: (nextValue: boolean) => void;
}) {
    const fetcher = options.fetchImpl || fetch;
    const apiPath = '/api/admin/workspace-self-run/approve';
    const response = await fetcher(`${options.apiBaseUrl}${apiPath}`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ approval_id: options.approvalId }),
    });

    if (response.status === 401 || response.status === 403) {
        options.onUnauthorized();
        return null;
    }
    if (response.status === 404) {
        const message = buildSelfRunUnsupportedMessage(apiPath);
        options.onUnsupported(message);
        options.setUnavailable(true);
        return { applied: false, unsupported: true, message };
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(options.buildApiErrorMessage(apiPath, response.status, data?.detail || data?.message, 'self-run 승인 반영에 실패했습니다.'));
    }

    options.setUnavailable(false);
    options.onSuccess(data?.message || 'self-run 승인 반영을 완료했습니다.');
    return data;
}
