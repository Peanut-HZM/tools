## Context

### 当前状态
- 后端 `LLMConfig` 模型包含基础字段：id, name, provider_type, base_url, api_key_encrypted, model_name, request_params, is_default, is_active, created_at
- 前端 `LLMConfigsPage.tsx` 使用内联表单进行增删改查
- API Key 完全不可见（type="password"），无法复制

### 利益相关者
- 管理员：需要管理多个大模型配置
- 开发者：需要复制 API Key 到其他平台使用
- 普通用户：使用各功能时调用大模型

### 约束
- API Key 必须加密存储（安全要求）
- 需要兼容现有的大模型调用逻辑
- 前端使用 React + Tailwind CSS

## Goals / Non-Goals

### Goals（目标）
1. 弹窗式交互：所有操作使用 Modal 对话框
2. API Key 可视化：眼睛图标切换显示/脱敏，一键复制
3. 分类管理：区分对话类型和编程类型
4. API Key 记录管理：创建时间、使用历史、备注

### Non-Goals（不在范围内）
- 大模型调用逻辑修改（仅管理界面）
- API Key 使用统计图表
- 批量导入/导出
- API Key 过期提醒

## Decisions

### D1: Modal vs Drawer
**决策**：使用 Modal（模态框）而非 Drawer（抽屉）
**理由**：
- LLM 配置字段数量适中（8-10个），Modal 足够展示
- Drawer 适合复杂表单或需要同时参考其他内容的场景
- Modal 体验更集中，用户专注于单一任务

### D2: API Key 显示策略
**决策**：存储完整 Key，前端控制显示策略
**方案**：
- 后端存储：保持 `api_key_encrypted` 完整加密存储
- 前端显示：默认显示脱敏版本（如 `sk-abc...xyz`），点击眼睛显示完整
- 复制功能：点击复制按钮直接复制完整 Key

**备选方案考虑**：
- 只存前后各4位 + 中间脱敏 → 复制时需要调用后端解密（不安全且慢）
- 最终采用：前端本地处理显示，后端只返回是否需要脱敏的标志

### D3: 分类字段设计
**决策**：新增 `category` 字段，使用枚举
```python
class LLMConfigCategory(str, Enum):
    CHAT = "chat"      # 对话类型
    CODE = "code"      # 编程类型
```

**理由**：
- 枚举确保数据一致性
- 便于后续扩展（如 IMAGE = "image" 图像生成类型）

### D4: API Key 识别方案
**决策**：新增 `api_key_suffix` 字段，保存最后 4 位
```python
api_key_suffix = Column(String(4), nullable=True)  # 方便用户识别是哪个 Key
```

**理由**：
- 用户可能有多个同供应商的 Key，需要识别
- 只存最后4位，即使泄露也不影响安全

### D5: 前端组件结构
**决策**：提取 Modal 组件，复用现有 UI 组件
```
LLMConfigsPage.tsx
├── AddConfigModal     # 新增弹窗
├── EditConfigModal    # 编辑弹窗  
├── DeleteConfirmModal # 删除确认弹窗
└── ConfigDetailModal # 详情弹窗（可选）
```

**理由**：
- 保持代码组织清晰
- Modal 内容较长时便于维护

## Risks / Trade-offs

### R1: API Key 安全
**风险**：前端显示完整 Key 可能被截屏或泄露
**缓解**：
- 页面添加水印（可选）
- 切换显示后 N 秒自动隐藏
- 复制后提示"Key 已复制，请妥善保管"

### R2: 向后兼容性
**风险**：数据模型变更影响现有配置
**缓解**：
- 新增字段均有默认值
- 旧数据迁移：category 默认为 "chat"
- 删除字段使用软删除

### R3: 用户体验复杂度
**风险**：功能过多导致界面复杂
**缓解**：
- 弹窗分步：基本信息 → 高级配置
- 使用折叠面板隐藏不常用字段
- 保持核心操作（增删改）简洁

## Migration Plan

### 步骤 1: 后端模型变更
```bash
# 数据库迁移
alembic revision --autogenerate -m "add llm_config category and suffix"
```

### 步骤 2: 前端 API 更新
- 更新 TypeScript 类型定义
- 添加新的 API 调用

### 步骤 3: 前端组件重构
- 提取 Modal 组件
- 实现眼睛切换功能
- 添加复制功能

### 回滚计划
如果出现问题：
1. 前端：回滚到内联表单版本（功能降级）
2. 后端：数据模型新增字段不影响现有接口
