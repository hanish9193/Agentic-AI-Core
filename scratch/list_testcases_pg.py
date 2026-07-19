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
    
    # Query test cases joining scenarios and requirements
    query = """
        SELECT tc.id, tc.title, tc.evaluation_status, tc.is_frozen, s.scenario_name 
        FROM test_cases tc
        JOIN scenarios s ON tc.scenario_id = s.id
        JOIN requirements r ON s.requirement_id = r.id
        WHERE r.project_id = %s
    """
    cur.execute(query, (project_id,))
    rows = cur.fetchall()
    print(f"Total test cases found in PG for project {project_id}: {len(rows)}")
    for idx, r in enumerate(rows):
        print(f"  {idx+1}. ID: {r[0]} | Title: {r[1]} | Eval Status: {r[2]} | Frozen: {r[3]} | Scenario: {r[4]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
