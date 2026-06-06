---
author: Peanut
created_at: 2026-06-06
purpose: dev-services.py 启动前自动安全安装缺失依赖的设计方案
---

# dev-services.py 启动前依赖自动安装设计

## 背景

当前 `dev-services.py` 在启动服务前不会检查依赖是否已安装。如果 `node_modules` 缺失或 Python venv 中缺少 `requirements.txt` 中的包，服务启动会直接失败（如 `ModuleNotFoundError: No module named 'apscheduler'`）。

## 目标

在启动服务前，安全地检查并安装缺失的依赖，降低因依赖缺失导致的启动失败。

## 设计原则

1. **保守安装**：只在检测到依赖缺失时才安装，避免每次启动都重复安装
2. **安全降级**：安装失败不阻断启动流程，继续尝试启动，让健康检查做最终判断
3. **对称一致**：前后端安装逻辑风格统一，易于理解和维护

## 方案概述

采用**方案二：抽离独立的依赖安装模块**，在 `start_service()` 中插入依赖安装步骤。

## 详细设计

### 1. 新增依赖安装函数

```python
def install_dependencies(svc: Service) -> bool:
    """根据服务类型安装缺失的依赖。返回 True 表示依赖已满足（或无需安装），
    False 表示安装失败（但不阻断启动）。"""
```

按服务类型分发：

#### 1.1 Python 后端

- **检查方式**：读取 `requirements.txt`，提取前 3~5 个关键包名，尝试用服务对应的 Python 解释器执行 `python -c "import pkg1, pkg2, ..."`
- **安装触发**：任一导入失败时，运行 `{python_exe} -m pip install -r requirements.txt`
- **使用解释器**：优先使用服务检测到的 venv Python（`venv/Scripts/python.exe` 或 `.venv/bin/python`），回退到 `sys.executable`

#### 1.2 前端（Vite / Taro / UniApp / Next.js）

- **检查方式**：检查 `node_modules` 目录是否存在
- **安装触发**：`node_modules` 不存在时，运行 `{package_manager} install`
- **包管理器选择**：优先 `pnpm`（`pnpm-lock.yaml` 存在）> `yarn`（`yarn.lock` 存在）> `npm`

#### 1.3 Node.js 后端

- **检查方式**：同前端，检查 `node_modules` 是否存在
- **安装触发**：缺失时运行 `npm install`

#### 1.4 Spring Boot（Maven / Gradle）

- **暂不处理**：Maven/Gradle 的依赖安装通常在编译时自动处理（`mvn spring-boot:run` 会自动下载依赖），暂不需要额外步骤

### 2. 启动流程变更

在 `start_service()` 函数中，在「端口占用检查」之后、「启动进程」之前插入依赖安装步骤：

```
启动服务流程：
  ├── 检查目录存在
  ├── 清理孤儿进程（Python）
  ├── 检查端口占用 → 如有则先停止
  ├── 【新增】安装依赖（如缺失）
  │     ├── 检查依赖是否满足
  │     ├── 缺失 → 执行安装命令
  │     └── 安装失败 → log WARN，继续启动
  ├── 启动进程
  └── 健康检查
```

### 3. 日志与降级行为

| 场景 | 日志级别 | 行为 |
|------|----------|------|
| 依赖已满足，无需安装 | DEBUG | 跳过，直接启动 |
| 依赖缺失，开始安装 | INFO | 显示安装命令 |
| 安装成功 | SUCCESS | 继续启动 |
| 安装失败 | WARN | 不阻断，继续尝试启动 |
| 无法判断依赖状态 | WARN | 跳过安装，继续启动 |

### 4. 边界情况

- **`requirements.txt` 不存在**：跳过 Python 依赖检查（某些项目用 `pyproject.toml`）
- **`node_modules` 存在但内容损坏**：保守策略下无法检测，依赖健康检查兜底
- **网络不可用导致 install 失败**：log WARN 后继续启动，开发者会看到启动失败日志
- **多个服务同时缺失依赖**：串行安装，避免并发冲突

## 不处理的范围

- 不对比 `package.json` / `requirements.txt` 的时间戳（超出保守策略范围）
- 不自动创建 Python venv（假设 venv 已由开发者创建）
- 不处理 `pyproject.toml` 依赖（当前项目均使用 `requirements.txt`）

## 验收标准

1. `node_modules` 缺失的前端项目启动时，脚本自动运行 `npm install` 后再启动
2. Python venv 中缺少 `requirements.txt` 中的包时，脚本自动运行 `pip install` 后再启动
3. 安装失败时，脚本 log 警告但继续尝试启动
4. 依赖已满足时，安装步骤被跳过，启动速度不受影响
