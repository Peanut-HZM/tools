# P2-①b 文件插件系统 设计文档

**日期**：2026-08-30
**Phase**：3-Plan-2-1b（按用户约定编号；与原 P2 列表对应"Plugin 工具支持 → 文件插件子方向"）
**状态**：设计完成，待 user 评审
**对应规划 ID**：Phase 3 P2 ①Plugin 工具支持 的 ①b 文件插件子方向

---

## 1. 背景与目标

### 1.1 背景

Phase 3 P1 已交付：
- **Plan 1A** — MCP 工具支持（外部进程/服务类插件）
- **Plan 1B** — Memory 向量检索
- **Plan 1C** — Langfuse / OpenTelemetry 集成
- **Plan 1D** — Checkpoint 时间旅行

P2 ①"Plugin 工具支持"包含 3 个子方向：
- **①a Provider 热插拔**（LLM/embedding/image provider 实例的运行时管理）—— 已 100% 落地（`admin_llm_providers.py` 完整 CRUD + toggle + test-connection + reveal；`OrderedLLMGateway` 无缓存，运行时即生效）
- **①b 文件插件系统**（运维手工 drop .py 到 plugins/，启动时扫描）—— **本 spec 的范围**
- **①c 外部服务插件**（HTTP/stdio services beyond MCP）—— 候选后续 plan

### 1.2 目标

让运维通过简单的"放 .py 文件 + 重启服务"流程，给 Agent 添加新的内置式 Tool，无需修改 backend 代码或走完整发布流程。

### 1.3 非目标（明确划出去）

- 不做运行时 reload / 启用-禁用 / 运行时卸载 —— 全部需要重启 backend
- 不做 Provider 插件 / 事件钩子插件 —— 留 P2-①c 候选
- 不做 manifest / 依赖声明 / 版本锁定 —— 单 .py 装饰器即可
- 不做沙箱 —— in-process Python 即代码，信任模型靠 ops code review
- 不做 admin UI 上传 / 第三方插件仓库 —— 纯运维手工部署

---

## 2. 架构总览

### 2.1 Component 布局

```
backend/
├── plugins/                                # 新增（gitignore 候选 / 仓库提供 README）
│   ├── README.md                           # 插件编写说明（最小 API + 示例）
│   └── *.py                                # 运维手工 drop 单文件插件
└── app/services/harness/
    └── plugin_loader.py                    # 新增：扫描器 + @register_tool 装饰器
```

### 2.2 启动时数据流

```
[backend 启动 → app/main.py lifespan]
    │
    ▼
get_tool_registry() → ToolRegistry 单例
    │
    ▼
PluginLoader.scan("backend/plugins/")      ← 新增
    │
    ├─ glob("*.py") → 跳过 _*.py 与 __pycache__
    │
    └─ 对每个 .py：
         ├─ importlib.util.spec_from_file_location(plugin_name, path)
         ├─ module = importlib.util.module_from_spec(spec)
         ├─ spec.loader.exec_module(module)     ← 触发 @register_tool 装饰器
         │      │
         │      └─ register_tool(name=..., description=..., parameters=...)
         │           │
         │           ├─ 装饰时立即校验：
         │           │     - name/description 非空
         │           │     - 被装饰函数是 async def
         │           ├─ 构建 FunctionTool 包装（实现 ToolProtocol）
         │           └─ tool_registry.register_dynamic(function_tool)
         │
         └─ 异常隔离：单文件失败 → ERROR log + continue
    │
    ▼
[ToolRegistry 已含所有 builtin + dynamic + plugin tools]
    │
    ▼
[正常服务启动]
```

### 2.3 与现有代码的衔接

完全复用 `tool_registry.py:63 register_dynamic(tool: ToolProtocol)` —— 该方法注释明确"MCP tools 也走这里"。P2-①b plugin 与 MCP tool 共存 `_dynamic` 命名空间，天然无冲突。

不修改的文件：
- `backend/app/services/harness/tool_registry.py`
- `backend/app/services/harness/tool_protocol.py`
- `backend/app/services/harness/agent_runtime.py`
- `backend/app/main.py`（仅在 lifespan 中加一行 `PluginLoader.scan()` 调用）

仅新增：
- `backend/app/services/harness/plugin_loader.py`（~150 行）
- `backend/plugins/` 目录 + README.md + 1 个示例 hello_world.py

---

## 3. 关键设计

### 3.1 PluginLoader API

```python
class PluginLoader:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._loaded: List[str] = []  # 已成功加载的 plugin 名称（启动期记录）

    def scan(self, plugins_dir: str | Path) -> None:
        """扫描目录、加载所有 .py、注册 tool 到 tool_registry。

        失败隔离：单文件抛异常时记录 ERROR log + 跳过该文件，不阻断整体加载。
        """
```

### 3.2 `@register_tool` 装饰器

```python
def register_tool(
    *,
    name: str,
    description: str,
    parameters: dict,  # OpenAI function calling JSON schema
):
    """装饰器：把 async def fn(arguments, context) 包成 ToolProtocol 实例并注册。"""
```

被装饰函数签名（与 `ToolProtocol.execute(args, ctx)` 对齐）：
```python
async def my_tool(arguments: dict, context: ToolContext) -> dict:
    ...

    return {"text": "Hello, world!"}     # → ToolResult.text(...)
    # 或 return {"json": {...}}            → ToolResult.json(...)
    # 或 return {"image": "https://..."}   → ToolResult.image(...)
    # 或 return {"error": "..."}            → ToolResult.error(...)
    # 或 return {...raw dict...}            → 视作 JSON content (content_type="json")
```

返回 dict 通过 `_wrap_result()` 映射到 ToolResult（见 §3.4）。

### 3.3 错误处理表

| 场景 | 行为 |
|---|---|
| 单 .py 抛 SyntaxError / ImportError | ERROR log（含文件路径 + traceback 前 5 行），跳过，继续加载其他 |
| 单 .py 触发装饰器 ValueError | 同上 |
| plugins/ 目录不存在 | WARN log "plugins dir not found"，跳过，正常启动 |
| plugins/ 为空 | INFO log "no plugins loaded"，正常启动 |
| 装饰器缺 name / description | 装饰时立即 ValueError（开发期 fail-fast） |
| 装饰器作用在同步函数 | 装饰时立即 TypeError |
| 同名 tool 二次注册 | 复用 `register_dynamic` 已有 warning + 覆盖语义 |
| .py 文件名以 `_` 开头 | 跳过（约定：私有文件不视为插件） |
| 非 `.py` 文件 / `__pycache__/` | 跳过 |

### 3.4 FunctionTool 包装 + 结果映射

注册时构造的 `FunctionTool` 类（实现 `ToolProtocol`）：

```python
class FunctionTool:
    def __init__(self, name, description, parameters, fn):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._fn = fn

    async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        raw = await self._fn(arguments, context)
        return _wrap_result(self.name, raw)

    def is_available(self, ctx: ToolContext) -> bool:
        return True  # plugin 默认对所有 agent 可用（可后续通过 binding 控制）

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _wrap_result(tool_name: str, raw: Any) -> ToolResult:
    """把 plugin 函数返回的 dict 映射到 ToolResult。

    约定（key 优先级从高到低）：
      1. {"error": "..."}      → ToolResult.error(...)
      2. {"text": "..."}        → ToolResult.text(...)
      3. {"image": url, "alt": "..."} → ToolResult.image(url, alt=...)
      4. {"json": {...}}        → ToolResult.json(...)
      5. 其它 dict / 非 dict    → ToolResult(success=True, content=raw, content_type="json")
      6. None                   → ToolResult(success=True, content="", content_type="text")
    """
```

实现要点：`_wrap_result` 是独立纯函数，便于单测覆盖每个分支。

---

## 4. 测试策略

### 4.1 单元测试 `test_plugin_loader.py`

| 用例 | 覆盖 |
|---|---|
| `test_scan_empty_dir` | 空目录正常返回 |
| `test_scan_nonexistent_dir` | 不存在的目录 WARN log 跳过，不抛 |
| `test_scan_normal_plugin` | 含一个合法 .py → 1 个 tool 注册到 registry |
| `test_scan_syntax_error_isolated` | 一个 OK + 一个 syntax error → OK 注册成功，error 跳过 |
| `test_scan_value_error_isolated` | 装饰器抛 ValueError → 跳过，其他 OK |
| `test_scan_skips_underscore_files` | `_internal.py` 被跳过 |
| `test_scan_skips_pycache` | `__pycache__/` 被跳过 |
| `test_loader_logs_progress` | 每个加载结果有对应 INFO/ERROR log |

### 4.2 装饰器单元测试 `test_plugin_decorator.py`

| 用例 | 覆盖 |
|---|---|
| `test_register_tool_basic` | 装饰 async def → 返回 FunctionTool 已注册 |
| `test_register_tool_missing_name` | 缺 name 抛 ValueError |
| `test_register_tool_sync_fn_rejected` | 装饰同步函数抛 TypeError |
| `test_function_tool_execute` | execute(args, ctx) → 转发到原函数 + `_wrap_result` 返回正确 ToolResult |
| `test_function_tool_to_openai_schema` | 返回符合 OpenAI function calling 格式 |
| `test_wrap_result_text` | `{"text": "..."}` → `ToolResult.text(...)` |
| `test_wrap_result_json` | `{"json": {...}}` → `ToolResult.json(...)` |
| `test_wrap_result_image` | `{"image": url}` → `ToolResult.image(...)` |
| `test_wrap_result_error` | `{"error": "..."}` → `ToolResult.error(...)` |
| `test_wrap_result_raw_dict_fallback` | 未知 dict → `content_type="json"` |
| `test_wrap_result_none` | `None` → 空 content text result |

### 4.3 集成测试 `test_runtime_plugin.py`（harness/）

| 用例 | 覆盖 |
|---|---|
| `test_agent_can_invoke_plugin_tool` | Agent 配置 binding → 模拟 LLM function call → 验证 plugin tool 被调用 + 返回正确 |
| `test_plugin_tool_appears_in_registry` | 启动后 `tool_registry.get_tools_for_agent(agent_id, ctx)` 含 plugin tool |

### 4.4 不测

- 恶意 .py 内容（安全层不在 unit 测试范围，靠 ops code review + 信任模型）
- 插件并发加载（启动期单线程）
- 插件热重载（不在 scope）

---

## 5. 已知限制 / 不做清单

| 不做 | 留给 |
|---|---|
| 运行时 reload（不重启增减） | 候选续作 / 视运维需求 |
| 启用-禁用（不删文件但运行时屏蔽） | 同上 |
| Manifest / 依赖声明 / 版本锁定 | 同上（单 .py 装饰器足够） |
| Plugin 沙箱（限制 import / 网络 / 文件） | 不做（in-process Python 即代码；信任模型靠 ops） |
| Provider 插件 / 事件钩子 | P2-①c 候选 |
| admin UI 上传 / Web 管理 | 不做（安全考虑） |
| 第三方插件仓库 / Marketplace | P2-④ Agent 市场 |
| Plugin 签名 / 校验和 | 不做（内部插件，信任模型） |
| Plugin 独立测试框架（plugin 自己 pytest） | 不强制；loader 不验证测试存在 |

---

## 6. 文件清单

新增：

- `backend/app/services/harness/plugin_loader.py`（~150 行：PluginLoader + register_tool + FunctionTool）
- `backend/plugins/__init__.py`（空，标识为 package）
- `backend/plugins/README.md`（插件编写说明：最小 API + 示例）
- `backend/plugins/hello_world.py`（示例 plugin，可选保留作为 smoke test）

修改：

- `backend/app/main.py` lifespan 中加 1 行：`PluginLoader(registry).scan("backend/plugins/")`
- `backend/.gitignore` 添加 `backend/plugins/*.py`（除 `__init__.py` 和 README）

新增测试：

- `backend/tests/harness/test_plugin_loader.py`（~150 行）
- `backend/tests/harness/test_plugin_decorator.py`（~80 行）
- `backend/tests/harness/test_runtime_plugin.py`（~80 行）

---

## 7. 决策记录

### 7.1 为什么不动 tool_registry.py

`register_dynamic` 已经存在（Plan 1A 加的），注释明确"MCP tools 也走这里"。Plugin tool 与 MCP tool 同属 `_dynamic` 命名空间，**复用 = 不引入新概念**。

### 7.2 为什么不做 sandbox

in-process Python 文件就是代码，无法在运行时限制其 `import os; os.system('rm -rf /')`。沙箱需要操作系统级隔离（容器 / 微 VM），远超本 plan 范围。信任模型：ops 有代码 review SOP，新 .py 走 PR 流程入仓。

### 7.3 为什么不做 admin UI 上传

同 §7.2。admin UI 让非运维角色也能上传代码 = 严重越权。当前模型："能 push 到 backend/plugins/ 的人" = "已经能直接 push 到 backend 代码仓的人"，权限边界清晰。

### 7.4 为什么只重启生效，不做运行时 reload

importlib 的模块热替换 + 装饰器副作用清理有大量边界场景（import 缓存、状态持有、cyclic dep），且 P2 范围以"运维简单流程"为目标。重启 = 30 秒停机 vs 运行时 reload = 几小时调试。**YAGNI**。

---

## 8. 实施 task 拆分（预估 3-4 个 task）

1. **Task 1: 注册装饰器 + FunctionTool 实现** —— `plugin_loader.py` 核心 + 装饰器单元测试
2. **Task 2: PluginLoader.scan + 启动集成** —— 扫描器 + 启动调用 + loader 单元测试 + `plugins/` 目录 + README
3. **Task 3: Runtime 集成测试** —— harness 集成测试，agent 调用 plugin tool 端到端验证

预估代码量：~300 行（含测试 + 文档）。单 plan 可完成。

---

## 9. 参考 / 相关

- `backend/app/services/harness/tool_registry.py` — `register_dynamic` 接口
- `backend/app/services/harness/tool_protocol.py` — `ToolProtocol` 接口
- Plan 1A（已 merge `393db228`）— MCP tools 走 `register_dynamic` 的先例
- Phase 3 设计文档 §11.4 P2 列表第 5 项 "Plugin 工具支持"