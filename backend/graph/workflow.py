"""
The graph answers exactly one question: who runs next. It never calls an
LLM directly - that's each agent's job through BaseAgent.run().

Today's graph, one node longer than last milestone:
    START -> Scenario Agent -> TestCase Agent -> Evaluation Agent -> END

build_graph() takes optional agent instances instead of hardcoding them at
module level. Needed since ScenarioAgent, TestCaseAgent, and now
EvaluationAgent all call a real LLM: tests build this exact graph with
agents wired to mocked LLMServices, without a real API key. Nothing about
the topology moves - only how the nodes get their agent instances.

Note: graph.invoke() returns a plain dict, not a WorkflowState instance,
even though WorkflowState is the state schema - verified against
langgraph 1.2.7. run_workflow() reconstructs a real WorkflowState so
nothing outside this file needs to know that detail.
"""

from langgraph.graph import END, START, StateGraph

from backend.agents.base import BaseAgent
from backend.agents.evaluation_agent import EvaluationAgent
from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.models.requirement import Requirement
from backend.models.state import WorkflowState


def build_graph(
    scenario_agent: BaseAgent | None = None,
    test_case_agent: BaseAgent | None = None,
    evaluation_agent: BaseAgent | None = None,
):
    scenario_agent = scenario_agent or ScenarioAgent()
    test_case_agent = test_case_agent or TestCaseAgent()
    evaluation_agent = evaluation_agent or EvaluationAgent()

    def _scenario_node(state: WorkflowState) -> WorkflowState:
        return scenario_agent.run(state)

    def _test_case_node(state: WorkflowState) -> WorkflowState:
        return test_case_agent.run(state)

    def _evaluation_node(state: WorkflowState) -> WorkflowState:
        return evaluation_agent.run(state)

    builder = StateGraph(WorkflowState)
    builder.add_node("scenario_agent", _scenario_node)
    builder.add_node("test_case_agent", _test_case_node)
    builder.add_node("evaluation_agent", _evaluation_node)
    builder.add_edge(START, "scenario_agent")
    builder.add_edge("scenario_agent", "test_case_agent")
    builder.add_edge("test_case_agent", "evaluation_agent")
    builder.add_edge("evaluation_agent", END)
    return builder.compile()


# Default real graph - used by run_workflow() below and, later, the API layer.
graph = build_graph()


def run_workflow(requirement: Requirement, graph_instance=None) -> WorkflowState:
    """Entry point used by the terminal test today, and the API layer later.

    graph_instance lets tests pass a graph built with mocked agents.
    Defaults to the real module-level graph otherwise.
    """
    graph_instance = graph_instance or graph

    initial_state = WorkflowState(requirement=requirement)
    initial_state.add_log("Requirement received")

    raw_result = graph_instance.invoke(initial_state)
    final_state = WorkflowState(**raw_result)

    final_state.add_log("Workflow finished")
    return final_state