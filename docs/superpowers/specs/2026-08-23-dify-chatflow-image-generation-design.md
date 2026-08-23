# Dify Chatflow 图像生成对话系统 — 设计规格

- **日期**：2026-08-23
- **状态**：Draft，待用户 review
- **作者**：Claude（brainstorming 流程产出）
- **路径**：`docs/superpowers/specs/2026-08-23-dify-chatflow-image-generation-design.md`

---

## 1. 背景与目标

### 1.1 背景

现有图像生成工具（`docs/plans/2026-08-23-image-generation-tool-design.md`）使用 **Workflow** 类型应用，单次 `POST /workflows/run` 调用，用户提交提示词 → 后端 → Dify → 图像模型 → 返回图片。

这种模式的问题：
- 用户提示词质量参差不齐 → 直接生图效果差
- 没有"对话收集信息 → 信息足够再生图"的引导流程
- 不支持基于上一张图的迭代修改（"颜色再暖一点"、"人物换成卡通"）

### 1.2 目标

引入**真正多轮对话**（streaming）让用户在生成图片前能：
1. 与 LLM 对话，补充缺失的细节（风格、场景、光照、细节）
2. 当信息足够时，LLM 自主触发图片生成
3. 生图后能继续对话迭代修改

### 1.3 非目标

- ❌ 不做语音对话
- ❌ 不做图片审美评分
- ❌ 不做用户人设/偏好持久化（用户每次对话独立）

---

## 2. 关键决策

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| D1 | Dify 应用类型 | **Chatflow**（不是 Workflow） | 原生支持对话历史 + streaming；可视化编排 LLM + 工具节点 |
| D2 | 对话轮次 | **动态轮次** | LLM 根据信息完整度自主判断何时生成，不固定问题数 |
| D3 | 结束条件 | **LLM 自主判断** | 用特殊标记 `<<GENERATE>>` 触发生图；用户无需手动触发 |
| D4 | 对话范围 | **text2img 完整对话；其他 3 个简化对话** | text2img 只有文本，信息最少；其他已有图，问 1-2 轮即可 |
| D5 | LLM 路由 | **自动路由**（小模型处理简单问题，大模型处理复杂描述） | 成本 + 效果平衡 |
| D6 | 迭代修改 | **支持**（基于 conversation_id 继续对话） | 用户体验闭环 |
| D7 | 对话历史存储 | **Dify 服务端 + 项目 DB 只存 conversation_id** | 避免双写一致性问题 |

---

## 3. Dify 应用架构

### 3.1 4 个 Chatflow 应用

| Chatflow | 对话重点 | 工具输入 |
|---|---|---|
| **text2img-chat** | 主题/风格/场景/光照/细节 | prompt + size + n + style |
| **img2img-chat** | 想改什么/想要什么效果/强度 | prompt + reference_url + strength + size |
| **inpaint-chat** | 蒙版区域想要画什么 | prompt + image_url + mask_url + size |
| **upload-edit-chat** | 编辑类型 + 可选微调 | image_url + edit_type + prompt |

### 3.2 text2img-chat 节点编排

```
[开始]
  ↓
[对话历史变量] ← Dify Chatflow 自动管理
  ↓
[LLM 节点: "对话大脑"] ← 核心
  System Prompt:
    你是图像生成助手。你的任务是帮用户收集足够的信息来生成图片。
    你需要了解：主题、风格(写实/卡通/油画/水彩/3D)、场景、光照、细节。
    
    规则：
    1. 每轮最多问 1 个问题（不要一次问一堆）
    2. 用户回答后，把已知信息总结成 JSON 格式的内部状态
    3. 当信息满足以下 3 项以上时，输出特殊标记 <<GENERATE>>
    4. 在 <<GENERATE>> 之后，输出润色后的完整英文提示词
  ↓
[条件分支: 检查 <<GENERATE>> 标记]
  ├─ 未触发 → [结束] (回复追问，等用户继续回答)
  └─ 已触发 → 继续
       ↓
  [LLM 节点: "提示词路由+润色"] ← 自动路由
    根据提示词复杂度选择模型：
    - 简单描述（<50字、无复杂场景）→ 小模型（qwen-turbo）
    - 复杂描述（多元素、氛围、光影）→ 大模型（gpt-4o）
    输出：润色后的英文图像生成提示词
       ↓
  [工具节点: 图像生成] ← 选定的图像插件
    输入：润色后的 prompt + size + n + style
       ↓
  [代码节点: 组装最终输出]
    输出变量：
      - image_urls: string (JSON 数组)
      - model_used: string
      - polish_prompt: string
  ↓
[结束]
```

### 3.3 简化版 Chatflow（img2img / inpaint / upload-edit）

**img2img-chat**：
```
[开始] → [LLM 对话]（已知参考图，问"改什么/什么效果"） → [工具节点: img2img] → [代码] → [结束]
```

**inpaint-chat**：
```
[开始] → [LLM 对话]（已知图+蒙版，问"重绘区域画什么"） → [工具节点: inpaint] → [代码] → [结束]
```

**upload-edit-chat**：
```
[开始] → [LLM 对话]（已知图，问"什么编辑 + 微调"） → [工具节点: upload_edit] → [代码] → [结束]
```

---

## 4. 后端改动

### 4.1 `backend/app/services/dify_client.py` — 新增 `chat_*` 方法

新增 4 个方法，**保留原 `run_*` 方法**（兼容旧调用）：

```python
@dataclass
class ChatRunResult:
    conversation_id: str     # 多轮对话 ID（首次生成时返回，后续轮次回传）
    answer: str              # LLM 回复文本（追问 or 生成说明）
    image_urls: List[str]    # 生成图片（仅 <<GENERATE>> 触发后有值）
    model_used: str
    polish_prompt: str       # 润色后的提示词
    raw_response: dict

async def chat_text2img(
    prompt: str,
    conversation_id: Optional[str],
    size: str, n: int, style: str, model_preference: str,
    user_id: str, timeout: float = 60.0,
) -> ChatRunResult:
    """调用 text2img-chat Chatflow"""
    # POST /chat-messages
    # body: {
    #   "inputs": {"size": size, "n": n, "style": style, "model_preference": model_preference},
    #   "query": prompt,
    #   "response_mode": "blocking",
    #   "user": user_id,
    #   "conversation_id": conversation_id  # 多轮时传入
    # }
```

`chat_img2img` / `chat_inpaint` / `chat_upload_edit` 类似。

### 4.2 `backend/app/services/image_generation_service.py` — 新增 `chat_generate` 方法

```python
async def chat_generate(
    user_id, operation, prompt, conversation_id, params, reference_file, mask_file,
) -> ChatRunResult:
    """多轮对话生成 — 支持追问和迭代生成"""
    # 1. 调用对应 chat_* 方法
    # 2. 如有图片生成 → 走原有 OSS 上传 + 历史写入流程
    # 3. 如仅是追问 → 只返回 answer + conversation_id（不扣配额、不写历史）
    # 4. 迭代修改：传 conversation_id → Dify 带上下文继续对话
```

### 4.3 `backend/app/routes/image_generation.py` — 新增 `/chat` 端点

```python
@router.post("/chat")  # 多轮对话入口
async def chat_generate(request: ChatGenerateRequest):
    """
    请求：{ operation, prompt, conversation_id?, size, n, ... }
    响应：
    {
      "conversation_id": "xxx",      # 首次生成时返回
      "answer": "你想用什么风格？",    # LLM 追问
      "image_urls": [...],           # 生成了才有
      "polish_prompt": "...",
      "status": "asking" | "generated"
    }
    """

# 保留原 /generate 端点（一次性 blocking 生成，作为"跳过对话直接生成"的快捷方式）
```

### 4.4 数据库迁移

```sql
-- 新增字段：关联"哪张图是哪个对话产生的"
ALTER TABLE image_gen_history 
ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(64) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_img_gen_history_conversation 
ON image_gen_history(conversation_id) WHERE conversation_id IS NOT NULL;
```

只在生成图片时写 `conversation_id`（追问时不写）。

---

## 5. 前端改动

### 5.1 `frontend/src/stores/imageGenerationStore.ts` — 新增对话状态

```typescript
interface ImageGenState {
  // ... 原有字段 ...

  // 对话相关
  conversationId: string | null;
  conversationHistory: ChatMessage[];
  currentAnswer: string | null;

  // 动作
  chatGenerate: (params) => Promise<ChatResult>;
  sendMessage: (message: string) => Promise<ChatResult>;
  resetConversation: () => void;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}
```

### 5.2 `frontend/src/components/Tools/ImageGeneration/forms/Text2ImgForm.tsx` — 改为对话式 UI

```
┌────────────────────────────────────────┐
│  对话区域                               │
│  ┌──────────────────────────────────┐  │
│  │ 🤖 你想生成什么图片？              │  │
│  │ 👤 一只猫在太空                      │  │
│  │ 🤖 想要什么风格？(写实/卡通/油画)   │  │
│  └──────────────────────────────────┘  │
│                                        │
│  [输入框 + 发送按钮]                     │
│                                        │
│  ┌─ 生成结果 ──────────────────────┐    │
│  │  [图片]                            │    │
│  │  模型: qwen-image-v1              │    │
│  │  [下载] [以此图为参考] [继续对话]    │    │
│  └─────────────────────────────────┘    │
└────────────────────────────────────────┘
```

### 5.3 `frontend/src/api/imageGenerationApi.ts` — 新增 `chatGenerate` 方法

```typescript
export async function chatGenerate(
  operation: Operation,
  prompt: string,
  conversationId: string | null,
  params: { size, n, style, ... },
  references?: { image?: File, mask?: File },
) → {
  // POST /image-generation/chat
  // FormData: 文件 + conversation_id
  // 返回：{ conversation_id, answer, image_urls?, polish_prompt?, status }
}
```

### 5.4 `frontend/src/hooks/useImageGenerate.ts` — 区分对话模式和直接模式

```typescript
export function useImageGenerate() {
  // 流式对话模式（默认，text2img 主流程）
  const handleChat = async (prompt: string) => {
    const result = await chatGenerate(operation, prompt, conversationId, params);
    // result.image_urls 有值 → 生成成功
    // result.answer 有值 → LLM 追问
  };

  // 直接生成模式（img2img/inpaint/upload_edit 简化流程 + 跳过对话选项）
  const handleDirectGenerate = async () => {
    // 调原有 generate() 方法
  };
}
```

---

## 6. 对话历史存储

**Dify 服务端（自动）**：
- Dify Chatflow 内置对话历史管理
- 每次调用 `chatGenerate(conversation_id)`，Dify 自动带历史
- 后端不存对话内容，只存 `conversation_id`

**项目 DB（轻量）**：
- `image_gen_history` 表新增 `conversation_id` 字段
- 仅在生成图片时写入（追问时不写）
- 作用：用户在历史抽屉里能"基于此图继续对话"

---

## 7. 测试与验收

### 7.1 Dify 端测试

| 测试项 | 通过条件 |
|---|---|
| 启动 text2img-chat | 不报错，进入对话模式 |
| 输入"一只猫" | LLM 追问风格 |
| 回答"卡通" | LLM 追问场景 |
| 回答"在太空" | LLM 触发 `<<GENERATE>>`，返回图片 |
| 继续说"颜色再亮一点" | 新生成一张猫的图片（带上下文） |

### 7.2 后端测试

- `tests/test_chat_flow.py`：模拟多轮对话 + 迭代生成
- 配额：仅生成图片时扣减，追问不扣
- 历史：`conversation_id` 正确写入

### 7.3 前端冒烟

| 步骤 | 期望 |
|---|---|
| 进入 text2img tab | 显示对话 UI（空状态："你想画什么？"） |
| 输入"一只猫" | 1 秒内显示 LLM 追问 |
| 回答 3 轮 | 第 3 轮触发生成，显示图片 |
| 点"以此图为参考" | 切到 img2img，对话历史自动关联 |
| 历史抽屉看 | 该记录显示对话来源 |

---

## 8. 风险与限制

| 风险 | 影响 | 缓解 |
|---|---|---|
| Dify Chatflow streaming 在某些网络下不稳定 | 长轮对话断流 | 优先 `response_mode="blocking"`，streaming 作为可选 |
| LLM 路由判断不准确 | 简单问题被路由到大模型，浪费 token | 路由节点加严格 prompt 规则 + 测试用例 |
| 对话历史无限增长 | Dify 端存储膨胀 | 设置 Dify 自动清理（保留 30 天） |
| `conversation_id` 失效（用户清缓存） | 无法继续对话 | 前端兜底：丢失时重新发起对话 |
| 不同模型的 prompt 格式要求不同 | 跨模型生图失败 | 路由节点统一输出英文结构化 prompt |

---

## 9. 实施步骤

按以下顺序实施：

1. **Dify 端创建 Chatflow**（浏览器操作）
   - 登录 Dify → 创建 4 个 Chatflow 应用
   - 配置 LLM 节点、路由节点、工具节点
   - 测试每个 Chatflow

2. **后端改动**
   - 迁移脚本（新增 conversation_id 字段）
   - `dify_client.py` 新增 `chat_*` 方法
   - `image_generation_service.py` 新增 `chat_generate` 方法
   - `routes/image_generation.py` 新增 `/chat` 端点
   - 集成测试

3. **前端改动**
   - 状态管理（对话历史）
   - 表单 UI 改为对话式
   - API 封装
   - 冒烟测试

4. **联调**
   - 端到端对话流
   - 配额与历史写入
   - 边界 case（断网、超时、conversation_id 失效）

---

## 附录 A：原设计参考

- 现有图像生成工具设计：`docs/plans/2026-08-23-image-generation-tool-design.md`
- 部署清单：`docs/plans/2026-08-23-image-generation-tool-deployment-checklist.md`
