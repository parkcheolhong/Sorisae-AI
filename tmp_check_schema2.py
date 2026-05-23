import sqlite3
conn = sqlite3.connect('/app/app.db')
cur = conn.cursor()

cur.execute("SELECT id, title, category_id, is_active FROM projects LIMIT 10")
print("=== projects 샘플 ===")
for row in cur.fetchall():
    print(row)

cur.execute("SELECT id, name FROM categories")
print("\n=== categories ===")
for row in cur.fetchall():
    print(row)

# count
cur.execute("SELECT COUNT(*) FROM projects")
print(f"\n총 projects: {cur.fetchone()[0]}")

conn.close()
