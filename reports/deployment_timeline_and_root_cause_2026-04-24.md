# 배포 타임라인 및 반복 원인 확정 보고서 (2026-04-24)

## 1) 최근 7일 배포 타임라인 증거표

기준 시간대: KST (+09:00)

수집 근거:

- Docker daemon 이벤트: backend 컨테이너 start, die, destroy
- Docker inspect/ps: 이미지 참조, digest, 생성/시작 시각, restart_count
- 세션 트랜스크립트: docker compose up/restart/recreate 및 실검증 결과

| 시각 (KST) | 이벤트 | 이미지 태그/식별자 | compose 동작 | 재기동/상태 근거 |
|---|---|---|---|---|
| 2026-04-23 15:33:33 | backend 빌드/기동 기록 | devanalysis114-backend:latest, manifest sha256:f96e78f2305debdbea44284c7653effa66936490d3052278e8ea9f5712520f53 | docker compose up -d --build backend | 트랜스크립트 이벤트 (assistant/tool/user 기록) |
| 2026-04-24 19:06:55 | 다중 서비스 재빌드 기록 | devanalysis114-backend:latest 외 | docker compose up -d --build backend frontend-admin frontend-marketplace nginx | 트랜스크립트 execution_start 기록 |
| 2026-04-24 21:02:11 | status 복구 세션 시작 | backend 런타임 이미지: devanalysis114-backend | docker compose restart backend 시도 | 직후 probe connection_error/404 관측 |
| 2026-04-24 21:02:35 | backend 재빌드/재기동 | manifest sha256:958cd6366044b9259916f7aaf70e04bcbfb53fa9cbb4f5c319282b89ba5a0e55 | docker compose up -d --build backend | 이후 probe 200/200 및 openapi status 노출 |
| 2026-04-24 21:03:47 ~ 21:04:59 | 마운트 보강 반영 단계 | 동일 이미지 태그 latest | docker compose up -d backend, 이후 force-recreate | /app/app 마운트 최종 반영 확인 |
| 2026-04-24 21:05:00 | backend die/destroy/start | image=devanalysis114-backend | recreate 완료 직후 lifecycle 이벤트 | docker events: die, destroy, start 연속 발생 |
| 2026-04-24 21:05:00 이후 | 최종 정상 상태 | image_ref=devanalysis114-backend, image_id=sha256:958cd6366044b9259916f7aaf70e04bcbfb53fa9cbb4f5c319282b89ba5a0e55 | backend Up, 8000 바인딩 | probe1=200, probe2=200, openapi_has_status=True, restart_count=0 |

### 7일 범위 보강 메모

- Docker events 조회 범위는 2026-04-17 21:09:43 KST ~ 현재 시각으로 실행함.
- daemon 이벤트 버퍼상 backend lifecycle 상세는 2026-04-24 21:05 시점 위주로 확인됨.
- 7일 전체를 완전 복원하려면 Docker daemon 장기 로그(JSON-file/journald) 또는 CI 배포 로그를 별도 보존해야 함.

## 2) 왜 반복됐는지 최종 원인 확정 보고서

### 결론 요약

- 반복 원인은 단일 버그가 아니라, 엔트리포인트 위임 구조 + 마운트 비대칭 + untracked 파일 유입이 겹치며 발생한 운영 반영 불일치다.

### 원인 1: 엔트리포인트 위임 구조로 실제 라우터 등록 지점이 분리됨

- backend 실행 커맨드는 backend.main:app 을 기동함.
- backend.main 은 app.main 을 import 하여 app/create_application 을 위임함.
- 따라서 라우트 누락/추가 판단은 backend/main.py 수정만으로 끝나지 않고 app/main.py 상태에 직접 의존함.

근거 파일:

- backend/main.py
- docker-compose.yml backend command

### 원인 2: 컨테이너 마운트 비대칭으로 app 경로 변경이 런타임에 즉시 반영되지 않음

- 당시 backend 서비스는 /app/backend 는 bind mount였지만 /app/app 은 mount되지 않음.
- 결과: app/main.py 변경 후 단순 restart 시, 런타임이 기대와 다른 소스를 참조하거나 이전 상태를 유지할 수 있었음.
- 조치: backend volumes에 ./app:/app/app 추가 후 force-recreate로 반영 확정.

근거 파일:

- docker-compose.yml volumes

### 원인 3: untracked 파일 유입으로 추적/검증 체계 밖에서 핵심 경로가 변경됨

- git 상태에서 app/main.py, backend/llm/router.py 가 untracked로 존재.
- 핵심 런타임 경로가 tracked 이력 없이 바뀌면, 누가 언제 어떤 변경을 넣었는지 포렌식 난이도가 급상승함.
- 이 상태에서 엔트리포인트 분리/마운트 비대칭이 겹치며 재현성 저하와 반복 장애가 발생함.

근거 명령:

- git status --short -- app/main.py backend/main.py backend/llm/router.py backend/llm/orchestrator.py docker-compose.yml

### 원인 4: 로컬 검증 환경과 컨테이너 런타임 불일치

- 로컬 Python 3.10에서 datetime.UTC import 오류 발생.
- 컨테이너는 Python 3.11로 정상.
- 즉, 로컬 import 검증 실패가 운영 장애 원인 자체는 아니지만, 진단 신호를 혼합시켜 판단 지연을 유발함.

## 3) 최종 조치 및 판정

### 적용 조치

- app/main.py
  - /api/llm/status 라우터 include 복구
  - mandatory_routes 하드게이트 추가 (누락 시 startup fail)
- docker-compose.yml
  - backend volume에 ./app:/app/app 추가
- 운영 검증
  - /api/llm/status 2회 연속 200
  - OpenAPI에 /api/llm/status 노출 확인
  - 컨테이너 내부 create_application 라우트 등록 확인

### 판정

- 구현됨: 예
- 완료됨: 예 (요청 범위인 status 경로 복구 + 2회 실검증 + 재발 원인 확정 보고까지 완료)
- 실패: 아니오

## 4) 재발 방지 고정 권고

1. app/main.py, backend/llm/router.py 를 tracked 상태로 전환하고 PR 필수 경로로 강제
2. backend 기동 전 라우트 하드게이트 유지 (/api/llm/status 누락 시 부팅 실패)
3. compose 운영 기준에서 backend는 app/backend 모두 명시 mount 또는 완전 이미지 방식으로 일원화
4. 배포 타임라인 보존을 위해 Docker events 장기 보관 또는 CI 배포 로그 아카이브 의무화
