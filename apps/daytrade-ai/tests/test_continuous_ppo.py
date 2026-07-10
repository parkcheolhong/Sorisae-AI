"""연속 행동(포지션 사이즈) PPO + ONNX export → M4 추론 연결 테스트.

검증:
  - 연속 TradingEnv: action 클립([-1,1]), 보상 정의, 연속 포지션.
  - ContinuousPPOAgent: act 범위·결정성·비퇴화.
  - ONNX export 라운드트립(onnx/onnxruntime 설치 시): numpy 정책과 1e-5 이내 일치.
  - OnnxPolicyModel: 파이프라인 추론 인터페이스 연결(prob_buy/prob_sell 유효).
"""
from __future__ import annotations

import numpy as np
import pytest

from daytrade.feed.simulated import SimulatedFeed
from daytrade.rl import ContinuousPPOAgent, RLConfig, TradingEnv, run_episode, train_ppo_continuous


def _ticks(n=600, seed=4):
    return list(SimulatedFeed(symbol="CPPO", n_ticks=n, seed=seed).ticks())


def _env():
    return TradingEnv(_ticks(), RLConfig(cost_bps=0.5, reward_scale=1e4, action_mode="continuous"))


def test_continuous_env_action_clip_and_reward():
    env = _env()
    env.reset(seed=0)
    obs, r, term, trunc, info = env.step(5.0)   # 범위 초과 → +1 로 클립
    assert info["position"] == 1.0
    obs, r, term, trunc, info = env.step(-9.0)  # → -1 로 클립
    assert info["position"] == -1.0
    obs, r, term, trunc, info = env.step(0.3)   # 연속값 유지
    assert info["position"] == pytest.approx(0.3)


def test_agent_act_in_range_and_determinism():
    a1 = ContinuousPPOAgent(seed=1)
    a2 = ContinuousPPOAgent(seed=1)
    env1, env2 = _env(), _env()
    _, ac1, _, t1 = run_episode(env1, a1, seed=2)
    _, ac2, _, t2 = run_episode(env2, a2, seed=2)
    assert all(-1.0 <= float(a) <= 1.0 for a in ac1)
    assert ac1 == pytest.approx(ac2)
    assert t1 == pytest.approx(t2)


def test_continuous_training_does_not_degrade():
    env = _env()
    agent = ContinuousPPOAgent(seed=0)
    _, _, _, base = run_episode(env, agent, greedy=False, seed=1)
    history = train_ppo_continuous(env, agent, iterations=30, seed=1)
    _, _, _, trained = run_episode(env, agent, greedy=True, seed=1)
    assert len(history) == 30
    assert np.isfinite(trained)
    assert trained >= base - abs(base) * 0.5 - 1.0


def test_onnx_policy_export_roundtrip_matches_numpy():
    onnx = pytest.importorskip("onnx")
    ort = pytest.importorskip("onnxruntime")
    import tempfile
    from pathlib import Path

    from daytrade.training.onnx_export import export_continuous_policy_to_onnx

    env = _env()
    agent = ContinuousPPOAgent(seed=0)
    train_ppo_continuous(env, agent, iterations=10, seed=1)

    with tempfile.TemporaryDirectory() as d:
        path = str(Path(d) / "policy.onnx")
        export_continuous_policy_to_onnx(agent.W, agent.b, env._mean, env._std, path)
        sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        iname = sess.get_inputs()[0].name

        rng = np.random.default_rng(0)
        for _ in range(20):
            raw_feats = rng.normal(size=env._mean.shape[0])  # 표준화 전 raw 피처
            position = float(rng.uniform(-1, 1))
            obs_raw = np.concatenate([raw_feats, [position]]).astype(np.float32)
            onnx_out = float(sess.run(None, {iname: obs_raw.reshape(1, -1)})[0][0][0])
            # numpy 참조: 그래프가 내장한 표준화(mean9/std9)와 동일하게 재현
            std_feats = (raw_feats - env._mean) / env._std
            obs_std = np.concatenate([std_feats, [position]])
            ref = agent.mean(obs_std)
            assert abs(onnx_out - ref) <= 1e-5


def test_onnx_policy_model_inference_interface():
    pytest.importorskip("onnx")
    pytest.importorskip("onnxruntime")
    import tempfile
    from pathlib import Path

    from daytrade.features.engine import FeatureEngine
    from daytrade.inference import OnnxPolicyModel
    from daytrade.training.onnx_export import export_continuous_policy_to_onnx

    env = _env()
    agent = ContinuousPPOAgent(seed=0)
    train_ppo_continuous(env, agent, iterations=10, seed=1)

    with tempfile.TemporaryDirectory() as d:
        path = str(Path(d) / "policy.onnx")
        export_continuous_policy_to_onnx(agent.W, agent.b, env._mean, env._std, path)
        model = OnnxPolicyModel(path)

        fe = FeatureEngine(depth=10)
        for tick in _ticks(120, seed=5):
            fv = fe.update(tick)
            pb, ps = model.predict(fv)
            assert 0.0 <= pb <= 1.0 and 0.0 <= ps <= 1.0
            assert not (pb > 0 and ps > 0)  # 롱/숏 동시 양수 불가(부호 사상)
        assert -1.0 <= model._position <= 1.0
