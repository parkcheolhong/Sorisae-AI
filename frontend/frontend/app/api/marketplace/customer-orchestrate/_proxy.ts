import { NextResponse } from 'next/server';
import { ADMIN_PROXY_TIMEOUT_MS } from '@/lib/admin-session';

const RETRYABLE_STATUSES = new Set([502, 503, 504]);
const RETRY_ATTEMPTS_PER_TARGET = 2;
const RETRY_DELAY_MS = 500;

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function isAbortLike(error: unknown): boolean {
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

export function noStoreJson(payload: unknown, status: number) {
    return NextResponse.json(payload, {
        status,
        headers: {
            'Cache-Control': 'no-store',
        },
    });
}

function collectBackendTargets(): string[] {
    const rawTargets = [
        process.env.BACKEND_PROXY_TARGET,
        process.env.LOCAL_API_BASE_URL,
        'http://backend:8000',
        'http://host.docker.internal:8000',
        'http://localhost:8000',
    ];
    const normalized = rawTargets
        .map((value) => String(value || '').trim())
        .filter(Boolean)
        .map((value) => value.replace(/\/$/, ''));
    return [...new Set(normalized)];
}

export type ProxyResult = {
    target: string;
    response: Response;
    bodyText: string;
    parsedBody: any;
    invalidHtml: boolean;
};

export async function fetchWithFallback(path: string, init: RequestInit): Promise<ProxyResult> {
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
                    signal: AbortSignal.timeout(ADMIN_PROXY_TIMEOUT_MS),
                });
                const bodyText = await response.text();
                const parsedBody = parseJsonSafely(bodyText);
                const invalidHtml = isHtmlLike(response.headers.get('content-type'), bodyText);

                if (invalidHtml || RETRYABLE_STATUSES.has(response.status)) {
                    if (attempt < RETRY_ATTEMPTS_PER_TARGET) {
                        await sleep(RETRY_DELAY_MS * attempt);
                        continue;
                    }
                    if (invalidHtml) {
                        continue;
                    }
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
                if (attempt < RETRY_ATTEMPTS_PER_TARGET && isAbortLike(error)) {
                    await sleep(RETRY_DELAY_MS * attempt);
                    continue;
                }
                break;
            }
        }
    }

    throw {
        target: lastTarget,
        error: lastError,
    };
}
