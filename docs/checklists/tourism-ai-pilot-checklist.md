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

---

## 10. 관측성 정밀화 — OTel 분산 트레이싱 · 갭 클로저 로드맵 (§0.22)

> 배경: 레퍼런스 아키텍처 적합성 평가(캔버스 `tourism-voip-architecture-fit`) 결과, 스펙 헤드라인인
> **정밀 ns 타임스탬프 + 분산 트레이싱**이 유일한 "명확한 갭"으로 확인됨. 본 절은 그 해소 작업.
> 원칙: 기존 패턴(`backend/voip/metrics.py`·`carbon_meter.py`)과 동일하게 **opt-in · 의존성 가드 · fail-open** —
> 미설치/비활성/실패 어느 경우에도 앱 기동·요청 처리·대면 통역(§0.20.3 동결)에 **무영향**.

| ID | 항목 | 상태 | 검증 / 비고 |
|----|------|------|------|
| OBS-1 | OTel 트레이싱 모듈(opt-in·fail-open) | [x] | `backend/observability/tracing.py` — `OTEL_TRACING_ENABLED` 게이트(기본 OFF) |
| OBS-2 | `main.py` 와이어업 | [x] | prometheus 블록 직후 `init_tracing(app)`(try/except, fail-open) |
| OBS-3 | 옵션 의존성 선언 | [x] | `requirements-observability.txt`(메인 이미지 불변, opt-in 설치) |
| OBS-4 | FastAPI/httpx 자동 계측 | [x] | 요청 span + 아웃바운드 httpx(STT/번역/TTS·외부 API) → 발화 단위 trace 연결 |
| OBS-5 | `py_compile`(OTel 미설치 안전) | [x] | 의존성 부재 시 no-op tracer 폴백, import 안전 |
| OBS-6 | NTP(±1ms) 동기화 런북 | [x] (문서) | 노드 `chrony` 설정 — OS/인프라 영역(코드 아님), 아래 런북 |

### 10.1 활성화 런북 (운영, opt-in)

```bash
# 1) 옵션 의존성 설치(메인 이미지에는 미포함 — 활성화 시에만)
pip install -r requirements-observability.txt
# 2) 수집기(Jaeger/Tempo, OTLP gRPC 4317) 기동 후 env 설정
export OTEL_TRACING_ENABLED=1
export OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317   # 또는 jaeger OTLP
export OTEL_SERVICE_NAME=devanalysis114-backend
# 3) 노드 시계 ±1ms 동기화 (정밀 타임스탬프 전제 — OS 레벨)
sudo apt-get install -y chrony && sudo systemctl enable --now chrony
chronyc tracking   # offset 확인
# 4) 백엔드 재기동 → 발화(STT→번역→TTS) 단위 trace 가 수집기에 표시
```

> 비활성(기본): `OTEL_TRACING_ENABLED` 미설정 시 `init_tracing`은 즉시 `False` 반환(no-op). 의존성 미설치 시에도 동일.

### 10.2 보류(계획) 항목 — 위험/타당성 사유

| 항목 | 상태 | 보류 사유 (어떤 경우에도 파악 가능하도록 명시) |
|------|------|------|
| 오토튜너 `search_space` 확장 — **RAG top-k** | [x] 런타임 연결+제안기 | **§10.4** — `TOURISM_RAG_TOP_K` 런타임 SSOT 연결 + `eval_tourism_retrieval.py --sweep` 제안기(관광 검색 목적함수). worldlinco VoIP 스터디와 **분리**(목적함수 상이). |
| 오토튜너 `search_space` 확장 — 코덱·지터버퍼·GPU클럭·번역batch | [ ] 계획 | `eval/worldlinco/`는 사람승인 게이트라 배포 위험은 없으나, **런타임 SSOT에 미연결된 노브는 무의미한 제안**을 생성. 각 노브의 런타임 적용 경로 선(先)연결 후 추가해야 함(RAG top-k 가 선례 — §10.4). |
| RTP 레벨 지연 메트릭(RTT/jitter/loss) | [~] 설계+백엔드 구현 · 모바일 opt-in | **P2P 적합 방식**으로 진행 — 클라이언트 `getStats()`→백엔드 보고(§10.3). 백엔드 메트릭·엔드포인트·모바일 리포터 구현, **기본 비활성(opt-in)**. |
| SFU 미디어 서버 / K8s 멀티-AZ | [ ] 로드맵 | 다자 통화·서버 녹음/믹싱 또는 수평확장·다중 AZ가 제품 요구가 될 때 도입(현 1:1 P2P·단일 호스트 Compose 로 MVP 충족). |

### 10.3 RTP 지연 측정 — 클라이언트 getStats → 백엔드 보고 (P2P 적합 설계)

> 서버측 RTP 중계 지점이 없는 **P2P + TURN** 구조에서 실측하는 정공법: 각 단말이
> `RTCPeerConnection.getStats()`로 RTT/jitter/loss/bitrate를 주기 표본화해 백엔드로 보고 →
> 백엔드는 off-path Prometheus 히스토그램으로 집계. **off-path · opt-in · fail-open**(통화 경로 무영향).

| ID | 항목 | 상태 | 검증 / 비고 |
|----|------|------|------|
| RTP-1 | 백엔드 QoS 메트릭(role 라벨) | [x] | `voip_client_rtt_seconds`·`_jitter_seconds`·`_packet_loss_ratio`·`_outgoing_bitrate_bps` (`backend/voip/metrics.py`, fail-open) |
| RTP-2 | 보고 엔드포인트 | [x] | `POST /api/v1/voip/webrtc-stats`(인증·격리·fail-open, PII 미수집) `nadotongryoksa_voip_router.py` |
| RTP-3 | 모바일 표본 파서(순수함수) | [x] | `webrtcStatsReporter.ts` `extractWebRTCStatsSample()` — candidate-pair/inbound-rtp/remote-inbound 파싱, 손실은 누적 카운터 델타 |
| RTP-4 | 모바일 리포터(주기 표본·보고) | [x] | `WebRTCStatsReporter`(기본 5s, fetch fail-open) |
| RTP-5 | 통화 클라이언트 opt-in 연결 | [x] | `VoIPCallClient.startStatsReporter(opts)` + `hangup()`에서 정지. **자동 호출 없음 → 기본 런타임 무변경** |
| RTP-6 | 유닛 테스트 | [x] | `__tests__/webrtcStatsReporter.test.ts`(파서 순수함수) |

- **수집 항목(수치 QoS만, PII 없음):** `rtt_ms`·`jitter_ms`·`packet_loss_ratio(0..1)`·`outgoing_bitrate_bps`·`role(caller/callee)`. 통화/방 식별자 등은 메트릭 라벨에 넣지 않음(데이터 최소화).
- **KPI 매핑:** Grafana `histogram_quantile(0.95, voip_client_rtt_seconds_bucket)` → 스펙 `<30ms RTT`, `voip_client_packet_loss_ratio` → `<2% 손실` 게이지화.
- **활성화(opt-in):** 통화 화면/훅이 연결 성공 후 `client.startStatsReporter({ apiBaseUrl, authToken, role })` 호출 시에만 보고 시작. 미호출 시 완전 비활성.

### 10.4 RAG top-k — 런타임 SSOT 연결 + 자동 튜닝 제안기 (오토튜너 확장 1단계)

> **설계 결정:** RAG top-k 는 VoIP voice-relay 자동 튜너(`eval/worldlinco/`, VAD/턴테이킹 QoE
> 목적함수)와 **목적함수가 다르므로** worldlinco `SEARCH_SPACE` 에 섞지 않는다. 대신 이미 존재하는
> **관광 검색 정확도 목적함수**(`eval_tourism_retrieval.py`, 골든 질의셋·`category_hit@k`)에 연결한다.
> 이로써 §10.2 가 경고한 "런타임 미연결 노브 = 무의미한 제안" 안티패턴을 피한다.

| ID | 항목 | 상태 | 검증 / 비고 |
|----|------|------|------|
| RAG-1 | 런타임 SSOT 접근자 | [x] | `tourism_rag_top_k()` — env `TOURISM_RAG_TOP_K`(기본 5, [1..20] 클램프), 매 호출 env 재평가 → **재기동 없이 라이브 조정** (`backend/services/tourism_kb/service.py`) |
| RAG-2 | 검색 경로 연결(비파괴) | [x] | `search_tourism_places(limit=None)` 이 SSOT 사용. **명시 limit 호출자(친구챗·일정·eval)는 영향 없음** → 기본 동작 불변 |
| RAG-3 | 자동 튜닝 제안기 | [x] | `eval_tourism_retrieval.py --sweep 3,5,8,12` → k별 정확도/정밀도/지연 평가 후 최적 k 제안. **제안 전용·사람 승인 게이트**(`PROPOSAL_ONLY_REQUIRES_HUMAN_APPROVAL`) |
| RAG-4 | 제안 산출물 | [x] | `reports/tourism_rag_topk_proposal.json`(current/proposed top-k·`current_in_sweep`·`improves_over_current`·후보표·`apply_hint`) |
| RAG-5 | 유닛 테스트 | [x] | `tests/test_tourism_rag_topk.py`(knob 파싱·클램프·`select_best_k` 순위·정직성, Qdrant 불필요) — 8 pass |

- **선택 기준(사전식):** `accuracy_category_hit ↑` → `mean_precision_at_k ↑` → `run_time_sec ↓` → `k ↓`(프롬프트 절약). 동률은 더 작은 k 선호.
- **정직성 가드:** 현재 운영 k 가 스윕 후보에 없으면 그 정확도를 측정하지 않은 것이므로 `improves_over_current=null`(+`current_in_sweep=false`) — 검증 없이 "개선"으로 단정하지 않음(헌법 규칙). 현재 k 를 `--sweep` 에 포함해야 개선 여부 확정.
- **채택(사람 승인 후):** `export TOURISM_RAG_TOP_K=<k>` — 백엔드 재기동 불필요(매 호출 env 재평가). 회귀 시 즉시 원복.
- **기본 동작 불변 보장:** env 미설정 시 `tourism_rag_top_k()`=5(기존 `search()` 기본값과 동일), 운영 친구챗/일정 경로는 자체 명시 limit 사용으로 무영향.

### 10.5 오토튜너 잔여 노브 — 노브별 상세 설계 (필요조건·위험·절차)

> **핵심 판단:** RAG top-k(§10.4)가 오프라인에서 안전하게 끝까지 연결 가능했던 유일한 노브다. 세 전제가 모두 충족됐기 때문 — ① in-repo 런타임 config 지점, ② in-repo 목적함수(골든셋 하니스), ③ 동결 오디오 경로(§0.20.3)와 무관. 아래 4개는 모두 **서버 인프라** 또는 **동결 미디어 경로**라 위 전제를 충족하지 못한다 → "지금 코드로 RAG top-k처럼" 처리하면 검증 불가/위험. 코드 변경 없이 *설계만* 기록(착수는 트리거·환경 충족 시).

#### 10.5.1 번역 batch (vLLM 서빙 배치) — 서버 인프라

- **실제 위치:** vLLM 기동 인자 `--max-num-seqs`(동시 시퀀스)·`--max-num-batched-tokens`(배치 토큰). `scripts/vllm-rtx5090-32b.env`·`gpu-llm-server/docker-compose.vllm-32b.yml`·`scripts/start_vllm_rtx5090_32b.ps1`. **앱 코드 아님** — 번역은 `backend/services/nadotongryoksa/translator.py::_llm_translate` 가 vLLM(Qwen 32B)에 **발화당 1요청**, 배치는 서빙엔진 continuous batching 이 자동 처리.
- **선연결 필요:** 현재 env 에 배치 노브 없음 → `VLLM_MAX_NUM_SEQS` 등 노출 + compose/스크립트가 `--max-num-seqs ${VLLM_MAX_NUM_SEQS}` 전달하도록 추가.
- **목적함수:** 동시 통화 부하에서 번역 **p95 지연 vs 처리량(tokens/s)**. 하니스: `scripts/worldlinco_loadtest.py`(동시 통화 시뮬). **GPU 서버 필요**(오프라인 측정 불가).
- **위험:** 배치↑ → 처리량↑·VRAM↑·**개별 지연↑**(실시간 통역은 지연이 더 중요). `VLLM_MAX_MODEL_LEN=8192`·`GPU_MEMORY_UTILIZATION=0.92` 와 상호작용 → OOM 위험.
- **절차:** (1) env 노브 노출 (2) 서버 부하 스윕 `seqs ∈ {…}` (3) **p95 지연 게이트 하** 최대 처리량 설정 선택 (4) 승인 후 env 반영·vLLM 재기동.

#### 10.5.2 지터버퍼 — 동결 오디오 경로(§0.20.3)

- **실제 위치:** WebRTC 수신측. 표준 노출 `RTCRtpReceiver.jitterBufferTarget`(ms) 또는 `playoutDelayHint`. **현재 `voipCallClient.ts` 에 튜닝 코드 없음**(평범한 createOffer/Answer) → 동결 경로에 **신규 추가** 필요. react-native-webrtc 의 해당 API 지원 여부 **선확인**(미지원이면 노브 부재 → 보류).
- **목적함수:** 언더런(끊김)/손실 vs 입↔귀 지연. 측정은 이미 가능 — `voip_client_jitter_seconds`·`voip_client_packet_loss_ratio`(§10.3) + 사용자 실통화 A/B.
- **위험:** 동결 오디오 경로. 버퍼↓ → 지연↓·**언더런↑**. 사용자 실통화 회귀 위험(과거 VAD/에코 튜닝 회귀 사례 참조).
- **절차:** (1) RN-webrtc API 지원 확인 (2) **opt-in** 노브로만 (3) `voip_client_*` + 실통화 A/B (4) 승인.

#### 10.5.3 코덱 (Opus 파라미터) — 동결 미디어 경로

- **실제 위치:** SDP 협상 — Opus `maxaveragebitrate`·`useinbandfec`·`usedtx`·ptime. SDP munging(`voipCallClient.ts` offer/answer) 또는 `RTCRtpSender.setParameters`. 현재 미사용.
- **목적함수:** 명료도(MOS) vs 대역폭/손실복원(FEC). 측정: `voip_client_outgoing_bitrate_bps` + 손실 + 주관 품질.
- **위험:** **가장 위험** — 동결 미디어 경로, 협상 실패 시 통화 자체 실패. SDP munging 은 단말/네트워크 호환성 광범위 테스트 필수.
- **절차:** (1) 안전 파라미터만(FEC on·DTX 등) (2) 단말·네트워크 호환성 광범위 테스트 (3) 단계적 롤아웃.

#### 10.5.4 GPU 클럭 — 서버 하드웨어 (보류 권장)

- **실제 위치:** 서버 OS `nvidia-smi -lgc <min,max>`·`-pl <watts>`. **repo·앱 무관**.
- **목적함수:** 추론 지연 vs 전력/발열/안정성. 측정: 로드테스트 + 전력/온도 모니터.
- **위험:** 하드웨어 안정성·수명·전력. **효용(지연 소폭↓) 대비 위험 커 보류 권장.**
- **절차:** 필요 시 운영자가 서버에서 모니터링 하 신중히(코드 작업 아님).

> **결론:** 오토튜너 in-repo 안전 확장은 RAG top-k(§10.4)로 1건 완료. §10.5 의 4개는 서버 인프라(번역batch·GPU)·동결 미디어 경로(지터버퍼·코덱)라, 해당 환경/트리거가 충족될 때 위 절차로 착수한다.

---

## 11. 지역 무관 통화 일관성 — TURN 릴레이 연동/검증 (원거리 먹통 해소)

> 증상: 같은 네트워크(LAN/무선ADB) 폰만 정상, LTE/5G·타 네트워크 원거리 통화는 "신호만 받고 음성 먹통". 원인은 **TURN 릴레이 미연동** — LTE/5G CGNAT(대칭 NAT)는 STUN-only 로 P2P 직결이 막혀 TURN 경유가 필수다.

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| TURN-1 | 백엔드 fail-loud(조용한 STUN-only 강등 차단) | [x] | `nadotongryoksa_voip_router.py::_default_turn_servers` — TURN 미설정 시 경고 1회. `turn_relay_configured()` 헬퍼 추가 |
| TURN-2 | coturn 배포 설정 저장소 커밋 | [x] | `coturn/`(compose·`.env.example`·README) 추적 추가. `coturn/.env`(시크릿)은 gitignore 유지 |
| TURN-3 | 지역 무관 일관성 검증 도구 | [x] | `scripts/verify_turn_relay.py` — 백엔드 도달성 + TURN 포트 도달성을 *실행 네트워크* 기준 PASS/FAIL. 의존성 없음(stdlib) |
| TURN-4 | (운영) coturn 공개 배포 + 방화벽 | [x] | `worldlinco-coturn` 가동 2일+, 공인 IP `211.218.172.124`, 3478/udp·tcp + relay 레인지 49160-49200/udp 게시 확인 |
| TURN-5 | (운영) 백엔드 TURN_URLS/TURN_SECRET 설정·재시작 | [x] | 백엔드 컨테이너 env 에 `TURN_URLS`/`TURN_SECRET` 적재 확인 — **앱에 TURN 정상 하달됨** |
| TURN-6 | TURN Allocate 실측(미디어 평면) | [x] | `verify_turn_relay.py --allocate` → Allocate 성공, 릴레이 `211.218.172.124:49170` 발급. 서버측 릴레이 동작 입증 |
| TURN-7 | 장거리 기준 고정(force-relay) | [x] | `VOIP_FORCE_RELAY=1` → 백엔드가 `ice_transport_policy=relay` 하달, 단말은 릴레이 경로만 사용. 같은 LAN 테스트도 셀룰러와 동일 경로 = 지역 무관 동일 결과 |
| TURN-8 | TURN 한-노브 설정 | [x] | `TURN_SECRET` 만 있으면 `TURN_DOMAIN`/`TURN_PORT` 로 URL 자동 유도. compose 에 coturn 서비스(`--profile turn`) 통합 |

### 11.1 활성화 절차 (운영자 — 코드 아님, 이걸로 지역 무관 일관성 고정)

```bash
# 1) coturn 노드 기동(공인 IP 노드)
cd coturn && cp .env.example .env   # TURN_SECRET(랜덤)·TURN_EXTERNAL_IP(공인IP) 설정
docker compose -f docker-compose.coturn.yml up -d
# 2) 방화벽/공유기 공개: 3478/udp·tcp + relay UDP 레인지(49160-49200/udp)
# 3) 백엔드 .env 에 동일 시크릿/주소 설정 후 재시작(누락 고리)
#    TURN_URLS=turn:<공인IP>:3478   TURN_SECRET=<coturn 과 동일>
docker restart devanalysis114-backend
```

### 11.2 일관성 측정(같은 명령을 LAN·LTE 핫스팟에서 각각 실행 → 결과 동일해야 함)

```bash
python scripts/verify_turn_relay.py --base-url https://metanova1004.com
# [PASS] backend_health / [PASS] turn_relay <ip>:3478  ← 두 네트워크에서 모두 PASS 여야 지역 무관
```

### 11.3 장거리 기준 고정 — 측정 결과(2026-06-22)

서버에서 측정한 실측 증거(모두 PASS):

```text
[PASS] backend_health: HTTP 200
[PASS] turn_relay 211.218.172.124:3478: TCP connect OK
[PASS] turn_allocate 211.218.172.124:3478: Allocate 성공 — 릴레이 211.218.172.124:49170 (미디어 평면 OK)
```

- DNS(공개 8.8.8.8/1.1.1.1): `metanova1004.com → 211.218.172.124` (프록시 아님, TURN 직결 가능).
- 백엔드 컨테이너 env: `TURN_URLS`/`TURN_SECRET`/`VOIP_FORCE_RELAY=1`/`TURN_DOMAIN` 적재 확인, health 200.
- 코드: `VOIP_FORCE_RELAY=1` → 콜-init 응답에 `ice_transport_policy="relay"` → 단말(신빌드)이 릴레이 경로만 사용.

**완전 일관성을 위한 잔여(서버/단말 영역, 코드 아님):**
1. 원격 LTE 단말에서 `python scripts/verify_turn_relay.py --base-url https://metanova1004.com --turn turn:211.218.172.124:3478 --allocate` 가 **서버와 동일하게 PASS** 인지(엣지 라우터/ISP 가 미디어 UDP 레인지 49160-49200 를 외부에 열어주는지).
2. **신규 빌드 배포** — 기존 APK 는 `ice_transport_policy` 미지원이라 force-relay 강제가 클라에 완전 바인딩되려면 신빌드가 필요(단, 기존 빌드도 TURN 후보는 받으므로 직결 실패 시 릴레이로 폴백됨).

> **경계(정직):** 서버측 릴레이는 Allocate 실측으로 **동작 입증 완료**. "어디서나 같은 결과"는 force-relay(모든 통화 동일 경로) + 미디어 UDP 레인지 외부 개방(위 1) + 신빌드(위 2)로 고정된다. 코드/구성/서버 env 는 이 커밋으로 정합됐고, 남은 건 원격 네트워크 PASS 재현과 신빌드 배포다.

### 11.4 혼자(단말 1대 기준) 통신 완결 검증 절차 — 산속·무인 환경용

> 전제: "신호만 받음"은 시그널링(WebSocket/HTTPS 443)은 되는데 **미디어(UDP)** 가 안 흐른다는 뜻. 따라서 검증의 핵심은 **외부 망에서 미디어 UDP 도달 여부** 하나다. 아래 A는 사람 1명·단말 1대로 그걸 직접 판정한다.

> 구조 사실: 서버측 aiortc 피어는 `recvonly`(상행 수신만)라 **양방향 통화 브리지가 아니다**. 실제 두 단말 음성은 **phone↔phone P2P(시그널링 서버는 SDP 중계만)**. 따라서 **2폰 실측이 진실의 기준**이고, 폰 1대로는 완결 판정 불가(A는 그 사전 게이트).

**A. 미디어 평면 도달성 사전 게이트 (노트북 1대, 폰 테더링)**
1. 폰 **모바일 데이터(LTE/5G)** 로 노트북 테더링. ※ 서버 업링크와 **다른 통신사/회선**이어야 '원거리'.
2. 노트북에서 (PowerShell, 한 줄 — 시크릿은 `coturn/.env` 의 `TURN_SECRET` 값):
   ```powershell
   $env:TURN_SECRET="<coturn/.env 의 TURN_SECRET>"; python scripts/verify_turn_relay.py --base-url https://metanova1004.com --turn turn:211.218.172.124:3478 --allocate
   ```
3. 판정: **3줄 PASS**(backend_health / turn_relay / turn_allocate) → 그 망에서 미디어까지 도달. `turn_allocate`만 FAIL → 미디어 UDP 레인지(49160-49200)가 라우터/ISP에서 막힘(아래 C).

**B. 실제 양방향 음성 — 진짜 원거리 (폰 2대, 서로 다른 통신사) ★기준**
- 폰A = **SK 모바일데이터**, 폰B = **KT 모바일데이터**(서로 다른 통신사 = 진짜 원거리). 또는 한쪽 wifi.
- 두 폰에 **build 170(v1.0.118) 이상** 설치(인앱 업데이트). `VOIP_FORCE_RELAY=1` 이라 양쪽 모두 **릴레이 경로만** 사용 → 같은 방 테스트와 **동일 경로**. 양방향 음성이 들리면 지역 무관 동일 결과 확정.
- 기존 빌드로도 1차 가능(직결 실패 시 릴레이 폴백). build 170 은 그 경로를 **강제**해 "지정 폰만 됨" 거짓통과를 원천 차단.

**C. A/B 가 FAIL 일 때 — 단 하나의 조치 (서버 작업, 코드 아님)**
- 공인 IP 직결이면 불필요. 라우터/방화벽 뒤면 아래 UDP를 외부 공개(포워딩):
  - `3478/udp`, `3478/tcp` (TURN 시그널)
  - `49160-49200/udp` (미디어 릴레이 레인지)
- 적용 후 A를 재실행 → 모두 PASS 면 베타/데모 구동 가능 상태.

**D. 신규 빌드(force-relay 클라 바인딩) — build 170 발행 완료 (2026-06-22)**
- 실제 배포 경로는 **로컬 Gradle + 인앱 업데이터**(EAS 클라우드 아님): `pwsh scripts/publish_worldlinco_apk.ps1` → `uploads/marketplace_local/apk/` 에 APK·매니페스트 발행 → 폰이 인앱 업데이트.
- 발행됨: **v1.0.118 / versionCode 170** (`/api/marketplace/apk/worldlinco/manifest` 가 170 반환 확인). 두 테스트 폰에서 인앱 업데이트로 받으면 됨.
- 다음 빌드 시: `app.json` 의 `version`/`android.versionCode` 만 올리고 위 스크립트 재실행.

### 11.5 중·장거리 "받으면 끊김" 대책 — ICE 자동 재연결 (build 171, 2026-06-22)

> 베타 목적은 **실제 원거리 통화 시 (1) 연결 유지 (2) 통역 음성 정상 전달**. USB 테더링 근거리 테스트는 이 문제를 재현하지 못한다(사장님 직접 근거리 OK 확인 완료).

**진단(실측 근거):**
- 신호(WebSocket)·DNS(`metanova1004.com→211.218.172.124`, 공인 8.8.8.8/1.1.1.1 확인)·TURN_SECRET·force-relay·coturn 설정 **모두 정상**.
- relay-only(`ice_transport_policy:relay`, `auto_relay_applied:true`) 통화가 교차 통신사 셀룰러에서 **연결 성공 + 한국어 STT 정상**(`detected=ko transcript='지금 현재 음성 테스트 중입니다'`) → **릴레이 미디어 경로/공유기 포워딩 정상 입증**.
- 기존 "엉뚱한 말"의 원인 = **단말 지정 언어가 ja(일본어)** 오설정(한국어를 일본어로 강제 인식). 단말 언어를 본인 언어로 지정하면 해소.
- **남은 코드 결함**: `oniceconnectionstatechange` 가 상태를 알리기만 하고 `disconnected/failed` 시 **복구를 안 함** → 장거리 LTE 경로 변동/일시 손실에서 ICE 가 끊기면 그대로 통화 종료("받으면 끊김").

**조치(코드, `apps/mobile-nadotongryoksa/src/services/voipCallClient.ts`):**
- ICE `disconnected` → **2.5s 자가회복 유예** 후에도 미복구면 재시작. `failed` → 즉시 재시작.
- 재시작 = `restartIce()` + `createOffer({iceRestart:true})` 재협상(offerer='caller'만 수행해 글레어 방지). callee 는 통화 유지하며 caller 의 재시작 offer 를 기존 `handleOffer` 로 재협상.
- 최대 **4회 백오프(2/4/6/8s) 재시도**, **재연결 중에는 통화를 끊지 않고 'connecting' 으로 유지**(`getPeerConnectionState`) → 예산 소진 시에만 terminal 노출.
- `VoIPCallConfig.participantRole` 추가, `VoIPCallScreen` 에서 주입. `hangup()` 에서 타이머/플래그 정리.

**발행: v1.0.119 / versionCode 171** (`pwsh scripts/publish_worldlinco_apk.ps1`, BUILD SUCCESSFUL, 인앱 매니페스트 반영). 원격 폰 인앱 업데이트 후 실제 원거리 통화로 검증.

**원거리 실측 절차(단말별 본인 언어 지정 필수):**
1. 두 폰 모두 build 171 로 업데이트.
2. 각 폰의 "🌐 통역 지정 언어(이 단말)" 를 **그 폰 사용자의 실제 언어**로 지정(예: 한국어 화자=ko, 영어 화자=en). 두 폰을 같은 언어로 두면 통역 의미 없음.
3. 서로 다른 지역/통신사에서 통화 → 통역 음성/텍스트 전달 + 끊김 여부 확인. 일시 끊김은 자동 재연결로 복구되어야 함.

### 11.6 언어 실시간 저장 · 채팅 WS 복구 · 통화 추적 · 풀셋팅 (build 172, 2026-06-22)

**(1) 언어/국가 변경 → 백엔드 실시간 저장 (요청: 매번 복잡 과정 없이 즉시 반영)**
- 백엔드는 이미 `PATCH /api/auth/me` 로 `preferred_language`/`country_code` 실시간 저장(`backend/auth_router.py::update_me`). 가입 시 기본값 설정 + 이후 수동 변경 모두 지원.
- **결함:** 모바일 "🌐 통역 지정 언어(이 단말)" 선택(`handleSelectVoipLocalLang`)이 **로컬 AsyncStorage 에만 저장**하고 백엔드 미반영 → 상대 단말이 읽는 `preferred_language` 가 안 바뀜.
- **조치(`apps/mobile-nadotongryoksa/App.tsx`):** 언어 선택 시 ① 즉시 로컬 반영(오프라인 대비) ② `callUpdateMeApi`(PATCH /me)로 **백엔드 실시간 저장** + `userInfo`/저장 인증상태 갱신. 별도 "프로필 저장" 단계 불필요(탭 한 번).

**(2) 채팅 끊김 복구 — nginx WebSocket 업그레이드 헤더 (서버, 코드 아님)**
- **근본 원인:** 채팅 WS(`/api/mobile/chat/rooms/{id}/ws`)에 nginx 전용 location 이 없어 일반 `location /api/` 로 빠짐 → 그 블록엔 `Upgrade`/`Connection` 헤더가 없어 **WS 핸드셰이크가 101 로 승급 못 함 → 채팅 즉시 끊김**. (VoIP 시그널링은 전용 블록이 있어 정상.)
- **조치(`nginx/nginx.conf/nginx.conf`):** 두 HTTPS 서버 블록(`metanova1004.com` 포함)에 `location ^~ /api/mobile/chat/` 추가 — `Upgrade`/`Connection`/`Sec-WebSocket-*` 헤더 전달. `nginx -t` 통과 + `nginx -s reload` 적용.
- **검증:** `curl.exe` WS 핸드셰이크 프로브 → **403**(잘못된 토큰 거부; 라우트 도달) 반환. 수정 전이라면 업그레이드 미전달로 404/426. = 업그레이드가 백엔드 WS 핸들러까지 정상 도달.

**(3) 통화 이력 추적기 — `scripts/voip_call_trace.ps1` (신규)**
- 백엔드 컨테이너 로그에서 통화 이벤트만 추려 **[신호]/[음성]/[텍스트]/[통화]** 로 분류·집계. "신호 가는지 / 음성 통역 되는지 / 텍스트 전달 되는지" 한 화면 확인.
- 실시간: `pwsh scripts/voip_call_trace.ps1 -Follow` · 특정 통화: `-CallId <id>` · 요약: 기본(최근 30m). 소스 마커: `[VoIP] Signal relayed|App signaling`, `voice_translation`, `[voice-stt]`, `[voice/synthesize]`, `chat_message`, `Call ended(quality=...)`.

**(4) 시스템 풀 셋팅 재점검:** backend(healthy)·postgres·redis·qdrant·minio·coturn·nginx·marketplace·vllm·interpreter **모두 정상**. (`llm-nginx`/`llm-web-ui` 재시작 중인 건 별도 LLM 스택, 통역앱 무관.)

**발행: v1.0.120 / versionCode 172** — ICE 자동 재연결(11.5) + 언어 실시간 저장 포함. 채팅 복구·추적기는 서버측이라 빌드 불필요(즉시 적용).

---

## 12. 통역 통화 재설계 — "무전기" → 실시간 연속 음성대화 (설계 SSOT, 2026-06-22)

> 사장님 실측 피드백: "빨간 녹음 보고 말하기가 무의미, 거리 멀수록 음성 전달 안 됨, 양쪽이 무전기처럼 설정된 느낌, 통신을 타고 가는 느낌이 없다." → **방향 확정: 실시간 음성대화. 잘못된(무전기) 구현은 갈아엎되, 본 설계(§12) 기준으로 교체.**

### 12.1 근원지 (코드 확정)

| # | 사실 | 근거(파일) |
|---|------|-----------|
| R1 | 앱-앱 통화는 `requested_mode` 가 **자동 `voip_full_auto`** 로 결정됨 | `nadotongryoksa_voip_router.py` `_normalize_call_mode` (`return "voip_full_auto" if has_app_target`) |
| R2 | `auto_relay_applied = auto_relay_requested & resolved_mode==voip_full_auto & app_call` | 동 파일 call-init |
| R3 | 앱은 `voiceRelayServerReady`(=auto_relay_applied‖voip_full_auto)면 **voiceRelay 자동 ON** | `VoIPCallScreen.tsx` (auto-enable effect) |
| R4 | voiceRelay ON → **원격 원음 WebRTC 트랙을 영구 음소거** | `voipCallClient.ts` `remoteAudioSuppressed`(주석: "영구히 음소거"), `VoIPCallScreen` 억제 effect |
| R5 | 캡처 = **세그먼트(빨간 녹음) + 엄격 턴 잠금**: `remoteListenHoldMs=2600`, `fairnessBargeInMs=7000`, 캡처 중 로컬 마이크 suspend | `voiceRelayTurnController.ts`, `voipCallClient.ts` `suspendLocalAudioForRelay` |
| **R6** | **STT 가 클라이언트(각 폰 마이크 녹음→업로드)에서 일어남.** 서버 aiortc 피어는 `recvonly`로 받기만 하고 STT 미수행 | `nadotongryoksa_voip_router.py` `addTransceiver("audio","recvonly")` (track 소비/STT 없음), `VoIPCallScreen.tsx` 세그먼트 업로드 |
| **R7** | **(결정적) STT 녹음을 위해 WebRTC 마이크를 정지시킴** — `suspendLocalAudioForVoiceRelay()`. 모바일은 expo-av 녹음과 WebRTC 가 같은 마이크를 동시 점유 못 하므로, 통역 중 양쪽 업링크가 꺼져 **라이브 음성 자체가 흐를 수 없음.** → 무전기는 버그가 아니라 클라-STT 구조의 강제 결과. **클라 단독 라이브 듀플렉스 불가** | `VoIPCallScreen.tsx:~2246` |

**결론:** 들리는 소리가 **번역문 TTS 토막뿐**(원음 영구 차단) + **반이중 턴제** + **세그먼트 단위** → 구조 자체가 무전기. 거리 악화는 세그먼트가 약전계에서 **문장 통째 유실**되기 때문(연속 오디오면 잠깐 글리치로 끝남). 두 "relay"(① `VOIP_FORCE_RELAY`=TURN 전송 ② `auto_relay`=통역 세그먼트)가 별개인데 이름이 겹쳐 경로가 헷갈림.

> **핵심(R6 함의):** 무전기 음소거가 존재하는 *진짜* 이유 = STT 가 **클라이언트 마이크** 기반이라, 라이브 원음을 스피커로 틀면 마이크가 상대 목소리/자기 TTS 를 다시 주워 STT 가 오염·에코됨. 따라서 **완전한 실시간화의 정답은 STT 를 서버측 레그별 오디오 탭으로 이전**하는 것(각 레그 업링크 = 그 화자의 깨끗한 음성). 그러면 클라는 라이브 원음을 끊을 필요가 없어진다. → 아래 P-server 가 본 교체의 핵심.

### 12.2 목표 구조 — 라이브 풀듀플렉스 + 통역 오버레이

1. **라이브 음성 항상 ON.** 원격 WebRTC 원음을 **절대 영구 음소거하지 않는다.** 두 사람의 실제 목소리가 연속으로 흐름 = 진짜 통화, 거리 악화 시 graceful degrade.
2. **STT 는 게이트가 아니라 병렬 탭(passive tap).** 마이크·원음을 **음소거하지 않고** 연속 캡처해 STT. 에코는 WebRTC AEC(이미 `echoCancellation:true`)로 처리.
3. **턴 잠금 제거.** `remoteListenHoldMs`/`fairnessBargeIn` 의 캡처 차단 게이트를 끈다(연속 캡처). dedupe + 짧은 에코 가드(자기 TTS 꼬리)만 유지.
4. **통역 = 오버레이.** 자막 텍스트는 항상 표시. TTS 는 선택(기본 자막, TTS 시 라이브 볼륨 일시 덕킹)으로 두 목소리 충돌 완화.
5. **모드 의존 음소거 제거 → 단일 일관 경로.** `voip_full_auto` 는 "자막 오버레이 활성" 의미일 뿐, 상대 목소리를 끊지 않는다.

### 12.3 단계 (체크리스트)

**Phase 1 — 클라이언트 라이브 듀플렉스(중간 단계, 즉시 체감용). 플래그 `voip.live_duplex_mode` 로 안전 토글.**
- [ ] **P1-flag** `worldlincoTuningConfig.ts` 에 `voip.live_duplex_mode`(기본 ON) 추가 — 한 스위치로 라이브 모드 on/off(회귀 시 즉시 복귀).
- [ ] **P1-client** `voipCallClient.ts`: live_duplex 시 `remoteAudioSuppressed` 영구 억제 **미적용** — 원격 원음 `enabled=true` 유지(라이브 다운링크는 WebRTC AEC 로 마이크에서 상쇄됨). `suspendLocalAudioForRelay`(마이크 stop) 미사용.
- [ ] **P1-turn** `voiceRelayTurnController.ts`: live_duplex 시 `isVoiceRelayListenActive` 캡처 차단 무력화(연속 캡처), `remoteListenHoldMs`→짧은 에코 가드. dedupe/echo-window 유지(자기 TTS 꼬리 방지).
- [ ] **P1-screen** `VoIPCallScreen.tsx`: live_duplex 시 `setRemoteAudioSuppressed(true)` 경로 스킵(원음 유지), 캡처 중 마이크 mute 제거, 자막 오버레이 상시.
- [x] **P1-flag/turn/client/screen** 구현 완료(플래그 게이트). 단 **기본값 0(휴면)** — R7 때문.
- ⛔ **한계(R7, 결정적):** 클라가 STT 녹음을 하려면 WebRTC 마이크를 정지하므로, **클라 단독으로 live_duplex=1 을 켜면 라이브 음성이 흐르지 못한다.** 따라서 P1 스캐폴딩은 **P-server 이후에만 의미**가 있다(그때 클라가 마이크를 점유하지 않게 되면 1 로 승격). → **P1 단독 빌드는 무의미, 건너뛰고 P-server 로 직행.**

**P-server — 본 교체의 핵심(서버측 레그별 STT). 무전기 구조를 근본 제거.**
- [ ] **PS-1** `nadotongryoksa_voip_router.py` aiortc `recvonly` 피어가 **각 레그 오디오 트랙을 실제 소비**(`@peer.on("track")` → 리샘플 48k→16k → 청크 버퍼).
- [ ] **PS-2** 서버 스트리밍 STT(faster-whisper) 로 레그별 깨끗한 업링크 음성을 전사 → 번역 → **상대 레그로 `voice_translation` 푸시**(클라 마이크 STT 대체).
- [ ] **PS-3** 클라는 STT/세그먼트/턴 로직 제거, **라이브 원음 + 서버 자막/TTS 수신만**. 무전기 잔재 0.

**P2(후속)** TTS 덕킹(재생 중 라이브 볼륨↓) + UI "빨간 녹음" → "통역 자막 ON" 패시브 인디케이터.
**P3(선택)** 부분 결과(partial) 스트리밍으로 자막 지연 추가 단축.

### 12.4 수용 기준(DoD)

1. 앱-앱 통화 중 **양쪽이 상대 실제 목소리를 연속 청취**(원격 트랙 `enabled` 가 통화 내내 true — 로그/getStats 확인).
2. 마이크 잠금 없이 **자막이 연속 갱신**(한쪽이 길게 말해도 상대가 끼어들 수 있음).
3. 한 폰을 멀리 이동 시 **문장 통째 무음 없이** 부분 글리치로만 저하.
4. 어떤 모드에서도 **원음을 영구 음소거하는 경로가 존재하지 않음**(grep 가드).
5. `scripts/voip_call_trace.ps1` 로 신호/음성/텍스트 전달이 동시에 관측됨.

### 12.5 구현 선택 결정 — 확장·최적화 기준 (단일 서버 가정 금지) (2026-06-22)

> 정책: **단일 RTX 5090 로컬 서버에 묶인 구현 금지.** 서버 사양은 증설 예정이고 서버 구축은 최적화한다.
> 따라서 코드는 처음부터 이상 설계(멀티리전 Anycast + SFU + Whisper/NLLB/FastSpeech + Optuna/관측)의 **컴포넌트 경계를 코드 경계로** 채택한다. 증설(다노드·다리전)은 **코드 재작성이 아니라 배포/설정 변경**으로 끝나야 한다.

**핵심 원칙 — 인프로세스 결합 금지:**
- 미디어 / Signalling / ASR / MT / TTS / Cache / Metrics 를 **각각 독립 (마이크로)서비스**로. 단일 프로세스 내장 금지.
- ASR/MT/TTS 는 **stateless GPU 서비스**로 분리 → GPU 풀에 다노드 수평 확장. (1차 배포는 현 서버에 공존, 증설 시 노드로 분산만.)
- 모든 서비스 엔드포인트는 **환경변수/서비스 디스커버리** 기반. `localhost`/특정 호스트 하드코딩 금지.
- 미디어 평면은 **SFU 지향 구조**로 설계(현 aiortc `recvonly` 탭을 SFU/미디어서비스로 승격 가능하게). 호출당 수평 확장 가능해야 함.

**채택(=기능 핵심):** 이상 설계의 **"media-tap → 서버 ASR + 원본/번역 멀티트랙"** = 본 문서 **P-server**.
- 이상 설계 ④⑥⑦(미디어에서 RTP를 ASR로 복제, 채널0 원본 + 채널1 번역 동시 재생)이 현재 빠진 조각.
- 단, P-server 의 STT/MT/TTS 는 **API 내장이 아니라 독립 GPU 서비스 호출**로 구현(확장 대비).

**단계적(코드는 풀설계, 배포는 점증):**
- 1차 배포: 현 서버 1대에 분리된 서비스들을 함께 기동(Compose). 코드엔 단일 서버 가정 없음.
- 증설 시: Helm/Compose 의 replica·노드 배치만 변경 → 멀티노드. 이후 멀티리전/Anycast/Active-Active/Optuna 튜닝 활성화.

**KPI 설계선:** 라이브 오디오 e2e ≤300ms·MOS≥4.2(WebRTC Opus). 통역 오버레이(STT+MT+TTS)는 라이브와 **분리**되어 뒤따름 → 실시간 통화감은 라이브 트랙이 보장.

**다음 착수:** PS-0(미디어 토폴로지 확정: mobile↔server vs P2P, SFU 승격 경로 결정) → PS-1(레그 track 소비, 미디어서비스 경계 정립) → PS-2(독립 ASR→MT→TTS 서비스 파이프라인, 상대 레그 푸시) → PS-3(클라 로컬STT 제거, 라이브+오버레이).

---

## 13. 서버 미디어 브리지(MCU) + 스트리밍 동시통역 — 정식 상품 설계 SSOT (2026-06-22)

> 정책 재확인: "장난감"이 아닌 **정식 상품(통신기기 탑재 / OEM 하드웨어 탑재 가능)**. 단일 서버 가정 금지, 처음부터 확장·최적화 구조.

### 13.1 PS-0 코드 실측 — 근본 원인 (확정)

`backend/marketplace/nadotongryoksa_voip_router.py` 정독 결과:
- **실제 통화 = 순수 P2P(앱↔앱).** 시그널링 핸들러(`call_participants` 경로, L2470~)는 offer/answer/candidate 를 `_relay_app_signal` 로 **상대 폰에 중계만** 한다. **미디어(RTP)는 폰↔폰 직결**(TURN relay 경유). 서버는 미디어 경로에 **없음**.
- `voice_translation`(L2586) 메시지 = **클라가 STT/번역한 텍스트**를 서버가 그대로 relay. → "무전기"의 근본(R6 확정).
- aiortc `recvonly` 피어(L2649~, `connected_clients` 경로)는 실제 통화에 연결 안 됨 + track 소비 안 함(죽은/단일레그 경로). **게다가 `aiortc` 가 `requirements.txt` 에 없음** → 운영 백엔드에 미설치(`try/except`→`None`). 즉 서버는 통화 오디오를 **한 번도 본 적 없음**.

**결론(정직):** 현 P2P 구조로는 서버측 STT/동시통역이 **원천 불가**. 미디어를 반드시 **서버 경유(MCU 브리지)** 로 바꿔야 한다.

### 13.2 목표 구조 — MCU 미디어 브리지 + AI 탭

```
[폰 A] ──(WebRTC sendrecv, SRTP)──► [서버 MediaBridge] ◄──(WebRTC sendrecv)── [폰 B]
                                         │  │
            A 업링크 ─MediaRelay─────────┘  └──────── B 업링크
                 │  (연속 라이브 오디오: A→B, B→A 그대로 포워딩 = 통화감/거리무관)
                 ▼
            [AI 탭/레그]  48k→16k 리샘플 → VAD/endpoint → STT → 동시MT → (자막 push / TTS 트랙 주입)
```

- **라이브 경로(즉시, ≤300ms):** 서버가 A 업링크를 B 다운링크로, B를 A로 `MediaRelay` 포워딩. 양쪽이 **상대 실제 목소리를 연속 청취**. 마이크 잠금/원음 음소거 **영구 제거**. 거리 무관(서버가 안정적 허브, 공인 도달성은 서버 구축에서 최적화).
- **통역 오버레이(뒤따름, ear-to-ear 1.5~3s):** 각 레그 업링크를 탭 → STT→MT → 상대에게 **자막(data) + 선택적 TTS 트랙**. 라이브와 분리되므로 통화감 손상 없음.

### 13.3 컴포넌트 경계(독립 서비스, §12.5 준수)

| 모듈 | 역할 | 위치 | 확장 |
|---|---|---|---|
| MediaBridge | 2-레그 WebRTC 종단 + MediaRelay 포워딩 + 탭 | `backend/voip/media_bridge.py` (신규) | 호출당 인스턴스 → 다노드 SFU 승격 경로 |
| Interpret Pipeline | buffer→endpoint→STT→MT→emit | `media_bridge` 내 탭 소비자(추후 별 서비스 분리) | STT/MT/TTS 는 호출형(환경변수 엔드포인트) |
| STT/MT/TTS | 실제 추론 | `voice_gateway._run_faster_whisper`, `translator.translate`, `_synthesize_tts` 재사용 → 차후 독립 GPU 서비스 | GPU 풀 수평확장 |

### 13.4 단계 (체크리스트)

- [x] **MB-0** `requirements.txt` 에 `aiortc>=1.9.0`, `av>=12.0.0`, `numpy` 추가. lazy import 가드 유지(미설치 시 `is_available()`=False → P2P 폴백). 로컬 env 확인: `available=True`.
- [x] **MB-1** `backend/voip/media_bridge.py`: `CallMediaBridge`(2 레그 `RTCPeerConnection`, paced queue 트랙으로 A↔B 오디오 연속 포워딩, renegotiation-free, 비-트리클 ICE 대기). 플래그 `VOIP_SERVER_MEDIA_BRIDGE`(기본 OFF → 회귀 안전).
- [x] **MB-2** 레그별 **AI 탭 소비자**(`_InterpretTap`): 48k→16k 리샘플 + RMS/무음갭 endpoint → 세그먼트 WAV → `_run_faster_whisper`(executor) → `translator.translate` → 상대 레그로 `voice_translation`(자막) emit. (TTS 트랙 주입은 MB-4.)
- [x] **MB-3** 시그널링 라우터(`nadotongryoksa_voip_router.py`) 서버 브리지 모드: 플래그 ON 시 offer→`bridge.handle_offer`(서버 answer), candidate→`bridge.add_ice_candidate`, 클라 `voice_translation` 무시, hangup/disconnect 시 `_close_bridge`. **플래그 OFF 시 기존 P2P 경로 그대로**(예외 시도 P2P 폴백). 컴파일·import 검증 완료.
- [x] **MB-4** TTS 트랙 주입(`CallMediaBridge._inject_tts`): 번역 텍스트 → `_synthesize_tts`(executor) → `_decode_to_48k_mono_frames`(av MP3 디코드/리샘플) → 상대 레그 다운링크 큐 push(원음+번역 멀티트랙). 플래그 `VOIP_BRIDGE_TTS`(기본 ON). **에코 가드**: 주입 중+꼬리(`tts_guard_until`) 동안 해당 레그 탭 억제(자기 번역음 재통역 루프 차단). import 검증 완료.
- [x] **MB-5** 클라 전환: `worldlincoTuningConfig.ts` 에 `setVoipServerBridgeActive`/`isVoipServerBridgeActive`/`isLiveDuplexActive` 추가. `voipCallClient.ts` 가 서버 answer(`from_role='server_bridge'`) 수신 시 브리지 모드 ON(hangup 시 OFF). `VoIPCallScreen.tsx`: `live_duplex_mode===1` 인라인 체크를 `isLiveDuplexActive()` 로 교체(원음 영구 억제 미적용·연속 캡처 동작이 브리지 모드에서 자동 활성), `startVoiceRelaySegment` 최상단에 `isVoipServerBridgeActive()` 가드로 **로컬 STT 캡처/마이크 점유 전면 중단**. 클라 `voice_translation` 송신 경로는 도달 불가(이중 안전: 서버도 MB-3 에서 무시). lint: 신규 오류 0(기존 `Audio` 네임스페이스 경고만).
- [~] **MB-6** 서버 구축 완료(실통화만 남음). 실측 검증:
  - 이미지 재빌드 OK — 컨테이너 내 `aiortc 1.14.0 / av 16.1.0 / numpy 2.5.0`. `requirements.delivery.lock.txt` 실측 버전 고정.
  - 컨테이너 내 `media_bridge.is_available()=True`, 플래그 `VOIP_SERVER_MEDIA_BRIDGE=1` 활성(`.env` + compose).
  - **공인 도달성 OK**: 서버 aiortc 가 coturn 에 TURN 릴레이 할당 성공 → 릴레이 주소 `211.218.172.124:49162`, 후보 타입 `host/srflx/relay`(HAS_RELAY=True). NAT 뒤 서버도 미디어 수신 가능.
  - **운영 픽스 2건**:
    (1) 백엔드 컨테이너 안에서 `metanova1004.com`→`127.0.0.1` 로 잡혀 서버 TURN 클라이언트가 자신을 가리키던 문제 → compose `backend.extra_hosts: "metanova1004.com:host-gateway"` 로 coturn(호스트 3478) 도달.
    (2) 쉘 세션의 잔류 `TURN_SECRET=x` 가 compose(.env)보다 우선해 컨테이너에 잘못된 시크릿이 주입 → coturn 401(`Cannot find credentials`). 쉘 오버라이드 제거 후 정상(allocate 성공). **교훈**: `docker compose` 는 쉘 env > .env 이므로 배포 전 `docker compose config | grep TURN_SECRET` 로 확인.
  - [ ] **남은 1단계(사용자 협업)**: 모바일 앱을 MB-5/MB-7 반영분으로 재빌드 → 실통화. 통화 중 서버 answer/offer(`from_role='server_bridge'`)로 클라가 브리지 모드 진입 → 라이브 연속 음성 + 서버 자막/TTS. `scripts/voip_call_trace.ps1 -Follow` 로 [신호]/[음성]/[텍스트] 동시 관측하며 DoD(§12.4) 확정.
- [x] **MB-7 (2026-06-22, 실통화 무음·무자막 근본 원인 픽스)** — "신호·전화받기는 되는데 음성/텍스트가 안 감"의 정확한 원인은 **MCU 연결 토폴로지 누락**이었다.
  - 원인: MB-3 은 caller offer→서버 answer 만 처리. 그러나 callee 는 P2P 습관상 **offer 를 기다리기만** 하고 스스로 offer 하지 않는데, 서버가 caller offer 를 소비(중계 안 함)하므로 **callee 레그가 서버와 영영 연결되지 않음** → 양방향 미디어/탭 경로 미생성.
  - 픽스 ① 서버가 callee 에 **offer 를 보낸다**: `CallMediaBridge.create_offer_for(role)` + `handle_answer(role, sdp)` 추가. callee 시그널링 접속 시 서버가 `from_role='server_bridge'` offer 전송, callee 의 기존 `handleOffer→answer` 경로 재사용, answer 는 `bridge.handle_answer` 로 적용. (caller=서버 answerer, callee=서버 offerer 비대칭이지만 두 레그 모두 서버 종단.)
  - 픽스 ② `handle_offer` 의 `addTrack` 순서 교정: **setRemoteDescription(offer) → addTrack(downlink) → createAnswer**. 트랙을 remote 전에 붙이면 별도 트랜시버 생성으로 m-line 불일치 → 미디어 깨짐. (answerer=remote 우선, offerer=track 우선으로 분리.)
  - 픽스 ③ 같은 언어(ko=ko) TTS 에코 제거: `from_lang==to_lang` 이면 라이브 육성이 이미 그대로 전달되므로 TTS 재합성 생략(자막만). 언어 상이 + 번역 결과 있을 때만 TTS 주입.
  - 클라(MB-7): `voipCallClient.ts` `case 'offer'` 에서도 `from_role==='server_bridge'` 면 브리지 모드 ON(callee 는 answer 가 아니라 offer 로 진입하므로 필수). 컴파일·lint 신규 오류 0.
- [x] **MB-8 (2026-06-22, 미디어 정책 확정 — 사장님 결정)** — **통번역(다른 언어) 통화에서는 원본 육성을 상대에게 전달하지 않는다.** 알아듣지 못하는 원어 육성과 번역 음성(TTS)이 겹치는 것을 방지.
  - 구현(`media_bridge._consume_uplink`): 레그 언어로 `_is_cross_language(src,tgt)` 판정 → **같은 언어/미지정이면 원음 포워딩(육성 통화, TTS 없음)**, **다른 언어면 원음 차단**(다운링크엔 TTS 번역음+자막만). `_lang_primary` 로 `ko-KR`/`en_US` 등 정규화. 한쪽이라도 `auto`(미지정)면 무음 방지 위해 원음 통화로 안전 폴백.
  - 효과: 정책이 상호배타로 깔끔해짐 — 육성 통화(원음만)·통번역 통화(번역음만). v1 한계: 통번역 시 발화→TTS 사이 지연 구간엔 상대가 잠시 무음(스트리밍 ASR/증분 TTS 로 §13.5 에서 단축). 필요 시 원음을 낮은 볼륨으로 더킹하는 옵션은 후속.
- [x] **MB-9 (2026-06-22, 실통화 2차 — 통번역 음성 무전달 + 광고/환각 혼선 픽스)** — SK폰↔KT탭 실측 후 진단·수정.
  - **근본원인 A (통번역 음성 전혀 안 들림)**: 다운링크 큐 `maxsize=50`(=1초)에 멀티초 TTS 프레임(예: 3.66s=183프레임)을 **한꺼번에 push** → 오버플로로 **마지막 ~1초만 남고 잘림**. 교차언어는 원음 차단(MB-8)이라 사실상 무음. **픽스**: `_inject_tts` 를 ~실시간(18ms) **페이싱 주입**으로 변경 + 큐 150 확대 + `[bridge] tts injected` INFO 로그. (synth/decode 자체는 정상 — 컨테이너 실측 mp3 23KB/183프레임 확인.)
  - **근본원인 B (감사합니다/배달의민족 잡음)**: 1초 미만 노이즈/광고 버스트가 STT 로 유입 → Whisper 환각 상투구. **픽스**: ① 엔드포인터 게이트 상향(`RMS 280→420`, `MIN_SPEECH 350→550ms`), ② 환각 블록리스트 `_is_hallucination`(감사합니다/ご視聴…/thank you/구두점-only 등) 폐기, ③ Whisper 내장 Silero VAD ON(`WHISPER_VAD_FILTER=1`, compose+.env).
  - **단방향 통역(caller→callee=0)**: 원인 후보 = SK폰 삼성 Freecess 앱 동결(logcat `freeze com.parkcheolhong.worldlinco` 6초 주기) → 마이크/업링크 중단. 클라(build174)에서 통화중 포그라운드 서비스 + 배터리 최적화 예외로 해결 예정.
  - **광고 사운드 통화 방해**: 통화 활성 동안 광고 음소거/중단 — 클라(build174).
  - 적용: 백엔드 recreate(`compose up -d backend`) 완료, health 200, `WHISPER_VAD_FILTER=1` 컨테이너 반영, `_is_hallucination('감사합니다')=True` 실측. **남음**: 클라 build174(광고 음소거 + 동결 방지).
- [x] **MB-10 (2026-06-22, 실통화 3차 — 2중창 울림 + 발화 유실(10마디 중 2마디) 픽스)** — 양 기기 2중창 + 비실시간 전달 진단·수정.
  - **근본원인 A (2중창 울림)**: 브리지 모드에서 **서버가 다운링크에 TTS 주입**(MB-4/9) + **클라(build173)가 `voice_translation` 자막을 받아 `synthesizeSpeech`/`Speech.speak` 로 같은 번역을 또 재생** → 같은 번역음이 두 번(서버 스트림 + 클라 자체 재생) = 2중창·자기에코 재흡수. **픽스(무빌드 즉시)**: `VOIP_BRIDGE_TTS=0` — 서버 TTS 주입을 끄고 번역 음성은 클라가 1회만 재생(AEC 통합 네이티브 통화-렌더 경로). 서버는 포워딩 + STT/번역 + 자막 emit 담당.
  - **근본원인 B (10마디 중 2마디만 전달, 비실시간)**: MB-9 의 **페이싱 TTS 주입(3~5s)** + STT/번역이 모두 `feed()`→`_finalize_segment`→`_run_pipeline` 로 **업링크 소비 루프 내부에서 await** → 한 발화 처리(STT+번역+TTS, 수 초) 동안 `track.recv()` 미호출 → 그 사이 발화가 유실·지연. **픽스**: `_InterpretTap` 에 **세그먼트 큐 + 백그라운드 워커(`_segment_worker`)** 도입 — 소비 루프는 읽기/포워딩/엔드포인팅만(비블로킹), 확정 세그먼트는 큐로 넘겨 워커가 직렬 STT→번역→emit 처리. 큐 가득 시 oldest drop(지연 누적 방지), `flush()` 는 종료 시 최대 3s 드레인, `close()` 로 워커 취소.
  - 적용: 백엔드 `compose up -d --force-recreate backend` 완료, health 200, `VOIP_BRIDGE_TTS=0` 컨테이너 반영, startup clean(미디어 브리지 import 오류 없음). **build174 전환 예정**: 서버주입 TTS 재활성(`VOIP_BRIDGE_TTS=1`) + 클라 자체 TTS 억제(`isVoipServerBridgeActive` 시 voice_translation 자막-only) → OEM/덤클라 대응 product 경로 일원화.

- [x] **MB-11 (2026-06-22, build174 — 서버주입 TTS 일원화 + 광고 음소거 + Freecess 동결 방지)** — 사장님 지시 정식 경로.
  - **서버주입 TTS 일원화 + 무경합 롤아웃**: 클라가 브리지 모드에서 `voice_translation` 을 **자막-only** 로만 처리(자체 TTS 재생/원격오디오 억제/에코판정 전부 skip, `VoIPCallScreen.tsx`). 번역 음성은 서버가 다운링크에 1회 주입 → 2중창 원천 제거. **레그별 능력 협상**: 클라(build174+)가 브리지 감지 시 `client_caps{server_tts:true}` 전송(`voipCallClient.announceBridgeCaps`), 서버는 `set_leg_wants_server_tts` 로 기록 후 **그 레그에만** TTS 주입(`media_bridge._inject_tts` 게이트). 신호 없는 구버전(build173)은 자체 재생 → 서버 미주입 → **버전 혼재 중에도 2중창 없음**. 마스터 `VOIP_BRIDGE_TTS=1` 복원.
  - **통화중 광고 음소거**: 앱에 광고 SDK 없음 → 외부 앱 미디어(예: "배달의민족")가 마이크로 음향 유입. 네이티브 `VoipAudioModule` 가 통화 시작 시 **오디오 포커스(`AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE`, `USAGE_VOICE_COMMUNICATION`)** 획득 → 다른 앱 재생을 일시중단/덕킹, 종료 시 abandon.
  - **삼성 Freecess 동결 방지**: 통화 화면 진입 시 **포그라운드 서비스(`VoipCallForegroundService`, type=microphone)** 시작 + **배터리 최적화 예외 요청**(`requestIgnoreBatteryOptimizations`), 종료/언마운트 시 stop. 매니페스트 권한(`FOREGROUND_SERVICE_MICROPHONE`, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`) + `<service>` 추가. → 백그라운드 동결로 인한 마이크/업링크 중단(단방향 통화) 방지.
  - 적용: 백엔드 recreate(`VOIP_BRIDGE_TTS=1`, health 200, startup clean), **로컬 Gradle 빌드 v1.0.122/build174 게시 완료(65.12MB, 마켓플레이스 자동업그레이드)**. **남음**: build174 자동업그레이드 후 통번역 실통화 재검증(2중창 0 + 양방향 음성 실시간 + 광고 무유입).

- [x] **MB-12 (2026-06-23, build174 4km 실통화 로그 리뷰 — 볼륨 상향 + 신뢰도 필터 오삭제 교정)** — 사장님 4km 장거리 통역 통화 후 로그 분석.
  - **로그 종합(call-abb4b5604a22)**: `interpret emit=137 / tts injected=137`(양방향 균형), **실제 에러 0 · 큐 폭주 0 · `leg failed=0`** — 거리가 늘어도 ICE/릴레이 안정(끊김 없음). 클린 teardown(`leg closed → tearing down → closed`). ("ERROR 2건"은 grep 패턴 echo + `error_code:null` JSON 오탐, 실에러 아님.)
  - **볼륨(사장님: "2배 이상 올려야")**: Edge TTS 가 이미 피크 풀스케일이라 피크 정규화는 게인 미적용 → 체감(RMS) 낮음. **픽스**: `_decode_to_48k_mono_frames` 에 **RMS 라우드니스 정규화(`TTS_TARGET_RMS≈0.28`, ≈-11dBFS) + 하드 피크 리미터(`TTS_TARGET_PEAK`/`TTS_MAX_GAIN`)** 추가 — 작은 발화도 일정 음량으로 끌어올리고 클리핑 방지.
  - **혼잣말 환각(사장님: "언제든지요/감사합니다")**: 노이즈→Whisper 환각. 1차로 STT 신뢰도 필터(`avg_logprob`/`no_speech_prob`) 도입.
  - **⚠ 로그가 드러낸 부작용 — 신뢰도 필터 오삭제(중요)**: `OR` 조건(`avg_logprob<-0.85 OR no_speech>0.55`)이 **실제 짧은 발화를 잘라먹음**. 로그 실측 폐기 예: `見たんですか?`(봤어요?, no_speech=0.57), `そうです`(0.94), `そうですか`(0.99), `조결이 국외너머까지…차를 돌려와야 됩니다`(0.93). 짧은 발화는 `no_speech_prob` 가 원래 높게 나오기 때문. **픽스**: `OR → AND`(`avg_logprob<-1.0` **AND** `no_speech>0.80`) — 텍스트 신뢰도 낮음 **그리고** 비음성 가능성 높음일 때만 폐기. 실제 발화는 보통 `avg_logprob` 가 양호해 생존, 노이즈 환각(둘 다 나쁨)만 컷. 알려진 상투구는 블록리스트(`_is_hallucination`)가 계속 처리.
  - **종료 후 stray emit 가드**: 로그 말미 `closed` 직후 1건 emit(`frames=0`) 관측 → `_InterpretTap._stopped` 플래그로 `_run_pipeline` 진입/emit 직전 차단(무해하나 클린업).
  - 적용: `media_bridge.py` 수정, lint 0. 백엔드 recreate 후 재검증 예정. **남음**: build174 4km 재통화로 (1) 볼륨 체감 2배↑ (2) 짧은 발화("그래요?/봤어요?") 정상 전달 (3) 환각 무유입 동시 확인.

- [x] **MB-13 (2026-06-23, 서버 브리지 런타임 튜닝 — 링코 튜닝샵에서 음량·대화템포 실시간 조정)** — 사장님 지시: "볼륨/대화 템을 관리자 대시보드에서 정밀 튜닝 + 현재값을 기본으로 + 로컬에서 직접 + 마켓 레일 링코에 실시간 반영."
  - **배경**: 기존 링코 튜닝샵 SSOT(`knowledge/worldlinco_tuning_config.json`, 매요청 read + 앱 라이브 fetch)는 **구 클라이언트 릴레이**(Silero VAD/에코가드)만 다뤘다. 신 서버 브리지(`media_bridge.py`)는 음량/템포 상수를 **import 시 env 로 1회** 읽어 런타임 조정 불가였다.
  - **SSOT 확장**(`worldlinco_tuning.py` + JSON): `voip_bridge` 섹션 신설 — `silence_gap_ms·min_speech_ms·max_speech_ms·rms_gate·tts_guard_tail_ms`(대화 템포/지연), `tts_target_rms`(핵심 음량)·`tts_target_peak`·`tts_max_gain`(라우드니스), `min_avg_logprob·max_no_speech_prob`(환각 필터). **현재 코드 기본값을 그대로 기본값으로** 고정. `WorldlincoVoipBridgeTuningUpdate`(bounds 검증) + 공개 payload 포함.
  - **런타임 반영**(`media_bridge.py`): 모듈 상수 → **TTL(2s) 캐시 getter `_bridge_cfg()`** 로 전환. endpointer(`feed/flush/_finalize`)·TTS 음량(`_decode_to_48k_mono_frames`)·에코가드·환각필터 모두 이 캐시를 읽음 → **통화 중에도 슬라이더 저장 후 ~2초 내 반영**(재시작/재빌드 불필요). SSOT 부재/파싱실패 시 코드 기본값 폴백(fail-safe).
  - **관리자 UI**(`admin-worldlinco-tuning-panel.tsx`): 링코 튜닝샵에 **🌉 서버 브리지(MCU) 통역** 섹션 추가(음량 핵심 노브 최상단 — 차량/원거리 0.40~0.55 권장 힌트). 저장 시 "통화 중 ~2초 실시간 반영" 안내. 기존 `/api/admin/worldlinco/tuning` PUT 경로 재사용.
  - 검증: 백엔드 recreate·health 200, 컨테이너 내 `_bridge_cfg()` 정상(0.28→0.5 파일변경→TTL 새로고침 반영→원복 실측), 단위테스트 `test_worldlinco_tuning.py` 4 passed. **사용법**: 관리자 대시보드 → 링코 → WorldLinco 튜닝 → 서버 브리지 섹션에서 `번역 음량` 올리고 저장 → 통화 중 즉시 커짐. **남음**: 사장님 4km 재통화로 음량 슬라이더 체감 확인.

- [x] **MB-14 (2026-06-23, build175 — 수신 팝업 받기/거절 + 양쪽 동시 종료 + 설정 허브(소리/진동/무음·국가/언어·비밀번호))** — 사장님 지시: 수신 시 받기/거절 팝업, 한쪽이 끊으면 양쪽 동시 종료, 상단 우측 설정 아이콘 + 소리/진동/무음·내정보(국가/언어)·비밀번호 변경.
  - **수신 팝업 모달(받기/거절)**: `App.tsx` 의 인앱 수신 surface 2종(`showIncomingVoipFixedPanel`/`showIncomingVoipBanner`)이 **하드코딩 `false`** 로 비활성 → 실제로 받기/거절 버튼이 어디에도 안 떴음(근본 원인). **픽스**: `hasPendingIncomingVoip(=pending && !active)` 로 구동되는 **앱 전역 `<Modal>` 수신 팝업** 신설(어느 레일/화면에 있어도 위에 표시, 받기→통화 진입·거절→`handleRejectIncomingVoipCall` 로 즉시 사라짐). 죽은 `showIncomingVoipFixedPanel` 변수 제거.
  - **양쪽 동시 종료**: 로컬 `voipCallClient.hangup()` 이 소켓을 닫기만 하고 **'hangup' 신호를 안 보냄** → 상대는 ICE/teardown 타임아웃에 의존(느림/불안정)이 근본 원인. **픽스**: `hangup(notifyPeer=true)` 가 소켓 닫기 전 `{type:'hangup'}` 송신 → 서버(`nadotongryoksa_voip_router.py`)가 이미 peer relay + 브리지 teardown 처리. 상대 수신 시 `onRemoteHangup` 콜백(일시적 ICE `disconnected` 와 구분되는 **확정 종료** 신호)으로 `VoIPCallScreen` 이 정리 후 자동 종료. `callEndedRef` 가드로 `onHangup` 1회만 호출(로컬/원격 중복 방지), 원격 수신 시 `hangup(false)` 로 에코 차단.
  - **설정 허브(상단 우측 ⚙️)**: 로그인 상태에서 우상단 고정 기어 아이콘 → 슬라이드업 `<Modal>`. (1) **수신 알림 소리/진동/무음** 세그먼트 — `worldlinco_settings_v1`(AsyncStorage) 저장 + `incomingAlertSoundModeRef` 로 알림 발생 시 즉시 반영. 네이티브 `VoipIncomingAlertController.startVoip(…, soundMode)` 에 모드 전달(소리=벨+진동/진동=진동만/무음=둘 다 끔, 풀스크린 팝업은 유지) + JS 폴백도 모드 게이팅. (2) **내 정보** 국가/언어 인라인 피커 — 선택 즉시 `PATCH /api/auth/me` 실시간 저장(상대 단말이 읽는 언어까지 일관 적용). (3) **비밀번호 변경** — 기존 `PasswordSecurityModal`(`openPasswordChange`) 재사용(중복 구현 방지).
  - 변경 파일: `App.tsx`, `src/services/voipCallClient.ts`, `src/screens/VoIPCallScreen.tsx`, `src/native/voipIncomingAlert.ts`, `android/.../VoipIncomingAlertModule.kt`, `android/.../VoipIncomingAlertController.kt`, `app.json`(version 1.0.123 · versionCode 175). 백엔드 엔드포인트(`PATCH /api/auth/me`, `POST /api/auth/password/change`)는 기존 자산 재사용. TS lint 0. **남음**: build175 EAS 빌드 후 SK/KT/WiFi 실기기로 (1) 수신 팝업 받기/거절 (2) 한쪽 종료 시 양쪽 동시 종료 (3) 소리/진동/무음·국가/언어 실시간 저장 확인.

- [x] **MB-15 (2026-06-23, 소리새 AI 정밀 분석 — 횡설수설(언어 오감지·저신뢰 STT)·지역(거친 GPS·좌표 그라운딩) 근본원인 교정 + 친구모드 튜닝 노브 노출)** — 사장님 지시: "대화 중 버그(지역/횡설수설) 검출, 정밀 튜닝 필요, 심층분석."
  - **심층분석 결론(경로 분기)**: 소리새 AI는 ① 친구 모드(`/voice/friend-chat`) ② 대면·통화 통역(`/face/voice-translate`) ③ 서버 VoIP 브리지(`media_bridge`) ④ 관광 구조화(`/voice/answer`)로 갈라져 있고, **환각·신뢰도 방어막이 경로마다 달랐던 것**이 버그가 "여러 가지로" 나타난 1차 원인. 가장 강한 방어(router.py)가 ①③에는 미적용이었다.
  - **B-1 (친구 모드 STT 신뢰도 게이트 부재 → 횡설수설)**: `voice_friend_chat` 은 문구/길이만 검사하고 `stt_trust`/`avg_logprob`/`no_speech_prob` 를 안 봤음 → 잡음·잔향발 저신뢰 전사가 그대로 LLM 입력 → 엉뚱한 답. **픽스**: `_run_faster_whisper` 가 이미 반환하는 `stt_trust=='low'` 면 422 거부(오디오 입력 한정, 텍스트 직접입력은 통과). `VOICE_FRIEND_REJECT_LOW_TRUST` 로 즉시 무력화 가능.
  - **B-2 (답변 언어가 STT 오감지에 끌려감 → 외국어 오답)**: 짧은 한국어를 ja/zh 로 오감지하면 페르소나가 그 언어로 답하던 문제. **픽스**: `_run_faster_whisper` 에 `language_probability` 노출 → 감지 확률이 임계(`friend_min_lang_prob`, 기본 0.60) 미만이면 감지 언어 무시하고 **프로필 언어로 폴백**.
  - **B-3 (서버 브리지 환각 목록이 축소판 → 다국어 자막/아웃트로 환각 누수)**: `media_bridge._HALLUCINATION_PHRASES`(한/일/영 ~25개)만 써서 router 의 60+ 다국어 시그니처(스칸디나비아·독·불·서/포 자막 크레딧·유튜브 인트로 등)를 못 잡았음. **픽스**: `_is_hallucination` 이 공용 `_is_whisper_hallucination_phrase`(router) 를 재사용(지연 임포트, fail-open).
  - **G-1 (좌표만 와서 페르소나에 'lat,lon' 숫자만 주입 → 지역 맥락 약화)**: **픽스**: 지역/국가 라벨이 없고 좌표만 있으면 서버에서 **OSM Nominatim reverse 지오코딩(캐시·좌표 2자리 거칠게)** 으로 'Osaka, Japan' 같은 실제 지역명 보강. `VOICE_FRIEND_REVERSE_GEOCODE` 토글.
  - **G-2 (지오 박스 경도 보정 누락 → 고위도서 동서 과대 → 먼 장소가 '근처'로 혼입)**: `tourism_kb` geo bounding box 가 위·경도에 동일 델타 적용. **픽스**: `lon_deg = lat_deg / cos(lat)` 보정으로 동서/남북 반경을 실거리에 맞춤.
  - **G-3 (거친 GPS 좌표를 그대로 그라운딩 → 엉뚱한 동네 안내)**: **픽스**: 모바일이 `accuracy_m`(`resolveHybridLocation` 정확도) 전송 → 서버가 `geo_accuracy_max_m`(기본 3000m) 초과면 좌표를 location_hint/그라운딩에서 제외(지역명/웹 폴백). 모바일 `gpsAccuracyM` state 추가.
  - **튜닝 노브 노출**: SSOT(`worldlinco_tuning_config.json` + `worldlinco_tuning.py`)에 `sorisae_ai` 섹션 신설(`friend_min_lang_prob`·`geo_accuracy_max_m`), `voice_gateway._sorisae_cfg()` TTL(2s) 캐시로 대화 중 ~2초 반영. 관리자 패널에 **🐦 소리새 AI 친구 모드** 섹션 추가.
  - 변경 파일: `backend/llm/voice_gateway.py`, `backend/voip/media_bridge.py`, `backend/services/tourism_kb/service.py`, `backend/marketplace/worldlinco_tuning.py`, `knowledge/worldlinco_tuning_config.json`, `frontend/.../admin-worldlinco-tuning-panel.tsx`, `apps/mobile-nadotongryoksa/App.tsx`. 백엔드 `py_compile` 통과, lint 0(신규), `test_worldlinco_tuning.py` 4 passed.
  - 적용: 백엔드 `docker restart devanalysis114-backend` 완료(health 200 — 서버측 B-1/B-2/B-3/G-1/G-2/G-3 + `sorisae_ai` 튜닝 라이브). **로컬 Gradle 빌드 v1.0.124/build176 게시 완료(65.14MB, 마켓 manifest versionCode=176 확인)** — 모바일 `accuracy_m` 전송(G-3)은 build176부터 반영. **남음**: build176 자동업그레이드 후 친구 모드 실대화로 (1) 잡음발 횡설수설 차단 (2) 한국어 발화에 한국어 답 (3) 지역명/근처 정확도 확인.

- [x] **MB-16 (2026-06-23, 소리새 AI 친구 모드 — 근거 없는 '날조 연락처(가짜 전화번호·주소)' 차단)** — 사장님 실사용: "춘천 맛집 안내인데 주소·연락처가 불명확/거짓인데 마치 진짜처럼 안내함(춘천은 033~)."
  - **근본원인**: 장소 질의에서 그라운딩(자체 Qdrant 인덱스 → OSM Nominatim → 웹)이 **모두 비면**(국내 인덱스 미적재 + "맛집/안내" 같은 자연어가 Nominatim 자유검색에 안 잡힘 + 웹키 부재), 친구 모드가 **비그라운딩 분기**로 빠져 LLM 이 시스템 지시("지어내지 말 것")를 무시하고 **그럴듯한 가짜 전화번호(033-xxx-xxxx)·주소를 '진짜처럼' 생성**.
  - **픽스 ① 날조 연락처 강제 제거(안전망, 필수)**: 반환 직전 `grounding_block` 이 비었으면(=검증 근거 없음) 답변에서 **전화번호 패턴을 무조건 제거**하고 정직 안내("정확한 전화번호·주소는 검색해 확인 후 알려드릴게요")로 대체(`_redact_unverified_contacts`). 전화 정규식은 `0XX-XXX-XXXX`/`010-XXXX-XXXX`/`+82-…`/9~11자리 연속만 잡고 **연도(2026)·가격(5,000원)·시간(9시~18시)·날짜(2026-06-23)는 보존**(단위테스트로 오탐 0 확인). 장소질의 분류와 무관하게 적용("먹을만한 데"처럼 키워드 미스해도 차단).
  - **픽스 ② 비그라운딩 프롬프트 강화**: 검색 근거가 없을 때 "전화번호·주소·영업시간을 **절대 만들어내지 말 것**(그럴듯한 033- 번호 포함). 이름·대략 위치는 가능하나 연락처는 확인 후 안내/지역 되묻기"로 명시.
  - **픽스 ③ 장소 질의 인식어 확대**: `먹을만`·`먹거리`·`맛있는`·`밥집`·`음식점` 추가 → 그라운딩(실데이터 검색) 트리거율↑.
  - 변경 파일: `backend/llm/voice_gateway.py`. `py_compile` 통과, 정규식 단위검증 OK. 백엔드 `docker restart` 후 컨테이너에 코드 반영 확인(health 200). **남음**: (후속·데이터) 국내 관광 인덱스(춘천 등) Qdrant 적재 + OSM 질의어 정제로 **실제 검증된 번호/주소를 '제공'**하는 방향(현재는 '날조 차단'까지 완료).

- [x] **MB-17 (2026-06-23, 관광 데이터 무결성 라이브 감사 — '수집 자료가 모두 날조 아니냐' 우려 검증 + 그라운딩-인지 날조 차단 강화)** — 사장님 우려: "수집한 관광 실시간 자료 안내도 그렇게(날조) 되는 것 아니냐? 국내뿐 아니라 국가별 모두 확인. 어제 작업·체크리스트·기술서의 관광 특화 AI 작업이 모두 날조일 수 있다."
  - **감사 방법**: Qdrant(`tourism_places`) 라이브 직접 질의(collection status·scroll 표본·country/geo count) + 인제스트 스크립트(`scripts/ingest_tourism_city.py`)·설계서 대조. 추정 아닌 **실측**.
  - **결론 ① 인덱스 데이터는 진짜다(날조 아님)**: `tourism_places` = **18,047 포인트**(status green, geo 인덱싱). 표본 payload 전부 `source=osm`/`source_id`(실 OSM 노드 id)·실좌표·`license=ODbL`(또는 Wikidata CC0). 즉 **저장된 KB·인제스트 인프라 작업은 실재하며 날조가 아니다.** 날조는 KB가 아니라 **미커버 질의 시 LLM 즉석 생성**에서 발생한 것(MB-16).
  - **결론 ② 국가별 실측(17개국 커버)**: JP=3574·KR=2571·US=1249·TH=1239·VN=1160·FR=933·GB=764·NL=737·IT=721·SG=709·TW=688·ES=664·AU=634·MY=626·ID=601·AE=595·HK=582 (CITY_REGISTRY 26개 도시). 국내·국외 모두 실데이터 존재.
  - **결론 ③ 춘천 = 0건(근본원인 확정)**: `CITY_REGISTRY` 한국은 seoul·busan·jeju·incheon만 → **춘천 bbox geo count = 0**. 미커버 도시는 인덱스 공백 → 그라운딩 공백 → (MB-16 이전) 날조. **데이터 날조가 아니라 커버리지 공백 문제.**
  - **결론 ④ 커버 도시도 전화번호 80.7% 비어있음(MB-16의 허점 발견)**: `empty_phone=14558/18047(80.7%)`. OSM 노드 다수가 phone 미보유 → 검색돼도 그라운딩 블록에 번호 없음 → 모델이 **빈 번호를 지어내도 MB-16은 못 막음**(MB-16은 '그라운딩이 완전히 빌 때'만 작동했음).
  - **강화 픽스(그라운딩-인지 날조 차단)**: `_redact_unverified_contacts(text, lang, grounding_block)` 로 시그니처 확장 + `_grounding_phone_digits()` 추가. **답변의 전화번호를 검색 근거 블록의 실제 번호(정규화 숫자열)와 대조해, 근거에 없는 번호는 그라운딩 유무와 무관하게 제거**. 호출부도 '그라운딩 빌 때만'→**항상** 실행으로 변경. → (a)미커버=전부 제거 (b)커버지만 번호 없음=날조 제거 (c)근거에 실번호 있음=유지. 단위검증 4케이스(춘천 가짜 제거/실번호 유지/근거밖 번호 제거/잡담 무영향) 통과.
  - 변경 파일: `backend/llm/voice_gateway.py`. `py_compile` 통과. 백엔드 `docker restart` 완료(health 200, 컨테이너 `_grounding_phone_digits` 반영). **남음(데이터 확장)**: 춘천·전주·강릉·경주 등 국내 관광도시 + OSM phone 보강 ingest 로 '날조 차단'→'검증된 번호 제공' 전환.

- [x] **MB-18 (2026-06-23, 정직 안내(114 유도) + 교차국가 지역오염 버그 수정 — 라이브 검증으로 발견)** — 사장님 지시: "번호를 지우는 게 정보냐? 114로 정직하게 안내하라" + "예약·일정 등 모든 정보 분석해 버그 수정. ①인덱스 데이터 ②그라운딩 ③문서주장 라이브 검증."
  - **정직 안내(삭제 대신 출처 유도)**: MB-16/17의 날조번호 '삭제'만으론 정보가 아니다 → `_UNVERIFIED_CONTACT_NOTE` 를 **"확인된 번호가 없음을 밝히고 114(전화번호 안내)·공식 홈페이지로 확인 유도"**(일=104, 영/중=공식사이트·현지 안내)로 교체. 비그라운딩 프롬프트도 "침묵·모호 금지, 정직하게 없음을 말하고 권위 출처로 안내"로 강화.
  - **라이브 검증 ② 중 발견한 핵심 버그(지역 오염)**: `/api/llm/voice/answer` 실호출(오사카·JP, 좌표 없이 region_hint/country_code만) → **인천(한국, 126.6)·후쿠오카가 오사카 질의에 혼입**. 원인: `_answer_collect_candidates`→`search_tourism_places` 가 **좌표(lat/lon)만** 지오필터로 쓰고 **country_code/region_hint 를 검색에 전혀 안 씀** → 좌표 없으면 전세계 텍스트매칭. 이것이 사장님이 겪던 "지역" 오안내의 구조적 원인.
  - **픽스(국가 필터 + 단계적 폴백)**: `TourismVectorStore.search(..., country_code)` 신설 — Qdrant `country` keyword 페이로드 인덱스 생성 후 `MatchValue` 조건을 (있으면) cos(lat) 지오박스와 **AND** 결합. 지오 결과가 비어도 **국가는 유지**한 채 폴백(① 국가+지오 → ② 국가만 → ③ 무필터)해 교차국가 오염을 막음. `search_tourism_places`·`_answer_collect_candidates`(4개 호출부)·`_friend_fetch_index_grounding`·`_friend_fetch_grounding` 까지 `country_code` 스레딩, friend-chat/answer 가 `request.country_code` 전달.
  - **라이브 재검증(실측)**: (a) 좌표 없이 country=JP → 결과 전부 JP(후쿠오카·도쿄), **인천 한국 사라짐**. (b) 오사카 좌표(34.69/135.50)+JP → 결과 전부 **오사카 도심(34.69~34.71/135.55~135.58, ~8km)**. 즉 좌표 없으면 국가로, 좌표 있으면 동네 단위로 정확.
  - **예약/일정 경로 점검**: `/voice/answer` 구조화 일정은 전화·주소·영업시간을 전부 **서버 후보(`candidates[pid]`=실 OSM)에서만 주입**하고 LLM 은 `blurb`+장소선택만 → 일정·연락처 날조 불가 구조 확인(설계대로 동작).
  - 변경 파일: `backend/services/tourism_kb/service.py`, `backend/llm/voice_gateway.py`. `py_compile` 통과, 신규 lint 0(잔여는 사전 import 미해결 경고). Qdrant `country` 인덱스 생성 + 백엔드 `docker restart`(health 200) 후 위 (a)(b) 실측 통과. **남음(데이터)**: 미커버 국내도시(춘천 등) ingest 로 '국가 필터'를 넘어 '도시 정밀 검증번호 제공'.

- [x] **MB-19 (2026-06-23, 소리새 AI 친구모드 자기에코 무한 자문자답 루프 차단 + Q/A 좌우 구분 표출)** — 사장님 실사용: "혼자 묻고 혼자 답하고 수없이 반복, 가끔 영어로 답하다 자기 음성을 다시 주워담고 또 말함. 안내 중엔 녹음 멈추고 발화 끝나면 재개해야. 질문/답변 언어 구분 표출(좌우). 대면 통역창과 충돌 → 분리 필요."
  - **근본원인(루프)**: 친구모드(`faceAiMode==='gpt'`)는 통역모드와 달리 **텍스트 에코 가드가 전혀 없었음**(`faceSpokenHistoryRef` 비교는 통역 경로에만 존재). 반이중 게이트(`faceSpeakingRef`)는 재생 promise 완료를 기다리지만, 한 번이라도 마이크가 TTS 꼬리를 잡으면 그 전사가 다시 friend-chat→답변→TTS→재캡처로 무한 반복. 끊을 2차 방어막이 없었던 것이 핵심.
  - **픽스 ① 자기에코 텍스트 가드(확정적 루프 차단)**: 발화한 답변을 `faceGptSpokenEchoRef`(정규화 텍스트+timestamp, 최근 5개)에 기록. 다음 전사가 최근 발화 답변과 `echoOverlapRatio≥0.7`(포함관계=1 또는 문자 bigram Dice) 이면 **자기에코로 보고 그 턴을 버림**(새 답변·TTS 생성 안 함). `FACE_CONVERSATION_ECHO_GUARD_MS`(25s) 창. early-return 시 기존 무-uri 패턴과 동일하게 `scheduleFaceConversationRestart(null)` 로 듣기 루프 유지. `normalizeEchoText`(공백·구두점 제거, 언어무관)·`echoOverlapRatio` 헬퍼 신설.
  - **픽스 ② Q/A 좌우 구분 표출**: `sorisaeQaLog` 상태 신설(질문·질문언어·답변·답변언어, 최근 50). 소리새AI 모드에서 **좌=🙋질문(입력 언어 라벨)·우=🐦답변(출력 언어 라벨)** 버블을 스크롤(maxHeight 260)로 표출. 질문언어=`data.detected_language`, 답변언어=`replyLangCode`. '지우기' 버튼 포함.
  - **반이중**: 기존 `faceSpeakingRef` 게이트(재생 중 녹음 시작 차단 + `playFaceTranslationOutput` 가 `didJustFinish`/30s 안전상한으로 실제 재생완료까지 promise 유지 + 1.5s drain)와 ①의 에코가드 조합으로 "발화 중 듣기정지 → 발화 완료 후 재개"가 보장됨.
  - **픽스 ③ 소리새AI 분리(드래그 플로팅 심볼 → 전용 풀스크린 창)**: 사장님 선택(드래그 모달). 로그인·비통화 중 🐦 **드래그 가능 플로팅 심볼**(`PanResponder`+`Animated.ValueXY`, 이동량 4px 미만이면 '탭'으로 판정) 표시 → 탭하면 **소리새AI 전용 `Modal`**(슬라이드)이 열림. 전용 토글 `handleToggleSorisaeConversation`(통역모드의 '상대 언어 필요' 제약 없이 항상 gpt 경로) + 창 열림 시 `faceAiMode='gpt'` 강제 + 닫을 때 진행 대화/재생 정리(`closeSorisaeWindow`). 창 안에 Q/A 좌우 버블(언어 라벨) + 마이크 ON/OFF + 지우기. → 대면 통역창과 캡처 경로 충돌 원천 분리.
  - 변경 파일: `apps/mobile-nadotongryoksa/App.tsx`(헬퍼·ref·에코가드·Q/A 패널·플로팅 심볼·전용 창·스타일), `app.json`(version 1.0.125·versionCode 177). `tsc --noEmit` 신규 오류 0(잔여 `TS1323`@9244 는 사전 dynamic-import 경고). **로컬 Gradle 빌드 v1.0.125/build177 게시 완료(BUILD SUCCESSFUL, 65.15MB, 마켓 manifest versionCode=177)**. **남음**: build177 자동업그레이드 후 실대화로 (1) 자문자답 루프 0 (2) 발화 중 듣기정지·완료 후 재개 (3) 플로팅 심볼→전용 창 분리 (4) Q/A 좌우·언어 라벨 확인.

- [x] **MB-20 (2026-06-23, build178 — 전화번호 안내 전면 제거(상호명+주소만) + 플로팅 심볼 상단 이동 + ADB 라이브 설치/검증)** — 사장님 실사용(build177 미적용 상태): "마이크 발화중 멈춤이 안되어 재녹취후 텍스트생성됨(반이중 실패 재보고), 소리새 열기가 너무 아래 있다, 전화번호 안내는 안 하는 게 맞다(지역번호 오류·주소 불명확) — 정확한 주소와 상호명만 안내하라. ADB 연결돼 있으니 접속해 확인하라."
  - **핵심 원인(현상 그대로)**: build177(에코가드+반이중+플로팅 심볼)이 **자동 업그레이드 안 된 상태** → 화면이 그대로(구버전). ADB로 직접 설치 필요.
  - **픽스 ① 전화번호 안내 전면 제거(MB-18 정책 재변경)**: 사장님 지시 반영 — 114 유도(MB-18)도 폐기하고 **전화번호는 아예 안내하지 않음**. `_redact_unverified_contacts(..., strip_all=True)` 추가 → friend-chat 응답의 **모든 전화번호를 검증 여부와 무관하게 제거**. `_UNVERIFIED_CONTACT_NOTE` 를 "전화번호는 정확하지 않을 수 있어 안내하지 않음, 상호명·주소로 안내(정확 번호는 현장/공식사이트 확인)"로 교체(ko/en/ja/zh). 프롬프트도 **PHONE NUMBER POLICY(STRICT)**: 전화번호를 말·추측·낭독 금지, **상호명+주소로만 안내**, 웹근거에 번호가 있어도 출력 금지로 강화. 단위검증 3케이스(번호 제거·상호명/주소 보존) 통과.
  - **픽스 ② 플로팅 심볼 상단 이동**: `sorisaeBtnPos` 기본 y = `height-220`(하단) → **`height*0.32`(상단 1/3)**, x = `width-74`. ADB 스크린샷으로 우상단 카드 옆에 표시 확인.
  - **ADB 라이브 설치/검증(요청대로 직접 접속)**: build178(v1.0.126) 로컬 Gradle 빌드(BUILD SUCCESSFUL, 65.15MB). 연결기기 설치 — **R83W70QY11H·172.30.1.19 = Success(설치 후 dumpsys `versionCode=178`/`versionName=1.0.126` 확인, 앱 force-stop→재기동)**, R3CT209943N = 설치 중 device offline(절전/USB). 스크린샷으로 헤더 `v1.0.126 · build 178` + 🐦 플로팅 심볼 상단 위치 육안 확인. ReactNativeJS logcat 모니터(`FACE_CONVERSATION|gpt_self_echo|vad_end`) 가동 — 실대화 시 자기에코/반이중 이벤트 추적.
  - 변경 파일: `backend/llm/voice_gateway.py`(strip_all·노트·프롬프트), `apps/mobile-nadotongryoksa/App.tsx`(심볼 위치), `app.json`(version 1.0.126·versionCode 178). `py_compile` 통과. 백엔드 `docker restart`(health 200) — 전화번호 제거 정책 라이브. **남음**: 사장님 실대화로 (1) 발화 중 듣기정지·완료 후 재개(반이중) 정상 (2) 전화번호 0 노출·상호명+주소만 (3) 플로팅 심볼 위치 적정 확인. R3CT 기기는 온라인 복귀 시 재설치.

- [x] **MB-21 (2026-06-23, build179 — 대면 통역 단일 창화(중복 소리새AI 진입점 제거) + 전화번호 '데이터대로 안내'로 정책 환원)** — 사장님 지시: "대면 통역 우측의 소리새AI 버튼·소리새AI 대화 ON/OFF 제거(중복 충돌/버그 우려) → 대면 통역 단일 창. 일본 등 타국은 정보가 정확한데 왜 한국처럼 똑같이 안내하나? **정보대로** 안내하라 — 주소 있으면 주소, 전화 있으면 전화, 상호 있으면 상호. 관광 특화 AI 맞나?"
  - **픽스 ① 대면 통역 단일 창**: 메인 대면 카드에서 `faceAiModeRow`(🌐통역/🐦소리새AI 세그먼트 토글)·gpt 힌트·메인 Q/A 패널을 **삭제**. 대화 토글 라벨도 gpt 분기 제거(통역 단일). 소리새AI는 **플로팅 🐦 심볼 → 전용 Modal**로만 진입(MB-19/20). `handleToggleFaceConversation` 시작 시 `faceAiMode='translate'` 강제 + `closeSorisaeWindow` 종료 시 `'translate'` 복귀 → gpt 모드가 메인 캡처 루프로 새지 않게 차단(중복 충돌 원천 제거). 스크린샷으로 메인 카드에 토글 없음 + 🐦 심볼만 확인.
  - **픽스 ② 전화번호 '데이터대로 안내'로 환원(MB-20 strip_all 철회)**: MB-20의 '전화번호 전면 제거'는 **검증된 번호가 있는 국가(일본 등)까지 똑같이 지워** 관광 안내 품질을 떨어뜨림. → friend-chat 리댁션을 **그라운딩-인지(strip_all=False)** 로 환원: 검색 근거(OSM/인덱스/웹)에 **실제 있는** 번호·주소·상호는 그대로 안내하고, 근거에 없는(=모델 날조) 번호만 제거. 프롬프트도 "데이터가 가진 NAME/ADDRESS/PHONE/HOURS를 **그대로** 안내, 단 데이터에 없는 건 절대 지어내지 말 것"으로 환원. `_UNVERIFIED_CONTACT_NOTE` 는 '근거 없는 번호를 뺐다'는 짧은 정직 안내로 축소. 단위검증: (일본·근거에 번호 있음=`06-6211-3039` 유지) / (춘천·근거 없음=날조번호 제거, 상호 '춘천 명동닭갈비'·주소 '명동길 11' 유지) 통과.
  - 변경 파일: `apps/mobile-nadotongryoksa/App.tsx`(대면 카드 UI 삭제·모드 강제), `backend/llm/voice_gateway.py`(strip_all 철회·프롬프트·노트), `app.json`(version 1.0.127·versionCode 179). 신규 lint 0, `py_compile` 통과. 백엔드 `docker restart`(health 200) + **build179 빌드/게시(BUILD SUCCESSFUL) → ADB 설치(R83W70QY11H·172.30.1.19 = versionCode 179 확인, 재기동)**. R3CT 기기 offline(복귀 시 재설치). **남음**: 실대화로 (1) 대면=통역 단일·소리새=플로팅창 분리 동작 (2) 일본 등 검증 번호/주소/상호 정상 안내·한국 미커버 날조만 차단 확인.

- [x] **MB-22 (2026-06-23, build180 — 소리새AI/대면 통역 처리 경로 '창 기준'으로 완전 분리(레이스 버그 수정))** — 사장님(강한 불만): "분명히 분리하라고 했잖아. 대면 통역은 통역만, 소리새AI는 질문·관광 안내·대화만 되게 하라."
  - **근본원인(라이브 로그로 확정)**: 소리새 전용 창에서 "일본의 유명한 관광지가 어디야?"를 물었는데 logcat 에 **`bilingual:true`(통역 경로)** 로 처리됨. 원인은 세그먼트 라우팅 분기 `isFaceGptMode` 가 **`faceAiModeRef.current === 'gpt'`**(비동기 `setFaceAiMode` 와 캡처 루프 타이밍 레이스) 에 의존 → 소리새 창인데도 통역으로 새는 경우 발생. UI(MB-21)는 분리했지만 **처리 로직이 모드 플래그에 의존**해 실질 분리가 깨졌던 것.
  - **픽스(처리 분기 SSOT = 창 열림 여부)**: `sorisaeWindowOpenRef`(전용 창 열림 ref) 신설 후 `isFaceGptMode = !songMode && target==='main' && sorisaeWindowOpenRef.current` 로 변경. → **소리새 창이 열려 있으면 무조건 friend-chat(질문/관광/대화), 닫혀 있으면 무조건 voice-translate(통역)**. 모드 플래그 타이밍과 무관하게 결정적 분리. ref 는 플로팅 심볼 탭(열기)·`closeSorisaeWindow`(닫기)·`useEffect` 에서 동기 갱신, 창 열릴 때 진행 중이던 대면 통역 캡처를 `stopVoiceInput` 으로 중단해 두 경로 동시활성 방지. 디버그 로그에 `route:'sorisae'|'translate'` 추가(검증용).
  - 변경 파일: `apps/mobile-nadotongryoksa/App.tsx`, `app.json`(1.0.128·versionCode 180). 신규 lint 0. **build180 빌드/게시(BUILD SUCCESSFUL) → ADB 설치(R83W70QY11H·172.30.1.19 = versionCode 180, 재기동)**. 신규 logcat 모니터(`route:`) 가동. **남음**: 실대화로 (1) 대면=`route:translate` 만 (2) 소리새 창=`route:sorisae` 만 + 일본 검증번호 안내 확인.

### 13.5 후속(스트리밍 고도화, 상품 품질)
- 스트리밍 ASR(부분결과/endpointing) + 동시 MT(wait-k) + 증분 TTS, 또는 **Speech-to-Speech 스트리밍(SeamlessStreaming/StreamSpeech)** 코어로 ear-to-ear 추가 단축·운율 보존.
- 엣지/온디바이스 추론 경로(OEM 하드웨어 탑재 대비).
