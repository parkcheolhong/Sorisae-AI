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

export async function GET() {
    const validatorBaseUrl = resolveValidatorBaseUrl();

    try {
        const response = await fetch(`${validatorBaseUrl}/metrics`, {
            cache: 'no-store',
            signal: AbortSignal.timeout(20_000),
        });

        const text = await response.text();
        if (isHtmlLike(response.headers.get('content-type'), text)) {
            return NextResponse.json(
                {
                    detail: 'Prometheus 메트릭 프록시가 HTML 응답을 받았습니다.',
                    code: 'MARKETPLACE_METRICS_PROMETHEUS_HTML_RESPONSE',
                    backend: validatorBaseUrl,
                },
                { status: 502, headers: { 'Cache-Control': 'no-store' } },
            );
        }

        return new NextResponse(text, {
            status: response.status,
            headers: {
                'Cache-Control': 'no-store',
                'Content-Type': response.headers.get('content-type') || 'text/plain; charset=utf-8',
            },
        });
    } catch (error) {
        return NextResponse.json(
            {
                detail: error instanceof Error ? error.message : 'Prometheus 메트릭 요청에 실패했습니다.',
                code: 'MARKETPLACE_METRICS_PROMETHEUS_FETCH_FAILED',
                backend: validatorBaseUrl,
            },
            { status: 502, headers: { 'Cache-Control': 'no-store' } },
        );
    }
}
