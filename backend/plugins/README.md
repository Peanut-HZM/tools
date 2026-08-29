# Agent Harness Plugin 目录

把 .py 文件放这里，重启 backend，文件里的 `@register_tool` 装饰的函数会自动注册为 Agent 可用的 Tool。

## 最小 API

```python
from app.services.harness.plugin_loader import register_tool
from app.services.harness.tool_protocol import ToolContext

@register_tool(
    name="my_tool",                      # 必填，全局唯一
    description="简短描述（LLM 看到）",
    parameters={                         # OpenAI function calling JSON schema
        "type": "object",
        "properties": {
            "msg": {"type": "string"}
        },
        "required": ["msg"],
    },
)
async def my_tool(arguments: dict, context: ToolContext) -> dict:
    return {"text": f"got {arguments.get('msg', '')}"}
```

## 返回值约定

返回 dict 通过 `_wrap_result()` 映射为标准 `ToolResult`：

| 返回 dict | 映射结果 |
|---|---|
| `{"text": "..."}` | `ToolResult.text(...)` |
| `{"json": {...}}` | `ToolResult.json(...)` |
| `{"image": "url", "alt": "..."}` | `ToolResult.image(url, alt=...)` |
| `{"error": "..."}` | `ToolResult.error(...)` |
| 其它 dict / 非 dict | 视作 JSON content |
| `None` | 空文本 result |

## 失败隔离

单文件抛 `SyntaxError` / `ImportError` / 装饰器校验失败时，PluginLoader 仅记录 ERROR log + 跳过该文件，**不影响其他插件加载和服务启动**。

## 命名约定

- 文件名以 `_` 开头视为私有文件，**不会**被加载（如 `_helper.py`）
- 不要与 builtin tool / MCP tool 重名（重名时 Plugin tool 覆盖对方 + 警告日志）
- 调试建议：起一个独特的 `name=` 前缀（如 `myteam_*`）

## 部署

1. 编写 .py 文件
2. 把文件 scp / git push 到 `backend/plugins/` 目录
3. 重启 backend（`python dev-services.py restart backend`）
4. 查日志：`tail -f logs/app.log | grep PluginLoader`

## 信任模型

in-process Python 即代码，无法沙箱限制 `import os; os.system(...)`。**新 .py 必须走 PR 流程 + 代码 review**。允许 push 到 `backend/plugins/` 的人 = 允许 push 到 `backend/` 全部代码的人。

## 不做（明确）

- 不支持运行时 reload / 启用-禁用（须重启）
- 不支持 Manifest / 依赖声明 / 版本锁定（单 .py 装饰器足够）
- 不支持 sandbox / 权限限制（trust 模型靠 code review）
- 不支持 admin UI 上传（安全考虑）