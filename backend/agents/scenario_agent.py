"""
Generates scenarios via LLM instead of hardcoded data. The graph and
BaseAgent interface are untouched - only what's inside run() changed.

_GeneratedScenario / _GeneratedScenarioBatch are the LLM's output contract,
deliberately separate from the Scenario domain model. The LLM should only
ever produce content (name, description, priority) - it never gets to
invent system-owned fields like id, requirement_id, confidence, or
generated_at. This agent is what turns "content the LLM made up" into
"a real Scenario object", by supplying the system-owned fields itself.
"""

from pydantic import BaseModel, Field, field_validator

from backend.agents.base import BaseAgent
from backend.config.settings import get_settings
from backend.models.common import Priority
from backend.models.scenario import Scenario
from backend.models.state import WorkflowState
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt


class _GeneratedScenario(BaseModel):
    scenario_name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    priority: Priority = Priority.MEDIUM

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_case(cls, value):
        # Models are inconsistent about "high" vs "High" vs "HIGH" - the
        # content is what matters, not whether the model followed the
        # exact casing from the prompt.
        return value.lower() if isinstance(value, str) else value


class _GeneratedScenarioBatch(BaseModel):
    scenarios: list[_GeneratedScenario] = Field(min_length=1)


class ScenarioAgent(BaseAgent):
    name = "Scenario Agent"

    def __init__(self, llm_service: LLMService | None = None, scenario_count: int | None = None):
        self.llm_service = llm_service or LLMService()
        self.scenario_count = scenario_count or get_settings().generation.scenario_count

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        state.add_log(f"{self.name} started")

        prompt = load_prompt(
            "scenario_prompt.txt",
            title=state.requirement.title,
            description=state.requirement.description,
            count=str(self.scenario_count),
        )

        batch = self.llm_service.structured_generate(
            user=prompt,
            response_model=_GeneratedScenarioBatch,
        )

        for item in batch.scenarios:
            state.generated_scenarios.append(
                Scenario(
                    requirement_id=state.requirement.id,
                    scenario_name=item.scenario_name,
                    description=item.description,
                    priority=item.priority,
                )
            )

        state.add_log(f"{self.name} generated {len(batch.scenarios)} scenarios")
        return state