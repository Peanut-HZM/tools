# 视频生成工具（MiniMax 文生视频）设计文档

**日期**：2026-08-30
**状态**：设计完成
**需求**：按现有图像生成 agent 的完整流程与逻辑，新增视频生成工具（MiniMax 视频生成 v2 API）；生成视频必须转存自有 OSS；前端可播放、可下载、可弹框预览；验收样例为"高燃的动漫 AI 短剧战斗视频"。

---

## 1. API 要点（已核实官方文档）

- 创建：`POST https://api.minimaxi.com/v2/video_generation`，Bearer 认证；必填 `model`（MiniMax-H3 / H3-Max）、`content`（数组，文生视频=仅一个 `{type:"text", text: prompt}`）、`resolution`（480P/768P/2K）、`duration`（4-15s）、`ratio`（文生视频必填且不可 adaptive）
- 查询：`GET /v2/query/video_generation/{task_id}` → `task.status`（queued/running/succeeded/failed/cancelled）；成功后 `task.content.url` 为**限时下载链接**（必须及时转存）
- 异步任务，通常 1-5 分钟出片

## 2. 架构（对齐 image_gen 链路）

```
app/services/harness/video_provider/
├── base.py        # VideoGenError(retryable) / VideoGenParams / VideoGenResult / VideoModelProvider 抽象
│                  #   （含 _download_and_upload：下载 mp4 → OssService.upload_bytes → video-gen/{uuid}.mp4）
├── minimax.py     # MiniMaxVideoProvider：submit → poll(10s 间隔, 上限 8min) → OSS 转存
└── registry.py    # register_provider("minimax_video", ...)

app/services/harness/tools/video_gen.py   # VideoGenTool(BuiltinTool) name="video_gen"
backend/app/routes 不变：chat_stream 注册工具 + SSE 转发（复用现有 tool_call_start/tool_result）
```

- **模型链**：对齐 image_gen——从 `ctx.agent.default_model_id/fallback_model_ids` 解析 `category="video_gen"` 的 LLMModel；provider 按 `provider.provider_type` 经 registry 构造（MinMax provider 的 base 去掉 `/v1` 即视频 API base）
- **OSS**：`OssService.upload_bytes`（v2 已加），key=`video-gen/{uuid}.mp4`，content_type=`video/mp4`；转存失败降级原始 URL
- **chat_stream**：注册 VideoGenTool；done 分支附件收集条件扩展为 `name in ("image_gen","video_gen")`
- **Agent 种子**：slug=`video-generation-assistant`（"视频生成助手"），system_prompt 对齐图生（意图探究 → 视频提示词工程：主体+动作叙事+镜头运动+氛围；硬约束保留；必调工具；禁编造链接）+ `_bind_video_models`（category=video_gen 模型自动挂载，排除/优选逻辑按 model_name）
- **端点**：`GET /api/v1/tools/video-generation/agent`（幂等种子 + 返回 agent_id）
- **DB 配置**：脚本幂等插入 `LLMModel(category="video_gen", model_name="MiniMax-H3", provider=MinMax)`（用户已配好 key）

## 3. 前端

- `VideoGenerationTool.tsx`（workspace 组件，id=`video-generation`）：对齐图生页（全宽、多轮、SSE、OSS URL）
  - tool_result(name=video_gen) → 视频卡片：`<video controls preload="metadata" src=OSS>` + 下载按钮
  - 点击视频 → 弹框预览（大窗口 `<video controls autoplay>` + 下载 + 关闭）
  - 工具输出消息过滤、历史正序、URL 折叠——复用图生页模式
- `toolComponents.tsx` 注册 `'video-generation'`
- `tools_data.py` 增加工具条目（首页卡片）

## 4. 测试与验收

| 层 | 内容 |
|---|---|
| provider 单测 | submit 成功/失败（401/402/422）；poll 状态机 queued→running→succeeded / failed；OSS 转存（mock oss_client）；非 200 分类 |
| 工具单测 | 参数校验（duration 4-15/resolution/ratio）；模型链缺失报错；门控（agent 绑定）|
| seed/API | 幂等种子；agent 端点；chat_stream 附件收集含 video_gen |
| 验收 | 真实生成"高燃的动漫 AI 短剧战斗视频"：prompt 经 agent 扩写 → MiniMax-H3 → OSS mp4 → 前端播放/下载/弹框 |

超时与体验：轮询上限 8 分钟；vite proxy timeout 已是 600s；前端"生成中"占位（tool_call_start）。
