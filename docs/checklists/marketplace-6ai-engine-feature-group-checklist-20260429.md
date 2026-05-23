# 마켓플레이스 AI 엔진 기능군 체크리스트 (2026-04-29)

## 목적

- 요청 범위: AI 엑셀 엔진, AI 이미지 엔진, AI 영상 엔진, AI 문서작성 엔진, AI 음악만들기 엔진, 추가 AI 파워포인트 엔진
- 현재 구현 상태를 즉시 점검하고, 기능군별로 다음 구현 항목을 분리한다.

## 점검 기준

- 상태 값은 `구현됨`, `실패`만 사용한다.
- 이 문서는 코드/설정 정적 검토 기준이며, 실행 검증은 별도 단계로 분리한다.

## 기능군 A. 마켓플레이스 상품 진열/랜딩

- [x] 구현됨: 7개 고정 상품 카드가 마켓 메인에 노출됨 (엑셀/이미지/영상/문서/음악/주식/파워포인트)
- [x] 구현됨: 상세 랜딩 라우트 맵에 파워포인트까지 포함해 엔진 랜딩이 연결됨

근거 파일

- [frontend/frontend/app/marketplace/page.tsx](frontend/frontend/app/marketplace/page.tsx)
- [frontend/frontend/app/marketplace/[id]/page.tsx](frontend/frontend/app/marketplace/[id]/page.tsx)

## 기능군 B. 팝업 오케스트레이터 UI 메타/프리셋

- [x] 구현됨: `ai-sheet`, `ai-image`, `ai-video`, `ai-document`, `ai-music`, `ai-powerpoint` 메타/프리셋 존재

근거 파일

- [frontend/frontend/hooks/use-feature-orchestrator.ts](frontend/frontend/hooks/use-feature-orchestrator.ts)

## 기능군 C. 백엔드 feature catalog/API 라우팅

- [x] 구현됨: feature catalog API와 accept/stream/poll 라우팅 존재
- [x] 구현됨: runtime catalog에 `ai-powerpoint`가 추가됨
- [x] 구현됨: `get_service`에서 `ai-sheet`, `ai-powerpoint` 디스패치 지원

근거 파일

- [backend/marketplace/router.py](backend/marketplace/router.py#L185)
- [backend/marketplace/feature_orchestrate_router.py](backend/marketplace/feature_orchestrate_router.py)

## 기능군 D. 엔진 레지스트리/실행 계층

- [x] 구현됨: 엔진 레지스트리에 스프레드시트/이미지/음악/문서/영상/파워포인트 클래스 존재
- [x] 구현됨: 프런트 feature_id(`ai-*`) 기준 runtime service 디스패치가 6종 모두 직접 연결됨
- [x] 구현됨: 파워포인트 엔진 클래스/레지스트리 항목 추가

근거 파일

- [backend/marketplace/feature_orchestrator/engines/__init__.py](backend/marketplace/feature_orchestrator/engines/__init__.py)
- [backend/marketplace/feature_orchestrator/services/orchestrator_service.py](backend/marketplace/feature_orchestrator/services/orchestrator_service.py)

## 기능군 E. 산출물 품질/다운로드

- [x] 구현됨: 엑셀 엔진은 preview schema + final xlsx/csv 패키지까지 구현
- [x] 구현됨: 이미지/음악/문서/영상 엔진도 preview + final 산출물 파일 생성 및 delivery-assets 다운로드 경로를 구현
- [x] 구현됨: 파워포인트 산출물(pptx) 생성/다운로드 파이프라인 추가

근거 파일

- [backend/marketplace/feature_orchestrator/engines/spreadsheet_generation_engine.py](backend/marketplace/feature_orchestrator/engines/spreadsheet_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/image_generation_engine.py](backend/marketplace/feature_orchestrator/engines/image_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/music_generation_engine.py](backend/marketplace/feature_orchestrator/engines/music_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/document_generation_engine.py](backend/marketplace/feature_orchestrator/engines/document_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/video_generation_engine.py](backend/marketplace/feature_orchestrator/engines/video_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/powerpoint_generation_engine.py](backend/marketplace/feature_orchestrator/engines/powerpoint_generation_engine.py)

## 기능군 F. 테스트/문서 정합성

- [x] 구현됨: 상품 수/타이틀 테스트 기대값을 최신 UI(7가지 AI 엔진)로 동기화
- [x] 구현됨: 파워포인트 엔진 popup e2e( preview → final → download ) 추가
- [x] 구현됨: 관리자/고객 오케스트레이터 브리지 기반 ai-powerpoint 선택 통합 시나리오 추가
- [x] 구현됨: ai-powerpoint 전용 2개 Playwright 시나리오를 동일 조건으로 2회 연속 통과
- [x] 구현됨: 6종 상품군 브라우저 smoke(launcher→popup→preview/final→download 패널) 통과
- [x] 구현됨: feature catalog API 응답(6종/enabled) 검증 테스트 추가 및 통과

근거 파일

- [frontend/frontend/tests/marketplace-generator-products.playwright.spec.ts](frontend/frontend/tests/marketplace-generator-products.playwright.spec.ts)
- [frontend/frontend/app/marketplace/page.tsx](frontend/frontend/app/marketplace/page.tsx#L437)
- [frontend/frontend/tests/marketplace-liveview-ai-powerpoint-launcher.playwright.spec.ts](frontend/frontend/tests/marketplace-liveview-ai-powerpoint-launcher.playwright.spec.ts)
- [frontend/frontend/tests/marketplace-orchestrator-ai-powerpoint-bridge.playwright.spec.ts](frontend/frontend/tests/marketplace-orchestrator-ai-powerpoint-bridge.playwright.spec.ts)
- [frontend/frontend/tests/marketplace-liveview-6feature-browser-smoke.playwright.spec.ts](frontend/frontend/tests/marketplace-liveview-6feature-browser-smoke.playwright.spec.ts)
- [frontend/frontend/tests/marketplace-feature-catalog-api.playwright.spec.ts](frontend/frontend/tests/marketplace-feature-catalog-api.playwright.spec.ts)
- [backend/marketplace/router.py](backend/marketplace/router.py)
- [backend/marketplace/feature_orchestrator/engines/image_generation_engine.py](backend/marketplace/feature_orchestrator/engines/image_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/video_generation_engine.py](backend/marketplace/feature_orchestrator/engines/video_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/document_generation_engine.py](backend/marketplace/feature_orchestrator/engines/document_generation_engine.py)
- [backend/marketplace/feature_orchestrator/engines/music_generation_engine.py](backend/marketplace/feature_orchestrator/engines/music_generation_engine.py)

실검증 기록

- 1차: `PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:3010` 기준 2개 테스트 모두 통과
- 2차: 동일 명령 재실행 시 2개 테스트 모두 통과
- 브라우저 6종 smoke: `marketplace-liveview-6feature-browser-smoke.playwright.spec.ts` 1회 통과
- API 카탈로그 검증: `marketplace-feature-catalog-api.playwright.spec.ts` 1회 통과
- 백엔드 6종 실행/다운로드 스모크: `ai-sheet/ai-image/ai-video/ai-document/ai-music/ai-powerpoint` 모두 PASS

## 즉시 구현 백로그 (기능군별)

1. 상품 진열

- [x] 구현됨: 파워포인트 상품을 7번째로 추가하고 slug(`powerpoint`) / 상품 id(`powerpoint-deck-builder`)를 확정

1. 오케스트레이터 UI

- [x] 구현됨: `ai-powerpoint` meta/preset/template/chips/stat 카드 추가
- [x] 구현됨: 상세 랜딩 페이지 `ENGINE_LANDING_MAP`에 powerpoint 항목 추가

1. 백엔드 catalog/service

- [x] 구현됨: `_FEATURE_CATALOG`에 `ai-powerpoint`를 추가
- [x] 구현됨: `get_service`에 feature_id별 런타임 디스패치(`ai-sheet`, `ai-powerpoint`) 적용

1. 엔진 구현

- [x] 구현됨: `PowerPointGenerationEngine`(preview/final/quality/manifest) 신규 추가
- [x] 구현됨: 기존 4개(이미지/영상/문서/음악)를 실제 산출물/다운로드 경로로 승격

1. 정합성 테스트

- [x] 구현됨: 상품 개수/타이틀 e2e 업데이트
- [x] 구현됨: feature catalog API 응답 검증 테스트 추가
- [x] 구현됨: `ai-powerpoint` preview→final→download 경로 테스트 추가
- [x] 구현됨: admin-llm 브리지 payload 기반 고객 오케스트레이터 ai-powerpoint 선택 테스트 추가
- [x] 구현됨: 6종 상품군 브라우저 smoke 테스트 추가 및 통과

## 이번 점검 결론

- 전체 상태: `구현됨`
- 잔여 메모:
  - 관리자 `/admin` 경로에서 별도 hook-order 오류 로그가 관측됨(본 6종 상품군 범위와 분리 이슈)
