import psycopg2

conn = psycopg2.connect('postgresql://postgres:hanish13@localhost:5432/Agentic_ai')
cur = conn.cursor()

cur.execute("""
    SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    ORDER BY tc.table_name
""")
for r in cur.fetchall():
    print(f"{r[0]}.{r[1]} -> {r[2]}")

conn.close()
