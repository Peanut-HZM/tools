"""OpenCode 原生 Token 用量读取器测试

覆盖 ccusage ``opencode`` 适配器的关键语义：

- **Token 口径**：四桶映射、``reasoning`` 进 extra 桶、``tokens.total`` 兜底、
  ``input`` 不做 cache 扣减、全 0 行丢弃
- **模型名解析**：v1 的 ``modelID`` / v2 的 ``model.id``、原值不做归一化、
  缺 model / provider 的行丢弃
- **时区归桶**：按本机时区的自然日切分
- **去重**：v1 / v2 / 旧 JSON 文件三源之间按 message id 去重
- **路径发现**：``OPENCODE_DATA_DIR`` / ``XDG_DATA_HOME`` / 默认目录
- **fork 复制剔除**：fork 会话开头复制自父会话的消息不重复统计
"""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 公共夹具
# ---------------------------------------------------------------------------

#: 2026-01-02T08:00:00+08:00（本机时区）
TS_2026_01_02 = 1767312000000

#: 2026-01-03T00:30:00+08:00（本机时区）—— 用于验证跨 UTC 日界线的归桶
TS_2026_01_03_LOCAL = int(
    datetime(2026, 1, 3, 0, 30, 0).astimezone().timestamp() * 1000
)


def _legacy_payload(
    *,
    model: str = "kimi-k2.5-free",
    provider: str = "opencode",
    input_tokens: int = 100,
    output_tokens: int = 10,
    reasoning: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    total: int = 0,
    created: int = TS_2026_01_02,
    cost: float | None = None,
) -> dict:
    """构造 v1（``message`` 表 / JSON 文件）形态的 payload。"""
    payload = {
        "role": "assistant",
        "time": {"created": created},
        "providerID": provider,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "reasoning": reasoning,
            "cache": {"read": cache_read, "write": cache_write},
        },
    }
    if model is not None:
        payload["modelID"] = model
    if total:
        payload["tokens"]["total"] = total
    if cost is not None:
        payload["cost"] = cost
    return payload


def _v2_payload(
    *,
    model: str = "deepseek-v4.1-flash-free",
    provider: str = "opencode",
    input_tokens: int = 100,
    output_tokens: int = 10,
    reasoning: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    total: int = 0,
    created: int | None = TS_2026_01_02,
) -> dict:
    """构造 v2（``session_message`` 表）形态的 payload。"""
    payload = {
        "role": "assistant",
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "reasoning": reasoning,
            "cache": {"read": cache_read, "write": cache_write},
        },
    }
    if created is not None:
        payload["time"] = {"created": created}
    if model is not None:
        payload["model"] = {"providerID": provider, "id": model}
    elif provider is not None:
        payload["providerID"] = provider
    if total:
        payload["tokens"]["total"] = total
    return payload


def _create_db(
    db_path: Path,
    *,
    v1_rows: list[tuple] | None = None,
    v2_rows: list[tuple] | None = None,
    forks: list[tuple] | None = None,
) -> None:
    """创建 opencode 形态的 SQLite 库。

    ``v1_rows``: ``(id, session_id, time_created, data_json)``
    ``v2_rows``: ``(id, session_id, type, seq, time_created, data_json)``
    ``forks``: ``(id, fork_session_id, fork_boundary_json)``
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE message (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                time_created INTEGER NOT NULL DEFAULT 0,
                time_updated INTEGER NOT NULL DEFAULT 0,
                data TEXT
            );
            CREATE TABLE session_message (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                type TEXT,
                seq INTEGER NOT NULL DEFAULT 0,
                time_created INTEGER,
                time_updated INTEGER,
                data TEXT
            );
            CREATE TABLE session_v2 (
                id TEXT PRIMARY KEY,
                fork_session_id TEXT,
                fork_boundary TEXT
            );
            """
        )
        for message_id, session_id, created, data in v1_rows or []:
            conn.execute(
                "INSERT INTO message (id, session_id, time_created, time_updated, data)"
                " VALUES (?,?,?,?,?)",
                (message_id, session_id, created, created, data),
            )
        for message_id, session_id, msg_type, seq, created, data in v2_rows or []:
            conn.execute(
                "INSERT INTO session_message"
                " (id, session_id, type, seq, time_created, time_updated, data)"
                " VALUES (?,?,?,?,?,?,?)",
                (message_id, session_id, msg_type, seq, created, created, data),
            )
        for fork_id, parent_id, boundary in forks or []:
            conn.execute(
                "INSERT INTO session_v2 (id, fork_session_id, fork_boundary) VALUES (?,?,?)",
                (fork_id, parent_id, boundary),
            )
        conn.commit()
    finally:
        conn.close()


def _write_message_file(root: Path, session_id: str, message_id: str, payload: dict) -> None:
    """写入旧版 opencode 的消息 JSON 文件。"""
    directory = root / "storage" / "message" / session_id
    directory.mkdir(parents=True, exist_ok=True)
    body = dict(payload)
    body.setdefault("id", message_id)
    body.setdefault("sessionID", session_id)
    (directory / f"{message_id}.json").write_text(
        json.dumps(body, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture
def opencode_root(tmp_path, monkeypatch):
    """构造一个 opencode 数据根目录，并把读取器指向它。"""
    root = tmp_path / "opencode"
    root.mkdir()
    monkeypatch.setenv("OPENCODE_DATA_DIR", str(root))
    return root


def _read(root: Path, since=date(2026, 1, 1), until=date(2026, 1, 31)):
    from app.utils.agent_readers.opencode_reader import read_opencode_records

    return read_opencode_records(since, until)


# ---------------------------------------------------------------------------
# Token 口径
# ---------------------------------------------------------------------------


class TestTokenAccounting:
    """四桶映射 + reasoning 进 extra + total 兜底"""

    def test_buckets_map_directly_from_tokens(self, opencode_root):
        """input/output/cache_read/cache_write 直接取自 tokens，cache 不从 input 里扣"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(
                        _legacy_payload(
                            input_tokens=100,
                            output_tokens=10,
                            cache_read=500,
                            cache_write=7,
                        )
                    ),
                )
            ],
        )
        record = _read(opencode_root).records[0]
        assert record["input_tokens"] == 100
        assert record["output_tokens"] == 10
        assert record["cache_read_tokens"] == 500
        assert record["cache_creation_tokens"] == 7
        assert record["total_tokens"] == 617

    def test_reasoning_goes_to_extra_bucket(self, opencode_root):
        """reasoning 不进 output，而是进不可见的 extra 桶（只计入 total）"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(reasoning=50)),
                )
            ],
        )
        record = _read(opencode_root).records[0]
        assert record["output_tokens"] == 10
        assert record["total_tokens"] == 100 + 10 + 50

    def test_total_fallback_fills_output_when_output_is_zero(self, opencode_root):
        """tokens.total 超出分桶之和且 output 为 0 时，差值补进 output"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(input_tokens=100, output_tokens=0, total=250)),
                )
            ],
        )
        record = _read(opencode_root).records[0]
        assert record["output_tokens"] == 150
        assert record["total_tokens"] == 250

    def test_total_fallback_adds_to_extra_when_output_present(self, opencode_root):
        """tokens.total 超出分桶之和且 output 非 0 时，差值补进 extra"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(input_tokens=100, output_tokens=50, total=300)),
                )
            ],
        )
        record = _read(opencode_root).records[0]
        assert record["output_tokens"] == 50
        assert record["total_tokens"] == 300

    def test_all_zero_tokens_are_dropped(self, opencode_root):
        """四个桶全 0 且 extra 也 0 的行直接丢弃"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(input_tokens=0, output_tokens=0)),
                )
            ],
        )
        assert _read(opencode_root).records == []

    def test_missing_tokens_block_is_dropped(self, opencode_root):
        """没有 tokens 结构的行直接丢弃"""
        payload = _legacy_payload()
        del payload["tokens"]
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[("msg_1", "ses_1", TS_2026_01_02, json.dumps(payload))],
        )
        assert _read(opencode_root).records == []

    def test_non_object_cache_is_treated_as_zero(self, opencode_root):
        """cache 不是对象时按 0 处理，不影响其它桶"""
        payload = _legacy_payload()
        payload["tokens"]["cache"] = 0
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[("msg_1", "ses_1", TS_2026_01_02, json.dumps(payload))],
        )
        record = _read(opencode_root).records[0]
        assert record["cache_read_tokens"] == 0
        assert record["cache_creation_tokens"] == 0


# ---------------------------------------------------------------------------
# 模型名解析
# ---------------------------------------------------------------------------


class TestModelResolution:
    """v1 modelID / v2 model.id，取原值不做归一化"""

    def test_v1_uses_model_id_field(self, opencode_root):
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(model="kimi-k2.5-free")),
                )
            ],
        )
        assert _read(opencode_root).records[0]["model"] == "kimi-k2.5-free"

    def test_v2_uses_model_object_id(self, opencode_root):
        _create_db(
            opencode_root / "opencode.db",
            v2_rows=[
                (
                    "msg_2",
                    "ses_1",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="deepseek-v4.1-flash-free")),
                )
            ],
        )
        assert _read(opencode_root).records[0]["model"] == "deepseek-v4.1-flash-free"

    @pytest.mark.parametrize("raw", ["k2p6", "claude-opus-4.5", "gemini-3-pro-high"])
    def test_model_name_is_kept_verbatim(self, opencode_root, raw):
        """ccusage 的 resolve/normalize 只用于定价查找，展示名保持原值"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                ("msg_1", "ses_1", TS_2026_01_02, json.dumps(_legacy_payload(model=raw)))
            ],
        )
        assert _read(opencode_root).records[0]["model"] == raw

    def test_missing_model_is_dropped(self, opencode_root):
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                ("msg_1", "ses_1", TS_2026_01_02, json.dumps(_legacy_payload(model=None)))
            ],
        )
        assert _read(opencode_root).records == []

    def test_missing_provider_is_dropped(self, opencode_root):
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(provider=None)),
                )
            ],
        )
        assert _read(opencode_root).records == []

    def test_v2_non_assistant_rows_are_skipped(self, opencode_root):
        """v2 只统计 type == 'assistant' 的消息"""
        _create_db(
            opencode_root / "opencode.db",
            v2_rows=[
                (
                    "msg_user",
                    "ses_1",
                    "user",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload()),
                )
            ],
        )
        assert _read(opencode_root).records == []


# ---------------------------------------------------------------------------
# 时区归桶
# ---------------------------------------------------------------------------


class TestTimezoneBucket:
    """按本机时区的自然日归桶"""

    def test_uses_local_calendar_day(self, opencode_root):
        """UTC 16:30 在本机（UTC+8）是次日 00:30，应归到次日"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_03_LOCAL,
                    json.dumps(_legacy_payload(created=TS_2026_01_03_LOCAL)),
                )
            ],
        )
        record = _read(opencode_root).records[0]
        assert record["record_date"] == date(2026, 1, 3)

    def test_rows_outside_the_window_are_dropped(self, opencode_root):
        """区间外的记录不计入"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload()),
                )
            ],
        )
        assert _read(opencode_root, since=date(2026, 2, 1), until=date(2026, 2, 28)).records == []
        assert len(_read(opencode_root, since=date(2026, 1, 2), until=date(2026, 1, 2)).records) == 1


# ---------------------------------------------------------------------------
# 去重
# ---------------------------------------------------------------------------


class TestDedupe:
    """v1 / v2 / 旧 JSON 文件三源按 message id 去重"""

    def test_same_id_in_v1_and_v2_keeps_v1(self, opencode_root):
        """ccusage 的顺序是 v1 → v2 → JSON，同 id 时先到先得"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_dup",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(input_tokens=100)),
                )
            ],
            v2_rows=[
                (
                    "msg_dup",
                    "ses_1",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(input_tokens=999)),
                )
            ],
        )
        records = _read(opencode_root).records
        assert len(records) == 1
        assert records[0]["input_tokens"] == 100

    def test_json_file_duplicate_of_db_row_kept_once(self, opencode_root):
        """旧 JSON 文件与数据库同 id 时只统计一次"""
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_dup",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(input_tokens=100)),
                )
            ],
        )
        _write_message_file(
            opencode_root,
            "ses_1",
            "msg_dup",
            _legacy_payload(input_tokens=999),
        )
        records = _read(opencode_root).records
        assert len(records) == 1
        assert records[0]["input_tokens"] == 100

    def test_json_file_only_row_is_counted(self, opencode_root):
        """数据库里没有的历史消息文件照常统计"""
        _create_db(opencode_root / "opencode.db")
        _write_message_file(
            opencode_root,
            "ses_1",
            "msg_legacy",
            _legacy_payload(input_tokens=42),
        )
        records = _read(opencode_root).records
        assert len(records) == 1
        assert records[0]["input_tokens"] == 42


# ---------------------------------------------------------------------------
# 路径发现
# ---------------------------------------------------------------------------


class TestPathDiscovery:
    """OPENCODE_DATA_DIR / XDG_DATA_HOME / 默认目录"""

    def test_opencode_data_dir_takes_precedence_without_fallback(self, tmp_path, monkeypatch):
        """设置了 OPENCODE_DATA_DIR 就只用它，不回落默认目录"""
        from app.utils.agent_readers.opencode_reader import _opencode_data_dirs

        configured = tmp_path / "configured"
        configured.mkdir()
        monkeypatch.setenv("OPENCODE_DATA_DIR", str(configured))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        assert _opencode_data_dirs() == [configured]

    def test_empty_opencode_data_dir_returns_nothing(self, tmp_path, monkeypatch):
        """变量存在但为空时不回落（对齐 ccusage）"""
        from app.utils.agent_readers.opencode_reader import _opencode_data_dirs

        monkeypatch.setenv("OPENCODE_DATA_DIR", "")
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        assert _opencode_data_dirs() == []

    def test_non_directory_entries_are_skipped(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.opencode_reader import _opencode_data_dirs

        missing = tmp_path / "missing"
        real = tmp_path / "real"
        real.mkdir()
        monkeypatch.setenv("OPENCODE_DATA_DIR", f"{missing},{real}")
        assert _opencode_data_dirs() == [real]

    def test_xdg_data_home_is_used_when_absolute(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.opencode_reader import _opencode_data_dirs

        xdg = tmp_path / "xdg"
        (xdg / "opencode").mkdir(parents=True)
        monkeypatch.delenv("OPENCODE_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
        assert _opencode_data_dirs() == [xdg / "opencode"]

    def test_relative_xdg_data_home_falls_back_to_default(self, tmp_path, monkeypatch):
        """相对路径的 XDG_DATA_HOME 视为未设置"""
        from app.utils.agent_readers.opencode_reader import _opencode_data_dirs

        monkeypatch.delenv("OPENCODE_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", "relative-xdg")
        default = tmp_path / "home" / ".local" / "share" / "opencode"
        default.mkdir(parents=True)
        monkeypatch.setattr(
            "app.utils.agent_readers.opencode_reader.real_home",
            lambda: tmp_path / "home",
        )
        assert _opencode_data_dirs() == [default]

    def test_default_path_is_local_share_opencode(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.opencode_reader import _opencode_data_dirs

        monkeypatch.delenv("OPENCODE_DATA_DIR", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        default = tmp_path / "home" / ".local" / "share" / "opencode"
        default.mkdir(parents=True)
        monkeypatch.setattr(
            "app.utils.agent_readers.opencode_reader.real_home",
            lambda: tmp_path / "home",
        )
        assert _opencode_data_dirs() == [default]


# ---------------------------------------------------------------------------
# fork 复制剔除
# ---------------------------------------------------------------------------


class TestForkCopyCutoff:
    """fork 会话复制自父会话的那段消息不应重复统计"""

    def test_through_boundary_drops_copied_rows(self, opencode_root):
        """through 边界：seq <= 边界 seq 的行都是复制来的"""
        boundary = json.dumps({"type": "through", "messageID": "msg_p2"})
        _create_db(
            opencode_root / "opencode.db",
            v2_rows=[
                (
                    "msg_p1",
                    "ses_parent",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="parent-model", input_tokens=10)),
                ),
                (
                    "msg_p2",
                    "ses_parent",
                    "assistant",
                    2,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="parent-model", input_tokens=20)),
                ),
                (
                    "msg_f1",
                    "ses_fork",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="fork-model", input_tokens=100)),
                ),
                (
                    "msg_f2",
                    "ses_fork",
                    "assistant",
                    2,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="fork-model", input_tokens=200)),
                ),
                (
                    "msg_f3",
                    "ses_fork",
                    "assistant",
                    3,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="fork-model", input_tokens=300)),
                ),
            ],
            forks=[("ses_fork", "ses_parent", boundary)],
        )
        records = _read(opencode_root).records
        by_model = {record["model"]: record for record in records}
        # 父会话的两条照常统计（复制来的部分只在 fork 里被剔除）
        assert by_model["parent-model"]["input_tokens"] == 30
        # fork 只保留自己生成的第 3 条（seq=3 > cutoff=2）
        assert by_model["fork-model"]["input_tokens"] == 300

    def test_before_boundary_uses_last_parent_seq(self, opencode_root):
        """before 边界：截断到边界之前最后一条父消息的 seq"""
        boundary = json.dumps({"type": "before", "messageID": "msg_p2"})
        _create_db(
            opencode_root / "opencode.db",
            v2_rows=[
                (
                    "msg_p1",
                    "ses_parent",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="parent-model", input_tokens=10)),
                ),
                (
                    "msg_p2",
                    "ses_parent",
                    "assistant",
                    2,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="parent-model", input_tokens=20)),
                ),
                (
                    "msg_f1",
                    "ses_fork",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="fork-model", input_tokens=100)),
                ),
                (
                    "msg_f2",
                    "ses_fork",
                    "assistant",
                    2,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(model="fork-model", input_tokens=200)),
                ),
            ],
            forks=[("ses_fork", "ses_parent", boundary)],
        )
        records = _read(opencode_root).records
        by_model = {record["model"]: record for record in records}
        # 父会话边界之前的 seq=1 被复制，seq=2 是 fork 自己产生的
        assert by_model["fork-model"]["input_tokens"] == 200

    def test_unresolvable_boundary_keeps_all_rows(self, opencode_root):
        """边界无法解析时保留该 fork 的全部消息，不靠猜测丢弃"""
        boundary = json.dumps({"type": "unknown-type", "messageID": "msg_p2"})
        _create_db(
            opencode_root / "opencode.db",
            v2_rows=[
                (
                    "msg_f1",
                    "ses_fork",
                    "assistant",
                    1,
                    TS_2026_01_02,
                    json.dumps(_v2_payload(input_tokens=100)),
                )
            ],
            forks=[("ses_fork", "ses_parent", boundary)],
        )
        records = _read(opencode_root).records
        assert records[0]["input_tokens"] == 100


# ---------------------------------------------------------------------------
# 其它
# ---------------------------------------------------------------------------


class TestRobustness:
    """异常输入只丢该条，不中断整体"""

    def test_broken_row_does_not_break_the_whole_read(self, opencode_root):
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                ("msg_bad", "ses_1", TS_2026_01_02, "{not-json"),
                (
                    "msg_good",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(input_tokens=77)),
                ),
            ],
        )
        records = _read(opencode_root).records
        assert len(records) == 1
        assert records[0]["input_tokens"] == 77

    def test_missing_database_yields_no_records(self, opencode_root):
        """没有安装 opencode 不是异常：静默返回空结果"""
        assert _read(opencode_root).records == []
        assert _read(opencode_root).errors == []

    def test_record_source_metadata(self, opencode_root):
        _create_db(
            opencode_root / "opencode.db",
            v1_rows=[
                (
                    "msg_1",
                    "ses_1",
                    TS_2026_01_02,
                    json.dumps(_legacy_payload(cost=0.25)),
                )
            ],
        )
        record = _read(opencode_root).records[0]
        assert record["source"] == "opencode"
        assert record["source_raw"] == "opencode-sqlite"
        assert record["total_cost"] == pytest.approx(0.25)
