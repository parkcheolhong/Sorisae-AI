from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from . import crud, models
from .database import get_db
from .vector_service import vector_service

router = APIRouter(tags=["marketplace-stats"])


def _serialize_currency_stat(value: float) -> int | float:
    rounded_value = round(float(value), 2)
    return int(rounded_value) if float(rounded_value).is_integer() else rounded_value


@router.get("/stats/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    crud.ensure_marketplace_seed_data(db)
    projects_count = db.query(models.Project).filter(
        models.Project.is_active.is_(True)
    ).count()
    users_count = db.query(models.User).count()
    purchases_count = db.query(models.Purchase).filter(
        models.Purchase.status == "completed"
    ).count()
    reviews_count = db.query(models.Review).count()

    return {
        "projects": projects_count,
        "users": users_count,
        "purchases": purchases_count,
        "reviews": reviews_count,
        "vector_search": vector_service.get_stats(),
    }


@router.get("/stats/top-projects")
def get_top_projects(limit: int = 10, db: Session = Depends(get_db)):
    crud.ensure_marketplace_seed_data(db)
    projects = db.query(models.Project).filter(
        models.Project.is_active.is_(True)
    ).order_by(models.Project.downloads.desc()).limit(limit).all()

    return [
        {
            "id": project.id,
            "title": project.title,
            "downloads": project.downloads,
            "rating": project.rating,
            "price": project.price,
        }
        for project in projects
    ]


@router.get("/stats/revenue")
def get_revenue_stats(db: Session = Depends(get_db)):
    crud.ensure_marketplace_seed_data(db)
    completed_purchases = db.query(models.Purchase).filter(
        models.Purchase.status == "completed"
    ).all()

    total_revenue = sum(purchase.amount for purchase in completed_purchases)
    average_purchase_amount = (
        total_revenue / len(completed_purchases)
        if completed_purchases
        else 0
    )

    return {
        "total_revenue": _serialize_currency_stat(total_revenue),
        "total_purchases": len(completed_purchases),
        "average_purchase_amount": _serialize_currency_stat(average_purchase_amount),
    }
