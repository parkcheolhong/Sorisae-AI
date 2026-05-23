import sqlite3
from pathlib import Path

repo_root = Path(__file__).resolve().parent
db_path = repo_root / "app.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 이미 존재하는지 확인
    cursor.execute("SELECT id FROM marketplace_products WHERE name = 'sorisae-interpreter'")
    existing = cursor.fetchone()
    if existing:
        print(f"이미 등록됨: ID {existing[0]}")
        conn.close()
        exit(0)

    # 새 상품 삽입
    cursor.execute("""
        INSERT INTO marketplace_products (
            name, description, category, price, currency,
            demo_url, github_url, file_url, file_type, file_size,
            thumbnail_url, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        'sorisae-interpreter',
        '13개 언어 통번역 Python 패키지 - 나도통역사\n한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어, 독일어, 러시아어, 아랍어, 베트남어, 태국어, 인도네시아어, 소리새어\n\n오프라인 모드: 인터넷 없이 내장 번역 DB로 기본 통역 가능\n하이브리드 연결: 지상파 → 모바일 → 위성 → 로컬 AI 자동 전환',
        '통역·번역',
        0.0,
        'KRW',
        'http://127.0.0.1:8000/api/marketplace/zip/sorisae-interpreter-v1.zip',
        'https://github.com/parkcheolhong/run_all_shinsegye.py',
        'http://127.0.0.1:8000/api/marketplace/zip/sorisae-interpreter-v1.zip',
        'zip',
        27620,
        '',
        'active'
    ))

    conn.commit()
    cursor.execute("SELECT last_insert_rowid()")
    product_id = cursor.fetchone()[0]
    print(f"상품 등록 완료: ID {product_id}")
    print(f"  이름: sorisae-interpreter")
    print(f"  파일: sorisae-interpreter-v1.zip (27.6 KB)")
    print(f"  URL: http://127.0.0.1:8000/api/marketplace/zip/sorisae-interpreter-v1.zip")

except Exception as e:
    print(f"오류: {e}")
    conn.rollback()
finally:
    conn.close()
