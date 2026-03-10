# Agent系统重构设计方案

## 📋 项目概述

将现有的"产品经理Agent"重构为通用的"Agent系统"，支持多Agent管理和切换。

## 🏗️ 架构设计

### 1. 数据库设计

**表名**: `agents`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(100) | Agent名称 |
| description | TEXT | Agent描述 |
| system_prompt | TEXT | 系统提示词 |
| icon | VARCHAR(50) | 图标类名 |
| icon_color | VARCHAR(100) | 图标颜色样式 |
| category | VARCHAR(50) | 分类 |
| is_active | BOOLEAN | 是否启用 |
| is_default | BOOLEAN | 是否为默认 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**默认Agent数据**:
1. 产品经理助手（保留现有功能）
2. 代码助手（新增）
3. 写作助手（新增）

### 2. 后端API设计

#### Agent管理API (管理员)

```
GET    /api/v1/admin/agents              # 获取Agent列表
POST   /api/v1/admin/agents              # 创建Agent
GET    /api/v1/admin/agents/{id}         # 获取Agent详情
PUT    /api/v1/admin/agents/{id}         # 更新Agent
DELETE /api/v1/admin/agents/{id}         # 删除Agent
POST   /api/v1/admin/agents/{id}/default # 设为默认
GET    /api/v1/admin/agents/stats        # 获取统计
```

#### Agent公开API (所有用户)

```
GET /api/v1/agents              # 获取启用的Agent列表
GET /api/v1/agents/default      # 获取默认Agent
```

#### 修改现有对话API

```
POST /api/v1/conversations/{id}/chat/stream
```

**请求参数变更**:
```json
{
  "content": "用户消息",
  "llm_config_id": "模型配置ID",
  "agent_id": "Agent ID"  // 新增
}
```

### 3. 前端页面设计

#### 首页工具卡片变更

**当前**: 产品经理 Agent
**改为**: AI Agent

点击后跳转到Agent选择页面或直接打开对话页面使用默认Agent

#### 对话页面变更

**顶部工具栏增加**:
- Agent选择下拉框（切换不同Agent）
- 显示当前Agent名称和图标

#### 后台管理新增

**侧边栏菜单**: Agent管理

**页面功能**:
- Agent列表（名称、描述、状态、操作）
- 添加Agent按钮
- 编辑Agent（弹窗表单）
  - 名称
  - 描述
  - 系统提示词（textarea，支持多行）
  - 图标选择
  - 图标颜色
  - 分类
  - 启用/禁用
- 设为默认
- 删除

## 📝 实施步骤

### Phase 1: 数据库和后端基础
1. ✅ 创建 `Agent` 模型
2. ✅ 创建Agent管理服务
3. ⬜ 创建Agent管理API路由
4. ⬜ 修改流式对话接口，支持 `agent_id` 参数
5. ⬜ 执行数据库迁移

### Phase 2: 前端基础
6. ⬜ 创建Agent API服务
7. ⬜ 修改首页工具卡片
8. ⬜ 修改对话页面，增加Agent选择器
9. ⬜ 创建后台Agent管理页面

### Phase 3: 数据迁移和验证
10. ⬜ 将产品经理配置迁移为Agent
11. ⬜ 功能验证测试

## 🔧 关键代码变更点

### 1. 流式对话接口 (chat_stream.py)

**当前系统提示词**:
```python
"你是一个专业的产品经理助手..."
```

**改为根据Agent动态获取**:
```python
agent_service = AgentManagementService(db)
if agent_id:
    agent = agent_service.get_agent(agent_id)
else:
    agent = agent_service.get_default_agent()

system_prompt = agent.system_prompt if agent else "默认提示词"
```

### 2. 前端对话页面 (ProductManagerAgent.tsx)

**增加Agent状态**:
```typescript
const [agents, setAgents] = useState<Agent[]>([]);
const [selectedAgentId, setSelectedAgentId] = useState<string>('');
```

**增加Agent选择器**:
```typescript
<select value={selectedAgentId} onChange={...}>
  {agents.map(agent => (
    <option key={agent.id} value={agent.id}>
      {agent.name}
    </option>
  ))}
</select>
```

### 3. 工具数据 (tools_data.py)

**修改产品经理Agent为通用Agent**:
```python
Tool(
    id="ai-agent",
    icon="fa-robot",
    iconColor="bg-gradient-to-r from-blue-500 to-purple-500",
    title="AI Agent",
    description="智能AI助手，支持多种专业场景的对话和咨询",
    ...
)
```

## ✅ 验收标准

1. [ ] 首页显示"AI Agent"而不是"产品经理 Agent"
2. [ ] 点击AI Agent可以进入对话页面
3. [ ] 对话页面可以选择不同的Agent
4. [ ] 不同Agent使用不同的系统提示词回复
5. [ ] 后台管理可以查看所有Agent
6. [ ] 后台管理可以添加新的Agent
7. [ ] 后台管理可以编辑Agent的提示词
8. [ ] 后台管理可以删除Agent
9. [ ] 后台管理可以设置默认Agent
10. [ ] 原有产品经理Agent作为默认Agent保留

## 🚀 下一步行动

需要我继续开发实现吗？我可以：
1. 继续完成后端API开发
2. 创建前端Agent管理页面
3. 修改现有对话页面支持Agent切换
4. 执行数据库迁移

请告诉我你希望优先进行哪部分开发！
