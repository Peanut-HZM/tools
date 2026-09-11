"""ZCode Token 用量读取器测试

覆盖 _find_zcode_db 路径发现、fetch_zcode_records SQL 行为、
sync_token_usage zcode 分支集成。
"""
import os
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


# ========== 路径发现测试 ==========

class TestFindZcodeDb:
    """_find_zcode_db 路径候选与诊断输出"""

    def test_mac_home_path_hit(self, tmp_path, monkeypatch):
        """Mac home 路径 ~/.zcode/cli/db/db.sqlite 命中"""
        zcode_dir = tmp_path / ".zcode" / "cli" / "db"
        zcode_dir.mkdir(parents=True)
        db_file = zcode_dir / "db.sqlite"
        db_file.touch()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("APPDATA", raising=False)

        from app.utils.zcode_usage_reader import _find_zcode_db
        result = _find_zcode_db()

        assert result["path"] == str(db_file)
        # 命中的 candidate 应有 exists=True, readable=True
        hit = next(c for c in result["candidates_checked"] if c["path"] == str(db_file))
        assert hit["exists"] is True
        assert hit["readable"] is True

    def test_macos_appdata_hit_when_home_missing(self, tmp_path, monkeypatch):
        """macOS AppData 路径 ~/Library/Application Support/ZCode/cli/db/db.sqlite 命中"""
        # home 路径不存在
        # AppData 路径存在
        appdata_dir = tmp_path / "Library" / "Application Support" / "ZCode" / "cli" / "db"
        appdata_dir.mkdir(parents=True)
        db_file = appdata_dir / "db.sqlite"
        db_file.touch()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("APPDATA", raising=False)

        from app.utils.zcode_usage_reader import _find_zcode_db
        result = _find_zcode_db()

        assert result["path"] == str(db_file)

    def test_windows_appdata_hit(self, tmp_path, monkeypatch):
        """Windows APPDATA 路径 %APPDATA%/ZCode/cli/db/db.sqlite 命中"""
        appdata_dir = tmp_path / "ZCode" / "cli" / "db"
        appdata_dir.mkdir(parents=True)
        db_file = appdata_dir / "db.sqlite"
        db_file.touch()
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nonexistent")
        monkeypatch.setenv("APPDATA", str(tmp_path))

        from app.utils.zcode_usage_reader import _find_zcode_db
        result = _find_zcode_db()

        assert result["path"] == str(db_file)

    def test_no_candidate_returns_none_with_full_diagnostics(self, tmp_path, monkeypatch):
        """所有候选都不存在时 path=None 但 candidates_checked 含全部"""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("APPDATA", raising=False)

        from app.utils.zcode_usage_reader import _find_zcode_db
        result = _find_zcode_db()

        assert result["path"] is None
        assert len(result["candidates_checked"]) >= 3  # Mac home + macOS AppData + Windows
        for c in result["candidates_checked"]:
            assert c["exists"] is False
            assert c["reason"] in ("FILE_NOT_FOUND", None)

    def test_unreadable_file_marked_not_readable(self, tmp_path, monkeypatch):
        """DB 存在但不可读时 readable=False，整体 path=None"""
        zcode_dir = tmp_path / ".zcode" / "cli" / "db"
        zcode_dir.mkdir(parents=True)
        db_file = zcode_dir / "db.sqlite"
        db_file.touch()
        db_file.chmod(0o000)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("APPDATA", raising=False)

        try:
            from app.utils.zcode_usage_reader import _find_zcode_db
            result = _find_zcode_db()

            # 当前实现是 _find_zcode_db()，先用 os.access 检查 readable
            # 在 chmod 000 下，os.access(R_OK) 应返回 False
            hit = next((c for c in result["candidates_checked"] if c["path"] == str(db_file)), None)
            assert hit is not None
            assert hit["exists"] is True
            assert hit["readable"] is False
            assert hit["reason"] == "NOT_READABLE"
            assert result["path"] is None
        finally:
            db_file.chmod(0o644)  # 恢复权限以便 tmp_path 清理
