#!/usr/bin/env python3
import sqlite3

db = sqlite3.connect("/app/app.db")
c = db.cursor()

# ID 10 상품 확인
c.execute("SELECT id, title, is_active FROM projects WHERE id = 10")
row = c.fetchone()
if row:
    print(f"ID: {row[0]}, 제목: {row[1]}, is_active: {row[2]}")
else:
    print("ID 10 없음")

# 모든 상품의 is_active 값 확인
print("\n모든 상품:")
c.execute("SELECT id, title, is_active FROM projects ORDER BY id")
for row in c.fetchall():
    print(f"  ID {row[0]}: {row[1][:30]}... is_active={row[2]}")

db.close()
