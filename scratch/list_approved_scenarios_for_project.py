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
    
    # Query scenarios linked to project through requirements
    query = """
        SELECT s.id, s.scenario_name, s.approved, s.rejected, r.project_id 
        FROM scenarios s
        JOIN requirements r ON s.requirement_id = r.id
        WHERE r.project_id = %s
    """
    cur.execute(query, (project_id,))
    rows = cur.fetchall()
    
    print(f"Scenarios for Project {project_id}:")
    print("=" * 90)
    total = 0
    approved_count = 0
    for r in rows:
        total += 1
        if r[2]:
            approved_count += 1
        print(f"ID: {r[0]} | Approved: {r[2]:5} | Rejected: {r[3]:5} | Name: {r[1]}")
        
    print("=" * 90)
    print(f"Total Scenarios: {total} | Approved: {approved_count}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
