import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
    return proxyBackendRequest(req, '/api/llm/orchestrate/chat', {
        label: '오케스트레이션 채팅',
        requireAuth: true,
        timeoutMs: 300_000,
    });
}
