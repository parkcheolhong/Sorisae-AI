import { NextRequest, NextResponse } from 'next/server';
import { ADMIN_PROXY_TIMEOUT_MS } from '@/lib/admin-session';

const RETRYABLE_STATUSES = new Set([502, 503, 504]);
const RETRY_ATTEMPTS_PER_TARGET = 2;
const RETRY_DELAY_MS = 400;
const STATUS_WITHOUT_RESPONSE_BODY = new Set([204, 205, 304]);

function resolveTimeoutMs(raw: unknown, fallbackMs: number, minMs: number, maxMs: number): number {
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
        return fallbackMs;
    }
    return Math.min(maxMs, Math.max(minMs, Math.round(parsed)));
}

const DEFAULT_PROXY_TIMEOUT_MS = resolveTimeoutMs(
    process.env.BACKEND_PROXY_TIMEOUT_MS,
    Math.max(30_000, ADMIN_PROXY_TIMEOUT_MS),
    5_000,
    600_000,
);

const ORCHESTRATOR_CHAT_PROXY_TIMEOUT_MS = resolveTimeoutMs(
    process.env.ORCHESTRATOR_CHAT_PROXY_TIMEOUT_MS,
    300_000,
    30_000,
    900_000,
);

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

export function isAbortLike(error: unknown): boolean {
    return error instanceof Error && /abort|timeout/i.test(`${error.name} ${error.message}`);
}

function isHtmlLike(contentType: string | null, bodyText: string): boolean {
    const normalizedType = String(contentType || '').toLowerCase();
    const normalizedBody = String(bodyText || '').trim().toLowerCase();
    return normalizedType.includes('text/html') || normalizedBody.startsWith('<!doctype html') || normalizedBody.startsWith('<html');
}

function parseJsonSafely(text: string) {
    try {
        return text ? JSON.parse(text) : null;
    } catch {
        return null;
    }
}

export function jsonNoStore(payload: unknown, status: number) {
    if (STATUS_WITHOUT_RESPONSE_BODY.has(status)) {
        return new NextResponse(null, {
            status,
            headers: {
                'Cache-Control': 'no-store',
            },
        });
    }

    return NextResponse.json(payload, {
        status,
        headers: {
            'Cache-Control': 'no-store',
        },
    });
}

function isContainerLikeRuntime(): boolean {
    const markerValues = [
        process.env.DOCKER,
        process.env.CONTAINER,
        process.env.KUBERNETES_SERVICE_HOST,
    ]
        .map((value) => String(value || '').trim().toLowerCase())
        .filter(Boolean);

    if (markerValues.some((value) => ['1', 'true', 'yes'].includes(value))) {
        return true;
    }

    // If internal docker service host is configured, avoid localhost fallback.
    const internalHints = [
        process.env.BACKEND_PROXY_TARGET,
        process.env.LOCAL_API_BASE_URL,
    ]
        .map((value) => String(value || '').trim().toLowerCase())
        .filter(Boolean);

    return internalHints.some((value) => value.includes('backend:') || value.includes('host.docker.internal'));
}

function isLocalhostTarget(value: string): boolean {
    return /https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(value);
}

export function collectBackendTargets(): string[] {
    const rawTargets = [
        process.env.BACKEND_PROXY_TARGET,
        process.env.LOCAL_API_BASE_URL,
        'http://backend:8000',
        'http://host.docker.internal:8000',
        process.env.NEXT_PUBLIC_API_URL,
        ...(isContainerLikeRuntime() ? [] : ['http://localhost:8000']),
    ];
    const normalized = rawTargets
        .map((value) => String(value || '').trim())
        .filter(Boolean)
        .map((value) => value.replace(/\/$/, ''));
    const uniqueTargets = [...new Set(normalized)];
    const allowLocalhostFallback = !isContainerLikeRuntime();

    // In containerized runtime, localhost usually points to frontend-admin itself.
    const internalTargets = uniqueTargets.filter((value) => {
        const lowered = value.toLowerCase();
        return lowered.includes('backend:8000') || lowered.includes('host.docker.internal:8000');
    });
    const nonLocalTargets = uniqueTargets.filter((value) => !isLocalhostTarget(value));
    const localhostTargets = allowLocalhostFallback
        ? uniqueTargets.filter((value) => isLocalhostTarget(value))
        : [];

    return [...new Set([...internalTargets, ...nonLocalTargets, ...localhostTargets])];
}

export type BackendFetchResult = {
    target: string;
    response: Response;
    bodyText: string;
    parsedBody: any;
    invalidHtml: boolean;
};

function resolveProxyTimeoutForPath(path: string, timeoutOverrideMs?: number): number {
    if (typeof timeoutOverrideMs === 'number' && Number.isFinite(timeoutOverrideMs) && timeoutOverrideMs > 0) {
        return Math.round(timeoutOverrideMs);
    }

    if (path.startsWith('/api/llm/orchestrate/chat')) {
        return ORCHESTRATOR_CHAT_PROXY_TIMEOUT_MS;
    }

    return DEFAULT_PROXY_TIMEOUT_MS;
}

export async function fetchBackendWithFallback(path: string, init: RequestInit, timeoutMs: number): Promise<BackendFetchResult> {
    const targets = collectBackendTargets();
    let lastError: unknown = null;
    let lastTarget = targets[0] || 'http://backend:8000';

    for (const target of targets) {
        lastTarget = target;
        const requestUrl = `${target}${path}`;

        for (let attempt = 1; attempt <= RETRY_ATTEMPTS_PER_TARGET; attempt += 1) {
            try {
                const response = await fetch(requestUrl, {
                    ...init,
                    cache: 'no-store',
                    signal: AbortSignal.timeout(timeoutMs),
                });
                const bodyText = await response.text();
                const invalidHtml = isHtmlLike(response.headers.get('content-type'), bodyText);
                const parsedBody = parseJsonSafely(bodyText);

                if (invalidHtml) {
                    if (attempt < RETRY_ATTEMPTS_PER_TARGET) {
                        await sleep(RETRY_DELAY_MS * attempt);
                    }
                    continue;
                }

                if (RETRYABLE_STATUSES.has(response.status) && attempt < RETRY_ATTEMPTS_PER_TARGET) {
                    await sleep(RETRY_DELAY_MS * attempt);
                    continue;
                }

                return {
                    target,
                    response,
                    bodyText,
                    parsedBody,
                    invalidHtml,
                };
            } catch (error) {
                lastError = error;
                if (attempt < RETRY_ATTEMPTS_PER_TARGET) {
                    await sleep(RETRY_DELAY_MS * attempt);
                    continue;
                }
                break;
            }
        }
    }

    throw { target: lastTarget, error: lastError };
}

function buildForwardHeaders(req: NextRequest) {
    const headers = new Headers();
    req.headers.forEach((value, key) => {
        const normalized = key.toLowerCase();
        if (normalized === 'host' || normalized === 'connection' || normalized === 'content-length') {
            return;
        }
        headers.set(key, value);
    });
    return headers;
}

type ProxyRequestOptions = {
    requireAuth?: boolean;
    label?: string;
    timeoutMs?: number;
};

export async function proxyBackendRequest(req: NextRequest, backendPathWithQuery: string, options: ProxyRequestOptions = {}) {
    const label = options.label || '백엔드 프록시';
    const auth = req.headers.get('authorization') || '';
    if (options.requireAuth && !auth.trim()) {
        return jsonNoStore({ detail: 'Authorization 헤더가 필요합니다.' }, 401);
    }

    const method = req.method.toUpperCase();
    const timeoutMs = resolveProxyTimeoutForPath(backendPathWithQuery, options.timeoutMs);
    const headers = buildForwardHeaders(req);
    const body = method === 'GET' || method === 'HEAD' ? undefined : await req.text();

    try {
        const { target, response, bodyText, parsedBody } = await fetchBackendWithFallback(backendPathWithQuery, {
            method,
            headers,
            body,
        }, timeoutMs);

        if (STATUS_WITHOUT_RESPONSE_BODY.has(response.status)) {
            return new NextResponse(null, {
                status: response.status,
                headers: {
                    'Cache-Control': 'no-store',
                    'X-Backend-Target': target,
                },
            });
        }

        const contentType = response.headers.get('content-type') || '';
        if (contentType.toLowerCase().includes('application/json')) {
            return jsonNoStore(parsedBody ?? (bodyText ? { detail: bodyText } : null), response.status);
        }

        return new NextResponse(bodyText, {
            status: response.status,
            headers: {
                'Cache-Control': 'no-store',
                ...(contentType ? { 'Content-Type': contentType } : {}),
                'X-Backend-Target': target,
            },
        });
    } catch (wrappedError: any) {
        const target = String(wrappedError?.target || collectBackendTargets()[0] || 'http://backend:8000');
        const error = wrappedError?.error ?? wrappedError;
        return jsonNoStore(
            {
                detail: isAbortLike(error)
                    ? `${label} upstream timeout (${Math.round(timeoutMs / 1000)}초, target=${target}${backendPathWithQuery})`
                    : `${label} 연결 실패 (target=${target}${backendPathWithQuery}): ${error?.message || String(error || 'unknown')}`,
                error: isAbortLike(error)
                    ? `${label} 응답이 ${Math.round(timeoutMs / 1000)}초 안에 오지 않았습니다.`
                    : `${label} 연결 실패: ${error?.message || String(error || 'unknown')}`,
                backend: target,
            },
            isAbortLike(error) ? 504 : 502,
        );
    }
}