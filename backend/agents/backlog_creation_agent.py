from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.services.llm import LLMService
from backend.repository.project_repository import get_project_repository
from pydantic import BaseModel, Field

class UserStoryResponse(BaseModel):
    user_story: str = Field(description="Format: As a [user role], I want to [action], so that [business value].")
    acceptance_criteria: list[str] = Field(description="List of acceptance criteria for this user story.")

class BacklogCreationAgent(BaseAgent):
    name = "Backlog Creation Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()
        self.repo = get_project_repository()

    def run(self, state: WorkflowState) -> WorkflowState:
        if not state.requirement:
            raise ValueError(f"{self.name} requires state.requirement to be set")
        if not state.generated_scenarios:
            state.add_log(f"{self.name}: No generated scenarios found to build backlog items.")
            return state

        state.add_log(f"{self.name} started")

        for scenario in state.generated_scenarios:
            prompt = (
                "You are an expert Agile Product Owner. Generate a structured Agile User Story "
                "and corresponding acceptance criteria for the following scenario under the given requirement.\n\n"
                f"Requirement Title: {state.requirement.title}\n"
                f"Requirement Description: {state.requirement.description}\n\n"
                f"Scenario Name: {scenario.scenario_name}\n"
                f"Scenario Description: {scenario.description}\n"
            )
            try:
                story = self.llm_service.structured_generate(
                    user=prompt,
                    response_model=UserStoryResponse
                )

                # Format the backlog item
                notes_content = (
                    f"**Agile User Story**:\n{story.user_story}\n\n"
                    f"**Acceptance Criteria**:\n" + 
                    "\n".join(f"- {ac}" for ac in story.acceptance_criteria)
                )

                # Save as scenario note in the repository to keep models clean
                self.repo.add_scenario_note(scenario.id, notes_content)
                state.add_log(f"{self.name}: Generated user story for scenario '{scenario.scenario_name}' and saved as scenario note.")
            except Exception as e:
                state.add_log(f"{self.name}: Failed to generate user story for scenario '{scenario.scenario_name}': {e}")

        state.add_log(f"{self.name} finished: Generated {len(state.generated_scenarios)} backlog items.")
        return state
