"""
配置迁移服务 —— 本地 ↔ 服务器

安全约束：
1. 执行顺序为「先写目标端、后删源端」。先删后写在写失败时会丢失配置（不可接受）；
   先写后删的最坏情况是短暂重复，可通过再次迁移自愈。
2. 迁移必须重加密：源端密钥与目标端密钥不同，密文不可直接拷贝。
3. 明文只在内存，不落盘、不进日志。
4. 目标端已有同名配置时迁移失败，不自动改名、不静默覆盖。
"""
import logging

from app.storage.locator import StorageLocation, server_available
from app.storage.repository import (
    SENSITIVE_COLUMNS,
    TOOL_TABLES,
    get_repository,
)

logger = logging.getLogger(__name__)


def _encrypt_sensitive(tool: str, plain: dict, location: StorageLocation) -> dict:
    """用目标端密钥加密敏感列"""
    from app.storage.crypto import LocalEncryption
    from app.utils.encryption import EncryptionUtils

    cipher: dict = {}
    for column, value in plain.items():
        if not value:
            cipher[column] = None
            continue

        if location is StorageLocation.LOCAL:
            cipher[column] = LocalEncryption.encrypt(value)
        else:
            cipher[column] = EncryptionUtils.encrypt(value)

    return cipher


def migrate_config(
    user_id: str, tool: str, config_id: str, target: StorageLocation
) -> dict:
    """迁移单条配置到目标存储位置。

    Returns:
        { "success": bool, "storage_location": str, "message": str }

    Raises:
        ValueError: 配置不存在 / 目标不可用 / 别名冲突 / 解密失败
    """
    if tool not in TOOL_TABLES:
        raise ValueError(f"未知工具：{tool}")

    target = StorageLocation.from_value(target)

    if target is StorageLocation.SERVER:
        available, reason = server_available()
        if not available:
            raise ValueError(reason or "未配置远程服务器，无法上传")

    # 1. 定位源端（配置在哪一侧就从哪一侧迁出）。
    #    优先在「目标端的另一侧」找 —— 本地迁移到本地时若同 id 在两侧都有
    #    （上次迁移的中间态），应迁出服务器侧那份而不是误判为无需迁移。
    #    若一边仓储初始化失败则跳过，不能因一边不可达而阻断定位。
    source_repo = None
    source_location = None
    locate_errors: list[str] = []

    locate_order = (
        (StorageLocation.SERVER, StorageLocation.LOCAL)
        if target is StorageLocation.LOCAL
        else (StorageLocation.LOCAL, StorageLocation.SERVER)
    )
    for location in locate_order:
        try:
            repo = get_repository(location, tool)
            if repo.get(config_id, user_id):
                source_repo = repo
                source_location = location
                break
        except Exception as exc:
            locate_errors.append(f"{location.value}：{exc}")
            logger.warning("定位源端时 %s 侧不可用：%s", location.value, exc)

    if source_repo is None or source_location is None:
        raise ValueError(f"配置不存在：{config_id}。定位失败：{locate_errors}")

    if source_location is target:
        return {
            "success": True,
            "storage_location": target.value,
            "message": "配置已在目标存储位置，无需迁移",
        }

    # 2. 解密（源端密钥）→ 明文（仅内存）
    source_row = source_repo.get_with_secret(config_id, user_id)
    if source_row is None:
        raise ValueError(f"配置不存在：{config_id}")

    plain = {}
    for column in SENSITIVE_COLUMNS.get(tool, []):
        key = f"{column.removesuffix('_encrypted')}_decrypted"
        plain[column] = source_row.get(key)

    # 3. 目标端别名冲突检查
    target_repo = get_repository(target, tool)
    alias_field = "name" if tool == "k8s" else "alias"
    alias = source_row.get(alias_field)
    if alias:
        existing = target_repo.find_by_alias(user_id, alias)
        if existing and existing.get("id") != config_id:
            raise ValueError(
                f"目标端已存在同名配置「{alias}」，请先改名或删除后再迁移"
            )

    # 4. 重加密（目标端密钥）
    cipher = _encrypt_sensitive(tool, plain, target)

    # 5. 先写目标端。若目标端残留同 id 旧行（上次迁移删除源端失败的中间态），
    #    先按 id 清掉避免主键冲突 —— 这正是「再次迁移可自动修复」的自愈路径。
    #    该残留行可能带无效的 deleted 标记或错误位置标记，仓储层的软删除过滤
    #    读不到它，因此这里直接按主键删除（随后立即重写同 id 新行）。
    from sqlalchemy import delete as sa_delete

    with target_repo._engine().begin() as conn:
        conn.execute(
            sa_delete(target_repo.table).where(
                target_repo.table.c.id == config_id,
                target_repo.table.c.user_id == user_id,
            )
        )

    #    只取目标端 Table 中真实存在的列 —— 源端行可能包含额外的派生字段
    #    （如 _decrypted 后缀），直接拷贝会导致 insert 失败。
    #    target_repo.table.c 是 SQLAlchemy ColumnCollection，其键即合法列名。
    valid_columns = set(target_repo.table.c.keys())
    payload = {
        key: value
        for key, value in source_row.items()
        if key in valid_columns and key != "storage_location"
    }
    payload.update(cipher)
    payload["storage_location"] = target.value

    target_repo.create(user_id, payload, target)

    # 6. 后删源端
    try:
        source_repo.delete(config_id, user_id)
    except Exception as exc:
        logger.warning("迁移后删除源端失败（两端暂时重复）：%s", exc)
        return {
            "success": True,
            "storage_location": target.value,
            "message": (
                "已迁移到目标位置，但源端记录清理失败（两端暂时重复，"
                "再次迁移可自动修复）"
            ),
        }

    return {
        "success": True,
        "storage_location": target.value,
        "message": "迁移成功",
    }


def migrate_all(user_id: str, tool: str, target: StorageLocation) -> dict:
    """批量迁移该用户的全部配置到目标存储位置。

    单条失败不中断整体，失败项收集到 errors 返回。
    """
    if tool not in TOOL_TABLES:
        raise ValueError(f"未知工具：{tool}")

    target = StorageLocation.from_value(target)

    if target is StorageLocation.SERVER:
        available, reason = server_available()
        if not available:
            raise ValueError(reason or "未配置远程服务器，无法上传")

    # 收集源端（与目标相反的一侧）的全部配置
    source_location = (
        StorageLocation.SERVER if target is StorageLocation.LOCAL else StorageLocation.LOCAL
    )
    source_repo = get_repository(source_location, tool)
    rows = source_repo.list(user_id)

    migrated = 0
    errors: list[dict] = []

    for row in rows:
        config_id = row.get("id")
        try:
            migrate_config(user_id, tool, config_id, target)
            migrated += 1
        except Exception as exc:
            logger.warning("批量迁移配置 %s 失败：%s", config_id, exc)
            errors.append({"config_id": config_id, "message": str(exc)})

    return {
        "success": len(errors) == 0,
        "migrated": migrated,
        "failed": len(errors),
        "errors": errors,
    }
