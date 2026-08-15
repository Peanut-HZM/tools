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
        try:
            client = self._get_or_connect(server)
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
            entries = [self._pool.pop(k) for k in list(self._pool.keys())]
        for entry in entries:
            try:
                entry["client"].close()
            except Exception:
                pass
        logger.info("SSH 连接池已全部关闭")


pool = SSHConnectionPool()
