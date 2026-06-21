# 소리새 AI 관광 지식·RAG 파일럿 — 빌드 · 검증 체크리스트

> **최종 갱신:** 2026-06-22
> **브랜치:** `feat/worldlinco-build90-92`
> **기술서:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §0.21 · 상세 SSOT `docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md`

표시: `[ ]` 미착수 · `[~]` 부분 완료 · `[x]` 완료

---

## 1. 빌드 · 배포

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| BLD-1 | 백엔드 신규 모듈 `py_compile` | [x] | feedback/multimodal/service/main/tourism_feedback_router OK |
| BLD-2 | 모바일 typecheck (변경 파일) | [x] | `tourismAnswer.ts`·`TravelItineraryPanel.tsx` 오류 0 (기존 무관 오류만) |
| BLD-3 | 의존성 선언 | [x] | `fastembed>=0.8.0`·`cryptography>=42`·`Pillow>=12.2`·`google-auth>=2.30` |
| DEP-1 | 백엔드 배포(컨테이너 재기동) | [x] | `docker restart devanalysis114-backend` |
| DEP-2 | health 200 | [x] | `GET /api/health` → 200 |
| DEP-3 | 라우터 로드 | [x] | logs: `tourism review/feedback/carbon router loaded` |

## 2. 사람검수 루프 (§0.21.1)

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| REV-1 | sample/labels/stats 왕복 | [x] | 라벨 3건 → `human_precision_retrieval=0.5`·`poi_accuracy=1.0` |
| REV-2 | admin 메뉴 진입(토큰 게이트) | [x] | `app/admin/tourism-review/page.tsx` |
| REV-3 | 자체완결 콘솔 | [x] | `GET /api/tourism-review/console` |

## 3. 컴플라이언스 7/7 (§0.21.2)

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| CMP-1 | 미디어 라이선스 게이트(default-deny) | [x] | `test_media_license.py` |
| CMP-2 | 접근성 색대비 CI 게이트 | [x] | `make contrast` AA PASS |
| CMP-3 | 탄소 측정 + admin | [x] | `/api/ops/carbon/stats` |
| CMP-4 | PII 암호화·동의·출처화면 | [x] | `pii_crypto.py`·`locationConsent.ts`·`DataSourcesModal.tsx` |

## 4. E2E<1s — 캐시 · SSE · 모바일 클라이언트 (§0.21.3)

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| LAT-1 | 검색 KPI <1s | [x] | warm p95≈201ms |
| LAT-2 | 답변 캐시 HIT <1s | [x] | 266ms(server 0.5ms) |
| LAT-3 | SSE preview <1s | [x] | preview 327ms → final 3441ms |
| LAT-4 | 모바일 SSE(over-POST) preview-first 렌더 | [x] | `streamTravelItinerary` XHR 파서 + 폴백 |
| LAT-5 | SSE 라이브 재검(배포 후) | [x] | warm preview **241ms**<1s → final 2985ms → done (PASS) |

## 5. 베타 피드백 NPS·A/B (§0.21.4)

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| FB-1 | POST/stats 왕복 + A·B 분해 | [x] | A=100·B=−100·overall NPS=0 |
| FB-2 | 빈 피드백 422 | [x] | rating·nps 미입력 거부 |
| FB-3 | 모바일 평가 카드 + admin NPS 카드 | [x] | `TravelItineraryPanel`·tourism-review 페이지 |
| FB-4 | 배포 후 라이브 재검 | [x] | POST(A:up/10)→stats NPS=100 (PASS), 테스트행 정리 |

## 6. 멀티모달 CLIP (§0.21.5)

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| CLIP-1 | CLIP text↔image 정렬 | [x] | cat 0.296(1위) |
| CLIP-2 | clip 컬렉션 적재+검색(live) | [x] | "a cute cat"→Cat·"blue square"→Block |
| CLIP-3 | 백필 CLI | [x] | `scripts/index_tourism_clip.py` |
| CLIP-4 | 운영 이미지 백필 적재(서버) | [ ] | GA 잔여 |

## 7. Git

| ID | 항목 | 상태 |
|----|------|------|
| GIT-1 | 어제 미푸시 커밋(build 159) push | [x] `f7b10835a` |
| GIT-2 | 오늘 관광 AI 작업 커밋 | [x] `f487c4aef` (53 files) |
| GIT-3 | origin push | [x] `64af6e1bb..f487c4aef` → 동기화 |

---

## 9. 운영 서버 CLIP 백필 런북 (②, RTX 5090 서버에서 실행)

> CLIP 임베딩은 fastembed ONNX/CPU라 **GPU 불필요**. 최초 1회 모델 다운로드 ~350MB(서버 인터넷 필요).
> 전제: `requirements.txt`에 `fastembed>=0.8.0`·`Pillow>=12.2` 추가됨 → **백엔드 이미지 재빌드 필요**.

**A. Docker Compose 환경(권장)**

```bash
# 1) 최신 코드 동기화
cd /workspace            # 서버의 리포 루트
git fetch origin && git checkout feat/worldlinco-build90-92 && git pull --ff-only

# 2) fastembed/Pillow 설치 위해 백엔드 이미지 재빌드 + 재기동
docker compose build backend
docker compose up -d backend

# 3) 백필 실행(컨테이너 내부, Qdrant는 compose 네트워크로 'qdrant' 호스트 해석)
docker compose exec -e TOURISM_CLIP_ENABLED=1 backend \
  python scripts/index_tourism_clip.py --progress
#   옵션: --limit 500 (일부만)  --batch 32 (업서트 배치)

# 4) 질의시점 멀티모달 융합 ON: 백엔드 환경에 TOURISM_CLIP_ENABLED=1 추가 후 재기동
#    (docker-compose.yml backend.environment 또는 .env 에 TOURISM_CLIP_ENABLED=1)
docker compose up -d backend

# 5) 검증 — clip 컬렉션 적재 수 + 텍스트→이미지 검색
docker compose exec backend python - <<'PY'
from backend.services.tourism_kb import get_tourism_store
s = get_tourism_store()
print("clip points:", s.client.count("tourism_places_clip").count)
PY
curl -s "http://127.0.0.1:8000/api/health"
```

**B. 네이티브 venv 환경**

```bash
source /workspace/.venv/bin/activate
pip install -r requirements.txt          # fastembed/Pillow 반영
export QDRANT_URL="http://127.0.0.1:6333" TOURISM_CLIP_ENABLED=1
python scripts/index_tourism_clip.py --progress
# 질의 ON: 백엔드 프로세스 env 에 TOURISM_CLIP_ENABLED=1 두고 재기동
```

**기대 결과:** 백필 종료시 `{"ok": true, "report": {...}}`(scanned/embedded/upserted/skipped). 게이트 통과(CC0/CC-BY 출처표기) 이미지가 있는 POI만 대상이라 일부 skip 정상. 적재 후 검색은 본 컬렉션(dense+sparse)과 `tourism_places_clip`을 **클라이언트측 RRF**로 융합.

**롤백:** `TOURISM_CLIP_ENABLED` 제거 후 재기동 → 본 컬렉션만 사용(무영향). `tourism_places_clip` 컬렉션은 비파괴이므로 삭제만으로 원복.

---

## 8. 재검(배포 후 실검) 로그 — 2026-06-22 배포본

- [x] SSE `/answer/stream` preview→final 라이브 — cold 16.8s(모델로드)→**warm preview 241ms<1s**, final 2985ms, done. PASS
- [x] `/api/tourism-feedback` POST→stats 라이브 — A:up/nps10 → overall NPS=100, 테스트행 정리 완료
- [x] `/api/tourism-review/stats` 라이브 — available=true (라벨 0, 클린 상태)
- [ ] (서버) `TOURISM_CLIP_ENABLED=1` 백필 후 멀티모달 검색 — GA 잔여(운영 서버)
