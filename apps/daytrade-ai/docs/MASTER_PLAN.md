# daytrade-ai 마스터 플랜 (설계서 100% 구현 SSOT)

> 목적: 사장님이 제시한 **「AI 기반 주식 단타(스캘핑·초단타) 자동매매 시스템」 설계서(1️⃣~15️⃣)** 를
> **타협 없이 그대로** 구현하기 위한 단일 기준 문서. 시간 날 때마다 틈틈이 진행하는 **장기 과제**이며,
> 서버는 **최고 사양**으로 구축한다는 전제(초저지연 HFT 급)를 깔고 정밀하게 설계한다.
>
> 이 문서는 SSOT 이다. 작업할 때마다 이 문서의 체크박스를 갱신한다.

### 문서 세트(함께 보기)
- **`MASTER_PLAN.md`** (본 문서): 무엇을/언제 — 마일스톤·작업·인수기준·추적 매트릭스.
- **`MASTER_TECH_SPEC.md`**: 어떻게 — 아키텍처·설계 구조도(mermaid)·인터페이스·데이터 스키마·레이턴시 버짓·보안.
- **`ANALYSIS_CHECKLIST.md`**: 중·장기 분석 체크리스트(시장·전략·리스크·기술·규제·운영) + 분기 리뷰 게이트.

---

## 0. 설계 원칙 / 전제

- **최종 목표 레이턴시**: end-to-end ≤ 5 ms (코로케이션 시 2~3 ms), 추론 ≤ 1 ms, ingest ≤ 2 µs.
- **언어 분할(설계서 §2 준수)**: 핵심 순환은 **C++/Rust**, 리스크는 **Go/Rust**, 전략·모니터링·튜닝은 **Python**.
- **GPU**: 실서버 RTX 5090 32GB 가용(설계서의 A100/A6000 대체). TensorRT FP16/INT8.
- **안전 최우선**: 모의(paper)·시뮬 → 페이퍼트레이딩 → 소액 실거래 순. 실거래는 **거래소 사전 승인 + 규제 준수**가 코드보다 선행.
- **증분 가능**: 각 마일스톤은 독립적으로 빌드·검증·배포 가능해야 한다.
- **회귀 방지**: 모든 모듈은 단위/통합 테스트 + 레이턴시 벤치를 동반한다.

---

## 1. 성능 인수 기준 (SSOT — 설계서 §7·§12 종합)

| 지표 | 목표 | 출처 | 측정 방법 |
|------|------|------|-----------|
| Ingest 수신 | ≤ 2 µs | §2 | DPDK rx + hardware TS |
| Feature 변환 | ≤ 0.5 ms | §2 | C++ 벤치 |
| AI 추론 | ≤ 1 ms (0.5 목표) | §2/§3-3 | TensorRT enqueue+sync |
| 시그널 전달 | < 1 ms | §2 | lock-free queue 측정 |
| Risk 체크 | < 0.5 ms | §2 | Go/Rust 벤치 |
| 주문 라우팅(네트워크) | ≤ 0.5 ms | §2 | FIX FAST + NIC offload |
| **시그널→주문 e2e** | **< 5 ms** | §7 | tcpreplay + dpdk-app |
| 슬리피지 | ≤ 0.05 % | §7 | 백테스트/페이퍼 측정 |
| Sharpe (백테스트) | > 2.0 | §7 | 10M ticks 시뮬 |
| 실시간 VaR | ≤ 0.5 % | §12 | Monte-Carlo 100 samples |
| 서킷브레이커 | latency > 10 ms → 자동 pause | §8/§12 | 런타임 가드 |
| PTP 시계 정확도 | ± 100 ns | §4/§12 | IEEE 1588v2 + Chrony |
| 모델 warm-up | < 5 ms | §12 | cold-start 벤치 |

> 이 표의 모든 값은 **인수(acceptance) 게이트**다. 미달 시 다음 단계(특히 실거래)로 진행 불가.

---

## 2. 설계서 → 마일스톤 추적 매트릭스

| 설계서 절 | 내용 | 마일스톤 | 상태 |
|-----------|------|----------|------|
| 1️⃣ 전체 아키텍처 | 컴포넌트 토폴로지 | 전 마일스톤 | 🟡 진행 |
| 2️⃣ 핵심 모듈 상세 | 언어·레이턴시 목표 | M3~M6 | ⬜ |
| 3️⃣ 초 감지 로직 | OBI/volume/momentum/VWAP/뉴스/SNS/order-flow | M1·M3 | 🟡 부분(Python) |
| 3-2 감지 파이프라인(C++) | lock-free ring-buffer 루프 | M3 | 🟡 스캐폴드+골든테스트(빌드 서버) |
| 3-3 AI-Inference 연동 | TensorRT enqueue | M4 | 🟡 학습→ONNX→런타임(Python) 완료, TensorRT는 M4 |
| 4️⃣ 하드웨어·네트워크 | Solarflare/DPDK/FPGA/PTP/Co-Lo | M9 | ⬜ |
| 5️⃣ 소프트웨어 스택 | Kafka/Pulsar/FlatBuffers/ONNX/FIX… | M1~M8 | 🟡 부분(ONNX 학습·추론 연결) |
| 6️⃣ 샘플 파이프라인 | Python+C++ 바인딩 | M3·M4 | 🟡 Python 레퍼런스 + C++ pybind11 스캐폴드 |
| 7️⃣ 백테스트→실전 | 데이터·시뮬·RL·paper·재학습·실전 | M1·M2·M5·M7·M11 | 🟡 시뮬+학습모델+RL+재학습 오케스트레이션(트리거→핫스왑) 완료 |
| 8️⃣ 위험·규제·보안 | 한도/규제/HSM/감사로그 | M6·M10 | 🟡 리스크 코어 + 불변 감사로그(해시체인) 완료 |
| 9️⃣ 자동 튜닝 | Optuna TPE + 스케줄러 | M2(탐색)·M7(자동화) | 🟢 워크포워드 Sharpe+리스크제약 TPE 탐색 + 재학습 게이트 결합 + 경량 인프로세스 스케줄러(일일 재학습/5분 튜닝) 완료, Airflow 분산은 선택 |
| 🔟 배포·운영 | Terraform/K8s/Helm/Argo | M8 | ⬜ |
| 11️⃣ 비용·성능 추정 | 인프라 비용 | M9(참고) | ⬜ |
| 12️⃣ 구현 전 체크리스트 | 네트워크/AI/오더북/위험/법/테스트/보안 | 전 마일스톤 게이트 | 🟡 |
| 13️⃣ 참고 오픈소스 | 링크 모음 | 부록 A | ✅ |
| 14️⃣ 5-step 로드맵 | 거래소 연결→실전 | M1·M3·M4·M5·M7 | 🟡 |
| 15️⃣ 핵심 요약 | — | — | — |

범례: ✅ 완료 · 🟡 부분 · ⬜ 미착수 · 🟥 차단(외부 의존)

---

## 3. 현재 상태 (M0 — 완료된 Python 레퍼런스)

설계서 §6 의 Python 파이프라인을 **동작·테스트되는 레퍼런스 구현**으로 완성(`apps/daytrade-ai/daytrade/`).
이는 M3+ 의 C++ 고성능 구현에 대한 **정답지(골든 레퍼런스)** 이자 백테스트/전략 검증 베이스다.

- [x] 도메인 타입(`types.py`), 설정·안전 이중 게이트(`config.py`)
- [x] Feed 인터페이스 + 합성 시뮬 + CSV 리플레이(`feed/`)
- [x] Feature(OBI·OBI z-score·volume spike·micro-momentum·VWAP·spread)(`features/`)
- [x] Detection(§3-2 의사코드 규칙)(`detection/`)
- [x] AI 추론 플러거블(휴리스틱 + ONNX 어댑터)(`inference/`)
- [x] Risk(포지션·총노출·레버리지·서킷브레이커·슬리피지 가드)(`risk/`)
- [x] Execution(OrderExecutor 인터페이스 + PaperExecutor + Portfolio)(`execution/`)
- [x] Pipeline + Monitoring(레이턴시/슬리피지/P&L/Sharpe/MDD)
- [x] Backtest 러너 + CLI, 단위 테스트 44건, 마켓플레이스 등록(id=45)

**격차(gap)**: 현재는 순수 Python(ms~µs 처리지만 GIL·인터프리터 한계) → 설계서의 sub-ms·µs 목표는
C++/DPDK/lock-free/TensorRT 로 재구현해야 달성. M1부터 단계적으로 교체·확장한다.

---

## 4. 마일스톤 상세

각 마일스톤: **목표 / 구성요소(정확한 스택) / 작업 / 산출물 / 인수기준 / 의존성**.

### M1 — 실데이터 피드 & 백테스트 신뢰성 (Python 확장) ✅ 핵심 완료
- **목표**: 합성 데이터를 실데이터로 교체, 재현 가능한 회귀셋 확보, 백테스트 정합성 확보.
- **1차 대상 시장**: 암호화폐(Binance, 24h·무료 L2 top-10). 이후 미국주식(Alpaca)/KRX 확장.
- **구성요소**: WebSocket 피드(Binance depth10@100ms + aggTrade), CSV 레코더(CsvReplayFeed 포맷), 추후 FlatBuffers/Cap'n Proto(§5).
- **작업**:
  - [x] `feed/binance.py` — `MarketFeed` 구현(실시간 L2 top-10 + 체결 정규화, 순수 함수 + 라이브 WS 브리지, 8개 단위테스트)
  - [x] `feed/recorder.py` — 틱→CSV(CsvReplayFeed 포맷) 저장·통과기록(RecordingFeed), 라운드트립 테스트
  - [x] CLI `record` 서브커맨드(라이브 캡처 → CSV → `replay` 백테스트로 연결)
  - [x] 백테스트 비용 모델 보강(수수료 `commission_bps`·매도세 `sell_tax_bps`·부분체결 `partial_fill`) + 6개 테스트. (틱 순차 처리로 look-ahead 없음; 체결지연은 모니터링 레이턴시로 추적)
  - [x] Upbit(L2, 무료)·Alpaca(L1 IEX) 피드 어댑터 추가(순수 정규화 + 주입 소스 + 라이브 WS) + 11개 테스트
  - [x] 직렬화 스키마(FlatBuffers `schemas/market.fbs`) 정의 + 골든 일치 테스트(FEATURE_NAMES 순서 강제)
  - [x] **실데이터 루프 실행**: 실제 Binance BTCUSDT 2500틱 캡처(`data/btcusdt_real.csv`) → replay/walkforward/tune 재검증
  - [x] **고속 바이너리 틱 스토어(KDB+/q 경량 대안)** — `storage/tickstore.py`: 의존성 없는 고정폭 컬럼형 포맷(`TickStoreWriter`/`TickStore`/`TickStoreFeed`, **이어쓰기(append) 지원**). 스토어 1개=종목 1개(헤더 심볼 고정, KDB+ 파티셔닝 관례), 타임스탬프 정렬 전제 **`read_range` lower-bound 이진 탐색(O(log n + k))** + 임의접근(`get`). CSV→스토어 변환(`csv_to_store`), CSV 대비 무파싱·소용량(테스트로 검증). 8개 테스트
  - [x] **실데이터 장기 캡처 → 일별 스토어 적재** — `storage/recorder.py`(`RollingTickStoreWriter`: UTC 일별 `.dts` 로테이션·재시작 이어쓰기, `StoreRecordingFeed`: 통과기록) + `scripts/capture_to_store.py`(Binance/Upbit/Alpaca/sim 소스, 자동 재연결 백오프, SIGINT/SIGTERM 안전종료). **증설 대기 기간 동안 실데이터 축적 → GPU 확보 즉시 6개월+ walk-forward/INT8 투입**. 5개 테스트
  - [x] **틱 스토어 CLI 결선** — `cli.load_replay_feed` 확장자 디스패치(`.dts`→`TickStoreFeed`, 그 외→CSV). `replay`/`walkforward`/`tune`/`train`/`events`/`rl` 입력이 `.dts` 를 직접 수용(대용량 적재 가속). 3개 테스트
  - [x] **Backtrader 연동 어댑터(교차검증/리서치)** — `backtest/backtrader_adapter.py`: 틱→OHLCV 바 집계 코어(`ticks_to_ohlcv`, **의존성 0**) + pandas/backtrader 결선부(`bars_to_dataframe`/`ticks_to_backtrader_feed`/`run_backtrader`, 미설치 시 설치 안내 ImportError). 6개 테스트(bt 미설치 시 결선부 skip)
  - [x] **백테스트 리포트 고도화** — `backtest/report.py`: equity curve 기반 위험조정 지표(Sortino·Calmar·낙폭지속·수익팩터·VaR/CVaR·승률) + 의존성 0 인라인 SVG 스파크라인 **HTML 리포트** + JSON. CLI `sim`/`replay --report-json/--report-html`. 5개 테스트
- **산출물**: 실데이터 캡처 CSV(회귀셋 `data/btcusdt_real.csv`), 비용 반영 백테스트, `schemas/market.fbs`, 다중 거래소 어댑터, **바이너리 틱 스토어(`.dts`)**, **Backtrader 어댑터**
- **인수기준**: 라이브→기록→리플레이 라운드트립 100% 일치(달성), 비용(수수료·세금·부분체결) 반영(달성), 틱 스토어↔CSV 라운드트립 일치(달성)
- **의존성**: 라이브 캡처 시 `websockets`(미설치 시 안내) + 네트워크, Alpaca 라이브는 API 키. 틱 스토어는 **의존성 0**(표준 `struct`). Backtrader 어댑터 결선부는 `backtrader`·`pandas`(선택)
- **상태**: ✅ 핵심 완료 (잔여: 실데이터 장기 캡처는 운영 단계. KDB+ 자체는 `storage/tickstore.py` 로 경량 대체)
- **실데이터 검증 발견(중요)**:
  - **자산 스케일 의존**: 암호화폐 오더북 수량은 작아 `|OBI|`가 수~수십 수준(BTC 중앙값 ~3.6). 합성용 `obi_threshold=1e6`/탐색범위(1e4~5e5)는 부적합 → walkforward/tune CLI 에 `--obi-threshold`·`--calibrate-obi`(데이터 분포 p25~p95 자동 보정) 추가.
  - **클래스 불균형 함정**: 캡처 윈도가 매우 잔잔(2500틱 ~10bps 폭)해 ±bps 이벤트가 희소 → 라벨 거의 0 → **정확도 ~0.94 가 무의미**(전부 0 예측). `walk_forward_validate` 에 **balanced_acc + pos_rate** 추가해 불균형을 노출(실측 bal_acc≈0.5, pos_rate≈0.06).
  - **레짐 의존**: 잔잔한 윈도에서는 OOS 거래/수익 ≈ 0(튜닝 best_value=0). 합성 Sharpe 40+ 와 대비되는 정직한 결과 → 변동성 있는 장시간 캡처·다중 레짐 회귀셋이 후속 필수.
  - **장시간 재검증(6000틱 ≈ 10분, BTCUSDT)**: 여전히 잔잔(14.4bps 레인지, |OBI| p95≈8.7). 라벨 1bps 로 낮추면 OOS `bal_acc≈0.5`·`pos_rate≈2~3%`·`overfit_gap≈0.002` → **클래스 불균형(이벤트 희소)** 을 정직하게 노출(raw acc 0.97↑ 무의미). 튜닝 best_value=0 재확인.
  - **고변동성 종목 캡처(6000틱, SOLUSDT·DOGEUSDT)**: 미 증시 개장/지표 시간대를 세션 중 대기할 수 없어 **고베타 알트코인**으로 변동성 확보. 레인지 SOL 30.1bps·DOGE 32.2bps(BTC의 ~2배), 틱당 수익률 σ SOL 0.305bps(최고)>DOGE 0.22bps>BTC. 워크포워드(2bps 라벨): 모든 폴드 `pos_rate>0`(이벤트 존재), `overfit_gap≈0`(과적합 없음). 튜닝 best_value=0(지속 OOS 엣지는 여전히 어려움). **RL 결과 — 변동성이 미세 엣지를 만듦**: random ≈ −5430 → 학습 greedy **SOL +9.99 / DOGE +16.9**(BTC 잔잔 −17 대비 양전환). 두 알트 모두 윈도 내 소폭 하락 → 숏/플랫 편향(long=0). 결론: **변동성↑ → 학습 신호↑ 가설 실증**. 다음 관문은 **실제 급변 이벤트(뉴스/청산 캐스케이드) 구간 타게팅 캡처**.

### M2 — AI 학습 파이프라인 (PyTorch → ONNX → TensorRT) 🟡 핵심 완료
- **목표**: 규칙 기반 → 학습 기반 모델, 과최적화 방지.
- **구성요소**: PyTorch(LSTM/Transformer), Ray-RLlib/Stable-Baselines3(DDPG), ONNX export, TensorRT INT8, Optuna(탐색).
- **작업**:
  - [x] 라벨링 파이프라인(forward-return, look-ahead 차단) — `training/labeling.py`
  - [x] 데이터셋 빌더(런타임 `FeatureEngine` 재사용 → train/serve skew 제거) + 시퀀스 윈도잉 + 시간순 분할 — `training/dataset.py`
  - [x] 순수 numpy 로지스틱(표준화 내장, 의존성 0, 항상 동작) + JSON 직렬화 — `training/logreg.py`
  - [x] LSTM/Transformer 학습 + 표준화 내장 모듈 — `training/torch_trainer.py`(torch 선택)
  - [x] ONNX export: numpy(`onnx.helper` 직접 그래프) / torch(`torch.onnx`) — `training/onnx_export.py`
  - [x] 런타임 연결: `OnnxModel`(단일 [1,F]) / `SequenceOnnxModel`(윈도 [1,L,F]) / `NumpyLogRegModel`(JSON, dep-free), `load_model` 확장자 디스패치
  - [x] CLI `train` 서브커맨드(--backend numpy|torch, --kind lstm|transformer) + 검증지표 출력
  - [x] **워크포워드 검증 프레임**(과최적화 방지) — `training/walkforward.py`: rolling/anchored 분할(purge=horizon embargo), 분류 OOS+과최적화 갭(`validate`), 폴드별 학습→OOS 파이프라인 백테스트(`backtest`), CLI `walkforward` 서브커맨드
  - [x] 테스트: 라벨/데이터셋/로지스틱/워크포워드(항상 실행) + ONNX·torch 라운드트립(설치 시 실행) — JSON↔ONNX 예측 일치 확인
  - [x] **하이퍼파라미터 탐색**(설계서 §9) — `training/tuning.py`: 워크포워드 OOS 점수를 목적함수로 최대화. optuna TPE + 순수 random 폴백(미설치 시), CLI `tune` 서브커맨드
  - [x] **RL 에이전트(Gym-Trading 환경)** — `daytrade/rl/`: `TradingEnv`(Gymnasium 호환, 운영 `FeatureEngine` 재사용 → skew 제거, **수익률 기반 스케일 불변 보상** − 전환비용), CLI `rl` 서브커맨드. 실데이터(BTCUSDT 6000틱) 검증: random −5434 → 학습 greedy ≈ −17(잔잔 레짐 → 거의 플랫 수렴, **가짜 수익 없음**).
  - [x] **PPO 교체** — `rl/ppo.py`: 순수 numpy actor-critic(GAE(λ)+클리핑 surrogate+엔트로피), REINFORCE(`agent.py`) 대체. CLI `rl --algo ppo|reinforce`(기본 ppo). 변동성 캡처(SOL/DOGE)·이벤트 윈도에서 양(+) 학습 확인.
  - [x] **RLlib 브리지** — `rl/gym_env.py`(`make_gym_trading_env`, gymnasium 어댑터) + `rl/rllib_train.py`(`train_ppo_rllib`): ray[rllib] 설치 시 동일 `TradingEnv` 를 RLlib PPO 로 학습(미설치 시 명확한 ImportError, numpy PPO 폴백).
  - [x] **급변 이벤트 타게팅 캡처** — `feed/event_capture.py` + CLI `events`: 변동성/거래량/OBI 트리거 구간만 pre/post 윈도로 농축 기록(SOL 6000틱 → 이벤트 1,145틱 추출). 잔잔 구간 희석 제거 → 회귀셋 품질↑.
  - [x] **연속 행동(포지션 사이즈) + ONNX 서빙 → M4 연결** — `TradingEnv(action_mode="continuous")` + `ContinuousPPOAgent`(Gaussian 정책, tanh-bounded mean·GAE·클리핑) + `export_continuous_policy_to_onnx`(표준화 내장 그래프) + `OnnxPolicyModel`(stateful, 포지션 추적 → prob_buy/prob_sell 사상). CLI `rl --algo cppo --onnx ...`. 골든: ONNX↔numpy 정책 1e-5 일치.
  - [x] **RLlib 실측 하니스(turnkey)** — `scripts/bench_rllib_ppo.py`(ray 설치 시 RLlib 분산 PPO, 미설치 시 numpy 폴백) + `daytrade/rl/bench.py`(`benchmark_ppo`: 처리량 steps/sec·수렴 reward_curve). 로컬 검증 완료(numpy ~1.9만 steps/sec). `.build()`→`.build_algo()` 신 API 대응.
  - [x] **RLlib 단일 노드 실측(로컬, ray 2.55.1)** — Windows/Py3.10 에 `ray[rllib]` 설치 후 신 API 스택 PPO 학습 확인. local runner(`--num-env-runners 0`): 6,000 steps, 674 steps/sec, reward −2209→−1271. 분산 워커(`--num-env-runners 2`): 32,000 steps, 818 steps/sec, reward **−3264→−1281→−52→+826(양수 수렴)**. (※ 초기화 오버헤드 포함값 — 처리량 절대치는 numpy 단일프로세스가 더 높으나 RLlib 은 분산·GPU 확장성이 목적.)
  - [ ] RLlib 분산 학습 GPU 실측(서버) — RTX 5090 서버에서 `--num-env-runners 4+` 로 처리량/수렴 스케일 확인
  - [ ] TensorRT INT8 변환 + 정확도 검증, walk-forward 6개월+ 히스토리 — GPU/데이터 단계
  - [ ] cold-start warm-up(< 5 ms) 벤치 — M4 와 함께
- **산출물**: `model.json`(dep-free) / `model.onnx`(생산) / `seq_*.onnx`(LSTM·Transformer), 학습/검증 리포트(JSON), 워크포워드 OOS 리포트
- **인수기준(현 단계)**: 학습→export→런타임 추론 라운드트립 일치(달성), 분리가능 신호 학습 검증(달성), 워크포워드 OOS 평가 프레임(달성). (walk-forward Sharpe>2.0·INT8 손실은 **실데이터**·GPU 단계 — 현재 합성 데이터 Sharpe 는 데모용)
- **의존성**: numpy(필수) / torch·onnx·onnxruntime(선택). TensorRT·6개월+ 틱데이터는 후속

### M3 — C++ 핵심 순환 (Low-Latency Ingest + Feature + Detection) ★핵심  🟢 빌드·골든 검증 완료(dev=MinGW-w64 UCRT / 서버=MSVC·GCC)
- **목표**: 설계서 §3-2 의 sub-ms C++ 루프 실구현. Python 레퍼런스와 **수치 동일성** 보장.
- **구성요소**: C++20, DPDK/Solarflare Onload, lock-free ring-buffer(64KB 페이지 정렬), Eigen, pybind11(Python 바인딩).
- **진척(이번 단계)**: 개발 PC(Windows/Py3.10)에 **MinGW-w64 16.1.0(UCRT)** 설치 후 pybind11 모듈을 실제 빌드,
  골든 동일성 테스트 **통과**(피처 1e-9 + detection side/confidence 일치). `build.ps1` 은 MSVC↔MinGW 자동 감지 +
  Python 실행기 고정 + 골든 자동 실행으로 **dev/서버 공통 turnkey**. 산출물(.pyd)은 정적 링크로 런타임 DLL 의존 없음.
  - [x] `cpp/include/daytrade/market.hpp` — `OrderBookLevel`/`FeatureVector`/`Signal` (types.py·market.fbs 미러)
  - [x] `cpp/include/daytrade/feature_engine.hpp` — OBI/z-score/volume-spike/VWAP/micro-momentum, **engine.py 연산순서 라인 미러**
  - [x] `cpp/include/daytrade/detection_engine.hpp` — §3-2 시그널 로직 + confidence 합성(가중치/스쿼시 동일)
  - [x] `cpp/src/bindings.cpp` + `CMakeLists.txt`(MINGW 정적링크 분기) + `build.ps1`(MSVC/MinGW 자동)/`build.sh` (pybind11)
  - [x] **골든 테스트 통과** `tests/test_cpp_golden.py` — 1e-9 피처 동일성 + side/confidence 동일성(C++ 모듈 빌드 후 실측)
  - [ ] `cpp/ingest/` — DPDK rx, zero-copy ring-buffer, hardware timestamp(PTP) *(서버 빌드 후)*
  - [ ] `LockFreeQueue<MarketTick>`(캐시라인 정렬), Eigen 벡터화
  - [ ] 마이크로벤치(Google Benchmark): ingest ≤ 2µs, feature ≤ 0.5ms, signal < 1ms
- **산출물**: `daytrade_cpp`(pybind11 모듈) → `libdetector.so`/벤치 리포트로 확장
- **인수기준**: §1 레이턴시 표 충족, Python 레퍼런스 대비 시그널 동일성(골든 테스트 통과)
- **의존성**: C++20 컴파일러 + CMake(서버). Solarflare NIC + DPDK 환경(없으면 AF_XDP/일반 소켓 폴백 모드 제공)

### M4 — AI-Inference 엔진 (C++ TensorRT/ONNX Runtime)  🟡 파이썬 결선 스캐폴드 완료(엔진 빌드는 GPU 서버)
- **목표**: §3-3 추론 스레드 — CPU·GPU 비동기, ≤ 1 ms.
- **구성요소**: TensorRT(C++ API), ONNX Runtime(CUDA EP), CUDA stream, lock-free signal queue 연동.
- **진척(이번 단계)**: GPU 없이도 검증 가능한 **파이썬 측 결선 스캐폴드 + graceful fallback** 완료.
  연속 RL 정책 ONNX 를 실제 파이프라인 백테스트에 물려 PnL 비교(휴리스틱 대비)까지 동작 확인.
  - [x] `daytrade/inference/trt.py` — `load_inference_model`(TensorRT→ORT(CUDA)→ORT(CPU)→Heuristic 폴백 팩토리)
  - [x] `TensorRTModel` + `build_engine`(FP32/FP16/INT8, calibrator) — guarded import(서버), 미설치 시 명확한 안내
  - [x] **모델 핫스왑(Blue-Green)** `HotSwapModel`(stage→activate 원자 교체, 스레드 안전)
  - [x] **추론 레이턴시 히스토그램** `LatencyHistogram`(p50/p95/p99) + `MeasuredModel` 데코레이터
  - [x] C++ 인터페이스 스캐폴드 `cpp/include/daytrade/inference_engine.hpp`(`IInferenceEngine`/`TensorRtEngine`/`HotSwapInference` lock-free atomic, §3-3)
  - [x] **C++ TensorRT 비동기 구현** `cpp/inference/inference_engine_trt.cpp` — `enqueueV3` + CUDA stream(H2D/D2H async, PImpl), `DAYTRADE_WITH_TENSORRT` 가드(서버 빌드)
  - [x] **추론 레이턴시 실측 하니스** `scripts/measure_inference_latency.py` — p50/95/99 + warmup, 백엔드 자동(TRT→ORT→Heuristic). 로컬 휴리스틱 p99≈0.7µs·warmup<5ms 확인
  - [x] 연속 RL 정책 ONNX → 파이프라인 백테스트 PnL 비교 `scripts/compare_policy_pnl.py` + `load_model` 자동 디스패치(출력차원1→OnnxPolicyModel)
  - [ ] TensorRT INT8 보정(calibrator) + 정확도 검증, 추론 ≤1ms **GPU 실측**(RTX 5090, `--engine model.plan`)
- **산출물**: inference 라이브러리 + 추론 레이턴시 히스토그램(JSON)
- **인수기준**: 추론 ≤ 1 ms(0.5 목표), warm-up < 5 ms
- **의존성**: M2 모델, GPU(TensorRT)

### M5 — Order Router + Execution (FIX/FAST) + Paper-Trading
- **목표**: §2/§6 주문 라우팅·체결, 페이퍼 트레이딩 라이브.  🟢 코어 구현·테스트 완료(실거래 세션은 서버/브로커)
- **구성요소**: QuickFIX/N(또는 QuickFIX/J), FIX FAST, mTLS, IBKR Paper/Alpaca, RDMA(코로케이션 시).
- **진척(이번 단계)**: FIX 와이어 포맷·라우터·영속·페이퍼봇을 **의존성 0 으로 구현 + 11개 테스트 통과**.
  실제 FIX 세션(전송)은 `config/fix.cfg`(QuickFIX 이니시에이터) + 브로커 계정으로 서버에서 끼운다(테스트 가능한 코어 + 서버 전송).
  - [x] `OrderExecutor` 어댑터 `FixExecutor` — FIX 4.4 `NewOrderSingle`(35=D, 시장가/지정가/IOC), `ExecutionReport`(35=8) 파싱
  - [x] FIX 코덱 `execution/fix.py` — SOH/BodyLength/CheckSum 정확 생성·검증(`verify_checksum`), 손상 탐지
  - [x] `SimulatedFixVenue` — 와이어 왕복(encode→decode→매칭→encode) 모의 거래소(페이퍼/테스트)
  - [x] `OrderRouter` — 멱등 client_order_id, 슬리피지 가드, 거절 지정가 **재견적(re-quote)**, 체결 피드백 콜백 + **예외 흡수**(실행기 단절/예외를 거절로 격하 → 파이프라인 크래시 방지, `stats.errors`). `FlakyExecutor`(거부/예외/부분체결) chaos 주입 복원력 테스트 8개
  - [x] `TradeStore`(sqlite) — 체결/자본곡선 영속(상태 DB) + 재학습 데이터 적재 지점
  - [x] **페이퍼 트레이딩 봇** `scripts/paper_trading_bot.py` — 피드(sim/csv/live)→파이프라인→모의주문→sqlite(자본곡선 스냅샷)
  - [x] `config/fix.cfg` — QuickFIX/N 이니시에이터 템플릿(mTLS·재전송/시퀀스·24h 세션)
  - [x] **Alpaca 주문 어댑터** `execution/alpaca_executor.py` — `build_alpaca_order`/`parse_alpaca_fill`(REST v2, 의존성0 테스트) + `AlpacaExecutor`(paper 기본, `requests` 전송은 서버). 4개 테스트 통과
  - [x] **라이브 상시운영 러너** `daytrade/ops/runner.py`(`LiveRunner`) + `scripts/live_ops.py` — 자동재연결(지수 백오프)·heartbeat·UTC 일일리포트, M6(`/metrics`·감사로그·알림)+`TradeStore` 결선. 그레이스풀 종료(`request_stop`)·헬스(`is_healthy`). 9개 테스트 통과(주입 시계로 네트워크 없이 검증)
  - [x] **서버 데몬화 패키징** `deploy/` — systemd 유닛(`daytrade-live.service`, `Restart=always`·`SIGTERM`·`TimeoutStopSec`·보안 하드닝) + `Dockerfile`(비루트·`STOPSIGNAL SIGTERM`·`HEALTHCHECK /healthz`) + `.dockerignore` + env 템플릿. `/healthz`(liveness)·`/readyz`(readiness=서킷브레이커·틱 신선도)
  - [ ] 실 브로커 세션 실연동: IBKR=FIX(`FixExecutor`+`fix.cfg`), Alpaca=REST(`AlpacaExecutor`) — **계정/네트워크(서버)**
  - [ ] 페이퍼 2주 무중단 라이브 운영(실피드 상주) — 러너·데몬 패키징 준비됨, 상주 가동은 서버
- **산출물**: `config/fix.cfg`, `execution/{fix,fix_executor,router,store,alpaca_executor}.py`, `ops/runner.py`, `deploy/{Dockerfile,daytrade-live.service,daytrade-live.env}`, 페이퍼/라이브 봇
- **인수기준**: 페이퍼 2주 무중단, 슬리피지 ≤ 0.05 %, e2e < 5 ms(클라우드 5~10ms 허용 명시)
- **의존성**: 브로커 FIX 계정, 인증서(실세션). 코어/봇은 의존성 0(로컬 동작)

### M6 — 모니터링 & 감사 로그 & 운영 안정성  🟢 코어 구현·테스트 완료(인프라 연동은 서버)
- **목표**: §8 감사/§10-5 모니터링.
- **구성요소**: Prometheus exporter, Grafana, Jaeger(트레이싱), Alertmanager/PagerDuty, Kafka+WAL(immutable log).
- **진척(이번 단계)**: 의존성 0 순수 파이썬으로 **메트릭 노출·불변 감사로그·알림 규칙**을 구현 + 9개 테스트 통과. 페이퍼봇에 결선(`--audit`/`--metrics-out`).
  - [x] 메트릭 exporter `monitoring/exporter.py` — Prometheus **text exposition**(Counter/Gauge/Histogram, 라벨, 누적 버킷) + `registry_from_run`(레이턴시·슬리피지·P&L·Sharpe·MDD·주문성공률·서킷브레이커)
  - [x] 불변 감사 로그 `monitoring/audit.py` — **해시 체인 WAL**(append-only JSONL, sha256 체인, 재개/연장) + `verify()` 변조 탐지(누락·재정렬·페이로드 변조)
  - [x] 알림 규칙 `monitoring/alerts.py` — 인프로세스 `AlertEngine`(서킷브레이커·낙폭·레이턴시 p99·주문거절률·피드 정체)
  - [x] 운영 아티팩트 — `config/grafana_dashboard.json`(Import용), `config/alert_rules.yml`(Prometheus/Alertmanager)
  - [x] **메트릭 HTTP `/metrics` 서버** `monitoring/server.py` — stdlib `http.server`(데몬 스레드, `/healthz`), `LiveMetrics` 로 라이브 갱신 반영(Prometheus 스크레이프)
  - [x] **인프로세스 분산 트레이싱** `monitoring/tracing.py` — 파이프라인 구간(features→detection→inference→risk→execution) span, 샘플링, Jaeger JSON export, 구간별 p50/p95/p99 µs 요약. **기본 NoopTracer = 핫패스 무오버헤드**
  - [x] 페이퍼봇 결선 — `--audit`/`--metrics-out`/`--metrics-port`(라이브 노출)/`--trace-out`+`--trace-sample`, 종료 시 알림 평가
  - [x] **상시운영 결합** — `daytrade/ops/LiveRunner` 가 `/metrics`(라이브 갱신)·해시체인 감사로그·알림 평가·일일리포트를 무중단 가동에 결선(`scripts/live_ops.py`)
  - [x] **인프로세스 장애 주입(Chaos-Mesh 경량 대안)** — `daytrade/testing/faults.py`: `FaultInjectingFeed`(끊김 `ConnectionError`·틱 드롭·호가창 손상·지연 스파이크 주입), `FlakyFeedFactory`(초기 N세션 조기 끊김→이후 정상 = **끊김→백오프 재연결→회복** 재현), `FlakyExecutor`(주문 거부·브로커 예외·부분체결 주입). K8s 없이 `LiveRunner` 자동 재연결·감사(`feed_error`/`feed_disconnect`)·실행기 내성을 단위 테스트로 검증(8개 테스트)
  - [ ] Kafka 5년 보관 파이프라인(immutable log → 장기 스토리지), 운영 Jaeger collector 전송, **Chaos-Mesh K8s 레벨 주입**(서버 단계)
- **산출물**: `monitoring/{exporter,audit,alerts,server,tracing}.py`, `ops/runner.py`, `config/{grafana_dashboard.json,alert_rules.yml}`
- **인수기준**: 전 지표 실시간 노출(`/metrics` HTTP + 포맷 검증 완료), 감사 로그 무결성 검증(변조 탐지 테스트 통과), 구간 트레이싱 가시화
- **의존성**: Kafka/Prometheus 인프라(서버). 코어는 의존성 0(로컬 동작)

### M7 — 자동 튜닝 & 주기적 재학습 (재학습 오케스트레이션 + Optuna/스케줄러)  🟢 코어 + 튜닝 + 스케줄러 + KPI 회귀셋 + 런타임 핫스왑 결선 완료
- **목표**: §7 일일 재학습 Blue-Green, §9 Optuna TPE 튜닝.
- **구성요소**: 재학습 오케스트레이터, Optuna(TPE)/random 폴백, 경량 인프로세스 스케줄러, ConfigMap patch.
- **진척(이번 단계)**: TradeStore/감사로그 트리거 → 데이터셋→재학습→워크포워드→ONNX export→**Blue-Green 핫스왑**을 의존성 0(numpy/JSON, onnx 설치 시 ONNX 동반)으로 구현. 워크포워드 **Sharpe 목적함수 + 리스크 제약** 튜닝을 재학습 게이트와 결합하고, Airflow 없이 상주하는 **경량 스케줄러**(일일 재학습 + 5분 튜닝 트리거)로 결선. 전 테스트(213) 통과.
  - [x] **재학습 오케스트레이터** `daytrade/ops/retrain.py`(`RetrainOrchestrator`) + `scripts/retrain.py`
  - [x] 트리거 판정 `evaluate_trigger` — `TradeStore`(체결/자본곡선) 라이브 낙폭·수익률·체결수·force 로 재학습 결정
  - [x] 데이터셋→`train_logreg`→`walk_forward_validate`(OOS balanced acc + 과최적화 갭) **인수 게이트**
  - [x] 버전 아티팩트(`models/model_vN.{json,onnx}` + `current.json` 포인터) + `HotSwapModel.swap()` 승격 + 감사로그(`retrain_trigger`/`retrain_result`/`model_hotswap`)
  - [x] `TradeStore` 리더 `equity_curve`/`fills_count`/`latest_run_id`
  - [x] **(E) Optuna TPE 목적함수/제약(§9) 본격화** — `training/tuning.py`: 기본 목적함수를 **`mean_oos_sharpe`** 로 전환, `RiskConstraints`(OOS 최악 MDD 한도·수익폴드비율 하한)를 패널티로 soft-constraint 반영(`score_summary`). 과최적화로 1~2 폴드에 베팅하는 해 억제
  - [x] **(E) 튜닝↔재학습 게이트 결합** — `RetrainOrchestrator.tune_and_validate(ticks, …)`: 워크포워드 탐색 best 하이퍼파라미터(horizon/up_bps/down_bps/lr/epochs)로 재학습 후 동일 인수 게이트 통과 시 승격. best 시그널 임계(ai/obi/vol)·튜닝 메타를 `current.json` 에 기록
  - [x] **(F) 경량 인프로세스 스케줄러** — `daytrade/ops/scheduler.py`(`Scheduler`): interval/daily 작업, 주입 가능한 시계/sleep, 작업 예외 흡수(상주 지속), 그레이스풀 종료(`request_stop`) + `scripts/scheduler.py`(일일 02:00 UTC 재학습 + 5분 튜닝 트리거, SIGTERM/SIGINT) — **Airflow 없이 상주**
  - [x] **(G) KPI 회귀셋** `daytrade/training/kpi.py`(`compare_regimes`) + `scripts/kpi_regression.py` — 다중 레짐(잔잔/변동/이벤트빈발)에서 baseline vs tuned 워크포워드 **OOS** KPI(평균 수익률·Sharpe·최악 MDD·수익폴드비율) 비교 → 레짐 평균 개선 판정(verdict, CI 게이트용 exit code). 합성 3레짐 실측 예: 평균 Sharpe **+1.98→+4.09**, 최악 MDD 0.042→0.013, 3/3 레짐 개선(PASS)
  - [x] **(H) `current.json` 런타임 결선** `daytrade/ops/registry.py`(`load_current`/`apply_signal_overrides`) + `TradingPipeline.reload_from_current()` + `LiveRunner`(시동·세션 경계마다 버전 감시 → 무중단 핫스왑, `on_reload`/감사 `model_reload`). 핫스왑된 모델 경로 + best 시그널 임계(ai/obi/vol)가 실제 추론/탐지에 적용(`scripts/live_ops.py --model-dir`)
  - [x] **(I) Prometheus 결선** — `LiveMetrics` 에 `daytrade_model_version`/`daytrade_model_reloads_total` 게이지(러너 핫스왑 시 갱신) + `registry_from_kpi_verdict()`(KPI verdict → `daytrade_kpi_*` 게이지, `kpi_regression.py --metrics-out` 로 textfile collector/pushgateway 노출). Grafana 대시보드에 모델버전/핫스왑·KPI(baseline vs tuned)·게이트 판정 패널 추가
  - [x] **(J) 회귀셋 CI 게이트화** — `apps/daytrade-ai/Makefile`(`compile`/`test`/`kpi-gate`/`check`) + `.github/workflows/daytrade-ai-ci.yml`(PR 시 compile+test+KPI 게이트, 개선 실패 시 exit 1 로 자동 차단, 리포트/.prom 아티팩트 업로드)
  - [x] **(K) Alertmanager MLOps 규칙** — `config/alert_rules.yml` `daytrade-mlops` 그룹: `KpiRegression`(verdict PASS 실패), `ModelReloadStorm`(15분 내 핫스왑 ≥3=플래핑), `RetrainStalled`(26h 내 버전 정체=스케줄러 중단), `ModelServingUninitialized`(model_version=0 10분 지속)
  - [x] **(L) 모델 자동 롤백** — `registry.py`(`history.jsonl` 누적 + `rollback_current`/`load_history`) + `RetrainOrchestrator.rollback()` + `LiveRunner` 핫스왑 후 KPI 가드(승격 시 감시 무장 → 윈도 내 낙폭 한도 초과 시 직전 버전 자동 복귀, 감사 `kpi_breach`/`model_rollback`, 루프 방지). `scripts/live_ops.py --rollback`
  - [x] **(M) 롤백 쿨다운/블랙리스트** — `registry.py` 가드 상태(`guard.json`): `model_signature`(라벨+시그널 파라미터 해시)로 롤백된 '나쁜 모델'을 쿨다운 동안 **재승격 금지**(`is_signature_blacklisted` → train_and_validate 게이트, 감사 `promotion_blocked`). `auto_rollback`(롤백+블랙리스트+기록 일원화) + 연속 롤백 한도 초과 시 **재학습 일시중지**(`retrain_paused_until` → orchestrate/tune_and_validate 즉시 반환, 감사 `retrain_paused`)
  - [x] **(N) 통합 E2E 시나리오 테스트** — 스케줄러→재학습(v1,v2 승격)→핫스왑→인위적 낙폭→자동 롤백(v1 복귀)→블랙리스트 재승격 차단→감사 무결(`kpi_breach`/`model_reload`/`promotion_blocked`)→KPI verdict 게이지(`daytrade_kpi_passed=0`) 한 흐름 단일 테스트(`test_rollback_guard_m7.py`)
- **산출물**: `ops/retrain.py`, `ops/scheduler.py`, `ops/registry.py`(+history/rollback), `training/kpi.py`, `scripts/{retrain,scheduler,kpi_regression}.py`, `Makefile`, `.github/workflows/daytrade-ai-ci.yml`, `config/{alert_rules.yml,grafana_dashboard.json}`, 버전 모델 아티팩트
- **인수기준**: 트리거→(튜닝)→재학습→OOS 검증→무중단 핫스왑 재현(테스트 통과), 자동 튜닝 KPI 개선(회귀셋 verdict PASS, CI 게이트)
- **의존성**: M6 메트릭/`TradeStore`(완료), Optuna(미설치 시 random 폴백·테스트 가능), Airflow(분산 스케줄은 선택)

### M8 — 배포 & DR (Terraform/K8s/Helm/Argo/Velero/Chaos)
- **목표**: §10 운영 가이드.
- **구성요소**: Terraform, Docker, K8s(CPU-pin, GPU-device, NVIDIA GPU Operator), Helm, Argo Rollout(Canary/Blue-Green), Velero, Chaos-Mesh.
- **작업**:
  - [ ] 인프라 IaC(Terraform), 컨테이너화(CPU pinning, GPU device plugin)
  - [ ] Helm chart + Argo Rollout(카나리), GitHub Actions CI/CD
  - [ ] Velero S3 스냅샷(hourly) + DB 백업(pgBackRest)
  - [ ] Chaos-Mesh(네트워크 지연·pod kill) SLA 검증
- **산출물**: Terraform/Helm/Argo 매니페스트
- **인수기준**: Zero-downtime 롤아웃, Chaos 시 SLA 유지
- **의존성**: K8s 클러스터

### M9 — 하드웨어·네트워크 초저지연 (Solarflare/DPDK/FPGA/PTP/Co-Lo)
- **목표**: §4 물리 인프라.
- **구성요소**: Solarflare Onload + DPDK, PTP(IEEE 1588v2)+Chrony, 40GbE Mellanox+DCB, (선택)Xilinx Alveo U280 FPGA, Co-Location(NY2/Chicago/Seoul).
- **작업**:
  - [ ] NIC DPDK 튜닝(rx-mode=0, no-interrupt, RSS), PTP 동기화(±100ns)
  - [ ] (선택)FPGA 오더북 정규화 오프로드(0.2µs)
  - [ ] Kafka/Pulsar 백업 스트리밍(0-lag)
  - [ ] 코로케이션/Direct Connect 회선
- **산출물**: 인프라 구성서, 레이턴시 실측
- **인수기준**: e2e 2~5 ms 실측
- **의존성**: 🟥 물리 장비·코로케이션 계약(서버 최고사양 구축 시 진행)

### M10 — 규제·보안·실거래 승인 (코드보다 선행하는 게이트)
- **목표**: §8/§12 법·보안.
- **작업**:
  - [ ] 알고리즘 매매 신고(KRX/SEC/NASDAQ), 실시간 보고(<15분) 체계
  - [ ] 거래소 HFT 프로그램 사전 인증·시뮬 테스트
  - [ ] TLS 1.3 + mTLS, 주문 서명 HSM(AWS CloudHSM), 키 Vault 보관
  - [ ] KYC, 데이터 프라이버시(GDPR/PIPA) — 뉴스/SNS 수집 익명화
- **산출물**: 규제 점검표, 보안 구성
- **인수기준**: 승인·인증 완료, 보안 감사 통과
- **의존성**: 🟥 법무/거래소(외부)

### M11 — 실전 전환 게이트
- **목표**: §7/§14 단계적 실거래.
- **작업**:
  - [ ] 1M~10M ticks 시뮬 → Sharpe > 2, 슬리피지 ≤ 0.05 %, e2e < 5 ms 검증
  - [ ] 페이퍼 트레이딩 2주
  - [ ] 소액 실거래 1개월(한도 점증, 킬스위치 검증)
- **산출물**: 성과·리스크 리포트
- **인수기준**: §1 전 지표 + Sharpe/슬리피지 충족 후에만 자본 확대
- **의존성**: M1~M10 완료

---

## 5. 디렉터리 목표 구조 (확장 후)

```
apps/daytrade-ai/
  daytrade/            # Python: 전략·백테스트·모니터링·튜닝 (현재 + 확장)
  cpp/                 # C++: ingest(DPDK) / feature(Eigen) / detection / inference(TensorRT)
    ingest/  feature/  detection/  inference/  bindings/(pybind11)
  schemas/             # FlatBuffers/Cap'n Proto (.fbs) — C++/Python 공유
  models/              # 학습 산출물(onnx, trt plan), 모델 카드
  training/            # PyTorch/RLlib 학습·라벨링·walk-forward
  airflow/dags/        # auto_tuner, retrain
  deploy/              # Terraform, Helm, Argo, Dockerfiles
  monitoring/          # Grafana 대시보드, alert 규칙, exporter(Go)
  fix/                 # QuickFIX 설정, router
  docs/                # MASTER_PLAN.md(본 문서), 설계 매핑, 런북
  tests/               # 단위/통합/골든/벤치
  scripts/             # 등록·운영 스크립트
```

---

## 6. 진행 방식(틈틈이 작업 규칙)

1. 한 번에 **하나의 마일스톤 안의 한 작업(체크박스)** 을 집어 완료→테스트→문서 갱신.
2. C++ 작업은 항상 **Python 레퍼런스와의 골든 테스트**로 정확성 보증.
3. 각 작업 종료 시: 본 문서 체크박스 + 추적 매트릭스 상태 갱신.
4. 실거래 관련(M5 실주문/M10/M11)은 **안전 게이트·승인 확인 후에만** 진행.
5. 외부 의존(🟥: 하드웨어/코로케이션/규제)은 가용해질 때 진행, 그 전까지 폴백 모드로 개발.

---

## 부록 A — 참고 오픈소스(설계서 §13)

DPDK · Solarflare Onload · FIX FAST · QuickFIX/N · TensorRT · Optuna · Ray RLlib · KDB+/q ·
Backtrader · FinRL(Gym-Trading) · Velero · Chaos-Mesh · mediasoup · coturn.

## 부록 B — 추천 착수 순서

**M1 → M2 → M3** 가 ROI 최상(실데이터 검증 → 학습모델 → C++ 고속화).
M3는 본 프로젝트의 기술적 심장부이므로 충분한 골든 테스트와 함께 진행한다.
