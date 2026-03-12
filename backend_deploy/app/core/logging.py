"""
日志配置模块
提供统一的日志记录器配置，支持模块级别日志控制
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

from app.config.config import settings

# 日志目录配置
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# 产品经理 Agent 专用日志目录
PM_AGENT_LOGS_DIR = LOGS_DIR / "pm_agent"
PM_AGENT_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 确保主日志目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_log_format() -> str:
    """
    获取日志格式字符串

    格式: 时间 - 模块名 - 级别 - 消息
    包含请求ID（如果可用）
    """
    return "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"


def get_detailed_log_format() -> str:
    """
    获取详细日志格式

    包含文件名和行号，便于调试
    """
    return "%(asctime)s - %(name)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s"


def create_file_handler(
    log_file: str,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: int = logging.INFO,
) -> RotatingFileHandler:
    """
    创建文件日志处理器

    Args:
        log_file: 日志文件名
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        level: 日志级别

    Returns:
        配置好的文件处理器
    """
    handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(get_log_format()))
    return handler


def create_console_handler(level: int = logging.INFO) -> logging.StreamHandler:
    """
    创建控制台日志处理器

    Args:
        level: 日志级别

    Returns:
        配置好的控制台处理器
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(get_log_format()))
    return handler


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    add_console: bool = True,
) -> logging.Logger:
    """
    设置并返回指定名称的日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件名（可选，如果不提供则使用默认日志文件）
        level: 日志级别
        add_console: 是否添加控制台输出

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 添加文件处理器
    if log_file:
        file_handler = create_file_handler(str(LOGS_DIR / log_file))
        logger.addHandler(file_handler)
    else:
        # 使用默认应用日志文件
        default_handler = create_file_handler(str(LOGS_DIR / "app.log"))
        logger.addHandler(default_handler)

    # 添加控制台处理器
    if add_console:
        console_handler = create_console_handler(level)
        logger.addHandler(console_handler)

    return logger


def get_pm_agent_logger(name: str) -> logging.Logger:
    """
    获取产品经理 Agent 专用的日志记录器

    为产品经理 Agent 功能创建独立的日志文件，便于问题排查

    Args:
        name: 模块名称（通常使用 __name__）

    Returns:
        配置好的日志记录器
    """
    # 创建专用的日志文件名
    log_filename = f"pm_agent_{name.replace('.', '_')}.log"
    return setup_logger(
        name=f"pm_agent.{name}",
        log_file=str(PM_AGENT_LOGS_DIR / log_filename),
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )


def get_service_logger(name: str) -> logging.Logger:
    """
    获取服务层通用的日志记录器

    Args:
        name: 模块名称

    Returns:
        配置好的日志记录器
    """
    return setup_logger(name, level=logging.DEBUG if settings.DEBUG else logging.INFO)


def get_api_logger(name: str) -> logging.Logger:
    """
    获取 API 层专用的日志记录器

    包含请求/响应日志

    Args:
        name: API 模块名称

    Returns:
        配置好的日志记录器
    """
    return setup_logger(
        name=f"api.{name}",
        log_file="api.log",
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )


# 预配置的常用日志记录器
# 可以直接导入使用，无需重复配置

# 核心模块日志
core_logger = setup_logger("app.core", "core.log")
security_logger = setup_logger("app.core.security", "security.log")
rate_limiter_logger = setup_logger("app.core.rate_limiter", "rate_limiter.log")

# 服务层日志
service_logger = setup_logger("app.services", "services.log")
llm_logger = setup_logger("app.services.llm", "llm.log")
conversation_logger = setup_logger("app.services.conversation", "conversation.log")
prd_logger = setup_logger("app.services.prd", "prd.log")

# API日志
api_logger = setup_logger("app.api", "api.log")
routes_logger = setup_logger("app.routes", "routes.log")

# 第三方服务日志
external_logger = setup_logger("app.external", "external.log")


class RequestIdFilter(logging.Filter):
    """
    日志过滤器：自动添加请求ID到日志记录

    如果在 logging.MDC 中设置了 request_id，则自动添加到每条日志中
    """

    def filter(self, record):
        # 尝试获取请求ID（如果使用了 MDC 或类似机制）
        if hasattr(record, "request_id"):
            pass  # 已有request_id属性
        else:
            record.request_id = "-"
        return True


class ContextLogger:
    """
    上下文日志记录器

    支持在日志中添加上下文信息（如请求ID、用户ID等）
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.context = {}

    def set_context(self, **kwargs):
        """设置日志上下文"""
        self.context.update(kwargs)

    def clear_context(self):
        """清除日志上下文"""
        self.context = {}

    def _format_message(self, message: str) -> str:
        """格式化消息，添加上下文信息"""
        if self.context:
            context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
            return f"[{context_str}] {message}"
        return message

    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(self._format_message(message), *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self.logger.info(self._format_message(message), *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(self._format_message(message), *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self.logger.error(self._format_message(message), *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self.logger.critical(self._format_message(message), *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        self.logger.exception(self._format_message(message), *args, **kwargs)


def get_context_logger(name: str) -> ContextLogger:
    """
    获取带上下文的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        上下文日志记录器实例
    """
    logger = logging.getLogger(name)
    return ContextLogger(logger)
