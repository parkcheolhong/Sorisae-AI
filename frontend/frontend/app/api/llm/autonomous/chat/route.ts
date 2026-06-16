import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
    return proxyBackendRequest(req, '/api/llm/autonomous/chat', {
        label: '멀티 에이전트 자율 오케스트레이터',
        requireAuth: true,
        timeoutMs: 300_000,
    });
}
