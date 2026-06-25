"""인프로세스 장애 주입(chaos) 도구 — Chaos-Mesh 없이 복원력 검증(설계서 §10 운영 안정성).

Chaos-Mesh 는 K8s 레벨에서 네트워크 지연·파드 킬 등을 주입하지만 클러스터가 필요하다. 본 모듈은
동일 목적(자동 재연결·서킷브레이커·롤백 가드의 **장애 내성 검증**)을 **인프로세스**에서 달성한다.
피드/실행기를 감싸 끊김·지연·드롭·손상·거부·예외를 결정론적으로 주입하므로, 네트워크·실시간 없이
`LiveRunner` 등의 회복 동작을 단위 테스트로 재현할 수 있다.
"""
from .faults import (
    FaultInjectingFeed,
    FlakyExecutor,
    FlakyFeedFactory,
)

__all__ = [
    "FaultInjectingFeed",
    "FlakyFeedFactory",
    "FlakyExecutor",
]
