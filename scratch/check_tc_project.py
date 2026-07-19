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
    
    query = """
        SELECT tc.id, tc.title, tc.scenario_id, s.scenario_name, s.requirement_id, r.title, r.project_id, p.name
        FROM test_cases tc
        LEFT JOIN scenarios s ON tc.scenario_id = s.id
        LEFT JOIN requirements r ON s.requirement_id = r.id
        LEFT JOIN projects p ON r.project_id = p.id
        WHERE tc.id = %s
    """
    cur.execute(query, (tc_id,))
    row = cur.fetchone()
    if row:
        print(f"Test Case ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Scenario ID: {row[2]} | Name: {row[3]}")
        print(f"Requirement ID: {row[4]} | Title: {row[5]}")
        print(f"Project ID: {row[6]} | Name: {row[7]}")
    else:
        print(f"Test case {tc_id} not found.")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
