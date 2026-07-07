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
import fitz
from fastapi import FastAPI, HTTPException, Body, status, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config.settings import get_settings
from backend.services.project_service import ProjectService
from backend.services.workflow_service import WorkflowService
from backend.schemas.project_dto import ProjectCreate, ProjectResponse
from backend.schemas.requirement_dto import RequirementCreate, RequirementResponse
from backend.schemas.scenario_dto import ScenarioUpdate, ScenarioResponse
from backend.schemas.testcase_dto import TestCaseUpdate, TestCaseResponse, ScriptUpdatePayload
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
            line_of_business=p.line_of_business,
            created_at=p.created_at,
            requirements=p.requirements
        )
        for p in projects
    ]


@app.post("/api/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate):
    p = project_service.create_project(name=data.name, description=data.description, line_of_business=data.line_of_business)
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        line_of_business=p.line_of_business,
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
        line_of_business=p.line_of_business,
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
                attachments=raw_metadata.get("attachments", []),
                original_filename=r.original_filename,
                requirement_id=r.requirement_id,
                requirement_title=r.requirement_title
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
            requirement_title=r.requirement_title
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def parse_requirements_from_text(project_id: UUID, text: str, filename: str):
    # Regex split to look for pattern blocks like REQ-001 or Requirement 1
    pattern = r'(REQ-\d+|Requirement\s+\d+|[A-Z]+-\d+):'
    parts = re.split(pattern, text)
    
    imported = []
    if len(parts) > 1:
        i = 1
        while i < len(parts):
            req_id = parts[i].strip()
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            description = content
            
            # Guess priority
            priority = "medium"
            if any(k in description.lower() for k in ["high", "critical", "urgent", "must"]):
                priority = "high"
            elif any(k in description.lower() for k in ["low", "minor", "nice to have"]):
                priority = "low"
                
            # Guess line of business / domain
            business_domain = "general"
            for k in ["banking", "finance", "auth", "login", "profile", "billing", "payment", "checkout", "search", "upload", "insurance", "retail", "healthcare"]:
                if k in description.lower():
                    business_domain = k.capitalize()
                    break
                    
            # Try to extract a clean requirement title from description
            req_title = "Requirement Block"
            title_match = re.search(r'Title\s*\n\s*([^\n]+)', description, re.IGNORECASE)
            if title_match:
                req_title = title_match.group(1).strip()
            else:
                first_line = description.split('\n')[0].strip()
                if first_line:
                    req_title = first_line[:50].strip()
                    
            title = f"{req_id}: {req_title}"
            
            req = project_service.create_requirement(
                project_id=project_id,
                title=title,
                description=description,
                priority=priority,
                business_domain=business_domain,
                attachments=[filename],
                original_filename=filename,
                requirement_id=req_id,
                requirement_title=req_title
            )
            imported.append(req)
            i += 2
    else:
        # Split by double newline (paragraph blocks)
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        for idx, block in enumerate(blocks):
            if len(block) < 25:
                continue
                
            req_id = f"REQ-{idx+1:03d}"
            priority = "medium"
            if any(k in block.lower() for k in ["high", "critical", "urgent"]):
                priority = "high"
            elif any(k in block.lower() for k in ["low", "minor"]):
                priority = "low"
                
            business_domain = "general"
            for k in ["banking", "finance", "auth", "login", "profile", "billing", "payment", "checkout", "search", "upload", "insurance", "retail", "healthcare"]:
                if k in block.lower():
                    business_domain = k.capitalize()
                    break
                    
            req_title = block[:50].strip() + "..."
            title = f"{req_id}: {req_title}"
            
            req = project_service.create_requirement(
                project_id=project_id,
                title=title,
                description=block,
                priority=priority,
                business_domain=business_domain,
                attachments=[filename],
                original_filename=filename,
                requirement_id=req_id,
                requirement_title=req_title
            )
            imported.append(req)
            
    if not imported:
        # Create a single default block
        req = project_service.create_requirement(
            project_id=project_id,
            title=filename,
            description=text or "Empty file content",
            priority="medium",
            business_domain="general",
            attachments=[filename],
            original_filename=filename,
            requirement_id="REQ-001",
            requirement_title=filename
        )
        imported.append(req)
        
    return imported


@app.post("/api/v1/projects/{project_id}/requirements/import", response_model=list[RequirementResponse])
async def import_requirements(project_id: UUID, file: UploadFile = File(...)):
    p = project_service.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    file_bytes = await file.read()
    filename = file.filename
    ext = Path(filename).suffix.lower()

    imported = []
    try:
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(file_bytes))
            cols = {col.lower().replace(" ", "").replace("_", ""): col for col in df.columns}
            
            id_col = cols.get("requirementid") or cols.get("id")
            desc_col = cols.get("requirement") or cols.get("description") or cols.get("title")
            priority_col = cols.get("priority")
            module_col = cols.get("module") or cols.get("businessdomain") or cols.get("domain")

            if not desc_col:
                desc_col = df.columns[0]

            for idx, row in df.iterrows():
                req_id_val = str(row[id_col]) if (id_col and id_col in df.columns) else f"REQ-{idx+1:03d}"
                desc_val = str(row[desc_col]) if (desc_col and desc_col in df.columns) else ""
                priority_val = str(row[priority_col]).lower() if (priority_col and priority_col in df.columns) else "medium"
                module_val = str(row[module_col]) if (module_col and module_col in df.columns) else "general"

                if not desc_val.strip() or pd.isna(row[desc_col]):
                    continue

                if priority_val not in ["low", "medium", "high"]:
                    priority_val = "medium"

                req = project_service.create_requirement(
                    project_id=project_id,
                    title=f"{req_id_val}: {desc_val[:50]}...",
                    description=desc_val,
                    priority=priority_val,
                    business_domain=module_val,
                    attachments=[filename],
                    original_filename=filename,
                    requirement_id=req_id_val,
                    requirement_title=desc_val[:50]
                )
                imported.append(req)
        elif ext == ".pdf":
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            imported = parse_requirements_from_text(project_id, text, filename)
        elif ext in [".docx", ".doc"]:
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
                    xml_content = docx_zip.read('word/document.xml')
                    root = ET.fromstring(xml_content)
                    
                    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    paragraphs = []
                    for para in root.findall('.//w:p', namespaces):
                        text_elems = para.findall('.//w:t', namespaces)
                        text = "".join([t.text for t in text_elems if t.text])
                        if text.strip():
                            paragraphs.append(text)
                    full_text = "\n\n".join(paragraphs)
            except Exception:
                full_text = "Failed to parse Word document XML structure."
            imported = parse_requirements_from_text(project_id, full_text, filename)
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
            imported = parse_requirements_from_text(project_id, text, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File import failed: {exc}")

    repo = project_service.repo
    raw_db = repo._read_raw()
    reqs_raw = raw_db.get("requirements", {})

    res = []
    for r in imported:
        r_str = str(r.id)
        raw_metadata = reqs_raw.get(r_str, {})
        res.append(
            RequirementResponse(
                id=r.id,
                title=r.title,
                description=r.description,
                source=r.source,
                uploaded_at=r.uploaded_at,
                priority=raw_metadata.get("priority", "medium"),
                business_domain=raw_metadata.get("business_domain", "general"),
                attachments=raw_metadata.get("attachments", []),
                original_filename=r.original_filename,
                requirement_id=r.requirement_id,
                requirement_title=r.requirement_title
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
        generated_at=updated.generated_at
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
            "retries": settings.playwright.retries
        }
    }


@app.put("/api/v1/settings")
def write_settings(payload: dict = Body(...)):
    override_path = Path(__file__).parent / "config" / "override.yaml"
    try:
        overrides = {}
        for section in ["llm", "workflow", "browser", "rag", "generation", "evaluation", "playwright"]:
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
    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        line_of_business=updated.line_of_business,
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
    raw = repo._read_raw()
    reports_raw = raw.get("reports", {})
    report_data = {}
    for r_id, r_info in reports_raw.items():
        if r_info.get("execution_id") == str(execution_id):
            report_data = r_info
            break

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
    raw = repo._read_raw()
    reports_raw = raw.get("reports", {})
    for r_id, r_info in reports_raw.items():
        if r_info.get("execution_id") == str(execution_id):
            pdf_path = r_info.get("pdf_path")
            if pdf_path and Path(pdf_path).exists():
                return FileResponse(pdf_path, filename=Path(pdf_path).name)
    raise HTTPException(status_code=404, detail="PDF report not found")


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/html")
def get_execution_html(project_id: UUID, execution_id: UUID):
    repo = project_service.repo
    raw = repo._read_raw()
    reports_raw = raw.get("reports", {})
    for r_id, r_info in reports_raw.items():
        if r_info.get("execution_id") == str(execution_id):
            html_path = r_info.get("html_path")
            if html_path and Path(html_path).exists():
                return FileResponse(html_path)
    raise HTTPException(status_code=404, detail="HTML report not found")


@app.get("/api/v1/projects/{project_id}/executions/{execution_id}/junit")
def get_execution_junit(project_id: UUID, execution_id: UUID):
    repo = project_service.repo
    raw = repo._read_raw()
    reports_raw = raw.get("reports", {})
    for r_id, r_info in reports_raw.items():
        if r_info.get("execution_id") == str(execution_id):
            junit_path = r_info.get("junit_path")
            if junit_path and Path(junit_path).exists():
                return FileResponse(junit_path, filename=Path(junit_path).name)
    raise HTTPException(status_code=404, detail="JUnit XML report not found")


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


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
