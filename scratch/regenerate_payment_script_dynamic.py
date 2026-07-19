import sys
import os
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.getcwd())

from backend.repository.postgres_project_repository import PostgresProjectRepository
from backend.agents.playwright_agent import PlaywrightAgent
from uuid import UUID

repo = PostgresProjectRepository()
tc_id = UUID("18c09ec4-a136-4d8a-aa01-d50be7ed333c")

test_case = repo.get_test_case(tc_id)
if not test_case:
    print(f"Error: Test case {tc_id} not found in PostgreSQL.")
    exit(1)

print(f"Loaded test case: {test_case.title}")

# Find associated project
scenario = repo.get_scenario(test_case.scenario_id)
requirement = repo.get_requirement(scenario.requirement_id)
projects = repo.list_projects()
target_proj = None
for proj in projects:
    if requirement.id in proj.requirements:
        target_proj = proj
        break

if not target_proj and projects:
    target_proj = projects[0]

target_url = target_proj.target_url if target_proj else "https://adactinhotelapp.com/"
target_username = "ADACTINFORQA"
target_password = "3U0515"

# Load vault credentials if available
try:
    from backend.services.vault_service import VaultService
    v_user, v_pass = VaultService().get_credentials(str(target_proj.id))
    if v_user:
        target_username = v_user
    if v_pass:
        target_password = v_pass
except Exception as e:
    print(f"Vault load warning: {e}")

# Initialize PlaywrightAgent
agent = PlaywrightAgent(repo=repo)

print("\nGenerating script dynamically via PlaywrightAgent...")
new_script = agent._generate_script(
    test_case=test_case,
    framework="playwright",
    target_url=target_url,
    target_username=target_username,
    target_password=target_password
)

print("\nDYNAMICALLY GENERATED PLAYWRIGHT SCRIPT:")
print("=" * 80)
print(new_script)
print("=" * 80)

# Verify against hallucinations before updating database
if "SearchHotel.aspx" in new_script:
    print("WARNING: Script contains hallucinated .aspx reference!")
if "input#continue" in new_script and "input#Submit" not in new_script:
    print("WARNING: Script might be skipping the Search page Submit button!")
if "textContent" in new_script and "order_no" in new_script:
    print("WARNING: Script is using textContent on order_no instead of inputValue!")

# Update PostgreSQL testcase script
test_case.playwright_script = new_script
repo.update_test_case(test_case)
print("Updated database with the dynamically generated script.")
