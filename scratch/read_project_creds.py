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
    cur.execute("SELECT id, name, target_username, target_password_enc FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if row:
        print(f"Project ID: {row[0]}")
        print(f"Project Name: {row[1]}")
        print(f"Target Username: {row[2]}")
        print(f"Target Password Enc: {row[3]}")
    else:
        print(f"Project {project_id} not found in database.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
