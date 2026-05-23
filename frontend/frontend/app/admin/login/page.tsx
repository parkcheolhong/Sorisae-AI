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
const ADMIN_LOGIN_REMEMBER_PASSWORD_KEY = "admin_login_remember_password_v1";
const ADMIN_LOGIN_EMAIL_KEY = "admin_login_email_v1";
const ADMIN_LOGIN_PASSWORD_KEY = "admin_login_password_v1";
const ADMIN_LOGIN_ALLOW_PASSKEY_KEY = "admin_login_allow_passkey_v1";
const ADMIN_LOGIN_REQUEST_TIMEOUT_MS = ADMIN_PROXY_TIMEOUT_MS + 7_000;
const ADMIN_LOGIN_RETRY_COUNT = 1;

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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rememberId, setRememberId] = useState(true);
  const [rememberPassword, setRememberPassword] = useState(false);
  const [allowPasskeyOnDevice, setAllowPasskeyOnDevice] = useState(true);
  const [passkeyBusy, setPasskeyBusy] = useState(false);
  const [passkeyReady, setPasskeyReady] = useState(false);

  useEffect(() => {
    try {
      const savedRememberId = localStorage.getItem(ADMIN_LOGIN_REMEMBER_ID_KEY);
      const savedRememberPassword = localStorage.getItem(ADMIN_LOGIN_REMEMBER_PASSWORD_KEY);
      const savedAllowPasskey = localStorage.getItem(ADMIN_LOGIN_ALLOW_PASSKEY_KEY);
      const savedEmail = localStorage.getItem(ADMIN_LOGIN_EMAIL_KEY);
      const savedPassword = localStorage.getItem(ADMIN_LOGIN_PASSWORD_KEY);

      const nextRememberId = savedRememberId !== 'false';
      const nextRememberPassword = savedRememberPassword === 'true';
      const nextAllowPasskey = savedAllowPasskey !== 'false';

      setRememberId(nextRememberId);
      setRememberPassword(nextRememberPassword);
      setAllowPasskeyOnDevice(nextAllowPasskey);

      if (nextRememberId && savedEmail) {
        setEmail(savedEmail);
      }
      if (nextRememberPassword && savedPassword) {
        setPassword(savedPassword);
      }
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
      localStorage.setItem(ADMIN_LOGIN_REMEMBER_PASSWORD_KEY, rememberPassword ? 'true' : 'false');
      if (rememberPassword && password) {
        localStorage.setItem(ADMIN_LOGIN_PASSWORD_KEY, password);
      } else {
        localStorage.removeItem(ADMIN_LOGIN_PASSWORD_KEY);
      }
    } catch {
    }
  }, [password, rememberPassword]);

  useEffect(() => {
    try {
      localStorage.setItem(ADMIN_LOGIN_ALLOW_PASSKEY_KEY, allowPasskeyOnDevice ? 'true' : 'false');
    } catch {
    }
  }, [allowPasskeyOnDevice]);

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
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setError('패스키 로그인 전 관리자 이메일을 입력해주세요.');
      return;
    }
    if (!passkeyReady) {
      setError('이 브라우저/기기에서는 패스키 로그인을 사용할 수 없습니다.');
      return;
    }

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

      const credential = await navigator.credentials.get({
        publicKey: normalizePublicKeyOptions(startPayload.options),
      }) as PublicKeyCredential | null;

      if (!credential) {
        throw new Error('패스키 로그인 승인 정보가 반환되지 않았습니다.');
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
      window.location.replace('/admin');
    } catch (err: any) {
      setError(err?.message || '패스키 로그인 중 오류가 발생했습니다.');
      clearAdminToken();
    } finally {
      setPasskeyBusy(false);
    }
  };

  const handlePasskeyRegister = async () => {
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setError('패스키 등록 전 관리자 이메일을 입력해주세요.');
      return;
    }
    if (!password) {
      setError('패스키 등록 전 비밀번호로 먼저 본인 확인이 필요합니다.');
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
        body: JSON.stringify({ email: normalizedEmail, device_label: '이 기기 패스키' }),
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
    setLoading(true);
    setError("");
    const loginFlowStartedAt = performance.now();

    try {
      const authUrl = "/api/proxy";
      const normalizedEmail = email.trim();
      const normalizedPassword = password;

      if (!normalizedEmail || !normalizedPassword) {
        setError("이메일과 비밀번호를 모두 입력해주세요.");
        return;
      }

      const loginRequest = createTimeoutSignal(ADMIN_LOGIN_REQUEST_TIMEOUT_MS);

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
      loginRequest.cleanup();
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
        if (rememberPassword) {
          localStorage.setItem(ADMIN_LOGIN_PASSWORD_KEY, normalizedPassword);
        } else {
          localStorage.removeItem(ADMIN_LOGIN_PASSWORD_KEY);
        }
      } catch {
      }

      setAdminToken(data.access_token);

      // /me 호출로 관리자 권한 확인
      const me = data.user;
      if (!me || (typeof me !== 'object')) {
        setError("관리자 정보 응답 형식이 올바르지 않습니다. 프록시와 백엔드 상태를 확인해주세요.");
        clearAdminToken();
        return;
      }

      if (!me.is_admin && !me.is_superuser) {
        setError("관리자 권한이 없습니다.");
        clearAdminToken();
        return;
      }

      window.location.replace("/admin");
    } catch (err) {
      const message = err instanceof DOMException && err.name === 'AbortError'
        ? `서버 응답이 ${Math.floor(ADMIN_LOGIN_REQUEST_TIMEOUT_MS / 1000)}초 이상 지연되어 로그인을 중단했습니다. 관리자 프록시와 백엔드 상태를 먼저 확인한 뒤 다시 시도해주세요.`
        : '서버 연결에 실패했습니다. 관리자 프록시 또는 백엔드 연결 상태를 확인한 뒤 다시 시도해주세요.';
      clearAdminToken();
      setError(message);
    } finally {
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
            관리자 계정으로 로그인하세요
          </p>
          <p className="mt-2 text-xs text-[#7b7b98]">
            아이디/비밀번호 기억, 지문/패스키 로그인 사용 여부, 로그인 전 복구 진입 경로를 이 화면에서 바로 확인할 수 있습니다.
          </p>
        </div>

        {/* 오류 메시지 */}
        {error && (
          <div data-testid="admin-login-error" className="mb-5 rounded-lg border border-[#ffcccc] bg-[#fff0f0] px-4 py-3 text-sm text-[#cc0000]">
            ⚠️ {error}
          </div>
        )}

        {/* 로그인 폼 */}
        <form onSubmit={handleLogin} data-testid="admin-login-form">
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
              autoComplete="username"
              required
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
              placeholder="••••••••"
              autoComplete="current-password"
              required
              data-testid="admin-login-password"
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
                checked={rememberPassword}
                onChange={(e) => setRememberPassword(e.target.checked)}
                data-testid="admin-login-remember-password"
                className="h-4 w-4"
              />
              비밀번호 기억
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
              공용 기기에서는 비밀번호 기억을 권장하지 않습니다.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            data-testid="admin-login-submit"
            className={`w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white transition-opacity ${loading
              ? 'cursor-not-allowed bg-[#aaa]'
              : 'cursor-pointer bg-[linear-gradient(135deg,#667eea,#764ba2)]'
              }`}
          >
            {loading ? "⏳ 로그인 중..." : "🔐 로그인"}
          </button>

          <button
            type="button"
            disabled={!passkeyReady || passkeyBusy}
            data-testid="admin-login-passkey-button"
            className={`mt-3 w-full rounded-lg border px-4 py-[14px] text-base font-semibold transition-colors ${allowPasskeyOnDevice ? 'border-[#667eea] bg-white text-[#5b67d8] hover:bg-[#f4f6ff]' : 'cursor-not-allowed border-[#ddd] bg-[#f3f3f3] text-[#999]'}`}
            onClick={() => void handlePasskeyLogin()}
          >
            {passkeyBusy ? '⏳ 패스키 처리 중...' : '📱 지문/패스키 로그인'}
          </button>

          <button
            type="button"
            disabled={!passkeyReady || passkeyBusy}
            data-testid="admin-login-passkey-register"
            onClick={() => void handlePasskeyRegister()}
            className={`mt-3 w-full rounded-lg border px-4 py-[14px] text-base font-semibold transition-colors ${passkeyReady ? 'border-[#764ba2] bg-white text-[#764ba2] hover:bg-[#f7f0ff]' : 'cursor-not-allowed border-[#ddd] bg-[#f3f3f3] text-[#999]'}`}
          >
            {passkeyBusy ? '⏳ 패스키 등록 중...' : '🪪 이 기기 패스키 등록'}
          </button>

          <div className="mt-4 flex flex-col gap-2 text-sm">
            <Link href="/admin/recovery" className="font-medium text-[#5b67d8] underline underline-offset-2">
              비밀번호를 잊으셨나요?
            </Link>
            <Link href="/admin/recovery" data-testid="admin-login-recovery-link" className="hidden">
              비밀번호를 잊으셨나요?
            </Link>
            <Link href="/admin/recovery?mode=carrier" className="font-medium text-[#5b67d8] underline underline-offset-2">
              통신사 본인확인 후 비밀번호 재설정
            </Link>
            <Link href="/admin/recovery?mode=carrier" data-testid="admin-login-carrier-recovery-link" className="hidden">
              통신사 본인확인 후 비밀번호 재설정
            </Link>
          </div>

          <div className="mt-5 rounded-xl border border-[#d8dcff] bg-[#f7f8ff] px-4 py-4 text-sm text-[#4d5588]">
            <div className="font-semibold text-[#2f376d]">로그인 문제 해결 안내</div>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>관리자 비밀번호를 잊은 경우 로그인 전 복구 페이지에서 재설정 흐름을 시작할 수 있습니다.</li>
              <li>통신사 본인확인과 패스키(지문/Face ID)는 다음 단계에서 관리자/회원 공통 인증 코어로 연결할 예정입니다.</li>
              <li>고위험 설정 변경 시 추가 본인확인이 필요할 수 있습니다.</li>
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
