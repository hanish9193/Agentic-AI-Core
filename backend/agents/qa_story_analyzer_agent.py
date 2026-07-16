from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt
from pydantic import BaseModel, Field

class RiskItem(BaseModel):
    area: str = Field(description="Area of risk or potential failure point")
    risk_level: str = Field(description="high, medium, or low")
    mitigation: str = Field(description="Proposed mitigation strategy")

class TestStrategyDetails(BaseModel):
    approach: str = Field(description="Automated functional, API, performance, or manual strategy details")
    environment: str = Field(description="Target execution environment (e.g. QA, UAT, Staging, Production)")

class TestScopeDetails(BaseModel):
    in_scope: list[str] = Field(default_factory=list, description="Capabilities in scope")
    out_scope: list[str] = Field(default_factory=list, description="Capabilities out of scope")

class TestingContextResponse(BaseModel):
    risk_analysis: list[RiskItem] = Field(default_factory=list)
    test_strategy: TestStrategyDetails
    test_scope: TestScopeDetails
    coverage_suggestions: list[str] = Field(default_factory=list)

class QAStoryAnalyzerAgent(BaseAgent):
    name = "QA Story Analyzer Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def run(self, state: WorkflowState) -> WorkflowState:
        state.add_log(f"{self.name} started")

        # Compile user story text from user_stories list or fall back to requirement description
        story_text = ""
        ac_text = ""
        if state.user_stories:
            story = state.user_stories[0]
            story_text = story.get("description", story.get("title", ""))
            ac_text = "\n".join(story.get("acceptance_criteria", []))
        elif state.requirement:
            story_text = state.requirement.description
            ac_text = "\n".join(state.requirement.acceptance_criteria)
        else:
            state.add_log(f"{self.name}: No story or requirement provided. Bypassing analysis.")
            return state

        try:
            prompt = load_prompt(
                "agents/qa_story_analyzer/roles_and_responsibilities.md",
                user_story=story_text,
                acceptance_criteria=ac_text
            )
            analysis = self.llm_service.structured_generate(
                user=prompt,
                response_model=TestingContextResponse
            )
            state.testing_context = analysis.model_dump()
            state.add_log(f"{self.name}: Analysis complete. Risks identified: {len(analysis.risk_analysis)}")
        except Exception as e:
            state.add_log(f"{self.name}: Story analysis failed, falling back to empty context: {e}")
            state.testing_context = {
                "risk_analysis": [],
                "test_strategy": {"approach": "standard QA", "environment": "QA"},
                "test_scope": {"in_scope": [], "out_scope": []},
                "coverage_suggestions": []
            }

        return state
