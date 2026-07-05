"""
The six-node graph, run with fakes underneath everything that would
otherwise touch a real LLM or a real subprocess. HumanApprovalAgent
needs neither, so build_graph() just uses its real instance by default.

Needs the stub_llm_service and fake_playwright_runner fixtures from
conftest.py, so this runs under pytest only, not `python -m`.
"""

from backend.agents.evaluation_agent import EvaluationAgent
from backend.agents.execution_agent import ExecutionAgent
from backend.agents.playwright_agent import PlaywrightAgent
from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.graph.workflow import build_graph, run_workflow
from backend.models.requirement import Requirement
from backend.models.test_case import TestCaseStatus


def test_graph_runs_all_six_agents(stub_llm_service, fake_playwright_runner):
    requirement = Requirement(
        title="Login flow",
        description="User can log in with valid credentials",
    )

    test_graph = build_graph(
        scenario_agent=ScenarioAgent(llm_service=stub_llm_service),
        test_case_agent=TestCaseAgent(llm_service=stub_llm_service),
        evaluation_agent=EvaluationAgent(llm_service=stub_llm_service),
        # human_approval_agent omitted - no LLM to stub, real instance is fine here
        playwright_agent=PlaywrightAgent(llm_service=stub_llm_service),
        execution_agent=ExecutionAgent(runner=fake_playwright_runner),
    )
    final_state = run_workflow(requirement, graph_instance=test_graph)

    assert len(final_state.generated_scenarios) == 3
    assert len(final_state.generated_test_cases) == 3
    assert final_state.generated_scenarios[0].scenario_name == "Valid Login"
    assert final_state.generated_test_cases[0].scenario_id == final_state.generated_scenarios[0].id
    assert "Workflow finished" in final_state.logs[-1]

    # The canned evaluation fixture scores everything at 0.9, above the
    # 0.75 threshold - all three auto-approved, get scripts, and get run.
    assert len(final_state.approved_test_cases()) == 3
    assert all(tc.playwright_script is not None for tc in final_state.generated_test_cases)
    assert all(tc.status == TestCaseStatus.PASSED for tc in final_state.generated_test_cases)
    assert len(final_state.execution_results) == 3
    assert any("Execution Agent finished: 3/3 passed" in line for line in final_state.logs)

    print("Log trail:")
    for line in final_state.logs:
        print("   ", line)

    print("\nFinal state of the full pipeline:")
    for tc in final_state.generated_test_cases:
        print(f"    - {tc.title} confidence={tc.confidence:.2f} eval={tc.evaluation_status.value} "
              f"has_script={tc.playwright_script is not None} exec_status={tc.status.value}")