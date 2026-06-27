"""WorldLinco V2 — Communication OS layer (additive, Strangler Fig).

이 패키지는 로드맵(`docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md`)의 상위 계층
(Orchestrator / Session Core / Hubs)을 **기존 hot path를 변경하지 않고** 점진적으로
얹기 위한 자리다. 모든 기능은 ``COMM_V2_*`` 환경변수로 opt-in 하며, 기본값은 off다.
"""
