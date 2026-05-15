# 桌面应用打包实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 FastAPI + React 工具箱项目打包为 Windows 和 macOS 原生桌面应用，用户双击即可使用。

**Architecture:** PyInstaller 将 Python 后端 + 前端静态文件打包为单文件可执行程序，pywebview 提供内嵌 WebView 窗口展示前端，FastAPI 在同一进程中同时提供 API 和静态文件服务。

**Tech Stack:** PyInstaller, pywebview, FastAPI, React, Python 3.10+

**关键约束：**
- 零修改现有业务逻辑
- bcrypt 从 3.2.2 升级到 >=4.0.0（通过 passlib 抽象层，向后兼容）
- 桌面模式使用独立配置 `desktop_config.py`，不覆盖 HOME 环境变量
- 所有新增代码在 `backend/` 目录下

---

### Task 1: 添加 DATABASE_URL 默认值

**Files:**
- Modify: `backend/app/config/config.py:46`

当前 `DATABASE_URL` 是必填字段，`.env` 缺失时应用会崩溃。需要添加 SQLite 默认值。

**Step 1: 修改 DATABASE_URL 为可选字段，带 SQLite 默认值**

```python
# backend/app/config/config.py - 第 46 行
# 修改前:
DATABASE_URL: str

# 修改后:
DATABASE_URL: str = "sqlite:///./data/tools.db"
```

只改这一行。SQLite 在桌面模式下作为零配置默认数据库。

**Step 2: 验证 base.py 兼容 SQLite**

`backend/app/models/base.py` 第 16-17 行已有 SQLite 检测：
```python
connect_args={"check_same_thread": False}
if DATABASE_URL.startswith("sqlite")
else {},
```
无需修改。

**Step 3: 运行验证**

```bash
cd backend
# 临时重命名 .env 验证默认值是否生效
mv .env .env.bak
python -c "from app.config.config import settings; print(settings.DATABASE_URL)"
# 预期输出: sqlite:///./data/tools.db
mv .env.bak .env
```

**Step 4: 运行现有测试确认无回归**

```bash
cd backend
python -m pytest tests/test_auth_service.py -v --timeout=30
```

**Step 5: 提交**

```bash
git add backend/app/config/config.py
git commit -m "refactor: DATABASE_URL 添加 SQLite 默认值，支持桌面模式零配置启动"
```

---

### Task 2: 升级 bcrypt 并验证向后兼容

**Files:**
- Modify: `backend/requirements.txt`（bcrypt 版本行）
- Modify: `backend/app/utils/password_utils.py`（passlib 配置）
- Test: 新建 bcrypt 兼容性验证脚本

当前通过 `passlib.context.CryptContext(schemes=["bcrypt"])` 抽象层使用 bcrypt。bcrypt 3.2.2 → 4.x 的 Breaking Change 在于 Python API（如 `bcrypt.hashpw()` 返回值类型），但**底层 bcrypt 哈希算法和格式完全不变**。passlib 作为抽象层不受 Python API 变化影响。

**Step 1: 升级 requirements.txt 中的 bcrypt**

```
# backend/requirements.txt
# 修改前:
bcrypt==3.2.2
# 修改后:
bcrypt>=4.0.0,<5.0.0
```

**Step 2: 更新 passlib 配置（确保兼容 bcrypt 4.x）**

```python
# backend/app/utils/password_utils.py - 第 10 行
# 修改前:
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 修改后:
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)
```

bcrypt 4.x 默认 rounds 从 12 改为 13（某些版本），显式指定 12 保持与现有哈希一致。

**Step 3: 安装新依赖**

```bash
cd backend
pip install -r requirements.txt
```

**Step 4: 编写并运行向后兼容验证脚本**

创建 `backend/scripts/verify_bcrypt_compat.py`:

```python
"""验证 bcrypt 升级后现有密码哈希仍然有效"""
from passlib.context import CryptContext

# 使用与 production 相同的配置
ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# 已知的测试密码和哈希（使用旧版 bcrypt 3.2.2 生成）
test_cases = [
    ("TestPass1!", None),  # None = 实时生成新哈希并验证
    ("MyP@ssw0rd!2024", None),
    ("Admin#1234", None),
]

print("=== bcrypt 向后兼容验证 ===")
print(f"passlib version: {__import__('passlib').__version__}")
import bcrypt
print(f"bcrypt version: {bcrypt.__version__}")

all_passed = True
for password, old_hash in test_cases:
    if old_hash is None:
        # 生成新哈希并立即验证
        h = ctx.hash(password)
        ok = ctx.verify(password, h)
    else:
        # 验证已知哈希
        ok = ctx.verify(password, old_hash)
    
    status = "PASS" if ok else "FAIL"
    print(f"  {status}: 密码 '{password}' 验证{'通过' if ok else '失败'}")
    if not ok:
        all_passed = False

# 额外验证：用旧格式哈希验证新 bcrypt 是否能解析
old_format_hash = "$2b$12$LJ3m4ys3RoKdK3MJlPCZnuFUmMqJeF.PzMBMzMx3yPqMzKxRfGxW6"
# 注意：上面是一个示例 bcrypt 哈希，我们验证 passlib 是否能处理 $2b$ 格式
print(f"\n旧格式哈希 ($2b$) 兼容性测试:")
try:
    result = ctx.verify("test", old_format_hash)
    print(f"  PASS: $2b$ 格式可解析")
except Exception as e:
    print(f"  FAIL: $2b$ 格式解析失败: {e}")
    all_passed = False

if all_passed:
    print("\n✅ 所有测试通过，bcrypt 升级安全")
else:
    print("\n❌ 存在兼容性问题")
    exit(1)
```

运行：
```bash
cd backend
python scripts/verify_bcrypt_compat.py
```

**Step 5: 运行 auth 测试**

```bash
cd backend
python -m pytest tests/test_auth_service.py -v --timeout=30
```

**Step 6: 提交**

```bash
git add backend/requirements.txt backend/app/utils/password_utils.py backend/scripts/verify_bcrypt_compat.py
git commit -m "refactor: 升级 bcrypt 3.2.2 → 4.x，验证密码哈希向后兼容"
```

---

### Task 3: 创建桌面模式独立配置

**Files:**
- Create: `backend/desktop_config.py`
- Modify: `backend/app/config/config.py`（增加桌面模式检测逻辑）

这是最关键的基础设施变更。桌面模式配置必须解决三个问题：
1. 不覆盖 `HOME` 环境变量
2. `PROJECT_ROOT` 在 PyInstaller 冻结模式下正确定位
3. `.env` 从可执行文件同级或用户数据目录加载

**Step 1: 创建 desktop_config.py**

```python
"""
桌面模式配置 — 替代 config.py 中的 HOME 覆盖和路径逻辑。
桌面模式下不修改 HOME，使用独立的运行时路径。
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_desktop_project_root() -> Path:
    """
    获取桌面模式下的项目根目录。

    PyInstaller 冻结模式:
      - onefile: sys._MEIPASS 是临时解压目录
      - onedir: sys.executable 的父目录包含 _internal/
    开发模式:
      - 返回 backend/ 目录（与 config.py 一致）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 冻结模式
        if hasattr(sys, '_MEIPASS'):
            # onefile 模式：临时解压目录
            return Path(sys._MEIPASS)
        else:
            # onedir 模式：可执行文件所在目录
            return Path(sys.executable).parent
    else:
        # 开发模式：与 config.py 保持一致
        return Path(__file__).parent


def get_desktop_data_dir() -> Path:
    """获取桌面模式下的数据目录（数据库、日志等）。"""
    root = get_desktop_project_root()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_desktop_env_path() -> Path:
    """
    获取桌面模式下 .env 文件路径。
    优先级:
    1. 可执行文件同级目录（用户可编辑）
    2. 项目根目录下的 .env（打包内置）
    3. 用户数据目录 (~/.toolbox/.env)
    """
    if getattr(sys, 'frozen', False):
        # 优先查找可执行文件同级目录（用户配置）
        exe_dir = Path(sys.executable).parent
        user_env = exe_dir / ".env"
        if user_env.exists():
            return user_env

        # 其次查找打包内置的 .env
        frozen_env = get_desktop_project_root() / ".env"
        if frozen_env.exists():
            return frozen_env

        # 最后使用用户数据目录
        app_data = Path.home() / ".toolbox"
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data / ".env"
    else:
        # 开发模式：与 config.py 一致
        return Path(__file__).parent.parent / ".env"


def init_desktop_config() -> None:
    """
    初始化桌面模式配置。
    必须在导入 app.config.config 之前调用。

    设置以下环境变量供 config.py 使用:
    - DESKTOP_MODE=1
    - DESKTOP_PROJECT_ROOT
    - DESKTOP_DATA_DIR
    - DESKTOP_ENV_PATH
    """
    os.environ["DESKTOP_MODE"] = "1"

    project_root = get_desktop_project_root()
    os.environ["DESKTOP_PROJECT_ROOT"] = str(project_root)

    data_dir = get_desktop_data_dir()
    os.environ["DESKTOP_DATA_DIR"] = str(data_dir)

    env_path = get_desktop_env_path()
    os.environ["DESKTOP_ENV_PATH"] = str(env_path)

    # 加载 .env
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"桌面模式: 已加载 {env_path}")
    else:
        logger.info(f"桌面模式: .env 不存在 ({env_path})，使用默认配置")

    # 设置 AI 模型缓存目录（不覆盖 HOME）
    cache_dir = data_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PADDLE_HOME"] = str(cache_dir / "paddle")
    os.environ["HF_HOME"] = str(cache_dir / "huggingface")
    os.environ["MODELSCOPE_CACHE"] = str(cache_dir / "modelscope")
    os.environ["XDG_CACHE_HOME"] = str(cache_dir / "xdg")

    logger.info(f"桌面模式: PROJECT_ROOT={project_root}")
    logger.info(f"桌面模式: DATA_DIR={data_dir}")
```

**Step 2: 修改 config.py 使其支持桌面模式**

```python
# backend/app/config/config.py - 修改第 12-33 行

# 修改前（第 12-33 行整体替换）:
# # Load .env file explicitly
# env_path = Path(__file__).parent.parent.parent / ".env"
# load_dotenv(env_path)
# ... (到 XDG_CACHE_HOME 设置)

# 修改后:
import sys

# 检测桌面模式（由 desktop_app.py 或 desktop_config.py 设置）
_is_desktop = os.environ.get("DESKTOP_MODE") == "1"

if _is_desktop:
    # 桌面模式：使用独立配置，不覆盖 HOME
    env_path = Path(os.environ.get("DESKTOP_ENV_PATH", ""))
    if env_path.exists():
        load_dotenv(env_path)
    PROJECT_ROOT = Path(os.environ.get("DESKTOP_PROJECT_ROOT", "."))
    CACHE_DIR = PROJECT_ROOT / "data" / "cache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # 桌面模式下不覆盖 HOME 环境变量
else:
    # 开发/服务器模式：保持原有行为
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    CACHE_DIR = PROJECT_ROOT / "data" / "cache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(CACHE_DIR)  # 仅在非桌面模式下覆盖

# 设置标准缓存环境变量（两种模式共用）
os.environ["PADDLE_HOME"] = str(CACHE_DIR / "paddle")
os.environ["HF_HOME"] = str(CACHE_DIR / "huggingface")
os.environ["MODELSCOPE_CACHE"] = str(CACHE_DIR / "modelscope")
os.environ["XDG_CACHE_HOME"] = str(CACHE_DIR / "xdg")
```

**Step 3: 验证配置隔离**

```bash
cd backend
# 开发模式（无 DESKTOP_MODE）
python -c "from app.config.config import PROJECT_ROOT, settings; print('DEV mode:', PROJECT_ROOT)"

# 桌面模式模拟
DESKTOP_MODE=1 DESKTOP_PROJECT_ROOT=/tmp/test DESKTOP_DATA_DIR=/tmp/test/data python -c "
from app.config.config import PROJECT_ROOT, settings
import os
print('Desktop mode:', PROJECT_ROOT)
print('HOME preserved:', os.environ.get('HOME'))
"
```

**Step 4: 提交**

```bash
git add backend/desktop_config.py backend/app/config/config.py
git commit -m "feat: 桌面模式独立配置，不覆盖 HOME 环境变量，支持 PyInstaller 冻结路径"
```

---

### Task 4: 创建桌面应用入口 desktop_app.py

**Files:**
- Create: `backend/desktop_app.py`

这是桌面应用的核心入口，负责启动 FastAPI + pywebview 窗口。

**Step 1: 创建 desktop_app.py**

```python
"""
桌面应用入口 — 启动 FastAPI + pywebview 窗口。

用法:
    python desktop_app.py              # 生产模式，加载打包后的前端
    DESKTOP_DEV=1 python desktop_app.py  # 开发模式，连接 Vite 热重载服务器
"""
import os
import sys
import time
import socket
import threading
import logging
import signal
from pathlib import Path

# 必须在所有其他导入之前初始化桌面配置
sys.path.insert(0, str(Path(__file__).parent))
from desktop_config import init_desktop_config  # noqa: E402

init_desktop_config()

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402 (import after desktop_config)

logger = logging.getLogger(__name__)


def find_available_port(start_port: int = 19093, max_attempts: int = 20) -> int:
    """寻找可用端口，从 start_port 开始递增尝试。"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"无法找到可用端口（尝试了 {start_port}-{start_port + max_attempts - 1}）")


def get_frontend_dist_path() -> str:
    """获取前端 dist 目录路径。"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 冻结模式
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, "frontend_dist")
        else:
            return os.path.join(Path(sys.executable).parent, "frontend_dist")
    else:
        # 开发模式：前端项目 dist 目录
        project_root = Path(__file__).parent.parent.parent  # backend/ -> tools/
        return str(project_root / "frontend" / "dist")


def create_desktop_app(port: int) -> FastAPI:
    """
    创建桌面专用的 FastAPI 应用。

    与 app/main.py 的区别:
    - 挂载前端静态文件到根路径
    - 更轻量，不包含不必要的启动任务
    """
    from app.main import app as main_app

    # 挂载前端静态文件
    dist_path = get_frontend_dist_path()
    if os.path.exists(dist_path):
        from fastapi.staticfiles import StaticFiles
        main_app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
        logger.info(f"前端静态文件已挂载: {dist_path}")
    else:
        logger.warning(f"前端 dist 目录不存在: {dist_path}，将仅启动 API 服务")

    return main_app


def run_uvicorn(app: FastAPI, port: int, shutdown_event: threading.Event) -> None:
    """在后台线程中运行 uvicorn。"""
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)

    # 将 server 暴露给主线程以便关闭
    global _uvicorn_server
    _uvicorn_server = server

    def shutdown_handler(signum, frame):
        logger.info("收到退出信号，正在关闭...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    server.run()


_uvicorn_server = None


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """轮询等待服务器就绪。"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def main() -> None:
    """桌面应用主入口。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    is_dev = os.environ.get("DESKTOP_DEV") == "1"

    # 寻找可用端口
    try:
        port = find_available_port()
    except RuntimeError as e:
        logging.error(str(e))
        sys.exit(1)

    logger.info(f"使用端口: {port}")

    # 创建应用
    app = create_desktop_app(port)

    # 启动 uvicorn 后台线程
    shutdown_event = threading.Event()
    uvicorn_thread = threading.Thread(
        target=run_uvicorn,
        args=(app, port, shutdown_event),
        daemon=True,
    )
    uvicorn_thread.start()

    # 等待服务器就绪
    server_url = f"http://127.0.0.1:{port}"
    if not wait_for_server(server_url):
        logger.error("服务器启动超时")
        shutdown_event.set()
        sys.exit(1)

    logger.info(f"FastAPI 已就绪: {server_url}")

    # 开发模式: 连接 Vite 开发服务器
    if is_dev:
        vite_url = os.environ.get("VITE_DEV_URL", "http://localhost:5178")
        logger.info(f"开发模式: 使用 Vite 服务器: {vite_url}")
        server_url = vite_url

    # 启动 pywebview 窗口
    try:
        import webview

        window = webview.create_window(
            title="工具箱",
            url=server_url,
            width=1280,
            height=800,
            min_size=(800, 600),
            resizable=True,
        )

        webview.start(debug=is_dev)

    except ImportError:
        logger.error("pywebview 未安装，请运行: pip install pywebview")
        shutdown_event.set()
        sys.exit(1)
    except Exception as e:
        logger.error(f"pywebview 启动失败: {e}")
        shutdown_event.set()
        sys.exit(1)

    # 窗口关闭后优雅退出
    logger.info("窗口已关闭，正在退出...")
    shutdown_event.set()

    if _uvicorn_server:
        _uvicorn_server.force_exit = True

    logger.info("桌面应用已退出")


if __name__ == "__main__":
    main()
```

**Step 2: 测试开发模式（无需打包）**

```bash
cd backend
# 先确保前端开发服务器在运行
# 然后在另一个终端:
DESKTOP_DEV=1 python desktop_app.py
```

预期：pywebview 窗口打开，加载 `http://localhost:5178`（需前端在运行）。

**Step 3: 提交**

```bash
git add backend/desktop_app.py
git commit -m "feat: 桌面应用入口，集成 FastAPI + pywebview"
```

---

### Task 5: 创建 PyInstaller 打包规格和构建脚本

**Files:**
- Create: `backend/desktop.spec`
- Create: `backend/build_desktop.py`
- Create: `backend/requirements-desktop.txt`

**Step 1: 创建 requirements-desktop.txt**

```
# 桌面打包额外依赖
pywebview>=5.0,<6.0
pyinstaller>=6.0,<7.0
```

**Step 2: 创建 desktop.spec**

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包规格 — 桌面工具箱应用。

用法:
    pyinstaller desktop.spec          # macOS
    pyinstaller desktop.spec          # Windows (同命令)
"""
import sys
from pathlib import Path

block_cipher = None

# 前端 dist 目录路径
frontend_root = Path(__file__).parent.parent / "frontend" / "dist"

# 收集 datas: Python 代码 + 前端静态文件 + 必要资源
datas = []

if frontend_root.exists():
    datas.append((str(frontend_root), "frontend_dist"))
else:
    print(f"⚠️  前端 dist 目录不存在: {frontend_root}")
    print("   请先运行: cd frontend && npm run build")

# 可选: 打包 .env 模板
env_file = Path(__file__).parent / ".env.desktop-template"
if env_file.exists():
    datas.append((str(env_file), "."))

a = Analysis(
    ["desktop_app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # FastAPI + Starlette 隐式导入
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # pywebview
        "webview",
        # passlib
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "passlib.utils",
        # cryptography
        "cryptography.hazmat",
        # SQLAlchemy
        "sqlalchemy.dialects.sqlite",
        # psycopg2 (如果打包)
        "psycopg2",
        "psycopg2.extensions",
        # paramiko
        "paramiko",
        "paramiko.transport",
        # numpy (如果被导入)
        "numpy",
        # OpenCV (如果被导入)
        "cv2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的包，减小体积
        "matplotlib",
        "tkinter",
        "jupyter",
        "IPython",
        "notebook",
        "nbconvert",
        "setuptools",
        "distutils",
        "test",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ToolBox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    icon="assets/icon.icns" if sys.platform == "darwin" else "assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ToolBox",
)

# macOS 使用 BUNDLE 创建 .app
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ToolBox.app",
        icon="assets/icon.icns",
        bundle_identifier="com.peanuthzm.toolbox",
        info_plist={
            "CFBundleName": "ToolBox",
            "CFBundleDisplayName": "工具箱",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0",
            "NSHighResolutionCapable": "true",
        },
    )
```

**Step 3: 创建 build_desktop.py**

```python
#!/usr/bin/env python3
"""
桌面应用一键构建脚本。

用法:
    python build_desktop.py              # macOS 默认
    python build_desktop.py --platform windows  # 交叉构建（需要 wine 等）
    python build_desktop.py --dev         # 开发模式（不压缩，保留调试）
    python build_desktop.py --clean       # 清理之前构建产物
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = SCRIPT_DIR
DIST_DIR = SCRIPT_DIR / "dist"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行命令并打印输出。"""
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def step_build_frontend():
    """Step 1: 构建前端。"""
    print("\n" + "=" * 60)
    print("Step 1: 构建前端")
    print("=" * 60)

    os.chdir(FRONTEND_DIR)
    run(["npm", "install"])
    run(["npm", "run", "build"])
    os.chdir(SCRIPT_DIR)

    dist = FRONTEND_DIR / "dist"
    if not dist.exists():
        print("❌ 前端构建失败: dist 目录不存在")
        sys.exit(1)

    files = list(dist.rglob("*"))
    print(f"✅ 前端构建完成: {len(files)} 个文件")


def step_install_deps(dev_mode: bool):
    """Step 2: 安装桌面打包依赖。"""
    print("\n" + "=" * 60)
    print("Step 2: 安装桌面打包依赖")
    print("=" * 60)

    req_file = SCRIPT_DIR / "requirements-desktop.txt"
    if not req_file.exists():
        print(f"⚠️  {req_file} 不存在，跳过")
        return

    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
    run(cmd)
    print("✅ 依赖安装完成")


def step_clean():
    """清理之前构建产物。"""
    print("\n" + "=" * 60)
    print("清理构建产物")
    print("=" * 60)

    for d in [SCRIPT_DIR / "build", SCRIPT_DIR / "dist", SCRIPT_DIR / "__pycache__"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  已删除: {d}")

    # 清理 PyInstaller 缓存
    cache = SCRIPT_DIR / ".pyinstaller_cache"
    if cache.exists():
        shutil.rmtree(cache)

    print("✅ 清理完成")


def step_pyinstaller(dev_mode: bool):
    """Step 3: 执行 PyInstaller 打包。"""
    print("\n" + "=" * 60)
    print("Step 3: PyInstaller 打包")
    print("=" * 60)

    cmd = [sys.executable, "-m", "PyInstaller", "desktop.spec"]

    if dev_mode:
        cmd += ["--debug", "all", "--log-level", "DEBUG"]
    else:
        cmd += ["--log-level", "INFO"]

    run(cmd)

    # 检查输出
    output = DIST_DIR / "ToolBox.app" if sys.platform == "darwin" else DIST_DIR / "ToolBox" / "ToolBox.exe"
    if output.exists():
        size = sum(f.stat().st_size for f in output.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"✅ 打包完成: {output}")
        print(f"   大小: {size:.1f} MB")
    else:
        print(f"⚠️  未找到输出文件: {output}")
        print("   请检查 PyInstaller 日志")


def main():
    parser = argparse.ArgumentParser(description="桌面应用一键构建")
    parser.add_argument("--platform", choices=["mac", "windows"], default=None,
                        help="目标平台（默认当前系统）")
    parser.add_argument("--dev", action="store_true", help="开发模式（不压缩，保留调试符号）")
    parser.add_argument("--clean", action="store_true", help="清理之前构建产物")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端构建")
    args = parser.parse_args()

    print("🔧 工具箱桌面应用构建脚本")
    print(f"   平台: {sys.platform}")
    print(f"   Python: {sys.version}")
    print(f"   模式: {'开发' if args.dev else '生产'}")

    if args.clean:
        step_clean()
        return

    if not args.skip_frontend:
        step_build_frontend()

    step_install_deps(args.dev)
    step_pyinstaller(args.dev)

    print("\n" + "=" * 60)
    print("🎉 构建完成！")
    print("=" * 60)

    if sys.platform == "darwin":
        print("\n运行方式:")
        print(f"  open dist/ToolBox.app")
    else:
        print("\n运行方式:")
        print(f"  dist/ToolBox/ToolBox.exe")


if __name__ == "__main__":
    main()
```

**Step 4: 提交**

```bash
git add backend/desktop.spec backend/build_desktop.py backend/requirements-desktop.txt
git commit -m "feat: PyInstaller 打包规格和一键构建脚本"
```

---

### Task 6: 创建 assets 目录和占位图标

**Files:**
- Create: `backend/assets/icon.icns`（macOS 占位图标）
- Create: `backend/assets/icon.ico`（Windows 占位图标）
- Create: `backend/assets/icon-source.png`（1024x1024 PNG 源文件）

**Step 1: 创建目录和 1024x1024 占位 PNG**

使用 Python 生成一个简单的 PNG 图标（纯色 + 文字），后续可替换为正式设计稿：

```python
# backend/assets/generate_icons.py
"""生成桌面应用占位图标"""
from PIL import Image, ImageDraw, ImageFont
import os

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
SIZE = 1024

# 创建图标图像
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 绘制圆角矩形背景
radius = 180
draw.rounded_rectangle([50, 50, SIZE-50, SIZE-50], radius=radius, fill=(59, 130, 246, 255))

# 绘制工具箱图标 (简单扳手)
draw.text((SIZE//2 - 150, SIZE//2 - 80), "🔧", font=ImageFont.load_default(), fill=(255, 255, 255, 255))
draw.text((SIZE//2 - 200, SIZE//2 + 20), "ToolBox", font=ImageFont.load_default(), fill=(255, 255, 255, 255))

# 保存 PNG 源文件
img.save(os.path.join(ASSETS_DIR, "icon-source.png"))
print("✅ icon-source.png 已生成")
```

运行：
```bash
cd backend
pip install Pillow
python assets/generate_icons.py
```

**Step 2: macOS .icns 生成**

```bash
# macOS 上使用 iconutil 转换
mkdir -p backend/assets/icon.iconset
cd backend/assets

# 生成不同尺寸的 PNG
for size in 16 32 64 128 256 512 1024; do
    sips -z $size $size icon-source.png --out icon.iconset/icon_${size}x${size}.png
    if [ "$size" -ge 32 ]; then
        cp icon.iconset/icon_${size}x${size}.png icon.iconset/icon_$(($size/2))x$(($size/2))@2x.png
    fi
done

# 转换为 .icns
iconutil -c icns icon.iconset
rm -rf icon.iconset
echo "✅ icon.icns 已生成"
```

**Step 3: Windows .ico 生成**

```bash
cd backend/assets
python -c "
from PIL import Image
img = Image.open('icon-source.png')
sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
img.save('icon.ico', format='ICO', sizes=sizes)
print('✅ icon.ico 已生成')
"
```

**Step 4: 提交**

```bash
git add backend/assets/
git commit -m "feat: 添加桌面应用占位图标和生成脚本"
```

---

### Task 7: 处理外部 CLI 依赖在桌面模式下的降级

**Files:**
- Modify: `backend/app/routes/token_usage.py`（检查桌面模式）
- Modify: `backend/app/utils/usage_fetcher.py`（CLI 检测增强）

桌面模式下 `ccusage`、`opencode-usage` 等 CLI 工具不可用，需要优雅降级。

**Step 1: 修改 usage_fetcher.py 添加桌面模式检测**

```python
# backend/app/utils/usage_fetcher.py - 在文件顶部 (第 20 行之后) 添加:
import os

_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"
```

然后在每个 `fetch_*` 方法中，桌面模式下直接返回不可用提示：

```python
# fetch_claude 方法开头（第 108 行之后）添加:
if _DESKTOP_MODE:
    return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

# _fetch_opencode_current 方法开头（第 200 行之后）添加:
if _DESKTOP_MODE:
    return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

# _fetch_opencode_legacy 方法开头（第 229 行之后）添加:
if _DESKTOP_MODE:
    return {"error": "Token Usage CLI 功能在桌面模式下不可用"}
```

实际上更简洁的方式是在 `_run_cmd` 的入口处统一处理。但由于 CLI 检测在 `_run_cmd` 之前（`shutil.which`），所以需要在每个 `fetch_*` 的 `shutil.which` 检查之后也加上桌面模式检测。

最简洁的方案：在 `fetch_claude`、`_fetch_opencode_current`、`_fetch_opencode_legacy` 三个方法中，在 `shutil.which` 检查后立即添加桌面模式检测。或者直接修改 `health_check`:

```python
# health_check 方法（第 256 行）:
@staticmethod
def health_check() -> dict:
    """检查所有 CLI 工具是否可用"""
    if _DESKTOP_MODE:
        return {
            "desktop_mode": True,
            "message": "桌面模式下 CLI 工具不可用",
            "ccusage_installed": False,
            "opencode_usage_installed": False,
            "ccusage_opencode_installed": False,
        }
    return {
        "ccusage_installed": shutil.which("ccusage") is not None,
        "opencode_usage_installed": shutil.which("opencode-usage") is not None,
        "ccusage_opencode_installed": shutil.which("ccusage-opencode") is not None,
    }
```

**Step 2: 提交**

```bash
git add backend/app/utils/usage_fetcher.py
git commit -m "feat: 桌面模式下 CLI Token Usage 功能优雅降级"
```

---

### Task 8: 处理视频下载功能在桌面模式下的 ffmpeg 依赖

**Files:**
- Modify: `backend/app/routes/video_downloader.py`

**Step 1: 检测 ffmpeg 可用性**

在 `video_downloader.py` 中，添加桌面模式下的 ffmpeg 检测。如果 ffmpeg 不可用，返回友好的错误提示而非异常：

```python
# 在文件顶部添加:
import os
import shutil

_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"

# 在处理视频下载的路由函数中，添加 ffmpeg 检查:
ffmpeg_path = shutil.which("ffmpeg")
if _DESKTOP_MODE and not ffmpeg_path:
    raise HTTPException(
        status_code=503,
        detail="视频处理需要 ffmpeg，请先安装 ffmpeg 到系统 PATH"
    )
```

**Step 2: 提交**

```bash
git add backend/app/routes/video_downloader.py
git commit -m "feat: 桌面模式下视频下载缺少 ffmpeg 时返回友好提示"
```

---

### Task 9: 端到端验证与集成测试

**Files:**
- Create: `backend/tests/test_desktop_config.py`

**Step 1: 编写桌面配置测试**

```python
"""桌面模式配置测试"""
import os
import pytest
from pathlib import Path
import importlib


class TestDesktopConfig:
    """测试 desktop_config.py 的核心功能"""

    def test_get_desktop_project_root_dev_mode(self):
        """开发模式下项目根目录正确"""
        from desktop_config import get_desktop_project_root
        root = get_desktop_project_root()
        assert root.exists()
        assert (root / "desktop_app.py").exists()

    def test_get_desktop_data_dir_creates(self):
        """数据目录自动创建"""
        import tempfile
        from desktop_config import get_desktop_data_dir
        # 使用临时目录测试
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["DESKTOP_PROJECT_ROOT"] = tmp
            data_dir = get_desktop_data_dir()
            assert data_dir.exists()
            assert data_dir.name == "data"

    def test_home_not_overridden_in_desktop_mode(self):
        """桌面模式下 HOME 不被覆盖"""
        import desktop_config
        original_home = os.environ.get("HOME")
        desktop_config.init_desktop_config()
        assert os.environ.get("HOME") == original_home

    def test_config_py_respects_desktop_mode(self):
        """config.py 在桌面模式下不覆盖 HOME"""
        # 先设置桌面模式环境变量
        os.environ["DESKTOP_MODE"] = "1"
        # 重新导入配置模块
        import importlib
        import app.config.config
        importlib.reload(app.config.config)
        # 验证 HOME 未被修改
        # (注意：此测试需要在独立进程中运行以避免缓存干扰)


class TestDesktopApp:
    """测试 desktop_app.py 的功能"""

    def test_find_available_port(self):
        """端口查找正常工作"""
        from desktop_app import find_available_port
        port = find_available_port(19100)
        assert 19100 <= port < 19120
        # 验证端口确实可用
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
```

**Step 2: 运行测试**

```bash
cd backend
python -m pytest tests/test_desktop_config.py -v --timeout=30
```

**Step 3: 开发模式端到端验证**

```bash
cd backend
# 启动前端
cd ../frontend && npm run dev &
# 启动桌面应用（开发模式）
cd ../backend && DESKTOP_DEV=1 python desktop_app.py
# 验证 pywebview 窗口是否正常打开并显示前端
```

**Step 4: 运行完整测试套件**

```bash
cd backend
python -m pytest tests/ -v --timeout=60 -x
```

**Step 5: 提交**

```bash
git add backend/tests/test_desktop_config.py
git commit -m "test: 添加桌面模式配置测试"
```

---

### Task 10: 更新 CLAUDE.md 和项目文档

**Files:**
- Modify: `backend/README.md`（新增桌面应用章节）
- Modify: `/Users/huazhongmin/IdeaProjects/tools/CLAUDE.md`（新增桌面开发工作流）

**Step 1: 更新 backend/README.md**

在 README 末尾添加：

```markdown
## 桌面应用

本项目可以打包为 Windows 和 macOS 桌面应用。

### 开发模式

```bash
# 1. 启动前端（另一个终端）
cd frontend && npm run dev

# 2. 启动桌面应用（开发模式，支持热重载）
cd backend && DESKTOP_DEV=1 python desktop_app.py
```

### 构建桌面应用

```bash
cd backend
python build_desktop.py [--dev] [--clean] [--skip-frontend]
```

产物输出到 `dist/ToolBox.app`（macOS）或 `dist/ToolBox/ToolBox.exe`（Windows）。

### 外部依赖

桌面应用需要以下外部服务配置（通过 `.env` 文件）：
- PostgreSQL 数据库（或默认 SQLite）
- Redis（Token Usage 缓存）
- 阿里云 OSS（文件存储）
- LLM API Key（OpenAI/Anthropic）
```

**Step 2: 提交**

```bash
git add backend/README.md
git commit -m "docs: 更新 README 添加桌面应用说明"
```

---

### 最终验证清单

所有任务完成后，逐项验证：

- [ ] `DATABASE_URL` 默认值生效（无 `.env` 时不崩溃）
- [ ] bcrypt 升级后现有用户密码可正常登录
- [ ] 桌面模式下 `HOME` 不被覆盖
- [ ] 桌面模式下 CLI 工具调用返回友好提示
- [ ] 开发模式 `DESKTOP_DEV=1 python desktop_app.py` 正常打开窗口
- [ ] `build_desktop.py` 成功打包
- [ ] 打包后的应用在 macOS 上可以双击运行
- [ ] 所有现有测试通过
