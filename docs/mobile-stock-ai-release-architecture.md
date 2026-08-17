# Mobile Stock AI Release Architecture

## Overview

이 문서는 모바일 네이티브 앱의 배포 자동화와 주문 안전 UX 확장을 위한 구조도와 실행 설계를 고정합니다.

## Architecture Diagram

```mermaid
flowchart TD
    A[Developer] --> B[apps/mobile-stock-ai/scripts/ensure-eas-project-id.mjs]
    B --> C[eas-project-id.json]
    B --> D[.env.local EXPO_PROJECT_ID]
    C --> E[apps/mobile-stock-ai/app.config.ts]
    D --> E
    E --> F[eas build: staging or production]

    G[GitHub Actions workflow_dispatch] --> H[.github/workflows/mobile-eas-build.yml]
    H --> B
    H --> I[eas build --profile staging|production]
    H --> J[eas submit --profile staging|production]

    K[Mobile App Auth Screen] --> L[SecureStore token/header/baseUrl]
    L --> M[Order Screen step1 validate risk/qty/sl]
    M --> N[Order Screen step2 final confirm]
    N --> O[/api/llm/voice/orchestrate]

    K --> P[Download Screen]
    P --> Q[/api/marketplace/download-product]
```

## Release Strategy

- staging
  - 목적: 내부 테스트 배포, 빠른 검증
  - EAS profile: staging
  - Android: apk internal distribution
  - Submit: 선택 실행
- production
  - 목적: 실제 운영 배포
  - EAS profile: production
  - autoIncrement 활성
  - Submit 전 Gate: version/changelog/approval 자동 검증 통과 필수
  - Submit: release 대상 스토어 제출

## EXPO_PROJECT_ID Automation Flow

1. 스크립트 실행: apps/mobile-stock-ai/scripts/ensure-eas-project-id.mjs
2. 기존 연결 정보 조회: eas project:info
3. 미연결 시 project:init 수행
4. 최종 projectId를 eas-project-id.json 저장
5. .env.local의 EXPO_PROJECT_ID 갱신
6. app.config.ts가 env 우선, 파일 fallback으로 로드

## Dynamic Config Hardening

1. app.config.ts에서 placeholder projectId(전체 0 UUID)를 무시
2. owner를 parkcheolhong으로 고정
3. updates.url / runtimeVersion.policy(appVersion) 동적 설정 반영
4. 손절 하드게이트 값을 EXPO_PUBLIC_MAX_STOP_LOSS_PERCENT로 외부화

## Order Safety UX Flow

1. 1단계 검증

- 리스크 비율, 수량, 손절 비율 검증
- 숫자 조건 실패 시 주문 차단
- 하드게이트: 손절 비율이 EXPO_PUBLIC_MAX_STOP_LOSS_PERCENT 초과 시 즉시 차단
- 기본값: EXPO_PUBLIC_MAX_STOP_LOSS_PERCENT 미설정 시 2

1. 2단계 최종 확인

- 최종 확인 스위치 ON 전까지 최종 주문 버튼 비활성
- 최종 주문 시 위험 파라미터를 payload에 함께 첨부
- 실행 직전에도 손절 2% 초과 여부를 다시 검사하여 이중 차단

## Command References

- ensure project id
  - npm --prefix apps/mobile-stock-ai run eas:project:ensure
- staging build
  - npm run build:mobile:android:staging
  - npm run build:mobile:ios:staging
- production build
  - npm run build:mobile:android:production
  - npm run build:mobile:ios:production
- staging submit
  - npm run submit:mobile:android:staging
  - npm run submit:mobile:ios:staging
- production submit
  - npm run submit:mobile:ios:production
- production submit dry-run check
  - npm --prefix apps/mobile-stock-ai run release:dry-run:production-submit
