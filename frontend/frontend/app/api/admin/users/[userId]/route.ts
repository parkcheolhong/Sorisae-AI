import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

type RouteContext = {
    params: Promise<{
        userId: string;
    }>;
};

async function proxyToBackend(req: NextRequest, userId: string, method: 'PUT' | 'DELETE') {
    const url = `/api/admin/users/${encodeURIComponent(userId)}`;
    return proxyBackendRequest(req, url, {
        label: `관리자 사용자 ${method}`,
        requireAuth: true,
    });
}

export async function PUT(req: NextRequest, context: RouteContext) {
    const { userId } = await context.params;
    return proxyToBackend(req, userId, 'PUT');
}

export async function DELETE(req: NextRequest, context: RouteContext) {
    const { userId } = await context.params;
    return proxyToBackend(req, userId, 'DELETE');
}
