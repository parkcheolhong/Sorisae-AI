# AGENTS.md

## Cursor Cloud specific instructions

### Architecture Overview

This is a Korean-language full-stack AI project analysis + marketplace platform ("개발분석114.com" / "MetaNova"). Key services:

| Service | Technology | Dev Port |
|---------|-----------|----------|
| Backend API | Python 3.13 / FastAPI / Uvicorn | 8000 |
| Frontend (marketplace + admin) | Next.js 16 / React / TypeScript | 3000 (marketplace), 3005 (admin) |
| PostgreSQL | 15-alpine | 5432 |
| Redis | 7-alpine | 6380 (host) → 6379 (container) |
| Qdrant | v1.16.2 | 6333 |
| MinIO | S3-compatible object store | 9000 (API), 9001 (console) |

### Running services locally (outside Docker Compose)

The docker-compose.yml is designed for production with GPU support. For local dev without GPU:

1. **Infrastructure** — Start Postgres, Redis, Qdrant, MinIO as standalone Docker containers (see commands below).
2. **Backend** — Run with Python 3.13 venv directly (not in Docker).
3. **Frontend** — Run Next.js dev server with `npm run dev`.

### Critical: hostname resolution

The backend's `backend/marketplace/database.py` hardcodes the Postgres hostname to `"postgres"` when `POSTGRES_HOST` is `localhost`/`127.0.0.1`. To run the backend natively, add these entries to `/etc/hosts`:

```
127.0.0.1 postgres
127.0.0.1 redis
127.0.0.1 qdrant
127.0.0.1 minio
```

### Starting infrastructure services

```bash
docker run -d --name devanalysis114-postgres \
  -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=changeme -e POSTGRES_DB=devanalysis114 \
  -p 127.0.0.1:5432:5432 --health-cmd="pg_isready -U admin -d devanalysis114" \
  --health-interval=10s --health-timeout=5s --health-retries=5 postgres:15-alpine

docker run -d --name devanalysis114-redis -p 127.0.0.1:6380:6379 redis:7-alpine redis-server --appendonly yes

docker run -d --name devanalysis114-qdrant -p 127.0.0.1:6333:6333 qdrant/qdrant:v1.16.2

docker run -d --name devanalysis114-minio \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 127.0.0.1:9000:9000 -p 127.0.0.1:9001:9001 \
  minio/minio:RELEASE.2025-02-28T09-55-16Z server /data --console-address ":9001"
```

### Starting the backend

```bash
source /workspace/.venv/bin/activate
export DATABASE_URL="postgresql://admin:changeme@127.0.0.1:5432/devanalysis114"
export POSTGRES_HOST=postgres POSTGRES_PORT=5432
export REDIS_URL="redis://127.0.0.1:6380/0"
export QDRANT_URL="http://127.0.0.1:6333"
export MINIO_ENDPOINT="127.0.0.1:9000" MINIO_ACCESS_KEY=minioadmin MINIO_SECRET_KEY=minioadmin
export SECRET_KEY="dev-secret-key-for-local-testing-only"
export ENABLE_AD_ORDER_WORKER_BOOTSTRAP=false
export ENABLE_SELF_RUN_VIDEO_WORKER_BOOTSTRAP=false
export ENABLE_AD_ORDER_RUNTIME_RECOVERY_BOOTSTRAP=false
export SORISAE_CENTRAL_ENABLED=false
export VIDEO_REQUIRE_GENERATIVE_ENGINE=false VIDEO_ENGINE_FALLBACK_TO_INTERNAL=true
export MARKETPLACE_BILLING_ALLOW_SIMULATED_CHECKOUT=true
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Starting the frontend

```bash
cd /workspace/frontend/frontend
BACKEND_PROXY_TARGET=http://localhost:8000 LOCAL_API_BASE_URL=http://localhost:8000 npm run dev -- --port 3000
```

For admin on a separate port: use `--port 3005`.

### Backend port SSOT (8000)

로컬·프로브·프론트 프록시는 **항상 `:8000`** 을 사용합니다. Windows에서 `8001` 등 대체 포트 uvicorn은 바인드 거부(`WinError 10013`)가 날 수 있으므로 사용하지 않습니다.

**Docker Compose 환경 (권장):**

```powershell
docker restart devanalysis114-backend
# health 확인
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

프론트 `.env.local` / Playwright / probe 기본값: `BACKEND_PROXY_TARGET` · `LOCAL_API_BASE_URL` → `http://127.0.0.1:8000`

**DoD-2 HTTP probe:**

```powershell
docker restart devanalysis114-backend
$env:PROBE_LOGIN_EMAIL="119cash@naver.com"
$env:PROBE_LOGIN_PASSWORD="changeme-probe-local"
python scripts/run_11stage_orchestrator_probe.py --mode http --admin --base-url http://127.0.0.1:8000
python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace --base-url http://127.0.0.1:8000
```

### Running tests

```bash
# Backend tests (from /workspace)
source /workspace/.venv/bin/activate
pytest tests/  # root-level tests
pytest backend/tests/ --ignore=backend/tests/test_orchestrator_operational_evidence_targets.py

# Frontend tests
cd /workspace/frontend/frontend && npm run test

# Makefile shortcut (compile check + core tests)
make check
```

### Known caveats

- Ensure `frontend/frontend/package.json` remains valid JSON (no trailing commas), otherwise `npm ci` will fail.
- **GPU**: The actual dev/production server has an RTX 5090 32GB. Cursor Cloud Agent VMs do not have GPU hardware, so the health check GPU warning is expected only in cloud agent sessions. On the real server, GPU is fully available and torch/CUDA will work normally.
- Redis is exposed on host port **6380** (not 6379) to avoid conflicts.
- Some backend tests (`test_orchestrator_compat_manifest_write`, `test_runtime_config_persistence`) have pre-existing failures unrelated to environment setup.
- The `test_orchestrator_operational_evidence_targets.py` test file has an import error (missing function) and must be excluded.
- Async backend tests (those marked `@pytest.mark.asyncio`, e.g. `test_autonomous_orchestrator.py`, `test_orchestrator_dialogue_mode.py`) use **`pytest-asyncio`** (`requirements.txt`). Run with `python -m pytest <file> --asyncio-mode=auto` (default when `pyproject.toml` `[tool.pytest.ini_options] asyncio_mode = "auto"` is present).
- The autonomous multi-agent orchestrator (`/api/llm/autonomous/chat`) runs the A-brain agents (reasoner/planner/reviewer) via Ollama; without an LLM server those agents return `error`/stub, but the B-brain `coder` (template generator) + `validator` (`py_compile`) work without GPU/LLM, so the approval→code-generation path is testable in cloud agent sessions.
- Frontend `npm run test` has a pre-existing failure in `tests/rail-labels.test.mjs` (asserts the marketplace page still contains the legacy label `5가지 AI 엔진 상품`, which the current code no longer uses). The other two checks (`smoke`, `nadotongryoksa-contracts`) pass. There is no `lint` script defined for the frontend.
- There is no root `/` route; the app renders at `/marketplace` and `/admin` (a bare `/` returns 404, and `/login` redirects to `/admin/login`). The marketplace login/signup form is embedded in the right sidebar of `/marketplace`, not on a separate page.

### Coding conventions

- **UTC time (Py 3.12+):** `datetime.utcnow()` is deprecated. Use the SSOT helper `from backend.time_utils import utcnow` — it returns a **naive** UTC `datetime` (drop-in: preserves DB-naive comparisons and `isoformat() + "Z"` output). Do **not** edit the `datetime.utcnow()` strings inside `backend/llm/orchestrator.py` code-generation templates or the generated reference app `app/`; they are kept in lockstep for golden-task consistency.
- **Rate limiting:** Reuse `backend/security_gates.py` (`_InMemoryQuotaGate` + `require_*_quota` deps) for per-user/client quotas; it returns `429` + `Retry-After`. Tests reset global quota state via `backend/tests/conftest.py` autouse fixture (`reset_for_test()`).
