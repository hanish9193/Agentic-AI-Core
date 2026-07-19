import psycopg2

tc_id = "d462aba4-2f31-4862-a318-32220d21b55c"

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT title, playwright_script FROM test_cases WHERE id = %s", (tc_id,))
    row = cur.fetchone()
    if row:
        print(f"Title: {row[0]}")
        print("Playwright Script:")
        print("=" * 80)
        print(row[1])
        print("=" * 80)
    else:
        print(f"Test case {tc_id} not found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
