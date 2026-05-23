# Sorisae Dispatch Slot I/O Contract (2026-05-05)

## Scope
- Endpoint: POST /api/marketplace/sorisae/dispatch
- Router source of truth: backend/marketplace/sorisae_engine_router.py
- Engine return source of truth: backend/services/shinsegye/engine_hub.py
- Fixed core slots in this gate:
  - voice_movie
  - detective_dashboard
  - integrated_dashboard
  - movie_server
  - master
  - shopping

## Request Contract

### JSON Object

```json
{
  "engine_type": "voice_movie",
  "context": {
    "contract_probe": "R1",
    "ts": "2026-05-05T00:00:00+09:00",
    "source": "schema-validation"
  },
  "entry_fn": "main",
  "use_module_adapter": true,
  "adapter_entry_candidates": ["run", "execute", "start"]
}
```

### Required Fields
- engine_type: string

### Optional Fields
- context: object | null (default: null)
- entry_fn: string (default: "main")
- use_module_adapter: boolean (default: true)
- adapter_entry_candidates: `array<string>` | null (default: null)

### Validation Rules
- engine_type must be registered in SorisaeEngineHub registry.
- If engine_type is not registered, API returns HTTP 400.

## Response Contract

### Common Envelope
Every successful dispatch returns a JSON object including:
- engine: string
- status: string
- result: any | null

### Status Variants

1. flask_server_ok

```json
{
  "engine": "voice_movie",
  "status": "flask_server_ok",
  "server_url": "http://sorisae-voice-movie:5050",
  "result": {}
}
```

1. flask_server_unavailable

```json
{
  "engine": "voice_movie",
  "status": "flask_server_unavailable",
  "server_url": "http://sorisae-voice-movie:5050",
  "error": "<network error>",
  "result": null
}
```

1. ok

```json
{
  "engine": "decision",
  "status": "ok",
  "result": {}
}
```

1. slot_map_ok

```json
{
  "engine": "decision",
  "status": "slot_map_ok",
  "adapter_used": false,
  "entry_fn": "main",
  "adapter_entry_fn": "test_decision_engine",
  "result": {}
}
```

1. adapter_ok

```json
{
  "engine": "multilingual",
  "status": "adapter_ok",
  "adapter_used": true,
  "entry_fn": "main",
  "adapter_entry_fn": "run",
  "result": {}
}
```

1. adapter_error

```json
{
  "engine": "multilingual",
  "status": "adapter_error",
  "adapter_used": true,
  "entry_fn": "main",
  "adapter_entry_fn": "run",
  "adapter_candidates": ["main", "run", "execute", "start"],
  "error": "<runtime error>",
  "result": null
}
```

1. module_only

```json
{
  "engine": "dream",
  "status": "module_only",
  "adapter_used": false,
  "module": "sorisae_slot.slot010_dream_interpreter.py",
  "entry_fn": "main",
  "adapter_candidates": ["main", "run", "execute", "start"],
  "result": null
}
```

1. fallback

```json
{
  "engine": "decision",
  "status": "fallback",
  "error": "<import error>",
  "result": null
}
```

1. error

```json
{
  "engine": "decision",
  "status": "error",
  "error": "<execution error>",
  "result": null
}
```

## Core Slot Mapping (Flask Container)
- voice_movie -> slot001_sorisae_voice_movie_server.py -> <http://sorisae-voice-movie:5050>
- detective_dashboard -> slot041_cyber_detective_dashboard.py -> <http://sorisae-cyber-detective:5052>
- integrated_dashboard -> slot089_sorisae_integrated_dashboard.py -> <http://sorisae-integrated-dashboard:5050>
- movie_server -> slot103_sorisae_movie_web_server.py -> <http://sorisae-movie-server:5000>
- master -> slot106_sorisae_master_system.py -> <http://sorisae-master-system:5050>
- shopping -> slot120_shopping_mall_dashboard.py -> <http://sorisae-shopping-mall:5050>

## Verification Rule for Gate #1
- Two live rounds must satisfy all of the following for all six core slots:
  - HTTP status = 200
  - response.status = flask_server_ok
  - has field engine
  - has field status
  - has field result
  - error is false or absent
