import { expect, test } from '@playwright/test';
import { execSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const ADMIN_EMAIL = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '119cash@naver.com';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? 'space0215@';

type PasskeyDbSnapshot = {
    email: string;
    passkey_enabled: boolean;
    passkey_registered: boolean;
    passkey_registered_at: string | null;
    passkey_sign_count: number;
    credential_id_length: number;
    active_sessions: number;
};

type PasskeyNetworkEvent = {
    phase: 'register' | 'login';
    kind: 'request' | 'response' | 'failed';
    action: string;
    url: string;
    method?: string;
    status?: number;
    body?: string;
    error?: string;
};

type PasskeyEvidence = {
    attempt: number;
    captured_at: string;
    email: string;
    db_before: PasskeyDbSnapshot;
    db_after_register: PasskeyDbSnapshot;
    db_after_login: PasskeyDbSnapshot;
    db_after_logout: PasskeyDbSnapshot;
    register: {
        dialog_message: string | null;
        error_message: string;
        requests: PasskeyNetworkEvent[];
    };
    login: {
        error_message: string;
        requests: PasskeyNetworkEvent[];
    };
};

function shellEscapeSingleQuoted(value: string) {
    return `'${String(value).replace(/'/g, `''`)}'`;
}

function resetPasskeyStateForAccount(email: string) {
    const escapedEmail = shellEscapeSingleQuoted(email);
    const psqlBase = 'docker exec devanalysis114-postgres psql -U admin -d devanalysis114';

    // Keep password deterministic for passkey enrollment path that verifies password ownership.
    const safePassword = ADMIN_PASSWORD.replace(/'/g, "\\'");
    const passwordHash = execSync(
        `docker exec devanalysis114-backend python -c "from backend.auth import get_password_hash; print(get_password_hash('${safePassword}'))"`,
        { encoding: 'utf8' },
    ).trim();
    const escapedHash = shellEscapeSingleQuoted(passwordHash);

    execSync(
        `${psqlBase} -c "UPDATE users SET hashed_password = ${escapedHash} WHERE email = ${escapedEmail};"`,
        { stdio: 'ignore' },
    );

    // Reset passkey credential fields and active sessions so each attempt starts from the same state.
    execSync(
        `${psqlBase} -c "UPDATE users SET passkey_enabled = FALSE, passkey_credential_id = NULL, passkey_public_key = NULL, passkey_sign_count = 0, passkey_registered_at = NULL WHERE email = ${escapedEmail}; DELETE FROM user_active_sessions WHERE user_id IN (SELECT id FROM users WHERE email = ${escapedEmail});"`,
        { stdio: 'ignore' },
    );

    const userId = execSync(
        `${psqlBase} -t -A -c "SELECT id FROM users WHERE email = ${escapedEmail} LIMIT 1;"`,
        { encoding: 'utf8' },
    ).trim();

    if (userId) {
        // Session cache key used by backend/auth.py
        try {
            execSync(`docker exec devanalysis114-redis redis-cli -n 0 DEL auth:active_session:${userId}`, { stdio: 'ignore' });
        } catch {
        }
    }
}

function getPasskeyDbSnapshot(email: string): PasskeyDbSnapshot {
    const escapedEmail = shellEscapeSingleQuoted(email);
    const psqlBase = 'docker exec devanalysis114-postgres psql -U admin -d devanalysis114';
    const sql = `select u.email, coalesce(u.passkey_enabled, false)::text as passkey_enabled, (u.passkey_registered_at is not null)::text as passkey_registered, coalesce(u.passkey_registered_at::text, '') as passkey_registered_at, coalesce(u.passkey_sign_count, 0)::text as passkey_sign_count, length(coalesce(u.passkey_credential_id, ''))::text as credential_id_length, count(uas.*)::text as active_sessions from users u left join user_active_sessions uas on uas.user_id = u.id where u.email = ${escapedEmail} group by u.email, u.passkey_enabled, u.passkey_registered_at, u.passkey_sign_count, u.passkey_credential_id;`;
    const raw = execSync(
        `${psqlBase} -t -A -F "|" -c ${JSON.stringify(sql)}`,
        { encoding: 'utf8' },
    ).trim();
    const [
        dbEmail = email,
        passkeyEnabled = 'f',
        passkeyRegistered = 'f',
        passkeyRegisteredAt = '',
        passkeySignCount = '0',
        credentialIdLength = '0',
        activeSessions = '0',
    ] = raw.split('|');

    return {
        email: dbEmail,
        passkey_enabled: passkeyEnabled === 't' || passkeyEnabled === 'true',
        passkey_registered: passkeyRegistered === 't' || passkeyRegistered === 'true',
        passkey_registered_at: passkeyRegisteredAt || null,
        passkey_sign_count: Number(passkeySignCount || 0),
        credential_id_length: Number(credentialIdLength || 0),
        active_sessions: Number(activeSessions || 0),
    };
}

function writePasskeyEvidence(testInfo: import('@playwright/test').TestInfo, evidence: PasskeyEvidence) {
    const outputPath = testInfo.outputPath(`admin-passkey-operational-evidence-attempt-${evidence.attempt}.json`);
    writeFileSync(outputPath, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8');
    console.log('[admin-passkey-operational-evidence]', outputPath);
}

function createPasskeyNetworkCapture(page: import('@playwright/test').Page, phase: 'register' | 'login') {
    const events: PasskeyNetworkEvent[] = [];

    const requestHandler = (request: import('@playwright/test').Request) => {
        const requestUrl = new URL(request.url());
        const action = requestUrl.searchParams.get('action') || '';
        if (requestUrl.pathname !== '/api/proxy' || !action.startsWith(`passkey-${phase}`)) {
            return;
        }
        events.push({
            phase,
            kind: 'request',
            action,
            url: request.url(),
            method: request.method(),
            body: request.postData() || '',
        });
    };

    const responseHandler = async (response: import('@playwright/test').Response) => {
        const responseUrl = new URL(response.url());
        const action = responseUrl.searchParams.get('action') || '';
        if (responseUrl.pathname !== '/api/proxy' || !action.startsWith(`passkey-${phase}`)) {
            return;
        }
        let body = '';
        try {
            body = await response.text();
        } catch {
        }
        events.push({
            phase,
            kind: 'response',
            action,
            url: response.url(),
            status: response.status(),
            body: body.slice(0, 2000),
        });
    };

    const failedHandler = (request: import('@playwright/test').Request) => {
        const requestUrl = new URL(request.url());
        const action = requestUrl.searchParams.get('action') || '';
        if (requestUrl.pathname !== '/api/proxy' || !action.startsWith(`passkey-${phase}`)) {
            return;
        }
        events.push({
            phase,
            kind: 'failed',
            action,
            url: request.url(),
            error: request.failure()?.errorText || 'request failed',
        });
    };

    page.on('request', requestHandler);
    page.on('response', responseHandler);
    page.on('requestfailed', failedHandler);

    return {
        events,
        dispose: () => {
            page.off('request', requestHandler);
            page.off('response', responseHandler);
            page.off('requestfailed', failedHandler);
        },
    };
}

async function ensureLoginForm(page: import('@playwright/test').Page) {
    await page.goto('/admin/login', { waitUntil: 'domcontentloaded' });
    // If a previous session is still active, the app may redirect to /admin first.
    // Log out and return to a stable login-form state for deterministic passkey steps.
    const logoutButton = page.getByTestId('admin-topnav-logout');
    if (await logoutButton.isVisible({ timeout: 1500 }).catch(() => false)) {
        await logoutButton.click();
        await page.waitForURL(/\/admin\/login(?:\/)?(?:\?.*)?$/);
    }
    await expect(page.getByTestId('admin-login-form')).toBeVisible();
}

async function attachVirtualAuthenticator(page: import('@playwright/test').Page) {
    const client = await page.context().newCDPSession(page);
    await client.send('WebAuthn.enable');
    const result = await client.send('WebAuthn.addVirtualAuthenticator', {
        options: {
            protocol: 'ctap2',
            transport: 'internal',
            hasResidentKey: true,
            hasUserVerification: true,
            isUserVerified: true,
            automaticPresenceSimulation: true,
        },
    });
    return {
        client,
        authenticatorId: String(result.authenticatorId),
    };
}

async function registerPasskey(page: import('@playwright/test').Page) {
    await ensureLoginForm(page);
    await page.getByTestId('admin-login-email').fill(ADMIN_EMAIL);
    await page.getByTestId('admin-login-password').fill(ADMIN_PASSWORD);

    const capture = createPasskeyNetworkCapture(page, 'register');
    try {
        const registerResult = await page.evaluate(async ({ email, password }) => {
            const decodeBase64Url = (value: string) => {
                const normalized = String(value || '').replace(/-/g, '+').replace(/_/g, '/');
                const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
                const decoded = window.atob(padded);
                return Uint8Array.from(decoded, (char) => char.charCodeAt(0));
            };

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

            const normalizePublicKeyOptions = (options: any) => ({
                ...options,
                challenge: decodeBase64Url(String(options?.challenge || '')),
                user: options?.user
                    ? {
                        ...options.user,
                        id: decodeBase64Url(String(options.user.id || '')),
                    }
                    : undefined,
                excludeCredentials: Array.isArray(options?.excludeCredentials)
                    ? options.excludeCredentials.map((item: any) => ({ ...item, id: decodeBase64Url(String(item?.id || '')) }))
                    : undefined,
            });

            const startResponse = await fetch('/api/proxy?action=passkey-register-start', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
                body: JSON.stringify({
                    email,
                    device_label: '이 기기 패스키',
                    password,
                }),
                cache: 'no-store',
            });
            const startPayload = await startResponse.json().catch(() => null);
            if (!startResponse.ok || !startPayload?.registration_token || !startPayload?.options) {
                return {
                    ok: false,
                    message: startPayload?.detail || `passkey-register-start failed (${startResponse.status})`,
                };
            }

            const createdCredential = await navigator.credentials.create({
                publicKey: normalizePublicKeyOptions(startPayload.options),
            }) as PublicKeyCredential | null;
            if (!createdCredential) {
                return { ok: false, message: '패스키 등록 결과를 받지 못했습니다.' };
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
                return {
                    ok: false,
                    message: finishPayload?.detail || `passkey-register-finish failed (${finishResponse.status})`,
                };
            }

            return {
                ok: true,
                message: '패스키 등록이 완료되었습니다.',
            };
        }, { email: ADMIN_EMAIL, password: ADMIN_PASSWORD });

        if (!registerResult?.ok) {
            throw new Error(registerResult?.message || '패스키 등록 실패');
        }

        const dialogMessage = String(registerResult.message || '패스키 등록이 완료되었습니다.');
        expect(dialogMessage).toContain('패스키 등록이 완료되었습니다.');

        return {
            dialogMessage,
            errorMessage: '',
            requests: capture.events,
        };
    } finally {
        capture.dispose();
    }
}

async function loginWithPasskey(page: import('@playwright/test').Page) {
    await ensureLoginForm(page);
    await page.getByTestId('admin-login-email').fill(ADMIN_EMAIL);

    const capture = createPasskeyNetworkCapture(page, 'login');
    try {
        const loginResult = await page.evaluate(async (email) => {
            const decodeBase64Url = (value: string) => {
                const normalized = String(value || '').replace(/-/g, '+').replace(/_/g, '/');
                const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
                const decoded = window.atob(padded);
                return Uint8Array.from(decoded, (char) => char.charCodeAt(0));
            };

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

            const normalizePublicKeyOptions = (options: any) => ({
                ...options,
                challenge: decodeBase64Url(String(options?.challenge || '')),
                allowCredentials: Array.isArray(options?.allowCredentials)
                    ? options.allowCredentials.map((item: any) => ({ ...item, id: decodeBase64Url(String(item?.id || '')) }))
                    : undefined,
            });

            const startResponse = await fetch('/api/proxy?action=passkey-login-start', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
                body: JSON.stringify({ email }),
                cache: 'no-store',
            });
            const startPayload = await startResponse.json().catch(() => null);
            if (!startResponse.ok || !startPayload?.options) {
                return {
                    ok: false,
                    message: startPayload?.detail || `passkey-login-start failed (${startResponse.status})`,
                };
            }

            const credential = await navigator.credentials.get({
                publicKey: normalizePublicKeyOptions(startPayload.options),
            }) as PublicKeyCredential | null;

            if (!credential) {
                return { ok: false, message: '패스키 로그인 승인 정보가 반환되지 않았습니다.' };
            }

            const finishResponse = await fetch('/api/proxy?action=passkey-login-finish', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
                body: JSON.stringify({
                    email,
                    credential: {
                        id: credential.id,
                        rawId: encodeArrayBuffer(credential.rawId),
                        type: credential.type,
                        response: credential.response && 'authenticatorData' in credential.response
                            ? {
                                clientDataJSON: encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).clientDataJSON),
                                authenticatorData: encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).authenticatorData),
                                signature: encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).signature),
                                userHandle: (credential.response as AuthenticatorAssertionResponse).userHandle
                                    ? encodeArrayBuffer((credential.response as AuthenticatorAssertionResponse).userHandle as ArrayBuffer)
                                    : null,
                            }
                            : {},
                    },
                }),
                cache: 'no-store',
            });
            const finishPayload = await finishResponse.json().catch(() => null);
            if (!finishResponse.ok || !finishPayload?.access_token) {
                return {
                    ok: false,
                    message: finishPayload?.detail || `passkey-login-finish failed (${finishResponse.status})`,
                };
            }

            localStorage.setItem('admin_token', finishPayload.access_token);
            return { ok: true };
        }, ADMIN_EMAIL);

        if (!loginResult?.ok) {
            return {
                errorMessage: loginResult?.message || '패스키 로그인 완료에 실패했습니다.',
                requests: capture.events,
            };
        }

        await page.goto('/admin', { waitUntil: 'domcontentloaded' });
        const logoutButton = page.getByTestId('admin-topnav-logout');
        const currentUrl = page.url();
        const tokenAvailable = await page.evaluate(() => !!localStorage.getItem('admin_token'));
        const logoutVisible = await logoutButton.isVisible({ timeout: 2000 }).catch(() => false);

        if (!logoutVisible && /\/admin\/login(?:\/)?(?:\?.*)?$/.test(currentUrl) && !tokenAvailable) {
            return {
                errorMessage: '패스키 로그인 완료 후에도 관리자 세션이 확인되지 않았습니다.',
                requests: capture.events,
            };
        }

        return {
            errorMessage: '',
            requests: capture.events,
        };
    } catch (error) {
        return {
            errorMessage: error instanceof Error ? error.message : '패스키 로그인 중 예외가 발생했습니다.',
            requests: capture.events,
        };
    } finally {
        capture.dispose();
    }
}

async function logoutToLogin(page: import('@playwright/test').Page) {
    const logoutButton = page.getByTestId('admin-topnav-logout');
    if (await logoutButton.isVisible({ timeout: 1500 }).catch(() => false)) {
        await logoutButton.click();
    } else {
        await page.evaluate(async () => {
            const token = localStorage.getItem('admin_token') || '';
            if (token) {
                await fetch('/api/proxy', {
                    method: 'DELETE',
                    headers: { Authorization: `Bearer ${token}` },
                    cache: 'no-store',
                }).catch(() => null);
            }
            localStorage.removeItem('admin_token');
        });
        await page.goto('/admin/login', { waitUntil: 'domcontentloaded' });
    }
    await page.waitForURL(/\/admin\/login(?:\/)?(?:\?.*)?$/);
    await expect(page.getByTestId('admin-login-form')).toBeVisible();
}

test.describe('admin passkey operational verification', () => {
    test.describe.configure({ timeout: 120000 });
    test.use({ storageState: { cookies: [], origins: [] } });

    test.beforeEach(() => {
        resetPasskeyStateForAccount(ADMIN_EMAIL);
    });

    test.afterEach(async ({ page }) => {
        // Keep attempts isolated: if a test fails before explicit logout,
        // force a best-effort logout to avoid 409 active-session carryover.
        try {
            await page.goto('/admin', { waitUntil: 'domcontentloaded' });
            const logoutButton = page.getByTestId('admin-topnav-logout');
            if (await logoutButton.isVisible({ timeout: 1500 }).catch(() => false)) {
                await logoutButton.click();
            }
        } catch {
        }
    });

    for (const attempt of [1, 2]) {
        test(`passkey register + login closes operational flow attempt ${attempt}`, async ({ page }, testInfo) => {
            const { client, authenticatorId } = await attachVirtualAuthenticator(page);
            const evidence: PasskeyEvidence = {
                attempt,
                captured_at: new Date().toISOString(),
                email: ADMIN_EMAIL,
                db_before: getPasskeyDbSnapshot(ADMIN_EMAIL),
                db_after_register: getPasskeyDbSnapshot(ADMIN_EMAIL),
                db_after_login: getPasskeyDbSnapshot(ADMIN_EMAIL),
                db_after_logout: getPasskeyDbSnapshot(ADMIN_EMAIL),
                register: {
                    dialog_message: null,
                    error_message: '',
                    requests: [],
                },
                login: {
                    error_message: '',
                    requests: [],
                },
            };

            try {
                const registerResult = await registerPasskey(page);
                evidence.register.dialog_message = registerResult.dialogMessage;
                evidence.register.error_message = registerResult.errorMessage;
                evidence.register.requests = registerResult.requests;
                evidence.db_after_register = getPasskeyDbSnapshot(ADMIN_EMAIL);

                const loginResult = await loginWithPasskey(page);
                evidence.login.error_message = loginResult.errorMessage;
                evidence.login.requests = loginResult.requests;
                if (loginResult.errorMessage) {
                    throw new Error(loginResult.errorMessage);
                }
                evidence.db_after_login = getPasskeyDbSnapshot(ADMIN_EMAIL);

                await logoutToLogin(page);
                evidence.db_after_logout = getPasskeyDbSnapshot(ADMIN_EMAIL);
            } finally {
                writePasskeyEvidence(testInfo, evidence);
                await client.send('WebAuthn.removeVirtualAuthenticator', { authenticatorId }).catch(() => { });
            }
        });
    }
});
