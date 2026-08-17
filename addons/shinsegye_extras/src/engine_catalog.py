"""
소리새 엔진 통합 카탈로그

이 파일은 tmp/external_migrations의 모든 소리새 소스 파일을 분류하고
통합 상태를 기록하는 공식 레지스트리입니다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any

# ── 통합 완료된 엔진 목록 ──────────────────────────────────────────────
INTEGRATED_ENGINES: List[Dict[str, Any]] = [
    # 통역/언어 축 (addons/shinsegye_interpreter/src/)
    {"id": "INT-001", "file": "sorisae_interpreter.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-002", "file": "hybrid_interpreter_system.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/health", "status": "integrated"},
    {"id": "INT-003", "file": "hybrid_conversation_translator.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-004", "file": "multilingual_system.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-005", "file": "sorisae_multilingual_support.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    {"id": "INT-006", "file": "sorisae_southeast_asia_translator.py", "category": "interpreter", "addon": "shinsegye_interpreter", "api": "/api/marketplace/interpreter/translate", "status": "integrated"},
    # 음악/오디오 축 (addons/shinsegye_music_system/src/)
    {"id": "MUS-001", "file": "ai_music_composer.py", "category": "music", "addon": "shinsegye_music_system", "api": "/api/marketplace/music/compose/emotion", "status": "integrated"},
    {"id": "MUS-002", "file": "emotion_based_music_generator.py", "category": "music", "addon": "shinsegye_music_system", "api": "/api/marketplace/music/compose/emotion", "status": "integrated"},
    {"id": "MUS-003", "file": "music_chat_friend_system.py", "category": "music", "addon": "shinsegye_music_system", "api": "/api/marketplace/music/friends/demo", "status": "integrated"},
    # IoT 축 (addons/shinsegye_extras/src/)
    {"id": "IOT-001", "file": "hybrid_iot_controller.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/health", "status": "integrated"},
    {"id": "IOT-002", "file": "sorisae_iot_smarthome.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/devices", "status": "integrated"},
    {"id": "IOT-003", "file": "sorisae_iot_integration.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/status", "status": "integrated"},
    {"id": "IOT-004", "file": "multi_ego_engine.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/status", "status": "integrated"},
    {"id": "IOT-005", "file": "spatiotemporal_learning_system.py", "category": "iot", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/iot/status", "status": "integrated"},
    # 게임 경제 축 (addons/shinsegye_extras/src/)
    {"id": "GAM-001", "file": "sorisae_game_economy_system.py", "category": "simulation", "addon": "shinsegye_extras", "api": "/api/marketplace/extras/game/simulate", "status": "integrated"},
]

# ── 미통합 엔진 목록 (기타 243개 중 대표 목록) ──────────────────────
# 하드웨어 의존성으로 오프라인 전용 분류
OFFLINE_ENGINES: List[Dict[str, Any]] = [
    # 음성/TTS 카테고리 (speech_recognition, pyttsx3 요구)
    {"id": "VOI-001", "file": "sorisae_voice_processor.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-002", "file": "hybrid_voice_processor.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-003", "file": "voice_calling_system.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-004", "file": "voice_command_processor.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-005", "file": "sorisae_iot_voice_control.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-006", "file": "voice_tuner.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    {"id": "VOI-007", "file": "sorisae_voice_reactive.py", "category": "voice", "deps": ["speech_recognition", "pyttsx3"], "status": "offline", "reason": "hardware-audio-required"},
    # 보안 카테고리
    {"id": "SEC-001", "file": "hybrid_cyber_security_system.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SEC-002", "file": "advanced_security_system.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SEC-003", "file": "biometric_security_system.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SEC-004", "file": "cyber_detective_ai.py", "category": "security", "deps": [], "status": "available", "reason": "pending-integration"},
    # AI 브레인 카테고리
    {"id": "BRN-001", "file": "sorisae_master_hybrid_system.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "BRN-002", "file": "sorisae_ai_decision_engine.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "BRN-003", "file": "sorisae_enhanced_consciousness.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "BRN-004", "file": "sorisae_ethical_consciousness_engine.py", "category": "brain", "deps": [], "status": "available", "reason": "pending-integration"},
    # 시뮬레이션 카테고리 (추가 통합 대상)
    {"id": "SIM-001", "file": "game_earning_analysis.py", "category": "simulation", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "SIM-002", "file": "sorisae_fantasy_vr_infinite_universe_game.py", "category": "simulation", "deps": [], "status": "available", "reason": "pending-integration"},
    # 투자/금융 카테고리
    {"id": "FIN-001", "file": "sorisae_investment_advisor_200.py", "category": "finance", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "FIN-002", "file": "stock_prediction_200_percent.py", "category": "finance", "deps": [], "status": "available", "reason": "pending-integration"},
    {"id": "FIN-003", "file": "sorisae_dual_brain_stock_system.py", "category": "finance", "deps": [], "status": "available", "reason": "pending-integration"},
]


def get_all_engines() -> List[Dict[str, Any]]:
    """전체 엔진 목록 반환"""
    return INTEGRATED_ENGINES + OFFLINE_ENGINES


def get_integration_summary() -> Dict[str, Any]:
    """통합 현황 요약"""
    integrated = [e for e in INTEGRATED_ENGINES]
    offline = [e for e in OFFLINE_ENGINES if e["status"] == "offline"]
    available = [e for e in OFFLINE_ENGINES if e["status"] == "available"]

    # 실제 소스 파일 총수 (tmp 디렉토리 기반)
    src_base = Path(__file__).resolve().parents[3] / "tmp" / "external_migrations" / "run_all_shinsegye.py"
    total_src_files = 0
    if src_base.exists():
        total_src_files = sum(1 for f in src_base.rglob("*.py")
                              if "__pycache__" not in str(f) and f.stat().st_size > 1000)

    return {
        "total_source_files": total_src_files,
        "integrated_count": len(integrated),
        "offline_count": len(offline),
        "available_for_integration": len(available),
        "integration_rate": round(len(integrated) / max(total_src_files, 1) * 100, 1),
        "categories": {
            "interpreter": len([e for e in integrated if e["category"] == "interpreter"]),
            "music": len([e for e in integrated if e["category"] == "music"]),
            "iot": len([e for e in integrated if e["category"] == "iot"]),
            "simulation": len([e for e in integrated if e["category"] == "simulation"]),
            "voice_offline": len(offline),
            "pending": len(available),
        }
    }
