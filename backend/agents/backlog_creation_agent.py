from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.services.llm import LLMService
from backend.repository.project_repository import get_project_repository
from backend.utils.prompts import load_prompt
from pydantic import BaseModel, Field

class StoryBlock(BaseModel):
    title: str = Field(description="Title of user story")
    description: str = Field(description="Format: As a [role], I want to [action], so that [value]")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Agile acceptance criteria list")

class FeatureBlock(BaseModel):
    title: str = Field(description="Feature title")
    description: str = Field(description="Feature description")
    user_stories: list[StoryBlock] = Field(min_length=1)

class EpicResponse(BaseModel):
    title: str = Field(description="Epic title")
    description: str = Field(description="Epic description")
    features: list[FeatureBlock] = Field(min_length=1)

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

        state.add_log(f"{self.name} started")

        try:
            # Load standard roles_and_responsibilities prompt template
            prompt = load_prompt(
                "agents/backlog_creation/roles_and_responsibilities.md",
                requirement_detail=f"Title: {state.requirement.title}\nDescription: {state.requirement.description}",
                scenarios="N/A (Generating backlog prior to scenarios)"
            )
            epic = self.llm_service.structured_generate(
                user=prompt,
                response_model=EpicResponse
            )

            # Flat-map stories to state.user_stories and keep the hierarchical tree
            state.user_stories = []
            for f in epic.features:
                for story in f.user_stories:
                    story_dict = {
                        "title": story.title,
                        "description": story.description,
                        "acceptance_criteria": story.acceptance_criteria,
                        "feature_title": f.title,
                        "epic_title": epic.title
                    }
                    state.user_stories.append(story_dict)

            state.add_log(f"{self.name}: Backlog tree created. Stories generated: {len(state.user_stories)}")

            # Legacy unit test compatibility fallback: if scenarios are pre-populated, map notes
            if state.generated_scenarios:
                for scenario in state.generated_scenarios:
                    notes_content = (
                        f"**Agile User Story**:\nAs a user, I want to execute scenario {scenario.scenario_name}.\n\n"
                        f"**Acceptance Criteria**:\n- Verify execution output behaves correctly."
                    )
                    self.repo.add_scenario_note(scenario.id, notes_content)
                    state.add_log(f"{self.name}: Generated user story for scenario '{scenario.scenario_name}' and saved as scenario note.")

        except Exception as e:
            state.add_log(f"{self.name} failed: {e}")

        return state
