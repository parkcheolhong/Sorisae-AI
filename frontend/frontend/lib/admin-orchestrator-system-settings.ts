interface AdminSystemSettingFieldLike {
    key: string;
    value: string;
}

interface AdminSystemSettingSectionLike {
    id: string;
    fields: AdminSystemSettingFieldLike[];
}

interface AdminSystemSettingsResponseLike {
    sections: AdminSystemSettingSectionLike[];
}

export function normalizeOrchestratorSystemSettings<T extends AdminSystemSettingsResponseLike>(options: {
    settings: T;
    sectionIds: string[];
    previousOpen?: Record<string, boolean>;
}) {
    const filteredSections = options.settings.sections.filter((section) => options.sectionIds.includes(section.id));
    const draft = filteredSections.reduce<Record<string, string>>((acc, section) => {
        for (const field of section.fields) {
            acc[field.key] = field.value ?? '';
        }
        return acc;
    }, {});
    const openState = filteredSections.reduce<Record<string, boolean>>((acc, section) => {
        acc[section.id] = options.previousOpen?.[section.id] ?? false;
        return acc;
    }, {});

    return {
        settings: {
            ...options.settings,
            sections: filteredSections,
        } as T,
        draft,
        openState,
    };
}

export async function loadOrchestratorSystemSettingsBundle<T extends AdminSystemSettingsResponseLike>(options: {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    sectionIds: string[];
    previousOpen?: Record<string, boolean>;
}) {
    const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/system-settings`);
    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
        const detail = (data as any)?.detail || (data as any)?.error || `설정 조회 실패(${response.status})`;
        throw new Error(detail);
    }

    return normalizeOrchestratorSystemSettings({
        settings: data as T,
        sectionIds: options.sectionIds,
        previousOpen: options.previousOpen,
    });
}

export async function saveOrchestratorSystemSettingsBundle<T extends AdminSystemSettingsResponseLike>(options: {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    sectionIds: string[];
    values: Record<string, string>;
}) {
    const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/system-settings`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ values: options.values }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
        const detail = (data as any)?.detail || (data as any)?.error || `설정 저장 실패(${response.status})`;
        throw new Error(detail);
    }

    return normalizeOrchestratorSystemSettings({
        settings: data as T,
        sectionIds: options.sectionIds,
    });
}
