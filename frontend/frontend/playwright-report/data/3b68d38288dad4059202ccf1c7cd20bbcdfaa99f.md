# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: admin.setup.playwright.spec.ts >> create admin storage state
- Location: tests\admin.setup.playwright.spec.ts:39:5

# Error details

```
Error: expect(received).not.toBeNull()

Received: null

Call Log:
- Timeout 15000ms exceeded while waiting on the predicate
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e3]:
    - generic [ref=e4]:
      - generic [ref=e5]: 🛡️
      - heading "관리자 대시보드" [level=1] [ref=e6]
      - paragraph [ref=e7]: 관리자 계정으로 로그인하세요
      - paragraph [ref=e8]: 아이디/비밀번호 기억, 지문/패스키 로그인 사용 여부, 로그인 전 복구 진입 경로를 이 화면에서 바로 확인할 수 있습니다.
    - generic [ref=e9]:
      - generic [ref=e10]:
        - generic [ref=e11]: 이메일
        - textbox "이메일" [ref=e12]:
          - /placeholder: admin@example.com
          - text: 119cash@naver.com
      - generic [ref=e13]:
        - generic [ref=e14]: 비밀번호
        - textbox "비밀번호" [ref=e15]:
          - /placeholder: ••••••••
          - text: space0215@
      - generic [ref=e16]:
        - generic [ref=e17]:
          - checkbox "아이디 기억" [checked] [ref=e18]
          - text: 아이디 기억
        - generic [ref=e19]:
          - checkbox "비밀번호 기억" [ref=e20]
          - text: 비밀번호 기억
        - generic [ref=e21]:
          - checkbox "이 기기에서 지문/패스키 로그인 사용" [checked] [ref=e22]
          - text: 이 기기에서 지문/패스키 로그인 사용
        - paragraph [ref=e23]: 공용 기기에서는 비밀번호 기억을 권장하지 않습니다.
      - button "⏳ 로그인 중..." [disabled] [ref=e24]
      - button "📱 지문/패스키 로그인" [ref=e25] [cursor=pointer]
      - button "🪪 이 기기 패스키 등록" [ref=e26] [cursor=pointer]
      - generic [ref=e27]:
        - link "비밀번호를 잊으셨나요?" [ref=e28] [cursor=pointer]:
          - /url: /admin/recovery
        - link "통신사 본인확인 후 비밀번호 재설정" [ref=e29] [cursor=pointer]:
          - /url: /admin/recovery?mode=carrier
      - generic [ref=e30]:
        - generic [ref=e31]: 로그인 문제 해결 안내
        - list [ref=e32]:
          - listitem [ref=e33]: 관리자 비밀번호를 잊은 경우 로그인 전 복구 페이지에서 재설정 흐름을 시작할 수 있습니다.
          - listitem [ref=e34]: 통신사 본인확인과 패스키(지문/Face ID)는 다음 단계에서 관리자/회원 공통 인증 코어로 연결할 예정입니다.
          - listitem [ref=e35]: 고위험 설정 변경 시 추가 본인확인이 필요할 수 있습니다.
    - paragraph [ref=e36]: DevAnalysis114 Admin v2.2.0
  - alert [ref=e37]
```

# Test source

```ts
  1  | ﻿import * as fs from 'node:fs';
  2  | import * as path from 'node:path';
  3  | import { expect, test } from '@playwright/test';
  4  | 
  5  | const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
  6  | const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
  7  | const STORAGE_STATE_PATH = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
  8  | const PLAYWRIGHT_ADMIN_BASE_URL = (process.env.PLAYWRIGHT_ADMIN_BASE_URL ?? 'http://localhost:3005').replace(/\/$/, '');
  9  | const ADMIN_DASHBOARD_WAIT_MS = 30_000;
  10 | 
  11 | function readExistingAdminToken(): string {
  12 |     try {
  13 |         const raw = fs.readFileSync(STORAGE_STATE_PATH, 'utf-8');
  14 |         const parsed = JSON.parse(raw);
  15 |         const origins = Array.isArray(parsed?.origins) ? parsed.origins : [];
  16 |         for (const origin of origins) {
  17 |             const localStorageItems = Array.isArray(origin?.localStorage) ? origin.localStorage : [];
  18 |             const tokenEntry = localStorageItems.find((item: any) => item?.name === 'admin_token' && typeof item?.value === 'string' && item.value.trim());
  19 |             if (tokenEntry?.value) {
  20 |                 return tokenEntry.value;
  21 |             }
  22 |         }
  23 |     } catch {
  24 |     }
  25 |     return '';
  26 | }
  27 | 
  28 | async function writeStorageStateWithToken(page: any, token: string) {
  29 |     await page.addInitScript((nextToken: string) => {
  30 |         window.localStorage.setItem('admin_token', nextToken);
  31 |     }, token);
  32 |     await page.goto(PLAYWRIGHT_ADMIN_BASE_URL);
  33 |     await page.evaluate((nextToken: string) => {
  34 |         window.localStorage.setItem('admin_token', nextToken);
  35 |     }, token);
  36 |     await page.context().storageState({ path: STORAGE_STATE_PATH });
  37 | }
  38 | 
  39 | test('create admin storage state', async ({ page }) => {
  40 |     test.setTimeout(60_000);
  41 |     fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });
  42 |     if (ADMIN_USERNAME && ADMIN_PASSWORD) {
  43 |         await page.goto('/admin/login');
  44 |         await page.getByTestId('admin-login-email').fill(ADMIN_USERNAME);
  45 |         await page.getByTestId('admin-login-password').fill(ADMIN_PASSWORD);
  46 |         await page.getByTestId('admin-login-submit').click();
> 47 |         await expect.poll(async () => page.evaluate(() => window.localStorage.getItem('admin_token')), {
     |         ^ Error: expect(received).not.toBeNull()
  48 |             timeout: 15000,
  49 |         }).not.toBeNull();
  50 |     } else {
  51 |         const existingToken = readExistingAdminToken();
  52 |         test.skip(!existingToken, 'PLAYWRIGHT_ADMIN_USERNAME / PLAYWRIGHT_ADMIN_PASSWORD 또는 기존 admin_token storageState 필요');
  53 |         await writeStorageStateWithToken(page, existingToken);
  54 |     }
  55 |     await page.goto('/admin');
  56 |     await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
  57 |     await page.getByTestId('admin-topnav-api-docs').waitFor({ timeout: ADMIN_DASHBOARD_WAIT_MS });
  58 |     await page.context().storageState({ path: STORAGE_STATE_PATH });
  59 | });
  60 | 
```