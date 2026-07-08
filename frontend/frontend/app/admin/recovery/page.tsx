"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { resolveApiBaseUrl } from "@/lib/api";

type VerificationChannel = "email" | "phone";
type RecoveryStep = "request" | "verify" | "complete";

function encodeArrayBuffer(value: ArrayBuffer | Uint8Array) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  const decoded = atob(padded);
  return Uint8Array.from(decoded, (char) => char.charCodeAt(0));
}

function normalizePublicKeyOptions(options: Record<string, unknown> | null | undefined) {
  if (!options || typeof options !== "object") {
    return null;
  }
  return {
    ...options,
    challenge: decodeBase64Url(String(options.challenge || "")),
    user: options.user && typeof options.user === "object"
      ? {
        ...(options.user as Record<string, unknown>),
        id: decodeBase64Url(String((options.user as Record<string, unknown>).id || "")),
      }
      : undefined,
    excludeCredentials: Array.isArray(options.excludeCredentials)
      ? options.excludeCredentials.map((item) => {
        const credential = item as Record<string, unknown>;
        return {
          ...credential,
          id: decodeBase64Url(String(credential.id || "")),
        };
      })
      : undefined,
    allowCredentials: Array.isArray(options.allowCredentials)
      ? options.allowCredentials.map((item) => {
        const credential = item as Record<string, unknown>;
        return {
          ...credential,
          id: decodeBase64Url(String(credential.id || "")),
        };
      })
      : undefined,
  };
}

function AdminRecoveryPageContent() {
  const searchParams = useSearchParams();
  const intent = searchParams.get("intent") || "default";
  const apiBaseUrl = resolveApiBaseUrl();

  const [step, setStep] = useState<RecoveryStep>("request");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [verificationChannel, setVerificationChannel] = useState<VerificationChannel>("email");
  const [verificationCode, setVerificationCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [recoverySessionToken, setRecoverySessionToken] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [maskedTarget, setMaskedTarget] = useState("");
  const [devOtpHint, setDevOtpHint] = useState("");
  const [passkeyReady, setPasskeyReady] = useState(false);
  const [passkeyBusy, setPasskeyBusy] = useState(false);

  const title = useMemo(() => (
    intent === "passkey" ? "인증 후 패스키 등록" : "관리자 비밀번호 복구"
  ), [intent]);

  useEffect(() => {
    setPasskeyReady(
      typeof window !== "undefined"
      && typeof window.PublicKeyCredential !== "undefined"
      && typeof navigator.credentials?.create === "function",
    );
    const presetEmail = searchParams.get("email");
    if (presetEmail) {
      setEmail(presetEmail);
    }
  }, [searchParams]);

  const startRecovery = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/recovery/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope: "admin",
          user_hint: email.trim(),
          verification_channel: verificationChannel,
          phone_number: verificationChannel === "phone" ? phoneNumber.trim() : undefined,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `인증 코드 발송 실패 (HTTP ${response.status})`);
      }
      setRecoverySessionToken(String(payload.recovery_session_token || ""));
      setMaskedTarget(String(payload.masked_target || ""));
      setDevOtpHint(String(payload.dev_otp_hint || ""));
      setStep("verify");
      setMessage(
        `${payload.masked_target || "등록된 연락처"}(으)로 6자리 인증 코드를 보냈습니다. 15분 이내에 입력해주세요.`,
      );
    } catch (e: any) {
      setError(e.message || "인증 코드 발송에 실패했습니다.");
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
          verification_code: verificationCode.trim(),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `인증 실패 (HTTP ${response.status})`);
      }
      setResetToken(String(payload.reset_token || ""));
      setStep("complete");
      setMessage(
        intent === "passkey"
          ? "본인 확인이 완료되었습니다. 아래에서 이 기기 패스키를 등록하세요."
          : "본인 확인이 완료되었습니다. 새 비밀번호를 설정하거나 패스키를 등록할 수 있습니다.",
      );
    } catch (e: any) {
      setError(e.message || "인증 코드 확인에 실패했습니다.");
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
      setResetToken("");
      setVerificationCode("");
      setNewPassword("");
      setStep("request");
    } catch (e: any) {
      setError(e.message || "비밀번호 재설정에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeyRegister = async () => {
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !resetToken) {
      setError("패스키 등록 전 이메일 인증을 완료해주세요.");
      return;
    }
    if (!passkeyReady) {
      setError("이 브라우저/기기에서는 패스키 등록을 사용할 수 없습니다.");
      return;
    }

    setPasskeyBusy(true);
    setError("");
    try {
      const startResponse = await fetch("/api/proxy?action=passkey-register-start", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "Cache-Control": "no-cache", Pragma: "no-cache" },
        body: JSON.stringify({
          email: normalizedEmail,
          device_label: "이 기기 패스키",
          recovery_reset_token: resetToken,
        }),
        cache: "no-store",
      });
      const startPayload = await startResponse.json().catch(() => null);
      if (!startResponse.ok || !startPayload) {
        throw new Error(startPayload?.detail || "패스키 등록 시작에 실패했습니다.");
      }

      const publicKeyOptions = normalizePublicKeyOptions(startPayload.options);
      if (!publicKeyOptions) {
        throw new Error("패스키 등록 옵션을 해석하지 못했습니다.");
      }

      const createdCredential = await navigator.credentials.create({
        publicKey: publicKeyOptions as unknown as PublicKeyCredentialCreationOptions,
      }) as PublicKeyCredential | null;

      if (!createdCredential) {
        throw new Error("패스키 등록 결과를 받지 못했습니다.");
      }

      const finishResponse = await fetch("/api/proxy?action=passkey-register-finish", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "Cache-Control": "no-cache", Pragma: "no-cache" },
        body: JSON.stringify({
          registration_token: startPayload.registration_token,
          credential: {
            id: createdCredential.id,
            rawId: encodeArrayBuffer(createdCredential.rawId),
            type: createdCredential.type,
            response: createdCredential.response && "attestationObject" in createdCredential.response
              ? {
                clientDataJSON: encodeArrayBuffer((createdCredential.response as AuthenticatorAttestationResponse).clientDataJSON),
                attestationObject: encodeArrayBuffer((createdCredential.response as AuthenticatorAttestationResponse).attestationObject),
              }
              : {},
          },
        }),
        cache: "no-store",
      });
      const finishPayload = await finishResponse.json().catch(() => null);
      if (!finishResponse.ok || !finishPayload?.registered) {
        throw new Error(finishPayload?.detail || "패스키 등록 완료에 실패했습니다.");
      }

      setMessage("패스키 등록이 완료되었습니다. 다음부터 지문/패스키 로그인을 사용할 수 있습니다.");
      setResetToken("");
      setVerificationCode("");
      setNewPassword("");
    } catch (err: any) {
      setError(err?.message || "패스키 등록 중 오류가 발생했습니다.");
    } finally {
      setPasskeyBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] px-4 font-['Segoe_UI',sans-serif]">
      <div className="w-full max-w-[520px] rounded-2xl bg-white px-10 py-12 shadow-[0_20px_60px_rgba(0,0,0,0.2)]">
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#667eea,#764ba2)] text-2xl">🔐</div>
          <h1 className="m-0 text-[22px] font-bold text-[#1a1a2e]">{title}</h1>
          <p className="mt-2 text-sm text-[#666]">
            로그인 전에 이메일 또는 휴대폰 인증으로 관리자 계정을 확인할 수 있습니다.
          </p>
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

        {step === "request" && (
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

            <div>
              <label className="mb-1.5 block text-[13px] font-semibold text-[#444]">인증 방법</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setVerificationChannel("email")}
                  className={`flex-1 rounded-lg border px-3 py-2 text-sm font-semibold ${verificationChannel === "email" ? "border-[#667eea] bg-[#f4f6ff] text-[#5b67d8]" : "border-[#e0e0e0] bg-white text-[#666]"}`}
                >
                  이메일
                </button>
                <button
                  type="button"
                  onClick={() => setVerificationChannel("phone")}
                  className={`flex-1 rounded-lg border px-3 py-2 text-sm font-semibold ${verificationChannel === "phone" ? "border-[#667eea] bg-[#f4f6ff] text-[#5b67d8]" : "border-[#e0e0e0] bg-white text-[#666]"}`}
                >
                  휴대폰(SMS)
                </button>
              </div>
            </div>

            {verificationChannel === "phone" && (
              <div>
                <label className="mb-1.5 block text-[13px] font-semibold text-[#444]">휴대폰 번호</label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="01012345678"
                  className="box-border w-full rounded-lg border-[1.5px] border-[#e0e0e0] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
                />
                <p className="mt-1 text-xs text-[#888]">계정에 등록된 번호가 있으면 비워도 됩니다.</p>
              </div>
            )}

            <button
              type="button"
              onClick={() => void startRecovery()}
              disabled={loading || !email.trim() || (verificationChannel === "phone" && !phoneNumber.trim())}
              className={`w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || !email.trim() ? "bg-[#aaa]" : "bg-[linear-gradient(135deg,#667eea,#764ba2)]"}`}
            >
              {loading ? "처리 중..." : "인증 코드 받기"}
            </button>
          </div>
        )}

        {step === "verify" && (
          <div className="space-y-4">
            <div className="rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4 text-sm text-[#4d5588]">
              <div className="font-semibold text-[#2f376d]">인증 코드 입력</div>
              <p className="mt-1 text-xs">
                {maskedTarget ? `${maskedTarget}(으)로 발송된 6자리 코드를 입력하세요.` : "발송된 6자리 코드를 입력하세요."}
              </p>
              {devOtpHint && (
                <p className="mt-2 rounded-lg bg-[#fff8e6] px-3 py-2 text-xs text-[#8a6d00]">
                  개발 환경 힌트: {devOtpHint}
                </p>
              )}
            </div>
            <input
              type="text"
              inputMode="numeric"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              placeholder="123456"
              maxLength={6}
              className="box-border w-full rounded-lg border-[1.5px] border-[#d9def7] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
            />
            <button
              type="button"
              onClick={() => void verifyIdentity()}
              disabled={loading || verificationCode.trim().length < 6}
              className={`w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || verificationCode.trim().length < 6 ? "bg-[#aaa]" : "bg-[linear-gradient(135deg,#667eea,#764ba2)]"}`}
            >
              {loading ? "확인 중..." : "인증 확인"}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("request");
                setVerificationCode("");
                setMessage("");
              }}
              className="w-full rounded-lg border border-[#ddd] bg-white px-4 py-3 text-sm font-semibold text-[#666]"
            >
              처음으로
            </button>
          </div>
        )}

        {step === "complete" && (
          <div className="space-y-4">
            {intent !== "passkey" && (
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
                  className={`mt-3 w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || !resetToken || newPassword.length < 8 ? "bg-[#aaa]" : "bg-[#238636]"}`}
                >
                  비밀번호 재설정
                </button>
              </div>
            )}

            <div className="rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4">
              <div className="mb-2 text-sm font-semibold text-[#2f376d]">이 기기 패스키 등록</div>
              <p className="mb-3 text-xs text-[#6b7399]">
                인증이 완료되었으므로 비밀번호 없이도 이 기기에 패스키를 등록할 수 있습니다.
              </p>
              <button
                type="button"
                onClick={() => void handlePasskeyRegister()}
                disabled={!passkeyReady || passkeyBusy || !resetToken}
                data-testid="admin-recovery-passkey-register"
                className={`w-full rounded-lg border px-4 py-[14px] text-base font-semibold ${passkeyReady && resetToken ? "border-[#764ba2] bg-white text-[#764ba2] hover:bg-[#f7f0ff]" : "cursor-not-allowed border-[#d8d8e8] bg-[#f4f4f8] text-[#9c9cb0]"}`}
              >
                {passkeyBusy ? "⏳ 패스키 등록 중..." : "🪪 이 기기 패스키 등록"}
              </button>
            </div>
          </div>
        )}

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
