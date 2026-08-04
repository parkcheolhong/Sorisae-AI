'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const DEFAULT_RETURN_TO = '/marketplace';
const ALLOWED_RETURN_TO = new Set([
    '/marketplace',
]);

function sanitizeReturnTo(value: string | null | undefined) {
    const candidate = String(value || '').trim();
    return ALLOWED_RETURN_TO.has(candidate) ? candidate : DEFAULT_RETURN_TO;
}

function parseHashParams() {
    if (typeof window === 'undefined') {
        return new URLSearchParams();
    }
    const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash;
    return new URLSearchParams(hash);
}

export default function SocialAuthCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [message, setMessage] = useState('소셜 로그인 처리를 확인하는 중입니다.');
    const [error, setError] = useState('');

    const returnTo = useMemo(() => sanitizeReturnTo(searchParams.get('return_to')), [searchParams]);

    useEffect(() => {
        const params = parseHashParams();
        const accessToken = String(params.get('access_token') || '').trim();
        const provider = String(params.get('provider') || '').trim();
        const finalReturnTo = sanitizeReturnTo(params.get('return_to') || returnTo);

        if (!accessToken) {
            setError('소셜 로그인 토큰을 받지 못했습니다.');
            setMessage('');
            return;
        }

        try {
            window.localStorage.setItem('customer_token', accessToken);
        } catch {
            setError('소셜 로그인 토큰을 저장하지 못했습니다.');
            setMessage('');
            return;
        }

        window.location.replace(finalReturnTo);
        setMessage(provider ? `${provider} 로그인 완료` : '소셜 로그인 완료');
    }, [returnTo]);

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
            <div className="max-w-md rounded-2xl border border-slate-800 bg-slate-900 px-6 py-8 text-center">
                <h1 className="text-xl font-semibold">소셜 로그인 처리 중</h1>
                {message ? <p className="mt-3 text-sm text-slate-300">{message}</p> : null}
                {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
            </div>
        </div>
    );
}
