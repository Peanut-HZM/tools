# Memory 向量检索 (pgvector) 设计文档

**日期**：2026-08-29  
**Phase**：3-Plan-1B  
**状态**：设计中

## §1 背景与目标

### 现状

Phase 2 已实现基础 KV 记忆存储：
- `agent_memory_long_term` 表：`(agent_id, user_id, key)` 唯一约束，JSONB `value`
- `memory_read` / `memory_write` BuiltinTool：按 key 读写
- Agent 模型字段：`memory_long_term_enabled`, `memory_long_term_config`

### 目标

为 Agent 添加**语义检索**能力，支持长期记忆的向量搜索：
- 自动检索：每轮对话前用语义相似度检索相关记忆，注入 system prompt
- 手动检索：Agent 通过 `memory_search` 工具主动查询
- 重要度排序：记忆带 `importance` 权重，影响检索排序
- 优雅降级：向量 API 不可用时降级为关键词 LIKE 匹配

### 非目标

- Procedural Memory（Agent 技能系统）→ Phase 3 后续 plan
- 记忆自动淘汰/遗忘机制 → 预留 `access_count` 字段，淘汰逻辑后续实现
- 本地 embedding 模型支持 → 预留接口，Phase 3-1B+ 实现

## §2 架构总览

```
┌──────────────────────────────────────────────────────┐
│                    Agent Runtime                      │
│  ┌─────────────┐   ┌──────────────────────────────┐  │
│  │ system prompt│◄──│ _retrieve_long_term_memory() │  │
│  │ (auto inject)│   │ query = last user message    │  │
│  └─────────────┘   │ top_k = 5, threshold = 0.7   │  │
└────────────────────────────────────┼──────────────────┘
                                     │ vector search
                          ┌──────────▼──────────┐
                          │   MemoryService      │
                          │  - search(query, k)  │
                          │  - store(key, val)   │
                          └──┬───────────┬───────┘
                 embed()     │           │  SQL query
                    ┌────────▼──┐   ┌────▼──────────┐
                    │Embedding  │   │ agent_memory  │
                    │Provider   │   │ _long_term    │
                    │(抽象层)    │   │ (pgvector)    │
                    └───────────┘   └───────────────┘
```

### 数据流

1. **写入**（memory_write 工具）：用户调用 `memory_write(key, value)` → MemoryService 调用 EmbeddingProvider 生成 embedding → 存入 DB（key + value + embedding + importance）
2. **自动检索**（每轮对话前）：AgentRuntime 取最后一条 user message → MemoryService.search(query, top_k=5) → 结果注入 system prompt 的 `<long_term_memory>` 段
3. **手动检索**（memory_search 工具）：Agent 主动调用 → 同样的 search 逻辑 → 返回结果给 Agent

### 组件清单

| 组件 | 文件 | 职责 |
|------|------|------|
| EmbeddingProvider | `services/harness/embeddings/` | 生成向量（接口 + 2-3 实现） |
| MemoryService | `services/harness/memory_service.py` | 读写 + 向量检索 |
| memory_search 工具 | `tools/memory_search.py` | 手动向量检索 BuiltinTool |
| memory_read/write 增强 | `tools/memory_read.py`, `memory_write.py` | 写入时自动生成 embedding |
| AgentRuntime 集成 | `agent_runtime.py` | 对话前自动检索注入 |
| Alembic 迁移 | 新 migration | 加 embedding/importance/access_count 列 |
| 前端 | Admin 配置 + Memory 查看器 | embedding 模型配置 + 记忆浏览 |

## §3 数据库变更

### 迁移内容

在现有 `agent_memory_long_term` 表上新增 3 列：

```sql
-- 新增列
ALTER TABLE agent_memory_long_term
  ADD COLUMN embedding VECTOR(1536),         -- pgvector，nullable（历史数据无向量）
  ADD COLUMN importance FLOAT DEFAULT 0.5,    -- 0.0-1.0，记忆重要度
  ADD COLUMN access_count INTEGER DEFAULT 0;  -- 被检索命中次数

-- 向量索引（IVFFlat，适合 <100K 行规模）
CREATE INDEX idx_memory_embedding 
  ON agent_memory_long_term 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);

-- 复合索引：按 (agent_id, user_id) 做向量检索
CREATE INDEX idx_memory_agent_user_embedding 
  ON agent_memory_long_term 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 50)
  WHERE agent_id IS NOT NULL;
```

### 设计决策

- **embedding nullable**：历史 KV 数据无向量，异步回填（或标记 `embedding IS NULL` 的行只走关键词匹配）
- **维度固定 1536**：对应 text-embedding-3-small；pgvector 的 VECTOR 类型维度在建表时确定，运行时不能变。如果将来换维度，需要新 migration + 重新 embed 所有行
- **importance 默认 0.5**：写入时可指定，影响检索排序分数（`score = cosine_sim * importance`）
- **access_count**：每次被检索命中 +1，用于后续淘汰低频记忆

### 回填策略

迁移后首次启动时：
1. 统计 `embedding IS NULL` 的行数
2. 如果 > 0，后台批量生成 embedding（每批 50 条，间隔 1s 避免 rate limit）
3. 进度 log：`"回填记忆向量：已完成 50/200"`
4. 失败不阻塞启动，下次启动重试

## §4 EmbeddingProvider 层

### 接口定义

```python
# services/harness/embeddings/provider.py

class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding 向量，返回维度由模型决定"""
        ...
    
    async def validate(self) -> bool:
        """验证 API 可用性"""
        ...
```

### 工厂

```python
# services/harness/embeddings/factory.py

def create_embedding_provider(model_config: dict) -> EmbeddingProvider:
    """根据 model_config 创建对应的 provider
    model_config 格式: {"provider": "openai", "model": "text-embedding-3-small", "api_key": "...", "base_url": "..."}
    """
```

### 实现

| Provider | 模型 | 维度 | 说明 |
|----------|------|------|------|
| `OpenAIEmbeddingProvider` | text-embedding-3-small/large | 1536/3072 | 用 `openai` SDK，支持 `base_url` 自定义（兼容 API 兼容服务） |
| `DashScopeEmbeddingProvider` | text-embedding-v3 | 1024 | 通义千问 embedding，用 `dashscope` SDK |
| （预留）`LocalEmbeddingProvider` | sentence-transformers | 384-768 | 本地运行，Phase 3-1B+ 再做 |

### 维度兼容

不同模型维度不同（1536 vs 1024 vs 768），但 DB 列固定 `VECTOR(1536)`。

**解决方案**：DB 列固定 1536 维。如果配置的模型输出维度 ≠ 1536，在 provider 层做 padding/truncation 对齐：
- < 1536 → 末尾补零
- \> 1536 → 截断前 1536 维（会有质量损失，log warning）

推荐用户配置 1536 维模型（text-embedding-3-small 刚好是）。

### 配置来源

Agent 的 `memory_long_term_config` JSONB 存储：

```json
{
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "embedding_api_key": "sk-...",
  "embedding_base_url": "https://api.openai.com/v1",
  "auto_inject": true,
  "auto_inject_top_k": 5,
  "auto_inject_threshold": 0.7,
  "auto_inject_timeout_seconds": 5
}
```

如果 `embedding_api_key` 为空，fallback 到全局默认 embedding 配置（环境变量 `EMBEDDING_API_KEY` 或复用 `OPENAI_API_KEY`）。

## §5 MemoryService + 工具变更

### MemoryService

```python
# services/harness/memory_service.py

class MemoryService:
    async def store(self, agent_id, user_id, key, value, importance=0.5) -> None:
        """写入记忆：保存 KV + 生成 embedding + UPSERT"""
        
    async def search(self, agent_id, user_id, query, top_k=5, threshold=0.7) -> list[MemoryEntry]:
        """向量检索：生成 query embedding → cosine similarity → 过滤 + 排序"""
        # score = cosine_sim * importance（重要度加权）
        # access_count += 1 for hit rows
        
    async def get_by_key(self, agent_id, user_id, key) -> MemoryEntry | None:
        """按 key 精确查询（现有逻辑）"""
        
    async def list_all(self, agent_id, user_id) -> list[MemoryEntry]:
        """列出所有记忆（现有逻辑）"""
    
    async def delete(self, agent_id, user_id, key) -> bool:
        """删除记忆"""
```

### search 实现

```sql
SELECT *, 
  1 - (embedding <=> $query_embedding) AS similarity
FROM agent_memory_long_term
WHERE agent_id = $agent_id 
  AND (user_id = $user_id OR user_id IS NULL)  -- 支持 agent 全局记忆
  AND embedding IS NOT NULL
ORDER BY embedding <=> $query_embedding
LIMIT $top_k;
```

然后 `final_score = similarity * importance`，过滤 `final_score < threshold` 的结果。

### 工具变更

**增强 `memory_write`**：写入时自动调用 `MemoryService.store()`，生成 embedding。新增可选参数 `importance`（默认 0.5）。

**增强 `memory_read`**：保持现有按 key 查询 + 列出全部功能，不变。

**新增 `memory_search`**：

```python
class MemorySearchTool(BuiltinTool):
    name = "memory_search"
    display_name = "记忆搜索"
    description = "语义搜索长期记忆，返回最相关的记忆条目"
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词或自然语言描述"},
            "top_k": {"type": "integer", "default": 5, "description": "返回条数"}
        },
        "required": ["query"]
    }
```

**is_available**：仅当 `agent.memory_long_term_enabled == True` 时可用。

**scope 逻辑**：检索时同时匹配 `(agent_id, user_id)` 的私有记忆和 `(agent_id, NULL)` 的全局记忆，合并后排序返回。

## §6 AgentRuntime 集成（自动注入）

### 注入时机

AgentRuntime 每轮对话构建 system prompt 时，在 LLM 调用前执行记忆检索。

### 流程

```
user message 到达
  │
  ├─ agent.memory_long_term_enabled?
  │   ├─ No → 正常流程
  │   └─ Yes ↓
  │
  ├─ _retrieve_long_term_memory(last_user_message)
  │   ├─ query = last_user_message[:500]  # 截断避免 embedding 超长
  │   ├─ results = MemoryService.search(agent_id, user_id, query, top_k=5, threshold=0.7)
  │   └─ return results
  │
  ├─ 构建 memory context block:
  │   """
  │   <long_term_memory>
  │   以下是与当前对话相关的长期记忆：
  │   - [key1]: value1 (相关度: 0.92)
  │   - [key2]: value2 (相关度: 0.85)
  │   ...
  │   </long_term_memory>
  │   """
  │
  └─ 注入到 system prompt 末尾（append，不替换现有内容）
```

### 防护措施

| 风险 | 防护 |
|------|------|
| 检索超时拖慢对话 | 超时 5s，超时则跳过注入（log warning） |
| embedding API 不可用 | 降级为关键词 LIKE 匹配（现有 Phase 2 逻辑） |
| 检索结果为空 | 不注入 memory block，正常继续 |
| 首条消息无 user message | 跳过检索（系统消息 / 开场白场景） |
| 重复注入膨胀 prompt | 去重：按 key 合并，同一轮不重复注入 |

### 降级链

向量检索 → 关键词 LIKE → 跳过。任一层失败不阻塞对话。

## §7 前端变更

### Agent 配置页 — Memory 设置区

在现有 Agent 编辑页的 `memory_long_term_enabled` 开关下方，增加 embedding 配置表单（仅开关打开时显示）：

| 字段 | 类型 | 说明 |
|------|------|------|
| Embedding Provider | Select | OpenAI / DashScope |
| Embedding Model | Text | 模型名（默认 `text-embedding-3-small`） |
| API Key | Password | 可选，留空则用全局默认 |
| Base URL | Text | 可选，自定义 endpoint |
| Auto Inject | Switch | 是否自动检索注入（默认开） |
| Top K | Number | 自动注入条数（默认 5） |
| Threshold | Number | 相似度阈值（默认 0.7） |

这些值存入 `agent.memory_long_term_config` JSONB。

### Agent 对话页 — 记忆查看器

在对话页侧边栏或设置面板中，新增「长期记忆」标签页：

- 列表展示当前 Agent 对该用户的所有记忆（key + value 摘要 + importance + 访问次数）
- 支持搜索（调用 memory_search API）
- 支持手动删除
- 显示 embedding 状态（✅ 已生成 / ⏳ 待生成）

### API 新增

```
GET  /api/v1/harness/agents/{id}/memories          # 列出记忆
DELETE /api/v1/harness/agents/{id}/memories/{key}   # 删除记忆
POST /api/v1/harness/agents/{id}/memories/search    # 向量检索（调试用）
```

**注意**：这些 API 仅供展示/管理，Agent 运行时直接走 MemoryService 不经过 HTTP。

## §8 错误处理

| 场景 | 处理 |
|------|------|
| pgvector 扩展不可用 | 启动时检测，log error + 禁用向量检索，降级为关键词 LIKE |
| Embedding API 超时/失败 | 写入时：存储 KV 但 `embedding=NULL`，标记待回填；检索时：跳过向量匹配，降级关键词 |
| 向量维度不匹配 | provider 层 pad/truncate + log warning |
| DB 中全为 `embedding=NULL`（历史数据未回填） | 检索时 fallback 到 LIKE 匹配，不报错 |
| Agent `memory_long_term_enabled=False` | 所有记忆工具 `is_available()` 返回 False，不执行任何操作 |

## §9 测试计划

| 类型 | 覆盖 |
|------|------|
| 单元测试 | EmbeddingProvider 各实现（mock API）+ MemoryService 逻辑 |
| 集成测试 | 向量检索端到端（需要测试 DB 支持 pgvector） |
| 降级测试 | 模拟 embedding API 不可用 → 验证关键词 fallback |
| 边界测试 | 空 query / 超长 query / 无结果 / 全 NULL embedding |
| 前端测试 | 配置表单渲染 + 记忆列表 CRUD |

## §10 边界约束

| 约束 | 值 |
|------|-----|
| 单条 value 大小 | ≤ 10KB（沿用 Phase 2） |
| 每 (agent, user) 记忆条数 | ≤ 500（Phase 2 是 100，向量检索成本高，适当放宽） |
| embedding 维度 | 固定 1536（DB 列类型决定） |
| 自动检索超时 | 5s（可配置） |
| 回填批次大小 | 50 条/批 |
