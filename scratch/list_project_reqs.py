import psycopg2

project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, title, requirement_id FROM requirements WHERE project_id = %s", (project_id,))
    rows = cur.fetchall()
    print("PostgreSQL Requirements:")
    print("=" * 80)
    for r in rows:
        print(f"ID: {r[0]} | Req ID: {r[2]} | Title: {r[1]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
