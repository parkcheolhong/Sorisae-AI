# Backend Start Recovery Checklist

## Scope
- [x] `start:backend` 표준 진입점 참조 확인
- [x] 루트 `scripts/start_backend_stack.ps1` 복구
- [x] 루트 `scripts/stop_backend_stack.ps1` 정합성 보강
- [x] 루트 `backend/models.py` 호환 레이어 복구
- [x] 루트 `backend/marketplace/__init__.py`, `schemas.py`, `crud.py` 호환 레이어 복구
- [x] 루트 `backend/llm/__init__.py`, `model_config.py` 호환 레이어 복구
- [ ] `npm run start:backend` 재실행
- [ ] 백엔드 컨테이너 기동 상태 확인

## Evidence Log
- `package.json` 표준 명령이 `scripts/start_backend_stack.ps1`, `scripts/stop_backend_stack.ps1`를 참조함을 확인했다.
- 루트 `scripts` 폴더에 누락된 백엔드 시작/종료 PowerShell 스크립트를 복구했다.
- 루트 `backend/models.py` 호환 레이어를 복구해 `backend.main`, `backend.auth_router`의 공용 모델 import 경로를 다시 만족시켰다.
- 루트 `backend/marketplace` 패키지에 누락된 `__init__.py`, `schemas.py`, `crud.py`를 복구해 `router.py`의 상대 import 경로를 다시 만족시켰다.
- 루트 `backend/llm` 패키지에 누락된 `__init__.py`, `model_config.py`를 복구해 `backend.main`의 LLM 런타임 설정 import 경로를 다시 만족시켰다.
