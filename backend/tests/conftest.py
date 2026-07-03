"""
Shared fixtures for backend/tests/. pytest auto-discovers this file for
every test in this directory - anything used by more than one test file
belongs here, not copy-pasted into each one.
"""

import pytest

from backend.agents.scenario_agent import _GeneratedScenario, _GeneratedScenarioBatch
from backend.agents.test_case_agent import TestCaseListResponse, TestCaseResponse


class StubLLMService:
    """Test double for LLMService - never touches litellm. Keyed by
    response_model so one stub instance can serve multiple agents in a
    single graph-level test, each expecting a different schema back."""

    def __init__(self, responses: dict[type, object]):
        self._responses = responses

    def structured_generate(self, *, user, response_model, **kwargs):
        try:
            return self._responses[response_model]
        except KeyError:
            raise AssertionError(
                f"StubLLMService has no canned response for {response_model.__name__} - "
                f"add one when constructing the stub for this test"
            )


@pytest.fixture
def canned_scenario_batch() -> _GeneratedScenarioBatch:
    return _GeneratedScenarioBatch(
        scenarios=[
            _GeneratedScenario(
                scenario_name="Valid Login",
                description="User logs in with correct username and password",
                priority="high",
            ),
            _GeneratedScenario(
                scenario_name="Invalid Login",
                description="User attempts login with an incorrect password",
                priority="medium",
            ),
            _GeneratedScenario(
                scenario_name="Empty Password",
                description="User submits the login form with an empty password field",
                priority="low",
            ),
        ]
    )


@pytest.fixture
def canned_test_case_batch(canned_scenario_batch: _GeneratedScenarioBatch) -> TestCaseListResponse:
    return TestCaseListResponse(
        test_cases=[
            TestCaseResponse(
                scenario_name=s.scenario_name,
                title=f"Verify: {s.scenario_name}",
                preconditions=["Application is running"],
                steps=["Navigate to the login page", f"Execute scenario: {s.description}"],
                expected_result=f"System behaves correctly for '{s.scenario_name}'",
            )
            for s in canned_scenario_batch.scenarios
        ]
    )


@pytest.fixture
def stub_llm_service(
    canned_scenario_batch: _GeneratedScenarioBatch,
    canned_test_case_batch: TestCaseListResponse,
) -> StubLLMService:
    return StubLLMService(
        {
            _GeneratedScenarioBatch: canned_scenario_batch,
            TestCaseListResponse: canned_test_case_batch,
        }
    )