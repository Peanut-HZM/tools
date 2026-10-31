import asyncio
import io
import json
import logging
import socket
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict

import paramiko
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from app.config.database import get_pooled_db_connection, release_db_connection
from app.models.ssh_tool_models import (
    CreateSSHRequest, UpdateSSHRequest, SSHConfigResponse, TestSSHConnectionRequest,
    SFTPListRequest, SFTPListResponse, SFTPFileInfo, SFTPDownloadRequest, SFTPDownloadResponse,
    SFTPUploadRequest, SFTPUploadResponse, SFTPDeleteRequest, SFTPDeleteResponse,
    SFTPMkdirRequest, SFTPMkdirResponse, SFTPRenameRequest, SFTPRenameResponse,
    SSHTunnelRequest, SSHTunnelResponse, SSHTunnelInfo, SSHTunnelListResponse,
    BatchCommandRequest, BatchCommandResponse, BatchCommandResult, TunnelProtocol
)
from app.services.auth_service import get_auth_service
from app.utils.encryption import EncryptionUtils

logger = logging.getLogger(__name__)

class SSHToolService:
    _column_map = None

    @staticmethod
    def _ensure_table():
        conn = get_pooled_db_connection()
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
            # 幂等加列：存储位置标记（LOCAL=本机 / SERVER=服务器）
            from app.storage.remote_db import ensure_remote_column

            ensure_remote_column(
                "ssh_configs",
                "storage_location",
                "storage_location VARCHAR(16) NOT NULL DEFAULT 'SERVER'",
            )
            conn.commit()
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def _get_column_map():
        if SSHToolService._column_map:
            return SSHToolService._column_map
        SSHToolService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'ssh_configs'"
            )
            columns = {row['column_name'] for row in cursor.fetchall()}
        finally:
            cursor.close()
            release_db_connection(conn)
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
        # 落库为大写 LOCAL/SERVER，对外统一小写
        storage_location = str(row.get('storage_location') or 'server').lower()
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
            storage_location=storage_location,
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
        """按需获取配置记录（自动定位存储位置，含解密后的敏感字段）"""
        repo, _location = SSHToolService._locate(user_id, config_id)
        if repo is None:
            return None
        return repo.get_with_secret(config_id, user_id)

    @staticmethod
    def _decrypt_password(cipher: Optional[str]) -> Optional[str]:
        """兼容路径：直接解密密文（远程旧行可能缺 *_decrypted 键时使用）"""
        if not cipher:
            return None
        from app.utils.encryption import EncryptionUtils

        return EncryptionUtils.decrypt(cipher)

    @staticmethod
    def _get_connection_secrets(config: dict):
        """从配置记录提取连接用的明文密码/私钥/口令。

        优先用 get_with_secret 的 *_decrypted 明文键；
        兜底走密文列 + _decrypt_password 兼容路径。
        """
        password = config.get("password_decrypted")
        if password is None:
            password = SSHToolService._decrypt_password(config.get("password_encrypted"))
        private_key = config.get("private_key_decrypted")
        if private_key is None:
            private_key = SSHToolService._decrypt_password(config.get("private_key_encrypted"))
        passphrase = config.get("passphrase_decrypted")
        if passphrase is None:
            passphrase = SSHToolService._decrypt_password(config.get("passphrase_encrypted"))
        return password, private_key, passphrase

    @staticmethod
    def get_configs(user_id: str) -> List[SSHConfigResponse]:
        """获取当前用户的所有 SSH 配置（合并本地 + 服务器，脱敏）"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        rows: list[dict] = []

        try:
            rows.extend(get_repository(StorageLocation.LOCAL, "ssh").list(user_id))
        except Exception as exc:
            logger.warning("读取本地 SSH 配置失败：%s", exc)

        available, _ = server_available()
        if available:
            try:
                rows.extend(get_repository(StorageLocation.SERVER, "ssh").list(user_id))
            except Exception as exc:
                logger.warning("读取服务器 SSH 配置失败：%s", exc)

        rows.sort(key=lambda r: r.get("created_at") or datetime.min, reverse=True)
        return [SSHToolService._row_to_response(row) for row in rows]

    @staticmethod
    def get_config(user_id: str, config_id: str) -> Optional[SSHConfigResponse]:
        """获取单条配置（自动定位存储位置，脱敏）"""
        repo, _location = SSHToolService._locate(user_id, config_id)
        if repo is None:
            return None
        row = repo.get(config_id, user_id)
        if row is None:
            return None
        return SSHToolService._row_to_response(row)

    @staticmethod
    def _locate(user_id: str, config_id: str):
        """定位配置所在位置与仓储；找不到返回 (None, None)"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        for location in (StorageLocation.LOCAL, StorageLocation.SERVER):
            try:
                repo = get_repository(location, "ssh")
            except Exception:
                continue
            if repo.get(config_id, user_id):
                return repo, location
        return None, None

    @staticmethod
    def _assert_alias_unique(user_id: str, alias: str, exclude_config_id: str | None = None) -> None:
        """别名唯一性 —— 跨本地与服务器两侧检查"""
        from app.storage.locator import StorageLocation, server_available
        from app.storage.repository import get_repository

        locations = [StorageLocation.LOCAL]
        available, _ = server_available()
        if available:
            locations.append(StorageLocation.SERVER)

        for location in locations:
            try:
                repo = get_repository(location, "ssh")
                existing = repo.find_by_alias(user_id, alias)
            except Exception:
                continue
            if existing and existing.get("id") != exclude_config_id:
                raise ValueError(f"别名 '{alias}' 已存在（存储位置：{location.value}）")

    @staticmethod
    def create_config(
        user_id: str, request: CreateSSHRequest, storage_location: StorageLocation
    ) -> SSHConfigResponse:
        """创建 SSH 连接配置（敏感字段按存储位置加密）"""
        from app.storage.locator import StorageLocation
        from app.storage.repository import get_repository

        alias = SSHToolService._normalize(request.alias)
        host = SSHToolService._normalize(request.host)
        username = SSHToolService._normalize(request.username)
        group_name = SSHToolService._normalize(request.group_name)

        if not alias or not host or not username:
            raise HTTPException(status_code=400, detail="Invalid configuration")
        SSHToolService._validate_port(request.port)

        SSHToolService._assert_alias_unique(user_id, alias)

        if not isinstance(storage_location, StorageLocation):
            storage_location = StorageLocation.from_value(storage_location)

        repo = get_repository(storage_location, "ssh")
        config_id = str(uuid.uuid4())
        now = datetime.now()

        payload = {
            "id": config_id,
            "alias": alias,
            "host": host,
            "port": request.port,
            "username": username,
            "group_name": group_name,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        # 敏感字段用目标仓储的密钥加密（本地用本地密钥，远程用服务器密钥）
        if request.password:
            payload["password_encrypted"] = repo._encrypt(request.password)
        if request.private_key:
            payload["private_key_encrypted"] = repo._encrypt(request.private_key)
        if request.passphrase:
            payload["passphrase_encrypted"] = repo._encrypt(request.passphrase)

        repo.create(user_id, payload, storage_location)

        row = repo.get(config_id, user_id)
        if row is None:
            raise RuntimeError("SSH 配置创建后无法读回")
        logger.info("SSH config created: %s (storage=%s)", config_id, storage_location.value)
        return SSHToolService._row_to_response(row)

    @staticmethod
    def update_config(
        user_id: str,
        request: UpdateSSHRequest,
        storage_location: Optional[StorageLocation] = None,
    ) -> SSHConfigResponse:
        """更新配置；显式传位置直接用指定仓储，传 None 自动定位"""
        from app.storage.locator import StorageLocation

        if storage_location is not None:
            if not isinstance(storage_location, StorageLocation):
                storage_location = StorageLocation.from_value(storage_location)
            repo = get_repository(storage_location, "ssh")
            location = storage_location
        else:
            repo, location = SSHToolService._locate(user_id, request.id)
        if repo is None:
            raise HTTPException(status_code=404, detail="Config not found")

        existing = repo.get(request.id, user_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Config not found")

        updates: dict = {}

        if request.alias is not None:
            alias = SSHToolService._normalize(request.alias)
            if not alias:
                raise HTTPException(status_code=400, detail="Invalid alias")
            if alias != existing.get("alias"):
                SSHToolService._assert_alias_unique(user_id, alias, exclude_config_id=request.id)
            updates["alias"] = alias

        if request.host is not None:
            host = SSHToolService._normalize(request.host)
            if not host:
                raise HTTPException(status_code=400, detail="Invalid host")
            updates["host"] = host

        if request.port is not None:
            SSHToolService._validate_port(request.port)
            updates["port"] = request.port

        if request.username is not None:
            username = SSHToolService._normalize(request.username)
            if not username:
                raise HTTPException(status_code=400, detail="Invalid username")
            updates["username"] = username

        if request.password is not None:
            updates["password_encrypted"] = repo._encrypt(request.password) if request.password else None

        if request.private_key is not None:
            updates["private_key_encrypted"] = repo._encrypt(request.private_key) if request.private_key else None

        if request.passphrase is not None:
            updates["passphrase_encrypted"] = repo._encrypt(request.passphrase) if request.passphrase else None

        if request.group_name is not None:
            updates["group_name"] = SSHToolService._normalize(request.group_name)

        if request.is_active is not None:
            updates["is_active"] = request.is_active

        if not updates:
            return SSHToolService._row_to_response(existing)

        updated = repo.update(request.id, user_id, updates, location)
        if updated is None:
            raise HTTPException(status_code=404, detail="Config not found")
        logger.info("SSH config updated: %s", request.id)
        return SSHToolService._row_to_response(updated)

    @staticmethod
    def delete_config(user_id: str, config_id: str) -> bool:
        """删除配置（本地为硬删除，服务器侧由仓储决定）"""
        repo, _location = SSHToolService._locate(user_id, config_id)
        if repo is None:
            return False
        deleted = repo.delete(config_id, user_id)
        if deleted:
            logger.info("SSH config deleted: %s", config_id)
        return deleted

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
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": "Authentication failed"}))
            except Exception:
                pass
            await websocket.close(code=4003, reason="Authentication failed")
            return

        config = SSHToolService._get_config_record(config_id, user_id)
        if not config:
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": "Config not found"}))
            except Exception:
                pass
            await websocket.close(code=4000, reason="Config not found")
            return

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        channel = None
        try:
            password, private_key, passphrase = SSHToolService._get_connection_secrets(config)
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
            # 防止被 server 端 TCP idle timeout 切断
            ssh.get_transport().set_keepalive(30)

            channel = ssh.invoke_shell(term='xterm-256color', width=cols, height=rows)
            # 设置 5s 超时,避免 recv 永久阻塞,让循环有机会响应 stop_event
            channel.settimeout(5.0)
            logger.info("SSH session started: user_id=%s config_id=%s", user_id, config_id)

            stop_event = asyncio.Event()

            async def send_pong():
                """每 30s 向前端发一次 pong,前端以 90s 无数据为死亡判定;channel 死亡时主动关闭 WS"""
                while not stop_event.is_set():
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=30.0)
                        return  # stop_event 被 set,退出
                    except asyncio.TimeoutError:
                        pass
                    # 检查 SSH channel 是否仍然存活
                    if channel is not None and (channel.closed or not channel.get_transport() or not channel.get_transport().is_active()):
                        try:
                            await websocket.send_text(json.dumps({"type": "error", "message": "SSH 通道已断开"}))
                        except Exception:
                            pass
                        break
                    try:
                        if websocket.client_state.name == "CONNECTED":
                            await websocket.send_text(json.dumps({"type": "pong"}))
                    except Exception:
                        break

            async def receive_from_client():
                while not stop_event.is_set():
                    try:
                        data = await websocket.receive_text()
                    except WebSocketDisconnect:
                        break
                    except Exception:
                        break
                    try:
                        message = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    message_type = message.get('type')
                    if message_type == 'resize' and channel is not None:
                        try:
                            channel.resize_pty(width=int(message.get('cols', cols)), height=int(message.get('rows', rows)))
                        except Exception:
                            pass
                    elif message_type == 'input' and channel is not None:
                        try:
                            channel.send(message.get('data', ''))
                        except Exception as e:
                            logger.warning("SSH channel send failed: %s", e)
                            try:
                                safe_msg = str(e)[:200].encode('ascii', 'ignore').decode('ascii')
                                await websocket.send_text(json.dumps({"type": "error", "message": f"SSH 通道异常: {safe_msg}"}))
                            except Exception:
                                pass
                            stop_event.set()
                            break
                    elif message_type == 'ping':
                        # 兼容旧协议,后端不再依赖前端 ping
                        pass

            async def send_to_client():
                loop = asyncio.get_event_loop()
                while not stop_event.is_set():
                    if channel is None:
                        break
                    if channel.exit_status_ready():
                        try:
                            await websocket.send_text(json.dumps({"type": "exit"}))
                        except Exception:
                            pass
                        break
                    try:
                        # 在 executor 里跑阻塞的 recv,settimeout(5.0) 保证最多阻塞 5s
                        data = await loop.run_in_executor(None, channel.recv, 4096)
                    except Exception as e:
                        # 空闲超时是正常的,继续循环。
                        # 注意: Python 3.10+ 中 socket.timeout 即 TimeoutError,且 str(e) 为空串,
                        # 不能用字符串匹配判断,必须按类型判断,否则空闲 5s 后输出循环会被误杀
                        if isinstance(e, (TimeoutError, socket.timeout)) or 'timed out' in str(e).lower() or 'timeout' in str(e).lower():
                            continue
                        # 其他异常视为会话结束
                        logger.warning("send_to_client recv error: %r", e)
                        break
                    if not data:
                        try:
                            await websocket.send_text(json.dumps({"type": "exit"}))
                        except Exception:
                            pass
                        break
                    try:
                        await websocket.send_text(data.decode('utf-8', errors='ignore'))
                    except Exception:
                        break

            pong_task = asyncio.create_task(send_pong())
            try:
                await asyncio.gather(receive_from_client(), send_to_client())
            finally:
                stop_event.set()
                pong_task.cancel()
                try:
                    await pong_task
                except (asyncio.CancelledError, Exception):
                    pass
        except Exception as e:
            logger.error("SSH connection failed: %s", str(e))
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": "SSH connection failed"}))
            except Exception:
                pass
            try:
                await websocket.close(code=4000, reason="SSH connection failed")
            except Exception:
                pass
        finally:
            try:
                ssh.close()
            except Exception:
                pass
            logger.info("SSH session closed: user_id=%s config_id=%s", user_id, config_id)

    # ============ SFTP 文件传输功能 ============

    @staticmethod
    def _get_sftp_client(config_id: str, user_id: str):
        """获取 SFTP 客户端"""
        config = SSHToolService._get_config_record(config_id, user_id)
        if not config:
            raise ValueError("Configuration not found")

        password, private_key, passphrase = SSHToolService._get_connection_secrets(config)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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

        return ssh.open_sftp(), ssh

    @staticmethod
    def sftp_list_files(config_id: str, user_id: str, request: SFTPListRequest) -> SFTPListResponse:
        """列出远程目录文件"""
        try:
            sftp, ssh = SSHToolService._get_sftp_client(config_id, user_id)
            try:
                files = []
                for entry in sftp.listdir_attr(request.path):
                    # 获取文件详情
                    stat = sftp.stat(f"{request.path}/{entry.filename}")
                    files.append(SFTPFileInfo(
                        name=entry.filename,
                        path=f"{request.path}/{entry.filename}",
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        is_directory=entry.st_mode & 0o40000 != 0,
                        permissions=oct(stat.st_mode)[-3:]
                    ))

                return SFTPListResponse(files=files, current_path=request.path)
            finally:
                sftp.close()
                ssh.close()
        except Exception as e:
            logger.error(f"SFTP list files failed: {e}")
            raise e

    @staticmethod
    def sftp_download_file(config_id: str, user_id: str, request: SFTPDownloadRequest) -> SFTPDownloadResponse:
        """下载远程文件"""
        try:
            sftp, ssh = SSHToolService._get_sftp_client(config_id, user_id)
            try:
                stat = sftp.stat(request.remote_path)
                file_size = stat.st_size

                # 判断是否为文本文件
                is_text = request.remote_path.lower().endswith(('.txt', '.log', '.csv', '.json', '.xml', '.py', '.js', '.ts', '.md'))

                if is_text and file_size < 1024 * 1024:  # 小于 1MB 的文本文件直接返回内容
                    with sftp.open(request.remote_path, 'r') as f:
                        content = f.read()
                    return SFTPDownloadResponse(
                        file_name=request.remote_path.split('/')[-1],
                        file_size=file_size,
                        content=content
                    )
                else:
                    # 二进制文件需要保存到临时目录
                    import base64
                    with sftp.open(request.remote_path, 'rb') as f:
                        file_data = f.read()
                    content = base64.b64encode(file_data).decode('utf-8')
                    return SFTPDownloadResponse(
                        file_name=request.remote_path.split('/')[-1],
                        file_size=file_size,
                        content=content
                    )
            finally:
                sftp.close()
                ssh.close()
        except Exception as e:
            logger.error(f"SFTP download failed: {e}")
            raise e

    @staticmethod
    def sftp_upload_file(config_id: str, user_id: str, request: SFTPUploadRequest) -> SFTPUploadResponse:
        """上传文件到远程"""
        try:
            sftp, ssh = SSHToolService._get_sftp_client(config_id, user_id)
            try:
                import base64

                # 解码文件内容
                if request.is_base64:
                    file_data = base64.b64decode(request.content)
                else:
                    file_data = request.content.encode('utf-8')

                # 确保远程目录存在
                remote_dir = '/'.join(request.remote_path.split('/')[:-1])
                if remote_dir:
                    try:
                        sftp.stat(remote_dir)
                    except FileNotFoundError:
                        # 递归创建目录
                        SSHToolService._mkdir_p(sftp, remote_dir)

                # 上传文件
                with sftp.open(request.remote_path, 'wb') as f:
                    f.write(file_data)

                stat = sftp.stat(request.remote_path)

                return SFTPUploadResponse(
                    success=True,
                    remote_path=request.remote_path,
                    file_size=stat.st_size
                )
            finally:
                sftp.close()
                ssh.close()
        except Exception as e:
            logger.error(f"SFTP upload failed: {e}")
            raise e

    @staticmethod
    def _mkdir_p(sftp, remote_dir):
        """递归创建远程目录"""
        dirs = remote_dir.strip('/').split('/')
        path = ''
        for d in dirs:
            path += '/' + d
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)

    @staticmethod
    def sftp_delete(config_id: str, user_id: str, request: SFTPDeleteRequest) -> SFTPDeleteResponse:
        """删除远程文件或目录"""
        try:
            sftp, ssh = SSHToolService._get_sftp_client(config_id, user_id)
            try:
                stat = sftp.stat(request.remote_path)
                is_dir = stat.st_mode & 0o40000 != 0

                if is_dir:
                    # 递归删除目录
                    SSHToolService._rmtree(sftp, request.remote_path)
                else:
                    sftp.remove(request.remote_path)

                return SFTPDeleteResponse(success=True, message=f"Deleted: {request.remote_path}")
            finally:
                sftp.close()
                ssh.close()
        except Exception as e:
            logger.error(f"SFTP delete failed: {e}")
            raise e

    @staticmethod
    def _rmtree(sftp, remote_path):
        """递归删除目录"""
        for entry in sftp.listdir_attr(remote_path):
            sub_path = f"{remote_path}/{entry.filename}"
            if entry.st_mode & 0o40000 != 0:
                SSHToolService._rmtree(sftp, sub_path)
            else:
                sftp.remove(sub_path)
        sftp.rmdir(remote_path)

    @staticmethod
    def sftp_mkdir(config_id: str, user_id: str, request: SFTPMkdirRequest) -> SFTPMkdirResponse:
        """创建远程目录"""
        try:
            sftp, ssh = SSHToolService._get_sftp_client(config_id, user_id)
            try:
                SSHToolService._mkdir_p(sftp, request.remote_path)
                return SFTPMkdirResponse(success=True, remote_path=request.remote_path)
            finally:
                sftp.close()
                ssh.close()
        except Exception as e:
            logger.error(f"SFTP mkdir failed: {e}")
            raise e

    @staticmethod
    def sftp_rename(config_id: str, user_id: str, request: SFTPRenameRequest) -> SFTPRenameResponse:
        """重命名/移动文件"""
        try:
            sftp, ssh = SSHToolService._get_sftp_client(config_id, user_id)
            try:
                sftp.rename(request.old_path, request.new_path)
                return SFTPRenameResponse(success=True, old_path=request.old_path, new_path=request.new_path)
            finally:
                sftp.close()
                ssh.close()
        except Exception as e:
            logger.error(f"SFTP rename failed: {e}")
            raise e

    # ============ SSH 隧道功能 ============

    _tunnels: Dict[str, dict] = {}

    @staticmethod
    async def create_tunnel(config_id: str, user_id: str, request: SSHTunnelRequest) -> SSHTunnelResponse:
        """创建 SSH 隧道"""
        try:
            config = SSHToolService._get_config_record(config_id, user_id)
            if not config:
                raise ValueError("Configuration not found")

            password, private_key, passphrase = SSHToolService._get_connection_secrets(config)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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

            tunnel_id = str(uuid.uuid4())

            # 启动隧道（简化版本，实际生产需要更复杂的处理）
            if request.tunnel_type == TunnelProtocol.LOCAL:
                # 本地端口转发
                transport = ssh.get_transport()
                transport.request_port_forward('', request.local_port)
                # 注意：完整的端口转发需要单独的线程来处理连接

            SSHToolService._tunnels[tunnel_id] = {
                'ssh': ssh,
                'tunnel_type': request.tunnel_type.value,
                'local_port': request.local_port,
                'remote_host': request.remote_host,
                'remote_port': request.remote_port,
                'created_at': datetime.now()
            }

            return SSHTunnelResponse(
                tunnel_id=tunnel_id,
                status='active',
                message=f"Tunnel created: {request.local_port} -> {request.remote_host}:{request.remote_port}"
            )
        except Exception as e:
            logger.error(f"Create tunnel failed: {e}")
            raise e

    @staticmethod
    def stop_tunnel(tunnel_id: str) -> bool:
        """停止隧道"""
        if tunnel_id in SSHToolService._tunnels:
            tunnel = SSHToolService._tunnels[tunnel_id]
            tunnel['ssh'].close()
            del SSHToolService._tunnels[tunnel_id]
            return True
        return False

    @staticmethod
    def list_tunnels() -> SSHTunnelListResponse:
        """列出所有活跃隧道"""
        tunnels = []
        for tunnel_id, tunnel in SSHToolService._tunnels.items():
            tunnels.append(SSHTunnelInfo(
                tunnel_id=tunnel_id,
                tunnel_type=tunnel['tunnel_type'],
                local_port=tunnel['local_port'],
                remote_host=tunnel['remote_host'],
                remote_port=tunnel['remote_port'],
                created_at=tunnel['created_at']
            ))
        return SSHTunnelListResponse(tunnels=tunnels)

    # ============ 批量命令执行 ============

    @staticmethod
    def execute_batch_commands(config_id: str, user_id: str, request: BatchCommandRequest) -> BatchCommandResponse:
        """批量执行命令"""
        try:
            config = SSHToolService._get_config_record(config_id, user_id)
            if not config:
                raise ValueError("Configuration not found")

            password, private_key, passphrase = SSHToolService._get_connection_secrets(config)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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

            results = []
            success_count = 0
            failed_count = 0

            for cmd in request.commands:
                try:
                    start_time = time.time()
                    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=request.timeout)
                    exit_code = stdout.channel.recv_exit_status()
                    execution_time = (time.time() - start_time) * 1000

                    result = BatchCommandResult(
                        command=cmd,
                        stdout=stdout.read().decode('utf-8', errors='ignore'),
                        stderr=stderr.read().decode('utf-8', errors='ignore'),
                        exit_code=exit_code,
                        execution_time_ms=execution_time
                    )

                    if exit_code == 0:
                        success_count += 1
                    else:
                        failed_count += 1
                        result.error = f"Exit code: {exit_code}"

                    results.append(result)
                except Exception as e:
                    failed_count += 1
                    results.append(BatchCommandResult(
                        command=cmd,
                        stdout="",
                        stderr="",
                        exit_code=-1,
                        execution_time_ms=0,
                        error=str(e)
                    ))

            ssh.close()

            return BatchCommandResponse(
                results=results,
                total_count=len(request.commands),
                success_count=success_count,
                failed_count=failed_count
            )
        except Exception as e:
            logger.error(f"Batch commands failed: {e}")
            raise e
