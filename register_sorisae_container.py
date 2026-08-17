#!/usr/bin/env python3
import sqlite3
from datetime import datetime

db = sqlite3.connect("/app/app.db")
c = db.cursor()

try:
    # 이미 존재하는지 확인
    c.execute("SELECT id FROM projects WHERE title = 'sorisae-interpreter'")
    existing = c.fetchone()
    if existing:
        print(f"이미 등록됨: ID {existing[0]}")
        db.close()
        exit(0)

    # 새 상품 삽입
    now = datetime.now().isoformat()
    c.execute("""
        INSERT INTO projects (
            title, description, price, category_id, author_id,
            image_url, demo_url, github_url, file_key,
            downloads, rating, is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'sorisae-interpreter',
        '13개 언어 통번역 Python 패키지\n\n지원 언어: 한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어, 독일어, 러시아어, 아랍어, 베트남어, 태국어, 인도네시아어, 소리새어\n\n특징:\n- 오프라인 모드: 인터넷 없이 내장 번역 DB로 기본 통역 가능\n- 하이브리드 연결: 지상파 → 모바일 → 위성 → 로컬 AI 자동 전환\n- 원본: https://github.com/parkcheolhong/run_all_shinsegye.py',
        0.0,
        2,  # 모바일 앱 카테고리 (ID 19도 category_id=2 사용)
        1,
        '',
        'http://127.0.0.1:8000/api/marketplace/zip/sorisae-interpreter-v1.zip',
        'https://github.com/parkcheolhong/run_all_shinsegye.py',
        'sorisae-interpreter-v1.zip',
        0,
        5.0,
        True,
        now,
        now
    ))

    db.commit()
    c.execute("SELECT last_insert_rowid()")
    product_id = c.fetchone()[0]
    print(f"[OK] 상품 등록: ID {product_id}")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
