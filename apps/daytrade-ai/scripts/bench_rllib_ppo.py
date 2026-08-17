"""RLlib 분산 PPO 처리량/수렴 실측 — 서버(ray[rllib] 설치) 실행용.

ray[rllib] 가 설치돼 있으면 RLlib PPO 로 학습하며 **처리량(env steps/sec)** 과
**수렴(episode_return_mean 곡선)** 을 측정한다. 미설치 시 동일 지표 정의로 단일 프로세스
numpy PPO 벤치(`daytrade.rl.benchmark_ppo`)로 폴백하므로, 개발 PC 에서도 바로 돌아간다.

사용:
    # 서버(ray 설치): RLlib 분산 PPO 실측
    python scripts/bench_rllib_ppo.py --csv data/sol_events.csv --iterations 20 --num-env-runners 4

    # 로컬(ray 미설치): numpy PPO 폴백
    python scripts/bench_rllib_ppo.py --sim --ticks 4000 --algo cppo --iterations 30
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 패키지 루트(apps/daytrade-ai)를 import 경로에 추가 — `python scripts/...` 직접 실행 지원.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_ticks(args) -> list:
    from daytrade.feed.replay import CsvReplayFeed
    from daytrade.feed.simulated import SimulatedFeed

    if args.sim:
        return list(SimulatedFeed(symbol=args.symbol, n_ticks=args.ticks, seed=args.seed).ticks())
    return list(CsvReplayFeed(args.csv).ticks())


def _run_local(args, ticks) -> dict:
    from daytrade.rl import ContinuousPPOAgent, PPOAgent, RLConfig, TradingEnv, benchmark_ppo

    mode = "continuous" if args.algo == "cppo" else "discrete"
    env = TradingEnv(ticks, RLConfig(depth=args.depth, cost_bps=args.cost_bps,
                                     reward_scale=args.reward_scale, action_mode=mode))
    agent = ContinuousPPOAgent(seed=args.seed) if args.algo == "cppo" else PPOAgent(seed=args.seed)
    return benchmark_ppo(agent, env, iterations=args.iterations, seed=args.seed)


def _run_rllib(args, ticks) -> dict:
    import ray  # type: ignore
    from ray.rllib.algorithms.ppo import PPOConfig  # type: ignore
    from ray.tune.registry import register_env  # type: ignore

    from daytrade.rl import RLConfig
    from daytrade.rl.gym_env import make_gym_trading_env

    mode = "continuous" if args.algo == "cppo" else "discrete"
    cfg = RLConfig(depth=args.depth, cost_bps=args.cost_bps,
                   reward_scale=args.reward_scale, action_mode=mode)
    register_env("daytrade_env", lambda ec: make_gym_trading_env(ticks, cfg))

    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, include_dashboard=False)
    builder = (
        PPOConfig().environment("daytrade_env")
        .env_runners(num_env_runners=args.num_env_runners)
        .training(train_batch_size=args.train_batch_size)
    )
    # ray>=2.4x: build() → build_algo() 로 이름 변경(구버전 호환 폴백).
    algo = builder.build_algo() if hasattr(builder, "build_algo") else builder.build()

    reward_curve: list[float] = []
    t0 = time.perf_counter()
    last_steps = 0
    for _ in range(args.iterations):
        res = algo.train()
        last_steps = int(res.get("num_env_steps_sampled_lifetime", last_steps))
        runners = res.get("env_runners", {}) or {}
        reward_curve.append(float(runners.get("episode_return_mean", float("nan"))))
    wall = time.perf_counter() - t0
    algo.stop()
    ray.shutdown()

    tail = [r for r in reward_curve[-5:] if r == r] or [0.0]  # NaN 제외
    return {
        "backend": "rllib-ppo",
        "iterations": args.iterations,
        "num_env_runners": args.num_env_runners,
        "total_steps": last_steps,
        "wall_sec": round(wall, 4),
        "steps_per_sec": round(last_steps / wall, 1) if wall > 0 else 0.0,
        "reward_curve": [round(r, 4) if r == r else None for r in reward_curve],
        "final_mean": round(sum(tail) / len(tail), 4),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RLlib/numpy PPO 처리량·수렴 측정")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--sim", action="store_true")
    p.add_argument("--symbol", default="SOLUSDT")
    p.add_argument("--ticks", type=int, default=4000)
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--algo", choices=["ppo", "cppo"], default="ppo")
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--num-env-runners", dest="num_env_runners", type=int, default=2)
    p.add_argument("--train-batch-size", dest="train_batch_size", type=int, default=4000)
    p.add_argument("--cost-bps", dest="cost_bps", type=float, default=1.0)
    p.add_argument("--reward-scale", dest="reward_scale", type=float, default=1e4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--force-local", action="store_true", help="ray 설치돼 있어도 numpy 폴백 사용")
    args = p.parse_args(argv)

    ticks = _load_ticks(args)

    import importlib.util
    use_rllib = (not args.force_local) and importlib.util.find_spec("ray") is not None
    if use_rllib:
        try:
            result = _run_rllib(args, ticks)
        except Exception as exc:  # 서버 환경/버전 이슈 시 폴백 + 사유 기록
            print(f"[WARN] RLlib 경로 실패({exc!r}) → numpy 폴백")
            result = _run_local(args, ticks)
    else:
        if not args.force_local:
            print("[INFO] ray 미설치 → numpy PPO 폴백(서버에서 ray[rllib] 설치 시 분산 실측)")
        result = _run_local(args, ticks)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
