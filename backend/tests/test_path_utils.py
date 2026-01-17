"""
Unit tests for path utilities
"""
import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.path_utils import (
    validate_path,
    normalize_path,
    get_user_root_path,
    is_safe_path,
    join_user_path
)


class TestPathValidation:
    """Tests for path validation functions"""

    def test_validate_path_normal(self):
        """Test normal path validation"""
        assert validate_path("documents/file.md") == True
        assert validate_path("notes/subfolder/note.md") == True
        assert validate_path("file.md") == True

    def test_validate_path_traversal_attack(self):
        """Test path traversal attack prevention"""
        assert validate_path("../etc/passwd") == False
        assert validate_path("documents/../../../etc/passwd") == False
        assert validate_path("..\\windows\\system32") == False
        assert validate_path("documents/..\\..\\secret") == False

    def test_validate_path_empty(self):
        """Test empty path handling"""
        assert validate_path("") == True  # Empty path is valid (root)
        assert validate_path(".") == True

    def test_validate_path_special_chars(self):
        """Test paths with special characters"""
        assert validate_path("documents/my file.md") == True
        assert validate_path("notes/日本語.md") == True
        assert validate_path("docs/file-name_v2.md") == True


class TestPathNormalization:
    """Tests for path normalization"""

    def test_normalize_path_slashes(self):
        """Test slash normalization"""
        result = normalize_path("documents\\subfolder\\file.md")
        assert "\\" not in result or os.sep == "\\"

    def test_normalize_path_double_slashes(self):
        """Test double slash removal"""
        result = normalize_path("documents//subfolder//file.md")
        assert "//" not in result

    def test_normalize_path_trailing_slash(self):
        """Test trailing slash handling"""
        result = normalize_path("documents/")
        assert result == "documents" or result == "documents/"


class TestUserRootPath:
    """Tests for user root path generation"""

    def test_get_user_root_path(self):
        """Test user root path generation"""
        user_id = "test-user-123"
        root_path = get_user_root_path(user_id)
        assert user_id in root_path
        assert "markdown-files" in root_path.lower() or "users" in root_path.lower()

    def test_get_user_root_path_different_users(self):
        """Test that different users get different paths"""
        path1 = get_user_root_path("user1")
        path2 = get_user_root_path("user2")
        assert path1 != path2


class TestSafePath:
    """Tests for safe path checking"""

    def test_is_safe_path_within_root(self):
        """Test paths within root directory"""
        root = "/home/user/markdown-files"
        assert is_safe_path(root, f"{root}/documents/file.md") == True
        assert is_safe_path(root, f"{root}/notes/note.md") == True

    def test_is_safe_path_outside_root(self):
        """Test paths outside root directory"""
        root = "/home/user/markdown-files"
        assert is_safe_path(root, "/etc/passwd") == False
        assert is_safe_path(root, "/home/other-user/file.md") == False


class TestJoinUserPath:
    """Tests for joining user paths"""

    def test_join_user_path_simple(self):
        """Test simple path joining"""
        user_id = "test-user"
        relative_path = "documents/file.md"
        result = join_user_path(user_id, relative_path)
        assert user_id in result
        assert "documents" in result
        assert "file.md" in result

    def test_join_user_path_empty(self):
        """Test joining with empty relative path"""
        user_id = "test-user"
        result = join_user_path(user_id, "")
        assert user_id in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
