import psycopg2

req_id = "66362e04-5a1e-481e-9319-b616a3684967"

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, scenario_name, approved, rejected FROM scenarios WHERE requirement_id = %s", (req_id,))
    rows = cur.fetchall()
    print(f"Scenarios in PostgreSQL for Requirement {req_id}:")
    print("=" * 80)
    for r in rows:
        print(f"ID: {r[0]} | Approved: {r[2]:5} | Rejected: {r[3]:5} | Name: {r[1]}")
    print("=" * 80)
    print(f"Total: {len(rows)}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
