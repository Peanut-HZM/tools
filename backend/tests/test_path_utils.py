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


class TestSensitivePathDetection:
    """Tests for sensitive path detection"""

    def test_sensitive_path_shadow(self):
        """Test /etc/shadow detection"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/etc/shadow') is True

    def test_sensitive_path_passwd(self):
        """Test /etc/passwd detection"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/etc/passwd') is True

    def test_sensitive_path_proc(self):
        """Test /proc/ detection"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/proc/123') is True
        assert is_sensitive_path('/proc/cpuinfo') is True

    def test_sensitive_path_sys(self):
        """Test /sys/ detection"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/sys/class') is True
        assert is_sensitive_path('/sys/kernel') is True

    def test_sensitive_path_dev(self):
        """Test /dev/ detection"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/dev/null') is True
        assert is_sensitive_path('/dev/sda') is True

    def test_sensitive_path_root(self):
        """Test /root/ detection"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/root/.ssh') is True

    def test_non_sensitive_path(self):
        """Test non-sensitive paths"""
        from app.utils.path_utils import is_sensitive_path
        assert is_sensitive_path('/home/user/docs') is False
        assert is_sensitive_path('/tmp/file.txt') is False
        assert is_sensitive_path('/var/log/syslog') is False


class TestValidateAnyPath:
    """Tests for validate_any_path function"""

    def test_validate_any_path_valid_absolute(self):
        """Test valid absolute path"""
        from app.utils.path_utils import validate_any_path
        is_valid, result = validate_any_path('/home/user/docs')
        assert is_valid is True
        assert '/home/user/docs' in result

    def test_validate_any_path_valid_relative(self):
        """Test valid relative path"""
        from app.utils.path_utils import validate_any_path
        is_valid, result = validate_any_path('documents/file.md')
        assert is_valid is True
        # Should return absolute path
        assert os.path.isabs(result)

    def test_validate_any_path_empty(self):
        """Test empty path"""
        from app.utils.path_utils import validate_any_path
        is_valid, error = validate_any_path('')
        assert is_valid is False
        assert '空' in error

    def test_validate_any_path_traversal(self):
        """Test path traversal prevention"""
        from app.utils.path_utils import validate_any_path
        is_valid, error = validate_any_path('../../etc/passwd')
        assert is_valid is False
        assert '遍历' in error

    def test_validate_any_path_sensitive(self):
        """Test sensitive path rejection"""
        from app.utils.path_utils import validate_any_path
        is_valid, error = validate_any_path('/etc/shadow')
        assert is_valid is False
        assert '敏感' in error

    def test_validate_any_path_sensitive_proc(self):
        """Test /proc path rejection"""
        from app.utils.path_utils import validate_any_path
        is_valid, error = validate_any_path('/proc/123')
        assert is_valid is False
        assert '敏感' in error

    def test_validate_any_path_returns_absolute(self):
        """Test that result is always absolute path"""
        from app.utils.path_utils import validate_any_path
        is_valid, result = validate_any_path('/home/user/file.md')
        assert is_valid is True
        assert os.path.isabs(result)
