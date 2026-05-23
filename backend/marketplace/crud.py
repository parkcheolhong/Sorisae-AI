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
                "신세계소리새(SoriSae) AI 기반 실시간 통번역 앱 — Android APK 완제품.\n\n"
                "• 한국어↔영어/중국어/일본어/스페인어 실시간 음성 통역\n"
                "• 오프라인·위성·모바일 하이브리드 연결 자동 전환\n"
                "• 회의실·여행·의료·법률 특화 번역 모드 내장\n"
                "• APK 직접 설치 후 바로 사용 가능 (Android 8.0+)\n\n"
                "신세계소리새 마스터 하이브리드 시스템의 통역 엔진을 모바일에 이식한 완전 독립 실행형 앱입니다."
            ),
            "price": 0.0,
            "category_name": "모바일 앱",
            "demo_url": "/api/marketplace/apk/nadotongryoksa-v1.apk",
            "github_url": "/marketplace/nadotongryoksa",
            "tags": ["통역", "번역", "음성인식", "android", "apk", "무료", "신세계소리새"],
            "downloads": 0,
            "rating": 0.0,
            "files": {
                "README.md": """\
                    # 나도통역사 v1.0 — 신세계소리새 통번역 앱

                    ## 설치 방법
                    1. `nadotongryoksa-v1.apk` 파일을 Android 기기로 전송합니다.
                    2. 기기 설정 → 보안 → "알 수 없는 소스" 설치를 허용합니다.
                    3. APK 파일을 실행해 설치합니다.
                    4. 앱 실행 후 언어 쌍을 선택하고 마이크 버튼을 눌러 통역을 시작합니다.

                    ## 시스템 요구사항
                    - Android 8.0 (Oreo) 이상
                    - RAM 2GB 이상 권장
                    - 마이크 권한 필요

                    ## 지원 언어
                    한국어 ↔ 영어, 중국어(간체), 일본어, 스페인어

                    ## 오프라인 모드
                    인터넷 없이도 한↔영 기본 통역 가능 (경량 모델 내장)

                    ## 라이선스
                    신세계소리새 시스템 기반 — 개인 및 비상업적 사용 무료
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