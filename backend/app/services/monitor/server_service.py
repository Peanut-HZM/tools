"""
监控服务器服务 - 服务器 CRUD、SSH 导入、凭据加密、监控设置
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import HTTPException
import paramiko
from cryptography.fernet import InvalidToken

from app.config.database import get_pooled_db_connection, release_db_connection
from app.utils.encryption import EncryptionUtils
from app.models.monitor_models import (
    CreateMonitorServerRequest, UpdateMonitorServerRequest,
    TestMonitorServerRequest, MonitorSettings,
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
                       m.net_recv_rate, m.net_sent_rate, m.disk_read_rate, m.disk_write_rate,
                       m.collected_at AS metric_collected_at
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
            # 兼容嵌套 metric 行（测试模拟）与扁平指标列（真实查询结果）两种形态
            nested_metric = row.get("metric")
            if isinstance(nested_metric, dict):
                metric = nested_metric
            else:
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

            # 陈旧错误自愈：多个部署实例共享同一数据库时，旧版本实例会把它自己
            # 的历史错误反复写回（例如 paramiko DSSKey 在 4.0 已移除、代码已修），
            # 把另一实例刚写入的 online 覆盖成 offline。
            #
            # 判定依据不用 last_seen_at（对方写 offline 时会把它置 NULL），
            # 而用 monitor_metrics 的最新采集时间 —— 只有真正采集成功才会写这张表，
            # 对方实例不会碰它。最近 2 分钟内有指标落库 ⇒ 服务是通的，清掉陈旧错误。
            metric_at = row.get("metric_collected_at")
            if item.get("status") != "online" and metric_at is not None and item.get("metric") is not None:
                try:
                    if isinstance(metric_at, str):
                        metric_at = datetime.fromisoformat(metric_at.replace("Z", ""))
                    age = (datetime.now() - metric_at).total_seconds()
                except (TypeError, ValueError):
                    age = 9999
                if age < 120:
                    item["status"] = "online"
                    item["last_error"] = None
                    # 自愈时补上采集时间：对方实例写 offline 会把 last_seen_at 置 NULL，
                    # 不补会让卡片显示「尚未采集」而指标却有值，自相矛盾。
                    if item.get("last_seen_at") is None and metric_at is not None:
                        item["last_seen_at"] = metric_at

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
            values.append(user_id)
            cursor.execute(
                f"UPDATE monitor_servers SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s",
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
                "UPDATE monitor_servers SET deleted = TRUE, status = 'disabled', updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s",
                (server_id, user_id),
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
    def sync_from_ssh(user_id: str) -> Dict:
        """把用户全部 SSH 配置同步为监控服务器（幂等，可反复调用）

        语义：
        * SSH 配置新增 → 新建对应监控服务器（记录 source_ssh_id）
        * SSH 配置改过（名称 / 主机 / 端口 / 用户名）→ 更新监控服务器
        * SSH 配置已删除 → 对应的监控服务器标记 disabled（不物理删，
          历史指标与告警记录仍可追溯）
        * 本机节点与「手动添加、无 source_ssh_id」的服务器完全不动

        凭据复制：从 SSH 配置解密后重新加密写入监控服务器，两者之后各自独立管理
        （在监控里改密码不会反向影响 SSH 工具，符合「导入即快照」的既有语义）。
        """
        from app.services.ssh_tool_service import SSHToolService
        from app.utils.encryption import EncryptionUtils

        # 1) 现有监控服务器（按 source_ssh_id 索引）
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id, name, host, port, username, source_ssh_id, status, deleted
                   FROM monitor_servers
                   WHERE user_id = %s AND deleted = FALSE AND source_ssh_id IS NOT NULL""",
                (user_id,),
            )
            existing_rows = cursor.fetchall()
        finally:
            cursor.close()
            release_db_connection(conn)

        existing_by_ssh: Dict[str, Dict] = {
            str(r["source_ssh_id"]): dict(r) for r in existing_rows if r.get("source_ssh_id")
        }

        # 2) SSH 配置（已脱敏，需要单独取密文列来复制凭据）
        ssh_configs = SSHToolService.get_configs(user_id)

        created = updated = unchanged = disabled = 0
        items: list[Dict] = []

        for cfg in ssh_configs:
            ssh_id = cfg.id
            cur = existing_by_ssh.get(ssh_id)
            changed_fields: list[str] = []
            if cur:
                if (cur.get("name") or "") != cfg.alias:
                    changed_fields.append("name")
                if (cur.get("host") or "") != (cfg.host or ""):
                    changed_fields.append("host")
                if int(cur.get("port") or 22) != int(cfg.port or 22):
                    changed_fields.append("port")
                if (cur.get("username") or "") != (cfg.username or ""):
                    changed_fields.append("username")

            if cur and not changed_fields:
                unchanged += 1
                items.append({"sshConfigId": ssh_id, "name": cfg.alias, "action": "unchanged"})
                continue

            if cur:
                # 已存在且元信息变了：更新名称与连接信息
                conn = get_pooled_db_connection()
                cs = conn.cursor()
                try:
                    cs.execute(
                        """UPDATE monitor_servers
                           SET name = %s, host = %s, port = %s, username = %s, updated_at = CURRENT_TIMESTAMP
                           WHERE id = %s AND user_id = %s""",
                        (cfg.alias, cfg.host, cfg.port, cfg.username, cur["id"], user_id),
                    )
                    conn.commit()
                finally:
                    cs.close()
                    release_db_connection(conn)
                updated += 1
                items.append(
                    {"sshConfigId": ssh_id, "name": cfg.alias, "action": "updated",
                     "fields": changed_fields}
                )
                continue

            # 新建：复制凭据（从 SSH 配置的密文列解密，再写入监控服务器）
            try:
                MonitorServerService.import_from_ssh(user_id, ssh_id)
                created += 1
                items.append({"sshConfigId": ssh_id, "name": cfg.alias, "action": "created"})
            except InvalidToken:
                # SSH 配置里的密码/私钥是用旧主密钥加密的，当前密钥解不开。
                # 这类配置在 SSH 工具里同样无法使用，需要用户在 SSH 工具里重填密码。
                msg = "SSH 配置的密码无法解密（历史密钥问题），请到 SSH 工具重新填写密码后再同步"
                logger.warning("SSH 配置 %s 凭据无法解密，跳过同步", ssh_id)
                items.append(
                    {"sshConfigId": ssh_id, "name": cfg.alias, "action": "failed", "reason": msg}
                )
            except Exception as exc:  # 单条失败不影响其它服务器
                logger.warning("SSH 配置 %s 同步为监控服务器失败: %s", ssh_id, exc)
                items.append(
                    {"sshConfigId": ssh_id, "name": cfg.alias, "action": "failed",
                     "reason": str(exc)[:200] or type(exc).__name__}
                )

        # 3) SSH 侧已删除的 → 监控服务器标记 disabled
        live_ssh_ids = {c.id for c in ssh_configs}
        for ssh_id, row in existing_by_ssh.items():
            if ssh_id in live_ssh_ids:
                continue
            if row.get("status") == "disabled":
                continue
            conn = get_pooled_db_connection()
            cs = conn.cursor()
            try:
                cs.execute(
                    """UPDATE monitor_servers
                       SET status = 'disabled', updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s AND user_id = %s""",
                    (row["id"], user_id),
                )
                conn.commit()
            finally:
                cs.close()
                release_db_connection(conn)
            disabled += 1
            items.append(
                {"sshConfigId": ssh_id, "name": row.get("name") or "", "action": "disabled"}
            )

        logger.info(
            "SSH → 监控同步: user=%s 新建 %d / 更新 %d / 停用 %d / 未变 %d",
            user_id, created, updated, disabled, unchanged,
        )
        return {
            "sshTotal": len(ssh_configs),
            "created": created,
            "updated": updated,
            "disabled": disabled,
            "unchanged": unchanged,
            "items": items,
        }

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
        """加载私钥（复用 SSH 工具的方式）

        候选密钥类型必须动态探测：paramiko 5.x 已移除 DSSKey，
        写死 paramiko.DSSKey 会在模块属性访问时直接抛 AttributeError。
        """
        import io
        key_classes = [
            key_cls
            for key_cls in (
                getattr(paramiko, "RSAKey", None),
                getattr(paramiko, "Ed25519Key", None),
                getattr(paramiko, "ECDSAKey", None),
                getattr(paramiko, "DSSKey", None),  # paramiko < 5 才有，缺失时跳过
            )
            if key_cls is not None
        ]
        if not key_classes:
            raise HTTPException(status_code=500, detail="SSH 客户端不支持任何私钥类型")
        for key_cls in key_classes:
            try:
                return key_cls.from_private_key(io.StringIO(private_key), password=passphrase)
            except Exception:
                continue
        raise HTTPException(status_code=400, detail="无效的私钥")

    @staticmethod
    def get_enabled_servers(user_id: Optional[str] = None) -> List[Dict]:
        """获取启用（未被禁用）的监控服务器（含解密凭据，供采集引擎使用）

        :param user_id: 传 None 表示采集引擎的全局周期（所有用户都要采）；
                        传具体用户时只返回该用户的服务器，避免跨用户数据混用。
        """
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            sql = """SELECT * FROM monitor_servers
                     -- 采集后状态为 online/offline/error，enabled 仅作为新建服务器初始态，需一并采集
                     WHERE status <> 'disabled' AND deleted = FALSE"""
            params: tuple = ()
            if user_id is not None:
                sql += " AND user_id = %s"
                params = (user_id,)
            sql += " ORDER BY CASE WHEN server_type = 'local' THEN 0 ELSE 1 END, created_at"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        finally:
            cursor.close()
            release_db_connection(conn)
        result = []
        for row in rows:
            server = MonitorServerService._row_to_dict(row)
            # 单条凭据解密失败不能让整轮采集崩掉：标记该条为不可用并继续
            try:
                server["password"] = EncryptionUtils.decrypt(row.get("password_encrypted")) if row.get("password_encrypted") else None
                server["private_key"] = EncryptionUtils.decrypt(row.get("private_key_encrypted")) if row.get("private_key_encrypted") else None
                server["passphrase"] = EncryptionUtils.decrypt(row.get("passphrase_encrypted")) if row.get("passphrase_encrypted") else None
            except Exception as exc:
                logger.warning(
                    "监控服务器凭据解密失败，跳过采集: id=%s name=%s 错误=%s",
                    row.get("id"), row.get("name"), exc,
                )
                continue
            result.append(server)
        return result

    @staticmethod
    def update_status(server_id: str, status: str, last_error: Optional[str], last_seen_at: Optional[datetime]) -> None:
        """更新服务器采集状态

        **多实例竞争保护**：同一个数据库可能被多台机器上的同一应用同时采集
        （本机开发实例 + 远端部署实例各跑一个采集循环）。旧版本实例采集失败时
        会把另一实例刚写入的 online 覆盖成 offline，导致页面状态在
        online/offline 之间反复跳动，并不断回显早已修复的历史错误
        （如 paramiko DSSKey）。

        因此「标记 offline」加了时间护栏：只有当 last_seen_at 早于本次失败
        超过 60 秒时才允许覆盖 —— 说明最近确实没人成功采过它。
        写 online 不设限制，成功永远应该被记录。
        """
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            if status == "offline":
                cursor.execute(
                    """UPDATE monitor_servers
                       SET status = %s, last_error = %s, last_seen_at = %s, updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s
                         AND (last_seen_at IS NULL
                              OR last_seen_at < CURRENT_TIMESTAMP - INTERVAL '60 seconds')""",
                    (status, last_error, last_seen_at, server_id),
                )
            else:
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
