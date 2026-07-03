"""
The three-node graph, run with a stubbed LLM underneath every agent. The
graph topology runs exactly as it would in production - only the LLM
calls themselves are faked, via build_graph()'s agent injection. No API
key needed, no real network call.

Needs the stub_llm_service fixture from conftest.py, so this runs under
pytest only, not `python -m`.
"""

from backend.agents.evaluation_agent import EvaluationAgent
from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.graph.workflow import build_graph, run_workflow
from backend.models.requirement import Requirement
from backend.models.test_case import EvaluationStatus


def test_graph_runs_all_three_agents(stub_llm_service):
    requirement = Requirement(
        title="Login flow",
        description="User can log in with valid credentials",
    )

    test_graph = build_graph(
        scenario_agent=ScenarioAgent(llm_service=stub_llm_service),
        test_case_agent=TestCaseAgent(llm_service=stub_llm_service),
        evaluation_agent=EvaluationAgent(llm_service=stub_llm_service),
    )
    final_state = run_workflow(requirement, graph_instance=test_graph)

    assert len(final_state.generated_scenarios) == 3
    assert len(final_state.generated_test_cases) == 3
    assert final_state.generated_scenarios[0].scenario_name == "Valid Login"
    assert final_state.generated_test_cases[0].scenario_id == final_state.generated_scenarios[0].id
    assert "Workflow finished" in final_state.logs[-1]

    # The canned evaluation fixture scores everything at 0.9, comfortably
    # above the default 0.75 threshold - all three should be approved.
    assert len(final_state.approved_test_cases()) == 3
    assert all(tc.evaluation_status == EvaluationStatus.APPROVED for tc in final_state.generated_test_cases)

    print("Log trail:")
    for line in final_state.logs:
        print("   ", line)

    print("\nScenarios generated:")
    for s in final_state.generated_scenarios:
        print(f"    - {s.scenario_name} [{s.priority.value}]")

    print("\nTest cases after evaluation:")
    for tc in final_state.generated_test_cases:
        print(f"    - {tc.title} [{tc.priority.value}] confidence={tc.confidence:.2f} status={tc.evaluation_status.value}")