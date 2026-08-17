import sqlite3
conn = sqlite3.connect('/app/app.db')
cur = conn.cursor()

# projects 테이블 구조
cur.execute("PRAGMA table_info(projects)")
print("=== projects 테이블 컬럼 ===")
for row in cur.fetchall():
    print(row)

# categories 테이블
cur.execute("PRAGMA table_info(categories)")
print("\n=== categories 테이블 컬럼 ===")
for row in cur.fetchall():
    print(row)

# 현재 projects 데이터 샘플
cur.execute("SELECT id, name, category_id, status FROM projects LIMIT 5")
print("\n=== projects 샘플 ===")
for row in cur.fetchall():
    print(row)

# categories 데이터
cur.execute("SELECT id, name FROM categories")
print("\n=== categories 데이터 ===")
for row in cur.fetchall():
    print(row)

conn.close()
