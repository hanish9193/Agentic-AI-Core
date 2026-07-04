"""
The five-node graph, run with a stubbed LLM underneath the four agents
that need one. HumanApprovalAgent needs no stub - it's fully
deterministic, so build_graph() just uses its real instance by default,
same as it would in production.

Needs the stub_llm_service fixture from conftest.py, so this runs under
pytest only, not `python -m`.
"""

from backend.agents.evaluation_agent import EvaluationAgent
from backend.agents.playwright_agent import PlaywrightAgent
from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.graph.workflow import build_graph, run_workflow
from backend.models.requirement import Requirement


def test_graph_runs_all_five_agents(stub_llm_service):
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
    )
    final_state = run_workflow(requirement, graph_instance=test_graph)

    assert len(final_state.generated_scenarios) == 3
    assert len(final_state.generated_test_cases) == 3
    assert final_state.generated_scenarios[0].scenario_name == "Valid Login"
    assert final_state.generated_test_cases[0].scenario_id == final_state.generated_scenarios[0].id
    assert "Workflow finished" in final_state.logs[-1]

    # The canned evaluation fixture scores everything at 0.9, above the
    # 0.75 threshold - all three auto-approved, nothing for a human to do,
    # and all three should have a Playwright script generated.
    assert len(final_state.approved_test_cases()) == 3
    assert any("Human Approval Agent" in line for line in final_state.logs)
    assert any("no pending human decisions" in line for line in final_state.logs)
    assert all(tc.playwright_script is not None for tc in final_state.generated_test_cases)
    assert any("Playwright Agent finished: generated 3" in line for line in final_state.logs)

    print("Log trail:")
    for line in final_state.logs:
        print("   ", line)

    print("\nTest cases after the full pipeline:")
    for tc in final_state.generated_test_cases:
        print(f"    - {tc.title} [{tc.priority.value}] confidence={tc.confidence:.2f} "
              f"status={tc.evaluation_status.value} has_script={tc.playwright_script is not None}")