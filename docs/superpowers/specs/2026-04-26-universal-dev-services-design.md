---
author: 创建人
created_at: 2026-04-26
purpose: 通用 dev_services.py 设计规范
---

# 通用 dev_services.py 设计

## 概述

将现有的 `dev_services.py` 改造为通用服务管理脚本，可以在任何项目目录下执行，自动发现、管理和操作项目中各类服务。现有 `tools/dev_services.py` 保持不变。

## 架构设计

脚本分为 4 个核心层：

### 1. 项目发现层 (Discovery)

递归扫描当前工作目录（最多 3 层），通过特征文件识别项目类型：

| 特征文件 | 项目类型 | 关键字匹配 |
|---------|---------|-----------|
| `package.json` + vite | vite | `"vite"` in devDependencies/scripts |
| `package.json` + next | next.js | `"next"` in devDependencies |
| `package.json` + express/nestjs | node-backend | `"express"`/`"@nestjs/core"` |
| `requirements.txt` 或 `pyproject.toml` | python | `uvicorn`/`flask`/`django` |
| `pom.xml` | spring-boot | `spring-boot` dependency |
| `build.gradle` | spring-boot-gradle | `spring-boot` plugin |

跳过目录：`node_modules`, `__pycache__`, `.git`, `venv`, `.venv`, `target`, `build`, `dist`, `.omc`

### 2. 配置解析层 (ConfigParser)

从各项目配置文件中提取端口和启动命令：

**端口提取优先级：**
1. `.env` / `.env.development` 中的 `PORT`, `VITE_PORT`, `SERVER_PORT` 等
2. `package.json` scripts 中的 `--port` 参数
3. `pom.xml` 中的 `<server.port>` 属性
4. `build.gradle` 中的 `server.port` 配置
5. 框架默认值

**启动命令推导：**
- vite: `npx vite --port {port}` (优先用本地 node_modules/.bin/vite)
- next: `npx next dev --port {port}`
- node-backend: `node src/index.js` 或 `npx ts-node src/index.ts`
- python: `uvicorn app.main:app --reload --port {port}` 或 `python manage.py runserver {port}`
- spring-boot (maven): `mvn spring-boot:run -Dspring-boot.run.arguments=--server.port={port}`
- spring-boot (gradle): `gradle bootRun --args='--server.port={port}'`

### 3. 进程管理层 (ProcessManager)

复用现有逻辑，核心功能：

- **端口检测**: `check_port(port)` → `(in_use, pids)`
- **进程管理**: `kill_process(pid)`, `stop_service(port)`
- **健康检查**: 两阶段检查（日志关键字 + HTTP 探测）
- **彩色日志**: 统一的日志输出格式

### 4. 交互层 (CLI)

基于 `argparse`，支持以下命令：

```
start [--type TYPE] [--port PORT] [--foreground/-f]  # 启动服务
stop [--type TYPE] [--port PORT]                     # 停止服务
restart [--type TYPE] [--port PORT]                  # 重启服务
status                                               # 查看所有服务状态
kill [--type TYPE] [--port PORT] all|TYPE            # 强制终止
logs TYPE|all                                        # 查看日志
discover                                             # 仅扫描并列出发现的服务（不启动）
```

### 服务抽象

每个被发现的服务抽象为统一数据结构：

```python
@dataclass
class Service:
    name: str            # "前端" / "后端" / "API Server" / "项目名"
    project_type: str    # "vite" / "python" / "spring-boot" / "node"
    project_dir: Path    # 项目根目录
    port: int            # 提取到的端口
    start_cmd: list[str] # 启动命令列表
    health_keyword: str  # 日志关键字 ("ready in" / "Application startup" / "Started ")
    health_url: str      # HTTP 健康检查 URL
    health_timeout: int  # 超时秒数
```

### 日志目录

日志统一写入当前工作目录的 `logs/` 子目录：
- `{cwd}/logs/dev-services.log` — 脚本自身日志
- `{cwd}/logs/{service_name}.log` — 各服务日志

### 安装方式

脚本放在 `~/.claude/dev-services.py`，通过别名调用：

```bash
# Windows (PowerShell Profile)
Set-Alias -Name dev-services -Value "python $HOME\.claude\dev-services.py"

# macOS/Linux (bash/zsh)
alias dev-services="python ~/.claude/dev-services.py"
```

## 风险控制

- **不影响现有服务**: 新脚本放在全局位置，现有 `tools/dev_services.py` 完全不变
- **端口保护**: 仅在端口被占用时 Kill 对应进程，不盲目杀进程
- **深度限制**: 扫描最多 3 层，避免扫描过大目录
- **跳过黑名单**: 自动跳过 `node_modules` 等无关目录
- **依赖提示**: 检测到项目但缺少运行时（如未安装 Java/Python/Node），给出清晰提示而非报错退出

## 验收标准

1. 在 `tools` 项目目录下执行，能正确发现前端（Vite）和后端（FastAPI）服务
2. 在纯 Java Spring Boot 项目目录下执行，能发现并启动 Spring Boot 服务
3. 端口被占用时，先停止占用进程再启动新服务
4. `status` 命令能显示所有发现服务的运行状态
5. 脚本放在 `~/.claude/dev-services.py`，不修改 `tools/dev_services.py`
6. 支持 `--type` 过滤启动特定类型服务
7. 支持 `discover` 命令仅列出发现的服务
