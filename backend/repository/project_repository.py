import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from backend.models.project import Project
from backend.models.requirement import Requirement, RequirementSource
from backend.models.scenario import Scenario
from backend.models.test_case import TestCase
from backend.models.document import Document
from backend.models.execution_result import ExecutionResult

STORE_PATH = Path(__file__).parent.parent / "database" / "project_store.json"


class ProjectRepository(ABC):
    @abstractmethod
    def list_projects(self) -> list[Project]:
        pass

    @abstractmethod
    def get_project(self, project_id: UUID) -> Project | None:
        pass

    @abstractmethod
    def create_project(self, name: str, description: str) -> Project:
        pass

    @abstractmethod
    def update_project(self, project: Project) -> Project | None:
        pass

    @abstractmethod
    def delete_project(self, project_id: UUID) -> bool:
        pass

    @abstractmethod
    def get_requirements(self, project_id: UUID) -> list[Requirement]:
        pass

    @abstractmethod
    def create_requirement(
        self,
        project_id: UUID,
        title: str,
        description: str,
        priority: str,
        business_domain: str,
        attachments: list[str] | None = None
    ) -> Requirement:
        pass

    @abstractmethod
    def get_scenarios(self, requirement_id: UUID) -> list[Scenario]:
        pass

    @abstractmethod
    def save_scenarios(self, scenarios: list[Scenario]) -> None:
        pass

    @abstractmethod
    def update_scenario(self, scenario: Scenario) -> Scenario | None:
        pass

    @abstractmethod
    def delete_scenario(self, scenario_id: UUID) -> bool:
        pass

    @abstractmethod
    def get_test_cases(self, scenario_id: UUID) -> list[TestCase]:
        pass

    @abstractmethod
    def save_test_cases(self, test_cases: list[TestCase]) -> None:
        pass

    @abstractmethod
    def update_test_case(self, test_case: TestCase) -> TestCase | None:
        pass

    @abstractmethod
    def delete_test_case(self, test_case_id: UUID) -> bool:
        pass

    @abstractmethod
    def get_documents(self, project_id: UUID) -> list[Document]:
        pass

    @abstractmethod
    def save_document(self, document: Document) -> None:
        pass

    @abstractmethod
    def delete_document(self, project_id: UUID, document_id: UUID) -> bool:
        pass

    @abstractmethod
    def get_execution_results(self, project_id: UUID) -> list[ExecutionResult]:
        pass

    @abstractmethod
    def save_execution_result(self, project_id: UUID, result: ExecutionResult) -> None:
        pass


class JSONProjectRepository(ProjectRepository):
    def __init__(self, file_path: Path = STORE_PATH):
        self.file_path = file_path
        self._ensure_store_exists()

    def _ensure_store_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_raw({
                "projects": [],
                "requirements": {},
                "scenarios": {},
                "test_cases": {},
                "documents": {},
                "execution_results": {}
            })

    def _read_raw(self) -> dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                "projects": [],
                "requirements": {},
                "scenarios": {},
                "test_cases": {},
                "documents": {},
                "execution_results": {}
            }

    def _write_raw(self, data: dict) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def list_projects(self) -> list[Project]:
        raw = self._read_raw()
        return [Project.model_validate(p) for p in raw.get("projects", [])]

    def get_project(self, project_id: UUID) -> Project | None:
        projects = self.list_projects()
        for p in projects:
            if p.id == project_id:
                return p
        return None

    def create_project(self, name: str, description: str) -> Project:
        raw = self._read_raw()
        project = Project(
            id=uuid4(),
            name=name,
            description=description,
            created_at=datetime.now(timezone.utc),
            requirements=[]
        )
        raw.setdefault("projects", []).append(project.model_dump(mode="json"))
        self._write_raw(raw)
        return project

    def update_project(self, project: Project) -> Project | None:
        raw = self._read_raw()
        projects = raw.setdefault("projects", [])
        p_id_str = str(project.id)
        for idx, p in enumerate(projects):
            if p["id"] == p_id_str:
                projects[idx] = project.model_dump(mode="json")
                self._write_raw(raw)
                return project
        return None

    def delete_project(self, project_id: UUID) -> bool:
        raw = self._read_raw()
        projects = raw.setdefault("projects", [])
        p_id_str = str(project_id)
        
        project_idx = -1
        for idx, p in enumerate(projects):
            if p["id"] == p_id_str:
                project_idx = idx
                break
                
        if project_idx == -1:
            return False

        # Retrieve and clean up child elements
        proj = Project.model_validate(projects[project_idx])
        
        # Clean up requirements and their descendants
        reqs_raw = raw.setdefault("requirements", {})
        scenarios_raw = raw.setdefault("scenarios", {})
        tcs_raw = raw.setdefault("test_cases", {})
        
        for r_id in proj.requirements:
            r_str = str(r_id)
            if r_str in reqs_raw:
                del reqs_raw[r_str]
                
            # Clean up scenarios belonging to requirement
            sc_to_delete = [s_id for s_id, s_data in scenarios_raw.items() if s_data.get("requirement_id") == r_str]
            for s_id in sc_to_delete:
                del scenarios_raw[s_id]
                # Clean up test cases belonging to scenario
                tc_to_delete = [tc_id for tc_id, tc_data in tcs_raw.items() if tc_data.get("scenario_id") == s_id]
                for tc_id in tc_to_delete:
                    del tcs_raw[tc_id]

        # Clean up documents
        docs_raw = raw.setdefault("documents", {})
        docs_to_delete = [d_id for d_id, d_data in docs_raw.items() if d_data.get("project_id") == p_id_str]
        for d_id in docs_to_delete:
            del docs_raw[d_id]
            
        # Clean up executions
        execs_raw = raw.setdefault("execution_results", {})
        execs_to_delete = [e_id for e_id, e_data in execs_raw.items() if e_data.get("project_id") == p_id_str]
        for e_id in execs_to_delete:
            del execs_raw[e_id]

        # Delete project itself
        del projects[project_idx]
        self._write_raw(raw)
        return True

    def get_requirements(self, project_id: UUID) -> list[Requirement]:
        project = self.get_project(project_id)
        if not project:
            return []
        
        raw = self._read_raw()
        reqs_raw = raw.get("requirements", {})
        result = []
        for r_id in project.requirements:
            r_str = str(r_id)
            if r_str in reqs_raw:
                result.append(Requirement.model_validate(reqs_raw[r_str]))
        return result

    def create_requirement(
        self,
        project_id: UUID,
        title: str,
        description: str,
        priority: str,
        business_domain: str,
        attachments: list[str] | None = None
    ) -> Requirement:
        raw = self._read_raw()
        projects = raw.setdefault("projects", [])
        project_idx = -1
        for idx, p in enumerate(projects):
            if p["id"] == str(project_id):
                project_idx = idx
                break
        
        if project_idx == -1:
            raise ValueError(f"Project {project_id} not found")

        req_id = uuid4()
        req = Requirement(
            id=req_id,
            title=title,
            description=description,
            source=RequirementSource.MANUAL,
            uploaded_at=datetime.now(timezone.utc)
        )
        
        req_dump = req.model_dump(mode="json")
        req_dump["priority"] = priority
        req_dump["business_domain"] = business_domain
        req_dump["attachments"] = attachments or []

        raw.setdefault("requirements", {})[str(req_id)] = req_dump
        projects[project_idx].setdefault("requirements", []).append(str(req_id))
        
        self._write_raw(raw)
        return req

    def get_scenarios(self, requirement_id: UUID) -> list[Scenario]:
        raw = self._read_raw()
        scenarios_raw = raw.get("scenarios", {})
        result = []
        for s_id, s_data in scenarios_raw.items():
            if s_data.get("requirement_id") == str(requirement_id):
                result.append(Scenario.model_validate(s_data))
        return result

    def save_scenarios(self, scenarios: list[Scenario]) -> None:
        raw = self._read_raw()
        scenarios_raw = raw.setdefault("scenarios", {})
        for s in scenarios:
            scenarios_raw[str(s.id)] = s.model_dump(mode="json")
        self._write_raw(raw)

    def update_scenario(self, scenario: Scenario) -> Scenario | None:
        raw = self._read_raw()
        scenarios_raw = raw.setdefault("scenarios", {})
        s_id_str = str(scenario.id)
        if s_id_str in scenarios_raw:
            scenarios_raw[s_id_str] = scenario.model_dump(mode="json")
            self._write_raw(raw)
            return scenario
        return None

    def delete_scenario(self, scenario_id: UUID) -> bool:
        raw = self._read_raw()
        scenarios_raw = raw.setdefault("scenarios", {})
        s_id_str = str(scenario_id)
        if s_id_str in scenarios_raw:
            del scenarios_raw[s_id_str]
            tcs_raw = raw.setdefault("test_cases", {})
            to_delete = [tc_id for tc_id, tc_data in tcs_raw.items() if tc_data.get("scenario_id") == s_id_str]
            for tc_id in to_delete:
                del tcs_raw[tc_id]
            self._write_raw(raw)
            return True
        return False

    def get_test_cases(self, scenario_id: UUID) -> list[TestCase]:
        raw = self._read_raw()
        tcs_raw = raw.get("test_cases", {})
        result = []
        for tc_id, tc_data in tcs_raw.items():
            if tc_data.get("scenario_id") == str(scenario_id):
                result.append(TestCase.model_validate(tc_data))
        return result

    def save_test_cases(self, test_cases: list[TestCase]) -> None:
        raw = self._read_raw()
        tcs_raw = raw.setdefault("test_cases", {})
        for tc in test_cases:
            tcs_raw[str(tc.id)] = tc.model_dump(mode="json")
        self._write_raw(raw)

    def update_test_case(self, test_case: TestCase) -> TestCase | None:
        raw = self._read_raw()
        tcs_raw = raw.setdefault("test_cases", {})
        tc_id_str = str(test_case.id)
        if tc_id_str in tcs_raw:
            tcs_raw[tc_id_str] = test_case.model_dump(mode="json")
            self._write_raw(raw)
            return test_case
        return None

    def delete_test_case(self, test_case_id: UUID) -> bool:
        raw = self._read_raw()
        tcs_raw = raw.setdefault("test_cases", {})
        tc_id_str = str(test_case_id)
        if tc_id_str in tcs_raw:
            del tcs_raw[tc_id_str]
            self._write_raw(raw)
            return True
        return False

    def get_documents(self, project_id: UUID) -> list[Document]:
        raw = self._read_raw()
        docs_raw = raw.get("documents", {})
        result = []
        p_id_str = str(project_id)
        for doc_id, doc_data in docs_raw.items():
            if doc_data.get("project_id") == p_id_str:
                result.append(Document.model_validate(doc_data))
        return result

    def save_document(self, document: Document) -> None:
        raw = self._read_raw()
        docs_raw = raw.setdefault("documents", {})
        docs_raw[str(document.id)] = document.model_dump(mode="json")
        self._write_raw(raw)

    def delete_document(self, project_id: UUID, document_id: UUID) -> bool:
        raw = self._read_raw()
        docs_raw = raw.setdefault("documents", {})
        doc_id_str = str(document_id)
        if doc_id_str in docs_raw and docs_raw[doc_id_str].get("project_id") == str(project_id):
            del docs_raw[doc_id_str]
            self._write_raw(raw)
            return True
        return False

    def get_execution_results(self, project_id: UUID) -> list[ExecutionResult]:
        raw = self._read_raw()
        execs_raw = raw.get("execution_results", {})
        result = []
        p_id_str = str(project_id)
        for ex_id, ex_data in execs_raw.items():
            if ex_data.get("project_id") == p_id_str:
                # ExecutionResult doesn't natively have project_id in standard Pydantic schema, 
                # but we validate it after cleaning the extra field so validation matches.
                cleaned = dict(ex_data)
                cleaned.pop("project_id", None)
                result.append(ExecutionResult.model_validate(cleaned))
        return result

    def save_execution_result(self, project_id: UUID, result: ExecutionResult) -> None:
        raw = self._read_raw()
        execs_raw = raw.setdefault("execution_results", {})
        dump = result.model_dump(mode="json")
        dump["project_id"] = str(project_id)
        execs_raw[str(result.id)] = dump
        self._write_raw(raw)


_active_project_repo: ProjectRepository = JSONProjectRepository()


def get_project_repository() -> ProjectRepository:
    global _active_project_repo
    return _active_project_repo
