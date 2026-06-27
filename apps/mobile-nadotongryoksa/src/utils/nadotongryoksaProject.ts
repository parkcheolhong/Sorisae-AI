import {
    matchesWorldLincoProjectFields,
    WORLDLINGO_BRAND_NAME,
} from '../constants/worldlincoBrand';

export type MarketplaceProjectSummary = {
    id: number;
    title?: string | null;
    description?: string | null;
    github_url?: string | null;
    file_key?: string | null;
};

const WORLDLINGO_FALLBACK_PROJECT_ID = 38;

export function pickWorldLincoProjectId(
    projects: MarketplaceProjectSummary[],
    fallbackProjectId = WORLDLINGO_FALLBACK_PROJECT_ID,
): number {
    const match = projects.find((project) => matchesWorldLincoProjectFields([
        project.title,
        project.description,
        project.github_url,
        project.file_key,
    ]));
    return typeof match?.id === 'number' && match.id > 0 ? match.id : fallbackProjectId;
}

let cachedWorldLincoProjectIdPromise: Promise<number> | null = null;

export function resetWorldLincoProjectIdCache(): void {
    cachedWorldLincoProjectIdPromise = null;
}

export async function resolveWorldLincoProjectId(
    apiBaseUrl: string,
    fetchImpl: typeof fetch = fetch,
): Promise<number> {
    if (!cachedWorldLincoProjectIdPromise) {
        cachedWorldLincoProjectIdPromise = (async () => {
            try {
                const response = await fetchImpl(`${apiBaseUrl}/api/marketplace/projects?skip=0&limit=200`);
                if (!response.ok) {
                    return WORLDLINGO_FALLBACK_PROJECT_ID;
                }
                const payload = await response.json().catch(() => null) as
                    | { projects?: MarketplaceProjectSummary[] }
                    | MarketplaceProjectSummary[]
                    | null;
                const projects = Array.isArray(payload)
                    ? payload
                    : Array.isArray(payload?.projects)
                        ? payload.projects
                        : [];
                return pickWorldLincoProjectId(projects);
            } catch {
                return WORLDLINGO_FALLBACK_PROJECT_ID;
            }
        })();
    }
    return cachedWorldLincoProjectIdPromise;
}

/** @deprecated Use resolveWorldLincoProjectId — kept for legacy imports. */
export const pickNadotongryoksaProjectId = pickWorldLincoProjectId;

/** @deprecated Use resetWorldLincoProjectIdCache — kept for legacy imports. */
export const resetNadotongryoksaProjectIdCache = resetWorldLincoProjectIdCache;

/** @deprecated Use resolveWorldLincoProjectId — kept for legacy imports. */
export const resolveNadotongryoksaProjectId = resolveWorldLincoProjectId;

export { WORLDLINGO_BRAND_NAME };
