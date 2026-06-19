"""GLM-Coding Rusher 服务单元测试"""

import pytest
from datetime import datetime, time
from freezegun import freeze_time
from app.services.glm_coding_rusher_service import (
    parse_button_state, ButtonState,
    next_sale_time, format_countdown,
)


class TestParseButtonState:
    """测试按钮状态解析"""

    def test_sold_out(self):
        result = parse_button_state(text="暂时售罄", disabled=True)
        assert result == ButtonState.SOLD_OUT

    def test_coming_soon(self):
        result = parse_button_state(text="06月18日10:00补货", disabled=True)
        assert result == ButtonState.SOLD_OUT

    def test_buy_now(self):
        result = parse_button_state(text="立即购买", disabled=False)
        assert result == ButtonState.AVAILABLE

    def test_special_offer(self):
        result = parse_button_state(text="特惠订阅", disabled=False)
        assert result == ButtonState.AVAILABLE

    def test_open_now(self):
        result = parse_button_state(text="立即开通", disabled=False)
        assert result == ButtonState.AVAILABLE

    def test_disabled_but_available_text(self):
        result = parse_button_state(text="立即购买", disabled=True)
        assert result == ButtonState.SOLD_OUT

    def test_unknown_text(self):
        result = parse_button_state(text="某奇怪按钮", disabled=False)
        assert result == ButtonState.UNKNOWN

    def test_empty_text(self):
        result = parse_button_state(text="", disabled=False)
        assert result == ButtonState.UNKNOWN


class TestNextSaleTime:
    """测试下次开抢时间计算"""

    @freeze_time("2026-06-18 08:30:00")
    def test_before_sale_today(self):
        result = next_sale_time("10:00")
        assert result == datetime(2026, 6, 18, 10, 0, 0)

    @freeze_time("2026-06-18 10:30:00")
    def test_after_sale_today(self):
        result = next_sale_time("10:00")
        assert result == datetime(2026, 6, 19, 10, 0, 0)

    @freeze_time("2026-06-18 09:59:59")
    def test_one_second_before(self):
        result = next_sale_time("10:00")
        assert result == datetime(2026, 6, 18, 10, 0, 0)

    @freeze_time("2026-06-18 23:59:59")
    def test_end_of_day(self):
        result = next_sale_time("10:00")
        assert result == datetime(2026, 6, 19, 10, 0, 0)


class TestFormatCountdown:
    """测试倒计时格式化"""

    def test_zero(self):
        assert format_countdown(0) == "00:00:00"

    def test_one_second(self):
        assert format_countdown(1) == "00:00:01"

    def test_one_minute(self):
        assert format_countdown(60) == "00:01:00"

    def test_one_hour(self):
        assert format_countdown(3600) == "01:00:00"

    def test_complex(self):
        # 2 小时 5 分钟 3 秒
        assert format_countdown(2 * 3600 + 5 * 60 + 3) == "02:05:03"

    def test_negative(self):
        assert format_countdown(-5) == "00:00:00"
