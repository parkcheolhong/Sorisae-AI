# AI engine project standards

## segmentation model

AI 표본은 한 덩어리로 두지 않고 아래 4개 구간으로 나눠야 합니다.

1. profile segment: 프로그램 종류별 표본
2. contract segment: 공통 엔진 계약과 도메인 추가 계약
3. implementation segment: 폴더, 파일, 구현 정규화, 정합성에 맞는 코드량
4. verification segment: 테스트, 문서, 커밋 대상, 출고 ZIP

## profile segment

| profile_id | sample | core entities | mandatory AI contracts |
| --- | --- | --- | --- |
| `trading_system` | AI 주식 자동매매 | signals, orders, positions, portfolios | signal-ingestion, risk-guard, order-execution, portfolio-sync, broker-adapter |
| `autonomous_multimall_platform` | AI 엔진 자율운영 멀티 쇼핑몰 | tenants, storefronts, catalogs, orders, campaign_runs | tenant-orchestration, catalog-synchronization, campaign-optimizer, fulfillment-supervisor |
| `lottery_prediction_system` | AI 엔진 자동 로또 생성기 | draw_histories, feature_windows, prediction_runs, candidate_sets | historical-draw-loader, feature-window-builder, candidate-number-generator, prediction-evaluation |
| `document_writer_suite` | AI 엔진 자동 문서 작성기 | documents, templates, approval_runs, publishing_jobs | brief-ingestion, document-draft-engine, approval-routing, publishing-archive |
| `tax_filing_copilot` | AI 엔진 세무 작성기 | tax_profiles, ledger_entries, filings, compliance_reports | ledger-normalization, tax-rule-engine, filing-draft-generator, compliance-checker |
| `presentation_generator_suite` | AI 엔진 파워포인트 생성기 | briefs, slide_decks, slides, asset_jobs | brief-parser, slide-outline-generator, asset-layout-engine, deck-exporter |

## contract segment

- common engine contract: `engine-core`, `feature-pipeline`, `training-pipeline`, `inference-runtime`, `evaluation-report`, `service-integration`
- trading broker live contract: `BROKER_PROVIDER`, `BROKER_TRADING_MODE`, `BROKER_ACCOUNT_ID`, `BROKER_LIVE_ACK_TOKEN`, `BROKER_API_TOKEN` or `BROKER_API_KEY` + `BROKER_API_SECRET`
- provider-specific contract:
  - `alpaca`: `ALPACA_API_KEY`, `ALPACA_API_SECRET`, optional `ALPACA_DATA_FEED`
  - `kis`: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO`, `KIS_PRODUCT_CODE`
  - `ibkr`: `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`

## implementation segment

- required folders: `app/`, `backend/`, `ai/`, `configs/`, `docs/`, `infra/`, `scripts/`, `tests/`
- optional UI folders by profile: `frontend/`, `addons/nextjs_react/`
- required service package rule: use `app/services/__init__.py` and `app/services/runtime_service.py`
- line count는 하한일 뿐이며, 구현 정합성은 책임 분리, 상태 근거, 검증 가능 payload, 운영 증거까지 채워졌는지로 판정해야 합니다.
- 각 profile은 runtime, service, ai, docs, tests가 같은 계약을 공유해야 하며 어느 한 층이라도 placeholder이면 미달로 판정합니다.
- 확장 가능한 프로그램 기준은 retrieval, evaluation, observability, policy gate, replay evidence를 증설 가능한 지점으로 남겨야 합니다.
- minimum file floor:
  - runtime entry files: `40+` lines for `app/main.py`, `backend/main.py`
  - primary service files: `80+` lines target for domain runtime/orchestration services
  - AI engine files: `20+` lines target per file with real typed logic
  - security/provider contract files: `30+` lines target with explicit validation
  - tests: `3+` executable cases per critical contract slice

### implementation normalization table

| profile_id | normalized implementation requirements |
| --- | --- |
| `trading_system` | signal ingestion, risk guard, order execution, portfolio sync, broker adapter를 개별 책임으로 분리하고 strategy overview payload에서 모두 연결해야 함 |
| `autonomous_multimall_platform` | tenant orchestration, catalog sync, campaign optimizer, fulfillment supervisor를 독립 서비스로 두고 tenant 상태와 복구 힌트를 동시에 반환해야 함 |
| `lottery_prediction_system` | draw loader, feature window builder, candidate generator, evaluator가 분리된 파이프라인이어야 하며 예측 근거와 데이터 품질을 함께 노출해야 함 |
| `document_writer_suite` | brief ingestion, draft engine, approval routing, publishing archive가 lifecycle 단계로 분리되고 draft quality, approval queue, publishing decision이 함께 반환되어야 함 |
| `tax_filing_copilot` | ledger normalization, rule engine, filing draft, compliance checker가 세무 흐름 순서로 구현되고 reviewer action과 mismatch 근거를 포함해야 함 |
| `presentation_generator_suite` | brief parser, outline generator, layout engine, exporter를 분리하고 deck status, asset fit, export readiness가 같은 runtime에 연결되어야 함 |

### common required files

| segment | required files |
| --- | --- |
| runtime | `app/main.py`, `app/routes.py`, `app/runtime.py`, `backend/main.py`, `frontend/app/page.tsx` |
| service | `app/services/__init__.py`, `app/services/runtime_service.py`, `backend/service/application_service.py`, `backend/service/domain_adapter_service.py` |
| ai | `ai/adapters.py`, `ai/evaluation.py`, `ai/features.py`, `ai/inference.py`, `ai/model_registry.py`, `ai/router.py`, `ai/schemas.py`, `ai/train.py` |
| security | `backend/core/auth.py`, `backend/core/security.py`, `app/core/security.py`, `infra/deploy/security.md` |
| validation | `tests/test_runtime.py`, `tests/test_routes.py`, `tests/test_security_runtime.py`, `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/file_manifest.md` |

### profile required files

| profile_id | required files |
| --- | --- |
| `trading_system` | `backend/app/connectors/broker.py`, `backend/service/strategy_service.py`, `tests/test_broker_connector.py`, `tests/test_ai_pipeline.py`, `configs/app.env.example` |
| `autonomous_multimall_platform` | `backend/app/connectors/shopify.py`, `backend/service/domain_adapter_service.py`, `frontend/components/order-summary.tsx`, `docs/operations_guide.md`, `docs/order_profile.md` |
| `lottery_prediction_system` | `ai/features.py`, `ai/evaluation.py`, `tests/test_ai_pipeline.py`, `docs/runtime.md`, `docs/testing.md` |
| `document_writer_suite` | `backend/service/application_service.py`, `ai/router.py`, `docs/order_profile.md`, `docs/scaffold_inventory.md`, `tests/test_runtime.py` |
| `tax_filing_copilot` | `backend/core/models.py`, `backend/service/application_service.py`, `docs/runbook.md`, `docs/operational_readiness.md`, `tests/test_security_runtime.py` |
| `presentation_generator_suite` | `frontend/app/page.tsx`, `frontend/components/runtime-shell.tsx`, `ai/router.py`, `docs/usage.md`, `tests/test_routes.py` |

### minimum code volume table

코드량은 구현 정합성을 보완하는 하한선입니다. 아래 기준만 맞고 책임/상태/검증 근거가 비어 있으면 미달입니다.

| profile_id | runtime floor | service floor | AI floor | docs floor | tests floor |
| --- | --- | --- | --- | --- | --- |
| `trading_system` | `app/main.py 40+`, `backend/main.py 40+` | `strategy_service.py 100+`, `domain_adapter_service.py 80+` | `features.py`, `inference.py`, `evaluation.py` each `25+` | `docs/order_profile.md 30+`, `docs/runtime.md 30+` | `test_broker_connector.py 3+`, total critical tests `5+` |
| `autonomous_multimall_platform` | `app/main.py 40+`, `backend/main.py 40+` | `application_service.py 80+`, `domain_adapter_service.py 80+` | `features.py`, `router.py`, `evaluation.py` each `20+` | `docs/order_profile.md 25+`, `docs/operations_guide.md 25+` | total critical tests `4+` |
| `lottery_prediction_system` | `app/main.py 40+`, `backend/main.py 40+` | `application_service.py 80+` | `features.py`, `train.py`, `evaluation.py` each `25+` | `docs/order_profile.md 25+`, `docs/testing.md 25+` | total critical tests `4+` |
| `document_writer_suite` | `app/main.py 40+`, `backend/main.py 40+` | `application_service.py 80+`, `runtime_service.py 60+` | `router.py`, `schemas.py`, `evaluation.py` each `20+` | `docs/order_profile.md 25+`, `docs/scaffold_inventory.md 20+` | total critical tests `4+` |
| `tax_filing_copilot` | `app/main.py 40+`, `backend/main.py 40+` | `application_service.py 90+`, `domain_adapter_service.py 80+` | `schemas.py`, `inference.py`, `evaluation.py` each `20+` | `docs/order_profile.md 25+`, `docs/runbook.md 30+` | total critical tests `4+` |
| `presentation_generator_suite` | `app/main.py 40+`, `backend/main.py 40+` | `application_service.py 80+` | `router.py`, `adapters.py`, `schemas.py` each `20+` | `docs/order_profile.md 25+`, `docs/usage.md 25+` | total critical tests `4+` |

### expansion technology targets

| profile_id | expansion targets |
| --- | --- |
| `trading_system` | market regime detector, anomaly-aware risk throttling, broker failover evidence chain, post-trade evaluation pipeline |
| `autonomous_multimall_platform` | tenant policy engine, catalog conflict resolver, demand forecast, fulfillment exception triage |
| `lottery_prediction_system` | feature importance explainer, candidate diversity scorer, batch evaluation runner, model lineage ledger |
| `document_writer_suite` | retrieval-backed brief enrichment, policy-aware drafting, approval bottleneck predictor, archive search index |
| `tax_filing_copilot` | regulation diff detector, evidence completeness scorer, filing simulation sandbox, audit trail summarizer |
| `presentation_generator_suite` | brand compliance checker, layout experiment replay, speaker note generator, delivery rehearsal evaluator |

### verification mapping by profile

| profile_id | must confirm in regenerated output |
| --- | --- |
| `trading_system` | broker env contract, provider contract lines, broker tests, shipment ZIP |
| `autonomous_multimall_platform` | tenant/store entities in `docs/order_profile.md`, commerce adapter targets, operations guide |
| `lottery_prediction_system` | draw history entities, candidate generator contracts, evaluation docs |
| `document_writer_suite` | document/template entities, approval-routing contract, scaffold inventory, automatic validation result |
| `tax_filing_copilot` | ledger/tax entities, compliance contract, security/runtime docs |
| `presentation_generator_suite` | slide/brief entities, deck-exporter contract, usage docs, frontend shell |

### profile completion criteria table

| profile_id | operational validation checklist | documentation checklist | focused proof |
| --- | --- | --- | --- |
| `trading_system` | dependency install, standalone boot, `/health`, `/runtime`, `/report`, `/ai/health`, broker contract health, shipment ZIP reproduction | `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/runtime.md`, `docs/runbook.md`, `docs/automatic_validation_result.json` must reflect broker/risk/order/portfolio contracts | `tests/test_broker_connector.py`, `tests/test_ai_pipeline.py`, `completion_gate_ok: true`, shipment ZIP path recorded |
| `autonomous_multimall_platform` | dependency install, standalone boot, `/health`, `/runtime`, `/report`, `/ai/health`, tenant orchestration snapshot, shipment ZIP reproduction | `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/runtime.md`, `docs/operations_guide.md`, `docs/automatic_validation_result.json` must reflect tenant/catalog/campaign/fulfillment contracts | `tests/test_runtime.py`, `tests/test_routes.py`, `tests/test_ai_pipeline.py`, `completion_gate_ok: true`, shipment ZIP path recorded |
| `lottery_prediction_system` | dependency install, standalone boot, `/health`, `/runtime`, `/report`, `/ai/health`, candidate generation snapshot, shipment ZIP reproduction | `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/runtime.md`, `docs/testing.md`, `docs/automatic_validation_result.json` must reflect draw history / candidate / evaluation contracts | `tests/test_runtime.py`, `tests/test_routes.py`, `tests/test_ai_pipeline.py`, `completion_gate_ok: true`, shipment ZIP path recorded |
| `document_writer_suite` | dependency install, standalone boot, `/health`, `/runtime`, `/report`, `/ai/health`, draft/approval/publish snapshot, shipment ZIP reproduction | `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/runtime.md`, `docs/runbook.md`, `docs/automatic_validation_result.json` must reflect brief/draft/approval/archive contracts | `tests/test_runtime.py`, `tests/test_routes.py`, `tests/test_ai_pipeline.py`, `completion_gate_ok: true`, shipment ZIP path recorded |
| `tax_filing_copilot` | dependency install, standalone boot, `/health`, `/runtime`, `/report`, `/ai/health`, ledger/compliance snapshot, shipment ZIP reproduction | `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/runtime.md`, `docs/operational_readiness.md`, `docs/automatic_validation_result.json` must reflect ledger/rule/filing/compliance contracts | `tests/test_runtime.py`, `tests/test_routes.py`, `tests/test_security_runtime.py`, `completion_gate_ok: true`, shipment ZIP path recorded |
| `presentation_generator_suite` | dependency install, standalone boot, `/health`, `/runtime`, `/report`, `/ai/health`, deck/export snapshot, shipment ZIP reproduction | `docs/order_profile.md`, `docs/scaffold_inventory.md`, `docs/runtime.md`, `docs/usage.md`, `docs/automatic_validation_result.json` must reflect brief/outline/layout/export contracts | `tests/test_runtime.py`, `tests/test_routes.py`, `tests/test_ai_pipeline.py`, `completion_gate_ok: true`, shipment ZIP path recorded |

## verification segment

- docs baseline: runtime, runbook, deployment, testing, order profile, commit target guidance
- tests baseline: runtime, routes, security, domain contract coverage
- delivery baseline: shipment ZIP plus curated commit target list
- transient exclusion baseline: virtualenv, pytest cache, `__pycache__`, runtime logs, local validation scratch files
