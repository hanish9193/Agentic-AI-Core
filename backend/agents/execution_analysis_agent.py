from pydantic import BaseModel, Field
from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.models.execution_result import ExecutionStatus
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt


class _ExecutionAnalysisResponse(BaseModel):
    failure_category: str = Field(description="One of: Product Bug, Test Environment Issue, Flaky Test / Automation Issue")
    root_cause_summary: str = Field(description="Summary of the root cause of this failure")
    trace_analysis: str = Field(description="Detailed analysis of trace log errors")
    screenshot_findings: str = Field(description="Findings from checking the screenshot")
    suggest_retry: bool = Field(description="True if test should be retried, False otherwise")
    retest_pending_candidate: bool = Field(description="True if it represents a bug candidate")


class ExecutionAnalysisAgent(BaseAgent):
    name = "Execution Analysis Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def run(self, state: WorkflowState) -> WorkflowState:
        if not state.execution_results:
            state.add_log(f"{self.name}: no execution results found to analyze.")
            return state

        result = state.execution_results[-1]
        
        # If execution succeeded, skip failure analysis
        if result.status == ExecutionStatus.PASSED:
            result.failure_category = "None"
            result.root_cause_summary = "Execution passed successfully."
            result.trace_analysis = "N/A"
            result.screenshot_findings = "N/A"
            result.suggest_retry = False
            result.retest_pending_candidate = False
            state.add_log(f"{self.name}: skipped analysis as execution passed.")
            return state

        state.add_log(f"{self.name} started analysis for execution {result.id}")

        # Find the test case in state or construct dummy placeholder
        tc = next((t for t in state.generated_test_cases if t.id == result.test_case_id), None)
        tc_title = tc.title if tc else "Unknown Test Case"
        tc_steps = "\n".join(f"- {s}" for s in tc.steps) if tc else "N/A"
        tc_expected = tc.expected_result if tc else "N/A"

        failure_msg = result.error_message or "Unknown failure"
        screenshot_desc = "Screenshot captured during failure" if result.screenshot_path else "No screenshot captured"

        prompt = load_prompt(
            "execution_analysis_prompt.txt",
            steps=tc_steps,
            expected_result=tc_expected,
            logs=failure_msg,
            screenshot_desc=screenshot_desc
        )

        try:
            analysis = self.llm_service.structured_generate(
                user=prompt,
                response_model=_ExecutionAnalysisResponse
            )

            result.failure_category = analysis.failure_category
            result.root_cause_summary = analysis.root_cause_summary
            result.trace_analysis = analysis.trace_analysis
            result.screenshot_findings = analysis.screenshot_findings
            result.suggest_retry = analysis.suggest_retry
            result.retest_pending_candidate = analysis.retest_pending_candidate

            state.add_log(
                f"{self.name} triaged failure: Category={analysis.failure_category}, "
                f"Root Cause={analysis.root_cause_summary}"
            )
        except Exception as exc:
            state.add_log(f"{self.name} analysis failed: {exc}")
            # Populate fallback defaults
            result.failure_category = "Test Environment Issue"
            result.root_cause_summary = f"Analysis agent failed: {exc}. Execution error: {failure_msg}"
            result.trace_analysis = failure_msg
            result.screenshot_findings = "Unknown"
            result.suggest_retry = True
            result.retest_pending_candidate = False

        return state
