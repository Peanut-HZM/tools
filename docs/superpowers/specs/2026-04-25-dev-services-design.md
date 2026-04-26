---
author: Peanut
created_at: 2026-04-25
purpose: Design spec for optimizing dev_services.py with health checks, colored logging, foreground mode, and comprehensive service management
---

# Dev Services 脚本优化设计

## 目标

优化 `dev_services.py`，解决以下问题：
1. 日志输出不友好（无颜色、无状态反馈）
2. 启动后不检查服务是否真正就绪
3. 缺少健康检查机制
4. 缺少 kill 和 logs 子命令
5. 存在 unreachable 代码 bug

## 架构

### 日志系统

使用 ANSI 颜色码实现彩色输出，Windows 兼容处理：

| 级别 | 颜色 | 用途 |
|------|------|------|
| INFO | 白色 | 常规信息 |
| SUCCESS | 绿色 | 服务已就绪等成功状态 |
| WARN | 黄色 | 端口占用等警告 |
| ERROR | 红色 | 启动失败等错误 |

格式：`[HH:MM:SS] [LEVEL] message`，控制台带 ANSI 颜色码。Windows 兼容性：
- 调用 `sys.stdout.reconfigure(encoding='utf-8')` 确保 UTF-8 输出
- Windows 10+ 原生支持 ANSI，无需 `colorama`
- 日志文件纯文本（无 ANSI 转义码）

### 健康检查

两阶段检测，先日志关键字再 HTTP 探测：

**后端健康检查：**
1. 轮询 `logs/backend.log`，等待 `Application startup complete`（超时 30s）
2. HTTP GET `http://127.0.0.1:19092/docs`，等待 200（超时 10s）

**前端健康检查：**
1. 轮询 `logs/frontend.log`，等待 `ready in`（超时 30s）
2. HTTP GET `http://localhost:5178`，等待 200（超时 10s）

**失败处理：** 输出日志文件最后 20 行帮助诊断。

**实现方式：** 优先用 `requests`，无则用 `urllib.request`（标准库 fallback）。

**日志轮询：** 每 1 秒检查一次日志文件新增内容（追踪文件读取位置，只读新增部分，避免全文件重复读取）。超时 30s 后判定失败。

### 运行模式

**后台模式（默认）：** 启动后返回命令行，子进程输出重定向到日志文件。

**前台模式（`--foreground` / `-f`）：** 子进程 stdout/stderr 实时输出到终端，支持 Ctrl+C 优雅停止。Windows 实现：使用 `subprocess.CREATE_NEW_PROCESS_GROUP` 创建进程组，捕获 `KeyboardInterrupt` 后调用 `proc.terminate()` 终止子进程（Windows 上 SIGINT 行为与 POSIX 不同，不依赖 signal 模块）。

### 命令接口

```
python dev_services.py <action> [options]

action:
  start         启动服务（默认）
  stop          停止服务
  kill          强制终止服务
  restart       重启服务
  status        查看服务状态
  logs          实时查看日志

options:
  --backend-only    只操作后端
  --frontend-only   只操作前端
  --foreground, -f  前台模式（仅 start 有效）
```

**kill 子命令：** `python dev_services.py kill backend|frontend|all`
- `stop` = 优雅停止：`proc.terminate()` + 等待 3s + `proc.kill()` 强制
- `kill` = 强制终止：直接 `proc.kill()`，不等待
- 两者都支持 `--backend-only` / `--frontend-only` 参数

**日志模式：** 统一使用 `"w"` 模式（每次启动覆盖旧日志），避免日志文件无限增长。

**logs 子命令：** `python dev_services.py logs backend|frontend|all`
- Windows 平台：优先使用 PowerShell `Get-Content -Wait -Tail 50`
- Fallback：Python 实现文件轮询（每 1 秒读取新增内容）

## 实现细节

### 依赖

不引入新的 pip 依赖。使用标准库：`argparse`, `os`, `signal`, `subprocess`, `sys`, `time`, `psutil`, `shutil`, `socket`, `pathlib`, `datetime`, `urllib.request`, `http.client`。

`psutil` 已有（项目已安装）。

### 代码结构

单文件 `dev_services.py`，按功能分组：

```
# 常量定义
# 工具函数：log(), check_port(), find_process_by_port()
# 进程管理：start_backend(), start_frontend(), stop_service(), kill_service(), stop_all()
# 健康检查：wait_for_log_keyword(), http_health_check(), check_health()
# 前台模式：run_foreground()
# 子命令：status(), tail_logs()
# 入口：main()
```

### 修复现有 bug

- 删除 `start_frontend()` 中第 187-188 行 unreachable 代码
- `stop_all()` 支持 `--backend-only` / `--frontend-only` 参数

## 数据流

```
start 命令
  → 停止已有进程（restart 时）
  → start_backend() / start_frontend()
  → 输出 "等待服务就绪..."
  → wait_for_log_keyword() → 日志出现关键字
  → http_health_check() → HTTP 200
  → 输出 "服务已就绪"
  → 返回
```
