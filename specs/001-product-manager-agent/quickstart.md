# Quick Start: 产品经理 Agent

**Feature**: 001-product-manager-agent  
**Version**: 1.0.0  
**Last Updated**: 2026-02-15

---

## 环境要求

- **Python**: 3.11+
- **Node.js**: 18+
- **Redis**: 7.0+ (用于限流和缓存)
- **数据库**: SQLite (开发) / PostgreSQL (生产)

---

## 1. 后端启动

### 1.1 安装依赖

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 1.2 配置环境变量

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env 文件，配置以下关键项
cat > .env << EOF
# 数据库
DATABASE_URL=sqlite:///./pm_agent.db

# Redis (限流和缓存)
REDIS_URL=redis://localhost:6379/0

# 加密密钥 (用于API Key加密)
# 生成: openssl rand -hex 32
MASTER_KEY=your-32-byte-hex-key-here

# 搜索服务 (竞品分析)
SERPAPI_KEY=your-serpapi-key-here

# 可选: 默认LLM配置
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4
EOF
```

### 1.3 初始化数据库

```bash
# 运行迁移
alembic upgrade head

# 创建管理员用户 (可选)
python scripts/create_admin.py --username admin --password admin123
```

### 1.4 启动服务

```bash
# 开发模式 (热重载)
uvicorn app.main:app --reload --host 0.0.0.0 --port 19092

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 19092 --workers 4
```

服务启动后访问:
- API 文档: http://localhost:19092/docs
- ReDoc: http://localhost:19092/redoc

---

## 2. 前端启动

### 2.1 安装依赖

```bash
cd frontend

npm install

# 安装额外依赖
npm install mermaid html2pdf.js docx diff-match-patch
```

### 2.2 配置环境变量

```bash
# 创建 .env.local
cat > .env.local << EOF
# API 基础URL
VITE_API_BASE_URL=http://localhost:19092/api/v1

# 其他配置
VITE_APP_TITLE=产品经理 Agent
EOF
```

### 2.3 启动开发服务器

```bash
npm run dev
```

前端访问: http://localhost:5178

---

## 3. 配置大模型

### 3.1 访问后台管理

1. 登录系统管理员账号
2. 进入"系统设置" → "大模型配置"
3. 点击"添加配置"

### 3.2 添加 OpenAI 配置示例

```yaml
配置名称: OpenAI GPT-4
供应商类型: OpenAI
Base URL: https://api.openai.com/v1
API Key: sk-xxxxxxxxxxxxxxxxxxxxxxxx  # 会被加密存储
模型名称: gpt-4
请求参数:
  temperature: 0.7
  max_tokens: 4000
  timeout: 30
设为默认: true
启用: true
```

### 3.3 添加国内厂商配置示例

**百度文心一言**:
```yaml
配置名称: 百度文心一言
供应商类型: 百度
Base URL: https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat
API Key: 您的API Key
模型名称: ERNIE-Bot-4
```

**阿里通义千问**:
```yaml
配置名称: 阿里通义千问
供应商类型: 阿里
Base URL: https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
API Key: 您的API Key
模型名称: qwen-max
```

### 3.4 测试连接

点击配置列表中的"测试连接"按钮，验证配置是否正确。

---

## 4. 开始使用

### 4.1 创建会话

1. 访问产品经理 Agent 页面
2. 点击"新建对话"
3. 输入产品想法，例如："我想做个记账软件"

### 4.2 对话流程

Agent 会引导您完成以下阶段：

```
需求澄清 (10-15轮对话)
    ↓
竞品分析 (自动生成)
    ↓
架构设计 (自动生成)
    ↓
详细设计 (自动生成)
    ↓
完整PRD (导出使用)
```

### 4.3 导出PRD

在对话过程中或完成后，可以：
- 点击"查看PRD"预览生成的文档
- 点击"导出"选择 Markdown / PDF / Word 格式

---

## 5. 配置限流（可选）

管理员可以在"系统设置" → "限流配置"中调整：

```yaml
普通用户: 50次/小时
高级用户: 200次/小时
```

---

## 6. 故障排除

### 6.1 API Key 加密错误

**错误**: `InvalidKeyLength` 或加密失败

**解决**:
```bash
# 生成正确的 32 字节密钥
openssl rand -hex 32

# 将生成的密钥设置到 MASTER_KEY 环境变量
```

### 6.2 Redis 连接失败

**错误**: `Connection refused`

**解决**:
```bash
# 检查 Redis 是否运行
redis-cli ping

# 如果没有运行，启动 Redis
redis-server

# 或修改 .env 禁用限流 (不推荐生产环境)
# REDIS_URL=  # 留空则禁用限流
```

### 6.3 大模型 API 调用失败

**错误**: `Connection timeout` 或 `Invalid API key`

**解决**:
1. 检查网络是否能访问对应的 API 地址
2. 在后台管理中测试配置连接
3. 查看后端日志获取详细错误信息

### 6.4 竞品搜索失败

**错误**: `SerpAPI error`

**解决**:
1. 检查 SERPAPI_KEY 是否配置正确
2. 检查 SerpAPI 账户余额
3. 临时禁用竞品分析功能（不影响核心PRD生成）

---

## 7. 生产部署

### 7.1 数据库迁移到 PostgreSQL

```bash
# 修改 .env
DATABASE_URL=postgresql://user:password@localhost/pm_agent

# 重新运行迁移
alembic upgrade head
```

### 7.2 使用 Docker 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "19092:19092"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/pm_agent
      - REDIS_URL=redis://redis:6379/0
      - MASTER_KEY=${MASTER_KEY}
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=pm_agent
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 7.3 环境变量检查清单

部署前确认以下环境变量已配置：

- [ ] `DATABASE_URL` - 数据库连接字符串
- [ ] `REDIS_URL` - Redis 连接字符串
- [ ] `MASTER_KEY` - 加密密钥 (32字节hex)
- [ ] `SERPAPI_KEY` - 搜索API密钥 (可选)
- [ ] `DEFAULT_LLM_PROVIDER` - 默认LLM供应商 (可选)

---

## 8. 开发指南

### 8.1 添加新的 LLM 供应商

1. 创建适配器文件 `backend/src/services/llm/{provider}_adapter.py`
2. 继承 `LLMProvider` 基类
3. 实现 `generate()` 和 `test_connection()` 方法
4. 在 `factory.py` 中注册适配器

### 8.2 修改 PRD 模板

编辑 `backend/src/templates/prd_template.md`，调整生成的PRD结构。

### 8.3 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v

# 前端测试
cd frontend
npm test
```

---

## 9. 参考资源

- **API 文档**: http://localhost:19092/docs
- **需求规格书**: `/specs/001-product-manager-agent/spec.md`
- **数据模型**: `/specs/001-product-manager-agent/data-model.md`
- **API 契约**: `/specs/001-product-manager-agent/contracts/api.yaml`

---

## 10. 获得帮助

遇到问题？

1. 查看后端日志: `tail -f backend/logs/app.log`
2. 查看浏览器开发者工具 Network 面板
3. 检查 API 文档中的错误响应说明
4. 在后台管理中检查大模型配置状态
