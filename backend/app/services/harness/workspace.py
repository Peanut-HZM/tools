"""WorkspaceService — Agent 工作区（文件沙箱）

P2-③ 多模态沙箱
每个 (agent_id, user_id) 一个隔离目录；所有路径操作限制在工作区内
（resolve + is_relative_to 白名单校验，防 `../` 与绝对路径逃逸）。
"""
import logging
import os
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# 单文件写入上限（字节）
_MAX_WRITE_BYTES = 1024 * 1024
# 列表条数上限
_MAX_LIST_ENTRIES = 200


class PathEscapeError(Exception):
    """路径逃逸工作区（安全拒绝）"""
    pass


class WorkspaceFileError(Exception):
    """工作区文件操作失败（不存在/二进制/超限/非法参数）"""
    pass


def _default_root() -> Path:
    """工作区根目录：环境变量 WORKSPACE_ROOT 优先，否则 <backend>/data/agent_workspaces"""
    env_root = os.environ.get("WORKSPACE_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[3] / "data" / "agent_workspaces"


class WorkspaceService:
    """Agent 工作区：路径安全 + 文件读写 + 列表"""

    def __init__(self, root: Path | None = None):
        self._root = (root or _default_root()).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def workspace_dir(self, agent_id: str, user_id: str) -> Path:
        """获取（并确保存在）指定 (agent, user) 的工作区目录"""
        d = self._root / str(agent_id) / str(user_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def safe_resolve(self, agent_id: str, user_id: str, relative_path: str) -> Path:
        """解析工作区内相对路径；逃逸时抛 PathEscapeError

        安全：join 后 resolve（展开符号链接），再校验仍位于该 (agent, user)
        工作区目录内。绝对路径输入会被 join 语义丢弃后按逃逸处理。
        """
        base = self.workspace_dir(agent_id, user_id)
        candidate = (base / relative_path).resolve()
        if candidate != base and base not in candidate.parents:
            logger.warning("工作区路径逃逸被拒绝: %s", relative_path[:200])
            raise PathEscapeError("path 超出工作区范围")
        return candidate

    def read_file(
        self, agent_id: str, user_id: str, path: str, max_bytes: int = 65536
    ) -> Tuple[str, bool]:
        """读取文本文件，返回 (内容, 是否截断)

        异常：PathEscapeError / WorkspaceFileError（不存在或非文本）
        """
        target = self.safe_resolve(agent_id, user_id, path)
        if not target.is_file():
            raise WorkspaceFileError(f"文件不存在: {path}")
        try:
            data = target.read_bytes()
        except OSError as e:
            raise WorkspaceFileError(f"读取失败: {type(e).__name__}")

        truncated = len(data) > max_bytes
        data = data[:max_bytes]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise WorkspaceFileError("非文本文件（utf-8 解码失败）")
        return text, truncated

    def write_file(
        self, agent_id: str, user_id: str, path: str, content: str, mode: str = "overwrite"
    ) -> dict:
        """写入文本文件（overwrite / append），返回 {path, size_bytes, mode}

        异常：PathEscapeError / WorkspaceFileError（超限或非法 mode）
        """
        if mode not in ("overwrite", "append"):
            raise WorkspaceFileError(f"非法 mode: {mode}")
        payload = content.encode("utf-8")
        if len(payload) > _MAX_WRITE_BYTES:
            raise WorkspaceFileError("内容超过 1MB 上限")

        target = self.safe_resolve(agent_id, user_id, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if mode == "append":
                # newline="" 禁止平台换行翻译（Windows 下避免 \n → \r\n）
                with open(target, "a", encoding="utf-8", newline="") as f:
                    f.write(content)
            else:
                target.write_text(content, encoding="utf-8")
        except OSError as e:
            raise WorkspaceFileError(f"写入失败: {type(e).__name__}")

        return {"path": path, "size_bytes": len(payload), "mode": mode}

    def list_files(self, agent_id: str, user_id: str, path: str = "") -> List[dict]:
        """递归列出工作区文件，返回 [{path(相对), size_bytes}]，上限 200 条"""
        base = self.safe_resolve(agent_id, user_id, path) if path else self.workspace_dir(agent_id, user_id)
        if not base.is_dir():
            raise WorkspaceFileError(f"目录不存在: {path}")

        files: List[dict] = []
        for p in sorted(base.rglob("*")):
            if p.is_file():
                files.append({
                    "path": p.relative_to(self.workspace_dir(agent_id, user_id)).as_posix(),
                    "size_bytes": p.stat().st_size,
                })
                if len(files) >= _MAX_LIST_ENTRIES:
                    break
        return files
