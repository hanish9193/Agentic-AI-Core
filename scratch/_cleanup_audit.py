import psycopg2

conn = psycopg2.connect('postgresql://postgres:hanish13@localhost:5432/Agentic_ai')
cur = conn.cursor()

cur.execute("SELECT id FROM projects WHERE name = 'Agentic AI Automation'")
keep_id = cur.fetchone()[0]
print(f"Keeping project: Agentic AI Automation (id: {keep_id})")

cur.execute("SELECT COUNT(*) FROM projects")
total = cur.fetchone()[0]
print(f"Total projects before cleanup: {total}")

cur.execute("SELECT COUNT(*) FROM projects WHERE name != 'Agentic AI Automation'")
to_delete = cur.fetchone()[0]
print(f"Projects to delete: {to_delete}")

print("\nRelated data (all projects):")
tables = [
    'requirements', 'scenarios', 'test_cases', 'executions',
    'reports', 'documents', 'scenario_notes', 'test_case_notes',
    'project_users', 'releases', 'test_cycles',
    'refresh_tokens', 'audit_logs'
]
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

conn.close()
