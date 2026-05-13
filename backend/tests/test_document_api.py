import pytest
from fastapi.testclient import TestClient
from app.main import app
from dotenv import load_dotenv
import os

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
client = TestClient(app)
headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

def test_document_user_profile():
    response = client.get("/documents/user/profile", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "user_id" in response.json()["data"]

def test_document_user_limits():
    response = client.get("/documents/user/limits", params={"pages": 1, "mb": 0.1}, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "max_pages" in response.json()["data"]["limits"]

def test_document_projects_list_create():
    # List projects
    response = client.get("/documents/projects", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    # Create project
    create_data = {"name": "Test Project", "description": "Created by test", "instruction": "Test instructions"}
    response = client.post("/documents/projects", json=create_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "id" in response.json()["data"]
    project_id = response.json()["data"]["id"]
    return project_id

def test_document_project_crud():
    # Create project
    create_data = {"name": "CRUD Project", "description": "CRUD test", "instruction": "CRUD instructions"}
    response = client.post("/documents/projects", json=create_data, headers=headers)
    assert response.status_code == 200
    project_id = response.json()["data"]["id"]
    # Get project
    response = client.get(f"/documents/projects/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    # Update project
    update_data = {"name": "Updated Project", "description": "Updated desc", "instruction": "Updated instructions"}
    response = client.put(f"/documents/projects/{project_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    # Delete project
    response = client.delete(f"/documents/projects/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_document_upload_documents():
    # Create project
    create_data = {"name": "Upload Project", "description": "Upload test", "instruction": "Upload instructions"}
    response = client.post("/documents/projects", json=create_data, headers=headers)
    assert response.status_code == 200
    project_id = response.json()["data"]["id"]
    # Upload a dummy file (PNG)
    file_content = b"\x89PNG\r\n\x1a\n" + b"0" * 100  # Minimal PNG header + dummy data
    files = [("files", ("test.png", file_content, "image/png"))]
    response = client.post(f"/documents/projects/{project_id}/documents/upload", headers=headers, files=files)
    assert response.status_code == 200
    assert response.json()["success"] is True
