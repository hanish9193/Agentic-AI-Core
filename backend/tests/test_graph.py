"""
The two-node graph, run with a stubbed LLM underneath ScenarioAgent. The
graph topology and TestCaseAgent run exactly as they would in production -
only the LLM call itself is faked, via build_graph()'s agent injection.
No API key needed, no real network call, and this test won't start
failing the moment an API key expires or a provider rate-limits you.

Needs the stub_llm_service fixture from conftest.py, so - same as
test_foundation.py - this runs under pytest only, not `python -m`.
"""

from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.graph.workflow import build_graph, run_workflow
from backend.models.requirement import Requirement


def test_graph_runs_scenario_then_testcase_agent(stub_llm_service):
    requirement = Requirement(
        title="Login flow",
        description="User can log in with valid credentials",
    )

    test_graph = build_graph(
        scenario_agent=ScenarioAgent(llm_service=stub_llm_service),
        test_case_agent=TestCaseAgent(llm_service=stub_llm_service),
    )
    final_state = run_workflow(requirement, graph_instance=test_graph)

    assert len(final_state.generated_scenarios) == 3
    assert len(final_state.generated_test_cases) == 3
    assert final_state.generated_scenarios[0].scenario_name == "Valid Login"
    assert final_state.generated_test_cases[0].scenario_id == final_state.generated_scenarios[0].id
    assert "Workflow finished" in final_state.logs[-1]

    print("Log trail:")
    for line in final_state.logs:
        print("   ", line)

    print("\nScenarios generated:")
    for s in final_state.generated_scenarios:
        print(f"    - {s.scenario_name} [{s.priority.value}]")

    print("\nTest cases generated:")
    for tc in final_state.generated_test_cases:
        print(f"    - {tc.title} [{tc.priority.value}] status={tc.status.value}")