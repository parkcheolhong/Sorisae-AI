"""WorldLinco P2 자동 튜닝 스캐폴드 단위테스트 (stdlib 폴백 경로).

Optuna 미설치 환경에서도 동작해야 하므로 폴백 제안기를 검증한다.
"""

import json

import pytest  # pyright: ignore[reportMissingImports]

from eval.worldlinco.search_space import KNOBS_BY_NAME, clamp_config, current_config
from eval.worldlinco import optimize as opt


def test_knob_clamp_snaps_to_step_and_bounds():
    knob = KNOBS_BY_NAME["silero_silence_ms"]  # 600..1400 step 50
    assert knob.clamp(1234.0) == 1250.0          # 가장 가까운 스텝
    assert knob.clamp(99999.0) == knob.high       # 상한
    assert knob.clamp(-5.0) == knob.low           # 하한


def test_clamp_config_fills_missing_with_current():
    cfg = clamp_config({"silero_silence_ms": 813.0})
    assert cfg["silero_silence_ms"] == 800.0      # 813 -> step 50 snap
    # 누락된 노브는 현재 SSOT 값으로 채움.
    assert cfg["silero_safety_cap_ms"] == KNOBS_BY_NAME["silero_safety_cap_ms"].current


def test_seed_observations_runnable_without_input():
    obs = opt.load_observations(None)
    assert obs, "내장 시드 관측이 있어야 한다"
    report = opt.build_report(obs)
    assert report["gate_status"].startswith("PROPOSAL_ONLY")
    assert set(report["devices"]) >= {"s10", "tab"}


def test_dominant_rearm_lowers_silence():
    # post_flush_rearm 지배 → 종단 무음을 낮춰 마이크 재개를 빠르게.
    obs = [opt.Observation(
        params=current_config(), j=0.6,
        components={"post_flush_rearm": 0.45, "reject_rate": 0.05},
        device="tab")]
    proposal = opt.propose_next(obs)
    assert proposal["silero_silence_ms"] < current_config()["silero_silence_ms"]


def test_dominant_reject_raises_silence():
    # reject_rate 지배 → 종단 무음/최소세그먼트를 높여 무음거절을 줄임.
    base = dict(current_config())
    base["silero_silence_ms"] = 800.0
    obs = [opt.Observation(
        params=base, j=0.7,
        components={"reject_rate": 0.40, "post_flush_rearm": 0.05},
        device="s10")]
    proposal = opt.propose_next(obs)
    assert proposal["silero_silence_ms"] > base["silero_silence_ms"]


def test_propose_is_deterministic_with_seed():
    obs = opt.load_observations(None)
    a = opt.propose_next(obs, seed=7)
    b = opt.propose_next(obs, seed=7)
    assert a == b


def test_load_observations_groups_by_device_and_config(tmp_path):
    rows = [
        {"log_file": "s10-g10-001.log", "config_version": 3, "objective_J": 0.40,
         "objective_components": {"post_flush_rearm": 0.20}},
        {"log_file": "s10-g10-002.log", "config_version": 3, "objective_J": 0.50,
         "objective_components": {"post_flush_rearm": 0.30}},
        {"log_file": "tab-g10-001.log", "config_version": 3, "objective_J": 0.65,
         "objective_components": {"post_flush_rearm": 0.44}},
        # 레지스트리에 없는 config_version은 무시되어야 한다.
        {"log_file": "s10-x.log", "config_version": 99, "objective_J": 0.10},
    ]
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    obs = opt.load_observations(str(p))

    by_dev = {o.device: o for o in obs}
    assert set(by_dev) == {"s10", "tab"}
    assert by_dev["s10"].n_calls == 2
    assert by_dev["s10"].j == pytest.approx(0.45)        # (0.40+0.50)/2
    assert by_dev["s10"].components["post_flush_rearm"] == pytest.approx(0.25)


def test_report_emits_proposal_json(tmp_path):
    obs = opt.load_observations(None)
    report = opt.build_report(obs)
    out = tmp_path / "proposal.json"
    out.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["backend"] in {"optuna", "stdlib-coordinate"}
    for dev in loaded["devices"].values():
        # 제안 벡터는 모든 노브를 포함하고 경계 내여야 한다.
        for name, knob in KNOBS_BY_NAME.items():
            v = dev["proposed_next"][name]
            assert knob.low <= v <= knob.high
