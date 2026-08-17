# daytrade-ai 라이브 상시운영 러너 컨테이너(설계서 §6/§10-5 운영 안정성).
# 빌드 컨텍스트 = apps/daytrade-ai:
#   docker build -f deploy/Dockerfile -t daytrade-live .
# 실행(예):
#   docker run -d --name daytrade-live -p 9108:9108 -v daytrade-data:/data \
#     daytrade-live --feed binance --symbol BTCUSDT --metrics-host 0.0.0.0
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DAYTRADE_METRICS_PORT=9108

WORKDIR /app

# 런타임 의존성: numpy(코어) + websockets(라이브 거래소 피드). 그 외는 순수 표준 라이브러리.
RUN pip install --no-cache-dir "numpy>=1.26" "websockets>=12.0"

COPY daytrade ./daytrade
COPY scripts ./scripts
COPY config ./config

# 비루트 사용자 + 영속 볼륨(/data: sqlite·감사로그·리포트).
RUN useradd -r -u 10001 trader \
    && mkdir -p /data \
    && chown -R trader:trader /app /data
USER trader
VOLUME ["/data"]
EXPOSE 9108

# 그레이스풀 셧다운: SIGTERM → live_ops.py 가 안전 종료(당일 리포트·run_end 감사 후 종료).
STOPSIGNAL SIGTERM

# liveness: /healthz(curl 없는 slim 이미지라 stdlib urllib 사용).
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; p=os.environ.get('DAYTRADE_METRICS_PORT','9108'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz',timeout=2).status==200 else 1)"

ENTRYPOINT ["python", "scripts/live_ops.py"]
# 기본값(override 가능): 컨테이너에서는 0.0.0.0 바인드로 /metrics 노출 + /data 영속.
CMD ["--feed", "sim", "--symbol", "AAPL", \
     "--metrics-host", "0.0.0.0", "--metrics-port", "9108", \
     "--db", "/data/live.sqlite", "--audit", "/data/audit.jsonl", "--report-dir", "/data/reports"]
