import sys
import os
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.getcwd())

from backend.repository.postgres_project_repository import PostgresProjectRepository
from backend.agents.playwright_agent import PlaywrightAgent
from backend.models.state import WorkflowState
from uuid import UUID

# Connect to database using existing repository provider
repo = PostgresProjectRepository()

tc_id = UUID("d462aba4-2f31-4862-a318-32220d21b55c")
test_case = repo.get_test_case(tc_id)

if not test_case:
    print(f"Error: Test case {tc_id} not found in DB.")
    exit(1)

print(f"Loaded test case: {test_case.title}")
print(f"Description of expectations: {test_case.expected_result}")
print(f"Steps defined in DB:")
for step in test_case.steps:
    print(f"  - {step}")

# Find associated scenario and requirement
scenario = repo.get_scenario(test_case.scenario_id)
requirement = repo.get_requirement(scenario.requirement_id)

# Initialize PlaywrightAgent
agent = PlaywrightAgent(repo=repo)

# Generate new script
new_script = agent._generate_script(
    test_case=test_case,
    framework="playwright",
    target_url="https://adactinhotelapp.com/",
    target_username="ADACTINFORQA",
    target_password="3U0515"
)

print("\nNEW GENERATED PLAYWRIGHT SCRIPT:")
print("=" * 80)
print(new_script)
print("=" * 80)

# Save back to database
test_case.playwright_script = new_script
repo.update_test_case(test_case)
print("Updated playwright_script in PostgreSQL successfully!")
