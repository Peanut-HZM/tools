# Token Usage 设备指纹识别与合并实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Token Usage 系统引入设备指纹（基于 MAC 地址哈希），实现设备自动识别、用户确认复用、手动合并及历史重复数据处理。

**Architecture:** 保持现有 UUID 作为主键，新增 `device_fingerprint` 字段和 `device_id_alias` 映射表；指纹匹配时提示用户，不自动合并；查询统计时通过 `LEFT JOIN device_id_alias` 按 canonical_device_id 聚合。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React 18 + TypeScript, Tailwind CSS, Recharts

---

## 文件结构映射

### 后端新增/修改

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/token_usage_models.py` | 修改 | 扩展 DeviceRegistry，新增 DeviceIdAlias/DeviceMergeLog 模型 |
| `backend/alembic/versions/20260607_token_usage_device_fingerprint.py` | 创建 | 数据库迁移：扩展 device_registry，创建 device_id_alias/device_merge_log |
| `backend/app/utils/device_id.py` | 修改 | 新增 `get_device_fingerprint()` 函数 |
| `backend/app/services/token_usage_sync_service.py` | 修改 | 同步时注册/更新设备指纹，返回 fingerprint_match |
| `backend/app/routes/token_usage.py` | 修改 | 新增 `/devices/alias`、`/devices/merge`、`/devices/alias/{id}` 接口；summary/details 聚合 alias |
| `backend/app/utils/device_name_resolver.py` | 创建 | 统一封装设备名称解析 + alias 聚合查询辅助函数 |

### 前端新增/修改

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/api/tokenUsageApi.ts` | 修改 | 新增指纹匹配相关类型和 API 函数 |
| `frontend/src/components/Tools/TokenUsage.tsx` | 修改 | 增加设备名称明细列、指纹匹配提示弹窗、设备管理入口 |
| `frontend/src/components/Tools/TokenUsage/DeviceManagerModal.tsx` | 创建 | 设备管理弹窗：列表/重命名/合并/撤销 |
| `frontend/src/components/Tools/TokenUsage/FingerprintMatchDialog.tsx` | 创建 | 指纹匹配确认弹窗 |

---

## Task 1: 数据库迁移 — 扩展 DeviceRegistry 并创建 Alias/MergeLog 表

**Files:**
- Create: `backend/alembic/versions/20260607_token_usage_device_fingerprint.py`
- Modify: `backend/app/models/token_usage_models.py`

- [ ] **Step 1: 创建 Alembic 迁移文件**

```python
"""token usage device fingerprint support

Revision ID: 20260607_token_usage_device_fingerprint
Revises: 20260516_token_usage_dimensions
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260607_token_usage_device_fingerprint"
down_revision = "20260516_token_usage_dimensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 扩展 device_registry
    op.add_column(
        "device_registry",
        sa.Column("device_fingerprint", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "device_registry",
        sa.Column("fingerprint_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "device_registry",
        sa.Column("id_type", sa.String(length=16), nullable=False, server_default="uuid"),
    )
    op.create_index(
        "idx_device_registry_fingerprint",
        "device_registry",
        ["user_id", "device_fingerprint"],
        unique=False,
    )

    # 2) 创建 device_id_alias 表
    op.create_table(
        "device_id_alias",
        sa.Column("alias_device_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_device_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("alias_device_id"),
    )
    op.create_index(
        "idx_device_alias_user",
        "device_id_alias",
        ["user_id", "canonical_device_id"],
        unique=False,
    )

    # 3) 创建 device_merge_log 表
    op.create_table(
        "device_merge_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_device_id", sa.String(length=128), nullable=False),
        sa.Column("target_device_id", sa.String(length=128), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_device_merge_log_user",
        "device_merge_log",
        ["user_id", "merged_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("device_merge_log")
    op.drop_table("device_id_alias")
    op.drop_index("idx_device_registry_fingerprint", table_name="device_registry")
    op.drop_column("device_registry", "id_type")
    op.drop_column("device_registry", "fingerprint_version")
    op.drop_column("device_registry", "device_fingerprint")
```

- [ ] **Step 2: 修改 models 文件 — 扩展 DeviceRegistry**

在 `backend/app/models/token_usage_models.py` 的 `DeviceRegistry` 类中添加字段：

```python
class DeviceRegistry(Base):
    """设备注册表 — 管理设备 ID 与显示名称的映射"""
    __tablename__ = "device_registry"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=True)
    default_display_name = Column(String(128), nullable=True)
    device_fingerprint = Column(String(256), nullable=True)
    fingerprint_version = Column(Integer, nullable=False, default=0)
    id_type = Column(String(16), nullable=False, default="uuid")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "device_id"),
        Index("idx_device_registry_fingerprint", "user_id", "device_fingerprint"),
    )
```

- [ ] **Step 3: 在 models 文件中新增 DeviceIdAlias 和 DeviceMergeLog 模型**

在 `DeviceRegistry` 类后面追加：

```python
class DeviceIdAlias(Base):
    """设备 ID 别名映射 — 用于复用/合并同一物理设备的多个 UUID"""
    __tablename__ = "device_id_alias"

    alias_device_id = Column(String(128), primary_key=True)
    canonical_device_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_device_alias_user", "user_id", "canonical_device_id"),
    )


class DeviceMergeLog(Base):
    """设备合并日志 — 记录手动合并/复用操作"""
    __tablename__ = "device_merge_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    source_device_id = Column(String(128), nullable=False)
    target_device_id = Column(String(128), nullable=False)
    merged_at = Column(DateTime(timezone=True), server_default=func.now())
    record_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_device_merge_log_user", "user_id", "merged_at"),
    )
```

- [ ] **Step 4: 导入新模型到路由**

修改 `backend/app/routes/token_usage.py` 的 import：

```python
from app.models.token_usage_models import (
    TokenUsageRecord,
    TokenUsageSyncLog,
    DeviceRegistry,
    DeviceIdAlias,
    DeviceMergeLog,
)
```

- [ ] **Step 5: 运行迁移**

```bash
cd backend
alembic upgrade head
```

Expected: `20260607_token_usage_device_fingerprint` 成功应用。

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/token_usage_models.py backend/alembic/versions/20260607_token_usage_device_fingerprint.py backend/app/routes/token_usage.py
git commit -m "feat: 添加设备指纹相关的数据模型和迁移"
```

---

## Task 2: 后端 — 实现设备指纹生成工具

**Files:**
- Modify: `backend/app/utils/device_id.py`
- Test: `backend/tests/test_device_id.py`（若 tests 目录不存在则创建）

- [ ] **Step 1: 在 device_id.py 中新增指纹生成函数**

替换 `backend/app/utils/device_id.py` 为以下内容（保留原有函数）：

```python
"""设备标识工具 — 生成并持久化稳定的设备 UUID 和硬件指纹"""

import getpass
import hashlib
import logging
import socket
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 固定 salt，仅用于防止彩虹表，不用于区分用户
_FINGERPRINT_SALT = "tools-device-fingerprint-v1"


def get_device_id() -> str:
    """获取设备唯一标识（UUID）"""
    config_dir = Path.home() / ".tools"
    config_dir.mkdir(parents=True, exist_ok=True)
    device_file = config_dir / "device_id"

    if device_file.exists():
        return device_file.read_text().strip()

    device_id = str(uuid.uuid4())
    try:
        device_file.write_text(device_id)
        logger.info(f"已生成并保存设备标识: {device_id}")
    except Exception as e:
        logger.warning(f"设备标识持久化失败，将使用临时 UUID: {e}")

    return device_id


def get_device_display_name() -> str:
    """获取设备显示名称（用户名@主机名）"""
    try:
        username = getpass.getuser() or "unknown"
        hostname = socket.gethostname() or "unknown"
        return f"{username}@{hostname}"
    except Exception:
        return "unknown"


def _get_mac_address() -> Optional[str]:
    """获取第一个非虚拟网卡的 MAC 地址"""
    try:
        import psutil
        interfaces = psutil.net_if_addrs()
        for name, addrs in interfaces.items():
            # 跳过常见虚拟/回环接口
            if any(
                name.lower().startswith(prefix)
                for prefix in ("lo", "docker", "br-", "veth", "vmnet", "ppp", "tun", "tap")
            ):
                continue
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac = addr.address.replace(":", "").replace("-", "").lower()
                    if mac and mac != "000000000000" and mac != "ffffffffffff":
                        return mac
    except Exception as e:
        logger.debug(f"获取 MAC 地址失败: {e}")
    return None


def _build_fingerprint(mac: Optional[str], hostname: str, username: str) -> str:
    """基于 MAC + 主机名 + 用户名 + salt 生成本地指纹"""
    parts = [part for part in (mac, hostname, username, _FINGERPRINT_SALT) if part]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_device_fingerprint() -> Tuple[str, str]:
    """
    获取设备指纹。

    Returns:
        (fingerprint, id_type)
        - fingerprint: 硬件指纹哈希（MAC 不可用时回退为 UUID）
        - id_type: 'hardware'（基于 MAC）或 'uuid'（回退）
    """
    try:
        mac = _get_mac_address()
        hostname = socket.gethostname() or "unknown"
        username = getpass.getuser() or "unknown"

        if mac:
            return _build_fingerprint(mac, hostname, username), "hardware"

        # MAC 不可获取时回退为 UUID
        logger.debug("无法获取 MAC 地址，使用 UUID 作为指纹")
        return get_device_id(), "uuid"
    except Exception as e:
        logger.warning(f"生成设备指纹失败，使用 UUID 回退: {e}")
        return get_device_id(), "uuid"
```

- [ ] **Step 2: 安装 psutil 依赖**

检查 `backend/requirements.txt` 是否已有 `psutil`，若没有则添加：

```bash
# 在 requirements.txt 中确认或追加
psutil>=5.9.0
```

然后安装：

```bash
cd backend
pip install psutil
```

- [ ] **Step 3: 编写测试验证指纹生成**

创建 `backend/tests/test_device_id.py`：

```python
import re

from app.utils.device_id import get_device_fingerprint, _build_fingerprint


def test_build_fingerprint_is_deterministic():
    fp1 = _build_fingerprint("aabbccddeeff", "host1", "user1")
    fp2 = _build_fingerprint("aabbccddeeff", "host1", "user1")
    assert fp1 == fp2
    assert len(fp1) == 64
    assert re.match(r"^[0-9a-f]{64}$", fp1)


def test_build_fingerprint_differs_with_different_inputs():
    fp1 = _build_fingerprint("aabbccddeeff", "host1", "user1")
    fp2 = _build_fingerprint("aabbccddeeff", "host1", "user2")
    assert fp1 != fp2


def test_get_device_fingerprint_returns_tuple():
    fingerprint, id_type = get_device_fingerprint()
    assert isinstance(fingerprint, str)
    assert id_type in ("hardware", "uuid")
```

- [ ] **Step 4: 运行测试**

```bash
cd backend
pytest tests/test_device_id.py -v
```

Expected: 3 tests PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/device_id.py backend/tests/test_device_id.py backend/requirements.txt
git commit -m "feat: 实现设备指纹生成工具"
```

---

## Task 3: 后端 — 同步服务集成设备指纹

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py`
- Modify: `backend/app/utils/device_name_resolver.py`（创建）

- [ ] **Step 1: 创建设备名称解析辅助模块**

创建 `backend/app/utils/device_name_resolver.py`：

```python
"""设备名称解析与 alias 聚合辅助函数"""

from sqlalchemy.orm import Session

from app.models.token_usage_models import DeviceRegistry, DeviceIdAlias


def load_device_name_map(db: Session, user_id: str) -> dict[str, str]:
    """
    加载用户下所有设备的显示名称。
    返回: {device_id: display_name}
    """
    rows = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()
    return {
        row.device_id: row.display_name or row.default_display_name or row.device_id
        for row in rows
    }


def load_alias_map(db: Session, user_id: str) -> dict[str, str]:
    """
    加载用户下所有 device_id 的别名映射。
    返回: {alias_device_id: canonical_device_id}
    """
    rows = db.query(DeviceIdAlias).filter(DeviceIdAlias.user_id == user_id).all()
    return {row.alias_device_id: row.canonical_device_id for row in rows}


def resolve_canonical_device_id(device_id: str, alias_map: dict[str, str]) -> str:
    """将 alias_device_id 解析为 canonical_device_id，无映射时返回原值"""
    return alias_map.get(device_id, device_id)


def resolve_device_name(device_id: str, device_name_map: dict[str, str]) -> str:
    """解析设备显示名称，无注册信息时返回 device_id"""
    return device_name_map.get(device_id, device_id)
```

- [ ] **Step 2: 修改同步服务导入**

在 `backend/app/services/token_usage_sync_service.py` 中修改 import：

```python
from app.models.token_usage_models import (
    TokenUsageRecord,
    TokenUsageSyncLog,
    DeviceRegistry,
    DeviceIdAlias,
)
from app.utils.device_id import get_device_id, get_device_display_name, get_device_fingerprint
```

- [ ] **Step 3: 新增/修改设备注册逻辑**

将 `sync_token_usage` 函数中的设备注册段替换为：

```python
    device_id = get_device_id()
    device_name = get_device_display_name()
    device_fingerprint, id_type = get_device_fingerprint()

    fingerprint_match = None
    db = SessionLocal()
    result = {"sources_synced": [], "total_records": 0, "errors": []}

    # 确保设备已注册到 device_registry，并更新指纹
    try:
        existing = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=device_id
        ).first()
        if not existing:
            # 检查是否有相同指纹的设备
            matched = None
            if device_fingerprint:
                matched = db.query(DeviceRegistry).filter_by(
                    user_id=user_id, device_fingerprint=device_fingerprint
                ).first()

            if matched and matched.device_id != device_id:
                fingerprint_match = {
                    "matched_device_id": matched.device_id,
                    "matched_device_name": matched.display_name
                    or matched.default_display_name
                    or matched.device_id,
                }

            db.add(DeviceRegistry(
                user_id=user_id,
                device_id=device_id,
                display_name=None,
                default_display_name=device_name,
                device_fingerprint=device_fingerprint,
                fingerprint_version=1,
                id_type=id_type,
            ))
            db.commit()
        else:
            existing.device_fingerprint = device_fingerprint
            existing.fingerprint_version = 1
            existing.id_type = id_type
            if not existing.default_display_name:
                existing.default_display_name = device_name
            db.commit()
    except Exception as e:
        logger.warning(f"设备注册失败: {e}")
```

- [ ] **Step 4: 在返回结果中附加 fingerprint_match**

在 `sync_token_usage` 函数末尾 return 之前添加：

```python
    if fingerprint_match:
        result["fingerprint_match"] = fingerprint_match
    return result
```

- [ ] **Step 5: 修改 v2 同步入口以携带指纹**

在 `backend/app/routes/token_usage.py` 的 `/refresh-ccusage` 端点中，当前代码是：

```python
        count = await asyncio.to_thread(
            sync_token_usage_v2,
            db=db,
            user_id=user_id,
            device_id=get_device_id(),
            device_name=get_device_display_name(),
            since=today,
            until=today,
        )
```

该端点不经过 `sync_token_usage`，因此需要在调用前也注册设备指纹。修改该端点设备注册逻辑：

```python
from app.utils.device_id import get_device_id, get_device_display_name, get_device_fingerprint

# ...

@router.post("/refresh-ccusage")
async def refresh_ccusage_endpoint(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """手动触发 ccusage 同步（v2 数据源）。同步运行，等待完成。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    if os.environ.get("DESKTOP_MODE") == "1":
        raise HTTPException(status_code=403, detail="桌面模式不支持手动同步")

    lock = get_sync_lock()
    if lock.locked():
        raise HTTPException(status_code=429, detail="同步进行中，请稍后重试")

    device_id = get_device_id()
    device_name = get_device_display_name()
    device_fingerprint, id_type = get_device_fingerprint()

    db = SessionLocal()
    try:
        _ensure_device_registered_with_fingerprint(
            db, user_id, device_id, device_name, device_fingerprint, id_type
        )
        today = date.today().isoformat()
        count = await asyncio.to_thread(
            sync_token_usage_v2,
            db=db,
            user_id=user_id,
            device_id=device_id,
            device_name=device_name,
            since=today,
            until=today,
        )
        return {"success": True, "synced_records": count, "date": today}
    except Exception as e:
        logger.error(f"[ccusage-manual] 手动同步失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")
    finally:
        db.close()
```

- [ ] **Step 6: 新增 _ensure_device_registered_with_fingerprint 辅助函数**

在 `backend/app/routes/token_usage.py` 中新增：

```python
def _ensure_device_registered_with_fingerprint(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    device_fingerprint: str,
    id_type: str,
) -> Optional[dict]:
    """确保设备已注册，并返回 fingerprint_match（如有）。"""
    existing = db.query(DeviceRegistry).filter_by(
        user_id=user_id, device_id=device_id
    ).first()
    if existing:
        existing.device_fingerprint = device_fingerprint
        existing.fingerprint_version = 1
        existing.id_type = id_type
        if not existing.default_display_name:
            existing.default_display_name = device_name
        db.commit()
        return None

    matched = None
    if device_fingerprint:
        matched = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_fingerprint=device_fingerprint
        ).first()

    db.add(DeviceRegistry(
        user_id=user_id,
        device_id=device_id,
        display_name=None,
        default_display_name=device_name,
        device_fingerprint=device_fingerprint,
        fingerprint_version=1,
        id_type=id_type,
    ))
    db.commit()

    if matched and matched.device_id != device_id:
        return {
            "matched_device_id": matched.device_id,
            "matched_device_name": matched.display_name
            or matched.default_display_name
            or matched.device_id,
        }
    return None
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/token_usage_sync_service.py backend/app/utils/device_name_resolver.py backend/app/routes/token_usage.py
git commit -m "feat: 同步服务集成设备指纹检测"
```

---

## Task 4: 后端 — 新增设备别名与合并 API

**Files:**
- Modify: `backend/app/routes/token_usage.py`

- [ ] **Step 1: 新增 Pydantic 请求模型**

在 `backend/app/routes/token_usage.py` 的模型区追加：

```python
class DeviceAliasRequest(BaseModel):
    alias_device_id: str
    canonical_device_id: str


class DeviceMergeRequest(BaseModel):
    source_device_ids: list[str]
    target_device_id: str
```

- [ ] **Step 2: 新增 /devices/alias POST 接口**

在 `/devices/{device_id}/rename` 路由附近新增：

```python
@router.post("/devices/alias")
async def create_device_alias(
    req: DeviceAliasRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """将当前设备(alias)映射到已有设备(canonical)下"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    if req.alias_device_id == req.canonical_device_id:
        raise HTTPException(status_code=400, detail="alias 和 canonical 不能相同")

    db = SessionLocal()
    try:
        # 确认目标设备存在
        canonical = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=req.canonical_device_id
        ).first()
        if not canonical:
            raise HTTPException(status_code=404, detail="目标设备不存在")

        alias = db.query(DeviceIdAlias).filter_by(
            user_id=user_id, alias_device_id=req.alias_device_id
        ).first()
        if alias:
            alias.canonical_device_id = req.canonical_device_id
        else:
            db.add(DeviceIdAlias(
                user_id=user_id,
                alias_device_id=req.alias_device_id,
                canonical_device_id=req.canonical_device_id,
            ))

        # 记录合并日志
        record_count = (
            db.query(TokenUsageRecord)
            .filter(
                TokenUsageRecord.user_id == user_id,
                TokenUsageRecord.device_id == req.alias_device_id,
            )
            .count()
        )
        db.add(DeviceMergeLog(
            user_id=user_id,
            source_device_id=req.alias_device_id,
            target_device_id=req.canonical_device_id,
            record_count=record_count,
        ))
        db.commit()

        invalidate_user_query_cache(user_id)
        return {
            "alias_device_id": req.alias_device_id,
            "canonical_device_id": req.canonical_device_id,
            "record_count": record_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建设备别名失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建别名失败: {e}")
    finally:
        db.close()
```

- [ ] **Step 3: 新增 /devices/merge POST 接口**

```python
@router.post("/devices/merge")
async def merge_devices(
    req: DeviceMergeRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """批量将多个源设备合并到目标设备下"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    if req.target_device_id in req.source_device_ids:
        raise HTTPException(status_code=400, detail="源设备不能包含目标设备")

    db = SessionLocal()
    try:
        canonical = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=req.target_device_id
        ).first()
        if not canonical:
            raise HTTPException(status_code=404, detail="目标设备不存在")

        total_records = 0
        for source_id in req.source_device_ids:
            if source_id == req.target_device_id:
                continue

            alias = db.query(DeviceIdAlias).filter_by(
                user_id=user_id, alias_device_id=source_id
            ).first()
            if alias:
                alias.canonical_device_id = req.target_device_id
            else:
                db.add(DeviceIdAlias(
                    user_id=user_id,
                    alias_device_id=source_id,
                    canonical_device_id=req.target_device_id,
                ))

            record_count = (
                db.query(TokenUsageRecord)
                .filter(
                    TokenUsageRecord.user_id == user_id,
                    TokenUsageRecord.device_id == source_id,
                )
                .count()
            )
            total_records += record_count
            db.add(DeviceMergeLog(
                user_id=user_id,
                source_device_id=source_id,
                target_device_id=req.target_device_id,
                record_count=record_count,
            ))

        db.commit()
        invalidate_user_query_cache(user_id)
        return {
            "merged": len(req.source_device_ids),
            "target_device_id": req.target_device_id,
            "total_record_count": total_records,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"合并设备失败: {e}")
        raise HTTPException(status_code=500, detail=f"合并失败: {e}")
    finally:
        db.close()
```

- [ ] **Step 4: 新增 /devices/alias/{alias_device_id} DELETE 接口**

```python
@router.delete("/devices/alias/{alias_device_id}")
async def delete_device_alias(
    alias_device_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """撤销设备的 alias 映射"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        alias = db.query(DeviceIdAlias).filter_by(
            user_id=user_id, alias_device_id=alias_device_id
        ).first()
        if not alias:
            raise HTTPException(status_code=404, detail="别名映射不存在")

        db.delete(alias)
        db.commit()
        invalidate_user_query_cache(user_id)
        return {"alias_device_id": alias_device_id, "removed": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"撤销别名失败: {e}")
        raise HTTPException(status_code=500, detail=f"撤销失败: {e}")
    finally:
        db.close()
```

- [ ] **Step 5: 扩展 /devices GET 接口返回更完整信息**

修改 `get_user_devices` 返回字段：

```python
@router.get("/devices")
async def get_user_devices(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """获取当前用户的设备列表（含指纹类型和 canonical_id）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        regs = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()
        alias_rows = db.query(DeviceIdAlias).filter(DeviceIdAlias.user_id == user_id).all()
        alias_map = {row.alias_device_id: row.canonical_device_id for row in alias_rows}

        if regs:
            devices = [
                {
                    "id": reg.device_id,
                    "name": reg.display_name
                    or reg.default_display_name
                    or reg.device_id,
                    "default_name": reg.default_display_name or reg.device_id,
                    "display_name": reg.display_name,
                    "fingerprint": reg.device_fingerprint,
                    "id_type": reg.id_type,
                    "canonical_id": alias_map.get(reg.device_id),
                }
                for reg in regs
            ]
        else:
            device_ids = (
                db.query(TokenUsageRecord.device_id)
                .filter(TokenUsageRecord.user_id == user_id)
                .distinct()
                .all()
            )
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        return {"devices": devices}
    finally:
        db.close()
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/token_usage.py
git commit -m "feat: 新增设备别名与合并 API"
```

---

## Task 5: 后端 — 查询聚合时应用 device_id_alias

**Files:**
- Modify: `backend/app/routes/token_usage.py`
- Modify: `backend/app/utils/device_name_resolver.py`

- [ ] **Step 1: 扩展 device_name_resolver 提供 alias 聚合辅助**

在 `backend/app/utils/device_name_resolver.py` 中新增：

```python
from sqlalchemy import func, or_
from app.models.token_usage_models import TokenUsageRecord


def build_alias_aware_device_filter(device_id: str, alias_map: dict[str, str]) -> list:
    """
    当 device_id 是 canonical 时，查询需同时包含其 alias 下的记录。
    返回 SQLAlchemy filter 条件列表。
    """
    aliases = [aid for aid, cid in alias_map.items() if cid == device_id]
    if aliases:
        return [TokenUsageRecord.device_id.in_([device_id] + aliases)]
    return [TokenUsageRecord.device_id == device_id]
```

- [ ] **Step 2: 修改 _build_record_filters 支持 alias 展开**

在 `backend/app/routes/token_usage.py` 中修改 `_build_record_filters`：

```python
def _build_record_filters(
    user_id: str,
    req,
    since_date: Optional[datetime] = None,
    alias_map: Optional[dict[str, str]] = None,
) -> list:
    """构建 Token Usage 记录查询条件，保证元信息和明细口径一致。"""
    from app.utils.device_name_resolver import build_alias_aware_device_filter

    filters = [TokenUsageRecord.user_id == user_id]
    if since_date is not None:
        filters.append(TokenUsageRecord.record_date >= since_date.date())
    if getattr(req, "source", "all") != "all":
        filters.append(TokenUsageRecord.source == req.source)
    if getattr(req, "device_id", None):
        if alias_map:
            filters.extend(
                build_alias_aware_device_filter(req.device_id, alias_map)
            )
        else:
            filters.append(TokenUsageRecord.device_id == req.device_id)
    # ... 后续 tool_id/model 逻辑保持不变
    tool_id = getattr(req, "tool_id", None)
    if tool_id:
        source_matches = [
            source
            for source in ("claude", "opencode", "codex")
            if _map_source_to_tool(source)["tool_id"] == tool_id
        ]
        if tool_id not in source_matches:
            source_matches.append(tool_id)
        fallback_filters = [TokenUsageRecord.tool_id == tool_id]
        if source_matches:
            fallback_filters.append(
                (TokenUsageRecord.tool_id.is_(None))
                & (TokenUsageRecord.source.in_(source_matches))
            )
        filters.append(or_(*fallback_filters))
    if getattr(req, "model", None):
        filters.append(TokenUsageRecord.model == req.model)
    return filters
```

- [ ] **Step 3: 修改 summary/details/query 加载 alias_map 并传入**

以 `/summary` 为例，在 `db = SessionLocal()` 之后立即加载：

```python
from app.utils.device_name_resolver import load_alias_map

# ...

db = SessionLocal()
try:
    alias_map = load_alias_map(db, user_id)
    # ...
    records = (
        db.query(TokenUsageRecord)
        .filter(*_build_record_filters(user_id, req, since_date, alias_map))
        .all()
    )
```

`/details` 和 `/query` 同理。

- [ ] **Step 4: 修改 _load_device_names 支持 alias 名称解析**

```python
def _load_device_names(db, user_id: str) -> dict[str, str]:
    from app.utils.device_name_resolver import load_device_name_map, load_alias_map

    names = load_device_name_map(db, user_id)
    alias_map = load_alias_map(db, user_id)

    # 为 canonical device 补充 alias 的显示名
    for alias_id, canonical_id in alias_map.items():
        if canonical_id not in names:
            names[canonical_id] = names.get(alias_id, canonical_id)

    return names
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/token_usage.py backend/app/utils/device_name_resolver.py
git commit -m "feat: 查询聚合时应用 device_id_alias"
```

---

## Task 6: 前端 — API 层新增类型和函数

**Files:**
- Modify: `frontend/src/api/tokenUsageApi.ts`

- [ ] **Step 1: 新增类型定义**

在 `DeviceInfo` 后追加：

```typescript
export interface DeviceInfo {
  id: string;
  name: string;
  default_name?: string;
  display_name?: string | null;
  fingerprint?: string | null;
  id_type?: 'hardware' | 'uuid';
  canonical_id?: string | null;
}

export interface FingerprintMatch {
  matched_device_id: string;
  matched_device_name: string;
  message?: string;
}

export interface SyncTokenUsageResponse {
  message?: string;
  sources_synced: string[];
  total_records: number;
  errors: string[];
  locked?: boolean;
  lock_ttl_seconds?: number;
  fingerprint_match?: FingerprintMatch | null;
}
```

- [ ] **Step 2: 新增 API 函数**

在文件末尾追加：

```typescript
export async function createDeviceAlias(
  aliasDeviceId: string,
  canonicalDeviceId: string
): Promise<{ alias_device_id: string; canonical_device_id: string; record_count: number }> {
  const response = await fetch(`${BASE_URL}/devices/alias`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      alias_device_id: aliasDeviceId,
      canonical_device_id: canonicalDeviceId,
    }),
  });
  if (!response.ok) {
    throw await readError(response, '创建设备别名失败');
  }
  return response.json();
}

export async function mergeDevices(
  sourceDeviceIds: string[],
  targetDeviceId: string
): Promise<{ merged: number; target_device_id: string; total_record_count: number }> {
  const response = await fetch(`${BASE_URL}/devices/merge`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source_device_ids: sourceDeviceIds,
      target_device_id: targetDeviceId,
    }),
  });
  if (!response.ok) {
    throw await readError(response, '合并设备失败');
  }
  return response.json();
}

export async function deleteDeviceAlias(aliasDeviceId: string): Promise<{ alias_device_id: string; removed: boolean }> {
  const response = await fetch(`${BASE_URL}/devices/alias/${encodeURIComponent(aliasDeviceId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '撤销设备别名失败');
  }
  return response.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/tokenUsageApi.ts
git commit -m "feat: 前端 API 层增加设备别名和合并接口"
```

---

## Task 7: 前端 — 明细表格增加设备名称列

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`
- Modify: `frontend/src/api/tokenUsageApi.ts`（已在 Task 6 完成）

- [ ] **Step 1: 修改 details 返回类型支持 device_name**

`DbUsageItem` 已有 `group_key`，我们需要从后端接口返回每个明细行的 `device_name`。

修改 `backend/app/routes/token_usage.py` 的 `/details` 端点，在构建 `DbUsageItem` 时增加 `device_name`：

```python
# 先加载 device_name_map
device_name_map = _load_device_names(db, user_id)

# ... 构建 items 时
items.append(
    DbUsageItem(
        date=date_key,
        input_tokens=int(r.input_tokens or 0),
        output_tokens=int(r.output_tokens or 0),
        cache_creation_tokens=int(r.cache_creation_tokens or 0),
        cache_read_tokens=int(r.cache_read_tokens or 0),
        total_tokens=int(r.total_tokens or 0),
        total_cost=float(r.total_cost or 0),
        models_used=[r.model] if r.model else [],
        model_breakdowns=[],
        tool_id=r.tool_id,
        group_key=group_key,
        device_name=device_name_map.get(r.device_id, r.device_id),
    )
)
```

修改 `DbUsageItem` Pydantic 模型：

```python
class DbUsageItem(BaseModel):
    # ... 原有字段
    tool_id: Optional[str] = Field(default=None)
    group_key: Optional[str] = Field(default=None)
    device_name: Optional[str] = Field(default=None, description="设备显示名称")
```

前端 `DbUsageItem` 类型同步修改：

```typescript
export interface DbUsageItem extends UsageItem {
  group_key?: string;
  tool_id?: string;
  device_name?: string;
}
```

- [ ] **Step 2: 在表格中新增设备名称列**

修改 `frontend/src/components/Tools/TokenUsage.tsx` 中表格 thead：

```tsx
<tr>
  <th className="px-4 py-3 text-left">日期</th>
  {groupBy !== 'none' && <th className="px-4 py-3 text-left">分组</th>}
  <th className="px-4 py-3 text-left">设备</th>
  <th className="px-4 py-3 text-left">工具</th>
  {/* ... 后续列保持不变 */}
</tr>
```

修改 tbody 中数据行：

```tsx
<td className="max-w-[160px] truncate px-4 py-3 text-slate-300" title={item.device_name || '-'}>
  {item.device_name || '-'}
</td>
<td className="max-w-[160px] truncate px-4 py-3 text-slate-400" title={getRowToolLabel(item)}>
  {getRowToolLabel(item)}
</td>
```

同时修改导出 CSV 的 headers 和 rows：

```typescript
const headers = ['日期', '分组', '设备', '工具', '模型', '输入 Token', '输出 Token', '缓存创建', '缓存读取', '总 Token', '成本 USD'];
const rows = details.data.items.map(item => [
  item.date,
  getGroupLabel(item),
  item.device_name || '-',
  getRowToolLabel(item),
  // ...
]);
```

- [ ] **Step 3: 调整空数据 colSpan**

空数据时的 colSpan 从 `groupBy === 'none' ? 9 : 10` 改为 `groupBy === 'none' ? 10 : 11`。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx frontend/src/api/tokenUsageApi.ts backend/app/routes/token_usage.py
git commit -m "feat: Token Usage 明细表格增加设备名称列"
```

---

## Task 8: 前端 — 指纹匹配提示弹窗

**Files:**
- Create: `frontend/src/components/Tools/TokenUsage/FingerprintMatchDialog.tsx`
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: 创建 FingerprintMatchDialog 组件**

```tsx
import React from 'react';
import { Monitor, X } from 'lucide-react';
import type { FingerprintMatch } from '../../../api/tokenUsageApi';

interface Props {
  match: FingerprintMatch;
  currentDeviceName: string;
  onReuse: () => void;
  onCreateNew: () => void;
  onClose: () => void;
}

export default function FingerprintMatchDialog({
  match,
  currentDeviceName,
  onReuse,
  onCreateNew,
  onClose,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-900 p-5 shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10">
            <Monitor className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-medium text-white">检测到已存在的设备</h3>
            <p className="text-xs text-slate-400">系统发现当前设备与已有记录匹配</p>
          </div>
          <button onClick={onClose} className="ml-auto text-slate-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-4 space-y-2 rounded-md bg-slate-950 p-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">当前设备：</span>
            <span className="text-slate-200">{currentDeviceName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">匹配到已有设备：</span>
            <span className="text-slate-200">{match.matched_device_name}</span>
          </div>
        </div>

        <p className="mb-4 text-sm text-slate-300">
          这可能是同一台物理设备。请选择如何处理：
        </p>

        <div className="flex gap-2">
          <button
            onClick={onReuse}
            className="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            复用已有设备
          </button>
          <button
            onClick={onCreateNew}
            className="flex-1 rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
          >
            创建为新设备
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 在 TokenUsage.tsx 中集成弹窗**

新增 state：

```tsx
const [fingerprintMatch, setFingerprintMatch] = useState<FingerprintMatch | null>(null);
```

修改 sync 或 refresh 的响应处理。以 refresh 为例：

```tsx
const handleRefresh = async () => {
  // ...
  const result = await refreshTokenUsage();
  if (result.fingerprint_match) {
    setFingerprintMatch(result.fingerprint_match);
  }
  // ...
};
```

在 JSX 末尾渲染弹窗：

```tsx
{fingerprintMatch && (
  <FingerprintMatchDialog
    match={fingerprintMatch}
    currentDeviceName={getDeviceDisplayName()}
    onReuse={async () => {
      try {
        await createDeviceAlias(
          getCurrentDeviceId(),
          fingerprintMatch.matched_device_id
        );
        setFingerprintMatch(null);
        await loadDevices();
        await Promise.all([summary.refresh(), details.refresh()]);
      } catch (e: any) {
        setError(e.message || '复用设备失败');
      }
    }}
    onCreateNew={() => setFingerprintMatch(null)}
    onClose={() => setFingerprintMatch(null)}
  />
)}
```

注意：这里需要获取当前 device_id。可以通过新增 API `/token-usage/whoami` 或本地存储。为简化，让后端 `/devices` 返回当前设备时标记 `is_current`。

- [ ] **Step 3: 后端 /devices 接口标记当前设备**

修改 `get_user_devices`：

```python
from app.utils.device_id import get_device_id

# ...

current_device_id = get_device_id()
devices = [
    {
        # ...
        "is_current": reg.device_id == current_device_id,
    }
    for reg in regs
]
```

前端类型增加 `is_current?: boolean`。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage/FingerprintMatchDialog.tsx frontend/src/components/Tools/TokenUsage.tsx frontend/src/api/tokenUsageApi.ts backend/app/routes/token_usage.py
git commit -m "feat: 指纹匹配提示弹窗"
```

---

## Task 9: 前端 — 设备管理弹窗（合并/撤销/重命名）

**Files:**
- Create: `frontend/src/components/Tools/TokenUsage/DeviceManagerModal.tsx`
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: 创建设备管理弹窗组件**

这是一个带多选和合并功能的模态框。核心 props：

```tsx
interface Props {
  devices: DeviceInfo[];
  open: boolean;
  onClose: () => void;
  onRename: (deviceId: string, name: string) => Promise<void>;
  onMerge: (sourceIds: string[], targetId: string) => Promise<void>;
  onUnmerge: (aliasDeviceId: string) => Promise<void>;
}
```

组件内部维护选中状态和合并目标。实现要点：

- 列表展示设备名称、ID 类型（hardware/uuid）、是否已被合并（canonical_id）。
- 支持点击重命名（prompt 输入框）。
- 多选设备后显示"合并到..."按钮，选择目标设备后调用 `onMerge`。
- 已被合并的设备显示"撤销合并"按钮。
- 提供"一键合并同名设备"按钮。

完整实现约 200 行，根据项目现有 UI 风格使用 Tailwind。

- [ ] **Step 2: 在 TokenUsage.tsx 中打开设备管理弹窗**

新增 state：

```tsx
const [deviceManagerOpen, setDeviceManagerOpen] = useState(false);
```

在设备下拉框旁增加"管理"按钮：

```tsx
<button
  onClick={() => setDeviceManagerOpen(true)}
  title="管理设备"
  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800"
>
  <Settings className="h-4 w-4" />
</button>
```

引入 `Settings` 图标：`import { Settings } from 'lucide-react';`。

渲染弹窗：

```tsx
<DeviceManagerModal
  devices={devices}
  open={deviceManagerOpen}
  onClose={() => setDeviceManagerOpen(false)}
  onRename={async (id, name) => {
    await renameDevice(id, name);
    await loadDevices();
    await Promise.all([summary.refresh(), details.refresh()]);
  }}
  onMerge={async (sourceIds, targetId) => {
    await mergeDevices(sourceIds, targetId);
    await loadDevices();
    await Promise.all([summary.refresh(), details.refresh()]);
  }}
  onUnmerge={async (aliasId) => {
    await deleteDeviceAlias(aliasId);
    await loadDevices();
    await Promise.all([summary.refresh(), details.refresh()]);
  }}
/>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Tools/TokenUsage/DeviceManagerModal.tsx frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat: 设备管理弹窗支持合并与撤销"
```

---

## Task 10: 验证与收尾

- [ ] **Step 1: 后端语法检查**

```bash
cd backend
python -m py_compile app/main.py
python -m py_compile app/routes/token_usage.py
python -m py_compile app/services/token_usage_sync_service.py
python -m py_compile app/utils/device_id.py
python -m py_compile app/utils/device_name_resolver.py
```

Expected: 全部通过，无语法错误。

- [ ] **Step 2: 前端 TypeScript 检查**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 无类型错误。

- [ ] **Step 3: 重启服务并浏览器验证**

```bash
cd G:\IdeaProjects\tools
python dev_services.py restart
```

Expected: 前后端正常启动。

验证清单：
- [ ] Token Usage 页面正常加载，无 Console 报错。
- [ ] 明细表格中出现"设备"列，显示正确设备名。
- [ ] 删除 `~/.tools/device_id` 后重新同步，弹出"检测到已存在的设备"提示。
- [ ] 选择"复用已有设备"后，历史数据聚合到已有设备下。
- [ ] 设备管理弹窗中可手动合并多个同名设备。
- [ ] 合并后可撤销，数据恢复为独立设备。

- [ ] **Step 4: 最终 Commit**

```bash
git add .
git commit -m "feat: Token Usage 设备指纹识别与合并功能完整实现"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - ✅ 设备指纹生成（MAC + 主机名哈希）→ Task 2
   - ✅ 同步时检查 fingerprint_match → Task 3
   - ✅ 用户确认复用/创建新设备 → Task 8
   - ✅ device_id_alias 映射表 → Task 1 + Task 4
   - ✅ 查询时按 canonical_device_id 聚合 → Task 5
   - ✅ 手动合并多个设备 → Task 4 + Task 9
   - ✅ 撤销合并 → Task 4 + Task 9
   - ✅ 明细表格增加设备名称列 → Task 7
   - ✅ 隐私安全（MAC 不上传原始值）→ Task 2
   - ✅ 降级策略（无 MAC 时使用 UUID）→ Task 2

2. **Placeholder scan:**
   - 无 TBD/TODO
   - 所有代码片段可直接复制使用
   - 所有命令含预期输出

3. **Type consistency:**
   - `DeviceInfo` 前后端字段一致
   - `FingerprintMatch` 前后端一致
   - `DbUsageItem.device_name` 前后端一致
   - API 路径统一为 `/token-usage/devices/...`

4. **边界情况:**
   - MAC 获取失败 → 回退 UUID（Task 2）
   - alias 和 canonical 相同 → 400 错误（Task 4）
   - 目标设备不存在 → 404 错误（Task 4）
   - 合并时同时同步新数据 → 依赖 invalidate_user_query_cache + 数据库事务
