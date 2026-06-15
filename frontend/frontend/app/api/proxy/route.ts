import { NextRequest, NextResponse } from "next/server";
import { ADMIN_PROXY_TIMEOUT_MS } from "@/lib/admin-session";
import { fetchBackendWithFallback, isAbortLike, jsonNoStore } from '@/app/api/_shared/backend-proxy';

const ADMIN_PROXY_RETRYABLE_STATUSES = new Set([502, 503, 504]);
const ADMIN_PROXY_RETRY_ATTEMPTS = 3;
const ADMIN_PROXY_RETRY_DELAY_MS = 700;
const ADMIN_REGRESSION_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1' && process.env.CI === '1' && process.env.NODE_ENV !== 'production';
const ADMIN_REGRESSION_MOCK_TOKEN = 'admin-regression-mock-token';
const ADMIN_REGRESSION_MOCK_USER = {
  username: 'ui.admin.round@devanalysis.local',
  email: 'ui.admin.round@devanalysis.local',
  is_active: true,
  is_admin: true,
  is_superuser: true,
};
const ADMIN_REGRESSION_WEBAUTHN_CHALLENGE = 'YWRtaW4tcmVncmVzc2lvbi1jaGFsbGVuZ2U';
const ADMIN_REGRESSION_WEBAUTHN_USER_ID = 'YWRtaW4tcmVncmVzc2lvbi11c2Vy';

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isHtmlLike(contentType: string | null, bodyText: string): boolean {
  const normalizedType = String(contentType || '').toLowerCase();
  const normalizedBody = String(bodyText || '').trim().toLowerCase();
  return normalizedType.includes('text/html') || normalizedBody.startsWith('<!doctype html') || normalizedBody.startsWith('<html');
}

function parseJsonSafely(text: string) {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

function nowMs() {
  return Date.now();
}

function buildAdminRegressionPasskeyOptions(kind: 'register' | 'login') {
  const common = {
    challenge: ADMIN_REGRESSION_WEBAUTHN_CHALLENGE,
    timeout: 60_000,
    userVerification: 'required',
  };
  if (kind === 'register') {
    return {
      ...common,
      rp: { name: 'Admin Regression' },
      user: {
        id: ADMIN_REGRESSION_WEBAUTHN_USER_ID,
        name: ADMIN_REGRESSION_MOCK_USER.email,
        displayName: 'Admin Regression',
      },
      pubKeyCredParams: [
        { type: 'public-key', alg: -7 },
        { type: 'public-key', alg: -257 },
      ],
      authenticatorSelection: {
        residentKey: 'required',
        requireResidentKey: true,
        userVerification: 'required',
      },
      attestation: 'none',
    };
  }
  return {
    ...common,
    allowCredentials: [],
  };
}

function adminRegressionLoginPayload() {
  return {
    access_token: ADMIN_REGRESSION_MOCK_TOKEN,
    token_type: 'bearer',
    user: ADMIN_REGRESSION_MOCK_USER,
  };
}

async function fetchWithRetry(pathOrUrl: string, init: RequestInit, expectJson = true) {
  const isBackendPath = pathOrUrl.startsWith('/');
  if (isBackendPath) {
    let lastError: unknown = null;
    for (let attempt = 1; attempt <= ADMIN_PROXY_RETRY_ATTEMPTS; attempt += 1) {
      try {
        const result = await fetchBackendWithFallback(pathOrUrl, init, ADMIN_PROXY_TIMEOUT_MS);
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

  let lastResponse: Response | null = null;
  let lastError: unknown = null;

  for (let attempt = 1; attempt <= ADMIN_PROXY_RETRY_ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch(pathOrUrl, {
        ...init,
        cache: 'no-store',
        signal: AbortSignal.timeout(ADMIN_PROXY_TIMEOUT_MS),
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
            invalidHtml: true,
          };
        }
        return {
          target: pathOrUrl,
          response,
          bodyText: text,
          parsedBody: parseJsonSafely(text),
          invalidHtml: false,
        };
      }

      return {
        target: pathOrUrl,
        response,
        bodyText: await response.text(),
        parsedBody: null,
        invalidHtml: false,
      };
    } catch (error) {
      lastError = error;
      if (!isAbortLike(error) || attempt >= ADMIN_PROXY_RETRY_ATTEMPTS) {
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

export async function POST(req: NextRequest) {
  if (ADMIN_REGRESSION_MOCK_BACKEND) {
    return jsonNoStore(adminRegressionLoginPayload(), 200);
  }

  const body = await req.text();
  const requestStartedAt = nowMs();
  try {
    const loginStartedAt = nowMs();
    const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/login', {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    console.info('[admin-proxy-metric]', {
      stage: 'login',
      backend: target,
      status: response.status,
      elapsedMs: nowMs() - loginStartedAt,
      totalElapsedMs: nowMs() - requestStartedAt,
    });

    if (invalidHtml) {
      return jsonNoStore(
        {
          detail: '관리자 로그인 프록시가 백엔드 대신 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
          code: 'ADMIN_PROXY_HTML_RESPONSE',
          backend: target,
        },
        502,
      );
    }

    if (!parsedBody || typeof parsedBody.access_token !== 'string' || !parsedBody.access_token.trim()) {
      if (!response.ok) {
        return jsonNoStore(parsedBody ?? { detail: bodyText || '로그인에 실패했습니다.' }, response.status);
      }
      return jsonNoStore(
        {
          detail: '관리자 로그인 응답에 access_token이 없습니다.',
          code: 'ADMIN_PROXY_INVALID_LOGIN_PAYLOAD',
          backend: target,
        },
        502,
      );
    }

    const meStartedAt = nowMs();
    const meResult = await fetchWithRetry('/api/auth/me', {
      headers: { Authorization: `Bearer ${parsedBody.access_token}` },
    });
    const mePayload = meResult.parsedBody;
    console.info('[admin-proxy-metric]', {
      stage: 'me',
      backend: meResult.target,
      status: meResult.response.status,
      elapsedMs: nowMs() - meStartedAt,
      totalElapsedMs: nowMs() - requestStartedAt,
    });
    if (!meResult.response.ok || !mePayload || typeof mePayload !== 'object') {
      return jsonNoStore(
        {
          detail: '관리자 로그인 후 권한 확인에 실패했습니다.',
          code: 'ADMIN_PROXY_INVALID_ME_PAYLOAD',
          backend: meResult.target,
        },
        meResult.response.ok ? 502 : meResult.response.status,
      );
    }

    console.info('[admin-proxy-metric]', {
      stage: 'post-complete',
      backend: meResult.target,
      status: response.status,
      loginElapsedMs: loginStartedAt - requestStartedAt >= 0 ? nowMs() - loginStartedAt : null,
      totalElapsedMs: nowMs() - requestStartedAt,
    });
    return jsonNoStore({
      ...parsedBody,
      user: mePayload,
    }, response.status);
  } catch (e: any) {
    console.info('[admin-proxy-metric]', {
      stage: 'post-failed',
      backend: e?.target || resolveBackendBaseUrl(),
      elapsedMs: nowMs() - requestStartedAt,
      error: e?.error instanceof Error ? e.error.message : e instanceof Error ? e.message : String(e || 'unknown'),
    });
    const error = e?.error ?? e;
    return jsonNoStore(
      {
        error: isAbortLike(error)
          ? `백엔드 로그인 응답이 ${ADMIN_PROXY_TIMEOUT_MS / 1000}초 안에 오지 않았습니다.`
          : `백엔드 연결 실패: ${error.message}`,
        backend: e?.target || resolveBackendBaseUrl(),
      },
      isAbortLike(error) ? 504 : 502,
    );
  }
}

export async function PATCH(req: NextRequest) {
  const bodyText = await req.text();
  const action = req.nextUrl.searchParams.get('action') || '';
  if (ADMIN_REGRESSION_MOCK_BACKEND) {
    if (action === 'passkey-register-start') {
      return jsonNoStore({
        registration_token: 'admin-regression-registration-token',
        options: buildAdminRegressionPasskeyOptions('register'),
      }, 200);
    }
    if (action === 'passkey-register-finish') {
      return jsonNoStore({ registered: true }, 200);
    }
    if (action === 'passkey-login-start') {
      return jsonNoStore({ options: buildAdminRegressionPasskeyOptions('login') }, 200);
    }
    if (action === 'passkey-login-finish') {
      return jsonNoStore(adminRegressionLoginPayload(), 200);
    }
  }

  const path = action === 'passkey-register-start'
    ? '/api/auth/passkey/register/start'
    : action === 'passkey-register-finish'
      ? '/api/auth/passkey/register/finish'
      : action === 'passkey-login-start'
        ? '/api/auth/passkey/login/start'
        : action === 'passkey-login-finish'
          ? '/api/auth/passkey/login/finish'
          : '';
  if (!path) {
    return jsonNoStore({ detail: '지원하지 않는 관리자 프록시 PATCH action입니다.' }, 400);
  }

  try {
    const { target, response, bodyText: responseText, parsedBody, invalidHtml } = await fetchWithRetry(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: bodyText,
    });
    if (invalidHtml) {
      return jsonNoStore({ detail: '관리자 패스키 프록시가 HTML 응답을 받았습니다.', code: 'ADMIN_PROXY_HTML_RESPONSE', backend: target }, 502);
    }
    return jsonNoStore(parsedBody ?? (responseText ? { detail: responseText } : {}), response.status);
  } catch (e: any) {
    const error = e?.error ?? e;
    return jsonNoStore(
      {
        error: isAbortLike(error)
          ? `패스키 프록시 응답이 ${ADMIN_PROXY_TIMEOUT_MS / 1000}초 안에 오지 않았습니다.`
          : `백엔드 연결 실패: ${error.message}`,
        backend: e?.target || resolveBackendBaseUrl(),
      },
      isAbortLike(error) ? 504 : 502,
    );
  }
}

export async function GET(req: NextRequest) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.trim()) {
    return jsonNoStore({ detail: 'Authorization 헤더가 필요합니다.' }, 401);
  }
  if (ADMIN_REGRESSION_MOCK_BACKEND) {
    if (auth.trim() !== `Bearer ${ADMIN_REGRESSION_MOCK_TOKEN}`) {
      return jsonNoStore({ detail: '관리자 회귀(mock) 토큰이 올바르지 않습니다.' }, 401);
    }
    return jsonNoStore(ADMIN_REGRESSION_MOCK_USER, 200);
  }

  try {
    const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/me', {
      headers: { Authorization: auth },
    });

    if (invalidHtml) {
      return jsonNoStore(
        {
          detail: '관리자 인증 확인 프록시가 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
          code: 'ADMIN_PROXY_HTML_RESPONSE',
          backend: target,
        },
        502,
      );
    }

    if (!parsedBody || typeof parsedBody !== 'object') {
      if (!response.ok) {
        return jsonNoStore({ detail: bodyText || '관리자 정보 조회에 실패했습니다.' }, response.status);
      }
      return jsonNoStore(
        {
          detail: '관리자 인증 확인 응답 형식이 올바르지 않습니다.',
          code: 'ADMIN_PROXY_INVALID_ME_PAYLOAD',
          backend: target,
        },
        502,
      );
    }

    return jsonNoStore(parsedBody, response.status);
  } catch (e: any) {
    const error = e?.error ?? e;
    return jsonNoStore(
      {
        error: isAbortLike(error)
          ? `백엔드 인증 확인 응답이 ${ADMIN_PROXY_TIMEOUT_MS / 1000}초 안에 오지 않았습니다.`
          : `백엔드 연결 실패: ${error.message}`,
      },
      isAbortLike(error) ? 504 : 502,
    );
  }
}

export async function PUT(req: NextRequest) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.trim()) {
    return jsonNoStore({ detail: 'Authorization 헤더가 필요합니다.' }, 401);
  }
  if (ADMIN_REGRESSION_MOCK_BACKEND) {
    if (auth.trim() !== `Bearer ${ADMIN_REGRESSION_MOCK_TOKEN}`) {
      return jsonNoStore({ detail: '관리자 회귀(mock) 토큰이 올바르지 않습니다.' }, 401);
    }
    return jsonNoStore({
      access_token: ADMIN_REGRESSION_MOCK_TOKEN,
      token_type: 'bearer',
    }, 200);
  }

  try {
    const { target, response, bodyText, parsedBody, invalidHtml } = await fetchWithRetry('/api/auth/extend', {
      method: "PUT",
      headers: { Authorization: auth },
    });

    if (invalidHtml) {
      return jsonNoStore(
        {
          detail: '관리자 세션 연장 프록시가 HTML 응답을 받았습니다. 프록시/배포 경로를 확인해주세요.',
          code: 'ADMIN_PROXY_HTML_RESPONSE',
          backend: target,
        },
        502,
      );
    }

    if (!parsedBody || typeof parsedBody.access_token !== 'string' || !parsedBody.access_token.trim()) {
      if (!response.ok) {
        return jsonNoStore(parsedBody ?? { detail: bodyText || '세션 연장에 실패했습니다.' }, response.status);
      }
      return jsonNoStore(
        {
          detail: '세션 연장 응답에 access_token이 없습니다.',
          code: 'ADMIN_PROXY_INVALID_EXTEND_PAYLOAD',
          backend: target,
        },
        502,
      );
    }

    return jsonNoStore(parsedBody, response.status);
  } catch (e: any) {
    const error = e?.error ?? e;
    return jsonNoStore(
      {
        error: isAbortLike(error)
          ? `백엔드 세션 연장 응답이 ${ADMIN_PROXY_TIMEOUT_MS / 1000}초 안에 오지 않았습니다.`
          : `백엔드 연결 실패: ${error.message}`,
        backend: e?.target || resolveBackendBaseUrl(),
      },
      isAbortLike(error) ? 504 : 502,
    );
  }
}

function resolveBackendBaseUrl(): string {
  // 컨테이너 런타임에서는 localhost가 프론트 컨테이너 자신을 가리킬 수 있어 마지막 순위로 내린다.
  const rawCandidates = [
    process.env.BACKEND_PROXY_TARGET,
    process.env.LOCAL_API_BASE_URL,
    process.env.NEXT_PUBLIC_API_URL,
    'http://backend:8000',
    'http://host.docker.internal:8000',
    'http://localhost:8000',
  ];
  const normalized = rawCandidates
    .map((value) => String(value || '').trim().replace(/\/$/, ''))
    .filter(Boolean);
  const unique = [...new Set(normalized)];
  const internalTargets = unique.filter((value) => {
    const lowered = value.toLowerCase();
    return lowered.includes('backend:8000') || lowered.includes('host.docker.internal:8000');
  });
  const nonLocalTargets = unique.filter((value) => !/https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(value));
  const localTargets = unique.filter((value) => /https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(value));
  const ordered = [...new Set([...internalTargets, ...nonLocalTargets, ...localTargets])];
  return ordered[0] || 'http://backend:8000';
}
