import { NextRequest, NextResponse } from 'next/server';

const TTS_PROXY_TIMEOUT_MS = 30_000;

function resolveBackendBaseUrl(): string {
    return (
        process.env.BACKEND_PROXY_TARGET ??
        process.env.NEXT_PUBLIC_API_URL ??
        process.env.LOCAL_API_BASE_URL ??
        'http://localhost:8000'
    );
}

export async function POST(req: NextRequest) {
    const backendBaseUrl = resolveBackendBaseUrl();
    const requestBody = await req.text();

    try {
        const response = await fetch(`${backendBaseUrl}/api/llm/voice/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: requestBody,
            cache: 'no-store',
            signal: AbortSignal.timeout(TTS_PROXY_TIMEOUT_MS),
        });

        const responseText = await response.text();
        try {
            const payload = responseText ? JSON.parse(responseText) : null;
            return NextResponse.json(payload, {
                status: response.status,
                headers: { 'Cache-Control': 'no-store' },
            });
        } catch {
            return NextResponse.json(
                { detail: responseText || `TTS 프록시 실패 (${response.status})` },
                { status: response.ok ? 502 : response.status },
            );
        }
    } catch (error) {
        return NextResponse.json(
            {
                detail: error instanceof Error ? error.message : 'TTS 프록시 요청에 실패했습니다.',
                code: 'TTS_PROXY_FETCH_FAILED',
            },
            { status: 502 },
        );
    }
}
