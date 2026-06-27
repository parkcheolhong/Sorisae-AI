import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export const dynamic = 'force-dynamic';

export async function GET(
    req: NextRequest,
    context: { params: Promise<{ sessionId: string }> },
) {
    const { sessionId } = await context.params;
    return proxyBackendRequest(req, `/api/llm/autonomous/session/${encodeURIComponent(sessionId)}`, {
        label: '멀티 에이전트 자율 세션',
        requireAuth: true,
    });
}
