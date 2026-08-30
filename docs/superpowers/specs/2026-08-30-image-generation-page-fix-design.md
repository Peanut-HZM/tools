# 图像生成页面修复（多轮对话式图生）设计文档

**日期**：2026-08-30
**状态**：已实现并完成验收（2026-08-30）

验收记录：
1. 后端自动化：pytest tests/harness 762 passed（含图生页面 10 个新测试）
2. 真实生成：scripts/acceptance_image_gen.py → ACCEPTANCE PASS（HTTP 200 image/jpeg）
3. 浏览器 e2e（agent-browser，真实登录用户路径）：
   - 工作区打开图像生成页（不再出现"未知工具"）✓
   - 第一轮模糊请求 → 助手追问主题/风格/画幅，未生成 ✓
   - 第二轮补足信息 → 复述意图 + 真实生成 → 页面显示图片（img.complete=true, 2048px）✓
   - 刷新后图片仍在（附件持久化）✓

过程中修复的环境/链路问题：开发库从未执行 harness 迁移（phase1 迁移本身含 PG 不兼容的布尔默认值与无效索引，已幂等化修复）；pgvector 不可用时 embedding 列降级 TEXT；LLM 配额需 admin 发放；llm bridge 丢失 provider 原生 tool_calls（kimi 空回复根因）；工具 schema 归一化为 OpenAI 现代格式（DashScope 400 根因）；豆包 provider 404 可转移 + ark list 形状解析；conversations.agent_id NOT NULL 下创建会话 500；doubao-seedream 模型端点名失效（已更新为 doubao-seedream-4-0-250828）。
**性质**：缺陷修复 + 功能补全（/goal：页面完全不可用；要求多轮对话探究意图后再真实生成图片，并完成验收）

---

## 1. 根因（已诊断）

1. `frontend/src/components/Workspace/toolComponents.tsx` 的 `toolComponentMap` **没有 `image-generation` 映射**，且 `Tools/` 下从未实现图像生成页面组件 → TabPanels 渲染"未知工具: image-generation"（截图现象）
2. `backend/app/api/routes/chat_stream.py` 的 SSE **只转发 chunk/done/error**，`tool_call_start` / `tool_result` / `image_generated` 事件被丢弃（代码注释："Task 19 再扩展前端 SSE 事件类型"）——即使有页面也看不到生成过程与结果
3. 没有图像生成专用 Agent：多轮意图探究需要专门的角色设定（system_prompt）
4. 消息 API 不透出 `Message.attachments`，生成结果无法在刷新后持久显示

可复用的既有能力（无需新建）：harness `ImageGenTool`（含 prompt 润色、provider 故障转移、`content.image_urls` + `attachments` 返回结构）、`ImageGenRenderer`（聊天内渲染器）、`conversationApi.sendMessageStream`、本机已配置可用的 image_gen 模型（火山方舟 doubao_seedream ×2，密钥齐全）。

## 2. 设计

### 2.1 图像生成 Agent（幂等种子）

- `ensure_image_gen_agent(db) -> Agent`：按 `slug="image-generation-assistant"` 查询，无则创建：
  - `name="图像生成助手"`、`visibility="public"`、`is_active=True`、`is_default=False`
  - `system_prompt`（多轮意图探究的核心约束，中文）：
    1. 你是图像生成助手，通过多轮对话理解用户意图
    2. **信息不足时禁止调用 image_gen 工具**；首轮必须回应并追问关键要素：主体内容、风格、画幅比例、数量（一次最多问 2-3 个问题，避免审问感）
    3. 用户补充后仍缺关键信息则继续追问；信息足够时先复述理解到的意图再调用 image_gen（operation=text2img，prompt 用中文描述）
    4. 生成成功后在回复中说明并附图片链接；失败时说明原因并建议调整
  - 已存在时**不覆盖**（保护 admin 的人工修改），仅当 `is_active=False` 时重新激活
- 懒初始化：由新端点 `GET /api/v1/tools/image-generation/agent` 调用（登录用户可访问），返回 `{agent_id, name}`；同时启动 lifespan 调用一次（admin 管理页可见）

### 2.2 SSE 事件转发（兑现 Task 19 的最小集）

chat_stream `generate_stream` 增加两个分支（现有 chunk/done/error 行为不变，未知事件旧前端自动忽略）：

| runtime 事件 | SSE 形状 |
|---|---|
| `tool_call_start` | `{"type":"tool_call_start","data":{"name": call.name, "arguments": call.arguments}}` |
| `tool_result` | `{"type":"tool_result","data":{"name": call.name, "success": result.success, "content_type": result.content_type, "content": <json 或文本，截断 4KB>, "attachments": [...]}}` |

### 2.3 生成结果持久化

- done 分支：本轮若发生过 `image_gen` 成功的 tool_result，把其 `attachments`（`[{type:"image", url, name, mime_type}]`）写入 `agent_message.attachments`（列已存在，此前无人写入）
- `agent_msg_dict` 与 `_message_to_dict`（conversations.py）增加 `attachments` 字段透出 → 刷新页面后图片仍可显示

### 2.4 前端页面

- 新组件 `frontend/src/components/Tools/ImageGeneration/ImageGenerationTool.tsx`，注册 `toolComponentMap['image-generation']`
- 交互流程（多轮对话探究意图）：
  1. 挂载时：`GET /tools/image-generation/agent` 取 agent_id → localStorage 恢复或新建会话 → `GET messages` 回填历史（含 attachments 图片）
  2. 发送：`sendMessageStream` 消费增强——`chunk`→流式文本；`tool_call_start`(name=image_gen)→"🎨 正在生成图像…"占位；`tool_result`(image_gen 成功)→渲染图片卡片（网格、点击原图、safeHref 校验）；`tool_result`(失败)→错误卡片；`done`→落定消息（含 attachments 持久渲染）
  3. 会话体验：澄清轮次与普通聊天一致，由 Agent system_prompt 驱动；页面提供"开始新对话"按钮（新会话）
- `conversationApi.sendMessageStream` 增加**可选** `onEvent?(event)` 回调透传全部未加工事件（向后兼容：现有调用方不传则行为不变）

## 3. 验收标准（全部必须通过）

1. **后端自动化**：seed 幂等（两次调用同一 agent_id）；chat_stream 集成测试断言 `tool_call_start`/`tool_result` 事件被转发且 done 消息带 attachments；`_message_to_dict` 含 attachments
2. **真实生成**：脚本直接驱动 `ImageGenTool`（真实 gateway → 火山方舟 provider），生成 URL 必须 HTTP 200 且 `Content-Type: image/*`（证明"图片真实生成成功"而非占位）
3. **浏览器 e2e**：登录 → 工作区打开"图像生成"页面（不再是"未知工具"）→ 第一轮输入模糊需求 → Agent 必须提出澄清问题（不生成）→ 补充信息 → Agent 复述意图并生成 → 页面真实显示生成的图片 → 刷新后图片仍在
4. 回归：既有 harness/chat 测试零回归；前端 build + tsc 通过

## 4. 不做清单

图生图/局部重绘/上传编辑（工具已支持 operation，但页面 v1 只做文生图多轮流程）；图片历史画廊（独立 tab，候选续作）；SSE 断线重连（沿用现有简单实现）。
