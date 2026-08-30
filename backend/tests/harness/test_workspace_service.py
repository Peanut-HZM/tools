"""WorkspaceService 单元测试（P2-③）"""
import uuid

import pytest

from app.services.harness.workspace import (
    PathEscapeError,
    WorkspaceFileError,
    WorkspaceService,
)

AID = str(uuid.uuid4())
UID = str(uuid.uuid4())
UID2 = str(uuid.uuid4())


@pytest.fixture
def ws(tmp_path):
    return WorkspaceService(root=tmp_path)


def test_workspace_dir_creates(ws, tmp_path):
    d = ws.workspace_dir(AID, UID)
    assert d.is_dir()
    assert tmp_path in d.parents or d.parent.parent == tmp_path


def test_safe_resolve_normal(ws, tmp_path):
    p = ws.safe_resolve(AID, UID, "notes/todo.txt")
    assert tmp_path in p.parents


def test_safe_resolve_rejects_escape(ws):
    with pytest.raises(PathEscapeError):
        ws.safe_resolve(AID, UID, "../escape.txt")
    with pytest.raises(PathEscapeError):
        ws.safe_resolve(AID, UID, "a/../../b.txt")
    with pytest.raises(PathEscapeError):
        ws.safe_resolve(AID, UID, "C:\\Windows\\system32")


def test_read_write_roundtrip(ws):
    ws.write_file(AID, UID, "a/b.txt", "hello 世界")
    content, truncated = ws.read_file(AID, UID, "a/b.txt")
    assert content == "hello 世界"
    assert truncated is False


def test_write_append(ws):
    ws.write_file(AID, UID, "log.txt", "line1\n")
    ws.write_file(AID, UID, "log.txt", "line2\n", mode="append")
    content, _ = ws.read_file(AID, UID, "log.txt")
    assert content == "line1\nline2\n"


def test_write_invalid_mode(ws):
    with pytest.raises(WorkspaceFileError):
        ws.write_file(AID, UID, "x.txt", "data", mode="delete")


def test_read_missing_file(ws):
    with pytest.raises(WorkspaceFileError):
        ws.read_file(AID, UID, "nope.txt")


def test_read_binary_rejected(ws, tmp_path):
    ws.write_file(AID, UID, "bin.dat", "x")
    binary_path = ws.safe_resolve(AID, UID, "bin.dat")
    binary_path.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(WorkspaceFileError):
        ws.read_file(AID, UID, "bin.dat")


def test_read_truncation(ws):
    ws.write_file(AID, UID, "big.txt", "x" * 1000)
    content, truncated = ws.read_file(AID, UID, "big.txt", max_bytes=100)
    assert truncated is True
    assert len(content.encode("utf-8")) <= 100 + 100  # 截断按字节，字符切分留余量


def test_write_over_1mb_rejected(ws):
    with pytest.raises(WorkspaceFileError):
        ws.write_file(AID, UID, "huge.txt", "x" * (1024 * 1024 + 1))


def test_list_files(ws):
    ws.write_file(AID, UID, "a.txt", "1")
    ws.write_file(AID, UID, "sub/b.txt", "22")
    files = ws.list_files(AID, UID)
    rels = {f["path"] for f in files}
    assert rels == {"a.txt", "sub/b.txt"}
    assert {f["size_bytes"] for f in files} == {1, 2}


def test_isolation_between_users(ws):
    ws.write_file(AID, UID, "secret.txt", "mine")
    with pytest.raises(WorkspaceFileError):
        ws.read_file(AID, UID2, "secret.txt")
