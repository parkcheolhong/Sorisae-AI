import { NextRequest } from 'next/server';
import { fetchWithFallback, noStoreJson } from '../../_proxy';

export async function GET(req: NextRequest, context: { params: Promise<{ runId: string }> }) {
    const { runId } = await context.params;
    const authHeader = req.headers.get('authorization') || '';

    try {
        const result = await fetchWithFallback(`/api/marketplace/customer-orchestrate/stage-runs/${encodeURIComponent(runId)}`, {
            method: 'GET',
            headers: {
                ...(authHeader ? { Authorization: authHeader } : {}),
            },
        });

        if (result.invalidHtml) {
            return noStoreJson(
                {
                    detail: 'customer-orchestrate stage-run 조회 프록시가 HTML 응답을 받았습니다.',
                    code: 'CUSTOMER_STAGE_RUN_DETAIL_HTML_RESPONSE',
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
                detail: error?.message || 'customer-orchestrate stage-run 조회 프록시 연결 실패',
                code: 'CUSTOMER_STAGE_RUN_DETAIL_PROXY_FAILED',
                backend: wrapped?.target || null,
            },
            502,
        );
    }
}
