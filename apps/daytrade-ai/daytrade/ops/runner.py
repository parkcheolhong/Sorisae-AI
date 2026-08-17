"""LiveRunner — 페이퍼봇 라이브 상시운영 슈퍼바이저(설계서 §6/§10-5 운영 안정성).

영속 `TradingPipeline` 을 라이브 피드에 물려 **상시 가동**하며, 다음을 결합한다.
  - **자동 재연결**: 피드 스트림이 끊기면(generator 종료/예외) 지수 백오프로 재연결(포트폴리오/메트릭은 유지).
  - **heartbeat**: 주기적으로 라이브 메트릭(`LiveMetrics`) 갱신 + 알림 평가 + 콜백(상태 1줄).
  - **일일 리포트**: UTC 자정 경계에서 당일 손익/체결/알림 요약을 리포트로 산출(파일 + 감사로그).
  - **감사로그/알림/`/metrics`**: M6 구성요소(`AuditLog`/`AlertEngine`/`MetricsServer`)를 상시 결선.

테스트 가능성: 벽시계(`wall`)·단조시계(`mono`)·`sleep` 을 주입할 수 있어 네트워크/실시간 없이 검증한다.
정체(no-tick) 감지는 스크레이프 측 규칙(`time() - daytrade_last_tick_unixtime > N`, `config/alert_rules.yml`)
이 담당한다(틱이 없으면 인프로세스 루프는 블록되므로).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..feed.base import MarketFeed
from ..monitoring.alerts import AlertEngine
from ..monitoring.audit import AuditLog
from ..monitoring.exporter import LiveMetrics
from ..pipeline import TradingPipeline


@dataclass
class RunnerConfig:
    symbol: str
    heartbeat_sec: float = 15.0
    reconnect_base_sec: float = 1.0
    reconnect_max_sec: float = 30.0
    max_reconnects: int = 0      # 연속 재연결 실패 한도(0=무제한)
    max_runtime_sec: float = 0.0  # 총 가동 시간 한도(0=무제한)
    max_ticks: int = 0            # 총 틱 한도(0=무제한)
    report_dir: str | None = None  # 일일 리포트 저장 디렉터리(None=파일 미기록)
    model_dir: str | None = None   # current.json 감시 디렉터리(None=런타임 핫스왑 비활성)
    # M7-L: 핫스왑 후 라이브 KPI 악화 시 직전 버전 자동 롤백.
    rollback_enabled: bool = False
    rollback_drawdown_pct: float = 1.0   # 스왑 이후 낙폭이 이 값(%) 이상이면 롤백
    rollback_window_sec: float = 300.0   # 스왑 후 감시 윈도(초). 경과 시 안정 판정·감시 해제


@dataclass
class DailyReport:
    date: str
    ticks: int
    fills: int
    signals: int
    rejects: int
    start_equity: float
    end_equity: float
    pnl: float
    return_pct: float
    max_drawdown_pct: float
    alerts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "date": self.date, "ticks": self.ticks, "fills": self.fills,
            "signals": self.signals, "rejects": self.rejects,
            "start_equity": round(self.start_equity, 2), "end_equity": round(self.end_equity, 2),
            "pnl": round(self.pnl, 2), "return_pct": round(self.return_pct, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4), "alerts": self.alerts,
        }


class LiveRunner:
    def __init__(
        self,
        pipeline: TradingPipeline,
        feed_factory: Callable[[], MarketFeed],
        *,
        config: RunnerConfig,
        audit: AuditLog | None = None,
        alert_engine: AlertEngine | None = None,
        live: LiveMetrics | None = None,
        on_heartbeat: Callable[[dict], None] | None = None,
        on_report: Callable[[DailyReport], None] | None = None,
        on_tick=None,
        on_reload: Callable[[dict], None] | None = None,
        rollback_fn: Callable[[], dict | None] | None = None,
        stop_flag: Callable[[], bool] | None = None,
        wall: Callable[[], float] = time.time,
        mono: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.pipeline = pipeline
        self.feed_factory = feed_factory
        self.cfg = config
        self.audit = audit
        self.alerts = alert_engine or AlertEngine()
        self.live = live
        self.on_heartbeat = on_heartbeat
        self.on_report = on_report
        self.on_tick = on_tick
        self.on_reload = on_reload
        self.rollback_fn = rollback_fn
        self.stop_flag = stop_flag
        self._wall = wall
        self._mono = mono
        self._sleep = sleep

        self._stop_requested = False
        self._total_ticks = 0
        self._reconnects = 0
        self._consecutive_failures = 0
        self._last_prices: dict[str, float] = {}
        self._peak_equity = pipeline.portfolio.starting_cash
        self._active_alerts: set[str] = set()
        self._reports: list[DailyReport] = []
        self._loaded_model_version: int | None = None
        self._model_reloads = 0
        self._rollbacks = 0
        self._swap_watch: dict | None = None  # 핫스왑 후 KPI 감시 상태(None=비감시)

        # 당일 기준선(일일 리포트 델타 계산용).
        self._day = self._today()
        self._day_baseline = self._counters_snapshot()
        self._day_start_equity = self._equity()
        self._last_hb_mono = self._mono()
        self._start_mono = self._mono()
        self._last_tick_wall = self._wall()

    # ── 시간/스냅샷 헬퍼 ───────────────────────────────────────────
    def _today(self) -> str:
        return datetime.fromtimestamp(self._wall(), tz=timezone.utc).date().isoformat()

    def _equity(self) -> float:
        if not self._last_prices:
            return self.pipeline.portfolio.equity({self.cfg.symbol: 0.0})
        return self.pipeline.portfolio.equity(self._last_prices)

    def _counters_snapshot(self) -> dict:
        m = self.pipeline.metrics
        return {"ticks": m.ticks, "signals": m.signals, "orders": m.orders_submitted,
                "fills": m.fills, "rejects": m.rejects}

    def _live_snapshot(self) -> dict:
        equity = self._equity()
        self._peak_equity = max(self._peak_equity, equity)
        dd = (self._peak_equity - equity) / self._peak_equity * 100.0 if self._peak_equity else 0.0
        m = self.pipeline.metrics
        staleness_ms = max(0.0, (self._wall() - self._last_tick_wall) * 1000.0)
        return {
            "equity": equity,
            "max_drawdown_pct": dd,
            "orders_submitted": m.orders_submitted,
            "rejects": m.rejects,
            "halted": m.halted,
            "staleness_ms": staleness_ms,
            "latency_ms_p99": 0.0,  # 라이브 p99 는 스크레이프 측 histogram 으로(여기선 0)
        }

    # ── 그레이스풀 종료 / 헬스 ────────────────────────────────────
    def request_stop(self) -> None:
        """외부(시그널 핸들러 등)에서 안전 종료 요청. 다음 점검 지점에서 루프를 빠져나간다."""
        self._stop_requested = True

    def last_tick_age(self) -> float:
        """마지막 틱 이후 경과(초). readiness/정체 판정용."""
        return max(0.0, self._wall() - self._last_tick_wall)

    def is_healthy(self, *, max_staleness_sec: float = 10.0) -> bool:
        """레디니스: 서킷브레이커 미발동 + 최근 틱 신선도."""
        return (not self.pipeline.metrics.halted) and self.last_tick_age() <= max_staleness_sec

    # ── 런타임 모델 핫스왑(current.json 감시) ─────────────────────
    def _maybe_reload_model(self) -> None:
        """model_dir/current.json 버전이 바뀌었으면 파이프라인 모델·시그널을 런타임 교체.

        재학습/스케줄러가 새 모델을 승격하면(버전↑) 상시 러너가 무중단으로 집어 든다.
        """
        if not self.cfg.model_dir:
            return
        from .registry import load_current

        cur = load_current(self.cfg.model_dir)
        if cur is None or cur.version == self._loaded_model_version:
            return
        prev = self._loaded_model_version
        applied = self.pipeline.reload_from_current(self.cfg.model_dir)
        if applied is None:
            return
        self._loaded_model_version = cur.version
        self._model_reloads += 1
        if self.live is not None:
            self.live.set_model(cur.version, self._model_reloads)
        if self.audit is not None:
            self.audit.append("model_reload", version=cur.version,
                              model_path=applied.get("model_path"), signal=applied.get("signal"))
        if self.on_reload is not None:
            self.on_reload({"version": cur.version, "reloads": self._model_reloads, **applied})
        # 승격(버전↑)일 때만 KPI 감시 무장(롤백 reload(버전↓)는 무장하지 않음 → 루프 방지).
        if (self.cfg.rollback_enabled and self.rollback_fn is not None
                and prev is not None and cur.version > prev):
            self._swap_watch = {"armed_wall": self._wall(), "peak": self._equity(),
                                "from_version": prev, "to_version": cur.version}

    def _check_rollback_guard(self) -> None:
        """핫스왑 후 윈도 내 낙폭이 한도를 넘으면 직전 버전으로 자동 롤백."""
        w = self._swap_watch
        if w is None:
            return
        equity = self._equity()
        w["peak"] = max(w["peak"], equity)
        dd = (w["peak"] - equity) / w["peak"] * 100.0 if w["peak"] else 0.0
        if (self._wall() - w["armed_wall"]) > self.cfg.rollback_window_sec:
            self._swap_watch = None  # 윈도 통과 → 안정 판정, 감시 해제.
            return
        if dd < self.cfg.rollback_drawdown_pct:
            return
        # 임계 초과 → 롤백 실행.
        if self.audit is not None:
            self.audit.append("kpi_breach", drawdown_pct=round(dd, 4),
                              version=w["to_version"], window_sec=self.cfg.rollback_window_sec)
        restored = self.rollback_fn() if self.rollback_fn else None
        self._swap_watch = None
        if restored is None:
            return
        self._rollbacks += 1
        self._maybe_reload_model()  # current.json 이 이전 버전으로 갱신됨 → 파이프라인 반영.
        if self.on_reload is not None:
            self.on_reload({"event": "rollback", "rollbacks": self._rollbacks, **restored})

    # ── 정지 조건 ─────────────────────────────────────────────────
    def _should_stop(self) -> bool:
        if self._stop_requested:
            return True
        if self.stop_flag is not None and self.stop_flag():
            return True
        if self.cfg.max_ticks and self._total_ticks >= self.cfg.max_ticks:
            return True
        if self.cfg.max_runtime_sec and (self._mono() - self._start_mono) >= self.cfg.max_runtime_sec:
            return True
        if self.cfg.max_reconnects and self._consecutive_failures > self.cfg.max_reconnects:
            return True
        return False

    # ── heartbeat / 알림 / 일일 리포트 ────────────────────────────
    def _maybe_heartbeat(self, force: bool = False) -> None:
        if not force and (self._mono() - self._last_hb_mono) < self.cfg.heartbeat_sec:
            return
        self._last_hb_mono = self._mono()
        snap = self._live_snapshot()
        if self.live is not None:
            self.live.update(self.pipeline.metrics, snap["equity"], now_unixtime=self._last_tick_wall)
        self._check_rollback_guard()
        self._evaluate_alerts(snap)
        hb = {"ts": self._wall(), "ticks": self._total_ticks, "equity": round(snap["equity"], 2),
              "fills": self.pipeline.metrics.fills, "reconnects": self._reconnects,
              "halted": snap["halted"], "active_alerts": sorted(self._active_alerts)}
        if self.on_heartbeat is not None:
            self.on_heartbeat(hb)

    def _evaluate_alerts(self, snap: dict) -> None:
        fired = {a.name: a for a in self.alerts.evaluate(snap)}
        newly = set(fired) - self._active_alerts
        for name in sorted(newly):
            a = fired[name]
            if self.audit is not None:
                self.audit.append("alert", name=a.name, severity=a.severity, message=a.message, value=a.value)
        self._active_alerts = set(fired)

    def _maybe_roll_day(self, force: bool = False) -> None:
        today = self._today()
        if not force and today == self._day:
            return
        end_equity = self._equity()
        base = self._day_baseline
        cur = self._counters_snapshot()
        pnl = end_equity - self._day_start_equity
        ret = (pnl / self._day_start_equity * 100.0) if self._day_start_equity else 0.0
        dd = (self._peak_equity - end_equity) / self._peak_equity * 100.0 if self._peak_equity else 0.0
        report = DailyReport(
            date=self._day,
            ticks=cur["ticks"] - base["ticks"],
            fills=cur["fills"] - base["fills"],
            signals=cur["signals"] - base["signals"],
            rejects=cur["rejects"] - base["rejects"],
            start_equity=self._day_start_equity,
            end_equity=end_equity,
            pnl=pnl,
            return_pct=ret,
            max_drawdown_pct=dd,
            alerts=sorted(self._active_alerts),
        )
        self._reports.append(report)
        if self.cfg.report_dir:
            Path(self.cfg.report_dir).mkdir(parents=True, exist_ok=True)
            (Path(self.cfg.report_dir) / f"report_{report.date}.json").write_text(
                json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if self.audit is not None:
            self.audit.append("daily_report", **report.as_dict())
        if self.on_report is not None:
            self.on_report(report)
        # 다음 날 기준선 리셋.
        self._day = today
        self._day_baseline = cur
        self._day_start_equity = end_equity

    # ── 메인 루프 ─────────────────────────────────────────────────
    def run(self) -> dict:
        if self.audit is not None:
            self.audit.append("run_start", symbol=self.cfg.symbol,
                              mode=self.pipeline.effective_mode.value)
        self._maybe_reload_model()  # 시동 시 최신 승격 모델(current.json) 적용.
        try:
            while not self._should_stop():
                connected_any = self._consume_one_session()
                if self._should_stop():
                    break
                # 세션 종료(피드 끊김) → 재연결 백오프.
                self._reconnects += 1
                if connected_any:
                    self._consecutive_failures = 0
                else:
                    self._consecutive_failures += 1
                if self.audit is not None:
                    self.audit.append("feed_disconnect", reconnects=self._reconnects,
                                      consecutive_failures=self._consecutive_failures)
                if self._should_stop():
                    break
                self._sleep(self._backoff())
        except KeyboardInterrupt:  # pragma: no cover - 운영 중단
            pass

        self._maybe_roll_day(force=True)  # 종료 시 당일 리포트 마감.
        summary = self._summary()
        if self.audit is not None:
            self.audit.append("run_end", **summary)
        return summary

    def _consume_one_session(self) -> bool:
        """피드 1세션 소비. 끊기면 반환(재연결은 호출자). 최소 1틱 받으면 True."""
        got = False
        self._maybe_reload_model()  # 세션(재연결) 경계마다 승격 모델 점검 → 무중단 핫스왑.
        try:
            feed = self.feed_factory()
            for tick in feed.ticks():
                if not got:
                    got = True
                    if self.audit is not None:
                        self.audit.append("feed_connect", symbol=self.cfg.symbol)
                # 일일 경계 점검은 처리 전에(직전 영업일 마감 = 직전 틱 기준 자산/카운터).
                self._maybe_roll_day()
                self.pipeline.process_tick(tick)
                self._total_ticks += 1
                self._last_prices = {tick.symbol: tick.last_price}
                self._last_tick_wall = self._wall()
                if self.on_tick is not None:
                    self.on_tick(tick)
                self._maybe_heartbeat()
                if self._should_stop():
                    break
        except Exception as exc:  # noqa: BLE001 — 피드 오류는 재연결로 흡수
            if self.audit is not None:
                self.audit.append("feed_error", error=type(exc).__name__, detail=str(exc)[:200])
        return got

    def _backoff(self) -> float:
        # 지수 백오프(연속 실패 기준), 상한 캡.
        exp = self.cfg.reconnect_base_sec * (2 ** max(0, self._consecutive_failures - 1))
        return min(exp, self.cfg.reconnect_max_sec)

    def _summary(self) -> dict:
        m = self.pipeline.metrics
        equity = self._equity()
        return {
            "symbol": self.cfg.symbol,
            "ticks": self._total_ticks,
            "reconnects": self._reconnects,
            "fills": m.fills,
            "signals": m.signals,
            "rejects": m.rejects,
            "end_equity": round(equity, 2),
            "pnl": round(equity - self.pipeline.portfolio.starting_cash, 2),
            "days_reported": len(self._reports),
            "model_reloads": self._model_reloads,
            "model_version": self._loaded_model_version,
            "rollbacks": self._rollbacks,
            "halted": m.halted,
        }

    @property
    def reports(self) -> list[DailyReport]:
        return self._reports
