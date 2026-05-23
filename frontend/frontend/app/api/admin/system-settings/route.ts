import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export async function GET(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/system-settings', {
        label: '오케스트레이터 전역 설정',
        requireAuth: true,
        timeoutMs: 60_000,
    });
}

export async function PUT(req: NextRequest) {
    return proxyBackendRequest(req, '/api/admin/system-settings', {
        label: '오케스트레이터 전역 설정',
        requireAuth: true,
        timeoutMs: 60_000,
    });
}