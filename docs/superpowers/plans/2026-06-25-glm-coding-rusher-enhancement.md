# GLM-Coding Pro 抢购工具增强版实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除所有虚假判断，确保登录态、抢购结果、错误处理都真实可追溯。

**Architecture:** 后端重构核心逻辑（正面登录检测、双重支付页验证、时间窗口控制、错误重试、截图管理器），增加 WebSocket 实时日志推送，配置持久化到数据库。前端改用 WebSocket 接收日志，增强日志展示。

**Tech Stack:** Python 3.10+, FastAPI, Playwright, SQLite, React 18, TypeScript, WebSocket

---

## 文件结构

**后端新增文件：**
- `backend/app/services/glm_coding_rusher_enhanced.py` - 增强版核心逻辑（登录检测、支付验证、截图管理器、错误处理）
- `backend/tests/test_glm_coding_rusher_enhanced.py` - 后端单元测试

**后端修改文件：**
- `backend/app/services/glm_coding_rusher_service.py` - 重构主流程，使用增强模块
- `backend/app/routes/glm_coding_rusher.py` - 添加 WebSocket 端点，移除内存配置
- `backend/app/models/glm_coding_rusher_models.py` - 确认配置表定义

**前端新增文件：**
- `frontend/src/hooks/useWebSocketLogs.ts` - WebSocket 日志 Hook

**前端修改文件：**
- `frontend/src/api/glmCodingRusherApi.ts` - 添加 WebSocket 连接函数
- `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx` - 使用 WebSocket，增强日志展示

---

## Task 1: 后端增强模块 - 登录态正面检测

**Files:**
- Create: `backend/app/services/glm_coding_rusher_enhanced.py`
- Create: `backend/tests/test_glm_coding_rusher_enhanced.py`

- [ ] **Step 1: 编写登录态检测测试**

```python
# backend/tests/test_glm_coding_rusher_enhanced.py
import pytest
from unittest.mock import Mock
from app.services.glm_coding_rusher_enhanced import check_login_state_positive

def test_check_login_state_positive_with_avatar():
    """测试：检测到用户头像，判定为已登录"""
    page = Mock()
    page.locator.return_value.count.return_value = 1
    
    result = check_login_state_positive(page)
    assert result is True

def test_check_login_state_positive_no_indicators():
    """测试：未检测到任何已登录特征，判定为未登录"""
    page = Mock()
    page.locator.return_value.count.return_value = 0
    
    result = check_login_state_positive(page)
    assert result is False

def test_check_login_state_positive_with_exception():
    """测试：异常情况一律视为未登录"""
    page = Mock()
    page.locator.side_effect = Exception("Browser error")
    
    result = check_login_state_positive(page)
    assert result is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_check_login_state_positive_with_avatar -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.glm_coding_rusher_enhanced'"

- [ ] **Step 3: 实现登录态正面检测函数**

```python
# backend/app/services/glm_coding_rusher_enhanced.py
"""GLM-Coding Pro 抢购工具增强模块"""
import logging
from typing import List

logger = logging.getLogger(__name__)

# 已登录特征（必须检测到至少一个）
LOGIN_INDICATORS = [
    "img.avatar",
    "img[alt*='头像']",
    ".user-name",
    ".user-email",
    "[class*='user-info']",
    "button:has-text('我的账户')",
    "button:has-text('个人中心')",
    "a:has-text('退出登录')",
]

def check_login_state_positive(page) -> bool:
    """
    正面检测：必须检测到已登录特征
    
    Args:
        page: Playwright 页面对象
    
    Returns:
        True 表示已登录（检测到至少一个特征）
        False 表示未登录（没有检测到任何特征）或异常
    """
    try:
        for selector in LOGIN_INDICATORS:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    logger.info(f"检测到已登录特征: {selector}")
                    return True
            except Exception:
                continue
        
        logger.warning("未检测到任何已登录特征")
        return False
    except Exception as e:
        logger.error(f"登录态检测异常: {e}")
        return False  # 异常一律视为未登录
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_check_login_state_positive_with_avatar -v`
Expected: PASS

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_check_login_state_positive_no_indicators -v`
Expected: PASS

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_check_login_state_positive_with_exception -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd "G:\IdeaProjects\tools"
git add backend/app/services/glm_coding_rusher_enhanced.py backend/tests/test_glm_coding_rusher_enhanced.py
git commit -m "feat: 添加登录态正面检测模块"
```

---

## Task 2: 后端增强模块 - 支付页双重检测

**Files:**
- Modify: `backend/tests/test_glm_coding_rusher_enhanced.py`
- Modify: `backend/app/services/glm_coding_rusher_enhanced.py`

- [ ] **Step 1: 编写支付页验证测试**

```python
# 追加到 backend/tests/test_glm_coding_rusher_enhanced.py

def test_verify_payment_page_success():
    """测试：URL 变化 + 支付关键词，判定为支付页"""
    page = Mock()
    page.url = "https://open.bigmodel.cn/payment/confirm"
    page.text_content.return_value = "订单确认 支付金额 100元"
    
    result = verify_payment_page(page, "https://open.bigmodel.cn/glm-coding")
    
    assert result["is_payment_page"] is True
    assert result["url_changed"] is True
    assert "payment" in result["current_url"]

def test_verify_payment_page_no_url_change():
    """测试：URL 未变化，判定为非支付页"""
    page = Mock()
    page.url = "https://open.bigmodel.cn/glm-coding"
    page.text_content.return_value = "订单确认"
    
    result = verify_payment_page(page, "https://open.bigmodel.cn/glm-coding")
    
    assert result["is_payment_page"] is False
    assert result["url_changed"] is False

def test_verify_payment_page_no_indicators():
    """测试：URL 变化但无支付特征，判定为非支付页"""
    page = Mock()
    page.url = "https://open.bigmodel.cn/other-page"
    page.text_content.return_value = "其他页面内容"
    
    result = verify_payment_page(page, "https://open.bigmodel.cn/glm-coding")
    
    assert result["is_payment_page"] is False
    assert result["url_changed"] is True
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_verify_payment_page_success -v`
Expected: FAIL with "NameError: name 'verify_payment_page' is not defined"

- [ ] **Step 3: 实现支付页双重检测函数**

```python
# 追加到 backend/app/services/glm_coding_rusher_enhanced.py

# 支付页特征（URL 关键词或页面内容）
PAYMENT_URL_KEYWORDS = [
    "payment",
    "order",
    "checkout",
    "confirm",
    "pay",
    "billing",
]

PAYMENT_PAGE_INDICATORS = [
    "订单确认",
    "支付",
    "付款",
    "金额",
    "订单详情",
    "请选择支付方式",
]

def verify_payment_page(page, original_url: str) -> dict:
    """
    双重检测：验证是否真正进入支付页
    
    Args:
        page: Playwright 页面对象
        original_url: 点击前的 URL（目标页 URL）
    
    Returns:
        {
            "is_payment_page": bool,
            "current_url": str,
            "url_changed": bool,
            "payment_indicators": list,
            "evidence": str,
        }
    """
    current_url = page.url
    url_changed = current_url != original_url
    
    # 检测 1: URL 关键词匹配
    url_matched = any(
        keyword in current_url.lower() 
        for keyword in PAYMENT_URL_KEYWORDS
    )
    
    # 检测 2: 页面内容匹配
    content_matched = []
    try:
        body_text = page.text_content("body") or ""
        content_matched = [
            indicator for indicator in PAYMENT_PAGE_INDICATORS
            if indicator in body_text
        ]
    except Exception as e:
        logger.warning(f"读取页面内容失败: {e}")
    
    # 双重检测：URL 必须变化 + (URL 关键词 OR 页面内容)
    is_payment_page = url_changed and (url_matched or len(content_matched) > 0)
    
    return {
        "is_payment_page": is_payment_page,
        "current_url": current_url,
        "url_changed": url_changed,
        "payment_indicators": content_matched,
        "evidence": f"URL变化={url_changed}, URL关键词={url_matched}, 页面特征={content_matched}",
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_verify_payment_page_success -v`
Expected: PASS

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_verify_payment_page_no_url_change -v`
Expected: PASS

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_verify_payment_page_no_indicators -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/glm_coding_rusher_enhanced.py backend/tests/test_glm_coding_rusher_enhanced.py
git commit -m "feat: 添加支付页双重检测模块"
```

---

## Task 3: 后端增强模块 - 错误分类与重试机制

**Files:**
- Modify: `backend/tests/test_glm_coding_rusher_enhanced.py`
- Modify: `backend/app/services/glm_coding_rusher_enhanced.py`

- [ ] **Step 1: 编写错误分类与重试测试**

```python
# 追加到 backend/tests/test_glm_coding_rusher_enhanced.py

from app.services.glm_coding_rusher_enhanced import classify_error, ErrorType, execute_with_retry

def test_classify_error_temporary():
    """测试：超时错误分类为临时性错误"""
    error = Exception("Connection timeout")
    result = classify_error(error, "page_load")
    assert result == ErrorType.TEMPORARY

def test_classify_error_permanent():
    """测试：元素未找到分类为永久性错误"""
    error = Exception("Element not found")
    result = classify_error(error, "button_click")
    assert result == ErrorType.PERMANENT

def test_execute_with_retry_temporary_error():
    """测试：临时性错误自动重试 3 次"""
    call_count = 0
    
    def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Timeout")
        return "success"
    
    result = execute_with_retry(failing_func, max_retries=3, context="test")
    assert result == "success"
    assert call_count == 3

def test_execute_with_retry_permanent_error():
    """测试：永久性错误立即失败，不重试"""
    call_count = 0
    
    def failing_func():
        nonlocal call_count
        call_count += 1
        raise Exception("Element not found")
    
    with pytest.raises(Exception, match="Element not found"):
        execute_with_retry(failing_func, max_retries=3, context="test")
    
    assert call_count == 1  # 只调用一次，不重试
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_classify_error_temporary -v`
Expected: FAIL

- [ ] **Step 3: 实现错误分类与重试函数**

```python
# 追加到 backend/app/services/glm_coding_rusher_enhanced.py

from enum import Enum
import time as time_module

class ErrorType(str, Enum):
    """错误类型分类"""
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"

def classify_error(error: Exception, context: str = "") -> ErrorType:
    """
    根据异常类型和上下文判断错误类型
    """
    error_str = str(error).lower()
    
    # 临时性错误
    temporary_keywords = [
        "timeout", "timed out", "network", "connection",
        "temporary failure", "loading failed", "net::err",
    ]
    if any(keyword in error_str for keyword in temporary_keywords):
        return ErrorType.TEMPORARY
    
    if context in ["page_load", "page_reload"] and "timeout" in error_str:
        return ErrorType.TEMPORARY
    
    # 永久性错误
    permanent_keywords = [
        "not found", "no element", "login expired", "selector",
    ]
    if any(keyword in error_str for keyword in permanent_keywords):
        return ErrorType.PERMANENT
    
    return ErrorType.UNKNOWN

def execute_with_retry(func, max_retries: int = 3, context: str = "", task_id: str = ""):
    """
    带重试机制的执行函数
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            error_type = classify_error(e, context)
            
            if error_type == ErrorType.PERMANENT:
                logger.error(f"{context} 发生永久性错误（不可重试）: {str(e)}")
                raise
            
            if attempt < max_retries:
                logger.warning(f"{context} 发生临时性错误，{attempt + 1}/{max_retries} 次重试: {str(e)}")
                time_module.sleep(1)
            else:
                logger.error(f"{context} 重试 {max_retries} 次后仍然失败: {str(e)}")
                raise
    
    raise last_error
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py -v`
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/glm_coding_rusher_enhanced.py backend/tests/test_glm_coding_rusher_enhanced.py
git commit -m "feat: 添加错误分类与重试机制"
```

---

## Task 4: 后端增强模块 - 截图管理器

**Files:**
- Modify: `backend/tests/test_glm_coding_rusher_enhanced.py`
- Modify: `backend/app/services/glm_coding_rusher_enhanced.py`

- [ ] **Step 1: 编写截图管理器测试**

```python
# 追加到 backend/tests/test_glm_coding_rusher_enhanced.py

from pathlib import Path
from app.services.glm_coding_rusher_enhanced import ScreenshotManager

def test_screenshot_manager_take_screenshot(tmp_path):
    """测试：截图管理器保存截图"""
    page = Mock()
    page.screenshot = Mock()
    
    manager = ScreenshotManager("test-task-123", tmp_path)
    filepath = manager.take_screenshot(page, "login_success", "登录成功")
    
    assert filepath.exists()
    assert "login_success" in filepath.name
    assert "test-task-123" in filepath.name
    page.screenshot.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_screenshot_manager_take_screenshot -v`
Expected: FAIL

- [ ] **Step 3: 实现截图管理器**

```python
# 追加到 backend/app/services/glm_coding_rusher_enhanced.py

from pathlib import Path
from datetime import datetime

class ScreenshotManager:
    """截图管理器"""
    
    def __init__(self, task_id: str, base_dir: Path):
        self.task_id = task_id
        self.screenshot_dir = base_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots = []
    
    def take_screenshot(self, page, step: str, description: str = "") -> Path:
        """
        截取页面截图并保存
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{step}_{self.task_id}_{timestamp}.png"
        filepath = self.screenshot_dir / filename
        
        try:
            page.screenshot(path=str(filepath))
            self.screenshots.append({
                "step": step,
                "path": str(filepath),
                "description": description,
                "timestamp": timestamp,
            })
            
            log_msg = f"截图已保存: {filepath}"
            if description:
                log_msg += f" ({description})"
            logger.info(log_msg)
            
            return filepath
        except Exception as e:
            logger.warning(f"截图失败: {str(e)}")
            return None
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_glm_coding_rusher_enhanced.py::test_screenshot_manager_take_screenshot -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/glm_coding_rusher_enhanced.py backend/tests/test_glm_coding_rusher_enhanced.py
git commit -m "feat: 添加截图管理器"
```

---

## Task 5: 后端配置持久化

**Files:**
- Modify: `backend/app/services/glm_coding_rusher_service.py`
- Modify: `backend/app/routes/glm_coding_rusher.py`

- [ ] **Step 1: 实现配置持久化函数**

在 `backend/app/services/glm_coding_rusher_service.py` 中添加：

```python
from app.models.glm_coding_rusher_models import GlmCodingRusherConfig

def get_config(user_id: str = "system") -> dict:
    """从数据库读取配置"""
    db = _get_db()
    try:
        config = db.query(GlmCodingRusherConfig).filter(
            GlmCodingRusherConfig.user_id == user_id
        ).first()
        
        if config:
            return {
                "target_package": config.target_package,
                "sale_time": config.sale_time,
                "preheat_seconds": config.preheat_seconds,
                "refresh_interval_ms": config.refresh_interval_ms,
                "timeout_seconds": config.timeout_seconds,
                "headless": config.headless,
            }
        else:
            default_config = {
                "target_package": "pro",
                "sale_time": "10:00",
                "preheat_seconds": 90,
                "refresh_interval_ms": 500,
                "timeout_seconds": 60,
                "headless": False,
            }
            save_config(default_config, user_id)
            return default_config
    finally:
        db.close()

def save_config(config: dict, user_id: str = "system") -> dict:
    """保存配置到数据库"""
    db = _get_db()
    try:
        validate_config(config)
        
        db_config = db.query(GlmCodingRusherConfig).filter(
            GlmCodingRusherConfig.user_id == user_id
        ).first()
        
        if db_config:
            db_config.target_package = config.get("target_package", "pro")
            db_config.sale_time = config.get("sale_time", "10:00")
            db_config.preheat_seconds = config.get("preheat_seconds", 90)
            db_config.refresh_interval_ms = config.get("refresh_interval_ms", 500)
            db_config.timeout_seconds = config.get("timeout_seconds", 60)
            db_config.headless = config.get("headless", False)
        else:
            db_config = GlmCodingRusherConfig(
                user_id=user_id,
                target_package=config.get("target_package", "pro"),
                sale_time=config.get("sale_time", "10:00"),
                preheat_seconds=config.get("preheat_seconds", 90),
                refresh_interval_ms=config.get("refresh_interval_ms", 500),
                timeout_seconds=config.get("timeout_seconds", 60),
                headless=config.get("headless", False),
            )
            db.add(db_config)
        
        db.commit()
        return {"success": True, "message": "配置已保存"}
    except ConfigError as e:
        db.rollback()
        return {"success": False, "message": str(e)}
    except Exception as e:
        db.rollback()
        logger.error(f"保存配置失败: {e}")
        return {"success": False, "message": f"保存失败: {str(e)}"}
    finally:
        db.close()
```

- [ ] **Step 2: 修改路由使用配置持久化**

在 `backend/app/routes/glm_coding_rusher.py` 中：

1. 删除内存配置：
```python
# 删除这行
_config_store = { ... }
```

2. 修改配置 API：
```python
from app.services.glm_coding_rusher_service import get_config, save_config

@router.get("/config")
def get_config_api(user_id: str = "system"):
    config = get_config(user_id)
    return {"success": True, "config": config}

@router.post("/config")
def save_config_api(config: dict, user_id: str = "system"):
    result = save_config(config, user_id)
    return result
```

- [ ] **Step 3: 测试配置持久化**

启动后端服务，访问配置 API，验证配置保存到数据库。

```bash
python dev_services.py restart backend
curl http://localhost:19092/api/glm-coding-rusher/config
```

Expected: 返回默认配置

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/glm_coding_rusher_service.py backend/app/routes/glm_coding_rusher.py
git commit -m "feat: 配置持久化到数据库"
```

---

## Task 6: 后端 WebSocket 实时日志

**Files:**
- Modify: `backend/app/routes/glm_coding_rusher.py`
- Modify: `backend/app/services/glm_coding_rusher_service.py`

- [ ] **Step 1: 实现 WebSocket 连接管理器**

在 `backend/app/routes/glm_coding_rusher.py` 中添加：

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast_log(self, log_entry: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "log", "data": log_entry})
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    from app.services.glm_coding_rusher_service import get_task_logs
    
    await manager.connect(websocket)
    try:
        recent_logs = get_task_logs(limit=50)
        await websocket.send_json({"type": "history", "data": recent_logs})
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

- [ ] **Step 2: 在日志函数中集成 WebSocket 推送**

在 `backend/app/services/glm_coding_rusher_service.py` 的 `_append_log` 函数中添加：

```python
def _append_log(phase: str, message: str, task_id: str):
    entry = { ... }
    _logs_buffer.append(entry)
    _save_log_to_db(entry)
    
    # WebSocket 推送
    try:
        from app.routes.glm_coding_rusher import manager
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast_log(entry),
                loop
            )
    except Exception as e:
        logger.debug(f"WebSocket 推送异常: {e}")
    
    logger.info(f"[{phase}] {message}")
```

- [ ] **Step 3: 测试 WebSocket**

使用浏览器开发者工具或 WebSocket 测试工具连接 `ws://localhost:19092/api/glm-coding-rusher/ws/logs`，验证能接收日志。

- [ ] **Step 4: 提交**

```bash
git add backend/app/routes/glm_coding_rusher.py backend/app/services/glm_coding_rusher_service.py
git commit -m "feat: 添加 WebSocket 实时日志推送"
```

---

## Task 7: 前端 WebSocket 集成

**Files:**
- Create: `frontend/src/hooks/useWebSocketLogs.ts`
- Modify: `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx`

- [ ] **Step 1: 创建 WebSocket Hook**

```typescript
// frontend/src/hooks/useWebSocketLogs.ts
import { useEffect, useState, useCallback } from 'react';

export const useWebSocketLogs = (onLogReceived: (log: any) => void) => {
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/glm-coding-rusher/ws/logs`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'history') {
        setLogs(message.data);
      } else if (message.type === 'log') {
        setLogs(prev => [...prev, message.data]);
        onLogReceived(message.data);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 5000); // 5 秒后重连
    };

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
    };

    return ws;
  }, [onLogReceived]);

  useEffect(() => {
    const ws = connect();
    return () => {
      ws.close();
    };
  }, [connect]);

  return { connected, logs };
};
```

- [ ] **Step 2: 在组件中使用 WebSocket Hook**

在 `GlmCodingRusher.tsx` 中：

```typescript
import { useWebSocketLogs } from '../../../hooks/useWebSocketLogs';

function GlmCodingRusher() {
  const [logs, setLogs] = useState<any[]>([]);
  
  const handleLogReceived = useCallback((log: any) => {
    setLogs(prev => [...prev, log]);
  }, []);
  
  const { connected, logs: wsLogs } = useWebSocketLogs(handleLogReceived);
  
  useEffect(() => {
    setLogs(wsLogs);
  }, [wsLogs]);
  
  // ... 其他代码 ...
}
```

- [ ] **Step 3: 增强日志展示**

添加日志图标和颜色：

```typescript
const getPhaseIcon = (phase: string) => {
  const icons: Record<string, { icon: string; color: string }> = {
    preheating: { icon: '🔥', color: 'text-orange-500' },
    refreshing: { icon: '🔄', color: 'text-blue-500' },
    clicking: { icon: '🖱️', color: 'text-purple-500' },
    success: { icon: '✅', color: 'text-green-500' },
    failed: { icon: '❌', color: 'text-red-500' },
    warning: { icon: '⚠️', color: 'text-yellow-500' },
    payment: { icon: '💳', color: 'text-indigo-500' },
    screenshot: { icon: '📸', color: 'text-pink-500' },
  };
  return icons[phase] || { icon: '📝', color: 'text-gray-500' };
};

// 日志列表
{logs.map(log => {
  const { icon, color } = getPhaseIcon(log.phase);
  return (
    <div key={log.id} className="flex items-start gap-2 p-2 bg-gray-50 rounded">
      <span className={`${color} text-lg`}>{icon}</span>
      <div className="flex-1">
        <div className="text-sm text-gray-600">
          {new Date(log.created_at).toLocaleTimeString()}
        </div>
        <div className="text-sm font-mono">{log.message}</div>
      </div>
    </div>
  );
})}
```

- [ ] **Step 4: 测试 WebSocket 连接**

启动前后端，打开浏览器，验证日志实时更新。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/hooks/useWebSocketLogs.ts frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx
git commit -m "feat: 前端集成 WebSocket 实时日志"
```

---

## Task 8: 集成测试与验收

- [ ] **Step 1: 测试登录态检测**

启动后端，点击"登录"按钮，在浏览器中完成登录，验证日志中显示"检测到已登录特征"。

- [ ] **Step 2: 测试时间窗口控制**

设置开抢时间为 1 小时后，尝试启动任务，验证返回错误"距离开抢还有 60 分钟，超过最大提前量 10 分钟"。

- [ ] **Step 3: 测试配置持久化**

修改配置，重启后端，验证配置未丢失。

- [ ] **Step 4: 测试 WebSocket 日志**

启动抢购任务，验证前端日志实时更新，无延迟。

- [ ] **Step 5: 测试截图保存**

完成一次抢购流程，验证 `backend/data/glm_coding_rusher/screenshots/` 目录下有截图文件。

- [ ] **Step 6: 最终提交**

```bash
git add .
git commit -m "feat: GLM-Coding Pro 抢购工具增强版完成"
```

---

## 验收标准

- ✅ 登录态检测使用正面检测
- ✅ 抢购成功使用双重检测
- ✅ 距离开抢超过 10 分钟拒绝启动
- ✅ 已过开抢时间 20 分钟放弃补抢
- ✅ 临时性错误自动重试 3 次
- ✅ 关键步骤自动截图保存
- ✅ 配置持久化到数据库
- ✅ 日志通过 WebSocket 实时推送
- ✅ 所有错误如实反馈，无兜底逻辑
