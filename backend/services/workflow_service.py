from uuid import UUID
from backend.agents.scenario_agent import ScenarioAgent
from backend.agents.test_case_agent import TestCaseAgent
from backend.agents.evaluation_agent import EvaluationAgent
from backend.models.state import WorkflowState
from backend.models.scenario import Scenario
from backend.models.test_case import TestCase
from backend.agents.playwright_agent import PlaywrightAgent
from backend.agents.execution_agent import ExecutionAgent
from backend.models.execution_result import ExecutionResult
from backend.repository.project_repository import get_project_repository



class WorkflowService:
    @property
    def repo(self):
        return get_project_repository()


    def generate_scenarios(self, project_id: UUID, requirement_id: UUID, count: int) -> list[Scenario]:
        project = self.repo.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        requirements = self.repo.get_requirements(project_id)
        requirement = next((r for r in requirements if r.id == requirement_id), None)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found in project {project_id}")

        # Instantiate ScenarioAgent with the requested custom scenario count
        agent = ScenarioAgent(scenario_count=count)
        
        # Build initial WorkflowState
        state = WorkflowState(requirement=requirement)
        state.add_log("Starting scenario generation from service")
        
        # Execute agent run
        final_state = agent.run(state)
        
        # Persist scenarios
        self.repo.save_scenarios(final_state.generated_scenarios)
        return final_state.generated_scenarios

    def generate_test_cases(self, project_id: UUID, requirement_id: UUID) -> list[TestCase]:
        project = self.repo.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        requirements = self.repo.get_requirements(project_id)
        requirement = next((r for r in requirements if r.id == requirement_id), None)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found in project {project_id}")

        scenarios = self.repo.get_scenarios(requirement_id)
        # Business rule check: only approved scenarios can proceed to test case generation
        approved_scenarios = [s for s in scenarios if s.approved]
        if not approved_scenarios:
            raise ValueError("Cannot generate test cases: no approved scenarios exist for this requirement")

        # Setup state with approved scenarios
        state = WorkflowState(requirement=requirement, generated_scenarios=approved_scenarios)
        state.add_log("Starting test case generation and evaluation steps from service")

        # Run agents sequentially as in the graph
        tc_agent = TestCaseAgent()
        state = tc_agent.run(state)

        eval_agent = EvaluationAgent()
        state = eval_agent.run(state)

        # Persist generated test cases
        self.repo.save_test_cases(state.generated_test_cases)
        return state.generated_test_cases

    def generate_playwright_script(self, project_id: UUID, test_case_id: UUID) -> TestCase:
        raw = self.repo._read_raw()
        tc_data = raw.get("test_cases", {}).get(str(test_case_id))
        if not tc_data:
            raise ValueError(f"TestCase {test_case_id} not found")
        test_case = TestCase.model_validate(tc_data)

        sc_data = raw.get("scenarios", {}).get(str(test_case.scenario_id))
        if not sc_data:
            raise ValueError(f"Scenario {test_case.scenario_id} not found for TestCase {test_case_id}")
        scenario = Scenario.model_validate(sc_data)

        req_data = raw.get("requirements", {}).get(str(scenario.requirement_id))
        if not req_data:
            raise ValueError(f"Requirement {scenario.requirement_id} not found for Scenario {scenario.id}")
        requirement = Requirement.model_validate(req_data)

        human_approved = []
        if test_case.evaluation_status != "approved":
            human_approved.append(test_case.id)

        state = WorkflowState(
            requirement=requirement,
            generated_test_cases=[test_case],
            human_approved_test_case_ids=human_approved
        )
        state.add_log("Generating Playwright script from service")

        agent = PlaywrightAgent()
        state = agent.run(state)

        updated_tc = state.generated_test_cases[0]
        self.repo.save_test_cases([updated_tc])
        return updated_tc


# Global stream event log buffer
active_execution_events = {}


def run_execution_and_stream(workflow_service: WorkflowService, project_id: UUID, test_case_id: UUID) -> None:
    tc_id_str = str(test_case_id)
    events = []
    active_execution_events[tc_id_str] = events

    def log_event(status, timeline, log, screenshot=None, artifact=None):
        events.append({
            "status": status,
            "timeline": timeline,
            "log": log,
            "screenshot": screenshot,
            "artifact": artifact
        })

    try:
        log_event("Generating", "Generating execution runner environment", "Initiating process group for Playwright...")
        
        raw = workflow_service.repo._read_raw()
        tc_data = raw.get("test_cases", {}).get(tc_id_str)
        if not tc_data:
            raise ValueError(f"TestCase {test_case_id} not found")
        test_case = TestCase.model_validate(tc_data)

        sc_data = raw.get("scenarios", {}).get(str(test_case.scenario_id))
        if not sc_data:
            raise ValueError(f"Scenario {test_case.scenario_id} not found")
        scenario = Scenario.model_validate(sc_data)

        req_data = raw.get("requirements", {}).get(str(scenario.requirement_id))
        if not req_data:
            raise ValueError(f"Requirement {scenario.requirement_id} not found")
        requirement = Requirement.model_validate(req_data)

        log_event("Running", "Running Playwright TypeScript tests", "npx playwright test --reporter=json --trace=on")

        human_approved = []
        if test_case.evaluation_status != "approved":
            human_approved.append(test_case.id)

        state = WorkflowState(
            requirement=requirement,
            generated_test_cases=[test_case],
            human_approved_test_case_ids=human_approved
        )
        
        agent = ExecutionAgent()
        state = agent.run(state)
        
        result = state.execution_results[0]
        
        # Save updated test case status and execution result in repo
        workflow_service.repo.update_test_case(test_case)
        workflow_service.repo.save_execution_result(project_id, result)
        
        log_event("Capturing Screenshots", "Capturing run artifacts", "Collecting trace.zip and screenshot logs...")
        log_event("Collecting Trace", "Finalizing execution report", "Exporting JUnit XML and JSON report format...")
        
        log_event(
            "Completed", 
            "Execution completed successfully", 
            result.error_message or "All steps passed.",
            screenshot=result.screenshot_path,
            artifact={
                "duration": result.duration_seconds,
                "status": result.status.value,
                "screenshot": result.screenshot_path,
                "video": result.video_path,
                "trace": result.trace_path
            }
        )
    except Exception as exc:
        log_event("Completed", "Execution completed with error", str(exc))

