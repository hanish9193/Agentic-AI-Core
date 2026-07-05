"""
Manual, one-off check against REAL infrastructure - a real LLM AND, as of
this version, a real Playwright execution. Not part of the automated
suite - pytest won't collect this (doesn't match test_*.py), deliberately:
this costs real time and money and needs things installed that shouldn't
be required just to run the test suite.

NEW PREREQUISITE as of ExecutionAgent: unlike everything before it, this
step needs Node.js, npm, @playwright/test installed in this project, and
an actual browser downloaded (npx playwright install chromium). None of
that was needed for the LLM-only agents. If you haven't done this yet:

    npm init -y                              (if backend/playwright/ has no package.json)
    npm install --save-dev @playwright/test  (run inside backend/playwright/)
    npx playwright install chromium

Requires LLM_API_KEY (and, for Ollama, LLM_API_BASE) in .env set for
whatever LLM_PROVIDER / LLM_MODEL are configured to.

Several real LLM calls happen now: Scenario Agent, TestCase Agent,
Evaluation Agent, then one Playwright-generation call PER auto-approved
test case, then ExecutionAgent actually runs each generated script in a
real browser. On local Ollama this can easily take 5-15 minutes total.
That's expected, not a hang.

HumanApprovalAgent needs no LLM, but it also can't do anything useful on
a fresh single-pass run - a human can't act on confidence scores that
don't exist yet when the graph starts. So after the normal run, this
script checks for any NEEDS_REVIEW test case and, if one exists,
simulates a human approving it as a SEPARATE second step, then generates
AND executes a script for it too - completing the same chain the graph
would have run, on the one item a human had to weigh in on. This is
clearly a simulation, not the real interactive flow (which needs
persistence and a pause/resume graph, neither built yet).

Run with:
    python -m backend.live_check
"""

from backend.agents.execution_agent import ExecutionAgent
from backend.agents.human_approval_agent import HumanApprovalAgent
from backend.agents.playwright_agent import PlaywrightAgent
from backend.graph.workflow import run_workflow
from backend.models.requirement import Requirement
from backend.models.test_case import EvaluationStatus
from backend.services.llm import LLMServiceError
from backend.services.playwright_runner import PlaywrightRunnerError

# Deliberately NOT login-related. The old dummy data used "Valid Login" /
# "Invalid Login" / "Empty Password" - if this requirement were about
# login too, a real LLM producing similar-sounding names wouldn't prove
# anything. A clearly different domain makes it obvious the scenarios
# below are genuinely generated, not leftover dummy data.
_REQUIREMENT = Requirement(
    title="Profile picture upload size limit",
    description=(
        "Users can upload a profile picture up to 5MB in size, in JPG or "
        "PNG format only. Uploads exceeding the limit or in an unsupported "
        "format must be rejected with a clear error message, and the "
        "previous picture must remain unchanged if the upload fails."
    ),
)


def _print_test_case_block(tc, final_state) -> None:
    print(f"    - {tc.title} [{tc.priority.value}]")
    print(f"        preconditions: {tc.preconditions}")
    print(f"        steps: {tc.steps}")
    print(f"        expected: {tc.expected_result}")
    print(f"        confidence: {tc.confidence:.2f}  eval_status: {tc.evaluation_status.value}")
    print(f"        reason: {tc.evaluation_reason}")
    if tc.playwright_script:
        print(f"        playwright script:")
        for line in tc.playwright_script.splitlines():
            print(f"            {line}")
    else:
        print(f"        playwright script: (none - not approved)")

    execution = next((r for r in final_state.execution_results if r.test_case_id == tc.id), None)
    if execution:
        print(f"        EXECUTION RESULT: {execution.status.value}  ({execution.duration_seconds:.2f}s)")
        if execution.error_message:
            print(f"            error: {execution.error_message}")
        if execution.trace_path:
            print(f"            trace: {execution.trace_path}")
    else:
        print(f"        EXECUTION RESULT: (not executed)")


def main():
    print(f"Sending requirement to the real LLM: '{_REQUIREMENT.title}'\n")

    try:
        final_state = run_workflow(_REQUIREMENT)
    except LLMServiceError as exc:
        print("Live LLM call failed. Usual causes, in order of likelihood:")
        print("  1. LLM_API_KEY in .env is missing, empty, or invalid")
        print("  2. The account behind that key has no billing/quota set up")
        print("  3. LLM_PROVIDER / LLM_MODEL in .env don't match a real, available model")
        print(f"\nUnderlying error: {exc}")
        return
    except PlaywrightRunnerError as exc:
        print("Playwright execution failed - this is the NEW prerequisite this round:")
        print("  1. Node.js/npm not installed, or")
        print("  2. @playwright/test not installed in backend/playwright/, or")
        print("  3. No browser downloaded (npx playwright install chromium)")
        print(f"\nUnderlying error: {exc}")
        return

    print("Log trail:")
    for line in final_state.logs:
        print("   ", line)

    print("\nScenarios generated by the LLM:")
    for s in final_state.generated_scenarios:
        print(f"    - {s.scenario_name} [{s.priority.value}]: {s.description}")

    print("\nTest cases after the full pipeline:")
    for tc in final_state.generated_test_cases:
        _print_test_case_block(tc, final_state)

    print(f"\n{len(final_state.approved_test_cases())} of {len(final_state.generated_test_cases)} test cases approved.")
    passed = sum(1 for r in final_state.execution_results if r.status.value == "passed")
    print(f"{passed} of {len(final_state.execution_results)} executed test cases actually passed.")

    print(
        "\nA generated script 'looking right' and a script that actually passes when run are "
        "different claims - if any executed here failed or errored, read the error_message "
        "above. That's not this pipeline malfunctioning; it's the pipeline doing exactly what "
        "ExecutionAgent exists for: catching bugs in AI-generated code before a human would have to."
    )

    needs_review = [tc for tc in final_state.generated_test_cases if tc.evaluation_status == EvaluationStatus.NEEDS_REVIEW]
    print("\n--- Human approval simulation (a separate step, not part of the graph above) ---")
    if not needs_review:
        print(
            "Nothing landed in NEEDS_REVIEW this run - every test case was either "
            "confidently approved or rejected outright. That's fine; the mechanism "
            "itself is verified regardless by the dedicated test files."
        )
        return

    candidate = needs_review[0]
    print(f"Simulating a human approving: '{candidate.title}' (confidence {candidate.confidence:.2f})")
    print(f"  approved_test_cases() before: {[tc.title for tc in final_state.approved_test_cases()]}")

    final_state.request_test_case_approval(candidate.id)
    final_state = HumanApprovalAgent().run(final_state)
    print(f"  approved_test_cases() after:  {[tc.title for tc in final_state.approved_test_cases()]}")

    print("  Generating a Playwright script for the newly-approved test case...")
    final_state = PlaywrightAgent().run(final_state)

    print("  Executing that newly-generated script...")
    try:
        final_state = ExecutionAgent().run(final_state)
        execution = next((r for r in final_state.execution_results if r.test_case_id == candidate.id), None)
        print(f"  result: {execution.status.value if execution else 'not found'}")
    except PlaywrightRunnerError as exc:
        print(f"  Playwright execution unavailable: {exc}")


if __name__ == "__main__":
    main()