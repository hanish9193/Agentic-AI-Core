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

import datetime
from uuid import uuid4
from backend.agents.base import BaseAgent
from backend.models.execution_result import ExecutionResult, ExecutionStatus
from backend.models.state import WorkflowState
from backend.models.test_case import TestCase, TestCaseStatus
from backend.services.playwright_runner import PlaywrightRunner, PlaywrightRunnerError
from backend.models.batch_context import BatchContext, QueueItem
from backend.services.batch_queue_manager import BatchQueueManager

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

        # Compile queue items
        queue = []
        for i, tc in enumerate(runnable):
            required_state = "LOGIN"
            title_lower = tc.title.lower()
            if "search" in title_lower:
                required_state = "SEARCH"
            elif "select" in title_lower or "result" in title_lower:
                required_state = "RESULTS"
            elif "book" in title_lower:
                required_state = "BOOKING"
            elif "confirm" in title_lower:
                required_state = "CONFIRMATION"

            item = QueueItem(
                task_id=f"TASK-{i+1}",
                requirement_id=state.requirement.id,
                testcase_id=tc.id,
                required_state=required_state,
                playwright_script=tc.playwright_script,
                dataset_row=i,
                priority=1,
                estimated_duration=30.0,
                status="queued"
            )
            queue.append(item)

        # Initialize BatchContext
        batch_id = f"BATCH-{datetime.date.today().strftime('%Y%m%d')}-{int(datetime.datetime.now().timestamp()) % 1000:03d}"
        context = BatchContext(
            batch_id=batch_id,
            project_id=uuid4(),
            queue=queue
        )

        # Execute using the queue manager
        qm = BatchQueueManager(runner=self.runner, on_log=self.on_log)
        result_context = qm.run_batch(context)

        # Adapt result_context back to workflow state
        for item in result_context.queue:
            tc = next((t for t in runnable if t.id == item.testcase_id), None)
            if not tc:
                continue

            tc.status = _STATUS_MAP.get(item.status, TestCaseStatus.BLOCKED)

            artifacts = result_context.artifacts.get(item.task_id, {})
            screenshot_path = artifacts["screenshots"][0]["path"] if artifacts.get("screenshots") else None
            video_path = artifacts.get("video")
            trace_path = artifacts.get("trace")

            error_message = item.error_message
            if not error_message and item.status in ["failed", "error"]:
                error_message = "Test execution failed."

            # Extract first trace/video/screenshot path
            res = ExecutionResult(
                test_case_id=tc.id,
                status=ExecutionStatus(item.status) if item.status in ["passed", "failed"] else ExecutionStatus.ERROR,
                duration_seconds=item.duration,
                error_message=error_message,
                screenshot_path=screenshot_path,
                video_path=video_path,
                trace_path=trace_path
            )
            # Attach timeline & console logs to the raw payload of ExecutionResult
            res._raw_payload = {
                "timeline": artifacts.get("timeline", []),
                "logs": artifacts.get("logs", []),
                "console": artifacts.get("console", [])
            }
            state.execution_results.append(res)

        passed = sum(1 for r in state.execution_results[-len(runnable):] if r.status == ExecutionStatus.PASSED)
        state.add_log(f"{self.name} finished: {passed}/{len(runnable)} passed")
        return state