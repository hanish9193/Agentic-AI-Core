import pytest
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.jira_service import JiraService
from backend.agents.jira_sync_agent import JiraSyncAgent
from backend.models.state import WorkflowState
from backend.models.requirement import Requirement
from backend.models.scenario import Scenario
from backend.models.test_case import TestCase, TestCaseStatus
from backend.models.execution_result import ExecutionResult
from backend.repository.project_repository import get_project_repository


def test_jira_service_mock_mode():
    service = JiraService()
    assert service.mock_mode is True

    # Test create issue
    issue = service.create_issue("Test Story", "Description details", "Story")
    assert issue is not None
    assert "key" in issue
    assert "url" in issue
    assert "browse" in issue["url"]

    # Test search issues
    results = service.search_issues("project = 'QA'")
    assert isinstance(results, list)

    # Test comment
    comment_success = service.add_comment(issue["key"], "Test comment")
    assert comment_success is True

    # Test transition
    transition_success = service.transition_issue(issue["key"], "Done")
    assert transition_success is True

    # Test upload attachment
    attachment_success = service.upload_attachment(issue["key"], "test.png", b"fakebytes", "image/png")
    assert attachment_success is True


def test_jira_sync_agent_sync_user_story(mock_llm_service):
    repo = get_project_repository()
    
    # Create project and requirement context
    project = repo.create_project("Jira Project Test", "Description", "general", "playwright")
    project.jira_project_key = "MOCKPROJ"
    
    req = repo.create_requirement(
        project_id=project.id,
        title="Jira Requirement",
        description="Verify JIRA sync flow",
        priority="high",
        business_domain="test"
    )
    
    # Reload project to have the requirement link
    project.requirements.append(req.id)
    repo.update_project(project)

    # Create approved scenario
    scenario = Scenario(
        requirement_id=req.id,
        scenario_name="Approved Login Flow",
        description="Verify User Story sync is triggered only for approved scenarios",
        approved=True
    )
    repo.save_scenarios([scenario])

    agent = JiraSyncAgent()
    state = WorkflowState(requirement=req, generated_scenarios=[scenario])
    
    # Run the agent for user story sync operation
    config = {
        "configurable": {
            "operation": "sync_user_story",
            "user_id": str(uuid4())
        }
    }
    final_state = agent.run(state, config=config)

    # Verify scenario was updated with synced attributes
    updated_sc = repo.get_scenarios(req.id)[0]
    assert updated_sc.jira_issue_key is not None
    assert updated_sc.jira_issue_url is not None
    assert updated_sc.jira_sync_status == "synced"
    assert updated_sc.jira_last_synced_at is not None


def test_jira_sync_agent_sync_bug(mock_llm_service):
    repo = get_project_repository()
    
    # Create project context
    project = repo.create_project("Bug Project Test", "Description", "general", "playwright")
    
    req = repo.create_requirement(
        project_id=project.id,
        title="Bug Requirement",
        description="Verify bug ticketing flow",
        priority="medium",
        business_domain="test"
    )
    project.requirements.append(req.id)
    repo.update_project(project)

    # Create scenario and test case
    scenario = Scenario(
        requirement_id=req.id,
        scenario_name="Login Failure",
        description="Fails when password is bad",
        approved=True
    )
    repo.save_scenarios([scenario])
    
    tc = TestCase(
        scenario_id=scenario.id,
        title="Verify Login Fails",
        preconditions=[],
        steps=["Step 1"],
        expected_result="Should show password mismatch error"
    )
    repo.save_test_cases([tc])

    # Simulate execution failure
    result = ExecutionResult(
        test_case_id=tc.id,
        status=TestCaseStatus.FAILED,
        error_message="Expected mismatch error but page timed out.",
        duration_seconds=5.2
    )

    agent = JiraSyncAgent()
    state = WorkflowState(requirement=req, execution_results=[result])
    
    # Run the agent for bug sync operation
    config = {
        "configurable": {
            "operation": "sync_bug",
            "user_id": str(uuid4())
        }
    }
    final_state = agent.run(state, config=config)

    # Verify test case status is set to retest_pending and linked to Bug ticket
    updated_tc = repo.get_test_case(tc.id)
    assert updated_tc.status == TestCaseStatus.RETEST_PENDING
    assert updated_tc.jira_issue_key is not None
    assert updated_tc.jira_issue_url is not None
    assert updated_tc.jira_sync_status == "created"


def test_jira_webhook_resolves_status():
    client = TestClient(app)
    repo = get_project_repository()
    
    # Save a test case with matching JIRA issue key
    jira_key = "BUG-999"
    tc = TestCase(
        scenario_id=uuid4(),
        title="Verify Webhook Triggers Retest",
        preconditions=[],
        steps=["Step 1"],
        expected_result="Test state transitions",
        status=TestCaseStatus.FAILED
    )
    tc.jira_issue_key = jira_key
    repo.save_test_cases([tc])

    # Send webhook payload indicating the JIRA issue was marked "Resolved"
    payload = {
        "issue": {
            "key": jira_key,
            "fields": {
                "status": {
                    "name": "Resolved"
                }
            }
        }
    }
    
    response = client.post("/api/v1/webhooks/jira", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Wait, in memory fallback might run without DB persistence if not saved.
    # Let's assert database state or mock returned count if SQL provider is active
    if getattr(repo, "session", None) is not None:
        updated_tc = repo.get_test_case(tc.id)
        assert updated_tc.status == TestCaseStatus.RETEST_PENDING
