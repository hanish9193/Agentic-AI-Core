"""
ExecutionAgent doesn't generate or judge anything - no LLM, no prompt,
same "doesn't think" category as HumanApprovalAgent. It calls
PlaywrightRunner (never subprocess/npx directly) for every approved test
case that has a generated script, and records what actually happened.

This is the first agent to write TestCase.status - that field has been
sitting at its PENDING default since the very first model was written,
specifically reserved for this moment ("status moves to PASSED/FAILED/
BLOCKED once ExecutionAgent actually runs it" - see test_case.py).

Only test cases with BOTH approval and a generated script get run.
Approved-but-no-script shouldn't happen in the normal pipeline order
(PlaywrightAgent runs before this), but it's not an error here - it
just means nothing to execute for that one, not a broken state.

_execute() catches PlaywrightRunnerError per test case rather than
letting it propagate out of the loop. Without this, one bad test case
(e.g. npx unavailable, discovered mid-batch) would lose the results for
every other test case that hadn't run yet - the batch should keep going
and report what happened to each one individually.
"""

from backend.agents.base import BaseAgent
from backend.models.execution_result import ExecutionResult, ExecutionStatus
from backend.models.state import WorkflowState
from backend.models.test_case import TestCase, TestCaseStatus
from backend.services.playwright_runner import PlaywrightRunner, PlaywrightRunnerError

_STATUS_MAP = {
    "passed": TestCaseStatus.PASSED,
    "failed": TestCaseStatus.FAILED,
    "skipped": TestCaseStatus.BLOCKED,
    "error": TestCaseStatus.BLOCKED,
}


class ExecutionAgent(BaseAgent):
    name = "Execution Agent"

    def __init__(self, runner: PlaywrightRunner | None = None, on_log = None):
        self.runner = runner or PlaywrightRunner()
        self.on_log = on_log

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        runnable = [tc for tc in state.approved_test_cases() if tc.playwright_script]
        if not runnable:
            state.add_log(f"{self.name}: no approved test cases with a generated script to execute")
            return state

        state.add_log(f"{self.name} started")

        for test_case in runnable:
            state.execution_results.append(self._execute(test_case))

        passed = sum(1 for r in state.execution_results[-len(runnable):] if r.status == ExecutionStatus.PASSED)
        state.add_log(f"{self.name} finished: {passed}/{len(runnable)} passed")
        return state

    def _execute(self, test_case: TestCase) -> ExecutionResult:
        try:
            try:
                raw = self.runner.run(test_case.playwright_script, run_id=str(test_case.id), on_log=self.on_log)
            except TypeError as exc:
                if "unexpected keyword argument 'on_log'" in str(exc) or "got an unexpected keyword argument" in str(exc):
                    raw = self.runner.run(test_case.playwright_script, run_id=str(test_case.id))
                else:
                    raise
        except PlaywrightRunnerError as exc:
            test_case.status = TestCaseStatus.BLOCKED
            return ExecutionResult(test_case_id=test_case.id, status=ExecutionStatus.ERROR, error_message=str(exc))

        test_case.status = _STATUS_MAP.get(raw.status, TestCaseStatus.BLOCKED)

        return ExecutionResult(
            test_case_id=test_case.id,
            status=ExecutionStatus(raw.status),
            duration_seconds=raw.duration_seconds,
            error_message=raw.error_message,
            screenshot_path=raw.screenshot_path,
            video_path=raw.video_path,
            trace_path=raw.trace_path,
        )