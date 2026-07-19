import psycopg2

ids = [
    "d462aba4-2f31-4862-a318-32220d21b55c",
    "18c09ec4-a136-4d8a-aa01-d50be7ed333c"
]

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    for i in ids:
        cur.execute("SELECT id, title, is_deleted, evaluation_status FROM test_cases WHERE id = %s", (i,))
        row = cur.fetchone()
        if row:
            print(f"ID={row[0]} | Title={row[1]} | is_deleted={row[2]} | status={row[3]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
