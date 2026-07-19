import psycopg2

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    
    tables = [
        "projects", "requirements", "scenarios", "test_cases", 
        "documents", "executions", "reports", "releases", "test_cycles"
    ]
    
    print("PostgreSQL Database 'Agentic_ai' Migrated Content Verification:")
    print("=" * 60)
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"Table '{table:15}': {count} records found.")
        except Exception as te:
            print(f"Table '{table:15}': Error querying table: {te}")
            conn.rollback()
            
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to connect or query PostgreSQL: {e}")
