import asyncio
import io
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

import paramiko
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from app.config.database import get_db_connection
from app.models.ssh_tool_models import CreateSSHRequest, UpdateSSHRequest, SSHConfigResponse, TestSSHConnectionRequest
from app.services.auth_service import get_auth_service
from app.utils.encryption import EncryptionUtils

logger = logging.getLogger(__name__)

class SSHToolService:
    _column_map = None

    @staticmethod
    def _ensure_table():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ssh_configs (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    alias VARCHAR(64) NOT NULL,
                    host VARCHAR(255) NOT NULL,
                    port INT NOT NULL DEFAULT 22,
                    username VARCHAR(128) NOT NULL,
                    password_encrypted TEXT,
                    private_key_encrypted TEXT,
                    passphrase_encrypted TEXT,
                    group_name VARCHAR(64),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ssh_configs_user_id ON ssh_configs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ssh_configs_user_alias ON ssh_configs(user_id, alias)")
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _get_column_map():
        if SSHToolService._column_map:
            return SSHToolService._column_map
        SSHToolService._ensure_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'ssh_configs'"
            )
            columns = {row['column_name'] for row in cursor.fetchall()}
        finally:
            cursor.close()
            conn.close()
        def pick(preferred: str, fallback: str):
            if preferred in columns:
                return preferred
            if fallback in columns:
                return fallback
            return preferred
        SSHToolService._column_map = {
            "deleted": pick("deleted", "is_deleted"),
            "password": pick("password_encrypted", "password"),
            "private_key": pick("private_key_encrypted", "private_key"),
            "passphrase": pick("passphrase_encrypted", "passphrase")
        }
        return SSHToolService._column_map
    @staticmethod
    def _row_to_response(row) -> SSHConfigResponse:
        return SSHConfigResponse(
            id=row['id'],
            user_id=row['user_id'],
            alias=row['alias'],
            host=row['host'],
            port=row['port'],
            username=row['username'],
            password=None,
            private_key=None,
            passphrase=None,
            group_name=row['group_name'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    @staticmethod
    def _normalize(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    @staticmethod
    def _validate_port(port: int):
        if port < 1 or port > 65535:
            raise HTTPException(status_code=400, detail="Invalid port")

    @staticmethod
    def test_connection(request: TestSSHConnectionRequest) -> bool:
        host = SSHToolService._normalize(request.host)
        username = SSHToolService._normalize(request.username)
        private_key = SSHToolService._normalize(request.private_key)
        passphrase = SSHToolService._normalize(request.passphrase)
        password = request.password

        if not host or not username:
            raise HTTPException(status_code=400, detail="Invalid connection info")
        SSHToolService._validate_port(request.port)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            pkey = SSHToolService._load_private_key(private_key, passphrase) if private_key else None
            ssh.connect(
                hostname=host,
                port=request.port,
                username=username,
                password=password,
                pkey=pkey,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            return True
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            ssh.close()

    @staticmethod
    def _get_config_record(config_id: str, user_id: str):
        column_map = SSHToolService._get_column_map()
        deleted_column = column_map["deleted"]
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT * FROM ssh_configs WHERE id = %s AND user_id = %s AND {deleted_column} = FALSE",
                (config_id, user_id)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_configs(user_id: str) -> List[SSHConfigResponse]:
        column_map = SSHToolService._get_column_map()
        deleted_column = column_map["deleted"]
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT * FROM ssh_configs WHERE user_id = %s AND {deleted_column} = FALSE ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [SSHToolService._row_to_response(row) for row in rows]
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_config(user_id: str, request: CreateSSHRequest) -> SSHConfigResponse:
        column_map = SSHToolService._get_column_map()
        deleted_column = column_map["deleted"]
        password_column = column_map["password"]
        private_key_column = column_map["private_key"]
        passphrase_column = column_map["passphrase"]
        alias = SSHToolService._normalize(request.alias)
        host = SSHToolService._normalize(request.host)
        username = SSHToolService._normalize(request.username)
        group_name = SSHToolService._normalize(request.group_name)

        if not alias or not host or not username:
            raise HTTPException(status_code=400, detail="Invalid configuration")
        SSHToolService._validate_port(request.port)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            config_id = str(uuid.uuid4())
            now = datetime.now()

            encrypted_password = EncryptionUtils.encrypt(request.password) if request.password else None
            encrypted_key = EncryptionUtils.encrypt(request.private_key) if request.private_key else None
            encrypted_passphrase = EncryptionUtils.encrypt(request.passphrase) if request.passphrase else None

            cursor.execute(
                f"""
                INSERT INTO ssh_configs (
                    id, user_id, alias, host, port, username, {password_column},
                    {private_key_column}, {passphrase_column}, group_name, is_active,
                    created_at, updated_at, {deleted_column}
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                """,
                (
                    config_id, user_id, alias, host, request.port,
                    username, encrypted_password, encrypted_key, encrypted_passphrase,
                    group_name, True, now, now
                )
            )
            conn.commit()

            cursor.execute("SELECT * FROM ssh_configs WHERE id = %s", (config_id,))
            row = cursor.fetchone()
            logger.info("SSH config created: %s", config_id)
            return SSHToolService._row_to_response(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_config(user_id: str, request: UpdateSSHRequest) -> SSHConfigResponse:
        column_map = SSHToolService._get_column_map()
        password_column = column_map["password"]
        private_key_column = column_map["private_key"]
        passphrase_column = column_map["passphrase"]
        if not SSHToolService._get_config_record(request.id, user_id):
            raise HTTPException(status_code=404, detail="Config not found")

        update_fields = []
        params = []

        if request.alias is not None:
            alias = SSHToolService._normalize(request.alias)
            if not alias:
                raise HTTPException(status_code=400, detail="Invalid alias")
            update_fields.append("alias = %s")
            params.append(alias)

        if request.host is not None:
            host = SSHToolService._normalize(request.host)
            if not host:
                raise HTTPException(status_code=400, detail="Invalid host")
            update_fields.append("host = %s")
            params.append(host)

        if request.port is not None:
            SSHToolService._validate_port(request.port)
            update_fields.append("port = %s")
            params.append(request.port)

        if request.username is not None:
            username = SSHToolService._normalize(request.username)
            if not username:
                raise HTTPException(status_code=400, detail="Invalid username")
            update_fields.append("username = %s")
            params.append(username)

        if request.password is not None:
            encrypted_password = EncryptionUtils.encrypt(request.password) if request.password else None
            update_fields.append(f"{password_column} = %s")
            params.append(encrypted_password)

        if request.private_key is not None:
            encrypted_key = EncryptionUtils.encrypt(request.private_key) if request.private_key else None
            update_fields.append(f"{private_key_column} = %s")
            params.append(encrypted_key)

        if request.passphrase is not None:
            encrypted_passphrase = EncryptionUtils.encrypt(request.passphrase) if request.passphrase else None
            update_fields.append(f"{passphrase_column} = %s")
            params.append(encrypted_passphrase)

        if request.group_name is not None:
            group_name = SSHToolService._normalize(request.group_name)
            update_fields.append("group_name = %s")
            params.append(group_name)

        if request.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(request.is_active)

        if not update_fields:
            record = SSHToolService._get_config_record(request.id, user_id)
            return SSHToolService._row_to_response(record)

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(request.id)
        params.append(user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            sql = f"UPDATE ssh_configs SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
            cursor.execute(sql, tuple(params))
            conn.commit()
            record = SSHToolService._get_config_record(request.id, user_id)
            logger.info("SSH config updated: %s", request.id)
            return SSHToolService._row_to_response(record)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete_config(user_id: str, config_id: str) -> bool:
        column_map = SSHToolService._get_column_map()
        deleted_column = column_map["deleted"]
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"UPDATE ssh_configs SET {deleted_column} = TRUE WHERE id = %s AND user_id = %s",
                (config_id, user_id)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info("SSH config deleted: %s", config_id)
                return True
            return False
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _load_private_key(private_key: str, passphrase: Optional[str]):
        key_classes = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]
        if "BEGIN" in private_key:
            for key_cls in key_classes:
                try:
                    return key_cls.from_private_key(io.StringIO(private_key), password=passphrase)
                except Exception:
                    continue
        else:
            for key_cls in key_classes:
                try:
                    return key_cls.from_private_key_file(private_key, password=passphrase)
                except Exception:
                    continue
        raise HTTPException(status_code=400, detail="Invalid private key")

    @staticmethod
    async def handle_ssh_session(websocket: WebSocket, config_id: str, token: str, cols: int = 80, rows: int = 24):
        await websocket.accept()
        try:
            auth_service = get_auth_service()
            token_data = auth_service.verify_token_data(token)
            user_id = token_data.user_id
        except ValueError:
            await websocket.close(code=4003, reason="Authentication failed")
            return

        config = SSHToolService._get_config_record(config_id, user_id)
        if not config:
            await websocket.close(code=4000, reason="Config not found")
            return

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            column_map = SSHToolService._get_column_map()
            password_value = config.get(column_map["password"])
            private_key_value = config.get(column_map["private_key"])
            passphrase_value = config.get(column_map["passphrase"])
            password = EncryptionUtils.decrypt(password_value) if password_value else None
            private_key = EncryptionUtils.decrypt(private_key_value) if private_key_value else None
            passphrase = EncryptionUtils.decrypt(passphrase_value) if passphrase_value else None
            pkey = SSHToolService._load_private_key(private_key, passphrase) if private_key else None

            ssh.connect(
                hostname=config['host'],
                port=config['port'],
                username=config['username'],
                password=password,
                pkey=pkey,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )

            channel = ssh.invoke_shell(term='xterm-256color', width=cols, height=rows)
            logger.info("SSH session started: %s", config_id)

            async def receive_from_client():
                while True:
                    try:
                        data = await websocket.receive_text()
                    except WebSocketDisconnect:
                        break
                    try:
                        message = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    message_type = message.get('type')
                    if message_type == 'resize':
                        channel.resize_pty(width=int(message.get('cols', cols)), height=int(message.get('rows', rows)))
                    elif message_type == 'input':
                        channel.send(message.get('data', ''))

            async def send_to_client():
                while True:
                    if channel.exit_status_ready():
                        break
                    if channel.recv_ready():
                        data = channel.recv(4096)
                        if not data:
                            break
                        await websocket.send_text(data.decode('utf-8', errors='ignore'))
                    else:
                        await asyncio.sleep(0.01)

            await asyncio.gather(receive_from_client(), send_to_client())
        except Exception as e:
            logger.error("SSH connection failed: %s", str(e))
            await websocket.close(code=4000, reason="SSH connection failed")
        finally:
            ssh.close()
            logger.info("SSH session closed: %s", config_id)
