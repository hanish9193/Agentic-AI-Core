import sqlite3

conn = sqlite3.connect('backend/local_fallback.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in local_fallback.db:", [t[0] for t in tables])

conn.close()
