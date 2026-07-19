import psycopg2

exec_id = "39a331e4-2fc1-4751-94ea-98e93867891d"

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, status, logs, error_message FROM executions WHERE id = %s", (exec_id,))
    row = cur.fetchone()
    if row:
        print(f"Execution ID: {row[0]}")
        print(f"Status: {row[1]}")
        print(f"Error Message: {row[3]}")
        print("Logs:")
        print("=" * 80)
        print(row[2])
        print("=" * 80)
    else:
        print(f"Execution {exec_id} not found in database.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
