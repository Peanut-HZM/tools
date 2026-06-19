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


# 登录态检测：检查页面是否包含未登录特征元素
# 如果页面包含这些元素，说明未登录；否则说明已登录
UNLOGIN_INDICATORS = [
    "登录 / 注册",  # 未登录时的按钮文字
    "请输入账号",   # 登录表单
    "扫码登录",     # 扫码登录提示
]


def _check_login_state(page) -> bool:
    """
    检查页面是否处于登录状态

    Returns:
        True 表示已登录，False 表示未登录
    """
    try:
        body_text = page.text_content("body") or ""
        # 如果页面包含未登录特征元素，说明未登录
        for indicator in UNLOGIN_INDICATORS:
            if indicator in body_text:
                return False
        # 检查是否有登录按钮（精确匹配）
        login_button = page.locator("button:has-text('登录 / 注册')")
        if login_button.count() > 0:
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


# Pro 套餐特征文本
PRO_PACKAGE_KEYWORD = "Pro 全量权益"
PRO_BUTTON_SELECTORS = [
    # 通过 Pro 套餐卡片定位按钮
    "xpath=//h3[contains(text(), 'Pro 全量权益')]/ancestor::div[1]//button",
    # 直接定位第三个"特惠订阅"按钮
    "button >> nth=2",
]


def _find_pro_button(page):
    """
    在页面中定位 Pro 套餐的购买按钮

    Returns:
        Playwright locator 对象，或 None
    """
    for selector in PRO_BUTTON_SELECTORS:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                return locator.first
        except Exception as e:
            logger.debug(f"选择器 {selector} 未命中: {e}")
            continue
    return None


def _detect_pro_button_state(page) -> dict:
    """
    检测 Pro 套餐按钮的当前状态

    Returns:
        {"state": ButtonState, "text": str, "disabled": bool, "html": str}
    """
    button = _find_pro_button(page)
    if button is None:
        return {
            "state": ButtonState.UNKNOWN,
            "text": "未找到",
            "disabled": True,
            "html": "",
        }

    try:
        text = button.text_content() or ""
        disabled = button.is_disabled()
        html = button.inner_html()
        state = parse_button_state(text, disabled)
        return {"state": state, "text": text, "disabled": disabled, "html": html}
    except Exception as e:
        logger.warning(f"读取按钮状态异常: {e}")
        return {
            "state": ButtonState.UNKNOWN,
            "text": "异常",
            "disabled": True,
            "html": "",
        }


import threading
import uuid
import time as time_module


# 全局任务状态（单实例控制）
_current_task = {
    "is_running": False,
    "current_phase": "idle",
    "message": "待命",
    "next_sale_time": None,
    "countdown_seconds": None,
    "last_error": None,
    "task_id": None,
}
_task_lock = threading.Lock()
_logs_buffer: list = []


def _update_task(**kwargs):
    """更新任务状态（线程安全）"""
    with _task_lock:
        _current_task.update(kwargs)


def _append_log(phase: str, message: str, task_id: str):
    """追加日志到缓冲区"""
    _logs_buffer.append({
        "id": str(uuid.uuid4()),
        "task_id": task_id,
        "phase": phase,
        "message": message,
        "created_at": datetime.now(),
    })
    logger.info(f"[{phase}] {message}")


def get_task_status() -> dict:
    """获取当前任务状态"""
    with _task_lock:
        return dict(_current_task)


def get_task_logs(task_id: str = None, limit: int = 100) -> list:
    """获取任务日志"""
    if task_id:
        logs = [l for l in _logs_buffer if l["task_id"] == task_id]
    else:
        logs = list(_logs_buffer)
    return logs[-limit:]


def _execute_rush(config: dict):
    """
    在独立线程中执行抢购主循环

    Args:
        config: 已校验的配置字典
    """
    task_id = _current_task["task_id"]
    sale_time = config["sale_time"]
    interval_ms = config["refresh_interval_ms"]
    timeout = config["timeout_seconds"]

    _append_log("preheating", "启动浏览器...", task_id)
    _update_task(current_phase="preheating", message="启动浏览器")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(get_state_path()))
            page = context.new_page()

            # 打开目标页面
            _append_log("preheating", f"打开目标页面: {TARGET_URL}", task_id)
            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

            # 校验登录态
            if not _check_login_state(page):
                _append_log("failed", "登录态已失效", task_id)
                _update_task(
                    is_running=False, current_phase="failed",
                    message="登录态已失效，请重新登录", last_error="登录态失效"
                )
                browser.close()
                return

            _append_log("preheating", "预热完成，等待开抢时间...", task_id)

            # 等待到 9:59:50
            target = next_sale_time(sale_time)
            rush_start = target.replace(second=50) if target.second == 0 else target
            now = datetime.now()

            # 如果当前时间早于 rush_start，等待
            wait_seconds = (rush_start - now).total_seconds()
            if wait_seconds > 0:
                _append_log("preheating", f"等待 {int(wait_seconds)} 秒后开始刷新", task_id)
                _update_task(countdown_seconds=int(wait_seconds))
                # 这里简化处理：实际可以倒计时刷新
                time_module.sleep(max(0, wait_seconds - 5))  # 提前 5 秒准备

            # 刷新轮询
            _update_task(current_phase="refreshing", message="开始刷新页面")
            _append_log("refreshing", "开始高频刷新...", task_id)

            deadline = time_module.time() + timeout
            retry_count = 0

            while time_module.time() < deadline:
                try:
                    page.reload(wait_until="networkidle", timeout=15000)
                    result = _detect_pro_button_state(page)

                    _append_log(
                        "refreshing",
                        f"按钮状态: {result['state'].value} 文字: {result['text']}",
                        task_id,
                    )

                    if result["state"] == ButtonState.AVAILABLE:
                        _append_log("clicking", "检测到可点击！立即点击...", task_id)
                        _update_task(current_phase="clicking", message="正在点击")

                        button = _find_pro_button(page)
                        if button:
                            button.click()
                            _append_log("clicking", "已点击按钮，等待页面响应...", task_id)

                            # 等待进入支付页
                            page.wait_for_timeout(3000)
                            current_url = page.url
                            _append_log("success", f"已跳转到: {current_url}", task_id)
                            _update_task(
                                is_running=False, current_phase="success",
                                message=f"成功进入下单页: {current_url}",
                            )
                            browser.close()
                            return

                    retry_count += 1
                    time_module.sleep(interval_ms / 1000.0)

                except Exception as e:
                    logger.warning(f"刷新异常: {e}")
                    retry_count += 1
                    time_module.sleep(interval_ms / 1000.0)

            # 超时
            _append_log("failed", f"超时 {timeout}s，共刷新 {retry_count} 次", task_id)
            _update_task(
                is_running=False, current_phase="failed",
                message=f"抢购超时（{timeout}s），未抢到", last_error="超时",
            )
            browser.close()

    except Exception as e:
        logger.error(f"抢购流程异常: {e}")
        _append_log("failed", f"流程异常: {e}", task_id)
        _update_task(
            is_running=False, current_phase="failed",
            message=f"流程异常: {str(e)}", last_error=str(e),
        )


def start_rush(config: dict) -> dict:
    """
    启动抢购任务

    Args:
        config: 配置字典

    Returns:
        {"success": bool, "message": str, "task_id": str}
    """
    if _current_task["is_running"]:
        return {"success": False, "message": "已有任务在运行，请先停止", "task_id": None}

    task_id = str(uuid.uuid4())
    _update_task(
        is_running=True,
        current_phase="idle",
        message="任务已启动",
        task_id=task_id,
        last_error=None,
    )

    thread = threading.Thread(target=_execute_rush, args=(config,), daemon=True)
    thread.start()

    return {"success": True, "message": "任务已启动", "task_id": task_id}


def stop_rush() -> dict:
    """停止当前抢购任务"""
    if not _current_task["is_running"]:
        return {"success": False, "message": "当前没有运行中的任务"}

    _update_task(
        is_running=False, current_phase="failed",
        message="任务已手动停止", last_error="手动停止",
    )
    return {"success": True, "message": "任务已停止"}
