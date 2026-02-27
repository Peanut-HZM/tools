# Research: 产品经理 Agent 技术决策

**Feature**: 001-product-manager-agent  
**Date**: 2026-02-15  
**Status**: Complete

---

## Technical Context

基于项目现有技术栈和需求分析，确定以下技术方案：

| 类别 | 决策 | 说明 |
|------|------|------|
| **后端语言** | Python 3.11 | 项目已有FastAPI后端，保持一致 |
| **前端框架** | React 18 + TypeScript | 项目已有React前端，保持一致 |
| **数据库** | SQLite (开发) / PostgreSQL (生产) | 与现有项目一致 |
| **LLM调用** | 统一抽象层 + Provider适配器 | 支持多供应商 |
| **文档解析** | mammoth.js (Word) + pdf-parse (PDF) | 成熟稳定 |
| **图表渲染** | Mermaid.js | 原生支持，无需后端处理 |
| **导出功能** | html2pdf.js + docx.js | 前端生成，减轻服务端压力 |

---

## 1. LLM Provider 抽象层设计

### 问题
需要支持至少5种大模型供应商（OpenAI、Anthropic、Azure、百度文心、阿里通义），每种API格式不同。

### 决策
**采用适配器模式（Adapter Pattern）**

```
┌─────────────────────────────────────────────┐
│            LLM Service Layer                │
│  ┌──────────────┐      ┌────────────────┐  │
│  │ 统一接口     │◄────►│ Provider抽象层 │  │
│  │ (generate)   │      │                │  │
│  └──────────────┘      └────────┬───────┘  │
│                                 │          │
│         ┌──────────┬────────────┼────────┐ │
│         ▼          ▼            ▼        ▼ │
│      OpenAI   Anthropic     Azure    国内  │
│      Adapter  Adapter       Adapter  厂商  │
└─────────────────────────────────────────────┘
```

### Rationale
- **统一接口**: 所有供应商通过相同接口调用，降低耦合
- **易于扩展**: 新增供应商只需添加适配器
- **故障切换**: 主配置失败时自动切换备用配置
- **测试友好**: 可Mock适配器进行单元测试

### 统一接口设计
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, 
        messages: List[Message], 
        config: GenerationConfig
    ) -> GenerationResult:
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        pass
```

---

## 2. 竞品搜索服务选型

### 问题
竞品分析需要搜索相关产品信息（FR-006）。

### 决策
**使用 SerpAPI (Google Search API)**

| 选项 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| SerpAPI | 数据全面，API友好 | 付费 | ✅ 选用 |
| 自建爬虫 | 免费 | 维护成本高，易被屏蔽 | ❌ 不选 |
| Bing API | 价格较低 | 数据质量一般 | ❌ 备选 |

### Rationale
- SerpAPI 返回结构化的搜索结果，易于解析
- 支持中文搜索，满足国内产品需求
- 有免费额度（100次/月），适合初期验证

---

## 3. 文档解析方案

### 问题
需要支持 Markdown、Word、PDF 文档上传解析（FR-003）。

### 决策
**后端处理方案**

| 文档类型 | 处理方式 | 库/工具 |
|----------|----------|---------|
| Markdown | 直接解析 | Python markdown库 |
| Word (.docx) | 服务端解析 | python-docx |
| PDF | 服务端解析 | PyPDF2 / pdfplumber |

### Rationale
- **安全性**: 敏感文档不在前端暴露
- **一致性**: 所有文档类型统一在后端处理
- **可扩展**: 新增格式只需添加后端解析器

---

## 4. 对话上下文管理

### 问题
需要维护多轮对话上下文（FR-005），支持50轮对话不丢失（SC-009）。

### 决策
**数据库存储 + 内存缓存**

```
用户发送消息
    │
    ▼
┌─────────────────┐
│ 1. 保存到数据库  │ ◄── 持久化
│ 2. 更新内存缓存  │ ◄── 加速读取
└─────────────────┘
    │
    ▼
调用 LLM API
    │
    ▼
保存 AI 响应
    │
    ▼
返回给用户
```

### Rationale
- **持久化**: 数据库存储确保数据不丢失
- **性能**: 内存缓存减少数据库查询
- **成本**: 控制LLM API调用次数（带历史上下文）

---

## 5. API Key 加密存储

### 问题
需要安全存储大模型 API Key（FR-023）。

### 决策
**AES-256-GCM 加密**

```python
# 加密流程
1. 从环境变量获取 MASTER_KEY
2. 生成随机 IV (Initialization Vector)
3. 使用 AES-256-GCM 加密 apiKey
4. 存储: iv + ciphertext + auth_tag

# 解密流程
1. 从数据库读取加密数据
2. 分离 iv、ciphertext、auth_tag
3. 使用 MASTER_KEY 解密
4. 返回明文 apiKey 用于 API 调用
```

### Rationale
- **AES-256-GCM**: 提供加密和完整性验证
- **环境变量存储密钥**: 密钥与应用代码分离
- **随机IV**: 相同明文加密后结果不同，增加安全性

---

## 6. 限流实现方案

### 问题
需要实现分级限流：普通用户50次/小时，高级用户200次/小时（FR-037）。

### 决策
**Redis + Sliding Window 算法**

```python
# 限流逻辑
1. 使用 Redis 存储用户调用记录
2. Key: rate_limit:{user_id}:{hour}
3. Value: 当前小时调用次数
4. TTL: 1小时（自动过期）

# 检查限流
if current_count >= limit:
    return 429 Too Many Requests
else:
    increment count
    allow request
```

### Rationale
- **Redis**: 高性能，支持原子操作
- **滑动窗口**: 比固定窗口更公平
- **自动过期**: 无需手动清理过期数据

---

## 7. 并发控制实现

### 问题
需要处理多设备同时编辑同一会话的冲突（FR-034）。

### 决策
**乐观锁（Version Field）**

```sql
-- 更新时检查版本号
UPDATE conversations 
SET content = ?, version = version + 1
WHERE id = ? AND version = ?

-- 如果 affected_rows == 0，说明版本冲突
```

### Rationale
- **乐观锁**: 读多写少场景性能更好
- **版本号**: 简单有效，易于实现
- **冲突处理**: 后端检测冲突，前端提示用户选择

---

## 8. 项目结构决策

基于项目已有结构，采用前后端分离架构：

```
backend/
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── conversations.py    # 会话管理API
│   │   │   ├── messages.py         # 消息API
│   │   │   ├── prd.py              # PRD管理API
│   │   │   ├── llm_config.py       # 大模型配置API
│   │   │   └── competitor.py       # 竞品分析API
│   │   └── dependencies.py
│   ├── services/
│   │   ├── llm/
│   │   │   ├── base.py             # LLM抽象接口
│   │   │   ├── openai_adapter.py   # OpenAI适配器
│   │   │   ├── anthropic_adapter.py
│   │   │   ├── azure_adapter.py
│   │   │   ├── baidu_adapter.py    # 文心一言
│   │   │   ├── aliyun_adapter.py   # 通义千问
│   │   │   └── factory.py          # 适配器工厂
│   │   ├── conversation_service.py
│   │   ├── prd_generator.py
│   │   ├── competitor_analyzer.py
│   │   └── document_parser.py
│   ├── models/
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── prd.py
│   │   └── llm_config.py
│   ├── core/
│   │   ├── security.py             # 加密相关
│   │   ├── rate_limiter.py         # 限流器
│   │   └── config.py
│   └── main.py
└── tests/

frontend/src/
├── components/
│   └── ProductManagerAgent/
│       ├── ChatInterface.tsx       # 对话主界面
│       ├── Sidebar.tsx             # 侧边栏
│       ├── MessageBubble.tsx       # 消息气泡
│       ├── PRDPreview.tsx          # PRD预览
│       └── VersionHistory.tsx      # 版本历史
├── services/
│   ├── conversationApi.ts
│   ├── prdApi.ts
│   └── llmConfigApi.ts
└── hooks/
    ├── useConversation.ts
    └── usePRD.ts
```

---

## 9. 依赖清单

### 后端依赖

```txt
# 核心框架
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0

# 数据库
sqlalchemy==2.0.23
alembic==1.12.0
aiosqlite==0.19.0  # 开发环境

# LLM客户端
openai==1.3.0
anthropic==0.7.0
httpx==0.25.0  # 通用HTTP客户端

# 加密
cryptography==41.0.0

# 限流
redis==5.0.0

# 文档解析
python-docx==1.1.0
PyPDF2==3.0.0
python-markdown==3.5.0

# 搜索
serpapi==0.1.0

# 其他
python-multipart==0.0.6  # 文件上传
```

### 前端依赖

```json
{
  "mermaid": "^10.6.0",
  "html2pdf.js": "^0.10.1",
  "docx": "^8.5.0",
  "diff-match-patch": "^1.0.5"
}
```

---

## 10. 待澄清问题

无 - 所有技术决策已在规格书澄清阶段解决。

---

## 总结

| 组件 | 技术选型 | 理由 |
|------|----------|------|
| LLM调用 | 适配器模式 | 支持多供应商，易于扩展 |
| 竞品搜索 | SerpAPI | 数据全面，API友好 |
| 文档解析 | 后端处理 | 安全，一致，可扩展 |
| 对话存储 | DB + 缓存 | 持久化 + 性能 |
| API Key加密 | AES-256-GCM | 安全，标准方案 |
| 限流 | Redis滑动窗口 | 高性能，公平 |
| 并发控制 | 乐观锁 | 适合读多写少 |
