"""
Unit tests for File API endpoints
"""
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Set up test root before importing app
TEST_ROOT = tempfile.mkdtemp()
os.environ["MARKDOWN_EDITOR_ROOT"] = TEST_ROOT

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_files():
    """Set up test files before each test"""
    # Create test directory structure
    test_dir = Path(TEST_ROOT)
    
    # Clean up any existing files
    for item in test_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            import shutil
            shutil.rmtree(item)
    
    # Create test files
    (test_dir / "test.md").write_text("# Test\n\nThis is a test file.")
    (test_dir / "readme.md").write_text("# README\n\nProject readme.")
    
    # Create subdirectory with files
    subdir = test_dir / "docs"
    subdir.mkdir(exist_ok=True)
    (subdir / "guide.md").write_text("# Guide\n\nUser guide content.")
    
    yield
    
    # Cleanup is handled by next test setup


class TestGetDirectoryTree:
    """Tests for GET /api/files/tree"""
    
    def test_get_tree_success(self):
        """Test successful directory tree retrieval"""
        response = client.get("/api/files/tree")
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "directory"
        assert "children" in data
        
        # Should contain markdown files
        file_names = [c["name"] for c in data["children"] if c["type"] == "file"]
        assert "test.md" in file_names
        assert "readme.md" in file_names
    
    def test_get_tree_with_subdirectory(self):
        """Test that subdirectories with markdown files are included"""
        response = client.get("/api/files/tree")
        assert response.status_code == 200
        
        data = response.json()
        dir_names = [c["name"] for c in data["children"] if c["type"] == "directory"]
        assert "docs" in dir_names
    
    def test_get_tree_invalid_path(self):
        """Test error handling for path traversal attempt"""
        response = client.get("/api/files/tree?root=../../../etc")
        assert response.status_code == 400


class TestReadFile:
    """Tests for GET /api/files/read"""
    
    def test_read_file_success(self):
        """Test successful file read"""
        response = client.get("/api/files/read?path=test.md")
        assert response.status_code == 200
        
        data = response.json()
        assert data["path"] == "test.md"
        assert "# Test" in data["content"]
        assert data["size"] > 0
    
    def test_read_file_not_found(self):
        """Test error when file doesn't exist"""
        response = client.get("/api/files/read?path=nonexistent.md")
        assert response.status_code == 404
    
    def test_read_file_path_traversal(self):
        """Test error for path traversal attempt"""
        response = client.get("/api/files/read?path=../../../etc/passwd")
        assert response.status_code == 400


class TestSaveFile:
    """Tests for POST /api/files/save"""
    
    def test_save_file_success(self):
        """Test successful file save"""
        new_content = "# Updated Test\n\nNew content here."
        response = client.post("/api/files/save", json={
            "path": "test.md",
            "content": new_content
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # Verify content was saved
        read_response = client.get("/api/files/read?path=test.md")
        assert read_response.json()["content"] == new_content
    
    def test_save_file_not_found(self):
        """Test error when saving to non-existent file"""
        response = client.post("/api/files/save", json={
            "path": "nonexistent.md",
            "content": "content"
        })
        assert response.status_code == 404


class TestCreateFile:
    """Tests for POST /api/files/create"""
    
    def test_create_file_success(self):
        """Test successful file creation"""
        response = client.post("/api/files/create", json={
            "path": "new_file.md",
            "content": "# New File\n\nContent here."
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["path"] == "new_file.md"
        
        # Verify file exists
        read_response = client.get("/api/files/read?path=new_file.md")
        assert read_response.status_code == 200
    
    def test_create_file_already_exists(self):
        """Test error when file already exists"""
        response = client.post("/api/files/create", json={
            "path": "test.md",
            "content": "content"
        })
        assert response.status_code == 409


class TestDeleteFile:
    """Tests for DELETE /api/files/delete"""
    
    def test_delete_file_success(self):
        """Test successful file deletion"""
        # First create a file to delete
        client.post("/api/files/create", json={
            "path": "to_delete.md",
            "content": "delete me"
        })
        
        response = client.delete("/api/files/delete?path=to_delete.md")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # Verify file is gone
        read_response = client.get("/api/files/read?path=to_delete.md")
        assert read_response.status_code == 404
    
    def test_delete_file_not_found(self):
        """Test error when deleting non-existent file"""
        response = client.delete("/api/files/delete?path=nonexistent.md")
        assert response.status_code == 404


class TestRenameFile:
    """Tests for POST /api/files/rename"""
    
    def test_rename_file_success(self):
        """Test successful file rename"""
        # Create a file to rename
        client.post("/api/files/create", json={
            "path": "old_name.md",
            "content": "rename me"
        })
        
        response = client.post("/api/files/rename", json={
            "old_path": "old_name.md",
            "new_path": "new_name.md"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # Verify old file is gone
        old_response = client.get("/api/files/read?path=old_name.md")
        assert old_response.status_code == 404
        
        # Verify new file exists
        new_response = client.get("/api/files/read?path=new_name.md")
        assert new_response.status_code == 200
    
    def test_rename_file_not_found(self):
        """Test error when source file doesn't exist"""
        response = client.post("/api/files/rename", json={
            "old_path": "nonexistent.md",
            "new_path": "new.md"
        })
        assert response.status_code == 404


class TestDirectoryOperations:
    """Tests for directory API endpoints"""
    
    def test_create_directory_success(self):
        """Test successful directory creation"""
        response = client.post("/api/files/directory/create?path=new_dir")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    def test_create_directory_already_exists(self):
        """Test error when directory already exists"""
        response = client.post("/api/files/directory/create?path=docs")
        assert response.status_code == 409
    
    def test_delete_empty_directory(self):
        """Test deleting an empty directory"""
        # Create empty directory
        client.post("/api/files/directory/create?path=empty_dir")
        
        response = client.delete("/api/files/directory/delete?path=empty_dir")
        assert response.status_code == 200
    
    def test_delete_non_empty_directory_without_recursive(self):
        """Test error when deleting non-empty directory without recursive flag"""
        response = client.delete("/api/files/directory/delete?path=docs")
        assert response.status_code == 400
        assert "not empty" in response.json()["detail"].lower()
    
    def test_delete_non_empty_directory_with_recursive(self):
        """Test deleting non-empty directory with recursive flag"""
        # Create a directory with content
        client.post("/api/files/directory/create?path=to_delete_dir")
        client.post("/api/files/create", json={
            "path": "to_delete_dir/file.md",
            "content": "content"
        })
        
        response = client.delete("/api/files/directory/delete?path=to_delete_dir&recursive=true")
        assert response.status_code == 200
