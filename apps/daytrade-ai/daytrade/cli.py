"""CLI 진입점 — 합성 시뮬레이션/리플레이 백테스트 실행.

예:
    python -m daytrade.cli sim --symbol AAPL --ticks 5000
    python -m daytrade.cli sim --no-ai --obi-threshold 5e5
    python -m daytrade.cli replay --csv ticks.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backtest.runner import run_backtest
from .config import SignalConfig, TradingConfig, TradingMode
from .feed.simulated import SimulatedFeed
from .feed.replay import CsvReplayFeed
from .feed.binance import BinanceFeed
from .feed.recorder import write_ticks_csv


def _resolve_safe_output_path(raw_path: str) -> Path:
    value = str(raw_path or "").strip()
    if not value:
        raise ValueError("출력 경로가 비어 있습니다.")
    if "\x00" in value:
        raise ValueError("출력 경로에 허용되지 않는 문자가 포함되어 있습니다.")

    input_path = Path(value).expanduser()
    candidate = input_path.resolve() if input_path.is_absolute() else (Path.cwd() / input_path).resolve()
    base = Path.cwd().resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("출력 경로는 현재 작업 디렉터리 내부여야 합니다.")
    return candidate


def _build_config(args: argparse.Namespace) -> TradingConfig:
    signal = SignalConfig(
        depth=args.depth,
        obi_threshold=args.obi_threshold,
        volume_spike_ratio=args.vol_spike,
        ai_buy_threshold=args.ai_threshold,
        ai_sell_threshold=args.ai_threshold,
        use_ai=not args.no_ai,
    )
    return TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=(args.symbol,),
        starting_cash=args.cash,
        signal=signal,
        seed=args.seed,
    )


def load_replay_feed(path: str):
    """확장자 디스패치: `.dts` → 바이너리 틱 스토어 피드, 그 외 → CSV 리플레이.

    대용량 적재 시 CSV 텍스트 파싱을 건너뛰는 `TickStoreFeed` 로 가속한다(M1 storage 결선).
    """
    if str(path).lower().endswith(".dts"):
        from .storage import TickStoreFeed
        return TickStoreFeed(path)
    return CsvReplayFeed(path)


def _train_feed(args: argparse.Namespace):
    if getattr(args, "sim", False):
        return SimulatedFeed(
            symbol=args.symbol, n_ticks=args.ticks, depth=args.depth, seed=args.seed
        )
    return load_replay_feed(args.csv)


def _run_tune(args: argparse.Namespace) -> int:
    from .config import RiskConfig, SignalConfig, TradingConfig, TradingMode
    from .training import run_tuning

    feed = _train_feed(args)
    ticks = list(feed.ticks())
    if len(ticks) < 100:
        print("[ERR] 탐색에는 더 많은 틱이 필요합니다.")
        return 2

    base_config = TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=(args.symbol,),
        starting_cash=args.cash,
        signal=SignalConfig(depth=args.depth, use_ai=True),
        # 결정적 OOS 평가를 위해 벽시계 레이턴시 서킷브레이커 비활성.
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=args.seed,
    )

    space = None
    if args.calibrate_obi:
        import numpy as np

        from .feed.memory import ListFeed
        from .features.engine import FeatureEngine
        from .training import ParamSpec, default_search_space

        fe = FeatureEngine(depth=args.depth)
        abs_obi = np.abs([fe.update(t).obi for t in ListFeed(ticks).ticks()])
        lo = max(1e-6, float(np.percentile(abs_obi, 25)))
        hi = max(lo * 2, float(np.percentile(abs_obi, 95)))
        space = default_search_space()
        space["obi_threshold"] = ParamSpec("loguniform", lo, hi)
        print(f"[calibrate] obi_threshold range -> [{lo:.4g}, {hi:.4g}]")

    result = run_tuning(
        ticks, base_config,
        space=space,
        n_trials=args.n_trials, metric=args.metric,
        n_splits=args.n_splits, scheme=args.scheme,
        seed=args.seed, backend=args.backend,
    )

    if args.out:
        try:
            out_path = _resolve_safe_output_path(args.out)
        except ValueError as exc:
            print(f"[ERR] invalid --out: {exc}")
            return 2
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"metric": result.metric, "best_value": result.best_value,
                        "best_params": result.best_params, "backend": result.backend},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[OK] best 파라미터 저장 -> {out_path}")

    if args.json:
        print(json.dumps({"backend": result.backend, "metric": result.metric,
                          "best_value": result.best_value, "best_params": result.best_params,
                          "trials": result.trials}, ensure_ascii=False, indent=2))
    else:
        print("=" * 64)
        print(" daytrade-ai hyperparameter tuning")
        print("=" * 64)
        for line in result.summary_lines():
            print(" " + line)
        print("=" * 64)
    return 0


def _run_events(args: argparse.Namespace) -> int:
    from .feed.event_capture import EventCaptureConfig, iter_event_ticks

    if args.live:
        source = BinanceFeed(symbol=args.symbol, depth=args.depth, max_ticks=args.ticks).ticks()
    else:
        source = load_replay_feed(args.csv).ticks()

    cfg = EventCaptureConfig(
        ret_bps=args.ret_bps, window=args.window, pre=args.pre, post=args.post,
        vol_spike=args.vol_spike, obi_z=args.obi_z, depth=args.depth, max_events=args.max_events,
    )
    try:
        n = write_ticks_csv(args.out, iter_event_ticks(source, cfg), depth=args.depth)
    except ModuleNotFoundError:
        print("[ERR] 라이브 캡처에는 'websockets' 패키지가 필요합니다: pip install websockets")
        return 2
    print(f"[OK] {n} event-window ticks -> {args.out}  "
          f"(replay: python -m daytrade.cli replay --csv {args.out})")
    if n == 0:
        print("  (이벤트 없음 — 임계를 낮추거나(--ret-bps/--vol-spike/--obi-z) 더 변동성 큰 구간을 캡처)")
    return 0


def _run_rl(args: argparse.Namespace) -> int:
    import numpy as np

    from .rl import (
        ContinuousPPOAgent,
        LinearPolicyAgent,
        PPOAgent,
        RLConfig,
        TradingEnv,
        run_episode,
        train,
        train_ppo,
        train_ppo_continuous,
    )

    feed = _train_feed(args)
    ticks = list(feed.ticks())
    if len(ticks) < 50:
        print("[ERR] RL 학습에는 더 많은 틱이 필요합니다(>=50).")
        return 2

    action_mode = "continuous" if args.algo == "cppo" else "discrete"
    env = TradingEnv(
        ticks,
        RLConfig(depth=args.depth, cost_bps=args.cost_bps, reward_scale=args.reward_scale,
                 action_mode=action_mode),
    )

    if args.algo == "cppo":
        agent = ContinuousPPOAgent(seed=args.seed, gamma=args.gamma)
        _, _, _, base = run_episode(env, agent, greedy=False, seed=args.seed)
        history = train_ppo_continuous(env, agent, iterations=args.iterations, seed=args.seed)
        _, actions, _, trained = run_episode(env, agent, greedy=True, seed=args.seed)
    elif args.algo == "ppo":
        agent = PPOAgent(seed=args.seed, gamma=args.gamma)
        _, _, _, base = run_episode(env, agent, greedy=False, seed=args.seed)
        history = train_ppo(env, agent, iterations=args.iterations, seed=args.seed)
        _, actions, _, trained = run_episode(env, agent, greedy=True, seed=args.seed)
    else:
        agent = LinearPolicyAgent(seed=args.seed, lr=args.lr, gamma=args.gamma)
        _, _, _, base = run_episode(env, agent, greedy=False, seed=args.seed)
        history = train(env, agent, episodes=args.episodes, seed=args.seed)
        _, actions, _, trained = run_episode(env, agent, greedy=True, seed=args.seed)

    # 그리디 포지션 분포(롱/플랫/숏 비중) — 정책이 한쪽으로 붕괴했는지 진단.
    if args.algo == "cppo":
        pos = np.array([float(a) for a in actions])
        dist = {"short": int(np.sum(pos < -0.05)), "flat": int(np.sum(np.abs(pos) <= 0.05)),
                "long": int(np.sum(pos > 0.05)), "mean_abs_size": round(float(np.mean(np.abs(pos))), 4)}
    else:
        pos = np.array([(-1, 0, 1)[a] for a in actions])
        dist = {"short": int(np.sum(pos < 0)), "flat": int(np.sum(pos == 0)), "long": int(np.sum(pos > 0))}

    if args.onnx and args.algo == "cppo":
        from .training.onnx_export import export_continuous_policy_to_onnx

        try:
            onnx_out_path = _resolve_safe_output_path(args.onnx)
        except ValueError as exc:
            print(f"[ERR] invalid --onnx: {exc}")
            return 2
        onnx_out_path.parent.mkdir(parents=True, exist_ok=True)

        export_continuous_policy_to_onnx(
            agent.W, agent.b, env._mean, env._std, str(onnx_out_path)
        )
        print(f"[OK] 연속 RL 정책 ONNX export -> {onnx_out_path}  (추론: OnnxPolicyModel)")

    if args.out:
        if args.algo == "cppo":
            payload_w = {"W": agent.W.tolist(), "b": float(agent.b), "log_std": float(agent.log_std)}
        else:
            payload_w = {"W": agent.W.tolist(), "b": agent.b.tolist()}
        try:
            out_path = _resolve_safe_output_path(args.out)
        except ValueError as exc:
            print(f"[ERR] invalid --out: {exc}")
            return 2
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({**payload_w, "cost_bps": args.cost_bps, "reward_scale": args.reward_scale},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[OK] 정책 가중치 저장 -> {out_path}")

    iter_based = args.algo in ("ppo", "cppo")
    payload = {
        "algo": args.algo,
        "ticks": len(ticks),
        "iters" if iter_based else "episodes": args.iterations if iter_based else args.episodes,
        "baseline_reward": round(base, 4),
        "trained_greedy_reward": round(trained, 4),
        "final10_mean": round(float(np.mean(history[-10:])), 4) if history else 0.0,
        "greedy_position_dist": dist,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=" * 64)
        print(f" daytrade-ai RL (TradingEnv + {args.algo.upper()})")
        print("=" * 64)
        for k, v in payload.items():
            print(f"  {k:24s}: {v}")
        print("=" * 64)
    return 0


def _run_walkforward(args: argparse.Namespace) -> int:
    from .config import RiskConfig, SignalConfig, TradingConfig, TradingMode
    from .training import walk_forward_backtest, walk_forward_validate
    from .training.dataset import build_dataset

    feed = _train_feed(args)
    ticks = list(feed.ticks())
    if len(ticks) <= args.horizon:
        print("[ERR] 틱이 너무 적습니다(틱 > horizon 필요).")
        return 2

    signal = SignalConfig(
        depth=args.depth,
        obi_threshold=args.obi_threshold,
        volume_spike_ratio=args.vol_spike,
        ai_buy_threshold=args.ai_threshold,
        ai_sell_threshold=args.ai_threshold,
    )
    config = TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=(args.symbol,),
        starting_cash=args.cash,
        signal=signal,
        # 워크포워드 OOS 백테스트의 결정성을 위해 벽시계 레이턴시 서킷브레이커 비활성.
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=args.seed,
    )

    if args.mode == "validate":
        from .feed.memory import ListFeed

        bundle = build_dataset(ListFeed(ticks), signal, horizon=args.horizon, up_bps=args.up_bps, down_bps=args.down_bps)
        report = walk_forward_validate(bundle, n_splits=args.n_splits, scheme=args.scheme, epochs=args.epochs, seed=args.seed)
    else:
        report = walk_forward_backtest(
            ticks, config, horizon=args.horizon, up_bps=args.up_bps, down_bps=args.down_bps,
            n_splits=args.n_splits, scheme=args.scheme, epochs=args.epochs, seed=args.seed,
        )

    if args.json:
        print(json.dumps({"folds": report.folds, "summary": report.summary}, ensure_ascii=False, indent=2))
    else:
        print("=" * 64)
        print(f" daytrade-ai walk-forward ({args.mode})")
        print("=" * 64)
        for line in report.summary_lines():
            print(" " + line)
        print("=" * 64)
    return 0


def _run_train(args: argparse.Namespace) -> int:
    from .config import SignalConfig
    from .training import build_dataset, train_logreg

    signal = SignalConfig(depth=args.depth)
    feed = _train_feed(args)
    bundle = build_dataset(
        feed, signal, horizon=args.horizon, up_bps=args.up_bps, down_bps=args.down_bps
    )
    if len(bundle) == 0:
        print("[ERR] 학습 표본이 비었습니다(틱/horizon 확인).")
        return 2

    if args.backend == "numpy":
        model, metrics = train_logreg(
            bundle.X, bundle.y_buy, bundle.y_sell,
            feature_names=bundle.feature_names, horizon=args.horizon,
            epochs=args.epochs, lr=args.lr, seed=args.seed,
        )
        model.save_json(args.out)
        print(f"[OK] numpy 모델 저장 -> {args.out}  (samples={len(bundle)})")
        if args.onnx:
            from .training.onnx_export import export_numpy_logreg_to_onnx

            try:
                export_numpy_logreg_to_onnx(model, args.onnx)
                print(f"[OK] ONNX export -> {args.onnx}")
            except ModuleNotFoundError as exc:
                print(f"[WARN] ONNX export 생략: {exc}")
    else:
        try:
            from .training.torch_trainer import build_sequence_dataset, train_sequence_model
            from .training.onnx_export import export_torch_sequence_to_onnx
        except ModuleNotFoundError:
            print("[ERR] torch 백엔드에는 'torch' 패키지가 필요합니다: pip install torch")
            return 2
        seqs, Y = build_sequence_dataset(bundle, args.seq_len)
        if seqs.shape[0] == 0:
            print("[ERR] 시퀀스 표본이 비었습니다(seq-len/틱 확인).")
            return 2
        module, metrics = train_sequence_model(
            seqs, Y, kind=args.kind, hidden=args.hidden, epochs=args.epochs, lr=args.lr, seed=args.seed
        )
        export_torch_sequence_to_onnx(
            module, args.out, seq_len=args.seq_len, n_features=seqs.shape[2]
        )
        print(f"[OK] torch({args.kind}) ONNX export -> {args.out}  (seq_len={args.seq_len})")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daytrade", description="AI 주식 단타 자동매매 시뮬레이터")
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--symbol", default="AAPL")
    common.add_argument("--cash", type=float, default=1_000_000.0)
    common.add_argument("--depth", type=int, default=10)
    common.add_argument("--obi-threshold", dest="obi_threshold", type=float, default=1.0e6)
    common.add_argument("--vol-spike", dest="vol_spike", type=float, default=2.0)
    common.add_argument("--ai-threshold", dest="ai_threshold", type=float, default=0.90)
    common.add_argument("--no-ai", action="store_true", help="AI 추론 비활성(규칙만)")
    common.add_argument("--model", help="추론 모델 경로(*.json=numpy logreg, *.onnx=확률모델/연속RL정책 자동판별)")
    common.add_argument("--seed", type=int, default=42)
    common.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    common.add_argument("--report-json", dest="report_json", help="고급 분석 리포트 JSON 저장 경로")
    common.add_argument("--report-html", dest="report_html", help="equity 스파크라인 HTML 리포트 저장 경로")

    p_sim = sub.add_parser("sim", parents=[common], help="합성 시뮬레이션 백테스트")
    p_sim.add_argument("--ticks", type=int, default=5_000)
    p_sim.add_argument("--start-price", dest="start_price", type=float, default=100.0)
    p_sim.add_argument("--event-prob", dest="event_prob", type=float, default=0.01)

    p_rep = sub.add_parser("replay", parents=[common], help="CSV/틱스토어 리플레이 백테스트")
    p_rep.add_argument("--csv", required=True, help="리플레이 입력(.csv 또는 .dts 틱스토어)")

    p_record = sub.add_parser("record", help="Binance 실시간 피드를 CSV(CsvReplayFeed 포맷)로 기록")
    p_record.add_argument("--symbol", default="BTCUSDT")
    p_record.add_argument("--depth", type=int, default=10)
    p_record.add_argument("--ticks", type=int, default=1_000, help="기록할 틱 수")
    p_record.add_argument("--out", required=True, help="저장 CSV 경로")

    p_wf = sub.add_parser("walkforward", help="워크포워드 OOS 검증/백테스트 (M2 후속)")
    wsrc = p_wf.add_mutually_exclusive_group(required=True)
    wsrc.add_argument("--csv", help="리플레이 입력(.csv 또는 .dts 틱스토어)")
    wsrc.add_argument("--sim", action="store_true", help="합성 시뮬레이션 입력")
    p_wf.add_argument("--mode", choices=["backtest", "validate"], default="backtest")
    p_wf.add_argument("--symbol", default="AAPL")
    p_wf.add_argument("--depth", type=int, default=10)
    p_wf.add_argument("--ticks", type=int, default=20_000, help="--sim 시 생성 틱 수")
    p_wf.add_argument("--cash", type=float, default=1_000_000.0)
    p_wf.add_argument("--seed", type=int, default=42)
    p_wf.add_argument("--n-splits", dest="n_splits", type=int, default=5)
    p_wf.add_argument("--scheme", choices=["rolling", "anchored"], default="rolling")
    p_wf.add_argument("--horizon", type=int, default=20)
    p_wf.add_argument("--up-bps", dest="up_bps", type=float, default=5.0)
    p_wf.add_argument("--down-bps", dest="down_bps", type=float, default=5.0)
    p_wf.add_argument("--ai-threshold", dest="ai_threshold", type=float, default=0.55)
    p_wf.add_argument("--obi-threshold", dest="obi_threshold", type=float, default=1.0e6,
                      help="자산 스케일에 맞춰 조정(암호화폐 오더북은 수~수십 수준)")
    p_wf.add_argument("--vol-spike", dest="vol_spike", type=float, default=2.0)
    p_wf.add_argument("--epochs", type=int, default=200)
    p_wf.add_argument("--json", action="store_true")

    p_tune = sub.add_parser("tune", help="워크포워드 점수를 목적함수로 하이퍼파라미터 탐색 (M2/§9)")
    tsrc = p_tune.add_mutually_exclusive_group(required=True)
    tsrc.add_argument("--csv", help="리플레이 입력(.csv 또는 .dts 틱스토어)")
    tsrc.add_argument("--sim", action="store_true", help="합성 시뮬레이션 입력")
    p_tune.add_argument("--symbol", default="AAPL")
    p_tune.add_argument("--depth", type=int, default=10)
    p_tune.add_argument("--ticks", type=int, default=20_000, help="--sim 시 생성 틱 수")
    p_tune.add_argument("--cash", type=float, default=1_000_000.0)
    p_tune.add_argument("--seed", type=int, default=42)
    p_tune.add_argument("--n-trials", dest="n_trials", type=int, default=20)
    p_tune.add_argument("--n-splits", dest="n_splits", type=int, default=3)
    p_tune.add_argument("--scheme", choices=["rolling", "anchored"], default="rolling")
    p_tune.add_argument("--metric", default="mean_oos_return_pct",
                        help="목적함수(예: mean_oos_return_pct, mean_oos_sharpe)")
    p_tune.add_argument("--backend", choices=["auto", "optuna", "random"], default="auto")
    p_tune.add_argument("--calibrate-obi", dest="calibrate_obi", action="store_true",
                        help="obi_threshold 탐색범위를 데이터 |OBI| 분포(p25~p95)로 자동 보정(자산 스케일 무관)")
    p_tune.add_argument("--out", help="best 파라미터 JSON 저장 경로")
    p_tune.add_argument("--json", action="store_true")

    p_train = sub.add_parser("train", help="라벨링→학습→ONNX export (M2)")
    src = p_train.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="리플레이 입력(.csv 또는 .dts 틱스토어)")
    src.add_argument("--sim", action="store_true", help="합성 시뮬레이션 입력")
    p_train.add_argument("--symbol", default="AAPL")
    p_train.add_argument("--depth", type=int, default=10)
    p_train.add_argument("--ticks", type=int, default=20_000, help="--sim 시 생성 틱 수")
    p_train.add_argument("--seed", type=int, default=42)
    p_train.add_argument("--backend", choices=["numpy", "torch"], default="numpy")
    p_train.add_argument("--out", required=True, help="numpy=*.json, torch=*.onnx 저장 경로")
    p_train.add_argument("--onnx", help="numpy 백엔드에서 ONNX 도 함께 export 할 경로")
    p_train.add_argument("--horizon", type=int, default=20, help="예측 지평(틱)")
    p_train.add_argument("--up-bps", dest="up_bps", type=float, default=5.0)
    p_train.add_argument("--down-bps", dest="down_bps", type=float, default=5.0)
    p_train.add_argument("--epochs", type=int, default=300)
    p_train.add_argument("--lr", type=float, default=0.1)
    # torch 전용
    p_train.add_argument("--seq-len", dest="seq_len", type=int, default=32)
    p_train.add_argument("--kind", choices=["lstm", "transformer"], default="lstm")
    p_train.add_argument("--hidden", type=int, default=32)

    p_ev = sub.add_parser("events", help="급변 이벤트 타게팅 캡처(변동성/거래량/OBI 트리거 구간만 기록)")
    esrc = p_ev.add_mutually_exclusive_group(required=True)
    esrc.add_argument("--csv", help="기존 CSV 에서 이벤트 윈도만 추출")
    esrc.add_argument("--live", action="store_true", help="Binance 라이브 피드를 스캔하며 이벤트만 기록")
    p_ev.add_argument("--symbol", default="BTCUSDT")
    p_ev.add_argument("--depth", type=int, default=10)
    p_ev.add_argument("--ticks", type=int, default=20_000, help="--live 시 스캔할 최대 소스 틱 수")
    p_ev.add_argument("--out", required=True, help="저장 CSV 경로")
    p_ev.add_argument("--ret-bps", dest="ret_bps", type=float, default=5.0, help="|윈도 수익률| 임계(bps). 0=비활성")
    p_ev.add_argument("--window", type=int, default=20, help="수익률 측정 윈도(틱)")
    p_ev.add_argument("--pre", type=int, default=10, help="이벤트 전 프리롤(틱)")
    p_ev.add_argument("--post", type=int, default=30, help="이벤트 후 포스트롤(틱)")
    p_ev.add_argument("--vol-spike", dest="vol_spike", type=float, default=0.0, help="volume_spike 임계(0=비활성)")
    p_ev.add_argument("--obi-z", dest="obi_z", type=float, default=0.0, help="|obi_norm| 임계(0=비활성)")
    p_ev.add_argument("--max-events", dest="max_events", type=int, default=0, help="최대 이벤트 수(0=무제한)")

    p_rl = sub.add_parser("rl", help="강화학습 — TradingEnv + REINFORCE/PPO (M2 후속)")
    rsrc = p_rl.add_mutually_exclusive_group(required=True)
    rsrc.add_argument("--csv", help="리플레이 입력(.csv 또는 .dts 틱스토어)")
    rsrc.add_argument("--sim", action="store_true", help="합성 시뮬레이션 입력")
    p_rl.add_argument("--symbol", default="AAPL")
    p_rl.add_argument("--depth", type=int, default=10)
    p_rl.add_argument("--ticks", type=int, default=5_000, help="--sim 시 생성 틱 수")
    p_rl.add_argument("--seed", type=int, default=0)
    p_rl.add_argument("--algo", choices=["ppo", "cppo", "reinforce"], default="ppo",
                      help="ppo(이산 actor-critic) | cppo(연속 포지션 사이즈) | reinforce(베이스라인)")
    p_rl.add_argument("--episodes", type=int, default=200, help="reinforce 에피소드 수")
    p_rl.add_argument("--iterations", type=int, default=40, help="ppo/cppo 반복(iteration) 수")
    p_rl.add_argument("--lr", type=float, default=0.05, help="reinforce 학습률")
    p_rl.add_argument("--gamma", type=float, default=0.99)
    p_rl.add_argument("--onnx", help="cppo 정책을 ONNX 로 export 할 경로(OnnxPolicyModel 로딩)")
    p_rl.add_argument("--cost-bps", dest="cost_bps", type=float, default=1.0,
                      help="포지션 전환당 비용(bps). 잦은 뒤집기 억제")
    p_rl.add_argument("--reward-scale", dest="reward_scale", type=float, default=1e4,
                      help="보상 스케일(수익률이 작아 학습 안정화용)")
    p_rl.add_argument("--out", help="학습된 정책 가중치 JSON 저장 경로")
    p_rl.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "events":
        return _run_events(args)

    if args.cmd == "rl":
        return _run_rl(args)

    if args.cmd == "tune":
        return _run_tune(args)

    if args.cmd == "walkforward":
        return _run_walkforward(args)

    if args.cmd == "train":
        return _run_train(args)

    if args.cmd == "record":
        feed = BinanceFeed(symbol=args.symbol, depth=args.depth, max_ticks=args.ticks)
        try:
            n = write_ticks_csv(args.out, feed.ticks(), depth=args.depth)
        except ModuleNotFoundError:
            print("[ERR] 라이브 기록에는 'websockets' 패키지가 필요합니다: pip install websockets")
            return 2
        print(f"[OK] {n} ticks recorded -> {args.out}  (replay: python -m daytrade.cli replay --csv {args.out})")
        return 0

    config = _build_config(args)

    if args.cmd == "sim":
        feed = SimulatedFeed(
            symbol=args.symbol,
            n_ticks=args.ticks,
            start_price=args.start_price,
            depth=args.depth,
            seed=args.seed,
            event_prob=args.event_prob,
        )
    else:
        feed = load_replay_feed(args.csv)

    report = run_backtest(config, feed, model_path=getattr(args, "model", None))

    if getattr(args, "report_json", None):
        from .backtest.report import report_to_json

        report_to_json(report.metrics, args.report_json)
        print(f"[OK] 분석 리포트(JSON) -> {args.report_json}")
    if getattr(args, "report_html", None):
        from .backtest.report import report_to_html

        report_to_html(report.metrics, args.report_html, title=f"daytrade-ai {args.symbol} backtest")
        print(f"[OK] 분석 리포트(HTML) -> {args.report_html}")

    if args.json:
        print(json.dumps(report.metrics.as_dict(), ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(" daytrade-ai backtest report")
        print("=" * 60)
        for line in report.summary_lines():
            print(" " + line)
        print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
