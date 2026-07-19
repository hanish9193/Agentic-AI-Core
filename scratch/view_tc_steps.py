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
    cur.execute("SELECT title, steps, expected_result FROM test_cases WHERE id = %s", (tc_id,))
    row = cur.fetchone()
    if row:
        print(f"Title: {row[0]}")
        print("Steps:")
        for s in row[1]:
            print(f"  - {s}")
        print(f"Expected Result: {row[2]}")
    else:
        print(f"Testcase {tc_id} not found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
