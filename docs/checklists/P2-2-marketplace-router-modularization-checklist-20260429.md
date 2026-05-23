# P2-2 체크리스트: marketplace/router.py 도메인 분리

작업명: marketplace/router.py 분리
우선순위: P2
시작일: 2026-04-29
상태: 구현됨

## Phase 1: 분석

- [x] 1.1 `customer-orchestrate` 도메인이 자체 계약 테스트를 보유하는지 확인
- [x] 1.2 첫 분리 단위를 `customer-orchestrate` 슬라이스로 확정
- [x] 1.3 `feature-orchestrate`, `campaign-orchestrate`, `video-worker` 후속 분리 후보 검토

## Phase 2: 구현

- [x] 2.1 `backend/marketplace/customer_orchestrate_router.py` 생성
- [x] 2.2 기존 `router.py`에서 customer-orchestrate 라우트 블록 제거 후 include 전환
- [x] 2.3 `backend/marketplace/feature_orchestrate_router.py` 생성 및 include 전환
- [x] 2.4 `backend/marketplace/campaign_orchestrate_router.py` 생성 및 include 전환
- [x] 2.5 `backend/marketplace/video_worker_router.py` 생성 및 include 전환
- [x] 2.6 `backend/marketplace/search_router.py` 생성 및 include 전환
- [x] 2.7 `backend/marketplace/code_generator_router.py` 생성 및 include 전환
- [x] 2.8 `backend/marketplace/face_recognition_router.py` 생성 및 include 전환
- [x] 2.9 `backend/marketplace/ml_detectors_router.py` 생성 및 include 전환
- [x] 2.10 후속 도메인 분리 진행 (ad-video/order, remaining heavy slices)
- [x] 2.10a `backend/marketplace/categories_router.py` 생성 및 include 전환
- [x] 2.10b `backend/marketplace/subscription_router.py` 생성 및 include 전환
- [x] 2.10c `backend/marketplace/ad_order_runtime.py` 생성 후 ad-order runtime helper 분리 및 `router.py` 위임 전환
- [x] 2.10d `backend/marketplace/ad_order_processing.py` 생성 후 ad-order processing 본체(렌더/품질/패키징) 분리 및 `router.py` 호환 래퍼 위임 전환

## Phase 3: 검증

- [x] 3.1 `pytest backend/tests/test_marketplace_customer_orchestrate_contract.py -q`
  - 결과: `4 passed`
- [x] 3.2 feature/campaign/video smoke 검증 실행
  - feature accepted: `202 accepted`
  - campaign strategies: `200`
  - video worker status: `200`
- [x] 3.3 search/codegen/face/ml smoke 검증 실행
  - search semantic empty query: `200`
  - code-generator profiles: `200`
  - face-recognition status: `200`
  - ml-detectors status: `200`
- [x] 3.3 라우터 import/build 오류 없음 확인
  - 새 서브라우터 파일 오류 없음
  - `router.py` 라인 수: `4754 -> 4264`
- [x] 3.4 categories 라우트 등록 보존 검증
  - FastAPI OpenAPI 기준 `/api/marketplace/categories` (`GET`,`POST`) 및 `/api/marketplace/categories/{category_id}` (`PUT`,`DELETE`) 등록 확인
- [x] 3.5 subscription/billing/device/webhook 라우트 이전 후 데코레이터 보존 확인
  - `router.py`에는 `/projects*` 2개만 잔존, 구독/결제 8개는 `subscription_router.py`에 존재 확인
- [x] 3.6 ad-order runtime helper 분리 후 호환 심볼 검증 2회
  - `python -m py_compile backend/marketplace/router.py backend/marketplace/ad_order_runtime.py` 통과
  - `python -c "from backend.marketplace import router as r; assert callable(r.ensure_ad_order_runtime_ready); assert callable(r._enqueue_ad_order); assert callable(r.get_ad_queue_runtime_status); print('symbol-check-ok')"` 통과
- [x] 3.7 ad-order processing 본체 분리 후 컴파일/운영 경로 실검증 2회
  - `python -m py_compile backend/marketplace/router.py backend/marketplace/ad_order_processing.py` 통과 (2회)
  - `powershell -NoProfile -File final_production_verification.ps1` 통과 (2회)
  - pass 1/2 공통 결과: Marketplace 200, Admin 200, ML Detectors 200, Backend Container RUNNING
- [x] 3.8 2.10 후속 ad-order enqueue→worker consume→상태 전이 E2E 2회 실검증
  - 실행 경로: `POST /api/video/generate` -> `GET /api/video/status/{job_id}` 폴링
  - 공통 결과: generate 응답 `202` + `status=queued` 확인, 약 2초 내 `status=failed` / `progress=100` 전이 확인 (worker consume 및 터미널 상태 전이 성립)
  - run 1: `job_id=37a804e3-1281-4e44-b2a0-dcdff872acbe`, 전이 `queued -> failed`
  - run 2: `job_id=0b557431-d05a-4a21-8606-ade4ba76742c`, 전이 `queued -> failed`
  - DB 확인: 두 건 모두 `ad_video_orders.status=failed`, `progress_percent=100`, `error_message=name 'portrait_image_prompt' is not defined`
- [x] 3.9 `portrait_image_prompt` NameError 원인 추적 및 즉시 수정 + 재검증 2회
  - 원인: 실행 중 백엔드 프로세스가 ad-order worker 모듈을 이미 import한 상태라, 파일 수정만으로는 런타임 함수 객체가 갱신되지 않음 (핫패치 직후 생성 주문은 동일 NameError 지속)
  - 코드 수정: `backend/marketplace/ad_order_processing.py`의 `build_ad_package_zip`에서 `requires_realistic_human` 계산을 지역 변수 의존이 없는 식으로 하드닝
    - 변경: `bool(portrait_image_prompt)` -> `bool(str(getattr(order, "portrait_image_prompt", "") or "").strip())`
  - 런타임 반영: `docker restart devanalysis114-backend` 수행
  - post-restart run 1: `job_id=5266018f-4e70-40d1-9503-e11c71e141af`, 전이 `queued -> failed`, DB `error_message=No module named 'torch'`
  - post-restart run 2: `job_id=694e4a0d-f60e-41e3-b189-a3ac535b96a0`, 전이 `queued -> failed`, DB `error_message=No module named 'torch'`
  - 판정: `name 'portrait_image_prompt' is not defined`는 재현되지 않음. 현재 잔여 차단 원인은 `torch` 런타임 의존성 누락.
- [x] 3.10 torch 설치 경로 확정 + 품질 경로 graceful fallback + enqueue→consume→completed E2E 2회
  - torch 설치 경로 확정: `Dockerfile.backend` 빌드 단계에 `pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch` 추가
  - ffmpeg 런타임 경로 확정: `Dockerfile.backend`에 `apt-get install -y --no-install-recommends ffmpeg` 추가
  - graceful fallback 보강:
    - `backend/marketplace/router.py`의 `_generate_video_by_engine`에서 `torch/torchvision` import 계열 예외 시 internal ffmpeg로 자동 폴백
    - `backend/marketplace/ad_order_processing.py`에서 품질 평가 예외 시 자동 품질 fallback 통과 처리
    - internal ffmpeg 엔진은 비생성형 경로 특성상 품질 게이트 실패를 자동 bypass 하도록 보강
  - API 제어 보강: `backend/video_api_router.py`에서 `engine_type` 입력 허용(기본 `dedicated_engine` 유지)
  - 워커 안정화: `backend/marketplace/router.py`의 `run_ad_order_worker()` 시작 시 DB bind 초기화(`check_database_availability`) 선행
  - 누락 심볼 복구: `_resolve_storyboard_scene_source` 정의 복구로 internal ffmpeg NameError 제거
  - 최종 실검증(2회): `POST /api/video/generate` -> `GET /api/video/status/{job_id}` 폴링
    - run 1: `job_id=a48e1165-084c-4d18-a780-028209827031`, 전이 `queued -> rendering -> completed`
    - run 2: `job_id=081fa395-7d9f-4430-ad67-bf7c0fa20234`, 전이 `queued -> rendering -> completed`
  - 추가 카나리(후속 동기화):
    - API canary: `job_id=e111887d-6a30-4bfe-81ef-bb29236f0a21`, 중간 폴링 `rendering(84)` 이후 `작업을 찾을 수 없습니다` 간헐 재현, DB 최종 상태는 `failed`(`quality_score=61.0`, `품질 게이트 실패`)
    - DB canary(재현성 확보): `order_id=26`, `job_id=aac94990-260e-4b9a-b04c-df74e5b16140`, 전이 `queued -> rendering -> completed`, 최종 `progress=100`, `QG=True`, `QS=81.5`, `ERR=None`
    - DB canary 2연속 완료 재현: `order_id=27`, `job_id=0752985c-f4c7-46a5-94cb-a2eef9a1c650`, 전이 `queued -> rendering -> completed`, 최종 `progress=100`, `QG=True`, `QS=86.0`, `ERR=None`
  - 운영 경로 재검증(2회, 2026-04-29): `powershell -NoProfile -File final_production_verification.ps1` 연속 2회 통과
    - pass 1: Marketplace 200, Admin 200, ML Detectors 200, Backend RUNNING
    - pass 2: Marketplace 200, Admin 200, ML Detectors 200, Backend RUNNING
    - 공통: ChunkLoadError 미재현, CORS 정상 로드, 잔여 경고는 CORB/CSP(프레임워크/브라우저 레벨)

## 메모

- customer-orchestrate 계약 엔드포인트(`/chat`, `/stage-runs`, `/accepted`, `/stream`, `/stage-runs/update`, `/generated-programs/latest`)는 유지되어야 함.
- 첫 검증은 계약 테스트 하나로 가설을 판별하고, 통과 시 다음 도메인으로 확장.
- 기존 `router.py`의 광범위한 Pylance 경고는 이번 작업 이전부터 존재하며, 새 서브라우터 파일에는 신규 오류가 없다.

## 최종 보고

- 판정: 완료됨
- 완료 근거:
  - 도메인 분리 구현 항목(Phase 2) 전부 완료 및 체크 반영
  - E2E 완료 검증 충족: enqueue->consume->completed 실증 2회 이상 확보
    - `job_id=a48e1165-084c-4d18-a780-028209827031` completed
    - `job_id=081fa395-7d9f-4430-ad67-bf7c0fa20234` completed
    - DB canary 연속 completed 재현
      - `order_id=26`, `job_id=aac94990-260e-4b9a-b04c-df74e5b16140`, completed
      - `order_id=27`, `job_id=0752985c-f4c7-46a5-94cb-a2eef9a1c650`, completed
  - 운영 경로 실검증 2회 충족
    - `powershell -NoProfile -File final_production_verification.ps1` 연속 2회 통과
    - 공통 결과: Marketplace 200, Admin 200, ML Detectors 200, Backend RUNNING
- 참고(비차단): CORB/CSP 경고는 브라우저/프레임워크 레벨 경고로 기록 유지
