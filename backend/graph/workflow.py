"""
The graph answers exactly one question: who runs next. It never calls an
LLM directly - that's each agent's job through BaseAgent.run().

Today's graph is intentionally the smallest possible one:
    START -> Scenario Agent -> END

Note: graph.invoke() returns a plain dict, not a WorkflowState instance,
even though WorkflowState is the state schema - verified against
langgraph 1.2.7. run_workflow() reconstructs a real WorkflowState so
nothing outside this file needs to know that detail.
"""

from langgraph.graph import END, START, StateGraph

from backend.agents.scenario_agent import ScenarioAgent
from backend.models.requirement import Requirement
from backend.models.state import WorkflowState

_scenario_agent = ScenarioAgent()


def _scenario_node(state: WorkflowState) -> WorkflowState:
    return _scenario_agent.run(state)


def build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("scenario_agent", _scenario_node)
    builder.add_edge(START, "scenario_agent")
    builder.add_edge("scenario_agent", END)
    return builder.compile()


graph = build_graph()


def run_workflow(requirement: Requirement) -> WorkflowState:
    """Entry point used by the terminal test today, and the API layer later."""
    initial_state = WorkflowState(requirement=requirement)
    initial_state.add_log("Requirement received")

    raw_result = graph.invoke(initial_state)
    final_state = WorkflowState(**raw_result)

    final_state.add_log("Workflow finished")
    return final_state