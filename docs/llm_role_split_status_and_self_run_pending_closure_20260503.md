# LLM 코딩봇 역할 분리도 상태 요약 + self-run pending_approval 정리 근거

작성일: 2026-05-03

## 1) 역할 분리도 (Planner / Generator / Verifier / Gatekeeper)

### Planner
- 위치 근거:
  - backend/admin_router.py:1600
  - backend/admin_router.py:1604
  - backend/admin_router.py:2455
- 상태 요약:
  - planner 모델 키(LLM_MODEL_PLANNER, LLM_MODEL_SMART_PLANNER) 분리 운영 구조가 코드에 반영됨.
  - self-run task 구성에서 planner 설계 결과와 auto_generator 산출물 경로 일관성 유지 지침이 포함됨.

### Generator
- 위치 근거:
  - backend/admin_router.py:1838
  - backend/admin_router.py:1842
  - backend/generators/facade.py:363
- 상태 요약:
  - python_code_generator / non_python_code_generator / multi_code_generator 프로파일이 분리됨.
  - 다중 생성기 매트릭스와 체크리스트 산출 경로가 분리되어 있음.

### Verifier
- 위치 근거:
  - backend/admin_router.py:2369
  - backend/admin_router.py:2798
  - backend/admin_router.py:2900
- 상태 요약:
  - Verifier→Generator 재시도 루프(최대 3회)와 smoke test(py_compile/pytest 맥락 포함)가 구현됨.
  - 승인 전 검증 함수(run_admin_approval_validation)와 연결되어 terminal gate 이전 품질 점검 수행.

### Gatekeeper
- 위치 근거:
  - backend/admin_router.py:2324
  - backend/admin_router.py:3298
  - backend/admin/orchestrator/self_run_approval_service.py:199
- 상태 요약:
  - approval gate 필드 충족 여부를 _is_self_run_approval_ready로 검사.
  - pending_approval 상태에서만 approve 경로 진입 허용.
  - source 변경 충돌, 변경 파일 부재, 재검증 실패 시 승인 차단.

---

## 2) self-run pending_approval 경고 닫기 실행 근거

### 실행 1: 최신 self-run 기록 조회
- API: GET /api/admin/workspace-self-run-record?latest=true
- 결과: 204 (기록 없음)

### 실행 2: pending 정리 normalize 실행
- API: POST /api/admin/workspace-self-run-record/normalize
- Body: {"cleanup_only": true}
- 결과: 200 / action=noop / "정리 대상 최신 self-run 실패 기록이 없습니다."

### 실행 3: 최신 기록 재조회
- API: GET /api/admin/workspace-self-run-record?latest=true
- 결과: 204 (기록 없음)

### 실행 4: pending 전용 재수집 확인
- API: GET /api/admin/workspace-self-run-record?latest=true&pending_only=true
- 결과: 204 (pending 기록 없음)

---

## 3) 결론

- pending_approval 경고는 현재 런타임 API 기준으로 닫힌 상태임.
- 경고가 화면에 남아 있다면, 캐시된 요약/스냅샷 데이터(stale document or cached diagnostics)일 가능성이 높음.
- 후속 권장:
  1. 상태 배너/요약 패널 갱신 시 pending_only 조회 결과를 우선 반영
  2. stale summary 문서 갱신 타임스탬프를 UI에 노출
  3. normalize(cleanup_only=true) 결과를 운영 이벤트 로그에 남겨 UI 경고 해제 근거로 사용
