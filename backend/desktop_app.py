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
from fastapi import FastAPI  # noqa: E402

logger = logging.getLogger(__name__)

# 全局 uvicorn server 引用，用于优雅关闭
_uvicorn_server = None


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
        # 开发模式：backend/ 的父目录是 tools/，前端在 tools/frontend/
        project_root = Path(__file__).parent.parent  # backend/ -> tools/
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
    global _uvicorn_server

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    _uvicorn_server = server
    server.run()


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
        logger.info(f"开发模式: 使用 Vite 热重载服务器: {vite_url}")
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
