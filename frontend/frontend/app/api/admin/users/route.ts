import { NextRequest } from 'next/server';
import { proxyBackendRequest } from '@/app/api/_shared/backend-proxy';

export async function GET(req: NextRequest) {
  return proxyBackendRequest(req, `/api/admin/users${req.nextUrl.search}`, {
    label: '관리자 사용자 목록',
    requireAuth: true,
  });
}
