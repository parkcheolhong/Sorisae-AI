"""관광 RAG top-k 런타임 SSOT + 스윕 제안기 단위테스트(Qdrant/임베딩 불필요).

검증 대상:
- `tourism_rag_top_k()`: env `TOURISM_RAG_TOP_K` 파싱·클램프·기본값(런타임 라이브 조정 출처).
- `eval_tourism_retrieval.select_best_k()`: k-스윕 요약에서 최적 k 제안(순수함수, 사람승인 게이트 표식).
이 둘은 외부 의존성이 없어 GPU/Qdrant 없는 환경에서도 결정적으로 검증된다.
"""

import importlib.util
import sys
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]

from backend.services.tourism_kb import tourism_rag_top_k
from backend.services.tourism_kb import service as tourism_service


def _load_eval_module():
    """scripts/eval_tourism_retrieval.py 를 파일 경로로 로드(패키지 아님)."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "eval_tourism_retrieval.py"
    spec = importlib.util.spec_from_file_location("eval_tourism_retrieval_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_top_k_default_unset(monkeypatch):
    monkeypatch.delenv("TOURISM_RAG_TOP_K", raising=False)
    assert tourism_rag_top_k() == tourism_service.TOURISM_RAG_TOP_K_DEFAULT


def test_top_k_parses_valid_env(monkeypatch):
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "8")
    assert tourism_rag_top_k() == 8


def test_top_k_clamps_bounds(monkeypatch):
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "999")
    assert tourism_rag_top_k() == tourism_service.TOURISM_RAG_TOP_K_MAX
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "0")
    assert tourism_rag_top_k() == tourism_service.TOURISM_RAG_TOP_K_MIN


def test_top_k_invalid_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "not-a-number")
    assert tourism_rag_top_k() == tourism_service.TOURISM_RAG_TOP_K_DEFAULT


def test_select_best_k_prefers_accuracy_then_smaller_k(monkeypatch):
    mod = _load_eval_module()
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "5")
    summaries = [
        {"k": 3, "accuracy_category_hit": 0.80, "mean_precision_at_k": 0.5,
         "country_hit_rate": 0.7, "run_time_sec": 1.0},
        {"k": 5, "accuracy_category_hit": 0.90, "mean_precision_at_k": 0.6,
         "country_hit_rate": 0.8, "run_time_sec": 1.2},
        {"k": 8, "accuracy_category_hit": 0.90, "mean_precision_at_k": 0.6,
         "country_hit_rate": 0.8, "run_time_sec": 2.0},
    ]
    prop = mod.select_best_k(summaries)
    # accuracy 동률(0.90)·precision 동률 → 더 빠르고 작은 k(=5) 선호.
    assert prop["proposed_top_k"] == 5
    assert prop["current_top_k"] == 5
    assert prop["current_in_sweep"] is True
    assert prop["improves_over_current"] is False
    assert prop["gate_status"].startswith("PROPOSAL_ONLY")
    assert prop["runtime_ssot_env"] == "TOURISM_RAG_TOP_K"
    assert [c["k"] for c in prop["candidates"]] == [3, 5, 8]


def test_select_best_k_recommends_change_when_better(monkeypatch):
    mod = _load_eval_module()
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "5")
    summaries = [
        {"k": 5, "accuracy_category_hit": 0.85, "mean_precision_at_k": 0.5,
         "country_hit_rate": 0.7, "run_time_sec": 1.0},
        {"k": 8, "accuracy_category_hit": 0.95, "mean_precision_at_k": 0.6,
         "country_hit_rate": 0.8, "run_time_sec": 1.5},
    ]
    prop = mod.select_best_k(summaries)
    assert prop["proposed_top_k"] == 8
    assert prop["current_in_sweep"] is True
    assert prop["improves_over_current"] is True
    assert "TOURISM_RAG_TOP_K=8" in prop["apply_hint"]


def test_select_best_k_honest_when_current_not_swept(monkeypatch):
    mod = _load_eval_module()
    monkeypatch.setenv("TOURISM_RAG_TOP_K", "5")  # 현재 k=5 인데 스윕엔 없음
    summaries = [
        {"k": 3, "accuracy_category_hit": 0.80, "mean_precision_at_k": 0.5,
         "country_hit_rate": 0.7, "run_time_sec": 1.0},
        {"k": 8, "accuracy_category_hit": 0.95, "mean_precision_at_k": 0.6,
         "country_hit_rate": 0.8, "run_time_sec": 1.5},
    ]
    prop = mod.select_best_k(summaries)
    assert prop["proposed_top_k"] == 8
    assert prop["current_in_sweep"] is False
    # 현재 k 미측정 → 개선 단정 금지(null).
    assert prop["improves_over_current"] is None
    assert "5" in prop["note"]


def test_select_best_k_empty_returns_empty():
    mod = _load_eval_module()
    assert mod.select_best_k([]) == {}
