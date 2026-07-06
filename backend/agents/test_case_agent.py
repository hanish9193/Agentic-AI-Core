"""
Generates test cases via LLM instead of hardcoded data. Same shape as
ScenarioAgent's conversion: graph and BaseAgent interface untouched, only
what's inside run() changed.

Correlates by scenario_number (a 1-based index into the numbered list
already shown in the prompt), not by echoing scenario_name back. This
used to be name-based, and it failed in a real live run: the LLM
returned "Upload exceeds Limit" for a scenario actually named "Upload
exceeds Limit (5.1MB PNG)" - a paraphrase, despite the prompt explicitly
saying not to. Numbers don't get paraphrased the same way text does,
and this exact pattern (numbered correlation, validate we got back
exactly {1..N}) has never failed once in EvaluationAgent, which used it
from the start. This should have been built the same way from day one.

priority is deliberately NOT part of the LLM's output contract - it's
inherited from the parent Scenario. The LLM only invents new content
(title, preconditions, steps, expected_result); priority already exists
upstream and re-deriving it here risks disagreeing with the scenario for
no benefit.
"""

from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.models.scenario import Scenario
from backend.models.state import WorkflowState
from backend.models.test_case import TestCase
from backend.services.llm import LLMService, LLMServiceError
from backend.utils.prompts import load_prompt


class TestCaseResponse(BaseModel):
    scenario_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected_result: str = Field(min_length=1)


class TestCaseListResponse(BaseModel):
    test_cases: list[TestCaseResponse] = Field(min_length=1)


def _format_scenarios_block(scenarios: list[Scenario]) -> str:
    return "\n".join(
        f"{i + 1}. {s.scenario_name} (priority: {s.priority.value}): {s.description}"
        for i, s in enumerate(scenarios)
    )


class TestCaseAgent(BaseAgent):
    name = "TestCase Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")
        if not state.generated_scenarios:
            raise ValueError(f"{self.name} requires at least one generated scenario")

        state.add_log(f"{self.name} started")

        prompt = load_prompt(
            "test_case_prompt.txt",
            title=state.requirement.title,
            description=state.requirement.description,
            scenarios=_format_scenarios_block(state.generated_scenarios),
            count=str(len(state.generated_scenarios)),
        )

        batch = self.llm_service.structured_generate(
            user=prompt,
            response_model=TestCaseListResponse,
        )

        expected_numbers = set(range(1, len(state.generated_scenarios) + 1))
        returned_numbers = {item.scenario_number for item in batch.test_cases}
        if returned_numbers != expected_numbers:
            raise LLMServiceError(
                f"{self.name}: LLM returned test cases for scenario numbers {sorted(returned_numbers)}, "
                f"expected exactly {sorted(expected_numbers)}"
            )

        for item in batch.test_cases:
            scenario = state.generated_scenarios[item.scenario_number - 1]
            state.generated_test_cases.append(
                TestCase(
                    scenario_id=scenario.id,
                    title=item.title,
                    preconditions=item.preconditions,
                    steps=item.steps,
                    expected_result=item.expected_result,
                    priority=scenario.priority,
                )
            )

        state.add_log(f"{self.name} generated {len(state.generated_test_cases)} test cases")
        return state