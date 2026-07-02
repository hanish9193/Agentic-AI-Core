"""
Temporary, hardcoded agent - same spirit as ScenarioAgent. One test case
per scenario, no AI yet.

Reads state.generated_scenarios, not state.selected_scenarios(). That's
deliberate for now: no Human Approval step exists in the graph yet, so
selected_scenario_ids is always empty here - reading selected_scenarios()
would silently produce zero test cases instead of one per scenario. Switch
this to selected_scenarios() when the approval node is added, not before.
"""

from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.models.test_case import TestCase


class TestCaseAgent(BaseAgent):
    name = "TestCase Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        if not state.generated_scenarios:
            raise ValueError(f"{self.name} requires at least one generated scenario")

        state.add_log(f"{self.name} started")

        for scenario in state.generated_scenarios:
            state.generated_test_cases.append(
                TestCase(
                    scenario_id=scenario.id,
                    title=f"Verify: {scenario.scenario_name}",
                    preconditions=["Application is running", "Login page is accessible"],
                    steps=[
                        "Navigate to the login page",
                        f"Execute scenario: {scenario.description}",
                        "Observe the resulting behaviour",
                    ],
                    expected_result=f"System behaves correctly for '{scenario.scenario_name}'",
                    priority=scenario.priority,
                )
            )

        state.add_log(f"{self.name} generated {len(state.generated_test_cases)} test cases")
        return state