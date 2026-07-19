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
    
    # Query test cases linked to project
    query = """
        SELECT tc.id, tc.title, tc.evaluation_status, tc.is_frozen, s.scenario_name 
        FROM test_cases tc
        JOIN scenarios s ON tc.scenario_id = s.id
        JOIN requirements r ON s.requirement_id = r.id
        WHERE r.project_id = %s
    """
    cur.execute(query, (project_id,))
    rows = cur.fetchall()
    
    print(f"Test Cases for Project {project_id} in PostgreSQL:")
    print("=" * 100)
    for r in rows:
        print(f"ID: {r[0]} | Status: {r[2]:10} | Frozen: {r[3]:5} | Scenario: {r[4][:30]} | Title: {r[1]}")
    print("=" * 100)
    print(f"Total: {len(rows)}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
