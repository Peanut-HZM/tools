---
author: Peanut
created_at: 2026-05-17
purpose: 数据库工具页面加载慢优化
---

# 数据库工具页面加载慢优化

## 问题

进入 `/tools/database-tool` 页面时，数据加载很慢。

## 根因

`database_tool_service.py` 中所有数据库操作仍使用 `get_db_connection()` 直接创建连接，未使用已添加的连接池。页面加载时两个并行请求（`getDatabases` + `getHistory`）各自新建连接，导致延迟。

## 方案

将 `database_tool_service.py` 中所有 `get_db_connection()` 替换为 `get_pooled_db_connection()`，所有 `conn.close()` 替换为 `release_db_connection(conn)`。与 `tools_service.py` 采用完全相同的模式。

## 影响范围

| 文件 | 变更 |
|------|------|
| `backend/app/services/database_tool_service.py` | 全部 `get_db_connection()` → `get_pooled_db_connection()`，`conn.close()` → `release_db_connection(conn)` |

## 验证

1. 重启后端服务
2. 打开数据库工具页面
3. 观察页面加载速度是否改善
