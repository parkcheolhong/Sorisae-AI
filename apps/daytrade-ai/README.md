# daytrade-ai — AI 주식 단타(스캘핑·초단타) 자동매매 시스템

오더북/체결 흐름을 실시간으로 분석해 **밀리초 단위로 시그널을 생성하고 자동으로 주문**하는
파이프라인을 이 개발 환경에서 **실제로 동작하는 Python 소프트웨어**로 구현한 프로젝트입니다.

> ⚠️ **안전 고지**: 기본 실행 모드는 **모의투자(paper)** 입니다. 실거래(LIVE)는 코드 레벨
> 이중 게이트(아래)를 모두 통과해야만 활성화되며, 이 저장소에는 **실주문을 내는 브로커
> 구현체를 포함하지 않습니다**. 실거래는 본인 책임이며 거래소·금융 규제(자본시장법, SEC
> Reg NMS, MiFID II 등) 준수와 사전 승인이 필요합니다.

---

## 1. 아키텍처

설계서의 흐름(Market Feed → Feature → Detection → AI Inference → Risk → Execution → Monitoring)을
그대로 모듈화했습니다.

```
feed → FeatureEngine → DetectionEngine → AI Inference → (결합) → RiskManager → Executor → Portfolio
  └─────────────────────────── Monitoring(레이턴시 / 슬리피지 / P&L) ───────────────────────────┘
```

| 모듈 | 파일 | 역할 |
|------|------|------|
| Market Feed | `daytrade/feed/` | `MarketFeed` 인터페이스 + `SimulatedFeed` + `CsvReplayFeed` + 라이브: `BinanceFeed`/`UpbitFeed`(L2)/`AlpacaFeed`(L1) + `RecordingFeed` + **급변 이벤트 캡처**(`event_capture.py`) |
| Storage | `daytrade/storage/` | **고속 바이너리 틱 스토어**(KDB+/q 경량 대안): `tickstore.py`(`TickStore`/`TickStoreFeed`, 고정폭 컬럼형·이진 탐색 질의 O(log n+k)·이어쓰기) + `recorder.py`(`RollingTickStoreWriter` 일별 로테이션·`StoreRecordingFeed`). 캡처 CLI `scripts/capture_to_store.py` |
| Feature Engine | `daytrade/features/engine.py` | OBI·OBI z-score·volume spike·micro-momentum·VWAP·spread |
| Detection Engine | `daytrade/detection/engine.py` | 규칙 기반 시그널(설계서 §3-2 의사코드) + confidence |
| AI Inference | `daytrade/inference/model.py` | 플러거블 모델: `HeuristicModel`(기본) / `NumpyLogRegModel`(JSON, dep-free) / `OnnxModel`(단일벡터) / `SequenceOnnxModel`(LSTM·Transformer 윈도) / `OnnxPolicyModel`(RL 연속정책, stateful). `load_model` 출력차원 자동판별 |
| AI Inference 엔진(M4) | `daytrade/inference/trt.py` | `load_inference_model`(TensorRT→ORT(CUDA)→ORT(CPU)→Heuristic 폴백) + `TensorRTModel`/`build_engine`(FP16/INT8, 서버) + `HotSwapModel`(Blue-Green) + `LatencyHistogram`/`MeasuredModel`(p50/95/99) |
| Training (M2) | `daytrade/training/` | 라벨링·데이터셋·numpy 로지스틱·torch LSTM/Transformer·ONNX export·**워크포워드 검증**·**HPO(optuna/random)**. `FeatureEngine` 재사용으로 train/serve skew 제거 |
| RL (M2 후속) | `daytrade/rl/` | `TradingEnv`(Gymnasium 호환, `FeatureEngine` 재사용, 수익률 보상−전환비용) + 순수 numpy **PPO**(`ppo.py`, actor-critic·GAE·클리핑) / REINFORCE(`agent.py`) + Gymnasium 어댑터·**RLlib PPO 브리지**(`gym_env.py`/`rllib_train.py`, ray 설치 시) |
| Risk Mgmt | `daytrade/risk/manager.py` | 포지션·가치·총노출·레버리지 한도 + 레이턴시/손익 서킷브레이커 + 슬리피지 가드 |
| Execution | `daytrade/execution/` | `OrderExecutor` + `PaperExecutor`(슬리피지·수수료·매도세·부분체결) + `Portfolio`(회계). **M5**: `OrderRouter`(멱등키·슬리피지가드·재견적·필콜백) / `FixExecutor`+`SimulatedFixVenue`(FIX 4.4 코덱 `fix.py`) / `AlpacaExecutor`(REST v2 paper) / `TradeStore`(sqlite 영속) |
| Pipeline | `daytrade/pipeline.py` | 전 구간 결선 + 틱당 처리 |
| Monitoring | `daytrade/monitoring/` | `metrics.py`(레이턴시 p50/p95/p99·슬리피지·P&L·Sharpe·MDD). **M6**: `exporter.py`(Prometheus text exposition) / `audit.py`(해시체인 불변 감사로그+무결성검증) / `alerts.py`(규칙) / `server.py`(`/metrics` HTTP) / `tracing.py`(인프로세스 span+Jaeger export) |
| Ops | `daytrade/ops/` | **B**: `LiveRunner`(라이브 상시운영 — 자동재연결·heartbeat·UTC 일일리포트, `/metrics`·감사로그·알림 결선, **current.json 런타임 핫스왑**, CLI `scripts/live_ops.py`). **M7**: `RetrainOrchestrator`(`retrain.py` — TradeStore 트리거→데이터셋→재학습→워크포워드→ONNX 핫스왑, `tune_and_validate` 로 워크포워드 Sharpe 튜닝 결합, CLI `scripts/retrain.py`) + `Scheduler`(`scheduler.py` — 경량 인프로세스 일일재학습/5분 튜닝, CLI `scripts/scheduler.py`) + `registry`(`load_current`/`apply_signal_overrides` — 핫스왑 포인터 결선) |
| Backtest | `daytrade/backtest/` | `runner.py`(합성/리플레이 시뮬레이션) + **`report.py`**(equity curve 분석: Sortino/Calmar/VaR·CVaR/수익팩터 + JSON·SVG HTML 리포트) + **`backtrader_adapter.py`**(틱→OHLCV `ticks_to_ohlcv`(의존성 0) + `run_backtrader`, bt/pandas 설치 시) |
| Testing(Chaos) | `daytrade/testing/faults.py` | **인프로세스 장애 주입**(Chaos-Mesh 경량 대안): `FaultInjectingFeed`(끊김·드롭·손상·지연) / `FlakyFeedFactory`(끊김→재연결→회복) / `FlakyExecutor`(거부·예외·부분체결) |
| Schema(SSOT) | `schemas/market.fbs` | 직렬화 SSOT(FlatBuffers). C++ 코어(M3) 공유 + `FEATURE_NAMES` 순서 골든 테스트 |
| C++ 코어(M3) | `cpp/` | 저지연 Feature/Detection 엔진(C++20 + pybind11). Python 레퍼런스와 **1e-9 수치 동일성 검증 통과**(`tests/test_cpp_golden.py`). 빌드: `cpp/build.ps1`(MSVC/MinGW 자동)·`build.sh`. M4 추론 헤더 스캐폴드 `include/daytrade/inference_engine.hpp` |

---

## 2. 설치 & 실행

```bash
cd apps/daytrade-ai
pip install -r requirements.txt        # numpy(필수) + pytest. onnxruntime 은 선택.

# 합성 시뮬레이션 백테스트
python -m daytrade.cli sim --symbol AAPL --ticks 5000 --obi-threshold 5e5 --event-prob 0.05

# 규칙만(AI 비활성)
python -m daytrade.cli sim --no-ai

# CSV 리플레이
python -m daytrade.cli replay --csv ticks.csv

# JSON 결과
python -m daytrade.cli sim --json
```

예시 출력(합성 데이터 기준):

```
 mode               : backtest  (non-live mode (safe by default))
 ticks / signals    : 5000 / 366
 orders / fills / rej: 76 / 76 / 0
 latency p50/p95/p99: 0.018 / 0.042 / 0.061 ms
 equity start/end   : 1,000,000.00 -> 1,011,487.51
 total return       : 1.1488 %
 sharpe             : 41.39   ← 합성 데이터라 비현실적으로 높음(실데이터로 재검증 필요)
```

> 합성 데이터의 성과(Sharpe 등)는 데모용이며 실제 수익성을 의미하지 않습니다. 실데이터
> 리플레이/페이퍼트레이딩으로 반드시 재검증하세요.

---

## 3. 프로그램으로 사용(임베드)

```python
from daytrade.config import TradingConfig, SignalConfig
from daytrade.feed.simulated import SimulatedFeed
from daytrade.backtest.runner import run_backtest

cfg = TradingConfig.backtest(signal=SignalConfig(obi_threshold=5e5, use_ai=True), seed=42)
report = run_backtest(cfg, SimulatedFeed(n_ticks=5000, seed=42, event_prob=0.05))
print(report.metrics.as_dict())
```

실거래 브로커를 붙이려면 `daytrade/execution/base.py` 의 `OrderExecutor` 를 구현하고
실시간 피드는 `daytrade/feed/base.py` 의 `MarketFeed` 를 구현해 끼우면 됩니다.

---

## 3-1. AI 학습 파이프라인 (M2)

라벨링 → 학습 → ONNX export → 런타임 추론 모델 연결까지 한 번에 수행합니다. 학습 피처는
런타임과 **동일한 `FeatureEngine`** 으로 생성되어 train/serve skew 가 없습니다.

```bash
# (1) 순수 numpy 로지스틱 — 의존성 0, 항상 동작. JSON + (선택) ONNX 동시 export
python -m daytrade.cli train --sim --ticks 20000 --backend numpy \
    --out model.json --onnx model.onnx --horizon 20 --up-bps 5 --down-bps 5

# (2) torch 시퀀스 모델(LSTM/Transformer) → ONNX  (torch/onnxscript 필요)
python -m daytrade.cli train --csv ticks.csv --backend torch \
    --kind lstm --seq-len 32 --hidden 32 --epochs 30 --out seq_lstm.onnx

# 학습한 모델로 추론(확장자로 자동 디스패치: .json→Numpy, .onnx→Onnx)
python -m daytrade.cli replay --csv ticks.csv   # 파이프라인에 model_path 주입해 사용
```

```python
from daytrade.inference.model import load_model, SequenceOnnxModel
m = load_model("model.json")          # NumpyLogRegModel (의존성 없음)
m = load_model("model.onnx")          # OnnxModel (단일 벡터, onnxruntime)
m = SequenceOnnxModel("seq_lstm.onnx", seq_len=32, n_features=8)  # LSTM/Transformer
# 셋 다 predict(fv) -> (prob_buy, prob_sell). TradingPipeline(cfg, model=m) 로 주입.
```

- **라벨**: forward-return(`(p[t+h]-p[t])/p[t]`)을 ±bps 임계로 이진화한 `y_buy`/`y_sell`(독립). 미래가 없는 마지막 `h`행은 제거(look-ahead 차단).
- **표준화 내장**: 학습 시 train 구간에서만 추정한 mean/std 를 JSON·ONNX 그래프에 실어, 원시 피처가 그대로 들어와도 동일 결과.
- **의존성 계층**: numpy 경로는 항상 동작(테스트 보장). `onnx`/`onnxruntime`/`torch` 는 설치 시에만 활성.

### 워크포워드 검증 (과최적화 방지)

시간순 out-of-sample 으로 일반화 성능을 측정합니다. 분할은 항상 train→test 순서이고,
라벨 horizon 누수를 막기 위해 경계에서 `purge=horizon` 만큼 train 끝을 잘라냅니다(embargo).

```bash
# 분류 OOS 정확도 + balanced_acc + pos_rate + 과최적화 갭(train_acc − oos_acc)
python -m daytrade.cli walkforward --sim --ticks 20000 --mode validate --scheme anchored --n-splits 5

# 폴드별 학습 → test 구간 OOS 백테스트(P&L/Sharpe/MDD) 집계
#  실자산은 오더북 스케일에 맞춰 --obi-threshold 지정(암호화폐는 수~수십 수준)
python -m daytrade.cli walkforward --csv ticks.csv --mode backtest --scheme rolling --n-splits 5 --obi-threshold 5
```

> **불균형 주의**: 잔잔한 구간에서는 ±bps 이벤트가 희소해 라벨이 거의 0 → 단순 정확도가
> 무의미하게 높아집니다(전부 "관망" 예측). 그래서 `validate` 는 `balanced_acc`(recall 평균)와
> `pos_rate`(이벤트 빈도)를 함께 보고합니다. `bal_acc≈0.5`면 사실상 무학습입니다.

```python
from daytrade.training import walk_forward_backtest, walk_forward_validate
rep = walk_forward_validate(bundle, n_splits=5, scheme="anchored")  # 분류 OOS
rep = walk_forward_backtest(ticks, cfg, horizon=20, n_splits=5)      # OOS 백테스트
print(rep.summary)   # mean_oos_sharpe, mean_overfit_gap, positive_fold_ratio ...
```

> 합성 데이터의 OOS Sharpe 는 비현실적으로 높습니다(데모). 실데이터 캡처(CLI `record`)
> 후 워크포워드로 재검증해야 의미가 있습니다.

### 하이퍼파라미터 탐색 (워크포워드 목적함수)

라벨/모델/시그널 하이퍼파라미터를 **워크포워드 OOS 점수를 최대화**하도록 탐색합니다.
평가가 항상 시간순 OOS 라 in-sample 과최적화로 흐르지 않습니다.

```bash
# optuna TPE(설치 시) — 미설치면 자동으로 순수 random 탐색 폴백
python -m daytrade.cli tune --sim --ticks 20000 --n-trials 30 \
    --metric mean_oos_sharpe --backend auto --out best.json

# 실자산: obi_threshold 탐색범위를 데이터 |OBI| 분포(p25~p95)로 자동 보정
python -m daytrade.cli tune --csv ticks.csv --n-trials 30 --calibrate-obi
```

```python
from daytrade.training import run_tuning, RiskConstraints

# 기본 목적함수 = mean_oos_sharpe(워크포워드 OOS Sharpe 최대화)
# RiskConstraints: OOS 최악 MDD 한도/수익폴드비율 하한을 패널티로 반영(과최적화 억제)
res = run_tuning(ticks, base_config, n_trials=30, backend="auto",
                 constraints=RiskConstraints(max_worst_mdd_pct=3.0, min_positive_fold_ratio=0.5))
print(res.best_params, res.best_value)   # 탐색 결과(best 파라미터/점수)
```

- **백엔드 계층**: `optuna` 있으면 TPE 샘플러, 없으면 seed 고정 random search(항상 동작).
- **목적함수**: 기본 `mean_oos_sharpe`(워크포워드 OOS Sharpe). `RiskConstraints` 로 MDD/수익폴드비율 soft-constraint.
- **탐색공간**: `horizon·up/down_bps·lr·epochs·ai_threshold·obi_threshold·volume_spike_ratio`(`default_search_space()`).

### 급변 이벤트 타게팅 캡처

블라인드 캡처는 잔잔한 구간을 잔뜩 담아 회귀셋이 희석됩니다. `events` 는 **급변(트리거) 구간만**
pre-roll + post-roll 윈도로 잘라 기록합니다(운영 `FeatureEngine` 으로 트리거 피처 계산).

```bash
# 기존 CSV 에서 이벤트 윈도만 추출(오프라인 농축)
python -m daytrade.cli events --csv data/solusdt_vol.csv --out data/sol_events.csv \
    --ret-bps 3 --window 20 --pre 10 --post 30 --obi-z 3

# Binance 라이브를 스캔하며 이벤트만 기록(최대 --ticks 소스 스캔)
python -m daytrade.cli events --live --symbol SOLUSDT --ticks 50000 --out data/events.csv \
    --ret-bps 5 --vol-spike 3 --max-events 50
```

- **트리거(OR)**: `|윈도 수익률| ≥ ret_bps` / `volume_spike ≥ vol_spike` / `|obi_norm| ≥ obi_z`(0=비활성).
- 예) SOL 6000틱 → 이벤트 윈도 1,145틱(19%)만 농축 추출.

### 강화학습 (TradingEnv + PPO / REINFORCE)

규칙/지도학습을 넘어, **포지션을 직접 정하는 정책**을 강화학습으로 탐색합니다. 환경은 운영과 동일한
`FeatureEngine` 으로 관측을 만들어 train/serve skew 를 제거하고, **수익률 기반 스케일 불변 보상**
(− 포지션 전환비용)을 씁니다. 의존성 0(gymnasium 설치 시 표준 Space 사용).

```bash
# PPO(이산: 숏/플랫/롱, actor-critic + GAE + 클리핑) — 의존성 0
python -m daytrade.cli rl --csv data/sol_events.csv --algo ppo --iterations 40 --reward-scale 1e4

# cPPO(연속 포지션 사이즈 ∈ [-1,1]) + 정책 ONNX export → M4 추론 엔진 연결
python -m daytrade.cli rl --csv data/sol_events.csv --algo cppo --iterations 40 \
    --reward-scale 1e4 --onnx artifacts/policy.onnx

# REINFORCE 베이스라인
python -m daytrade.cli rl --sim --ticks 5000 --algo reinforce --episodes 200 --out policy.json
```

```python
from daytrade.rl import TradingEnv, RLConfig, PPOAgent, train_ppo, run_episode
env = TradingEnv(ticks, RLConfig(cost_bps=1.0, reward_scale=1e4))
agent = PPOAgent(seed=0)
train_ppo(env, agent, iterations=40)                      # PPO 학습
_, actions, _, total = run_episode(env, agent, greedy=True)  # 평가(REINFORCE 와 동일 인터페이스)
```

- **행동**: 이산(0→숏 / 1→플랫 / 2→롱) 또는 **연속(목표 포지션 사이즈 ∈ [-1,1], cPPO)**.
- **보상**: `position·return − |Δposition|·cost_bps/1e4` → 잦은 뒤집기를 비용으로 벌함(스캘핑 현실).
- **PPO**: 순수 numpy actor-critic(GAE(λ) + 클리핑 surrogate + 엔트로피). 연속은 Gaussian 정책(`ContinuousPPOAgent`).
- **ONNX 서빙(M4 연결)**: cPPO 정책 → `export_continuous_policy_to_onnx`(표준화 내장 그래프) →
  `OnnxPolicyModel`(stateful, 포지션 추적) 이 `predict(fv)→(prob_buy,prob_sell)` 로 기존 파이프라인에 연결.
- **분산 학습(선택)**: `from daytrade.rl import train_ppo_rllib` — `ray[rllib]` 설치 시 동일 `TradingEnv`
  를 Gymnasium 어댑터(`make_gym_trading_env`)로 감싸 RLlib PPO 로 학습(미설치 시 명확한 안내).

### RL 정책(ONNX) vs 휴리스틱 PnL 비교 (실제 파이프라인)

연속행동 RL 정책을 학습 → ONNX export → `OnnxPolicyModel` 로 실제 `TradingPipeline` 백테스트에
물려 휴리스틱/규칙 대비 PnL(return%·realizedPnL·Sharpe·maxDD)을 한 표로 비교합니다.

```bash
python scripts/compare_policy_pnl.py --sim --symbol AAPL --ticks 5000 \
    --iterations 50 --ai-threshold 0.5
# rules-only / heuristic-AI / rl-policy-AI 3종 백테스트 비교 (in-sample 데모; OOS 는 walkforward)
```

`load_model` 은 ONNX 출력 차원으로 정책(1)↔확률(2)을 자동 판별하므로
`sim --model policy.onnx` 처럼 일반 백테스트에도 바로 물릴 수 있습니다.

### M4 추론 엔진 팩토리 (TensorRT → ONNX Runtime → 휴리스틱)

```python
from daytrade.inference import load_inference_model
# 서버: TensorRT 엔진 우선, 개발 PC: ONNX Runtime/휴리스틱 자동 폴백
model = load_inference_model("model.onnx", engine_path="model.plan",
                             measure=True, hot_swappable=True)
model.predict(fv)                       # 레이턴시 계측 + Blue-Green 핫스왑 지원
model.active.histogram.summary()        # {p50_us, p95_us, p99_us, ...}
```

### 페이퍼 트레이딩 봇 + 상태 영속 (M5)

실시간/리플레이 피드를 파이프라인에 흘려 모의주문을 내고, 체결·자본곡선을 sqlite 에 영속합니다.

```bash
python scripts/paper_trading_bot.py --sim --symbol AAPL --ticks 4000 --db runs.sqlite --json
python scripts/paper_trading_bot.py --csv data/sol_events.csv --db runs.sqlite      # 리플레이
python scripts/paper_trading_bot.py --live --symbol BTCUSDT --ticks 2000 --db runs.sqlite  # 실시간(websockets)
```

주문 라우팅(멱등키·슬리피지가드·재견적·체결콜백)과 FIX 4.4 어댑터는 `daytrade.execution` 에 있습니다:

```python
from daytrade.execution import OrderRouter, FixExecutor, SimulatedFixVenue
router = OrderRouter(FixExecutor(SimulatedFixVenue()), max_slippage_pct=0.005, max_requotes=1,
                     on_fill=lambda f: ...)   # 실거래는 FixExecutor 에 QuickFIX 세션 주입(config/fix.cfg)
```

실 브로커 연동(서버/계정): **IBKR** 은 FIX(`FixExecutor` + `config/fix.cfg`), **Alpaca** 는 REST(`AlpacaExecutor`).

```python
from daytrade.execution import AlpacaExecutor
ex = AlpacaExecutor(api_key, api_secret)        # paper 기본(api.alpaca paper). 실계좌는 is_live_account=True
fill = ex.submit(order, tick)                   # 내부에서 build_alpaca_order → POST /v2/orders → parse_alpaca_fill
```

### 모니터링 · 감사 로그 · 알림 (M6)

페이퍼봇에 결선되어 있으며 단독으로도 사용합니다. 메트릭은 Prometheus 노출 포맷, 감사로그는 해시체인 WAL.

```bash
# 페이퍼봇: 해시체인 감사로그 + Prometheus 메트릭 + 라이브 /metrics + 구간 트레이싱
python scripts/paper_trading_bot.py --sim --ticks 4000 --audit runs/audit.jsonl --metrics-out runs/metrics.prom --json
python scripts/paper_trading_bot.py --live --symbol BTCUSDT --metrics-port 9108 --json   # 라이브 /metrics 스크레이프
python scripts/paper_trading_bot.py --sim --ticks 4000 --trace-out runs/spans.json --trace-sample 50 --json  # 구간 span 프로파일
```

```python
from daytrade.monitoring import MetricsRegistry, AuditLog, AlertEngine, MetricsServer, Tracer, registry_from_run
reg = registry_from_run(run_metrics, symbol="AAPL", mode="paper"); open("metrics.prom","w").write(reg.render())
log = AuditLog("audit.jsonl"); log.append("fill", symbol="AAPL", qty=10, price=100.01); assert log.verify().ok
alerts = AlertEngine().evaluate(run_metrics.as_dict())   # 서킷브레이커/낙폭/레이턴시/거절률/정체

# /metrics HTTP 노출(Prometheus 스크레이프) + 파이프라인 구간 트레이싱(Jaeger식)
srv = MetricsServer(lambda: reg, port=9108).start()      # http://127.0.0.1:9108/metrics, /healthz
tracer = Tracer(sample_rate=50); pipe = TradingPipeline(cfg, tracer=tracer)  # 기본 NoopTracer=무오버헤드
# ... pipe.run(...); tracer.stage_summary()  # 구간별 p50/p95/p99 µs, tracer.export_jaeger()
```

운영 아티팩트: `config/grafana_dashboard.json`(Grafana Import) · `config/alert_rules.yml`(Prometheus/Alertmanager).

### 라이브 상시운영 러너 (자동재연결·heartbeat·일일리포트)

`LiveRunner`(`daytrade/ops/`)가 영속 파이프라인을 라이브 피드에 물려 무중단 가동하며, 피드가 끊기면
지수 백오프로 재연결하고, heartbeat(JSON 한 줄)와 UTC 자정 일일리포트를 산출한다. `/metrics`·감사로그·
알림·`TradeStore` 가 모두 결선된다.

```bash
# 합성/리플레이(반복 재연결로 무중단 시뮬레이션) — 30초 후 자동 종료
python scripts/live_ops.py --feed sim --symbol AAPL --metrics-port 9108 \
    --audit runs/audit.jsonl --report-dir runs/reports --db runs/live.sqlite --max-runtime 30

# 실시간(거래소/브로커 — websockets/계정 필요)
python scripts/live_ops.py --feed binance --symbol BTCUSDT --metrics-port 9108 --audit runs/audit.jsonl --report-dir runs/reports
python scripts/live_ops.py --feed upbit  --symbol KRW-BTC
python scripts/live_ops.py --feed alpaca --symbol AAPL    # ALPACA_API_KEY/SECRET_KEY env
```

> no-tick(피드 정체) 감지는 스크레이프 측 규칙(`time() - daytrade_last_tick_unixtime > N`,
> `config/alert_rules.yml`)이 담당합니다(인프로세스 루프는 틱 대기 시 블록되므로).

### 서버 데몬화 / 배포 (`deploy/`)

상주 운영용 패키징. 그레이스풀 종료(SIGTERM→당일 리포트·`run_end` 감사 후 정상 종료), `/healthz`(liveness),
`/readyz`(readiness = 서킷브레이커 미발동 + 틱 신선도).

```bash
# Docker (빌드 컨텍스트 = apps/daytrade-ai)
docker build -f deploy/Dockerfile -t daytrade-live .
docker run -d --name daytrade-live -p 9108:9108 -v daytrade-data:/data \
    daytrade-live --feed binance --symbol BTCUSDT --metrics-host 0.0.0.0
docker inspect --format '{{.State.Health.Status}}' daytrade-live   # HEALTHCHECK → /healthz

# systemd (네이티브 상주)
sudo cp deploy/daytrade-live.service /etc/systemd/system/
sudo install -D deploy/daytrade-live.env /etc/daytrade/daytrade-live.env   # 값 편집
sudo systemctl daemon-reload && sudo systemctl enable --now daytrade-live
journalctl -u daytrade-live -f      # heartbeat/일일리포트 JSON 로그 추적
```

| 엔드포인트 | 용도 | 응답 |
|-----------|------|------|
| `/metrics` | Prometheus 스크레이프 | text exposition |
| `/healthz` | liveness(프로세스 생존) | `200 ok` |
| `/readyz` | readiness(거래 가능 상태) | `200 ready` / `503 not ready` |

### 재학습 오케스트레이션 (M7 — 데이터→재학습→워크포워드→핫스왑)

상주 러너가 쌓은 `TradeStore`(체결/자본곡선)·감사로그를 **트리거 입력**으로, 캡처 틱을 **학습 입력**으로
받아 재학습→OOS 워크포워드 검증→인수 게이트→ONNX/JSON export→**Blue-Green 핫스왑**을 자동 연결한다.

```bash
# 라이브 sqlite 트리거(낙폭/수익률/체결수) + CSV 캡처로 재학습
python scripts/retrain.py --db runs/live.sqlite --csv data/sol_events.csv \
    --model-dir models --audit runs/retrain_audit.jsonl

# 트리거 무시 강제 재학습(스케줄/수동) — 합성 틱
python scripts/retrain.py --force --synthetic 4000 --model-dir models
# → models/model_vN.{json,onnx} + current.json, 감사로그에 retrain_trigger/result·model_hotswap
```

```python
from daytrade.ops import RetrainOrchestrator, TriggerConfig, evaluate_trigger
from daytrade.inference.trt import HotSwapModel

orch = RetrainOrchestrator(model_dir="models")           # 인수 게이트: OOS balanced acc + 과최적화 갭
rep = orch.orchestrate(store, feed, run_id=rid,          # 트리거→학습→검증→export
                       trigger=TriggerConfig(max_drawdown_pct=1.5), hotswap=hotswap_model)
# rep.accepted/promoted, rep.wf_summary, rep.artifacts(versioned)
```

> 인수 게이트(`AcceptanceConfig`): 평균 OOS balanced accuracy ≥ 0.5 + 과최적화 갭 ≤ 0.1 일 때만
> 승격합니다(클래스 불균형·과최적화에 안전). 실패 시 아티팩트를 만들지 않고 기존 모델을 유지합니다.

**튜닝↔재학습 결합**(`tune_and_validate`): 워크포워드 Sharpe 목적함수로 하이퍼파라미터를 자동 탐색한
뒤 best 파라미터로 재학습하고, 동일 인수 게이트를 통과해야 승격합니다(튜닝 메타·best 시그널 임계는
`current.json` 에 기록).

```python
from daytrade.training import RiskConstraints
rep = orch.tune_and_validate(ticks, n_trials=30, metric="mean_oos_sharpe",
                             constraints=RiskConstraints(max_worst_mdd_pct=3.0), hotswap=hotswap_model)
# rep.tuning(backend/metric/best_value/best_params), rep.accepted/promoted, rep.artifacts
```

### 경량 스케줄러 (M7-F — Airflow 없이 상주: 일일 재학습 + 5분 튜닝 트리거)

`retrain.py`/튜닝을 한 프로세스에서 주기 실행한다. **daily** 작업은 매일 지정 UTC 시각(기본 02:00)에
전체 재학습, **interval** 작업은 N분(기본 5분)마다 트리거를 점검해 충족 시 워크포워드 Sharpe 튜닝→재학습
을 돌린다. 작업 예외는 흡수(상주 지속)하고 SIGTERM/SIGINT 로 그레이스풀 종료한다.

```bash
# 상주: 매일 02:00 UTC 재학습 + 5분마다 튜닝 트리거(TPE/random), 모든 이벤트 JSON 1줄 출력
python scripts/scheduler.py --db runs/live.sqlite --csv data/sol_events.csv \
    --model-dir models --audit runs/sched_audit.jsonl \
    --daily-hour 2 --tune-every 300 --tune-trials 30 --max-mdd 3.0

# 스모크: 두 작업 1회 즉시 실행 후 종료(트리거 무시)
python scripts/scheduler.py --db :memory: --synthetic 1500 --once --force \
    --model-dir models --min-samples 50 --tune-trials 4 --tune-backend random
```

```python
from daytrade.ops import Scheduler
sch = Scheduler(poll_sec=1.0)                       # 주입 가능한 시계/sleep(테스트 가능)
sch.daily("retrain", at_hour=2, fn=daily_retrain)   # 매일 02:00 UTC
sch.every("tune", 300, tune_trigger)                # 5분마다
sch.run(max_runtime_sec=0)                          # 0=무제한 상주, request_stop()/SIGTERM 로 종료
```

### KPI 회귀셋 (M7-G — 튜닝 전/후 다중 레짐 비교, 자동 튜닝 KPI 개선 증빙)

다중 레짐(잔잔/변동/이벤트빈발)에서 **baseline**(기본 파라미터) vs **tuned**(워크포워드 Sharpe 튜닝)
모델의 **OOS** KPI(평균 수익률·Sharpe·최악 MDD·수익폴드비율)를 비교해 "자동 튜닝 KPI 개선"(M7 인수기준)을
정량 증빙한다. 개선 실패 시 비정상 종료(exit 1)하여 CI 게이트로 쓸 수 있다.

```bash
# 합성 3레짐 자동 생성 → 비교 리포트 + 개선 판정(PASS/FAIL)
python scripts/kpi_regression.py --synthetic-regimes --ticks 1500 --n-trials 20 \
    --backend auto --max-mdd 3.0 --out runs/kpi_regression.json
# 예: sharpe +1.98→+4.09 (improved), worst_mdd 0.042→0.013 (not_worse), 3/3 => PASS

# 실제 캡처 다중 레짐(NAME=CSV 반복)
python scripts/kpi_regression.py --regime open=data/sol_open.csv --regime news=data/sol_news.csv
```

> 두 결과 모두 **워크포워드 OOS(폴드)** 로 측정 → in-sample 과최적화로 흐르지 않음(워크포워드 자체가
> 일반화 측정). verdict: 레짐 평균 Sharpe 향상 + 최악 MDD 비악화(허용 0.1%p) 시 `passed=True`.

**Prometheus 결선(M7-I)**: `--metrics-out` 로 verdict 를 `.prom` textfile(node_exporter textfile
collector/pushgateway)로 노출(`daytrade_kpi_passed`/`daytrade_kpi_{baseline,tuned}_sharpe` 등). 라이브
러너는 핫스왑 시 `daytrade_model_version`/`daytrade_model_reloads_total` 게이지를 갱신한다(Grafana 패널
"운영 모델 버전/핫스왑", "자동 튜닝 KPI 회귀", "KPI 게이트 판정").

**CI 게이트(M7-J)**: `make -C apps/daytrade-ai check`(= compile + test + kpi-gate) 또는
`.github/workflows/daytrade-ai-ci.yml`(PR 시 자동). 튜닝 회귀(개선 실패) 시 **exit 1 로 머지 차단**.

```bash
make -C apps/daytrade-ai check          # 컴파일 + 테스트 + KPI 회귀 게이트
make -C apps/daytrade-ai kpi-gate KPI_TRIALS=30 KPI_TICKS=2000   # 게이트만(파라미터 override)
```

### 런타임 핫스왑 결선 (M7-H — current.json → 라이브 무중단 적용)

재학습/스케줄러가 승격한 `models/current.json`(모델 경로 + best 시그널 임계 ai/obi/vol)을 라이브
러너가 **시동·세션 경계마다 버전 감시**해 무중단으로 집어 든다(추론 모델 교체 + 탐지 임계 즉시 반영).

```bash
# --model-dir 지정 시 current.json 의 최신 승격 모델/임계를 자동 로드(버전 변경 시 핫스왑)
python scripts/live_ops.py --feed sim --symbol AAPL --model-dir models \
    --metrics-port 9108 --db runs/live.sqlite --heartbeat 5
# 새 버전 승격 시: {"event":"model_reload","version":N,...} + 감사로그 model_reload
```

```python
# 파이프라인 단독으로도 런타임 적용 가능
info = pipeline.reload_from_current("models")   # {version, model_path, signal} 또는 None
# → pipeline.model 교체 + pipeline.config.signal/detection.config 에 best 임계 반영
```

### 모델 자동 롤백 (M7-L — 핫스왑 후 KPI 악화 시 직전 버전 복귀)

승격(`current.json`)마다 스냅샷을 `models/history.jsonl` 에 누적한다. 라이브 러너는 **핫스왑 직후
감시를 무장**하고, 윈도 내 낙폭이 한도를 넘으면 직전 버전으로 자동 롤백한다(루프 방지: 롤백 reload 는
재무장하지 않음). 감사로그에 `kpi_breach`·`model_rollback` 기록.

```bash
# --rollback 활성: 스왑 후 1% 낙폭이 300초 내 발생 시 직전 버전 자동 복귀
python scripts/live_ops.py --feed sim --symbol AAPL --model-dir models \
    --rollback --rollback-drawdown 1.0 --rollback-window 300 --db runs/live.sqlite
```

```python
from daytrade.ops import rollback_current, auto_rollback
# 수동/오케스트레이터 롤백(현재보다 낮은 최신 버전, 또는 to_version 지정)
restored = rollback_current("models")               # {version, model_path, signal, rolled_back_from}
restored = orchestrator.rollback(to_version=3, hotswap=hotswap_model)
# auto_rollback: 롤백 + 나쁜 시그니처 블랙리스트 + 롤백 기록(가드 일원화) — 러너 --rollback 이 사용
restored = auto_rollback("models", cooldown_sec=86400)
```

**롤백 쿨다운/블랙리스트(M7-M)** — 롤백된 '나쁜 모델'의 시그니처(라벨+시그널 파라미터 해시)를 쿨다운
(`blacklist_cooldown_sec`) 동안 **재승격 금지**(같은 모델 반복 방지). 인수 게이트 통과 후에도 블랙리스트
시그니처면 승격 차단(감사 `promotion_blocked`). 또한 윈도 내 **연속 롤백이 한도(`max_consecutive_rollbacks`)
초과**하면 재학습을 일시중지(`retrain_pause_sec`)하여 orchestrate/tune_and_validate 가 즉시 반환한다(플래핑 차단).

```python
orch = RetrainOrchestrator(model_dir="models",
    blacklist_cooldown_sec=86400, max_consecutive_rollbacks=3,
    rollback_window_sec=86400, retrain_pause_sec=86400)
orch.retrain_pause_state()   # >0 이면 (해당 unixtime까지) 재학습 일시중지 상태
```

**Alertmanager MLOps 규칙(M7-K)** — `config/alert_rules.yml` `daytrade-mlops` 그룹:
`KpiRegression`(`daytrade_kpi_passed==0`), `ModelReloadStorm`(15분 핫스왑 ≥3), `RetrainStalled`(26h
버전 정체), `ModelServingUninitialized`(`model_version==0` 10분).

### 고속 바이너리 틱 스토어 (KDB+/q 경량 대안)

CSV 텍스트 파싱 없이 `struct` 언팩만으로 적재하는 고정폭 컬럼형 스토어. 타임스탬프 정렬을 전제로
시간범위 질의를 **이진 탐색(O(log n + k))** 으로 처리하고, 임의접근(`get`)도 O(1) 입니다.

```python
from daytrade.storage import TickStore, write_ticks_store, csv_to_store

write_ticks_store("data/btc.dts", feed.ticks(), depth=10)   # 또는 csv_to_store("btc.csv", "btc.dts")
store = TickStore("data/btc.dts")
print(len(store), store.time_bounds())                       # 틱 수, (first_ts, last_ts)
for tick in store.read_range(start_ns, end_ns):              # 시간범위 슬라이스(이진 탐색)
    ...
pipeline.run(store.to_feed())                                # MarketFeed 로 그대로 결선
```

**실데이터 장기 캡처(증설 전 데이터 축적)** — 라이브 피드를 UTC 일별 `.dts` 로 무손실 적재(자동 재연결·재시작 이어쓰기). CLI 입력은 `.dts` 를 직접 수용한다.

```bash
python scripts/capture_to_store.py --source binance --symbol BTCUSDT --out-dir data/ticks --max-ticks 1000000
python -m daytrade.cli walkforward --csv data/ticks/ticks_BTCUSDT_20260624.dts --n-splits 5   # .dts 직접 입력
```

**백테스트 리포트 고도화** — equity curve 기반 위험조정 지표 + HTML/JSON 리포트.

```bash
python -m daytrade.cli sim --ticks 5000 --report-html out/report.html --report-json out/report.json
```

```python
from daytrade.backtest import analyze_run, report_to_html
a = analyze_run(report.metrics)     # Sortino/Calmar/MDD지속/수익팩터/VaR·CVaR/승률
report_to_html(report.metrics, "report.html")   # 인라인 SVG 스파크라인(의존성 0)
```

### Backtrader 교차검증 어댑터

틱→OHLCV 바 집계 코어(`ticks_to_ohlcv`)는 **의존성 0**, 결선부는 `pip install backtrader pandas` 시 활성.

```python
from daytrade.backtest import ticks_to_ohlcv, run_backtrader
bars = ticks_to_ohlcv(feed.ticks(), bar_sec=1.0)             # 의존성 없이 항상 동작
res = run_backtrader(feed.ticks(), MyStrategy, bar_sec=1.0, cash=100_000)  # backtrader 필요
```

### 인프로세스 장애 주입 (Chaos-Mesh 경량 대안)

K8s 없이 끊김·드롭·손상·지연·주문거부를 결정론적으로 주입해 `LiveRunner` 의 자동 재연결·롤백 가드 등
복원 동작을 단위 테스트로 검증합니다.

```python
from daytrade.testing import FaultInjectingFeed, FlakyFeedFactory, FlakyExecutor

# 초기 2세션은 3틱 후 끊김 → 이후 정상(끊김→백오프 재연결→회복 재현)
factory = FlakyFeedFactory(lambda: CsvReplayFeed("btc.csv"), fail_sessions=2, disconnect_after=3)
runner = LiveRunner(pipeline, feed_factory=factory, config=RunnerConfig(symbol="BTCUSDT"))

bad_feed = FaultInjectingFeed(feed, disconnect_after=100, drop_indices={5, 9}, corrupt_indices={20})
flaky_exec = FlakyExecutor(executor, reject_indices={3}, raise_indices={7}, partial_indices={11})
```

### 추론 레이턴시 실측 (≤1ms 인수기준)

```bash
python scripts/measure_inference_latency.py --sim --ticks 5000              # 개발 PC(ORT/휴리스틱)
python scripts/measure_inference_latency.py --csv data/sol.csv --engine model.plan --target-ms 1.0  # 서버(TensorRT)
# 출력: backend, warmup_ms(<5ms), p50/95/99(us), meets_target
```

### 서버 실행 (M3 C++ 빌드 · RLlib 분산 PPO 실측)

```bash
# (1) M3 C++ 코어 빌드 + 골든 동일성 자동 검증 — build.ps1 이 MSVC↔MinGW 자동 감지
pwsh cpp/build.ps1          # Windows: MSVC C++ 워크로드 또는 MinGW-w64(UCRT). 빌드 후 골든 테스트 자동 실행
bash cpp/build.sh           # Linux(GCC/Clang)
#   ※ 개발 PC(Windows/Py3.10)에서 MinGW-w64 16.1.0(UCRT)로 실제 빌드·골든 통과 검증됨.

# (2) RLlib 분산 PPO 처리량/수렴 실측 (ray[rllib] 설치 시 RLlib, 아니면 numpy 폴백)
pip install "ray[rllib]" gymnasium
python scripts/bench_rllib_ppo.py --csv data/sol_events.csv --algo ppo \
    --iterations 20 --num-env-runners 4
# 출력: backend, steps_per_sec(처리량), reward_curve(수렴), final_mean
#   ※ 로컬 단일노드 실측(ray 2.55.1): 2 env-runners, 32k steps, reward 음→양 수렴 확인.
```

---

## 4. 안전 게이트 (실거래 차단)

실거래(LIVE)는 **두 조건을 모두** 만족해야만 활성화됩니다:

1. `TradingConfig.mode == TradingMode.LIVE`
2. 환경변수 `DAYTRADE_ALLOW_LIVE == "I_UNDERSTAND_THE_RISK"`

하나라도 어긋나면 실행기는 **자동으로 paper(모의)로 강등**됩니다. 또한 LIVE 가 인가돼도
`is_live == True` 인 사용자 제공 `OrderExecutor` 가 없으면 파이프라인 생성이 거부됩니다.

추가 안전장치:
- **레이턴시 서킷브레이커**: 처리 지연 > `max_latency_ms`(기본 10ms) → 신규 진입 중단
- **당일 손절/익절**: 자본 대비 ±2% 도달 시 거래 중단
- **슬리피지 가드**: 예상 슬리피지 > `max_slippage_pct` → 주문 거절
- 포지션 수량/가치, 총노출, 레버리지 한도

---

## 5. 설계서 대비 — 구현 범위

| 설계 항목 | 이 저장소 | 비고 |
|-----------|-----------|------|
| Feature/Detection/Risk/Execution/Monitoring/Backtest | ✅ Python 구현 | 동작·테스트 완료 |
| AI Inference | ✅ 휴리스틱 + 학습 파이프라인(M2) + ONNX/Numpy/Sequence 어댑터 | 학습→export→추론 라운드트립 완결. TensorRT INT8·walk-forward 는 GPU/실데이터 단계(M2 후속) |
| 모의투자/시뮬레이션 | ✅ | 기본 모드 |
| 실거래 브로커(FIX/REST/WebSocket) | 🔌 인터페이스만 | 본인 계정·어댑터 필요(법·규제) |
| DPDK 커널바이패스 / FPGA / 코로케이션 / 하드웨어 타임스탬프 | ❌ 환경 외 | 실 HFT 인프라 영역(전용 HW·회선·코로케이션) |
| 1ms 이하 레이턴시 | ❌ | Python 처리 지연은 수십~수백 µs 측정되나, 네트워크/거래소 왕복은 인프라 의존 |

이 구현은 **알고리즘·리스크·백테스트·모의체결**까지 완결적으로 동작하며, 초저지연
인프라(DPDK/FPGA/코로케이션)와 실거래 브로커 연동은 동일 인터페이스로 확장 가능한 구조입니다.

---

## 6. 테스트

```bash
cd apps/daytrade-ai
python -m pytest -q      # numpy 경로 항상 통과. onnx/torch 설치 시 export 라운드트립도 실행
```

커버리지: features / detection / inference / risk / portfolio / paper execution / safety gate / pipeline / backtest.
