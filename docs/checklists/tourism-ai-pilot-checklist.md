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
| CLIP-4 | 이미지 백필 적재 + 텍스트→이미지 검색(로컬 E2E) | [x] | ingest(wikidata 보존)→embedded 162→"Eiffel Tower"→에펠탑 #1 (§9.2) |
| CLIP-5 | 운영 서버 백필 적재 | [ ] | GA 잔여(런북 §9) |

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

### 9.1 로컬 1회 검증 결과 (2026-06-22, `--limit 5`)

컨테이너(`devanalysis114-backend`, fastembed 0.8.0·PIL 12.2.0) 내부에서 그대로 실행 → **무오류 종료(exit 0)**, CLIP 모델 자동 다운로드 정상.

```json
{"ok": true, "report": {"scanned": 256, "with_media": 0, "embedded": 0, "indexed": 0}}
```

검증으로 확인된 운영 적용 시 **전제 2가지**:

1. **컨테이너에 `scripts/`가 있어야 함.** 로컬 compose는 `backend/`만 마운트하고 `scripts/`는 미포함이라 `docker compose exec ... python scripts/...`가 바로 실패할 수 있음.
   - 운영: `docker compose build backend`로 이미지를 재빌드하면 리포 전체가 COPY되어 `scripts/` 포함(런북 A-2단계가 이를 보장).
   - 마운트만 쓰고 재빌드를 안 하는 환경이면 폴백: `docker cp scripts/index_tourism_clip.py <backend>:/app/scripts/ && docker exec -e TOURISM_CLIP_ENABLED=1 <backend> python /app/scripts/index_tourism_clip.py --progress`
2. **POI payload에 이미지 참조(`wikidata`/`wikimedia_commons`)가 있어야 임베딩됨.** 현재 적재 데이터(256건 샘플)는 `source,name,lat,lon,category,address,country,license` 위주로 **media 참조 0건** → `with_media=0`, `embedded=0`. 즉 명령은 정상이나 *임베딩할 이미지가 없음*. 멀티모달을 실제로 켜려면 적재 단계에서 OSM `wikidata`/`wikimedia_commons` 태그를 payload에 보존(또는 enrich)해야 함. (저작권 게이트는 CC0/CC-BY 출처표기만 통과)

> 참고: `--limit`은 스크롤 페이지(256) 단위로 적용됨(정확히 N개 컷 아님). 전체 백필은 `--limit 0`(기본) 사용.

### 9.2 적재 보강 + 백필 E2E 검증 (2026-06-22)

§9.1의 전제2(이미지 참조 부재)를 해소: `scripts/ingest_tourism_city.py` 보강 —
- `fetch_osm`: OSM 태그 `wikidata`/`wikimedia_commons`를 payload에 보존
- `fetch_wikidata`: QID 자체를 `wikidata`로 저장(place_media 가 P18 로 대표 이미지 조회)
- (스토어 `upsert_places`는 이미 두 키를 "있을 때만 저장"하므로 적재부만 보강하면 충분)

로컬 E2E(컨테이너 `devanalysis114-backend`):

```text
1) ingest --city paris --limit 200 → 384건 적재(OSM 229 + Wikidata 156)
2) index_tourism_clip --progress  → {"scanned":17984,"with_media":196,"embedded":162,"indexed":162}
3) tourism_places_clip count=162, 텍스트→이미지 검색:
   "Eiffel Tower"            → 에펠탑(Q243) 0.32  #1
   "a gothic cathedral"      → 노트르담 대성당(Q2981) 등
   "famous art museum building" → Palais de la Découverte/Galliera(박물관)
   "a river bridge in the city" → 퐁뇌프(Q335277)
```

→ 적재→백필→교차모달 검색까지 **embedded>0·의미 정합 일치 확인**. 운영은 §9 런북으로 동일 절차 실행(도시 재적재 후 백필).

### 9.3 27개 도시 일괄 갱신 — 단일 명령 (`tourism_kb_clip_refresh.py`)

전 도시 재적재(이미지 참조 보존) → CLIP 백필 1회를 한 프로세스로 수행. 백필은 컬렉션 전체를 스캔하므로 **마지막 1회면 모든 도시 커버**.

```bash
# Docker Compose(운영) — 이미지에 fastembed/scripts 반영 후
docker compose build backend && docker compose up -d backend
docker compose exec -e TOURISM_CLIP_ENABLED=1 backend \
  python scripts/tourism_kb_clip_refresh.py --all --progress
# 질의시점 융합 ON
#   backend env 에 TOURISM_CLIP_ENABLED=1 추가 후
docker compose up -d backend
```

```bash
# venv
source /workspace/.venv/bin/activate && pip install -r requirements.txt
QDRANT_URL=http://127.0.0.1:6333 TOURISM_CLIP_ENABLED=1 \
  python scripts/tourism_kb_clip_refresh.py --all --progress
```

옵션: `--cities paris,kyoto`(일부) · `--country KR,JP`(국가) · `--skip-ingest`(백필만) · `--skip-backfill`(적재만) · `--no-wikidata`(WDQS 제한 회피, 단 이미지 참조 대부분이 Wikidata P18 기반이므로 비권장) · `--limit 700`.

> 소요(공용 Overpass/WDQS): 도시당 ~50s 적재 × 27 ≈ 20–25분 + 백필(이미지 수에 비례, 수분). 공용 API 예의를 위해 도시간 `--sleep 2`(기본). cron/스케줄러 주1회 권장(§9 기존 `tourism_kb_refresh.cmd`는 OSM-only 갱신용).

### 9.4 배치 분리 — `tourism-worker` 컨테이너 (1단계 분리, 권장)

무거운 배치(ingest + CLIP 백필)를 API(`backend`)에서 떼어내 **API 트래픽 비수신·GPU 불필요** 전용 워커로 실행. `video-worker` 패턴 동일(같은 이미지, 포트 없음, `./scripts` 마운트).

- 서비스: `docker-compose.yml` `tourism-worker`(`devanalysis114-tourism-worker`)
- 루프: `scripts/tourism_worker_loop.py` → 내부적으로 `tourism_kb_clip_refresh.py` subprocess 주기 실행(실패해도 워커 미종료, SIGTERM 즉시 종료)
- 환경변수(기본): `TOURISM_REFRESH_INTERVAL_HOURS=168`(주1회) · `TOURISM_REFRESH_RUN_ON_START=false`(기동 시 공용 API 부하 회피) · `TOURISM_REFRESH_CITIES=all` · `TOURISM_REFRESH_LIMIT=700` · `TOURISM_CLIP_ENABLED=1`

```bash
# 워커만 기동(주기 갱신 시작)
docker compose up -d tourism-worker
docker compose logs -f tourism-worker
# 즉시 1회 갱신까지: 환경에 TOURISM_REFRESH_RUN_ON_START=true 후 재기동
# 수동 1회(워커와 별개, 일시 실행):
docker compose run --rm -e TOURISM_REFRESH_RUN_ON_START=true tourism-worker \
  python scripts/tourism_kb_clip_refresh.py --all --progress
```

> 검증(로컬): `py_compile` OK · `--dry-run` 실행계획 정상(`--all`/`--cities`) · `docker compose config` 앵커(`*video-env`)·env 해석 정상. 질의 경로(RAG/answer/SSE/CLIP-text)는 backend 유지(저지연·캐시 공유) → 워커는 적재/백필만 담당.

**라이브 1회 사이클 검증(2026-06-22, `RUN_ON_START=true`, cities=seoul,busan):**

```json
{"ok": true, "elapsed_sec": 396.1,
 "ingest": [{"seoul": 227}, {"busan": 180}],
 "backfill": {"scanned": 18047, "with_media": 279, "embedded": 197, "indexed": 197}}
```

워커 컨테이너 기동 → ingest(2도시) → CLIP 백필(embedded 197>0) → `rc=0` → `다음 갱신까지 대기`(스케줄 루프 전환)까지 **E2E 정상**. 검증 후 테스트 컨테이너 제거. 운영은 기본값(`--all`·`RUN_ON_START=false`·주1회)으로 `docker compose up -d tourism-worker`.

---

## 8. 재검(배포 후 실검) 로그 — 2026-06-22 배포본

- [x] SSE `/answer/stream` preview→final 라이브 — cold 16.8s(모델로드)→**warm preview 241ms<1s**, final 2985ms, done. PASS
- [x] `/api/tourism-feedback` POST→stats 라이브 — A:up/nps10 → overall NPS=100, 테스트행 정리 완료
- [x] `/api/tourism-review/stats` 라이브 — available=true (라벨 0, 클린 상태)
- [ ] (서버) `TOURISM_CLIP_ENABLED=1` 백필 후 멀티모달 검색 — GA 잔여(운영 서버)
