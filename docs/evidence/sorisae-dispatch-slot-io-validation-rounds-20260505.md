# Evidence: Sorisae Dispatch Slot I/O Validation (2026-05-05)

## Command Context
- Base URL: <http://127.0.0.1:8000>
- Endpoint: /api/marketplace/sorisae/dispatch
- Auth: /api/auth/login bearer token
- Core slots: voice_movie, detective_dashboard, integrated_dashboard, movie_server, master, shopping
- Probe fields:
  - engine_type (required)
  - context (object)
  - entry_fn="main"
  - use_module_adapter=true
  - adapter_entry_candidates=["run","execute","start"]

## Round 1
- R1|engine=voice_movie|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-voice-movie:5050>
- R1|engine=detective_dashboard|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-cyber-detective:5052>
- R1|engine=integrated_dashboard|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-integrated-dashboard:5050>
- R1|engine=movie_server|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-movie-server:5000>
- R1|engine=master|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-master-system:5050>
- R1|engine=shopping|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-shopping-mall:5050>

## Round 2
- R2|engine=voice_movie|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-voice-movie:5050>
- R2|engine=detective_dashboard|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-cyber-detective:5052>
- R2|engine=integrated_dashboard|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-integrated-dashboard:5050>
- R2|engine=movie_server|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-movie-server:5000>
- R2|engine=master|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-master-system:5050>
- R2|engine=shopping|http=200|status=flask_server_ok|statusType=String|hasEngine=True|hasStatus=True|hasResult=True|error=False|server_url=<http://sorisae-shopping-mall:5050>

## Verdict
- Gate #1 (slot I/O contract fixed) validation: pass (2 rounds)
- Blocking issue: none
