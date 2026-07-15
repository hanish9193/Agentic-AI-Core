import yaml
import re
from pathlib import Path
from uuid import UUID
import json
import asyncio
import io
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timezone
import fitz
from fastapi import FastAPI, HTTPException, Body, status, BackgroundTasks, UploadFile, File, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config.settings import get_settings
from backend.services.project_service import ProjectService
from backend.services.workflow_service import WorkflowService
from backend.schemas.project_dto import ProjectCreate, ProjectResponse
from backend.schemas.requirement_dto import RequirementCreate, RequirementResponse
from backend.schemas.scenario_dto import ScenarioUpdate, ScenarioResponse
from backend.schemas.testcase_dto import TestCaseUpdate, TestCaseResponse, ScriptUpdatePayload
from backend.models.document import Document
from backend.models.execution_result import ExecutionResult
import backend.services.report_service

from sqlalchemy.orm import Session
from backend.dependencies.auth_dependencies import get_db, get_current_user, has_permission
from backend.services.auth_service import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from backend.services.audit_service import log_audit
from backend.database.db_models import UserDB, RoleDB, PermissionDB, RolePermissionDB, ProjectUserDB, RefreshTokenDB, AuditLogDB

app = FastAPI(
    title="AI Test Automation Platform API",
    description="Enterprise API backing the AI Test Automation Platform.",
    version="1.0.0"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    from backend.database.db import SessionLocal, Base, engine, provider
    import backend.database.db_models  # Ensure models are loaded and registered with Base metadata
    from backend.database.db_seeder import seed_database
    if provider == "json":
        Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

# Initialize application services
project_service = ProjectService()
workflow_service = WorkflowService()


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    line_of_business: str | None = None
    framework: str | None = None
    jira_project_key: str | None = None


@app.get("/api/v1/projects", response_model=list[ProjectResponse])
def list_projects():
    projects = project_service.list_projects()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            line_of_business=p.line_of_business,
            framework=getattr(p, "framework", "playwright"),
            created_at=p.created_at,
            requirements=p.requirements,
            jira_project_key=getattr(p, "jira_project_key", None)
        )
        for p in projects
    ]


@app.post("/api/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
    if not data.description.strip():
        raise HTTPException(status_code=400, detail="Project description cannot be empty")
    p = project_service.create_project(name=data.name, description=data.description, line_of_business=data.line_of_business, framework=data.framework)
    if data.jira_project_key:
        p.jira_project_key = data.jira_project_key
        p = project_service.repo.update_project(p)
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        line_of_business=p.line_of_business,
        framework=p.framework,
        created_at=p.created_at,
        requirements=p.requirements,
        jira_project_key=getattr(p, "jira_project_key", None)
    )


@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
def update_project_settings(project_id: UUID, data: ProjectUpdate):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.name is not None:
        p.name = data.name
    if data.description is not None:
        p.description = data.description
    if data.line_of_business is not None:
        p.line_of_business = data.line_of_business
    if data.framework is not None:
        p.framework = data.framework
    if data.jira_project_key is not None:
        p.jira_project_key = data.jira_project_key
    
    updated = project_service.repo.update_project(p)
    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        line_of_business=updated.line_of_business,
        framework=getattr(updated, "framework", "playwright"),
        created_at=updated.created_at,
        requirements=updated.requirements,
        jira_project_key=getattr(updated, "jira_project_key", None)
    )


@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: UUID):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        line_of_business=p.line_of_business,
        framework=getattr(p, "framework", "playwright"),
        created_at=p.created_at,
        requirements=p.requirements,
        jira_project_key=getattr(p, "jira_project_key", None)
    )


@app.get("/api/v1/projects/{project_id}/requirements", response_model=list[RequirementResponse])
def get_requirements(project_id: UUID):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    
    reqs = project_service.get_requirements(project_id)
    result = []
    for r in reqs:
        result.append(
            RequirementResponse(
                id=r.id,
                title=r.title,
                description=r.description,
                source=r.source,
                uploaded_at=r.uploaded_at,
                priority=r.priority,
                business_domain=r.business_domain,
                attachments=r.attachments,
                original_filename=r.original_filename,
                requirement_id=r.requirement_id,
                requirement_title=r.requirement_title,
                jira_issue_key=getattr(r, "jira_issue_key", None),
                jira_issue_url=getattr(r, "jira_issue_url", None),
                jira_sync_status=getattr(r, "jira_sync_status", None),
                jira_last_synced_at=getattr(r, "jira_last_synced_at", None)
            )
        )
    return result


@app.post("/api/v1/projects/{project_id}/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(project_id: UUID, data: RequirementCreate):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        r = project_service.create_requirement(
            project_id=project_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            business_domain=data.business_domain,
            attachments=[],
            original_filename=None,
            requirement_id="REQ-MANUAL",
            requirement_title=data.title
        )
        return RequirementResponse(
            id=r.id,
            title=r.title,
            description=r.description,
            source=r.source,
            uploaded_at=r.uploaded_at,
            priority=data.priority,
            business_domain=data.business_domain,
            attachments=[],
            original_filename=r.original_filename,
            requirement_id=r.requirement_id,
            requirement_title=r.requirement_title,
            jira_issue_key=getattr(r, "jira_issue_key", None),
            jira_issue_url=getattr(r, "jira_issue_url", None),
            jira_sync_status=getattr(r, "jira_sync_status", None),
            jira_last_synced_at=getattr(r, "jira_last_synced_at", None)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/v1/projects/{project_id}/requirements/import", response_model=list[RequirementResponse])
async def import_requirements(project_id: UUID, file: UploadFile = File(...)):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    file_bytes = await file.read()
    filename = file.filename

    try:
        parsed_blocks = project_service.parse_requirements_from_file(filename, file_bytes)
        
        finalized_requirements = []
        for block in parsed_blocks:
            # 1. Create a draft requirement in DB
            req = project_service.create_requirement(
                project_id=project_id,
                title=block["title"],
                description=block["description"],
                priority=block["priority"],
                business_domain=block["business_domain"],
                attachments=[filename],
                original_filename=filename,
                requirement_id=block["requirement_id"],
                requirement_title=block["requirement_title"]
            )
            
            # 2. Run the LangGraph INGEST workflow for LLM enrichment + optional Feature Inventory mapping
            final_req = workflow_service.ingest_requirement(project_id, req)
            finalized_requirements.append(final_req)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File import failed: {exc}")

    res = []
    for r in finalized_requirements:
        res.append(
            RequirementResponse(
                id=r.id,
                title=r.title,
                description=r.description,
                source=r.source,
                uploaded_at=r.uploaded_at,
                priority=r.priority,
                business_domain=r.business_domain,
                attachments=r.attachments,
                original_filename=r.original_filename,
                requirement_id=r.requirement_id,
                requirement_title=r.requirement_title,
                jira_issue_key=getattr(r, "jira_issue_key", None),
                jira_issue_url=getattr(r, "jira_issue_url", None),
                jira_sync_status=getattr(r, "jira_sync_status", None),
                jira_last_synced_at=getattr(r, "jira_last_synced_at", None)
            )
        )
    return res





@app.post("/api/v1/projects/{project_id}/requirements/{requirement_id}/generate-scenarios", response_model=list[ScenarioResponse])
def generate_scenarios(project_id: UUID, requirement_id: UUID, payload: dict = Body(...)):
    count = payload.get("count", 3)
    mode = payload.get("mode", "append")
    try:
        scenarios = workflow_service.generate_scenarios(project_id, requirement_id, count, mode)
        return [
            ScenarioResponse(
                id=s.id,
                requirement_id=s.requirement_id,
                scenario_name=s.scenario_name,
                description=s.description,
                priority=s.priority,
                confidence=s.confidence,
                approved=s.approved,
                rejected=s.rejected,
                generated_at=s.generated_at,
                reviewer=s.reviewer,
                approved_at=s.approved_at,
                jira_issue_key=getattr(s, "jira_issue_key", None),
                jira_issue_url=getattr(s, "jira_issue_url", None),
                jira_sync_status=getattr(s, "jira_sync_status", None),
                jira_last_synced_at=getattr(s, "jira_last_synced_at", None)
            )
            for s in scenarios
        ]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {exc}")


@app.post("/api/v1/projects/{project_id}/requirements/{requirement_id}/generate-backlog", response_model=list[ScenarioResponse])
def generate_backlog(project_id: UUID, requirement_id: UUID):
    try:
        scenarios = workflow_service.generate_backlog(project_id, requirement_id)
        return [
            ScenarioResponse(
                id=s.id,
                requirement_id=s.requirement_id,
                scenario_name=s.scenario_name,
                description=s.description,
                priority=s.priority,
                confidence=s.confidence,
                approved=s.approved,
                rejected=s.rejected,
                generated_at=s.generated_at,
                reviewer=s.reviewer,
                approved_at=s.approved_at,
                jira_issue_key=getattr(s, "jira_issue_key", None),
                jira_issue_url=getattr(s, "jira_issue_url", None),
                jira_sync_status=getattr(s, "jira_sync_status", None),
                jira_last_synced_at=getattr(s, "jira_last_synced_at", None)
            )
            for s in scenarios
        ]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backlog generation failed: {exc}")


@app.get("/api/v1/projects/{project_id}/scenarios", response_model=list[ScenarioResponse])
def get_scenarios(project_id: UUID):
    try:
        scenarios = project_service.get_scenarios_for_project(project_id)
        return [
            ScenarioResponse(
                id=s.id,
                requirement_id=s.requirement_id,
                scenario_name=s.scenario_name,
                description=s.description,
                priority=s.priority,
                confidence=s.confidence,
                approved=s.approved,
                rejected=s.rejected,
                generated_at=s.generated_at,
                reviewer=s.reviewer,
                approved_at=s.approved_at,
                jira_issue_key=getattr(s, "jira_issue_key", None),
                jira_issue_url=getattr(s, "jira_issue_url", None),
                jira_sync_status=getattr(s, "jira_sync_status", None),
                jira_last_synced_at=getattr(s, "jira_last_synced_at", None)
            )
            for s in scenarios
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/v1/projects/{project_id}/scenarios/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(project_id: UUID, scenario_id: UUID, data: ScenarioUpdate):
    updated = project_service.update_scenario(
        scenario_id=scenario_id,
        scenario_name=data.scenario_name,
        description=data.description,
        priority=data.priority,
        approved=data.approved,
        rejected=data.rejected
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioResponse(
        id=updated.id,
        requirement_id=updated.requirement_id,
        scenario_name=updated.scenario_name,
        description=updated.description,
        priority=updated.priority,
        confidence=updated.confidence,
        approved=updated.approved,
        rejected=updated.rejected,
        generated_at=updated.generated_at,
        reviewer=updated.reviewer,
        approved_at=updated.approved_at,
        jira_issue_key=getattr(updated, "jira_issue_key", None),
        jira_issue_url=getattr(updated, "jira_issue_url", None),
        jira_sync_status=getattr(updated, "jira_sync_status", None),
        jira_last_synced_at=getattr(updated, "jira_last_synced_at", None)
    )


@app.delete("/api/v1/projects/{project_id}/scenarios/{scenario_id}")
def delete_scenario(project_id: UUID, scenario_id: UUID):
    success = project_service.delete_scenario(scenario_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"detail": "Scenario deleted successfully"}


@app.post("/api/v1/projects/{project_id}/scenarios/duplicate/{scenario_id}", response_model=ScenarioResponse)
def duplicate_scenario(project_id: UUID, scenario_id: UUID):
    duplicated = project_service.duplicate_scenario(scenario_id)
    if not duplicated:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioResponse(
        id=duplicated.id,
        requirement_id=duplicated.requirement_id,
        scenario_name=duplicated.scenario_name,
        description=duplicated.description,
        priority=duplicated.priority,
        confidence=duplicated.confidence,
        approved=duplicated.approved,
        rejected=duplicated.rejected,
        generated_at=duplicated.generated_at,
        reviewer=duplicated.reviewer,
        approved_at=duplicated.approved_at,
        jira_issue_key=getattr(duplicated, "jira_issue_key", None),
        jira_issue_url=getattr(duplicated, "jira_issue_url", None),
        jira_sync_status=getattr(duplicated, "jira_sync_status", None),
        jira_last_synced_at=getattr(duplicated, "jira_last_synced_at", None)
    )


@app.post("/api/v1/projects/{project_id}/requirements/{requirement_id}/generate-testcases", response_model=list[TestCaseResponse])
def generate_test_cases(project_id: UUID, requirement_id: UUID):
    try:
        test_cases = workflow_service.generate_test_cases(project_id, requirement_id)
        return [
            TestCaseResponse(
                id=tc.id,
                scenario_id=tc.scenario_id,
                title=tc.title,
                preconditions=tc.preconditions,
                steps=tc.steps,
                expected_result=tc.expected_result,
                priority=tc.priority,
                status=tc.status,
                confidence=tc.confidence,
                evaluation_status=tc.evaluation_status,
                evaluation_reason=tc.evaluation_reason,
                playwright_script=tc.playwright_script,
                generated_at=tc.generated_at,
                jira_issue_key=getattr(tc, "jira_issue_key", None),
                jira_issue_url=getattr(tc, "jira_issue_url", None),
                jira_sync_status=getattr(tc, "jira_sync_status", None),
                jira_last_synced_at=getattr(tc, "jira_last_synced_at", None)
            )
            for tc in test_cases
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Test case generation failed: {exc}")


@app.get("/api/v1/projects/{project_id}/testcases", response_model=list[TestCaseResponse])
def get_test_cases(project_id: UUID):
    try:
        test_cases = project_service.get_test_cases_for_project(project_id)
        return [
            TestCaseResponse(
                id=tc.id,
                scenario_id=tc.scenario_id,
                title=tc.title,
                preconditions=tc.preconditions,
                steps=tc.steps,
                expected_result=tc.expected_result,
                priority=tc.priority,
                status=tc.status,
                confidence=tc.confidence,
                evaluation_status=tc.evaluation_status,
                evaluation_reason=tc.evaluation_reason,
                playwright_script=tc.playwright_script,
                generated_at=tc.generated_at,
                jira_issue_key=getattr(tc, "jira_issue_key", None),
                jira_issue_url=getattr(tc, "jira_issue_url", None),
                jira_sync_status=getattr(tc, "jira_sync_status", None),
                jira_last_synced_at=getattr(tc, "jira_last_synced_at", None)
            )
            for tc in test_cases
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/v1/projects/{project_id}/testcases/{test_case_id}", response_model=TestCaseResponse)
def update_test_case(project_id: UUID, test_case_id: UUID, data: TestCaseUpdate):
    updated = project_service.update_test_case(
        test_case_id=test_case_id,
        title=data.title,
        preconditions=data.preconditions,
        steps=data.steps,
        expected_result=data.expected_result,
        priority=data.priority,
        status=data.status,
        confidence=data.confidence,
        evaluation_status=data.evaluation_status,
        evaluation_reason=data.evaluation_reason
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Test case not found")
    return TestCaseResponse(
        id=updated.id,
        scenario_id=updated.scenario_id,
        title=updated.title,
        preconditions=updated.preconditions,
        steps=updated.steps,
        expected_result=updated.expected_result,
        priority=updated.priority,
        status=updated.status,
        confidence=updated.confidence,
        evaluation_status=updated.evaluation_status,
        evaluation_reason=updated.evaluation_reason,
        playwright_script=updated.playwright_script,
        generated_at=updated.generated_at,
        jira_issue_key=getattr(updated, "jira_issue_key", None),
        jira_issue_url=getattr(updated, "jira_issue_url", None),
        jira_sync_status=getattr(updated, "jira_sync_status", None),
        jira_last_synced_at=getattr(updated, "jira_last_synced_at", None)
    )


@app.delete("/api/v1/projects/{project_id}/testcases/{test_case_id}")
def delete_test_case(project_id: UUID, test_case_id: UUID):
    success = project_service.delete_test_case(test_case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test case not found")
    return {"detail": "Test case deleted successfully"}


@app.put("/api/v1/projects/{project_id}/testcases/{test_case_id}/script", response_model=TestCaseResponse)
def update_test_case_script(project_id: UUID, test_case_id: UUID, payload: ScriptUpdatePayload):
    updated = project_service.update_test_case_script(test_case_id, payload.script)
    if not updated:
        raise HTTPException(status_code=404, detail="Test case not found")
    return TestCaseResponse(
        id=updated.id,
        scenario_id=updated.scenario_id,
        title=updated.title,
        preconditions=updated.preconditions,
        steps=updated.steps,
        expected_result=updated.expected_result,
        priority=updated.priority,
        status=updated.status,
        confidence=updated.confidence,
        evaluation_status=updated.evaluation_status,
        evaluation_reason=updated.evaluation_reason,
        playwright_script=updated.playwright_script,
        generated_at=updated.generated_at,
        jira_issue_key=getattr(updated, "jira_issue_key", None),
        jira_issue_url=getattr(updated, "jira_issue_url", None),
        jira_sync_status=getattr(updated, "jira_sync_status", None),
        jira_last_synced_at=getattr(updated, "jira_last_synced_at", None)
    )


@app.get("/api/v1/settings")
def read_settings():
    settings = get_settings()
    return {
        "llm": {
            "provider": settings.llm.provider,
            "model": settings.llm.model,
            "temperature": settings.llm.temperature,
            "api_key": settings.llm.api_key,
            "api_base": settings.llm.api_base,
        },
        "workflow": {
            "mode": settings.workflow.mode,
            "human_review_enabled": settings.workflow.human_review_enabled,
            "evaluation_threshold": settings.workflow.evaluation_threshold,
        },
        "browser": {
            "type": settings.browser.type,
            "headless": settings.browser.headless,
        },
        "rag": {
            "enabled": settings.rag.enabled,
            "vector_db_provider": settings.rag.vector_db_provider,
            "vector_db_path": settings.rag.vector_db_path,
            "ragflow_api_base": settings.rag.ragflow_api_base,
            "ragflow_api_key": settings.rag.ragflow_api_key,
            "ragflow_dataset_id": settings.rag.ragflow_dataset_id,
        },
        "generation": {
            "scenario_count": settings.generation.scenario_count,
        },
        "evaluation": {
            "duplicate_similarity_threshold": settings.evaluation.duplicate_similarity_threshold,
            "relevance_rejection_threshold": settings.evaluation.relevance_rejection_threshold,
        },
        "playwright": {
            "base_url": settings.playwright.base_url,
            "browser": settings.playwright.browser,
            "headless": settings.playwright.headless,
            "timeout": settings.playwright.timeout,
            "retries": settings.playwright.retries,
            "workspace_url": settings.playwright.workspace_url
        },
        "jira": {
            "base_url": settings.jira.base_url,
            "email": settings.jira.email,
            "api_token": settings.jira.api_token,
            "project_key": settings.jira.project_key,
            "default_issue_type": settings.jira.default_issue_type,
            "verify_ssl": settings.jira.verify_ssl,
            "resolved_statuses": settings.jira.resolved_statuses
        }
    }


@app.put("/api/v1/settings")
def save_settings(payload: dict = Body(...)):
    override_path = Path(__file__).parent / "config" / "override.yaml"
    try:
        overrides = {}
        for section in ["llm", "workflow", "browser", "rag", "generation", "evaluation", "playwright", "jira"]:
            if section in payload:
                overrides[section] = payload[section]

        with open(override_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(overrides, f)

        get_settings.cache_clear()
        
        return {"status": "success", "settings": read_settings()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {exc}")



@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: UUID, data: ProjectCreate):
    updated = project_service.update_project(project_id, name=data.name, description=data.description, line_of_business=data.line_of_business)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.jira_project_key is not None:
        updated.jira_project_key = data.jira_project_key
        updated = project_service.repo.update_project(updated)
    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        line_of_business=updated.line_of_business,
        framework=getattr(updated, "framework", "playwright"),
        created_at=updated.created_at,
        requirements=updated.requirements,
        jira_project_key=getattr(updated, "jira_project_key", None)
    )


@app.delete("/api/v1/projects/{project_id}")
def delete_project(project_id: UUID):
    success = project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"detail": "Project deleted successfully"}


@app.get("/api/v1/projects/{project_id}/documents", response_model=list[Document])
def get_documents(project_id: UUID):
    return project_service.get_documents(project_id)


def upload_to_ragflow_task(project_id: UUID, document_id: UUID, filename: str):
    from backend.services.rag_service import RAGFlowService
    from backend.repository.project_repository import get_project_repository
    import os
    from pathlib import Path
    
    rag_service = RAGFlowService()
    if not rag_service.is_active():
        return
        
    repo = get_project_repository()
    doc = repo.get_document(project_id, document_id)
    if not doc:
        return

    doc.embedding_status = "embedding"
    repo.save_document(doc)

    file_path = Path("data") / filename
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            f"Software Requirement Specification Document for {filename}\n"
            f"Requirement: The system shall support automated validation and Playwright visual verification.\n"
        )
        file_path.write_text(content, encoding="utf-8")

    res = rag_service.upload_document(file_path, filename)
    if res:
        doc.embedding_status = "completed"
        doc.metadata["ragflow_result"] = res
    else:
        doc.embedding_status = "failed"
        
    repo.save_document(doc)


def delete_from_ragflow_task(filename: str):
    from backend.services.rag_service import RAGFlowService
    rag_service = RAGFlowService()
    if rag_service.is_active():
        rag_service.delete_document(filename)


@app.post("/api/v1/projects/{project_id}/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(project_id: UUID, background_tasks: BackgroundTasks, payload: dict = Body(...)):
    filename = payload.get("filename")
    original_filename = payload.get("original_filename")
    mime_type = payload.get("mime_type", "text/plain")
    size = payload.get("size", 0)
    storage_path = payload.get("storage_path", "")
    metadata = payload.get("metadata", {})
    
    if not filename or not original_filename:
        raise HTTPException(status_code=400, detail="filename and original_filename are required")

    doc = project_service.create_document(
        project_id=project_id,
        filename=filename,
        original_filename=original_filename,
        mime_type=mime_type,
        size=size,
        storage_path=storage_path,
        metadata=metadata
    )
    
    background_tasks.add_task(upload_to_ragflow_task, project_id, doc.id, filename)
    return doc


@app.delete("/api/v1/projects/{project_id}/documents/{document_id}")
def delete_document(project_id: UUID, document_id: UUID, background_tasks: BackgroundTasks):
    doc = project_service.repo.get_document(project_id, document_id)
    success = project_service.delete_document(project_id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc:
        background_tasks.add_task(delete_from_ragflow_task, doc.filename)
        
    return {"detail": "Document deleted successfully"}


@app.post("/api/v1/projects/{project_id}/testcases/{test_case_id}/generate-script", response_model=TestCaseResponse)
def generate_playwright_script(project_id: UUID, test_case_id: UUID):
    try:
        updated_tc = workflow_service.generate_playwright_script(project_id, test_case_id)
        return TestCaseResponse(
            id=updated_tc.id,
            scenario_id=updated_tc.scenario_id,
            title=updated_tc.title,
            preconditions=updated_tc.preconditions,
            steps=updated_tc.steps,
            expected_result=updated_tc.expected_result,
            priority=updated_tc.priority,
            status=updated_tc.status,
            confidence=updated_tc.confidence,
            evaluation_status=updated_tc.evaluation_status,
            evaluation_reason=updated_tc.evaluation_reason,
            playwright_script=updated_tc.playwright_script,
            generated_at=updated_tc.generated_at,
            jira_issue_key=getattr(updated_tc, "jira_issue_key", None),
            jira_issue_url=getattr(updated_tc, "jira_issue_url", None),
            jira_sync_status=getattr(updated_tc, "jira_sync_status", None),
            jira_last_synced_at=getattr(updated_tc, "jira_last_synced_at", None)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {exc}")


@app.post("/api/v1/projects/{project_id}/testcases/{test_case_id}/execute")
def execute_test_case(project_id: UUID, test_case_id: UUID, background_tasks: BackgroundTasks):
    # Ensure test case exists before firing background run
    if not project_service.repo.get_test_case(test_case_id):
        raise HTTPException(status_code=404, detail="Test case not found")
        
    import uuid
    execution_id = uuid.uuid4()
    from backend.services.workflow_service import run_execution_and_stream
    background_tasks.add_task(run_execution_and_stream, workflow_service, project_id, test_case_id, execution_id)
    return {"status": "started", "execution_id": str(execution_id)}


@app.get("/api/v1/projects/{project_id}/testcases/{test_case_id}/execution-stream")
def get_execution_stream(project_id: UUID, test_case_id: UUID):
    tc_id_str = str(test_case_id)
    
    async def event_generator():
        # Clear out previous runs first so connections don't bleed
        from backend.services.workflow_service import active_execution_events
        yield f"data: {json.dumps({'status': 'Generating', 'timeline': 'Connecting...', 'log': 'Connecting to event log stream...'})}\n\n"
        
        last_index = 0
        while True:
            events = active_execution_events.get(tc_id_str, [])
            if last_index < len(events):
                for i in range(last_index, len(events)):
                    yield f"data: {json.dumps(events[i])}\n\n"
                    if events[i]["status"] == "Completed":
                        return
                last_index = len(events)
            
            await asyncio.sleep(0.4)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/projects/{project_id}/executions", response_model=list[ExecutionResult])
def list_execution_results(project_id: UUID):
    return project_service.get_execution_results(project_id)


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}")
def get_execution_detail(project_id: UUID, execution_id: UUID):
    result = project_service.get_execution_result(project_id, execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")

    tc_id_str = str(result.test_case_id)
    from backend.services.workflow_service import active_execution_events
    events = active_execution_events.get(tc_id_str, [])

    timeline = []
    logs = []
    
    if events:
        for ev in events:
            if ev.get("timeline"):
                timeline.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": ev["timeline"],
                    "type": "success" if ev["status"] == "Completed" else "info",
                    "details": ev.get("log", "")
                })
            if ev.get("log"):
                logs.append(ev["log"])
    else:
        timeline.append({
            "timestamp": result.executed_at.isoformat(),
            "event": "Completed",
            "type": "success" if result.status.value == "passed" else "error",
            "details": result.error_message or "All steps completed successfully."
        })
        logs.append(result.error_message or "Execution completed successfully.")

    # Query report from DB repo
    repo = project_service.repo
    report_data = repo.get_report_by_execution(execution_id) or {}

    return {
        "execution": {
            "id": str(result.id),
            "test_case_id": str(result.test_case_id),
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "error_message": result.error_message,
            "screenshot_path": result.screenshot_path,
            "video_path": result.video_path,
            "trace_path": result.trace_path,
            "executed_at": result.executed_at.isoformat()
        },
        "timeline": timeline,
        "logs": logs,
        "artifacts": {
            "screenshot": result.screenshot_path,
            "video": result.video_path,
            "trace": result.trace_path
        },
        "report": report_data
    }


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/screenshot")
def get_execution_screenshot(project_id: UUID, execution_id: UUID, path: str = None):
    if not path:
        result = project_service.get_execution_result(project_id, execution_id)
        if not result or not result.screenshot_path:
            raise HTTPException(status_code=404, detail="Screenshot not found")
        path = result.screenshot_path
    
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File does not exist")
    return FileResponse(file_path)


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/screenshot/{filename}")
@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/screenshots/{filename}")
def get_execution_screenshot_by_filename(project_id: UUID, execution_id: UUID, filename: str):
    file_path = Path("backend/playwrightt/public/artifacts") / str(execution_id) / "screenshots" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot does not exist")
    return FileResponse(file_path)


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/video")
def get_execution_video(project_id: UUID, execution_id: UUID, path: str = None):
    if not path:
        result = project_service.get_execution_result(project_id, execution_id)
        if not result or not result.video_path:
            raise HTTPException(status_code=404, detail="Video not found")
        path = result.video_path
        
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File does not exist")
    return FileResponse(file_path)


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/trace")
def get_execution_trace(project_id: UUID, execution_id: UUID, path: str = None):
    if not path:
        result = project_service.get_execution_result(project_id, execution_id)
        if not result or not result.trace_path:
            raise HTTPException(status_code=404, detail="Trace not found")
        path = result.trace_path
        
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File does not exist")
    return FileResponse(file_path, filename=file_path.name)


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/pdf")
def get_execution_pdf(project_id: UUID, execution_id: UUID):
    repo = project_service.repo
    report_info = repo.get_report_by_execution(execution_id)
    if report_info:
        pdf_path = report_info.get("pdf_path")
        if pdf_path and Path(pdf_path).exists():
            return FileResponse(pdf_path, filename=Path(pdf_path).name)
                
    # If not found, try to compile on the fly
    result = project_service.get_execution_result(project_id, execution_id)
    if result:
        from backend.services.report_service import ReportService
        try:
            r_info = ReportService().compile_reports(project_id, result)
            pdf_path = r_info.get("pdf_path")
            if pdf_path and Path(pdf_path).exists():
                return FileResponse(pdf_path, filename=Path(pdf_path).name)
        except Exception as compile_err:
            print(f"[On-the-fly PDF compile error]: {compile_err}")
            
    raise HTTPException(status_code=404, detail="PDF report not found")


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/html")
def get_execution_html(project_id: UUID, execution_id: UUID):
    repo = project_service.repo
    report_info = repo.get_report_by_execution(execution_id)
    if report_info:
        html_path = report_info.get("html_path")
        if html_path and Path(html_path).exists():
            return FileResponse(html_path)
                
    # If not found, try to compile on the fly
    result = project_service.get_execution_result(project_id, execution_id)
    if result:
        from backend.services.report_service import ReportService
        try:
            r_info = ReportService().compile_reports(project_id, result)
            html_path = r_info.get("html_path")
            if html_path and Path(html_path).exists():
                return FileResponse(html_path)
        except Exception as compile_err:
            print(f"[On-the-fly HTML compile error]: {compile_err}")
            
    raise HTTPException(status_code=404, detail="HTML report not found")


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/junit")
def get_execution_junit(project_id: UUID, execution_id: UUID):
    repo = project_service.repo
    report_info = repo.get_report_by_execution(execution_id)
    if report_info:
        junit_path = report_info.get("junit_path")
        if junit_path and Path(junit_path).exists():
            return FileResponse(junit_path, filename=Path(junit_path).name)
    raise HTTPException(status_code=404, detail="JUnit XML report not found")


@app.get("/api/v1/projects/{project_id}/traces")
def get_activity_traces(project_id: UUID):
    # Return dynamic LLM usage logs and costs mapped to project history
    settings = get_settings()
    repo = project_service.repo
    # Calculate mock/dynamic trace values based on generated count
    requirements = repo.get_requirements(project_id)
    sc_count = 0
    tc_count = 0
    for req in requirements:
        scs = repo.get_scenarios(req.id)
        sc_count += len(scs)
        for sc in scs:
            tc_count += len(repo.get_test_cases(sc.id))
    
    # Standard pricing model for tokens
    input_tokens = sc_count * 850 + tc_count * 1200
    output_tokens = sc_count * 450 + tc_count * 800
    total_tokens = input_tokens + output_tokens
    estimated_cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 100

    return {
        "model": settings.llm.model,
        "provider": settings.llm.provider,
        "temperature": settings.llm.temperature,
        "total_calls": sc_count + tc_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 4),
        "traces": [
            {
                "agent": "Scenario Agent",
                "calls": sc_count,
                "latency_sec": round(sc_count * 1.45, 2),
                "tokens": sc_count * 1300,
                "cost": round(sc_count * 1300 * 0.000003, 4)
            },
            {
                "agent": "TestCase Agent & Evaluation Agent",
                "calls": tc_count * 2,
                "latency_sec": round(tc_count * 2.15, 2),
                "tokens": tc_count * 2000,
                "cost": round(tc_count * 2000 * 0.0000045, 4)
            }
        ]
    }


@app.get("/api/v1/scenarios/{scenario_id}/notes")
def get_scenario_notes(scenario_id: UUID):
    return project_service.get_scenario_notes(scenario_id)


@app.post("/api/v1/scenarios/{scenario_id}/notes")
def add_scenario_note(scenario_id: UUID, payload: dict = Body(...)):
    note = payload.get("note")
    if not note:
        raise HTTPException(status_code=400, detail="Note content is required")
    project_service.add_scenario_note(scenario_id, note)
    return {"status": "success"}


@app.get("/api/v1/testcases/{test_case_id}/notes")
def get_test_case_notes(test_case_id: UUID):
    return project_service.get_test_case_notes(test_case_id)


@app.post("/api/v1/testcases/{test_case_id}/notes")
def add_test_case_note(test_case_id: UUID, payload: dict = Body(...)):
    note = payload.get("note")
    if not note:
        raise HTTPException(status_code=400, detail="Note content is required")
    project_service.add_test_case_note(test_case_id, note)
    return {"status": "success"}


@app.get("/api/v1/projects/{project_id}/testcases/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(project_id: UUID, test_case_id: UUID):
    tc = project_service.get_test_case(test_case_id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    return TestCaseResponse(
        id=tc.id,
        scenario_id=tc.scenario_id,
        title=tc.title,
        preconditions=tc.preconditions,
        steps=tc.steps,
        expected_result=tc.expected_result,
        priority=tc.priority,
        status=tc.status,
        confidence=tc.confidence,
        evaluation_status=tc.evaluation_status,
        evaluation_reason=tc.evaluation_reason,
        playwright_script=tc.playwright_script,
        generated_at=tc.generated_at,
        jira_issue_key=getattr(tc, "jira_issue_key", None),
        jira_issue_url=getattr(tc, "jira_issue_url", None),
        jira_sync_status=getattr(tc, "jira_sync_status", None),
        jira_last_synced_at=getattr(tc, "jira_last_synced_at", None)
    )


@app.get("/api/v1/playwright/workspace")
def get_playwright_workspace(project_id: UUID, test_case_id: UUID):
    tc = project_service.get_test_case(test_case_id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    # Get scenario info
    scenario_info = None
    if tc.scenario_id:
        sc = project_service.repo.get_scenario(tc.scenario_id)
        if sc:
            scenario_info = {
                "id": str(sc.id),
                "scenario_name": sc.scenario_name,
                "description": sc.description
            }
            
    settings = get_settings()
    return {
        "project_id": str(project_id),
        "test_case_id": str(test_case_id),
        "playwright_script": tc.playwright_script,
        "base_url": settings.playwright.base_url,
        "browser": settings.playwright.browser,
        "is_frozen": tc.is_frozen or tc.evaluation_status == "approved",
        "scenario": scenario_info
    }


@app.put("/api/v1/playwright/freeze")
def freeze_playwright_script(payload: dict = Body(...)):
    test_case_id = payload.get("test_case_id")
    is_frozen = payload.get("is_frozen", True)
    if not test_case_id:
        raise HTTPException(status_code=400, detail="test_case_id is required")
    
    tc = project_service.get_test_case(UUID(test_case_id))
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    tc.is_frozen = is_frozen
    project_service.repo.update_test_case(tc)
    return {"status": "success", "is_frozen": tc.is_frozen}


@app.put("/api/v1/playwright/script")
def save_playwright_script(payload: dict = Body(...)):
    project_id = payload.get("project_id")
    test_case_id = payload.get("test_case_id")
    script = payload.get("script")
    if not project_id or not test_case_id or script is None:
        raise HTTPException(status_code=400, detail="project_id, test_case_id, and script are required")
    
    tc = project_service.get_test_case(UUID(test_case_id))
    if tc and (tc.is_frozen or tc.evaluation_status == "approved"):
        raise HTTPException(status_code=403, detail="Cannot modify script because it is frozen or approved")

    from uuid import UUID
    updated = project_service.update_test_case_script(UUID(test_case_id), script)
    if not updated:
        raise HTTPException(status_code=404, detail="Test case not found")
    return {"status": "success"}


@app.post("/api/v1/projects/{project_id}/executions/webhook")
def process_execution_webhook(project_id: UUID, payload: dict = Body(...)):
    from backend.services.execution_service import ExecutionService
    from backend.services.workflow_service import active_execution_events
    
    print(f"[Webhook DEBUG] Received payload: {payload}")
    
    event = payload.get("event")
    test_case_id_str = payload.get("test_case_id")
    execution_id_str = payload.get("execution_id")
    
    if not event:
        raise HTTPException(status_code=400, detail="event is required")
        
    test_case_key = test_case_id_str or execution_id_str or "draft-execution"
    events = active_execution_events.setdefault(test_case_key, [])
    
    if event == "started":
        events.clear()  # reset previous events
        events.append({
            "status": "Running",
            "timeline": "Browser Started",
            "log": "Next.js execution engine started..."
        })
    elif event == "updated":
        log_line = payload.get("log_line")
        timeline_event = payload.get("timeline_event")
        live_screenshot = payload.get("live_screenshot")
        
        events.append({
            "status": "Running",
            "timeline": timeline_event.get("event") if timeline_event else None,
            "log": log_line,
            "screenshot": live_screenshot
        })
    elif event == "completed":
        # Finalize execution in Python service layer
        exec_service = ExecutionService()
        result = exec_service.finalize_execution(project_id, payload)
        
        events.append({
            "status": "Completed" if result.status.value == "passed" else "Failed",
            "timeline": "Execution completed successfully" if result.status.value == "passed" else "Execution completed with error",
            "log": result.error_message or "All steps completed.",
            "screenshot": result.screenshot_path,
            "artifact": {
                "duration": result.duration_seconds,
                "status": result.status.value,
                "screenshot": result.screenshot_path,
                "video": result.video_path,
                "trace": result.trace_path
            }
        })
        
    return {"status": "success"}


@app.get("/api/v1/executions/{execution_id}")
def get_execution_result_agnostic(execution_id: UUID):
    raw = project_service.repo._read_raw()
    execs_raw = raw.get("execution_results", {})
    ex_id_str = str(execution_id)
    if ex_id_str in execs_raw:
        ex_data = execs_raw[ex_id_str]
        cleaned = dict(ex_data)
        return cleaned
    raise HTTPException(status_code=404, detail="Execution not found")


class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str

class UserPasswordReset(BaseModel):
    password: str

class UserStatusToggle(BaseModel):
    is_active: bool

class RoleCreate(BaseModel):
    name: str

class RolePermissionsUpdate(BaseModel):
    role_id: str
    permission_ids: list[str]

class ProjectUserAssign(BaseModel):
    user_id: str
    role_id: str

@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    db_token = RefreshTokenDB(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
        revoked=False
    )
    db.add(db_token)
    db.commit()
    
    log_audit(db, user.id, None, "LOGIN", "USER", {"email": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@app.post("/api/v1/auth/refresh")
def refresh_session(payload: RefreshRequest, db: Session = Depends(get_db)):
    db_token = db.query(RefreshTokenDB).filter(RefreshTokenDB.token == payload.refresh_token).first()
    if not db_token or db_token.revoked or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    user = db.query(UserDB).filter(UserDB.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token}

@app.post("/api/v1/auth/logout")
def logout(payload: RefreshRequest, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    db_token = db.query(RefreshTokenDB).filter(RefreshTokenDB.token == payload.refresh_token).first()
    if db_token:
        db_token.revoked = True
        db.commit()
    log_audit(db, user.id, None, "LOGOUT", "USER", {"email": user.email})
    return {"status": "success"}

@app.get("/api/v1/admin/users")
def list_users(
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Users", "view"))
):
    users = db.query(UserDB).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at
        }
        for u in users
    ]

@app.post("/api/v1/admin/users")
def create_user(
    payload: UserCreate,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Users", "create"))
):
    exists = db.query(UserDB).filter(UserDB.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="User with this email already exists")
        
    new_user = UserDB(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    
    log_audit(db, user.id, None, "CREATE", "USER", {"new_user_email": payload.email, "role": payload.role})
    return {"status": "success", "user_id": str(new_user.id)}

@app.put("/api/v1/admin/users/{user_id}/status")
def toggle_user_status(
    user_id: UUID,
    payload: UserStatusToggle,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Users", "edit"))
):
    target = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_status = target.is_active
    target.is_active = payload.is_active
    db.commit()
    
    log_audit(db, user.id, None, "UPDATE", "USER", {
        "user_email": target.email,
        "is_active": {"old": old_status, "new": payload.is_active}
    })
    return {"status": "success"}

@app.put("/api/v1/admin/users/{user_id}/password")
def reset_user_password(
    user_id: UUID,
    payload: UserPasswordReset,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Users", "edit"))
):
    target = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    target.password_hash = hash_password(payload.password)
    db.commit()
    
    log_audit(db, user.id, None, "UPDATE", "USER", {"user_email": target.email, "action": "password_reset"})
    return {"status": "success"}

@app.get("/api/v1/admin/roles")
def list_roles(
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Roles", "view"))
):
    roles = db.query(RoleDB).all()
    return [{"id": str(r.id), "name": r.name} for r in roles]

@app.post("/api/v1/admin/roles")
def create_role(
    payload: RoleCreate,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Roles", "create"))
):
    exists = db.query(RoleDB).filter(RoleDB.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Role name already exists")
        
    new_role = RoleDB(name=payload.name)
    db.add(new_role)
    db.commit()
    
    log_audit(db, user.id, None, "CREATE", "ROLE", {"role_name": payload.name})
    return {"status": "success", "role_id": str(new_role.id)}

@app.get("/api/v1/admin/permissions")
def get_permissions_matrix(
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Permissions", "view"))
):
    perms = db.query(PermissionDB).all()
    role_perms = db.query(RolePermissionDB).all()
    return {
        "permissions": [{"id": str(p.id), "module": p.module, "action": p.action} for p in perms],
        "role_permissions": [{"role_id": str(rp.role_id), "permission_id": str(rp.permission_id)} for rp in role_perms]
    }

@app.post("/api/v1/admin/permissions")
def update_role_permissions(
    payload: RolePermissionsUpdate,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Permissions", "edit"))
):
    role_uuid = UUID(payload.role_id)
    db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role_uuid).delete()
    for p_id in payload.permission_ids:
        rp = RolePermissionDB(role_id=role_uuid, permission_id=UUID(p_id))
        db.add(rp)
    db.commit()
    
    role = db.query(RoleDB).filter(RoleDB.id == role_uuid).first()
    log_audit(db, user.id, None, "UPDATE", "PERMISSION", {
        "role_name": role.name if role else str(role_uuid),
        "permission_count": len(payload.permission_ids)
    })
    return {"status": "success"}

@app.post("/api/v1/projects/{project_id}/users")
def assign_user_to_project(
    project_id: UUID,
    payload: ProjectUserAssign,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Users", "edit"))
):
    user_uuid = UUID(payload.user_id)
    role_uuid = UUID(payload.role_id)
    
    exists = db.query(ProjectUserDB).filter(
        ProjectUserDB.project_id == project_id,
        ProjectUserDB.user_id == user_uuid
    ).first()
    
    if exists:
        old_role_id = exists.role_id
        exists.role_id = role_uuid
        action_name = "UPDATE"
        field_changes = {"role_id": {"old": str(old_role_id), "new": str(role_uuid)}}
    else:
        mapping = ProjectUserDB(project_id=project_id, user_id=user_uuid, role_id=role_uuid)
        db.add(mapping)
        action_name = "CREATE"
        field_changes = {"user_id": str(user_uuid), "role_id": str(role_uuid)}
        
    db.commit()
    log_audit(db, user.id, project_id, action_name, "USER", field_changes)
    return {"status": "success"}

@app.get("/api/v1/projects/{project_id}/users")
def list_project_users(
    project_id: UUID,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Users", "view"))
):
    mappings = db.query(ProjectUserDB).filter(ProjectUserDB.project_id == project_id).all()
    results = []
    for m in mappings:
        u = db.query(UserDB).filter(UserDB.id == m.user_id).first()
        r = db.query(RoleDB).filter(RoleDB.id == m.role_id).first()
        if u and r:
            results.append({
                "user_id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role_id": str(r.id),
                "role_name": r.name
            })
    return results

@app.get("/api/v1/admin/audit-logs")
def get_audit_logs(
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorized: bool = Depends(has_permission("Settings", "view"))
):
    logs = db.query(AuditLogDB).order_by(AuditLogDB.timestamp.desc()).limit(100).all()
    results = []
    for l in logs:
        u = db.query(UserDB).filter(UserDB.id == l.user_id).first() if l.user_id else None
        results.append({
            "id": str(l.id),
            "user_email": u.email if u else "System",
            "project_id": str(l.project_id) if l.project_id else None,
            "action": l.action,
            "module": l.module,
            "field_changes": l.field_changes,
            "timestamp": l.timestamp
        })
    return results


@app.post("/api/v1/webhooks/jira")
def jira_webhook(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Receives JIRA webhook events when bugs are updated/resolved."""
    issue = payload.get("issue", {})
    key = issue.get("key")
    if not key:
        return {"status": "ignored", "reason": "No issue key in payload"}
        
    status_name = issue.get("fields", {}).get("status", {}).get("name")
    if not status_name:
        return {"status": "ignored", "reason": "No status name in payload"}
        
    settings = get_settings()
    resolved_statuses = settings.jira.resolved_statuses
    if status_name not in resolved_statuses:
        return {"status": "ignored", "reason": f"Status '{status_name}' is not in resolved list."}
        
    from backend.database.db_models import TestCaseDB
    from backend.database.db import provider
    
    updated_count = 0
    if provider in ["sql", "postgres"] or (provider == "json" and db):
        db_tcs = db.query(TestCaseDB).filter(TestCaseDB.jira_issue_key == key, TestCaseDB.is_deleted == False).all()
        for db_tc in db_tcs:
            db_tc.status = "retest_pending"
            log_audit(db, None, None, "JIRA_UPDATE", "TESTCASE", {"jira_issue_key": key, "status": "retest_pending"})
            updated_count += 1
        db.commit()
        
    return {"status": "success", "updated_count": updated_count}


@app.post("/api/v1/projects/{project_id}/requirements/{requirement_id}/sync-jira")
def sync_requirement_jira(project_id: UUID, requirement_id: UUID, user: UserDB = Depends(get_current_user)):
    """Manually synchronize approved scenarios to JIRA as Stories."""
    repo = get_project_repository()
    requirement = repo.get_requirement(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
        
    scenarios = repo.get_scenarios(requirement_id)
    
    from backend.graph.workflow import build_graph
    from backend.models.state import WorkflowState
    
    local_graph = build_graph()
    state = WorkflowState(requirement=requirement, generated_scenarios=scenarios)
    state.add_log("Triggering JIRA user story sync via service")
    
    config = {
        "configurable": {
            "operation": "sync_user_story",
            "user_id": str(user.id)
        }
    }
    raw_result = local_graph.invoke(state, config)
    final_state = WorkflowState(**raw_result)
    
    return {"status": "success", "logs": final_state.logs}


@app.post("/api/v1/projects/{project_id}/executions/{execution_id}/sync-bug")
def sync_execution_bug(project_id: UUID, execution_id: UUID, user: UserDB = Depends(get_current_user)):
    """Manually synchronize a failed test run to JIRA as a Bug defect."""
    repo = get_project_repository()
    ex = repo.get_execution_result(project_id, execution_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Execution result not found")
        
    tc = repo.get_test_case(ex.test_case_id)
    if not tc:
        raise HTTPException(status_code=404, detail="TestCase not found")
        
    from backend.graph.workflow import build_graph
    from backend.models.state import WorkflowState
    
    local_graph = build_graph()
    state = WorkflowState(execution_results=[ex])
    state.add_log("Triggering JIRA bug sync via service")
    
    config = {
        "configurable": {
            "operation": "sync_bug",
            "user_id": str(user.id)
        }
    }
    raw_result = local_graph.invoke(state, config)
    final_state = WorkflowState(**raw_result)
    
    return {"status": "success", "logs": final_state.logs}


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
