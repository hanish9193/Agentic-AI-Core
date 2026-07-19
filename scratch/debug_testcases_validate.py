import sys
import os

# Adjust sys.path to include workspace root
sys.path.append(os.getcwd())

from backend.database.db import SessionLocal
from backend.database.db_models import TestCaseDB, ScenarioDB, RequirementDB
from backend.models.test_case import TestCase
from sqlalchemy import select

session = SessionLocal()
project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"
stmt = (
    select(TestCaseDB)
    .join(ScenarioDB, TestCaseDB.scenario_id == ScenarioDB.id)
    .join(RequirementDB, ScenarioDB.requirement_id == RequirementDB.id)
    .where(RequirementDB.project_id == project_id)
)
db_tcs = session.scalars(stmt).all()
print(f"Retrieved {len(db_tcs)} test cases from database.")

for tc in db_tcs:
    try:
        TestCase.model_validate(tc, from_attributes=True)
    except Exception as e:
        print("="*60)
        print(f"Validation error on test case ID: {tc.id} Title: {tc.title}")
        import traceback
        traceback.print_exc()
        print("="*60)
        break

session.close()
