"""관광 KB 멀티모달 갱신 워커 — 적재+CLIP 백필을 주기 실행(API 트래픽 비수신 전용 컨테이너).

설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md (§4 지속 최신화)
- 무거운 배치(ingest + CLIP 백필)를 API(backend)에서 분리해 자원 경합·지연을 제거(1단계 분리).
- 내부적으로 scripts/tourism_kb_clip_refresh.py 를 subprocess 로 호출(모델 메모리 매 회 격리).
- 실패해도 워커는 죽지 않고 다음 주기까지 대기(restart 폭주 방지). SIGTERM 시 즉시 종료.

환경변수:
  TOURISM_REFRESH_INTERVAL_HOURS  주기(기본 168=주1회)
  TOURISM_REFRESH_RUN_ON_START    기동 직후 1회 실행(기본 false — 공용 API 부하 회피)
  TOURISM_REFRESH_CITIES          대상('all' 또는 'paris,kyoto', 기본 all)
  TOURISM_REFRESH_LIMIT           도시·소스별 수집 상한(기본 700)
  TOURISM_REFRESH_NO_WIKIDATA     'true' 면 Wikidata 생략(이미지 참조↓, 비권장)
  TOURISM_CLIP_ENABLED            '1'(백필 모델 로드; compose 에서 주입)
  TOURISM_REFRESH_DRY_RUN         'true' 면 실행계획만 출력하고 종료(스모크용)

사용:
  python scripts/tourism_worker_loop.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_STOP = False


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    print(f"[{ts}] [tourism-worker] {msg}", flush=True)


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _build_cmd() -> list[str]:
    cities = os.environ.get("TOURISM_REFRESH_CITIES", "all").strip()
    limit = os.environ.get("TOURISM_REFRESH_LIMIT", "700").strip()
    cmd = [sys.executable, str(REPO / "scripts" / "tourism_kb_clip_refresh.py")]
    if cities.lower() in ("", "all"):
        cmd.append("--all")
    else:
        cmd += ["--cities", cities]
    cmd += ["--limit", limit, "--progress"]
    if _env_bool("TOURISM_REFRESH_NO_WIKIDATA"):
        cmd.append("--no-wikidata")
    return cmd


def _run_once() -> int:
    cmd = _build_cmd()
    _log(f"갱신 시작: {' '.join(cmd)}")
    t0 = time.time()
    env = dict(os.environ)
    env.setdefault("TOURISM_CLIP_ENABLED", "1")
    try:
        rc = subprocess.run(cmd, cwd=str(REPO), env=env, check=False).returncode
    except Exception as exc:  # noqa: BLE001
        _log(f"갱신 예외(다음 주기까지 대기): {exc}")
        return 1
    _log(f"갱신 종료 rc={rc} 소요={time.time() - t0:.1f}s")
    return rc


def _handle_sigterm(_signum, _frame) -> None:
    global _STOP
    _STOP = True
    _log("SIGTERM 수신 — 종료")


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    interval_h = float(os.environ.get("TOURISM_REFRESH_INTERVAL_HOURS", "168") or "168")
    interval_s = max(60.0, interval_h * 3600.0)
    run_on_start = _env_bool("TOURISM_REFRESH_RUN_ON_START")

    _log(
        f"기동: interval={interval_h}h run_on_start={run_on_start} "
        f"cities={os.environ.get('TOURISM_REFRESH_CITIES', 'all')} "
        f"clip_enabled={os.environ.get('TOURISM_CLIP_ENABLED', '0')}"
    )

    if _env_bool("TOURISM_REFRESH_DRY_RUN"):
        _log(f"DRY_RUN — 실행계획: {' '.join(_build_cmd())} / 주기 {interval_s:.0f}s")
        return 0

    if run_on_start:
        _run_once()

    while not _STOP:
        _log(f"다음 갱신까지 {interval_s / 3600.0:.1f}h 대기")
        # 인터럽트 응답성을 위해 잘게 쪼개 sleep.
        waited = 0.0
        while waited < interval_s and not _STOP:
            time.sleep(min(30.0, interval_s - waited))
            waited += 30.0
        if _STOP:
            break
        _run_once()
    _log("워커 종료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
