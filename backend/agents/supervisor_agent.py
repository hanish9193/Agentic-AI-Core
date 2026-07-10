import logging
from langchain_core.runnables import RunnableConfig
from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.models.operation import WorkflowOperation
from backend.models.test_case import EvaluationStatus

logger = logging.getLogger(__name__)

OPERATION_ROUTING_MAP = {
    WorkflowOperation.GENERATE_SCENARIOS: "scenario_agent",
    WorkflowOperation.APPROVE_SCENARIO: "human_approval_agent_1",
    WorkflowOperation.GENERATE_TESTCASES: "test_case_agent",
    WorkflowOperation.APPROVE_TESTCASE: "human_approval_agent_2",
    WorkflowOperation.GENERATE_PLAYWRIGHT: "playwright_agent",
    WorkflowOperation.EXECUTE: "execution_agent",
    WorkflowOperation.GENERATE_REPORT: "report_agent",
}

class SupervisorAgent(BaseAgent):
    name = "Supervisor Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        state.add_log(f"{self.name} started")
        return state

    def route_start(self, state: WorkflowState, config: RunnableConfig | None = None) -> str:
        """Determines the starting node based on config operation and validates prerequisites."""
        configurable = config.get("configurable", {}) if config else {}
        op = configurable.get("operation")

        # Linear end-to-end fallback for testing/empty configs
        if not op:
            state.add_log(f"{self.name}: No operation configured. Starting full pipeline at scenario_agent.")
            return "scenario_agent"

        # Validate prerequisite gates
        if op == WorkflowOperation.GENERATE_SCENARIOS:
            if not state.requirement:
                raise ValueError("Requirement must be set for scenario generation.")
            return "scenario_agent"

        elif op == WorkflowOperation.GENERATE_TESTCASES:
            if not state.requirement:
                raise ValueError("Requirement must be set for test case generation.")
            # Prerequisite: must have approved scenarios
            scenarios = state.generated_scenarios
            approved_scenarios = [s for s in scenarios if s.approved]
            if not approved_scenarios:
                state.add_log(f"{self.name}: Rejecting test case generation. Prerequisite failed: No approved scenarios.")
                raise ValueError("Test case generation rejected: No approved scenarios exist.")
            return "test_case_agent"

        elif op == WorkflowOperation.GENERATE_PLAYWRIGHT:
            if not state.requirement:
                raise ValueError("Requirement must be set for Playwright script generation.")
            # Prerequisite: must have approved test cases
            approved_tcs = state.approved_test_cases()
            if not approved_tcs:
                state.add_log(f"{self.name}: Rejecting script generation. Prerequisite failed: TestCase is not approved.")
                raise ValueError("Playwright script generation rejected: TestCase is not approved.")
            return "playwright_agent"

        elif op == WorkflowOperation.EXECUTE:
            if not state.requirement:
                raise ValueError("Requirement must be set for execution.")
            # Prerequisite: must have approved test cases with scripts
            runnable = [tc for tc in state.approved_test_cases() if tc.playwright_script]
            if not runnable:
                state.add_log(f"{self.name}: Rejecting execution. Prerequisite failed: No approved test cases with scripts.")
                raise ValueError("Execution rejected: No approved test cases with Playwright scripts found.")
            return "execution_agent"

        target = OPERATION_ROUTING_MAP.get(op)
        if not target:
            state.add_log(f"{self.name}: Unknown operation '{op}'. Transitioning to END.")
            return "end"

        state.add_log(f"{self.name}: Prerequisite checks passed. Routing to '{target}'.")
        return target

    def route_after_human_approval_1(self, state: WorkflowState, config: RunnableConfig | None = None) -> str:
        """Routes after scenario human approval node."""
        configurable = config.get("configurable", {}) if config else {}
        op = configurable.get("operation")
        if op == WorkflowOperation.GENERATE_SCENARIOS:
            return "end"
        return "test_case_agent"

    def route_after_human_approval_2(self, state: WorkflowState, config: RunnableConfig | None = None) -> str:
        """Routes after test case human approval node."""
        configurable = config.get("configurable", {}) if config else {}
        op = configurable.get("operation")
        if op == WorkflowOperation.GENERATE_TESTCASES:
            return "end"
        return "playwright_agent"

    def route_after_playwright(self, state: WorkflowState, config: RunnableConfig | None = None) -> str:
        """Routes after Playwright script generation."""
        configurable = config.get("configurable", {}) if config else {}
        op = configurable.get("operation")
        if op == WorkflowOperation.GENERATE_PLAYWRIGHT:
            return "end"
        return "execution_agent"
