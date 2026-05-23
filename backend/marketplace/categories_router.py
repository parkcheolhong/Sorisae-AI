from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session


def build_categories_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/categories")
    def list_marketplace_categories(request: Request, response: Response, db: Session = Depends(contract.get_db)):
        contract._apply_short_marketplace_categories_cache_headers(response)
        now_ts = contract.time.time()
        cached_payload = contract._MARKETPLACE_CATEGORIES_CACHE.get("payload")
        cached_at = float(contract._MARKETPLACE_CATEGORIES_CACHE.get("captured_at") or 0.0)
        if contract._should_throttle_marketplace_categories(request):
            response.headers["Retry-After"] = str(max(1, int(contract._MARKETPLACE_CATEGORIES_RATE_LIMIT_WINDOW_SEC)))
            contract._apply_marketplace_categories_degraded_headers(response, mitigation="marketplace-categories-degraded-cache")
            return contract._build_marketplace_categories_degraded_payload(cached_payload)
        if cached_payload is not None and (now_ts - cached_at) < contract._MARKETPLACE_CATEGORIES_CACHE_TTL_SEC:
            return cached_payload
        with contract._MARKETPLACE_CATEGORIES_CACHE_LOCK:
            now_ts = contract.time.time()
            cached_payload = contract._MARKETPLACE_CATEGORIES_CACHE.get("payload")
            cached_at = float(contract._MARKETPLACE_CATEGORIES_CACHE.get("captured_at") or 0.0)
            if cached_payload is not None and (now_ts - cached_at) < contract._MARKETPLACE_CATEGORIES_CACHE_TTL_SEC:
                return cached_payload
            categories = (
                db.query(contract.models.Category)
                .order_by(contract.models.Category.name.asc())
                .all()
            )
            payload = [
                {
                    "id": int(category.id),
                    "name": str(category.name or ""),
                    "description": getattr(category, "description", None),
                }
                for category in categories
            ]
            contract._MARKETPLACE_CATEGORIES_CACHE["captured_at"] = now_ts
            contract._MARKETPLACE_CATEGORIES_CACHE["payload"] = payload
            return payload

    @router.post("/categories")
    def create_marketplace_category(
        payload: Dict[str, Any],
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        if not (getattr(current_user, "is_admin", False) or getattr(current_user, "is_superuser", False)):
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        name = str(payload.get("name") or "").strip()
        description = str(payload.get("description") or "").strip() or None
        if not name:
            raise HTTPException(status_code=400, detail="카테고리 이름이 필요합니다.")
        existing = db.query(contract.models.Category).filter(contract.models.Category.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="이미 존재하는 카테고리입니다.")
        category = contract.models.Category(name=name, description=description)
        db.add(category)
        db.commit()
        db.refresh(category)
        contract._invalidate_marketplace_categories_cache()
        return {"id": int(category.id), "name": str(category.name or ""), "description": category.description}

    @router.put("/categories/{category_id}")
    def update_marketplace_category(
        category_id: int,
        payload: Dict[str, Any],
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        if not (getattr(current_user, "is_admin", False) or getattr(current_user, "is_superuser", False)):
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        category = db.query(contract.models.Category).filter(contract.models.Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")
        next_name = str(payload.get("name") or category.name or "").strip()
        if not next_name:
            raise HTTPException(status_code=400, detail="카테고리 이름이 필요합니다.")
        category.name = next_name
        category.description = str(payload.get("description") or "").strip() or None
        db.add(category)
        db.commit()
        db.refresh(category)
        contract._invalidate_marketplace_categories_cache()
        return {"id": int(category.id), "name": str(category.name or ""), "description": category.description}

    @router.delete("/categories/{category_id}")
    def delete_marketplace_category(
        category_id: int,
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        if not (getattr(current_user, "is_admin", False) or getattr(current_user, "is_superuser", False)):
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        category = db.query(contract.models.Category).filter(contract.models.Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")
        db.delete(category)
        db.commit()
        contract._invalidate_marketplace_categories_cache()
        return {"id": category_id, "name": str(getattr(category, "name", "") or "")}

    return router