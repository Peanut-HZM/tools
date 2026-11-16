"""
桌面应用入口 — 启动 FastAPI + pywebview 窗口。

用法:
    python desktop_app.py                # 生产模式，嵌入式后端 + 前端静态页面（同源）
    DESKTOP_DEV=1 python desktop_app.py  # 开发模式，窗口直连 Vite 热重载服务器
                                         # （需 dev-services.py 已启动 19092 后端，
                                         #   本模式不再启动嵌入式后端，避免双后端写同一 SQLite）

设计文档: docs/plans/2026-11-16-desktop-app-design.md
"""
import os
import sys
import time
import socket
import threading
import logging
from pathlib import Path

# 窗口化 exe（console=False）双击启动时 sys.stdout/stderr 为 None：
# uvicorn 的 ColourizedFormatter（自动颜色检测）、colorama 等库会调用
# sys.stdout.isatty() 直接 AttributeError。必须在任何库初始化日志之前兜底。
# （bash/终端带句柄启动时二者非 None，不受影响）
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# 必须在所有其他导入之前初始化桌面配置（含 .env 加载与 CWD 确定化）
sys.path.insert(0, str(Path(__file__).parent))
from desktop_config import init_desktop_config  # noqa: E402

init_desktop_config()

import uvicorn  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

logger = logging.getLogger(__name__)

# 全局 uvicorn server 引用，用于优雅关闭
_uvicorn_server = None


def find_available_port(start_port: int = 19093, max_attempts: int = 20) -> int:
    """寻找可用端口，从 start_port 开始递增尝试（默认避让 web 版后端 19092）。"""
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


def _remove_root_json_route(app: FastAPI) -> None:
    """尽力移除 app/main.py 的 JSON 根路由（endpoint 函数名 read_root）。

    找不到仅记 warning —— 队首插入的 SPA 根路由（setup_spa_routes）无论如何都会
    接管 /，因此移除失败不影响桌面版正确性。
    """
    routes = app.router.routes

    for route in list(routes):
        if (
            isinstance(route, APIRoute)
            and route.path == "/"
            and getattr(route.endpoint, "__name__", "") == "read_root"
        ):
            routes.remove(route)
            logger.info("已移除 JSON 根路由 read_root（桌面模式由 SPA 接管 /）")
            return
    logger.warning("未找到 read_root 路由，跳过移除（队首 SPA 根路由仍会接管 /）")


def _serve_index(dist_path: Path) -> FileResponse:
    """SPA 入口：统一返回 dist/index.html。"""
    return FileResponse(dist_path / "index.html")


def setup_spa_routes(app: FastAPI, dist_path: str) -> bool:
    """桌面模式专用：把前端 SPA 静态服务装配到既有 FastAPI 应用上。

    装配逻辑（设计文档 §4.1）：
    1. 队首插入 GET / -> index.html（确定性接管根路径，无副作用：/ 上无 API 路由）
    2. catch-all GET（正常注册在所有 API 路由之后，天然最后匹配）：
       - api/ 或 mcp 开头 -> JSON 404（未知 API 显式失败，禁止 SPA 兜底掩盖）
       - dist 内存在对应文件 -> FileResponse 直出
       - 最后一段带扩展名但文件不存在 -> JSON 404（避免 HTML 被按 JS/CSS MIME 解析报错）
       - 其余 -> index.html（SPA fallback，覆盖深链接刷新）
    3. WebSocket 路由为 WebSocketRoute，与 HTTP GET catch-all 分属不同 scope，互不影响

    接受任意 FastAPI 实例，便于用最小 app 单测。返回 dist 是否可用。
    """
    dist = Path(dist_path).resolve()
    index_file = dist / "index.html"
    if not index_file.exists():
        logger.warning(f"前端 dist 不完整（缺 index.html）: {dist}，将仅启动 API 服务")
        return False

    # 1) 尽力移除 JSON 根路由 + 队首插入 SPA 根路由（双保险）
    _remove_root_json_route(app)

    def _spa_index_endpoint() -> FileResponse:
        return FileResponse(index_file)

    app.router.routes.insert(0, APIRoute("/", _spa_index_endpoint, methods=["GET"], include_in_schema=False))

    # 2) catch-all SPA fallback
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, full_path: str):  # noqa: ANN202
        # 未知 API 显式 404
        if full_path == "api" or full_path.startswith("api/") or full_path.startswith("mcp"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        candidate = (dist / full_path).resolve()
        # 防路径穿越：解析后必须仍在 dist 内
        if candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)

        # 带扩展名的资源请求缺失（如过期 hashed chunk）显式 404
        last_segment = full_path.rsplit("/", 1)[-1]
        if "." in last_segment:
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        # 其余路径回退 index.html（BrowserRouter 深链接）
        return _serve_index(dist)

    logger.info(f"SPA 静态服务已装配: {dist}")
    return True


def create_desktop_app() -> FastAPI:
    """创建桌面专用的 FastAPI 应用：完整后端 + 前端静态服务。"""
    from app.main import app as main_app

    setup_spa_routes(main_app, get_frontend_dist_path())
    return main_app


def run_uvicorn(app: FastAPI, port: int, shutdown_event: threading.Event) -> None:
    """在后台线程中运行 uvicorn，shutdown_event 置位后优雅退出。"""
    global _uvicorn_server

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
        use_colors=False,  # 窗口化 exe 无终端，禁用颜色避免 isatty 检测
    )
    server = uvicorn.Server(config)
    _uvicorn_server = server

    # 监听退出信号：事件置位 -> 通知 uvicorn 优雅关闭
    def _watch_shutdown() -> None:
        shutdown_event.wait()
        server.should_exit = True

    watchdog = threading.Thread(target=_watch_shutdown, daemon=True)
    watchdog.start()

    try:
        server.run()
    except BaseException:
        # 线程异常不经过主线程的 try（threading.excepthook 在窗口化 exe 里
        # 只弹对话框不留痕迹）——落盘后通知主线程退出
        import traceback as _tb
        crash_path = _get_crash_log_path()
        crash_path.write_text(_tb.format_exc(), encoding="utf-8")
        shutdown_event.set()
        raise


def wait_for_server(url: str, timeout: float = 120.0) -> bool:
    """轮询等待服务器就绪（lifespan 启动任务较重，与 dev-services 对齐用 120s）。"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def _install_thread_crash_hook() -> None:
    """任意后台线程的未处理异常落盘（窗口化 exe 里只弹对话框不留痕迹）。"""
    import traceback as _tb

    def _hook(args: "threading.ExceptHookArgs") -> None:  # noqa: UP037
        crash_path = _get_crash_log_path()
        detail = "".join(_tb.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        with open(crash_path, "a", encoding="utf-8") as f:
            f.write(f"--- 线程 {args.thread} 未处理异常 ---\n{detail}\n")

    threading.excepthook = _hook


def main() -> None:
    """桌面应用主入口。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    _install_thread_crash_hook()

    is_dev = os.environ.get("DESKTOP_DEV") == "1"

    # 开发模式：窗口直连 Vite（后端用 dev-services 的 19092，本进程不启动嵌入式后端）
    if is_dev:
        vite_url = os.environ.get("VITE_DEV_URL", "http://localhost:5178")
        logger.info(f"开发模式: 窗口直连 Vite 热重载服务器 {vite_url}（嵌入式后端不启动）")
        server_url = vite_url
    else:
        # 生产模式：嵌入式后端 + 同源前端
        try:
            port = find_available_port()
        except RuntimeError as e:
            logging.error(str(e))
            sys.exit(1)

        logger.info(f"使用端口: {port}")
        app = create_desktop_app()

        shutdown_event = threading.Event()
        uvicorn_thread = threading.Thread(
            target=run_uvicorn,
            args=(app, port, shutdown_event),
            daemon=True,
        )
        uvicorn_thread.start()

        health_url = f"http://127.0.0.1:{port}/api/v1/health"
        if not wait_for_server(health_url):
            logger.error(f"服务器启动超时（{health_url}）")
            shutdown_event.set()
            sys.exit(1)

        logger.info(f"FastAPI 已就绪: http://127.0.0.1:{port}")
        server_url = f"http://127.0.0.1:{port}"

    # 启动 pywebview 窗口
    try:
        import webview

        webview.create_window(
            title="工具箱",
            url=server_url,
            width=1280,
            height=800,
            min_size=(800, 600),
            resizable=True,
        )
        webview.start(debug=is_dev)

    except ImportError:
        logger.error("pywebview 未安装，请运行: pip install -r requirements-desktop.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"pywebview 启动失败: {e}")
        sys.exit(1)

    # 窗口关闭后优雅退出
    logger.info("窗口已关闭，正在退出...")
    if not is_dev:
        shutdown_event.set()
        if _uvicorn_server is not None:
            uvicorn_thread.join(timeout=5)
            if uvicorn_thread.is_alive():
                logger.warning("uvicorn 未在 5s 内退出，强制退出")
                _uvicorn_server.force_exit = True

    logger.info("桌面应用已退出")


def _get_crash_log_path() -> Path:
    """获取崩溃日志路径：frozen=exe 同级 logs/，dev=backend/logs/。"""
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "crash.log"


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        # 窗口化 exe（console=False）没有 stdout/stderr，未处理异常只弹一个
        # "Unhandled exception in script" 对话框，根因无处可查——必须落盘
        import traceback as _tb
        crash_path = _get_crash_log_path()
        crash_path.write_text(_tb.format_exc(), encoding="utf-8")
        raise
