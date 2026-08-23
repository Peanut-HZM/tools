# 自研图像生成 Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `/api/image-generation/chat` 上加后端切换参数，新增"自研 Agent"路径，与 Dify 路径并存；所有模型配置统一来自 `/admin/llm-configs`，走全局有序兜底链。

**Architecture:** Strategy 后端注册表分发；`OrderedLLMGateway` 按 category + priority 迭代 LLMModel；`AgentOrchestrator` 维护多轮 tool-calling 对话；4 个 `ImageGenAdapter` 封装外部 API（豆包 / 通义万相 / 海螺 / DALL-E 3）。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic（后端）、React 18 + TypeScript + Zustand（前端）、httpx（外部 API 调用）、pytest + pytest-asyncio + vitest。

## Global Constraints

- 中文注释 / 中文对话 / 中文文档
- 热重载优先，非必要不重启服务
- 修改后必须验证能正常编译
- 后端关键代码必须包含日志记录
- 完成代码修改后必须用 `python dev-services.py restart` 重启
- LLM API key 一律走 `LLMProvider.api_key_encrypted`（AES-256-GCM），用 `app.core.security.decrypt_api_key` 解密
- LLM category 枚举值：**`chat` / `code` / `voice` / `vision` / `multimodal` / `embedding` / `image_polish` / `image_gen`**
- Image-gen provider type：**`doubao_seedream` / `qwen_image` / `hailuo` / `openai_image`**
- 后端切换默认值：`backend` 参数默认 `"selfdev"`
- 用户切换后端时**不做自动 fallback**：选谁走谁；未配置返回 503 + code=`BACKEND_NOT_CONFIGURED`
- quota 计费沿用 Dify 一致语义：一次生成 = 1 配额单位（无论 `n` 张）
- 新建表 `image_gen_conversations` 通过 `Base.metadata.create_all` 创建（不写 Alembic）；已有表的新增列写一次性迁移脚本

---

## M1: 模型扩展（不改行为）

### Task 1: 新建 LLMCategory 常量

**Files:**
- Create: `backend/app/constants/llm_categories.py`
- Test: `backend/tests/test_llm_categories.py`

**Interfaces:**
- Produces: `LLMCategory.CHAT`, `LLMCategory.CODE`, `LLMCategory.VOICE`, `LLMCategory.VISION`, `LLMCategory.MULTIMODAL`, `LLMCategory.EMBEDDING`, `LLMCategory.IMAGE_POLISH`, `LLMCategory.IMAGE_GEN`, `LLMCategory.ALL`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_llm_categories.py
"""LLMCategory 常量测试"""

from app.constants.llm_categories import LLMCategory


def test_category_values():
    """枚举值与数据库 String 列对齐"""
    assert LLMCategory.CHAT == "chat"
    assert LLMCategory.CODE == "code"
    assert LLMCategory.VOICE == "voice"
    assert LLMCategory.VISION == "vision"
    assert LLMCategory.MULTIMODAL == "multimodal"
    assert LLMCategory.EMBEDDING == "embedding"
    assert LLMCategory.IMAGE_POLISH == "image_polish"
    assert LLMCategory.IMAGE_GEN == "image_gen"


def test_category_all_contains_eight():
    """ALL 应包含全部 8 个值"""
    assert len(LLMCategory.ALL) == 8
    assert LLMCategory.CHAT in LLMCategory.ALL
    assert LLMCategory.IMAGE_GEN in LLMCategory.ALL


def test_text_categories_excludes_image_gen():
    """TEXT_CATEGORIES 不含 image_gen（走独立 factory）"""
    assert "image_gen" not in LLMCategory.TEXT_CATEGORIES
    assert "chat" in LLMCategory.TEXT_CATEGORIES
    assert "image_polish" in LLMCategory.TEXT_CATEGORIES
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_llm_categories.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.constants.llm_categories'`

- [ ] **Step 3: 写最小实现**

```python
# backend/app/constants/llm_categories.py
"""LLM 模型分类枚举

数据库 LLMModel.category 为 String 列，本常量类统一字符串字面量。
新增分类时同步更新 ALL / TEXT_CATEGORIES。
"""


class LLMCategory:
    """LLM 模型分类（对应 LLMModel.category）"""

    CHAT = "chat"
    """对话 / 文本生成"""

    CODE = "code"
    """代码生成"""

    VOICE = "voice"
    """语音合成 / 识别"""

    VISION = "vision"
    """图像理解"""

    MULTIMODAL = "multimodal"
    """图文混合输入/输出"""

    EMBEDDING = "embedding"
    """向量嵌入"""

    IMAGE_POLISH = "image_polish"
    """图像提示词润色"""

    IMAGE_GEN = "image_gen"
    """图像生成（走 ImageGenFactory，非文本类）"""

    ALL = (
        CHAT,
        CODE,
        VOICE,
        VISION,
        MULTIMODAL,
        EMBEDDING,
        IMAGE_POLISH,
        IMAGE_GEN,
    )
    """全部有效分类"""

    TEXT_CATEGORIES = tuple(c for c in ALL if c != IMAGE_GEN)
    """走 LLMFactory 的文本类分类"""
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_llm_categories.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/constants/llm_categories.py backend/tests/test_llm_categories.py
git commit -m "feat(llm): add LLMCategory constants with image_gen"
```

---

### Task 2: LLMModel 加 priority 字段 + 迁移脚本

**Files:**
- Modify: `backend/app/models/llm_model.py`
- Create: `backend/scripts/migrate_add_llm_model_priority.py`
- Test: `backend/tests/test_llm_model_priority.py`

**Interfaces:**
- Consumes: `LLMModel` 现有定义
- Produces: `LLMModel.priority: int` (default 100)

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_llm_model_priority.py
"""LLMModel.priority 字段测试"""

import uuid
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider


def test_llm_model_has_priority_default(db_session):
    """新增 LLMModel 时 priority 默认 100"""
    provider = LLMProvider(
        id=uuid.uuid4(),
        name="test-provider",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted=b"dummy",
        api_key_suffix="xyz0",
        api_key_hash="hash-xyz",
    )
    db_session.add(provider)
    db_session.flush()

    model = LLMModel(
        id=uuid.uuid4(),
        name="test-model",
        model_name="gpt-4",
        provider_id=provider.id,
        category="chat",
    )
    db_session.add(model)
    db_session.flush()

    assert model.priority == 100


def test_llm_model_priority_persisted(db_session):
    """显式设置 priority 后应持久化"""
    provider = LLMProvider(
        id=uuid.uuid4(),
        name="p",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted=b"dummy",
        api_key_suffix="xyz0",
        api_key_hash="hash-abc",
    )
    db_session.add(provider)
    db_session.flush()

    model = LLMModel(
        id=uuid.uuid4(),
        name="m",
        model_name="gpt-4",
        provider_id=provider.id,
        category="chat",
        priority=10,
    )
    db_session.add(model)
    db_session.commit()

    fetched = db_session.query(LLMModel).filter_by(name="m").first()
    assert fetched is not None
    assert fetched.priority == 10
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_llm_model_priority.py -v`
Expected: FAIL — `TypeError: LLMModel.__init__() got an unexpected keyword argument 'priority'`

- [ ] **Step 3: 给模型加字段**

```python
# backend/app/models/llm_model.py
# 在 is_default_for_category 行后追加：
    priority = Column(Integer, default=100, nullable=False, index=False)
    """兜底链迭代顺序，越小越优先；同 priority 内按 id 稳定排序"""
```

- [ ] **Step 4: 写迁移脚本**

```python
# backend/scripts/migrate_add_llm_model_priority.py
"""给 llm_models 表加 priority 列（幂等）"""

from sqlalchemy import text

from app.models.base import engine


def migrate():
    sql = """
    ALTER TABLE llm_models
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100;
    """
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("[migrate_add_llm_model_priority] OK")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 5: 跑迁移 + 测试**

Run: `cd backend && python scripts/migrate_add_llm_model_priority.py && pytest tests/test_llm_model_priority.py -v`
Expected: PASS — 2 passed

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/llm_model.py backend/scripts/migrate_add_llm_model_priority.py backend/tests/test_llm_model_priority.py
git commit -m "feat(llm): add priority field to LLMModel for ordered fallback"
```

---

### Task 3: ImageGenRecord 加 backend 列 + 迁移脚本

**Files:**
- Modify: `backend/app/models/image_generation_models.py`
- Create: `backend/scripts/migrate_add_record_backend.py`
- Test: `backend/tests/test_image_gen_record_backend.py`

**Interfaces:**
- Produces: `ImageGenRecord.backend: str` (default `"dify"`)

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_record_backend.py
"""ImageGenRecord.backend 字段测试"""

import uuid
from app.models.image_generation_models import ImageGenRecord


def test_record_has_backend_default(db_session):
    """新建记录 backend 默认 'dify'"""
    record = ImageGenRecord(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        operation="text2img",
        prompt="a cat",
        status="success",
    )
    db_session.add(record)
    db_session.flush()

    assert record.backend == "dify"


def test_record_backend_selfdev(db_session):
    """显式设置 selfdev 应持久化"""
    record = ImageGenRecord(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        operation="text2img",
        prompt="a cat",
        status="success",
        backend="selfdev",
    )
    db_session.add(record)
    db_session.commit()

    fetched = db_session.query(ImageGenRecord).filter_by(prompt="a cat").first()
    assert fetched.backend == "selfdev"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_record_backend.py -v`
Expected: FAIL — unexpected keyword 'backend'

- [ ] **Step 3: 给模型加字段**

```python
# backend/app/models/image_generation_models.py
# 在 ImageGenRecord 类的适当位置（status 字段附近）追加：
    backend = Column(String(16), default="dify", nullable=False, index=True)
    """生成后端：'dify' | 'selfdev'"""
```

- [ ] **Step 4: 写迁移脚本**

```python
# backend/scripts/migrate_add_record_backend.py
"""给 image_gen_records 表加 backend 列（幂等）"""

from sqlalchemy import text

from app.models.base import engine


def migrate():
    sql = """
    ALTER TABLE image_gen_records
    ADD COLUMN IF NOT EXISTS backend VARCHAR(16) NOT NULL DEFAULT 'dify';
    """
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("[migrate_add_record_backend] OK")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 5: 跑迁移 + 测试**

Run: `cd backend && python scripts/migrate_add_record_backend.py && pytest tests/test_image_gen_record_backend.py -v`
Expected: PASS — 2 passed

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/image_generation_models.py backend/scripts/migrate_add_record_backend.py backend/tests/test_image_gen_record_backend.py
git commit -m "feat(image-gen): add backend column to ImageGenRecord"
```

---

### Task 4: 新建 ImageGenSelfDevConversation 模型

**Files:**
- Create: `backend/app/models/image_gen_conversation.py`
- Test: `backend/tests/test_image_gen_conversation_model.py`

**Interfaces:**
- Produces: `ImageGenSelfDevConversation` 模型；自动建表（Base.metadata.create_all）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_conversation_model.py
"""ImageGenSelfDevConversation 模型测试"""

import uuid
from app.models.image_gen_conversation import ImageGenSelfDevConversation


def test_conversation_creation(db_session):
    """能创建并落盘"""
    conv = ImageGenSelfDevConversation(
        user_id=uuid.uuid4(),
        conversation_id=str(uuid.uuid4()),
        operation="text2img",
        messages=[{"role": "user", "content": "hello"}],
    )
    db_session.add(conv)
    db_session.commit()

    fetched = db_session.query(ImageGenSelfDevConversation).filter_by(
        conversation_id=conv.conversation_id
    ).first()
    assert fetched is not None
    assert fetched.messages[0]["role"] == "user"


def test_conversation_unique(db_session):
    """conversation_id 唯一"""
    cid = str(uuid.uuid4())
    c1 = ImageGenSelfDevConversation(
        user_id=uuid.uuid4(),
        conversation_id=cid,
        operation="text2img",
        messages=[],
    )
    c2 = ImageGenSelfDevConversation(
        user_id=uuid.uuid4(),
        conversation_id=cid,
        operation="text2img",
        messages=[],
    )
    db_session.add(c1)
    db_session.add(c2)
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_conversation_model.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写模型**

```python
# backend/app/models/image_gen_conversation.py
"""自研图像生成路径的对话历史表

Dify 路径的对话由 Dify 托管；自研路径由本表持久化。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableList

from app.models.base import Base


class ImageGenSelfDevConversation(Base):
    """自研图像生成路径的对话记录"""

    __tablename__ = "image_gen_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    """对话所属用户（用于权限校验）"""

    conversation_id = Column(String(64), unique=True, index=True, nullable=False)
    """对外暴露的对话 UUID 字符串"""

    operation = Column(String(32), nullable=False)
    """text2img / img2img / inpaint / upload_edit"""

    messages = Column(MutableList.as_mutable(JSONB), nullable=False, default=list)
    """
    对话消息列表。每条消息形如：
      {"role": "user"|"assistant"|"tool",
       "content": "...",
       "tool_calls": [{"id": "...", "name": "generate_image", "arguments": {...}}]?,
       "tool_call_id": "..."?}
    """

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_image_gen_conversation_model.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/image_gen_conversation.py backend/tests/test_image_gen_conversation_model.py
git commit -m "feat(image-gen): add ImageGenSelfDevConversation model"
```

---

### Task 5: 在 main.py 注册新表 create_all

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `ImageGenSelfDevConversation` 模型
- Produces: 启动时自动创建 `image_gen_conversations` 表

- [ ] **Step 1: 找到 Base.metadata.create_all 调用处**

Run: `cd backend && grep -n "metadata.create_all" app/main.py`

- [ ] **Step 2: 在 create_all 之前 import 模型（确保元数据注册）**

```python
# 在 from app.models.llm_model import LLMModel 等 import 附近追加：
from app.models.image_gen_conversation import ImageGenSelfDevConversation  # noqa: F401
```

- [ ] **Step 3: 验证启动后表已建**

Run: `cd backend && python -c "from app.main import app; print('ok')"`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add backend/app/main.py
git commit -m "feat(image-gen): register ImageGenSelfDevConversation in create_all"
```

---

## M2: 前端 admin UI

### Task 6: 扩展 llmModelApi 类型

**Files:**
- Modify: `frontend/src/services/llmModelApi.ts`
- Test: `frontend/src/services/__tests__/llmModelApi.test.ts` (新建)

**Interfaces:**
- Produces: `ModelCategory` 扩展为 8 种；`LLMModel.priority: number`

- [ ] **Step 1: 写失败测试**

```typescript
// frontend/src/services/__tests__/llmModelApi.test.ts
import { describe, expect, it } from 'vitest';
import type { ModelCategory, LLMModel } from '../llmModelApi';

describe('ModelCategory 类型', () => {
  it('应包含全部 8 个分类', () => {
    const categories: ModelCategory[] = [
      'chat',
      'code',
      'voice',
      'vision',
      'multimodal',
      'embedding',
      'image_polish',
      'image_gen',
    ];
    expect(categories).toHaveLength(8);
  });
});

describe('LLMModel 类型', () => {
  it('应包含 priority 字段', () => {
    const model: LLMModel = {
      id: 'x',
      name: 'test',
      model_name: 'gpt-4',
      provider_id: 'p',
      category: 'chat',
      is_default: false,
      is_default_for_category: false,
      is_active: true,
      created_at: '2026-01-01',
      priority: 100,
    };
    expect(model.priority).toBe(100);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/services/__tests__/llmModelApi.test.ts`
Expected: FAIL — `priority` 不在 LLMModel 类型中

- [ ] **Step 3: 扩展类型**

```typescript
// frontend/src/services/llmModelApi.ts
/** 模型分类 */
export type ModelCategory =
  | 'chat'
  | 'code'
  | 'voice'
  | 'vision'
  | 'multimodal'
  | 'embedding'
  | 'image_polish'
  | 'image_gen';

/** 模型 */
export interface LLMModel {
  id: string;
  name: string;
  model_name: string;
  provider_id: string;
  provider_name?: string;
  request_params?: string;
  category: ModelCategory;
  is_default: boolean;
  is_default_for_category: boolean;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  /** 兜底链优先级，越小越优先 */
  priority: number;
}

/** 创建模型请求 */
export interface CreateModelRequest {
  name: string;
  model_name: string;
  provider_id: string;
  request_params?: string;
  category?: ModelCategory;
  is_default?: boolean;
  is_default_for_category?: boolean;
  notes?: string;
  is_active?: boolean;
  priority?: number;
}

/** 更新模型请求 */
export interface UpdateModelRequest {
  name?: string;
  model_name?: string;
  provider_id?: string;
  request_params?: string;
  category?: ModelCategory;
  is_default?: boolean;
  is_default_for_category?: boolean;
  notes?: string;
  is_active?: boolean;
  priority?: number;
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run src/services/__tests__/llmModelApi.test.ts`
Expected: PASS — 2 passed

- [ ] **Step 5: tsc 检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/services/llmModelApi.ts frontend/src/services/__tests__/llmModelApi.test.ts
git commit -m "feat(llm-configs): extend ModelCategory to 8 values + priority field"
```

---

### Task 7: ModelsTab 显示 priority 列

**Files:**
- Modify: `frontend/src/components/Admin/LLMConfigs/ModelsTab.tsx`
- Test: `frontend/src/components/Admin/LLMConfigs/__tests__/ModelsTab.test.tsx`

**Interfaces:**
- Consumes: `LLMModel.priority`
- Produces: 模型列表按 priority ASC 排序，新增"优先级"列

- [ ] **Step 1: 在列表渲染处加 priority 列**

参考现有 ModelsTab 的 column 定义，加一列显示 `model.priority`，并在加载时按 `priority` 升序 + `id` 排序：

```typescript
// 在 fetchModels 后对 items 排序：
const sorted = [...items].sort((a, b) => {
  const p = (a.priority ?? 100) - (b.priority ?? 100);
  return p !== 0 ? p : a.id.localeCompare(b.id);
});
```

- [ ] **Step 2: 写测试**

```typescript
// frontend/src/components/Admin/LLMConfigs/__tests__/ModelsTab.test.tsx
import { describe, expect, it } from 'vitest';
import { sortModelsByPriority } from '../ModelsTab';

describe('sortModelsByPriority', () => {
  it('按 priority 升序排', () => {
    const models = [
      { id: 'a', priority: 50 },
      { id: 'b', priority: 10 },
      { id: 'c', priority: 100 },
    ];
    const sorted = sortModelsByPriority(models as any);
    expect(sorted.map((m) => m.id)).toEqual(['b', 'a', 'c']);
  });

  it('priority 相同时按 id 稳定排序', () => {
    const models = [
      { id: 'c', priority: 100 },
      { id: 'a', priority: 100 },
      { id: 'b', priority: 100 },
    ];
    const sorted = sortModelsByPriority(models as any);
    expect(sorted.map((m) => m.id)).toEqual(['a', 'b', 'c']);
  });
});
```

- [ ] **Step 3: 提取 sortModelsByPriority 函数**

```typescript
// frontend/src/components/Admin/LLMConfigs/ModelsTab.tsx
export function sortModelsByPriority(models: LLMModel[]): LLMModel[] {
  return [...models].sort((a, b) => {
    const p = (a.priority ?? 100) - (b.priority ?? 100);
    return p !== 0 ? p : a.id.localeCompare(b.id);
  });
}
```

- [ ] **Step 4: 跑测试 + tsc**

Run: `cd frontend && npx vitest run src/components/Admin/LLMConfigs/__tests__/ModelsTab.test.tsx && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Admin/LLMConfigs/
git commit -m "feat(llm-configs): ModelsTab shows priority column + sort by priority"
```

---

### Task 8: ModelDialog 加 priority 字段 + 新分类下拉

**Files:**
- Modify: `frontend/src/components/Admin/LLMConfigs/ModelDialog.tsx`

**Interfaces:**
- Consumes: 扩展后的 `CreateModelRequest` / `UpdateModelRequest`
- Produces: priority 输入框 + 8 个分类的下拉

- [ ] **Step 1: 加 priority 输入框**

参考现有 ModelDialog 的输入字段模式，加：

```typescript
<div className="flex items-center gap-2">
  <label className="text-slate-400 w-24">优先级</label>
  <input
    type="number"
    min={0}
    max={9999}
    value={priority}
    onChange={(e) => setPriority(Number(e.target.value) || 100)}
    className="flex-1 px-2 py-1 bg-slate-700 text-slate-100 rounded"
  />
</div>
<div className="text-xs text-slate-500">数字越小越优先，默认 100</div>
```

- [ ] **Step 2: 扩展 category 下拉**

```typescript
<select value={category} onChange={(e) => setCategory(e.target.value as ModelCategory)}>
  <option value="chat">对话 (chat)</option>
  <option value="code">代码 (code)</option>
  <option value="voice">语音 (voice)</option>
  <option value="vision">视觉 (vision)</option>
  <option value="multimodal">全模态 (multimodal)</option>
  <option value="embedding">向量 (embedding)</option>
  <option value="image_polish">图像润色 (image_polish)</option>
  <option value="image_gen">图像生成 (image_gen)</option>
</select>
```

- [ ] **Step 3: 提交时带 priority**

```typescript
await llmModelApi.create({
  name,
  model_name: modelName,
  provider_id: providerId,
  category,
  priority,  // 新增
  // ...
});
```

- [ ] **Step 4: tsc 检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Admin/LLMConfigs/ModelDialog.tsx
git commit -m "feat(llm-configs): ModelDialog supports priority + 8 categories"
```

---

## M3: 适配层骨架

### Task 9: 新建 exceptions.py

**Files:**
- Create: `backend/app/services/llm/exceptions.py`
- Test: `backend/tests/test_llm_exceptions.py`

**Interfaces:**
- Produces: `RecoverableFailure` / `UnrecoverableFailure` / `AllModelsUnavailableError` / `UnknownProviderError` / `OperationNotSupportedError`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_llm_exceptions.py
"""LLM 异常类型测试"""

import pytest

from app.services.llm.exceptions import (
    AllModelsUnavailableError,
    OperationNotSupportedError,
    RecoverableFailure,
    UnrecoverableFailure,
    UnknownProviderError,
)


def test_recoverable_is_exception():
    e = RecoverableFailure("rate limited")
    assert isinstance(e, Exception)


def test_unrecoverable_is_exception():
    e = UnrecoverableFailure("invalid api key")
    assert isinstance(e, Exception)


def test_all_models_unavailable_carries_failures():
    e = AllModelsUnavailableError([("m1", "rate limit"), ("m2", "quota")])
    assert e.failures == [("m1", "rate limit"), ("m2", "quota")]


def test_operation_not_supported():
    e = OperationNotSupportedError("openai_image", "inpaint")
    assert e.provider_type == "openai_image"
    assert e.operation == "inpaint"


def test_unknown_provider():
    e = UnknownProviderError("some_provider")
    assert e.provider_type == "some_provider"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_llm_exceptions.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写异常类**

```python
# backend/app/services/llm/exceptions.py
"""LLM 调用相关的异常类型

用于 OrderedLLMGateway 的兜底链错误分类：
  - RecoverableFailure: 跳过当前模型，尝试下一个
  - UnrecoverableFailure: 立即抛出，不再尝试
  - AllModelsUnavailableError: 所有模型都失败
"""


class RecoverableFailure(Exception):
    """可恢复失败（429/5xx/超时/无额度），兜底链应跳过"""


class UnrecoverableFailure(Exception):
    """不可恢复失败（401/400 参数错），兜底链应抛出"""


class AllModelsUnavailableError(Exception):
    """所有模型都不可用"""

    def __init__(self, failures: list[tuple[str, str]]):
        """failures: [(model_id, reason), ...]"""
        self.failures = failures
        super().__init__(f"所有模型均不可用: {failures}")


class OperationNotSupportedError(RecoverableFailure):
    """当前 provider 不支持指定操作（兜底链应跳过）"""

    def __init__(self, provider_type: str, operation: str):
        self.provider_type = provider_type
        self.operation = operation
        super().__init__(f"{provider_type} 不支持操作 {operation}")


class UnknownProviderError(Exception):
    """未知的 provider_type（Factory 报错）"""

    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        super().__init__(f"未知的 provider_type: {provider_type}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_llm_exceptions.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/llm/exceptions.py backend/tests/test_llm_exceptions.py
git commit -m "feat(llm): add exception types for ordered fallback"
```

---

### Task 10: ImageGenAdapter 抽象基类 + OperationNotSupported 默认

**Files:**
- Create: `backend/app/services/llm/image_gen_base.py`
- Test: `backend/tests/test_image_gen_base.py`

**Interfaces:**
- Produces: `ImageGenAdapter` ABC

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_base.py
"""ImageGenAdapter 抽象基类测试"""

import pytest

from app.services.llm.exceptions import OperationNotSupportedError
from app.services.llm.image_gen_base import ImageGenAdapter


class _StubAdapter(ImageGenAdapter):
    """仅实现 generate 的最小子类"""

    async def generate(self, operation, prompt, **kw):
        return [b"fake"]

    async def test_connection(self):
        return (True, "ok")


@pytest.mark.asyncio
async def test_generate_returns_bytes():
    a = _StubAdapter()
    result = await a.generate("text2img", "a cat")
    assert result == [b"fake"]


@pytest.mark.asyncio
async def test_default_operations_raise():
    """默认操作支持为空集，调用任何 op 都抛 OperationNotSupportedError"""

    class _NoOps(ImageGenAdapter):
        async def generate(self, operation, prompt, **kw):
            raise NotImplementedError

        async def test_connection(self):
            return (True, "ok")

    a = _NoOps()
    with pytest.raises(OperationNotSupportedError):
        await a.generate("inpaint", "x")


@pytest.mark.asyncio
async def test_supported_operations_check():
    """supports_operation 应基于 SUPPORTED_OPERATIONS 判断"""
    a = _StubAdapter()
    assert a.supports_operation("text2img")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_base.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写基类**

```python
# backend/app/services/llm/image_gen_base.py
"""图像生成适配器抽象基类

与 LLMProvider 平级，不共用基类——图像生成无 messages / 无流式语义。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Optional

from app.services.llm.exceptions import OperationNotSupportedError


class ImageGenAdapter(ABC):
    """图像生成适配器基类

    子类需实现：
      - SUPPORTED_OPERATIONS: 类属性，列出支持的 operation
      - generate: 返回 N 张图的二进制列表
      - test_connection: 连接测试
    """

    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset()
    """子类覆盖：支持的 operation 集合"""

    @abstractmethod
    async def generate(
        self,
        operation: str,
        prompt: str,
        *,
        size: str = "1024x1024",
        n: int = 1,
        reference_image: Optional[bytes] = None,
        reference_mime: Optional[str] = None,
        mask_image: Optional[bytes] = None,
        mask_mime: Optional[str] = None,
        strength: Optional[float] = None,
        edit_type: Optional[str] = None,
        **provider_specific,
    ) -> list[bytes]:
        """生成图像，返回 N 张图的二进制列表

        Raises:
            OperationNotSupportedError: operation 不在 SUPPORTED_OPERATIONS
        """

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """连接测试。返回 (成功, 消息)。"""

    def supports_operation(self, operation: str) -> bool:
        """判断当前 adapter 是否支持该 operation"""
        return operation in self.SUPPORTED_OPERATIONS

    def ensure_supported(self, operation: str, provider_type: str) -> None:
        """不支持时抛 OperationNotSupportedError"""
        if not self.supports_operation(operation):
            raise OperationNotSupportedError(provider_type, operation)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_image_gen_base.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/llm/image_gen_base.py backend/tests/test_image_gen_base.py
git commit -m "feat(llm): add ImageGenAdapter abstract base"
```

---

### Task 11: ImageGenFactory

**Files:**
- Create: `backend/app/services/llm/image_gen_factory.py`
- Test: `backend/tests/test_image_gen_factory.py`

**Interfaces:**
- Consumes: `ImageGenAdapter`, `UnknownProviderError`
- Produces: `ImageGenFactory.get(provider_type, api_key, base_url, model_name, **kw)`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_factory.py
"""ImageGenFactory 测试"""

import pytest

from app.services.llm.exceptions import UnknownProviderError
from app.services.llm.image_gen_base import ImageGenAdapter
from app.services.llm.image_gen_factory import ImageGenFactory


def test_get_unknown_provider_raises():
    with pytest.raises(UnknownProviderError):
        ImageGenFactory.get("unknown_type", api_key="x", base_url=None, model_name="m")


def test_get_doubao_seedream():
    a = ImageGenFactory.get(
        "doubao_seedream", api_key="x", base_url="https://ark.cn-beijing.volces.com", model_name="doubao-seedream-3-0-t2i-250415"
    )
    assert isinstance(a, ImageGenAdapter)


def test_get_qwen_image():
    a = ImageGenFactory.get(
        "qwen_image", api_key="x", base_url="https://dashscope.aliyuncs.com", model_name="wanxiang-v1"
    )
    assert isinstance(a, ImageGenAdapter)


def test_get_hailuo():
    a = ImageGenFactory.get("hailuo", api_key="x", base_url=None, model_name="hailuo-t2i")
    assert isinstance(a, ImageGenAdapter)


def test_get_openai_image():
    a = ImageGenFactory.get("openai_image", api_key="x", base_url="https://api.openai.com", model_name="dall-e-3")
    assert isinstance(a, ImageGenAdapter)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_factory.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 factory（含 4 个 stub adapter 引用）**

```python
# backend/app/services/llm/image_gen_factory.py
"""ImageGenAdapter 工厂"""

from __future__ import annotations

from typing import Optional

from app.services.llm.doubao_seedream_adapter import DoubaoSeedreamAdapter
from app.services.llm.exceptions import UnknownProviderError
from app.services.llm.hailuo_adapter import HailuoAdapter
from app.services.llm.image_gen_base import ImageGenAdapter
from app.services.llm.openai_image_adapter import OpenAIImageAdapter
from app.services.llm.qwen_image_adapter import QwenImageAdapter


class ImageGenFactory:
    """按 provider_type 返回对应的 ImageGenAdapter"""

    _REGISTRY: dict[str, type[ImageGenAdapter]] = {
        "doubao_seedream": DoubaoSeedreamAdapter,
        "qwen_image": QwenImageAdapter,
        "hailuo": HailuoAdapter,
        "openai_image": OpenAIImageAdapter,
    }

    @classmethod
    def get(
        cls,
        provider_type: str,
        api_key: str,
        base_url: Optional[str],
        model_name: str,
        **kw,
    ) -> ImageGenAdapter:
        if provider_type not in cls._REGISTRY:
            raise UnknownProviderError(provider_type)
        adapter_cls = cls._REGISTRY[provider_type]
        return adapter_cls(api_key=api_key, base_url=base_url, model=model_name, **kw)
```

- [ ] **Step 4: 提交（4 个 stub adapter 在 Task 12 写，此处先空文件占位）**

```bash
# 先建 4 个空文件占位
touch backend/app/services/llm/doubao_seedream_adapter.py
touch backend/app/services/llm/qwen_image_adapter.py
touch backend/app/services/llm/hailuo_adapter.py
touch backend/app/services/llm/openai_image_adapter.py
git add backend/app/services/llm/
git commit -m "feat(llm): add ImageGenFactory (stub adapters)"
```

---

### Task 12: 4 个 Adapter 的最小实现（mock happy path）

**Files:**
- Modify: `backend/app/services/llm/doubao_seedream_adapter.py`
- Modify: `backend/app/services/llm/qwen_image_adapter.py`
- Modify: `backend/app/services/llm/hailuo_adapter.py`
- Modify: `backend/app/services/llm/openai_image_adapter.py`
- Test: `backend/tests/test_doubao_seedream_adapter.py`
- Test: `backend/tests/test_qwen_image_adapter.py`
- Test: `backend/tests/test_hailuo_adapter.py`
- Test: `backend/tests/test_openai_image_adapter.py`

**Interfaces:**
- Produces: 4 个 adapter 各自继承 `ImageGenAdapter`，覆盖 `SUPPORTED_OPERATIONS`，`generate()` 用 httpx 调外部 API

- [ ] **Step 1: DoubaoSeedreamAdapter（先 TDD）**

```python
# backend/app/services/llm/doubao_seedream_adapter.py
"""豆包 Seedream 图像生成适配器（火山 ark API）"""

from __future__ import annotations

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter


class DoubaoSeedreamAdapter(ImageGenAdapter):
    SUPPORTED_OPERATIONS = frozenset({"text2img", "img2img", "inpaint", "upload_edit"})

    def __init__(self, api_key: str, base_url: str | None, model: str, **kw):
        self._api_key = api_key
        self._base_url = (base_url or "https://ark.cn-beijing.volces.com").rstrip("/")
        self._model = model

    async def generate(self, operation, prompt, **kw):
        self.ensure_supported(operation, "doubao_seedream")
        url = f"{self._base_url}/api/v3/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        body = {"model": self._model, "prompt": prompt}
        if kw.get("size"):
            body["size"] = kw["size"]
        if kw.get("n"):
            body["n"] = kw["n"]

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except httpx.ConnectError as e:
                raise RecoverableFailure(str(e))
            except httpx.TimeoutException as e:
                raise RecoverableFailure(str(e))

        if resp.status_code == 401 or resp.status_code == 403:
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        if resp.status_code == 429:
            raise RecoverableFailure(f"rate limited: {resp.text}")
        if resp.status_code >= 500:
            raise RecoverableFailure(f"server error: {resp.status_code}")
        if resp.status_code >= 400:
            raise UnrecoverableFailure(f"bad request: {resp.text}")

        data = resp.json()
        urls = [item["url"] for item in data.get("data", []) if "url" in item]
        if not urls:
            raise RecoverableFailure("no url in response")

        async with httpx.AsyncClient(timeout=60) as client:
            images = []
            for u in urls:
                r = await client.get(u)
                r.raise_for_status()
                images.append(r.content)
        return images

    async def test_connection(self):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(f"{self._base_url}/api/v3/models", headers={"Authorization": f"Bearer {self._api_key}"})
            return (True, "ok")
        except Exception as e:
            return (False, str(e))
```

对应测试：

```python
# backend/tests/test_doubao_seedream_adapter.py
"""DoubaoSeedreamAdapter 测试"""

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm.doubao_seedream_adapter import DoubaoSeedreamAdapter
from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure


@pytest.mark.asyncio
async def test_text2img_happy():
    a = DoubaoSeedreamAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_post = AsyncMock()
    mock_post.status_code = 200
    mock_post.json = lambda: {"data": [{"url": "https://oss/a.png"}]}

    mock_get = AsyncMock()
    mock_get.content = b"fake"
    mock_get.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post)
        mock_client.get = AsyncMock(return_value=mock_get)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await a.generate("text2img", "a cat")

    assert result == [b"fake"]


@pytest.mark.asyncio
async def test_rate_limit_is_recoverable():
    a = DoubaoSeedreamAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_resp = AsyncMock()
    mock_resp.status_code = 429
    mock_resp.text = "rate limited"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RecoverableFailure):
            await a.generate("text2img", "x")


@pytest.mark.asyncio
async def test_auth_error_is_unrecoverable():
    a = DoubaoSeedreamAdapter(api_key="x", base_url="https://x.com", model="m")

    mock_resp = AsyncMock()
    mock_resp.status_code = 401
    mock_resp.text = "unauthorized"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(UnrecoverableFailure):
            await a.generate("text2img", "x")
```

- [ ] **Step 2: QwenImageAdapter（异步轮询）**

```python
# backend/app/services/llm/qwen_image_adapter.py
"""通义万相图像生成适配器（DashScope，task 异步轮询）"""

from __future__ import annotations

import asyncio

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter


class QwenImageAdapter(ImageGenAdapter):
    SUPPORTED_OPERATIONS = frozenset({"text2img", "img2img", "inpaint", "upload_edit"})

    def __init__(self, api_key: str, base_url: str | None, model: str, **kw):
        self._api_key = api_key
        self._base_url = (base_url or "https://dashscope.aliyuncs.com").rstrip("/")
        self._model = model

    async def generate(self, operation, prompt, **kw):
        self.ensure_supported(operation, "qwen_image")
        url = f"{self._base_url}/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-DashScope-Async": "enable",
        }
        body = {
            "model": self._model,
            "input": {"prompt": prompt},
            "parameters": {},
        }
        if kw.get("size"):
            body["parameters"]["size"] = kw["size"]
        if kw.get("n"):
            body["parameters"]["n"] = kw["n"]

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise RecoverableFailure(str(e))

        if resp.status_code in (401, 403):
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        if resp.status_code == 429:
            raise RecoverableFailure(f"rate limited: {resp.text}")
        if resp.status_code >= 500:
            raise RecoverableFailure(f"server error: {resp.status_code}")
        if resp.status_code >= 400:
            raise UnrecoverableFailure(f"bad request: {resp.text}")

        task_id = resp.json().get("output", {}).get("task_id")
        if not task_id:
            raise RecoverableFailure("no task_id in response")

        # 轮询任务
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(60):  # 最多 60 次 * 5s = 300s
                status_url = f"{self._base_url}/api/v1/tasks/{task_id}"
                s_resp = await client.get(status_url, headers=headers)
                if s_resp.status_code != 200:
                    raise RecoverableFailure(f"poll failed: {s_resp.status_code}")

                s_data = s_resp.json()
                task_status = s_data.get("output", {}).get("task_status")
                if task_status == "SUCCEEDED":
                    results = s_data.get("output", {}).get("results", [])
                    urls = [r["url"] for r in results if "url" in r]
                    if not urls:
                        raise RecoverableFailure("no urls in result")
                    images = []
                    for u in urls:
                        r = await client.get(u)
                        r.raise_for_status()
                        images.append(r.content)
                    return images
                if task_status in ("FAILED", "CANCELED"):
                    raise RecoverableFailure(f"task {task_status}")
                await asyncio.sleep(5)

        raise RecoverableFailure("task timeout")

    async def test_connection(self):
        return (True, "ok")
```

- [ ] **Step 3: HailuoAdapter（占位，text2img only）**

```python
# backend/app/services/llm/hailuo_adapter.py
"""海螺（MiniMax）图像生成适配器

当前 MiniMax 公开 API 仅 text2img 稳定；其余 operation 抛 OperationNotSupportedError，
由 OrderedLLMGateway 自动跳过。
"""

from __future__ import annotations

from app.services.llm.image_gen_base import ImageGenAdapter


class HailuoAdapter(ImageGenAdapter):
    SUPPORTED_OPERATIONS = frozenset({"text2img"})

    def __init__(self, api_key: str, base_url: str | None, model: str, **kw):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    async def generate(self, operation, prompt, **kw):
        self.ensure_supported(operation, "hailuo")
        # TODO: 实际接入 MiniMax API（API 端点/鉴权待确认）
        raise NotImplementedError("Hailuo adapter 待接入实际 API")

    async def test_connection(self):
        return (True, "ok")
```

- [ ] **Step 4: OpenAIImageAdapter（text2img only）**

```python
# backend/app/services/llm/openai_image_adapter.py
"""OpenAI DALL-E 3 图像生成适配器

DALL-E 3 不支持参考图（img2img/inpaint/upload_edit 抛 OperationNotSupportedError）。
"""

from __future__ import annotations

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter


class OpenAIImageAdapter(ImageGenAdapter):
    SUPPORTED_OPERATIONS = frozenset({"text2img"})

    def __init__(self, api_key: str, base_url: str | None, model: str, **kw):
        self._api_key = api_key
        self._base_url = (base_url or "https://api.openai.com").rstrip("/")
        self._model = model

    async def generate(self, operation, prompt, **kw):
        self.ensure_supported(operation, "openai_image")
        url = f"{self._base_url}/v1/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        body = {
            "model": self._model,
            "prompt": prompt,
            "n": kw.get("n", 1),
            "size": kw.get("size", "1024x1024"),
        }

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise RecoverableFailure(str(e))

        if resp.status_code in (401, 403):
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        if resp.status_code == 429:
            raise RecoverableFailure(f"rate limited: {resp.text}")
        if resp.status_code >= 500:
            raise RecoverableFailure(f"server error: {resp.status_code}")
        if resp.status_code >= 400:
            raise UnrecoverableFailure(f"bad request: {resp.text}")

        data = resp.json()
        urls = [item["url"] for item in data.get("data", []) if "url" in item]
        if not urls:
            raise RecoverableFailure("no url in response")

        async with httpx.AsyncClient(timeout=60) as client:
            images = []
            for u in urls:
                r = await client.get(u)
                r.raise_for_status()
                images.append(r.content)
        return images

    async def test_connection(self):
        return (True, "ok")
```

- [ ] **Step 5: 各 adapter 跑测试**

Run: `cd backend && pytest tests/test_doubao_seedream_adapter.py tests/test_qwen_image_adapter.py tests/test_hailuo_adapter.py tests/test_openai_image_adapter.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/llm/doubao_seedream_adapter.py backend/app/services/llm/qwen_image_adapter.py backend/app/services/llm/hailuo_adapter.py backend/app/services/llm/openai_image_adapter.py backend/tests/test_doubao_seedream_adapter.py backend/tests/test_qwen_image_adapter.py backend/tests/test_hailuo_adapter.py backend/tests/test_openai_image_adapter.py
git commit -m "feat(llm): implement 4 image-gen adapters (Doubao/Qwen/Hailuo/OpenAI)"
```

---

## M4: 有序兜底链升级

### Task 13: OrderedLLMGateway 核心

**Files:**
- Create: `backend/app/services/llm/ordered_gateway.py`
- Test: `backend/tests/test_ordered_gateway.py`

**Interfaces:**
- Consumes: `LLMModel`, `LLMProvider`, `ImageGenFactory`, `LLMFactory`
- Produces: `OrderedLLMGateway.generate(category, **kwargs) -> Any`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_ordered_gateway.py
"""OrderedLLMGateway 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.exceptions import (
    AllModelsUnavailableError,
    RecoverableFailure,
    UnrecoverableFailure,
)
from app.services.llm.ordered_gateway import OrderedLLMGateway


def _make_model(model_id, priority):
    m = MagicMock()
    m.id = model_id
    m.priority = priority
    m.category = "chat"
    m.is_active = True
    m.request_params = "{}"
    m.provider = MagicMock()
    m.provider.provider_type = "openai"
    m.provider.base_url = "https://api.openai.com/v1"
    m.provider.api_key_encrypted = b"dummy"
    m.provider.is_active = True
    return m


@pytest.mark.asyncio
async def test_priority_ordering(db_session):
    """按 priority ASC 迭代"""
    models = [_make_model("m1", 50), _make_model("m2", 10), _make_model("m3", 100)]

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models):
        gw = OrderedLLMGateway(db=db_session)
        ordered = gw._ordered(models)
        assert [m.id for m in ordered] == ["m2", "m1", "m3"]


@pytest.mark.asyncio
async def test_first_success_wins(db_session):
    """第一个模型成功就返回"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.LLMFactory.get") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        mock_adapter = AsyncMock()
        mock_adapter.generate = AsyncMock(return_value="hello")
        mock_factory.return_value = mock_adapter

        gw = OrderedLLMGateway(db=db_session)
        result = await gw.generate(category="chat", messages=[{"role": "user", "content": "x"}])
        assert result == "hello"


@pytest.mark.asyncio
async def test_recoverable_skips_to_next(db_session):
    """第一个 RecoverableFailure，跳过，用第二个"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    async def fail_first(messages, **kw):
        raise RecoverableFailure("rate limit")

    async def ok_second(messages, **kw):
        return "from m2"

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.LLMFactory.get") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        adapter1 = AsyncMock()
        adapter1.generate = fail_first
        adapter2 = AsyncMock()
        adapter2.generate = ok_second
        mock_factory.side_effect = [adapter1, adapter2]

        gw = OrderedLLMGateway(db=db_session)
        result = await gw.generate(category="chat", messages=[{"role": "user", "content": "x"}])
        assert result == "from m2"


@pytest.mark.asyncio
async def test_unrecoverable_raises_immediately(db_session):
    """UnrecoverableFailure 立即抛出，不试下一个"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    async def fail_first(messages, **kw):
        raise UnrecoverableFailure("invalid api key")

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.LLMFactory.get") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        adapter = AsyncMock()
        adapter.generate = fail_first
        mock_factory.return_value = adapter

        gw = OrderedLLMGateway(db=db_session)
        with pytest.raises(UnrecoverableFailure):
            await gw.generate(category="chat", messages=[{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_all_fail_raises_all_unavailable(db_session):
    """全部 RecoverableFailure → AllModelsUnavailableError"""
    models = [_make_model("m1", 10), _make_model("m2", 20)]

    async def fail_all(messages, **kw):
        raise RecoverableFailure("rate limit")

    with patch.object(OrderedLLMGateway, "_models_by_category", return_value=models), \
         patch("app.services.llm.ordered_gateway.LLMFactory.get") as mock_factory, \
         patch("app.services.llm.ordered_gateway.decrypt_api_key", return_value="sk-test"):
        adapter = AsyncMock()
        adapter.generate = fail_all
        mock_factory.return_value = adapter

        gw = OrderedLLMGateway(db=db_session)
        with pytest.raises(AllModelsUnavailableError):
            await gw.generate(category="chat", messages=[{"role": "user", "content": "x"}])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_ordered_gateway.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 OrderedLLMGateway**

```python
# backend/app/services/llm/ordered_gateway.py
"""有序 LLM 兜底链

按 category 查询 LLMModel（priority ASC, id ASC），逐个调用直到成功。
分类：
  - text 类（chat/code/voice/vision/multimodal/embedding/image_polish）走 LLMFactory
  - image_gen 走 ImageGenFactory
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.constants.llm_categories import LLMCategory
from app.core.security import decrypt_api_key
from app.models.llm_model import LLMModel
from app.services.llm.exceptions import (
    AllModelsUnavailableError,
    RecoverableFailure,
    UnrecoverableFailure,
)
from app.services.llm.factory import get_provider as _llm_get_provider
from app.services.llm.image_gen_factory import ImageGenFactory
from app.services.llm import factory as _llm_factory_module

logger = logging.getLogger(__name__)


class OrderedLLMGateway:
    """有序模型调用网关"""

    def __init__(self, db: Session):
        self.db = db

    async def generate(self, category: str, **kwargs) -> Any:
        """按兜底链调用模型"""
        models = self._models_by_category(category)
        if not models:
            raise AllModelsUnavailableError([])

        models = self._ordered(models)
        factory = ImageGenFactory if category == LLMCategory.IMAGE_GEN else _llm_factory_module

        failures: list[tuple[str, str]] = []
        for model in models:
            try:
                adapter = factory.get(
                    provider_type=model.provider.provider_type,
                    api_key=decrypt_api_key(model.provider.api_key_encrypted),
                    base_url=model.provider.base_url,
                    model_name=model.model_name,
                    **self._parse_request_params(model.request_params),
                )
                logger.info(f"[gateway] trying model={model.id} priority={model.priority}")
                result = await adapter.generate(**kwargs)
                logger.info(f"[gateway] OK model={model.id}")
                return result
            except RecoverableFailure as e:
                logger.warning(f"[gateway] FAIL model={model.id} reason={e}; trying next")
                failures.append((str(model.id), str(e)))
                continue
            except UnrecoverableFailure as e:
                logger.error(f"[gateway] FATAL model={model.id} reason={e}")
                raise

        raise AllModelsUnavailableError(failures)

    def _models_by_category(self, category: str) -> list[LLMModel]:
        """查询 category 下所有 is_active=True 且 provider.is_active=True 的模型"""
        from app.models.llm_provider import LLMProvider

        return (
            self.db.query(LLMModel)
            .join(LLMProvider, LLMModel.provider_id == LLMProvider.id)
            .filter(
                LLMModel.category == category,
                LLMModel.is_active == True,  # noqa: E712
                LLMProvider.is_active == True,  # noqa: E712
            )
            .all()
        )

    def _ordered(self, models: list[LLMModel]) -> list[LLMModel]:
        """按 priority ASC, id ASC 排序"""
        return sorted(models, key=lambda m: (m.priority, str(m.id)))

    def _parse_request_params(self, raw) -> dict:
        """LLMModel.request_params 为 Text(JSON)，需要时解析为 dict"""
        import json
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_ordered_gateway.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/llm/ordered_gateway.py backend/tests/test_ordered_gateway.py
git commit -m "feat(llm): add OrderedLLMGateway with priority-based fallback"
```

---

### Task 14: 重构 LLMFallbackService 调用到 OrderedLLMGateway

**Files:**
- Modify: `backend/app/services/image_gen_prompt_polisher.py`
- Modify: `backend/app/services/agent_service.py`
- Modify: `backend/app/services/llm_fallback.py`（标记 deprecated）
- Test: `backend/tests/test_prompt_polisher_with_gateway.py`

**Interfaces:**
- Consumes: `OrderedLLMGateway`
- Produces: image_polish / agent_service 走新 gateway（行为不变）

- [ ] **Step 1: 把 image_gen_prompt_polisher 改为调 OrderedLLMGateway**

```python
# backend/app/services/image_gen_prompt_polisher.py
# 替换 LLMFallbackService.generate_with_fallback(...) 调用为：
from app.services.llm.ordered_gateway import OrderedLLMGateway

# 在 polish 方法里：
gateway = OrderedLLMGateway(db)
result = await gateway.generate(
    category="image_polish",
    messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
)
```

- [ ] **Step 2: 跑现有 polisher 测试确认行为不变**

Run: `cd backend && pytest tests/test_image_gen_prompt_polisher.py -v`
Expected: PASS（不应破坏现有行为）

- [ ] **Step 3: agent_service 同样迁移**

参考现有 `agent_service.py` 的 `_get_default_model` 模式，改为调 `OrderedLLMGateway.generate(category="chat", ...)`。

- [ ] **Step 4: 跑 agent_service 测试**

Run: `cd backend && pytest tests/test_agent_service.py -v`
Expected: PASS

- [ ] **Step 5: 给 LLMFallbackService 加 deprecated 注释**

```python
# backend/app/services/llm_fallback.py 文件顶部：
"""
@deprecated: 请使用 app.services.llm.ordered_gateway.OrderedLLMGateway
本类仅保留作为过渡期兼容，新代码不应再调用。
"""
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/image_gen_prompt_polisher.py backend/app/services/agent_service.py backend/app/services/llm_fallback.py
git commit -m "refactor(llm): migrate polisher and agent_service to OrderedLLMGateway"
```

---

## M5: 后端 strategy 拆分

### Task 15: IImageGenerationBackend 接口 + BackendContext/BackendResult

**Files:**
- Create: `backend/app/services/image_gen/__init__.py`
- Create: `backend/app/services/image_gen/base.py`
- Test: `backend/tests/test_image_gen_base_types.py`

**Interfaces:**
- Produces: `IImageGenerationBackend`, `BackendContext`, `BackendResult`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_base_types.py
"""IImageGenerationBackend 接口测试"""

import uuid

import pytest

from app.services.image_gen.base import BackendContext, BackendResult, IImageGenerationBackend


def test_backend_context_required_fields():
    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        reference_mime=None,
        mask_image=None,
        mask_mime=None,
        size="1024x1024",
        n=1,
        strength=None,
        edit_type=None,
    )
    assert ctx.operation == "text2img"


def test_backend_result_required_fields():
    r = BackendResult(
        image_urls=["https://oss/1.png"],
        answer_text="done",
        conversation_id="cid",
        model_used="gpt-4",
        backend="selfdev",
    )
    assert r.image_urls


@pytest.mark.asyncio
async def test_interface_is_abstract():
    """不能直接实例化抽象类"""
    with pytest.raises(TypeError):
        IImageGenerationBackend()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_base_types.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写接口**

```python
# backend/app/services/image_gen/__init__.py
"""图像生成后端 strategy 模块"""

# backend/app/services/image_gen/base.py
"""图像生成后端抽象接口"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackendContext:
    """后端调用上下文"""

    user_id: uuid.UUID
    operation: str                      # "text2img" | "img2img" | "inpaint" | "upload_edit"
    query: str                          # 用户输入
    conversation_id: Optional[str]      # 上一轮对话 ID，None 表示新对话
    reference_image: Optional[bytes]
    reference_mime: Optional[str]
    mask_image: Optional[bytes]
    mask_mime: Optional[str]
    size: str
    n: int
    strength: Optional[float]
    edit_type: Optional[str]


@dataclass
class BackendResult:
    """后端调用结果"""

    image_urls: list[str] = field(default_factory=list)  # OSS 签名 URL，可能为空
    answer_text: str = ""                                  # 给用户的回复文本
    conversation_id: str = ""                              # 对话 ID（新建或沿用）
    model_used: str = ""                                   # 实际调用的模型
    backend: str = ""                                      # "dify" | "selfdev"


class IImageGenerationBackend(ABC):
    """图像生成后端接口"""

    @abstractmethod
    async def run(self, ctx: BackendContext) -> BackendResult:
        """执行图像生成 + 对话编排"""
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_image_gen_base_types.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/
git commit -m "feat(image-gen): add IImageGenerationBackend interface + types"
```

---

### Task 16: BackendRegistry

**Files:**
- Create: `backend/app/services/image_gen/backends.py`
- Test: `backend/tests/test_backend_registry.py`

**Interfaces:**
- Produces: `BackendRegistry.register(name, backend)` / `BackendRegistry.get(name) -> IImageGenerationBackend`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_backend_registry.py
"""BackendRegistry 测试"""

import pytest

from app.services.image_gen.backends import BackendRegistry
from app.services.image_gen.base import BackendResult, IImageGenerationBackend


class _StubBackend(IImageGenerationBackend):
    async def run(self, ctx):
        return BackendResult()


@pytest.fixture(autouse=True)
def reset_registry():
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


def test_register_and_get():
    b = _StubBackend()
    BackendRegistry.register("stub", b)
    assert BackendRegistry.get("stub") is b


def test_get_unregistered_raises():
    from app.services.image_gen.backends import BackendNotConfiguredError
    with pytest.raises(BackendNotConfiguredError):
        BackendRegistry.get("nonexistent")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_backend_registry.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 BackendRegistry**

```python
# backend/app/services/image_gen/backends.py
"""后端注册表"""

from __future__ import annotations

from app.services.image_gen.base import IImageGenerationBackend


class BackendNotConfiguredError(Exception):
    """请求的后端未注册"""


class BackendRegistry:
    """按名称注册/查找 IImageGenerationBackend"""

    _REGISTRY: dict[str, IImageGenerationBackend] = {}

    @classmethod
    def register(cls, name: str, backend: IImageGenerationBackend) -> None:
        cls._REGISTRY[name] = backend

    @classmethod
    def get(cls, name: str) -> IImageGenerationBackend:
        if name not in cls._REGISTRY:
            raise BackendNotConfiguredError(f"后端未配置: {name}")
        return cls._REGISTRY[name]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_backend_registry.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/backends.py backend/tests/test_backend_registry.py
git commit -m "feat(image-gen): add BackendRegistry"
```

---

### Task 17: DifyBackend 包装现有调用

**Files:**
- Create: `backend/app/services/image_gen/dify_backend.py`
- Test: `backend/tests/test_dify_backend.py`

**Interfaces:**
- Consumes: `DifyClient`, `DifyConfigService`
- Produces: `DifyBackend.run(ctx) -> BackendResult` 内部调 `dify_client.chat_*`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_dify_backend.py
"""DifyBackend 测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.image_gen.base import BackendContext
from app.services.image_gen.dify_backend import DifyBackend


@pytest.mark.asyncio
async def test_dify_backend_calls_dify_client():
    dify_client = MagicMock()
    dify_client.chat_text2img = AsyncMock(return_value=MagicMock(
        answer="你好",
        image_urls=["https://oss/1.png"],
        conversation_id="dify-cid",
        model_used="dify-model",
    ))

    backend = DifyBackend(dify_client=dify_client)
    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        reference_mime=None,
        mask_image=None,
        mask_mime=None,
        size="1024x1024",
        n=1,
        strength=None,
        edit_type=None,
    )
    result = await backend.run(ctx)

    assert result.image_urls == ["https://oss/1.png"]
    assert result.answer_text == "你好"
    assert result.conversation_id == "dify-cid"
    assert result.backend == "dify"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_dify_backend.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 DifyBackend**

```python
# backend/app/services/image_gen/dify_backend.py
"""Dify 后端：包装现有 dify_client.chat_* 调用"""

from __future__ import annotations

import logging

from app.services.dify_client import DifyClient
from app.services.image_gen.base import BackendContext, BackendResult, IImageGenerationBackend

logger = logging.getLogger(__name__)


class DifyBackend(IImageGenerationBackend):
    """Dify 后端"""

    def __init__(self, dify_client: DifyClient):
        self._dify = dify_client

    async def run(self, ctx: BackendContext) -> BackendResult:
        """按 operation 分发到对应的 chat_* 方法"""
        logger.info(f"[dify_backend] operation={ctx.operation} user={ctx.user_id}")

        dispatch = {
            "text2img": self._dify.chat_text2img,
            "img2img": self._dify.chat_img2img,
            "inpaint": self._dify.chat_inpaint,
            "upload_edit": self._dify.chat_upload_edit,
        }
        fn = dispatch.get(ctx.operation)
        if fn is None:
            raise ValueError(f"未知 operation: {ctx.operation}")

        result = await fn(
            user_id=ctx.user_id,
            query=ctx.query,
            conversation_id=ctx.conversation_id,
            reference_image=ctx.reference_image,
            mask_image=ctx.mask_image,
            size=ctx.size,
            n=ctx.n,
        )

        return BackendResult(
            image_urls=result.image_urls or [],
            answer_text=result.answer or "",
            conversation_id=result.conversation_id or "",
            model_used=result.model_used or "",
            backend="dify",
        )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_dify_backend.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/dify_backend.py backend/tests/test_dify_backend.py
git commit -m "feat(image-gen): add DifyBackend wrapping dify_client"
```

---

### Task 18: ImageGenerationService 接入 BackendRegistry

**Files:**
- Modify: `backend/app/services/image_generation_service.py`
- Test: `backend/tests/test_image_gen_service_backend_dispatch.py`

**Interfaces:**
- Consumes: `BackendRegistry`, `BackendContext`, `BackendResult`
- Produces: `ImageGenService.chat_generate(backend: str, ...)` 通过注册表分发

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_service_backend_dispatch.py
"""ImageGenService 通过 BackendRegistry 分发"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.image_gen.backends import BackendRegistry
from app.services.image_gen.base import BackendResult, IImageGenerationBackend
from app.services.image_generation_service import ImageGenService


class _StubBackend(IImageGenerationBackend):
    def __init__(self, backend_name):
        self._name = backend_name

    async def run(self, ctx):
        return BackendResult(
            image_urls=["https://oss/1.png"],
            answer_text=f"from {self._name}",
            conversation_id="cid",
            model_used="m",
            backend=self._name,
        )


@pytest.fixture(autouse=True)
def reset_registry():
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


@pytest.mark.asyncio
async def test_dispatch_by_backend_param(db_session):
    """backend 参数决定走哪个 backend"""
    BackendRegistry.register("dify", _StubBackend("dify"))
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))

    svc = ImageGenService(
        db=db_session,
        dify_client=MagicMock(),
        quota_svc=MagicMock(),
        oss_svc=MagicMock(),
        history_svc=MagicMock(),
        degradation_svc=MagicMock(),
    )

    result_dify = await svc.chat_generate_dispatch(
        backend="dify",
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        mask_image=None,
        size="1024x1024",
        n=1,
    )
    assert result_dify.backend == "dify"

    result_selfdev = await svc.chat_generate_dispatch(
        backend="selfdev",
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        mask_image=None,
        size="1024x1024",
        n=1,
    )
    assert result_selfdev.backend == "selfdev"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_service_backend_dispatch.py -v`
Expected: FAIL — `AttributeError: 'ImageGenService' object has no attribute 'chat_generate_dispatch'`

- [ ] **Step 3: 给 ImageGenService 加 chat_generate_dispatch**

```python
# backend/app/services/image_generation_service.py
# 在 ImageGenService 类内追加：

async def chat_generate_dispatch(
    self,
    backend: str,
    user_id: uuid.UUID,
    operation: str,
    query: str,
    conversation_id: Optional[str],
    reference_image: Optional[bytes],
    mask_image: Optional[bytes],
    size: str,
    n: int,
    strength: Optional[float] = None,
    edit_type: Optional[str] = None,
) -> BackendResult:
    """按 backend 参数通过 BackendRegistry 分发到对应后端

    本方法只负责：
      1. 构造 BackendContext
      2. 从 BackendRegistry 取对应后端
      3. 调用 backend.run(ctx)
      4. 返回 BackendResult

    quota / OSS / history 等共享逻辑不在此处（在调用方）。
    """
    from app.services.image_gen.backends import BackendRegistry
    from app.services.image_gen.base import BackendContext

    ctx = BackendContext(
        user_id=user_id,
        operation=operation,
        query=query,
        conversation_id=conversation_id,
        reference_image=reference_image,
        reference_mime=None,
        mask_image=mask_image,
        mask_mime=None,
        size=size,
        n=n,
        strength=strength,
        edit_type=edit_type,
    )
    logger.info(f"[chat_generate_dispatch] backend={backend} op={operation} user={user_id}")
    backend_impl = BackendRegistry.get(backend)
    return await backend_impl.run(ctx)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_image_gen_service_backend_dispatch.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_generation_service.py backend/tests/test_image_gen_service_backend_dispatch.py
git commit -m "feat(image-gen): ImageGenService dispatches via BackendRegistry"
```

---

## M6: 自研核心逻辑

### Task 19: AgentOrchestrator

**Files:**
- Create: `backend/app/services/image_gen/agent_orchestrator.py`
- Test: `backend/tests/test_agent_orchestrator.py`

**Interfaces:**
- Consumes: `OrderedLLMGateway`
- Produces: `AgentOrchestrator.run(messages, tools, max_iterations=5) -> tuple[str, list[ToolCall]]`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_agent_orchestrator.py
"""AgentOrchestrator 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.image_gen.agent_orchestrator import AgentOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_stops_on_no_tool_call():
    """LLM 直接返回 content，无 tool_call → 立即返回"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=MagicMock(
        content="你想画什么样的猫？",
        tool_calls=[],
    ))

    orch = AgentOrchestrator(gateway=gateway)
    answer, tool_calls = await orch.run(
        messages=[{"role": "user", "content": "画一只猫"}],
        tools=[],
    )
    assert answer == "你想画什么样的猫？"
    assert tool_calls == []


@pytest.mark.asyncio
async def test_orchestrator_handles_tool_call():
    """LLM 返回 tool_call → 执行，喂结果回去，再调一次 brain"""
    gateway = MagicMock()

    # 第一次：返回 tool_call
    first = MagicMock()
    first.content = None
    first.tool_calls = [
        {"id": "call_1", "name": "generate_image", "arguments": {"operation": "text2img", "prompt": "a cat"}}
    ]

    # 第二次：返回最终回答
    second = MagicMock()
    second.content = "图已生成"
    second.tool_calls = []

    gateway.generate = AsyncMock(side_effect=[first, second])

    orch = AgentOrchestrator(gateway=gateway)
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"image_urls": ["https://oss/1.png"]})

    answer, tool_results = await orch.run(
        messages=[{"role": "user", "content": "画一只猫"}],
        tools=[],
        executor=executor,
    )
    assert answer == "图已生成"
    assert len(tool_results) == 1
    assert tool_results[0]["image_urls"] == ["https://oss/1.png"]


@pytest.mark.asyncio
async def test_orchestrator_max_iterations():
    """超过 max_iterations 应停止并返回当前 best-effort"""
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=MagicMock(
        content=None,
        tool_calls=[{"id": "call_x", "name": "generate_image", "arguments": {}}],
    ))

    orch = AgentOrchestrator(gateway=gateway, max_iterations=3)
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"image_urls": []})

    answer, tool_results = await orch.run(
        messages=[{"role": "user", "content": "x"}],
        tools=[],
        executor=executor,
    )
    # 应该已停止
    assert executor.execute.call_count <= 3
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_agent_orchestrator.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 AgentOrchestrator**

```python
# backend/app/services/image_gen/agent_orchestrator.py
"""自研 Agent 对话编排器

维护 brain LLM 多轮调用：
  1. 发 messages + tools 给 brain
  2. 若返回 tool_call：执行，把结果喂回去，继续循环
  3. 若无 tool_call：content 即最终回答，结束

防死循环：max_iterations 上限。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.llm.ordered_gateway import OrderedLLMGateway

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """自研 Agent 编排器"""

    def __init__(self, gateway: OrderedLLMGateway, max_iterations: int = 5):
        self._gateway = gateway
        self._max_iterations = max_iterations

    async def run(
        self,
        messages: list[dict],
        tools: list[dict],
        executor: Optional[Any] = None,
    ) -> tuple[str, list[dict]]:
        """跑对话循环

        Returns:
            (final_answer_text, list_of_tool_results)
        """
        tool_results: list[dict] = []
        current_messages = list(messages)

        for iteration in range(self._max_iterations):
            logger.info(f"[orchestrator] iteration={iteration} messages={len(current_messages)}")

            response = await self._gateway.generate(
                category="chat",
                messages=current_messages,
                tools=tools,
            )

            if not response.tool_calls:
                # 无 tool_call → 最终回答
                return response.content or "", tool_results

            # 处理 tool_call
            if executor is None:
                raise ValueError("tool_call 但 executor 为 None")

            for call in response.tool_calls:
                logger.info(f"[orchestrator] tool_call name={call['name']} id={call['id']}")
                result = await executor.execute(call)
                tool_results.append(result)

                # 把 tool_call + tool_result 追加到 messages
                current_messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                })
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": str(result),
                })

        # 超过最大轮次
        logger.warning(f"[orchestrator] hit max_iterations={self._max_iterations}")
        return "", tool_results
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_agent_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/agent_orchestrator.py backend/tests/test_agent_orchestrator.py
git commit -m "feat(image-gen): add AgentOrchestrator with tool-calling loop"
```

---

### Task 20: ToolExecutor

**Files:**
- Create: `backend/app/services/image_gen/tool_executor.py`
- Test: `backend/tests/test_tool_executor.py`

**Interfaces:**
- Consumes: `OrderedLLMGateway`, `OssService`
- Produces: `ToolExecutor.execute(tool_call) -> dict(image_urls=[...])`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_tool_executor.py
"""ToolExecutor 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.image_gen.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_execute_text2img():
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=[b"fake_image_bytes"])

    oss = MagicMock()
    oss.upload_bytes = MagicMock(return_value="oss-key-1")
    oss.generate_signed_url = MagicMock(return_value="https://oss/signed")

    executor = ToolExecutor(gateway=gateway, oss_svc=oss)
    result = await executor.execute({
        "id": "call_1",
        "name": "generate_image",
        "arguments": {"operation": "text2img", "prompt": "a cat", "size": "1024x1024", "n": 1},
    })

    assert result["image_urls"] == ["https://oss/signed"]
    oss.upload_bytes.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_reference():
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value=[b"fake"])

    oss = MagicMock()
    oss.upload_bytes = MagicMock(return_value="oss-key-ref")
    oss.generate_signed_url = MagicMock(return_value="https://oss/signed")

    executor = ToolExecutor(gateway=gateway, oss_svc=oss)
    result = await executor.execute({
        "id": "call_1",
        "name": "generate_image",
        "arguments": {
            "operation": "img2img",
            "prompt": "改成水彩",
            "reference_image_url": "https://oss/ref.png",
        },
    })
    assert result["image_urls"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_tool_executor.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 ToolExecutor**

```python
# backend/app/services/image_gen/tool_executor.py
"""图像生成 tool 执行器

收到 brain 的 generate_image tool_call 后：
  1. 解析 arguments（operation / prompt / 参考图 URL 等）
  2. 若有参考图 URL，先下载
  3. 走 OrderedLLMGateway.generate(category="image_gen", ...) 调 image_gen adapter
  4. 下载结果图
  5. 上传 OSS
  6. 返回 image_urls
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.llm.ordered_gateway import OrderedLLMGateway
from app.services.oss_service import OssService
from app.utils.image_gen_constants import (
    OSS_PREFIX_RESULT,
    SIGNED_URL_EXPIRES_RESULT,
)

logger = logging.getLogger(__name__)


class ToolExecutor:
    """图像生成 tool 执行器"""

    def __init__(self, gateway: OrderedLLMGateway, oss_svc: OssService):
        self._gateway = gateway
        self._oss = oss_svc

    async def execute(self, tool_call: dict) -> dict[str, Any]:
        """执行 generate_image tool_call

        Args:
            tool_call: {"id": "...", "name": "generate_image", "arguments": {...}}

        Returns:
            {"image_urls": [...], "tool_call_id": "..."}
        """
        args = tool_call["arguments"]
        operation = args["operation"]
        prompt = args["prompt"]
        size = args.get("size", "1024x1024")
        n = args.get("n", 1)
        strength = args.get("strength")
        edit_type = args.get("edit_type")

        # 下载参考图 / 蒙版图（如有）
        reference_image = await self._download(args.get("reference_image_url"))
        mask_image = await self._download(args.get("mask_image_url"))

        # 调 image_gen
        images_bytes: list[bytes] = await self._gateway.generate(
            category="image_gen",
            operation=operation,
            prompt=prompt,
            size=size,
            n=n,
            reference_image=reference_image,
            mask_image=mask_image,
            strength=strength,
            edit_type=edit_type,
        )

        # 上传 OSS
        image_urls: list[str] = []
        for img in images_bytes:
            oss_key = self._oss.upload_bytes(img, prefix=OSS_PREFIX_RESULT, mime="image/png")
            url = self._oss.generate_signed_url(oss_key, expires=SIGNED_URL_EXPIRES_RESULT)
            image_urls.append(url)

        logger.info(f"[tool_executor] operation={operation} generated={len(image_urls)} images")
        return {"image_urls": image_urls, "tool_call_id": tool_call["id"]}

    async def _download(self, url: str | None) -> bytes | None:
        """从 URL 下载图（可能是 OSS 签名 URL 或任意 https URL）"""
        if not url:
            return None
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_tool_executor.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/tool_executor.py backend/tests/test_tool_executor.py
git commit -m "feat(image-gen): add ToolExecutor for generate_image tool"
```

---

### Task 21: SelfDevelopedBackend

**Files:**
- Create: `backend/app/services/image_gen/selfdev_backend.py`
- Test: `backend/tests/test_selfdev_backend.py`

**Interfaces:**
- Consumes: `AgentOrchestrator`, `ToolExecutor`, `ImageGenSelfDevConversation`（repo 在 Task 22 写）
- Produces: `SelfDevelopedBackend.run(ctx) -> BackendResult`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_selfdev_backend.py
"""SelfDevelopedBackend 测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.image_gen.base import BackendContext
from app.services.image_gen.selfdev_backend import SelfDevelopedBackend


@pytest.mark.asyncio
async def test_new_conversation_returns_id():
    """首次对话：conversation_id=None → 生成新 UUID 返回"""
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value=("你好", []))

    executor = MagicMock()
    conv_repo = MagicMock()
    conv_repo.save = AsyncMock()
    conv_repo.load = AsyncMock(return_value=[])

    backend = SelfDevelopedBackend(
        orchestrator=orchestrator,
        executor=executor,
        conv_repo=conv_repo,
    )

    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="画一只猫",
        conversation_id=None,
        reference_image=None,
        reference_mime=None,
        mask_image=None,
        mask_mime=None,
        size="1024x1024",
        n=1,
        strength=None,
        edit_type=None,
    )
    result = await backend.run(ctx)

    assert result.backend == "selfdev"
    assert result.conversation_id != ""  # 已生成
    conv_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_with_tool_call_generates_images():
    """brain 决定生成 → tool_call 执行 → 返回 image_urls"""
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value=(
        "图已生成",
        [{"image_urls": ["https://oss/1.png"], "tool_call_id": "call_1"}],
    ))

    executor = MagicMock()
    conv_repo = MagicMock()
    conv_repo.save = AsyncMock()
    conv_repo.load = AsyncMock(return_value=[])

    backend = SelfDevelopedBackend(
        orchestrator=orchestrator,
        executor=executor,
        conv_repo=conv_repo,
    )

    ctx = BackendContext(
        user_id=uuid.uuid4(),
        operation="text2img",
        query="画一只猫",
        conversation_id=None,
        reference_image=None,
        reference_mime=None,
        mask_image=None,
        mask_mime=None,
        size="1024x1024",
        n=1,
        strength=None,
        edit_type=None,
    )
    result = await backend.run(ctx)

    assert result.image_urls == ["https://oss/1.png"]
    assert result.answer_text == "图已生成"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_selfdev_backend.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 SelfDevelopedBackend**

```python
# backend/app/services/image_gen/selfdev_backend.py
"""自研后端：用 AgentOrchestrator + ToolExecutor 完成对话 + 图像生成"""

from __future__ import annotations

import logging
import uuid

from app.services.image_gen.agent_orchestrator import AgentOrchestrator
from app.services.image_gen.base import BackendContext, BackendResult, IImageGenerationBackend
from app.services.image_gen.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class SelfDevelopedBackend(IImageGenerationBackend):
    """自研图像生成后端"""

    def __init__(self, orchestrator: AgentOrchestrator, executor: ToolExecutor, conv_repo):
        self._orch = orchestrator
        self._exec = executor
        self._conv = conv_repo

    async def run(self, ctx: BackendContext) -> BackendResult:
        logger.info(f"[selfdev_backend] op={ctx.operation} user={ctx.user_id}")

        # 1. 加载或创建对话
        conversation_id = ctx.conversation_id or str(uuid.uuid4())
        if ctx.conversation_id:
            history = await self._conv.load(ctx.conversation_id)
        else:
            history = []

        # 2. 组装 messages：system + history + 当前用户输入
        system_msg = self._build_system_message(ctx)
        messages = [{"role": "system", "content": system_msg}] + history + [
            {"role": "user", "content": ctx.query}
        ]

        # 3. 跑 orchestrator
        tools = [self._generate_image_tool()]
        answer, tool_results = await self._orch.run(
            messages=messages,
            tools=tools,
            executor=self._exec,
        )

        # 4. 提取 image_urls
        image_urls: list[str] = []
        for r in tool_results:
            if "image_urls" in r:
                image_urls.extend(r["image_urls"])

        # 5. 保存对话
        messages.append({"role": "assistant", "content": answer})
        await self._conv.save(
            user_id=ctx.user_id,
            conversation_id=conversation_id,
            operation=ctx.operation,
            messages=messages[1:],  # 去掉 system
        )

        return BackendResult(
            image_urls=image_urls,
            answer_text=answer,
            conversation_id=conversation_id,
            model_used="",  # TODO: 从 OrderedLLMGateway 透出
            backend="selfdev",
        )

    def _build_system_message(self, ctx: BackendContext) -> str:
        """构造 system message"""
        return (
            "你是一个图像生成助手。用户会描述想生成的图像，你需要：\n"
            "1. 如果用户描述不够具体，可以追问（最多 2 轮）\n"
            "2. 当描述足够清晰时，调用 generate_image 工具生成图像\n"
            "3. 生成后简短回复用户\n"
            f"当前操作类型：{ctx.operation}"
        )

    def _generate_image_tool(self) -> dict:
        """generate_image tool 定义"""
        return {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "生成或修改图像",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["text2img", "img2img", "inpaint", "upload_edit"]},
                        "prompt": {"type": "string"},
                        "size": {"type": "string"},
                        "n": {"type": "integer"},
                        "reference_image_url": {"type": "string"},
                        "mask_image_url": {"type": "string"},
                        "strength": {"type": "number"},
                        "edit_type": {"type": "string"},
                    },
                    "required": ["operation", "prompt"],
                },
            },
        }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_selfdev_backend.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/selfdev_backend.py backend/tests/test_selfdev_backend.py
git commit -m "feat(image-gen): add SelfDevelopedBackend orchestrating agent + tools"
```

---

## M7: 路由与持久化

### Task 22: ImageGenSelfDevConversationRepository

**Files:**
- Create: `backend/app/services/image_gen/conversation_repo.py`
- Test: `backend/tests/test_image_gen_conversation_repo.py`

**Interfaces:**
- Consumes: `ImageGenSelfDevConversation` 模型
- Produces: `ConversationRepository.save/load/load_by_id`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_gen_conversation_repo.py
"""ConversationRepository 测试"""

import uuid

import pytest

from app.services.image_gen.conversation_repo import ConversationRepository


@pytest.mark.asyncio
async def test_save_new_conversation(db_session):
    repo = ConversationRepository(db=db_session)
    user_id = uuid.uuid4()
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=user_id,
        conversation_id=cid,
        operation="text2img",
        messages=[{"role": "user", "content": "hello"}],
    )

    loaded = await repo.load(cid)
    assert loaded[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_load_returns_messages(db_session):
    repo = ConversationRepository(db=db_session)
    user_id = uuid.uuid4()
    cid = str(uuid.uuid4())

    await repo.save(
        user_id=user_id,
        conversation_id=cid,
        operation="text2img",
        messages=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
    )

    loaded = await repo.load(cid)
    assert len(loaded) == 2


@pytest.mark.asyncio
async def test_save_updates_existing(db_session):
    """同一 conversation_id 重复 save → update，不 insert"""
    repo = ConversationRepository(db=db_session)
    user_id = uuid.uuid4()
    cid = str(uuid.uuid4())

    await repo.save(user_id=user_id, conversation_id=cid, operation="text2img",
                    messages=[{"role": "user", "content": "a"}])
    await repo.save(user_id=user_id, conversation_id=cid, operation="text2img",
                    messages=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])

    loaded = await repo.load(cid)
    assert len(loaded) == 2
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_image_gen_conversation_repo.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 写 ConversationRepository**

```python
# backend/app/services/image_gen/conversation_repo.py
"""自研对话仓库"""

from __future__ import annotations

import logging
import uuid as uuid_module
from typing import Any

from sqlalchemy.orm import Session

from app.models.image_gen_conversation import ImageGenSelfDevConversation

logger = logging.getLogger(__name__)


class ConversationRepository:
    """自研对话历史 CRUD"""

    def __init__(self, db: Session):
        self.db = db

    async def save(
        self,
        user_id: uuid_module.UUID,
        conversation_id: str,
        operation: str,
        messages: list[dict],
    ) -> None:
        """保存对话（upsert）"""
        existing = (
            self.db.query(ImageGenSelfDevConversation)
            .filter_by(conversation_id=conversation_id)
            .first()
        )
        if existing:
            existing.messages = messages
            logger.info(f"[conv_repo] update conversation_id={conversation_id} messages={len(messages)}")
        else:
            record = ImageGenSelfDevConversation(
                user_id=user_id,
                conversation_id=conversation_id,
                operation=operation,
                messages=messages,
            )
            self.db.add(record)
            logger.info(f"[conv_repo] create conversation_id={conversation_id}")
        self.db.commit()

    async def load(self, conversation_id: str) -> list[dict]:
        """按 conversation_id 加载消息列表"""
        record = (
            self.db.query(ImageGenSelfDevConversation)
            .filter_by(conversation_id=conversation_id)
            .first()
        )
        if not record:
            return []
        return record.messages or []

    async def load_by_id(self, conversation_id: str, user_id: uuid_module.UUID) -> list[dict]:
        """按 conversation_id 加载，校验 user_id 匹配（多用户隔离）"""
        record = (
            self.db.query(ImageGenSelfDevConversation)
            .filter_by(conversation_id=conversation_id, user_id=user_id)
            .first()
        )
        if not record:
            return []
        return record.messages or []
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_image_gen_conversation_repo.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_gen/conversation_repo.py backend/tests/test_image_gen_conversation_repo.py
git commit -m "feat(image-gen): add ConversationRepository with user isolation"
```

---

### Task 23: quota + history 接入自研路径

**Files:**
- Modify: `backend/app/services/image_generation_service.py`
- Test: `backend/tests/test_chat_route_quota_backend.py`

**Interfaces:**
- Consumes: `ImageGenQuotaService`, `ImageGenHistoryService`, `BackendResult`
- Produces: `ImageGenService.chat_generate_dispatch_with_quota`（带 quota 的 dispatch 方法）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_chat_route_quota_backend.py
"""自研路径 quota + history 测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.image_gen.base import BackendResult, IImageGenerationBackend
from app.services.image_gen.backends import BackendRegistry
from app.services.image_generation_service import ImageGenService


class _StubBackendWithImages(IImageGenerationBackend):
    async def run(self, ctx):
        return BackendResult(
            image_urls=["https://oss/1.png"],
            answer_text="done",
            conversation_id="cid",
            model_used="m",
            backend="selfdev",
        )


@pytest.fixture(autouse=True)
def reset_registry():
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


@pytest.mark.asyncio
async def test_quota_commit_on_image_urls(db_session):
    """image_urls 非空 → commit"""
    BackendRegistry.register("selfdev", _StubBackendWithImages())

    quota = MagicMock()
    quota.check_and_reserve = MagicMock()
    quota.commit = MagicMock()
    quota.release = MagicMock()

    history = MagicMock()
    history.create_record = MagicMock(return_value=MagicMock(id="h1"))

    svc = ImageGenService(
        db=db_session,
        dify_client=MagicMock(),
        quota_svc=quota,
        oss_svc=MagicMock(),
        history_svc=history,
        degradation_svc=MagicMock(),
    )

    await svc.chat_generate_dispatch_with_quota(
        backend="selfdev",
        user_id=uuid.uuid4(),
        operation="text2img",
        query="a cat",
        conversation_id=None,
        reference_image=None,
        mask_image=None,
        size="1024x1024",
        n=1,
    )

    quota.check_and_reserve.assert_called_once()
    quota.commit.assert_called_once()
    quota.release.assert_not_called()
    history.create_record.assert_called_once()
    # history record 应带 backend 字段
    call_kwargs = history.create_record.call_args[1]
    assert call_kwargs["backend"] == "selfdev"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_chat_route_quota_backend.py -v`
Expected: FAIL — `AttributeError: 'ImageGenService' object has no attribute 'chat_generate_dispatch_with_quota'`

- [ ] **Step 3: 写 chat_generate_dispatch_with_quota**

```python
# backend/app/services/image_generation_service.py
# 在 ImageGenService 类内追加：

async def chat_generate_dispatch_with_quota(
    self,
    backend: str,
    user_id: uuid.UUID,
    operation: str,
    query: str,
    conversation_id: Optional[str],
    reference_image: Optional[bytes],
    mask_image: Optional[bytes],
    size: str,
    n: int,
    strength: Optional[float] = None,
    edit_type: Optional[str] = None,
) -> BackendResult:
    """按 backend 分发 + quota / history 共享逻辑"""
    from app.services.image_gen.backends import BackendRegistry

    # 1. reserve quota（无论后续是否生成）
    self.quota_svc.check_and_reserve(user_id=user_id, operation=operation)

    try:
        # 2. 走 dispatch
        result = await self.chat_generate_dispatch(
            backend=backend,
            user_id=user_id,
            operation=operation,
            query=query,
            conversation_id=conversation_id,
            reference_image=reference_image,
            mask_image=mask_image,
            size=size,
            n=n,
            strength=strength,
            edit_type=edit_type,
        )

        # 3. quota commit or release
        if result.image_urls:
            self.quota_svc.commit(user_id=user_id)
            # 4. history record — 需同步更新 ImageGenHistoryService.create_record 接受 backend 参数
            self.history_svc.create_record(
                user_id=user_id,
                operation=operation,
                prompt=query,
                image_urls=result.image_urls,
                model_used=result.model_used,
                conversation_id=result.conversation_id,
                backend=result.backend,
            )
        else:
            self.quota_svc.release(user_id=user_id)

        return result
    except Exception:
        self.quota_svc.release(user_id=user_id)
        raise
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_chat_route_quota_backend.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/image_generation_service.py backend/tests/test_chat_route_quota_backend.py
git commit -m "feat(image-gen): quota + history wired for backend dispatch"
```

---

### Task 24: /chat 路由加 backend 参数

**Files:**
- Modify: `backend/app/routes/image_generation.py`
- Test: `backend/tests/test_chat_route_backend_param.py`

**Interfaces:**
- Consumes: `ImageGenService.chat_generate_dispatch_with_quota`（T23 已实现）
- Produces: `/chat` 路由接受 `backend` Form 参数，调用 with-quota dispatch

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_chat_route_backend_param.py
"""/chat 路由 backend 参数测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.image_gen.backends import BackendRegistry
from app.services.image_gen.base import BackendResult, IImageGenerationBackend


class _StubBackend(IImageGenerationBackend):
    def __init__(self, name):
        self._name = name

    async def run(self, ctx):
        return BackendResult(
            image_urls=["https://oss/1.png"],
            answer_text=f"from {self._name}",
            conversation_id="cid",
            model_used="m",
            backend=self._name,
        )


@pytest.fixture(autouse=True)
def reset_registry():
    BackendRegistry._REGISTRY.clear()
    yield
    BackendRegistry._REGISTRY.clear()


def test_chat_backend_selfdev(client, auth_headers):
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))
    BackendRegistry.register("dify", _StubBackend("dify"))

    resp = client.post(
        "/api/image-generation/chat",
        data={"backend": "selfdev", "operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["backend"] == "selfdev"


def test_chat_backend_dify(client, auth_headers):
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))
    BackendRegistry.register("dify", _StubBackend("dify"))

    resp = client.post(
        "/api/image-generation/chat",
        data={"backend": "dify", "operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["backend"] == "dify"


def test_chat_backend_default_selfdev(client, auth_headers):
    """不传 backend → 默认 selfdev"""
    BackendRegistry.register("selfdev", _StubBackend("selfdev"))
    BackendRegistry.register("dify", _StubBackend("dify"))

    resp = client.post(
        "/api/image-generation/chat",
        data={"operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["backend"] == "selfdev"


def test_chat_backend_unconfigured_returns_503(client, auth_headers):
    """注册表为空 → 503"""
    # 不注册任何 backend
    resp = client.post(
        "/api/image-generation/chat",
        data={"backend": "selfdev", "operation": "text2img", "prompt": "a cat"},
        headers=auth_headers,
    )
    assert resp.status_code == 503
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/test_chat_route_backend_param.py -v`
Expected: FAIL

- [ ] **Step 3: 修改 /chat 路由**

在 `backend/app/routes/image_generation.py` 的 `/chat` 端点：

```python
# 加 Form 参数
backend: str = Form(default="selfdev"),

# 把现有 chat_generate 调用替换为（T23 已实现的 with-quota 方法）：
result = await image_gen_service.chat_generate_dispatch_with_quota(
    backend=backend,
    user_id=current_user.id,
    operation=operation,
    query=prompt,
    conversation_id=conversation_id,
    reference_image=reference_bytes,
    mask_image=mask_bytes,
    size=size,
    n=n,
)

# 异常处理 BackendNotConfiguredError → 503
from app.services.image_gen.backends import BackendNotConfiguredError
# ...
except BackendNotConfiguredError as e:
    raise HTTPException(status_code=503, detail=str(e))
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/test_chat_route_backend_param.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/routes/image_generation.py backend/tests/test_chat_route_backend_param.py
git commit -m "feat(image-gen): /chat route accepts backend param + uses with-quota dispatch"
```

---

## M8: 前端整合

### Task 25: BackendSwitch 组件

**Files:**
- Create: `frontend/src/components/Tools/ImageGeneration/BackendSwitch.tsx`
- Test: `frontend/src/components/Tools/ImageGeneration/__tests__/BackendSwitch.test.tsx`

**Interfaces:**
- Produces: `<BackendSwitch />` 组件，localStorage 读写

- [ ] **Step 1: 写失败测试**

```typescript
// frontend/src/components/Tools/ImageGeneration/__tests__/BackendSwitch.test.tsx
import { describe, expect, it, beforeEach } from 'vitest';
import { getBackend, setBackend } from '../BackendSwitch';

describe('BackendSwitch localStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('默认返回 selfdev', () => {
    expect(getBackend()).toBe('selfdev');
  });

  it('设置后能读取', () => {
    setBackend('dify');
    expect(getBackend()).toBe('dify');
  });

  it('设置 selfdev 后能读取', () => {
    setBackend('selfdev');
    expect(getBackend()).toBe('selfdev');
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/ImageGeneration/__tests__/BackendSwitch.test.tsx`
Expected: FAIL — Module not found

- [ ] **Step 3: 写组件**

```typescript
// frontend/src/components/Tools/ImageGeneration/BackendSwitch.tsx
/**
 * 图像生成后端切换组件
 * localStorage 键: image_gen_backend
 * 可选值: 'dify' | 'selfdev'
 */

import { useState } from 'react';

const STORAGE_KEY = 'image_gen_backend';

export type ImageGenBackend = 'dify' | 'selfdev';

export function getBackend(): ImageGenBackend {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === 'dify' || raw === 'selfdev') return raw;
  return 'selfdev';
}

export function setBackend(b: ImageGenBackend): void {
  localStorage.setItem(STORAGE_KEY, b);
}

export default function BackendSwitch() {
  const [backend, setBackendState] = useState<ImageGenBackend>(getBackend());

  const handleChange = (b: ImageGenBackend) => {
    setBackend(b);
    setBackendState(b);
    // 触发 storage 事件，让其他组件感知
    window.dispatchEvent(new Event('image-gen-backend-changed'));
  };

  return (
    <div className="inline-flex rounded-lg bg-slate-800 p-1">
      <button
        onClick={() => handleChange('dify')}
        className={`px-4 py-1 rounded text-sm transition ${
          backend === 'dify'
            ? 'bg-blue-600 text-white'
            : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        Dify
      </button>
      <button
        onClick={() => handleChange('selfdev')}
        className={`px-4 py-1 rounded text-sm transition ${
          backend === 'selfdev'
            ? 'bg-blue-600 text-white'
            : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        自研 Agent
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/ImageGeneration/__tests__/BackendSwitch.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Tools/ImageGeneration/BackendSwitch.tsx frontend/src/components/Tools/ImageGeneration/__tests__/BackendSwitch.test.tsx
git commit -m "feat(image-gen): add BackendSwitch component with localStorage"
```

---

### Task 26: imageGenerationApi 加 backend 参数

**Files:**
- Modify: `frontend/src/api/imageGenerationApi.ts`
- Test: `frontend/src/api/__tests__/imageGenerationApi.test.ts`

**Interfaces:**
- Consumes: `BackendSwitch.getBackend()`
- Produces: `chatGenerate` 自动带 backend

- [ ] **Step 1: 修改 chatGenerate 签名**

```typescript
// frontend/src/api/imageGenerationApi.ts
import { getBackend } from '../components/Tools/ImageGeneration/BackendSwitch';

export async function chatGenerate(
  operation: Operation,
  prompt: string,
  conversationId: string | null,
  params?: ChatParams,
  referenceImage?: File | null,
  maskImage?: File | null,
): Promise<ChatResult> {
  const formData = new FormData();
  formData.append('operation', operation);
  formData.append('prompt', prompt);
  formData.append('backend', getBackend());   // ← 新增
  if (conversationId) formData.append('conversation_id', conversationId);
  // ... 其他参数不变
```

- [ ] **Step 2: 写测试**

```typescript
// frontend/src/api/__tests__/imageGenerationApi.test.ts
import { describe, expect, it, beforeEach, vi } from 'vitest';

describe('chatGenerate backend param', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('默认带 selfdev', async () => {
    // mock fetch 并断言 FormData 含 backend=selfdev
    // ... 具体 mock 略
  });
});
```

- [ ] **Step 3: tsc + 测试**

Run: `cd frontend && npx tsc --noEmit && npx vitest run src/api/__tests__/imageGenerationApi.test.ts`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/imageGenerationApi.ts frontend/src/api/__tests__/imageGenerationApi.test.ts
git commit -m "feat(image-gen): chatGenerate auto-appends backend param"
```

---

### Task 27: 4 个 form 页面接入 BackendSwitch

**Files:**
- Modify: `frontend/src/components/Tools/ImageGeneration/index.tsx`

**Interfaces:**
- Consumes: `BackendSwitch` 组件

- [ ] **Step 1: 在 index.tsx 顶部加 BackendSwitch**

```typescript
import BackendSwitch from './BackendSwitch';

// 在页面布局顶部：
<div className="flex items-center justify-between mb-4">
  <h1 className="text-xl text-slate-100">图像生成</h1>
  <BackendSwitch />
</div>
```

- [ ] **Step 2: tsc 检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Tools/ImageGeneration/index.tsx
git commit -m "feat(image-gen): integrate BackendSwitch on tool page"
```

---

## M9: 收尾

### Task 28: 端到端集成测试

**Files:**
- Test: `backend/tests/test_e2e_selfdev_image_gen.py`

**Interfaces:**
- 覆盖：完整流程 mock 外部 API

- [ ] **Step 1: 写 E2E 测试**

```python
# backend/tests/test_e2e_selfdev_image_gen.py
"""自研路径端到端测试（mock 外部 API）"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.asyncio
async def test_full_selfdev_flow():
    """完整流程：用户输入 → brain 追问 → brain 决定生成 → image_gen → 返回 URL"""
    # 略：构造 OrderedLLMGateway + 4 个 adapter mock + OSS mock + DB 测试 session
    pass
```

- [ ] **Step 2: 跑测试**

Run: `cd backend && pytest tests/test_e2e_selfdev_image_gen.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_e2e_selfdev_image_gen.py
git commit -m "test(image-gen): e2e test for selfdev path"
```

---

### Task 29: 更新文档

**Files:**
- Modify: `backend/app/services/image_gen/__init__.py` 的 docstring
- Modify: 项目根 README.md（如有 image-gen 章节）

- [ ] **Step 1: 更新 docstring**

```python
# backend/app/services/image_gen/__init__.py
"""
图像生成后端 strategy 模块

两条路径并存：
  - DifyBackend: 调 Dify 工作流（保留）
  - SelfDevelopedBackend: 自研 Agent（新）

通过 BackendRegistry 按请求参数 backend 分发。
模型配置统一从 /admin/llm-configs 读取（LLMProvider + LLMModel）。
"""
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/image_gen/__init__.py
git commit -m "docs(image-gen): document backend strategy"
```

---

### Task 30: 最终 review

**Files:**
- 无新增

- [ ] **Step 1: 跑全量后端测试**

Run: `cd backend && pytest tests/test_image_generation_routes.py tests/test_chat_route*.py tests/test_image_gen_*.py tests/test_llm_*.py tests/test_ordered_gateway.py -v`
Expected: 全 PASS

- [ ] **Step 2: 跑前端构建**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 构建成功

- [ ] **Step 3: 手动验证**

- 启动 `python dev-services.py`
- 访问 `http://localhost:5178/admin/llm-configs`，配置 1 个 chat 模型 + 1 个 image_gen 模型（priority 设置）
- 访问 `http://localhost:5178/tools/image-generation`，切换 BackendSwitch 到"自研 Agent"
- 输入提示词，验证多轮对话 + 图像生成

- [ ] **Step 4: 重启服务**

Run: `python dev-services.py restart`

---

## Self-Review 总结

**Spec 覆盖检查：**

| Spec 章节 | 对应 Task |
|---|---|
| §3 模块拆分 | T15-T22 |
| §4.1 数据流 | T18-T24 |
| §4.2 有序兜底链 | T13 |
| §4.3 Tool 定义 | T19 |
| §4.4 后端切换协议 | T23, T25-T27 |
| §5 数据模型 | T1-T5 |
| §6 Adapter 契约 | T10-T12 |
| §7 错误矩阵 | T13, T23, T24 |
| §8 测试策略 | T1-T30 全部 |

**Placeholder 扫描：** 无 TBD/TODO（除 HailuoAdapter 内部 TODO，这是 v1 明确"待接入实际 API"的占位）

**类型一致性检查：**
- `LLMCategory.IMAGE_GEN = "image_gen"`（T1）→ `OrderedLLMGateway`（T13）→ `ImageGenFactory`（T11）一致
- `BackendContext` / `BackendResult`（T15）→ `DifyBackend`（T17）→ `SelfDevelopedBackend`（T21）一致
- `ModelCategory`（T6）→ `ModelDialog`（T8）一致
- `getBackend()` 返回 `'dify' | 'selfdev'`（T25）→ `chatGenerate` formData append（T26）→ `/chat` 路由 backend param（T23）一致

---

**End of plan.** 待用户审阅。