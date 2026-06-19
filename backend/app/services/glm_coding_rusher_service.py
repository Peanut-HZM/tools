"""GLM-Coding Pro 抢购核心服务"""

import logging
from enum import Enum
from pathlib import Path
from typing import List
from datetime import datetime, time, timedelta

logger = logging.getLogger(__name__)

# 项目根目录（backend/）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = _BACKEND_ROOT / "data" / "glm_coding_rusher"
TARGET_URL = "https://open.bigmodel.cn/glm-coding"


def get_state_path() -> Path:
    """返回登录态 state 文件路径"""
    return STATE_DIR / "state.json"


def state_file_exists() -> bool:
    """检查 state 文件是否存在"""
    return get_state_path().exists()


class ButtonState(str, Enum):
    """按钮状态"""
    SOLD_OUT = "sold_out"       # 售罄/未开放
    AVAILABLE = "available"     # 可点击购买
    UNKNOWN = "unknown"         # 无法识别


# 可点击购买状态的关键词
AVAILABLE_KEYWORDS: List[str] = [
    "立即购买",
    "立即开通",
    "特惠订阅",
    "立即抢购",
]


def parse_button_state(text: str, disabled: bool) -> ButtonState:
    """
    根据按钮文字和 disabled 属性判断按钮状态

    Args:
        text: 按钮文字
        disabled: 是否禁用

    Returns:
        ButtonState 枚举值
    """
    text = (text or "").strip()
    if not text:
        return ButtonState.UNKNOWN

    # disabled 状态一律视为不可点击
    if disabled:
        # 即使是售罄类文字，disabled 也是 SOLD_OUT
        if any(kw in text for kw in ["售罄", "补货", "抢完"]):
            return ButtonState.SOLD_OUT
        return ButtonState.SOLD_OUT

    # 非 disabled：检查是否为可购买关键词
    for kw in AVAILABLE_KEYWORDS:
        if kw in text:
            return ButtonState.AVAILABLE

    # 包含售罄/补货关键词但非 disabled（页面改版或特殊情况）
    if any(kw in text for kw in ["售罄", "补货", "抢完"]):
        return ButtonState.SOLD_OUT

    return ButtonState.UNKNOWN


def next_sale_time(sale_time_str: str, now: datetime = None) -> datetime:
    """
    计算下一次开抢时间

    Args:
        sale_time_str: 格式 "HH:MM"，例如 "10:00"
        now: 当前时间（用于测试），默认为 datetime.now()

    Returns:
        下一次开抢的 datetime
    """
    if now is None:
        now = datetime.now()

    h, m = map(int, sale_time_str.split(":"))
    today_sale = now.replace(hour=h, minute=m, second=0, microsecond=0)

    if now < today_sale:
        return today_sale
    return today_sale + timedelta(days=1)


def format_countdown(seconds: int) -> str:
    """
    将秒数格式化为 HH:MM:SS

    Args:
        seconds: 剩余秒数

    Returns:
        格式化后的倒计时字符串
    """
    if seconds <= 0:
        return "00:00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class ConfigError(Exception):
    """配置校验错误"""
    pass


def validate_config(config: dict) -> None:
    """
    校验抢购配置

    Args:
        config: 配置字典

    Raises:
        ConfigError: 配置不合法
    """
    # sale_time 校验
    sale_time = config.get("sale_time", "")
    if not sale_time:
        raise ConfigError("sale_time 不能为空")
    try:
        h, m = map(int, sale_time.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError()
    except (ValueError, TypeError):
        raise ConfigError("sale_time 格式必须为 HH:MM，例如 10:00")

    # preheat_seconds 校验
    preheat = config.get("preheat_seconds", 0)
    if preheat < 30:
        raise ConfigError("preheat_seconds 不能小于 30 秒")

    # refresh_interval_ms 校验
    interval = config.get("refresh_interval_ms", 0)
    if interval < 200:
        raise ConfigError("refresh_interval_ms 不能小于 200ms，避免风控")

    # timeout_seconds 校验
    timeout = config.get("timeout_seconds", 0)
    if timeout < 10:
        raise ConfigError("timeout_seconds 不能小于 10 秒")
    if timeout > 600:
        raise ConfigError("timeout_seconds 不能大于 600 秒（10 分钟）")


# 登录态检测关键字
LOGIN_INDICATORS = ["登录", "注册", "微信一键登录", "请输入账号"]


def _check_login_state(page) -> bool:
    """
    检查页面是否处于登录状态

    Returns:
        True 表示已登录，False 表示未登录
    """
    try:
        body_text = page.text_content("body") or ""
        for indicator in LOGIN_INDICATORS:
            if indicator in body_text:
                return False
        return True
    except Exception as e:
        logger.warning(f"检查登录状态异常: {e}")
        return False


def open_login_window(headless: bool = False) -> dict:
    """
    打开浏览器让用户手动登录，登录成功后保存 state

    Returns:
        {"success": bool, "message": str}
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()

            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

            # 等待用户登录（最多 5 分钟）
            logger.info("等待用户登录，最多 5 分钟...")
            for _ in range(300):  # 每秒检测一次，共 300 次
                page.wait_for_timeout(1000)
                if _check_login_state(page):
                    # 登录成功，保存 state
                    STATE_DIR.mkdir(parents=True, exist_ok=True)
                    context.storage_state(path=str(get_state_path()))
                    logger.info("登录成功，state 已保存")
                    browser.close()
                    return {"success": True, "message": "登录成功，已保存登录态"}

            browser.close()
            return {"success": False, "message": "登录超时（5 分钟），请重试"}
    except Exception as e:
        logger.error(f"登录流程异常: {e}")
        return {"success": False, "message": f"登录失败: {str(e)}"}


def check_login_valid() -> dict:
    """
    检查现有登录态是否有效

    Returns:
        {"valid": bool, "message": str}
    """
    if not state_file_exists():
        return {"valid": False, "message": "未登录，请先完成登录"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(get_state_path()))
            page = context.new_page()
            page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)

            is_logged_in = _check_login_state(page)
            browser.close()

            if is_logged_in:
                return {"valid": True, "message": "登录态有效"}
            return {"valid": False, "message": "登录态已失效，请重新登录"}
    except Exception as e:
        logger.error(f"校验登录态失败: {e}")
        return {"valid": False, "message": f"校验失败: {str(e)}"}
