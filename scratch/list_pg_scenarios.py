import psycopg2

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, requirement_id, scenario_name, approved, rejected FROM scenarios LIMIT 30")
    rows = cur.fetchall()
    print("PostgreSQL Scenario Records:")
    print("=" * 80)
    for r in rows:
        print(f"ID: {r[0]} | ReqID: {r[1]} | Name: {r[2]} | Approved: {r[3]} | Rejected: {r[4]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
