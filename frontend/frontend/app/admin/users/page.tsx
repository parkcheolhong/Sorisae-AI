'use client';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';
import {
  ADMIN_SESSION_CHECK_INTERVAL_MS,
  ADMIN_SESSION_WARNING_WINDOW_MS,
  clearAdminToken,
  extendAdminSessionToken,
  getAdminToken,
  getAdminTokenExpiryMs,
  getRemainingSessionMinutes,
} from '@/lib/admin-session';
import { redirectToAdminLogin } from '@/lib/admin-navigation';

interface User {
  id: number; username: string; email: string;
  is_admin: boolean; is_superuser: boolean; is_active: boolean;
  member_type?: 'individual' | 'sole_proprietor' | 'corporation' | string;
  business_name?: string | null;
  business_registration_number?: string | null;
  representative_name?: string | null;
  created_at: string | null;
}

const memberTypeLabels: Record<string, string> = {
  individual: '개인',
  sole_proprietor: '개인사업자',
  corporation: '법인',
};

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const sessionWarningExpRef = useRef<number | null>(null);

  const token = () => getAdminToken();
  const headers = () => ({ 'Authorization': `Bearer ${token()}`, 'Content-Type': 'application/json' });

  useEffect(() => {
    if (!token()) { redirectToAdminLogin(router); return; }
    fetchWithAdminBootstrapRetry('/api/admin/users', { headers: headers() })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) { setUsers(d.users); setTotal(d.total); } setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      const currentToken = token();
      const expiryMs = getAdminTokenExpiryMs(currentToken);
      if (!currentToken || !expiryMs) {
        return;
      }

      const remainingMs = expiryMs - Date.now();
      if (remainingMs <= 0) {
        clearAdminToken();
        redirectToAdminLogin(router);
        return;
      }

      if (remainingMs > ADMIN_SESSION_WARNING_WINDOW_MS) {
        sessionWarningExpRef.current = null;
        return;
      }

      if (sessionWarningExpRef.current === expiryMs) {
        return;
      }

      sessionWarningExpRef.current = expiryMs;

      const shouldExtend = window.confirm(`관리자 세션이 약 ${getRemainingSessionMinutes(expiryMs)}분 후 만료됩니다. 로그인 시간을 연장할까요?`);
      if (!shouldExtend) {
        return;
      }

      extendAdminSessionToken(currentToken)
        .then(() => {
          sessionWarningExpRef.current = null;
        })
        .catch(() => {
          clearAdminToken();
          redirectToAdminLogin(router);
        });
    }, ADMIN_SESSION_CHECK_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [router]);

  const toggle = async (user: User, field: 'is_admin' | 'is_active') => {
    const body = { [field]: !user[field] };
    const r = await fetch(`/api/admin/users/${user.id}`, {
      method: 'PUT', headers: headers(), body: JSON.stringify(body)
    });
    if (r.ok) {
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, [field]: !u[field] } : u));
      setMsg(`✅ ${user.username} ${field} 변경 완료`);
      setTimeout(() => setMsg(''), 2000);
    }
  };

  const del = async (user: User) => {
    if (!confirm(`${user.username} 삭제?`)) return;
    const r = await fetch(`/api/admin/users/${user.id}`, { method: 'DELETE', headers: headers() });
    if (r.ok) setUsers(prev => prev.filter(u => u.id !== user.id));
  };

  return (
    <div className="min-h-screen bg-[#0d1117] px-6 py-8 text-[#c9d1d9]" data-testid="admin-users-page">
      <div className="mx-auto max-w-[1100px]">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">👥 회원가입 사용자 확인</h1>
            <p className="mt-1 text-sm text-slate-400" data-testid="admin-users-total">전체 {total}명 · 가입 유형/사업자 정보 연결 상태 확인</p>
          </div>
          <Link href="/admin" className="rounded-xl border border-slate-700 bg-slate-700 px-4 py-2 text-sm text-slate-100 transition hover:bg-slate-600">
            ← 대시보드
          </Link>
        </div>
        {msg && <div className="mb-4 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">{msg}</div>}
        {loading ? <p className="text-slate-400">⏳ 로딩 중...</p> : (
          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-[#111827] shadow-[0_0_0_1px_rgba(148,163,184,0.06)]" data-testid="admin-users-table">
            <table className="min-w-[1180px] w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-700/80 bg-[#0f172a]">
                  {['ID', '사용자명', '이메일', '가입 유형', '사업자/법인', '대표자', '관리자', '활성', '슈퍼유저', '가입일', '액션'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-semibold text-slate-300">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className="border-b border-slate-800/80 last:border-b-0 hover:bg-slate-900/50" data-testid={`admin-user-row-${u.id}`}>
                    <td className="px-4 py-3 text-slate-400">{u.id}</td>
                    <td className="px-4 py-3 font-semibold text-slate-100">{u.username}</td>
                    <td className="px-4 py-3 text-slate-300">{u.email}</td>
                    <td className="px-4 py-3 text-slate-300" data-testid={`admin-user-member-type-${u.id}`}>
                      {memberTypeLabels[u.member_type || 'individual'] || u.member_type || '개인'}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      <div className="max-w-[220px] truncate" title={u.business_name || u.business_registration_number || '-'}>
                        {u.business_name || '-'}
                      </div>
                      {u.business_registration_number && <div className="mt-1 text-xs text-slate-500">{u.business_registration_number}</div>}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{u.representative_name || '-'}</td>
                    <td className="px-4 py-3">
                      <span onClick={() => toggle(u, 'is_admin')} className={`cursor-pointer rounded-full px-3 py-1 text-xs font-semibold ${u.is_admin ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                        {u.is_admin ? '✅ Y' : '❌ N'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span onClick={() => toggle(u, 'is_active')} className={`cursor-pointer rounded-full px-3 py-1 text-xs font-semibold ${u.is_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                        {u.is_active ? '✅ Y' : '❌ N'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${u.is_superuser ? 'bg-sky-500/20 text-sky-300' : 'bg-slate-700 text-slate-300'}`}>
                        {u.is_superuser ? '⭐ Y' : 'N'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">{u.created_at?.slice(0, 10) || '-'}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => del(u)} className="rounded-md bg-rose-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-500">삭제</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
