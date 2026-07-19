"""
Database cleanup script - removes all projects except 'Agentic AI Automation'.
Deletes in FK-safe order (children first).
"""
import psycopg2
import sys

DB_URL = 'postgresql://postgres:hanish13@localhost:5432/Agentic_ai'
KEEP_NAME = 'Agentic AI Automation'

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Get the project to keep
    cur.execute("SELECT id FROM projects WHERE name = %s", (KEEP_NAME,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: Project '{KEEP_NAME}' not found!")
        conn.close()
        sys.exit(1)
    keep_id = row[0]
    print(f"Keeping: {KEEP_NAME} (id: {keep_id})")

    # Count before
    cur.execute("SELECT COUNT(*) FROM projects")
    before = cur.fetchone()[0]
    print(f"Projects before: {before}")

    # Delete in FK-safe order (children before parents)
    delete_order = [
        ('test_case_notes', 'test_case_id IN (SELECT id FROM test_cases WHERE scenario_id IN (SELECT id FROM scenarios WHERE requirement_id IN (SELECT id FROM requirements WHERE project_id != %s)))'),
        ('scenario_notes', 'scenario_id IN (SELECT id FROM scenarios WHERE requirement_id IN (SELECT id FROM requirements WHERE project_id != %s))'),
        ('test_cases', 'scenario_id IN (SELECT id FROM scenarios WHERE requirement_id IN (SELECT id FROM requirements WHERE project_id != %s))'),
        ('scenarios', 'requirement_id IN (SELECT id FROM requirements WHERE project_id != %s)'),
        ('reports', 'project_id != %s'),
        ('executions', 'project_id != %s'),
        ('test_cycles', 'release_id IN (SELECT id FROM releases WHERE project_id != %s)'),
        ('requirements', 'project_id != %s'),
        ('releases', 'project_id != %s'),
        ('documents', 'project_id != %s'),
        ('audit_logs', 'project_id != %s'),
        ('project_users', 'project_id != %s'),
        ('refresh_tokens', 'TRUE'),
        ('projects', 'id != %s'),
    ]

    for table, where_clause in delete_order:
        # Replace %s with the keep_id
        query = f"DELETE FROM {table} WHERE {where_clause.replace('%s', repr(keep_id))}"
        cur.execute(f"DELETE FROM {table} WHERE {where_clause}", (keep_id,))
        deleted = cur.rowcount
        if deleted > 0:
            print(f"  Deleted {deleted} rows from {table}")

    # Count after
    cur.execute("SELECT COUNT(*) FROM projects")
    after = cur.fetchone()[0]
    print(f"\nProjects after: {after}")
    print(f"Removed: {before - after} projects")

    conn.commit()
    print("\nCleanup complete. Database committed.")

    # Verify
    cur.execute("SELECT name FROM projects ORDER BY name")
    remaining = cur.fetchall()
    print(f"\nRemaining projects ({len(remaining)}):")
    for r in remaining:
        print(f"  - {r[0]}")

    conn.close()

if __name__ == '__main__':
    main()
