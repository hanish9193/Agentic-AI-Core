import sys
from uuid import UUID
from backend.repository.project_repository import get_project_repository

def main():
    repo = get_project_repository()
    # List all projects
    projects = repo.list_projects()
    print("=== PROJECTS ===")
    for p in projects:
        print(f"Project ID: {p.id}, Name: {p.name}")
        executions = repo.get_execution_results(p.id)
        print(f"  Executions count: {len(executions)}")
        for ex in sorted(executions, key=lambda x: x.executed_at, reverse=True)[:5]:
            print(f"    Execution ID: {ex.id}, Status: {ex.status.value}, Executed At: {ex.executed_at}, TestCase ID: {ex.test_case_id}")

if __name__ == "__main__":
    main()
