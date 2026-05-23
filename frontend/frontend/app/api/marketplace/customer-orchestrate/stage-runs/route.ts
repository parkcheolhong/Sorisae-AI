import { NextRequest } from 'next/server';
import { fetchWithFallback, noStoreJson } from '../_proxy';

export async function POST(req: NextRequest) {
    const bodyText = await req.text();
    const authHeader = req.headers.get('authorization') || '';

    try {
        const result = await fetchWithFallback('/api/marketplace/customer-orchestrate/stage-runs', {
            method: 'POST',
            headers: {
                ...(authHeader ? { Authorization: authHeader } : {}),
                'Content-Type': req.headers.get('content-type') || 'application/json',
            },
            body: bodyText,
        });

        if (result.invalidHtml) {
            return noStoreJson(
                {
                    detail: 'customer-orchestrate stage-runs 프록시가 HTML 응답을 받았습니다.',
                    code: 'CUSTOMER_STAGE_RUNS_HTML_RESPONSE',
                    backend: result.target,
                },
                502,
            );
        }

        return noStoreJson(result.parsedBody ?? { detail: result.bodyText || '' }, result.response.status);
    } catch (wrapped: any) {
        const error = wrapped?.error;
        return noStoreJson(
            {
                detail: error?.message || 'customer-orchestrate stage-runs 프록시 연결 실패',
                code: 'CUSTOMER_STAGE_RUNS_PROXY_FAILED',
                backend: wrapped?.target || null,
            },
            502,
        );
    }
}
