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
