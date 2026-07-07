from uuid import UUID, uuid4
from datetime import datetime, timezone
from backend.models.project import Project
from backend.models.requirement import Requirement
from backend.models.scenario import Scenario
from backend.models.test_case import TestCase
from backend.models.common import Priority
from backend.models.test_case import TestCaseStatus, EvaluationStatus
from backend.models.document import Document
from backend.models.execution_result import ExecutionResult
from backend.repository.project_repository import get_project_repository



class ProjectService:
    @property
    def repo(self):
        return get_project_repository()



    def list_projects(self) -> list[Project]:
        return self.repo.list_projects()

    def get_project(self, project_id: UUID) -> Project | None:
        return self.repo.get_project(project_id)

    def create_project(self, name: str, description: str, line_of_business: str = "general") -> Project:
        return self.repo.create_project(name, description, line_of_business)

    def get_requirements(self, project_id: UUID) -> list[Requirement]:
        return self.repo.get_requirements(project_id)

    def create_requirement(
        self,
        project_id: UUID,
        title: str,
        description: str,
        priority: str,
        business_domain: str,
        attachments: list[str] | None = None,
        original_filename: str | None = None,
        requirement_id: str | None = None,
        requirement_title: str | None = None
    ) -> Requirement:
        return self.repo.create_requirement(
            project_id, title, description, priority, business_domain, attachments,
            original_filename, requirement_id, requirement_title
        )

    def get_scenarios_for_requirement(self, requirement_id: UUID) -> list[Scenario]:
        return self.repo.get_scenarios(requirement_id)

    def get_scenarios_for_project(self, project_id: UUID) -> list[Scenario]:
        requirements = self.get_requirements(project_id)
        scenarios = []
        for req in requirements:
            scenarios.extend(self.get_scenarios_for_requirement(req.id))
        return scenarios

    def update_scenario(
        self,
        scenario_id: UUID,
        scenario_name: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        approved: bool | None = None
    ) -> Scenario | None:
        # We need to find the scenario first. To find a scenario by ID, let's load all scenarios.
        # Wait, does the repository support get_scenario by ID?
        # Let's add a helper in the repository or just lookup from raw since we have list_projects/get_scenarios.
        # Actually, in our JSON repository, we can just load the raw file, get it, update it, and write it back.
        # But to be clean, let's look up the scenario from the raw data.
        # Wait, JSONProjectRepository has `update_scenario(scenario)` which takes a Scenario instance.
        # Let's find the scenario in the repo.
        raw_data = self.repo._read_raw()
        scenario_data = raw_data.get("scenarios", {}).get(str(scenario_id))
        if not scenario_data:
            return None
        
        scenario = Scenario.model_validate(scenario_data)
        if scenario_name is not None:
            scenario.scenario_name = scenario_name
        if description is not None:
            scenario.description = description
        if priority is not None:
            scenario.priority = priority
        if approved is not None:
            scenario.approved = approved
            if not approved:
                self.repo.delete_test_cases_for_scenario(scenario_id)

        return self.repo.update_scenario(scenario)

    def delete_scenario(self, scenario_id: UUID) -> bool:
        return self.repo.delete_scenario(scenario_id)

    def duplicate_scenario(self, scenario_id: UUID) -> Scenario | None:
        raw_data = self.repo._read_raw()
        scenario_data = raw_data.get("scenarios", {}).get(str(scenario_id))
        if not scenario_data:
            return None
        
        orig = Scenario.model_validate(scenario_data)
        dup = Scenario(
            id=uuid4(),
            requirement_id=orig.requirement_id,
            scenario_name=f"{orig.scenario_name} (Copy)",
            description=orig.description,
            priority=orig.priority,
            confidence=orig.confidence,
            approved=orig.approved,
            generated_at=datetime.now(timezone.utc)
        )
        self.repo.save_scenarios([dup])
        return dup

    def get_test_cases_for_scenario(self, scenario_id: UUID) -> list[TestCase]:
        return self.repo.get_test_cases(scenario_id)

    def get_test_cases_for_project(self, project_id: UUID) -> list[TestCase]:
        scenarios = self.get_scenarios_for_project(project_id)
        test_cases = []
        for sc in scenarios:
            test_cases.extend(self.get_test_cases_for_scenario(sc.id))
        return test_cases

    def update_test_case(
        self,
        test_case_id: UUID,
        title: str | None = None,
        preconditions: list[str] | None = None,
        steps: list[str] | None = None,
        expected_result: str | None = None,
        priority: Priority | None = None,
        status: TestCaseStatus | None = None,
        confidence: float | None = None,
        evaluation_status: EvaluationStatus | None = None,
        evaluation_reason: str | None = None
    ) -> TestCase | None:
        raw_data = self.repo._read_raw()
        tc_data = raw_data.get("test_cases", {}).get(str(test_case_id))
        if not tc_data:
            return None
        
        tc = TestCase.model_validate(tc_data)
        if title is not None:
            tc.title = title
        if preconditions is not None:
            tc.preconditions = preconditions
        if steps is not None:
            tc.steps = steps
        if expected_result is not None:
            tc.expected_result = expected_result
        if priority is not None:
            tc.priority = priority
        if status is not None:
            tc.status = status
        if confidence is not None:
            tc.confidence = confidence
        if evaluation_status is not None:
            tc.evaluation_status = evaluation_status
        if evaluation_reason is not None:
            tc.evaluation_reason = evaluation_reason

        return self.repo.update_test_case(tc)

    def delete_test_case(self, test_case_id: UUID) -> bool:
        return self.repo.delete_test_case(test_case_id)

    def update_project(self, project_id: UUID, name: str, description: str, line_of_business: str = "general") -> Project | None:
        proj = self.repo.get_project(project_id)
        if not proj:
            return None
        proj.name = name
        proj.description = description
        proj.line_of_business = line_of_business
        return self.repo.update_project(proj)

    def delete_project(self, project_id: UUID) -> bool:
        return self.repo.delete_project(project_id)

    def get_documents(self, project_id: UUID) -> list[Document]:
        return self.repo.get_documents(project_id)

    def create_document(
        self,
        project_id: UUID,
        filename: str,
        original_filename: str,
        mime_type: str,
        size: int,
        storage_path: str,
        metadata: dict | None = None
    ) -> Document:
        doc = Document(
            id=uuid4(),
            project_id=project_id,
            filename=filename,
            original_filename=original_filename,
            mime_type=mime_type,
            size=size,
            storage_path=storage_path,
            embedding_status="pending",
            metadata=metadata or {}
        )
        self.repo.save_document(doc)
        return doc

    def delete_document(self, project_id: UUID, document_id: UUID) -> bool:
        return self.repo.delete_document(project_id, document_id)

    def get_execution_results(self, project_id: UUID) -> list[ExecutionResult]:
        return self.repo.get_execution_results(project_id)

    def save_execution_result(self, project_id: UUID, result: ExecutionResult) -> None:
        self.repo.save_execution_result(project_id, result)

    def get_scenario_notes(self, scenario_id: UUID) -> list[str]:
        return self.repo.get_scenario_notes(scenario_id)

    def add_scenario_note(self, scenario_id: UUID, note: str) -> None:
        self.repo.add_scenario_note(scenario_id, note)

    def get_test_case_notes(self, test_case_id: UUID) -> list[str]:
        return self.repo.get_test_case_notes(test_case_id)

    def add_test_case_note(self, test_case_id: UUID, note: str) -> None:
        self.repo.add_test_case_note(test_case_id, note)

    def update_test_case_script(self, test_case_id: UUID, script: str) -> TestCase | None:
        raw_data = self.repo._read_raw()
        tc_data = raw_data.get("test_cases", {}).get(str(test_case_id))
        if not tc_data:
            return None
        tc = TestCase.model_validate(tc_data)
        tc.playwright_script = script
        return self.repo.update_test_case(tc)

    def get_execution_result(self, project_id: UUID, execution_id: UUID) -> ExecutionResult | None:
        return self.repo.get_execution_result(project_id, execution_id)

