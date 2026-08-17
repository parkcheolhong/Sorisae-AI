import { NextResponse } from 'next/server';

function resolveValidatorBaseUrl(): string {
    return (
        process.env.BACKEND_PROXY_TARGET ??
        process.env.NEXT_PUBLIC_API_URL ??
        process.env.LOCAL_API_BASE_URL ??
        'http://localhost:8000'
    );
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
    const validatorBaseUrl = resolveValidatorBaseUrl();

    try {
        const response = await fetch(`${validatorBaseUrl}/api/metrics/summary`, {
            cache: 'no-store',
            signal: AbortSignal.timeout(20_000),
        });

        const text = await response.text();
        if (isHtmlLike(response.headers.get('content-type'), text)) {
            return NextResponse.json(
                {
                    detail: '메트릭 요약 프록시가 HTML 응답을 받았습니다.',
                    code: 'MARKETPLACE_METRICS_SUMMARY_HTML_RESPONSE',
                    backend: validatorBaseUrl,
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
                detail: text || '메트릭 요약 응답을 해석하지 못했습니다.',
                code: 'MARKETPLACE_METRICS_SUMMARY_NON_JSON_RESPONSE',
                backend: validatorBaseUrl,
            },
            { status: response.ok ? 502 : response.status, headers: { 'Cache-Control': 'no-store' } },
        );
    } catch (error) {
        return NextResponse.json(
            {
                detail: error instanceof Error ? error.message : '메트릭 요약 요청에 실패했습니다.',
                code: 'MARKETPLACE_METRICS_SUMMARY_FETCH_FAILED',
                backend: validatorBaseUrl,
            },
            { status: 502, headers: { 'Cache-Control': 'no-store' } },
        );
    }
}
