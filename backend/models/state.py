"""
Workflow state.

This is the object that flows through every node in the LangGraph. Each
agent reads what it needs and writes only its own slice of this — the
Scenario Agent appends to `generated_scenarios`, it does not touch
`requirement`, and so on.

Selection is tracked as a list of ids, not by flipping `Scenario.approved`
in place. That keeps "what's selected" answerable by looking at State
alone, without scanning every scenario object for a mutated flag.

Deliberately minimal for now — no playwright_script. That gets added as
a field when PlaywrightAgent actually exists, not before.
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from backend.models.requirement import Requirement
from backend.models.scenario import Scenario
from backend.models.test_case import EvaluationStatus, TestCase


class WorkflowState(BaseModel):
    requirement: Requirement | None = None
    generated_scenarios: list[Scenario] = Field(default_factory=list)
    selected_scenario_ids: list[UUID] = Field(default_factory=list)
    generated_test_cases: list[TestCase] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)

    def add_log(self, message: str) -> None:
        self.logs.append(f"[{datetime.now(timezone.utc).isoformat()}] {message}")

    def select_scenario(self, scenario_id: UUID) -> None:
        known_ids = {s.id for s in self.generated_scenarios}
        if scenario_id not in known_ids:
            raise ValueError(f"Scenario {scenario_id} is not in generated_scenarios")
        if scenario_id not in self.selected_scenario_ids:
            self.selected_scenario_ids.append(scenario_id)

    def selected_scenarios(self) -> list[Scenario]:
        return [s for s in self.generated_scenarios if s.id in self.selected_scenario_ids]

    def approved_test_cases(self) -> list[TestCase]:
        """Test cases EvaluationAgent approved, ranked by confidence
        descending. This is a computed view, not a stored reordering -
        generated_test_cases keeps its original generation order so the
        raw record stays intact for auditing."""
        approved = [tc for tc in self.generated_test_cases if tc.evaluation_status == EvaluationStatus.APPROVED]
        return sorted(approved, key=lambda tc: tc.confidence, reverse=True)