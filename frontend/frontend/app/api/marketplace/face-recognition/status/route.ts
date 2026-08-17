import { NextResponse } from 'next/server';

function resolveBackendBaseUrl(): string {
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
    const backendBaseUrl = resolveBackendBaseUrl();
    try {
        const response = await fetch(`${backendBaseUrl}/api/marketplace/face-recognition/status`, {
            cache: 'no-store',
            signal: AbortSignal.timeout(20_000),
        });
        const text = await response.text();
        const contentType = response.headers.get('content-type');

        if (isHtmlLike(contentType, text)) {
            return NextResponse.json(
                {
                    detail: '얼굴 인식 상태 프록시가 HTML 응답을 받았습니다.',
                    code: 'MARKETPLACE_FACE_STATUS_HTML_RESPONSE',
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
                detail: text || '얼굴 인식 상태 응답을 해석하지 못했습니다.',
                code: 'MARKETPLACE_FACE_STATUS_NON_JSON_RESPONSE',
                backend: backendBaseUrl,
            },
            { status: response.ok ? 502 : response.status, headers: { 'Cache-Control': 'no-store' } },
        );
    } catch (error) {
        return NextResponse.json(
            {
                detail: error instanceof Error ? error.message : '얼굴 인식 상태 요청에 실패했습니다.',
                code: 'MARKETPLACE_FACE_STATUS_FETCH_FAILED',
                backend: backendBaseUrl,
            },
            { status: 502, headers: { 'Cache-Control': 'no-store' } },
        );
    }
}