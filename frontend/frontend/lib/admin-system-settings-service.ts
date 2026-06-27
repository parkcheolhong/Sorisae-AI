export interface AdminPasswordChangeResponse {
    changed: boolean;
    message: string;
    username?: string;
    email?: string;
}

export interface AdminPostgresPasswordUpdateResponse {
    changed: boolean;
    message: string;
    env_path?: string;
    secret_host_path?: string;
    postgres_user?: string;
    postgres_host?: string;
    postgres_db?: string;
}

export interface AdminSystemSettingField {
    key: string;
    label: string;
    value: string;
    effective_value?: string;
    needs_attention?: boolean;
    sensitive: boolean;
    multiline: boolean;
}

export interface AdminSystemSettingSection {
    id: string;
    title: string;
    usage: string;
    description: string;
    fields: AdminSystemSettingField[];
}

export interface AdminSystemSettingStatusSection {
    id: string;
    title: string;
    usage: string;
    description: string;
}

export interface AdminSystemSettingsSummary {
    admin_domain: string;
    api_domain: string;
    local_api_base_url: string;
    local_api_base_url_warning?: string;
    api_docs_url?: string;
    marketplace_host_root: string;
    marketplace_upload_root: string;
    nginx_http_port: string;
    nginx_https_port: string;
    selected_profile: string;
    code_generation_strategy: string;
    min_files?: number;
    min_dirs?: number;
    stage11_min_files?: number;
    stage11_min_dirs?: number;
    default_model: string;
    chat_model: string;
    voice_chat_model: string;
    reasoning_model: string;
    coding_model: string;
    available_model_count: number;
    available_models: string[];
    generator_profiles: Array<{
        id: string;
        label: string;
        generator: string;
        runtime_role: string;
    }>;
}

export interface AdminSystemSettingsIntegrationCheckItem {
    id: string;
    label: string;
    ok: boolean;
    url: string;
    detail: string;
}

export interface AdminSystemSettingsIntegrationChecks {
    items: AdminSystemSettingsIntegrationCheckItem[];
    connected_count: number;
    total_count: number;
    all_connected: boolean;
}

export interface AdminSystemSettingsResponse {
    env_path: string;
    runtime_config_path: string;
    sections: AdminSystemSettingSection[];
    summary: AdminSystemSettingsSummary;
    integration_checks?: AdminSystemSettingsIntegrationChecks;
    recommended_env_updates?: Record<string, string>;
    empty_field_count?: number;
    applied_env_update_count?: number;
}

export interface AdminIdentityProviderSettings {
    provider: string;
    env_keys: Record<string, string>;
    callback_url: string;
    guides: Record<string, string>;
    complete_payload_contracts: Array<{
        provider: string;
        required_fields: string[];
        optional_fields: string[];
        callback_fields: string[];
    }>;
    provider_statuses: Array<{
        provider: string;
        endpoint: string;
        callback_url: string;
        endpoint_configured: boolean;
        client_id_configured: boolean;
        client_secret_configured: boolean;
        callback_configured: boolean;
        request_mapping_ready: boolean;
        complete_mapping_ready: boolean;
        complete_payload_fields: string[];
        request_payload_fields: string[];
        env_keys?: string[];
    }>;
}

export interface AdminGlobalAutomaticModeResponse {
    applied_at: string;
    message: string;
    restart_required: boolean;
    env_path: string;
    runtime_config_path: string;
    updated_env_values: Record<string, string>;
    runtime_summary: {
        selected_profile: string;
        code_generation_strategy: string;
        model_tuning_level: number;
        token_tuning_level: number;
        timeout_tuning_level: number;
        min_files: number;
        min_dirs: number;
        allow_synthetic_fallback: boolean;
        force_complete: boolean;
    };
}

function isUnauthorized(status: number) {
    return status === 401 || status === 403;
}

function isRetryableStatus(status: number) {
    return status === 502 || status === 503 || status === 504;
}

function joinApiUrl(baseUrl: string, path: string) {
    return `${baseUrl.replace(/\/$/, '')}${path}`;
}

function isDirectLocalBackendUrl(value: string | undefined | null) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized.startsWith('http://localhost:8000') || normalized.startsWith('http://127.0.0.1:8000');
}

function buildAdminApiBaseUrlCandidates(apiBaseUrl: string) {
    const candidates: string[] = [];
    const push = (value: string | undefined | null) => {
        const normalized = String(value || '').trim().replace(/\/$/, '');
        if (!normalized) {
            return;
        }
        if (candidates.indexOf(normalized) >= 0) {
            return;
        }
        candidates.push(normalized);
    };

    push(apiBaseUrl);

    if (typeof window !== 'undefined') {
        push(window.location.origin);
        const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;
        if (!isDirectLocalBackendUrl(configuredApiUrl)) {
            push(configuredApiUrl);
        }
    } else {
        push(process.env.NEXT_PUBLIC_API_URL);
    }

    return candidates;
}

async function fetchAdminJsonWithAutoFallback<T>(options: {
    apiBaseUrl: string;
    path: string;
    init?: RequestInit;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const attempts = buildAdminApiBaseUrlCandidates(options.apiBaseUrl);
    let lastResponse: Response | null = null;
    let lastPayload: any = null;
    let lastError: Error | null = null;

    for (const baseUrl of attempts) {
        try {
            const response = await fetcher(joinApiUrl(baseUrl, options.path), options.init);
            if (isUnauthorized(response.status)) {
                throw new Error('__ADMIN_SYSTEM_UNAUTHORIZED__');
            }

            const data = await response.json().catch(() => null);
            if (response.ok && data) {
                return data as T;
            }

            lastResponse = response;
            lastPayload = data;
            if (!isRetryableStatus(response.status)) {
                break;
            }
        } catch (error: any) {
            if (error?.message === '__ADMIN_SYSTEM_UNAUTHORIZED__') {
                throw error;
            }
            lastError = error instanceof Error ? error : new Error(String(error || '관리자 시스템 설정 요청 실패'));
        }
    }

    const detail = lastPayload?.detail || lastPayload?.error;
    if (detail) {
        throw new Error(detail);
    }
    if (lastResponse) {
        throw new Error(`설정 조회 실패(${lastResponse.status})`);
    }
    throw new Error(lastError?.message || '관리자 시스템 설정 요청 실패');
}

export function buildSystemSettingsDraft(settings: AdminSystemSettingsResponse) {
    return settings.sections.reduce<Record<string, string>>((acc, section) => {
        for (const field of section.fields) {
            acc[field.key] = field.value ?? '';
        }
        return acc;
    }, {});
}

export function buildSystemSettingsOpenState(settings: AdminSystemSettingsResponse, previous: Record<string, boolean>) {
    const nextOpen: Record<string, boolean> = {};
    settings.sections.forEach((section) => {
        nextOpen[section.id] = previous[section.id] ?? false;
    });
    return nextOpen;
}

export async function loadAdminSystemSettings(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    return fetchAdminJsonWithAutoFallback<AdminSystemSettingsResponse>({
        apiBaseUrl: options.apiBaseUrl,
        path: '/api/admin/system-settings',
        init: {
            headers: { Authorization: `Bearer ${options.token}` },
        },
        fetchImpl: options.fetchImpl,
    });
}

export async function saveAdminSystemSettings(options: {
    apiBaseUrl: string;
    token: string;
    values: Record<string, string>;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/system-settings`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ values: options.values }),
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SYSTEM_UNAUTHORIZED__');
    }

    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
        throw new Error((data as any)?.detail || `설정 저장 실패(${response.status})`);
    }

    return data as AdminSystemSettingsResponse;
}

export async function fillAdminSystemSettingsMissingDefaults(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/system-settings/fill-missing-defaults`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SYSTEM_UNAUTHORIZED__');
    }

    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
        throw new Error((data as any)?.detail || `빈 값 보강 실패(${response.status})`);
    }

    return data as AdminSystemSettingsResponse;
}

export async function applyAdminGlobalAutomaticMode(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/system-settings/global-automatic-mode`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SYSTEM_UNAUTHORIZED__');
    }

    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
        throw new Error((data as any)?.detail || `전역 자동 전환 실패(${response.status})`);
    }

    return data as AdminGlobalAutomaticModeResponse;
}

export async function loadAdminIdentityProviderSettings(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    return fetchAdminJsonWithAutoFallback<AdminIdentityProviderSettings>({
        apiBaseUrl: options.apiBaseUrl,
        path: '/api/admin/identity-provider-settings',
        init: {
            headers: { Authorization: `Bearer ${options.token}` },
        },
        fetchImpl: options.fetchImpl,
    });
}

export async function changeAdminAccountPassword(options: {
    apiBaseUrl: string;
    token: string;
    currentPassword: string;
    newPassword: string;
    confirmPassword: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/account/password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${options.token}`,
        },
        body: JSON.stringify({
            current_password: options.currentPassword,
            new_password: options.newPassword,
            confirm_password: options.confirmPassword,
        }),
    });
    const data = await response.json().catch(() => null) as AdminPasswordChangeResponse | null;
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SYSTEM_UNAUTHORIZED__');
    }
    if (!response.ok) {
        const detail = (data as any)?.detail || data?.message || '관리자 비밀번호 변경에 실패했습니다.';
        throw new Error(detail);
    }
    return data;
}

export async function updateAdminPostgresRuntimePassword(options: {
    apiBaseUrl: string;
    token: string;
    newPassword: string;
    confirmPassword: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/system-settings/postgres-password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${options.token}`,
        },
        body: JSON.stringify({
            new_password: options.newPassword,
            confirm_password: options.confirmPassword,
        }),
    });
    const data = await response.json().catch(() => null) as AdminPostgresPasswordUpdateResponse | null;
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_SYSTEM_UNAUTHORIZED__');
    }
    if (!response.ok) {
        throw new Error((data as any)?.detail || data?.message || 'PostgreSQL 런타임 비밀번호 저장에 실패했습니다.');
    }
    return data;
}

export function assertAdminSystemSettingsServiceContract() {
    const sample = buildSystemSettingsDraft({
        env_path: '',
        runtime_config_path: '',
        sections: [],
        summary: {
            admin_domain: '',
            api_domain: '',
            local_api_base_url: '',
            marketplace_host_root: '',
            marketplace_upload_root: '',
            nginx_http_port: '',
            nginx_https_port: '',
            selected_profile: '',
            code_generation_strategy: '',
            default_model: '',
            chat_model: '',
            voice_chat_model: '',
            reasoning_model: '',
            coding_model: '',
            available_model_count: 0,
            available_models: [],
            generator_profiles: [],
        },
    });
    if (typeof sample !== 'object' || Array.isArray(sample)) {
        throw new Error('admin system settings service contract 누락: draft builder object 반환 필요');
    }
}
