"""GLM-Coding Rusher 服务单元测试"""

import pytest
from app.services.glm_coding_rusher_service import parse_button_state, ButtonState


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
