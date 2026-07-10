"""메트릭 HTTP 노출 서버(설계서 §10-5) — 의존성 0(stdlib http.server).

`/metrics` 로 Prometheus text exposition 을, `/healthz` 로 헬스를 제공한다. 데몬 스레드에서
구동되어 메인 트레이딩 루프를 막지 않으며, `registry_provider()` 가 매 요청 시 **현재** 레지스트리를
반환하므로 라이브 갱신이 그대로 스크레이프에 반영된다.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from .exporter import MetricsRegistry


class MetricsServer:
    """Prometheus 스크레이프용 `/metrics` 서버.

    Args:
        registry_provider: 호출 시 현재 `MetricsRegistry` 를 반환(라이브 갱신 반영).
        host/port: 바인드 주소. port=0 이면 OS 가 빈 포트 할당(`self.port` 로 확인).
    """

    def __init__(
        self,
        registry_provider: Callable[[], MetricsRegistry],
        *,
        host: str = "127.0.0.1",
        port: int = 9108,
        ready_provider: Callable[[], bool] | None = None,
    ) -> None:
        self._provider = registry_provider
        self._ready_provider = ready_provider
        self._host = host
        self._requested_port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> "MetricsServer":
        provider = self._provider
        ready_provider = self._ready_provider

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path.rstrip("/") in ("/metrics", ""):
                    body = provider().render().encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path.rstrip("/") == "/healthz":
                    # liveness: 서버 스레드가 응답 가능하면 살아있음.
                    body = b"ok"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path.rstrip("/") == "/readyz":
                    # readiness: ready_provider 가 없으면 항상 ready, 있으면 그 결과(503=not ready).
                    ready = True if ready_provider is None else bool(ready_provider())
                    body = b"ready" if ready else b"not ready"
                    self.send_response(200 if ready else 503)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):  # 조용히(트레이딩 콘솔 오염 방지)
                return

        self._httpd = ThreadingHTTPServer((self._host, self._requested_port), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="metrics-http", daemon=True)
        self._thread.start()
        return self

    @property
    def port(self) -> int:
        if self._httpd is None:
            return self._requested_port
        return self._httpd.server_address[1]

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self.port}/metrics"

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def __enter__(self) -> "MetricsServer":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
