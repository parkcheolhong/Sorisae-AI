"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchWithAdminBootstrapRetry } from "@/lib/admin-bootstrap-fetch";
import {
  ADMIN_PROXY_TIMEOUT_MS,
  clearAdminToken,
  setAdminToken,
} from "@/lib/admin-session";

const ADMIN_LOGIN_REMEMBER_ID_KEY = "admin_login_remember_id_v1";
const ADMIN_LOGIN_EMAIL_KEY = "admin_login_email_v1";
const ADMIN_LOGIN_PASSWORD_KEY = "admin_login_password_v1";
const ADMIN_LOGIN_ALLOW_PASSKEY_KEY = "admin_login_allow_passkey_v1";
const ADMIN_LOGIN_REQUEST_TIMEOUT_MS = ADMIN_PROXY_TIMEOUT_MS + 7_000;
const ADMIN_LOGIN_RETRY_COUNT = 1;
const AUTH_PASSKEY_ONLY = String(process.env.NEXT_PUBLIC_AUTH_PASSKEY_ONLY || '').toLowerCase() === 'true';

async function resolveAdminPostLoginPath(
  accessToken: string,
  me?: { is_admin?: boolean; is_superuser?: boolean } | null,
): Promise<string> {
  if (me?.is_admin || me?.is_superuser) {
    return '/admin';
  }
  try {
    const regionalRes = await fetch('/api/admin/worldlinco/regional/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (regionalRes.ok) {
      const regionalMe = await regionalRes.json() as { is_regional_manager?: boolean };
      if (regionalMe.is_regional_manager) {
        return '/admin/regional';
      }
    }
  } catch {
    // ignore regional scope probe failures
  }
  return '/admin';
}

const createTimeoutSignal = (timeoutMs: number) => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timeoutId);
    },
  };
};

export default function AdminLoginPage() {
  const [hydrated, setHydrated] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rememberId, setRememberId] = useState(true);
  const [allowPasskeyOnDevice, setAllowPasskeyOnDevice] = useState(true);
  const [passkeyBusy, setPasskeyBusy] = useState(false);
  const [passkeyReady, setPasskeyReady] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    try {
      const savedRememberId = localStorage.getItem(ADMIN_LOGIN_REMEMBER_ID_KEY);
      const savedAllowPasskey = localStorage.getItem(ADMIN_LOGIN_ALLOW_PASSKEY_KEY);
      const savedEmail = localStorage.getItem(ADMIN_LOGIN_EMAIL_KEY);

      const nextRememberId = savedRememberId !== 'false';
      const nextAllowPasskey = savedAllowPasskey !== 'false';

      setRememberId(nextRememberId);
      setAllowPasskeyOnDevice(nextAllowPasskey);

      if (nextRememberId && savedEmail) {
        setEmail(savedEmail);
      }
      // Immediately block legacy plaintext password persistence.
      localStorage.removeItem(ADMIN_LOGIN_PASSWORD_KEY);
    } catch {
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(ADMIN_LOGIN_REMEMBER_ID_KEY, rememberId ? 'true' : 'false');
      if (rememberId && email.trim()) {
        localStorage.setItem(ADMIN_LOGIN_EMAIL_KEY, email.trim());
      } else {
        localStorage.removeItem(ADMIN_LOGIN_EMAIL_KEY);
      }
    } catch {
    }
  }, [email, rememberId]);

  useEffect(() => {
    try {
      localStorage.setItem(ADMIN_LOGIN_ALLOW_PASSKEY_KEY, allowPasskeyOnDevice ? 'true' : 'false');
    } catch {
    }
  }, [allowPasskeyOnDevice]);

  const resolveEmailInputValue = () => {
    const fromState = email.trim();
    if (fromState) {
      return fromState;
    }
    if (typeof document === 'undefined') {
      return '';
    }
    const el = document.querySelector('[data-testid="admin-login-email"]') as HTMLInputElement | null;
    return String(el?.value || '').trim();
  };

  const resolvePasswordInputValue = () => {
    const fromState = password;
    if (fromState) {
      return fromState;
    }
    if (typeof document === 'undefined') {
      return '';
    }
    const el = document.querySelector('[data-testid="admin-login-password"]') as HTMLInputElement | null;
    return String(el?.value || '');
  };

  useEffect(() => {
    const ready = typeof window !== 'undefined'
      && allowPasskeyOnDevice
      && typeof window.PublicKeyCredential !== 'undefined'
      && !!navigator.credentials;
    setPasskeyReady(Boolean(ready));
  }, [allowPasskeyOnDevice]);

  const encodeBase64Url = (value: string) => {
    const encoded = window.btoa(value);
    return encoded.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  };

  const encodeArrayBuffer = (value: ArrayBuffer | Uint8Array) => {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
    let binary = '';
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return encodeBase64Url(binary);
  };

  const decodeBase64Url = (value: string) => {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
    const decoded = window.atob(padded);
    return Uint8Array.from(decoded, (char) => char.charCodeAt(0));
  };

  const normalizePublicKeyOptions = (options: any) => {
    if (!options || typeof options !== 'object') {
      return null;
    }
    return {
      ...options,
      challenge: decodeBase64Url(String(options.challenge || '')),
      user: options.user ? {
        ...options.user,
        id: decodeBase64Url(String(options.user.id || '')),
      } : undefined,
      excludeCredentials: Array.isArray(options.excludeCredentials)
        ? options.excludeCredentials.map((item: any) => ({
          ...item,
          id: decodeBase64Url(String(item.id || '')),
        }))
        : undefined,
      allowCredentials: Array.isArray(options.allowCredentials)
        ? options.allowCredentials.map((item: any) => ({
          ...item,
          id: decodeBase64Url(String(item.id || '')),
        }))
        : undefined,
    };
  };

  const handlePasskeyLogin = async () => {
    const normalizedEmail = resolveEmailInputValue();
    if (!normalizedEmail) {
      setError('패스키 로그인 전 관리자 이메일을 입력해주세요.');
      return;
    }
    if (!passkeyReady) {
      setError('이 브라우저/기기에서는 패스키 로그인을 사용할 수 없습니다.');
      return;
    }

    const supportsConditionalMediation =
      typeof window.PublicKeyCredential !== 'undefined'
      && typeof PublicKeyCredential.isConditionalMediationAvailable === 'function'
      && await PublicKeyCredential.isConditionalMediationAvailable();

    setPasskeyBusy(true);
    setError('');
    try {
      const startResponse = await fetch('/api/proxy?action=passkey-login-start', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
        body: JSON.stringify({ email: normalizedEmail }),
        cache: 'no-store',
      });
      const startPayload = await startResponse.json().catch(() => null);
      if (!startResponse.ok || !startPayload) {
        throw new Error(startPayload?.detail || '패스키 로그인 시작에 실패했습니다.');
      }

      const baseOptions = normalizePublicKeyOptions(startPayload.options);
      const shouldTryConditionalLogin = supportsConditionalMediation && Array.isArray(baseOptions?.allowCredentials) && baseOptions.allowCredentials.length > 0;
      let credential: PublicKeyCredential | null = null;
      let firstAttemptError: unknown = null;

      const getCredential = async (
        options: any,
        mediation?: CredentialMediationRequirement,
      ): Promise<PublicKeyCredential | null> => {
        return await (mediation
          ? navigator.credentials.get({ mediation, publicKey: options })
          : navigator.credentials.get({ publicKey: options })) as PublicKeyCredential | null;
      };

      try {
        credential = await getCredential(baseOptions);
      } catch (error) {
        firstAttemptError = error;
      }

      if (!credential && shouldTryConditionalLogin) {
        try {
          const { allowCredentials, ...conditionalOptions } = baseOptions || {};
          credential = await getCredential(conditionalOptions, 'conditional');
        } catch (error) {
          if (!firstAttemptError) {
            firstAttemptError = error;
          }
        }
      }

      if (!credential) {
        throw firstAttemptError instanceof Error
          ? firstAttemptError
          : new Error('패스키 로그인 승인 정보가 반환되지 않았습니다.');
      }

      const finishResponse = await fetch('/api/proxy?action=passkey-login-finish', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
        body: JSON.stringify({
          email: normalizedEmail,
          credential: {
            id: credential.id,
            rawId: encodeArrayBuffer(credential.rawId),
            type: credential.type,
            response: credential.response && 'authenticatorData' in credential.response
              ? {
                clientDataJSON: encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).clientDataJSON),
                authenticatorData: encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).authenticatorData),
                signature: encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).signature),
                userHandle: (credential.response as AuthenticatorAssertionResponse).userHandle ? encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).userHandle!) : null,
              }
              : {},
          },
        }),
        cache: 'no-store',
      });
      const finishPayload = await finishResponse.json().catch(() => null);
      if (!finishResponse.ok || !finishPayload?.access_token) {
        throw new Error(finishPayload?.detail || '패스키 로그인 완료에 실패했습니다.');
      }

      setAdminToken(finishPayload.access_token);
      const nextPath = await resolveAdminPostLoginPath(finishPayload.access_token);
      window.location.replace(nextPath);
    } catch (err: any) {
      setError(err?.message || '패스키 로그인 중 오류가 발생했습니다.');
      clearAdminToken();
    } finally {
      setPasskeyBusy(false);
    }
  };

  const handlePasskeyRegister = async () => {
    const normalizedEmail = resolveEmailInputValue();
    if (!normalizedEmail) {
      setError('패스키 등록 전 관리자 이메일을 입력해주세요.');
      return;
    }
    const normalizedPassword = resolvePasswordInputValue();
    if (!normalizedPassword) {
      window.location.href = `/admin/recovery?intent=passkey&email=${encodeURIComponent(normalizedEmail)}`;
      return;
    }
    if (!passkeyReady) {
      setError('이 브라우저/기기에서는 패스키 등록을 사용할 수 없습니다.');
      return;
    }

    setPasskeyBusy(true);
    setError('');
    try {
      const startResponse = await fetch('/api/proxy?action=passkey-register-start', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
        body: JSON.stringify({
          email: normalizedEmail,
          device_label: '이 기기 패스키',
          password: normalizedPassword,
        }),
        cache: 'no-store',
      });
      const startPayload = await startResponse.json().catch(() => null);
      if (!startResponse.ok || !startPayload) {
        throw new Error(startPayload?.detail || '패스키 등록 시작에 실패했습니다.');
      }

      const createdCredential = await navigator.credentials.create({
        publicKey: normalizePublicKeyOptions(startPayload.options),
      }) as PublicKeyCredential | null;

      if (!createdCredential) {
        throw new Error('패스키 등록 결과를 받지 못했습니다.');
      }

      const finishResponse = await fetch('/api/proxy?action=passkey-register-finish', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
        body: JSON.stringify({
          registration_token: startPayload.registration_token,
          credential: {
            id: createdCredential.id,
            rawId: encodeArrayBuffer(createdCredential.rawId),
            type: createdCredential.type,
            response: createdCredential.response && 'attestationObject' in createdCredential.response
              ? {
                clientDataJSON: encodeArrayBuffer((createdCredential.response as AuthenticatorAttestationResponse).clientDataJSON),
                attestationObject: encodeArrayBuffer((createdCredential.response as AuthenticatorAttestationResponse).attestationObject),
              }
              : {},
          },
        }),
        cache: 'no-store',
      });
      const finishPayload = await finishResponse.json().catch(() => null);
      if (!finishResponse.ok || !finishPayload?.registered) {
        throw new Error(finishPayload?.detail || '패스키 등록 완료에 실패했습니다.');
      }

      setError('');
      alert('패스키 등록이 완료되었습니다. 다음부터 지문/패스키 로그인 버튼으로 로그인할 수 있습니다.');
    } catch (err: any) {
      setError(err?.message || '패스키 등록 중 오류가 발생했습니다.');
    } finally {
      setPasskeyBusy(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (AUTH_PASSKEY_ONLY) {
      setError('비밀번호 로그인은 비활성화되었습니다. 지문/패스키 로그인 또는 패스키 등록을 사용해주세요.');
      return;
    }

    const authUrl = "/api/proxy";
    const normalizedEmail = email.trim();
    const normalizedPassword = password;

    if (!normalizedEmail || !normalizedPassword) {
      setError("이메일과 비밀번호를 모두 입력해주세요.");
      return;
    }

    setLoading(true);
    const loginFlowStartedAt = performance.now();
    const loginRequest = createTimeoutSignal(ADMIN_LOGIN_REQUEST_TIMEOUT_MS);

    try {
      const res = await fetchWithAdminBootstrapRetry(authUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "Cache-Control": "no-cache",
          "Pragma": "no-cache",
        },
        cache: "no-store",
        body: new URLSearchParams({ username: normalizedEmail, password: normalizedPassword }),
        signal: loginRequest.signal,
      }, {
        retries: ADMIN_LOGIN_RETRY_COUNT,
        retryDelayMs: 1200,
        timeoutMs: ADMIN_LOGIN_REQUEST_TIMEOUT_MS,
        traceLabel: 'admin-login-post',
        onMetric: (metric) => {
          console.info('[admin-login-metric]', metric);
        },
      });
      console.info('[admin-login-flow]', {
        stage: 'post-response',
        status: res.status,
        elapsedMs: Math.round(performance.now() - loginFlowStartedAt),
      });

      if (!res.ok) {
        const raw = await res.text();
        let detail = "로그인에 실패했습니다.";
        try {
          const parsed = JSON.parse(raw);
          if (typeof parsed?.detail === "string" && parsed.detail.trim().length > 0) {
            detail = parsed.detail;
          }
        } catch {
          if (raw.trim().length > 0) {
            detail = raw;
          }
        }
        setError(detail);
        return;
      }

      const data = await res.json();
      console.info('[admin-login-flow]', {
        stage: 'payload-parsed',
        elapsedMs: Math.round(performance.now() - loginFlowStartedAt),
        hasAccessToken: typeof data?.access_token === 'string' && data.access_token.trim().length > 0,
        hasUser: !!data?.user,
      });
      if (!data || typeof data.access_token !== "string" || !data.access_token.trim()) {
        clearAdminToken();
        setError("로그인 응답 형식이 올바르지 않습니다. 관리자 프록시 상태를 다시 확인해주세요.");
        return;
      }

      try {
        if (rememberId) {
          localStorage.setItem(ADMIN_LOGIN_EMAIL_KEY, normalizedEmail);
        } else {
          localStorage.removeItem(ADMIN_LOGIN_EMAIL_KEY);
        }
        localStorage.removeItem(ADMIN_LOGIN_PASSWORD_KEY);
      } catch {
      }

      setAdminToken(data.access_token);

      const me = data.user;
      if (!me || (typeof me !== 'object')) {
        setError("관리자 정보 응답 형식이 올바르지 않습니다. 프록시와 백엔드 상태를 확인해주세요.");
        clearAdminToken();
        return;
      }

      if (!me.is_admin && !me.is_superuser) {
        const nextPath = await resolveAdminPostLoginPath(data.access_token, me);
        if (nextPath !== '/admin/regional') {
          setError("관리자 또는 지역 관리자 권한이 없습니다.");
          clearAdminToken();
          return;
        }
        window.location.replace(nextPath);
        return;
      }

      window.location.replace('/admin');
    } catch (err) {
      const message = err instanceof DOMException && err.name === 'AbortError'
        ? `서버 응답이 ${Math.floor(ADMIN_LOGIN_REQUEST_TIMEOUT_MS / 1000)}초 이상 지연되어 로그인을 중단했습니다. 관리자 프록시와 백엔드 상태를 먼저 확인해주세요.`
        : '서버 연결에 실패했습니다. 관리자 프록시 또는 백엔드 연결 상태를 확인한 뒤 다시 시도해주세요.';
      clearAdminToken();
      setError(message);
    } finally {
      loginRequest.cleanup();
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] px-4 font-['Segoe_UI',sans-serif]">
      <div className="w-full max-w-[420px] rounded-2xl bg-white px-10 py-12 shadow-[0_20px_60px_rgba(0,0,0,0.2)]">
        {/* 로고 영역 */}
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#667eea,#764ba2)] text-2xl">🛡️</div>
          <h1 className="m-0 text-[22px] font-bold text-[#1a1a2e]">
            관리자 대시보드
          </h1>
          <p className="mt-1.5 text-sm text-[#666]">
            관리자 · 지역 관리자 로그인
          </p>
          <p className="mt-2 text-xs text-[#7b7b98]">
            지문/패스키 로그인 전용 모드입니다. 지역 관리자는 로그인 후 자동으로 지역 대시보드로 이동합니다.
          </p>
        </div>

        {/* 오류 메시지 */}
        {error && (
          <div data-testid="admin-login-error" role="alert" className="mb-5 rounded-lg border border-[#ffcccc] bg-[#fff0f0] px-4 py-3 text-sm text-[#cc0000]">
            ⚠️ {error}
          </div>
        )}

        {/* 로그인 폼 */}
        <form onSubmit={handleLogin} data-testid="admin-login-form" noValidate>
          <div className="mb-[18px]">
            <label htmlFor="admin-login-email" className="mb-1.5 block text-[13px] font-semibold text-[#444]">
              이메일
            </label>
            <input
              id="admin-login-email"
              name="username"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com"
              autoComplete="username webauthn"
              data-testid="admin-login-email"
              className="box-border w-full rounded-lg border-[1.5px] border-[#e0e0e0] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
            />
          </div>

          <div className="mb-6">
            <label htmlFor="admin-login-password" className="mb-1.5 block text-[13px] font-semibold text-[#444]">
              비밀번호
            </label>
            <input
              id="admin-login-password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={AUTH_PASSKEY_ONLY ? "패스키 전용 모드에서는 비활성화" : "••••••••"}
              autoComplete="current-password"
              data-testid="admin-login-password"
              disabled={AUTH_PASSKEY_ONLY}
              className="box-border w-full rounded-lg border-[1.5px] border-[#e0e0e0] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
            />
          </div>

          <div className="mb-5 space-y-3 rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-3 text-sm text-[#4e5678]">
            <label htmlFor="admin-login-remember-id" className="flex items-center gap-2">
              <input
                id="admin-login-remember-id"
                name="rememberId"
                type="checkbox"
                checked={rememberId}
                onChange={(e) => setRememberId(e.target.checked)}
                data-testid="admin-login-remember-id"
                className="h-4 w-4"
              />
              아이디 기억
            </label>
            <label htmlFor="admin-login-remember-password" className="flex items-center gap-2">
              <input
                id="admin-login-remember-password"
                name="rememberPassword"
                type="checkbox"
                checked={false}
                disabled
                data-testid="admin-login-remember-password"
                className="h-4 w-4"
              />
              비밀번호 기억 (보안 정책으로 비활성화)
            </label>
            <label htmlFor="admin-login-allow-passkey" className="flex items-center gap-2">
              <input
                id="admin-login-allow-passkey"
                name="allowPasskeyOnDevice"
                type="checkbox"
                checked={allowPasskeyOnDevice}
                onChange={(e) => setAllowPasskeyOnDevice(e.target.checked)}
                data-testid="admin-login-allow-passkey"
                className="h-4 w-4"
              />
              이 기기에서 지문/패스키 로그인 사용
            </label>
            <p className="text-[12px] text-[#7b7b98]">
              비밀번호는 브라우저에 저장되지 않습니다.
            </p>
          </div>

          <button
            type="submit"
            disabled={!hydrated || loading || AUTH_PASSKEY_ONLY}
            data-testid="admin-login-submit"
            className={`w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white transition-opacity ${loading
              ? 'cursor-not-allowed bg-[#aaa]'
              : 'cursor-pointer bg-[linear-gradient(135deg,#667eea,#764ba2)]'
              }`}
          >
            {AUTH_PASSKEY_ONLY ? "🔒 비밀번호 로그인 비활성화" : loading ? "⏳ 로그인 중..." : "🔐 로그인"}
          </button>

          <button
            type="button"
            disabled={!hydrated || !passkeyReady || passkeyBusy}
            data-testid="admin-login-passkey-button"
            className={`mt-3 w-full rounded-lg border px-4 py-[14px] text-base font-semibold transition-colors ${allowPasskeyOnDevice ? 'border-[#667eea] bg-white text-[#5b67d8] hover:bg-[#f4f6ff]' : 'border-[#d6d8e6] bg-[#f3f4f8] text-[#8b90a8]'} ${(!passkeyReady || passkeyBusy) ? 'cursor-not-allowed opacity-60' : ''}`}
            onClick={() => void handlePasskeyLogin()}
          >
            {passkeyBusy ? '⏳ 패스키 처리 중...' : '📱 지문/패스키 로그인'}
          </button>

          <button
            type="button"
            disabled={!hydrated || !passkeyReady || passkeyBusy}
            data-testid="admin-login-passkey-register"
            onClick={() => void handlePasskeyRegister()}
            className={`mt-3 w-full rounded-lg border px-4 py-[14px] text-base font-semibold transition-colors ${passkeyReady ? 'border-[#764ba2] bg-white text-[#764ba2] hover:bg-[#f7f0ff]' : 'cursor-not-allowed border-[#d8d8e8] bg-[#f4f4f8] text-[#9c9cb0]'} ${passkeyBusy ? 'opacity-60' : ''}`}
          >
            {passkeyBusy ? '⏳ 패스키 등록 중...' : '🪪 이 기기 패스키 등록'}
          </button>

          {passkeyBusy ? (
            <button
              type="button"
              data-testid="admin-login-passkey-cancel"
              className="mt-3 w-full rounded-lg border border-[#e6e8f6] bg-[#f8f9ff] px-4 py-3 text-sm font-semibold text-[#5b67d8] hover:bg-[#eef1ff]"
              onClick={() => {
                setPasskeyBusy(false);
                setError('패스키 처리를 중단했습니다. 다시 시도해주세요.');
              }}
            >
              처리 중단
            </button>
          ) : null}

          <div className="mt-4 flex flex-col gap-2 text-sm">
            <Link href="/admin/recovery" className="font-medium text-[#5b67d8] underline underline-offset-2">
              비밀번호를 잊으셨나요? (이메일/문자 인증)
            </Link>
            <Link href="/admin/recovery?intent=passkey" className="font-medium text-[#5b67d8] underline underline-offset-2">
              비밀번호 없이 패스키 등록 (이메일/문자 인증)
            </Link>
            <Link href="/admin/recovery" data-testid="admin-login-recovery-link" className="hidden">
              비밀번호를 잊으셨나요?
            </Link>
            <Link href="/admin/recovery?mode=carrier" data-testid="admin-login-carrier-recovery-link" className="hidden">
              통신사 본인확인 후 비밀번호 재설정
            </Link>
          </div>

          <div className="mt-5 rounded-xl border border-[#d8dcff] bg-[#f7f8ff] px-4 py-4 text-sm text-[#4d5588]">
            <div className="font-semibold text-[#2f376d]">로그인 문제 해결 안내</div>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>비밀번호 로그인은 정책상 비활성화되어 있습니다.</li>
              <li>복구 페이지에서 이메일 또는 SMS 인증 후 이 기기에 패스키를 등록할 수 있습니다.</li>
              <li>패스키 등록 후에는 지문/Face ID로 바로 로그인할 수 있습니다.</li>
            </ul>
          </div>
        </form>

        <p className="mt-5 text-center text-xs text-[#999]">
          DevAnalysis114 Admin v2.2.0
        </p>
      </div>
    </div>
  );
}
