## 1. 后端数据模型变更

- [x] 1.1 在 `backend/app/models/llm_config.py` 中新增 `category` 字段（枚举：chat/code）
- [x] 1.2 新增 `api_key_suffix` 字段（保存最后 4 位）
- [x] 1.3 新增 `notes` 字段（备注）
- [x] 1.4 创建数据库迁移文件
- [x] 1.5 更新 `backend/app/models/__init__.py` 导出

## 2. 后端 API 扩展

- [x] 2.1 在 `CreateLLMConfigRequest` 和 `UpdateLLMConfigRequest` 中添加 `category` 和 `notes` 字段
- [x] 2.2 修改 `LLMConfigResponse` 返回 `category`、`api_key_suffix`、`notes`、`created_at`
- [x] 2.3 添加按分类查询的 API（如需要）

## 3. 前端类型定义

- [x] 3.1 在 `frontend/src/services/llmConfigApi.ts` 中更新 `LLMConfig` 接口
- [x] 3.2 在 `CreateLLMConfigRequest` 中添加 `category` 和 `notes` 字段

## 4. 前端弹窗组件开发

- [x] 4.1 创建 `ConfigModal` 基础弹窗组件
- [x] 4.2 创建 `AddConfigModal` 新增配置弹窗
- [x] 4.3 创建 `EditConfigModal` 编辑配置弹窗（复用 ConfigModal）
- [x] 4.4 创建 `DeleteConfirmModal` 删除确认弹窗

## 5. 前端 API Key 可视化功能

- [x] 5.1 创建 `ApiKeyDisplay` 组件（支持脱敏/显示切换）
- [x] 5.2 添加眼睛图标切换按钮
- [x] 5.3 添加一键复制功能
- [x] 5.4 添加复制成功 Toast 提示

## 6. 前端分类功能

- [x] 6.1 在配置表单中添加分类下拉选择器
- [x] 6.2 在配置列表中显示分类标签
- [x] 6.3 添加分类筛选功能

## 7. 前端记录管理功能

- [x] 7.1 在表单中添加备注字段
- [x] 7.2 在列表中显示创建时间
- [x] 7.3 显示 API Key 后缀（最后 4 位）

## 8. 页面集成与测试

- [x] 8.1 重构 `LLMConfigsPage.tsx`，移除内联表单，使用弹窗
- [x] 8.2 测试新增配置流程
- [x] 8.3 测试编辑配置流程
- [x] 8.4 测试删除配置流程
- [x] 8.5 测试 API Key 显示/隐藏/复制功能
- [x] 8.6 测试分类功能
- [x] 8.7 整体回归测试
