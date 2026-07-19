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
    
    # Alter commands to add missing columns if they don't exist
    cur.execute("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS rejected BOOLEAN NOT NULL DEFAULT FALSE")
    cur.execute("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS path_type VARCHAR(100) NOT NULL DEFAULT 'happy_path'")
    cur.execute("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS tags JSON NOT NULL DEFAULT '[]'")
    
    conn.commit()
    print("PostgreSQL 'scenarios' table schema updated successfully with rejected, path_type, and tags columns.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to update PostgreSQL database schema: {e}")
