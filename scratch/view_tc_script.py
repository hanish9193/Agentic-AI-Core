import psycopg2

tc_id = "18c09ec4-a136-4d8a-aa01-d50be7ed333c"

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, title, playwright_script FROM test_cases WHERE id = %s", (tc_id,))
    row = cur.fetchone()
    if row:
        print(f"Test Case ID: {row[0]}")
        print(f"Title: {row[1]}")
        print("Playwright Script:")
        print("=" * 80)
        print(row[2])
        print("=" * 80)
    else:
        print(f"Test case {tc_id} not found in database.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
