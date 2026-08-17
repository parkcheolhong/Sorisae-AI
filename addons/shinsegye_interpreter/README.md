# Shinsegye Interpreter Migration

This folder contains a migrated subset of the interpreter program from:

- Repository: `parkcheolhong/run_all_shinsegye.py`
- Source commit: `56b7d89`
- Migration date: 2026-04-29

## Included Files

- `src/sorisae_interpreter.py`
- `src/hybrid_conversation_translator.py`
- `src/hybrid_interpreter_system.py`
- `src/multilingual_system.py`
- `src/sorisae_multilingual_support.py`
- `src/sorisae_southeast_asia_translator.py`
- `run_interpreter.py`
- `service_api.py`
- `requirements.txt`
- `docs/INTERPRETER_GUIDE.md`

## Quick Run

1. Install dependencies:

```bash
pip install -r addons/shinsegye_interpreter/requirements.txt
```

1. Run migrated interpreter launcher:

```bash
python addons/shinsegye_interpreter/run_interpreter.py
```

1. Run the standalone FastAPI service:

```bash
python -m uvicorn addons.shinsegye_interpreter.service_api:app --host 0.0.0.0 --port 8011
```

1. Platform integration endpoints:

```text
POST /api/marketplace/interpreter/translate
GET  /api/marketplace/interpreter/health
```

## Notes

- This migration intentionally keeps only the interpreter-related subset.
- Some runtime paths in `run_interpreter.py` point to source files under project root, which are included in this migrated package under `src/`.
- For direct module import tests, prepend `addons/shinsegye_interpreter/src` to `PYTHONPATH`.
- `docker-compose.yml` now includes an `interpreter-service` container on port `8011`, and backend requests can proxy through `INTERPRETER_SERVICE_URL`.
