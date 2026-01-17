"""
Integration tests for API endpoints
"""
import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers by registering and logging in"""
    # Register a test user
    register_response = client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    if register_response.status_code == 200:
        token = register_response.json().get("token")
    else:
        # User might already exist, try login
        login_response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpassword123"
        })
        token = login_response.json().get("token")
    
    return {"Authorization": f"Bearer {token}"}


class TestAuthAPI:
    """Integration tests for authentication API"""

    def test_register_new_user(self, client):
        """Test user registration"""
        import uuid
        unique_username = f"testuser_{uuid.uuid4().hex[:8]}"
        
        response = client.post("/api/auth/register", json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == unique_username

    def test_register_duplicate_user(self, client):
        """Test duplicate user registration"""
        # First registration
        client.post("/api/auth/register", json={
            "username": "duplicate_user",
            "email": "duplicate@example.com",
            "password": "testpassword123"
        })
        
        # Second registration with same username
        response = client.post("/api/auth/register", json={
            "username": "duplicate_user",
            "email": "duplicate2@example.com",
            "password": "testpassword123"
        })
        
        assert response.status_code in [400, 409]

    def test_login_valid_credentials(self, client):
        """Test login with valid credentials"""
        import uuid
        unique_username = f"logintest_{uuid.uuid4().hex[:8]}"
        
        # Register first
        client.post("/api/auth/register", json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123"
        })
        
        # Login
        response = client.post("/api/auth/login", json={
            "username": unique_username,
            "password": "testpassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent_user",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401

    def test_get_current_user(self, client, auth_headers):
        """Test getting current user info"""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without auth"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401


class TestFileAPI:
    """Integration tests for file operations API"""

    def test_get_directory_tree(self, client, auth_headers):
        """Test getting directory tree"""
        response = client.get(
            "/api/markdown-editor/files/tree",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "type" in data

    def test_create_and_read_file(self, client, auth_headers):
        """Test creating and reading a file"""
        import uuid
        filename = f"test_{uuid.uuid4().hex[:8]}.md"
        content = "# Test File\n\nThis is test content."
        
        # Create file
        create_response = client.post(
            "/api/markdown-editor/files/create",
            json={"path": filename, "content": content},
            headers=auth_headers
        )
        
        assert create_response.status_code == 200
        
        # Read file
        read_response = client.get(
            f"/api/markdown-editor/files/read?path={filename}",
            headers=auth_headers
        )
        
        assert read_response.status_code == 200
        data = read_response.json()
        assert data["content"] == content

    def test_save_file(self, client, auth_headers):
        """Test saving file content"""
        import uuid
        filename = f"save_test_{uuid.uuid4().hex[:8]}.md"
        
        # Create file first
        client.post(
            "/api/markdown-editor/files/create",
            json={"path": filename, "content": "Initial content"},
            headers=auth_headers
        )
        
        # Save new content
        new_content = "# Updated Content"
        save_response = client.post(
            "/api/markdown-editor/files/save",
            json={"path": filename, "content": new_content},
            headers=auth_headers
        )
        
        assert save_response.status_code == 200
        
        # Verify content was updated
        read_response = client.get(
            f"/api/markdown-editor/files/read?path={filename}",
            headers=auth_headers
        )
        assert read_response.json()["content"] == new_content

    def test_delete_file(self, client, auth_headers):
        """Test deleting a file"""
        import uuid
        filename = f"delete_test_{uuid.uuid4().hex[:8]}.md"
        
        # Create file first
        client.post(
            "/api/markdown-editor/files/create",
            json={"path": filename, "content": "To be deleted"},
            headers=auth_headers
        )
        
        # Delete file
        delete_response = client.delete(
            f"/api/markdown-editor/files/delete?path={filename}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        
        # Verify file is deleted
        read_response = client.get(
            f"/api/markdown-editor/files/read?path={filename}",
            headers=auth_headers
        )
        assert read_response.status_code == 404

    def test_unauthorized_file_access(self, client):
        """Test file access without authentication"""
        response = client.get("/api/markdown-editor/files/tree")
        assert response.status_code == 401


class TestConfigAPI:
    """Integration tests for configuration API"""

    def test_get_config(self, client, auth_headers):
        """Test getting user configuration"""
        response = client.get(
            "/api/markdown-editor/config",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "theme" in data
        assert "fontSize" in data

    def test_save_config(self, client, auth_headers):
        """Test saving user configuration"""
        config = {
            "theme": "dark",
            "fontSize": 16,
            "autoSaveInterval": 60,
            "previewTheme": "github",
            "showLineNumbers": True,
            "tabSize": 4,
            "useSpaces": True,
            "wordWrap": True,
            "showMinimap": False,
            "language": "en-US"
        }
        
        response = client.post(
            "/api/markdown-editor/config",
            json=config,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify config was saved
        get_response = client.get(
            "/api/markdown-editor/config",
            headers=auth_headers
        )
        data = get_response.json()
        assert data["theme"] == "dark"
        assert data["fontSize"] == 16


class TestSearchAPI:
    """Integration tests for search API"""

    def test_search_files(self, client, auth_headers):
        """Test file name search"""
        response = client.get(
            "/api/markdown-editor/search/files?keyword=test",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_content(self, client, auth_headers):
        """Test content search"""
        response = client.get(
            "/api/markdown-editor/search/content?keyword=test",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
