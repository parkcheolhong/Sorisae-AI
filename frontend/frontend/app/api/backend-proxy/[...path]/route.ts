import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

type RouteContext = {
    params: Promise<{
        path: string[];
    }>;
};

export const dynamic = 'force-dynamic';

async function handle(req: NextRequest, context: RouteContext) {
    const { path } = await context.params;
    const search = req.nextUrl.search || '';
    const backendPath = `/api/${path.join('/')}${search}`;
    return proxyBackendRequest(req, backendPath, { label: '백엔드 API 프록시' });
}

export async function GET(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}

export async function POST(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}

export async function PUT(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}

export async function PATCH(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}

export async function DELETE(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}

export async function OPTIONS(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}

export async function HEAD(req: NextRequest, context: RouteContext) {
    return handle(req, context);
}