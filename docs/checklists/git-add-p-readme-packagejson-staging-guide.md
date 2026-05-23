# git add -p README/package.json Staging Guide

## 목적
`README.md`와 `frontend/frontend/package.json`에서 `git add -p`를 사용할 때, 현재 추천한 커밋 순서에 맞춰 `y / n / s / e` 중 무엇을 눌러야 하는지 한 번에 따라갈 수 있도록 정리한 가이드입니다.

## 기준 커밋 순서
1. 테스트/검증 흐름 커밋
2. CI 집계 커밋
3. README 문서 커밋

---

## 1. 테스트/검증 흐름 커밋

### 대상
- `frontend/frontend/package.json`
- README는 아직 stage 하지 않음

### 실행
```powershell
git add -p frontend/frontend/package.json
```

### package.json에서 기대하는 결과
이 커밋에는 아래만 들어가야 합니다.

- `test:popup-ui-interactions`
- `test:marketplace-liveview-sheet`
- `verify:popup-ui`
- `verify:marketplace-liveview`
- `e2e` / `e2e:headed`의 `playwright.config.cjs` 전환
- `e2e:marketplace-popup-interactions`
- `e2e:marketplace-popup-interactions:webserver`
- `e2e:marketplace-liveview*`

이 커밋에는 아래가 들어가면 안 됩니다.

- `verify:marketplace-playwright`
- `ci:marketplace`

### 입력 시나리오
#### 경우 A. scripts 블록이 큰 hunk 하나로 나오면
- 입력: `e`
- 이유: CI 집계 2줄만 제외하고 테스트 흐름만 stage 해야 함

편집창에서 아래 줄은 **남깁니다**.

```diff
+        "test:popup-ui-interactions": "powershell -ExecutionPolicy Bypass -File ./scripts/run-marketplace-popup-interactions.ps1",
+        "test:marketplace-liveview-sheet": "powershell -ExecutionPolicy Bypass -File ./scripts/run-marketplace-liveview-sheet.ps1",
+        "verify:popup-ui": "npm run verify && npm run test:popup-ui-interactions",
+        "verify:marketplace-liveview": "npm run verify && npm run test:marketplace-liveview-sheet",
-        "e2e": "playwright test -c playwright.config.ts",
+        "e2e": "playwright test -c playwright.config.cjs",
-        "e2e:headed": "playwright test -c playwright.config.ts --headed",
+        "e2e:headed": "playwright test -c playwright.config.cjs --headed",
+        "e2e:marketplace-popup-interactions": "playwright test -c playwright.marketplace.config.ts tests/marketplace-popup-interactions.playwright.spec.ts --project chromium",
+        "e2e:marketplace-popup-interactions:webserver": "set PLAYWRIGHT_USE_WEBSERVER=1&& playwright test -c playwright.marketplace.config.ts tests/marketplace-popup-interactions.playwright.spec.ts --project chromium",
-        "e2e:marketplace-liveview": "playwright test -c playwright.config.ts tests/marketplace-liveview-ai-image.playwright.spec.ts --project chromium --no-deps",
+        "e2e:marketplace-liveview": "playwright test -c playwright.config.cjs tests/marketplace-liveview-ai-image.playwright.spec.ts --project chromium --no-deps",
-        "e2e:marketplace-liveview:sheet": "playwright test -c playwright.config.ts tests/marketplace-liveview-ai-sheet-launcher.playwright.spec.ts --project chromium --no-deps",
+        "e2e:marketplace-liveview:sheet": "playwright test -c playwright.config.cjs tests/marketplace-liveview-ai-sheet-launcher.playwright.spec.ts --project chromium --no-deps",
-        "e2e:marketplace-liveview:launcher": "playwright test -c playwright.config.ts tests/marketplace-liveview-ai-image-launcher.playwright.spec.ts --project chromium --no-deps",
+        "e2e:marketplace-liveview:launcher": "playwright test -c playwright.config.cjs tests/marketplace-liveview-ai-image-launcher.playwright.spec.ts --project chromium --no-deps",
-        "e2e:marketplace-liveview:all": "playwright test -c playwright.config.ts tests/marketplace-liveview-ai-image.playwright.spec.ts tests/marketplace-liveview-ai-image-launcher.playwright.spec.ts --project chromium --no-deps"
+        "e2e:marketplace-liveview:all": "playwright test -c playwright.config.cjs tests/marketplace-liveview-ai-image.playwright.spec.ts tests/marketplace-liveview-ai-image-launcher.playwright.spec.ts --project chromium --no-deps"
```

편집창에서 아래 줄은 **지웁니다**.

```diff
+        "verify:marketplace-playwright": "npm run verify:popup-ui && npm run test:marketplace-liveview-sheet",
+        "ci:marketplace": "npm run verify:marketplace-playwright",
```

#### 경우 B. hunk가 split 되어 popup/liveview 관련만 따로 나오면
- 입력: `y`

#### 경우 C. CI 2줄만 있는 hunk가 같이 나오면
- 입력: `n`

### 확인
```powershell
git diff --staged -- frontend/frontend/package.json
```

---

## 2. CI 집계 커밋

### 대상
- `frontend/frontend/package.json`
- README는 아직 stage 하지 않아도 됨

### 실행
```powershell
git add -p frontend/frontend/package.json
```

### 이 커밋에 들어가야 하는 것
- `verify:marketplace-playwright`
- `ci:marketplace`

### 입력 시나리오
#### 경우 A. 아래 2줄만 있는 hunk가 나오면
```diff
+        "verify:marketplace-playwright": "npm run verify:popup-ui && npm run test:marketplace-liveview-sheet",
+        "ci:marketplace": "npm run verify:marketplace-playwright",
```
- 입력: `y`

#### 경우 B. 다른 줄까지 섞여 있으면
- 먼저 `s`
- split 되면 CI 2줄 hunk에서 `y`, 나머지는 `n`
- split 이 안 되면 `e`

`e` 편집 시에는 아래만 남깁니다.

```diff
+        "verify:marketplace-playwright": "npm run verify:popup-ui && npm run test:marketplace-liveview-sheet",
+        "ci:marketplace": "npm run verify:marketplace-playwright",
```

### 확인
```powershell
git diff --staged -- frontend/frontend/package.json
```

---

## 3. README 문서 커밋

### 대상
- `README.md`

### 실행
```powershell
git add -p README.md
```

### 이 커밋에 들어가야 하는 것
- `### Marketplace Playwright 검증 명령`
- 표의 4개 명령
- 운영 메모 2줄

### 입력 시나리오
#### 경우 A. Marketplace Playwright 검증 명령 섹션만 hunk로 나오면
- 입력: `y`

예상되는 핵심 hunk 내용:

```diff
+### Marketplace Playwright 검증 명령
+
+`frontend/frontend` 기준으로 아래 명령을 사용합니다.
+
+| 목적 | 표준 명령 | 비고 |
+|---|---|---|
+| 기본 프론트 검증 | `npm --prefix frontend/frontend run verify` | build + smoke + normalizer + popup section contract |
+| popup UI 상호작용 포함 검증 | `npm --prefix frontend/frontend run verify:popup-ui` | production build/start 서버 재사용 + popup interaction Playwright |
+| marketplace liveview 검증 | `npm --prefix frontend/frontend run verify:marketplace-liveview` | production build/start 서버 재사용 + liveview sheet Playwright |
+| CI용 marketplace 상위 검증 | `npm --prefix frontend/frontend run ci:marketplace` | popup UI + liveview Playwright를 한 번에 실행 |
+
+운영 메모:
+
+- popup UI / liveview Playwright는 `next dev`가 아니라 production `build/start` 서버를 외부에서 기동·재사용하는 흐름을 기준으로 정식화되어 있습니다.
+- CI에서는 `npm --prefix frontend/frontend run ci:marketplace`를 표준 명령으로 사용하면 popup interaction과 liveview sheet 검증을 같은 흐름으로 실행할 수 있습니다.
```

#### 경우 B. hunk가 너무 크게 섞여 나오면
- 먼저 `s`
- split 후 Marketplace Playwright 섹션 hunk에서 `y`
- 나머지는 `n`

#### 경우 C. `s`가 안 되면
- 입력: `e`
- 아래 섹션만 남기고 다른 `+` 줄은 지움

남겨야 하는 줄:

```diff
+### Marketplace Playwright 검증 명령
+
+`frontend/frontend` 기준으로 아래 명령을 사용합니다.
+
+| 목적 | 표준 명령 | 비고 |
+|---|---|---|
+| 기본 프론트 검증 | `npm --prefix frontend/frontend run verify` | build + smoke + normalizer + popup section contract |
+| popup UI 상호작용 포함 검증 | `npm --prefix frontend/frontend run verify:popup-ui` | production build/start 서버 재사용 + popup interaction Playwright |
+| marketplace liveview 검증 | `npm --prefix frontend/frontend run verify:marketplace-liveview` | production build/start 서버 재사용 + liveview sheet Playwright |
+| CI용 marketplace 상위 검증 | `npm --prefix frontend/frontend run ci:marketplace` | popup UI + liveview Playwright를 한 번에 실행 |
+
+운영 메모:
+
+- popup UI / liveview Playwright는 `next dev`가 아니라 production `build/start` 서버를 외부에서 기동·재사용하는 흐름을 기준으로 정식화되어 있습니다.
+- CI에서는 `npm --prefix frontend/frontend run ci:marketplace`를 표준 명령으로 사용하면 popup interaction과 liveview sheet 검증을 같은 흐름으로 실행할 수 있습니다.
```

### 확인
```powershell
git diff --staged -- README.md
```

---

## 빠른 요약

### package.json
- 테스트/검증 커밋: `e` 권장, CI 2줄 삭제
- CI 커밋: CI 2줄 hunk면 `y`

### README
- Marketplace Playwright 섹션 hunk면 `y`
- 너무 크면 `s`
- split 안 되면 `e`

---

## 잘못 stage 했을 때
```powershell
git restore --staged README.md
git restore --staged frontend/frontend/package.json
```

다시 시작:
```powershell
git add -p README.md
git add -p frontend/frontend/package.json
```
