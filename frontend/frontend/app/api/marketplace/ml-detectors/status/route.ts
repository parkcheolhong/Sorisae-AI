import { NextResponse } from 'next/server';

const EXTERNAL_BACKEND_CANDIDATES = [
    process.env.MARKETPLACE_VALIDATOR_BASE_URL,
    process.env.MULTI_PROGRAM_VALIDATOR_BASE_URL,
    process.env.BACKEND_PROXY_TARGET,
    process.env.NEXT_PUBLIC_API_URL,
    process.env.LOCAL_API_BASE_URL,
].filter((value): value is string => Boolean(value && value.trim()));

function isLocalBackendUrl(value: string): boolean {
    try {
        const url = new URL(value);
        const host = url.hostname.toLowerCase();
        return host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0';
    } catch {
        const normalized = value.toLowerCase();
        return normalized.includes('localhost') || normalized.includes('127.0.0.1') || normalized.includes('0.0.0.0');
    }
}

function resolveExternalBackendBaseUrl(): string | null {
    const candidate = EXTERNAL_BACKEND_CANDIDATES.find((value) => !isLocalBackendUrl(value));
    return candidate ?? null;
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

export async function GET() {
    const backendBaseUrl = resolveExternalBackendBaseUrl();

    if (!backendBaseUrl) {
        return NextResponse.json(
            {
                detail: '외부 ML 검출기 백엔드 URL이 설정되지 않았습니다. localhost 폴백은 차단되었습니다.',
                code: 'MARKETPLACE_ML_STATUS_EXTERNAL_BACKEND_REQUIRED',
                backend: null,
            },
            { status: 503, headers: { 'Cache-Control': 'no-store' } },
        );
    }

    try {
        const response = await fetch(`${backendBaseUrl}/api/marketplace/ml-detectors/status`, {
            cache: 'no-store',
            signal: AbortSignal.timeout(20_000),
        });
        const text = await response.text();
        const contentType = response.headers.get('content-type');

        if (isHtmlLike(contentType, text)) {
            return NextResponse.json(
                {
                    detail: 'ML 검출기 상태 프록시가 HTML 응답을 받았습니다.',
                    code: 'MARKETPLACE_ML_STATUS_HTML_RESPONSE',
                    backend: backendBaseUrl,
                },
                { status: 502, headers: { 'Cache-Control': 'no-store' } },
            );
        }

        const parsed = parseJsonSafely(text);
        if (parsed !== null) {
            return NextResponse.json(parsed, {
                status: response.status,
                headers: { 'Cache-Control': 'no-store' },
            });
        }

        return NextResponse.json(
            {
                detail: text || 'ML 검출기 상태 응답을 해석하지 못했습니다.',
                code: 'MARKETPLACE_ML_STATUS_NON_JSON_RESPONSE',
                backend: backendBaseUrl,
            },
            { status: response.ok ? 502 : response.status, headers: { 'Cache-Control': 'no-store' } },
        );
    } catch (error) {
        return NextResponse.json(
            {
                detail: error instanceof Error ? error.message : 'ML 검출기 상태 요청에 실패했습니다.',
                code: 'MARKETPLACE_ML_STATUS_FETCH_FAILED',
                backend: backendBaseUrl,
            },
            { status: 502, headers: { 'Cache-Control': 'no-store' } },
        );
    }
}
