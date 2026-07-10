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
from backend.models.requirement import Requirement
from backend.repository.project_repository import get_project_repository



class WorkflowService:
    @property
    def repo(self):
        return get_project_repository()


    def generate_scenarios(self, project_id: UUID, requirement_id: UUID, count: int, mode: str = "append") -> list[Scenario]:
        project = self.repo.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        requirements = self.repo.get_requirements(project_id)
        requirement = next((r for r in requirements if r.id == requirement_id), None)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found in project {project_id}")

        if mode == "replace":
            self.repo.clear_scenarios_for_requirement(requirement_id)

        # New LangGraph-based Orchestration:
        from backend.graph.workflow import build_graph
        from backend.models.operation import WorkflowOperation
        
        scenario_agent = ScenarioAgent(scenario_count=count)
        local_graph = build_graph(scenario_agent=scenario_agent)
        
        state = WorkflowState(requirement=requirement)
        state.add_log("Starting scenario generation from service via LangGraph")
        
        config = {"configurable": {"operation": WorkflowOperation.GENERATE_SCENARIOS}}
        raw_result = local_graph.invoke(state, config)
        final_state = WorkflowState(**raw_result)
        
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

        # Clear existing test cases for these approved scenarios first to prevent stale records
        for s in approved_scenarios:
            self.repo.delete_test_cases_for_scenario(s.id)

        # New LangGraph-based Orchestration:
        from backend.graph.workflow import build_graph
        from backend.models.operation import WorkflowOperation
        
        local_graph = build_graph()
        state = WorkflowState(requirement=requirement, generated_scenarios=approved_scenarios)
        state.add_log("Starting test case generation and evaluation steps from service via LangGraph")
        
        config = {"configurable": {"operation": WorkflowOperation.GENERATE_TESTCASES}}
        raw_result = local_graph.invoke(state, config)
        final_state = WorkflowState(**raw_result)

        # Persist generated test cases
        self.repo.save_test_cases(final_state.generated_test_cases)
        return final_state.generated_test_cases

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

        # Human approval gate: PlaywrightAgent must reject requests for unapproved test cases.
        if test_case.evaluation_status != "approved":
            raise ValueError("Playwright script generation rejected: Test case is not approved")

        # New LangGraph-based Orchestration:
        from backend.graph.workflow import build_graph
        from backend.models.operation import WorkflowOperation
        
        local_graph = build_graph()
        state = WorkflowState(
            requirement=requirement,
            generated_test_cases=[test_case],
            human_approved_test_case_ids=[test_case.id]
        )
        state.add_log("Generating Playwright script from service via LangGraph")
        
        config = {
            "configurable": {
                "operation": WorkflowOperation.GENERATE_PLAYWRIGHT,
                "test_case_id": str(test_case_id)
            }
        }
        raw_result = local_graph.invoke(state, config)
        final_state = WorkflowState(**raw_result)

        updated_tc = final_state.generated_test_cases[0]
        self.repo.save_test_cases([updated_tc])
        return updated_tc


# Global stream event log buffer
active_execution_events = {}


def run_execution_and_stream(workflow_service: WorkflowService, project_id: UUID, test_case_id: UUID, execution_id: UUID = None) -> None:
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
        
        import re
        from backend.services.playwright_runner import ARTIFACTS_ROOT
        
        known_screenshots = set()

        def on_log_callback(log_line: str):
            timeline_msg = None
            timeline_match = re.search(r"\[Timeline\]\s*([^:\n]+)(?::\s*(.+))?", log_line, re.IGNORECASE)
            if timeline_match:
                title = timeline_match.group(1).strip()
                desc = timeline_match.group(2).strip() if timeline_match.group(2) else ""
                timeline_msg = f"{title}: {desc}" if desc else title
            
            # Scan for newly created screenshots
            screenshot_file = None
            try:
                run_dir = ARTIFACTS_ROOT / tc_id_str
                if run_dir.exists():
                    pngs = list(run_dir.glob("*.png")) + list(run_dir.glob("**/*.png"))
                    for png in pngs:
                        png_str = str(png)
                        if png_str not in known_screenshots:
                            known_screenshots.add(png_str)
                            screenshot_file = png_str
                            break
            except Exception:
                pass

            log_event("Running", timeline_msg, log_line, screenshot=screenshot_file)

        # New LangGraph-based Orchestration:
        from backend.graph.workflow import build_graph
        from backend.models.operation import WorkflowOperation
        
        exec_agent = ExecutionAgent(on_log=on_log_callback)
        local_graph = build_graph(execution_agent=exec_agent)
        
        config = {"configurable": {"operation": WorkflowOperation.EXECUTE}}
        raw_result = local_graph.invoke(state, config)
        final_state = WorkflowState(**raw_result)
        
        result = final_state.execution_results[0]
        if execution_id:
            result.id = execution_id
        
        # Save updated test case status and execution result in repo
        workflow_service.repo.update_test_case(test_case)
        workflow_service.repo.save_execution_result(project_id, result)
        
        # Compile reports automatically via ReportService
        from backend.services.report_service import ReportService
        report_service = ReportService(workflow_service.repo)
        report_service.compile_reports(project_id, result)
        
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

