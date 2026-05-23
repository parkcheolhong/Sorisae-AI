module.exports = [
"[externals]/next/dist/build/adapter/setup-node-env.external.js [external] (next/dist/build/adapter/setup-node-env.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/build/adapter/setup-node-env.external.js", () => require("next/dist/build/adapter/setup-node-env.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/lib/incremental-cache/tags-manifest.external.js [external] (next/dist/server/lib/incremental-cache/tags-manifest.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/lib/incremental-cache/tags-manifest.external.js", () => require("next/dist/server/lib/incremental-cache/tags-manifest.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/node:async_hooks [external] (node:async_hooks, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("node:async_hooks", () => require("node:async_hooks"));

module.exports = mod;
}),
"[externals]/path [external] (path, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("path", () => require("path"));

module.exports = mod;
}),
"[externals]/next/dist/server/lib/incremental-cache/memory-cache.external.js [external] (next/dist/server/lib/incremental-cache/memory-cache.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/lib/incremental-cache/memory-cache.external.js", () => require("next/dist/server/lib/incremental-cache/memory-cache.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/lib/incremental-cache/shared-cache-controls.external.js [external] (next/dist/server/lib/incremental-cache/shared-cache-controls.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/lib/incremental-cache/shared-cache-controls.external.js", () => require("next/dist/server/lib/incremental-cache/shared-cache-controls.external.js"));

module.exports = mod;
}),
"[externals]/crypto [external] (crypto, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("crypto", () => require("crypto"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[project]/proxy.ts [middleware] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "config",
    ()=>config,
    "proxy",
    ()=>proxy
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$middleware$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/server.js [middleware] (ecmascript)");
;
const BLOCKED_POST_PATHS = new Set([
    '/api/server-actions',
    '/submit'
]);
const NO_STORE_VALUE = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0';
const FRONTEND_BUILD_ID = process.env.NEXT_PUBLIC_FRONTEND_BUILD_ID || process.env.CODEAI_FRONTEND_BUILD_ID || 'unknown-build';
function isAdminHost(request) {
    const host = request.headers.get('host') ?? '';
    return host.startsWith('admin.') || host.endsWith(':3005');
}
function isStaticAssetPath(pathname) {
    if (pathname.startsWith('/_next/') || pathname.startsWith('/admin/_next/')) {
        return true;
    }
    if (pathname === '/favicon.ico') {
        return true;
    }
    return /\.(?:js|mjs|css|map|json|txt|svg|png|jpg|jpeg|gif|webp|ico|woff|woff2|ttf|eot)$/i.test(pathname);
}
function applyNoStoreHeaders(response) {
    response.headers.set('Cache-Control', NO_STORE_VALUE);
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');
    response.headers.set('Surrogate-Control', 'no-store');
    response.headers.set('x-frontend-shell-cache-policy', 'no-store');
    response.headers.set('x-frontend-build-id', FRONTEND_BUILD_ID);
    response.headers.set('x-frontend-build-marker', 'codeai-frontend');
    return response;
}
function shouldApplyNoStore(pathname) {
    return pathname.startsWith('/admin') || pathname.startsWith('/marketplace') || pathname === '/privacy' || pathname === '/terms';
}
function proxy(request) {
    const hasNextActionHeader = request.headers.has('next-action');
    const pathname = request.nextUrl.pathname;
    // Static assets must bypass admin host redirects to keep client bundles loadable.
    if (isStaticAssetPath(pathname)) {
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$middleware$5d$__$28$ecmascript$29$__["NextResponse"].next();
    }
    // 현재 앱은 서버 액션을 사용하지 않으므로, 오래된 배포/외부 스캔 요청은 진입 전에 차단한다.
    if (request.method === 'POST' && (hasNextActionHeader || BLOCKED_POST_PATHS.has(pathname))) {
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$middleware$5d$__$28$ecmascript$29$__["NextResponse"].json({
            detail: '지원하지 않는 서버 액션 또는 비정상 폼 제출 요청입니다. 페이지를 새로고침한 뒤 다시 시도해주세요.',
            code: 'STALE_OR_INVALID_SERVER_ACTION'
        }, {
            status: 410,
            headers: {
                'Cache-Control': 'no-store',
                'x-codeai-blocked-reason': hasNextActionHeader ? 'invalid-next-action' : 'blocked-post-path'
            }
        });
    }
    if (!isAdminHost(request)) {
        const response = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$middleware$5d$__$28$ecmascript$29$__["NextResponse"].next();
        return shouldApplyNoStore(pathname) ? applyNoStoreHeaders(response) : response;
    }
    if (pathname.startsWith('/admin/_next') || pathname.startsWith('/_next') || pathname.startsWith('/admin') || pathname.startsWith('/marketplace') || pathname.startsWith('/marketplace/orchestrator') || pathname.startsWith('/api')) {
        const response = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$middleware$5d$__$28$ecmascript$29$__["NextResponse"].next();
        return shouldApplyNoStore(pathname) ? applyNoStoreHeaders(response) : response;
    }
    const url = request.nextUrl.clone();
    url.pathname = '/admin';
    url.search = '';
    return applyNoStoreHeaders(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$middleware$5d$__$28$ecmascript$29$__["NextResponse"].redirect(url));
}
const config = {
    matcher: [
        '/((?!_next/image).*)'
    ]
};
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__0u0ygru._.js.map