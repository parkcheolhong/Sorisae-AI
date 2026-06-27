import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export async function GET(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/worldlinco/tuning', {
        label: 'WorldLinco 튜닝',
        requireAuth: true,
        timeoutMs: 30_000,
    });
}

export async function PUT(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/worldlinco/tuning', {
        label: 'WorldLinco 튜닝',
        requireAuth: true,
        timeoutMs: 30_000,
    });
}
