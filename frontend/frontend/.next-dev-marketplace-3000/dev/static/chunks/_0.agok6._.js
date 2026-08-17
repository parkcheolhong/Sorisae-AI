(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/shared/api.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "api",
    ()=>api,
    "resolveApiBaseUrl",
    ()=>resolveApiBaseUrl,
    "resolveBackendDocsUrl",
    ()=>resolveBackendDocsUrl
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/axios/lib/axios.js [app-client] (ecmascript)");
;
function resolveConfiguredApiUrl() {
    const configured = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL?.trim();
    return configured && configured.length > 0 ? configured : 'http://localhost:8000';
}
function isDirectLocalBackendUrl(value) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized.startsWith('http://localhost:8000') || normalized.startsWith('http://127.0.0.1:8000');
}
function resolveBackendDocsUrl(apiBaseUrl) {
    const normalizedBase = String(apiBaseUrl || resolveApiBaseUrl()).trim().replace(/\/$/, '');
    if ("TURBOPACK compile-time truthy", 1) {
        const { hostname, origin, port, protocol } = window.location;
        const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isDirectFrontendDevPort = port === '3000' || port === '3005';
        const isGatewayPort = port === '8080' || port === '8443';
        if (isDirectFrontendDevPort && protocol !== 'https:') {
            return `${origin.replace(/\/$/, '')}/docs`;
        }
        if (normalizedBase === origin.replace(/\/$/, '') && isLocalHost) {
            return `${origin.replace(/\/$/, '')}/docs`;
        }
        if (!isLocalHost || isGatewayPort || protocol === 'https:') {
            return `${origin.replace(/\/$/, '')}/docs`;
        }
    }
    return `${normalizedBase}/docs`;
}
function resolveApiBaseUrl() {
    if ("TURBOPACK compile-time truthy", 1) {
        const { hostname, origin, port, protocol } = window.location;
        const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isDirectFrontendDevPort = port === '3000' || port === '3005';
        const isGatewayPort = port === '8080' || port === '8443';
        const configured = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL?.trim();
        if (configured && configured.length > 0) {
            return configured;
        }
        if (isDirectFrontendDevPort && protocol !== 'https:') {
            // Keep browser traffic same-origin only when no explicit backend URL is configured.
            return origin;
        }
        if (!isLocalHost || isGatewayPort || protocol === 'https:') {
            return origin;
        }
    }
    return resolveConfiguredApiUrl();
}
const api = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].create({
    baseURL: ("TURBOPACK compile-time truthy", 1) ? resolveApiBaseUrl() : "TURBOPACK unreachable",
    headers: {
        'Content-Type': 'application/json'
    }
});
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/api.ts [app-client] (ecmascript) <locals>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([]);
var __TURBOPACK__imported__module__$5b$project$5d2f$shared$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/shared/api.ts [app-client] (ecmascript)");
;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/app/admin/recovery/page.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>AdminRecoveryPage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/app-dir/link.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/navigation.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/lib/api.ts [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$shared$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/shared/api.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
;
function encodeArrayBuffer(value) {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
    let binary = "";
    bytes.forEach((byte)=>{
        binary += String.fromCharCode(byte);
    });
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function decodeBase64Url(value) {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(normalized.length + (4 - normalized.length % 4) % 4, "=");
    const decoded = atob(padded);
    return Uint8Array.from(decoded, (char)=>char.charCodeAt(0));
}
function normalizePublicKeyOptions(options) {
    if (!options || typeof options !== "object") {
        return null;
    }
    return {
        ...options,
        challenge: decodeBase64Url(String(options.challenge || "")),
        user: options.user && typeof options.user === "object" ? {
            ...options.user,
            id: decodeBase64Url(String(options.user.id || ""))
        } : undefined,
        excludeCredentials: Array.isArray(options.excludeCredentials) ? options.excludeCredentials.map((item)=>{
            const credential = item;
            return {
                ...credential,
                id: decodeBase64Url(String(credential.id || ""))
            };
        }) : undefined,
        allowCredentials: Array.isArray(options.allowCredentials) ? options.allowCredentials.map((item)=>{
            const credential = item;
            return {
                ...credential,
                id: decodeBase64Url(String(credential.id || ""))
            };
        }) : undefined
    };
}
function AdminRecoveryPageContent() {
    _s();
    const searchParams = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useSearchParams"])();
    const intent = searchParams.get("intent") || "default";
    const scopeParam = (searchParams.get("scope") || "admin").toLowerCase();
    const recoveryScope = scopeParam === "user" ? "user" : "admin";
    const returnTo = searchParams.get("return_to") || "/admin/login";
    const mobileReturnUri = searchParams.get("mobile_return_uri") || "";
    const apiBaseUrl = (0, __TURBOPACK__imported__module__$5b$project$5d2f$shared$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["resolveApiBaseUrl"])();
    const [step, setStep] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("request");
    const [email, setEmail] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [phoneNumber, setPhoneNumber] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [verificationChannel, setVerificationChannel] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("email");
    const [verificationCode, setVerificationCode] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [newPassword, setNewPassword] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [message, setMessage] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [error, setError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [recoverySessionToken, setRecoverySessionToken] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [resetToken, setResetToken] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [maskedTarget, setMaskedTarget] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [devOtpHint, setDevOtpHint] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [passkeyReady, setPasskeyReady] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [passkeyBusy, setPasskeyBusy] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const title = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "AdminRecoveryPageContent.useMemo[title]": ()=>{
            if (intent === "passkey") {
                return recoveryScope === "user" ? "사용자 인증 후 패스키 등록" : "관리자 인증 후 패스키 등록";
            }
            return recoveryScope === "user" ? "사용자 비밀번호 복구" : "관리자 비밀번호 복구";
        }
    }["AdminRecoveryPageContent.useMemo[title]"], [
        intent,
        recoveryScope
    ]);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AdminRecoveryPageContent.useEffect": ()=>{
            setPasskeyReady(("TURBOPACK compile-time value", "object") !== "undefined" && typeof window.PublicKeyCredential !== "undefined" && typeof navigator.credentials?.create === "function");
            const presetEmail = searchParams.get("email");
            if (presetEmail) {
                setEmail(presetEmail);
            }
        }
    }["AdminRecoveryPageContent.useEffect"], [
        searchParams
    ]);
    const startRecovery = async ()=>{
        setLoading(true);
        setError("");
        setMessage("");
        try {
            const response = await fetch(`${apiBaseUrl}/api/auth/recovery/start`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    scope: recoveryScope,
                    user_hint: email.trim(),
                    verification_channel: verificationChannel,
                    phone_number: verificationChannel === "phone" ? phoneNumber.trim() : undefined
                })
            });
            const payload = await response.json().catch(()=>({}));
            if (!response.ok) {
                throw new Error(payload.detail || `인증 코드 발송 실패 (HTTP ${response.status})`);
            }
            setRecoverySessionToken(String(payload.recovery_session_token || ""));
            setMaskedTarget(String(payload.masked_target || ""));
            setDevOtpHint(String(payload.dev_otp_hint || ""));
            setStep("verify");
            setMessage(`${payload.masked_target || "등록된 연락처"}(으)로 6자리 인증 코드를 보냈습니다. 15분 이내에 입력해주세요.`);
        } catch (e) {
            setError(e.message || "인증 코드 발송에 실패했습니다.");
        } finally{
            setLoading(false);
        }
    };
    const verifyIdentity = async ()=>{
        setLoading(true);
        setError("");
        setMessage("");
        try {
            const response = await fetch(`${apiBaseUrl}/api/auth/recovery/verify-identity`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    recovery_session_token: recoverySessionToken,
                    verification_code: verificationCode.trim()
                })
            });
            const payload = await response.json().catch(()=>({}));
            if (!response.ok) {
                throw new Error(payload.detail || `인증 실패 (HTTP ${response.status})`);
            }
            setResetToken(String(payload.reset_token || ""));
            setStep("complete");
            setMessage(intent === "passkey" ? "본인 확인이 완료되었습니다. 아래에서 이 기기 패스키를 등록하세요." : "본인 확인이 완료되었습니다. 새 비밀번호를 설정하거나 패스키를 등록할 수 있습니다.");
        } catch (e) {
            setError(e.message || "인증 코드 확인에 실패했습니다.");
        } finally{
            setLoading(false);
        }
    };
    const resetPassword = async ()=>{
        setLoading(true);
        setError("");
        setMessage("");
        try {
            const response = await fetch(`${apiBaseUrl}/api/auth/recovery/reset-password`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    scope: recoveryScope,
                    reset_token: resetToken,
                    new_password: newPassword
                })
            });
            const payload = await response.json().catch(()=>({}));
            if (!response.ok) {
                throw new Error(payload.detail || `비밀번호 재설정 실패 (HTTP ${response.status})`);
            }
            setMessage("비밀번호가 재설정되었습니다. 새 비밀번호로 다시 로그인하세요.");
            setResetToken("");
            setVerificationCode("");
            setNewPassword("");
            setStep("request");
        } catch (e) {
            setError(e.message || "비밀번호 재설정에 실패했습니다.");
        } finally{
            setLoading(false);
        }
    };
    const handlePasskeyRegister = async ()=>{
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
                headers: {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    Pragma: "no-cache"
                },
                body: JSON.stringify({
                    email: normalizedEmail,
                    device_label: "이 기기 패스키",
                    recovery_reset_token: resetToken
                }),
                cache: "no-store"
            });
            const startPayload = await startResponse.json().catch(()=>null);
            if (!startResponse.ok || !startPayload) {
                throw new Error(startPayload?.detail || "패스키 등록 시작에 실패했습니다.");
            }
            const publicKeyOptions = normalizePublicKeyOptions(startPayload.options);
            if (!publicKeyOptions) {
                throw new Error("패스키 등록 옵션을 해석하지 못했습니다.");
            }
            const createdCredential = await navigator.credentials.create({
                publicKey: publicKeyOptions
            });
            if (!createdCredential) {
                throw new Error("패스키 등록 결과를 받지 못했습니다.");
            }
            const finishResponse = await fetch("/api/proxy?action=passkey-register-finish", {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    Pragma: "no-cache"
                },
                body: JSON.stringify({
                    registration_token: startPayload.registration_token,
                    credential: {
                        id: createdCredential.id,
                        rawId: encodeArrayBuffer(createdCredential.rawId),
                        type: createdCredential.type,
                        response: createdCredential.response && "attestationObject" in createdCredential.response ? {
                            clientDataJSON: encodeArrayBuffer(createdCredential.response.clientDataJSON),
                            attestationObject: encodeArrayBuffer(createdCredential.response.attestationObject)
                        } : {}
                    }
                }),
                cache: "no-store"
            });
            const finishPayload = await finishResponse.json().catch(()=>null);
            if (!finishResponse.ok || !finishPayload?.registered) {
                throw new Error(finishPayload?.detail || "패스키 등록 완료에 실패했습니다.");
            }
            setMessage("패스키 등록이 완료되었습니다. 다음부터 지문/패스키 로그인을 사용할 수 있습니다.");
            setResetToken("");
            setVerificationCode("");
            setNewPassword("");
            if ("TURBOPACK compile-time truthy", 1) {
                window.setTimeout(()=>{
                    if (mobileReturnUri) {
                        const callback = `${mobileReturnUri}${mobileReturnUri.includes("?") ? "&" : "?"}${new URLSearchParams({
                            auth_mode: "passkey_register",
                            email: normalizedEmail
                        }).toString()}`;
                        window.location.href = callback;
                        return;
                    }
                    window.location.href = returnTo;
                }, 800);
            }
        } catch (err) {
            setError(err?.message || "패스키 등록 중 오류가 발생했습니다.");
        } finally{
            setPasskeyBusy(false);
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex min-h-screen items-center justify-center bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] px-4 font-['Segoe_UI',sans-serif]",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "w-full max-w-[520px] rounded-2xl bg-white px-10 py-12 shadow-[0_20px_60px_rgba(0,0,0,0.2)]",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mb-8 text-center",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "mb-3 inline-flex h-14 w-14 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#667eea,#764ba2)] text-2xl",
                            children: "🔐"
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 293,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                            className: "m-0 text-[22px] font-bold text-[#1a1a2e]",
                            children: title
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 294,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "mt-2 text-sm text-[#666]",
                            children: "로그인 전에 이메일 또는 휴대폰 인증으로 계정을 확인할 수 있습니다."
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 295,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 292,
                    columnNumber: 9
                }, this),
                error && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mb-4 rounded-lg border border-[#ffcccc] bg-[#fff0f0] px-4 py-3 text-sm text-[#cc0000]",
                    children: [
                        "⚠️ ",
                        error
                    ]
                }, void 0, true, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 301,
                    columnNumber: 11
                }, this),
                message && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mb-4 rounded-lg border border-[#cce7d0] bg-[#edf9f0] px-4 py-3 text-sm text-[#216e39]",
                    children: [
                        "✅ ",
                        message
                    ]
                }, void 0, true, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 306,
                    columnNumber: 11
                }, this),
                step === "request" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "space-y-4",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "mb-1.5 block text-[13px] font-semibold text-[#444]",
                                    children: "관리자 이메일"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 314,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                    type: "email",
                                    value: email,
                                    onChange: (e)=>setEmail(e.target.value),
                                    placeholder: "119cash@naver.com",
                                    className: "box-border w-full rounded-lg border-[1.5px] border-[#e0e0e0] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 315,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 313,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "mb-1.5 block text-[13px] font-semibold text-[#444]",
                                    children: "인증 방법"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 325,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "flex gap-2",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                            type: "button",
                                            onClick: ()=>setVerificationChannel("email"),
                                            className: `flex-1 rounded-lg border px-3 py-2 text-sm font-semibold ${verificationChannel === "email" ? "border-[#667eea] bg-[#f4f6ff] text-[#5b67d8]" : "border-[#e0e0e0] bg-white text-[#666]"}`,
                                            children: "이메일"
                                        }, void 0, false, {
                                            fileName: "[project]/app/admin/recovery/page.tsx",
                                            lineNumber: 327,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                            type: "button",
                                            onClick: ()=>setVerificationChannel("phone"),
                                            className: `flex-1 rounded-lg border px-3 py-2 text-sm font-semibold ${verificationChannel === "phone" ? "border-[#667eea] bg-[#f4f6ff] text-[#5b67d8]" : "border-[#e0e0e0] bg-white text-[#666]"}`,
                                            children: "휴대폰(SMS)"
                                        }, void 0, false, {
                                            fileName: "[project]/app/admin/recovery/page.tsx",
                                            lineNumber: 334,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 326,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 324,
                            columnNumber: 13
                        }, this),
                        verificationChannel === "phone" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "mb-1.5 block text-[13px] font-semibold text-[#444]",
                                    children: "휴대폰 번호"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 346,
                                    columnNumber: 17
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                    type: "tel",
                                    value: phoneNumber,
                                    onChange: (e)=>setPhoneNumber(e.target.value),
                                    placeholder: "01012345678",
                                    className: "box-border w-full rounded-lg border-[1.5px] border-[#e0e0e0] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 347,
                                    columnNumber: 17
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "mt-1 text-xs text-[#888]",
                                    children: "계정에 등록된 번호가 있으면 비워도 됩니다."
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 354,
                                    columnNumber: 17
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 345,
                            columnNumber: 15
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            type: "button",
                            onClick: ()=>void startRecovery(),
                            disabled: loading || !email.trim() || verificationChannel === "phone" && !phoneNumber.trim(),
                            className: `w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || !email.trim() ? "bg-[#aaa]" : "bg-[linear-gradient(135deg,#667eea,#764ba2)]"}`,
                            children: loading ? "처리 중..." : "인증 코드 받기"
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 358,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 312,
                    columnNumber: 11
                }, this),
                step === "verify" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "space-y-4",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4 text-sm text-[#4d5588]",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "font-semibold text-[#2f376d]",
                                    children: "인증 코드 입력"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 372,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "mt-1 text-xs",
                                    children: maskedTarget ? `${maskedTarget}(으)로 발송된 6자리 코드를 입력하세요.` : "발송된 6자리 코드를 입력하세요."
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 373,
                                    columnNumber: 15
                                }, this),
                                devOtpHint && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "mt-2 rounded-lg bg-[#fff8e6] px-3 py-2 text-xs text-[#8a6d00]",
                                    children: [
                                        "개발 환경 힌트: ",
                                        devOtpHint
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 377,
                                    columnNumber: 17
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 371,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                            type: "text",
                            inputMode: "numeric",
                            value: verificationCode,
                            onChange: (e)=>setVerificationCode(e.target.value),
                            placeholder: "123456",
                            maxLength: 6,
                            className: "box-border w-full rounded-lg border-[1.5px] border-[#d9def7] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 382,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            type: "button",
                            onClick: ()=>void verifyIdentity(),
                            disabled: loading || verificationCode.trim().length < 6,
                            className: `w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || verificationCode.trim().length < 6 ? "bg-[#aaa]" : "bg-[linear-gradient(135deg,#667eea,#764ba2)]"}`,
                            children: loading ? "확인 중..." : "인증 확인"
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 391,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            type: "button",
                            onClick: ()=>{
                                setStep("request");
                                setVerificationCode("");
                                setMessage("");
                            },
                            className: "w-full rounded-lg border border-[#ddd] bg-white px-4 py-3 text-sm font-semibold text-[#666]",
                            children: "처음으로"
                        }, void 0, false, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 399,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 370,
                    columnNumber: 11
                }, this),
                step === "complete" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "space-y-4",
                    children: [
                        intent !== "passkey" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "mb-2 text-sm font-semibold text-[#2f376d]",
                                    children: "새 비밀번호 설정"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 417,
                                    columnNumber: 17
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                    id: "admin-recovery-new-password",
                                    name: "newPassword",
                                    type: "password",
                                    autoComplete: "new-password",
                                    value: newPassword,
                                    onChange: (e)=>setNewPassword(e.target.value),
                                    placeholder: "새 비밀번호 (8자 이상)",
                                    className: "box-border w-full rounded-lg border-[1.5px] border-[#d9def7] px-[14px] py-3 text-[15px] outline-none transition-colors focus:border-[#667eea]"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 418,
                                    columnNumber: 17
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    type: "button",
                                    onClick: ()=>void resetPassword(),
                                    disabled: loading || !resetToken || newPassword.length < 8,
                                    className: `mt-3 w-full rounded-lg border-none px-4 py-[14px] text-base font-semibold text-white ${loading || !resetToken || newPassword.length < 8 ? "bg-[#aaa]" : "bg-[#238636]"}`,
                                    children: "비밀번호 재설정"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 428,
                                    columnNumber: 17
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 416,
                            columnNumber: 15
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "rounded-xl border border-[#ececff] bg-[#f8f9ff] px-4 py-4",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "mb-2 text-sm font-semibold text-[#2f376d]",
                                    children: "이 기기 패스키 등록"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 440,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "mb-3 text-xs text-[#6b7399]",
                                    children: "인증이 완료되었으므로 비밀번호 없이도 이 기기에 패스키를 등록할 수 있습니다."
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 441,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    type: "button",
                                    onClick: ()=>void handlePasskeyRegister(),
                                    disabled: !passkeyReady || passkeyBusy || !resetToken,
                                    "data-testid": "admin-recovery-passkey-register",
                                    className: `w-full rounded-lg border px-4 py-[14px] text-base font-semibold ${passkeyReady && resetToken ? "border-[#764ba2] bg-white text-[#764ba2] hover:bg-[#f7f0ff]" : "cursor-not-allowed border-[#d8d8e8] bg-[#f4f4f8] text-[#9c9cb0]"}`,
                                    children: passkeyBusy ? "⏳ 패스키 등록 중..." : "🪪 이 기기 패스키 등록"
                                }, void 0, false, {
                                    fileName: "[project]/app/admin/recovery/page.tsx",
                                    lineNumber: 444,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/app/admin/recovery/page.tsx",
                            lineNumber: 439,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 414,
                    columnNumber: 11
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "mt-6 text-center text-sm",
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                        href: returnTo,
                        className: "font-medium text-[#5b67d8] underline underline-offset-2",
                        children: "로그인으로 돌아가기"
                    }, void 0, false, {
                        fileName: "[project]/app/admin/recovery/page.tsx",
                        lineNumber: 458,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/app/admin/recovery/page.tsx",
                    lineNumber: 457,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/app/admin/recovery/page.tsx",
            lineNumber: 291,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/app/admin/recovery/page.tsx",
        lineNumber: 290,
        columnNumber: 5
    }, this);
}
_s(AdminRecoveryPageContent, "YGy3TGq7z1tdiYPnIa8nMqomkZ8=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useSearchParams"]
    ];
});
_c = AdminRecoveryPageContent;
function AdminRecoveryPage() {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Suspense"], {
        fallback: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex min-h-screen items-center justify-center bg-[linear-gradient(135deg,#667eea_0%,#764ba2_100%)] px-4 text-sm text-white",
            children: "복구 화면을 불러오는 중..."
        }, void 0, false, {
            fileName: "[project]/app/admin/recovery/page.tsx",
            lineNumber: 469,
            columnNumber: 25
        }, this),
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(AdminRecoveryPageContent, {}, void 0, false, {
            fileName: "[project]/app/admin/recovery/page.tsx",
            lineNumber: 470,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/app/admin/recovery/page.tsx",
        lineNumber: 469,
        columnNumber: 5
    }, this);
}
_c1 = AdminRecoveryPage;
var _c, _c1;
__turbopack_context__.k.register(_c, "AdminRecoveryPageContent");
__turbopack_context__.k.register(_c1, "AdminRecoveryPage");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=_0.agok6._.js.map