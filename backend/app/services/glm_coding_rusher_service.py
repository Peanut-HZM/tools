"""GLM-Coding Pro 抢购核心服务"""

from enum import Enum
from typing import List
from datetime import datetime, time, timedelta


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
