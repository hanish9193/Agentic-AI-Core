import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.repository.project_repository import JSONProjectRepository, get_project_repository
import backend.repository.project_repository as repo_module

TEST_STORE_PATH = Path(__file__).parent / "test_project_store.json"


@pytest.fixture(autouse=True)
def setup_test_db():
    # Clean up test JSON DB if it exists
    if TEST_STORE_PATH.exists():
        os.remove(TEST_STORE_PATH)
    
    # Point active project repository to our test DB file
    test_repo = JSONProjectRepository(file_path=TEST_STORE_PATH)
    repo_module._active_project_repo = test_repo
    
    yield
    
    # Clean up test JSON DB after test
    if TEST_STORE_PATH.exists():
        os.remove(TEST_STORE_PATH)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_and_list_projects(client):
    # Check initially empty
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json() == []

    # Create a project
    response = client.post("/api/v1/projects", json={"name": "Test Project", "description": "Desc"})
    assert response.status_code == 201
    proj = response.json()
    assert proj["name"] == "Test Project"
    assert proj["description"] == "Desc"
    assert "id" in proj

    # Check listed
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    projs = response.json()
    assert len(projs) == 1
    assert projs[0]["id"] == proj["id"]


def test_create_and_get_requirements(client):
    # Create project
    response = client.post("/api/v1/projects", json={"name": "Test Proj", "description": ""})
    proj_id = response.json()["id"]

    # Create requirement
    response = client.post(
        f"/api/v1/projects/{proj_id}/requirements",
        json={
            "title": "Req Title",
            "description": "Req Desc",
            "priority": "high",
            "business_domain": "finance"
        }
    )
    assert response.status_code == 201
    req = response.json()
    assert req["title"] == "Req Title"
    assert req["description"] == "Req Desc"

    # Get requirements
    response = client.get(f"/api/v1/projects/{proj_id}/requirements")
    assert response.status_code == 200
    reqs = response.json()
    assert len(reqs) == 1
    assert reqs[0]["title"] == "Req Title"
    assert reqs[0]["priority"] == "high"


def test_get_and_write_settings(client):
    # Get settings
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    cfg = response.json()
    assert "llm" in cfg
    assert "workflow" in cfg

    # Write settings
    response = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "provider": "ollama",
                "model": "llama3.1",
                "temperature": 0.5
            }
        }
    )
    assert response.status_code == 200
    updated_cfg = response.json()["settings"]
    assert updated_cfg["llm"]["provider"] == "ollama"
    assert updated_cfg["llm"]["temperature"] == 0.5

    # Cleanup settings override.yaml if created
    override_path = Path(__file__).parent.parent / "config" / "override.yaml"
    if override_path.exists():
        os.remove(override_path)


def test_update_and_delete_project(client):
    # Create project
    response = client.post("/api/v1/projects", json={"name": "Temp Project", "description": ""})
    proj_id = response.json()["id"]

    # Update project
    response = client.put(f"/api/v1/projects/{proj_id}", json={"name": "Updated Title", "description": "Updated Desc"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Updated Title"
    assert updated["description"] == "Updated Desc"

    # Delete project
    response = client.delete(f"/api/v1/projects/{proj_id}")
    assert response.status_code == 200
    assert response.json() == {"detail": "Project deleted successfully"}

    # Getting deleted project fails
    response = client.get(f"/api/v1/projects/{proj_id}")
    assert response.status_code == 404


def test_create_and_delete_documents(client):
    # Create project
    response = client.post("/api/v1/projects", json={"name": "Doc Project", "description": ""})
    proj_id = response.json()["id"]

    # Create document metadata
    response = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        json={
            "filename": "requirements.pdf",
            "original_filename": "Healthcare_v1.pdf",
            "mime_type": "application/pdf",
            "size": 150000,
            "storage_path": "/data/requirements.pdf"
        }
    )
    assert response.status_code == 201
    doc = response.json()
    assert doc["filename"] == "requirements.pdf"
    assert doc["embedding_status"] == "pending"

    # List documents
    response = client.get(f"/api/v1/projects/{proj_id}/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "requirements.pdf"

    # Delete document
    response = client.delete(f"/api/v1/projects/{proj_id}/documents/{doc['id']}")
    assert response.status_code == 200

    # Listed documents are empty now
    response = client.get(f"/api/v1/projects/{proj_id}/documents")
    assert response.json() == []


def test_get_activity_traces(client):
    # Create project
    response = client.post("/api/v1/projects", json={"name": "Trace Proj", "description": ""})
    proj_id = response.json()["id"]

    # Get traces
    response = client.get(f"/api/v1/projects/{proj_id}/traces")
    assert response.status_code == 200
    trace_data = response.json()
    assert "total_tokens" in trace_data
    assert "traces" in trace_data

