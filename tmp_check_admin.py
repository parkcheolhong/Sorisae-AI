import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL", "")
sync_url = DB_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
eng = create_engine(sync_url)

with eng.connect() as con:
    rows = con.execute(text(
        "SELECT email, is_admin, is_staff FROM users WHERE is_admin=true OR is_staff=true LIMIT 5"
    )).fetchall()
    for r in rows:
        print(r[0], "admin=" + str(r[1]), "staff=" + str(r[2]))
    if not rows:
        print("No admin/staff users found")
        # print first 3 users
        rows2 = con.execute(text("SELECT email, is_admin, is_staff FROM users LIMIT 3")).fetchall()
        for r in rows2:
            print(r[0], "admin=" + str(r[1]), "staff=" + str(r[2]))
