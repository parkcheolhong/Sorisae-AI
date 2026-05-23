"""
sorisae_flask_runner.py
=======================
소리새 Flask/SocketIO 슬롯을 독립 컨테이너에서 안전하게 기동하는 범용 러너.

환경변수:
  SLOT_FILE   : 실행할 슬롯 파일명 (예: slot001_sorisae_voice_movie_server.py)
  SLOT_PORT   : 바인딩 포트 (기본: 5050)
  SLOT_HOST   : 바인딩 호스트 (기본: 0.0.0.0)
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sorisae_flask_runner")

ENGINES_DIR = Path("/app/engines120")
SLOT_FILE = os.environ.get("SLOT_FILE", "")
SLOT_PORT = int(os.environ.get("SLOT_PORT", "5050"))
SLOT_HOST = os.environ.get("SLOT_HOST", "0.0.0.0")


def _load_slot_module(slot_file: str):
    """슬롯 파일을 동적으로 로드해 모듈 반환."""
    slot_path = ENGINES_DIR / slot_file
    if not slot_path.exists():
        raise FileNotFoundError(f"슬롯 파일 없음: {slot_path}")

    # engines120 를 sys.path 에 추가 (슬롯 간 내부 import 허용)
    engines_dir_str = str(ENGINES_DIR)
    if engines_dir_str not in sys.path:
        sys.path.insert(0, engines_dir_str)

    spec = importlib.util.spec_from_file_location("_sorisae_slot", slot_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _find_runnable(module) -> tuple[object | None, object | None, str]:
    """
    모듈에서 Flask app / SocketIO 객체를 탐지해 반환.
    반환: (runnable, app_obj, 종류)
      - 종류가 'socketio' → socketio.run(app_obj, host=, port=)
      - 종류가 'app'      → app_obj.run(host=, port=)
    """
    # 1순위: socketio 객체 (flask-socketio v5+는 socketio.run(app, ...) 필요)
    app_obj = None
    for attr in ("app", "application", "flask_app"):
        candidate = getattr(module, attr, None)
        if candidate is not None and hasattr(candidate, "run"):
            app_obj = candidate
            break

    for attr in ("socketio", "sio"):
        sio = getattr(module, attr, None)
        if sio is not None and hasattr(sio, "run"):
            return sio, app_obj, "socketio"

    # 2순위: Flask app 단독
    if app_obj is not None:
        return app_obj, app_obj, "app"

    # 3순위: 클래스 기반 슬롯 — 인스턴스 생성 후 내부 socketio/app 추출
    # 클래스명 중 'System', 'Server', 'Dashboard', 'Master' 등을 탐색
    for attr in dir(module):
        cls = getattr(module, attr, None)
        if (
            isinstance(cls, type)
            and cls.__module__ == "_sorisae_slot"
            and any(k in attr for k in ("System", "Server", "Dashboard", "Master", "Brain", "Hub"))
        ):
            try:
                instance = cls()
                sio = getattr(instance, "socketio", None) or getattr(instance, "sio", None)
                flask_app = getattr(instance, "web_app", None) or getattr(instance, "app", None)
                if sio and hasattr(sio, "run"):
                    return sio, flask_app, "socketio"
                if flask_app and hasattr(flask_app, "run"):
                    return flask_app, flask_app, "app"
            except Exception:
                continue

    return None, None, "none"


def _install_dispatch_endpoint(app_obj: object, slot_file: str) -> None:
    """Flask app 에 engine_hub 프록시 계약용 /api/dispatch 엔드포인트를 주입한다."""
    if app_obj is None or not hasattr(app_obj, "route"):
        return

    try:
        existing_rules = {getattr(rule, "rule", "") for rule in app_obj.url_map.iter_rules()} # pyright: ignore[reportAttributeAccessIssue]
    except Exception:
        existing_rules = set()

    if "/api/dispatch" in existing_rules:
        return

    @app_obj.route("/api/dispatch", methods=["POST"]) # pyright: ignore[reportAttributeAccessIssue]
    def _runner_dispatch_proxy():
        try:
            request = __import__("flask").request

            payload = request.get_json(silent=True) or {}
            context = payload.get("context") or {}
            engine_type = payload.get("engine_type") or slot_file
        except Exception:
            payload = {}
            context = {}
            engine_type = slot_file

        # 슬롯별 web endpoint와 분리해, 백엔드 프록시 계약을 안정적으로 보장한다.
        return {
            "ok": True,
            "engine": str(engine_type),
            "slot_file": slot_file,
            "runner": "sorisae_flask_runner",
            "context": context,
            "payload_size": len(json.dumps(payload, ensure_ascii=False)),
        }, 200


def main() -> None:
    if not SLOT_FILE:
        logger.error("SLOT_FILE 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    logger.info(f"슬롯 로드 중: {SLOT_FILE}")
    try:
        module = _load_slot_module(SLOT_FILE)
    except Exception as exc:
        logger.error(f"슬롯 로드 실패: {exc}")
        sys.exit(1)

    runnable, app_obj, kind = _find_runnable(module)
    if runnable is None:
        logger.error(f"{SLOT_FILE}: Flask app / SocketIO 객체를 찾을 수 없습니다.")
        sys.exit(1)

    # engine_hub -> Flask 슬롯 프록시 계약 엔드포인트 보장
    _install_dispatch_endpoint(app_obj, SLOT_FILE)

    logger.info(f"{SLOT_FILE}: {kind} 객체 탐지 → {SLOT_HOST}:{SLOT_PORT} 기동")
    try:
        if kind == "socketio" and app_obj is not None:
            # flask-socketio v5+: socketio.run(app, host=, port=, allow_unsafe_werkzeug=True)
            try:
                runnable.run(app_obj, host=SLOT_HOST, port=SLOT_PORT, allow_unsafe_werkzeug=True) # pyright: ignore[reportAttributeAccessIssue]
            except TypeError:
                # 구버전 호환: allow_unsafe_werkzeug 미지원 시
                runnable.run(app_obj, host=SLOT_HOST, port=SLOT_PORT) # pyright: ignore[reportAttributeAccessIssue]
        else:
            runnable.run(host=SLOT_HOST, port=SLOT_PORT) # pyright: ignore[reportAttributeAccessIssue]
    except Exception as exc:
        logger.error(f"서버 기동 실패: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
