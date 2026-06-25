"""마켓플레이스 CRUD 작업"""
from io import BytesIO
from pathlib import Path
from threading import Lock
from textwrap import dedent
from typing import List, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, schemas


SAMPLE_SELLER_EMAIL = "samples@devanalysis.local"
SAMPLE_SELLER_USERNAME = "marketplace_samples"
_INITIAL_DATA_LOCK = Lock()


def _resolve_upload_root() -> Path:
    workspace_root = Path(__file__).resolve().parents[2]
    return (workspace_root / "uploads" / "marketplace_local" / "samples").resolve()


def _build_sample_archive(files: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for file_path, content in files.items():
            archive.writestr(file_path, dedent(content).strip() + "\n")
    return buffer.getvalue()


def _store_sample_archive(slug: str, files: dict[str, str]) -> str:
    sample_root = _resolve_upload_root()
    sample_root.mkdir(parents=True, exist_ok=True)
    target = (sample_root / f"{slug}.zip").resolve()
    if not str(target).startswith(str(sample_root)):
        raise RuntimeError("sample archive path escaped sample root")
    target.write_bytes(_build_sample_archive(files))
    return f"local:samples/{slug}.zip"


def _get_or_create_tag(db: Session, name: str) -> models.Tag:
    tag = db.query(models.Tag).filter(models.Tag.name == name).first()
    if tag:
        return tag
    tag = models.Tag(name=name)
    db.add(tag)
    db.flush()
    return tag


def _sample_project_specs() -> list[dict[str, object]]:
    return [
        {
            "slug": "nadotongryoksa-v1",
            "title": "나도통역사 - 신세계소리새 통번역",
            "description": (
                "WorldLinco(나도통역사) — 소리새 AI 기반 실시간 통번역 슈퍼앱. Android APK 완제품 (v1.0.150).\n\n"
                "• 소리새 하늘색 UI 적용 — 전 화면 통일된 스카이블루 배경(신규 디자인)\n"
                "• 대면통역·VoIP 통역통화·채팅 번역·노래 번역·여행 예약 통합 채널\n"
                "• 소리새 AI 동반자 — 웨이크워드 호출·기억/성격을 가진 개인 통역 비서\n"
                "• 한국어↔영어/중국어/일본어/스페인어 실시간 음성 통역\n"
                "• 인앱 자동 업데이트(expo-updates) — 신규 빌드 배포 시 기기에서 자동 수신\n"
                "• APK 직접 설치 후 바로 사용 가능 (Android 8.0+)\n\n"
                "소리새 마스터 하이브리드 시스템의 통역 엔진을 모바일에 이식한 완전 독립 실행형 앱입니다."
            ),
            "price": 0.0,
            "category_name": "모바일 앱",
            "demo_url": "/api/marketplace/apk/nadotongryoksa-v1.apk",
            "github_url": "/marketplace/nadotongryoksa",
            "tags": ["통역", "번역", "음성인식", "android", "apk", "무료",
                     "WorldLinco", "소리새", "실시간통역", "AI동반자"],
            "downloads": 0,
            "rating": 0.0,
            "files": {
                "README.md": """\
                    # WorldLinco(나도통역사) v1.0.150 — 소리새 통번역 슈퍼앱

                    ## 새 디자인
                    전 화면에 "소리새 하늘색" 통일 배경(스카이블루 → 화이트 그라데이션)을 적용했습니다.

                    ## 주요 기능
                    - 대면통역 · VoIP 통역통화 · 채팅 번역 · 노래 번역 · 여행 예약
                    - 소리새 AI 동반자(웨이크워드 호출 · 개인 통역 비서)

                    ## 설치 방법
                    1. `nadotongryoksa-v1.apk` 파일을 Android 기기로 전송합니다.
                    2. 기기 설정 → 보안 → "알 수 없는 소스" 설치를 허용합니다.
                    3. APK 파일을 실행해 설치합니다.
                    4. 앱 실행 후 언어 쌍을 선택하고 마이크 버튼을 눌러 통역을 시작합니다.
                       (이후 신규 빌드는 인앱 자동 업데이트로 수신됩니다.)

                    ## 시스템 요구사항
                    - Android 8.0 (Oreo) 이상
                    - RAM 2GB 이상 권장
                    - 마이크 권한 필요

                    ## 지원 언어
                    한국어 ↔ 영어, 중국어(간체), 일본어, 스페인어

                    ## 오프라인 모드
                    인터넷 없이도 한↔영 기본 통역 가능 (경량 모델 내장)

                    ## 라이선스
                    소리새 시스템 기반 — 개인 및 비상업적 사용 무료
                """,
                "app/src/main/AndroidManifest.xml": """\
                    <?xml version="1.0" encoding="utf-8"?>
                    <manifest xmlns:android="http://schemas.android.com/apk/res/android"
                        package="com.shinsegye.nadotongryoksa">
                        <uses-permission android:name="android.permission.RECORD_AUDIO" />
                        <uses-permission android:name="android.permission.INTERNET" />
                        <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
                        <application
                            android:label="나도통역사"
                            android:icon="@mipmap/ic_launcher">
                            <activity android:name=".MainActivity"
                                android:exported="true">
                                <intent-filter>
                                    <action android:name="android.intent.action.MAIN" />
                                    <category android:name="android.intent.category.LAUNCHER" />
                                </intent-filter>
                            </activity>
                        </application>
                    </manifest>
                """,
                "app/src/main/java/com/shinsegye/nadotongryoksa/TranslationEngine.kt": """\
                    package com.shinsegye.nadotongryoksa

                    // 신세계소리새 통번역 엔진 — SoriSae Master Hybrid 기반
                    class TranslationEngine {
                        val supportedPairs = listOf("ko-en", "ko-zh", "ko-ja", "ko-es")

                        fun translate(text: String, from: String, to: String): String {
                            // SoriSae hybrid interpreter_system 연결
                            return "[${from}→${to}] $text"
                        }

                        fun voiceTranslate(audioBytes: ByteArray, from: String, to: String): String {
                            // 음성 → 텍스트 → 번역 파이프라인
                            return translate("(음성 입력)", from, to)
                        }
                    }
                """,
                "build.gradle": """\
                    plugins {
                        id 'com.android.application' version '8.2.0' apply false
                        id 'org.jetbrains.kotlin.android' version '1.9.0' apply false
                    }
                """,
            },
        },
        {
            "slug": "daytrade-ai-v1",
            "title": "daytrade-ai — AI 주식 단타(스캘핑) 자동매매 시스템 [실험 빌드]",
            "description": (
                "오더북·체결 흐름을 실시간 분석해 밀리초 단위로 시그널을 생성하고 자동 주문하는 "
                "AI 단타(스캘핑·초단타) 자동매매 파이프라인 — Python 완제품. (실험 빌드 v0.9)\n\n"
                "• Feature(OBI·OBI z-score·거래량 급증·마이크로 모멘텀·VWAP·스프레드) → Detection → "
                "AI 추론 → Risk → Execution(OrderRouter) → Monitoring 전 구간 모듈화\n"
                "• 기본 모의투자(paper)·백테스트 모드 — 실거래는 코드 레벨 이중 안전 게이트로 차단\n"
                "• 리스크 한도(포지션·총노출·레버리지) + 레이턴시/손익 서킷브레이커 + 슬리피지 가드 + "
                "주문 라우터 예외 흡수(브로커 단절 내성)\n"
                "• AI 추론 플러거블(휴리스틱 / ONNX) + 강화학습(PPO·연속 포지션 사이징) + "
                "워크포워드 OOS 검증 + Optuna 하이퍼파라미터 튜닝\n"
                "• MLOps 피드백 루프: 자동 재학습·검증·핫스왑(블루그린)·KPI 악화 시 자동 롤백·"
                "롤백 쿨다운/블랙리스트·스케줄러 (Prometheus/Grafana/Alertmanager 관측성)\n"
                "• 고속 바이너리 틱 스토어(.dts, KDB+ 경량 대안)·실데이터 일별 캡처·Backtrader 교차검증 어댑터\n"
                "• C++ 저지연 코어(FeatureEngine/DetectionEngine, Python과 1e-9 수치 동일성 골든 테스트)\n"
                "• 백테스트 리포트 고도화(Sortino·Calmar·VaR/CVaR·수익팩터·HTML 스파크라인)\n"
                "• 단위/통합 테스트 286건 통과 · CLI(`python -m daytrade.cli sim`) 즉시 실행\n\n"
                "주의: 실거래는 증권사 API 계약(KIS/키움 등) + 초저지연 인프라(DPDK/FPGA/코로케이션) "
                "확장 영역이며, 거래소·금융 규제 준수와 사전 승인이 필요합니다. 본 빌드는 모의/백테스트용입니다."
            ),
            "price": 349000.0,
            "category_name": "AI/ML",
            "demo_url": None,
            "github_url": "https://github.com/parkcheolhong/codeAI/tree/main/apps/daytrade-ai",
            "tags": ["주식", "단타", "스캘핑", "자동매매", "퀀트", "백테스트", "AI",
                     "강화학습", "MLOps", "실험빌드"],
            "downloads": 0,
            "rating": 0.0,
            "files": {
                "README.md": """\
                    # daytrade-ai — AI 주식 단타(스캘핑) 자동매매 시스템 [실험 빌드 v0.9]

                    오더북/체결 흐름을 실시간 분석해 밀리초 단위로 시그널을 만들고 자동 주문하는
                    Python 자동매매 파이프라인입니다. 기본은 모의투자(paper)·백테스트이며,
                    실거래는 코드 레벨 이중 안전 게이트를 통과해야만 활성화됩니다.

                    ## 빠른 시작
                    ```bash
                    pip install -r requirements.txt
                    python -m daytrade.cli sim --symbol AAPL --ticks 5000 --obi-threshold 5e5 --event-prob 0.05
                    python -m daytrade.cli sim --ticks 5000 --report-html report.html   # 분석 리포트
                    python -m pytest -q   # 286 passed
                    ```

                    ## 아키텍처
                    feed → FeatureEngine → DetectionEngine → AI Inference → RiskManager → OrderRouter → Portfolio
                    (+ Monitoring: 레이턴시 p50/p95/p99 · 슬리피지 · P&L · Sharpe · MDD)

                    ## 포함 범위
                    - 강화학습(PPO/연속 포지션) · 워크포워드 OOS 검증 · Optuna 튜닝
                    - MLOps 자동 재학습·핫스왑·자동 롤백·롤백 쿨다운/블랙리스트·스케줄러
                    - 고속 바이너리 틱 스토어(.dts) · 실데이터 일별 캡처 · Backtrader 어댑터
                    - C++ 저지연 코어(Python과 1e-9 수치 동일성) · 백테스트 HTML 리포트

                    전체 소스는 저장소 `apps/daytrade-ai/` 에 포함되어 있습니다.
                    GitHub: https://github.com/parkcheolhong/codeAI/tree/main/apps/daytrade-ai
                """,
                "requirements.txt": """\
                    numpy>=1.26
                    pytest>=8.0
                    # onnxruntime>=1.17  # (선택) ONNX 추론 어댑터 사용 시
                """,
                "SAFETY.md": """\
                    # 안전 게이트 (실거래 차단)

                    실거래(LIVE)는 아래 두 조건을 **모두** 만족해야만 활성화됩니다.
                    1. TradingConfig.mode == TradingMode.LIVE
                    2. 환경변수 DAYTRADE_ALLOW_LIVE == "I_UNDERSTAND_THE_RISK"

                    하나라도 어긋나면 실행기는 자동으로 paper(모의)로 강등됩니다. 또한 LIVE 가
                    인가돼도 사용자 제공 실거래 OrderExecutor(브로커 어댑터)가 없으면 파이프라인
                    생성이 거부됩니다. 본 패키지에는 실주문 구현체가 포함되지 않습니다.

                    추가 안전장치: 레이턴시 서킷브레이커(>10ms 중단), 당일 손절/익절(±2%),
                    슬리피지 가드, 포지션/총노출/레버리지 한도.

                    실거래는 자본시장법·SEC Reg NMS·MiFID II 등 규제 준수와 거래소 사전 승인이
                    필요하며, 모든 책임은 사용자에게 있습니다.
                """,
                "ARCHITECTURE.md": """\
                    # 모듈 맵

                    - daytrade/feed/        : MarketFeed + 합성/CSV 리플레이 + Binance/Upbit/Alpaca 라이브
                    - daytrade/features/    : OBI · OBI z-score · 거래량 급증 · 마이크로 모멘텀 · VWAP · 스프레드
                    - daytrade/detection/   : 규칙 기반 시그널 + confidence
                    - daytrade/inference/   : 플러거블 모델(휴리스틱 기본 / ONNX 어댑터)
                    - daytrade/risk/        : 포지션·총노출·레버리지 한도 + 서킷브레이커 + 슬리피지 가드
                    - daytrade/execution/   : OrderExecutor + PaperExecutor + OrderRouter(예외 흡수) + Portfolio
                    - daytrade/training/    : 라벨링·데이터셋 · 워크포워드 OOS 검증 · Optuna 튜닝 · ONNX export
                    - daytrade/rl/          : TradingEnv + PPO/연속 PPO/REINFORCE
                    - daytrade/ops/         : MLOps 재학습·핫스왑·자동 롤백·롤백 가드·스케줄러
                    - daytrade/storage/     : 고속 바이너리 틱 스토어(.dts) + 일별 캡처 레코더
                    - daytrade/testing/     : 인프로세스 장애 주입(FaultInjectingFeed/FlakyExecutor)
                    - daytrade/pipeline.py  : 전 구간 결선(틱당 처리)
                    - daytrade/monitoring/  : 레이턴시/슬리피지/P&L/Sharpe/MDD + Prometheus 메트릭
                    - daytrade/backtest/    : 시뮬레이션 러너 + 리포트 고도화 + Backtrader 어댑터
                    - cpp/                  : C++ 저지연 코어(Python과 1e-9 골든 패리티)
                    - daytrade/cli.py       : sim / replay / walkforward / tune / train / rl / events 진입점
                """,
            },
        },
    ]


def get_project(db: Session, project_id: int) -> Optional[models.Project]:
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects(
    db: Session,
    skip: int = 0,
    limit: int = 12,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "created_at",
    order: str = "desc",
) -> tuple[List[models.Project], int]:
    query = db.query(models.Project).filter(models.Project.is_active == True)
    if search:
        query = query.filter(
            or_(
                models.Project.title.ilike(f"%{search}%"),
                models.Project.description.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.filter(models.Project.category_id == category_id)
    if min_price is not None:
        query = query.filter(models.Project.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Project.price <= max_price)
    if order == "asc":
        query = query.order_by(getattr(models.Project, sort_by).asc())
    else:
        query = query.order_by(getattr(models.Project, sort_by).desc())
    total = query.count()
    projects = query.offset(skip).limit(limit).all()
    return projects, total


def create_project(db: Session, project: schemas.ProjectCreate, author_id: int) -> models.Project:
    tags = []
    if project.tags:
        for tag_name in project.tags:
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if not tag:
                tag = models.Tag(name=tag_name)
                db.add(tag)
            tags.append(tag)
    db_project = models.Project(
        title=project.title,
        description=project.description,
        price=project.price,
        category_id=project.category_id,
        author_id=author_id,
        demo_url=project.demo_url,
        github_url=project.github_url,
        image_url=project.image_url,
        tags=tags,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(db: Session, project_id: int, project_update: schemas.ProjectUpdate) -> Optional[models.Project]:
    db_project = get_project(db, project_id)
    if not db_project:
        return None
    update_data = project_update.dict(exclude_unset=True, exclude={"tags"})
    for key, value in update_data.items():
        if value is not None:
            setattr(db_project, key, value)
    if project_update.tags is not None:
        tags = []
        for tag_name in project_update.tags:
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if not tag:
                tag = models.Tag(name=tag_name)
                db.add(tag)
            tags.append(tag)
        db_project.tags = tags
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int) -> bool:
    db_project = get_project(db, project_id)
    if not db_project:
        return False
    db_project.is_active = False # type: ignore
    db.commit()
    return True


def get_categories(db: Session) -> List[models.Category]:
    return db.query(models.Category).all()


def create_category(db: Session, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def create_initial_data(db: Session):
    categories_data = [
        {"name": "웹 개발", "description": "웹사이트, 웹앱 프로젝트"},
        {"name": "모바일 앱", "description": "iOS, Android 앱"},
        {"name": "AI/ML", "description": "인공지능, 머신러닝 프로젝트"},
        {"name": "데이터 분석", "description": "데이터 분석, 시각화"},
        {"name": "게임", "description": "게임 개발 프로젝트"},
        {"name": "기타", "description": "기타 프로젝트"},
    ]
    for cat_data in categories_data:
        if not db.query(models.Category).filter(models.Category.name == cat_data["name"]).first():
            db.add(models.Category(**cat_data))
    db.flush()
    categories = {category.name: category for category in db.query(models.Category).all()}
    if not db.query(models.User).filter(models.User.email == "test@example.com").first():
        test_user = models.User(
            email="test@example.com",
            username="testuser",
            hashed_password="dummy_hash",
            full_name="테스트 사용자",
        )
        db.add(test_user)
    sample_seller = db.query(models.User).filter(models.User.email == SAMPLE_SELLER_EMAIL).first()
    if not sample_seller:
        sample_seller = models.User(
            email=SAMPLE_SELLER_EMAIL,
            username=SAMPLE_SELLER_USERNAME,
            hashed_password="sample_catalog_only",
            full_name="Marketplace Sample Seller",
            is_active=True,
        )
        db.add(sample_seller)
        db.flush()
    for spec in _sample_project_specs():
        category = categories.get(str(spec["category_name"])) # pyright: ignore[reportArgumentType]
        if category is None:
            continue
        tags = [_get_or_create_tag(db, str(tag_name)) for tag_name in spec["tags"]] # pyright: ignore[reportGeneralTypeIssues]
        file_key = _store_sample_archive(str(spec["slug"]), spec["files"]) # pyright: ignore[reportArgumentType]
        project = db.query(models.Project).filter(
            models.Project.author_id == sample_seller.id,
            models.Project.title == spec["title"],
        ).first()
        if not project:
            project = models.Project(
                title=str(spec["title"]),
                description=str(spec["description"]),
                price=float(spec["price"]), # pyright: ignore[reportArgumentType]
                category_id=category.id,
                author_id=sample_seller.id,
                demo_url=str(spec["demo_url"] or "") or None,
                github_url=str(spec["github_url"] or "") or None,
                file_key=file_key,
                downloads=int(spec["downloads"]), # pyright: ignore[reportArgumentType]
                rating=float(spec["rating"]), # type: ignore
                is_active=True,
                tags=tags,
            )
            db.add(project)
            continue
        project.description = str(spec["description"]) # type: ignore
        project.price = float(spec["price"]) # pyright: ignore[reportArgumentType, reportAttributeAccessIssue]
        project.category_id = category.id
        project.demo_url = str(spec["demo_url"] or "") or None # pyright: ignore[reportAttributeAccessIssue]
        project.github_url = str(spec["github_url"] or "") or None # pyright: ignore[reportAttributeAccessIssue]
        project.file_key = file_key # pyright: ignore[reportAttributeAccessIssue]
        project.downloads = int(spec["downloads"]) # pyright: ignore[reportArgumentType, reportAttributeAccessIssue]
        project.rating = float(spec["rating"]) # pyright: ignore[reportArgumentType, reportAttributeAccessIssue]
        project.is_active = True # pyright: ignore[reportAttributeAccessIssue]
        project.tags = tags
    db.commit()
    print("✅ 초기 데이터 생성 완료")


def ensure_marketplace_seed_data(db: Session) -> bool:
    has_active_projects = db.query(models.Project.id).filter(models.Project.is_active.is_(True)).first() is not None
    has_categories = db.query(models.Category.id).first() is not None
    if has_active_projects and has_categories:
        return False

    with _INITIAL_DATA_LOCK:
        has_active_projects = db.query(models.Project.id).filter(models.Project.is_active.is_(True)).first() is not None
        has_categories = db.query(models.Category.id).first() is not None
        if has_active_projects and has_categories:
            return False
        create_initial_data(db)
        return True


def create_review(db: Session, review: schemas.ReviewCreate, user_id: int):
    db_review = models.Review(project_id=review.project_id, user_id=user_id, rating=review.rating, comment=review.comment)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_reviews_by_project(db: Session, project_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Review).filter(models.Review.project_id == project_id).offset(skip).limit(limit).all()


def get_review_stats(db: Session, project_id: int):
    reviews = db.query(models.Review).filter(models.Review.project_id == project_id).all()
    if not reviews:
        return {"average_rating": 0, "total_reviews": 0}
    total = len(reviews)
    avg = sum(r.rating for r in reviews) / total
    return {"average_rating": round(avg, 1), "total_reviews": total} # pyright: ignore[reportCallIssue, reportArgumentType]


def get_purchase(db: Session, purchase_id: int) -> Optional[models.Purchase]:
    return db.query(models.Purchase).filter(models.Purchase.id == purchase_id).first()


def get_user_purchases(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> tuple[List[models.Purchase], int]:
    query = db.query(models.Purchase).filter(models.Purchase.buyer_id == user_id)
    total = query.count()
    purchases = query.offset(skip).limit(limit).all()
    return purchases, total


def create_purchase(db: Session, project_id: int, buyer_id: int, amount: float, payment_method: str = "card") -> models.Purchase:
    purchase = models.Purchase(
        project_id=project_id,
        buyer_id=buyer_id,
        amount=amount,
        payment_method=payment_method,
        status="pending",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


def update_purchase_status(db: Session, purchase_id: int, status: str, transaction_id: str = None) -> Optional[models.Purchase]: # type: ignore
    purchase = get_purchase(db, purchase_id)
    if not purchase:
        return None
    purchase.status = status # type: ignore
    if transaction_id:
        purchase.transaction_id = transaction_id # type: ignore
    db.commit()
    db.refresh(purchase)
    return purchase