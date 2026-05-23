"""
자율대화 실검증 스크립트
목적: fast_reply hardcoded 차단이 제거됐는지 확인 + 실제 LLM 응답 여부 검증
실행: python verify_autonomous_chat.py
"""
import httpx
import json
import sys
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "ui.admin.round@devanalysis.local"
ADMIN_PASSWORD = "RoundUi!20260426"
RESULTS = []
CHAT_TIMEOUT_SEC = 90
LLM_CASE_TIMEOUT_RETRIES = 1
LLM_CASE_ELAPSED_WARN_MS = 70000

HARDCODED_PHRASES = [
    "좋아요. 편하게 이어서 말해 주세요.",
    "편하게 이어서 말해 주세요. 지금 바로 답하거나 작업으로 바꿔서 도와드릴게요.",
]

TEST_CASES = [
    {
        "id": "TC-01",
        "desc": "7자 일반 질문 — 이전엔 hardcoded 반환됐던 케이스",
        "message": "무슨소리야?",
    },
    {
        "id": "TC-02",
        "desc": "이름 질문 — 이전엔 hardcoded 반환됐던 케이스",
        "message": "너의 이름은무엇인가?",
    },
    {
        "id": "TC-03",
        "desc": "24자 초과 — 이전에도 LLM으로 넘어갔던 케이스",
        "message": "지금 오케스트레이터 자율대화 기능이 정상적으로 작동하고 있는지 알려줘",
    },
    {
        "id": "TC-04",
        "desc": "인사 — fast_reply 인사 분기 유지 확인",
        "message": "안녕",
    },
]


def get_auth_token() -> str:
    resp = httpx.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token") or data.get("token") or ""
    if not token:
        raise RuntimeError(f"No token in login response: {data}")
    print(f"[Auth] token 획득 완료 ({len(token)}자)")
    return token


def call_chat(message: str, token: str) -> dict:
    payload = {
        "message": message,
        "conversation": [],
        "requested_conversation_mode": "auto",
        "response_style": "auto",
        "tone_preset": "auto",
        "lightweight": False,
    }
    start = time.time()
    resp = httpx.post(
        f"{BASE_URL}/api/llm/orchestrate/chat",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=CHAT_TIMEOUT_SEC,
    )
    elapsed_ms = int((time.time() - start) * 1000)
    resp.raise_for_status()
    data = resp.json()
    content = ""
    if isinstance(data, dict):
        content = (
            data.get("content")
            or (data.get("reply") or {}).get("content")
            or data.get("message")
            or data.get("response")
            or ""
        )
    return {
        "content": content,
        "grounding_mode": data.get("grounding_mode", "") if isinstance(data, dict) else "",
        "grounding_note": data.get("grounding_note", "") if isinstance(data, dict) else "",
        "elapsed_ms": elapsed_ms,
        "raw": data,
    }


def is_hardcoded(content: str) -> bool:
    for phrase in HARDCODED_PHRASES:
        if phrase in content:
            return True
    return False


def run_all():
    print(f"\n{'='*60}")
    print(f"  자율대화 실검증 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  대상: {BASE_URL}")
    print(
        f"  timeout policy: request={CHAT_TIMEOUT_SEC}s, retries={LLM_CASE_TIMEOUT_RETRIES}, elapsed-warn={LLM_CASE_ELAPSED_WARN_MS}ms"
    )
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    try:
        token = get_auth_token()
    except Exception as e:
        print(f"[Auth] 로그인 실패: {e}")
        sys.exit(1)

    for tc in TEST_CASES:
        print(f"[{tc['id']}] {tc['desc']}")
        print(f"  입력: \"{tc['message']}\"")
        try:
            retry_budget = LLM_CASE_TIMEOUT_RETRIES if tc["id"] in ("TC-01", "TC-02", "TC-03") else 0
            attempt = 0
            while True:
                attempt += 1
                try:
                    result = call_chat(tc["message"], token)
                    break
                except httpx.TimeoutException as e:
                    if attempt > retry_budget + 1:
                        raise
                    print(f"  timeout 발생, 재시도 {attempt}/{retry_budget + 1}: {e}")

            content = result["content"]
            hardcoded = is_hardcoded(content)
            elapsed = result["elapsed_ms"]

            print(f"  응답({elapsed}ms): {content[:120]}")
            print(f"  grounding: {result['grounding_note']}")

            # TC-01, TC-02, TC-03 은 hardcoded면 실패
            if tc["id"] in ("TC-01", "TC-02", "TC-03"):
                if hardcoded:
                    print(f"  결과: FAIL — hardcoded 응답 감지됨")
                    failed += 1
                    RESULTS.append({"id": tc["id"], "status": "FAIL", "reason": "hardcoded", "content": content[:200]})
                elif result["grounding_note"] == "관리자 빠른 응답 경로" and elapsed < 200:
                    # fast_reply 인사 분기에 걸린 경우 — LLM 경로 미도달
                    print(f"  결과: WARN — 빠른 응답(fast_reply) 경로 감지, LLM 미도달 가능성")
                    RESULTS.append({"id": tc["id"], "status": "WARN", "elapsed_ms": elapsed, "grounding": result["grounding_note"], "content": content[:200]})
                    failed += 1
                elif elapsed >= LLM_CASE_ELAPSED_WARN_MS:
                    print(f"  결과: PASS — LLM 경로 응답 확인됨 (지연 경고: {elapsed}ms)")
                    passed += 1
                    RESULTS.append({
                        "id": tc["id"],
                        "status": "PASS",
                        "elapsed_warning": True,
                        "elapsed_ms": elapsed,
                        "grounding": result["grounding_note"],
                        "content": content[:200],
                    })
                else:
                    print(f"  결과: PASS — LLM 경로 실제 응답 확인됨")
                    passed += 1
                    RESULTS.append({"id": tc["id"], "status": "PASS", "elapsed_ms": elapsed, "grounding": result["grounding_note"], "content": content[:200]})
            # TC-04 인사는 fast_reply가 허용됨
            else:
                print(f"  결과: OK (인사 fast_reply 허용)")
                passed += 1
                RESULTS.append({"id": tc["id"], "status": "OK", "content": content[:200]})

        except Exception as e:
            timeout_mark = isinstance(e, httpx.TimeoutException) or "timed out" in str(e).lower()
            print(f"  결과: ERROR — {e}")
            failed += 1
            RESULTS.append({
                "id": tc["id"],
                "status": "ERROR",
                "reason": str(e),
                "error_type": "timeout" if timeout_mark else "exception",
            })
        print()

    print(f"{'='*60}")
    print(f"  총 {len(TEST_CASES)}건 | PASS/OK: {passed} | FAIL/ERROR: {failed}")
    print(f"{'='*60}\n")

    # JSON 결과 저장
    out_path = "verify_autonomous_chat_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "verified_at": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "timeout_policy": {
                "request_timeout_sec": CHAT_TIMEOUT_SEC,
                "llm_case_retries": LLM_CASE_TIMEOUT_RETRIES,
                "elapsed_warn_ms": LLM_CASE_ELAPSED_WARN_MS,
            },
            "summary": {"total": len(TEST_CASES), "pass": passed, "fail": failed},
            "results": RESULTS,
        }, f, ensure_ascii=False, indent=2)
    print(f"결과 저장: {out_path}")

    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
