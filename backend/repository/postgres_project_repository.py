from datetime import datetime, timezone
from uuid import UUID
import logging
from sqlalchemy.orm import scoped_session
from sqlalchemy import select

from backend.models.project import Project
from backend.models.requirement import Requirement, RequirementSource
from backend.models.scenario import Scenario
from backend.models.test_case import TestCase
from backend.models.document import Document
from backend.models.execution_result import ExecutionResult
from backend.models.release import Release
from backend.models.test_cycle import TestCycle
from backend.repository.project_repository import ProjectRepository
from backend.database.db import SessionLocal
from backend.database.db_models import (
    ProjectDB, RequirementDB, ScenarioDB, TestCaseDB, 
    ExecutionDB, ReportDB, DocumentDB, ScenarioNoteDB, TestCaseNoteDB,
    ReleaseDB, TestCycleDB
)

logger = logging.getLogger("backend.repository.postgres_project_repository")

# Set up scoped session
db_session = scoped_session(SessionLocal)


class PostgresProjectRepository(ProjectRepository):
    @property
    def session(self):
        return db_session()

    def begin_transaction(self) -> None:
        session = self.session
        if not session.in_transaction():
            session.begin()

    def commit(self) -> None:
        session = self.session
        if session.in_transaction():
            session.commit()
        db_session.remove()

    def rollback(self) -> None:
        session = self.session
        if session.in_transaction():
            session.rollback()
        db_session.remove()

    def _flush_or_commit(self) -> None:
        session = self.session
        if not session.in_transaction():
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
            finally:
                db_session.remove()
        else:
            session.flush()

    def list_projects(self, include_deleted: bool = False) -> list[Project]:
        session = self.session
        stmt = select(ProjectDB)
        if not include_deleted:
            stmt = stmt.where(ProjectDB.is_deleted.is_(False))
        db_projects = session.scalars(stmt).all()
        return [
            Project(
                id=p.id,
                name=p.name,
                description=p.description,
                line_of_business=p.line_of_business,
                framework=p.framework,
                jira_project_key=p.jira_project_key,
                target_url=getattr(p, "target_url", None),
                target_username=getattr(p, "target_username", None),
                target_password_enc=getattr(p, "target_password_enc", None),
                created_at=p.created_at,
                requirements=[r.id for r in p.requirements if include_deleted or not r.is_deleted]
            )
            for p in db_projects
        ]

    def get_project(self, project_id: UUID, include_deleted: bool = False) -> Project | None:
        session = self.session
        stmt = select(ProjectDB).where(ProjectDB.id == project_id)
        if not include_deleted:
            stmt = stmt.where(ProjectDB.is_deleted.is_(False))
        p = session.scalar(stmt)
        if not p:
            return None
        return Project(
            id=p.id,
            name=p.name,
            description=p.description,
            line_of_business=p.line_of_business,
            framework=p.framework,
            jira_project_key=p.jira_project_key,
            target_url=getattr(p, "target_url", None),
            target_username=getattr(p, "target_username", None),
            target_password_enc=getattr(p, "target_password_enc", None),
            created_at=p.created_at,
            requirements=[r.id for r in p.requirements if include_deleted or not r.is_deleted]
        )

    def create_project(self, name: str, description: str, line_of_business: str = "general", framework: str = "playwright", jira_project_key: str | None = None, target_url: str | None = "https://adactinhotelapp.com/", target_username: str | None = None, target_password_enc: str | None = None) -> Project:
        session = self.session
        db_proj = ProjectDB(
            name=name,
            description=description,
            line_of_business=line_of_business,
            framework=framework,
            jira_project_key=jira_project_key,
            target_url=target_url,
            target_username=target_username,
            target_password_enc=target_password_enc
        )
        session.add(db_proj)
        self._flush_or_commit()
        return Project(
            id=db_proj.id,
            name=db_proj.name,
            description=db_proj.description,
            line_of_business=db_proj.line_of_business,
            framework=db_proj.framework,
            jira_project_key=db_proj.jira_project_key,
            target_url=db_proj.target_url,
            target_username=db_proj.target_username,
            target_password_enc=db_proj.target_password_enc,
            created_at=db_proj.created_at,
            requirements=[]
        )

    def update_project(self, project: Project) -> Project | None:
        session = self.session
        stmt = select(ProjectDB).where(ProjectDB.id == project.id, ProjectDB.is_deleted.is_(False))
        db_proj = session.scalar(stmt)
        if not db_proj:
            return None
        db_proj.name = project.name
        db_proj.description = project.description
        db_proj.line_of_business = project.line_of_business
        db_proj.framework = project.framework
        db_proj.jira_project_key = project.jira_project_key
        db_proj.target_url = project.target_url
        db_proj.target_username = project.target_username
        db_proj.target_password_enc = project.target_password_enc
        self._flush_or_commit()
        return project

    def delete_project(self, project_id: UUID, deleted_by: UUID | None = None) -> bool:
        session = self.session
        now = datetime.now(timezone.utc)
        stmt = select(ProjectDB).where(ProjectDB.id == project_id, ProjectDB.is_deleted.is_(False))
        db_proj = session.scalar(stmt)
        if not db_proj:
            return False
        
        db_proj.is_deleted = True
        db_proj.deleted_at = now
        db_proj.deleted_by = deleted_by
        # Cascade soft-deletes
        for req in db_proj.requirements:
            req.is_deleted = True
            req.deleted_at = now
            req.deleted_by = deleted_by
            for sc in req.scenarios:
                sc.is_deleted = True
                sc.deleted_at = now
                sc.deleted_by = deleted_by
                for tc in sc.test_cases:
                    tc.is_deleted = True
                    tc.deleted_at = now
                    tc.deleted_by = deleted_by
        
        self._flush_or_commit()
        return True

    def get_requirements(self, project_id: UUID, include_deleted: bool = False) -> list[Requirement]:
        session = self.session
        stmt = select(RequirementDB).where(RequirementDB.project_id == project_id)
        if not include_deleted:
            stmt = stmt.where(RequirementDB.is_deleted.is_(False))
        db_reqs = session.scalars(stmt).all()
        return [
            Requirement(
                id=r.id,
                title=r.title,
                description=r.description,
                source=RequirementSource(r.source),
                uploaded_at=r.uploaded_at,
                original_filename=r.original_filename,
                requirement_id=r.requirement_id,
                requirement_title=r.requirement_title,
                priority=r.priority,
                business_domain=r.business_domain,
                attachments=r.attachments,
                feature_mapping=r.feature_mapping,
                jira_issue_key=r.jira_issue_key,
                jira_issue_url=r.jira_issue_url,
                jira_sync_status=r.jira_sync_status,
                jira_last_synced_at=r.jira_last_synced_at,
                release_id=r.release_id
            )
            for r in db_reqs
        ]

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
        requirement_title: str | None = None,
        release_id: UUID | None = None
    ) -> Requirement:
        session = self.session
        db_req = RequirementDB(
            project_id=project_id,
            release_id=release_id,
            title=title,
            description=description,
            source="manual",
            uploaded_at=datetime.now(timezone.utc),
            original_filename=original_filename,
            requirement_id=requirement_id,
            requirement_title=requirement_title,
            priority=priority,
            business_domain=business_domain,
            attachments=attachments or []
        )
        session.add(db_req)
        self._flush_or_commit()
        return Requirement(
            id=db_req.id,
            title=db_req.title,
            description=db_req.description,
            source=RequirementSource(db_req.source),
            uploaded_at=db_req.uploaded_at,
            original_filename=db_req.original_filename,
            requirement_id=db_req.requirement_id,
            requirement_title=db_req.requirement_title,
            priority=db_req.priority,
            business_domain=db_req.business_domain,
            attachments=db_req.attachments,
            feature_mapping=db_req.feature_mapping,
            jira_issue_key=db_req.jira_issue_key,
            jira_issue_url=db_req.jira_issue_url,
            jira_sync_status=db_req.jira_sync_status,
            jira_last_synced_at=db_req.jira_last_synced_at,
            release_id=db_req.release_id
        )

    def save_requirement(
        self,
        requirement: Requirement,
        priority: str | None = None,
        business_domain: str | None = None,
        attachments: list[str] | None = None
    ) -> None:
        session = self.session
        stmt = select(RequirementDB).where(RequirementDB.id == requirement.id, RequirementDB.deleted_at.is_(None))
        db_req = session.scalar(stmt)
        if not db_req:
            db_req = RequirementDB(
                id=requirement.id,
                title=requirement.title,
                description=requirement.description,
                source=requirement.source.value,
                uploaded_at=requirement.uploaded_at,
                original_filename=requirement.original_filename,
                requirement_id=requirement.requirement_id,
                requirement_title=requirement.requirement_title,
                priority=priority or requirement.priority or "medium",
                business_domain=business_domain or requirement.business_domain or "general",
                attachments=attachments if attachments is not None else (requirement.attachments or []),
                feature_mapping=requirement.feature_mapping,
                jira_issue_key=requirement.jira_issue_key,
                jira_issue_url=requirement.jira_issue_url,
                jira_sync_status=requirement.jira_sync_status,
                jira_last_synced_at=requirement.jira_last_synced_at,
                release_id=requirement.release_id
            )
            session.add(db_req)
        else:
            db_req.title = requirement.title
            db_req.description = requirement.description
            db_req.source = requirement.source.value
            db_req.uploaded_at = requirement.uploaded_at
            db_req.original_filename = requirement.original_filename
            db_req.requirement_id = requirement.requirement_id
            db_req.requirement_title = requirement.requirement_title
            db_req.feature_mapping = requirement.feature_mapping
            db_req.jira_issue_key = requirement.jira_issue_key
            db_req.jira_issue_url = requirement.jira_issue_url
            db_req.jira_sync_status = requirement.jira_sync_status
            db_req.jira_last_synced_at = requirement.jira_last_synced_at
            db_req.release_id = requirement.release_id
            if priority is not None:
                db_req.priority = priority
            if business_domain is not None:
                db_req.business_domain = business_domain
            if attachments is not None:
                db_req.attachments = attachments

    def get_scenarios_for_project(self, project_id: UUID) -> list[Scenario]:
        session = self.session
        stmt = (
            select(ScenarioDB)
            .join(RequirementDB, ScenarioDB.requirement_id == RequirementDB.id)
            .where(RequirementDB.project_id == project_id, ScenarioDB.is_deleted.is_(False), RequirementDB.is_deleted.is_(False))
        )
        db_scs = session.scalars(stmt).all()
        return [Scenario.model_validate(s, from_attributes=True) for s in db_scs]

    def get_test_cases_for_project(self, project_id: UUID) -> list[TestCase]:
        session = self.session
        stmt = (
            select(TestCaseDB)
            .join(ScenarioDB, TestCaseDB.scenario_id == ScenarioDB.id)
            .join(RequirementDB, ScenarioDB.requirement_id == RequirementDB.id)
            .where(RequirementDB.project_id == project_id, TestCaseDB.is_deleted.is_(False), ScenarioDB.is_deleted.is_(False), RequirementDB.is_deleted.is_(False))
        )
        db_tcs = session.scalars(stmt).all()
        return [TestCase.model_validate(tc, from_attributes=True) for tc in db_tcs]

    def get_scenarios(self, requirement_id: UUID, include_deleted: bool = False) -> list[Scenario]:
        session = self.session
        stmt = select(ScenarioDB).where(ScenarioDB.requirement_id == requirement_id)
        if not include_deleted:
            stmt = stmt.where(ScenarioDB.is_deleted.is_(False))
        db_scenarios = session.scalars(stmt).all()
        return [Scenario.model_validate(s, from_attributes=True) for s in db_scenarios]

    def save_scenarios(self, scenarios: list[Scenario]) -> None:
        session = self.session
        for s in scenarios:
            stmt = select(ScenarioDB).where(ScenarioDB.id == s.id)
            db_sc = session.scalar(stmt)
            if not db_sc:
                db_sc = ScenarioDB(
                    id=s.id,
                    requirement_id=s.requirement_id,
                    scenario_name=s.scenario_name,
                    description=s.description,
                    priority=s.priority.value,
                    confidence=s.confidence,
                    approved=s.approved,
                    reviewer=s.reviewer,
                    approved_at=s.approved_at,
                    generated_at=s.generated_at,
                    jira_issue_key=s.jira_issue_key,
                    jira_issue_url=s.jira_issue_url,
                    jira_sync_status=s.jira_sync_status,
                    jira_last_synced_at=s.jira_last_synced_at
                )
                session.add(db_sc)
            else:
                db_sc.scenario_name = s.scenario_name
                db_sc.description = s.description
                db_sc.priority = s.priority.value
                db_sc.confidence = s.confidence
                db_sc.approved = s.approved
                db_sc.reviewer = s.reviewer
                db_sc.approved_at = s.approved_at
                db_sc.generated_at = s.generated_at
                db_sc.jira_issue_key = s.jira_issue_key
                db_sc.jira_issue_url = s.jira_issue_url
                db_sc.jira_sync_status = s.jira_sync_status
                db_sc.jira_last_synced_at = s.jira_last_synced_at
                db_sc.is_deleted = False
        self._flush_or_commit()

    def update_scenario(self, scenario: Scenario) -> Scenario | None:
        session = self.session
        stmt = select(ScenarioDB).where(ScenarioDB.id == scenario.id, ScenarioDB.is_deleted.is_(False))
        db_sc = session.scalar(stmt)
        if not db_sc:
            return None
        db_sc.scenario_name = scenario.scenario_name
        db_sc.description = scenario.description
        db_sc.priority = scenario.priority.value
        db_sc.confidence = scenario.confidence
        db_sc.approved = scenario.approved
        db_sc.reviewer = scenario.reviewer
        db_sc.approved_at = scenario.approved_at
        db_sc.generated_at = scenario.generated_at
        db_sc.jira_issue_key = scenario.jira_issue_key
        db_sc.jira_issue_url = scenario.jira_issue_url
        db_sc.jira_sync_status = scenario.jira_sync_status
        db_sc.jira_last_synced_at = scenario.jira_last_synced_at
        self._flush_or_commit()
        return scenario

    def delete_scenario(self, scenario_id: UUID, deleted_by: UUID | None = None) -> bool:
        session = self.session
        now = datetime.now(timezone.utc)
        stmt = select(ScenarioDB).where(ScenarioDB.id == scenario_id, ScenarioDB.is_deleted.is_(False))
        db_sc = session.scalar(stmt)
        if not db_sc:
            return False
        db_sc.is_deleted = True
        db_sc.deleted_at = now
        db_sc.deleted_by = deleted_by
        for tc in db_sc.test_cases:
            tc.is_deleted = True
            tc.deleted_at = now
            tc.deleted_by = deleted_by
        self._flush_or_commit()
        return True

    def clear_scenarios_for_requirement(self, requirement_id: UUID) -> None:
        session = self.session
        now = datetime.now(timezone.utc)
        stmt = select(ScenarioDB).where(ScenarioDB.requirement_id == requirement_id, ScenarioDB.is_deleted.is_(False))
        db_scenarios = session.scalars(stmt).all()
        for s in db_scenarios:
            s.is_deleted = True
            s.deleted_at = now
            for tc in s.test_cases:
                tc.is_deleted = True
                tc.deleted_at = now
        self._flush_or_commit()

    def get_test_cases(self, scenario_id: UUID, include_deleted: bool = False) -> list[TestCase]:
        session = self.session
        stmt = select(TestCaseDB).where(TestCaseDB.scenario_id == scenario_id)
        if not include_deleted:
            stmt = stmt.where(TestCaseDB.is_deleted.is_(False))
        db_tcs = session.scalars(stmt).all()
        return [TestCase.model_validate(tc, from_attributes=True) for tc in db_tcs]

    def save_test_cases(self, test_cases: list[TestCase]) -> None:
        session = self.session
        for tc in test_cases:
            stmt = select(TestCaseDB).where(TestCaseDB.id == tc.id)
            db_tc = session.scalar(stmt)
            if not db_tc:
                db_tc = TestCaseDB(
                    id=tc.id,
                    scenario_id=tc.scenario_id,
                    title=tc.title,
                    preconditions=tc.preconditions,
                    steps=tc.steps,
                    expected_result=tc.expected_result,
                    priority=tc.priority.value,
                    status=tc.status.value,
                    confidence=tc.confidence,
                    evaluation_status=tc.evaluation_status.value,
                    evaluation_reason=tc.evaluation_reason,
                    playwright_script=tc.playwright_script,
                    reviewer=tc.reviewer,
                    approved_at=tc.approved_at,
                    generated_at=tc.generated_at,
                    is_frozen=tc.is_frozen,
                    jira_issue_key=tc.jira_issue_key,
                    jira_issue_url=tc.jira_issue_url,
                    jira_sync_status=tc.jira_sync_status,
                    jira_last_synced_at=tc.jira_last_synced_at
                )
                session.add(db_tc)
            else:
                db_tc.title = tc.title
                db_tc.preconditions = tc.preconditions
                db_tc.steps = tc.steps
                db_tc.expected_result = tc.expected_result
                db_tc.priority = tc.priority.value
                db_tc.status = tc.status.value
                db_tc.confidence = tc.confidence
                db_tc.evaluation_status = tc.evaluation_status.value
                db_tc.evaluation_reason = tc.evaluation_reason
                db_tc.playwright_script = tc.playwright_script
                db_tc.reviewer = tc.reviewer
                db_tc.approved_at = tc.approved_at
                db_tc.generated_at = tc.generated_at
                db_tc.is_frozen = tc.is_frozen
                db_tc.jira_issue_key = tc.jira_issue_key
                db_tc.jira_issue_url = tc.jira_issue_url
                db_tc.jira_sync_status = tc.jira_sync_status
                db_tc.jira_last_synced_at = tc.jira_last_synced_at
                db_tc.is_deleted = False
        self._flush_or_commit()

    def update_test_case(self, test_case: TestCase) -> TestCase | None:
        session = self.session
        stmt = select(TestCaseDB).where(TestCaseDB.id == test_case.id, TestCaseDB.is_deleted.is_(False))
        db_tc = session.scalar(stmt)
        if not db_tc:
            return None
        db_tc.title = test_case.title
        db_tc.preconditions = test_case.preconditions
        db_tc.steps = test_case.steps
        db_tc.expected_result = test_case.expected_result
        db_tc.priority = test_case.priority.value
        db_tc.status = test_case.status.value
        db_tc.confidence = test_case.confidence
        db_tc.evaluation_status = test_case.evaluation_status.value
        db_tc.evaluation_reason = test_case.evaluation_reason
        db_tc.playwright_script = test_case.playwright_script
        db_tc.reviewer = test_case.reviewer
        db_tc.approved_at = test_case.approved_at
        db_tc.generated_at = test_case.generated_at
        db_tc.is_frozen = test_case.is_frozen
        db_tc.jira_issue_key = test_case.jira_issue_key
        db_tc.jira_issue_url = test_case.jira_issue_url
        db_tc.jira_sync_status = test_case.jira_sync_status
        db_tc.jira_last_synced_at = test_case.jira_last_synced_at
        self._flush_or_commit()
        return test_case

    def get_test_case(self, test_case_id: UUID, include_deleted: bool = False) -> TestCase | None:
        session = self.session
        stmt = select(TestCaseDB).where(TestCaseDB.id == test_case_id)
        if not include_deleted:
            stmt = stmt.where(TestCaseDB.is_deleted.is_(False))
        db_tc = session.scalar(stmt)
        if not db_tc:
            return None
        return TestCase.model_validate(db_tc, from_attributes=True)

    def delete_test_case(self, test_case_id: UUID, deleted_by: UUID | None = None) -> bool:
        session = self.session
        stmt = select(TestCaseDB).where(TestCaseDB.id == test_case_id, TestCaseDB.is_deleted.is_(False))
        db_tc = session.scalar(stmt)
        if not db_tc:
            return False
        db_tc.is_deleted = True
        db_tc.deleted_at = datetime.now(timezone.utc)
        db_tc.deleted_by = deleted_by
        self._flush_or_commit()
        return True

    def delete_test_cases_for_scenario(self, scenario_id: UUID) -> None:
        session = self.session
        stmt = select(TestCaseDB).where(TestCaseDB.scenario_id == scenario_id, TestCaseDB.is_deleted.is_(False))
        db_tcs = session.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        for tc in db_tcs:
            tc.is_deleted = True
            tc.deleted_at = now
        self._flush_or_commit()

    def get_documents(self, project_id: UUID) -> list[Document]:
        session = self.session
        stmt = select(DocumentDB).where(DocumentDB.project_id == project_id)
        db_docs = session.scalars(stmt).all()
        return [
            Document(
                id=d.id,
                project_id=d.project_id,
                filename=d.filename,
                original_filename=d.original_filename,
                mime_type=d.mime_type,
                size=d.size,
                uploaded_at=d.uploaded_at,
                storage_path=d.storage_key,  # Expose storage_key as path for models
                embedding_status=d.embedding_status,
                vector_collection=d.vector_collection,
                metadata=d.metadata_json
            )
            for d in db_docs
        ]

    def get_document(self, project_id: UUID, document_id: UUID) -> Document | None:
        session = self.session
        stmt = select(DocumentDB).where(DocumentDB.project_id == project_id, DocumentDB.id == document_id)
        d = session.scalar(stmt)
        if not d:
            return None
        return Document(
            id=d.id,
            project_id=d.project_id,
            filename=d.filename,
            original_filename=d.original_filename,
            mime_type=d.mime_type,
            size=d.size,
            uploaded_at=d.uploaded_at,
            storage_path=d.storage_key,
            embedding_status=d.embedding_status,
            vector_collection=d.vector_collection,
            metadata=d.metadata_json
        )

    def save_document(self, document: Document) -> None:
        session = self.session
        stmt = select(DocumentDB).where(DocumentDB.id == document.id)
        db_doc = session.scalar(stmt)
        if not db_doc:
            db_doc = DocumentDB(
                id=document.id,
                project_id=document.project_id,
                filename=document.filename,
                original_filename=document.original_filename,
                mime_type=document.mime_type,
                size=document.size,
                uploaded_at=document.uploaded_at,
                storage_provider="local",
                storage_key=document.storage_path,
                embedding_status=document.embedding_status,
                vector_collection=document.vector_collection,
                metadata_json=document.metadata
            )
            session.add(db_doc)
        else:
            db_doc.filename = document.filename
            db_doc.original_filename = document.original_filename
            db_doc.mime_type = document.mime_type
            db_doc.size = document.size
            db_doc.uploaded_at = document.uploaded_at
            db_doc.storage_key = document.storage_path
            db_doc.embedding_status = document.embedding_status
            db_doc.vector_collection = document.vector_collection
            db_doc.metadata_json = document.metadata
        self._flush_or_commit()

    def delete_document(self, project_id: UUID, document_id: UUID) -> bool:
        session = self.session
        stmt = select(DocumentDB).where(DocumentDB.project_id == project_id, DocumentDB.id == document_id)
        db_doc = session.scalar(stmt)
        if not db_doc:
            return False
        session.delete(db_doc)
        self._flush_or_commit()
        return True

    def get_execution_results(self, project_id: UUID) -> list[ExecutionResult]:
        session = self.session
        stmt = select(ExecutionDB).where(ExecutionDB.project_id == project_id)
        db_execs = session.scalars(stmt).all()
        return [
            ExecutionResult(
                id=ex.id,
                test_case_id=ex.test_case_id,
                status=ex.status,
                duration_seconds=ex.duration_seconds,
                error_message=ex.error_message,
                screenshot_path=ex.screenshot_path,
                video_path=ex.video_path,
                trace_path=ex.trace_path,
                browser_version=ex.browser_version,
                executed_at=ex.executed_at,
                test_cycle_id=ex.test_cycle_id,
                failure_category=ex.failure_category,
                root_cause_summary=ex.root_cause_summary,
                suggest_retry=ex.suggest_retry,
                retest_pending_candidate=ex.retest_pending_candidate,
                jira_bug_id=ex.jira_bug_id,
                jira_bug_url=ex.jira_bug_url
            )
            for ex in db_execs
        ]

    def get_execution_result(self, project_id: UUID, execution_id: UUID) -> ExecutionResult | None:
        session = self.session
        stmt = select(ExecutionDB).where(ExecutionDB.project_id == project_id, ExecutionDB.id == execution_id)
        ex = session.scalar(stmt)
        if not ex:
            return None
        return ExecutionResult(
            id=ex.id,
            test_case_id=ex.test_case_id,
            status=ex.status,
            duration_seconds=ex.duration_seconds,
            error_message=ex.error_message,
            screenshot_path=ex.screenshot_path,
            video_path=ex.video_path,
            trace_path=ex.trace_path,
            browser_version=ex.browser_version,
            executed_at=ex.executed_at,
            test_cycle_id=ex.test_cycle_id,
            failure_category=ex.failure_category,
            root_cause_summary=ex.root_cause_summary,
            suggest_retry=ex.suggest_retry,
            retest_pending_candidate=ex.retest_pending_candidate,
            jira_bug_id=ex.jira_bug_id,
            jira_bug_url=ex.jira_bug_url
        )

    def save_execution_result(self, project_id: UUID, result: ExecutionResult) -> None:
        session = self.session
        stmt = select(ExecutionDB).where(ExecutionDB.id == result.id)
        db_ex = session.scalar(stmt)
        if not db_ex:
            db_ex = ExecutionDB(
                id=result.id,
                test_case_id=result.test_case_id,
                project_id=project_id,
                test_cycle_id=result.test_cycle_id,
                status=result.status.value,
                duration_seconds=result.duration_seconds,
                error_message=result.error_message,
                screenshot_path=result.screenshot_path,
                video_path=result.video_path,
                trace_path=result.trace_path,
                browser_version=result.browser_version,
                executed_at=result.executed_at,
                failure_category=result.failure_category,
                root_cause_summary=result.root_cause_summary,
                suggest_retry=result.suggest_retry,
                retest_pending_candidate=result.retest_pending_candidate,
                jira_bug_id=result.jira_bug_id,
                jira_bug_url=result.jira_bug_url
            )
            session.add(db_ex)
        else:
            db_ex.status = result.status.value
            db_ex.duration_seconds = result.duration_seconds
            db_ex.error_message = result.error_message
            db_ex.screenshot_path = result.screenshot_path
            db_ex.video_path = result.video_path
            db_ex.trace_path = result.trace_path
            db_ex.browser_version = result.browser_version
            db_ex.executed_at = result.executed_at
            db_ex.test_cycle_id = result.test_cycle_id
            db_ex.failure_category = result.failure_category
            db_ex.root_cause_summary = result.root_cause_summary
            db_ex.suggest_retry = result.suggest_retry
            db_ex.retest_pending_candidate = result.retest_pending_candidate
            db_ex.jira_bug_id = result.jira_bug_id
            db_ex.jira_bug_url = result.jira_bug_url
        self._flush_or_commit()

    def get_scenario_notes(self, scenario_id: UUID) -> list[str]:
        session = self.session
        stmt = select(ScenarioNoteDB).where(ScenarioNoteDB.scenario_id == scenario_id)
        db_notes = session.scalars(stmt).all()
        return [n.note for n in db_notes]

    def add_scenario_note(self, scenario_id: UUID, note: str) -> None:
        session = self.session
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        formatted = f"[{timestamp}] {note}"
        db_note = ScenarioNoteDB(scenario_id=scenario_id, note=formatted)
        session.add(db_note)
        self._flush_or_commit()

    def get_test_case_notes(self, test_case_id: UUID) -> list[str]:
        session = self.session
        stmt = select(TestCaseNoteDB).where(TestCaseNoteDB.test_case_id == test_case_id)
        db_notes = session.scalars(stmt).all()
        return [n.note for n in db_notes]

    def add_test_case_note(self, test_case_id: UUID, note: str) -> None:
        session = self.session
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        formatted = f"[{timestamp}] {note}"
        db_note = TestCaseNoteDB(test_case_id=test_case_id, note=formatted)
        session.add(db_note)
        self._flush_or_commit()

    def get_requirement(self, requirement_id: UUID) -> Requirement | None:
        session = self.session
        stmt = select(RequirementDB).where(RequirementDB.id == requirement_id, RequirementDB.deleted_at.is_(None))
        r = session.scalar(stmt)
        if not r:
            return None
        return Requirement(
            id=r.id,
            title=r.title,
            description=r.description,
            source=RequirementSource(r.source),
            uploaded_at=r.uploaded_at,
            original_filename=r.original_filename,
            requirement_id=r.requirement_id,
            requirement_title=r.requirement_title,
            priority=r.priority,
            business_domain=r.business_domain,
            attachments=r.attachments,
            release_id=r.release_id
        )

    def get_scenario(self, scenario_id: UUID) -> Scenario | None:
        session = self.session
        stmt = select(ScenarioDB).where(ScenarioDB.id == scenario_id, ScenarioDB.deleted_at.is_(None))
        s = session.scalar(stmt)
        if not s:
            return None
        return Scenario.model_validate(s, from_attributes=True)

    def get_report_by_execution(self, execution_id: UUID) -> dict | None:
        session = self.session
        stmt = select(ReportDB).where(ReportDB.execution_id == execution_id)
        rep = session.scalar(stmt)
        if not rep:
            return None
        return {
            "id": str(rep.id),
            "project_id": str(rep.project_id),
            "execution_id": str(rep.execution_id),
            "junit_path": rep.junit_path,
            "html_path": rep.html_path,
            "pdf_path": rep.pdf_path,
            "created_at": rep.created_at.isoformat()
        }

    def save_report(self, project_id: UUID, execution_id: UUID, report_payload: dict) -> dict:
        session = self.session
        stmt = select(ReportDB).where(ReportDB.execution_id == execution_id)
        db_rep = session.scalar(stmt)
        if not db_rep:
            db_rep = ReportDB(
                id=report_payload.get("id") or uuid4(),
                project_id=project_id,
                execution_id=execution_id,
                junit_path=report_payload.get("junit_path"),
                html_path=report_payload.get("html_path"),
                pdf_path=report_payload.get("pdf_path")
            )
            session.add(db_rep)
        else:
            db_rep.junit_path = report_payload.get("junit_path")
            db_rep.html_path = report_payload.get("html_path")
            db_rep.pdf_path = report_payload.get("pdf_path")
        self._flush_or_commit()
        return {
            "id": str(db_rep.id),
            "project_id": str(db_rep.project_id),
            "execution_id": str(db_rep.execution_id),
            "junit_path": db_rep.junit_path,
            "html_path": db_rep.html_path,
            "pdf_path": db_rep.pdf_path,
            "created_at": db_rep.created_at.isoformat()
        }

    def list_releases(self, project_id: UUID) -> list[Release]:
        session = self.session
        stmt = select(ReleaseDB).where(ReleaseDB.project_id == project_id)
        db_releases = session.scalars(stmt).all()
        return [
            Release(
                id=r.id,
                project_id=r.project_id,
                name=r.name,
                description=r.description,
                status=r.status,
                start_date=r.start_date,
                end_date=r.end_date
            )
            for r in db_releases
        ]

    def create_release(self, project_id: UUID, name: str, description: str | None = None, status: str = "Active", start_date: datetime | None = None, end_date: datetime | None = None) -> Release:
        from uuid import uuid4
        session = self.session
        db_release = ReleaseDB(
            id=uuid4(),
            project_id=project_id,
            name=name,
            description=description,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        session.add(db_release)
        self._flush_or_commit()
        return Release(
            id=db_release.id,
            project_id=db_release.project_id,
            name=db_release.name,
            description=db_release.description,
            status=db_release.status,
            start_date=db_release.start_date,
            end_date=db_release.end_date
        )

    def get_release(self, release_id: UUID) -> Release | None:
        session = self.session
        stmt = select(ReleaseDB).where(ReleaseDB.id == release_id)
        r = session.scalar(stmt)
        if not r:
            return None
        return Release(
            id=r.id,
            project_id=r.project_id,
            name=r.name,
            description=r.description,
            status=r.status,
            start_date=r.start_date,
            end_date=r.end_date
        )

    def list_test_cycles(self, release_id: UUID) -> list[TestCycle]:
        session = self.session
        stmt = select(TestCycleDB).where(TestCycleDB.release_id == release_id)
        db_cycles = session.scalars(stmt).all()
        return [
            TestCycle(
                id=c.id,
                release_id=c.release_id,
                name=c.name,
                description=c.description,
                status=c.status,
                created_at=c.created_at
            )
            for c in db_cycles
        ]

    def create_test_cycle(self, release_id: UUID, name: str, description: str | None = None, status: str = "Active") -> TestCycle:
        from uuid import uuid4
        session = self.session
        db_cycle = TestCycleDB(
            id=uuid4(),
            release_id=release_id,
            name=name,
            description=description,
            status=status
        )
        session.add(db_cycle)
        self._flush_or_commit()
        return TestCycle(
            id=db_cycle.id,
            release_id=db_cycle.release_id,
            name=db_cycle.name,
            description=db_cycle.description,
            status=db_cycle.status,
            created_at=db_cycle.created_at
        )

    def get_test_cycle(self, cycle_id: UUID) -> TestCycle | None:
        session = self.session
        stmt = select(TestCycleDB).where(TestCycleDB.id == cycle_id)
        c = session.scalar(stmt)
        if not c:
            return None
        return TestCycle(
            id=c.id,
            release_id=c.release_id,
            name=c.name,
            description=c.description,
            status=c.status,
            created_at=c.created_at
        )
