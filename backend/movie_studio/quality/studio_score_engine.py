from __future__ import annotations

from typing import Iterable, List

from backend.movie_studio.contracts.quality_gate_contract import (
    QualityFailureContract,
    StudioQualityGateResultContract,
)


def build_quality_result(failures: Iterable[QualityFailureContract]) -> StudioQualityGateResultContract:
    failure_list: List[QualityFailureContract] = list(failures)
    passed = not failure_list
    score = 100.0 if passed else max(0.0, 100.0 - (len(failure_list) * 15.0))
    return StudioQualityGateResultContract(
        passed=passed,
        score=score,
        failures=failure_list,
        rerender_required=not passed,
    )
