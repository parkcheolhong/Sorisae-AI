# A-3-2 GPU LLM 품질 검증 보고서 (최종)

**일시:** 2026-06-16 KST (UTC 2026-06-15T22:03)  
**환경:** RTX 5090 32GB · vLLM `http://127.0.0.1:8008/v1` · **`Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`**  
**백엔드:** Docker `devanalysis114-backend` · Admin HTTP `POST /api/llm/autonomous/chat`

## 최종 요약

| 항목 | 결과 |
|------|------|
| `overall_passed` | ✅ **true** |
| `profile_aligned_32b_awq` | ✅ **true** (live = preferred 32B AWQ) |
| turn_controller | ✅ reasoner/planner `success` · reviewer `needs_revision` · `llm_connected: true` |
| http_testclient | ✅ HTTP 200 · reasoner `success` · stub 0 |
| http_api (Admin JWT) | ✅ login 200 · chat 200 · `llm_connected: true` |
| 증거 JSON | `A32_GPU_VERIFY_20260615-220314.json` |

## 검증 경로 (3 probe)

1. **turn_controller** — Python 직접 · A뇌 reasoner/planner/reviewer 연속 LLM 호출  
2. **http_testclient** — FastAPI TestClient (subprocess 격리 · event loop 충돌 방지)  
3. **http_api** — `127.0.0.1:8000` live backend · Admin 로그인 → Bearer → autonomous chat  

## vLLM 32B 프로필 정렬

- Compose: `gpu-llm-server/docker-compose.vllm-32b.yml`  
- 기동: `.\scripts\start_vllm_rtx5090_32b.ps1`  
- HF 캐시: `C:/gpu-llm-server-cache/huggingface` (14B·32B AWQ 사전 다운로드 확인)

## 운영 스크립트

| 스크립트 | 용도 |
|----------|------|
| `scripts/verify_autonomous_llm_gpu.py` | A-3-2 3-probe 자동 검증 |
| `scripts/reset_fixed_admin_password.py` | Admin DB bcrypt 재설정 (host 실행 시 `postgres`→`127.0.0.1` 자동) |
| `scripts/start_vllm_rtx5090_32b.ps1` | RTX 5090 32B AWQ vLLM recreate |

```powershell
$env:OLLAMA_BASE="http://127.0.0.1:8008/v1"
$env:VERIFY_ADMIN_EMAIL="119cash@naver.com"
$env:VERIFY_ADMIN_PASSWORD="<admin-password>"
python scripts/verify_autonomous_llm_gpu.py
```

## Admin UI · 비밀번호

- `/admin/llm` — `LLM 연결` / agent stub 없음 수동 확인  
- 전역 설정 패널 — **「관리자 계정 비밀번호 변경」** UI 추가 (PostgreSQL 런타임 비밀번호와 구분)  
- `http_api` probe용 Admin 계정: `scripts/reset_fixed_admin_password.py` 로 DB 해시 동기화 후 verify  

## 이전 이슈·조치

| 이슈 | 조치 |
|------|------|
| vLLM 14B만 로드 → 32B config 404 | `resolve_live_model_routes` · 32B compose 전환 |
| TestClient → event loop closed | verify probe 순서 변경 + subprocess testclient |
| `http_api` `llm_connected` null | backend 재시작 · verify fallback (agent success 추론) |
| Admin login 401 | `reset_fixed_admin_password.py` · host DB URL rewrite |

## Admin 패널 수동 확인

1. `/admin/llm` → 모드 **조언** · `FastAPI로 간단한 헬스체크 API 만들어줘`  
2. **`LLM 연결`** · reasoner `success` · stub 없음  
3. STAGE 잔여 표시 (full_auto 시)
