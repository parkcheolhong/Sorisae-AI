import { NextRequest, NextResponse } from 'next/server';

const VOICE_PROXY_TIMEOUT_MS = 60_000;
const VOICE_PROXY_AUTO_APPLY_TIMEOUT_MS = 180_000;

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

export async function POST(req: NextRequest) {
    const backendBaseUrl = resolveBackendBaseUrl();
    const requestBody = await req.text();
    const requestPayload = parseJsonSafely(requestBody) as { auto_apply?: boolean } | null;
    const timeoutMs = requestPayload?.auto_apply ? VOICE_PROXY_AUTO_APPLY_TIMEOUT_MS : VOICE_PROXY_TIMEOUT_MS;

    try {
        const response = await fetch(`${backendBaseUrl}/api/llm/voice/orchestrate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: requestBody,
            cache: 'no-store',
            signal: AbortSignal.timeout(timeoutMs),
        });

        const responseText = await response.text();
        if (isHtmlLike(response.headers.get('content-type'), responseText)) {
            return NextResponse.json(
                {
                    detail: '음성 프록시가 백엔드 대신 HTML 응답을 받았습니다. 백엔드 경로를 확인해주세요.',
                    code: 'VOICE_PROXY_HTML_RESPONSE',
                    backend: backendBaseUrl,
                },
                { status: 502, headers: { 'Cache-Control': 'no-store' } },
            );
        }

        const payload = parseJsonSafely(responseText);
        if (payload !== null) {
            return NextResponse.json(payload, {
                status: response.status,
                headers: { 'Cache-Control': 'no-store' },
            });
        }

        return NextResponse.json(
            {
                detail: responseText || `음성 프록시 요청 실패 (${response.status})`,
                code: 'VOICE_PROXY_NON_JSON_RESPONSE',
                backend: backendBaseUrl,
            },
            { status: response.ok ? 502 : response.status, headers: { 'Cache-Control': 'no-store' } },
        );
    } catch (error) {
        return NextResponse.json(
            {
                detail: error instanceof Error ? error.message : '음성 프록시 요청에 실패했습니다.',
                code: 'VOICE_PROXY_FETCH_FAILED',
                backend: backendBaseUrl,
            },
            { status: 502, headers: { 'Cache-Control': 'no-store' } },
        );
    }
}