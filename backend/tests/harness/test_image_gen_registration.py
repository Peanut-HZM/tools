"""image_gen 工具注册测试

覆盖：
- ImageGenTool 注册到 ToolRegistry 后可被检索
- 出现在 function schemas 中
- operation 字段含完整 enum 限制
"""
import pytest

from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tools.image_gen import ImageGenTool


class TestImageGenRegistration:
    def test_register_image_gen_tool(self, test_db):
        """ImageGenTool 可以注册到 ToolRegistry"""
        registry = ToolRegistry(db=test_db)
        tool = ImageGenTool()
        registry.register_builtin(tool)
        assert "image_gen" in registry._builtin

    def test_image_gen_in_function_schemas(self, test_db):
        """image_gen 出现在 function schemas 中"""
        registry = ToolRegistry(db=test_db)
        tool = ImageGenTool()
        registry.register_builtin(tool)
        schemas = registry.to_function_schemas([tool])
        assert len(schemas) == 1
        assert schemas[0]["name"] == "image_gen"
        assert "operation" in schemas[0]["parameters"]["properties"]

    def test_image_gen_function_schema_has_enums(self, test_db):
        """operation 字段含 enum 限制"""
        registry = ToolRegistry(db=test_db)
        tool = ImageGenTool()
        registry.register_builtin(tool)
        schemas = registry.to_function_schemas([tool])
        op_prop = schemas[0]["parameters"]["properties"]["operation"]
        assert "enum" in op_prop
        assert "text2img" in op_prop["enum"]
        assert "img2img" in op_prop["enum"]
        assert "inpaint" in op_prop["enum"]
        assert "upload_edit" in op_prop["enum"]
