"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { resolveApiBaseUrl } from "@/lib/api";

function AdminRecoveryPageContent() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode") || "default";
  const apiBaseUrl = resolveApiBaseUrl();
  const [email, setEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [recoverySessionToken, setRecoverySessionToken] = useState("");
  const [identitySessionToken, setIdentitySessionToken] = useState("");
  const [resetToken, setResetToken] = useState("");

  const title = useMemo(() => (
    mode === "carrier" ? "통신사 본인확인 후 재설정" : "관리자 비밀번호 복구"
  ), [mode]);

  const startRecovery = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/recovery/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope: "admin", user_hint: email.trim() }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `복구 시작 실패 (HTTP ${response.status})`);
      }
      setRecoverySessionToken(String(payload.recovery_session_token || ""));
      setMessage("복구 세션이 생성되었습니다. 현재 초안에서는 000000 코드를 입력하면 다음 단계로 진행됩니다.");
    } catch (e: any) {
      setError(e.message || "복구 시작에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const startCarrierVerification = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/identity/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope: "admin",
          purpose: "password_reset",
          user_hint: email.trim(),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `본인확인 시작 실패 (HTTP ${response.status})`);
      }
      setIdentitySessionToken(String(payload.session_token || ""));
      setMessage("본인확인 세션이 생성되었습니다. 현재 mock 구현에서는 동일하게 000000 코드를 입력하면 됩니다.");
    } catch (e: any) {
      setError(e.message || "본인확인 세션 생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const completeCarrierVerification = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/identity/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_token: identitySessionToken,
          verification_code: verificationCode.trim(),
          phone: "01000000000",
          name: "관리자",
          birth: "19900101",
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `본인확인 완료 실패 (HTTP ${response.status})`);
      }
      setMessage(`본인확인이 확인되었습니다. phone_last4=${String(payload.phone_last4 || '0000')}`);
    } catch (e: any) {
      setError(e.message || "본인확인 완료에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const verifyIdentity = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/recovery/verify-identity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recovery_session_token: recoverySessionToken,
          identity_session_token: identitySessionToken,
          verification_code: verificationCode.trim(),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `본인확인 실패 (HTTP ${response.status})`);
      }
      setResetToken(String(payload.reset_token || ""));
      setMessage("본인확인이 확인되었습니다. 새 비밀번호를 설정하세요.");
    } catch (e: any) {
      setError(e.message || "본인확인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/recovery/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope: "admin",
          reset_token: resetToken,
          new_password: newPassword,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `비밀번호 재설정 실패 (HTTP ${response.status})`);
      }
      setMessage("비밀번호가 재설정되었습니다. 새 비밀번호로 다시 로그인하세요.");
      setRecoverySessionToken("");
      setResetToken("");
      setVerificationCode("");
      setNewPassword("");
    } catch (e: any) {
      setError(e.message || "비밀번호 재설정에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] px-4 font-['Segoe_UI',sans-serif]">
      <div className="w-full max-w-[520px] rounded-2xl bg-white px-10 py-12 shadow-[0_20px_60px_rgba(0,0,0,0.2)]">
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#667eea,#764ba2)] text-2xl">🔐</div>
          <h1 className="m-0 text-[22px] font-bold text-[#1a1a2e]">{title}</h1>
          <p className="mt-2 text-sm text-[#666]">로그인 전에 관리자 비밀번호 복구를 시작할 수 있습니다.</p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-[#ffcccc] bg-[#fff0f0] px-4 py-3 text-sm text-[#cc0000]">
            ⚠️ {error}
          </div>
        )}
        {message && (
          <div className="mb-4 rounded-lg border border-[#cce7d0] bg-[#edf9f0] px-4 py-3 text-sm text-[#216e39]">
            ✅ {message}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-[13px] font-semibold text-[#444]">관리자 이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="119cash@naver.com"
              className="box-border w-full rounded-lg border-[1.5px] border-[#e0e0e0] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
            />
          </div>

          <button
            type="button"
            onClick={() => void startRecovery()}
            disabled={loading || !email.trim()}
            className={`w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || !email.trim() ? 'bg-[#aaa]' : 'bg-[linear-gradient(135deg,#667eea,#764ba2)]'}`}
          >
            {loading ? '처리 중...' : '복구 시작'}
          </button>

          <div className="rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4">
            <div className="mb-2 text-sm font-semibold text-[#2f376d]">본인확인 코드 입력</div>
            <p className="mb-3 text-xs text-[#6b7399]">현재 초안 구현에서는 테스트용 코드 `000000`을 사용합니다.</p>
            <div className="mb-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void startCarrierVerification()}
                disabled={loading || !email.trim()}
                className={`rounded-lg border px-3 py-2 text-sm font-semibold ${loading || !email.trim() ? 'cursor-not-allowed border-[#ddd] bg-[#f3f3f3] text-[#999]' : 'border-[#667eea] bg-white text-[#5b67d8] hover:bg-[#f4f6ff]'}`}
              >
                본인확인 세션 시작
              </button>
              <button
                type="button"
                onClick={() => void completeCarrierVerification()}
                disabled={loading || !identitySessionToken || !verificationCode.trim()}
                className={`rounded-lg border px-3 py-2 text-sm font-semibold ${loading || !identitySessionToken || !verificationCode.trim() ? 'cursor-not-allowed border-[#ddd] bg-[#f3f3f3] text-[#999]' : 'border-[#667eea] bg-white text-[#5b67d8] hover:bg-[#f4f6ff]'}`}
              >
                본인확인 완료
              </button>
            </div>
            <input
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              placeholder="000000"
              className="box-border w-full rounded-lg border-[1.5px] border-[#d9def7] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
            />
            <button
              type="button"
              onClick={() => void verifyIdentity()}
              disabled={loading || !recoverySessionToken || !identitySessionToken || !verificationCode.trim()}
              className={`mt-3 w-full rounded-lg border border-[#667eea] px-4 py-[14px] text-base font-semibold ${loading || !recoverySessionToken || !identitySessionToken || !verificationCode.trim() ? 'cursor-not-allowed border-[#ddd] bg-[#f3f3f3] text-[#999]' : 'bg-white text-[#5b67d8] hover:bg-[#f4f6ff]'}`}
            >
              복구 인증 연결
            </button>
          </div>

          <div className="rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4">
            <div className="mb-2 text-sm font-semibold text-[#2f376d]">새 비밀번호 설정</div>
            <input
              id="admin-recovery-new-password"
              name="newPassword"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="새 비밀번호 (8자 이상)"
              className="box-border w-full rounded-lg border-[1.5px] border-[#d9def7] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
            />
            <button
              type="button"
              onClick={() => void resetPassword()}
              disabled={loading || !resetToken || newPassword.length < 8}
              className={`mt-3 w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || !resetToken || newPassword.length < 8 ? 'bg-[#aaa]' : 'bg-[#238636]'}`}
            >
              비밀번호 재설정
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-sm">
          <Link href="/admin/login" className="font-medium text-[#5b67d8] underline underline-offset-2">
            관리자 로그인으로 돌아가기
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function AdminRecoveryPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] px-4 text-sm text-white">복구 화면을 불러오는 중...</div>}>
      <AdminRecoveryPageContent />
    </Suspense>
  );
}
