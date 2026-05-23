#!/usr/bin/env python3
# 백엔드 환경에서 SQLAlchemy로 직접 쿼리 실행
import sys
sys.path.insert(0, "/app")

from backend.marketplace import models, crud
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:////app/app.db")
Session = sessionmaker(bind=engine)
db = Session()

try:
    # SQLAlchemy로 직접 쿼리
    projects = db.query(models.Project).filter(models.Project.is_active == True).all()
    print(f"SQLAlchemy로 조회한 is_active=True 상품: {len(projects)}개")
    for p in projects:
        print(f"  ID {p.id}: {p.title}")
    
    # ID 10 직접 조회
    p10 = db.query(models.Project).filter(models.Project.id == 10).first()
    if p10:
        print(f"\nID 10 상세:")
        print(f"  title: {p10.title}")
        print(f"  is_active: {p10.is_active} (타입: {type(p10.is_active)})")
        print(f"  created_at: {p10.created_at}")
    else:
        print(f"\nID 10: 없음")
    
finally:
    db.close()
