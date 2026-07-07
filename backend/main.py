import yaml
from pathlib import Path
from uuid import UUID
import json
import asyncio
from fastapi import FastAPI, HTTPException, Body, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config.settings import get_settings
from backend.services.project_service import ProjectService
from backend.services.workflow_service import WorkflowService
from backend.schemas.project_dto import ProjectCreate, ProjectResponse
from backend.schemas.requirement_dto import RequirementCreate, RequirementResponse
from backend.schemas.scenario_dto import ScenarioUpdate, ScenarioResponse
from backend.schemas.testcase_dto import TestCaseUpdate, TestCaseResponse
from backend.models.document import Document
from backend.models.execution_result import ExecutionResult


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

# Initialize application services
project_service = ProjectService()
workflow_service = WorkflowService()


@app.get("/api/v1/projects", response_model=list[ProjectResponse])
def list_projects():
    projects = project_service.list_projects()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            requirements=p.requirements
        )
        for p in projects
    ]


@app.post("/api/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate):
    p = project_service.create_project(name=data.name, description=data.description)
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        requirements=p.requirements
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
        created_at=p.created_at,
        requirements=p.requirements
    )


@app.get("/api/v1/projects/{project_id}/requirements", response_model=list[RequirementResponse])
def get_requirements(project_id: UUID):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    
    reqs = project_service.get_requirements(project_id)
    # The JSON repository stores extra metadata fields inside raw dict.
    # We retrieve them dynamically from the database to map to Response DTO.
    repo = project_service.repo
    raw = repo._read_raw()
    reqs_raw = raw.get("requirements", {})

    result = []
    for r in reqs:
        r_str = str(r.id)
        raw_metadata = reqs_raw.get(r_str, {})
        result.append(
            RequirementResponse(
                id=r.id,
                title=r.title,
                description=r.description,
                source=r.source,
                uploaded_at=r.uploaded_at,
                priority=raw_metadata.get("priority", "medium"),
                business_domain=raw_metadata.get("business_domain", "general"),
                attachments=raw_metadata.get("attachments", [])
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
            attachments=[]
        )
        return RequirementResponse(
            id=r.id,
            title=r.title,
            description=r.description,
            source=r.source,
            uploaded_at=r.uploaded_at,
            priority=data.priority,
            business_domain=data.business_domain,
            attachments=[]
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/v1/projects/{project_id}/requirements/{requirement_id}/generate-scenarios", response_model=list[ScenarioResponse])
def generate_scenarios(project_id: UUID, requirement_id: UUID, payload: dict = Body(...)):
    count = payload.get("count", 3)
    try:
        scenarios = workflow_service.generate_scenarios(project_id, requirement_id, count)
        return [
            ScenarioResponse(
                id=s.id,
                requirement_id=s.requirement_id,
                scenario_name=s.scenario_name,
                description=s.description,
                priority=s.priority,
                confidence=s.confidence,
                approved=s.approved,
                generated_at=s.generated_at
            )
            for s in scenarios
        ]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {exc}")


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
                generated_at=s.generated_at
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
        approved=data.approved
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
        generated_at=updated.generated_at
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
        generated_at=duplicated.generated_at
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
                generated_at=tc.generated_at
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
                generated_at=tc.generated_at
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
        generated_at=updated.generated_at
    )


@app.delete("/api/v1/projects/{project_id}/testcases/{test_case_id}")
def delete_test_case(project_id: UUID, test_case_id: UUID):
    success = project_service.delete_test_case(test_case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test case not found")
    return {"detail": "Test case deleted successfully"}


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
        },
        "generation": {
            "scenario_count": settings.generation.scenario_count,
        },
        "evaluation": {
            "duplicate_similarity_threshold": settings.evaluation.duplicate_similarity_threshold,
            "relevance_rejection_threshold": settings.evaluation.relevance_rejection_threshold,
        }
    }


@app.put("/api/v1/settings")
def write_settings(payload: dict = Body(...)):
    override_path = Path(__file__).parent / "config" / "override.yaml"
    try:
        # Standardize structure in overrides dictionary
        overrides = {}
        for section in ["llm", "workflow", "browser", "rag", "generation", "evaluation"]:
            if section in payload:
                overrides[section] = payload[section]

        # Write to override.yaml
        with open(override_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(overrides, f)

        # Clear settings LRU cache to force reloading next time get_settings() is called
        get_settings.cache_clear()
        
        return {"status": "success", "settings": read_settings()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {exc}")



@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: UUID, data: ProjectCreate):
    updated = project_service.update_project(project_id, name=data.name, description=data.description)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        created_at=updated.created_at,
        requirements=updated.requirements
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


@app.post("/api/v1/projects/{project_id}/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(project_id: UUID, payload: dict = Body(...)):
    filename = payload.get("filename")
    original_filename = payload.get("original_filename")
    mime_type = payload.get("mime_type", "text/plain")
    size = payload.get("size", 0)
    storage_path = payload.get("storage_path", "")
    metadata = payload.get("metadata", {})
    
    if not filename or not original_filename:
        raise HTTPException(status_code=400, detail="filename and original_filename are required")

    return project_service.create_document(
        project_id=project_id,
        filename=filename,
        original_filename=original_filename,
        mime_type=mime_type,
        size=size,
        storage_path=storage_path,
        metadata=metadata
    )


@app.delete("/api/v1/projects/{project_id}/documents/{document_id}")
def delete_document(project_id: UUID, document_id: UUID):
    success = project_service.delete_document(project_id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
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
            generated_at=updated_tc.generated_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {exc}")


@app.post("/api/v1/projects/{project_id}/testcases/{test_case_id}/execute")
def execute_test_case(project_id: UUID, test_case_id: UUID, background_tasks: BackgroundTasks):
    # Ensure test case exists before firing background run
    raw = project_service.repo._read_raw()
    if str(test_case_id) not in raw.get("test_cases", {}):
        raise HTTPException(status_code=404, detail="Test case not found")
        
    from backend.services.workflow_service import run_execution_and_stream
    background_tasks.add_task(run_execution_and_stream, workflow_service, project_id, test_case_id)
    return {"status": "started"}


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


@app.get("/api/v1/projects/{project_id}/traces")
def get_activity_traces(project_id: UUID):
    # Return dynamic LLM usage logs and costs mapped to project history
    settings = get_settings()
    repo = project_service.repo
    raw = repo._read_raw()
    
    # Calculate mock/dynamic trace values based on generated count
    sc_count = len([s for s in raw.get("scenarios", {}).values() if s.get("requirement_id") in raw.get("requirements", {})])
    tc_count = len(raw.get("test_cases", {}))
    
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


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
