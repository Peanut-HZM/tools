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
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(INET, "sqlite")
def _compile_inet_for_sqlite(element, compiler, **kw):
    """SQLite 无 INET 类型，降级为 VARCHAR(45)（足以容纳 IPv6 地址）。"""
    return "VARCHAR(45)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
    """SQLite 无 JSONB 类型，降级为 JSON。

    背景：harness 引入 JSONB 列（如 conversations.metadata）后，任何导入
    app.models 包的测试在 SQLite 全量建表时都会编译失败，此处统一降级。
    """
    return "JSON"


@pytest.fixture(scope="session", autouse=True)
def _hermetic_master_key():
    """
    单元测试固定主密钥（key-in-DB 方案的测试逃生舱）。

    app_secrets 主密钥默认存放在数据库；单元测试使用 SQLite 内存库但
    encrypt/decrypt 走全局路径，若不固定密钥会触达真实数据库。
    通过 TOOLBOX_APP_SECRET_HEX 把密钥固定为确定性值，保证测试封闭。
    """
    os.environ["TOOLBOX_APP_SECRET_HEX"] = "ab" * 32
    yield
    os.environ.pop("TOOLBOX_APP_SECRET_HEX", None)


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
