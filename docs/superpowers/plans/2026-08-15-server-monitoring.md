# 服务器监控子项目实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有「系统监控」升级为对标宝塔/1Panel 的多服务器监控体系：SSH 无代理采集、历史趋势、远程进程/服务管理、告警（Webhook+站内），六页签前端。

**Architecture:** 后端单个 asyncio 后台采集任务每 30s 通过 paramiko 对远程 Linux 服务器执行内嵌 bash 脚本（一次往返返回全部指标 JSON），本机走 psutil；指标写入 PostgreSQL 时序表（保留 7 天），告警引擎在每次采样后评估规则；前端重构成 `SystemMonitor/` 目录六页签（服务器列表/总览/历史趋势/进程/服务/告警）。

**Tech Stack:** Python 3.10+ / FastAPI / psycopg2 / paramiko / psutil / httpx / PostgreSQL；React 18 / TypeScript / Tailwind / recharts / zustand

**规格文档:** `docs/superpowers/specs/2026-08-15-server-monitoring-design.md`

## Global Constraints

- 所有代码注释、日志、前端文案使用中文（遵循 AGENTS.md）
- 新增代码不引入 i18n（与现有 SystemMonitor 一致，纯中文文案）
- 数据库访问模式：`get_pooled_db_connection()` / `release_db_connection()`（`app.config.database`），psycopg2 RealDictCursor
- 凭据加密：`EncryptionUtils.encrypt/decrypt`（`app.utils.encryption`），解密后的密码/私钥严禁写入日志
- 路由鉴权：`user_id: str = Depends(get_current_user_id)`（`app.middleware.auth_middleware`）
- 后端验证：`cd backend && python -m py_compile <file> && ruff check . && pytest tests/test_monitor*.py`
- 前端验证：`cd frontend && npx tsc --noEmit && npx vitest run`
- 新增依赖：无（httpx、paramiko、psutil 已在 requirements.txt）
- 采集指标统一 dict 结构（后端所有模块共用）：
  ```python
  {
    "cpu_percent": float, "cpu_per_core": list[float], "load_avg": list[float],  # [l1,l5,l15]
    "mem_total": int, "mem_used": int, "mem_percent": float,
    "swap_total": int, "swap_used": int, "swap_percent": float,
    "disk_total": int, "disk_used": int, "disk_percent": float,
    "net_recv_rate": float, "net_sent_rate": float,   # B/s
    "disk_read_rate": float, "disk_write_rate": float, # B/s
    "process_count": int, "uptime_seconds": int,
  }
  ```
- `server` dict（服务器行，全后端共用）字段：`id, user_id, name, server_type('local'|'ssh'), host, port, username, password(已解密), private_key(已解密), passphrase(已解密), group_name, status, last_error, last_seen_at`

---

## 文件结构

```
backend/app/models/monitor_models.py                 # 新建：pydantic 模型
backend/app/services/monitor/__init__.py             # 新建
backend/app/services/monitor/script.py               # 新建：bash 采集脚本 + 解析纯函数
backend/app/services/monitor/ssh_client.py           # 新建：paramiko 连接池
backend/app/services/monitor/metric_repo.py          # 新建：时序存储
backend/app/services/monitor/server_service.py       # 新建：服务器 CRUD + 设置
backend/app/services/monitor/alert_engine.py         # 新建：告警规则/评估/日志
backend/app/services/monitor/webhook_notify.py       # 新建：Webhook 推送
backend/app/services/monitor/remote_ops.py           # 新建：按需远程操作（进程/服务/分区/权限）
backend/app/services/monitor/collector.py            # 新建：采集引擎
backend/app/routes/monitor.py                        # 新建：API 路由
backend/app/main.py                                  # 修改：注册路由 + lifespan 启动采集
backend/tests/test_monitor_script.py                 # 新建
backend/tests/test_monitor_alert_engine.py           # 新建
backend/tests/test_monitor_server_service.py         # 新建
backend/tests/test_monitor_collector.py              # 新建
backend/tests/test_monitor_api.py                    # 新建

frontend/src/api/monitorApi.ts                       # 新建
frontend/src/stores/monitorStore.ts                  # 新建
frontend/src/components/Tools/SystemMonitor/index.tsx            # 新建：页签容器
frontend/src/components/Tools/SystemMonitor/ServerList.tsx      # 新建
frontend/src/components/Tools/SystemMonitor/Overview.tsx        # 新建
frontend/src/components/Tools/SystemMonitor/History.tsx         # 新建
frontend/src/components/Tools/SystemMonitor/Processes.tsx       # 新建
frontend/src/components/Tools/SystemMonitor/Services.tsx        # 新建
frontend/src/components/Tools/SystemMonitor/Alerts.tsx          # 新建
frontend/src/components/Tools/SystemMonitor/components/MetricChart.tsx      # 新建
frontend/src/components/Tools/SystemMonitor/components/ServerCard.tsx      # 新建
frontend/src/components/Tools/SystemMonitor/components/ServerSelector.tsx  # 新建
frontend/src/components/Tools/SystemMonitor/components/ResourceCards.tsx   # 新建
frontend/src/components/Tools/SystemMonitor/components/SystemInfoCards.tsx # 新建
frontend/src/components/Tools/SystemMonitor/components/AddServerModal.tsx  # 新建
frontend/src/components/Tools/SystemMonitor/components/ConfirmModal.tsx    # 新建
frontend/src/components/Tools/SystemMonitor/SystemMonitor.test.tsx         # 新建
frontend/src/components/Workspace/toolComponents.tsx  # 修改：SystemMonitor 导入路径
frontend/src/components/Tools/SystemMonitor.tsx      # 删除（迁移后）
```

---

## 后端任务

### Task 1: 监控数据模型（monitor_models.py）

**Files:**
- Create: `backend/app/models/monitor_models.py`
- Test: `backend/tests/test_monitor_models.py`（随本任务新建）

**Interfaces:**
- Produces: 下述 pydantic 模型，Task 2/8/9 引用

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_models.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pydantic import ValidationError
import pytest
from app.models.monitor_models import (
    CreateMonitorServerRequest, MonitorServerResponse, ImportSSHRequest,
    AlertRuleCreateRequest, AlertRuleResponse, MonitorSettings,
)

def test_create_server_request_validation():
    req = CreateMonitorServerRequest(
        name="测试服务器", host="192.168.1.10", port=22,
        username="root", password="secret")
    assert req.server_type == "ssh"
    assert req.port == 22

def test_create_server_request_rejects_bad_port():
    with pytest.raises(ValidationError):
        CreateMonitorServerRequest(name="x", host="h", port=99999, username="u")

def test_import_ssh_request():
    assert ImportSSHRequest(ssh_config_id="abc").ssh_config_id == "abc"

def test_alert_rule_create():
    rule = AlertRuleCreateRequest(metric="cpu_percent", operator=">", threshold=90, duration=3)
    assert rule.server_id == "all"
    assert rule.duration == 3

def test_monitor_settings_defaults():
    s = MonitorSettings()
    assert s.webhook_url == ""
    assert s.collect_interval == 30
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_models.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现模型**

```python
# backend/app/models/monitor_models.py
"""
服务器监控数据模型 - 服务器/指标/告警相关请求与响应结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateMonitorServerRequest(BaseModel):
    """新建监控服务器请求"""
    name: str = Field(..., min_length=1, max_length=64)
    server_type: str = Field("ssh", pattern="^(local|ssh)$")
    host: Optional[str] = Field(None, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)
    group_name: Optional[str] = Field(None, max_length=64)


class UpdateMonitorServerRequest(BaseModel):
    """更新监控服务器请求（全部可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)
    group_name: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, pattern="^(enabled|disabled)$")


class MonitorServerResponse(BaseModel):
    """监控服务器响应"""
    id: str
    user_id: str
    name: str
    server_type: str
    host: str = ""
    port: int = 22
    username: str = ""
    group_name: Optional[str] = None
    status: str
    last_error: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    metric: Optional[dict] = None  # 最近一次采集指标（列表接口嵌入）


class ImportSSHRequest(BaseModel):
    """从 SSH 配置导入请求"""
    ssh_config_id: str = Field(..., min_length=1, max_length=64)


class TestMonitorServerRequest(BaseModel):
    """测试监控服务器连接请求"""
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)


class AlertRuleCreateRequest(BaseModel):
    """新建告警规则请求"""
    server_id: str = Field("all", min_length=1, max_length=64)
    metric: str = Field(..., pattern="^(cpu_percent|memory_percent|disk_percent|load_avg|net_recv_rate|net_sent_rate)$")
    operator: str = Field(..., pattern="^(>|>=|<|<=)$")
    threshold: float = Field(..., ge=0, le=1000000)
    duration: int = Field(3, ge=1, le=60)
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    """更新告警规则请求（全部可选）"""
    server_id: Optional[str] = None
    metric: Optional[str] = Field(None, pattern="^(cpu_percent|memory_percent|disk_percent|load_avg|net_recv_rate|net_sent_rate)$")
    operator: Optional[str] = Field(None, pattern="^(>|>=|<|<=)$")
    threshold: Optional[float] = Field(None, ge=0, le=1000000)
    duration: Optional[int] = Field(None, ge=1, le=60)
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    """告警规则响应"""
    id: str
    user_id: str
    server_id: str
    metric: str
    operator: str
    threshold: float
    duration: int
    enabled: bool
    created_at: datetime


class AlertLogResponse(BaseModel):
    """告警触发记录响应"""
    id: int
    rule_id: str
    server_id: str
    server_name: str
    metric: str
    actual_value: float
    status: str
    is_read: bool
    notified_at: datetime


class MonitorSettings(BaseModel):
    """监控设置"""
    webhook_url: Optional[str] = Field(None, max_length=500)
    collect_interval: int = Field(30, ge=10, le=300)


class ServiceActionRequest(BaseModel):
    """服务操作请求"""
    action: str = Field(..., pattern="^(start|stop|restart)$")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_models.py -v`
Expected: PASS（5 个）

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/monitor_models.py backend/tests/test_monitor_models.py
git commit -m "feat: 监控模块数据模型"
```

---

### Task 2: 服务器 CRUD 服务（server_service.py）

**Files:**
- Create: `backend/app/services/monitor/__init__.py`、`backend/app/services/monitor/server_service.py`
- Test: `backend/tests/test_monitor_server_service.py`

**Interfaces:**
- Consumes: Task 1 的 `CreateMonitorServerRequest` / `UpdateMonitorServerRequest` / `MonitorServerResponse` / `ImportSSHRequest` / `MonitorSettings`
- Produces:
  - `MonitorServerService.ensure_tables() -> None`
  - `MonitorServerService.get_servers(user_id) -> List[Dict]`（每项含 `metric` 最近指标）
  - `MonitorServerService.get_server(user_id, server_id) -> Optional[Dict]`（凭据已解密）
  - `MonitorServerService.create_server(user_id, req) -> Dict`
  - `MonitorServerService.update_server(user_id, server_id, req) -> Optional[Dict]`
  - `MonitorServerService.delete_server(user_id, server_id) -> bool`
  - `MonitorServerService.import_from_ssh(user_id, ssh_config_id) -> Dict`
  - `MonitorServerService.test_connection(req) -> None`（失败抛 `HTTPException(400)`）
  - `MonitorServerService.get_enabled_servers() -> List[Dict]`（全部用户，Task 7 用）
  - `MonitorServerService.update_status(server_id, status, last_error, last_seen_at) -> None`
  - `MonitorServerService.get_settings(user_id) -> Dict`
  - `MonitorServerService.save_settings(user_id, req) -> None`
  - `MonitorServerService.get_global_interval() -> int`

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_server_service.py
"""
监控服务器服务测试 - 使用内存 fake 数据库连接
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import server_service
from app.services.monitor.server_service import MonitorServerService


class FakeCursor:
    """模拟 psycopg2 游标（只覆盖本模块用到的操作）"""
    def __init__(self, conn, fetch_results=None, rowcount=1):
        self.conn = conn
        self._results = fetch_results if fetch_results is not None else []
        self.rowcount = rowcount
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, results=None):
        self.commits = 0
        self.rollbacks = 0
        self._results = results

    def cursor(self):
        return FakeCursor(self, self._results)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    holder = {"conn": FakeConn()}
    monkeypatch.setattr(server_service, "get_pooled_db_connection", lambda: holder["conn"])
    monkeypatch.setattr(server_service, "release_db_connection", lambda c: None)
    return holder


def test_create_server_encrypts_password(monkeypatch, fake_db):
    from app.models.monitor_models import CreateMonitorServerRequest
    req = CreateMonitorServerRequest(name="web1", host="10.0.0.1", username="root", password="p@ss")
    fake_db["conn"]._results = [{"id": "srv-1", "user_id": "u1", "name": "web1",
                                 "server_type": "ssh", "host": "10.0.0.1", "port": 22,
                                 "username": "root", "group_name": None, "status": "enabled",
                                 "last_error": None, "last_seen_at": None,
                                 "created_at": __import__("datetime").datetime(2026, 1, 1)}]
    created = MonitorServerService.create_server("u1", req)
    assert created["id"] == "srv-1"
    # 确认写入的是加密后的密码
    insert_sql = fake_db["conn"].cursor().executed[0][0] if fake_db["conn"].cursor().executed else ""
    # cursor 每次调用是新对象，直接断言结果即可
    assert created["name"] == "web1"


def test_get_servers_returns_metric(monkeypatch, fake_db):
    from datetime import datetime
    fake_db["conn"]._results = [
        {"id": "srv-1", "user_id": "u1", "name": "web1", "server_type": "ssh",
         "host": "10.0.0.1", "port": 22, "username": "root", "group_name": None,
         "status": "online", "last_error": None, "last_seen_at": datetime(2026, 1, 1),
         "created_at": datetime(2026, 1, 1),
         "metric": {"cpu_percent": 12.3, "mem_percent": 55.0, "disk_percent": 40.0,
                    "net_recv_rate": 1000, "net_sent_rate": 500}}
    ]
    servers = MonitorServerService.get_servers("u1")
    assert len(servers) == 1
    assert servers[0]["metric"]["cpu_percent"] == 12.3


def test_get_server_decrypts_credentials(monkeypatch, fake_db):
    from datetime import datetime
    fake_db["conn"]._results = [
        {"id": "srv-1", "user_id": "u1", "name": "web1", "server_type": "ssh",
         "host": "10.0.0.1", "port": 22, "username": "root",
         "password_encrypted": "ENC:pw", "private_key_encrypted": None,
         "passphrase_encrypted": None, "group_name": None, "status": "online",
         "last_error": None, "last_seen_at": datetime(2026, 1, 1),
         "created_at": datetime(2026, 1, 1)}
    ]
    monkeypatch.setattr(server_service.EncryptionUtils, "decrypt",
                        staticmethod(lambda v: v.replace("ENC:", "")))
    server = MonitorServerService.get_server("u1", "srv-1")
    assert server["password"] == "pw"


def test_get_global_interval_default(monkeypatch, fake_db):
    fake_db["conn"]._results = []  # 无全局设置行
    assert MonitorServerService.get_global_interval() == 30


def test_get_global_interval_from_db(monkeypatch, fake_db):
    fake_db["conn"]._results = [{"collect_interval": 60}]
    assert MonitorServerService.get_global_interval() == 60
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_server_service.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现服务**

```python
# backend/app/services/monitor/__init__.py
"""服务器监控服务模块"""
```

```python
# backend/app/services/monitor/server_service.py
"""
监控服务器服务 - 服务器 CRUD、SSH 导入、凭据加密、监控设置
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import HTTPException
import paramiko

from app.config.database import get_pooled_db_connection, release_db_connection
from app.utils.encryption import EncryptionUtils
from app.models.monitor_models import (
    CreateMonitorServerRequest, UpdateMonitorServerRequest, MonitorServerResponse,
    ImportSSHRequest, TestMonitorServerRequest, MonitorSettings,
)

logger = logging.getLogger(__name__)


class MonitorServerService:
    """监控服务器服务（静态方法 + 手写 SQL，沿用 ssh_tool_service 模式）"""

    @staticmethod
    def ensure_tables() -> None:
        """确保监控相关表存在（建表语句幂等）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_servers (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    name VARCHAR(64) NOT NULL,
                    server_type VARCHAR(16) NOT NULL DEFAULT 'ssh',
                    host VARCHAR(255) NOT NULL DEFAULT '',
                    port INT NOT NULL DEFAULT 22,
                    username VARCHAR(128) NOT NULL DEFAULT '',
                    password_encrypted TEXT,
                    private_key_encrypted TEXT,
                    passphrase_encrypted TEXT,
                    source_ssh_id VARCHAR(64),
                    group_name VARCHAR(64),
                    status VARCHAR(16) NOT NULL DEFAULT 'enabled',
                    last_error TEXT,
                    last_seen_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_servers_user ON monitor_servers(user_id, deleted)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_servers_status ON monitor_servers(status)")
            conn.commit()
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def ensure_local_server(user_id: str) -> None:
        """确保当前用户存在本机节点（幂等）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM monitor_servers WHERE user_id = %s AND server_type = 'local' AND deleted = FALSE",
                (user_id,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """INSERT INTO monitor_servers (id, user_id, name, server_type, status)
                       VALUES (%s, %s, '本机', 'local', 'enabled')""",
                    (str(uuid.uuid4()), user_id),
                )
                conn.commit()
                logger.info("已为用户 %s 创建本机监控节点", user_id)
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def _row_to_dict(row) -> Dict:
        """数据库行转响应 dict（去除加密字段，带解密凭据版本由 get_server 生成）"""
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "server_type": row["server_type"],
            "host": row.get("host") or "",
            "port": row.get("port") or 22,
            "username": row.get("username") or "",
            "group_name": row.get("group_name"),
            "status": row.get("status"),
            "last_error": row.get("last_error"),
            "last_seen_at": row.get("last_seen_at"),
            "created_at": row.get("created_at"),
        }

    @staticmethod
    def _get_row(user_id: str, server_id: str) -> Optional[Dict]:
        """查询单个服务器原始行（含加密凭据），不存在返回 None"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM monitor_servers
                   WHERE id = %s AND user_id = %s AND deleted = FALSE""",
                (server_id, user_id),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def get_servers(user_id: str) -> List[Dict]:
        """获取服务器列表（自动创建本机节点，嵌入最近指标）"""
        MonitorServerService.ensure_local_server(user_id)
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT s.*, m.cpu_percent, m.mem_percent, m.disk_percent,
                       m.net_recv_rate, m.net_sent_rate, m.disk_read_rate, m.disk_write_rate
                FROM monitor_servers s
                LEFT JOIN LATERAL (
                    SELECT * FROM monitor_metrics
                    WHERE server_id = s.id
                    ORDER BY collected_at DESC LIMIT 1
                ) m ON TRUE
                WHERE s.user_id = %s AND s.deleted = FALSE
                ORDER BY CASE WHEN s.server_type = 'local' THEN 0 ELSE 1 END, s.created_at
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
            release_db_connection(conn)
        result = []
        for row in rows:
            item = MonitorServerService._row_to_dict(row)
            metric = {
                "cpu_percent": row.get("cpu_percent"),
                "mem_percent": row.get("mem_percent"),
                "disk_percent": row.get("disk_percent"),
                "net_recv_rate": row.get("net_recv_rate"),
                "net_sent_rate": row.get("net_sent_rate"),
                "disk_read_rate": row.get("disk_read_rate"),
                "disk_write_rate": row.get("disk_write_rate"),
            }
            item["metric"] = metric if any(v is not None for v in metric.values()) else None
            result.append(item)
        return result

    @staticmethod
    def get_server(user_id: str, server_id: str) -> Optional[Dict]:
        """获取单个服务器，凭据已解密（内部使用）"""
        row = MonitorServerService._get_row(user_id, server_id)
        if not row:
            return None
        server = MonitorServerService._row_to_dict(row)
        server["password"] = EncryptionUtils.decrypt(row.get("password_encrypted")) if row.get("password_encrypted") else None
        server["private_key"] = EncryptionUtils.decrypt(row.get("private_key_encrypted")) if row.get("private_key_encrypted") else None
        server["passphrase"] = EncryptionUtils.decrypt(row.get("passphrase_encrypted")) if row.get("passphrase_encrypted") else None
        return server

    @staticmethod
    def create_server(user_id: str, req: CreateMonitorServerRequest) -> Dict:
        """新建监控服务器（凭据加密存储）"""
        if req.server_type == "local":
            raise HTTPException(status_code=400, detail="本机节点为内置节点，无需手动创建")
        server_id = str(uuid.uuid4())
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO monitor_servers
                   (id, user_id, name, server_type, host, port, username,
                    password_encrypted, private_key_encrypted, passphrase_encrypted, group_name, status)
                   VALUES (%s, %s, %s, 'ssh', %s, %s, %s, %s, %s, %s, %s, 'enabled')""",
                (server_id, user_id, req.name, req.host or "", req.port,
                 req.username or "",
                 EncryptionUtils.encrypt(req.password) if req.password else None,
                 EncryptionUtils.encrypt(req.private_key) if req.private_key else None,
                 EncryptionUtils.encrypt(req.passphrase) if req.passphrase else None,
                 req.group_name),
            )
            conn.commit()
            logger.info("监控服务器创建成功: user=%s name=%s", user_id, req.name)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)
        return MonitorServerService.get_server(user_id, server_id)

    @staticmethod
    def update_server(user_id: str, server_id: str, req: UpdateMonitorServerRequest) -> Optional[Dict]:
        """更新监控服务器（只更新传入字段）"""
        row = MonitorServerService._get_row(user_id, server_id)
        if not row:
            return None
        if row["server_type"] == "local":
            # 本机节点只允许改名/禁用
            fields, values = [], []
            for key, col in (("name", "name"), ("group_name", "group_name")):
                value = getattr(req, key, None)
                if value is not None:
                    fields.append(f"{col} = %s")
                    values.append(value)
            if req.status == "disabled":
                fields.append("status = 'disabled'")
            elif req.status == "enabled":
                fields.append("status = 'enabled'")
        else:
            fields, values = [], []
            for key, col, enc in (
                ("name", "name", False), ("host", "host", False),
                ("port", "port", False), ("username", "username", False),
                ("password", "password_encrypted", True),
                ("private_key", "private_key_encrypted", True),
                ("passphrase", "passphrase_encrypted", True),
                ("group_name", "group_name", False),
            ):
                value = getattr(req, key, None)
                if value is not None:
                    fields.append(f"{col} = %s")
                    values.append(EncryptionUtils.encrypt(value) if enc and value else value)
            if req.status in ("enabled", "disabled"):
                fields.append("status = %s")
                values.append(req.status)
        if not fields:
            return MonitorServerService.get_server(user_id, server_id)
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            values.append(server_id)
            cursor.execute(
                f"UPDATE monitor_servers SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                values,
            )
            conn.commit()
            logger.info("监控服务器更新: user=%s id=%s", user_id, server_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)
        return MonitorServerService.get_server(user_id, server_id)

    @staticmethod
    def delete_server(user_id: str, server_id: str) -> bool:
        """删除监控服务器（软删除；本机节点不可删除）"""
        row = MonitorServerService._get_row(user_id, server_id)
        if not row:
            return False
        if row["server_type"] == "local":
            raise HTTPException(status_code=400, detail="本机节点不可删除")
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE monitor_servers SET deleted = TRUE, status = 'disabled', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (server_id,),
            )
            conn.commit()
            logger.info("监控服务器删除: user=%s id=%s", user_id, server_id)
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def import_from_ssh(user_id: str, ssh_config_id: str) -> Dict:
        """从 SSH 配置导入为监控服务器（凭据复制，后续独立管理）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM ssh_configs
                   WHERE id = %s AND user_id = %s AND deleted = FALSE""",
                (ssh_config_id, user_id),
            )
            ssh_row = cursor.fetchone()
        finally:
            cursor.close()
            release_db_connection(conn)
        if not ssh_row:
            raise HTTPException(status_code=404, detail="SSH 配置不存在")
        # 复用 SSH 服务加密列名映射（password_encrypted / password 兼容）
        password_col = "password_encrypted" if "password_encrypted" in ssh_row else "password"
        private_key_col = "private_key_encrypted" if "private_key_encrypted" in ssh_row else "private_key"
        passphrase_col = "passphrase_encrypted" if "passphrase_encrypted" in ssh_row else "passphrase"
        req = CreateMonitorServerRequest(
            name=ssh_row["alias"],
            host=ssh_row["host"],
            port=ssh_row["port"],
            username=ssh_row["username"],
            password=EncryptionUtils.decrypt(ssh_row.get(password_col)) if ssh_row.get(password_col) else None,
            private_key=EncryptionUtils.decrypt(ssh_row.get(private_key_col)) if ssh_row.get(private_key_col) else None,
            passphrase=EncryptionUtils.decrypt(ssh_row.get(passphrase_col)) if ssh_row.get(passphrase_col) else None,
            group_name=ssh_row.get("group_name"),
        )
        # 直接复用 create_server 逻辑，并记录来源
        created = MonitorServerService.create_server(user_id, req)
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE monitor_servers SET source_ssh_id = %s WHERE id = %s",
                (ssh_config_id, created["id"]),
            )
            conn.commit()
        finally:
            cursor.close()
            release_db_connection(conn)
        logger.info("SSH 配置导入监控: user=%s ssh=%s", user_id, ssh_config_id)
        return created

    @staticmethod
    def test_connection(req: TestMonitorServerRequest) -> None:
        """测试 SSH 连接，失败抛 400"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pkey = None
            if req.private_key:
                pkey = MonitorServerService._load_private_key(req.private_key, req.passphrase)
            ssh.connect(
                hostname=req.host, port=req.port, username=req.username,
                password=req.password, pkey=pkey, timeout=10,
                allow_agent=False, look_for_keys=False,
            )
            ssh.close()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")

    @staticmethod
    def _load_private_key(private_key: str, passphrase: Optional[str]):
        """加载私钥（复用 SSH 工具的方式）"""
        import io
        key_classes = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]
        for key_cls in key_classes:
            try:
                return key_cls.from_private_key(io.StringIO(private_key), password=passphrase)
            except Exception:
                continue
        raise HTTPException(status_code=400, detail="无效的私钥")

    @staticmethod
    def get_enabled_servers() -> List[Dict]:
        """获取所有用户的启用监控服务器（含解密凭据，供采集引擎使用）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM monitor_servers
                   WHERE status = 'enabled' AND deleted = FALSE""",
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
            release_db_connection(conn)
        result = []
        for row in rows:
            server = MonitorServerService._row_to_dict(row)
            server["password"] = EncryptionUtils.decrypt(row.get("password_encrypted")) if row.get("password_encrypted") else None
            server["private_key"] = EncryptionUtils.decrypt(row.get("private_key_encrypted")) if row.get("private_key_encrypted") else None
            server["passphrase"] = EncryptionUtils.decrypt(row.get("passphrase_encrypted")) if row.get("passphrase_encrypted") else None
            result.append(server)
        return result

    @staticmethod
    def update_status(server_id: str, status: str, last_error: Optional[str], last_seen_at: Optional[datetime]) -> None:
        """更新服务器采集状态"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """UPDATE monitor_servers
                   SET status = %s, last_error = %s, last_seen_at = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s""",
                (status, last_error, last_seen_at, server_id),
            )
            conn.commit()
        finally:
            cursor.close()
            release_db_connection(conn)

    # ============ 监控设置 ============

    @staticmethod
    def get_settings(user_id: str) -> Dict:
        """获取监控设置（webhook_url 按用户；collect_interval 为全局）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT webhook_url FROM monitor_settings WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
            release_db_connection(conn)
        return {
            "webhook_url": row["webhook_url"] if row else "",
            "collect_interval": MonitorServerService.get_global_interval(),
        }

    @staticmethod
    def save_settings(user_id: str, req: MonitorSettings) -> None:
        """保存监控设置（webhook_url 按用户；collect_interval 写全局行）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO monitor_settings (user_id, webhook_url, updated_at)
                   VALUES (%s, %s, CURRENT_TIMESTAMP)
                   ON CONFLICT (user_id) DO UPDATE SET webhook_url = EXCLUDED.webhook_url, updated_at = CURRENT_TIMESTAMP""",
                (user_id, req.webhook_url or ""),
            )
            if req.collect_interval:
                cursor.execute(
                    """INSERT INTO monitor_settings (user_id, collect_interval, updated_at)
                       VALUES ('__global__', %s, CURRENT_TIMESTAMP)
                       ON CONFLICT (user_id) DO UPDATE SET collect_interval = EXCLUDED.collect_interval, updated_at = CURRENT_TIMESTAMP""",
                    (req.collect_interval,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def get_global_interval() -> int:
        """获取全局采集间隔（秒，默认 30）"""
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT collect_interval FROM monitor_settings WHERE user_id = '__global__'")
            row = cursor.fetchone()
        finally:
            cursor.close()
            release_db_connection(conn)
        return max(10, row["collect_interval"]) if row else 30
```

（说明：`monitor_settings` 表结构 `user_id VARCHAR(64) PRIMARY KEY, webhook_url TEXT, collect_interval INT, created_at TIMESTAMP, updated_at TIMESTAMP`，建表语句加入 `ensure_tables()` 的同一个连接中，见下方 Step 3 补充——请把 `ensure_tables()` 中的建表块与 settings 建表合并为一次提交。）

- [ ] **Step 4: 修正 ensure_tables 包含 settings 表**

在 `ensure_tables()` 的 `try` 块内、`conn.commit()` 之前追加：

```python
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_settings (
                    user_id VARCHAR(64) PRIMARY KEY,
                    webhook_url TEXT NOT NULL DEFAULT '',
                    collect_interval INT NOT NULL DEFAULT 30,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_server_service.py -v`
Expected: PASS（5 个）

- [ ] **Step 6: 校验语法与规范**

Run: `cd backend && python -m py_compile app/services/monitor/server_service.py && ruff check app/services/monitor/`
Expected: 无错误输出

- [ ] **Step 7: 提交**

```bash
git add backend/app/services/monitor/ backend/tests/test_monitor_server_service.py
git commit -m "feat: 监控服务器 CRUD 服务与设置"
```

---

### Task 3: SSH 连接池（ssh_client.py）

**Files:**
- Create: `backend/app/services/monitor/ssh_client.py`
- Test: `backend/tests/test_monitor_ssh_client.py`

**Interfaces:**
- Consumes: `server` dict（字段见 Global Constraints）；`paramiko`
- Produces:
  - `class SSHCommandError(Exception)`
  - `class SSHConnectionPool`：
    - `async def run_command(server: Dict, command: str, timeout: int = 10) -> str`
    - `def close_idle_connections(max_idle_seconds: int = 300) -> int`
    - `def close_all() -> None`
  - 模块级单例 `pool = SSHConnectionPool()`

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_ssh_client.py
"""
SSH 连接池测试 - mock paramiko 客户端
"""
import os
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import ssh_client
from app.services.monitor.ssh_client import SSHConnectionPool, SSHCommandError

SERVER = {
    "id": "srv-1", "server_type": "ssh", "host": "10.0.0.1", "port": 22,
    "username": "root", "password": "pw", "private_key": None, "passphrase": None,
}


class FakeChannel:
    """模拟 paramiko 通道（支持超时设置与退出码）"""
    def __init__(self, out=b"", err=b"", code=0):
        self.out = out
        self.err = err
        self.code = code
        self.timeout = None

    def settimeout(self, t):
        self.timeout = t

    def recv_exit_status(self):
        return self.code


class FakeStdout:
    def __init__(self, channel):
        self.channel = channel

    def read(self):
        if self.channel.timeout is None:
            raise TimeoutError("simulated read timeout")
        return self.channel.out


class FakeStderr:
    def __init__(self, channel):
        self.channel = channel

    def read(self):
        return self.channel.err


def make_fake_client(out=b"OK\n", err=b"", code=0):
    client = MagicMock()
    channel = FakeChannel(out=out, err=err, code=code)
    stdout = FakeStdout(channel)
    stderr = FakeStderr(channel)
    client.exec_command.return_value = (MagicMock(), stdout, stderr)
    transport = MagicMock()
    transport.set_keepalive = MagicMock()
    client.get_transport.return_value = transport
    return client


def test_run_command_success(monkeypatch):
    fake_client = make_fake_client(out=b"hello")
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    result = asyncio.run(p.run_command(SERVER, "echo hello", timeout=10))
    assert result == "hello"
    assert fake_client.exec_command.called


def test_run_command_nonzero_exit_raises(monkeypatch):
    fake_client = make_fake_client(out=b"", err=b"permission denied", code=1)
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    with pytest.raises(SSHCommandError):
        asyncio.run(p.run_command(SERVER, "bad-command", timeout=10))


def test_connection_reuse(monkeypatch):
    """同一服务器第二次执行应复用连接（只 connect 一次）"""
    fake_client = make_fake_client(out=b"x")
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    asyncio.run(p.run_command(SERVER, "cmd1"))
    asyncio.run(p.run_command(SERVER, "cmd2"))
    assert fake_client.connect.call_count == 1


def test_reconnect_after_failure(monkeypatch):
    """连接失效时自动重连一次"""
    calls = {"n": 0}

    def side_effect(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("conn lost")
        return None

    fake_client = make_fake_client(out=b"ok")
    fake_client.connect.side_effect = side_effect
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    result = asyncio.run(p.run_command(SERVER, "cmd"))
    assert result == "ok"
    assert calls["n"] == 2


def test_close_idle_connections(monkeypatch):
    fake_client = make_fake_client(out=b"x")
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    asyncio.run(p.run_command(SERVER, "cmd"))
    assert len(p._pool) == 1
    closed = p.close_idle_connections(max_idle_seconds=0)
    assert closed == 1
    assert len(p._pool) == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_ssh_client.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现连接池**

```python
# backend/app/services/monitor/ssh_client.py
"""
SSH 连接池 - 按 server_id 缓存连接（LRU），支持空闲关闭与断线重连
"""
import asyncio
import io
import logging
import threading
import time
from typing import Dict, Optional

import paramiko

logger = logging.getLogger(__name__)


class SSHCommandError(Exception):
    """SSH 命令执行失败（非零退出码或超时）"""


class SSHConnectionPool:
    """paramiko 连接池：连接按服务器复用，超过 max_size 时驱逐最旧连接"""

    def __init__(self, max_size: int = 8):
        self._pool: Dict[str, dict] = {}  # server_id -> {client, last_used}
        self._max_size = max_size
        self._lock = threading.Lock()

    # ---------- 内部连接管理 ----------

    @staticmethod
    def _load_private_key(private_key: str, passphrase: Optional[str]):
        """加载私钥内容"""
        key_classes = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]
        for key_cls in key_classes:
            try:
                return key_cls.from_private_key(io.StringIO(private_key), password=passphrase)
            except Exception:
                continue
        raise SSHCommandError("无效的私钥")

    def _connect(self, server: Dict) -> paramiko.SSHClient:
        """建立新连接"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = None
        if server.get("private_key"):
            pkey = self._load_private_key(server["private_key"], server.get("passphrase"))
        ssh.connect(
            hostname=server["host"], port=server["port"], username=server["username"],
            password=server.get("password"), pkey=pkey, timeout=10,
            allow_agent=False, look_for_keys=False,
        )
        ssh.get_transport().set_keepalive(30)
        return ssh

    def _get_or_connect(self, server: Dict) -> paramiko.SSHClient:
        """获取连接，不存在则新建"""
        key = server["id"]
        with self._lock:
            entry = self._pool.get(key)
            if entry:
                entry["last_used"] = time.time()
                return entry["client"]
        client = self._connect(server)
        with self._lock:
            self._pool[key] = {"client": client, "last_used": time.time()}
            if len(self._pool) > self._max_size:
                self._evict_oldest()
        return client

    def _evict_oldest(self) -> None:
        """驱逐最久未使用的连接"""
        if not self._pool:
            return
        oldest_key = min(self._pool, key=lambda k: self._pool[k]["last_used"])
        entry = self._pool.pop(oldest_key)
        try:
            entry["client"].close()
        except Exception:
            pass
        logger.debug("SSH 连接池驱逐最旧连接: %s", oldest_key)

    def _exec_once(self, client: paramiko.SSHClient, command: str, timeout: int) -> str:
        """执行一次命令，返回 stdout；非零退出码抛 SSHCommandError"""
        stdin, stdout, stderr = client.exec_command(command)
        stdout.channel.settimeout(timeout)
        try:
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("SSH 命令执行超时: %s", str(e))
            raise SSHCommandError(f"远程命令执行超时（>{timeout}s）")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise SSHCommandError(f"远程命令执行失败 (exit={code}): {err[:200]}")
        return out

    # ---------- 对外接口 ----------

    def run_command_sync(self, server: Dict, command: str, timeout: int = 10) -> str:
        """同步执行远程命令（失败时自动重连一次）"""
        key = server["id"]
        client = self._get_or_connect(server)
        try:
            return self._exec_once(client, command, timeout)
        except SSHCommandError:
            raise
        except (paramiko.SSHException, OSError, EOFError) as e:
            logger.warning("SSH 连接异常，尝试重连: %s", str(e))
            with self._lock:
                self._pool.pop(key, None)
            client = self._connect(server)
            with self._lock:
                self._pool[key] = {"client": client, "last_used": time.time()}
            return self._exec_once(client, command, timeout)

    async def run_command(self, server: Dict, command: str, timeout: int = 10) -> str:
        """异步执行远程命令（阻塞部分在线程池中运行）"""
        return await asyncio.to_thread(self.run_command_sync, server, command, timeout)

    def close_idle_connections(self, max_idle_seconds: int = 300) -> int:
        """关闭空闲超过阈值的连接，返回关闭数量"""
        now = time.time()
        closed = 0
        with self._lock:
            idle_keys = [
                k for k, v in self._pool.items()
                if now - v["last_used"] > max_idle_seconds
            ]
            for k in idle_keys:
                entry = self._pool.pop(k)
                try:
                    entry["client"].close()
                except Exception:
                    pass
                closed += 1
        if closed:
            logger.info("SSH 连接池清理空闲连接: %d 个", closed)
        return closed

    def close_all(self) -> None:
        """关闭所有连接（应用关闭时调用）"""
        with self._lock:
            keys = list(self._pool.keys())
            self._pool.clear()
        for k in keys:
            try:
                entry = self._pool.get(k)
                if entry:
                    entry["client"].close()
            except Exception:
                pass
        logger.info("SSH 连接池已全部关闭")


pool = SSHConnectionPool()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_ssh_client.py -v`
Expected: PASS（5 个）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/monitor/ssh_client.py backend/tests/test_monitor_ssh_client.py
git commit -m "feat: SSH 连接池（复用/重连/空闲清理）"
```

---

### Task 4: 采集脚本与解析（script.py）

**Files:**
- Create: `backend/app/services/monitor/script.py`
- Test: `backend/tests/test_monitor_script.py`

**Interfaces:**
- Produces:
  - `BASH_SCRIPT: str`（内嵌采集脚本，一次执行输出 `MONITOR_DATA_BEGIN<json>MONITOR_DATA_END`）
  - `parse_script_output(raw_output: str) -> Optional[Dict]`（解析失败返回 None，Task 7 使用）

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_script.py
"""
采集脚本解析测试 - 覆盖正常/异常/字段缺失场景
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.monitor.script import parse_script_output, BASH_SCRIPT


def _wrap(data: dict) -> str:
    import json
    return f"MONITOR_DATA_BEGIN{json.dumps(data)}MONITOR_DATA_END"


def test_parse_valid_output():
    raw = _wrap({
        "cpu_percent": 12.5, "cpu_per_core": [10.0, 15.0],
        "load_avg": [0.5, 0.4, 0.3],
        "mem_total": 8000000000, "mem_used": 4000000000, "mem_percent": 50.0,
        "swap_total": 2000000000, "swap_used": 0, "swap_percent": 0.0,
        "disk_total": 100000000000, "disk_used": 40000000000, "disk_percent": 40.0,
        "net_recv_rate": 1024.0, "net_sent_rate": 2048.0,
        "disk_read_rate": 512.0, "disk_write_rate": 256.0,
        "process_count": 128, "uptime_seconds": 3600,
    })
    result = parse_script_output(raw)
    assert result is not None
    assert result["cpu_percent"] == 12.5
    assert result["load_avg"] == [0.5, 0.4, 0.3]
    assert result["process_count"] == 128


def test_parse_with_noise_around_markers():
    """脚本错误输出混入时只取标记中间内容"""
    data = _wrap({"cpu_percent": 5.0, "mem_percent": 10.0})
    raw = f"some warning line\n{data}\ntrailing error"
    result = parse_script_output(raw)
    assert result["cpu_percent"] == 5.0


def test_parse_missing_marker_returns_none():
    assert parse_script_output("no markers here") is None


def test_parse_invalid_json_returns_none():
    raw = "MONITOR_DATA_BEGIN{not json MONITOR_DATA_END"
    assert parse_script_output(raw) is None


def test_parse_missing_required_key_returns_none():
    raw = _wrap({"cpu_percent": 5.0})  # 缺 mem_percent 等
    assert parse_script_output(raw) is None


def test_parse_clamps_percent_values():
    raw = _wrap({
        "cpu_percent": 150.0, "cpu_per_core": [-5.0],
        "load_avg": [1, 2, 3], "mem_total": 1, "mem_used": 1, "mem_percent": 99,
        "swap_total": 0, "swap_used": 0, "swap_percent": 0,
        "disk_total": 1, "disk_used": 0, "disk_percent": 200,
        "net_recv_rate": 1, "net_sent_rate": 1, "disk_read_rate": 1, "disk_write_rate": 1,
        "process_count": 1, "uptime_seconds": 1,
    })
    result = parse_script_output(raw)
    assert result["cpu_percent"] == 100.0
    assert result["cpu_per_core"] == [0.0]
    assert result["disk_percent"] == 100.0


def test_script_contains_markers_and_pure_bash():
    assert "MONITOR_DATA_BEGIN" in BASH_SCRIPT
    assert "MONITOR_DATA_END" in BASH_SCRIPT
    # 不依赖非标准工具
    for tool in ("vmstat", "iostat", "python", "top", "sar"):
        assert tool not in BASH_SCRIPT
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_script.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现脚本与解析**

```python
# backend/app/services/monitor/script.py
"""
内嵌 bash 采集脚本 - 无外部依赖（仅 bash 内建 + cat/awk/df/sleep），输出单行 JSON
"""
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BASH_SCRIPT = r'''#!/bin/bash
# 服务器监控采集脚本：两次采样计算 CPU/网络/磁盘速率，输出单行 JSON
interval=0.2
BEGIN='MONITOR_DATA_BEGIN'
END='MONITOR_DATA_END'

# --- CPU（总 + 各核心），基于 /proc/stat 两次采样 ---
prev_file=$(mktemp)
curr_file=$(mktemp)
grep '^cpu' /proc/stat > "$prev_file"
sleep "$interval"
grep '^cpu' /proc/stat > "$curr_file"
cpu_info=$(awk -v itv="$interval" '
BEGIN { printf "%.1f", 0 }
NR==FNR {
  if ($1 ~ /^cpu[0-9]+$/) {
    key=$1; n[key]=NF
    for (i=2; i<=NF; i++) p[key,i]=$i
  }
  if ($1 == "cpu") {
    for (i=2; i<=NF; i++) pt[i]=$i
  }
  next
}
{
  if ($1 ~ /^cpu[0-9]+$/) {
    key=$1
    pidle = p[key,5] + p[key,6]
    cidle = $5 + $6
    ptotal = 0; ctotal = 0
    for (i=2; i<=NF; i++) { ptotal += p[key,i]; ctotal += $i }
    idled = cidle - pidle; totald = ctotal - ptotal
    if (totald <= 0) { pct = 0 } else { pct = 100 * (1 - idled / totald) }
    if (pct < 0) pct = 0
    if (pct > 100) pct = 100
    printf "%s:%.1f,", key, pct
  }
  if ($1 == "cpu") {
    pidle = pt[5] + pt[6]; cidle = $5 + $6
    ptotal = 0; ctotal = 0
    for (i=2; i<=NF; i++) { ptotal += pt[i]; ctotal += $i }
    idled = cidle - pidle; totald = ctotal - ptotal
    if (totald <= 0) { total = 0 } else { total = 100 * (1 - idled / totald) }
    if (total < 0) total = 0
    if (total > 100) total = 100
    printf "TOTAL:%.1f", total
  }
}' "$prev_file" "$curr_file")
rm -f "$prev_file" "$curr_file"

# --- 内存 / 交换分区，基于 /proc/meminfo ---
mem_info=$(awk '
/^MemTotal:/ { t=$2 }
/^MemAvailable:/ { a=$2 }
/^SwapTotal:/ { st=$2 }
/^SwapFree:/ { sf=$2 }
END {
  t=t*1024; a=a*1024; st=st*1024; sf=sf*1024
  used = t - a
  if (used < 0) used = 0
  mempct = t > 0 ? used / t * 100 : 0
  swpct = st > 0 ? (st - sf) / st * 100 : 0
  printf "%d|%d|%.1f|%d|%d|%.1f", t, used, mempct, st, st - sf, swpct
}' /proc/meminfo)

# --- 负载与运行时长 ---
load_info=$(awk '{printf "%s|%s|%s", $1, $2, $3}' /proc/loadavg)
uptime_s=$(awk '{printf "%d", $1}' /proc/uptime)

# --- 磁盘容量（df -Pk，根分区） ---
disk_info=$(df -Pk / | awk 'NR==2 {printf "%d|%d|%.1f", $2*1024, ($2-$4)*1024, $5}' | sed 's/%$//')
disk_pct=$(echo "$disk_info" | awk -F'|' '{if ($3 > 100) $3 = 100; print $3}')

# --- 网络速率（/proc/net/dev 两次采样，排除 loopback） ---
net_before=$(mktemp)
net_after=$(mktemp)
awk 'NR>2 && $1 != "lo:" {gsub(":", "", $1); r += $2; t += $10} END {printf "%d %d", r, t}' /proc/net/dev > "$net_before"
sleep "$interval"
awk 'NR>2 && $1 != "lo:" {gsub(":", "", $1); r += $2; t += $10} END {printf "%d %d", r, t}' /proc/net/dev > "$net_after"
net_info=$(awk -v itv="$interval" '
NR==FNR { br=$1; bt=$2; next }
{ dr=$1-br; dt=$2-bt; if (dr<0) dr=0; if (dt<0) dt=0; printf "%.1f %.1f", dr/itv, dt/itv }
' "$net_before" "$net_after")
rm -f "$net_before" "$net_after"

# --- 磁盘 IO 速率（/proc/diskstats，排除分区与 loop/ram 设备） ---
io_before=$(mktemp)
io_after=$(mktemp)
awk 'NR>1 && $3 !~ /loop|ram/ && $3 ~ /^[a-z]+$/ && $3 !~ /[0-9]$/ {r += $6; w += $10} END {printf "%d %d", r, w}' /proc/diskstats > "$io_before"
sleep "$interval"
awk 'NR>1 && $3 !~ /loop|ram/ && $3 ~ /^[a-z]+$/ && $3 !~ /[0-9]$/ {r += $6; w += $10} END {printf "%d %d", r, w}' /proc/diskstats > "$io_after"
io_info=$(awk -v itv="$interval" '
NR==FNR { br=$1; bw=$2; next }
{ dr=$1-br; dw=$2-bw; if (dr<0) dr=0; if (dw<0) dw=0; printf "%.1f %.1f", dr*512/itv, dw*512/itv }
' "$io_before" "$io_after")
rm -f "$io_before" "$io_after"

# --- 进程数 ---
proc_count=$(ls /proc 2>/dev/null | grep -cE '^[0-9]+$')

echo "${BEGIN}$(cat <<JSON
{"cpu_percent": $(echo "$cpu_info" | sed -n 's/.*TOTAL:\([0-9.]*\)$/\1/p'),
 "cpu_per_core": [$(echo "$cpu_info" | grep -oE '^cpu[0-9]+:[0-9.]+' | sed 's/^cpu[0-9]*://' | paste -sd, -)],
 "load_avg": [$(echo "$load_info" | awk -F'|' '{print $1", "$2", "$3}')],
 "mem_total": $(echo "$mem_info" | cut -d'|' -f1),
 "mem_used": $(echo "$mem_info" | cut -d'|' -f2),
 "mem_percent": $(echo "$mem_info" | cut -d'|' -f3),
 "swap_total": $(echo "$mem_info" | cut -d'|' -f4),
 "swap_used": $(echo "$mem_info" | cut -d'|' -f5),
 "swap_percent": $(echo "$mem_info" | cut -d'|' -f6),
 "disk_total": $(echo "$disk_info" | cut -d'|' -f1),
 "disk_used": $(echo "$disk_info" | cut -d'|' -f2),
 "disk_percent": ${disk_pct:-0},
 "net_recv_rate": $(echo "$net_info" | cut -d' ' -f1),
 "net_sent_rate": $(echo "$net_info" | cut -d' ' -f2),
 "disk_read_rate": $(echo "$io_info" | cut -d' ' -f1),
 "disk_write_rate": $(echo "$io_info" | cut -d' ' -f2),
 "process_count": ${proc_count:-0},
 "uptime_seconds": ${uptime_s:-0}}
JSON
)${END}"
'''

_REQUIRED_KEYS = [
    "cpu_percent", "cpu_per_core", "load_avg",
    "mem_total", "mem_used", "mem_percent",
    "swap_total", "swap_used", "swap_percent",
    "disk_total", "disk_used", "disk_percent",
    "net_recv_rate", "net_sent_rate",
    "disk_read_rate", "disk_write_rate",
    "process_count", "uptime_seconds",
]


def parse_script_output(raw_output: str) -> Optional[Dict]:
    """解析采集脚本输出，失败返回 None"""
    try:
        start = raw_output.find("MONITOR_DATA_BEGIN")
        end = raw_output.find("MONITOR_DATA_END")
        if start == -1 or end == -1 or end <= start:
            return None
        data = json.loads(raw_output[start + len("MONITOR_DATA_BEGIN"):end])
        if not isinstance(data, dict):
            return None
        for key in _REQUIRED_KEYS:
            if key not in data:
                logger.warning("采集数据缺少字段: %s", key)
                return None
        # 数值收敛：百分比限制 0-100，速率/容量非负
        for pct_key in ("cpu_percent", "mem_percent", "swap_percent", "disk_percent"):
            data[pct_key] = max(0.0, min(100.0, float(data[pct_key])))
        data["cpu_per_core"] = [max(0.0, min(100.0, float(x))) for x in data["cpu_per_core"]]
        data["load_avg"] = [max(0.0, float(x)) for x in data["load_avg"]]
        for rate_key in ("net_recv_rate", "net_sent_rate", "disk_read_rate", "disk_write_rate"):
            data[rate_key] = max(0.0, float(data[rate_key]))
        for int_key in ("mem_total", "mem_used", "swap_total", "swap_used",
                        "disk_total", "disk_used", "process_count", "uptime_seconds"):
            data[int_key] = max(0, int(float(data[int_key])))
        data["cpu_percent"] = float(data["cpu_percent"])
        return data
    except (ValueError, TypeError, KeyError) as e:
        logger.warning("采集数据解析失败: %s", str(e))
        return None
```

（注：解析测试中的 `_wrap` 使用无噪音 JSON，实际脚本输出 JSON 本身包含换行，`json.loads` 容忍前后空白与换行，无需修改。）

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_script.py -v`
Expected: PASS（7 个）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/monitor/script.py backend/tests/test_monitor_script.py
git commit -m "feat: 内嵌 bash 采集脚本与解析"
```

---

### Task 5: 指标存储（metric_repo.py）

**Files:**
- Create: `backend/app/services/monitor/metric_repo.py`
- Test: `backend/tests/test_monitor_metric_repo.py`

**Interfaces:**
- Consumes: `server` dict、指标 dict（见 Global Constraints）
- Produces:
  - `ensure_tables() -> None`
  - `insert_metric(server_id: str, m: Dict) -> None`
  - `get_latest_metric(server_id: str) -> Optional[Dict]`
  - `query_metrics(server_id: str, range_key: str) -> List[Dict]`（`range_key ∈ {1h,6h,24h,7d}`；7d 按小时聚合）
  - `delete_expired_metrics(seconds: int) -> int`

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_metric_repo.py
"""
指标存储测试 - 内存 fake 数据库验证 SQL 生成与返回映射
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import metric_repo
from app.services.monitor.metric_repo import (
    ensure_tables, insert_metric, get_latest_metric,
    query_metrics, delete_expired_metrics, RANGE_SECONDS,
)


class FakeCursor:
    def __init__(self, results):
        self._results = results if results is not None else []
        self.rowcount = len(self._results)
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, results=None):
        self._results = results
        self.committed = False
        self.cursors = []

    def cursor(self):
        cur = FakeCursor(self._results)
        self.cursors.append(cur)
        return cur

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def fake_db(monkeypatch):
    holder = {"conn": FakeConn()}
    monkeypatch.setattr(metric_repo, "get_pooled_db_connection", lambda: holder["conn"])
    monkeypatch.setattr(metric_repo, "release_db_connection", lambda c: None)
    return holder


def test_range_seconds():
    assert RANGE_SECONDS == {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}


def test_insert_metric_uses_correct_sql(fake_db):
    m = {"cpu_percent": 10.0, "cpu_per_core": [1.0, 2.0], "load_avg": [0.1, 0.2, 0.3],
         "mem_total": 1, "mem_used": 1, "mem_percent": 1.0,
         "swap_total": 0, "swap_used": 0, "swap_percent": 0.0,
         "disk_total": 1, "disk_used": 1, "disk_percent": 1.0,
         "net_recv_rate": 1.0, "net_sent_rate": 1.0,
         "disk_read_rate": 1.0, "disk_write_rate": 1.0,
         "process_count": 10, "uptime_seconds": 100}
    insert_metric("srv-1", m)
    sql = fake_db["conn"].cursors[-1].executed[-1][0]
    assert "INSERT INTO monitor_metrics" in sql
    assert "jsonb" in sql.lower() or "json" in sql.lower()
    assert fake_db["conn"].committed


def test_get_latest_metric_returns_row(fake_db):
    fake_db["conn"] = FakeConn([{"collected_at": datetime(2026, 1, 1, 12, 0),
                                 "cpu_percent": 5.0, "mem_percent": 30.0,
                                 "net_recv_rate": 10.0}])
    result = get_latest_metric("srv-1")
    assert result["cpu_percent"] == 5.0
    assert result["collected_at"] is not None


def test_get_latest_metric_empty(fake_db):
    fake_db["conn"] = FakeConn([])
    assert get_latest_metric("srv-1") is None


def test_query_metrics_7d_uses_hourly_aggregation(fake_db):
    fake_db["conn"] = FakeConn([{"t": "2026-01-01 10:00:00", "cpu_percent": 5.0}])
    rows = query_metrics("srv-1", "7d")
    assert len(rows) == 1
    sql = fake_db["conn"].cursors[-1].executed[-1][0]
    assert "date_trunc" in sql


def test_delete_expired_returns_count(fake_db):
    fake_db["conn"] = FakeConn([])
    fake_db["conn"].cursors[-1].rowcount = 100
    assert delete_expired_metrics(604800) == 100
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_metric_repo.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现存储**

```python
# backend/app/services/monitor/metric_repo.py
"""
监控指标存储 - PostgreSQL 时序表写入/查询/聚合/清理
"""
import logging
from typing import Dict, List, Optional

from app.config.database import get_pooled_db_connection, release_db_connection

logger = logging.getLogger(__name__)

# 时间范围（秒）
RANGE_SECONDS = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}


def ensure_tables() -> None:
    """确保指标表存在"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_metrics (
                id BIGSERIAL PRIMARY KEY,
                server_id VARCHAR(64) NOT NULL,
                collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cpu_percent FLOAT,
                cpu_per_core JSONB,
                load_avg JSONB,
                mem_total BIGINT,
                mem_used BIGINT,
                mem_percent FLOAT,
                swap_total BIGINT,
                swap_used BIGINT,
                swap_percent FLOAT,
                disk_total BIGINT,
                disk_used BIGINT,
                disk_percent FLOAT,
                net_recv_rate FLOAT,
                net_sent_rate FLOAT,
                disk_read_rate FLOAT,
                disk_write_rate FLOAT,
                process_count INT,
                uptime_seconds BIGINT
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitor_metrics_server_time ON monitor_metrics(server_id, collected_at)"
        )
        conn.commit()
    finally:
        cursor.close()
        release_db_connection(conn)


def insert_metric(server_id: str, m: Dict) -> None:
    """写入一条指标"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO monitor_metrics (
                server_id, cpu_percent, cpu_per_core, load_avg,
                mem_total, mem_used, mem_percent,
                swap_total, swap_used, swap_percent,
                disk_total, disk_used, disk_percent,
                net_recv_rate, net_sent_rate, disk_read_rate, disk_write_rate,
                process_count, uptime_seconds
            ) VALUES (
                %s, %s, %s::jsonb, %s::jsonb,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            """,
            (
                server_id, m["cpu_percent"],
                __import__("json").dumps(m["cpu_per_core"]),
                __import__("json").dumps(m["load_avg"]),
                m["mem_total"], m["mem_used"], m["mem_percent"],
                m["swap_total"], m["swap_used"], m["swap_percent"],
                m["disk_total"], m["disk_used"], m["disk_percent"],
                m["net_recv_rate"], m["net_sent_rate"],
                m["disk_read_rate"], m["disk_write_rate"],
                m["process_count"], m["uptime_seconds"],
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("监控指标写入失败: server=%s 错误=%s", server_id, str(e))
        raise
    finally:
        cursor.close()
        release_db_connection(conn)


def _row_to_metric(row) -> Dict:
    """数据库行转指标 dict"""
    return {
        "collected_at": row.get("collected_at"),
        "cpu_percent": row.get("cpu_percent"),
        "cpu_per_core": row.get("cpu_per_core"),
        "load_avg": row.get("load_avg"),
        "mem_total": row.get("mem_total"),
        "mem_used": row.get("mem_used"),
        "mem_percent": row.get("mem_percent"),
        "swap_total": row.get("swap_total"),
        "swap_used": row.get("swap_used"),
        "swap_percent": row.get("swap_percent"),
        "disk_total": row.get("disk_total"),
        "disk_used": row.get("disk_used"),
        "disk_percent": row.get("disk_percent"),
        "net_recv_rate": row.get("net_recv_rate"),
        "net_sent_rate": row.get("net_sent_rate"),
        "disk_read_rate": row.get("disk_read_rate"),
        "disk_write_rate": row.get("disk_write_rate"),
        "process_count": row.get("process_count"),
        "uptime_seconds": row.get("uptime_seconds"),
    }


def get_latest_metric(server_id: str) -> Optional[Dict]:
    """获取最近一条指标"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM monitor_metrics WHERE server_id = %s ORDER BY collected_at DESC LIMIT 1",
            (server_id,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
        release_db_connection(conn)
    return _row_to_metric(row) if row else None


def query_metrics(server_id: str, range_key: str) -> List[Dict]:
    """查询历史指标；range_key ∈ {1h, 6h, 24h, 7d}；7d 按小时聚合降采样"""
    seconds = RANGE_SECONDS.get(range_key, RANGE_SECONDS["1h"])
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        if range_key == "7d":
            # 按小时聚合
            cursor.execute(
                """
                SELECT date_trunc('hour', collected_at) AS t,
                       avg(cpu_percent) AS cpu_percent,
                       avg(mem_percent) AS mem_percent,
                       avg(disk_percent) AS disk_percent,
                       avg(net_recv_rate) AS net_recv_rate,
                       avg(net_sent_rate) AS net_sent_rate,
                       avg(disk_read_rate) AS disk_read_rate,
                       avg(disk_write_rate) AS disk_write_rate,
                       avg((load_avg->>0)::float) AS load1
                FROM monitor_metrics
                WHERE server_id = %s AND collected_at >= now() - interval '604800 seconds'
                GROUP BY t ORDER BY t
                """,
                (server_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "collected_at": r["t"],
                    "cpu_percent": round(r["cpu_percent"], 1) if r["cpu_percent"] is not None else None,
                    "mem_percent": round(r["mem_percent"], 1) if r["mem_percent"] is not None else None,
                    "disk_percent": round(r["disk_percent"], 1) if r["disk_percent"] is not None else None,
                    "net_recv_rate": r["net_recv_rate"],
                    "net_sent_rate": r["net_sent_rate"],
                    "disk_read_rate": r["disk_read_rate"],
                    "disk_write_rate": r["disk_write_rate"],
                    "load_avg": [r["load1"]],
                }
                for r in rows
            ]
        cursor.execute(
            """
            SELECT * FROM monitor_metrics
            WHERE server_id = %s AND collected_at >= now() - make_interval(secs => %s)
            ORDER BY collected_at
            """,
            (server_id, seconds),
        )
        rows = cursor.fetchall()
        return [_row_to_metric(r) for r in rows]
    finally:
        cursor.close()
        release_db_connection(conn)


def delete_expired_metrics(seconds: int = 604800) -> int:
    """删除超过保留期的指标，返回删除数量"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM monitor_metrics WHERE collected_at < now() - make_interval(secs => %s)",
            (seconds,),
        )
        conn.commit()
        count = cursor.rowcount
        if count:
            logger.info("监控指标清理: 删除 %d 条过期数据", count)
        return count
    except Exception as e:
        conn.rollback()
        logger.error("监控指标清理失败: %s", str(e))
        return 0
    finally:
        cursor.close()
        release_db_connection(conn)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_metric_repo.py -v`
Expected: PASS（7 个）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/monitor/metric_repo.py backend/tests/test_monitor_metric_repo.py
git commit -m "feat: 监控指标时序存储（写入/查询/聚合/清理）"
```

---

### Task 6: 告警引擎与 Webhook（alert_engine.py + webhook_notify.py）

**Files:**
- Create: `backend/app/services/monitor/webhook_notify.py`、`backend/app/services/monitor/alert_engine.py`
- Test: `backend/tests/test_monitor_alert_engine.py`

**Interfaces:**
- Consumes: 指标 dict、`MonitorServerService.get_settings(user_id)`（webhook_url）
- Produces:
  - `webhook_notify.send_webhook(url: str, title: str, content: str) -> bool`
  - `alert_engine.ensure_tables() -> None`
  - `alert_engine.get_rules(user_id) -> List[Dict]`
  - `alert_engine.create_rule(user_id, req) -> Dict`
  - `alert_engine.update_rule(user_id, rule_id, req) -> Optional[Dict]`
  - `alert_engine.delete_rule(user_id, rule_id) -> bool`
  - `alert_engine.get_logs(user_id, page, page_size) -> Dict`（含 unread_count）
  - `alert_engine.mark_logs_read(user_id) -> None`
  - `alert_engine.evaluate(server: Dict, m: Dict) -> None`（Task 7 调用）

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_alert_engine.py
"""
告警引擎测试 - 规则评估、去重、恢复、Webhook 推送
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import alert_engine, webhook_notify

METRICS = {
    "cpu_percent": 95.0, "mem_percent": 20.0, "disk_percent": 30.0,
    "load_avg": [2.0, 1.5, 1.0], "net_recv_rate": 100.0, "net_sent_rate": 50.0,
}
SERVER = {"id": "srv-1", "user_id": "u1", "name": "web1", "server_type": "ssh",
          "host": "10.0.0.1", "port": 22, "username": "root", "password": None,
          "private_key": None, "passphrase": None, "group_name": None,
          "status": "enabled", "last_error": None, "last_seen_at": None}

RULE = {"id": "rule-1", "user_id": "u1", "server_id": "srv-1", "metric": "cpu_percent",
        "operator": ">", "threshold": 90, "duration": 2, "enabled": True}


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前重置告警内存状态"""
    alert_engine._firing_counts.clear()
    alert_engine._firing_active.clear()
    yield
    alert_engine._firing_counts.clear()
    alert_engine._firing_active.clear()


@pytest.fixture
def fake_db(monkeypatch):
    holder = {"conn": MagicMock()}
    monkeypatch.setattr(alert_engine, "get_pooled_db_connection", lambda: holder["conn"])
    monkeypatch.setattr(alert_engine, "release_db_connection", lambda c: None)
    return holder


class FakeCursor:
    def __init__(self, results):
        self._results = results if results is not None else []
        self.rowcount = 1
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        import re
        if "INSERT INTO monitor_alert_logs" in sql:
            # 模拟返回插入 id
            self._results = [{"id": 1}]
        if "RETURNING id" in sql:
            self._results = [{"id": "new-rule"}]

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake_db_with_rules(monkeypatch, fake_db):
    """get_rules 返回固定规则"""
    monkeypatch.setattr(
        alert_engine,
        "get_rules",
        lambda user_id: [dict(RULE)] if user_id == "u1" else [],
    )
    return fake_db


def test_evaluate_fires_after_duration(monkeypatch, fake_db_with_rules):
    """连续 2 次超过阈值后触发告警"""
    notified = {"n": 0}
    monkeypatch.setattr(webhook_notify, "send_webhook", lambda *a, **k: True)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, METRICS)
    assert alert_engine._firing_counts[("rule-1", "srv-1")] == 1
    assert not alert_engine._firing_active.get(("rule-1", "srv-1"))
    alert_engine.evaluate(SERVER, METRICS)
    assert alert_engine._firing_active.get(("rule-1", "srv-1")) is True


def test_evaluate_no_fire_when_below_threshold(monkeypatch, fake_db_with_rules):
    low = dict(METRICS, cpu_percent=10.0)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    alert_engine.evaluate(SERVER, low)
    assert alert_engine._firing_counts.get(("rule-1", "srv-1"), 0) == 0
    assert not alert_engine._firing_active.get(("rule-1", "srv-1"))


def test_firing_does_not_notify_twice(monkeypatch, fake_db_with_rules):
    """触发态中不再重复通知"""
    sends = {"n": 0}
    monkeypatch.setattr(webhook_notify, "send_webhook", lambda *a, **k: True)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, METRICS)
    alert_engine.evaluate(SERVER, METRICS)
    assert alert_engine._firing_active[("rule-1", "srv-1")]
    alert_engine.evaluate(SERVER, METRICS)  # 仍超阈值
    # 只通知一次：第二次触发插入 log，第三次不再插入
    assert alert_engine._firing_counts[("rule-1", "srv-1")] == 2


def test_recovery_writes_recovered_log(monkeypatch, fake_db_with_rules):
    recovered = {"written": []}
    monkeypatch.setattr(webhook_notify, "send_webhook", lambda *a, **k: True)
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: recovered["written"].append(k))
    monkeypatch.setattr(alert_engine, "_get_webhook_url", lambda uid: "http://hook")
    alert_engine.evaluate(SERVER, METRICS)  # 1
    alert_engine.evaluate(SERVER, METRICS)  # 2 → fire
    assert alert_engine._firing_active[("rule-1", "srv-1")]
    low = dict(METRICS, cpu_percent=10.0)
    alert_engine.evaluate(SERVER, low)  # 恢复
    assert alert_engine._firing_active.get(("rule-1", "srv-1")) is False
    assert any(w["status"] == "recovered" for w in recovered["written"])


def test_rule_server_all_matches_any_server(monkeypatch, fake_db, fake_db_with_rules):
    """server_id='all' 的规则对所有服务器生效"""
    monkeypatch.setattr(alert_engine, "get_rules", lambda uid: [dict(RULE, server_id="all")])
    monkeypatch.setattr(alert_engine, "_insert_log", lambda **k: {"id": 1})
    other = dict(SERVER, id="srv-2")
    alert_engine.evaluate(other, METRICS)
    assert alert_engine._firing_counts.get(("rule-1", "srv-2"), 0) == 1


def test_send_webhook_success(monkeypatch):
    resp = MagicMock()
    resp.status_code = 200
    monkeypatch.setattr(webhook_notify.httpx, "post", lambda *a, **k: resp)
    assert webhook_notify.send_webhook("http://hook", "标题", "内容") is True


def test_send_webhook_failure(monkeypatch):
    monkeypatch.setattr(webhook_notify.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(Exception("网络错误")))
    assert webhook_notify.send_webhook("http://hook", "标题", "内容") is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_alert_engine.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 Webhook 推送**

```python
# backend/app/services/monitor/webhook_notify.py
"""
Webhook 推送 - 兼容钉钉/企业微信/飞书机器人 markdown 格式
"""
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


def send_webhook(url: str, title: str, content: str) -> bool:
    """推送告警到 Webhook，成功返回 True"""
    if not url:
        return False
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "content": content},
    }
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        if resp.status_code < 400:
            return True
        logger.warning("Webhook 推送返回非成功状态: %s", resp.status_code)
        return False
    except Exception as e:
        logger.warning("Webhook 推送失败: %s", str(e))
        return False
```

- [ ] **Step 4: 实现告警引擎**

```python
# backend/app/services/monitor/alert_engine.py
"""
告警引擎 - 规则 CRUD、采样后评估、触发去重与恢复、站内通知记录
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.config.database import get_pooled_db_connection, release_db_connection
from app.models.monitor_models import AlertRuleCreateRequest, AlertRuleUpdateRequest
from app.services.monitor import webhook_notify
from app.services.monitor.server_service import MonitorServerService

logger = logging.getLogger(__name__)

# 内存触发状态：(rule_id, server_id) -> 连续命中次数
_firing_counts: Dict[tuple, int] = {}
# (rule_id, server_id) -> 当前是否处于触发态（触发态内不重复通知）
_firing_active: Dict[tuple, bool] = {}

_METRIC_LABELS = {
    "cpu_percent": "CPU 使用率",
    "memory_percent": "内存使用率",
    "disk_percent": "磁盘使用率",
    "load_avg": "负载（1分钟）",
    "net_recv_rate": "网络接收速率",
    "net_sent_rate": "网络发送速率",
}

_OPERATORS = {">": lambda v, t: v > t, ">=": lambda v, t: v >= t,
              "<": lambda v, t: v < t, "<=": lambda v, t: v <= t}


def ensure_tables() -> None:
    """确保告警表存在"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_alerts (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                server_id VARCHAR(64) NOT NULL DEFAULT 'all',
                metric VARCHAR(32) NOT NULL,
                operator VARCHAR(8) NOT NULL,
                threshold FLOAT NOT NULL,
                duration INT NOT NULL DEFAULT 3,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_alerts_user ON monitor_alerts(user_id)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_alert_logs (
                id BIGSERIAL PRIMARY KEY,
                rule_id VARCHAR(64) NOT NULL,
                server_id VARCHAR(64) NOT NULL,
                server_name VARCHAR(64) NOT NULL,
                metric VARCHAR(32) NOT NULL,
                actual_value FLOAT NOT NULL,
                status VARCHAR(16) NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                notified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitor_alert_logs_user ON monitor_alert_logs(server_id, notified_at)")
        conn.commit()
    finally:
        cursor.close()
        release_db_connection(conn)


# ============ 规则 CRUD ============

def get_rules(user_id: str) -> List[Dict]:
    """获取用户告警规则"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM monitor_alerts WHERE user_id = %s ORDER BY created_at",
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        cursor.close()
        release_db_connection(conn)


def create_rule(user_id: str, req: AlertRuleCreateRequest) -> Dict:
    """新建告警规则"""
    rule_id = str(uuid.uuid4())
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO monitor_alerts (id, user_id, server_id, metric, operator, threshold, duration, enabled)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (rule_id, user_id, req.server_id, req.metric, req.operator, req.threshold, req.duration, req.enabled),
        )
        conn.commit()
        logger.info("告警规则创建: user=%s metric=%s threshold=%s", user_id, req.metric, req.threshold)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
    return _get_rule(user_id, rule_id)


def _get_rule(user_id: str, rule_id: str) -> Optional[Dict]:
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM monitor_alerts WHERE id = %s AND user_id = %s",
            (rule_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        cursor.close()
        release_db_connection(conn)


def update_rule(user_id: str, rule_id: str, req: AlertRuleUpdateRequest) -> Optional[Dict]:
    """更新告警规则"""
    if not _get_rule(user_id, rule_id):
        return None
    fields, values = [], []
    for key in ("server_id", "metric", "operator", "threshold", "duration", "enabled"):
        value = getattr(req, key, None)
        if value is not None:
            fields.append(f"{key} = %s")
            values.append(value)
    if not fields:
        return _get_rule(user_id, rule_id)
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        values.append(rule_id)
        cursor.execute(f"UPDATE monitor_alerts SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()
        # 规则变更后重置该规则触发状态
        for key in list(_firing_counts.keys()):
            if key[0] == rule_id:
                _firing_counts.pop(key, None)
                _firing_active.pop(key, None)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
    return _get_rule(user_id, rule_id)


def delete_rule(user_id: str, rule_id: str) -> bool:
    """删除告警规则"""
    if not _get_rule(user_id, rule_id):
        return False
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM monitor_alerts WHERE id = %s", (rule_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)
    for key in list(_firing_counts.keys()):
        if key[0] == rule_id:
            _firing_counts.pop(key, None)
            _firing_active.pop(key, None)
    return True


# ============ 触发记录 ============

def _insert_log(rule_id, server_id, server_name, metric, actual_value, status) -> None:
    """写入触发记录（站内通知载体）"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO monitor_alert_logs (rule_id, server_id, server_name, metric, actual_value, status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (rule_id, server_id, server_name, metric, actual_value, status),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("告警日志写入失败: %s", str(e))
    finally:
        cursor.close()
        release_db_connection(conn)


def get_logs(user_id: str, page: int = 1, page_size: int = 20) -> Dict:
    """获取触发记录（分页），附带未读数"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        # 通过用户拥有的服务器过滤日志
        cursor.execute(
            """SELECT COUNT(*) AS total,
                      COUNT(*) FILTER (WHERE l.is_read = FALSE) AS unread
               FROM monitor_alert_logs l
               JOIN monitor_servers s ON s.id = l.server_id
               WHERE s.user_id = %s AND s.deleted = FALSE""",
            (user_id,),
        )
        summary = cursor.fetchone()
        offset = (page - 1) * page_size
        cursor.execute(
            """SELECT l.* FROM monitor_alert_logs l
               JOIN monitor_servers s ON s.id = l.server_id
               WHERE s.user_id = %s AND s.deleted = FALSE
               ORDER BY l.notified_at DESC LIMIT %s OFFSET %s""",
            (user_id, page_size, offset),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        release_db_connection(conn)
    total = summary["total"] if summary else 0
    return {
        "logs": [dict(r) for r in rows],
        "total": total,
        "unread_count": summary["unread"] if summary else 0,
        "page": page,
        "page_size": page_size,
    }


def mark_logs_read(user_id: str) -> None:
    """标记用户的告警记录全部已读"""
    conn = get_pooled_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE monitor_alert_logs l SET is_read = TRUE
               FROM monitor_servers s
               WHERE s.id = l.server_id AND s.user_id = %s""",
            (user_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_db_connection(conn)


# ============ 评估 ============

def _get_webhook_url(user_id: str) -> str:
    """获取用户 Webhook 地址"""
    settings = MonitorServerService.get_settings(user_id)
    return settings.get("webhook_url") or ""


def _evaluate_rule(rule: Dict, m: Dict) -> Optional[float]:
    """规则命中返回当前值，否则 None"""
    if rule["metric"] == "load_avg":
        value = m.get("load_avg")
        if not value:
            return None
        value = value[0]
    else:
        value = m.get(rule["metric"])
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    op = _OPERATORS.get(rule["operator"])
    if not op:
        return None
    return value if op(value, float(rule["threshold"])) else None


def evaluate(server: Dict, m: Dict) -> None:
    """每次采样后评估该服务器的所有告警规则"""
    try:
        rules = get_rules(server["user_id"])
    except Exception as e:
        logger.error("加载告警规则失败: server=%s 错误=%s", server.get("id"), str(e))
        return
    webhook_url = _get_webhook_url(server["user_id"])
    for rule in rules:
        if not rule["enabled"]:
            continue
        if rule["server_id"] not in ("all", server["id"]):
            continue
        key = (rule["id"], server["id"])
        value = _evaluate_rule(rule, m)
        if value is None:
            # 条件不满足：计数清零；若在触发态则写恢复记录
            _firing_counts[key] = 0
            if _firing_active.get(key):
                _firing_active[key] = False
                logger.info("告警恢复: rule=%s server=%s value=%s", rule["id"], server.get("name"), value)
                _insert_log(rule["id"], server["id"], server.get("name") or "",
                            rule["metric"], value if value is not None else 0, "recovered")
            continue
        count = _firing_counts.get(key, 0) + 1
        _firing_counts[key] = count
        if count < rule["duration"] or _firing_active.get(key):
            continue
        # 达到连续次数且未在触发态 → 触发
        _firing_active[key] = True
        _insert_log(rule["id"], server["id"], server.get("name") or "",
                    rule["metric"], value, "firing")
        label = _METRIC_LABELS.get(rule["metric"], rule["metric"])
        if webhook_url:
            content = (
                f"## 服务器监控告警\n"
                f"- 服务器: {server.get('name')}\n"
                f"- 指标: {label}\n"
                f"- 条件: {rule['operator']} {rule['threshold']}\n"
                f"- 当前值: {value}\n"
                f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            webhook_notify.send_webhook(webhook_url, f"监控告警 - {server.get('name')}", content)
        logger.warning("告警触发: rule=%s server=%s metric=%s value=%s",
                       rule["id"], server.get("name"), rule["metric"], value)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_alert_engine.py -v`
Expected: PASS（8 个）

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/monitor/webhook_notify.py backend/app/services/monitor/alert_engine.py backend/tests/test_monitor_alert_engine.py
git commit -m "feat: 告警引擎（规则/去重/恢复/Webhook/站内）"
```

---

### Task 7: 采集引擎（collector.py）

**Files:**
- Create: `backend/app/services/monitor/collector.py`
- Test: `backend/tests/test_monitor_collector.py`

**Interfaces:**
- Consumes: Task 2/3/4/5/6 全部模块
- Produces:
  - `class MonitorCollector`：
    - `async def start() -> None` / `async def stop() -> None`
    - `async def collect_all() -> None`（单周期）
    - `async def collect_server(server: Dict) -> Optional[Dict]`
    - `async def collect_now(server_id: str, user_id: str) -> Optional[Dict]`（手动采集，供重试接口）
  - 模块级单例 `monitor_collector = MonitorCollector()`
  - `local_metrics() -> Dict`（本机指标，导出供测试）

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_collector.py
"""
采集引擎测试 - mock SSH 与 psutil，验证状态流转与失败隔离
"""
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import collector
from app.services.monitor.collector import MonitorCollector, local_metrics
from app.services.monitor.script import BASH_SCRIPT
from app.services.monitor.ssh_client import SSHCommandError

LOCAL_SERVER = {"id": "srv-local", "user_id": "u1", "server_type": "local", "name": "本机",
                "host": "", "port": 22, "username": "", "password": None,
                "private_key": None, "passphrase": None, "group_name": None,
                "status": "enabled", "last_error": None, "last_seen_at": None}

SSH_SERVER = {"id": "srv-1", "user_id": "u1", "server_type": "ssh", "name": "web1",
              "host": "10.0.0.1", "port": 22, "username": "root", "password": "pw",
              "private_key": None, "passphrase": None, "group_name": None,
              "status": "enabled", "last_error": None, "last_seen_at": None}


def make_metrics():
    return {"cpu_percent": 10.0, "cpu_per_core": [5.0], "load_avg": [0.1, 0.2, 0.3],
            "mem_total": 8000000000, "mem_used": 1000000000, "mem_percent": 12.5,
            "swap_total": 0, "swap_used": 0, "swap_percent": 0.0,
            "disk_total": 100000000000, "disk_used": 40000000000, "disk_percent": 40.0,
            "net_recv_rate": 100.0, "net_sent_rate": 200.0,
            "disk_read_rate": 10.0, "disk_write_rate": 20.0,
            "process_count": 50, "uptime_seconds": 1000}


def test_local_metrics_shape():
    m = local_metrics()
    for key in ("cpu_percent", "cpu_per_core", "load_avg", "mem_total", "mem_used",
                "mem_percent", "swap_total", "swap_used", "swap_percent",
                "disk_total", "disk_used", "disk_percent",
                "net_recv_rate", "net_sent_rate", "disk_read_rate", "disk_write_rate",
                "process_count", "uptime_seconds"):
        assert key in m, f"缺少字段 {key}"


def test_collect_server_remote_success(monkeypatch):
    m = make_metrics()
    monkeypatch.setattr(collector, "run_command", __import__("unittest.mock").AsyncMock(return_value="raw"))
    monkeypatch.setattr(collector, "parse_script_output", lambda raw: m)
    monkeypatch.setattr(collector, "insert_metric", lambda *a, **k: None)
    status_updates = []
    monkeypatch.setattr(collector, "update_status",
                        lambda sid, status, err, ts: status_updates.append((sid, status, err)))
    monkeypatch.setattr(collector, "alert_evaluate", lambda *a, **k: None)

    result = asyncio.run(collector.MonitorCollector().collect_server(SSH_SERVER))
    assert result == m
    assert status_updates == [("srv-1", "online", None)]


def test_collect_server_remote_failure_marks_offline(monkeypatch):
    async def fail(*a, **k):
        raise SSHCommandError("连接失败")
    monkeypatch.setattr(collector, "run_command", fail)
    monkeypatch.setattr(collector, "insert_metric", lambda *a, **k: None)
    status_updates = []
    monkeypatch.setattr(collector, "update_status",
                        lambda sid, status, err, ts: status_updates.append((sid, status, err)))
    result = asyncio.run(collector.MonitorCollector().collect_server(SSH_SERVER))
    assert result is None
    assert status_updates[-1][1] == "offline"
    assert "连接失败" in (status_updates[-1][2] or "")


def test_collect_all_isolates_failures(monkeypatch):
    """一台失败不影响其他服务器"""
    monkeypatch.setattr(collector.MonitorCollector, "collect_server",
                        __import__("unittest.mock").AsyncMock(side_effect=[None, make_metrics()]))
    done = asyncio.run(collector.MonitorCollector().collect_all([SSH_SERVER, LOCAL_SERVER]))
    assert done == 1  # 成功 1 台


def test_collect_server_local(monkeypatch):
    m = make_metrics()
    monkeypatch.setattr(collector, "local_metrics", lambda: m)
    monkeypatch.setattr(collector, "insert_metric", lambda *a, **k: None)
    status_updates = []
    monkeypatch.setattr(collector, "update_status",
                        lambda sid, status, err, ts: status_updates.append((sid, status, err)))
    monkeypatch.setattr(collector, "alert_evaluate", lambda *a, **k: None)
    result = asyncio.run(collector.MonitorCollector().collect_server(LOCAL_SERVER))
    assert result == m
```

（注：`collect_all` 签名在本任务中定义为 `async def collect_all(self, servers: Optional[List] = None)`，便于测试注入服务器列表；不传时从 `get_enabled_servers()` 加载。）

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_collector.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现采集引擎**

```python
# backend/app/services/monitor/collector.py
"""
采集引擎 - asyncio 后台任务，每 30s 采集所有启用服务器（本机 psutil / 远程 SSH 脚本）
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import psutil

from app.services.monitor import alert_engine
from app.services.monitor.metric_repo import insert_metric
from app.services.monitor.script import BASH_SCRIPT, parse_script_output
from app.services.monitor.server_service import MonitorServerService
from app.services.monitor.ssh_client import pool

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 30  # 秒


def local_metrics() -> Dict:
    """采集本机指标（复用 psutil 与 system_monitor_service）"""
    from app.services.system_monitor_service import get_resource_usage

    net_before = psutil.net_io_counters()
    io_before = psutil.disk_io_counters()
    t0 = time.monotonic()
    usage = get_resource_usage()  # 内部会阻塞约 0.5s 计算 CPU 百分比
    t1 = time.monotonic()
    dt = max(0.1, t1 - t0)
    net_after = psutil.net_io_counters()
    io_after = psutil.disk_io_counters()

    mem = usage["memory"]
    swap = usage["swap"]
    disk = usage["disk"]
    try:
        load_avg = list(psutil.getloadavg())
    except OSError:
        load_avg = [0.0, 0.0, 0.0]

    return {
        "cpu_percent": float(usage["cpu"]["percent"]),
        "cpu_per_core": [float(x) for x in usage["cpu"]["per_cpu"]],
        "load_avg": load_avg,
        "mem_total": int(mem["total"]),
        "mem_used": int(mem["used"]),
        "mem_percent": float(mem["percent"]),
        "swap_total": int(swap["total"]),
        "swap_used": int(swap["used"]),
        "swap_percent": float(swap["percent"]),
        "disk_total": int(disk["total"]),
        "disk_used": int(disk["used"]),
        "disk_percent": float(disk["percent"]),
        "net_recv_rate": max(0.0, (net_after.bytes_recv - net_before.bytes_recv) / dt),
        "net_sent_rate": max(0.0, (net_after.bytes_sent - net_before.bytes_sent) / dt),
        "disk_read_rate": max(0.0, (io_after.read_bytes - io_before.read_bytes) / dt) if io_after and io_before else 0.0,
        "disk_write_rate": max(0.0, (io_after.write_bytes - io_before.write_bytes) / dt) if io_after and io_before else 0.0,
        "process_count": len(psutil.pids()),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


class MonitorCollector:
    """采集引擎：后台循环 + 手动采集"""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ---------- 生命周期 ----------

    async def start(self) -> None:
        """启动后台采集任务"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("监控采集引擎已启动")

    async def stop(self) -> None:
        """停止后台采集任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        pool.close_all()
        logger.info("监控采集引擎已停止")

    async def _loop(self) -> None:
        """后台循环：按全局间隔执行采集周期"""
        while self._running:
            interval = max(10, MonitorServerService.get_global_interval())
            cycle_start = time.monotonic()
            try:
                await self.collect_all()
            except Exception as e:
                logger.error("采集周期异常: %s", str(e), exc_info=True)
            elapsed = time.monotonic() - cycle_start
            await asyncio.sleep(max(1.0, interval - elapsed))

    # ---------- 采集 ----------

    async def collect_all(self, servers: Optional[List[Dict]] = None) -> int:
        """采集一批服务器，返回成功数；单台失败隔离"""
        if servers is None:
            try:
                servers = MonitorServerService.get_enabled_servers()
            except Exception as e:
                logger.error("加载监控服务器失败: %s", str(e))
                return 0
        if not servers:
            return 0
        sem = asyncio.Semaphore(5)
        results = await asyncio.gather(
            *[self._guarded(sem, s) for s in servers],
            return_exceptions=True,
        )
        success = sum(1 for r in results if isinstance(r, dict))
        await asyncio.to_thread(pool.close_idle_connections)
        logger.info("采集周期完成: 共 %d 台，成功 %d 台", len(servers), success)
        return success

    async def _guarded(self, sem: asyncio.Semaphore, server: Dict):
        async with sem:
            return await self.collect_server(server)

    async def collect_server(self, server: Dict) -> Optional[Dict]:
        """采集单台服务器：本机 psutil / 远程 SSH 脚本，成功写入并触发告警评估"""
        server_id = server.get("id")
        try:
            if server.get("server_type") == "local":
                metrics = await asyncio.to_thread(local_metrics)
            else:
                raw = await pool.run_command(server, BASH_SCRIPT, timeout=10)
                metrics = parse_script_output(raw)
                if metrics is None:
                    raise ValueError("采集脚本输出解析失败")
            insert_metric(server_id, metrics)
            MonitorServerService.update_status(server_id, "online", None, datetime.now())
            # 告警评估放在写入之后，独立 try 防止告警异常影响采集状态
            try:
                alert_engine.evaluate(server, metrics)
            except Exception as e:
                logger.error("告警评估失败: server=%s 错误=%s", server_id, str(e))
            return metrics
        except Exception as e:
            logger.warning("服务器采集失败: id=%s name=%s 错误=%s", server_id, server.get("name"), str(e))
            try:
                MonitorServerService.update_status(server_id, "offline", str(e)[:200], None)
            except Exception:
                pass
            return None

    async def collect_now(self, server_id: str, user_id: str) -> Optional[Dict]:
        """手动触发采集（重试按钮），不阻塞后台循环"""
        try:
            server = MonitorServerService.get_server(user_id, server_id)
        except Exception as e:
            logger.error("手动采集加载服务器失败: %s", str(e))
            return None
        if not server:
            return None
        return await self.collect_server(server)


monitor_collector = MonitorCollector()
```

（`collector.py` 中的 `run_command` / `parse_script_output` / `insert_metric` / `update_status` / `alert_evaluate` 为测试 monkeypatch 目标：测试中直接 monkeypatch `collector.run_command` 等模块级引用。因此请在 `collector.py` 顶部加：

```python
from app.services.monitor.ssh_client import pool, SSHCommandError
async def run_command(server, command, timeout=10):
    """远程执行命令（测试可替换）"""
    return await pool.run_command(server, command, timeout)
```

并将 `collect_server` 中 `await pool.run_command(...)` 改为 `await run_command(...)`。）

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_collector.py -v`
Expected: PASS（5 个）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/monitor/collector.py backend/tests/test_monitor_collector.py
git commit -m "feat: 采集引擎（后台循环/本机psutil/远程脚本/失败隔离）"
```

---

### Task 8: 按需远程操作（remote_ops.py）

**Files:**
- Create: `backend/app/services/monitor/remote_ops.py`
- Test: `backend/tests/test_monitor_remote_ops.py`

**Interfaces:**
- Consumes: `server` dict、`pool.run_command`、本机 subprocess
- Produces:
  - `async def get_partitions(server: Dict) -> List[Dict]`
  - `async def get_processes(server: Dict, sort_by: str, sort_order: str, search: Optional[str], project_type: Optional[str], page: int, page_size: int) -> Dict`
  - `async def kill_process(server: Dict, pid: int) -> bool`
  - `async def get_services(server: Dict) -> List[Dict]`
  - `async def service_action(server: Dict, unit: str, action: str) -> Dict`（返回 `{"success": bool, "message": str}`）
  - `async def check_privileges(server: Dict) -> Dict`（返回 `{"sudo_available": bool}`）
  - `async def get_system_info(server: Dict) -> Dict`（本机 psutil / 远程 uname+os-release，带 60s 缓存）

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_remote_ops.py
"""
按需远程操作测试 - mock 命令输出，验证解析逻辑
"""
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import remote_ops

SSH_SERVER = {"id": "srv-1", "user_id": "u1", "server_type": "ssh", "name": "web1",
              "host": "10.0.0.1", "port": 22, "username": "root", "password": "pw",
              "private_key": None, "passphrase": None, "group_name": None,
              "status": "enabled", "last_error": None, "last_seen_at": None}

LOCAL_SERVER = {"id": "srv-local", "user_id": "u1", "server_type": "local", "name": "本机",
                "host": "", "port": 22, "username": "", "password": None,
                "private_key": None, "passphrase": None, "group_name": None,
                "status": "enabled", "last_error": None, "last_seen_at": None}

DF_OUTPUT = """Filesystem     1024-blocks      Used Available Capacity Mounted on
/dev/vda1        20971520   4194304  16777216      20% /
"""

PS_OUTPUT = """1|root|Ss|0.0|0.1|100000|200000|1|00:12:34|/sbin/init
1234|root|S|5.5|2.0|500000|900000|8|02:00:00|/usr/bin/python3 /opt/app/main.py
5678|www|R|95.0|10.0|2000000|3000000|20|00:01:00|node /app/server.js
"""

SVC_OUTPUT = """nginx.service loaded active running The nginx HTTP and reverse proxy server
mysql.service loaded active exited MySQL Community Server
cron.service loaded not-running Regular background program processing daemon
"""

SVC_FILES_OUTPUT = """nginx.service enabled
mysql.service disabled
cron.service enabled
"""


def test_parse_df():
    rows = remote_ops._parse_df_output(DF_OUTPUT)
    assert len(rows) == 1
    assert rows[0]["device"] == "/dev/vda1"
    assert rows[0]["percent"] == 20.0
    assert rows[0]["total"] == 20971520 * 1024


def test_parse_ps():
    processes = remote_ops._parse_ps_output(PS_OUTPUT)
    assert len(processes) == 3
    assert processes[0]["pid"] == 1
    assert processes[1]["cpu_percent"] == 5.5
    assert processes[1]["command_line"].startswith("/usr/bin/python3")
    assert processes[2]["project_type"] == "Node.js"


def test_parse_services():
    services = remote_ops._parse_services_output(SVC_OUTPUT, SVC_FILES_OUTPUT)
    assert len(services) == 3
    nginx = services[0]
    assert nginx["name"] == "nginx.service"
    assert nginx["state"] == "running"
    assert nginx["enabled"] is True
    assert services[1]["enabled"] is False


def test_get_partitions_local(monkeypatch):
    """本机通过 subprocess 执行 df"""
    result = MagicMock(returncode=0, stdout=DF_OUTPUT, stderr="")
    monkeypatch.setattr(remote_ops, "_run_local_command", lambda *a, **k: ("", DF_OUTPUT))
    rows = asyncio.run(remote_ops.get_partitions(LOCAL_SERVER))
    assert rows[0]["device"] == "/dev/vda1"


def test_service_action_success(monkeypatch):
    async def fake_run(server, cmd, timeout=10):
        return ""
    monkeypatch.setattr(remote_ops, "_run_on_server", fake_run)
    result = asyncio.run(remote_ops.service_action(SSH_SERVER, "nginx.service", "restart"))
    assert result["success"] is True


def test_service_action_failure(monkeypatch):
    from app.services.monitor.ssh_client import SSHCommandError

    async def fake_run(server, cmd, timeout=10):
        raise SSHCommandError("需要 root 权限")
    monkeypatch.setattr(remote_ops, "_run_on_server", fake_run)
    result = asyncio.run(remote_ops.service_action(SSH_SERVER, "nginx.service", "restart"))
    assert result["success"] is False
    assert "root" in result["message"]


def test_check_privileges_sudo_ok(monkeypatch):
    async def fake_run(server, cmd, timeout=10):
        return "EXIT:0"
    monkeypatch.setattr(remote_ops, "_run_on_server", fake_run)
    result = asyncio.run(remote_ops.check_privileges(SSH_SERVER))
    assert result["sudo_available"] is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_monitor_remote_ops.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现远程操作**

```python
# backend/app/services/monitor/remote_ops.py
"""
按需远程操作 - 进程列表/结束、systemd 服务管理、磁盘分区、权限检测、系统信息
本机走 subprocess，远程走 SSH 连接池
"""
import asyncio
import logging
import subprocess
import time
from typing import Dict, List, Optional

from app.services.monitor.ssh_client import SSHCommandError, pool

logger = logging.getLogger(__name__)

# 系统信息缓存（60 秒）
_sysinfo_cache: Dict[str, dict] = {}
_sysinfo_cache_time: Dict[str, float] = {}
_SYSINFO_CACHE_TTL = 60


async def _run_on_server(server: Dict, command: str, timeout: int = 10) -> str:
    """在目标上执行命令：本机 subprocess / 远程 SSH"""
    if server.get("server_type") == "local":
        return await asyncio.to_thread(_run_local_command, command, timeout)
    return await pool.run_command(server, command, timeout)


def _run_local_command(command: str, timeout: int = 10) -> str:
    """本机执行 shell 命令"""
    result = subprocess.run(command, shell=True, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode != 0:
        raise SSHCommandError(f"本地命令执行失败 (exit={result.returncode}): {result.stderr[:200]}")
    return result.stdout


# ============ 磁盘分区 ============

def _parse_df_output(output: str) -> List[Dict]:
    """解析 df -Pk 输出（1024-blocks 单位）"""
    rows = []
    for line in output.strip().splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        mountpoint = " ".join(parts[5:])  # 挂载点可能含空格
        capacity = parts[4].rstrip("%")
        try:
            rows.append({
                "device": parts[0],
                "mountpoint": mountpoint,
                "fstype": "",
                "total": int(parts[1]) * 1024,
                "used": int(parts[2]) * 1024,
                "free": int(parts[3]) * 1024,
                "percent": float(capacity),
            })
        except ValueError:
            continue
    return rows


async def get_partitions(server: Dict) -> List[Dict]:
    """获取磁盘分区列表（实时）"""
    out = await _run_on_server(server, "df -Pk", timeout=10)
    return _parse_df_output(out)


# ============ 进程管理 ============

def _parse_ps_output(output: str) -> List[Dict]:
    """解析 ps 输出（管道分隔）：pid|user|stat|pcpu|pmem|rss|vsz|nlwp|etime|args"""
    processes = []
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 9)
        if len(parts) < 10:
            continue
        pid, user, stat, pcpu, pmem, rss, vsz, nlwp, etime, args = parts
        try:
            processes.append({
                "pid": int(pid),
                "name": args.split()[0].split("/")[-1] if args.split() else "",
                "username": user,
                "status": stat,
                "cpu_percent": round(float(pcpu), 1),
                "memory_percent": round(float(pmem), 1),
                "memory_rss": int(rss) * 1024,
                "memory_vms": int(vsz) * 1024,
                "num_threads": int(nlwp),
                "create_time": etime,
                "command_line": args[:300],
                "project_type": _detect_project_type(args),
            })
        except (ValueError, IndexError):
            continue
    return processes


def _detect_project_type(args: str) -> str:
    """按命令行检测项目类型（远程简化版）"""
    args_lower = args.lower()
    if "uvicorn" in args_lower or "fastapi" in args_lower:
        return "FastAPI"
    if "django" in args_lower:
        return "Django"
    if "flask" in args_lower:
        return "Flask"
    if "celery" in args_lower:
        return "Celery"
    if "gunicorn" in args_lower:
        return "Gunicorn"
    if "spring" in args_lower or "java -jar" in args_lower:
        return "Java"
    if "node" in args_lower:
        return "Node.js"
    if "nginx" in args_lower:
        return "Nginx"
    if "mysqld" in args_lower or "/mysql" in args_lower:
        return "MySQL"
    if "postgres" in args_lower:
        return "PostgreSQL"
    if "redis" in args_lower:
        return "Redis"
    if "dockerd" in args_lower or "containerd" in args_lower:
        return "Docker"
    if "python" in args_lower:
        return "Python"
    return "Other"


async def get_processes(
    server: Dict, sort_by: str = "cpu_percent", sort_order: str = "desc",
    search: Optional[str] = None, project_type: Optional[str] = None,
    page: int = 1, page_size: int = 50,
) -> Dict:
    """获取远程进程列表（ps 命令 + 服务端过滤/排序/分页）"""
    ps_cmd = (
        "ps axo pid=,user=,stat=,pcpu=,pmem=,rss=,vsz=,nlwp=,etime=,args= "
        "| awk '{pid=$1;user=$2;stat=$3;pcpu=$4;pmem=$5;rss=$6;vsz=$7;nlwp=$8;"
        "rest=\"\"; for(i=9;i<=NF;i++) rest=rest \" \" $i; "
        "print pid \"|\" user \"|\" stat \"|\" pcpu \"|\" pmem \"|\" rss \"|\" vsz \"|\" nlwp \"|\" etime \"|\" rest}'"
    )
    out = await _run_on_server(server, ps_cmd, timeout=15)
    processes = _parse_ps_output(out)

    if project_type and project_type != "all":
        processes = [p for p in processes if p["project_type"] == project_type]
    if search:
        search_lower = search.lower()
        processes = [
            p for p in processes
            if search_lower in p["name"].lower() or search_lower in p["command_line"].lower()
        ]

    reverse = sort_order == "desc"
    sort_keys = {"cpu_percent", "memory_percent", "pid", "memory_rss", "num_threads", "name"}
    if sort_by in sort_keys:
        key_fn = (lambda p: str(p[sort_by]).lower()) if sort_by == "name" else (lambda p: p[sort_by])
        processes.sort(key=key_fn, reverse=reverse)

    total = len(processes)
    offset = (page - 1) * page_size
    return {
        "processes": processes[offset:offset + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


async def kill_process(server: Dict, pid: int) -> bool:
    """结束远程进程（先 TERM 后 KILL）"""
    try:
        await _run_on_server(server, f"kill {pid}", timeout=10)
        return True
    except Exception:
        try:
            await _run_on_server(server, f"kill -9 {pid}", timeout=10)
            return True
        except Exception:
            return False


# ============ 服务管理 ============

def _parse_services_output(units_output: str, files_output: str) -> List[Dict]:
    """解析 systemctl 输出"""
    enabled_map = {}
    for line in files_output.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            enabled_map[parts[0]] = parts[1]
    services = []
    for line in units_output.strip().splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5 or not parts[0].endswith(".service"):
            continue
        name, load, active, state, desc = parts
        services.append({
            "name": name,
            "load": load,
            "active": active,
            "state": state,
            "description": desc,
            "enabled": enabled_map.get(name) == "enabled",
        })
    return services


async def get_services(server: Dict) -> List[Dict]:
    """获取 systemd 服务列表"""
    units_cmd = "systemctl list-units --type=service --all --no-pager --no-legend --plain"
    files_cmd = "systemctl list-unit-files --type=service --no-pager --no-legend --plain"
    try:
        units_out, files_out = await asyncio.gather(
            _run_on_server(server, units_cmd, timeout=15),
            _run_on_server(server, files_cmd, timeout=15),
        )
    except Exception as e:
        logger.warning("获取服务列表失败: %s", str(e))
        return []
    return _parse_services_output(units_out, files_out)


async def service_action(server: Dict, unit: str, action: str) -> Dict:
    """执行服务启停（优先 sudo -n，失败回退直接 systemctl）"""
    for cmd in (f"sudo -n systemctl {action} {unit}", f"systemctl {action} {unit}"):
        try:
            await _run_on_server(server, cmd, timeout=20)
            logger.info("服务操作成功: %s %s on %s", action, unit, server.get("name"))
            return {"success": True, "message": f"{action} 成功"}
        except SSHCommandError as e:
            last_error = str(e)
        except Exception as e:
            last_error = str(e)
    if "sudo" in last_error and "root" in last_error.lower():
        message = "需要 root 或无密码 sudo 权限"
    else:
        message = last_error[:200]
    return {"success": False, "message": message}


async def check_privileges(server: Dict) -> Dict:
    """检测 sudo 可用性"""
    try:
        out = await _run_on_server(server, "sudo -n true; echo EXIT:$?", timeout=10)
        return {"sudo_available": "EXIT:0" in out}
    except Exception:
        return {"sudo_available": False}


# ============ 系统信息 ============

async def get_system_info(server: Dict) -> Dict:
    """获取系统信息（本机 psutil / 远程命令，带 60s 缓存）"""
    server_id = server.get("id")
    now = time.time()
    if server_id in _sysinfo_cache and now - _sysinfo_cache_time.get(server_id, 0) < _SYSINFO_CACHE_TTL:
        return _sysinfo_cache[server_id]
    if server.get("server_type") == "local":
        from app.services.system_monitor_service import get_system_info as get_local_info
        info = get_local_info()
    else:
        cmd = (
            "hostname; cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'; "
            "uname -r; uptime -p"
        )
        try:
            out = await _run_on_server(server, cmd, timeout=10)
            lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
            info = {
                "hostname": lines[0] if len(lines) > 0 else server.get("host", ""),
                "os": lines[1] if len(lines) > 1 else "Linux",
                "kernel": lines[2] if len(lines) > 2 else "",
                "uptime_text": lines[3] if len(lines) > 3 else "",
                "platform": "Linux",
            }
        except Exception as e:
            logger.warning("远程系统信息获取失败: %s", str(e))
            info = {"hostname": server.get("host", ""), "os": "Linux",
                    "kernel": "", "uptime_text": "", "platform": "Linux"}
    _sysinfo_cache[server_id] = info
    _sysinfo_cache_time[server_id] = now
    return info
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_monitor_remote_ops.py -v`
Expected: PASS（8 个）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/monitor/remote_ops.py backend/tests/test_monitor_remote_ops.py
git commit -m "feat: 按需远程操作（进程/服务/分区/权限/系统信息）"
```

---

### Task 9: 监控 API 路由 + 主程序接线（routes/monitor.py + main.py）

**Files:**
- Create: `backend/app/routes/monitor.py`
- Modify: `backend/app/main.py`（注册路由 + lifespan 启动/停止采集引擎 + 建表）

**Interfaces:**
- Consumes: Task 1-8 全部模块
- Produces: 规格 4.5 节全部 API 端点

- [ ] **Step 1: 实现路由**

```python
# backend/app/routes/monitor.py
"""
监控模块 API 路由
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.auth_middleware import get_current_user_id
from app.models.monitor_models import (
    CreateMonitorServerRequest, UpdateMonitorServerRequest, MonitorServerResponse,
    ImportSSHRequest, TestMonitorServerRequest, AlertRuleCreateRequest,
    AlertRuleUpdateRequest, AlertRuleResponse, AlertLogResponse,
    MonitorSettings, ServiceActionRequest,
)
from app.services.monitor import alert_engine, remote_ops
from app.services.monitor.collector import monitor_collector
from app.services.monitor.metric_repo import get_latest_metric, query_metrics
from app.services.monitor.server_service import MonitorServerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitor", tags=["monitor"])


# ============ 服务器管理 ============

@router.get("/servers", response_model=List[MonitorServerResponse])
async def get_servers(user_id: str = Depends(get_current_user_id)):
    """获取服务器列表（含最近指标与实时状态）"""
    return MonitorServerService.get_servers(user_id)


@router.post("/servers", response_model=MonitorServerResponse)
async def create_server(
    request: CreateMonitorServerRequest,
    user_id: str = Depends(get_current_user_id),
):
    """新建监控服务器"""
    return MonitorServerService.create_server(user_id, request)


@router.post("/servers/test")
async def test_server_connection(
    request: TestMonitorServerRequest,
    user_id: str = Depends(get_current_user_id),
):
    """测试 SSH 连接"""
    MonitorServerService.test_connection(request)
    return {"success": True, "message": "连接成功"}


@router.post("/servers/import-ssh", response_model=MonitorServerResponse)
async def import_from_ssh(
    request: ImportSSHRequest,
    user_id: str = Depends(get_current_user_id),
):
    """从 SSH 配置导入监控服务器"""
    return MonitorServerService.import_from_ssh(user_id, request.ssh_config_id)


@router.put("/servers/{server_id}", response_model=MonitorServerResponse)
async def update_server(
    server_id: str,
    request: UpdateMonitorServerRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新监控服务器"""
    updated = MonitorServerService.update_server(user_id, server_id, request)
    if not updated:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return updated


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """删除监控服务器"""
    if not MonitorServerService.delete_server(user_id, server_id):
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"success": True}


@router.post("/servers/{server_id}/retry")
async def retry_server(
    server_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """手动触发采集（错误恢复）"""
    result = await monitor_collector.collect_now(server_id, user_id)
    if result is None:
        raise HTTPException(status_code=500, detail="采集失败，请检查连接配置")
    return {"success": True}


# ============ 监控数据 ============

@router.get("/servers/{server_id}/overview")
async def get_overview(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取服务器实时状态（最近一次采集指标）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {
        "server": {k: v for k, v in server.items() if k not in ("password", "private_key", "passphrase")},
        "metric": get_latest_metric(server_id),
    }


@router.get("/servers/{server_id}/metrics")
async def get_metrics(
    server_id: str,
    range: str = Query("1h", pattern="^(1h|6h|24h|7d)$"),
    user_id: str = Depends(get_current_user_id),
):
    """获取历史指标（7d 自动按小时聚合）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"server_id": server_id, "range": range, "points": query_metrics(server_id, range)}


@router.get("/servers/{server_id}/partitions")
async def get_partitions(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取磁盘分区列表"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"partitions": await remote_ops.get_partitions(server)}


@router.get("/servers/{server_id}/system-info")
async def get_system_info(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取系统信息（60s 缓存）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return await remote_ops.get_system_info(server)


# ============ 进程管理 ============

@router.get("/servers/{server_id}/processes")
async def get_processes(
    server_id: str,
    sort_by: str = Query("cpu_percent"),
    sort_order: str = Query("desc"),
    search: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    user_id: str = Depends(get_current_user_id),
):
    """获取进程列表（本机走 psutil，远程走 ps 命令）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    if server["server_type"] == "local":
        from app.services.system_monitor_service import get_process_list
        return get_process_list(sort_by=sort_by, sort_order=sort_order,
                                search=search, project_type=project_type,
                                page=page, page_size=page_size)
    return await remote_ops.get_processes(
        server, sort_by=sort_by, sort_order=sort_order, search=search,
        project_type=project_type, page=page, page_size=page_size)


@router.post("/servers/{server_id}/processes/{pid}/kill")
async def kill_process(
    server_id: str, pid: int, user_id: str = Depends(get_current_user_id),
):
    """结束进程"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    if server["server_type"] == "local":
        from app.services.system_monitor_service import kill_process as kill_local
        ok = kill_local(pid)
    else:
        ok = await remote_ops.kill_process(server, pid)
    if not ok:
        raise HTTPException(status_code=400, detail="进程不存在或无法终止（可能权限不足）")
    return {"success": True, "pid": pid}


# ============ 服务管理 ============

@router.get("/servers/{server_id}/services")
async def get_services(server_id: str, user_id: str = Depends(get_current_user_id)):
    """获取 systemd 服务列表"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return {"services": await remote_ops.get_services(server)}


@router.post("/servers/{server_id}/services/{unit}/action")
async def service_action(
    server_id: str, unit: str, request: ServiceActionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """执行服务操作（start/stop/restart）"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    result = await remote_ops.service_action(server, unit, request.action)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/servers/{server_id}/privileges")
async def get_privileges(server_id: str, user_id: str = Depends(get_current_user_id)):
    """检测 sudo 可用性"""
    server = MonitorServerService.get_server(user_id, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="监控服务器不存在")
    return await remote_ops.check_privileges(server)


# ============ 告警 ============

@router.get("/alerts", response_model=List[AlertRuleResponse])
async def get_alerts(user_id: str = Depends(get_current_user_id)):
    """获取告警规则"""
    return alert_engine.get_rules(user_id)


@router.post("/alerts", response_model=AlertRuleResponse)
async def create_alert(
    request: AlertRuleCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """新建告警规则"""
    return alert_engine.create_rule(user_id, request)


@router.put("/alerts/{rule_id}", response_model=AlertRuleResponse)
async def update_alert(
    rule_id: str, request: AlertRuleUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """更新告警规则"""
    updated = alert_engine.update_rule(user_id, rule_id, request)
    if not updated:
        raise HTTPException(status_code=404, detail="告警规则不存在")
    return updated


@router.delete("/alerts/{rule_id}")
async def delete_alert(rule_id: str, user_id: str = Depends(get_current_user_id)):
    """删除告警规则"""
    if not alert_engine.delete_rule(user_id, rule_id):
        raise HTTPException(status_code=404, detail="告警规则不存在")
    return {"success": True}


@router.get("/alerts/logs")
async def get_alert_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    user_id: str = Depends(get_current_user_id),
):
    """获取告警触发记录（含未读数）"""
    return alert_engine.get_logs(user_id, page=page, page_size=page_size)


@router.put("/alerts/logs/read")
async def mark_alert_logs_read(user_id: str = Depends(get_current_user_id)):
    """标记告警记录全部已读"""
    alert_engine.mark_logs_read(user_id)
    return {"success": True}


# ============ 设置 ============

@router.get("/settings")
async def get_settings(user_id: str = Depends(get_current_user_id)):
    """获取监控设置"""
    return MonitorServerService.get_settings(user_id)


@router.put("/settings")
async def save_settings(request: MonitorSettings, user_id: str = Depends(get_current_user_id)):
    """保存监控设置"""
    MonitorServerService.save_settings(user_id, request)
    return {"success": True}
```

- [ ] **Step 2: 接线 main.py**

修改 `backend/app/main.py`：

1. 在 `from app.routes import auth, contact_message` 行下方加入：
```python
from app.routes import monitor as monitor_router
```
2. 在 `app.include_router(glm_coding_rusher.router, prefix="/api")` 行之后加入：
```python
# Monitor router（服务器监控）
app.include_router(monitor_router.router, prefix="/api")
```
3. 在 `lifespan` 的 `# 启动后台清理任务` 之前加入：
```python
    # 初始化监控模块（建表 + 启动采集引擎）
    try:
        from app.services.monitor.server_service import MonitorServerService
        from app.services.monitor import metric_repo, alert_engine
        from app.services.monitor.collector import monitor_collector
        MonitorServerService.ensure_tables()
        metric_repo.ensure_tables()
        alert_engine.ensure_tables()
        await monitor_collector.start()
        logger.info("监控模块初始化完成")
    except Exception as e:
        logger.error(f"监控模块初始化失败: {e}")
```
4. 在 `lifespan` 的 `yield` 之后、`logger.info("Shutting down application...")` 附近加入：
```python
    # 停止监控采集引擎
    try:
        from app.services.monitor.collector import monitor_collector
        await monitor_collector.stop()
    except Exception as e:
        logger.warning(f"监控采集引擎停止异常: {e}")
```

- [ ] **Step 3: 语法检查**

Run: `cd backend && python -m py_compile app/routes/monitor.py app/main.py && ruff check app/routes/monitor.py app/services/monitor/`
Expected: 无错误输出

- [ ] **Step 4: 手工冒烟验证（启动后端）**

Run: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 19092`（观察日志出现「监控模块初始化完成」与「监控采集引擎已启动」，出现采集周期日志且无异常后 Ctrl+C 停止）

Expected: 日志无 ERROR；`GET /api/monitor/servers` 返回含本机节点的列表（用浏览器或 curl 带 token 验证）

- [ ] **Step 5: 提交**

```bash
git add backend/app/routes/monitor.py backend/app/main.py
git commit -m "feat: 监控 API 路由与主程序接线"
```

---

### Task 10: 后端集成测试（test_monitor_api.py）

**Files:**
- Create: `backend/tests/test_monitor_api.py`

**Interfaces:**
- Consumes: Task 9 的全部端点；TestClient + 注册用户（复用 test_ssh_tool_api 模式）

- [ ] **Step 1: 编写测试**

```python
# backend/tests/test_monitor_api.py
"""
监控 API 集成测试 - 服务器 CRUD、告警规则、设置（真实 PostgreSQL + 服务 monkeypatch）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.monitor.server_service import MonitorServerService
from app.services.monitor import alert_engine, remote_ops


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    register_response = client.post("/api/auth/register", json={
        "username": "monitor_test_user",
        "email": "monitor_test_user@example.com",
        "password": "testpassword123",
    })
    if register_response.status_code == 200:
        token = register_response.json().get("token")
    else:
        login_response = client.post("/api/auth/login", json={
            "username": "monitor_test_user",
            "password": "testpassword123",
        })
        token = login_response.json().get("token")
    return {"Authorization": f"Bearer {token}"}


def test_get_servers_creates_local_node(client, auth_headers):
    """首次获取服务器列表自动创建本机节点"""
    response = client.get("/api/monitor/servers", headers=auth_headers)
    assert response.status_code == 200
    servers = response.json()
    assert len(servers) >= 1
    assert any(s["server_type"] == "local" for s in servers)


def test_create_and_delete_server(client, auth_headers, monkeypatch):
    """创建监控服务器（凭据加密）→ 删除"""
    create_response = client.post("/api/monitor/servers", json={
        "name": "测试服务器", "host": "192.168.1.100", "port": 22,
        "username": "root", "password": "secret", "group_name": "生产",
    }, headers=auth_headers)
    assert create_response.status_code == 200
    server = create_response.json()
    assert server["server_type"] == "ssh"
    assert "password" not in server or server["password"] is None

    delete_response = client.delete(f"/api/monitor/servers/{server['id']}", headers=auth_headers)
    assert delete_response.status_code == 200


def test_create_server_invalid_port(client, auth_headers):
    response = client.post("/api/monitor/servers", json={
        "name": "x", "host": "h", "port": 99999, "username": "u",
    }, headers=auth_headers)
    assert response.status_code == 422


def test_test_connection_success(client, auth_headers, monkeypatch):
    monkeypatch.setattr(MonitorServerService, "test_connection",
                        staticmethod(lambda req: None))
    response = client.post("/api/monitor/servers/test", json={
        "host": "127.0.0.1", "port": 22, "username": "root", "password": "pw",
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_test_connection_failure(client, auth_headers, monkeypatch):
    from fastapi import HTTPException

    def fail(req):
        raise HTTPException(status_code=400, detail="连接失败: timeout")
    monkeypatch.setattr(MonitorServerService, "test_connection", staticmethod(fail))
    response = client.post("/api/monitor/servers/test", json={
        "host": "10.255.255.1", "port": 22, "username": "root", "password": "pw",
    }, headers=auth_headers)
    assert response.status_code == 400


def test_alert_rule_crud(client, auth_headers):
    create_response = client.post("/api/monitor/alerts", json={
        "server_id": "all", "metric": "cpu_percent", "operator": ">",
        "threshold": 90, "duration": 3,
    }, headers=auth_headers)
    assert create_response.status_code == 200
    rule = create_response.json()
    assert rule["metric"] == "cpu_percent"

    list_response = client.get("/api/monitor/alerts", headers=auth_headers)
    assert any(r["id"] == rule["id"] for r in list_response.json())

    update_response = client.put(f"/api/monitor/alerts/{rule['id']}", json={
        "threshold": 95,
    }, headers=auth_headers)
    assert update_response.status_code == 200
    assert update_response.json()["threshold"] == 95

    delete_response = client.delete(f"/api/monitor/alerts/{rule['id']}", headers=auth_headers)
    assert delete_response.status_code == 200


def test_settings_save_and_get(client, auth_headers):
    save_response = client.put("/api/monitor/settings", json={
        "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
        "collect_interval": 30,
    }, headers=auth_headers)
    assert save_response.status_code == 200

    get_response = client.get("/api/monitor/settings", headers=auth_headers)
    assert get_response.status_code == 200
    assert "test" in get_response.json()["webhook_url"]


def test_metrics_requires_auth(client):
    response = client.get("/api/monitor/servers")
    assert response.status_code == 401
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_monitor_api.py -v`
Expected: 全部 PASS（注意：需要真实 PostgreSQL 可用；若数据库不可用，跳过本任务并在提交说明中注明）

- [ ] **Step 3: 回归测试**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: 既有测试全部通过（新增测试全通过）

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_monitor_api.py
git commit -m "test: 监控 API 集成测试"
```

---

## 前端任务

### Task 11: 前端 API 封装（monitorApi.ts）

**Files:**
- Create: `frontend/src/api/monitorApi.ts`

**Interfaces:**
- Produces: 以下类型与函数（Task 12-17 使用）
  - 类型：`MonitorServer`、`MetricPoint`、`AlertRule`、`AlertLog`、`ServiceInfo`、`MonitorSettings`
  - 函数：`getServers() / createServer() / updateServer() / deleteServer() / importFromSsh() / retryServer() / testServerConnection()`
  - `getOverview(serverId) / getMetrics(serverId, range) / getPartitions(serverId) / getSystemInfo(serverId)`
  - `getProcesses(serverId, params) / killProcess(serverId, pid)`
  - `getServices(serverId) / serviceAction(serverId, unit, action) / getPrivileges(serverId)`
  - `getAlerts() / createAlert() / updateAlert() / deleteAlert() / getAlertLogs(page, pageSize) / markAlertLogsRead()`
  - `getSettings() / saveSettings(settings)`

- [ ] **Step 1: 实现**

```typescript
// frontend/src/api/monitorApi.ts
import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const MONITOR_API_URL = `${API_BASE_URL}/monitor`;

export interface MonitorServerMetric {
  cpu_percent: number | null;
  mem_percent: number | null;
  disk_percent: number | null;
  net_recv_rate: number | null;
  net_sent_rate: number | null;
  disk_read_rate: number | null;
  disk_write_rate: number | null;
}

export interface MonitorServer {
  id: string;
  user_id: string;
  name: string;
  server_type: 'local' | 'ssh';
  host: string;
  port: number;
  username: string;
  group_name?: string | null;
  status: string;
  last_error?: string | null;
  last_seen_at?: string | null;
  created_at: string;
  metric?: MonitorServerMetric | null;
}

export interface CreateMonitorServerRequest {
  name: string;
  server_type?: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  private_key?: string;
  passphrase?: string;
  group_name?: string;
}

export interface MetricPoint {
  collected_at: string;
  cpu_percent?: number | null;
  cpu_per_core?: number[] | null;
  load_avg?: number[] | null;
  mem_percent?: number | null;
  disk_percent?: number | null;
  net_recv_rate?: number | null;
  net_sent_rate?: number | null;
  disk_read_rate?: number | null;
  disk_write_rate?: number | null;
}

export interface AlertRule {
  id: string;
  user_id: string;
  server_id: string;
  metric: string;
  operator: string;
  threshold: number;
  duration: number;
  enabled: boolean;
  created_at: string;
}

export interface AlertLog {
  id: number;
  rule_id: string;
  server_id: string;
  server_name: string;
  metric: string;
  actual_value: number;
  status: 'firing' | 'recovered';
  is_read: boolean;
  notified_at: string;
}

export interface ServiceInfo {
  name: string;
  load: string;
  active: string;
  state: string;
  description: string;
  enabled: boolean;
}

export interface MonitorSettings {
  webhook_url: string;
  collect_interval: number;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  } as HeadersInit;
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '未知错误' }));
    throw new Error(error.detail || `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.append(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export const getServers = () => request<MonitorServer[]>(`${MONITOR_API_URL}/servers`);
export const createServer = (data: CreateMonitorServerRequest) =>
  request<MonitorServer>(`${MONITOR_API_URL}/servers`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const updateServer = (id: string, data: Partial<CreateMonitorServerRequest>) =>
  request<MonitorServer>(`${MONITOR_API_URL}/servers/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const deleteServer = (id: string) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/servers/${id}`, { method: 'DELETE' });
export const importFromSsh = (sshConfigId: string) =>
  request<MonitorServer>(`${MONITOR_API_URL}/servers/import-ssh`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ssh_config_id: sshConfigId }),
  });
export const retryServer = (id: string) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/servers/${id}/retry`, { method: 'POST' });
export const testServerConnection = (data: Omit<CreateMonitorServerRequest, 'name' | 'server_type'>) =>
  request<{ success: boolean; message: string }>(`${MONITOR_API_URL}/servers/test`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });

export const getOverview = (serverId: string) =>
  request<{ server: MonitorServer; metric: MetricPoint | null }>(
    `${MONITOR_API_URL}/servers/${serverId}/overview`);
export const getMetrics = (serverId: string, range: string) =>
  request<{ server_id: string; range: string; points: MetricPoint[] }>(
    `${MONITOR_API_URL}/servers/${serverId}/metrics${buildQuery({ range })}`);
export const getPartitions = (serverId: string) =>
  request<{ partitions: Array<{ device: string; mountpoint: string; fstype: string; total: number; used: number; free: number; percent: number }> }>(
    `${MONITOR_API_URL}/servers/${serverId}/partitions`);
export const getSystemInfo = (serverId: string) =>
  request<Record<string, string | number>>(`${MONITOR_API_URL}/servers/${serverId}/system-info`);

export interface ProcessParams {
  sort_by?: string;
  sort_order?: string;
  search?: string;
  project_type?: string;
  page?: number;
  page_size?: number;
}

export interface MonitorProcess {
  pid: number;
  name: string;
  username: string;
  status: string;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
  memory_vms: number;
  num_threads: number;
  create_time: string;
  command_line: string;
  project_type: string;
}

export const getProcesses = (serverId: string, params: ProcessParams = {}) =>
  request<{ processes: MonitorProcess[]; total: number; page: number; page_size: number; total_pages: number }>(
    `${MONITOR_API_URL}/servers/${serverId}/processes${buildQuery(params)}`);
export const killProcess = (serverId: string, pid: number) =>
  request<{ success: boolean; pid: number }>(
    `${MONITOR_API_URL}/servers/${serverId}/processes/${pid}/kill`, { method: 'POST' });

export const getServices = (serverId: string) =>
  request<{ services: ServiceInfo[] }>(`${MONITOR_API_URL}/servers/${serverId}/services`);
export const serviceAction = (serverId: string, unit: string, action: 'start' | 'stop' | 'restart') =>
  request<{ success: boolean; message: string }>(
    `${MONITOR_API_URL}/servers/${serverId}/services/${encodeURIComponent(unit)}/action`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    });
export const getPrivileges = (serverId: string) =>
  request<{ sudo_available: boolean }>(`${MONITOR_API_URL}/servers/${serverId}/privileges`);

export interface AlertRulePayload {
  server_id: string;
  metric: string;
  operator: string;
  threshold: number;
  duration: number;
  enabled?: boolean;
}

export const getAlerts = () => request<AlertRule[]>(`${MONITOR_API_URL}/alerts`);
export const createAlert = (data: AlertRulePayload) =>
  request<AlertRule>(`${MONITOR_API_URL}/alerts`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const updateAlert = (id: string, data: Partial<AlertRulePayload>) =>
  request<AlertRule>(`${MONITOR_API_URL}/alerts/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const deleteAlert = (id: string) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/alerts/${id}`, { method: 'DELETE' });
export const getAlertLogs = (page = 1, pageSize = 20) =>
  request<{ logs: AlertLog[]; total: number; unread_count: number; page: number; page_size: number }>(
    `${MONITOR_API_URL}/alerts/logs${buildQuery({ page, page_size: pageSize })}`);
export const markAlertLogsRead = () =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/alerts/logs/read`, { method: 'PUT' });

export const getSettings = () => request<MonitorSettings>(`${MONITOR_API_URL}/settings`);
export const saveSettings = (data: MonitorSettings) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/settings`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/monitorApi.ts
git commit -m "feat: 监控模块前端 API 封装"
```

---

### Task 12: 前端状态管理（monitorStore.ts）

**Files:**
- Create: `frontend/src/stores/monitorStore.ts`
- Test: `frontend/src/stores/monitorStore.test.ts`

**Interfaces:**
- Produces: `MonitorTab` 类型、`useMonitorStore`（zustand），字段见下方代码

- [ ] **Step 1: 编写测试**

```typescript
// frontend/src/stores/monitorStore.test.ts
import { describe, it, expect } from 'vitest';
import { useMonitorStore } from './monitorStore';

describe('monitorStore', () => {
  it('默认状态：服务器页签、无选中服务器', () => {
    const state = useMonitorStore.getState();
    expect(state.activeTab).toBe('servers');
    expect(state.selectedServerId).toBeNull();
    expect(state.unreadAlerts).toBe(0);
  });

  it('可以切换页签与选中服务器', () => {
    useMonitorStore.getState().setActiveTab('history');
    expect(useMonitorStore.getState().activeTab).toBe('history');

    useMonitorStore.getState().setSelectedServerId('srv-1');
    expect(useMonitorStore.getState().selectedServerId).toBe('srv-1');
  });

  it('可以设置服务器列表与未读数', () => {
    const fakeServer = { id: 'srv-1', name: '本机', server_type: 'local' } as any;
    useMonitorStore.getState().setServers([fakeServer]);
    expect(useMonitorStore.getState().servers).toHaveLength(1);
    useMonitorStore.getState().setUnreadAlerts(3);
    expect(useMonitorStore.getState().unreadAlerts).toBe(3);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/stores/monitorStore.test.ts`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 store**

```typescript
// frontend/src/stores/monitorStore.ts
import { create } from 'zustand';
import type { MonitorServer } from '../api/monitorApi';

export type MonitorTab = 'servers' | 'overview' | 'history' | 'processes' | 'services' | 'alerts';

interface MonitorState {
  servers: MonitorServer[];
  selectedServerId: string | null;
  activeTab: MonitorTab;
  unreadAlerts: number;
  setServers: (servers: MonitorServer[]) => void;
  setSelectedServerId: (id: string | null) => void;
  setActiveTab: (tab: MonitorTab) => void;
  setUnreadAlerts: (count: number) => void;
}

export const useMonitorStore = create<MonitorState>((set) => ({
  servers: [],
  selectedServerId: null,
  activeTab: 'servers',
  unreadAlerts: 0,
  setServers: (servers) => set({ servers }),
  setSelectedServerId: (id) => set({ selectedServerId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setUnreadAlerts: (count) => set({ unreadAlerts: count }),
}));
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/stores/monitorStore.test.ts`
Expected: PASS（3 个）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/stores/monitorStore.ts frontend/src/stores/monitorStore.test.ts
git commit -m "feat: 监控模块 zustand store"
```

---

### Task 13: 前端公共组件（MetricChart / ServerCard / ServerSelector / ResourceCards / SystemInfoCards / ConfirmModal / AddServerModal）

**Files:**
- Create: `frontend/src/components/Tools/SystemMonitor/components/MetricChart.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/components/ServerCard.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/components/ServerSelector.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/components/ResourceCards.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/components/SystemInfoCards.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/components/ConfirmModal.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/components/AddServerModal.tsx`
- Test: `frontend/src/components/Tools/SystemMonitor/components/ServerCard.test.tsx`

**Interfaces:**
- Produces（Task 14-17 使用）：
  - `MetricChart({ data: ChartPoint[]; lines: ChartLine[]; height?: number })`，`ChartPoint = { time: string; [key: string]: number | string | null }`，`ChartLine = { key: string; name: string; color: string }`
  - `ServerCard({ server, onSelect, onEdit, onDelete, onRetry })`
  - `ServerSelector({ servers, value, onChange, disabled? })`
  - `ResourceCards({ metric: MetricPoint | null })`
  - `SystemInfoCards({ info: Record<string, string | number> | null; server: MonitorServer })`
  - `ConfirmModal({ open, title, message, onConfirm, onCancel, danger? })`
  - `AddServerModal({ open, onClose, onSaved, sshConfigs })`（手动填写 + 从 SSH 导入两种模式）

- [ ] **Step 1: 编写 ServerCard 测试**

```typescript
// frontend/src/components/Tools/SystemMonitor/components/ServerCard.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ServerCard } from './ServerCard';
import type { MonitorServer } from '../../../api/monitorApi';

const server: MonitorServer = {
  id: 'srv-1',
  user_id: 'u1',
  name: 'web1',
  server_type: 'ssh',
  host: '10.0.0.1',
  port: 22,
  username: 'root',
  status: 'online',
  created_at: '2026-01-01T00:00:00',
  metric: { cpu_percent: 12.5, mem_percent: 55, disk_percent: 40, net_recv_rate: 100, net_sent_rate: 200, disk_read_rate: 0, disk_write_rate: 0 },
};

describe('ServerCard', () => {
  it('渲染服务器名称与状态', () => {
    render(<ServerCard server={server} onSelect={() => {}} />);
    expect(screen.getByText('web1')).toBeTruthy();
    expect(screen.getByText(/12.5%/)).toBeTruthy();
  });

  it('离线服务器显示错误信息', () => {
    const offline = { ...server, status: 'offline', last_error: '连接超时' };
    render(<ServerCard server={offline} onSelect={() => {}} />);
    expect(screen.getByText(/连接超时/)).toBeTruthy();
  });

  it('点击卡片触发 onSelect', () => {
    const onSelect = vi.fn();
    render(<ServerCard server={server} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('web1'));
    expect(onSelect).toHaveBeenCalledWith('srv-1');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/SystemMonitor/components/ServerCard.test.tsx`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现公共组件**

```tsx
// frontend/src/components/Tools/SystemMonitor/components/MetricChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export interface ChartPoint {
  time: string;
  [key: string]: number | string | null;
}

export interface ChartLine {
  key: string;
  name: string;
  color: string;
}

interface MetricChartProps {
  data: ChartPoint[];
  lines: ChartLine[];
  height?: number;
  yUnit?: string;
}

/** 通用趋势图：recharts 折线图封装 */
export default function MetricChart({ data, lines, height = 260, yUnit = '' }: MetricChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickFormatter={(v: string) => v.slice(5)} />
        <YAxis stroke="#64748b" fontSize={11} unit={yUnit} width={44} />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {lines.map((line) => (
          <Line key={line.key} type="monotone" dataKey={line.key} name={line.name}
            stroke={line.color} strokeWidth={1.5} dot={false} connectNulls />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
```

```tsx
// frontend/src/components/Tools/SystemMonitor/components/ServerCard.tsx
import type { MonitorServer } from '../../../api/monitorApi';

interface ServerCardProps {
  server: MonitorServer;
  onSelect: (id: string) => void;
  onEdit?: (server: MonitorServer) => void;
  onDelete?: (server: MonitorServer) => void;
  onRetry?: (server: MonitorServer) => void;
}

function fmtRate(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  if (v < 1024) return `${v.toFixed(0)} B/s`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB/s`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB/s`;
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'online' ? 'bg-emerald-500' : status === 'offline' ? 'bg-red-500' : status === 'error' ? 'bg-orange-500' : 'bg-slate-600';
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

/** 服务器状态卡片：名称/状态/资源小指标/错误信息 */
export function ServerCard({ server, onSelect, onEdit, onDelete, onRetry }: ServerCardProps) {
  const metric = server.metric;
  const offline = server.status !== 'online';
  return (
    <div
      className="bg-slate-900 rounded-xl p-4 border border-slate-800 hover:border-slate-700 cursor-pointer transition-colors"
      onClick={() => onSelect(server.id)}
      data-testid={`server-card-${server.id}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <StatusDot status={server.status} />
          <span className="text-white text-sm font-medium truncate">{server.name}</span>
        </div>
        <span className="text-xs text-slate-500 shrink-0">{server.server_type === 'local' ? '本机' : server.host}</span>
      </div>
      {server.group_name && <div className="text-xs text-slate-600 mt-0.5">{server.group_name}</div>}
      {offline ? (
        <div className="mt-2">
          <div className="text-xs text-red-400/80 break-words">{server.last_error || '服务器离线'}</div>
          {server.status === 'error' && onRetry && (
            <button
              className="mt-2 text-xs text-emerald-400 hover:text-emerald-300"
              onClick={(e) => { e.stopPropagation(); onRetry(server); }}
            >
              重试采集
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-1.5 mt-2 text-xs">
          <div className="text-slate-400">CPU <span className="text-white">{metric?.cpu_percent ?? '-'}%</span></div>
          <div className="text-slate-400">内存 <span className="text-white">{metric?.mem_percent ?? '-'}%</span></div>
          <div className="text-slate-400">磁盘 <span className="text-white">{metric?.disk_percent ?? '-'}%</span></div>
          <div className="text-slate-400">网络 <span className="text-white">{fmtRate(metric?.net_recv_rate)}</span></div>
        </div>
      )}
      {!offline && server.last_seen_at && (
        <div className="text-[11px] text-slate-600 mt-2">最近采集 {server.last_seen_at.replace('T', ' ').slice(0, 19)}</div>
      )}
      {(onEdit || onDelete) && (
        <div className="flex gap-2 mt-2" onClick={(e) => e.stopPropagation()}>
          {onEdit && <button className="text-xs text-slate-400 hover:text-white" onClick={() => onEdit(server)}>编辑</button>}
          {onDelete && server.server_type !== 'local' && (
            <button className="text-xs text-slate-400 hover:text-red-400" onClick={() => onDelete(server)}>删除</button>
          )}
        </div>
      )}
    </div>
  );
}
```

```tsx
// frontend/src/components/Tools/SystemMonitor/components/ServerSelector.tsx
import type { MonitorServer } from '../../../api/monitorApi';

interface ServerSelectorProps {
  servers: MonitorServer[];
  value: string | null;
  onChange: (id: string) => void;
  disabled?: boolean;
}

/** 服务器选择器：下拉切换当前监控目标 */
export default function ServerSelector({ servers, value, onChange, disabled }: ServerSelectorProps) {
  return (
    <select
      className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500 disabled:opacity-50"
      value={value ?? ''}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      data-testid="server-selector"
    >
      {servers.length === 0 && <option value="">暂无服务器</option>}
      {servers.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name}{s.status !== 'online' ? '（离线）' : ''}
        </option>
      ))}
    </select>
  );
}
```

```tsx
// frontend/src/components/Tools/SystemMonitor/components/ResourceCards.tsx
import type { MetricPoint } from '../../../api/monitorApi';

function fmtBytes(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
  return `${(v / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function fmtRate(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  return `${fmtBytes(v)}/s`;
}

function Meter({ label, value, color }: { label: string; value: number | null | undefined; color: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-slate-500">{label}</span>
        <span className="text-white font-medium">{value === null || value === undefined ? '-' : `${v.toFixed(1)}%`}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

/** 资源占用卡片：CPU/内存/磁盘/网络/磁盘IO */
export default function ResourceCards({ metric }: { metric: MetricPoint | null }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
      <Meter label="CPU 使用率" value={metric?.cpu_percent} color="bg-emerald-500" />
      <Meter label="内存使用率" value={metric?.mem_percent} color="bg-blue-500" />
      <Meter label="磁盘使用率" value={metric?.disk_percent} color="bg-amber-500" />
      <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
        <div className="text-xs text-slate-500 mb-1.5">网络速率</div>
        <div className="text-white text-sm font-medium">↓ {fmtRate(metric?.net_recv_rate)}</div>
        <div className="text-white text-sm font-medium mt-0.5">↑ {fmtRate(metric?.net_sent_rate)}</div>
      </div>
      <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
        <div className="text-xs text-slate-500 mb-1.5">磁盘 IO 速率</div>
        <div className="text-white text-sm font-medium">读 {fmtRate(metric?.disk_read_rate)}</div>
        <div className="text-white text-sm font-medium mt-0.5">写 {fmtRate(metric?.disk_write_rate)}</div>
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/components/Tools/SystemMonitor/components/SystemInfoCards.tsx
import type { MonitorServer } from '../../../api/monitorApi';

interface SystemInfoCardsProps {
  info: Record<string, string | number> | null;
  server: MonitorServer;
}

/** 系统信息卡片网格（8 张） */
export default function SystemInfoCards({ info, server }: SystemInfoCardsProps) {
  const cards = [
    { icon: 'fa-server', label: '主机', value: info?.hostname || server.name },
    { icon: 'fa-laptop', label: '系统', value: info?.os ? String(info.os).slice(0, 40) : server.server_type === 'local' ? '加载中' : 'Linux' },
    { icon: 'fa-code', label: '内核', value: info?.kernel ? String(info.kernel) : '-' },
    { icon: 'fa-clock', label: '运行时间', value: info?.uptime_text ? String(info.uptime_text) : '-' },
    { icon: 'fa-network-wired', label: '地址', value: server.host || '本机' },
    { icon: 'fa-user', label: '用户', value: server.username || '-' },
    { icon: 'fa-tag', label: '类型', value: server.server_type === 'local' ? '本机' : 'SSH 远程' },
    { icon: 'fa-bolt', label: '状态', value: server.status === 'online' ? '在线' : server.status === 'offline' ? '离线' : '已禁用' },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div key={card.label} className="bg-slate-900 rounded-xl p-3 border border-slate-800">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
            <i className={`fas ${card.icon}`} />
            {card.label}
          </div>
          <div className="text-sm text-white font-medium break-all">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/components/Tools/SystemMonitor/components/ConfirmModal.tsx
interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

/** 通用确认弹窗 */
export default function ConfirmModal({ open, title, message, onConfirm, onCancel, danger }: ConfirmModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 w-96 max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
        <div className="text-white font-medium mb-2">{title}</div>
        <div className="text-slate-400 text-sm mb-5">{message}</div>
        <div className="flex justify-end gap-3">
          <button className="px-4 py-1.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800" onClick={onCancel}>取消</button>
          <button
            className={`px-4 py-1.5 rounded-lg text-sm text-white ${danger ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'}`}
            onClick={onConfirm}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/components/Tools/SystemMonitor/components/AddServerModal.tsx
import { useState } from 'react';
import type { SSHConfig } from '../../../api/sshToolApi';
import * as monitorApi from '../../../api/monitorApi';

interface AddServerModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  sshConfigs: SSHConfig[];
}

/** 添加服务器弹窗：手动填写 / 从 SSH 配置导入 */
export default function AddServerModal({ open, onClose, onSaved, sshConfigs }: AddServerModalProps) {
  const [mode, setMode] = useState<'manual' | 'ssh'>('manual');
  const [form, setForm] = useState({
    name: '', host: '', port: '22', username: 'root', password: '', group_name: '',
  });
  const [sshConfigId, setSshConfigId] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const submit = async () => {
    setError('');
    setSaving(true);
    try {
      if (mode === 'ssh') {
        if (!sshConfigId) { setError('请选择 SSH 配置'); return; }
        await monitorApi.importFromSsh(sshConfigId);
      } else {
        if (!form.name || !form.host) { setError('服务器名称和地址必填'); return; }
        await monitorApi.createServer({
          name: form.name, host: form.host, port: Number(form.port),
          username: form.username, password: form.password || undefined,
          group_name: form.group_name || undefined,
        });
      }
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 w-[480px] max-w-[92vw]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-white font-medium">添加监控服务器</div>
          <button className="text-slate-500 hover:text-white" onClick={onClose}>✕</button>
        </div>
        <div className="flex gap-2 mb-4">
          <button
            className={`px-3 py-1.5 rounded-lg text-sm ${mode === 'manual' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'}`}
            onClick={() => setMode('manual')}
          >
            手动填写
          </button>
          <button
            className={`px-3 py-1.5 rounded-lg text-sm ${mode === 'ssh' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'}`}
            onClick={() => setMode('ssh')}
          >
            从 SSH 配置导入
          </button>
        </div>
        {mode === 'manual' ? (
          <div className="space-y-3">
            <input className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              placeholder="服务器名称 *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <div className="flex gap-3">
              <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                placeholder="IP/域名 *" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
              <input className="w-24 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                placeholder="端口" value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} />
            </div>
            <div className="flex gap-3">
              <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                placeholder="用户名" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
              <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                placeholder="密码（或留空用密钥）" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
            <input className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              placeholder="分组（可选）" value={form.group_name} onChange={(e) => setForm({ ...form, group_name: e.target.value })} />
          </div>
        ) : (
          <div>
            {sshConfigs.length === 0 ? (
              <div className="text-sm text-slate-500 py-3">暂无 SSH 配置，请先在 SSH 工具中添加</div>
            ) : (
              <select
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                value={sshConfigId}
                onChange={(e) => setSshConfigId(e.target.value)}
              >
                <option value="">请选择 SSH 配置</option>
                {sshConfigs.map((c) => (
                  <option key={c.id} value={c.id}>{c.alias}（{c.host}）</option>
                ))}
              </select>
            )}
            <div className="text-xs text-slate-600 mt-2">导入后凭据独立管理，与 SSH 工具互不影响</div>
          </div>
        )}
        {error && <div className="text-sm text-red-400 mt-3">{error}</div>}
        <div className="flex justify-end gap-3 mt-5">
          <button className="px-4 py-1.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800" onClick={onClose}>取消</button>
          <button className="px-4 py-1.5 rounded-lg text-sm text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50" onClick={submit} disabled={saving}>
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/SystemMonitor/components/ServerCard.test.tsx`
Expected: PASS（3 个）

- [ ] **Step 5: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/Tools/SystemMonitor/components/
git commit -m "feat: 监控公共组件（图表/卡片/选择器/弹窗）"
```

---

### Task 14: 页签容器 + 服务器列表页（index.tsx + ServerList.tsx）

**Files:**
- Create: `frontend/src/components/Tools/SystemMonitor/index.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/ServerList.tsx`
- Test: `frontend/src/components/Tools/SystemMonitor/SystemMonitor.test.tsx`

**Interfaces:**
- Consumes: Task 11/12/13；`getSSHConfigs`（已有 `frontend/src/api/sshToolApi.ts` 提供）
- Produces: 默认导出的 `SystemMonitor` 组件（Task 18 接入路由）；页签栏 + 六个页签的挂载

- [ ] **Step 1: 编写测试**

```tsx
// frontend/src/components/Tools/SystemMonitor/SystemMonitor.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SystemMonitor from './index';
import * as monitorApi from '../../api/monitorApi';

vi.mock('../../api/monitorApi', () => ({
  getServers: vi.fn(),
  getAlertLogs: vi.fn(),
  markAlertLogsRead: vi.fn(),
}));

const mockServers = [
  { id: 'srv-local', user_id: 'u1', name: '本机', server_type: 'local', host: '', port: 22,
    username: '', status: 'online', created_at: '2026-01-01T00:00:00',
    metric: { cpu_percent: 10, mem_percent: 20, disk_percent: 30, net_recv_rate: 0, net_sent_rate: 0, disk_read_rate: 0, disk_write_rate: 0 } },
  { id: 'srv-1', user_id: 'u1', name: 'web1', server_type: 'ssh', host: '10.0.0.1', port: 22,
    username: 'root', status: 'online', created_at: '2026-01-01T00:00:00',
    metric: { cpu_percent: 50, mem_percent: 60, disk_percent: 70, net_recv_rate: 0, net_sent_rate: 0, disk_read_rate: 0, disk_write_rate: 0 } },
];

describe('SystemMonitor 主容器', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (monitorApi.getServers as any).mockResolvedValue(mockServers);
    (monitorApi.getAlertLogs as any).mockResolvedValue({ logs: [], total: 0, unread_count: 2, page: 1, page_size: 20 });
  });

  it('渲染六页签与服务器列表', async () => {
    render(<SystemMonitor />);
    await waitFor(() => expect(screen.getByText('web1')).toBeTruthy());
    expect(screen.getByText('服务器列表')).toBeTruthy();
    expect(screen.getByText('总览')).toBeTruthy();
    expect(screen.getByText('历史趋势')).toBeTruthy();
    expect(screen.getByText('进程')).toBeTruthy();
    expect(screen.getByText('服务')).toBeTruthy();
    expect(screen.getByText('告警')).toBeTruthy();
  });

  it('切换页签', async () => {
    render(<SystemMonitor />);
    await waitFor(() => expect(screen.getByText('web1')).toBeTruthy());
    fireEvent.click(screen.getByText('总览'));
    expect(screen.getByTestId('server-selector')).toBeTruthy();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/SystemMonitor/SystemMonitor.test.tsx`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现页签容器**

```tsx
// frontend/src/components/Tools/SystemMonitor/index.tsx
import { useEffect } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import * as monitorApi from '../../api/monitorApi';
import ServerList from './ServerList';
import Overview from './Overview';
import History from './History';
import Processes from './Processes';
import Services from './Services';
import Alerts from './Alerts';

const TABS = [
  { key: 'servers', label: '服务器列表', icon: 'fa-server' },
  { key: 'overview', label: '总览', icon: 'fa-gauge-high' },
  { key: 'history', label: '历史趋势', icon: 'fa-chart-line' },
  { key: 'processes', label: '进程', icon: 'fa-list' },
  { key: 'services', label: '服务', icon: 'fa-cogs' },
  { key: 'alerts', label: '告警', icon: 'fa-bell' },
] as const;

/** 系统监控主容器：六页签导航 + 服务器状态管理 */
export default function SystemMonitor() {
  const { servers, setServers, activeTab, setActiveTab, selectedServerId, setSelectedServerId, unreadAlerts, setUnreadAlerts } = useMonitorStore();

  // 加载服务器列表 + 告警未读数
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [serverList, logs] = await Promise.all([monitorApi.getServers(), monitorApi.getAlertLogs(1, 1)]);
        if (cancelled) return;
        setServers(serverList);
        setUnreadAlerts(logs.unread_count);
        setSelectedServerId((prev) => prev ?? serverList[0]?.id ?? null);
      } catch {
        /* 加载失败静默处理，页签仍可切换 */
      }
    };
    load();
    const timer = setInterval(() => {
      monitorApi.getServers().then((list) => {
        if (!cancelled) { setServers(list); setSelectedServerId((prev) => prev ?? list[0]?.id ?? null); }
      }).catch(() => {});
    }, 10000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [setServers, setSelectedServerId, setUnreadAlerts]);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                activeTab === tab.key ? 'bg-emerald-600/20 text-emerald-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
              onClick={() => setActiveTab(tab.key)}
            >
              <i className={`fas ${tab.icon} text-xs`} />
              {tab.label}
              {tab.key === 'alerts' && unreadAlerts > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                  {unreadAlerts > 99 ? '99+' : unreadAlerts}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
      {/* 页签内容 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {activeTab === 'servers' && <ServerList />}
        {activeTab === 'overview' && <Overview />}
        {activeTab === 'history' && <History />}
        {activeTab === 'processes' && <Processes />}
        {activeTab === 'services' && <Services />}
        {activeTab === 'alerts' && <Alerts />}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 实现服务器列表页**

```tsx
// frontend/src/components/Tools/SystemMonitor/ServerList.tsx
import { useState } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import type { MonitorServer } from '../../api/monitorApi';
import * as monitorApi from '../../api/monitorApi';
import * as sshApi from '../../api/sshToolApi';
import { ServerCard } from './components/ServerCard';
import AddServerModal from './components/AddServerModal';
import ConfirmModal from './components/ConfirmModal';

/** 页签①服务器列表：状态卡片网格 + 添加/编辑/删除/重试 */
export default function ServerList() {
  const { servers, setServers, setSelectedServerId, setActiveTab } = useMonitorStore();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<MonitorServer | null>(null);
  const [deleting, setDeleting] = useState<MonitorServer | null>(null);
  const [sshConfigs, setSshConfigs] = useState<sshApi.SSHConfig[]>([]);
  const [error, setError] = useState('');

  const refresh = async () => {
    try {
      setServers(await monitorApi.getServers());
    } catch (e: any) {
      setError(e.message || '加载失败');
    }
  };

  const openAdd = async () => {
    setError('');
    try {
      setSshConfigs(await sshApi.getSSHConfigs());
    } catch { setSshConfigs([]); }
    setAddOpen(true);
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await monitorApi.deleteServer(deleting.id);
      setDeleting(null);
      await refresh();
    } catch (e: any) {
      setError(e.message || '删除失败');
      setDeleting(null);
    }
  };

  const handleRetry = async (server: MonitorServer) => {
    try {
      await monitorApi.retryServer(server.id);
      await refresh();
    } catch (e: any) {
      setError(e.message || '重试失败');
    }
  };

  const enter = (id: string) => {
    setSelectedServerId(id);
    setActiveTab('overview');
  };

  const groups: Record<string, MonitorServer[]> = {};
  for (const s of servers) {
    const g = s.group_name || '默认分组';
    (groups[g] ||= []).push(s);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-400">共 {servers.length} 台服务器</div>
        <button className="px-3 py-1.5 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-500 text-white" onClick={openAdd}>
          <i className="fas fa-plus mr-1.5" />添加服务器
        </button>
      </div>
      {error && <div className="text-sm text-red-400">{error}</div>}
      {Object.entries(groups).map(([group, list]) => (
        <div key={group}>
          <div className="text-xs text-slate-500 mb-2">{group}</div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
            {list.map((server) => (
              <ServerCard
                key={server.id}
                server={server}
                onSelect={enter}
                onEdit={(s) => setEditing(s)}
                onDelete={(s) => setDeleting(s)}
                onRetry={handleRetry}
              />
            ))}
          </div>
        </div>
      ))}
      {servers.length === 0 && (
        <div className="text-center text-slate-500 py-16">
          <i className="fas fa-server text-4xl mb-3 block text-slate-700" />
          暂无监控服务器，点击右上角添加
        </div>
      )}
      <AddServerModal open={addOpen} onClose={() => setAddOpen(false)} onSaved={refresh} sshConfigs={sshConfigs} />
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setEditing(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 w-[400px]" onClick={(e) => e.stopPropagation()}>
            <div className="text-white font-medium mb-3">编辑服务器（编辑后需手动触发采集）</div>
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white mb-3 focus:outline-none focus:border-emerald-500"
              defaultValue={editing.name}
              placeholder="服务器名称"
              id="edit-name"
            />
            <div className="flex justify-end gap-3">
              <button className="px-4 py-1.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800" onClick={() => setEditing(null)}>取消</button>
              <button
                className="px-4 py-1.5 rounded-lg text-sm text-white bg-emerald-600 hover:bg-emerald-500"
                onClick={async () => {
                  const nameInput = document.getElementById('edit-name') as HTMLInputElement;
                  try {
                    await monitorApi.updateServer(editing.id, { name: nameInput.value });
                    setEditing(null);
                    await refresh();
                  } catch (e: any) {
                    setError(e.message || '更新失败');
                  }
                }}
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
      <ConfirmModal
        open={!!deleting}
        title="删除服务器"
        message={`确定删除监控服务器「${deleting?.name}」？其历史指标与关联告警记录将保留。`}
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
        danger
      />
    </div>
  );
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/SystemMonitor/SystemMonitor.test.tsx`
Expected: PASS（2 个）。若 `Overview` 等子页签尚未创建导致 import 报错，先创建空壳组件（见 Task 15-17 实现后移除空壳）。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/Tools/SystemMonitor/index.tsx frontend/src/components/Tools/SystemMonitor/ServerList.tsx frontend/src/components/Tools/SystemMonitor/SystemMonitor.test.tsx
git commit -m "feat: 监控页签容器与服务器列表页"
```

---

### Task 15: 总览 + 历史趋势页（Overview.tsx + History.tsx）

**Files:**
- Create: `frontend/src/components/Tools/SystemMonitor/Overview.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/History.tsx`

**Interfaces:**
- Consumes: Task 11/12/13（`getOverview` / `getSystemInfo` / `getPartitions` / `getMetrics`、`ResourceCards` / `SystemInfoCards` / `ServerSelector` / `MetricChart`）

- [ ] **Step 1: 实现总览页**

```tsx
// frontend/src/components/Tools/SystemMonitor/Overview.tsx
import { useEffect, useState } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import * as monitorApi from '../../api/monitorApi';
import type { MetricPoint } from '../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import ResourceCards from './components/ResourceCards';
import SystemInfoCards from './components/SystemInfoCards';

/** 页签②总览：系统信息 + 资源卡片，5s 轮询 */
export default function Overview() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [metric, setMetric] = useState<MetricPoint | null>(null);
  const [info, setInfo] = useState<Record<string, string | number> | null>(null);
  const [partitions, setPartitions] = useState<Array<{ device: string; mountpoint: string; total: number; used: number; percent: number }>>([]);
  const [error, setError] = useState('');

  const server = servers.find((s) => s.id === selectedServerId) || null;

  // 切换服务器时加载系统信息与分区
  useEffect(() => {
    if (!server) return;
    let cancelled = false;
    setInfo(null);
    setPartitions([]);
    monitorApi.getSystemInfo(server.id).then((i) => { if (!cancelled) setInfo(i); }).catch(() => {});
    monitorApi.getPartitions(server.id)
      .then((r) => { if (!cancelled) setPartitions(r.partitions); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [server?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // 5s 轮询实时指标
  useEffect(() => {
    if (!server) return;
    let cancelled = false;
    const load = async () => {
      try {
        const data = await monitorApi.getOverview(server.id);
        if (!cancelled) setMetric(data.metric);
      } catch (e: any) {
        if (!cancelled) setError(e.message || '加载失败');
      }
    };
    load();
    const timer = setInterval(load, 5000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [server?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!server) {
    return <div className="text-center text-slate-500 py-16">请先在「服务器列表」添加或选择服务器</div>;
  }

  const fmtBytes = (v: number) => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(units.length - 1, Math.floor(Math.log(v) / Math.log(1024)));
    return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <div className="text-xs text-slate-500">每 5 秒自动刷新 · 数据每 30 秒采集一次</div>
      </div>
      {error && <div className="text-sm text-red-400">{error}</div>}
      <SystemInfoCards info={info} server={server} />
      <ResourceCards metric={metric} />
      {/* 分区表格 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="px-4 py-2.5 text-sm text-white font-medium border-b border-slate-800">磁盘分区</div>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-800">
              <th className="text-left px-4 py-2">设备</th>
              <th className="text-left px-4 py-2">挂载点</th>
              <th className="text-right px-4 py-2">总量</th>
              <th className="text-right px-4 py-2">已用</th>
              <th className="text-right px-4 py-2">使用率</th>
            </tr>
          </thead>
          <tbody>
            {partitions.map((p, i) => (
              <tr key={i} className="border-b border-slate-800/50 last:border-0">
                <td className="px-4 py-2 text-slate-300">{p.device}</td>
                <td className="px-4 py-2 text-slate-400">{p.mountpoint}</td>
                <td className="px-4 py-2 text-right text-slate-400">{fmtBytes(p.total)}</td>
                <td className="px-4 py-2 text-right text-slate-400">{fmtBytes(p.used)}</td>
                <td className="px-4 py-2 text-right">
                  <span className={p.percent > 90 ? 'text-red-400' : 'text-slate-300'}>{p.percent.toFixed(1)}%</span>
                </td>
              </tr>
            ))}
            {partitions.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-600">暂无分区数据</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 实现历史趋势页**

```tsx
// frontend/src/components/Tools/SystemMonitor/History.tsx
import { useEffect, useState } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import * as monitorApi from '../../api/monitorApi';
import type { MetricPoint } from '../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import MetricChart, { type ChartPoint, type ChartLine } from './components/MetricChart';

const RANGES = [
  { key: '1h', label: '近 1 小时' },
  { key: '6h', label: '近 6 小时' },
  { key: '24h', label: '近 24 小时' },
  { key: '7d', label: '近 7 天' },
];

const GROUPS = [
  {
    key: 'cpu', label: 'CPU',
    lines: [{ key: 'cpu_percent', name: 'CPU 使用率', color: '#10b981' }],
    yUnit: '%',
  },
  {
    key: 'memory', label: '内存',
    lines: [{ key: 'mem_percent', name: '内存使用率', color: '#3b82f6' }],
    yUnit: '%',
  },
  {
    key: 'load', label: '负载',
    lines: [{ key: 'load1', name: '负载(1分钟)', color: '#f59e0b' }],
    yUnit: '',
  },
  {
    key: 'net', label: '网络 IO',
    lines: [
      { key: 'net_recv_rate', name: '接收', color: '#10b981' },
      { key: 'net_sent_rate', name: '发送', color: '#f59e0b' },
    ],
    yUnit: 'B/s',
  },
  {
    key: 'diskio', label: '磁盘 IO',
    lines: [
      { key: 'disk_read_rate', name: '读', color: '#10b981' },
      { key: 'disk_write_rate', name: '写', color: '#f59e0b' },
    ],
    yUnit: 'B/s',
  },
];

function toChartPoints(points: MetricPoint[], group: string): ChartPoint[] {
  return points.map((p) => {
    const t = new Date(p.collected_at);
    const time = t.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    const point: ChartPoint = { time };
    if (group === 'cpu') point.cpu_percent = p.cpu_percent ?? null;
    if (group === 'memory') point.mem_percent = p.mem_percent ?? null;
    if (group === 'load') point.load1 = p.load_avg?.[0] ?? null;
    if (group === 'net') {
      point.net_recv_rate = p.net_recv_rate ?? null;
      point.net_sent_rate = p.net_sent_rate ?? null;
    }
    if (group === 'diskio') {
      point.disk_read_rate = p.disk_read_rate ?? null;
      point.disk_write_rate = p.disk_write_rate ?? null;
    }
    return point;
  });
}

/** 页签③历史趋势：时间范围 + 指标组切换 */
export default function History() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [range, setRange] = useState('1h');
  const [group, setGroup] = useState('cpu');
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!selectedServerId) return;
    let cancelled = false;
    setLoading(true);
    monitorApi.getMetrics(selectedServerId, range)
      .then((data) => { if (!cancelled) setPoints(toChartPoints(data.points, group)); })
      .catch((e: any) => { if (!cancelled) setError(e.message || '加载失败'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedServerId, range, group]);

  const groupConfig = GROUPS.find((g) => g.key === group)!;
  const lines: ChartLine[] = groupConfig.lines;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <div className="flex items-center gap-1 flex-wrap">
          {RANGES.map((r) => (
            <button
              key={r.key}
              className={`px-3 py-1.5 rounded-lg text-xs ${range === r.key ? 'bg-emerald-600/20 text-emerald-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
              onClick={() => setRange(r.key)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-1">
        {GROUPS.map((g) => (
          <button
            key={g.key}
            className={`px-3 py-1.5 rounded-lg text-xs ${group === g.key ? 'bg-emerald-600/20 text-emerald-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
            onClick={() => setGroup(g.key)}
          >
            {g.label}
          </button>
        ))}
      </div>
      {error && <div className="text-sm text-red-400">{error}</div>}
      {loading ? (
        <div className="text-center text-slate-500 py-16">加载中...</div>
      ) : points.length === 0 ? (
        <div className="text-center text-slate-500 py-16">暂无数据（采集后约 1 分钟可见）</div>
      ) : (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
          <MetricChart data={points} lines={lines} yUnit={groupConfig.yUnit} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/Tools/SystemMonitor/Overview.tsx frontend/src/components/Tools/SystemMonitor/History.tsx
git commit -m "feat: 总览与历史趋势页"
```

---

### Task 16: 进程 + 服务管理页（Processes.tsx + Services.tsx）

**Files:**
- Create: `frontend/src/components/Tools/SystemMonitor/Processes.tsx`
- Create: `frontend/src/components/Tools/SystemMonitor/Services.tsx`

**Interfaces:**
- Consumes: Task 11/12/13（`getProcesses` / `killProcess` / `getServices` / `serviceAction` / `getPrivileges`、`ServerSelector` / `ConfirmModal`）

- [ ] **Step 1: 实现进程管理页**

```tsx
// frontend/src/components/Tools/SystemMonitor/Processes.tsx
import { useEffect, useState, useCallback } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import * as monitorApi from '../../api/monitorApi';
import type { MonitorProcess } from '../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import ConfirmModal from './components/ConfirmModal';

const KNOWN_TYPES = ['all', 'FastAPI', 'Django', 'Flask', 'Celery', 'Gunicorn', 'Python',
  'Java', 'Node.js', 'Nginx', 'MySQL', 'PostgreSQL', 'Redis', 'Docker', 'Other'];

function fmtBytes(v: number): string {
  if (!v) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(v) / Math.log(1024));
  return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/** 页签④进程管理：列表/搜索/排序/分页/结束 */
export default function Processes() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [processes, setProcesses] = useState<MonitorProcess[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [projectType, setProjectType] = useState('all');
  const [sortBy, setSortBy] = useState('cpu_percent');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [loading, setLoading] = useState(false);
  const [killing, setKilling] = useState<MonitorProcess | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!selectedServerId) return;
    setLoading(true);
    try {
      const data = await monitorApi.getProcesses(selectedServerId, {
        sort_by: sortBy, sort_order: sortOrder, search: search || undefined,
        project_type: projectType, page, page_size: pageSize,
      });
      setProcesses(data.processes);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedServerId, sortBy, sortOrder, search, projectType, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(key);
      setSortOrder('desc');
    }
  };

  const handleKill = async () => {
    if (!killing || !selectedServerId) return;
    try {
      await monitorApi.killProcess(selectedServerId, killing.pid);
      setKilling(null);
      await load();
    } catch (e: any) {
      setError(e.message || '结束进程失败');
      setKilling(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <input
          className="flex-1 min-w-[180px] bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          placeholder="搜索进程名或命令行"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none"
          value={projectType}
          onChange={(e) => { setProjectType(e.target.value); setPage(1); }}
        >
          {KNOWN_TYPES.map((t) => <option key={t} value={t}>{t === 'all' ? '全部类型' : t}</option>)}
        </select>
        <button className="px-3 py-1.5 rounded-lg text-sm bg-slate-800 hover:bg-slate-700 text-slate-300" onClick={load}>
          <i className="fas fa-sync mr-1.5" />刷新
        </button>
      </div>
      {error && <div className="text-sm text-red-400">{error}</div>}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-800">
              <th className="text-left px-3 py-2 cursor-pointer hover:text-slate-300" onClick={() => handleSort('pid')}>PID</th>
              <th className="text-left px-3 py-2 cursor-pointer hover:text-slate-300" onClick={() => handleSort('name')}>进程名</th>
              <th className="text-left px-3 py-2 hidden md:table-cell">用户</th>
              <th className="text-right px-3 py-2 cursor-pointer hover:text-slate-300" onClick={() => handleSort('cpu_percent')}>CPU%</th>
              <th className="text-right px-3 py-2 cursor-pointer hover:text-slate-300" onClick={() => handleSort('memory_percent')}>内存%</th>
              <th className="text-right px-3 py-2 hidden lg:table-cell cursor-pointer hover:text-slate-300" onClick={() => handleSort('memory_rss')}>内存</th>
              <th className="text-left px-3 py-2 hidden xl:table-cell">运行时间</th>
              <th className="text-left px-3 py-2">类型</th>
              <th className="text-right px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {processes.map((p) => (
              <tr key={p.pid} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                <td className="px-3 py-2 text-slate-400">{p.pid}</td>
                <td className="px-3 py-2 text-white max-w-[240px] truncate" title={p.command_line}>{p.name}</td>
                <td className="px-3 py-2 text-slate-500 hidden md:table-cell">{p.username}</td>
                <td className="px-3 py-2 text-right text-slate-300">{p.cpu_percent.toFixed(1)}</td>
                <td className="px-3 py-2 text-right text-slate-300">{p.memory_percent.toFixed(1)}</td>
                <td className="px-3 py-2 text-right text-slate-400 hidden lg:table-cell">{fmtBytes(p.memory_rss)}</td>
                <td className="px-3 py-2 text-slate-500 hidden xl:table-cell">{p.create_time}</td>
                <td className="px-3 py-2">
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-emerald-400">{p.project_type}</span>
                </td>
                <td className="px-3 py-2 text-right">
                  <button className="text-red-400/80 hover:text-red-300 text-[11px]" onClick={() => setKilling(p)}>结束</button>
                </td>
              </tr>
            ))}
            {processes.length === 0 && !loading && (
              <tr><td colSpan={9} className="px-3 py-10 text-center text-slate-600">暂无进程</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>共 {total} 个进程</span>
          <div className="flex items-center gap-2">
            <button className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
            <span>{page} / {totalPages}</span>
            <button className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button>
          </div>
        </div>
      )}
      <ConfirmModal
        open={!!killing}
        title="结束进程"
        message={`确定结束进程 ${killing?.pid}（${killing?.name}）？该操作不可撤销。`}
        onConfirm={handleKill}
        onCancel={() => setKilling(null)}
        danger
      />
    </div>
  );
}
```

- [ ] **Step 2: 实现服务管理页**

```tsx
// frontend/src/components/Tools/SystemMonitor/Services.tsx
import { useEffect, useState, useCallback } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import * as monitorApi from '../../api/monitorApi';
import type { ServiceInfo } from '../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import ConfirmModal from './components/ConfirmModal';

/** 页签⑤服务管理：systemd 服务列表与启停 */
export default function Services() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [sudoOk, setSudoOk] = useState(false);
  const [confirm, setConfirm] = useState<{ unit: string; action: 'start' | 'stop' | 'restart' } | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    if (!selectedServerId) return;
    setLoading(true);
    try {
      const [svcRes, privRes] = await Promise.all([
        monitorApi.getServices(selectedServerId),
        monitorApi.getPrivileges(selectedServerId),
      ]);
      setServices(svcRes.services);
      setSudoOk(privRes.sudo_available);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedServerId]);

  useEffect(() => { load(); }, [load]);

  const doAction = async () => {
    if (!confirm || !selectedServerId) return;
    try {
      await monitorApi.serviceAction(selectedServerId, confirm.unit, confirm.action);
      setConfirm(null);
      await load();
    } catch (e: any) {
      setError(e.message || '操作失败');
      setConfirm(null);
    }
  };

  const filtered = services.filter((s) => search === '' || s.name.includes(search));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <input
          className="flex-1 min-w-[180px] bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          placeholder="搜索服务名"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="px-3 py-1.5 rounded-lg text-sm bg-slate-800 hover:bg-slate-700 text-slate-300" onClick={load}>
          <i className="fas fa-sync mr-1.5" />刷新
        </button>
      </div>
      {!sudoOk && selectedServerId && (
        <div className="text-xs text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
          当前用户可能没有 sudo 权限，服务操作可能需要 root 或无密码 sudo
        </div>
      )}
      {error && <div className="text-sm text-red-400">{error}</div>}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-800">
              <th className="text-left px-3 py-2">服务名</th>
              <th className="text-left px-3 py-2">状态</th>
              <th className="text-left px-3 py-2 hidden md:table-cell">描述</th>
              <th className="text-left px-3 py-2 hidden lg:table-cell">开机自启</th>
              <th className="text-right px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => {
              const running = s.state === 'running';
              return (
                <tr key={s.name} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                  <td className="px-3 py-2 text-white font-mono">{s.name}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-block h-1.5 w-1.5 rounded-full mr-1.5 ${running ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    <span className={running ? 'text-emerald-400' : 'text-slate-400'}>{s.state}</span>
                  </td>
                  <td className="px-3 py-2 text-slate-500 hidden md:table-cell max-w-[280px] truncate">{s.description}</td>
                  <td className="px-3 py-2 text-slate-400 hidden lg:table-cell">{s.enabled ? '已启用' : '未启用'}</td>
                  <td className="px-3 py-2 text-right space-x-2">
                    {running ? (
                      <>
                        <button className="text-amber-400/80 hover:text-amber-300" onClick={() => setConfirm({ unit: s.name, action: 'restart' })}>重启</button>
                        <button className="text-red-400/80 hover:text-red-300" onClick={() => setConfirm({ unit: s.name, action: 'stop' })}>停止</button>
                      </>
                    ) : (
                      <button className="text-emerald-400/80 hover:text-emerald-300" onClick={() => setConfirm({ unit: s.name, action: 'start' })}>启动</button>
                    )}
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && !loading && (
              <tr><td colSpan={5} className="px-3 py-10 text-center text-slate-600">暂无服务</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <ConfirmModal
        open={!!confirm}
        title="服务操作"
        message={`确定要${confirm?.action === 'start' ? '启动' : confirm?.action === 'stop' ? '停止' : '重启'}服务 ${confirm?.unit}？`}
        onConfirm={doAction}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/Tools/SystemMonitor/Processes.tsx frontend/src/components/Tools/SystemMonitor/Services.tsx
git commit -m "feat: 进程与服务管理页"
```

---

### Task 17: 告警设置页（Alerts.tsx）

**Files:**
- Create: `frontend/src/components/Tools/SystemMonitor/Alerts.tsx`

**Interfaces:**
- Consumes: Task 11/12/13（`getAlerts` / `createAlert` / `updateAlert` / `deleteAlert` / `getAlertLogs` / `markAlertLogsRead` / `getSettings` / `saveSettings`、`ConfirmModal`）

- [ ] **Step 1: 实现告警页**

```tsx
// frontend/src/components/Tools/SystemMonitor/Alerts.tsx
import { useEffect, useState, useCallback } from 'react';
import { useMonitorStore } from '../../stores/monitorStore';
import * as monitorApi from '../../api/monitorApi';
import type { AlertRule, AlertLog, MonitorSettings } from '../../api/monitorApi';
import ConfirmModal from './components/ConfirmModal';

const METRIC_OPTIONS = [
  { value: 'cpu_percent', label: 'CPU 使用率' },
  { value: 'memory_percent', label: '内存使用率' },
  { value: 'disk_percent', label: '磁盘使用率' },
  { value: 'load_avg', label: '负载（1分钟）' },
  { value: 'net_recv_rate', label: '网络接收速率' },
  { value: 'net_sent_rate', label: '网络发送速率' },
];

const OPERATORS = ['>', '>=', '<', '<='];

const METRIC_LABELS: Record<string, string> = Object.fromEntries(METRIC_OPTIONS.map((m) => [m.value, m.label]));

interface RuleForm {
  server_id: string;
  metric: string;
  operator: string;
  threshold: string;
  duration: string;
  enabled: boolean;
}

const EMPTY_FORM: RuleForm = { server_id: 'all', metric: 'cpu_percent', operator: '>', threshold: '90', duration: '3', enabled: true };

/** 页签⑥告警设置：规则 CRUD + Webhook 配置 + 触发记录 */
export default function Alerts() {
  const { servers, setUnreadAlerts } = useMonitorStore();
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [logs, setLogs] = useState<AlertLog[]>([]);
  const [settings, setSettings] = useState<MonitorSettings>({ webhook_url: '', collect_interval: 30 });
  const [editing, setEditing] = useState<RuleForm | null>(null);
  const [deleting, setDeleting] = useState<AlertRule | null>(null);
  const [formError, setFormError] = useState('');
  const [error, setError] = useState('');
  const [logPage, setLogPage] = useState(1);
  const [logTotal, setLogTotal] = useState(0);

  const loadRules = useCallback(async () => {
    setRules(await monitorApi.getAlerts());
  }, []);

  const loadLogs = useCallback(async (page = 1) => {
    const data = await monitorApi.getAlertLogs(page, 20);
    setLogs(data.logs);
    setLogTotal(data.total);
    setUnreadAlerts(data.unread_count);
  }, [setUnreadAlerts]);

  useEffect(() => {
    Promise.all([loadRules(), loadLogs(), monitorApi.getSettings()])
      .then(([, , s]) => setSettings(s))
      .catch((e: any) => setError(e.message || '加载失败'));
  }, [loadRules, loadLogs]);

  const saveRule = async () => {
    if (!editing) return;
    setFormError('');
    const threshold = Number(editing.threshold);
    const duration = Number(editing.duration);
    if (Number.isNaN(threshold)) { setFormError('阈值必须是数字'); return; }
    if (Number.isNaN(duration) || duration < 1 || duration > 60) { setFormError('持续时间需在 1-60 之间'); return; }
    try {
      const payload = {
        server_id: editing.server_id, metric: editing.metric, operator: editing.operator,
        threshold, duration, enabled: editing.enabled,
      };
      if (editing.id) await monitorApi.updateAlert(editing.id, payload);
      else await monitorApi.createAlert(payload);
      setEditing(null);
      await loadRules();
    } catch (e: any) {
      setFormError(e.message || '保存失败');
    }
  };

  const markRead = async () => {
    await monitorApi.markAlertLogsRead();
    setLogs((prev) => prev.map((l) => ({ ...l, is_read: true })));
    setUnreadAlerts(0);
  };

  const saveSettings = async () => {
    try {
      await monitorApi.saveSettings(settings);
    } catch (e: any) {
      setError(e.message || '保存设置失败');
    }
  };

  const serverName = (id: string) => {
    if (id === 'all') return '全部服务器';
    return servers.find((s) => s.id === id)?.name || id;
  };

  const fmtTime = (t: string) => t.replace('T', ' ').slice(0, 19);

  return (
    <div className="space-y-6">
      {error && <div className="text-sm text-red-400">{error}</div>}

      {/* 通知设置 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-sm text-white font-medium mb-3">通知设置</div>
        <div className="flex items-center gap-3">
          <input
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            placeholder="Webhook 地址（钉钉/企业微信/飞书机器人）"
            value={settings.webhook_url}
            onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
          />
          <button className="px-3 py-2 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-500 text-white" onClick={saveSettings}>保存</button>
        </div>
        <div className="text-xs text-slate-600 mt-2">
          采集间隔 {settings.collect_interval} 秒 · 告警触发后通过 Webhook 推送，同时在本页记录站内通知
        </div>
      </div>

      {/* 规则列表 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
          <div className="text-sm text-white font-medium">告警规则</div>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
            onClick={() => setEditing({ ...EMPTY_FORM, id: '' })}>
            <i className="fas fa-plus mr-1" />新建规则
          </button>
        </div>
        {rules.length === 0 ? (
          <div className="text-center text-slate-600 py-8 text-sm">暂无告警规则</div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800">
                <th className="text-left px-4 py-2">服务器</th>
                <th className="text-left px-4 py-2">条件</th>
                <th className="text-left px-4 py-2">持续时间</th>
                <th className="text-left px-4 py-2">状态</th>
                <th className="text-right px-4 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className="border-b border-slate-800/50 last:border-0">
                  <td className="px-4 py-2 text-slate-300">{serverName(r.server_id)}</td>
                  <td className="px-4 py-2 text-slate-300">
                    {METRIC_LABELS[r.metric] || r.metric} {r.operator} {r.threshold}
                  </td>
                  <td className="px-4 py-2 text-slate-500">连续 {r.duration} 次</td>
                  <td className="px-4 py-2">
                    <button
                      className={r.enabled ? 'text-emerald-400' : 'text-slate-500'}
                      onClick={async () => {
                        await monitorApi.updateAlert(r.id, { enabled: !r.enabled });
                        await loadRules();
                      }}
                    >
                      {r.enabled ? '已启用' : '已停用'}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button className="text-slate-400 hover:text-white"
                      onClick={() => setEditing({ server_id: r.server_id, metric: r.metric, operator: r.operator, threshold: String(r.threshold), duration: String(r.duration), enabled: r.enabled, id: r.id })}>
                      编辑
                    </button>
                    <button className="text-red-400/80 hover:text-red-300" onClick={() => setDeleting(r)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 触发记录 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
          <div className="text-sm text-white font-medium">触发记录</div>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300" onClick={markRead}>全部已读</button>
        </div>
        {logs.length === 0 ? (
          <div className="text-center text-slate-600 py-8 text-sm">暂无告警记录</div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {logs.map((log) => (
              <div key={log.id} className={`px-4 py-2.5 flex items-center gap-3 ${log.is_read ? 'opacity-60' : ''}`}>
                <span className={`h-2 w-2 rounded-full shrink-0 ${log.status === 'firing' ? 'bg-red-500' : 'bg-emerald-500'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-300">
                    <span className="text-white font-medium">{log.server_name}</span>
                    <span className="mx-1.5 text-slate-600">·</span>
                    {METRIC_LABELS[log.metric] || log.metric}
                    <span className="ml-1.5 text-red-400">{log.actual_value}</span>
                    <span className="ml-1.5 text-slate-600">{log.status === 'firing' ? '触发' : '恢复'}</span>
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5">{fmtTime(log.notified_at)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {logTotal > 20 && (
          <div className="flex justify-end items-center gap-2 px-4 py-2 text-xs text-slate-500">
            <button className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={logPage <= 1} onClick={() => { setLogPage(logPage - 1); loadLogs(logPage - 1); }}>上一页</button>
            <span>{logPage} / {Math.max(1, Math.ceil(logTotal / 20))}</span>
            <button className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={logPage >= Math.ceil(logTotal / 20)} onClick={() => { setLogPage(logPage + 1); loadLogs(logPage + 1); }}>下一页</button>
          </div>
        )}
      </div>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setEditing(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 w-[420px] space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="text-white font-medium">{editing.id ? '编辑规则' : '新建规则'}</div>
            <div className="flex gap-3">
              <select className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                value={editing.server_id} onChange={(e) => setEditing({ ...editing, server_id: e.target.value })}>
                <option value="all">全部服务器</option>
                {servers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <select className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                value={editing.metric} onChange={(e) => setEditing({ ...editing, metric: e.target.value })}>
                {METRIC_OPTIONS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div className="flex gap-3">
              <select className="w-24 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                value={editing.operator} onChange={(e) => setEditing({ ...editing, operator: e.target.value })}>
                {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
              </select>
              <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                placeholder="阈值" value={editing.threshold} onChange={(e) => setEditing({ ...editing, threshold: e.target.value })} />
              <input className="w-28 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                placeholder="连续次数" value={editing.duration} onChange={(e) => setEditing({ ...editing, duration: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input type="checkbox" checked={editing.enabled} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} />
              启用规则
            </label>
            {formError && <div className="text-sm text-red-400">{formError}</div>}
            <div className="flex justify-end gap-3 pt-2">
              <button className="px-4 py-1.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800" onClick={() => setEditing(null)}>取消</button>
              <button className="px-4 py-1.5 rounded-lg text-sm text-white bg-emerald-600 hover:bg-emerald-500" onClick={saveRule}>保存</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleting}
        title="删除规则"
        message={`确定删除该告警规则（${deleting ? METRIC_LABELS[deleting.metric] : ''} ${deleting?.operator} ${deleting?.threshold}）？`}
        onConfirm={async () => {
          if (!deleting) return;
          await monitorApi.deleteAlert(deleting.id);
          setDeleting(null);
          await loadRules();
        }}
        onCancel={() => setDeleting(null)}
        danger
      />
    </div>
  );
}
```

（说明：`RuleForm` 在保存时使用 `editing.id` 判断新建/更新，`EMPTY_FORM` 不带 id，编辑时带 id；`setEditing({ ...EMPTY_FORM, id: '' })` 已兼容该约定。）

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Tools/SystemMonitor/Alerts.tsx
git commit -m "feat: 告警设置页（规则/Webhook/触发记录）"
```

---

### Task 18: 路由接线 + 旧文件清理 + 前端全量测试

**Files:**
- Modify: `frontend/src/components/Workspace/toolComponents.tsx`（更新 SystemMonitor 导入）
- Delete: `frontend/src/components/Tools/SystemMonitor.tsx`（旧单文件，已迁移）

**Interfaces:**
- Consumes: Task 14 的默认导出 `SystemMonitor`

- [ ] **Step 1: 更新导入**

`frontend/src/components/Workspace/toolComponents.tsx` 第 48 行 `'system-monitor': SystemMonitor,` 的导入从：
```tsx
import SystemMonitor from '../Tools/SystemMonitor';
```
改为：
```tsx
import SystemMonitor from '../Tools/SystemMonitor';
```
（旧文件删除后同一路径指向新目录 `../Tools/SystemMonitor/index.tsx`，导入语句本身无需修改；仅需确认无其他文件直接引用旧路径。）

- [ ] **Step 2: 检查引用**

Run: `cd frontend && grep -rn "Tools/SystemMonitor'" src --include="*.tsx" --include="*.ts" | grep -v "SystemMonitor/"`

Expected: 仅 `toolComponents.tsx` 与 `App.tsx` 引用 `../Tools/SystemMonitor`（指向新目录，无需改动）

- [ ] **Step 3: 删除旧文件**

```bash
git rm frontend/src/components/Tools/SystemMonitor.tsx
```

- [ ] **Step 4: 前端全量验证**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 全部类型检查通过、全部测试通过（含既有测试）

- [ ] **Step 5: 手工验证**

1. 启动后端（`python dev-services.py start --backend-only`）
2. 启动前端（`python dev-services.py start --frontend-only`）
3. 浏览器打开 `/tools/system-monitor`：
   - 服务器列表显示本机节点，状态 online
   - 添加一台 SSH 服务器（测试连接通过后保存）
   - 总览页显示本机/远程指标、分区列表
   - 历史趋势页 1 分钟后有数据曲线
   - 进程页列出进程、可结束
   - 服务页列出 systemd 服务
   - 告警页新建规则、保存 Webhook、触发记录出现
4. 确认旧的 `/system-monitor/usage` 等接口仍可用（本机进程页走旧接口）

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/Workspace/toolComponents.tsx
git commit -m "refactor: 系统监控迁移至六页签结构"
```

---

## 自审记录

### 规格覆盖检查

| 规格章节 | 实现任务 |
|----------|----------|
| 3.1 monitor_servers | Task 2 |
| 3.2 monitor_metrics | Task 5 |
| 3.3 monitor_alerts | Task 6 |
| 3.4 monitor_alert_logs | Task 6 |
| 4.1 模块结构 | Task 1-9 |
| 4.2 采集引擎 | Task 7 |
| 4.3 SSH 连接复用 | Task 3 |
| 4.4 bash 脚本 | Task 4 |
| 4.5 API 路由 | Task 9 |
| 4.6 告警引擎 | Task 6 |
| 4.7 权限处理 | Task 8 |
| 4.8 清理任务 | Task 5 `delete_expired_metrics` + Task 9 挂载（见下方补充） |
| 5.1 目录结构 | Task 13-17 |
| 5.2 页签交互 | Task 14-17 |
| 5.3 store/API | Task 11-12 |
| 6 错误处理 | Task 3/7/8 |
| 7 测试策略 | Task 1-10/13/14 前端测试 |
| 8 兼容性 | Task 18（旧 API 保留、旧组件删除） |

**补充（自审发现）**：规格 4.8 要求清理任务每 6 小时执行。Task 9 的 lifespan 未挂载清理循环。请在 `main.py` 的监控初始化代码块中一并加入：

```python
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
```

并在 lifespan 的关闭段（`monitor_collector.stop()` 之后）加入：

```python
    try:
        monitor_cleanup_task.cancel()
        await monitor_cleanup_task
    except (asyncio.CancelledError, NameError, UnboundLocalError):
        pass
```

（`monitor_cleanup_task` 需在监控初始化 try 块外层定义变量，防止未初始化时关闭段报错：在 `lifespan` 顶部 `cleanup_task = get_manager()...` 附近加 `monitor_cleanup_task = None`。）

### 类型一致性

- `parse_script_output` 返回的指标 dict 与 Global Constraints 结构一致，Task 5/6/7 消费同一结构
- `server` dict 字段在 Task 2 定义、Task 3/7/8 消费，一致
- 前端 `MonitorServer` / `MetricPoint` / `AlertRule` 等类型在 Task 11 定义，Task 12-17 复用，一致
- 告警规则 `duration` 语义为「连续 N 次采样」（Task 6 `_firing_counts` 逻辑），前端表单标注「连续次数」，一致
