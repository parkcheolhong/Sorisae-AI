import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export async function GET(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/worldlinco/billing-policy', {
        label: 'WorldLinco 요금 정책',
        requireAuth: true,
        timeoutMs: 30_000,
    });
}

export async function PUT(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/worldlinco/billing-policy', {
        label: 'WorldLinco 요금 정책',
        requireAuth: true,
        timeoutMs: 30_000,
    });
}
