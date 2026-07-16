from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt
from pydantic import BaseModel, Field

class OrchestrationResponse(BaseModel):
    test_case_title: str
    execution_type: str = Field(description="Must be exactly one of: UI Automation, API Automation, Manual Testing")
    reason: str

class QAAutomationOrchestratorAgent(BaseAgent):
    name = "QA Automation Orchestrator Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def run(self, state: WorkflowState) -> WorkflowState:
        state.add_log(f"{self.name} started")

        if not state.generated_test_cases:
            state.add_log(f"{self.name}: No generated test cases to orchestrate.")
            return state

        for tc in state.generated_test_cases:
            # Skip if execution_type is already explicitly configured
            if tc.execution_type and tc.execution_type != "UI Automation":
                continue

            try:
                prompt = load_prompt(
                    "agents/automation_orchestrator/roles_and_responsibilities.md",
                    title=tc.title,
                    steps="\n".join(f"- {step}" for step in tc.steps),
                    expected_result=tc.expected_result
                )
                res = self.llm_service.structured_generate(
                    user=prompt,
                    response_model=OrchestrationResponse
                )
                tc.execution_type = res.execution_type
                state.add_log(f"{self.name}: Routed test case '{tc.title}' to '{tc.execution_type}' ({res.reason})")
            except Exception as e:
                state.add_log(f"{self.name}: Failed to orchestrate test case '{tc.title}': {e}")
                tc.execution_type = "UI Automation"

        return state
