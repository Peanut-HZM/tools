## Why

当前大模型配置管理功能存在以下问题：
1. **交互方式落后**：增删改查使用内联表单而非弹窗，体验不统一
2. **API Key 不透明**：完全不可见，无法复制复用，也没有分类管理
3. **缺乏记录管理**：API Key 被使用后没有记录，想在其他平台使用时无法查看

用户希望能够像管理密码一样管理大模型 API Key，支持分类、可视化复制、创建新 Key 等功能。

## What Changes

### 前端改动
1. **弹窗式交互**：所有增删改操作改为弹窗对话框
2. **API Key 可视化**：
   - 添加眼睛图标切换显示/脱敏
   - 默认脱敏显示（如 `sk-xxxx...abcd`）
   - 点击复制按钮一键复制
3. **API Key 分类**：新增分类字段（对话类型 / 编程类型）
4. **API Key 管理功能**：
   - 显示创建时间、最后使用时间
   - 支持备注/标签
   - 历史记录查看

### 后端改动
1. **数据模型扩展**：
   - 新增 `category` 字段（chat/code）
   - 新增 `api_key_last_chars` 字段（保存最后几位方便识别）
   - 新增 `notes` 字段（备注）
   - 新增 `created_by` 字段
2. **API 扩展**：
   - 新增分类查询
   - 新增复制记录功能
   - 新增备注更新接口

## Capabilities

### New Capabilities
- `llm-config-modal`: 弹窗式配置管理界面
- `llm-key-visibility`: API Key 可视化与复制功能
- `llm-key-categorization`: API Key 分类管理（对话/编程）
- `llm-key-management`: API Key 记录与历史管理

### Modified Capabilities
- `001-product-manager-agent`: 大模型 Agent 可能需要适配新的配置结构

## Impact

### 受影响代码
- `frontend/src/components/Admin/LLMConfigsPage.tsx` - 重构为弹窗
- `frontend/src/services/llmConfigApi.ts` - 新增 API
- `backend/app/models/llm_config.py` - 数据模型扩展
- `backend/app/api/routes/llm_config.py` - 新增接口
- `backend/app/services/llm_config_service.py` - 业务逻辑扩展
