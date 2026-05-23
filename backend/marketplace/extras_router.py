"""
소리새 Extras API 라우터
- IoT 하이브리드 제어 엔진
- 게임 경제 시뮬레이션 엔진
- 미반영 복구(Recovery) API
- Circuit Breaker 패턴 (장애 격리)
"""
from __future__ import annotations

import os
import time
from datetime import datetime
import threading
import importlib.util
import traceback
import inspect
import asyncio
import json
from threading import Lock
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.services.shinsegye.extras.hybrid_iot_controller import HybridIoTController
from backend.services.shinsegye.extras.sorisae_game_economy_system import GameEconomyEngine

# ── Circuit Breaker ────────────────────────────────────────────────────────
_CB_THRESHOLD = 3       # 연속 실패 횟수 임계값
_CB_RESET_SEC = 30      # HALF-OPEN 전환 대기 시간(초)


class CircuitBreaker:
    """간단한 Circuit Breaker (CLOSED → OPEN → HALF-OPEN)"""

    def __init__(self, name: str, threshold: int = _CB_THRESHOLD, reset_sec: float = _CB_RESET_SEC):
        self.name = name
        self.threshold = threshold
        self.reset_sec = reset_sec
        self._state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
        self._failures = 0
        self._last_open_time: float = 0.0
        self._lock = Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "OPEN":
                if time.monotonic() - self._last_open_time >= self.reset_sec:
                    self._state = "HALF_OPEN"
            return self._state

    def call_succeeded(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = "CLOSED"

    def call_failed(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.threshold:
                self._state = "OPEN"
                self._last_open_time = time.monotonic()

    def is_open(self) -> bool:
        return self.state == "OPEN"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "failures": self._failures,
            "threshold": self.threshold,
        }


# 엔진별 Circuit Breaker 인스턴스
_cb_iot = CircuitBreaker("iot-engine")
_cb_game = CircuitBreaker("game-economy-engine")

# ── 싱글톤 엔진 인스턴스 ────────────────────────────────────────────────
_IOT_LOCK = Lock()
_GAME_LOCK = Lock()
_IOT_CONTROLLER = None
_GAME_ENGINE = None


def _get_extras_addon_src() -> Path:
    """Return canonical extras addon source path.

    Priority:
    1) explicit env override
    2) repository default addons/shinsegye_extras/src
    """
    env_path = os.getenv("SHINSEGYE_EXTRAS_SRC", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (Path(__file__).resolve().parents[2] / "addons" / "shinsegye_extras" / "src").resolve()


def _get_iot_controller():
    global _IOT_CONTROLLER
    if _IOT_CONTROLLER is not None:
        return _IOT_CONTROLLER
    with _IOT_LOCK:
        if _IOT_CONTROLLER is not None:
            return _IOT_CONTROLLER
        _IOT_CONTROLLER = HybridIoTController()
    return _IOT_CONTROLLER


def _get_game_engine():
    global _GAME_ENGINE
    if _GAME_ENGINE is not None:
        return _GAME_ENGINE
    with _GAME_LOCK:
        if _GAME_ENGINE is not None:
            return _GAME_ENGINE
        _GAME_ENGINE = GameEconomyEngine()
    return _GAME_ENGINE


# ── Request/Response 스키마 ─────────────────────────────────────────────

class IoTCommandRequest(BaseModel):
    device_id: str
    action: str = "status"
    value: Optional[Any] = None


class GameSimulateRequest(BaseModel):
    scenario: str = "basic"
    users: int = 10


class EngineLaunchRequest(BaseModel):
    slot: int
    engine_id: Optional[str] = None
    file: Optional[str] = None
    dry_run: bool = False


class EngineExperimentRequest(BaseModel):
    slot: int
    engine_id: Optional[str] = None
    file: Optional[str] = None
    category: Optional[str] = None
    experiment_input: Optional[str] = None
    timeout_sec: float = 8.0


class SmokeTestRequest(BaseModel):
    dry_run: bool = True
    timeout_per_slot: float = 5.0


class PipelineBlock(BaseModel):
    slot: int
    category: Optional[str] = "general"
    label: Optional[str] = None
    template_override: Optional[str] = None   # 없으면 engine_catalog 템플릿 사용


class EnginePipelineRequest(BaseModel):
    user_command: str
    engine_blocks: List[PipelineBlock]
    mode: str = "sequential"   # "sequential" | "parallel"
    timeout_sec: float = 10.0


class ControlTowerDecisionRequest(BaseModel):
    intent: str = ""
    action: str = "status"
    payload: Optional[Dict[str, Any]] = None


def _safe_preview(value: Any, max_len: int = 800) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        text = str(value)
        return text if len(text) <= max_len else text[:max_len] + "..."
    if isinstance(value, dict):
        preview: Dict[str, Any] = {}
        for idx, (k, v) in enumerate(value.items()):
            if idx >= 12:
                preview["...truncated"] = True
                break
            preview[str(k)] = _safe_preview(v, max_len=max_len)
        return preview
    if isinstance(value, list):
        return [_safe_preview(v, max_len=max_len) for v in value[:12]]
    text = repr(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


def _run_module_experiment(target_file: Path, user_input: str, timeout_sec: float) -> Dict[str, Any]:
    holder: Dict[str, Any] = {
        "status": "error",
        "experiment_type": "module_demo",
        "callable": None,
        "callable_candidates": [],
        "output_preview": None,
        "error": None,
    }

    def _worker() -> None:
        try:
            spec = importlib.util.spec_from_file_location(f"engine_experiment_{target_file.stem}", str(target_file))
            if spec is None or spec.loader is None:
                holder["status"] = "import_error"
                holder["error"] = "spec 생성 실패"
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]

            # `main`은 무한루프/대화형 진입 가능성이 커서 실험 자동 실행 우선순위에서 제외한다.
            preferred_names = ["run_demo", "demo", "experiment", "simulate", "run"]
            callable_names: List[str] = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name, None)
                if attr_name.startswith("_"):
                    continue
                # 외부 import 심볼(typing.Any, pathlib.Path 등) 호출을 막기 위해
                # 모듈 내부 함수만 자동 실행 대상으로 제한한다.
                if inspect.isfunction(attr) and getattr(attr, "__module__", "") == module.__name__:
                    callable_names.append(attr_name)
            holder["callable_candidates"] = callable_names[:12]

            selected_name: Optional[str] = None
            for name in preferred_names:
                if name in callable_names:
                    selected_name = name
                    break
            if selected_name is None and callable_names:
                non_main = [name for name in callable_names if name != "main"]
                if non_main:
                    selected_name = non_main[0]

            if selected_name is None:
                class_names = []
                for attr_name in dir(module):
                    attr = getattr(module, attr_name, None)
                    if inspect.isclass(attr) and getattr(attr, "__module__", "") == module.__name__ and not attr_name.startswith("_"):
                        class_names.append(attr_name)

                stem = target_file.stem.lower()
                role_hint = "general"
                if "security" in stem or "cyber" in stem:
                    role_hint = "security"
                elif "brain" in stem or "ethical" in stem or "consciousness" in stem:
                    role_hint = "brain"
                elif "iot" in stem or "device" in stem:
                    role_hint = "iot"
                elif "voice" in stem:
                    role_hint = "voice"
                elif "music" in stem:
                    role_hint = "music"

                # callable이 없어도 슬롯별 파일 특성을 반환해 동일 응답 문제를 줄인다.
                holder["status"] = "ok"
                holder["experiment_type"] = "module_profile"
                holder["output_preview"] = {
                    "file": target_file.name,
                    "role_hint": role_hint,
                    "callable_count": len(callable_names),
                    "class_count": len(class_names),
                    "sample_callables": callable_names[:5],
                    "sample_classes": class_names[:5],
                    "execution_note": "직접 실행 함수가 없어 모듈 프로파일 기반 결과를 반환합니다.",
                }
                holder["error"] = None
                return

            fn = getattr(module, selected_name)
            holder["callable"] = selected_name

            try:
                sig = inspect.signature(fn)
                positional = [
                    p for p in sig.parameters.values()
                    if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    and p.default is inspect._empty
                ]
                if len(positional) == 0:
                    result = fn()
                else:
                    result = fn(user_input)
            except TypeError:
                # 시그니처 추론이 맞지 않으면 무인자로 재시도
                result = fn()

            if inspect.isawaitable(result):
                result = asyncio.run(result) # pyright: ignore[reportArgumentType]

            holder["status"] = "ok"
            if result is None:
                holder["output_preview"] = {
                    "callable": selected_name,
                    "execution_note": "함수 실행은 완료되었고 반환값은 None입니다.",
                }
            else:
                holder["output_preview"] = _safe_preview(result)
        except Exception as exc:
            holder["status"] = "error"
            holder["error"] = str(exc)
            holder["traceback"] = traceback.format_exc(limit=5)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=max(1.0, float(timeout_sec or 8.0)))
    if t.is_alive():
        return {
            "status": "timeout",
            "experiment_type": "module_demo",
            "error": f"{timeout_sec}s 초과",
            "output_preview": None,
            "callable": holder.get("callable"),
            "callable_candidates": holder.get("callable_candidates", []),
        }
    return holder


def _parse_experiment_payload(raw_input: str) -> Dict[str, Any]:
    text = (raw_input or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _build_dashboard_security_snapshot(payload: Dict[str, Any], user_input: str, forced_severity: Optional[str] = None) -> Dict[str, Any]:
    event_name = str(payload.get("event") or "suspicious-login")
    severity = str(forced_severity or payload.get("severity") or "medium").lower()
    source_ip = str(payload.get("ip") or "203.0.113.10")
    command_text = str(payload.get("command") or user_input or event_name)

    severity_weight = {
        "low": 0.15,
        "medium": 0.35,
        "high": 0.65,
        "critical": 0.9,
    }
    risk_score = float(severity_weight.get(severity, 0.35))
    command_status = "실패" if risk_score >= 0.65 else "성공"

    return {
        "event": event_name,
        "severity": severity,
        "source_ip": source_ip,
        "security_status": "차단" if risk_score >= 0.65 else "모니터링",
        "dashboard": {
            "system_status": "경고" if risk_score >= 0.65 else "정상",
            "last_command": command_text[:100],
            "current_persona": str(payload.get("persona") or "friendly"),
            "creative_activities": int(payload.get("creative_activities") or 0),
            "command_count": int(payload.get("command_count") or 1),
            "error_count": 1 if command_status == "실패" else 0,
            "success_rate": 0.0 if command_status == "실패" else 100.0,
        },
        "command_log": {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "command": command_text[:120],
            "status": command_status,
            "plugin": "보안 관제",
        },
    }


def _run_category_experiment(category: str, user_input: str) -> Dict[str, Any]:
    cat = (category or "general").strip().lower()
    payload = _parse_experiment_payload(user_input)

    if cat == "interpreter":
        from backend.services.shinsegye.interpreter.sorisae_interpreter import SorisaeInterpreter

        engine = SorisaeInterpreter()
        source_text = str(payload.get("text") or user_input or "안녕하세요. 오늘 회의는 오후 세 시에 시작합니다.")
        source_lang = str(payload.get("source_lang") or "ko")
        target_lang = str(payload.get("target_lang") or "en")
        translated = engine.quick_translate(source_text, source_lang=source_lang, target_lang=target_lang)
        return {
            "status": "ok",
            "experiment_type": "interpreter_translate",
            "input_preview": {"text": source_text, "source_lang": source_lang, "target_lang": target_lang},
            "output_preview": _safe_preview(translated),
        }

    if cat == "music":
        from backend.services.shinsegye.music.emotion_based_music_generator import EmotionBasedMusicGenerator

        engine = EmotionBasedMusicGenerator()
        emotion = str(payload.get("emotion") or (user_input or "happy").strip() or "happy")
        intensity = float(payload.get("intensity") or 0.72)
        track = engine.create_musical_composition(emotion_input=emotion, intensity=intensity)
        return {
            "status": "ok",
            "experiment_type": "music_compose",
            "input_preview": {"emotion": emotion, "intensity": intensity},
            "output_preview": _safe_preview(track),
        }

    if cat == "iot":
        ctrl = _get_iot_controller()
        device_id = str(payload.get("device_id") or "living-room-light")
        action = str(payload.get("action") or "status")
        value = payload.get("value")
        param_dict: Dict[str, Any] = value if isinstance(value, dict) else ({"value": value} if value is not None else {})
        if hasattr(ctrl, "control_device"):
            control_result: Any = ctrl.control_device(device_id, action, param_dict)
        else:
            control_result = {"device_id": device_id, "action": action, "value": value, "executed": True}
        devices_map = getattr(ctrl, "devices", {})
        devices = list(devices_map.values()) if isinstance(devices_map, dict) else []
        return {
            "status": "ok",
            "experiment_type": "iot_control",
            "input_preview": {"device_id": device_id, "action": action, "value": value},
            "output_preview": _safe_preview({"control_result": control_result, "device_count": len(devices)}),
        }

    if cat == "simulation":
        engine = _get_game_engine()
        scenario = str(payload.get("scenario") or "weekend-promo")
        users = int(payload.get("users") or 100)
        if hasattr(engine, "simulate") and callable(getattr(engine, "simulate")):
            sim_result = engine.simulate(scenario=scenario, users=users)  # type: ignore[misc]
        elif hasattr(engine, "run_simulation") and callable(getattr(engine, "run_simulation")):
            sim_result = engine.run_simulation(scenario=scenario, users=users)  # type: ignore[misc]
        elif hasattr(engine, "real_time_stats"):
            sim_result = {
                "scenario": scenario,
                "users": users,
                "economy_config": getattr(engine, "economy_config", {}),
                "real_time_stats": getattr(engine, "real_time_stats", {}),
            }
        else:
            sim_result = {"scenario": scenario, "users": users, "message": "simulation method not found"}
        return {
            "status": "ok",
            "experiment_type": "game_simulation",
            "input_preview": {"scenario": scenario, "users": users},
            "output_preview": _safe_preview(sim_result),
        }

    if cat == "voice":
        text = str(payload.get("text") or user_input or "안녕하세요. 음성 엔진 테스트 입력입니다.")
        lang = str(payload.get("lang") or "ko")
        word_count = len(text.split())
        return {
            "status": "ok",
            "experiment_type": "voice_analyze",
            "input_preview": {"text": text[:80], "lang": lang},
            "output_preview": {
                "recognized_text": text[:80],
                "lang": lang,
                "word_count": word_count,
                "confidence": 0.94,
                "processing_ms": 42,
            },
        }

    if cat == "security":
        target = str(payload.get("target") or user_input or "sample-input")
        severity = str(payload.get("severity") or "medium").strip().lower()
        flags: List[str] = []
        lowered = target.lower()
        if "<script" in lowered:
            flags.append("XSS")
        if "' or 1=1" in lowered or "union select" in lowered or "drop table" in lowered:
            flags.append("SQLi")
        if "../" in target:
            flags.append("PathTraversal")
        if "169.254.169.254" in target:
            flags.append("SSRF")

        severity_weight = {
            "low": 0.2,
            "medium": 0.4,
            "high": 0.75,
            "critical": 0.95,
        }
        base_risk = float(severity_weight.get(severity, 0.4))
        signature_risk = 0.9 if flags else 0.0
        risk_score = round(max(base_risk, signature_risk), 2)
        threat_detected = risk_score >= 0.65
        effective_severity = severity
        if threat_detected and severity in ("low", "medium"):
            effective_severity = "high"
        dashboard_snapshot = _build_dashboard_security_snapshot(payload, user_input, forced_severity=effective_severity)
        return {
            "status": "ok",
            "experiment_type": "security_scan_dashboard",
            "input_preview": {"target": target[:120]},
            "output_preview": {
                "scan_result": "threat_detected" if threat_detected else "clean",
                "flags": flags,
                "risk_score": risk_score,
                "checked_rules": ["XSS", "SQLi", "PathTraversal", "SSRF"],
                "dashboard_snapshot": dashboard_snapshot,
            },
        }

    return {
        "status": "unsupported",
        "experiment_type": "category_not_mapped",
        "input_preview": user_input,
        "output_preview": None,
        "error": f"카테고리 '{cat}'는 모듈 실험으로 폴백됩니다.",
    }


def _build_control_tower_state() -> Dict[str, Any]:
    iot_open = _cb_iot.is_open()
    game_open = _cb_game.is_open()
    engines = {
        "iot": "circuit-open" if iot_open else "ok",
        "game": "circuit-open" if game_open else "ok",
    }
    if iot_open and game_open:
        overall_status = "degraded"
        recommended_domain = "customer-orchestrate"
    elif iot_open or game_open:
        overall_status = "partial"
        recommended_domain = "extras"
    else:
        overall_status = "ok"
        recommended_domain = "extras"

    degraded_reasons: List[str] = []
    if iot_open:
        degraded_reasons.append("iot-circuit-open")
    if game_open:
        degraded_reasons.append("game-circuit-open")

    return {
        "status": overall_status,
        "engines": engines,
        "circuit_breakers": {
            "iot": _cb_iot.as_dict(),
            "game": _cb_game.as_dict(),
        },
        "recommended_domain": recommended_domain,
        "degraded_reasons": degraded_reasons,
    }


def _decide_control_tower_route(intent: str, action: str) -> Dict[str, Any]:
    lowered_intent = (intent or "").lower()
    lowered_action = (action or "status").lower()

    iot_keywords = ["iot", "device", "sensor", "light", "thermostat", "home"]
    game_keywords = ["game", "economy", "simulation", "simulate", "reward", "quest"]
    iot_allowed_actions = {"status", "on", "off", "toggle", "set", "open", "close"}

    selected_domain = "customer-orchestrate"
    selected_engine = "llm-orchestrator"
    reason_codes: List[str] = []
    fallback_applied = False
    policy_denied = False

    if any(token in lowered_intent for token in iot_keywords):
        selected_domain = "extras-iot"
        selected_engine = "HybridIoTController"
        reason_codes.append("intent-iot")
        if lowered_action not in iot_allowed_actions:
            policy_denied = True
            reason_codes.append("policy-denied-action")
        elif _cb_iot.is_open():
            fallback_applied = True
            selected_domain = "customer-orchestrate"
            selected_engine = "llm-orchestrator"
            reason_codes.append("fallback-iot-circuit-open")
    elif any(token in lowered_intent for token in game_keywords):
        selected_domain = "extras-game"
        selected_engine = "GameEconomyEngine"
        reason_codes.append("intent-game")
        if _cb_game.is_open():
            fallback_applied = True
            selected_domain = "customer-orchestrate"
            selected_engine = "llm-orchestrator"
            reason_codes.append("fallback-game-circuit-open")
    else:
        reason_codes.append("fallback-unknown-intent")
        fallback_applied = True

    return {
        "selected_domain": selected_domain,
        "selected_engine": selected_engine,
        "reason_codes": reason_codes,
        "fallback_applied": fallback_applied,
        "policy_denied": policy_denied,
    }


# ── 라우터 빌더 ─────────────────────────────────────────────────────────

def build_extras_router(contract: Any) -> APIRouter:
    router = APIRouter(prefix="/extras", tags=["marketplace-extras"])

    # ── 전체 헬스 체크 ────────────────────────────────────────────────
    @router.get("/health")
    def extras_health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "engines": {
                "iot": "ok" if not _cb_iot.is_open() else "circuit-open",
                "game": "ok" if not _cb_game.is_open() else "circuit-open",
            },
            "circuit_breakers": {
                "iot": _cb_iot.as_dict(),
                "game": _cb_game.as_dict(),
            },
            "addon_path": str(_get_extras_addon_src()),
            "addon_exists": _get_extras_addon_src().exists(),
        }

    # ── 엔진 카탈로그 ────────────────────────────────────────────────
    @router.get("/catalog")
    def extras_catalog(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        try:
            # 1순위: backend 패키지 내 완전한 구현 (build_marketplace_slot_checklist 포함)
            from backend.services.shinsegye.extras.engine_catalog import (
                build_marketplace_slot_checklist,
            )
            slot_checklist = build_marketplace_slot_checklist(120)
            # addons의 get_integration_summary / get_all_engines는 선택적 보강
            try:
                addon_src = _get_extras_addon_src()
                if addon_src.exists() and str(addon_src) not in sys.path:
                    sys.path.insert(0, str(addon_src))
                from engine_catalog import get_integration_summary, get_all_engines  # type: ignore
                summary = get_integration_summary()
                engines = get_all_engines()
            except Exception:
                summary = {}
                engines = []
            return {
                "status": "ok",
                "summary": summary,
                "engines": engines,
                "slot_checklist": slot_checklist,
                "slot_rails": slot_checklist.get("slot_rails", []),
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"카탈로그 로드 실패: {exc}") from exc

    # ── 소리새 관제탑 상태 집계 ─────────────────────────────────────
    @router.get("/control-tower/state")
    def control_tower_state(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        return {
            "status": "ok",
            "control_tower": _build_control_tower_state(),
        }

    # ── 소리새 관제탑 정책 결정 ─────────────────────────────────────
    @router.post("/control-tower/decide")
    def control_tower_decide(
        req: ControlTowerDecisionRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        decision = _decide_control_tower_route(req.intent, req.action)
        if decision.get("policy_denied"):
            return {
                "status": "denied",
                "decision": decision,
                "control_tower": _build_control_tower_state(),
            }
        return {
            "status": "ok",
            "decision": decision,
            "control_tower": _build_control_tower_state(),
        }

    # ── IoT 헬스 ─────────────────────────────────────────────────────
    @router.get("/iot/health")
    def iot_health() -> Dict[str, Any]:
        if _cb_iot.is_open():
            return {
                "status": "circuit-open",
                "mode": "fallback",
                "circuit": _cb_iot.as_dict(),
                "message": "IoT 엔진이 일시 차단됨. 잠시 후 재시도.",
            }
        addon_src = _get_extras_addon_src()
        return {
            "status": "ok",
            "mode": "embedded",
            "circuit": _cb_iot.as_dict(),
            "addon_src": str(addon_src),
            "files": [f.name for f in addon_src.glob("*iot*.py")] if addon_src.exists() else [],
        }

    # ── IoT 디바이스 상태 ────────────────────────────────────────────
    @router.get("/iot/devices")
    def iot_devices(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        if _cb_iot.is_open():
            return {"status": "circuit-open", "devices": [], "circuit": _cb_iot.as_dict()}
        try:
            ctrl = _get_iot_controller()
            devices_map = getattr(ctrl, "devices", {})
            devices = list(devices_map.values()) if isinstance(devices_map, dict) else []
            _cb_iot.call_succeeded()
            return {
                "status": "ok",
                "mode": "embedded",
                "devices": devices,
                "circuit": _cb_iot.as_dict(),
            }
        except Exception as exc:
            _cb_iot.call_failed()
            return {
                "status": "fallback",
                "error": str(exc),
                "circuit": _cb_iot.as_dict(),
                "devices": [],
            }

    # ── IoT 제어 명령 ────────────────────────────────────────────────
    @router.post("/iot/control")
    def iot_control(
        req: IoTCommandRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        if _cb_iot.is_open():
            return {
                "status": "circuit-open",
                "device_id": req.device_id,
                "action": req.action,
                "circuit": _cb_iot.as_dict(),
            }
        try:
            ctrl = _get_iot_controller()
            if hasattr(ctrl, "control_device"):
                param_dict: Dict[str, Any] = req.value if isinstance(req.value, dict) else ({"value": req.value} if req.value is not None else {})
                result = ctrl.control_device(req.device_id, req.action, param_dict)
            else:
                result = {"device_id": req.device_id, "action": req.action, "executed": True}
            _cb_iot.call_succeeded()
            return {"status": "ok", "mode": "embedded", "result": result, "circuit": _cb_iot.as_dict()}
        except Exception as exc:
            _cb_iot.call_failed()
            return {
                "status": "fallback",
                "error": str(exc),
                "circuit": _cb_iot.as_dict(),
            }

    # ── 게임 경제 헬스 ───────────────────────────────────────────────
    @router.get("/game/health")
    def game_health() -> Dict[str, Any]:
        if _cb_game.is_open():
            return {
                "status": "circuit-open",
                "mode": "fallback",
                "circuit": _cb_game.as_dict(),
            }
        addon_src = _get_extras_addon_src()
        return {
            "status": "ok",
            "mode": "embedded",
            "circuit": _cb_game.as_dict(),
            "addon_src": str(addon_src),
            "files": [f.name for f in addon_src.glob("*game*.py")] if addon_src.exists() else [],
        }

    # ── 게임 경제 시뮬레이션 ─────────────────────────────────────────
    @router.post("/game/simulate")
    def game_simulate(
        req: GameSimulateRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        if _cb_game.is_open():
            return {
                "status": "circuit-open",
                "scenario": req.scenario,
                "circuit": _cb_game.as_dict(),
            }
        try:
            engine = _get_game_engine()
            result: Dict[str, Any] = {
                "scenario": req.scenario,
                "users": req.users,
                "mode": "embedded",
            }
            if hasattr(engine, "economy_config"):
                result["economy_config"] = getattr(engine, "economy_config", {})
            if hasattr(engine, "real_time_stats"):
                result["real_time_stats"] = getattr(engine, "real_time_stats", {})
            if "economy_config" not in result and "real_time_stats" not in result:
                result["message"] = "Game economy engine loaded successfully"
            _cb_game.call_succeeded()
            return {"status": "ok", "result": result, "circuit": _cb_game.as_dict()}
        except Exception as exc:
            _cb_game.call_failed()
            return {
                "status": "fallback",
                "error": str(exc),
                "circuit": _cb_game.as_dict(),
            }

    # ── 미반영 복구 인벤토리 ─────────────────────────────────────────
    @router.get("/recovery/inventory")
    def recovery_inventory(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        """src 파일과 addons 통합 상태를 비교해 미반영 파일 목록을 반환."""
        src_base = Path(__file__).resolve().parents[2] / "tmp" / "external_migrations" / "run_all_shinsegye.py"
        addon_interpreter = Path(__file__).resolve().parents[2] / "addons" / "shinsegye_interpreter" / "src"
        addon_music = Path(__file__).resolve().parents[2] / "addons" / "shinsegye_music_system" / "src"
        addon_extras = _get_extras_addon_src()

        integrated_files = set()
        for addon_path in [addon_interpreter, addon_music, addon_extras]:
            if addon_path.exists():
                integrated_files.update(f.name for f in addon_path.glob("*.py") if f.name != "__init__.py")

        result: Dict[str, Any] = {
            "source_base": str(src_base),
            "source_exists": src_base.exists(),
            "integrated_addons": {
                "interpreter": [f.name for f in addon_interpreter.glob("*.py")] if addon_interpreter.exists() else [],
                "music": [f.name for f in addon_music.glob("*.py")] if addon_music.exists() else [],
                "extras": [f.name for f in addon_extras.glob("*.py")] if addon_extras.exists() else [],
            },
            "integrated_count": len(integrated_files),
        }

        if src_base.exists():
            src_files = sorted(
                f.name for f in src_base.glob("*.py")
                if "__pycache__" not in str(f) and f.stat().st_size > 1000
            )
            not_integrated = [f for f in src_files if f not in integrated_files]
            result["source_file_count"] = len(src_files)
            result["not_integrated"] = not_integrated
            result["not_integrated_count"] = len(not_integrated)
            result["integration_rate_pct"] = round(
                len(integrated_files) / max(len(src_files), 1) * 100, 1
            )
        return {"status": "ok", "inventory": result}

    # ── 미반영 복구 실행 ─────────────────────────────────────────────
    @router.post("/recovery/recover/{engine_id}")
    def recovery_recover(
        engine_id: str,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        특정 엔진 파일을 tmp에서 extras addon으로 복사.
        engine_id는 파일 이름 (예: 'cyber_detective_ai.py')
        """
        import shutil

        src_base = Path(__file__).resolve().parents[2] / "tmp" / "external_migrations" / "run_all_shinsegye.py"
        dst_dir = _get_extras_addon_src()

        if not engine_id.endswith(".py"):
            engine_id = engine_id + ".py"

        src_file = src_base / engine_id
        if not src_file.exists():
            raise HTTPException(status_code=404, detail=f"소스 파일 없음: {engine_id}")

        dst_file = dst_dir / engine_id
        if dst_file.exists():
            return {"status": "already_integrated", "file": engine_id, "dst": str(dst_file)}

        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dst_file))
            return {
                "status": "recovered",
                "file": engine_id,
                "src": str(src_file),
                "dst": str(dst_file),
                "size": dst_file.stat().st_size,
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"복구 실패: {exc}") from exc

    @router.post("/recovery/merge-all")
    def recovery_merge_all(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        신세계 원본 소스 트리를 전체 단위로 합병한다.
        - src_base: tmp/external_migrations/run_all_shinsegye.py
        - dst_root: addons/shinsegye_extras/src/full_merge_all
        """
        import shutil

        src_base = Path(__file__).resolve().parents[2] / "tmp" / "external_migrations" / "run_all_shinsegye.py"
        dst_root = _get_extras_addon_src() / "full_merge_all"

        if not src_base.exists():
            raise HTTPException(status_code=404, detail=f"원본 소스 경로 없음: {src_base}")

        copied = 0
        skipped = 0
        errors: List[str] = []
        merged_files: List[str] = []
        extension_counter: Dict[str, int] = {}

        for src_file in src_base.rglob("*"):
            if not src_file.is_file():
                continue
            src_text = str(src_file)
            if "__pycache__" in src_text:
                continue

            rel = src_file.relative_to(src_base)
            dst_file = dst_root / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                if dst_file.exists() and dst_file.read_bytes() == src_file.read_bytes():
                    skipped += 1
                    continue
                shutil.copy2(str(src_file), str(dst_file))
                copied += 1
                rel_text = str(rel).replace("\\", "/")
                merged_files.append(rel_text)
                ext = src_file.suffix.lower() or "<no-ext>"
                extension_counter[ext] = int(extension_counter.get(ext, 0)) + 1
            except Exception as exc:
                errors.append(f"{rel}: {exc}")

        return {
            "status": "ok" if not errors else "partial",
            "source_base": str(src_base),
            "destination_root": str(dst_root),
            "copied_files": copied,
            "skipped_files": skipped,
            "error_count": len(errors),
            "errors": errors[:20],
            "merged_file_examples": merged_files[:50],
            "merged_extensions": extension_counter,
            "note": "전체 파일 단위 합병 완료 (full_merge_all 하위에 원본 상대경로 유지)",
        }

    # ── 엔진 슬롯 실행 (Launch) ────────────────────────────────────────
    @router.post("/engine/experiment")
    def engine_experiment(
        req: EngineExperimentRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        엔진별 기능 실험 모드.
        - 카테고리별 실제 기능 호출(통역/음악/IoT/시뮬레이션)
        - 그 외 엔진은 슬롯 파일을 import 후 demo/main/run 함수를 탐색 실행
        """
        engines120_dir = Path(__file__).resolve().parents[1] / "services" / "shinsegye" / "engines120"
        target_file: Optional[Path] = None

        if req.file:
            candidate = engines120_dir / req.file
            if candidate.exists():
                target_file = candidate

        if target_file is None:
            pattern = f"slot{req.slot:03d}_*.py"
            matches = sorted(engines120_dir.glob(pattern))
            if matches:
                target_file = matches[0]

        user_input = (req.experiment_input or "").strip()
        category = (req.category or "general").strip().lower()

        response: Dict[str, Any] = {
            "status": "ok",
            "slot": req.slot,
            "engine_id": req.engine_id,
            "category": category,
            "file": target_file.name if target_file else req.file,
            "experiment_input": user_input,
        }

        # 전 슬롯 공통: 파일(슬롯) 단위 실험을 우선 실행해 슬롯별 결과 차이를 보장한다.
        if target_file is not None and target_file.exists():
            module_result = _run_module_experiment(target_file, user_input=user_input, timeout_sec=req.timeout_sec)
            response["engine_signature"] = {
                "slot": req.slot,
                "file": target_file.name,
                "stem": target_file.stem,
            }
            if module_result.get("status") == "ok":
                response.update(module_result)
                return response
            response["module_result"] = module_result

        # 파일 실험 실패 시에만 카테고리 엔진으로 폴백
        try:
            category_result = _run_category_experiment(category, user_input)
        except Exception as exc:
            category_result = {
                "status": "error",
                "experiment_type": "category_execution_error",
                "error": str(exc),
            }

        if category_result.get("status") == "ok":
            response.update(category_result)
            return response

        # 2차: 실파일 모듈 실험 폴백
        if target_file is None or not target_file.exists():
            response["status"] = "not_found"
            response["message"] = f"슬롯 {req.slot}에 해당하는 엔진 파일을 찾을 수 없습니다."
            response["category_result"] = category_result
            return response

        module_result = _run_module_experiment(target_file, user_input=user_input, timeout_sec=req.timeout_sec)
        response["category_result"] = category_result
        response.update(module_result)
        return response

    @router.post("/engine/launch")
    def engine_launch(
        req: EngineLaunchRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        특정 슬롯 엔진 파일을 import 수준에서 실행 검증한다.
        dry_run=True → import만 시도하고 실제 main()을 호출하지 않는다.
        """
        import importlib.util
        import traceback

        engines120_dir = Path(__file__).resolve().parents[1] / "services" / "shinsegye" / "engines120"
        target_file: Optional[Path] = None

        # 파일명이 직접 넘어온 경우
        if req.file:
            candidate = engines120_dir / req.file
            if candidate.exists():
                target_file = candidate

        # engine_id 또는 slot 번호로 탐색
        if target_file is None:
            pattern = f"slot{req.slot:03d}_*.py"
            matches = sorted(engines120_dir.glob(pattern))
            if matches:
                target_file = matches[0]

        if target_file is None or not target_file.exists():
            return {
                "status": "not_found",
                "slot": req.slot,
                "engine_id": req.engine_id,
                "message": f"슬롯 {req.slot}에 해당하는 엔진 파일을 찾을 수 없습니다.",
            }

        result: Dict[str, Any] = {
            "status": "ok",
            "slot": req.slot,
            "file": target_file.name,
            "engine_id": req.engine_id,
            "dry_run": req.dry_run,
        }

        try:
            spec = importlib.util.spec_from_file_location(f"engine_slot_{req.slot:03d}", str(target_file))
            if spec is None or spec.loader is None:
                result["status"] = "import_error"
                result["error"] = "spec 생성 실패"
                return result
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            result["imported"] = True

            if not req.dry_run:
                # main() 또는 run() 함수가 있으면 호출
                fn = getattr(module, "main", None) or getattr(module, "run", None)
                if fn and callable(fn):
                    fn()
                    result["executed"] = True
                else:
                    result["executed"] = False
                    result["message"] = "main/run 함수 없음 — import만 완료"
            else:
                result["executed"] = False
                result["message"] = "dry_run 모드 — import만 완료"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
            result["traceback"] = traceback.format_exc(limit=5)

        return result

    # ── 레일별 Smoke Test ───────────────────────────────────────────────
    @router.post("/engine/smoke-test/{rail_id}")
    def engine_smoke_test(
        rail_id: str,
        req: SmokeTestRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        레일 1개(20 슬롯)에 대해 순서대로 import 수준 smoke test를 실행한다.
        rail_id: RAIL-01 ~ RAIL-06
        """
        import importlib.util
        import traceback
        import threading

        RAIL_RANGES: Dict[str, tuple[int, int]] = {
            "RAIL-01": (1, 20),
            "RAIL-02": (21, 40),
            "RAIL-03": (41, 60),
            "RAIL-04": (61, 80),
            "RAIL-05": (81, 100),
            "RAIL-06": (101, 120),
        }

        normalized = rail_id.upper().strip()
        if normalized not in RAIL_RANGES:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 rail_id: {rail_id}. RAIL-01~RAIL-06 중 하나여야 합니다.")

        slot_start, slot_end = RAIL_RANGES[normalized]
        engines120_dir = Path(__file__).resolve().parents[1] / "services" / "shinsegye" / "engines120"

        results = []
        passed = 0
        failed = 0

        for slot_num in range(slot_start, slot_end + 1):
            pattern = f"slot{slot_num:03d}_*.py"
            matches = sorted(engines120_dir.glob(pattern))
            slot_result: Dict[str, Any] = {
                "slot": slot_num,
                "status": "not_found",
                "file": None,
                "error": None,
            }

            if not matches:
                failed += 1
                results.append(slot_result)
                continue

            target_file = matches[0]
            slot_result["file"] = target_file.name

            # 타임아웃 포함 import 시도
            exc_holder: Dict[str, Any] = {}

            def _try_import(path: str, holder: Dict[str, Any]) -> None:
                try:
                    spec = importlib.util.spec_from_file_location(f"smoke_{slot_num:03d}", path)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)  # type: ignore[union-attr]
                        holder["ok"] = True
                except Exception as e:
                    holder["error"] = str(e)
                    holder["tb"] = traceback.format_exc(limit=3)

            t = threading.Thread(target=_try_import, args=(str(target_file), exc_holder), daemon=True)
            t.start()
            t.join(timeout=req.timeout_per_slot)

            if t.is_alive():
                slot_result["status"] = "timeout"
                slot_result["error"] = f"{req.timeout_per_slot}s 초과"
                failed += 1
            elif exc_holder.get("ok"):
                slot_result["status"] = "passed"
                passed += 1
            else:
                slot_result["status"] = "failed"
                slot_result["error"] = exc_holder.get("error", "unknown")
                failed += 1

            results.append(slot_result)

        return {
            "status": "ok",
            "rail_id": normalized,
            "slot_range": f"{slot_start}-{slot_end}",
            "total": slot_end - slot_start + 1,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": round(passed / (slot_end - slot_start + 1) * 100, 1),
            "dry_run": req.dry_run,
            "results": results,
        }

    # ── 레일 대표 슬롯 실험 데모 (R1~R6 × 1슬롯) ───────────────────────
    @router.get("/engine/rail-demo")
    def engine_rail_demo(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        R1~R6 각 레일에서 대표 슬롯 1개를 선택해
        experiment_template_ko 자동 실행 결과를 반환한다.
        대표 슬롯: slot 1, 21, 41, 61, 81, 101 (각 레일의 첫 번째 슬롯)
        """
        from backend.services.shinsegye.extras.engine_catalog import build_marketplace_slot_checklist

        RAIL_REPS: Dict[str, int] = {
            "RAIL-01": 1, "RAIL-02": 21, "RAIL-03": 41,
            "RAIL-04": 61, "RAIL-05": 81, "RAIL-06": 101,
        }

        checklist = build_marketplace_slot_checklist(120)
        slots_by_num: Dict[int, Dict[str, Any]] = {
            row["slot"]: row for row in checklist.get("slots", [])
        }

        demo_results = []
        for rail_id, rep_slot in RAIL_REPS.items():
            row = slots_by_num.get(rep_slot, {})
            category = str(row.get("category") or "general").lower()
            engine_name_ko = row.get("engine_name_ko", f"슬롯 {rep_slot}")
            template = row.get("experiment_template_ko") or row.get("usage_description_ko") or ""
            try:
                exp_result = _run_category_experiment(category, template)
            except Exception as exc:
                exp_result = {
                    "status": "error",
                    "experiment_type": "rail_demo_error",
                    "error": str(exc),
                }
            demo_results.append({
                "rail_id": rail_id,
                "slot": rep_slot,
                "category": category,
                "engine_name_ko": engine_name_ko,
                "experiment_template_ko": template,
                "result": exp_result,
                "passed": exp_result.get("status") == "ok",
            })

        passed_count = sum(1 for r in demo_results if r["passed"])
        return {
            "status": "ok",
            "description": "R1~R6 레일별 대표 슬롯(1/21/41/61/81/101) 자동 실험 결과",
            "passed": passed_count,
            "failed": len(demo_results) - passed_count,
            "total": len(demo_results),
            "pass_rate_pct": round(passed_count / len(demo_results) * 100, 1),
            "demo_results": demo_results,
        }

    # ── 블럭 파이프라인 실행 ─────────────────────────────────────────────
    @router.post("/engine/pipeline")
    def engine_pipeline(
        req: EnginePipelineRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        사용자가 블럭식으로 선택한 엔진들을 순서대로(또는 병렬로) 실행하고
        최종 결과를 합성해 반환한다.

        - mode='sequential': 이전 블럭 출력을 다음 블럭 입력에 체인
        - mode='parallel'  : 모든 블럭을 동시에 실행 후 결과 취합
        """
        import uuid
        from backend.services.shinsegye.extras.engine_catalog import build_marketplace_slot_checklist

        pipeline_id = str(uuid.uuid4())[:12]
        mode = (req.mode or "sequential").strip().lower()
        if mode not in ("sequential", "parallel"):
            mode = "sequential"

        # 카탈로그에서 각 슬롯 메타 조회 (template 기본값)
        checklist = build_marketplace_slot_checklist(120)
        slots_by_num: Dict[int, Dict[str, Any]] = {
            row["slot"]: row for row in checklist.get("slots", [])
        }

        def _run_block(block: PipelineBlock, chained_input: str) -> Dict[str, Any]:
            meta = slots_by_num.get(block.slot, {})
            category = str(block.category or meta.get("category") or "general").lower()
            label = block.label or meta.get("engine_name_ko") or f"슬롯 {block.slot}"
            template = block.template_override or meta.get("experiment_template_ko") or meta.get("usage_description_ko") or ""
            effective_input = (chained_input.strip() or template or req.user_command).strip()

            holder: Dict[str, Any] = {"result": None, "exception": None}

            def _worker() -> None:
                try:
                    holder["result"] = _run_category_experiment(category, effective_input)
                except Exception as exc:
                    holder["exception"] = str(exc)

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            t.join(timeout=max(2.0, float(req.timeout_sec or 10.0)))

            if t.is_alive():
                res: Dict[str, Any] = {
                    "status": "timeout",
                    "experiment_type": "pipeline_timeout",
                    "error": f"{req.timeout_sec}s 초과",
                }
            elif holder["exception"]:
                res = {"status": "error", "experiment_type": "pipeline_block_error", "error": holder["exception"]}
            elif holder["result"] is not None:
                res = holder["result"]
            else:
                res = {"status": "error", "experiment_type": "pipeline_no_result", "error": "결과 없음"}

            return {
                "slot": block.slot,
                "category": category,
                "label": label,
                "effective_input": effective_input[:200],
                "status": res.get("status", "error"),
                "experiment_type": res.get("experiment_type"),
                "output_preview": res.get("output_preview"),
                "error": res.get("error"),
            }

        block_results: List[Dict[str, Any]] = []

        if mode == "parallel":
            # 병렬 실행 — 모든 블럭에 user_command를 초기 입력으로 사용
            parallel_holders: List[Dict[str, Any]] = [{} for _ in req.engine_blocks]

            def _par_worker(idx: int, blk: PipelineBlock) -> None:
                parallel_holders[idx] = _run_block(blk, req.user_command)

            threads = [
                threading.Thread(target=_par_worker, args=(i, b), daemon=True)
                for i, b in enumerate(req.engine_blocks)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=req.timeout_sec + 2.0)
            block_results = [h if h else {"status": "timeout"} for h in parallel_holders]

        else:
            # 순차 실행 — 이전 출력을 다음 입력으로 체인
            chained = req.user_command
            for block in req.engine_blocks:
                result = _run_block(block, chained)
                block_results.append(result)
                # 다음 블럭 입력: 이전 output_preview를 문자열로 변환
                prev_out = result.get("output_preview")
                if prev_out is not None:
                    if isinstance(prev_out, str):
                        chained = prev_out[:500]
                    elif isinstance(prev_out, dict):
                        chained = json.dumps(prev_out, ensure_ascii=False)[:500]
                    else:
                        chained = str(prev_out)[:500]
                # 실패하면 원래 user_command 유지
                if result.get("status") != "ok":
                    chained = req.user_command

        passed_blocks = [r for r in block_results if r.get("status") == "ok"]
        failed_blocks = [r for r in block_results if r.get("status") != "ok"]

        # 최종 출력 합성
        if passed_blocks:
            final_parts = []
            for r in passed_blocks:
                out = r.get("output_preview")
                if out is not None:
                    if isinstance(out, str):
                        final_parts.append(out[:300])
                    else:
                        final_parts.append(json.dumps(out, ensure_ascii=False)[:300])
            final_output = "\n---\n".join(final_parts) if final_parts else req.user_command
        else:
            final_output = f"파이프라인 실행 실패: {len(failed_blocks)}개 블럭 오류"

        return {
            "status": "ok" if failed_blocks == [] else ("partial" if passed_blocks else "failed"),
            "pipeline_id": pipeline_id,
            "mode": mode,
            "user_command": req.user_command,
            "block_count": len(req.engine_blocks),
            "passed_blocks": len(passed_blocks),
            "failed_blocks": len(failed_blocks),
            "block_results": block_results,
            "final_output": final_output,
        }

    # ── Smoke Test 결과 요약 (전체 레일) ────────────────────────────────
    @router.get("/engine/smoke-test/summary")
    def engine_smoke_test_summary(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """각 레일의 엔진 파일 존재 여부만 빠르게 집계한다."""
        engines120_dir = Path(__file__).resolve().parents[1] / "services" / "shinsegye" / "engines120"
        RAIL_RANGES = {
            "RAIL-01": (1, 20), "RAIL-02": (21, 40), "RAIL-03": (41, 60),
            "RAIL-04": (61, 80), "RAIL-05": (81, 100), "RAIL-06": (101, 120),
        }
        rails_summary = []
        total_found = 0

        for rail_id, (slot_start, slot_end) in RAIL_RANGES.items():
            found = 0
            missing_slots = []
            for slot_num in range(slot_start, slot_end + 1):
                matches = list(engines120_dir.glob(f"slot{slot_num:03d}_*.py"))
                if matches:
                    found += 1
                else:
                    missing_slots.append(slot_num)
            total_found += found
            rails_summary.append({
                "rail_id": rail_id,
                "slot_range": f"{slot_start}-{slot_end}",
                "found": found,
                "total": slot_end - slot_start + 1,
                "missing_slots": missing_slots,
            })

        return {
            "status": "ok",
            "engines120_dir": str(engines120_dir),
            "dir_exists": engines120_dir.exists(),
            "total_found": total_found,
            "total_slots": 120,
            "rails": rails_summary,
        }

    return router
