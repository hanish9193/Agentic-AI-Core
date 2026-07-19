from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.append(os.getcwd())

from backend.repository.postgres_project_repository import PostgresProjectRepository
from uuid import UUID

repo = PostgresProjectRepository()
tc_id = UUID("d462aba4-2f31-4862-a318-32220d21b55c")

# Test 1: Direct SQL query
print("=== SQL TEST ===")
import psycopg2
conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="Agentic_ai",
    user="postgres",
    password="hanish13"
)
cur = conn.cursor()
cur.execute("SELECT id, title FROM test_cases WHERE id = %s", (str(tc_id),))
row = cur.fetchone()
print("Direct SQL fetch row:", row)
cur.close()
conn.close()

# Test 2: Repository fetch
print("=== REPOSITORY TEST ===")
tc = repo.get_test_case(tc_id)
print("Repository fetch tc object:", tc)
