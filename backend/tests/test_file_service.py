"""
Unit tests for file service
"""
import pytest
import os
import sys
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.markdown_file_service import MarkdownFileService


class TestMarkdownFileService:
    """Tests for MarkdownFileService"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def file_service(self, temp_dir, monkeypatch):
        """Create MarkdownFileService instance with temp directory"""
        user_id = "test-user-123"
        service = MarkdownFileService(user_id)
        # Override the root path to use temp directory
        service._root_path = temp_dir
        return service

    def test_get_root_path(self, file_service):
        """Test getting root path"""
        root_path = file_service.get_root_path()
        assert root_path is not None
        assert isinstance(root_path, str)

    def test_create_file(self, file_service, temp_dir):
        """Test file creation"""
        result = file_service.create_file("test.md", "# Test Content")
        assert result.success == True
        
        # Verify file exists
        file_path = os.path.join(temp_dir, "test.md")
        assert os.path.exists(file_path)

    def test_create_file_with_directory(self, file_service, temp_dir):
        """Test file creation in subdirectory"""
        result = file_service.create_file("docs/test.md", "# Test")
        assert result.success == True
        
        # Verify file and directory exist
        file_path = os.path.join(temp_dir, "docs", "test.md")
        assert os.path.exists(file_path)

    def test_read_file(self, file_service, temp_dir):
        """Test file reading"""
        # Create a test file
        content = "# Test Content\n\nThis is a test."
        file_path = os.path.join(temp_dir, "test.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Read the file
        result = file_service.read_file("test.md")
        assert result.content == content
        assert result.path == "test.md"

    def test_read_nonexistent_file(self, file_service):
        """Test reading non-existent file"""
        with pytest.raises(FileNotFoundError):
            file_service.read_file("nonexistent.md")

    def test_save_file(self, file_service, temp_dir):
        """Test file saving"""
        # Create initial file
        file_path = os.path.join(temp_dir, "test.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Initial content")
        
        # Save new content
        new_content = "# Updated Content"
        result = file_service.save_file("test.md", new_content)
        assert result.success == True
        
        # Verify content was updated
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == new_content

    def test_delete_file(self, file_service, temp_dir):
        """Test file deletion"""
        # Create a test file
        file_path = os.path.join(temp_dir, "test.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Test content")
        
        # Delete the file
        result = file_service.delete_file("test.md")
        assert result.success == True
        assert not os.path.exists(file_path)

    def test_rename_file(self, file_service, temp_dir):
        """Test file renaming"""
        # Create a test file
        old_path = os.path.join(temp_dir, "old.md")
        with open(old_path, "w", encoding="utf-8") as f:
            f.write("Test content")
        
        # Rename the file
        result = file_service.rename_file("old.md", "new.md")
        assert result.success == True
        
        # Verify old file doesn't exist and new file does
        assert not os.path.exists(old_path)
        new_path = os.path.join(temp_dir, "new.md")
        assert os.path.exists(new_path)

    def test_create_directory(self, file_service, temp_dir):
        """Test directory creation"""
        result = file_service.create_directory("new_folder")
        assert result.success == True
        
        dir_path = os.path.join(temp_dir, "new_folder")
        assert os.path.isdir(dir_path)

    def test_delete_empty_directory(self, file_service, temp_dir):
        """Test empty directory deletion"""
        # Create a directory
        dir_path = os.path.join(temp_dir, "empty_folder")
        os.makedirs(dir_path)
        
        # Delete the directory
        result = file_service.delete_directory("empty_folder")
        assert result.success == True
        assert not os.path.exists(dir_path)

    def test_delete_nonempty_directory_without_recursive(self, file_service, temp_dir):
        """Test non-empty directory deletion without recursive flag"""
        # Create a directory with a file
        dir_path = os.path.join(temp_dir, "nonempty_folder")
        os.makedirs(dir_path)
        with open(os.path.join(dir_path, "file.md"), "w") as f:
            f.write("content")
        
        # Try to delete without recursive flag
        result = file_service.delete_directory("nonempty_folder", recursive=False)
        assert result.success == False

    def test_delete_nonempty_directory_with_recursive(self, file_service, temp_dir):
        """Test non-empty directory deletion with recursive flag"""
        # Create a directory with a file
        dir_path = os.path.join(temp_dir, "nonempty_folder")
        os.makedirs(dir_path)
        with open(os.path.join(dir_path, "file.md"), "w") as f:
            f.write("content")
        
        # Delete with recursive flag
        result = file_service.delete_directory("nonempty_folder", recursive=True)
        assert result.success == True
        assert not os.path.exists(dir_path)

    def test_get_directory_tree(self, file_service, temp_dir):
        """Test directory tree retrieval"""
        # Create some files and directories
        os.makedirs(os.path.join(temp_dir, "docs"))
        with open(os.path.join(temp_dir, "readme.md"), "w") as f:
            f.write("# Readme")
        with open(os.path.join(temp_dir, "docs", "guide.md"), "w") as f:
            f.write("# Guide")
        
        # Get directory tree
        tree = file_service.get_directory_tree()
        assert tree is not None
        assert tree.type == "directory"


class TestPathTraversalPrevention:
    """Tests for path traversal attack prevention"""

    @pytest.fixture
    def file_service(self):
        return MarkdownFileService("test-user")

    def test_path_traversal_read(self, file_service):
        """Test path traversal prevention in read"""
        with pytest.raises(ValueError):
            file_service.read_file("../../../etc/passwd")

    def test_path_traversal_save(self, file_service):
        """Test path traversal prevention in save"""
        with pytest.raises(ValueError):
            file_service.save_file("../../../etc/passwd", "malicious content")

    def test_path_traversal_create(self, file_service):
        """Test path traversal prevention in create"""
        with pytest.raises(ValueError):
            file_service.create_file("../../../etc/malicious.md", "content")

    def test_path_traversal_delete(self, file_service):
        """Test path traversal prevention in delete"""
        with pytest.raises(ValueError):
            file_service.delete_file("../../../etc/passwd")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
