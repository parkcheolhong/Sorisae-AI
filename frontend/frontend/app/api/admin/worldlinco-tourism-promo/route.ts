import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export async function GET(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/worldlinco/tourism-promo', {
        label: 'WorldLinco 관광 홍보',
        requireAuth: true,
        timeoutMs: 30_000,
    });
}

export async function PUT(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/worldlinco/tourism-promo', {
        label: 'WorldLinco 관광 홍보',
        requireAuth: true,
        timeoutMs: 30_000,
    });
}
