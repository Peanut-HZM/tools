---
purpose: 统一后端端口为 19092（dev-services 默认值与 backend/.env 兜底对齐），修复本地前端因后端跑在 8000 而 API 不可用的爆粗问题
date: 2026-08-09
---

# 后端端口统一 19092 设计

## 背景

同步服务器 `backend/.env` 后，本地 `python dev-services.py restart backend` 启动的后端跑在 8000（dev-services 默认），而 `frontend/.env.development` 的 Vite 代理目标 `VITE_API_PROXY_TARGET=http://127.0.0.1:19092` 转发到 19092 → 19092 端口无人监听，前端 API 请求全部爆粗。

项目既定端口是 19092（CLAUDE.md、`config.py` 默认值、`.env.example` 均是 19092），需要"所有相关地方"统一回 19092。

## 根因

1. `dev-services.py:68` 硬编码默认 Python 后端端口 `8000`
2. `dev-services.py:285` 从**系统环境变量**读 `BACKEND_PORT`，但不读 `backend/.env`
3. 服务器同步下来的 `backend/.env` 没有 `BACKEND_PORT`
4. → dev-services 用默认 8000 启动 uvicorn，与前端代理目标 19092 错位

## 方案

双保险：`.env` 显式声明 `BACKEND_PORT=19092` + `dev-services.py` 默认值改为 19092。杜绝默认偏移隐患。

## 改动

### `backend/.env`（gitignored，本地配置）

新增一行：

```
BACKEND_PORT=19092
```

### `dev-services.py:68`

```python
    "python": 8000,
```

改为：

```python
    "python": 19092,
```

## 影响范围

- `backend/.env`（gitignored，不进版本库）
- `dev-services.py:68`（默认端口常量）

## 不动

- `config.py` 的 `BACKEND_PORT: Optional[int] = 19092`（已是 19092）
- `frontend/.env.development` 的 `VITE_API_PROXY_TARGET=http://127.0.0.1:19092`（已对）
- `frontend/.env.production` 的 `VITE_API_BASE_URL=https://tools.peanuthzm.com.cn/api`（公网，与本地端口无关）
- `CLAUDE.md`（文档已是 19092）

## 验证

1. `python dev-services.py restart backend` → 健康检查 URL 应为 `http://127.0.0.1:19092`
2. `python dev-services.py status` → 显示 `端口: 19092`
3. 浏览器访问 `http://localhost:5178` 并触发一个 API 请求（如打开 cross-share 文件列表）→ 请求成功，无网络/CORS 错误
4. 前端 Vite dev 日志中不应出现 `/api` 代理到 8000 的痕迹

## 回滚

```bash
git checkout HEAD -- dev-services.py
# backend/.env 是 gitignored，手动删除 BACKEND_PORT=19092 行
```