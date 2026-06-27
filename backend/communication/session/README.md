# Session Core (얇은 버전) — `backend/communication/session/`

로드맵 [#2](../../../docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md) 1차 산출물. **통화/세션 단위로 언어쌍·통화 맥락을 기억**하는
최소 코어다. Strangler Fig 원칙: **추가형 · feature-flag · 기존 hot path 무접촉.**

## 설계 원칙
- **hot path 무접촉:** `nadotongryoksa_voip_router`·`voice-translate`는 이 모듈을 호출하지 않는다. 오케스트레이터가 플래그 on일 때만 얇게 연결(향후 단계).
- **플래그 off = no-op:** `SessionManager`의 모든 쓰기/조회는 `COMM_V2_SESSION_CORE` off면 `None`/빈값을 반환 → 호출부가 플래그 분기를 안 해도 안전.
- **DB/오디오 비보관:** 텍스트 요약만 메모리에 보관(프라이버시). 오디오 바이트 미저장.
- **Redis 승격 대비:** `SessionStore` 추상 → 인메모리 기본, 로드맵 #4에서 동일 인터페이스로 Redis 교체.

## 구성
| 파일 | 역할 |
|------|------|
| `config.py` | `COMM_V2_*` env → `SessionCoreConfig`(enabled/ttl/max_turns/max_sessions) |
| `models.py` | `LanguagePair`·`Participant`·`TurnRecord`·`SessionContext`(순수 dataclass) |
| `store.py` | `SessionStore` 추상 + `InMemorySessionStore`(thread-safe·TTL·LRU evict) |
| `manager.py` | `SessionManager` — get_or_create / update_language_pair / record_turn / purge |
| `integration.py` | hot path ↔ Session Core **유일 접점** — `record_call_init` / `record_relay_turn`(best-effort, flag-gated, **절대 throw 금지**) |

## 오케스트레이터 얇은 연결 (additive)
플래그 on일 때만 동작하며, off면 완전 no-op. 예외는 `integration.py` 내부에서 흡수 → hot path 무영향.

| 지점 | 파일 | 훅 |
|------|------|----|
| call_init | `backend/marketplace/nadotongryoksa_voip_router.py` (`/calls/initiate`) | `record_call_init(session_id, call_id, source/target_lang, participants)` — 언어쌍·참가자 기억 |
| relay 턴 | `backend/llm/router.py` (`/voice-translate`) | `record_relay_turn(session_id, source/target_lang, source/translated_text)` — `voice-translate`에 **옵션 `session_id`**(하위호환, 응답 contract 무변경) 추가 |
| 맥락 주입(#9 Meaning) | `backend/llm/router.py` + `translator.py` | `build_context_hint(session_id)` → **designated(VOIP) 모드에서만** MT system 프롬프트에 최근 대화 맥락을 보조 힌트로 주입(호칭·대명사·존댓말 일관성). **대면/bilingual·flag off·session_id 없음 → 미주입**. `translate(context_hint=...)` 제공 시 원격 캐시 우회(턴 특이적) |

> 클라이언트가 아직 `voice-translate`에 `session_id`를 보내지 않으면 relay 기록·맥락 주입 모두 no-op(무해). 추후 클라이언트가 세션 ID를 실으면 자동 활성.

## 맥락 주입 안전성
- **대면(🔒) 무접촉:** `bilingual_mode`일 때는 `context_hint`를 만들지 않음(미주입). VOIP designated 경로 전용.
- **캐시 오염 방지:** `context_hint` 제공 시 원격 캐시 read/write 우회. 로컬 고정 표현 사전(`_PHRASE_DICT`)은 그대로 우선.
- **기본 off:** `COMM_V2_SESSION_CORE` 미설정이면 `build_context_hint`가 항상 `None` → MT 동작 100% 동일.

## 환경변수 (기본 전부 off/보수값)
| 변수 | 기본 | 의미 |
|------|------|------|
| `COMM_V2_SESSION_CORE` | `false` | 마스터 스위치 |
| `COMM_V2_SESSION_TTL_SEC` | `3600` | 비활성 세션 만료(초) |
| `COMM_V2_SESSION_MAX_TURNS` | `50` | 세션당 최근 턴 보존 수 |
| `COMM_V2_SESSION_MAX_SESSIONS` | `10000` | 인메모리 세션 수 상한 |

## 사용 예
```python
from backend.communication.session import SessionManager, TurnRecord, LanguagePair

mgr = SessionManager()  # 플래그 off면 모든 호출 no-op
mgr.update_language_pair("sess-1", "ko", "ja", call_id="call-1")
mgr.record_turn("sess-1", TurnRecord(direction=LanguagePair("ko", "ja"),
                                     source_text="안녕", translated_text="こんにちは"))
pair = mgr.language_pair("sess-1")        # LanguagePair(ko, ja) | None(off)
ctx = mgr.recent_turns("sess-1", limit=5) # 최근 5턴
```

## 테스트
```bash
python -m pytest backend/tests/test_communication_session_core.py
```
