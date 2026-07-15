"""
ReportAgent doesn't generate or judge anything - no LLM, same "doesn't
think" category as HumanApprovalAgent and ExecutionAgent. It reads what
every other agent already produced and summarizes it into one
ExecutionReport, nothing more.

Deliberately tolerant: this agent only guards on state.requirement.
Every other agent requires SOME upstream data to exist before it can do
its job (TestCaseAgent needs scenarios, EvaluationAgent needs test
cases). ReportAgent has the opposite requirement - its whole job is to
accurately reflect whatever happened, including "nothing was generated"
or "everything got rejected". A report showing all zeros is a correct,
useful report; failing to produce one would hide exactly the situation
someone reading a report most needs to see.
"""

from backend.agents.base import BaseAgent
from backend.models.execution_report import ExecutionReport, TestCaseReportEntry
from backend.models.state import WorkflowState
from backend.models.test_case import EvaluationStatus, TestCase, TestCaseStatus


class ReportAgent(BaseAgent):
    name = "Report Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        state.add_log(f"{self.name} started")

        results_by_test_case_id = {r.test_case_id: r for r in state.execution_results}

        approved = sum(1 for tc in state.generated_test_cases if tc.evaluation_status == EvaluationStatus.APPROVED)
        needs_review = sum(1 for tc in state.generated_test_cases if tc.evaluation_status == EvaluationStatus.NEEDS_REVIEW)
        rejected = sum(1 for tc in state.generated_test_cases if tc.evaluation_status == EvaluationStatus.REJECTED)

        executed = [tc for tc in state.generated_test_cases if tc.status != TestCaseStatus.PENDING]
        passed = [tc for tc in executed if tc.status == TestCaseStatus.PASSED]
        failed = [tc for tc in executed if tc.status == TestCaseStatus.FAILED]
        blocked = [tc for tc in executed if tc.status == TestCaseStatus.BLOCKED]

        def _entry(test_case: TestCase) -> TestCaseReportEntry:
            result = results_by_test_case_id.get(test_case.id)
            return TestCaseReportEntry(
                title=test_case.title,
                status=test_case.status.value,
                duration_seconds=result.duration_seconds if result else None,
                reason=result.error_message if result else None,
            )

        # Collect stories
        stories_list = [s.jira_issue_key for s in state.generated_scenarios if s.jira_issue_key]
        # Collect bugs
        bugs_list = [tc.jira_issue_key for tc in state.generated_test_cases if tc.jira_issue_key]
        # Count retests
        retests_count = sum(1 for tc in state.generated_test_cases if tc.status.value in ["retest_pending", "retest_required"])

        report = ExecutionReport(
            requirement_title=state.requirement.title,
            scenario_count=len(state.generated_scenarios),
            test_case_count=len(state.generated_test_cases),
            approved_count=approved,
            needs_review_count=needs_review,
            rejected_count=rejected,
            executed_count=len(executed),
            passed_count=len(passed),
            failed_count=len(failed),
            blocked_count=len(blocked),
            pass_rate=(len(passed) / len(executed)) if executed else 0.0,
            total_execution_seconds=sum(r.duration_seconds for r in state.execution_results),
            failed_tests=[_entry(tc) for tc in failed],
            blocked_tests=[_entry(tc) for tc in blocked],
            jira_stories_synced=stories_list,
            jira_bugs_raised=bugs_list,
            jira_retests_required=retests_count
        )

        state.execution_report = report
        state.add_log(f"{self.name} finished: {report.passed_count}/{report.executed_count} passed ({report.pass_rate:.0%})")
        return state