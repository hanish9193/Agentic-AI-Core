"""
Shared fixtures for backend/tests/. pytest auto-discovers this file for
every test in this directory - anything used by more than one test file
belongs here, not copy-pasted into each one.
"""

import pytest

from backend.agents.scenario_agent import _GeneratedScenario, _GeneratedScenarioBatch


class StubLLMService:
    """Test double for LLMService - never touches litellm. Lets agent and
    graph tests run with zero network calls and no API key, by satisfying
    the same structured_generate(...) signature with a canned answer."""

    def __init__(self, batch: _GeneratedScenarioBatch):
        self._batch = batch

    def structured_generate(self, *, user, response_model, **kwargs):
        return self._batch


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
def stub_llm_service(canned_scenario_batch: _GeneratedScenarioBatch) -> StubLLMService:
    return StubLLMService(canned_scenario_batch)