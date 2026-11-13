"""path_utils 文件类型工具测试

重点覆盖「无扩展名但内容确定是文本」的知名配置文件识别逻辑：

- `xa-higress-config` / `xa-higress-config-pd(1)` 这类文件没有扩展名，
  靠扩展名判断会落到 'other'，前端无法路由到编辑器（显示「不支持的文件类型」）。
- 修复后应被识别为 'text'，同时**不影响**已有扩展名文件的判定。
"""
import os
import sys

import pytest

# 让测试能导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.path_utils import (  # noqa: E402
    get_effective_file_type,
    get_extension,
    get_file_type,
    get_file_type_for_extensionless,
)


class TestGetFileType:
    """原有按扩展名判定的行为不能被破坏"""

    def test_known_extensions(self):
        assert get_file_type("AGENTS.md") == "markdown"
        assert get_file_type("page.html") == "html"
        assert get_file_type("notes.txt") == "text"
        assert get_file_type("install.sh") == "code"
        assert get_file_type("pic.png") == "image"
        # FILE_TYPE_MAP 未覆盖 pdf / xlsx → 'other'（既有行为，不在本次改动范围）
        assert get_file_type("doc.pdf") == "other"
        assert get_file_type("data.csv") == "text"

    def test_extensionless_returns_other(self):
        """无扩展名文件在原逻辑下是 'other'（这正是需要兜底的原因）"""
        assert get_file_type("xa-higress-config") == "other"
        assert get_file_type("random-file") == "other"


class TestGetFileTypeForExtensionless:
    """无扩展名知名配置文件的语言识别"""

    def test_higress_config(self):
        assert get_file_type_for_extensionless("xa-higress-config") == "yaml"

    def test_higress_config_with_copy_suffix(self):
        """带副本后缀的文件同样命中（-pd(1) / -copy 等）"""
        assert get_file_type_for_extensionless("xa-higress-config-pd(1)") == "yaml"
        assert get_file_type_for_extensionless("xa-higress-config-copy") == "yaml"
        assert get_file_type_for_extensionless("xa-higress-config (2)") == "yaml"

    def test_plain_config_and_kubeconfig(self):
        assert get_file_type_for_extensionless("config") == "yaml"
        assert get_file_type_for_extensionless("kubeconfig") == "yaml"

    def test_path_is_stripped(self):
        """传入完整路径时只按文件名判断"""
        assert (
            get_file_type_for_extensionless("/Users/x/peanut/glodon/xa-higress-config")
            == "yaml"
        )

    def test_files_with_extension_are_ignored(self):
        """有扩展名的文件不走这条逻辑（由 get_file_type 负责）"""
        assert get_file_type_for_extensionless("AGENTS.md") == ""
        assert get_file_type_for_extensionless("install.sh") == ""
        assert get_file_type_for_extensionless("photo.png") == ""

    def test_unknown_extensionless_returns_empty(self):
        """未知名字不误判为文本"""
        assert get_file_type_for_extensionless("random-file") == ""
        assert get_file_type_for_extensionless("photo") == ""


class TestGetEffectiveFileType:
    """文件树 / 列表使用的有效类型判定"""

    def test_extensionless_known_config_becomes_text(self):
        assert get_effective_file_type("xa-higress-config") == "text"
        assert get_effective_file_type("xa-higress-config-pd(1)") == "text"

    def test_existing_types_are_unchanged(self):
        """已有扩展名的文件判定完全不变"""
        for name, expected in [
            ("AGENTS.md", "markdown"),
            ("page.html", "html"),
            ("notes.txt", "text"),
            ("install.sh", "code"),
            ("pic.png", "image"),
            ("data.csv", "text"),
            ("doc.pdf", "other"),  # pdf 不在 FILE_TYPE_MAP 中（既有行为）
            ("data.xlsx", "other"),  # xlsx 不在 FILE_TYPE_MAP 中
            ("dgpub-dev-ns-admin.kubeconfig", "other"),
        ]:
            assert get_effective_file_type(name) == expected

    def test_unknown_extensionless_stays_other(self):
        assert get_effective_file_type("random-file") == "other"
        assert get_effective_file_type("dgpub-dev-ns-admin.kubeconfig") == "other"


class TestGetExtension:
    """扩展名解析保持与 os.path.splitext 一致"""

    def test_extension(self):
        assert get_extension("AGENTS.md") == ".md"
        assert get_extension("xa-higress-config") == ""
        assert get_extension("archive.tar.gz") == ".gz"
        assert get_extension(".gitignore") == ""
