"""
소리새 AI 엔진 컨트롤 타워 (SorisaeEngineHub)

이 모듈은 codeAI 플랫폼의 중앙 AI 엔진 허브 역할을 합니다.
모든 AI 기능 요청은 이곳을 거쳐 소리새 엔진 슬롯으로 라우팅됩니다.

등록 규칙:
  - 새 마켓 상품 라우터에서 `engine="sorisae"` 를 선언하면
    SorisaeEngineHub.dispatch() 를 자동으로 경유합니다.
  - 슬롯 번호는 SORISAE_ENGINE_REGISTRY 에 엔진 타입 키로 등록합니다.
"""
from __future__ import annotations

import importlib.util
import logging
import socket
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

logger = logging.getLogger(__name__)

# ── 엔진 슬롯 경로 ──────────────────────────────────────────────
_ENGINES_DIR = (
    Path(__file__).resolve().parent / "engines120"
)
_EXTRAS_DIR = Path(__file__).resolve().parent / "extras"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LEGACY_ADDON_DIR = _REPO_ROOT / "addons" / "shinsegye_extras" / "src" / "full_merge_all"
_LEGACY_MODULES_DIR = _LEGACY_ADDON_DIR / "modules"
_LEGACY_AI_CODE_MANAGER_DIR = _LEGACY_MODULES_DIR / "ai_code_manager"
_LEGACY_PLUGINS_DIR = _LEGACY_MODULES_DIR / "plugins"


def _iter_helper_paths() -> list[Path]:
    helper_paths = [_ENGINES_DIR, _EXTRAS_DIR]
    helper_paths.extend(
        path
        for path in (
            _LEGACY_ADDON_DIR,
            _LEGACY_MODULES_DIR,
            _LEGACY_AI_CODE_MANAGER_DIR,
            _LEGACY_PLUGINS_DIR,
        )
        if path.exists()
    )
    return helper_paths

# ── 엔진 타입 → 슬롯 파일 매핑 ──────────────────────────────────
# 소리새 120 슬롯 전수 분석 결과: 중복·테스트·단순런처 제외,
# 실 능력 보유 슬롯 82개 전부 등록 → 100배 활용 체계 완성
SORISAE_ENGINE_REGISTRY: Dict[str, str] = {

    # ════════════════════════════════════════════════════════════
    # [A] 핵심 지능 · 의식 시스템  (105% 신적지능 / 양자 / 다차원)
    # ════════════════════════════════════════════════════════════
    "decision":                 "slot040_sorisae_ai_decision_engine.py",
    "divine":                   "slot100_sorisae_divine_intelligence_105.py",    # 105% 신적지능
    "transcendent":             "slot110_sorisae_transcendent_102.py",
    "master":                   "slot106_sorisae_master_system.py",
    "master_hybrid":            "slot097_sorisae_master_hybrid_system.py",
    "integrated":               "slot119_sorisae_integrated_hybrid_system.py",
    "dual_brain":               "slot051_sorisae_dual_brain_comparison.py",
    "consciousness":            "slot037_sorisae_enhanced_consciousness.py",     # 강화 의식
    "consciousness_engine":     "slot069_consciousness_engine.py",               # 순수 의식엔진
    "ethics":                   "slot038_sorisae_ethical_consciousness_engine.py",
    "ethics_simple":            "slot047_sorisae_ethical_consciousness_simple.py",
    "quantum":                  "slot118_sorisae_nextgen_features.py",           # 양자의식·시공간·멀티버스·DNA개인화·신경망직결
    "spacetime":                "slot061_spatiotemporal_learning_system_new.py", # 시공간 학습
    "spatiotemporal":           "slot036_spatiotemporal_learning_system.py",
    "core_features":            "slot088_sorisae_core_new_features_20251019_182012.py",

    # ════════════════════════════════════════════════════════════
    # [B] 음성 · 언어 처리 시스템  (음성인식 / TTS / 통역)
    # ════════════════════════════════════════════════════════════
    "voice_movie":              "slot001_sorisae_voice_movie_server.py",         # 음성+영화
    "voice_processor":          "slot004_sorisae_voice_processor.py",
    "voice_tuner":              "slot005_voice_tuner.py",                        # 음성 튜너
    "voice_reactive":           "slot006_sorisae_voice_reactive.py",             # 반응형 음성
    "voice_calling":            "slot007_voice_calling_system.py",               # 음성 통화
    "voice_hybrid":             "slot012_hybrid_voice_processor.py",
    "voice_command":            "slot020_voice_command_processor.py",            # 음성 명령 제어
    "voice_fallback":           "slot024_voice_response_fallback.py",
    "interpreter":              "slot015_sorisae_interpreter.py",
    "hybrid_interpreter":       "slot008_hybrid_interpreter_system.py",
    "multilingual":             "slot013_multilingual_system.py",
    "multilingual_support":     "slot023_sorisae_multilingual_support.py",       # 다국어지원 (SorisaeMultilingualSupport)
    "translator":               "slot003_hybrid_conversation_translator.py",
    "southeast_asia":           "slot016_sorisae_southeast_asia_translator.py",

    # ════════════════════════════════════════════════════════════
    # [C] 음악 · 창작 7대 분야  (작곡 / 감정음악 / 애니 / 영상 / 게임)
    # ════════════════════════════════════════════════════════════
    "music":                    "slot011_ai_music_composer.py",                  # 음악 창작
    "music_chat":               "slot017_music_chat_system.py",                  # 음악 채팅
    "music_chat_web":           "slot009_music_chat_web.py",
    "music_chat_friend":        "slot019_music_chat_friend_system.py",           # 음악 친구 시스템
    "emotion_music":            "slot028_emotion_based_music_generator.py",      # 감정기반 음악생성
    "animation_theme":          "slot029_animation_studio_theme_song_demo.py",   # 애니 테마곡
    "animation":                "slot091_sorisae_animation_studio_ultra.py",     # 애니메이션스튜디오
    "movie":                    "slot103_sorisae_movie_web_server.py",           # 영상 기획
    "game":                     "slot081_realtime_game_generator.py",            # 실시간 게임생성
    "game_concept":             "slot082_sorisae_game_concept_design.py",
    "game_economy":             "slot074_sorisae_game_economy_system.py",
    "earning_game":             "slot083_sorisae_earning_game.py",               # 수익게임
    "vr":                       "slot073_sorisae_fantasy_vr_infinite_universe_game.py",  # VR 무한우주

    # ════════════════════════════════════════════════════════════
    # [D] 감정 · 치유 · 꿈  (감정색채치료 / 꿈해석)
    # ════════════════════════════════════════════════════════════
    "emotion_therapy":          "slot093_emotion_color_therapist.py",            # 감정색채치료사 (98%)
    "dream":                    "slot010_dream_interpreter.py",                  # 꿈 해석기
    "ethical_gps":              "slot092_ethical_gps_system.py",                 # 윤리적 GPS

    # ════════════════════════════════════════════════════════════
    # [E] 미래예측 · 투자 · 주식
    # ════════════════════════════════════════════════════════════
    "future_prediction":        "slot104_future_prediction_engine.py",           # 미래예측 92%
    "stock":                    "slot045_sorisae_dual_brain_stock_system.py",
    "stock_prediction":         "slot076_stock_prediction_200_percent.py",       # 200% 주가예측
    "investment":               "slot075_sorisae_investment_advisor_200.py",     # 투자 어드바이저

    # ════════════════════════════════════════════════════════════
    # [F] IoT · 스마트홈 · 위성 · 자동차
    # ════════════════════════════════════════════════════════════
    "iot":                      "slot043_sorisae_iot_integration.py",
    "iot_core":                 "slot055_sorisae_iot_integration.py",            # IoT 코어
    "iot_voice":                "slot014_sorisae_iot_voice_control.py",          # IoT 음성 제어
    "iot_discovery":            "slot056_sorisae_iot_auto_discovery.py",         # IoT 자동 탐지
    "hybrid_iot":               "slot042_hybrid_iot_controller.py",
    "smarthome":                "slot044_sorisae_iot_smarthome.py",              # 스마트홈 AI집사
    "smart_car":                "slot114_sorisae_smart_car_control.py",
    "satellite":                "slot115_sorisae_satellite_wifi_system.py",      # 175개 위성네트워크

    # ════════════════════════════════════════════════════════════
    # [G] 보안 · 사이버탐정 · 법과학
    # ════════════════════════════════════════════════════════════
    "security":                 "slot049_advanced_security_system.py",
    "hybrid_security":          "slot039_hybrid_cyber_security_system.py",
    "biometric":                "slot063_biometric_security_system.py",
    "security_key":             "slot066_security_key_manager.py",              # 보안키 관리자
    "detective":                "slot050_cyber_detective_ai.py",                 # 사이버 탐정
    "detective_dashboard":      "slot041_cyber_detective_dashboard.py",
    "visual_monitor":           "slot046_cyber_detective_visual_monitoring.py",  # 시각 모니터링
    "cyber_future_tech":        "slot052_cyber_detective_future_tech.py",        # 차세대 수사기술
    "cyber_investigator":       "slot054_sorisae_cyber_investigator.py",
    "global_cyber_monitor":     "slot057_cyber_detective_global_server_analysis.py",  # 글로벌 사이버감시
    "gps_investigation":        "slot059_cyber_detective_gps_radius.py",         # GPS 반경 수사
    "cyber_realtime":           "slot062_cyber_realtime_monitor.py",

    # ════════════════════════════════════════════════════════════
    # [H] 비즈니스 · 마케팅 · 쇼핑
    # ════════════════════════════════════════════════════════════
    "marketing":                "slot109_autonomous_marketing_system.py",        # 자율 마케팅
    "shopping":                 "slot120_shopping_mall_dashboard.py",
    "shopping_tutor":           "slot095_integrated_shopping_tutor_designer.py", # 통합쇼핑·튜터·디자이너
    "civil_engineering":        "slot108_sorisae_civil_engineering_bidding.py",

    # ════════════════════════════════════════════════════════════
    # [I] 개발 · 플러그인 · 성능 · 분석
    # ════════════════════════════════════════════════════════════
    "plugin":                   "slot111_smart_plugin_generator.py",
    "virtual_team":             "slot098_virtual_dev_team.py",                   # 가상 개발팀
    "analyzer":                 "slot113_comprehensive_project_analyzer.py",
    "project_organizer":        "slot101_organize_projects_into_folders.py",
    "caching":                  "slot105_next_gen_caching_system.py",            # 차세대 캐싱
    "async_performance":        "slot116_async_performance_system.py",           # 비동기 고성능
    "integrated_dashboard":     "slot089_sorisae_integrated_dashboard.py",       # 통합 대시보드

    # ════════════════════════════════════════════════════════════
    # [J] 호환성 별칭  (기존 공개 키와 스캔 기반 보조 키 유지)
    # ════════════════════════════════════════════════════════════
    "movie_server":             "slot103_sorisae_movie_web_server.py",
    "movie_web":                "slot103_sorisae_movie_web_server.py",
    "calling":                  "slot007_voice_calling_system.py",
    "hybrid_voice":             "slot012_hybrid_voice_processor.py",
    "music_friend":             "slot019_music_chat_friend_system.py",
    "iot_voice_control":        "slot014_sorisae_iot_voice_control.py",
    "stock_200":                "slot076_stock_prediction_200_percent.py",
    "security_key_manager":     "slot066_security_key_manager.py",
    "realtime_monitor":         "slot062_cyber_realtime_monitor.py",
}

# ── 슬롯별 진입 함수 오버라이드 맵 (auto-scan 2026-05-05) ────────────
# entry_fn 인자 미지정 시 이 맵을 1순위로 참조한다.
# 스캔 근거: backend/services/shinsegye/engines120/ 내 모든 .py AST 파싱
SORISAE_SLOT_ENTRY_FN_MAP: Dict[str, str] = {
    # ── 함수 없음 / 클래스 전용 슬롯 (module_only 정상) ──
    # slot010, slot011, slot062, slot069, slot088, slot090, slot098, slot111, slot116
    # smarthome(slot044), music(slot011), dream(slot010) 등 클래스 기반

    # ── main 이 있는 슬롯 (기본 후보로 자동 처리됨, 명시 등록은 비어도 됨) ──

    # ── main 이 없는 슬롯 → 실제 진입 함수명 명시 ──
    "slot004_sorisae_voice_processor.py":              "test_voice_processor",
    "slot007_voice_calling_system.py":                 "test_voice_calling_system",
    "slot009_music_chat_web.py":                       "setup_music_chat_interface",
    "slot013_multilingual_system.py":                  "test_multilingual_system",
    "slot017_music_chat_system.py":                    "get_chat_system",
    "slot018_test_voice_reactive.py":                  "run_tests",
    "slot019_music_chat_friend_system.py":             "get_friend_system",
    "slot024_voice_response_fallback.py":              "get_fallback_response",
    "slot025_test_socket_voice_fixes.py":              "run_tests",
    "slot030_enhanced_voice_exit.py":                  "process_voice_command",
    "slot031_ai_speech_tts.py":                        "speak",
    "slot032_start_music_chat_server.py":              "start_server",
    "slot036_spatiotemporal_learning_system.py":       "test_spatiotemporal_learning",
    "slot037_sorisae_enhanced_consciousness.py":       "test_enhanced_consciousness",
    "slot038_sorisae_ethical_consciousness_engine.py": "test_ethical_consciousness_engine",
    "slot040_sorisae_ai_decision_engine.py":           "test_decision_engine",
    "slot041_cyber_detective_dashboard.py":            "dashboard",
    "slot043_sorisae_iot_integration.py":              "test_iot_integration",
    "slot044_sorisae_iot_smarthome.py":                "test_iot_system",
    "slot047_sorisae_ethical_consciousness_simple.py": "test_ethical_consciousness",
    "slot050_cyber_detective_ai.py":                   "demo_cyber_detective",
    "slot061_spatiotemporal_learning_system_new.py":   "test_spatiotemporal_system",
    "slot076_stock_prediction_200_percent.py":         "demonstrate_stock_prediction_200_percent",
    "slot080_realtime_game_generator_20251019_182012.py": "create_game_response",
    "slot081_realtime_game_generator.py":              "create_game_response",
    "slot094_sorisae_dashboard_web.py":                "run_dashboard",
    "slot099_detailed_technical_report.py":            "generate_detailed_technical_report",
    "slot109_autonomous_marketing_system.py":          "create_autonomous_marketing_response",
    "slot112_ethical_gps_system_simple.py":            "demo_ethical_gps_system",
    "slot120_shopping_mall_dashboard.py":              "start_dashboard_server",
}


def _resolve_slot_entry_fn(slot_file: str) -> Optional[str]:
    """슬롯 파일명 기준으로 권장 진입 함수명을 반환한다. 없으면 None."""
    return SORISAE_SLOT_ENTRY_FN_MAP.get(slot_file)


# ── Flask 서버형 슬롯 → 독립 컨테이너 URL 매핑 ──────────────────────
# docker-compose.yml 에 서비스로 분리된 슬롯.
# dispatch() 에서 이 맵에 해당하는 슬롯은 인-프로세스 실행 대신
# HTTP POST /api/dispatch 로 프록시한다.
# 환경변수로 URL 오버라이드 가능: SORISAE_FLASK_{UPPER_ALIAS}_URL
SORISAE_FLASK_SERVER_MAP: Dict[str, str] = {
    "slot001_sorisae_voice_movie_server.py":    "http://sorisae-voice-movie:5050",
    "slot041_cyber_detective_dashboard.py":     "http://sorisae-cyber-detective:5052",
    "slot089_sorisae_integrated_dashboard.py":  "http://sorisae-integrated-dashboard:5050",
    "slot094_sorisae_dashboard_web.py":         "http://sorisae-dashboard-web:5050",
    "slot103_sorisae_movie_web_server.py":      "http://sorisae-movie-server:5000",
    "slot106_sorisae_master_system.py":         "http://sorisae-master-system:5050",
    "slot120_shopping_mall_dashboard.py":       "http://sorisae-shopping-mall:5050",
}

# 환경변수 오버라이드 적용
import os as _os
_ENV_OVERRIDES = {
    "slot001_sorisae_voice_movie_server.py":    _os.environ.get("SORISAE_FLASK_VOICE_MOVIE_URL", ""),
    "slot041_cyber_detective_dashboard.py":     _os.environ.get("SORISAE_FLASK_CYBER_DETECTIVE_URL", ""),
    "slot089_sorisae_integrated_dashboard.py":  _os.environ.get("SORISAE_FLASK_INTEGRATED_DASHBOARD_URL", ""),
    "slot094_sorisae_dashboard_web.py":         _os.environ.get("SORISAE_FLASK_DASHBOARD_WEB_URL", ""),
    "slot103_sorisae_movie_web_server.py":      _os.environ.get("SORISAE_FLASK_MOVIE_SERVER_URL", ""),
    "slot106_sorisae_master_system.py":         _os.environ.get("SORISAE_FLASK_MASTER_SYSTEM_URL", ""),
    "slot120_shopping_mall_dashboard.py":       _os.environ.get("SORISAE_FLASK_SHOPPING_MALL_URL", ""),
}
for _slot, _url in _ENV_OVERRIDES.items():
    if _url:
        SORISAE_FLASK_SERVER_MAP[_slot] = _url




def _failure_payload(
    engine_type: str,
    status: str,
    error_code: str,
    error_message: str,
    retryable: bool,
    source: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "engine": engine_type,
        "status": status,
        "error": error_message,
        "error_code": error_code,
        "error_message": error_message,
        "retryable": retryable,
        "source": source,
        "result": None,
    }
    if extra:
        payload.update(extra)
    return payload


def _dispatch_to_flask_server(
    engine_type: str,
    slot_file: str,
    context: Dict[str, Any],
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Flask 서버형 슬롯에 HTTP POST 로 dispatch 요청을 프록시한다."""
    import urllib.request
    import urllib.error
    import json as _json

    base_url = SORISAE_FLASK_SERVER_MAP[slot_file]
    endpoint = f"{base_url}/api/dispatch"
    payload = _json.dumps({"engine_type": engine_type, "context": context}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _json.loads(resp.read())
            return {
                "engine": engine_type,
                "status": "flask_server_ok",
                "server_url": base_url,
                "result": body,
            }
    except urllib.error.HTTPError as exc:
        logger.warning(
            "[SorisaeHub] Flask 서버 HTTP 오류 (%s → %s): %s",
            engine_type, base_url, exc,
        )
        return _failure_payload(
            engine_type=engine_type,
            status="flask_server_http_error",
            error_code="FLASK_SERVER_HTTP_ERROR",
            error_message=str(exc),
            retryable=exc.code >= 500,
            source="flask_proxy",
            extra={"server_url": base_url, "http_status": exc.code},
        )
    except urllib.error.URLError as exc:
        reason = exc.reason
        reason_text = str(reason or exc)
        is_timeout = (
            isinstance(reason, TimeoutError)
            or isinstance(reason, socket.timeout)
            or "timed out" in reason_text.lower()
        )
        logger.warning(
            "[SorisaeHub] Flask 서버 연결 실패 (%s → %s): %s",
            engine_type, base_url, exc,
        )
        return _failure_payload(
            engine_type=engine_type,
            status="flask_server_timeout" if is_timeout else "flask_server_unavailable",
            error_code="FLASK_SERVER_TIMEOUT" if is_timeout else "FLASK_SERVER_NETWORK_ERROR",
            error_message=str(exc),
            retryable=True,
            source="flask_proxy",
            extra={"server_url": base_url},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "[SorisaeHub] Flask 프록시 예기치 못한 오류 (%s → %s)",
            engine_type,
            base_url,
        )
        return _failure_payload(
            engine_type=engine_type,
            status="flask_proxy_error",
            error_code="FLASK_PROXY_ERROR",
            error_message=str(exc),
            retryable=True,
            source="flask_proxy",
            extra={"server_url": base_url},
        )


_ENGINE_MODULE_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()

_DEFAULT_ADAPTER_ENTRY_CANDIDATES: tuple[str, ...] = (
    "main",       # 75/120 슬롯이 main을 최상위 진입 함수로 사용 (auto-scan 2026-05-05)
    "run",
    "execute",
    "start",
    "process",
    "handle",
    "run_dashboard",
    "start_server",
    "demo_ethical_gps_system",
)


def _iter_adapter_entry_candidates(
    entry_fn: str,
    adapter_entry_candidates: Optional[Iterable[str]],
) -> list[str]:
    candidates: list[str] = []
    raw_candidates = [entry_fn, *_DEFAULT_ADAPTER_ENTRY_CANDIDATES]
    if adapter_entry_candidates:
        raw_candidates.extend(adapter_entry_candidates)

    for candidate in raw_candidates:
        name = str(candidate or "").strip()
        if not name or name in candidates:
            continue
        candidates.append(name)
    return candidates


def _resolve_module_adapter_fn(
    module: Any,
    entry_fn: str,
    adapter_entry_candidates: Optional[Iterable[str]],
) -> tuple[Optional[Callable[..., Any]], Optional[str], list[str]]:
    candidates = _iter_adapter_entry_candidates(entry_fn, adapter_entry_candidates)
    for name in candidates:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn, name, candidates
    return None, None, candidates


def _invoke_engine_fn(fn: Callable[..., Any], ctx: Dict[str, Any]) -> Any:
    if not ctx:
        return fn()
    try:
        return fn(**ctx)
    except TypeError:
        return fn(ctx)


def _load_engine_module(slot_file: str) -> Any:
    """슬롯 파일을 동적으로 로드해 캐시합니다."""
    with _CACHE_LOCK:
        if slot_file in _ENGINE_MODULE_CACHE:
            return _ENGINE_MODULE_CACHE[slot_file]

        slot_path = _ENGINES_DIR / slot_file
        if not slot_path.exists():
            raise FileNotFoundError(
                f"[SorisaeHub] 슬롯 파일이 없습니다: {slot_path}"
            )

        spec = importlib.util.spec_from_file_location(
            f"sorisae_slot.{slot_file}", slot_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"[SorisaeHub] 슬롯 로드 실패: {slot_file}")

        # 일부 슬롯은 engines120/ 또는 extras/ 헬퍼를 절대 import 하므로
        # 동적 로드 전 검색 경로를 보장해야 로컬 의존성을 해석할 수 있습니다.
        for helper_dir in _iter_helper_paths():
            helper_dir_str = str(helper_dir)
            if helper_dir.exists() and helper_dir_str not in sys.path:
                sys.path.insert(0, helper_dir_str)

        module = importlib.util.module_from_spec(spec)
        sys.modules[f"sorisae_slot.{slot_file}"] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        _ENGINE_MODULE_CACHE[slot_file] = module
        logger.info("[SorisaeHub] 엔진 슬롯 로드 완료: %s", slot_file)
        return module


class SorisaeEngineHub:
    """
    소리새 AI 엔진 중앙 허브.

    사용 예시 (마켓 라우터에서):
        hub = SorisaeEngineHub.get_instance()
        result = hub.dispatch("decision", context={"query": "..."})

    오케스트레이터 훅:
        hub.orchestrator_hook(prompt, context) → str
    """

    _instance: Optional["SorisaeEngineHub"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._registry = SORISAE_ENGINE_REGISTRY.copy()
        logger.info(
            "[SorisaeHub] 컨트롤 타워 초기화 완료. 등록 엔진: %d개",
            len(self._registry),
        )

    @classmethod
    def get_instance(cls) -> "SorisaeEngineHub":
        if cls._instance is not None:
            return cls._instance
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    # ── 공개 API ──────────────────────────────────────────────────

    def list_engines(self) -> Dict[str, str]:
        """등록된 엔진 타입 목록을 반환합니다."""
        return dict(self._registry)

    def is_registered(self, engine_type: str) -> bool:
        return engine_type in self._registry

    def dispatch(
        self,
        engine_type: str,
        context: Optional[Dict[str, Any]] = None,
        entry_fn: str = "main",
        use_module_adapter: bool = False,
        adapter_entry_candidates: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        지정한 소리새 엔진 슬롯을 실행합니다.

        Args:
            engine_type: SORISAE_ENGINE_REGISTRY 에 등록된 엔진 키.
            context: 엔진에 전달할 파라미터 딕셔너리.
            entry_fn: 슬롯 모듈 내 호출할 함수 이름 (기본: "main").
            use_module_adapter: entry_fn 이 없을 때 어댑터 후보 함수를 자동 시도할지 여부.
            adapter_entry_candidates: 추가 어댑터 함수명 후보 목록.

        Returns:
            {"engine": engine_type, "result": ..., "status": "ok"} 형태.
        """
        if engine_type not in self._registry:
            registered = list(self._registry.keys())
            raise ValueError(
                f"[SorisaeHub] 알 수 없는 엔진 타입: '{engine_type}'. "
                f"등록된 타입: {registered}"
            )

        slot_file = self._registry[engine_type]

        # Flask 서버형 슬롯: 독립 컨테이너로 HTTP 프록시
        if slot_file in SORISAE_FLASK_SERVER_MAP:
            return _dispatch_to_flask_server(engine_type, slot_file, context or {})

        try:
            module = _load_engine_module(slot_file)
        except (FileNotFoundError, ImportError) as exc:
            logger.warning("[SorisaeHub] 슬롯 로드 실패 (%s): %s", slot_file, exc)
            return _failure_payload(
                engine_type=engine_type,
                status="fallback",
                error_code="ENGINE_LOAD_ERROR",
                error_message=str(exc),
                retryable=False,
                source="module_loader",
                extra={"slot_file": slot_file},
            )

        ctx = context or {}

        # entry_fn 정합 우선: 요청 함수가 있으면 그대로 호출
        fn: Optional[Callable] = getattr(module, entry_fn, None)
        if fn is None:
            # SORISAE_SLOT_ENTRY_FN_MAP 에서 슬롯별 권장 진입 함수명 조회
            slot_override = _resolve_slot_entry_fn(slot_file)
            if slot_override:
                fn = getattr(module, slot_override, None)
                if fn is not None:
                    try:
                        result = _invoke_engine_fn(fn, ctx)
                        return {
                            "engine": engine_type,
                            "status": "slot_map_ok",
                            "adapter_used": False,
                            "entry_fn": entry_fn,
                            "adapter_entry_fn": slot_override,
                            "result": result,
                        }
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "[SorisaeHub] slot_map 실행 오류 (%s/%s): %s",
                            engine_type,
                            slot_override,
                            exc,
                        )
                        return _failure_payload(
                            engine_type=engine_type,
                            status="error",
                            error_code="ENGINE_RUNTIME_ERROR",
                            error_message=str(exc),
                            retryable=False,
                            source="engine_runtime",
                            extra={
                                "entry_fn": entry_fn,
                                "adapter_entry_fn": slot_override,
                            },
                        )
            if use_module_adapter:
                adapter_fn, adapter_fn_name, candidates = _resolve_module_adapter_fn(
                    module=module,
                    entry_fn=entry_fn,
                    adapter_entry_candidates=adapter_entry_candidates,
                )
                if adapter_fn is not None and adapter_fn_name is not None:
                    try:
                        result = _invoke_engine_fn(adapter_fn, ctx)
                        return {
                            "engine": engine_type,
                            "status": "adapter_ok",
                            "adapter_used": True,
                            "entry_fn": entry_fn,
                            "adapter_entry_fn": adapter_fn_name,
                            "result": result,
                        }
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "[SorisaeHub] module adapter 실행 오류 (%s/%s): %s",
                            engine_type,
                            adapter_fn_name,
                            exc,
                        )
                        return _failure_payload(
                            engine_type=engine_type,
                            status="adapter_error",
                            error_code="ENGINE_ADAPTER_RUNTIME_ERROR",
                            error_message=str(exc),
                            retryable=False,
                            source="engine_adapter",
                            extra={
                                "adapter_used": True,
                                "entry_fn": entry_fn,
                                "adapter_entry_fn": adapter_fn_name,
                                "adapter_candidates": candidates,
                            },
                        )

            return {
                "engine": engine_type,
                "status": "module_only",
                "adapter_used": False,
                "module": getattr(module, "__name__", slot_file),
                "entry_fn": entry_fn,
                "adapter_candidates": _iter_adapter_entry_candidates(
                    entry_fn,
                    adapter_entry_candidates,
                ),
                "result": None,
            }

        try:
            result = _invoke_engine_fn(fn, ctx)
            return {"engine": engine_type, "status": "ok", "result": result}
        except Exception as exc:  # noqa: BLE001
            logger.error("[SorisaeHub] 엔진 실행 오류 (%s): %s", engine_type, exc)
            return _failure_payload(
                engine_type=engine_type,
                status="error",
                error_code="ENGINE_RUNTIME_ERROR",
                error_message=str(exc),
                retryable=False,
                source="engine_runtime",
                extra={"entry_fn": entry_fn},
            )

    def orchestrator_hook(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        LLM 오케스트레이터에서 호출하는 소리새 AI 훅.

        소리새 의사결정 엔진(DecisionEngine)으로 프롬프트를 분석해
        라우팅 힌트를 문자열로 반환합니다.
        Fallback: 빈 문자열 반환 (오케스트레이터가 기존 LLM 경로 사용).
        """
        try:
            slot_file = self._registry.get("decision", "")
            if not slot_file:
                return ""

            module = _load_engine_module(slot_file)
            engine_cls = getattr(module, "DecisionEngine", None)
            if engine_cls is None:
                return ""

            engine = engine_cls()
            hint = getattr(engine, "analyze_prompt", None)
            if hint:
                return str(hint(prompt, **(context or {})))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[SorisaeHub] orchestrator_hook fallback: %s", exc)
        return ""

    def register_engine(self, engine_type: str, slot_file: str) -> None:
        """
        런타임에 새 엔진 슬롯을 등록합니다.
        새 마켓 상품 라우터 빌더에서 호출하세요.

        Args:
            engine_type: 식별 키 (예: "my_product")
            slot_file:   engines120/ 아래 슬롯 파일명 (예: "slot121_my_product.py")
        """
        if engine_type in self._registry:
            logger.warning(
                "[SorisaeHub] 이미 등록된 엔진 타입 덮어씀: %s", engine_type
            )
        self._registry[engine_type] = slot_file
        logger.info(
            "[SorisaeHub] 엔진 등록: %s → %s", engine_type, slot_file
        )
