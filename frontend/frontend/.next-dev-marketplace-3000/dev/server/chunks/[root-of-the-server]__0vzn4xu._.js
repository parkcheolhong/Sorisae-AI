module.exports = [
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[project]/lib/admin-session.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ADMIN_PROXY_TIMEOUT_MS",
    ()=>ADMIN_PROXY_TIMEOUT_MS,
    "ADMIN_SESSION_CHECK_INTERVAL_MS",
    ()=>ADMIN_SESSION_CHECK_INTERVAL_MS,
    "ADMIN_SESSION_WARNING_WINDOW_MS",
    ()=>ADMIN_SESSION_WARNING_WINDOW_MS,
    "clearAdminToken",
    ()=>clearAdminToken,
    "extendAdminSessionToken",
    ()=>extendAdminSessionToken,
    "getAdminToken",
    ()=>getAdminToken,
    "getAdminTokenExpiryMs",
    ()=>getAdminTokenExpiryMs,
    "getRemainingSessionMinutes",
    ()=>getRemainingSessionMinutes,
    "logoutAdminSession",
    ()=>logoutAdminSession,
    "resolveAdminAccessToken",
    ()=>resolveAdminAccessToken,
    "setAdminToken",
    ()=>setAdminToken
]);
const ADMIN_PROXY_TIMEOUT_MS = 20_000;
const ADMIN_SESSION_WARNING_WINDOW_MS = 5 * 60 * 1000;
const ADMIN_SESSION_CHECK_INTERVAL_MS = 30 * 1000;
function decodeBase64Url(value) {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + (4 - normalized.length % 4) % 4, '=');
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    return Buffer.from(padded, 'base64').toString('utf-8');
}
function canUseBrowserStorage() {
    return ("TURBOPACK compile-time value", "undefined") !== 'undefined' && typeof localStorage !== 'undefined';
}
function getAdminToken() {
    if (!canUseBrowserStorage()) {
        return '';
    }
    //TURBOPACK unreachable
    ;
}
function resolveAdminAccessToken() {
    const adminToken = getAdminToken();
    if (adminToken) {
        return adminToken;
    }
    if (!canUseBrowserStorage()) {
        return '';
    }
    //TURBOPACK unreachable
    ;
}
function setAdminToken(token) {
    if (!canUseBrowserStorage()) {
        return;
    }
    //TURBOPACK unreachable
    ;
}
function clearAdminToken() {
    if (!canUseBrowserStorage()) {
        return;
    }
    //TURBOPACK unreachable
    ;
}
async function logoutAdminSession(currentToken = getAdminToken()) {
    const token = currentToken.trim();
    if (!token) {
        return;
    }
    const response = await fetch('/api/proxy', {
        method: 'DELETE',
        headers: {
            Authorization: `Bearer ${token}`
        }
    });
    if (response.status === 401 || response.status === 403) {
        return;
    }
    if (!response.ok) {
        const raw = await response.text();
        let payload = null;
        try {
            payload = raw ? JSON.parse(raw) : null;
        } catch  {
            payload = raw;
        }
        if (payload && typeof payload.detail === 'string' && payload.detail.trim()) {
            throw new Error(payload.detail);
        }
        if (payload && typeof payload.error === 'string' && payload.error.trim()) {
            throw new Error(payload.error);
        }
        if (typeof payload === 'string' && payload.trim()) {
            throw new Error(payload);
        }
        throw new Error(`로그아웃 실패 (HTTP ${response.status})`);
    }
}
function getAdminTokenExpiryMs(token) {
    if (!token) {
        return null;
    }
    const segments = token.split('.');
    if (segments.length < 2) {
        return null;
    }
    try {
        const payload = JSON.parse(decodeBase64Url(segments[1]));
        const exp = payload?.exp;
        if (typeof exp !== 'number' || !Number.isFinite(exp)) {
            return null;
        }
        return exp * 1000;
    } catch  {
        return null;
    }
}
function getRemainingSessionMinutes(expiryMs) {
    return Math.max(1, Math.ceil((expiryMs - Date.now()) / 60000));
}
async function extendAdminSessionToken(currentToken = getAdminToken()) {
    if (!currentToken) {
        throw new Error('관리자 인증 정보가 없습니다.');
    }
    const response = await fetch('/api/proxy', {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${currentToken}`
        }
    });
    const raw = await response.text();
    let payload = null;
    try {
        payload = raw ? JSON.parse(raw) : null;
    } catch  {
        payload = raw;
    }
    if (!response.ok) {
        if (payload && typeof payload.detail === 'string' && payload.detail.trim()) {
            throw new Error(payload.detail);
        }
        if (payload && typeof payload.error === 'string' && payload.error.trim()) {
            throw new Error(payload.error);
        }
        if (typeof payload === 'string' && payload.trim()) {
            throw new Error(payload);
        }
        throw new Error(`세션 연장 실패 (HTTP ${response.status})`);
    }
    if (!payload || typeof payload.access_token !== 'string' || !payload.access_token.trim()) {
        throw new Error('세션 연장 응답에 access_token이 없습니다.');
    }
    setAdminToken(payload.access_token);
    return payload;
}
}),
"[project]/app/api/_shared/backend-proxy.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "collectBackendTargets",
    ()=>collectBackendTargets,
    "fetchBackendWithFallback",
    ()=>fetchBackendWithFallback,
    "isAbortLike",
    ()=>isAbortLike,
    "jsonNoStore",
    ()=>jsonNoStore,
    "proxyBackendRequest",
    ()=>proxyBackendRequest
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/admin-session.ts [app-route] (ecmascript)");
;
;
const RETRYABLE_STATUSES = new Set([
    502,
    503,
    504
]);
const RETRY_ATTEMPTS_PER_TARGET = 2;
const RETRY_DELAY_MS = 400;
const STATUS_WITHOUT_RESPONSE_BODY = new Set([
    204,
    205,
    304
]);
function resolveTimeoutMs(raw, fallbackMs, minMs, maxMs) {
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
        return fallbackMs;
    }
    return Math.min(maxMs, Math.max(minMs, Math.round(parsed)));
}
const DEFAULT_PROXY_TIMEOUT_MS = resolveTimeoutMs(process.env.BACKEND_PROXY_TIMEOUT_MS, Math.max(30_000, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"]), 5_000, 600_000);
const ORCHESTRATOR_CHAT_PROXY_TIMEOUT_MS = resolveTimeoutMs(process.env.ORCHESTRATOR_CHAT_PROXY_TIMEOUT_MS, 300_000, 30_000, 900_000);
function sleep(ms) {
    return new Promise((resolve)=>setTimeout(resolve, ms));
}
function isAbortLike(error) {
    return error instanceof Error && /abort|timeout/i.test(`${error.name} ${error.message}`);
}
function isHtmlLike(contentType, bodyText) {
    const normalizedType = String(contentType || '').toLowerCase();
    const normalizedBody = String(bodyText || '').trim().toLowerCase();
    return normalizedType.includes('text/html') || normalizedBody.startsWith('<!doctype html') || normalizedBody.startsWith('<html');
}
function parseJsonSafely(text) {
    try {
        return text ? JSON.parse(text) : null;
    } catch  {
        return null;
    }
}
function jsonNoStore(payload, status) {
    if (STATUS_WITHOUT_RESPONSE_BODY.has(status)) {
        return new __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"](null, {
            status,
            headers: {
                'Cache-Control': 'no-store'
            }
        });
    }
    return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(payload, {
        status,
        headers: {
            'Cache-Control': 'no-store'
        }
    });
}
function isContainerLikeRuntime() {
    const markerValues = [
        process.env.DOCKER,
        process.env.CONTAINER,
        process.env.KUBERNETES_SERVICE_HOST
    ].map((value)=>String(value || '').trim().toLowerCase()).filter(Boolean);
    if (markerValues.some((value)=>[
            '1',
            'true',
            'yes'
        ].includes(value))) {
        return true;
    }
    // If internal docker service host is configured, avoid localhost fallback.
    const internalHints = [
        process.env.BACKEND_PROXY_TARGET,
        process.env.LOCAL_API_BASE_URL
    ].map((value)=>String(value || '').trim().toLowerCase()).filter(Boolean);
    return internalHints.some((value)=>value.includes('backend:') || value.includes('host.docker.internal'));
}
function isLocalhostTarget(value) {
    return /https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(value);
}
function collectBackendTargets() {
    const rawTargets = [
        process.env.BACKEND_PROXY_TARGET,
        process.env.LOCAL_API_BASE_URL,
        'http://backend:8000',
        'http://host.docker.internal:8000',
        process.env.NEXT_PUBLIC_API_URL,
        ...isContainerLikeRuntime() ? [] : [
            'http://localhost:8000'
        ]
    ];
    const normalized = rawTargets.map((value)=>String(value || '').trim()).filter(Boolean).map((value)=>value.replace(/\/$/, ''));
    const uniqueTargets = [
        ...new Set(normalized)
    ];
    const allowLocalhostFallback = !isContainerLikeRuntime();
    // In containerized runtime, localhost usually points to frontend-admin itself.
    const internalTargets = uniqueTargets.filter((value)=>{
        const lowered = value.toLowerCase();
        return lowered.includes('backend:8000') || lowered.includes('host.docker.internal:8000');
    });
    const nonLocalTargets = uniqueTargets.filter((value)=>!isLocalhostTarget(value));
    const localhostTargets = allowLocalhostFallback ? uniqueTargets.filter((value)=>isLocalhostTarget(value)) : [];
    return [
        ...new Set([
            ...internalTargets,
            ...nonLocalTargets,
            ...localhostTargets
        ])
    ];
}
function resolveProxyTimeoutForPath(path, timeoutOverrideMs) {
    if (typeof timeoutOverrideMs === 'number' && Number.isFinite(timeoutOverrideMs) && timeoutOverrideMs > 0) {
        return Math.round(timeoutOverrideMs);
    }
    if (path.startsWith('/api/llm/orchestrate/chat') || path.startsWith('/api/llm/autonomous/chat')) {
        return ORCHESTRATOR_CHAT_PROXY_TIMEOUT_MS;
    }
    return DEFAULT_PROXY_TIMEOUT_MS;
}
async function fetchBackendWithFallback(path, init, timeoutMs) {
    const targets = collectBackendTargets();
    let lastError = null;
    let lastTarget = targets[0] || 'http://backend:8000';
    for (const target of targets){
        lastTarget = target;
        const requestUrl = `${target}${path}`;
        for(let attempt = 1; attempt <= RETRY_ATTEMPTS_PER_TARGET; attempt += 1){
            try {
                const response = await fetch(requestUrl, {
                    ...init,
                    cache: 'no-store',
                    signal: AbortSignal.timeout(timeoutMs)
                });
                const bodyText = await response.text();
                const invalidHtml = isHtmlLike(response.headers.get('content-type'), bodyText);
                const parsedBody = parseJsonSafely(bodyText);
                if (invalidHtml) {
                    if (attempt < RETRY_ATTEMPTS_PER_TARGET) {
                        await sleep(RETRY_DELAY_MS * attempt);
                    }
                    continue;
                }
                if (RETRYABLE_STATUSES.has(response.status) && attempt < RETRY_ATTEMPTS_PER_TARGET) {
                    await sleep(RETRY_DELAY_MS * attempt);
                    continue;
                }
                return {
                    target,
                    response,
                    bodyText,
                    parsedBody,
                    invalidHtml
                };
            } catch (error) {
                lastError = error;
                if (attempt < RETRY_ATTEMPTS_PER_TARGET) {
                    await sleep(RETRY_DELAY_MS * attempt);
                    continue;
                }
                break;
            }
        }
    }
    throw {
        target: lastTarget,
        error: lastError
    };
}
function buildForwardHeaders(req) {
    const headers = new Headers();
    req.headers.forEach((value, key)=>{
        const normalized = key.toLowerCase();
        if (normalized === 'host' || normalized === 'connection' || normalized === 'content-length') {
            return;
        }
        headers.set(key, value);
    });
    return headers;
}
async function proxyBackendRequest(req, backendPathWithQuery, options = {}) {
    const label = options.label || '백엔드 프록시';
    const auth = req.headers.get('authorization') || '';
    if (options.requireAuth && !auth.trim()) {
        return jsonNoStore({
            detail: 'Authorization 헤더가 필요합니다.'
        }, 401);
    }
    const method = req.method.toUpperCase();
    const timeoutMs = resolveProxyTimeoutForPath(backendPathWithQuery, options.timeoutMs);
    const headers = buildForwardHeaders(req);
    const body = method === 'GET' || method === 'HEAD' ? undefined : await req.text();
    try {
        const { target, response, bodyText, parsedBody } = await fetchBackendWithFallback(backendPathWithQuery, {
            method,
            headers,
            body
        }, timeoutMs);
        if (STATUS_WITHOUT_RESPONSE_BODY.has(response.status)) {
            return new __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"](null, {
                status: response.status,
                headers: {
                    'Cache-Control': 'no-store',
                    'X-Backend-Target': target
                }
            });
        }
        const contentType = response.headers.get('content-type') || '';
        if (contentType.toLowerCase().includes('application/json')) {
            return jsonNoStore(parsedBody ?? (bodyText ? {
                detail: bodyText
            } : null), response.status);
        }
        return new __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"](bodyText, {
            status: response.status,
            headers: {
                'Cache-Control': 'no-store',
                ...contentType ? {
                    'Content-Type': contentType
                } : {},
                'X-Backend-Target': target
            }
        });
    } catch (wrappedError) {
        const target = String(wrappedError?.target || collectBackendTargets()[0] || 'http://backend:8000');
        const error = wrappedError?.error ?? wrappedError;
        return jsonNoStore({
            detail: isAbortLike(error) ? `${label} upstream timeout (${Math.round(timeoutMs / 1000)}초, target=${target}${backendPathWithQuery})` : `${label} 연결 실패 (target=${target}${backendPathWithQuery}): ${error?.message || String(error || 'unknown')}`,
            error: isAbortLike(error) ? `${label} 응답이 ${Math.round(timeoutMs / 1000)}초 안에 오지 않았습니다.` : `${label} 연결 실패: ${error?.message || String(error || 'unknown')}`,
            backend: target
        }, isAbortLike(error) ? 504 : 502);
    }
}
}),
"[project]/app/api/proxy/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "DELETE",
    ()=>DELETE,
    "GET",
    ()=>GET,
    "PATCH",
    ()=>PATCH,
    "POST",
    ()=>POST,
    "PUT",
    ()=>PUT
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/admin-session.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/app/api/_shared/backend-proxy.ts [app-route] (ecmascript)");
;
;
;
const ADMIN_PROXY_RETRYABLE_STATUSES = new Set([
    502,
    503,
    504
]);
const ADMIN_PROXY_RETRY_ATTEMPTS = 3;
const ADMIN_PROXY_RETRY_DELAY_MS = 700;
function envEnabled(value) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized === '1' || normalized === 'true' || normalized === 'yes';
}
const ADMIN_REGRESSION_MOCK_BACKEND = envEnabled(process.env.ADMIN_REGRESSION_MOCK_BACKEND) && envEnabled(process.env.CI) && ("TURBOPACK compile-time value", "development") !== 'production';
const ADMIN_REGRESSION_MOCK_TOKEN = 'admin-regression-mock-token';
const ADMIN_REGRESSION_MOCK_USER = {
    username: 'ui.admin.round@devanalysis.local',
    email: 'ui.admin.round@devanalysis.local',
    is_active: true,
    is_admin: true,
    is_superuser: true
};
const ADMIN_REGRESSION_WEBAUTHN_CHALLENGE = 'YWRtaW4tcmVncmVzc2lvbi1jaGFsbGVuZ2U';
const ADMIN_REGRESSION_WEBAUTHN_USER_ID = 'YWRtaW4tcmVncmVzc2lvbi11c2Vy';
function delay(ms) {
    return new Promise((resolve)=>setTimeout(resolve, ms));
}
function isHtmlLike(contentType, bodyText) {
    const normalizedType = String(contentType || '').toLowerCase();
    const normalizedBody = String(bodyText || '').trim().toLowerCase();
    return normalizedType.includes('text/html') || normalizedBody.startsWith('<!doctype html') || normalizedBody.startsWith('<html');
}
function parseJsonSafely(text) {
    try {
        return text ? JSON.parse(text) : null;
    } catch  {
        return null;
    }
}
function nowMs() {
    return Date.now();
}
function buildAdminRegressionPasskeyOptions(kind) {
    const common = {
        challenge: ADMIN_REGRESSION_WEBAUTHN_CHALLENGE,
        timeout: 60_000,
        userVerification: 'required'
    };
    if (kind === 'register') {
        return {
            ...common,
            rp: {
                name: 'Admin Regression'
            },
            user: {
                id: ADMIN_REGRESSION_WEBAUTHN_USER_ID,
                name: ADMIN_REGRESSION_MOCK_USER.email,
                displayName: 'Admin Regression'
            },
            pubKeyCredParams: [
                {
                    type: 'public-key',
                    alg: -7
                },
                {
                    type: 'public-key',
                    alg: -257
                }
            ],
            authenticatorSelection: {
                residentKey: 'required',
                requireResidentKey: true,
                userVerification: 'required'
            },
            attestation: 'none'
        };
    }
    return {
        ...common,
        allowCredentials: []
    };
}
function adminRegressionLoginPayload() {
    return {
        access_token: ADMIN_REGRESSION_MOCK_TOKEN,
        token_type: 'bearer',
        user: ADMIN_REGRESSION_MOCK_USER
    };
}
async function fetchWithRetry(pathOrUrl, init, expectJson = true) {
    const isBackendPath = pathOrUrl.startsWith('/');
    if (isBackendPath) {
        let lastError = null;
        for(let attempt = 1; attempt <= ADMIN_PROXY_RETRY_ATTEMPTS; attempt += 1){
            try {
                const result = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["fetchBackendWithFallback"])(pathOrUrl, init, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"]);
                if (result.invalidHtml && attempt < ADMIN_PROXY_RETRY_ATTEMPTS) {
                    await delay(ADMIN_PROXY_RETRY_DELAY_MS * attempt);
                    continue;
                }
                if (ADMIN_PROXY_RETRYABLE_STATUSES.has(result.response.status) && attempt < ADMIN_PROXY_RETRY_ATTEMPTS) {
                    await delay(ADMIN_PROXY_RETRY_DELAY_MS * attempt);
                    continue;
                }
                return result;
            } catch (error) {
                lastError = error;
                if (attempt < ADMIN_PROXY_RETRY_ATTEMPTS) {
                    await delay(ADMIN_PROXY_RETRY_DELAY_MS * attempt);
                    continue;
                }
            }
        }
        throw lastError instanceof Error ? lastError : new Error('관리자 프록시 요청에 실패했습니다.');
    }
    let lastResponse = null;
    let lastError = null;
    for(let attempt = 1; attempt <= ADMIN_PROXY_RETRY_ATTEMPTS; attempt += 1){
        try {
            const response = await fetch(pathOrUrl, {
                ...init,
                cache: 'no-store',
                signal: AbortSignal.timeout(__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"])
            });
            lastResponse = response;
            if (expectJson) {
                const text = await response.text();
                const contentType = response.headers.get('content-type');
                if (isHtmlLike(contentType, text)) {
                    if (attempt < ADMIN_PROXY_RETRY_ATTEMPTS) {
                        await delay(ADMIN_PROXY_RETRY_DELAY_MS * attempt);
                        continue;
                    }
                    return {
                        target: pathOrUrl,
                        response,
                        bodyText: text,
                        parsedBody: null,
                        invalidHtml: true
                    };
                }
                return {
                    target: pathOrUrl,
                    response,
                    bodyText: text,
                    parsedBody: parseJsonSafely(text),
                    invalidHtml: false
                };
            }
            return {
                target: pathOrUrl,
                response,
                bodyText: await response.text(),
                parsedBody: null,
                invalidHtml: false
            };
        } catch (error) {
            lastError = error;
            if (!(0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) || attempt >= ADMIN_PROXY_RETRY_ATTEMPTS) {
                break;
            }
            await delay(ADMIN_PROXY_RETRY_DELAY_MS * attempt);
        }
        if (lastResponse && !ADMIN_PROXY_RETRYABLE_STATUSES.has(lastResponse.status)) {
            break;
        }
    }
    throw lastError instanceof Error ? lastError : new Error('관리자 프록시 요청에 실패했습니다.');
}
async function POST(req) {
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(adminRegressionLoginPayload(), 200);
    }
    const body = await req.text();
    const requestStartedAt = nowMs();
    try {
        const loginStartedAt = nowMs();
        const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/login', {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body
        });
        console.info('[admin-proxy-metric]', {
            stage: 'login',
            backend: target,
            status: response.status,
            elapsedMs: nowMs() - loginStartedAt,
            totalElapsedMs: nowMs() - requestStartedAt
        });
        if (invalidHtml) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 로그인 프록시가 백엔드 대신 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
                code: 'ADMIN_PROXY_HTML_RESPONSE',
                backend: target
            }, 502);
        }
        if (!parsedBody || typeof parsedBody.access_token !== 'string' || !parsedBody.access_token.trim()) {
            if (!response.ok) {
                return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody ?? {
                    detail: bodyText || '로그인에 실패했습니다.'
                }, response.status);
            }
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 로그인 응답에 access_token이 없습니다.',
                code: 'ADMIN_PROXY_INVALID_LOGIN_PAYLOAD',
                backend: target
            }, 502);
        }
        const meStartedAt = nowMs();
        const meResult = await fetchWithRetry('/api/auth/me', {
            headers: {
                Authorization: `Bearer ${parsedBody.access_token}`
            }
        });
        const mePayload = meResult.parsedBody;
        console.info('[admin-proxy-metric]', {
            stage: 'me',
            backend: meResult.target,
            status: meResult.response.status,
            elapsedMs: nowMs() - meStartedAt,
            totalElapsedMs: nowMs() - requestStartedAt
        });
        if (!meResult.response.ok || !mePayload || typeof mePayload !== 'object') {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 로그인 후 권한 확인에 실패했습니다.',
                code: 'ADMIN_PROXY_INVALID_ME_PAYLOAD',
                backend: meResult.target
            }, meResult.response.ok ? 502 : meResult.response.status);
        }
        console.info('[admin-proxy-metric]', {
            stage: 'post-complete',
            backend: meResult.target,
            status: response.status,
            loginElapsedMs: loginStartedAt - requestStartedAt >= 0 ? nowMs() - loginStartedAt : null,
            totalElapsedMs: nowMs() - requestStartedAt
        });
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            ...parsedBody,
            user: mePayload
        }, response.status);
    } catch (e) {
        console.info('[admin-proxy-metric]', {
            stage: 'post-failed',
            backend: e?.target || resolveBackendBaseUrl(),
            elapsedMs: nowMs() - requestStartedAt,
            error: e?.error instanceof Error ? e.error.message : e instanceof Error ? e.message : String(e || 'unknown')
        });
        const error = e?.error ?? e;
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? `백엔드 로그인 응답이 ${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"] / 1000}초 안에 오지 않았습니다.` : `백엔드 연결 실패: ${error.message}`,
            backend: e?.target || resolveBackendBaseUrl()
        }, (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? 504 : 502);
    }
}
async function PATCH(req) {
    const bodyText = await req.text();
    const action = req.nextUrl.searchParams.get('action') || '';
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        if (action === 'passkey-register-start') {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                registration_token: 'admin-regression-registration-token',
                options: buildAdminRegressionPasskeyOptions('register')
            }, 200);
        }
        if (action === 'passkey-register-finish') {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                registered: true
            }, 200);
        }
        if (action === 'passkey-login-start') {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                options: buildAdminRegressionPasskeyOptions('login')
            }, 200);
        }
        if (action === 'passkey-login-finish') {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(adminRegressionLoginPayload(), 200);
        }
    }
    const path = action === 'passkey-register-start' ? '/api/auth/passkey/register/start' : action === 'passkey-register-finish' ? '/api/auth/passkey/register/finish' : action === 'passkey-login-start' ? '/api/auth/passkey/login/start' : action === 'passkey-login-finish' ? '/api/auth/passkey/login/finish' : '';
    if (!path) {
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            detail: '지원하지 않는 관리자 프록시 PATCH action입니다.'
        }, 400);
    }
    try {
        const { target, response, bodyText: responseText, parsedBody, invalidHtml } = await fetchWithRetry(path, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: bodyText
        });
        if (invalidHtml) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 패스키 프록시가 HTML 응답을 받았습니다.',
                code: 'ADMIN_PROXY_HTML_RESPONSE',
                backend: target
            }, 502);
        }
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody ?? (responseText ? {
            detail: responseText
        } : {}), response.status);
    } catch (e) {
        const error = e?.error ?? e;
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? `패스키 프록시 응답이 ${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"] / 1000}초 안에 오지 않았습니다.` : `백엔드 연결 실패: ${error.message}`,
            backend: e?.target || resolveBackendBaseUrl()
        }, (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? 504 : 502);
    }
}
async function GET(req) {
    const auth = req.headers.get("authorization") || "";
    if (!auth.trim()) {
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            detail: 'Authorization 헤더가 필요합니다.'
        }, 401);
    }
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        if (auth.trim() !== `Bearer ${ADMIN_REGRESSION_MOCK_TOKEN}`) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 회귀(mock) 토큰이 올바르지 않습니다.'
            }, 401);
        }
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(ADMIN_REGRESSION_MOCK_USER, 200);
    }
    try {
        const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/me', {
            headers: {
                Authorization: auth
            }
        });
        if (invalidHtml) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 인증 확인 프록시가 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
                code: 'ADMIN_PROXY_HTML_RESPONSE',
                backend: target
            }, 502);
        }
        if (!parsedBody || typeof parsedBody !== 'object') {
            if (!response.ok) {
                return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                    detail: bodyText || '관리자 정보 조회에 실패했습니다.'
                }, response.status);
            }
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 인증 확인 응답 형식이 올바르지 않습니다.',
                code: 'ADMIN_PROXY_INVALID_ME_PAYLOAD',
                backend: target
            }, 502);
        }
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody, response.status);
    } catch (e) {
        const error = e?.error ?? e;
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? `백엔드 인증 확인 응답이 ${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"] / 1000}초 안에 오지 않았습니다.` : `백엔드 연결 실패: ${error.message}`
        }, (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? 504 : 502);
    }
}
async function PUT(req) {
    const auth = req.headers.get("authorization") || "";
    if (!auth.trim()) {
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            detail: 'Authorization 헤더가 필요합니다.'
        }, 401);
    }
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        if (auth.trim() !== `Bearer ${ADMIN_REGRESSION_MOCK_TOKEN}`) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 회귀(mock) 토큰이 올바르지 않습니다.'
            }, 401);
        }
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            access_token: ADMIN_REGRESSION_MOCK_TOKEN,
            token_type: 'bearer'
        }, 200);
    }
    try {
        const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/extend', {
            method: "PUT",
            headers: {
                Authorization: auth
            }
        });
        if (invalidHtml) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 세션 연장 프록시가 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
                code: 'ADMIN_PROXY_HTML_RESPONSE',
                backend: target
            }, 502);
        }
        if (!parsedBody || typeof parsedBody.access_token !== 'string' || !parsedBody.access_token.trim()) {
            if (!response.ok) {
                return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody ?? {
                    detail: bodyText || '세션 연장에 실패했습니다.'
                }, response.status);
            }
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '세션 연장 응답에 access_token이 없습니다.',
                code: 'ADMIN_PROXY_INVALID_EXTEND_PAYLOAD',
                backend: target
            }, 502);
        }
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody, response.status);
    } catch (e) {
        const error = e?.error ?? e;
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? `백엔드 세션 연장 응답이 ${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"] / 1000}초 안에 오지 않았습니다.` : `백엔드 연결 실패: ${error.message}`,
            backend: e?.target || resolveBackendBaseUrl()
        }, (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? 504 : 502);
    }
}
async function DELETE(req) {
    const auth = req.headers.get('authorization') || '';
    if (!auth.trim()) {
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            detail: 'Authorization 헤더가 필요합니다.'
        }, 401);
    }
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        if (auth.trim() !== `Bearer ${ADMIN_REGRESSION_MOCK_TOKEN}`) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 회귀(mock) 토큰이 올바르지 않습니다.'
            }, 401);
        }
        return new __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"](null, {
            status: 204,
            headers: {
                'Cache-Control': 'no-store'
            }
        });
    }
    try {
        const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/logout', {
            method: 'POST',
            headers: {
                Authorization: auth
            }
        });
        if (invalidHtml) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
                detail: '관리자 로그아웃 프록시가 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
                code: 'ADMIN_PROXY_HTML_RESPONSE',
                backend: target
            }, 502);
        }
        if (response.status === 204) {
            return new __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"](null, {
                status: 204,
                headers: {
                    'Cache-Control': 'no-store'
                }
            });
        }
        if (!response.ok) {
            return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody ?? {
                detail: bodyText || '로그아웃에 실패했습니다.'
            }, response.status);
        }
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])(parsedBody ?? {
            ok: true
        }, response.status);
    } catch (e) {
        const error = e?.error ?? e;
        return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["jsonNoStore"])({
            error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? `백엔드 로그아웃 응답이 ${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$admin$2d$session$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ADMIN_PROXY_TIMEOUT_MS"] / 1000}초 안에 오지 않았습니다.` : `백엔드 연결 실패: ${error.message}`,
            backend: e?.target || resolveBackendBaseUrl()
        }, (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$_shared$2f$backend$2d$proxy$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["isAbortLike"])(error) ? 504 : 502);
    }
}
function resolveBackendBaseUrl() {
    // 컨테이너 런타임에서는 localhost가 프론트 컨테이너 자신을 가리킬 수 있어 마지막 순위로 내린다.
    const rawCandidates = [
        process.env.BACKEND_PROXY_TARGET,
        process.env.LOCAL_API_BASE_URL,
        process.env.NEXT_PUBLIC_API_URL,
        'http://backend:8000',
        'http://host.docker.internal:8000',
        'http://localhost:8000'
    ];
    const normalized = rawCandidates.map((value)=>String(value || '').trim().replace(/\/$/, '')).filter(Boolean);
    const unique = [
        ...new Set(normalized)
    ];
    const internalTargets = unique.filter((value)=>{
        const lowered = value.toLowerCase();
        return lowered.includes('backend:8000') || lowered.includes('host.docker.internal:8000');
    });
    const nonLocalTargets = unique.filter((value)=>!/https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(value));
    const localTargets = unique.filter((value)=>/https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(value));
    const ordered = [
        ...new Set([
            ...internalTargets,
            ...nonLocalTargets,
            ...localTargets
        ])
    ];
    return ordered[0] || 'http://backend:8000';
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__0vzn4xu._.js.map