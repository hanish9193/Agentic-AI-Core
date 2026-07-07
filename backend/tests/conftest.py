"""
Shared fixtures for backend/tests/. pytest auto-discovers this file for
every test in this directory - anything used by more than one test file
belongs here, not copy-pasted into each one.
"""

import pytest

from backend.agents.evaluation_agent import _EvaluationBatch, _TestCaseEvaluation
from backend.agents.scenario_agent import _GeneratedScenario, _GeneratedScenarioBatch
from backend.agents.test_case_agent import TestCaseListResponse, TestCaseResponse
from backend.services.playwright_runner import PlaywrightRunResult

_CANNED_PLAYWRIGHT_CODE = """import { test, expect } from "@playwright/test";

test("Verify: Valid Login", async ({ page }) => {
  // Step 1: Navigate to the login page
  await page.goto("/login");
  // Step 2: Enter valid credentials - locator is a best guess, no real page to inspect yet
  await page.getByLabel("Username").fill("testuser");
  await page.getByLabel("Password").fill("correct-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("Welcome")).toBeVisible();
});
"""


class StubLLMService:
    """Test double for LLMService - never touches litellm.

    structured_generate() is keyed by response_model, so one stub can
    serve multiple JSON-based agents in a single graph-level test, each
    expecting a different schema back.

    generate() has no response_model to key off (PlaywrightAgent's output
    is plain code, not a validated schema) - it just returns a single
    canned string, since only one agent currently uses this method."""

    def __init__(self, responses: dict[type, object] | None = None, generate_response: str | None = None):
        self._responses = responses or {}
        self._generate_response = generate_response if generate_response is not None else _CANNED_PLAYWRIGHT_CODE

    def structured_generate(self, *, user, response_model, **kwargs):
        try:
            return self._responses[response_model]
        except KeyError:
            raise AssertionError(
                f"StubLLMService has no canned response for {response_model.__name__} - "
                f"add one when constructing the stub for this test"
            )

    def generate(self, *, system, user, **kwargs) -> str:
        return self._generate_response


class FakePlaywrightRunner:
    """Test double for PlaywrightRunner - never touches npx/subprocess.
    Returns the same canned result for every call by default; construct
    with result_map={run_id: PlaywrightRunResult} for per-test-case
    control when a test needs different outcomes for different scripts."""

    def __init__(self, default_result: PlaywrightRunResult | None = None, result_map: dict[str, PlaywrightRunResult] | None = None):
        self._default = default_result or PlaywrightRunResult(status="passed", duration_seconds=1.5)
        self._result_map = result_map or {}

    def run(self, script: str, run_id: str) -> PlaywrightRunResult:
        return self._result_map.get(run_id, self._default)


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


def _canned_test_case_batch() -> TestCaseListResponse:
    return TestCaseListResponse(
        test_cases=[
            TestCaseResponse(
                scenario_number=1,
                title="Verify: Valid Login",
                preconditions=["Application is running"],
                steps=["Execute scenario: Valid Login"],
                expected_result="System behaves correctly for 'Valid Login'",
            ),
            TestCaseResponse(
                scenario_number=2,
                title="Verify: Invalid Login",
                preconditions=["Application is running"],
                steps=["Execute scenario: Invalid Login"],
                expected_result="System behaves correctly for 'Invalid Login'",
            ),
            TestCaseResponse(
                scenario_number=3,
                title="Verify: Empty Password",
                preconditions=["Application is running"],
                steps=["Execute scenario: Empty Password"],
                expected_result="System behaves correctly for 'Empty Password'",
            ),
        ]
    )

@pytest.fixture
def canned_evaluation_batch(canned_scenario_batch: _GeneratedScenarioBatch) -> _EvaluationBatch:
    return _EvaluationBatch(
        evaluations=[
            _TestCaseEvaluation(test_case_number=i, relevance=0.9, completeness=0.9, reason="Looks solid")
            for i in range(1, len(canned_scenario_batch.scenarios) + 1)
        ]
    )


@pytest.fixture
def stub_llm_service(
    canned_scenario_batch: _GeneratedScenarioBatch,
    canned_evaluation_batch: _EvaluationBatch,
) -> StubLLMService:
    return StubLLMService(
        responses={
            _GeneratedScenarioBatch: canned_scenario_batch,
            TestCaseListResponse: _canned_test_case_batch(),
            _EvaluationBatch: canned_evaluation_batch,
        },
        generate_response=_CANNED_PLAYWRIGHT_CODE,
    )


@pytest.fixture
def fake_playwright_runner() -> FakePlaywrightRunner:
    return FakePlaywrightRunner()