# 桌面应用打包设计

## 概述

将现有 FastAPI + React 工具箱项目打包为 Windows 和 macOS 原生桌面应用，用户双击即可使用，无需安装 Python 或配置开发环境。

## 技术选型

- **打包工具**: PyInstaller
- **内嵌浏览器**: pywebview（macOS 用 WebKit，Windows 用 Edge WebView2）
- **前端加载**: FastAPI 静态文件挂载，通过 `http://127.0.0.1:{port}/` 访问
- **分发格式**: macOS `.app`，Windows `.exe`

## 架构

```
桌面应用窗口 (pywebview)
├── WebView 加载 http://127.0.0.1:{port}/
│   └── 前端: React 构建产物 (dist/)
├── Python 进程 (PyInstaller 打包体内)
│   ├── FastAPI (uvicorn, 后台线程)
│   │   ├── /api/* 业务 API
│   │   └── / 前端静态文件
│   └── pywebview 窗口控制 (主线程)
└── 窗口关闭 → 优雅停止 uvicorn → 退出
```

## 启动流程

1. 用户双击 .app/.exe
2. `desktop_app.py` 加载配置（`.env` 或 `desktop_config.py`）
3. 寻找可用端口（优先 19093，被占用则递增）
4. 在后台线程启动 uvicorn（FastAPI）
5. 轮询等待 FastAPI 就绪
6. 创建 pywebview 窗口（1200x800，支持 F12 开发者工具）
7. 窗口关闭时优雅停止 uvicorn，进程退出

## 关键问题与修正方案

### 1. config.py 的 HOME 覆盖（严重）

`config.py` 第 27 行 `os.environ["HOME"] = str(CACHE_DIR)` 会破坏 `Path.home()` 在所有依赖该变量的代码中的行为。

**修正**: 新增 `backend/desktop_config.py`，桌面模式下：
- 不覆盖 `HOME` 环境变量
- `.env` 从可执行文件同级目录或用户数据目录加载
- `PROJECT_ROOT` 使用 `sys._MEIPASS`（PyInstaller 临时解压目录）或 `Path(sys.executable).parent`

### 2. DATABASE_URL 无默认值（严重）

`Settings.DATABASE_URL` 是必填字段，`.env` 缺失时应用崩溃。

**修正**: 添加默认值 `DATABASE_URL: str = "sqlite:///./data/tools.db"`

### 3. PROJECT_ROOT 在 PyInstaller 冻结模式下路径错误（严重）

`Path(__file__)` 在打包后指向临时解压目录，非原始源码树。

**修正**: `desktop_config.py` 中用 `sys.frozen` 检测 + `Path(sys.executable).parent` 定位运行时目录。

### 4. bcrypt 版本兼容性（高）

`bcrypt==3.2.2` 已知与 PyInstaller 打包不兼容。

**修正**: 升级到 `bcrypt>=4.0.0`（Rust 实现）。验证现有密码哈希向后兼容。

### 5. 外部 CLI 依赖（中）

`usage_fetcher.py` 调用 `ccusage`、`opencode-usage` 等命令行工具，打包后不存在。

**修正**: 桌面模式下这些路由返回功能不可用提示，不阻止应用启动。

### 6. imageio-ffmpeg 运行时下载（中）

视频下载功能依赖 ffmpeg 二进制，运行时下载到临时目录。

**修正**: 桌面模式下视频下载功能降级提示，或要求用户自行安装 ffmpeg。

### 7. WebSocket 兼容性（低）

3 个 WebSocket 端点（OpenClaw、SSH 终端）。pywebview 在 macOS（WebKit）和 Windows（Edge WebView2）上原生支持 WebSocket。

**修正**: 需在两个平台上做回归测试验证。

### 8. 前端 API 相对路径（低，已确认兼容）

前端 `api.ts` 生产构建使用相对路径 `/api`，与 FastAPI 静态文件挂载方案完全兼容。

## 需要新增的文件

| 文件 | 用途 |
|------|------|
| `backend/desktop_config.py` | 桌面模式配置，替代 config.py 的 HOME 覆盖和路径逻辑 |
| `backend/desktop_app.py` | 桌面应用入口，启动 FastAPI + pywebview 窗口 |
| `backend/build_desktop.py` | 一键构建脚本：前端 build → PyInstaller 打包 |
| `backend/desktop.spec` | PyInstaller 打包规格文件 |
| `backend/requirements-desktop.txt` | 桌面打包额外依赖 |
| `backend/assets/icon.icns` | macOS 应用图标 |
| `backend/assets/icon.ico` | Windows 应用图标 |

## 构建流程

```bash
python build_desktop.py [--platform mac|windows] [--dev] [--clean]
```

1. `npm install && npm run build` — 构建前端 dist/
2. `pip install -r requirements-desktop.txt` — 安装 pywebview、pyinstaller
3. `pyinstaller desktop.spec` — 执行打包
4. 输出产物到 `dist/desktop/`（macOS: ToolBox.app, Windows: ToolBox.exe）

## 开发工作流

日常开发不需要重新打包：

1. **桌面窗口 + Vite 热重载** — 设置 `VITE_DEV_URL` 环境变量，桌面窗口指向 `http://localhost:5178`，前端保持热重载
2. **传统浏览器开发** — 继续用 `dev_services.py`，在浏览器中开发

只有需要验证打包效果或分发时才运行 `build_desktop.py`。

## 外部服务依赖

桌面应用不内化任何外部服务，保持现状：
- 数据库：通过 `.env` 配置 PostgreSQL 或默认 SQLite
- Redis：通过 `.env` 配置
- 阿里云 OSS：通过 `.env` 配置
- LLM API：通过已有的 API Key 配置
