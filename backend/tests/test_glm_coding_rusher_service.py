"""GLM-Coding Rusher 服务单元测试"""

import pytest
from datetime import datetime, time
from freezegun import freeze_time
from app.services.glm_coding_rusher_service import (
    parse_button_state, ButtonState,
    next_sale_time, format_countdown,
    validate_config, ConfigError,
    get_state_path, STATE_DIR,
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


class TestValidateConfig:
    """测试配置校验"""

    def test_valid_config(self):
        config = {
            "target_package": "pro",
            "sale_time": "10:00",
            "preheat_seconds": 90,
            "refresh_interval_ms": 500,
            "timeout_seconds": 60,
        }
        result = validate_config(config)
        assert result is None  # 无错误

    def test_invalid_sale_time_format(self):
        config = {"sale_time": "25:00"}
        with pytest.raises(ConfigError, match="sale_time"):
            validate_config(config)

    def test_invalid_sale_time_text(self):
        config = {"sale_time": "abc"}
        with pytest.raises(ConfigError, match="sale_time"):
            validate_config(config)

    def test_preheat_too_small(self):
        config = {"preheat_seconds": 5, "sale_time": "10:00"}
        with pytest.raises(ConfigError, match="preheat_seconds"):
            validate_config(config)

    def test_refresh_interval_too_small(self):
        config = {"refresh_interval_ms": 50, "sale_time": "10:00", "preheat_seconds": 90, "timeout_seconds": 60}
        with pytest.raises(ConfigError, match="refresh_interval_ms"):
            validate_config(config)

    def test_timeout_too_small(self):
        config = {"timeout_seconds": 0, "sale_time": "10:00", "preheat_seconds": 90, "refresh_interval_ms": 500}
        with pytest.raises(ConfigError, match="timeout_seconds"):
            validate_config(config)

    def test_timeout_too_large(self):
        config = {"timeout_seconds": 3600, "sale_time": "10:00", "preheat_seconds": 90, "refresh_interval_ms": 500}
        with pytest.raises(ConfigError, match="timeout_seconds"):
            validate_config(config)


class TestGetStatePath:
    """测试 state 文件路径"""

    def test_returns_path_object(self):
        from pathlib import Path
        result = get_state_path()
        assert isinstance(result, Path)

    def test_path_ends_with_state_json(self):
        result = get_state_path()
        assert result.name == "state.json"

    def test_path_inside_state_dir(self):
        result = get_state_path()
        assert str(STATE_DIR) in str(result)
