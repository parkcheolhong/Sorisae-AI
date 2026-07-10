# daytrade-ai — 개발/CI 편의 타깃.
# 사용: make -C apps/daytrade-ai check   (저장소 루트에서)

PY ?= python
PYTEST ?= $(PY) -m pytest
# KPI 게이트 파라미터(CI 에서 override 가능): make kpi-gate KPI_TRIALS=30 KPI_TICKS=2000
KPI_TICKS ?= 1500
KPI_TRIALS ?= 12
KPI_BACKEND ?= random
KPI_MAX_MDD ?= 3.0
KPI_SEED ?= 42
KPI_OUT ?= runs/kpi_regression.json
KPI_METRICS_OUT ?= runs/kpi_regression.prom

.PHONY: test compile kpi-gate check

# 전체 테스트(환경 의존 import-error 파일 제외).
test:
	$(PYTEST) tests/ --ignore=tests/test_orchestrator_operational_evidence_targets.py

compile:
	$(PY) -m compileall -q daytrade scripts

# (J) KPI 회귀 게이트 — 튜닝 전/후 다중 레짐 비교, 개선 실패 시 exit 1 로 CI 차단.
kpi-gate:
	$(PY) scripts/kpi_regression.py --synthetic-regimes \
		--ticks $(KPI_TICKS) --n-trials $(KPI_TRIALS) --backend $(KPI_BACKEND) \
		--max-mdd $(KPI_MAX_MDD) --seed $(KPI_SEED) \
		--out $(KPI_OUT) --metrics-out $(KPI_METRICS_OUT)

# CI 게이트: 컴파일 + 테스트 + KPI 회귀 게이트.
check: compile test kpi-gate
