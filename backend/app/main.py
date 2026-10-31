import asyncio
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg2
from sqlalchemy.exc import DataError

from app.api.routes import conversations, health, llm_config, messages, prd
from app.config.config import settings
from app.models.base import Base, engine
from app.routes import (
    admin,
    asr_routes,
    auth,
    calendar,
    contact_message,
    converter,
    course_platform,
    course_platform_admin,
    cross_share,
    database_tool,
    deploy,
    http_client,
    image_downloader,
    json_tool,
    k8s_tool,
    key_generator,
    markdown_editor,
    ocr_routes,
    oss,
    redis_tool,
    resource_management,
    ssh_tool,
    tech_contents,
    token_usage,
    tools,
    video_downloader,
    ytdlp_routes,
)
from app.routes import monitor as monitor_router
from app.services.download_manager import get_manager
from app.services.token_usage_background_sync import (
    start_background_sync_task,
    stop_background_sync_task,
)

# 配置日志目录为项目根目录下的 logs 文件夹
PROJECT_ROOT = Path(__file__).parent.parent  # backend/app/main.py -> backend
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志格式
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(log_format)

# 配置文件处理器（按大小轮转，保留5个备份，每个最大10MB）
file_handler = RotatingFileHandler(
    LOGS_DIR / "app.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)

# 配置控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO, handlers=[file_handler, console_handler], format=log_format
)

# 配置 uvicorn 日志，确保启动错误也写入文件
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.addHandler(file_handler)
uvicorn_logger.setLevel(logging.INFO)

uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.addHandler(file_handler)
uvicorn_error_logger.setLevel(logging.INFO)

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addHandler(file_handler)
uvicorn_access_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# JWT Configuration (from settings)
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting application...")

    # 自动创建数据库表（Token Usage 相关模型）
    try:
        from app.models.token_usage_models import (  # noqa: F401
            TokenUsageRecord,
            TokenUsageSyncLog,
        )
        Base.metadata.create_all(bind=engine)
        logger.info("Token Usage 数据库表创建成功")
    except Exception as e:
        logger.warning(f"Token Usage 数据库表创建失败: {e}")

    # 初始化监控模块（建表 + 启动采集引擎）
    monitor_cleanup_task = None
    try:
        from app.services.monitor import alert_engine, metric_repo
        from app.services.monitor.collector import monitor_collector
        from app.services.monitor.server_service import MonitorServerService
        MonitorServerService.ensure_tables()
        metric_repo.ensure_tables()
        alert_engine.ensure_tables()

        async def monitor_cleanup_loop():
            """每 6 小时清理过期监控指标"""
            from app.services.monitor.metric_repo import delete_expired_metrics
            while True:
                await asyncio.sleep(6 * 3600)
                try:
                    delete_expired_metrics(7 * 24 * 3600)
                except Exception as e:
                    logger.warning(f"监控指标清理失败: {e}")
        monitor_cleanup_task = asyncio.create_task(monitor_cleanup_loop())

        await monitor_collector.start()
        logger.info("监控模块初始化完成")
    except Exception as e:
        logger.error(f"监控模块初始化失败: {e}")

    # 启动后台清理任务
    manager = get_manager()
    cleanup_task = asyncio.create_task(manager.start_cleanup_task())

    # 狼人杀房间心跳循环（超时托管/闲置回收）
    try:
        from app.routes.werewolf import manager as werewolf_manager
        werewolf_manager.start()
        from app.routes.sanguo import manager as sanguo_manager
        sanguo_manager.start()
        logger.info("狼人杀/三国杀房间心跳循环已启动")
    except Exception as e:
        logger.warning(f"狼人杀房间心跳循环启动失败: {e}")

    # 启动数据库工具连接池空闲清理任务（每 5 分钟清理 15 分钟未使用的引擎）
    try:
        from app.utils.db_connection_manager import DBConnectionManager

        async def db_pool_cleanup_loop():
            while True:
                await asyncio.sleep(300)
                try:
                    cleaned = DBConnectionManager.cleanup_idle_engines(idle_timeout=900)
                    if cleaned:
                        logger.info(f"数据库连接池空闲清理: 已清理 {cleaned} 个引擎")
                except Exception as e:
                    logger.warning(f"数据库连接池清理失败: {e}")

        db_pool_cleanup_task = asyncio.create_task(db_pool_cleanup_loop())
    except Exception as e:
        logger.warning(f"数据库连接池清理任务启动失败: {e}")
        db_pool_cleanup_task = None

    # 启动 OpenClaw 连接
    try:
        from app.services.openclaw_service import openclaw_service

        await openclaw_service.start()
    except Exception as e:
        logger.warning(f"OpenClaw 连接启动失败（功能将不可用）: {e}")

    # 启动 Token Usage 后台定时同步任务，不阻塞首屏查询
    start_background_sync_task()

    # 密钥安全校验
    try:
        _check_security_settings()
    except Exception as e:
        logger.warning(f"安全校验未通过: {e}")

    # 预初始化 SQLAlchemy 引擎连接池（按需懒加载，首次 checkout 时创建物理连接）
    try:
        from app.models.base import engine
        logger.info(f"SQLAlchemy engine 已就绪 (pool_size={engine.pool.size()}, pool_class={type(engine.pool).__name__})")
    except Exception as e:
        logger.warning(f"SQLAlchemy engine 初始化失败: {e}")

    # Harness 初始化（Phase 1: 验证内置工具可注册）
    try:
        from app.services.harness.tool_registry import ToolRegistry  # noqa: F401
        from app.services.harness.tools.db_query import DbQueryTool  # noqa: F401
        from app.services.harness.tools.web_search import WebSearchTool  # noqa: F401

        # 延迟初始化（需要请求级 DB session）
        # Phase 1: 只验证模块可导入，不创建实例
        logger.info("Harness ToolRegistry 模块已就绪（按需初始化）")
    except Exception as e:
        logger.warning(f"Harness 模块初始化失败: {e}")

    # ImageGenTool 模块可用性（运行时按需注册到 ToolRegistry）
    try:
        from app.services.harness.tools.image_gen import ImageGenTool  # noqa: F401

        logger.info("Harness ImageGenTool 模块已就绪（按需注册）")
    except Exception as e:
        logger.warning("ImageGenTool 模块加载失败: %s", type(e).__name__)

    # 启动时同步 MCP server（Phase 3-Plan-1A Task 5）
    try:
        await sync_mcp_servers()
    except Exception as e:
        logger.warning(f"MCP server 启动同步失败（功能将不可用）: {e}")

    # 加载本地插件工具（Phase 3 P2-①b 文件插件系统）
    try:
        await _scan_plugins()
    except Exception as e:
        logger.warning(f"Plugin 加载失败（功能将不可用）: {e}")

    # 记忆向量回填（Phase 3 Plan-1B / Task 6）：best-effort，非阻塞启动
    try:
        from app.models.base import SessionLocal
        from app.services.harness.memory_backfill import (
            count_pending_rows,
        )

        _backfill_db = SessionLocal()
        try:
            pending = count_pending_rows(_backfill_db)
            if pending > 0:
                logger.info(f"发现 {pending} 条记忆待回填 embedding，启动后台回填任务")
                # asyncio.create_task 使回填在后台异步运行，不阻塞 lifespan
                asyncio.create_task(_run_memory_backfill(_backfill_db))
        finally:
            # Session 由后台任务使用，此处不立即关闭
            pass
    except Exception as e:
        logger.warning(f"记忆回填启动检查失败（功能将不可用）: {e}")

    # LLM API Key 密钥自检：提前暴露「密文与主密钥不匹配」类配置问题
    try:
        from app.services.llm_provider_service import check_provider_keys_health
        check_provider_keys_health()
    except Exception as e:
        logger.warning(f"[密钥自检] 执行异常（不影响启动）: {e}")

    # 打印启动完成信号（dev-services.py 检测此关键字）
    logger.info("Application startup complete")

    # OpenTelemetry 初始化（Phase 3 Plan 1C Task 7）
    from app.services.harness.otel_init import init_otel
    otel_ok = init_otel()
    logger.info("OpenTelemetry export: %s", "enabled" if otel_ok else "disabled")

    # 启动 Token 用量定时同步调度器
    from app.services.token_usage_scheduler import init_scheduler, shutdown_scheduler
    init_scheduler()

    # MCP streamable HTTP 会话管理器随主应用生命周期启停。
    # StreamableHTTPSessionManager.run() 全进程只允许一次且 stop 不复位标记：
    # 生产 uvicorn 单次 lifespan 无影响；测试进程多个 with TestClient(app)
    # 会反复进出 lifespan，二次启动抛 RuntimeError 时跳过（复用已停实例，不阻塞用例）
    from app.mcp_server.k8s_server import get_mcp_starlette_app
    _mcp_app = get_mcp_starlette_app()
    try:
        async with _mcp_app.router.lifespan_context(_mcp_app):
            yield
    except RuntimeError as e:
        if "only be called once" in str(e):
            logger.warning("MCP session_manager 重复启动（测试重复 lifespan），跳过")
            yield
        else:
            raise

    # 关闭 Token 用量定时同步调度器
    try:
        shutdown_scheduler()
    except Exception as e:
        logger.warning(f"token usage scheduler 关闭失败: {e}")

    # OpenTelemetry shutdown（Phase 3 Plan 1C Task 7）
    from app.services.harness.otel_init import shutdown_otel
    shutdown_otel()

    # 关闭时
    logger.info("Shutting down application...")
    logger.info("Harness ToolRegistry 已清理（按需实例随 session 释放）")

    try:
        from app.services.openclaw_service import openclaw_service

        await openclaw_service.stop()
    except Exception as e:
        logger.error(f"OpenClaw 关闭异常: {e}")

    # 停止监控采集引擎
    try:
        from app.services.monitor.collector import monitor_collector
        await monitor_collector.stop()
    except Exception as e:
        logger.warning(f"监控采集引擎停止异常: {e}")

    # 停止监控指标清理任务（初始化失败时为 None，跳过取消）
    try:
        from app.routes.werewolf import manager as werewolf_manager
        werewolf_manager.shutdown()
        from app.routes.sanguo import manager as sanguo_manager
        sanguo_manager.shutdown()
    except Exception as e:
        logger.warning(f"狼人杀房间心跳循环停止失败: {e}")

    if monitor_cleanup_task is not None:
        monitor_cleanup_task.cancel()
        try:
            await monitor_cleanup_task
        except asyncio.CancelledError:
            pass

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await stop_background_sync_task()
    if 'db_pool_cleanup_task' in locals() and db_pool_cleanup_task is not None:
        db_pool_cleanup_task.cancel()
        try:
            await db_pool_cleanup_task
        except asyncio.CancelledError:
            pass
    try:
        from app.config.database import close_connection_pool

        close_connection_pool()
        engine.dispose()
        logger.info("数据库连接资源已释放")
    except Exception as e:
        logger.warning(f"数据库连接资源释放失败: {e}")


async def _run_memory_backfill(db):
    """后台回填任务包装：运行回填并最终关闭 Session"""
    from app.services.harness.memory_backfill import run_startup_backfill
    try:
        await run_startup_backfill(db)
    except Exception as e:
        logger.error("记忆回填任务失败: %s", type(e).__name__)
    finally:
        try:
            db.close()
        except Exception:
            pass


def _check_security_settings():
    """检查安全密钥配置是否合规"""
    from app.config.asr_config import asr_settings
    from app.config.config import settings
    from app.config.ocr_config import ocr_settings

    # 已知的硬编码默认值（需要替换）
    DEFAULT_KEYS = [
        "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4=",
    ]

    # 开发环境安全默认值
    DEV_DEFAULTS = [
        "dev-jwt-secret-change-me",
    ]

    if settings.JWT_SECRET_KEY in DEFAULT_KEYS or settings.JWT_SECRET_KEY in DEV_DEFAULTS:
        logger.warning("JWT_SECRET_KEY 使用了默认硬编码值，生产环境请务必更换！运行: python scripts/generate_keys.py")

    if len(settings.JWT_SECRET_KEY) < 32:
        logger.warning("JWT_SECRET_KEY 长度不足 32 字符，建议更换为更长的随机密钥")

    # 注：DB_ENCRYPTION_KEY 已废弃（LLM API Key 主密钥改为存放在 app_secrets 表，
    # 随数据库走、多环境天然一致），不再需要对其做默认值/长度检查。

    # 生产环境额外检查
    if settings.ENV == "prod":
        if not settings.ALIYUN_OSS_ACCESS_KEY_ID and settings.STORAGE_PROVIDER == "aliyun_oss":
            logger.error("生产环境使用 aliyun_oss 时 ALIYUN_OSS_ACCESS_KEY_ID 不能为空")

        if not settings.MINIO_ACCESS_KEY and settings.STORAGE_PROVIDER == "minio":
            logger.error("生产环境使用 minio 时 MINIO_ACCESS_KEY 不能为空")

        if not ocr_settings.API_KEY:
            logger.error("生产环境 OCR_API_KEY 不能为空")

        if not asr_settings.API_KEY:
            logger.error("生产环境 ASR_API_KEY 不能为空")


async def sync_mcp_servers():
    """启动时同步所有活跃的 MCP server。

    遍历所有 ``is_active=True`` 的 ``McpServer``，通过 ``McpServerManager.sync_server()``
    拉取工具列表并注册到全局 ``ToolRegistry``。
    单个 server 失败仅记录日志，不阻塞其他 server 与应用启动。
    """
    from app.models.base import SessionLocal
    from app.models.mcp_server import McpServer
    from app.services.harness.mcp_server_manager import get_mcp_server_manager

    db = SessionLocal()
    try:
        manager = get_mcp_server_manager()
        servers = db.query(McpServer).filter(McpServer.is_active == True).all()
        logger.info(f"启动时发现 {len(servers)} 个活跃 MCP server，开始同步")
        for server in servers:
            try:
                result = await manager.sync_server(server)
                if result["success"]:
                    logger.info(
                        f"[Startup MCP Sync] {server.name}: 已同步 "
                        f"{result['tools_count']} 个工具"
                    )
                else:
                    logger.warning(
                        f"[Startup MCP Sync] {server.name} 同步失败: "
                        f"{result.get('error')}"
                    )
            except Exception as e:
                logger.exception(
                    f"[Startup MCP Sync] {server.name} 同步异常: {e}"
                )
    finally:
        db.close()


async def _scan_plugins() -> None:
    """启动时扫描 backend/plugins/ 目录加载所有 plugin tool。

    PluginLoader.scan() 内部对单文件失败做隔离；这里再加一层 try/except
    防止目录权限等极端异常阻断 lifespan。
    """
    from app.services.harness.plugin_loader import PluginLoader
    from app.services.harness.tool_registry import get_tool_registry

    plugins_dir = PROJECT_ROOT / "plugins"
    PluginLoader(get_tool_registry()).scan(plugins_dir)


app = FastAPI(title="Tool Aggregation API", lifespan=lifespan)


# ---------------------------------------------------------------------------
# 全局异常处理：ID 格式非法导致的数据库类型转换错误
# ---------------------------------------------------------------------------
# 路径/查询参数里的 ID 若不是合法 UUID，透传到 UUID 列时 PostgreSQL 会抛
# InvalidTextRepresentation，默认响应是 500（服务端错误），语义上并不准确 ——
# 这类请求属于「资源不存在 / ID 格式非法」，应返回 404。
#
# 注意：SQLAlchemy ORM 会把 psycopg2 异常包装成 sqlalchemy.exc.DataError
# （其 .orig 才是原始 psycopg2 异常），所以两种入口都要处理；
# 且 DataError 还涵盖数值溢出、长度超限等其他错误，只有 .orig 命中
# InvalidTextRepresentation 时才转 404，其余保持原有 500 行为不变。
@app.exception_handler(psycopg2.errors.InvalidTextRepresentation)
async def invalid_text_representation_handler(
    request: Request, exc: psycopg2.errors.InvalidTextRepresentation
):
    logger.warning(
        "请求参数 ID 格式非法（按资源不存在处理）: path=%s err=%s",
        request.url.path,
        str(exc).splitlines()[0] if str(exc) else "",
    )
    return JSONResponse(
        status_code=404,
        content={"detail": "资源不存在或 ID 格式非法"},
    )


@app.exception_handler(DataError)
async def db_data_error_handler(request: Request, exc: DataError):
    """SQLAlchemy 数据类异常：仅 ID 格式非法转 404，其余原样抛出保持 500"""
    orig = getattr(exc, "orig", None)
    if isinstance(orig, psycopg2.errors.InvalidTextRepresentation):
        logger.warning(
            "请求参数 ID 格式非法（按资源不存在处理）: path=%s err=%s",
            request.url.path,
            str(orig).splitlines()[0] if str(orig) else "",
        )
        return JSONResponse(
            status_code=404,
            content={"detail": "资源不存在或 ID 格式非法"},
        )
    # 其它数据类错误（数值溢出、长度超限等）不属于 ID 格式问题，保持原行为
    raise exc

# Configure CORS - Updated to support Authorization header
cors_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["*"],
)

# Include routers
app.include_router(tools.router, prefix="/api")
app.include_router(image_downloader.router, prefix="/api")
app.include_router(video_downloader.router, prefix="/api")
app.include_router(ytdlp_routes.router, prefix="/api")
app.include_router(calendar.router)
app.include_router(key_generator.router)

# Authentication router
app.include_router(auth.router)

# Markdown Editor router
app.include_router(markdown_editor.router)

# Document Converter router
app.include_router(converter.router)

# OSS router
app.include_router(oss.router)

# Admin router
app.include_router(admin.router)

# Admin LLM quota router (LLM 用户配额管理)
from app.routes import admin_llm_quota

app.include_router(admin_llm_quota.router)

# User LLM quota router (用户查看自身配额)
from app.routes import user_quota

app.include_router(user_quota.router)

# Deploy info router
app.include_router(deploy.router, prefix="/api")

# OCR & ASR routers
app.include_router(ocr_routes.router, prefix="/api")
app.include_router(asr_routes.router, prefix="/api")

# Database Tool router
app.include_router(database_tool.router, prefix="/api")

# Redis Tool router
app.include_router(redis_tool.router, prefix="/api")

# SSH Tool router
app.include_router(ssh_tool.router, prefix="/api")

# K8s Tool router
app.include_router(k8s_tool.router, prefix="/api")

# Storage router（存储状态 + 配置迁移，router 自带 /api/storage 前缀）
from app.routes import storage as storage_router

app.include_router(storage_router.router)

# User API Token router（个人 PAT，供 MCP endpoint 认证）
from app.routes import user_api_token
app.include_router(user_api_token.router, prefix="/api")

# K8s 排障 MCP Server（只读，PAT 认证）—— streamable Starlette 全进程单例
# mount("/mcp") + 内部路径 /k8s 拼出端点 /mcp/k8s（避免精确路径 307 重定向）
from app.mcp_server.auth import PATAuthASGIMiddleware
from app.mcp_server.k8s_server import get_mcp_starlette_app
app.mount("/mcp", PATAuthASGIMiddleware(get_mcp_starlette_app()))

# JSON Tool router
app.include_router(json_tool.router, prefix="/api")

# Token Usage router
app.include_router(token_usage.router, prefix="/api")

# Resource Management router
app.include_router(resource_management.router, prefix="/api")

# CrossShare router
app.include_router(cross_share.router)

# Course Platform router
app.include_router(course_platform.router)

# Course Platform Admin router
app.include_router(course_platform_admin.router)

# Tech Contents router
app.include_router(tech_contents.router)

# Product Manager Agent routers
app.include_router(llm_config.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(prd.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")

# Health check router
app.include_router(health.router, prefix="/api/v1")

# Chat stream router (SSE)
from app.api.routes import admin_conversations, chat_stream

app.include_router(chat_stream.router, prefix="/api/v1")

# Admin conversation management router
app.include_router(admin_conversations.router, prefix="/api/v1")

# 竞品分析 router
from app.api.routes import competitor

app.include_router(competitor.router, prefix="/api/v1")

# 视频生成工具 router
from app.api.routes import tools_video_generation

app.include_router(tools_video_generation.router, prefix="/api/v1")

# Harness admin/mcp/servers router (Phase 3-Plan-1A Task 4)
from app.api.routes import admin_mcp_servers

app.include_router(admin_mcp_servers.router)

# Harness admin/tools router (Task 13)
from app.api.routes import admin_tools

app.include_router(admin_tools.router)

# Harness admin/traces router (Task 15)
from app.api.routes import admin_traces

app.include_router(admin_traces.router)

# Agent management router
from app.api.routes import agents as agents_router

app.include_router(agents_router.router, prefix="/api/v1")

# LLM 供应商 / 模型管理 router（Task 1.5.4）
from app.api.routes import admin_llm_models, admin_llm_providers

app.include_router(admin_llm_providers.router, prefix="/api/v1")
app.include_router(admin_llm_models.router, prefix="/api/v1")

# Contact Message router
app.include_router(contact_message.router)

# Monitor router（服务器监控）
app.include_router(monitor_router.router, prefix="/api")

# OpenClaw router
from app.routes import openclaw as openclaw_router

# HTTP Client router
app.include_router(http_client.router, prefix="/api")

# OpenClaw router (SSE streaming)
app.include_router(openclaw_router.router, prefix="/api")

# OpenClaw WebSocket router (mini-program)
from app.routes import openclaw_ws as openclaw_ws_router
from app.routes import werewolf as werewolf_router
from app.routes import sanguo as sanguo_router

app.include_router(openclaw_ws_router.router, prefix="/api")
app.include_router(werewolf_router.router, prefix="/api")
app.include_router(sanguo_router.router)
# WS 路由直接挂载：经 include_router 注册的 websocket 路由在本 Starlette 版本
# 的 _IncludedRouter 分发下会被 1008 拒绝，故用纯 Starlette 路由挂载
from starlette.routing import WebSocketRoute as _WerewolfWSRoute

app.router.routes.append(_WerewolfWSRoute("/api/games/werewolf/rooms/{room_id}/ws",
                                          werewolf_router.room_ws))
app.router.routes.append(_WerewolfWSRoute("/api/games/sanguo/rooms/{room_id}/ws",
                                          sanguo_router.sanguo_room_ws))

# OpenClaw Admin router
from app.routes import openclaw_admin as openclaw_admin_router

app.include_router(openclaw_admin_router.router)

# Harness memories management router (Phase 3 Plan-1B / Task 6)
from app.api.routes.harness_memories import (
    router as harness_memories_router,
)
from app.api.routes.harness_skills import router as harness_skills_router
from app.api.routes.marketplace import router as marketplace_router
from app.api.routes.tools_image_generation import (
    router as tools_image_generation_router,
)

app.include_router(harness_memories_router)
app.include_router(harness_skills_router)
app.include_router(marketplace_router)
app.include_router(tools_image_generation_router)

# Harness traces query router (Phase 3 Plan 1C / Task 3)
from app.api.routes import harness_traces

app.include_router(harness_traces.router)

# Harness checkpoint 时间旅行 router (Phase 3 Plan 1D / Task 4)
from app.api.routes.harness_checkpoints import (
    router as harness_checkpoints_router,
)

app.include_router(harness_checkpoints_router)


@app.get("/")
def read_root():
    return {"message": "Tool Aggregation API"}
