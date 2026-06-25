"""daytrade-ai 마켓플레이스 상품 등록 스크립트(idempotent, 타겟형).

전체 시드(`crud.create_initial_data`)는 현재 스키마와 어긋나는 레거시 유저 시드를
함께 만들려다 실패하므로, 여기서는 **daytrade-ai 상품 1건만** 안전하게 upsert 한다.

동작:
  1) "AI/ML" 카테고리를 찾는다(없으면 생성).
  2) 샘플 판매자(SAMPLE_SELLER_EMAIL)를 찾는다(없으면 첫 사용자로 폴백).
  3) `_sample_project_specs()` 에서 slug == "daytrade-ai-v1" 스펙을 읽어
     다운로드 아카이브(zip)를 저장하고 Project 행을 insert/update 한다.

실행(백엔드 컨테이너 내부):
  docker exec devanalysis114-backend python apps/daytrade-ai/scripts/register_marketplace_product.py
"""
from __future__ import annotations

import sys

from backend.marketplace.database import SessionLocal, _get_or_create_engine
from backend.marketplace import crud, models


SLUG = "daytrade-ai-v1"


def main() -> int:
    _get_or_create_engine()
    db = SessionLocal()
    try:
        spec = next((s for s in crud._sample_project_specs() if s["slug"] == SLUG), None)
        if spec is None:
            print(f"[ERR] spec '{SLUG}' not found in _sample_project_specs()")
            return 1

        category = (
            db.query(models.Category)
            .filter(models.Category.name == spec["category_name"])
            .first()
        )
        if category is None:
            category = models.Category(name=str(spec["category_name"]), description="AI/ML")
            db.add(category)
            db.flush()

        seller = (
            db.query(models.User)
            .filter(models.User.email == crud.SAMPLE_SELLER_EMAIL)
            .first()
        )
        if seller is None:
            seller = db.query(models.User).order_by(models.User.id.asc()).first()
        if seller is None:
            print("[ERR] no user available to own the product")
            return 2

        tags = [crud._get_or_create_tag(db, str(t)) for t in spec["tags"]]
        file_key = crud._store_sample_archive(str(spec["slug"]), spec["files"])

        project = (
            db.query(models.Project)
            .filter(
                models.Project.author_id == seller.id,
                models.Project.title == spec["title"],
            )
            .first()
        )
        action = "updated"
        if project is None:
            action = "inserted"
            project = models.Project(
                title=str(spec["title"]),
                description=str(spec["description"]),
                price=float(spec["price"]),
                category_id=category.id,
                author_id=seller.id,
                demo_url=(str(spec["demo_url"] or "") or None),
                github_url=(str(spec["github_url"] or "") or None),
                file_key=file_key,
                downloads=int(spec["downloads"]),
                rating=float(spec["rating"]),
                is_active=True,
                tags=tags,
            )
            db.add(project)
        else:
            project.description = str(spec["description"])
            project.price = float(spec["price"])
            project.category_id = category.id
            project.demo_url = (str(spec["demo_url"] or "") or None)
            project.github_url = (str(spec["github_url"] or "") or None)
            project.file_key = file_key
            project.is_active = True
            project.tags = tags

        db.commit()
        db.refresh(project)
        print(
            f"[OK] {action}: id={project.id} title={project.title!r} "
            f"price={project.price} category_id={project.category_id} "
            f"file_key={project.file_key} tags={[t.name for t in project.tags]}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[ERR] {type(exc).__name__}: {exc}")
        return 3
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
