import json
import urllib.request

response = urllib.request.urlopen("http://127.0.0.1:8000/api/marketplace/projects")
data = json.loads(response.read().decode("utf-8"))

print(f"전체 응답:")
print(f"  total: {data['total']}")
print(f"  skip: {data['skip']}")
print(f"  limit: {data['limit']}")
print(f"  projects.length: {len(data['projects'])}")

# DB와 비교
import sqlite3
db = sqlite3.connect("/app/app.db")
c = db.cursor()
c.execute("SELECT COUNT(*) FROM projects WHERE is_active = 1")
db_count = c.fetchone()[0]
db.close()

print(f"\nDB 상품 수 (is_active=1): {db_count}")
print(f"API total: {data['total']}")
print(f"불일치: {db_count != data['total']}")
