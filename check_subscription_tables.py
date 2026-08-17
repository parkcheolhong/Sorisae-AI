#!/usr/bin/env python3
import sqlite3

db = sqlite3.connect("/app/app.db")
c = db.cursor()

# 테이블 목록 확인
print("=== 구독 관련 테이블 ===")
c.execute("""
  SELECT name FROM sqlite_master 
  WHERE type='table' AND name LIKE '%subscription%'
  ORDER BY name
""")
for row in c.fetchall():
    print(f"  ✓ {row[0]}")

# 각 테이블의 레코드 수
print("\n=== 데이터 현황 ===")
tables = [
    "subscription_products",
    "subscription_plans", 
    "subscription_entitlements",
    "user_subscriptions",
    "subscription_transactions"
]

for table in tables:
    try:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"  {table}: {count}개")
    except:
        print(f"  {table}: [테이블 없음]")

# projects와 subscription 연동 확인
print("\n=== projects 테이블 구조 ===")
c.execute("PRAGMA table_info(projects)")
cols = [row[1] for row in c.fetchall()]
if any("subscription" in col for col in cols):
    print(f"  ✓ subscription FK 있음: {[c for c in cols if 'subscription' in c]}")
else:
    print(f"  ✗ subscription FK 없음")

db.close()
