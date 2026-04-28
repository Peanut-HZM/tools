# 工具列表按使用次数倒序排序设计

**日期**：2026-04-27  
**需求**：确保后台管理中的工具管理以及展示给用户端的工具列表，都按使用次数倒序排列

## 现状

| 场景 | 当前排序 | 代码位置 |
|---|---|---|
| 用户端 GET /api/tools | `ORDER BY category, title` | `tools_service.py` `get_tools_for_platform()` |
| 用户端按分类 GET /api/tools/category/{cat} | `ORDER BY title` | `tools_service.py` `get_tools_by_category()` |
| 后台管理 GET /api/admin/tools | 支持 `sort_by` 参数，含 `usage_count` | `tools_service.py` `get_tools_paginated()` |
| 后台管理前端默认 | `title-asc` | `ToolManagement.tsx:28-29` |

## 方案：最小改动

### 修改点

1. **后端 `get_tools_for_platform()`**：将 `ORDER BY category, title` 改为 `ORDER BY usage_count DESC, title ASC`（使用次数倒序，同次数按名称正序）
2. **后端 `get_tools_by_category()`**：将 `ORDER BY title` 改为 `ORDER BY usage_count DESC, title ASC`
3. **前端管理页**：将默认排序从 `title-asc` 改为 `usage_count-desc`

### 不改动的部分

- 搜索结果排序保持不变（按相关性更合理）
- 后台管理已有的排序选择器保留，仅改默认值
- 数据库 schema 无需变更（`usage_count` 字段已存在）