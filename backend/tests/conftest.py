"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import os
import sys
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 为 PostgreSQL 专属类型注册 SQLite 编译器，使全量建表 fixture（Base.metadata.create_all）
# 能在 SQLite 测试库上运行。仅影响 SQLite 测试库 DDL 编译，不触碰生产 PostgreSQL 模型。
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.ext.compiler import compiles


@compiles(INET, "sqlite")
def _compile_inet_for_sqlite(element, compiler, **kw):
    """SQLite 无 INET 类型，降级为 VARCHAR(45)（足以容纳 IPv6 地址）。"""
    return "VARCHAR(45)"


@pytest.fixture(scope="session")
def test_user_id():
    """Provide a test user ID"""
    return "test-user-12345"


@pytest.fixture(scope="function")
def temp_directory():
    """Create a temporary directory for each test"""
    temp_dir = tempfile.mkdtemp(prefix="markdown_editor_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def sample_markdown_content():
    """Provide sample markdown content for testing"""
    return """# Sample Document

## Introduction

This is a sample markdown document for testing purposes.

## Features

- Feature 1
- Feature 2
- Feature 3

## Code Example

```python
def hello_world():
    print("Hello, World!")
```

## Conclusion

This concludes the sample document.
"""


@pytest.fixture(scope="function")
def sample_config():
    """Provide sample editor configuration"""
    return {
        "theme": "dark",
        "fontSize": 14,
        "autoSaveInterval": 30,
        "previewTheme": "github",
        "showLineNumbers": True,
        "tabSize": 2,
        "useSpaces": True,
        "wordWrap": True,
        "showMinimap": False,
        "language": "zh-CN"
    }
