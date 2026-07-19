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
    
    # Query scenarios joining requirements and projects
    query = """
        SELECT s.id, s.scenario_name, s.approved, s.rejected, r.title 
        FROM scenarios s
        JOIN requirements r ON s.requirement_id = r.id
        WHERE r.project_id = %s
    """
    cur.execute(query, (project_id,))
    rows = cur.fetchall()
    print(f"Total scenarios found in PG for project {project_id}: {len(rows)}")
    for idx, r in enumerate(rows):
        print(f"  {idx+1}. ID: {r[0]} | Name: {r[1]} | Approved: {r[2]} | Rejected: {r[3]} | Req: {r[4]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
