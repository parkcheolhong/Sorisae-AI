# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4 file manifest

- task: 오케스트레이터 자가개선 실험 즉시 실행

원본 대상 경로: C:\Users\WORK\source\repos\parkcheolhong\codeAI
실험 복제본 경로: C:\Users\WORK\source\repos\parkcheolhong\codeAI\uploads\tmp\codeai_admin_runtime\admin_self_experiments\codeAI_20260423_045333
실행 모드: full

[반드시 지킬 원칙]
- 1. 대상 폴더 전체 구조와 핵심 파일 연결을 먼저 분석
- 2. 실험 복제본에서 실제 수정과 검증을 수행
- 3. 검증을 통과한 개선 결과물만 승인 대기 대상으로 남김
- 4. 원본 폴더는 승인 전까지 절대 직접 수정하지 않음
- 최종 응답에는 진단 요약, 실험 결과, 검증 결과, 승인 대기용 핵심 변경점을 모두 포함
- 승인 전 단계에서는 원본 폴더를 직접 수정했다고 주장하지 말 것

[선택 주문]
- 주문 템플릿: 디버깅 기반 결함 교정 루프
- 실행 범위: 지정 범위만 구현
- 사용자 주문: INSPECT-023 second live verification
- 위 주문은 현재 self-run 목적보다 우선순위를 침범하지 않는 범위에서 반영할 것

[디버깅 시스템 표준 프로토콜]
- 1단계 결함 식별 및 제거: validation_findings, runtime diagnostics, 보안 위반을 근거로 실제 결함만 식별하고 즉시 제거할 것
- 2단계 시스템 이해도 향상: 결함이 연결된 라우터, 상태, 저장 경로, 호출 체인을 설명 가능한 수준으로 재구성할 것
- 3단계 리스크 관리: 수정 파급 범위, 잠재 회귀, 미검증 영역, 승인 전 위험을 분리 기록할 것
- 4단계 성능 최적화: 결함 제거 후 남는 병목과 자원 낭비만 최적화하고, 기능 회귀를 만들지 말 것

[교정 조치 명령]
INSPECT-023 second live verification

[대상 구조 요약]
- 디렉터리 수: 407
- 파일 수: 1848
- 텍스트/코드 파일 수: 1126
- 분석 컨텍스트 포함 파일 수: 108
- 분석 컨텍스트 문자 수: 179830

[스킵 디렉터리]
- .git
- .playwright-mcp
- .pytest_cache
- .runtime
- .tmp
- .venv
- .venv-arcface310
- .venv.py313
- .venv.py313.20260409_200600.4823f7
- .venv.py313.20260409_201228.6ea186
- .venv.py313.20260418_205442.0184f1
- .venv.py313.cpu-2.10.0.20260418_210038
- .venv.py313.cpu-latest.20260418_205950
- .venv.py313.pypi-2.10.0.20260418_210125
- .venv.torchcheck313
- .venv312
- .venv313
- .vs
- __pycache__
- ai/__pycache__

[구조 프리뷰]
codeAI/
  .git/ [skip]
  .github/
    copilot-instructions.md
  .playwright-mcp/ [skip]
  .pytest_cache/ [skip]
  .runtime/ [skip]
  .tmp/ [skip]
  .venv/ [skip]
  .venv-arcface310/ [skip]
  .venv.py313/ [skip]
  .venv.py313.20260409_200600.4823f7/ [skip]
  .venv.py313.20260409_201228.6ea186/ [skip]
  .venv.py313.20260418_205442.0184f1/ [skip]
  .venv.py313.cpu-2.10.0.20260418_210038/ [skip]
  .venv.py313.cpu-latest.20260418_205950/ [skip]
  .venv.py313.pypi-2.10.0.20260418_210125/ [skip]
  .venv.torchcheck313/ [skip]
  .venv312/ [skip]
  .venv313/ [skip]
  .vs/ [skip]
  __pycache__/ [skip]
  addons/
    go_service/
      cmd/
        app/
          main.go
      internal/
        app/
          app.go
        domain/
          inventory.go
        http/
          handlers/
            health.go
            inventory.go
          router.go
        platform/
          runtime_store.go
        repository/
          inventory_repository.go
        service/
          inventory_service.go
      go.mod
      README.md
    nextjs_react/
      app/
        api/
          brief/
            route.ts
          health/
            route.ts
        dashboard/
          page.tsx
        globals.css
        layout.tsx
        loading.tsx
        page.tsx
      components/
        dashboardclient.tsx
        executionboard.tsx
        focusrail.tsx
        heropanel.tsx
        insighttimeline.tsx
        metriccluster.tsx
        signalmatrix.tsx
        themetoggle.tsx
      lib/
        data.ts
        types.ts
      .gitignore
      next-env.d.ts
      next.config.js
      package.json
      README.md
      tsconfig.json
    node_service/
      src/
        http/
          handlers/
...[중략: 구조 프리뷰가 길어 일부만 포함]

[핵심 텍스트 파일]
- .github/copilot-instructions.md (11698 bytes)
- addons/go_service/README.md (6647 bytes)
- addons/nextjs_react/app/api/brief/route.ts (153 bytes)
- addons/nextjs_react/app/api/health/route.ts (124 bytes)
- addons/nextjs_react/app/dashboard/page.tsx (257 bytes)
- addons/nextjs_react/app/globals.css (7117 bytes)
- addons/nextjs_react/app/layout.tsx (861 bytes)
- addons/nextjs_react/app/loading.tsx (256 bytes)
- addons/nextjs_react/app/page.tsx (248 bytes)
- addons/nextjs_react/components/dashboardclient.tsx (3759 bytes)
- addons/nextjs_react/components/executionboard.tsx (499 bytes)
- addons/nextjs_react/components/focusrail.tsx (648 bytes)
- addons/nextjs_react/components/heropanel.tsx (931 bytes)
- addons/nextjs_react/components/insighttimeline.tsx (502 bytes)
- addons/nextjs_react/components/metriccluster.tsx (590 bytes)
- addons/nextjs_react/components/signalmatrix.tsx (639 bytes)
- addons/nextjs_react/components/themetoggle.tsx (1030 bytes)
- addons/nextjs_react/lib/data.ts (3361 bytes)
- addons/nextjs_react/lib/types.ts (805 bytes)
- addons/nextjs_react/.gitignore (37 bytes)
- ...[중략: 핵심 텍스트 파일 목록이 길어 일부만 포함]

[분석용 파일 본문 컨텍스트 요약]
- 포함 파일 수: 108
- 누락 파일 수: 1
- 원본 컨텍스트 문자 수: 179830
- 컨텍스트 포함 파일에는 실행에 필요한 최소한의 소스 코드만 담길 것
- 주문 의도에 따라 실제 파일 본문 수정은 오케스트레이터 내부 코드 컨텍스트 조회로 보완할 것

[실행용 작업문 제약]
- 실행용 작업문에는 구조/컨텍스트를 요약본만 유지할 것
- 긴 산출물 파일명에 task 전문을 재사용하지 말 것
- 출고 아카이브 파일명은 output_dir 이름 또는 짧은 project_name 기준으로 생성할 것
- mode: full
- total_files: 48

## Files

- `README.md`
- `package.json`
- `tsconfig.json`
- `next-env.d.ts`
- `app/page.tsx`
- `app/layout.tsx`
- `configs/app.env.example`
- `scripts/check.sh`
- `docs/architecture.md`
- `docs/order_profile.md`
- `docs/flow_map.md`
- `docs/flow_registry.json`
- `docs/usage.md`
- `docs/runtime.md`
- `docs/deployment.md`
- `docs/testing.md`
- `docs/scaffold_inventory.md`
- `docs/stage_progress.md`
- `docs/stage_progress.json`
- `.gitignore`
- `next.config.js`
- `app/loading.tsx`
- `app/dashboard/page.tsx`
- `app/api/health/route.ts`
- `app/api/brief/route.ts`
- `app/globals.css`
- `components/dashboardclient.tsx`
- `components/heropanel.tsx`
- `components/metriccluster.tsx`
- `components/signalmatrix.tsx`
- `components/focusrail.tsx`
- `components/insighttimeline.tsx`
- `components/executionboard.tsx`
- `components/themetoggle.tsx`
- `lib/types.ts`
- `lib/data.ts`
- `addons/node_service/README.md`
- `addons/node_service/package.json`
- `addons/node_service/tsconfig.json`
- `addons/node_service/src/types.ts`
- `addons/node_service/src/config.ts`
- `addons/node_service/src/lib/runtimeStore.ts`
- `addons/node_service/src/repositories/orderRepository.ts`
- `addons/node_service/src/services/orderService.ts`
- `addons/node_service/src/http/handlers/health.go`
- `addons/node_service/src/http/handlers/inventory.go`
- `addons/node_service/src/http/router.go`
- `docs/multi_generator_matrix.json`
