"""
Same two-layer approach as test_scenario_agent.py:

1. LLMService <-> litellm, using real mock_response - proves LLMService
   is genuinely generic (works for TestCaseListResponse, not just the
   schema ScenarioAgent happens to use).
2. TestCaseAgent <-> LLMService, using StubLLMService (conftest.py) -
   verifies the agent's own logic: scenario-name correlation, priority
   inheritance, and the failure mode unique to this agent (an LLM
   response referencing a scenario that doesn't exist).
"""

import pytest

from backend.agents.test_case_agent import TestCaseAgent, TestCaseListResponse
from backend.config.settings import LLMConfig
from backend.models.requirement import Requirement
from backend.models.scenario import Scenario
from backend.models.state import WorkflowState
from backend.services.llm import LLMService, LLMServiceError

_TEST_LLM_CONFIG = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="fake-key-for-test")


def test_llm_service_structured_generate_parses_test_case_mock_response():
    """Same LLMService, different schema - confirms it's genuinely
    generic rather than accidentally shaped around ScenarioAgent."""
    service = LLMService(config=_TEST_LLM_CONFIG)

    result = service.structured_generate(
        user="irrelevant - mock_response short-circuits the call",
        response_model=TestCaseListResponse,
        mock_response=(
            '{"test_cases": [{"scenario_name": "Valid Login", "title": "Verify login", '
            '"preconditions": ["App running"], "steps": ["Go to login", "Enter creds"], '
            '"expected_result": "User is logged in"}]}'
        ),
    )

    assert len(result.test_cases) == 1
    assert result.test_cases[0].scenario_name == "Valid Login"


def _state_with_scenarios() -> WorkflowState:
    """Matches canned_scenario_batch in conftest.py exactly - the shared
    stub_llm_service fixture's canned test cases are keyed to these three
    scenario names, so this state must use the same ones."""
    requirement = Requirement(title="Login flow", description="User can log in with valid credentials")
    state = WorkflowState(requirement=requirement)
    state.generated_scenarios = [
        Scenario(requirement_id=requirement.id, scenario_name="Valid Login", description="desc", priority="high"),
        Scenario(requirement_id=requirement.id, scenario_name="Invalid Login", description="desc", priority="medium"),
        Scenario(requirement_id=requirement.id, scenario_name="Empty Password", description="desc", priority="low"),
    ]
    return state


def test_test_case_agent_correlates_by_scenario_name_and_inherits_priority(stub_llm_service):
    agent = TestCaseAgent(llm_service=stub_llm_service)
    state = _state_with_scenarios()

    result = agent.run(state)

    assert len(result.generated_test_cases) == 3
    tc = result.generated_test_cases[0]
    matching_scenario = next(s for s in state.generated_scenarios if s.id == tc.scenario_id)
    assert tc.priority == matching_scenario.priority  # inherited, not re-invented by the LLM
    assert "TestCase Agent generated 3 test cases" in result.logs[-1]


def test_test_case_agent_rejects_unrecognized_scenario_name():
    """The failure mode unique to this agent: LLM echoes back a
    scenario_name that doesn't match anything we sent it. Must fail
    loudly - silently dropping the test case would hide a real problem."""
    from backend.tests.conftest import StubLLMService

    bad_batch = TestCaseListResponse.model_validate(
        {
            "test_cases": [
                {
                    "scenario_name": "Some Scenario That Does Not Exist",
                    "title": "x",
                    "preconditions": [],
                    "steps": ["step"],
                    "expected_result": "y",
                }
            ]
        }
    )
    stub = StubLLMService({TestCaseListResponse: bad_batch})
    agent = TestCaseAgent(llm_service=stub)
    state = _state_with_scenarios()

    with pytest.raises(ValueError, match="unrecognized scenario"):
        agent.run(state)


def test_test_case_agent_requires_requirement():
    agent = TestCaseAgent(llm_service=None)  # never called - the guard fires first
    state = WorkflowState(requirement=None)

    with pytest.raises(ValueError):
        agent.run(state)


def test_test_case_agent_requires_generated_scenarios():
    agent = TestCaseAgent(llm_service=None)  # never called - the guard fires first
    requirement = Requirement(title="x", description="y")
    state = WorkflowState(requirement=requirement)  # no scenarios added

    with pytest.raises(ValueError):
        agent.run(state)