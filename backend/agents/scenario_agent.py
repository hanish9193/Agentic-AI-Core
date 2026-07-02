"""
Temporary, hardcoded agent - no LLM call yet. Its only job right now is to
prove Requirement -> Agent -> State -> Graph actually works before any AI
is introduced.

Confidence is deliberately left at the Scenario model's default (0.0):
scoring scenarios is the Evaluation Agent's job, not this one's. 0.0 reads
as "not yet scored" rather than "confidently bad", which matters if any
future gate checks confidence before Evaluation has run - the safe
default is to look unscored, not falsely confident.
"""

from backend.agents.base import BaseAgent
from backend.models.common import Priority
from backend.models.scenario import Scenario
from backend.models.state import WorkflowState

_DUMMY_SCENARIOS = (
    ("Valid Login", "User logs in with correct username and password", Priority.HIGH),
    ("Invalid Login", "User attempts login with an incorrect password", Priority.MEDIUM),
    ("Empty Password", "User submits the login form with an empty password field", Priority.LOW),
)

class ScenarioAgent(BaseAgent):
    name = "Scenario Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        state.add_log(f"{self.name} started")

        for scenario_name, description, priority in _DUMMY_SCENARIOS:
            state.generated_scenarios.append(
                Scenario(
                    requirement_id=state.requirement.id,
                    scenario_name=scenario_name,
                    description=description,
                    priority=priority,
                )
            )

        state.add_log(f"{self.name} generated {len(_DUMMY_SCENARIOS)} scenarios")
        return state