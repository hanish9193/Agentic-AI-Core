"""
HumanApprovalAgent doesn't think - no LLM, no prompt, no LLMService. It
validates and finalizes decisions that were already recorded on state via
WorkflowState.request_test_case_approval(), the same way select_scenario()
records a scenario pick before any agent processes it.

Business rule this agent enforces: a rejected test case (duplicate, or
below the relevance floor) can't be approved through this path. That's a
deliberate scope limit, not an oversight - if EvaluationAgent's rejection
was wrong, that's a different problem (a bad evaluation) than "this
plausible-but-uncertain item needs a human's judgment call", which is
the only thing this agent is meant to resolve.

Note on today's single-invoke graph: since a human can't act on
EvaluationAgent's output before it exists, pending_approval_ids is
normally empty on a fresh run_workflow() call - that's expected, not a
bug. Real human-in-the-loop needs the graph to pause and resume (a
LangGraph interrupt, plus somewhere to persist state in between, which
backend/database/ doesn't do yet). This agent's logic is correct and
tested regardless of when or how it gets invoked.
"""

from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.models.test_case import EvaluationStatus


class HumanApprovalAgent(BaseAgent):
    name = "Human Approval Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        state.add_log(f"{self.name} started")

        if not state.pending_approval_ids:
            state.add_log(f"{self.name}: no pending human decisions to process")
            return state

        test_cases_by_id = {tc.id: tc for tc in state.generated_test_cases}
        newly_approved = 0

        for test_case_id in state.pending_approval_ids:
            test_case = test_cases_by_id.get(test_case_id)
            if test_case is None:
                raise ValueError(
                    f"{self.name}: pending approval for unknown test case {test_case_id} - "
                    f"this should have been caught by request_test_case_approval()"
                )

            if test_case.evaluation_status == EvaluationStatus.REJECTED:
                raise ValueError(
                    f"{self.name}: cannot approve '{test_case.title}' - it was rejected "
                    f"(duplicate or below the relevance floor). This agent only resolves "
                    f"items needing review, it doesn't override an evaluation rejection."
                )

            if test_case_id not in state.human_approved_test_case_ids:
                state.human_approved_test_case_ids.append(test_case_id)
                newly_approved += 1

        state.add_log(
            f"{self.name} finished: {newly_approved} test case(s) human-approved, "
            f"{len(state.approved_test_cases())} total approved for automation"
        )
        return state