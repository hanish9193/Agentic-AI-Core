"""
The graph answers exactly one question: who runs next. It never calls an
LLM directly - that's each agent's job through BaseAgent.run().

Today's graph, the complete pipeline per the original roadmap:
    START -> SupervisorAgent -> ScenarioAgent -> HumanApprovalAgent_1 -> TestCaseAgent -> EvaluationAgent -> HumanApprovalAgent_2 -> PlaywrightAgent -> ExecutionAgent -> ReportAgent -> END

build_graph() takes optional agent instances instead of hardcoding them
at module level, needed since these agents call either a real LLM or a
real subprocess (Playwright CLI): tests build this exact graph with
agents wired to fakes, without a real API key or Node.js installed.
"""

from langgraph.graph import END, START, StateGraph

from backend.agents.base import BaseAgent
from backend.agents.supervisor_agent import SupervisorAgent
from backend.agents.evaluation_agent import EvaluationAgent
from backend.agents.execution_agent import ExecutionAgent
from backend.agents.human_approval_agent import HumanApprovalAgent
from backend.agents.playwright_agent import PlaywrightAgent
from backend.agents.report_agent import ReportAgent
from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.agents.requirement_analyst_agent import RequirementAnalystAgent
from backend.agents.feature_inventory_agent import FeatureInventoryAgent
from backend.agents.backlog_creation_agent import BacklogCreationAgent
from backend.agents.jira_sync_agent import JiraSyncAgent
from backend.models.requirement import Requirement
from backend.models.state import WorkflowState

try:
    from langsmith import traceable
except ImportError:
    def traceable(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f


def build_graph(
    scenario_agent: BaseAgent | None = None,
    test_case_agent: BaseAgent | None = None,
    evaluation_agent: BaseAgent | None = None,
    human_approval_agent: BaseAgent | None = None,
    playwright_agent: BaseAgent | None = None,
    execution_agent: BaseAgent | None = None,
    report_agent: BaseAgent | None = None,
    requirement_analyst_agent: BaseAgent | None = None,
    feature_inventory_agent: BaseAgent | None = None,
    backlog_creation_agent: BaseAgent | None = None,
    jira_sync_agent: BaseAgent | None = None,
):
    supervisor_agent = SupervisorAgent()
    scenario_agent = scenario_agent or ScenarioAgent()
    test_case_agent = test_case_agent or TestCaseAgent()
    evaluation_agent = evaluation_agent or EvaluationAgent()
    human_approval_agent = human_approval_agent or HumanApprovalAgent()
    playwright_agent = playwright_agent or PlaywrightAgent()
    execution_agent = execution_agent or ExecutionAgent()
    report_agent = report_agent or ReportAgent()
    requirement_analyst_agent = requirement_analyst_agent or RequirementAnalystAgent()
    feature_inventory_agent = feature_inventory_agent or FeatureInventoryAgent()
    backlog_creation_agent = backlog_creation_agent or BacklogCreationAgent()
    jira_sync_agent = jira_sync_agent or JiraSyncAgent()

    @traceable(name="SupervisorAgent")
    def _supervisor_node(state: WorkflowState) -> WorkflowState:
        return supervisor_agent.run(state)

    @traceable(name="ScenarioAgent")
    def _scenario_node(state: WorkflowState) -> WorkflowState:
        return scenario_agent.run(state)

    @traceable(name="HumanApprovalAgent")
    def _human_approval_node_1(state: WorkflowState) -> WorkflowState:
        return human_approval_agent.run(state)

    @traceable(name="TestCaseAgent")
    def _test_case_node(state: WorkflowState) -> WorkflowState:
        return test_case_agent.run(state)

    @traceable(name="EvaluationAgent")
    def _evaluation_node(state: WorkflowState) -> WorkflowState:
        return evaluation_agent.run(state)

    @traceable(name="HumanApprovalAgent")
    def _human_approval_node_2(state: WorkflowState) -> WorkflowState:
        return human_approval_agent.run(state)

    @traceable(name="PlaywrightAgent")
    def _playwright_node(state: WorkflowState) -> WorkflowState:
        return playwright_agent.run(state)

    @traceable(name="ExecutionAgent")
    def _execution_node(state: WorkflowState) -> WorkflowState:
        return execution_agent.run(state)

    @traceable(name="ReportAgent")
    def _report_node(state: WorkflowState) -> WorkflowState:
        return report_agent.run(state)

    @traceable(name="RequirementAnalystAgent")
    def _requirement_analyst_node(state: WorkflowState) -> WorkflowState:
        return requirement_analyst_agent.run(state)

    @traceable(name="FeatureInventoryAgent")
    def _feature_inventory_node(state: WorkflowState) -> WorkflowState:
        return feature_inventory_agent.run(state)

    @traceable(name="BacklogCreationAgent")
    def _backlog_creation_node(state: WorkflowState) -> WorkflowState:
        return backlog_creation_agent.run(state)

    @traceable(name="JiraSyncAgent")
    def _jira_sync_node(state: WorkflowState, config: dict | None = None) -> WorkflowState:
        return jira_sync_agent.run(state, config=config)

    builder = StateGraph(WorkflowState)
    
    # Nodes
    builder.add_node("supervisor_agent", _supervisor_node)
    builder.add_node("scenario_agent", _scenario_node)
    builder.add_node("human_approval_agent_1", _human_approval_node_1)
    builder.add_node("test_case_agent", _test_case_node)
    builder.add_node("evaluation_agent", _evaluation_node)
    builder.add_node("human_approval_agent_2", _human_approval_node_2)
    builder.add_node("playwright_agent", _playwright_node)
    builder.add_node("execution_agent", _execution_node)
    builder.add_node("report_agent", _report_node)
    builder.add_node("requirement_analyst_agent", _requirement_analyst_node)
    builder.add_node("feature_inventory_agent", _feature_inventory_node)
    builder.add_node("backlog_creation_agent", _backlog_creation_node)
    builder.add_node("jira_sync_agent", _jira_sync_node)

    # Routing Map
    routing_map = {
        "scenario_agent": "scenario_agent",
        "human_approval_agent_1": "human_approval_agent_1",
        "test_case_agent": "test_case_agent",
        "evaluation_agent": "evaluation_agent",
        "human_approval_agent_2": "human_approval_agent_2",
        "playwright_agent": "playwright_agent",
        "execution_agent": "execution_agent",
        "report_agent": "report_agent",
        "requirement_analyst_agent": "requirement_analyst_agent",
        "feature_inventory_agent": "feature_inventory_agent",
        "backlog_creation_agent": "backlog_creation_agent",
        "jira_sync_agent": "jira_sync_agent",
        "end": END,
    }

    # Edges
    builder.add_edge(START, "supervisor_agent")
    
    builder.add_conditional_edges(
        "supervisor_agent",
        supervisor_agent.route_start,
        routing_map
    )
    
    builder.add_conditional_edges(
        "requirement_analyst_agent",
        supervisor_agent.route_after_requirement_analyst,
        routing_map
    )
    
    builder.add_edge("feature_inventory_agent", END)
    
    builder.add_edge("scenario_agent", "backlog_creation_agent")
    builder.add_edge("backlog_creation_agent", "human_approval_agent_1")
    
    builder.add_conditional_edges(
        "human_approval_agent_1",
        supervisor_agent.route_after_human_approval_1,
        routing_map
    )
    
    builder.add_edge("test_case_agent", "evaluation_agent")
    builder.add_edge("evaluation_agent", "human_approval_agent_2")
    
    builder.add_conditional_edges(
        "human_approval_agent_2",
        supervisor_agent.route_after_human_approval_2,
        routing_map
    )
    
    builder.add_conditional_edges(
        "playwright_agent",
        supervisor_agent.route_after_playwright,
        routing_map
    )
    
    builder.add_edge("execution_agent", "report_agent")
    builder.add_edge("report_agent", END)
    builder.add_edge("jira_sync_agent", END)

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

    # In E2E tests / full pipeline, we start without a specific operation config,
    # which the supervisor defaults to routing linearly from start to end.
    raw_result = graph_instance.invoke(initial_state)
    final_state = WorkflowState(**raw_result)

    final_state.add_log("Workflow finished")
    return final_state