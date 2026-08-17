import sqlite3

db = sqlite3.connect("app.db")
c = db.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for row in c.fetchall():
    print(row[0])
db.close()
