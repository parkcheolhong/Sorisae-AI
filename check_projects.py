import sqlite3

db = sqlite3.connect("app.db")
c = db.cursor()

print("projects 테이블 모든 항목:")
c.execute("SELECT id, title FROM projects ORDER BY id")
for row in c.fetchall():
    print(f"  ID {row[0]}: {row[1]}")

print("\nprojects 테이블 총 개수:")
c.execute("SELECT COUNT(*) FROM projects")
print(f"  {c.fetchone()[0]}개")

db.close()
