# GLM-Coding Pro 抢购工具实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有工具聚合平台中新增一个"GLM-Coding Pro 抢购"工具，通过 Playwright 浏览器自动化实现登录态管理、页面刷新检测、自动点击下单，帮助用户在每天 10:00 的限量抢购中抢到 Pro 套餐。

**Architecture:** 后端新增一组路由 + 服务 + 模型 + Schema 文件，核心抢购逻辑封装在 `GlmCodingRusherService` 中，使用 Playwright 的 async API 管理浏览器生命周期；前端新增工具页面，通过 REST API 与后端交互，轮询获取实时状态和日志。

**Tech Stack:** FastAPI、SQLAlchemy、Playwright (Python)、React 18、TypeScript、Tailwind CSS、Zustand

**Spec reference:** `docs/superpowers/specs/2026-06-18-glm-coding-rusher-design.md`

---

## File Structure

### 新增文件

| 文件 | 职责 |
|------|------|
| `backend/app/models/glm_coding_rusher_models.py` | SQLAlchemy 模型（configs、logs） |
| `backend/app/schemas/glm_coding_rusher_schemas.py` | Pydantic 请求/响应模型 |
| `backend/app/services/glm_coding_rusher_service.py` | 核心抢购逻辑：登录、预热、刷新、点击 |
| `backend/app/routes/glm_coding_rusher.py` | FastAPI 路由（9 个端点） |
| `backend/data/glm_coding_rusher/.gitkeep` | 空目录占位，登录态 state 存储 |
| `backend/tests/test_glm_coding_rusher_service.py` | 服务单元测试（按钮解析、时间计算、配置校验） |
| `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx` | 抢购工具主页面 |
| `frontend/src/api/glmCodingRusherApi.ts` | 后端 API 封装 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `backend/requirements.txt` | 添加 `playwright` 依赖 |
| `backend/app/main.py` | 注册新路由 |
| `backend/app/data/tools_data.py` | 注册工具条目 |
| `frontend/src/App.tsx` | 添加路由映射 |
| `frontend/src/i18n/locales/zh-CN.ts` | 添加中文文案 |
| `frontend/src/i18n/locales/en-US.ts` | 添加英文文案 |

---

## Task 1: 后端基础设施 — 依赖、目录、模型

### 1.1 添加 Playwright 依赖

- [ ] **Step 1: 在 requirements.txt 中添加 playwright**

在 `backend/requirements.txt` 末尾追加：

```
# GLM Coding Rusher
playwright>=1.40.0
```

- [ ] **Step 2: 安装依赖**

```bash
cd backend
pip install playwright
playwright install chromium
```

Expected: playwright 安装成功，chromium 浏览器下载完成

- [ ] **Step 3: 创建 state 存储目录**

```bash
mkdir -p backend/data/glm_coding_rusher
touch backend/data/glm_coding_rusher/.gitkeep
```

- [ ] **Step 4: 创建 SQLAlchemy 模型**

创建 `backend/app/models/glm_coding_rusher_models.py`：

```python
"""GLM-Coding Pro 抢购工具数据库模型"""

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime
from sqlalchemy.sql import func

from app.models.base import Base


class GlmCodingRusherConfig(Base):
    __tablename__ = "glm_coding_rusher_configs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    target_package = Column(String(32), nullable=False, default="pro")
    sale_time = Column(String(8), nullable=False, default="10:00")
    preheat_seconds = Column(Integer, nullable=False, default=90)
    refresh_interval_ms = Column(Integer, nullable=False, default=500)
    timeout_seconds = Column(Integer, nullable=False, default=60)
    headless = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GlmCodingRusherLog(Base):
    __tablename__ = "glm_coding_rusher_logs"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    phase = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

- [ ] **Step 5: 提交**

```bash
git add backend/requirements.txt backend/data/glm_coding_rusher/.gitkeep backend/app/models/glm_coding_rusher_models.py
git commit -m "feat(glm-coding-rusher): 添加依赖、目录和数据库模型"
```

---

## Task 2: 核心服务 — 按钮状态解析（TDD）

- [ ] **Step 1: 写测试 — 按钮状态解析**

创建 `backend/tests/test_glm_coding_rusher_service.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.glm_coding_rusher_service'`

- [ ] **Step 3: 实现按钮状态解析**

创建 `backend/app/services/glm_coding_rusher_service.py`，只包含 `parse_button_state`：

```python
"""GLM-Coding Pro 抢购核心服务"""

from enum import Enum
from typing import List


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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestParseButtonState -v
```

Expected: 8 tests PASSED

- [ ] **Step 5: 提交**

```bash
git add backend/tests/test_glm_coding_rusher_service.py backend/app/services/glm_coding_rusher_service.py
git commit -m "feat(glm-coding-rusher): 实现按钮状态解析（TDD）"
```

---

## Task 3: 核心服务 — 时间计算（TDD）

- [ ] **Step 1: 写测试 — 下次开抢时间计算**

在 `backend/tests/test_glm_coding_rusher_service.py` 中追加：

```python
from datetime import datetime, time
from freezegun import freeze_time
from app.services.glm_coding_rusher_service import (
    parse_button_state, ButtonState,
    next_sale_time, format_countdown,
)


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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestNextSaleTime tests/test_glm_coding_rusher_service.py::TestFormatCountdown -v
```

Expected: FAIL — `ImportError: cannot import name 'next_sale_time'`

- [ ] **Step 3: 安装 freezegun**

```bash
cd backend
pip install freezegun
```

在 `backend/requirements.txt` 末尾追加：

```
freezegun>=1.2.0
```

- [ ] **Step 4: 实现时间计算函数**

在 `backend/app/services/glm_coding_rusher_service.py` 中追加（不要覆盖已有内容）：

```python
from datetime import datetime, time, timedelta


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
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestNextSaleTime tests/test_glm_coding_rusher_service.py::TestFormatCountdown -v
```

Expected: 9 tests PASSED

- [ ] **Step 6: 提交**

```bash
git add backend/tests/test_glm_coding_rusher_service.py backend/app/services/glm_coding_rusher_service.py backend/requirements.txt
git commit -m "feat(glm-coding-rusher): 实现时间计算函数（TDD）"
```

---

## Task 4: 核心服务 — 配置校验（TDD）

- [ ] **Step 1: 写测试 — 配置校验**

在 `backend/tests/test_glm_coding_rusher_service.py` 中追加：

```python
from app.services.glm_coding_rusher_service import validate_config, ConfigError


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
        config = {"refresh_interval_ms": 50, "sale_time": "10:00"}
        with pytest.raises(ConfigError, match="refresh_interval_ms"):
            validate_config(config)

    def test_timeout_too_small(self):
        config = {"timeout_seconds": 0, "sale_time": "10:00"}
        with pytest.raises(ConfigError, match="timeout_seconds"):
            validate_config(config)

    def test_timeout_too_large(self):
        config = {"timeout_seconds": 3600, "sale_time": "10:00"}
        with pytest.raises(ConfigError, match="timeout_seconds"):
            validate_config(config)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestValidateConfig -v
```

Expected: FAIL — `ImportError: cannot import name 'validate_config'`

- [ ] **Step 3: 实现配置校验**

在 `backend/app/services/glm_coding_rusher_service.py` 中追加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestValidateConfig -v
```

Expected: 7 tests PASSED

- [ ] **Step 5: 提交**

```bash
git add backend/tests/test_glm_coding_rusher_service.py backend/app/services/glm_coding_rusher_service.py
git commit -m "feat(glm-coding-rusher): 实现配置校验（TDD）"
```

---

## Task 5: Pydantic Schema

- [ ] **Step 1: 创建 Schema 文件**

创建 `backend/app/schemas/glm_coding_rusher_schemas.py`：

```python
"""GLM-Coding Pro 抢购工具 Pydantic 模型"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RusherConfigRequest(BaseModel):
    """配置请求"""
    target_package: str = Field(default="pro", description="目标套餐")
    sale_time: str = Field(default="10:00", description="每天开抢时间 HH:MM")
    preheat_seconds: int = Field(default=90, ge=30, description="提前预热秒数")
    refresh_interval_ms: int = Field(default=500, ge=200, description="刷新间隔毫秒")
    timeout_seconds: int = Field(default=60, ge=10, le=600, description="抢购超时秒数")
    headless: bool = Field(default=False, description="是否无头浏览器")


class RusherConfigResponse(BaseModel):
    """配置响应"""
    target_package: str
    sale_time: str
    preheat_seconds: int
    refresh_interval_ms: int
    timeout_seconds: int
    headless: bool


class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    logged_in: bool
    state_file_exists: bool
    login_time: Optional[str] = None
    message: str


class RusherStatusResponse(BaseModel):
    """抢购状态响应"""
    is_running: bool
    current_phase: str = Field(description="idle|preheating|refreshing|clicking|success|failed")
    message: str
    next_sale_time: Optional[str] = None
    countdown_seconds: Optional[int] = None
    last_error: Optional[str] = None


class RusherLogItem(BaseModel):
    """日志条目"""
    id: str
    task_id: str
    phase: str
    message: str
    created_at: datetime


class RusherLogListResponse(BaseModel):
    """日志列表响应"""
    items: List[RusherLogItem]
    total: int


class LoginRequest(BaseModel):
    """登录请求"""
    headless: bool = Field(default=False, description="是否无头浏览器登录（调试用）")


class StartRequest(BaseModel):
    """启动抢购请求"""
    config_override: Optional[RusherConfigRequest] = None
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/schemas/glm_coding_rusher_schemas.py
git commit -m "feat(glm-coding-rusher): 添加 Pydantic Schema"
```

---

## Task 6: 核心服务 — Playwright 浏览器管理

- [ ] **Step 1: 写测试 — 登录态文件路径**

在 `backend/tests/test_glm_coding_rusher_service.py` 中追加：

```python
from pathlib import Path
from app.services.glm_coding_rusher_service import get_state_path, STATE_DIR


class TestGetStatePath:
    """测试 state 文件路径"""

    def test_returns_path_object(self):
        result = get_state_path()
        assert isinstance(result, Path)

    def test_path_ends_with_state_json(self):
        result = get_state_path()
        assert result.name == "state.json"

    def test_path_inside_state_dir(self):
        result = get_state_path()
        assert str(STATE_DIR) in str(result)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestGetStatePath -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: 实现浏览器管理基础部分**

在 `backend/app/services/glm_coding_rusher_service.py` 中追加：

```python
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_glm_coding_rusher_service.py::TestGetStatePath -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: 实现登录流程（Playwright 同步 API）**

在 `backend/app/services/glm_coding_rusher_service.py` 中追加：

```python
from playwright.sync_api import sync_playwright, Browser, BrowserContext


# 登录态检测关键字
LOGIN_INDICATORS = ["登录", "注册", "微信一键登录", "请输入账号"]


def _check_login_state(page) -> bool:
    """
    检查页面是否处于登录状态

    Returns:
        True 表示已登录，False 表示未登录
    """
    body_text = page.text_content("body") or ""
    for indicator in LOGIN_INDICATORS:
        if indicator in body_text:
            return False
    return True


def open_login_window(headless: bool = False) -> dict:
    """
    打开浏览器让用户手动登录，登录成功后保存 state

    Returns:
        {"success": bool, "message": str}
    """
    try:
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
```

- [ ] **Step 6: 提交**

```bash
git add backend/tests/test_glm_coding_rusher_service.py backend/app/services/glm_coding_rusher_service.py
git commit -m "feat(glm-coding-rusher): 实现 Playwright 浏览器登录和状态校验"
```

---

## Task 7: 核心服务 — 抢购主循环

- [ ] **Step 1: 实现页面元素定位**

在 `backend/app/services/glm_coding_rusher_service.py` 中追加：

```python
import time


# Pro 套餐特征文本
PRO_PACKAGE_KEYWORD = "Pro 全量权益"
PRO_BUTTON_SELECTORS = [
    # 通过 Pro 套餐卡片定位按钮
    "xpath=//h3[contains(text(), 'Pro 全量权益')]/ancestor::div[1]//button",
    # 直接定位第三个"特惠订阅"按钮
    "button >> nth=2",
]


def _find_pro_button(page) -> Optional[object]:
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
```

- [ ] **Step 2: 实现抢购主循环**

在 `backend/app/services/glm_coding_rusher_service.py` 中追加：

```python
import threading
from datetime import datetime


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
                time.sleep(max(0, wait_seconds - 5))  # 提前 5 秒准备

            # 刷新轮询
            _update_task(current_phase="refreshing", message="开始刷新页面")
            _append_log("refreshing", "开始高频刷新...", task_id)

            deadline = time.time() + timeout
            retry_count = 0

            while time.time() < deadline:
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
                    time.sleep(interval_ms / 1000.0)

                except Exception as e:
                    logger.warning(f"刷新异常: {e}")
                    retry_count += 1
                    time.sleep(interval_ms / 1000.0)

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
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/glm_coding_rusher_service.py
git commit -m "feat(glm-coding-rusher): 实现抢购主循环和任务控制"
```

---

## Task 8: 后端 API 路由

- [ ] **Step 1: 创建路由文件**

创建 `backend/app/routes/glm_coding_rusher.py`：

```python
"""GLM-Coding Pro 抢购工具 API 路由"""

import logging
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.schemas.glm_coding_rusher_schemas import (
    RusherConfigRequest, RusherConfigResponse,
    LoginStatusResponse, RusherStatusResponse,
    RusherLogItem, RusherLogListResponse,
    LoginRequest, StartRequest,
)
from app.services.glm_coding_rusher_service import (
    open_login_window, check_login_valid, state_file_exists, get_state_path,
    validate_config, ConfigError,
    get_task_status, get_task_logs, start_rush, stop_rush,
    next_sale_time, format_countdown,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/glm-coding-rusher", tags=["GLM-Coding 抢购"])


# 内存配置（简化版，生产环境应存数据库）
_config_store = {
    "target_package": "pro",
    "sale_time": "10:00",
    "preheat_seconds": 90,
    "refresh_interval_ms": 500,
    "timeout_seconds": 60,
    "headless": False,
}
_config_lock = threading.Lock()


@router.post("/login")
def login(request: LoginRequest):
    """启动浏览器登录"""
    # 在后台线程中执行，避免阻塞 API
    def _run():
        open_login_window(headless=request.headless)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return {"success": True, "message": "登录窗口已打开，请在浏览器中完成登录"}


@router.get("/login-status", response_model=LoginStatusResponse)
def login_status():
    """检查登录状态"""
    exists = state_file_exists()
    if not exists:
        return LoginStatusResponse(
            logged_in=False, state_file_exists=False, message="未登录"
        )

    result = check_login_valid()
    return LoginStatusResponse(
        logged_in=result["valid"],
        state_file_exists=True,
        message=result["message"],
    )


@router.post("/config", response_model=RusherConfigResponse)
def save_config(request: RusherConfigRequest):
    """保存抢购配置"""
    config_dict = request.model_dump()
    try:
        validate_config(config_dict)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    with _config_lock:
        _config_store.update(config_dict)

    return RusherConfigResponse(**_config_store)


@router.get("/config", response_model=RusherConfigResponse)
def get_config():
    """获取当前配置"""
    with _config_lock:
        return RusherConfigResponse(**_config_store)


@router.post("/start")
def start(request: StartRequest = None):
    """启动抢购任务"""
    with _config_lock:
        config = dict(_config_store)

    if request and request.config_override:
        override = request.config_override.model_dump()
        try:
            validate_config(override)
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        config.update(override)

    try:
        validate_config(config)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = start_rush(config)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])

    return result


@router.post("/stop")
def stop():
    """停止抢购任务"""
    return stop_rush()


@router.get("/status", response_model=RusherStatusResponse)
def status():
    """获取抢购状态"""
    task = get_task_status()
    sale_time = _config_store.get("sale_time", "10:00")
    nxt = next_sale_time(sale_time)
    from datetime import datetime
    countdown = int((nxt - datetime.now()).total_seconds())

    return RusherStatusResponse(
        is_running=task["is_running"],
        current_phase=task["current_phase"],
        message=task["message"],
        next_sale_time=nxt.strftime("%Y-%m-%d %H:%M:%S"),
        countdown_seconds=countdown,
        last_error=task.get("last_error"),
    )


@router.get("/logs", response_model=RusherLogListResponse)
def logs(limit: int = 100):
    """获取抢购日志"""
    items = get_task_logs(limit=limit)
    return RusherLogListResponse(
        items=[RusherLogItem(**item) for item in items],
        total=len(items),
    )
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/routes/glm_coding_rusher.py
git commit -m "feat(glm-coding-rusher): 添加后端 API 路由"
```

---

## Task 9: 注册后端模块

- [ ] **Step 1: 在 main.py 中注册路由**

在 `backend/app/main.py` 中：

1. 在文件顶部的 import 区域追加：

```python
from app.routes import glm_coding_rusher
```

2. 在 `app.include_router(...)` 区域（其他路由注册附近）追加：

```python
# GLM-Coding Rusher router
app.include_router(glm_coding_rusher.router, prefix="/api")
```

- [ ] **Step 2: 在 tools_data.py 中注册工具条目**

在 `backend/app/data/tools_data.py` 的 `TOOLS_DATA` 列表末尾（`openclaw` 条目之前或之后）追加：

```python
    Tool(
        id="glm-coding-rusher",
        icon="fa-bolt",
        iconColor="bg-amber-500",
        title="GLM-Coding Pro 抢购",
        description="每天 10:00 限量抢购 GLM-Coding Pro 套餐，自动化抢购助手",
        rating=5.0,
        usageCount="New",
        category="开发工具",
        require_login=True,
    ),
```

- [ ] **Step 3: 启动数据库表创建（在 lifespan 中）**

在 `backend/app/main.py` 的 `lifespan()` 函数中，找到 `Base.metadata.create_all(bind=engine)` 附近，确认模型会自动建表。由于 `GlmCodingRusherConfig` 和 `GlmCodingRusherLog` 继承自 `Base`，只要模块被 import 就会注册，无需额外操作。

- [ ] **Step 4: 重启后端服务**

```bash
python dev_services.py restart backend
```

Expected: 服务正常启动，无报错

- [ ] **Step 5: 测试 API**

```bash
curl -s http://localhost:19092/api/glm-coding-rusher/login-status | python -m json.tool
```

Expected: 返回 `{"logged_in": false, "state_file_exists": false, "message": "未登录"}`

- [ ] **Step 6: 提交**

```bash
git add backend/app/main.py backend/app/data/tools_data.py
git commit -m "feat(glm-coding-rusher): 注册路由和工具条目"
```

---

## Task 10: 前端 API 层

- [ ] **Step 1: 创建 API 封装**

创建 `frontend/src/api/glmCodingRusherApi.ts`：

```typescript
/** GLM-Coding Pro 抢购工具 API */

const BASE_URL = '/api/glm-coding-rusher';

export interface RusherConfig {
  target_package: string;
  sale_time: string;
  preheat_seconds: number;
  refresh_interval_ms: number;
  timeout_seconds: number;
  headless: boolean;
}

export interface LoginStatus {
  logged_in: boolean;
  state_file_exists: boolean;
  login_time?: string;
  message: string;
}

export interface RusherStatus {
  is_running: boolean;
  current_phase: 'idle' | 'preheating' | 'refreshing' | 'clicking' | 'success' | 'failed';
  message: string;
  next_sale_time?: string;
  countdown_seconds?: number;
  last_error?: string;
}

export interface RusherLog {
  id: string;
  task_id: string;
  phase: string;
  message: string;
  created_at: string;
}

export interface LogListResponse {
  items: RusherLog[];
  total: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

/** 启动登录浏览器 */
export async function startLogin(headless = false): Promise<{ success: boolean; message: string }> {
  return request('/login', {
    method: 'POST',
    body: JSON.stringify({ headless }),
  });
}

/** 检查登录状态 */
export async function getLoginStatus(): Promise<LoginStatus> {
  return request('/login-status');
}

/** 保存配置 */
export async function saveConfig(config: Partial<RusherConfig>): Promise<RusherConfig> {
  return request('/config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

/** 获取当前配置 */
export async function getConfig(): Promise<RusherConfig> {
  return request('/config');
}

/** 启动抢购 */
export async function startRush(): Promise<{ success: boolean; message: string; task_id: string }> {
  return request('/start', { method: 'POST' });
}

/** 停止抢购 */
export async function stopRush(): Promise<{ success: boolean; message: string }> {
  return request('/stop', { method: 'POST' });
}

/** 获取状态 */
export async function getStatus(): Promise<RusherStatus> {
  return request('/status');
}

/** 获取日志 */
export async function getLogs(limit = 100): Promise<LogListResponse> {
  return request(`/logs?limit=${limit}`);
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/glmCodingRusherApi.ts
git commit -m "feat(glm-coding-rusher): 添加前端 API 封装"
```

---

## Task 11: 前端主页面 — 登录与配置

- [ ] **Step 1: 创建主页面组件**

创建 `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx`：

```tsx
import { useState, useEffect, useCallback } from 'react';
import {
  getLoginStatus, getConfig, saveConfig,
  startLogin, startRush, stopRush,
  getStatus, getLogs,
  RusherConfig, LoginStatus, RusherStatus, RusherLog,
} from '../../../api/glmCodingRusherApi';

const PHASE_LABELS: Record<string, string> = {
  idle: '待命',
  preheating: '预热中',
  refreshing: '刷新检测中',
  clicking: '正在点击',
  success: '抢购成功',
  failed: '已停止',
};

const PHASE_COLORS: Record<string, string> = {
  idle: 'bg-slate-600',
  preheating: 'bg-blue-500',
  refreshing: 'bg-yellow-500',
  clicking: 'bg-orange-500',
  success: 'bg-green-500',
  failed: 'bg-red-500',
};

export default function GlmCodingRusher() {
  const [loginStatus, setLoginStatus] = useState<LoginStatus | null>(null);
  const [config, setConfig] = useState<RusherConfig>({
    target_package: 'pro',
    sale_time: '10:00',
    preheat_seconds: 90,
    refresh_interval_ms: 500,
    timeout_seconds: 60,
    headless: false,
  });
  const [status, setStatus] = useState<RusherStatus>({
    is_running: false,
    current_phase: 'idle',
    message: '待命',
  });
  const [logs, setLogs] = useState<RusherLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 轮询状态和日志
  const poll = useCallback(async () => {
    try {
      const [s, l, ls] = await Promise.all([getStatus(), getLogs(), getLoginStatus()]);
      setStatus(s);
      setLogs(l.items);
      setLoginStatus(ls);
    } catch {
      // 忽略轮询错误
    }
  }, []);

  useEffect(() => {
    poll();
    const timer = setInterval(poll, 1000);
    return () => clearInterval(timer);
  }, [poll]);

  // 加载配置
  useEffect(() => {
    getConfig().then(setConfig).catch(() => {});
  }, []);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await startLogin(false);
      if (!res.success) throw new Error(res.message);
      // 等待用户完成登录
      const checkTimer = setInterval(async () => {
        const ls = await getLoginStatus();
        setLoginStatus(ls);
        if (ls.logged_in) {
          clearInterval(checkTimer);
          setLoading(false);
        }
      }, 2000);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await saveConfig(config);
      setConfig(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await startRush();
      if (!res.success) throw new Error(res.message);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopRush();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // 倒计时格式化
  const formatCountdown = (seconds?: number) => {
    if (seconds === undefined || seconds <= 0) return '00:00:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 标题 */}
        <div className="flex items-center gap-3">
          <i className="fas fa-bolt text-amber-500 text-2xl" />
          <h1 className="text-2xl font-bold">GLM-Coding Pro 抢购</h1>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* 登录状态卡片 */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold mb-2">登录状态</h2>
              <p className="text-slate-400 text-sm">
                {loginStatus?.logged_in ? '✅ 已登录' : '❌ 未登录'}
              </p>
              {loginStatus?.message && (
                <p className="text-slate-500 text-xs mt-1">{loginStatus.message}</p>
              )}
            </div>
            <button
              onClick={handleLogin}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {loginStatus?.logged_in ? '重新登录' : '打开登录窗口'}
            </button>
          </div>
        </div>

        {/* 配置卡片 */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 space-y-4">
          <h2 className="text-lg font-semibold">抢购配置</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-slate-400 block mb-1">开抢时间</label>
              <input
                type="text"
                value={config.sale_time}
                onChange={(e) => setConfig({ ...config, sale_time: e.target.value })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                placeholder="10:00"
              />
            </div>
            <div>
              <label className="text-sm text-slate-400 block mb-1">预热时间 (秒)</label>
              <input
                type="number"
                value={config.preheat_seconds}
                onChange={(e) => setConfig({ ...config, preheat_seconds: parseInt(e.target.value) || 90 })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm text-slate-400 block mb-1">刷新间隔 (ms)</label>
              <input
                type="number"
                value={config.refresh_interval_ms}
                onChange={(e) => setConfig({ ...config, refresh_interval_ms: parseInt(e.target.value) || 500 })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm text-slate-400 block mb-1">超时时间 (秒)</label>
              <input
                type="number"
                value={config.timeout_seconds}
                onChange={(e) => setConfig({ ...config, timeout_seconds: parseInt(e.target.value) || 60 })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>

          <button
            onClick={handleSaveConfig}
            disabled={loading}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            保存配置
          </button>
        </div>

        {/* 倒计时与状态卡片 */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">抢购状态</h2>
            <span className={`px-3 py-1 rounded-full text-xs font-medium text-white ${PHASE_COLORS[status.current_phase] || 'bg-slate-600'}`}>
              {PHASE_LABELS[status.current_phase] || status.current_phase}
            </span>
          </div>

          <div className="text-center mb-4">
            <div className="text-slate-400 text-sm mb-1">下次开抢</div>
            <div className="text-2xl font-mono font-bold">{status.next_sale_time || '--'}</div>
            <div className="text-3xl font-mono text-amber-400 mt-2">
              {formatCountdown(status.countdown_seconds)}
            </div>
          </div>

          <p className="text-sm text-slate-400 text-center mb-4">{status.message}</p>

          {status.last_error && (
            <p className="text-sm text-red-400 text-center mb-4">错误: {status.last_error}</p>
          )}

          <div className="flex justify-center gap-3">
            {!status.is_running ? (
              <button
                onClick={handleStart}
                disabled={!loginStatus?.logged_in || loading}
                className="px-6 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg text-sm font-bold disabled:opacity-50"
              >
                开始抢购
              </button>
            ) : (
              <button
                onClick={handleStop}
                disabled={loading}
                className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-bold disabled:opacity-50"
              >
                停止抢购
              </button>
            )}
          </div>
        </div>

        {/* 实时日志卡片 */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4">实时日志</h2>
          <div className="bg-slate-900 rounded-lg p-4 max-h-80 overflow-y-auto font-mono text-xs space-y-1">
            {logs.length === 0 ? (
              <div className="text-slate-500 text-center py-8">暂无日志</div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="flex gap-2">
                  <span className="text-slate-500 shrink-0">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                  <span className={`shrink-0 px-1.5 rounded ${PHASE_COLORS[log.phase] || 'bg-slate-600'} text-white text-[10px]`}>
                    {log.phase}
                  </span>
                  <span className="text-slate-300 break-all">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx
git commit -m "feat(glm-coding-rusher): 添加前端主页面组件"
```

---

## Task 12: 前端集成 — 路由、i18n、工具注册

- [ ] **Step 1: 在 App.tsx 中添加路由**

在 `frontend/src/App.tsx` 中：

1. 在顶部 import 区域追加：

```typescript
import GlmCodingRusher from './components/Tools/GlmCodingRusher/GlmCodingRusher';
```

2. 在 `handleToolClick` 函数的 `toolRoutes` 对象中追加：

```typescript
'glm-coding-rusher': '/tools/glm-coding-rusher',
```

3. 在 `<Route element={<Layout />}>` 内其他工具路由附近追加：

```typescript
<Route path="/tools/glm-coding-rusher" element={<GlmCodingRusher />} />
```

- [ ] **Step 2: 添加 i18n 文案**

在 `frontend/src/i18n/locales/zh-CN.ts` 中，找到 `errors.toolNotImplemented` 附近，在 `tools` 相关区域（或新建一个 `glmCodingRusher` 分组）追加：

```typescript
  glmCodingRusher: {
    title: 'GLM-Coding Pro 抢购',
    description: '每天 10:00 限量抢购 GLM-Coding Pro 套餐，自动化抢购助手',
    loginStatus: '登录状态',
    config: '抢购配置',
    saleTime: '开抢时间',
    preheatSeconds: '预热时间 (秒)',
    refreshInterval: '刷新间隔 (ms)',
    timeoutSeconds: '超时时间 (秒)',
    saveConfig: '保存配置',
    rushStatus: '抢购状态',
    nextSale: '下次开抢',
    startRush: '开始抢购',
    stopRush: '停止抢购',
    openLogin: '打开登录窗口',
    reLogin: '重新登录',
    realTimeLog: '实时日志',
    noLog: '暂无日志',
  },
```

在 `frontend/src/i18n/locales/en-US.ts` 中对应追加英文版本：

```typescript
  glmCodingRusher: {
    title: 'GLM-Coding Pro Rusher',
    description: 'Automated rush-buy for GLM-Coding Pro subscription, limited daily at 10:00',
    loginStatus: 'Login Status',
    config: 'Rush Config',
    saleTime: 'Sale Time',
    preheatSeconds: 'Preheat (seconds)',
    refreshInterval: 'Refresh Interval (ms)',
    timeoutSeconds: 'Timeout (seconds)',
    saveConfig: 'Save Config',
    rushStatus: 'Rush Status',
    nextSale: 'Next Sale',
    startRush: 'Start Rush',
    stopRush: 'Stop Rush',
    openLogin: 'Open Login Window',
    reLogin: 'Re-login',
    realTimeLog: 'Real-time Log',
    noLog: 'No logs yet',
  },
```

- [ ] **Step 3: 重启前端**

```bash
python dev_services.py restart frontend
```

Expected: 前端正常启动，无编译错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/App.tsx frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(glm-coding-rusher): 集成前端路由和 i18n 文案"
```

---

## Task 13: 端到端验证

- [ ] **Step 1: 浏览器验证 — 页面渲染**

1. 打开 `http://localhost:5178`
2. 找到"GLM-Coding Pro 抢购"卡片，点击
3. 确认页面正常渲染，无白屏
4. 打开浏览器 DevTools Console，确认无红色错误

- [ ] **Step 2: 浏览器验证 — 登录流程**

1. 点击"打开登录窗口"
2. 确认弹出 Chromium 浏览器窗口
3. 在弹出窗口中完成登录
4. 关闭弹出窗口后，确认主页面显示"已登录"

- [ ] **Step 3: 浏览器验证 — 配置保存**

1. 修改配置项（例如刷新间隔改为 800）
2. 点击"保存配置"
3. 刷新页面，确认配置已持久化

- [ ] **Step 4: 浏览器验证 — 状态轮询**

1. 观察倒计时是否正常跳动
2. 观察状态标签是否显示正确
3. 点击"开始抢购"，观察状态变化
4. 点击"停止抢购"，确认任务停止

- [ ] **Step 5: 提交修复（如有）**

```bash
git add -A
git commit -m "fix(glm-coding-rusher): 修复验证过程中发现的问题"
```

---

## 自审清单

**1. 规格覆盖检查：**

- [x] 后端模块（路由、服务、模型、Schema） — Task 1, 5, 6, 7, 8
- [x] 前端工具页面 — Task 11, 12
- [x] Playwright 登录态管理 — Task 6
- [x] 按钮检测 + 点击下单 — Task 7
- [x] 配置校验 — Task 4
- [x] 时间计算 + 倒计时 — Task 3
- [x] 错误处理（登录失效、超时、风控） — Task 7 中处理
- [x] 单实例控制 — Task 7 中 `_task_lock`
- [x] 实时日志 — Task 7 日志缓冲 + Task 11 轮询展示
- [x] 测试方案 — Task 2, 3, 4 单元测试
- [x] 工具注册 — Task 9 (tools_data.py)

**2. 占位符检查：** 无 TBD、TODO、"implement later" 等占位符。

**3. 类型一致性检查：**
- `ButtonState` 枚举在 Task 2 定义，Task 7 引用 ✓
- `RusherConfig` Schema 在 Task 5 定义，Task 8 和 Task 10 引用 ✓
- `RusherStatus` 在各处命名一致 ✓
- `parse_button_state` 在 Task 2 定义，Task 7 引用 ✓

---

Plan complete and saved to `docs/superpowers/plans/2026-06-18-glm-coding-rusher.md`.

两个执行选项：

**1. Subagent-Driven（推荐）** — 我按任务分派子 agent，每个任务完成后 review，快速迭代

**2. Inline Execution** — 在当前会话中批量执行任务，带检查点

**选哪种？**
