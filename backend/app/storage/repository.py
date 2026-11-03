"""
配置仓储 —— 本地 SQLite 与远程 PostgreSQL 的统一读写层

安全不变量：storage_location='LOCAL' 的配置，其敏感字段在物理上不可能
出现在远程 PostgreSQL 中。保障来自四重：
1. Repository 实例绑定存储位置，_assert_location 拒绝越界写入
2. 写入路径隔离 —— 写操作必须拿到对应位置的 Repository 实例
3. 每个 Repository 只读写自己那一侧的行（storage_location 过滤兜底）
4. 密钥隔离 —— 本地库用本机文件密钥，远程库用服务器密钥，密文互不可解
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import delete as sa_delete, insert, select, update as sa_update

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import (
    db_configs,
    get_local_engine,
    init_local_tables,
    k8s_connections,
    redis_configs,
    sql_execution_history,
    ssh_configs,
    table_schema_cache,
)

logger = logging.getLogger(__name__)

# 工具标识 → 表名
TOOL_TABLES: dict[str, str] = {
    "database": "db_configs",
    "k8s": "k8s_connections",
    "ssh": "ssh_configs",
    "redis": "redis_configs",
}

# 工具标识 → Table 对象
TOOL_TABLE_OBJECTS = {
    "database": db_configs,
    "k8s": k8s_connections,
    "ssh": ssh_configs,
    "redis": redis_configs,
}

# 需要在删除配置时一并清理的关联表（SQLite 外键默认关闭）。
# 注意：db_scan_history 无 db_config_id 列（按路径维度记录，见 init_db_tool.sql），
# 无法按配置删除，不在此清理。
RELATED_HISTORY_TABLES = {
    "database": ["sql_execution_history", "table_schema_cache"],
    "k8s": [],
    "ssh": [],
    "redis": [],
}

# 各工具的敏感列（迁移时需重加密）
SENSITIVE_COLUMNS: dict[str, list[str]] = {
    "database": ["password_encrypted"],
    "k8s": ["auth_data_encrypted", "ca_cert_encrypted"],
    "ssh": ["password_encrypted", "private_key_encrypted", "passphrase_encrypted"],
    "redis": ["password_encrypted"],
}


class ConfigRepository:
    """配置仓储基类。

    子类只需提供 `_engine()`、`_encrypt()`、`_decrypt()` 三个钩子。
    """

    location: StorageLocation = StorageLocation.SERVER

    def __init__(self, tool: str):
        if tool not in TOOL_TABLES:
            raise ValueError(f"未知工具：{tool}")
        self.tool = tool
        self.table_name = TOOL_TABLES[tool]
        self.table = TOOL_TABLE_OBJECTS[tool]

    # ============ 子类钩子 ============

    def _engine(self):
        raise NotImplementedError

    def _encrypt(self, plain: str) -> str:
        raise NotImplementedError

    def _decrypt(self, cipher: str) -> str:
        raise NotImplementedError

    def _now(self) -> datetime:
        return datetime.now()

    def _location_tag(self) -> str:
        """写入/过滤 storage_location 列用的标记（大写 LOCAL/SERVER）"""
        return self.location.name

    # ============ 安全闸门 ============

    def _assert_location(self, storage_location: StorageLocation) -> None:
        """校验传入的存储位置与本实例绑定位置一致。

        这是「LOCAL 数据不可能写进远程库」的类型层保障。
        """
        if storage_location is not self.location:
            raise ValueError(
                f"存储位置不匹配：{self.location.name} 仓储不接受 "
                f"{storage_location.name}"
            )

    # ============ 读 ============

    def list(self, user_id: str) -> list[dict]:
        """列出用户的全部配置（不含明文凭据）"""
        stmt = select(self.table).where(
            self.table.c.user_id == user_id,
            self.table.c.deleted.is_(False),
            self.table.c.storage_location == self._location_tag(),
        )
        with self._engine().begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def get(self, config_id: str, user_id: str) -> dict | None:
        """获取单条配置（不含明文凭据）"""
        stmt = select(self.table).where(
            self.table.c.id == config_id,
            self.table.c.user_id == user_id,
            self.table.c.deleted.is_(False),
            self.table.c.storage_location == self._location_tag(),
        )
        with self._engine().begin() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row) if row else None

    def find_by_alias(self, user_id: str, alias: str) -> dict | None:
        """按别名查找（用于跨库唯一性检查）。

        k8s 表的别名列是 name，其余工具是 alias。
        """
        alias_column = self.table.c.name if self.tool == "k8s" else self.table.c.alias
        stmt = select(self.table).where(
            self.table.c.user_id == user_id,
            alias_column == alias,
            self.table.c.deleted.is_(False),
            self.table.c.storage_location == self._location_tag(),
        )
        with self._engine().begin() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row) if row else None

    def get_with_secret(self, config_id: str, user_id: str) -> dict | None:
        """获取配置并解密敏感列（仅连接测试/实际连接时使用）。

        安全约束：
        - 不修改 self.get() 返回的字典（get/list 的返回值不含明文）
        - 解密后的明文放在独立的 result 字典里，调用方用完即丢弃
        """
        row = self.get(config_id, user_id)
        if row is None:
            return None

        # 拷贝一份新的字典，避免把明文写回 get/list 的缓存值
        result = dict(row)

        for column in SENSITIVE_COLUMNS.get(self.tool, []):
            cipher = row.get(column)
            if not cipher:
                result[f"{column.removesuffix('_encrypted')}_decrypted"] = None
                continue
            try:
                result[f"{column.removesuffix('_encrypted')}_decrypted"] = self._decrypt(cipher)
            except Exception as exc:
                logger.error("解密 %s 的 %s 失败：%s", config_id, column, exc)
                raise

        return result

    def list_all_locations(self, user_id: str) -> list[dict]:
        """列出用户在本侧的全部配置（跨位置视图用）"""
        return self.list(user_id)

    # ============ 写 ============

    def create(self, user_id: str, data: dict, storage_location: StorageLocation) -> dict:
        """创建配置。

        storage_location 必须与实例绑定位置一致，否则抛错。
        """
        self._assert_location(storage_location)

        payload = dict(data)
        payload["user_id"] = user_id
        # 位置标记由 Repository 注入 —— 不能依赖 Column 的 default
        payload["storage_location"] = self._location_tag()
        payload.setdefault("created_at", self._now())
        payload.setdefault("updated_at", self._now())

        stmt = insert(self.table).values(**payload)
        with self._engine().begin() as conn:
            conn.execute(stmt)

        created = self.get(payload["id"], user_id)
        if created is None:
            raise RuntimeError("配置创建后无法读回")
        return created

    def update(
        self, config_id: str, user_id: str, data: dict, storage_location: StorageLocation
    ) -> dict | None:
        """更新配置"""
        self._assert_location(storage_location)

        existing = self.get(config_id, user_id)
        if existing is None:
            return None

        payload = dict(data)
        payload.pop("id", None)
        payload.pop("user_id", None)
        payload["updated_at"] = self._now()

        stmt = (
            sa_update(self.table)
            .where(
                self.table.c.id == config_id,
                self.table.c.user_id == user_id,
                self.table.c.storage_location == self._location_tag(),
            )
            .values(**payload)
        )
        with self._engine().begin() as conn:
            conn.execute(stmt)

        return self.get(config_id, user_id)

    def delete(self, config_id: str, user_id: str) -> bool:
        """删除配置（并清理关联历史）"""
        existing = self.get(config_id, user_id)
        if existing is None:
            return False

        with self._engine().begin() as conn:
            conn.execute(
                sa_delete(self.table).where(
                    self.table.c.id == config_id,
                    self.table.c.user_id == user_id,
                    self.table.c.storage_location == self._location_tag(),
                )
            )
            # SQLite 外键默认关闭，需显式清理关联历史
            for related in RELATED_HISTORY_TABLES.get(self.tool, []):
                related_table = {
                    "sql_execution_history": sql_execution_history,
                    "table_schema_cache": table_schema_cache,
                }.get(related)
                if related_table is None:
                    continue
                conn.execute(
                    sa_delete(related_table).where(
                        related_table.c.db_config_id == config_id
                    )
                )

        return True


class LocalConfigRepository(ConfigRepository):
    """本地 SQLite 仓储"""

    location = StorageLocation.LOCAL

    def _engine(self):
        engine = get_local_engine()
        init_local_tables(engine)
        return engine

    def _encrypt(self, plain: str) -> str:
        return LocalEncryption.encrypt(plain)

    def _decrypt(self, cipher: str) -> str:
        return LocalEncryption.decrypt(cipher)


class RemoteConfigRepository(ConfigRepository):
    """远程 PostgreSQL 仓储"""

    location = StorageLocation.SERVER

    def _engine(self):
        from app.storage.remote_db import get_remote_engine

        return get_remote_engine()

    def _encrypt(self, plain: str) -> str:
        from app.utils.encryption import EncryptionUtils

        return EncryptionUtils.encrypt(plain)

    def _decrypt(self, cipher: str) -> str:
        from app.utils.encryption import EncryptionUtils

        return EncryptionUtils.decrypt(cipher)


def get_repository(location: StorageLocation, tool: str) -> ConfigRepository:
    """按存储位置返回对应仓库实现"""
    location = StorageLocation.from_value(location)

    if location is StorageLocation.LOCAL:
        return LocalConfigRepository(tool)
    return RemoteConfigRepository(tool)


def delete_config_everywhere(user_id: str, tool: str, config_id: str) -> bool:
    """删除配置：本地侧与服务器侧**都**尝试物理删除。

    安全要求：配置选择「仅保存在本机」后，服务器侧不允许残留任何副本
    （含密文列）。Repository.delete 走的是 SQL DELETE（物理删除），
    不是软删除标记，因此本函数保证「删除后两侧都查不到该 id」。

    一侧不可达（如远程库连接失败）时跳过该侧并记录日志，不影响另一侧。
    """
    deleted = False

    for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
        try:
            repo = get_repository(location, tool)
        except Exception as exc:
            logger.warning("获取 %s 侧仓储失败（tool=%s）：%s", location.value, tool, exc)
            continue
        try:
            if repo.delete(config_id, user_id):
                deleted = True
        except Exception as exc:
            logger.warning("删除 %s 侧配置 %s 失败：%s", location.value, config_id, exc)

    return deleted


def ensure_storage_location(
    user_id: str, tool: str, config_id: str, target: StorageLocation
) -> tuple[ConfigRepository, StorageLocation]:
    """确保配置位于 target 存储位置，返回（仓储, 位置）。

    若配置当前已在 target 侧 → 直接返回该侧仓储，不做任何写操作。
    若配置在另一侧 → 执行迁移（重加密写入目标端 + 物理删除源端），
    返回目标端仓储。

    安全保证：迁移后源端**物理删除**该行（Repository.delete 走 SQL DELETE），
    不会出现「已选本地但服务器仍残留密文副本」的情况。

    放在本模块（而非 migration.py）的原因：仓储路由的唯一真源是本模块的
    `get_repository`，这样调用方 monkeypatch `repository.get_repository` 时
    行为一致，不会出现两套仓储引用。
    """
    target = StorageLocation.from_value(target)

    # 先看目标侧是否已有该配置
    target_repo = get_repository(target, tool)
    if target_repo.get(config_id, user_id):
        return target_repo, target

    # 目标侧没有 → 源端必然有，迁移过去（延迟 import 避免循环依赖）
    from app.storage.migration import migrate_config

    migrate_config(user_id, tool, config_id, target)
    return target_repo, target
