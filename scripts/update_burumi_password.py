import bcrypt, psycopg2

pw = b'SPACE0215@#@'
new_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode('utf-8')

pg_pw = open('/run/codeai-secrets/postgres_password.txt').read().strip()
conn = psycopg2.connect(host='postgres', port=5432, user='admin', password=pg_pw, dbname='devanalysis114')
cur = conn.cursor()
cur.execute('UPDATE users SET hashed_password=%s WHERE email=%s RETURNING id, email', (new_hash, 'burumi69@gmail.com'))
row = cur.fetchone()
conn.commit()
cur.close()
conn.close()
print(f'UPDATED id={row[0]} email={row[1]}')
print(f'verify={bcrypt.checkpw(pw, new_hash.encode())}')
