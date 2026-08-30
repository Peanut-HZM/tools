"""hello_world.py — 示例 plugin

启动 backend 后会注册 `hello_world` tool。LLM 调用示例：
- tool_name: "hello_world"
- arguments: {"name": "world"}
- 返回: {"text": "Hello, world!"}
"""
from app.services.harness.plugin_loader import register_tool
from app.services.harness.tool_protocol import ToolContext


@register_tool(
    name="hello_world",
    description="返回一个问候语（用于演示插件系统）",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "要问候的名字",
            }
        },
        "required": [],
    },
)
async def hello_world(arguments: dict, context: ToolContext) -> dict:
    """hello_world 的实现"""
    name = arguments.get("name", "world")
    return {"text": f"Hello, {name}!"}