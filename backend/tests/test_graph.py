"""
Today's milestone, run directly:
    Requirement -> LangGraph -> Scenario Agent -> Updated State

No API, no UI. Just the graph, watched end to end.
"""

from backend.graph.workflow import run_workflow
from backend.models.requirement import Requirement


def test_graph_runs_scenario_agent():
    requirement = Requirement(
        title="Login flow",
        description="User can log in with valid credentials",
    )

    final_state = run_workflow(requirement)

    assert len(final_state.generated_scenarios) == 3
    assert final_state.generated_scenarios[0].scenario_name == "Valid Login"
    assert "Workflow finished" in final_state.logs[-1]

    print("Log trail:")
    for line in final_state.logs:
        print("   ", line)

    print("\nScenarios generated:")
    for s in final_state.generated_scenarios:
        print(f"    - {s.scenario_name} [{s.priority.value}]")


if __name__ == "__main__":
    test_graph_runs_scenario_agent()
    print("\nFirst LangGraph workflow: confirmed working.")