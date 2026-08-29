# Agent Harness 文件插件系统

> **Phase 3 P2-①b** — 让运维通过简单的"放 .py 文件 + 重启 backend"流程，给 Agent 添加新的内置式 Tool，无需修改 backend 代码或走完整发布流程。

## 1. 概念

- 插件 = `backend/plugins/` 目录下任意非 `_` 开头的 `.py` 文件
- 文件里用 `@register_tool(...)` 装饰 `async def fn(arguments, context) -> dict` 函数
- 启动时由 `PluginLoader.scan()` 加载文件、触发装饰器、把 Tool 注册到全局 `ToolRegistry._dynamic` 命名空间（与 MCP tools 共存）
- LLM 可以像调用 builtin / MCP tool 一样调用 plugin tool

## 2. 最小编写示例

```python
# backend/plugins/my_tool.py
from app.services.harness.plugin_loader import register_tool
from app.services.harness.tool_protocol import ToolContext

@register_tool(
    name="my_team_echo",
    description="返回 'Echo: <msg>'",
    parameters={
        "type": "object",
        "properties": {"msg": {"type": "string"}},
        "required": ["msg"],
    },
)
async def my_team_echo(arguments: dict, context: ToolContext) -> dict:
    return {"text": f"Echo: {arguments.get('msg', '')}"}
```

重启 backend：

```bash
python dev-services.py restart backend
tail -f logs/app.log | grep -E "PluginLoader|my_team_echo"
```

看到 `[PluginLoader] 已加载: my_tool.py` 即成功。LLM 现在可以调用 `my_team_echo` tool。

## 3. 返回值约定

| 返回 dict | 映射结果 |
|---|---|
| `{"text": "..."}` | `ToolResult.text(...)` |
| `{"json": {...}}` | `ToolResult.json(...)` |
| `{"image": "url", "alt": "..."}` | `ToolResult.image(url, alt=...)` |
| `{"error": "..."}` | `ToolResult.error(...)` |
| 其它 dict / 非 dict | 视作 JSON content（content_type="json"） |
| `None` | 空文本 result |

## 4. 部署流程

1. 编写 .py 文件并走 PR 流程（含 code review）
2. merge 后 deploy 脚本会 rsync 到目标机器的 `backend/plugins/` 目录
3. 重启 backend（30 秒停机）
4. 验证：在 admin UI 查看 Tool 列表，或 `tail logs/app.log | grep PluginLoader`

## 5. 失败隔离

- 单文件抛 `SyntaxError` / `ImportError` / 装饰器校验失败 → ERROR log + 跳过该文件
- 不影响其他插件加载
- 不影响 backend 启动

## 6. 已知限制

- 不支持运行时 reload / 启用-禁用 / 运行时卸载
- 不支持 Manifest / 依赖声明 / 版本锁定
- 不支持沙箱（trust 模型靠 code review）
- 不支持 admin UI 上传 / Web 管理
- 不支持第三方插件仓库 / Marketplace

完整设计参考 `docs/superpowers/specs/2026-08-30-agent-harness-phase3-plan2-1b-file-plugin-system-design.md`。
