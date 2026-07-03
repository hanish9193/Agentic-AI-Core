"""
Generates test cases via LLM instead of hardcoded data. Same shape as
ScenarioAgent's conversion: graph and BaseAgent interface untouched, only
what's inside run() changed.

TestCaseResponse / TestCaseListResponse are the LLM's output contract.
Unlike ScenarioAgent, this agent has a correlation problem ScenarioAgent
never had: with multiple scenarios going in, each generated test case
needs to map back to the *correct* scenario. Rather than trust the LLM to
preserve list order (not guaranteed), each TestCaseResponse echoes back
scenario_name, and the agent matches on that explicitly.

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
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt


class TestCaseResponse(BaseModel):
    scenario_name: str = Field(min_length=1)
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

        scenarios_by_name = {s.scenario_name: s for s in state.generated_scenarios}

        for item in batch.test_cases:
            matching_scenario = scenarios_by_name.get(item.scenario_name)
            if matching_scenario is None:
                raise ValueError(
                    f"{self.name}: LLM returned a test case for unrecognized scenario "
                    f"'{item.scenario_name}'; expected one of {list(scenarios_by_name)}"
                )

            state.generated_test_cases.append(
                TestCase(
                    scenario_id=matching_scenario.id,
                    title=item.title,
                    preconditions=item.preconditions,
                    steps=item.steps,
                    expected_result=item.expected_result,
                    priority=matching_scenario.priority,
                )
            )

        state.add_log(f"{self.name} generated {len(state.generated_test_cases)} test cases")
        return state