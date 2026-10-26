"""Agent 原生 Token 用量读取器测试

覆盖：
- base.py 的时间戳解析、cache 拆分、总数兜底、聚合
- Claude 读取器的去重规则（most-complete-wins / sidechain 折叠 / synthetic 丢弃）
- MiniMax Code 读取器的 SQLite 取数与字段映射
- Kimi 读取器的 usage.record 语义（只取 turn 作用域）
"""
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest


# ========== base.py ==========

class TestParseIsoTimestampMs:
    """严格 ISO-8601 时间戳解析（对齐 ccusage parse_ts_timestamp）"""

    def test_accepts_four_supported_shapes(self):
        from app.utils.agent_readers.base import parse_iso_timestamp_ms

        # 2026-01-02T03:04:05Z = 1767323045 秒
        # 长度 20 / 24 / 25 / 29
        assert parse_iso_timestamp_ms("2026-01-02T03:04:05Z") == 1767323045000
        assert parse_iso_timestamp_ms("2026-01-02T03:04:05.123Z") == 1767323045123
        assert parse_iso_timestamp_ms("2026-01-02T03:04:05+00:00") == 1767323045000
        assert (
            parse_iso_timestamp_ms("2026-01-02T03:04:05.123+00:00") == 1767323045123
        )

    @pytest.mark.parametrize(
        "value",
        [
            "2026-01-02T03:04:05",       # 长度 19，缺时区
            "2026-01-02 03:04:05Z",      # 分隔符错误
            "2026-01-02t03:04:05z",      # 小写
            "2026-01-02T03:04:05.1234Z",  # 超过 3 位小数
            "not-a-timestamp",
            "",
            None,
            1767313445000,
        ],
    )
    def test_rejects_invalid_shapes(self, value):
        from app.utils.agent_readers.base import parse_iso_timestamp_ms

        assert parse_iso_timestamp_ms(value) is None


class TestSplitInclusiveInput:
    """含 cache 的 input 拆分（zcode / copilot / grok / gemini 语义）"""

    def test_splits_cache_out_of_input(self):
        from app.utils.agent_readers.base import split_inclusive_input

        assert split_inclusive_input(1000, 800, 0) == (200, 800, 0)
        assert split_inclusive_input(1000, 800, 100) == (100, 800, 100)

    def test_clamps_cache_to_input(self):
        from app.utils.agent_readers.base import split_inclusive_input

        # cache_read 超过 input 时封顶
        assert split_inclusive_input(100, 500, 0) == (0, 100, 0)
        # cache_creation 超过剩余净输入时封顶
        assert split_inclusive_input(100, 50, 500) == (0, 50, 50)


class TestApplyTotalFallback:
    """总数兜底（对齐 ccusage apply_total_token_fallback）"""

    def test_no_missing_keeps_buckets(self):
        from app.utils.agent_readers.base import apply_total_fallback

        assert apply_total_fallback(10, 20, 30, 40, 0, 100) == (10, 20, 30, 40, 0)

    def test_missing_goes_to_output_when_output_is_zero(self):
        from app.utils.agent_readers.base import apply_total_fallback

        assert apply_total_fallback(10, 0, 0, 0, 0, 50) == (10, 40, 0, 0, 0)

    def test_missing_goes_to_extra_when_output_present(self):
        from app.utils.agent_readers.base import apply_total_fallback

        assert apply_total_fallback(10, 5, 0, 0, 0, 50) == (10, 5, 0, 0, 35)


class TestAggregateRecords:
    """按 (日期, 模型) 聚合"""

    def test_merges_same_date_and_model(self):
        from app.utils.agent_readers.base import aggregate_records

        rows = [
            {
                "record_date": "2026-01-02",
                "model": "m1",
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "extra_total_tokens": 0,
                "total_cost": 0.0,
            },
            {
                "record_date": "2026-01-02",
                "model": "m1",
                "input_tokens": 20,
                "output_tokens": 7,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 3,
                "extra_total_tokens": 0,
                "total_cost": 0.0,
            },
        ]
        records = aggregate_records(rows, source="test")
        assert len(records) == 1
        assert records[0]["input_tokens"] == 30
        assert records[0]["output_tokens"] == 12
        assert records[0]["cache_read_tokens"] == 3
        assert records[0]["total_tokens"] == 45
        assert records[0]["record_date"] == date(2026, 1, 2)


# ========== Claude 读取器 ==========

def _write_claude_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _claude_entry(
    timestamp: str = "2026-01-02T03:04:05.000Z",
    message_id: str = "msg_1",
    model: str = "claude-x",
    input_tokens: int = 100,
    output_tokens: int = 10,
    cache_read: int = 0,
    cache_creation: int = 0,
    sidechain: bool = False,
    session_id: str = "s1",
    request_id: str = None,
) -> dict:
    entry = {
        "type": "assistant",
        "timestamp": timestamp,
        "sessionId": session_id,
        "isSidechain": sidechain,
        "message": {
            "id": message_id,
            "role": "assistant",
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_creation,
            },
        },
    }
    if request_id is not None:
        entry["requestId"] = request_id
    return entry


@pytest.fixture
def claude_tree(tmp_path, monkeypatch):
    """构造一个临时的 ~/.claude/projects 目录树"""
    projects = tmp_path / "projects" / "proj"
    projects.mkdir(parents=True)
    monkeypatch.setattr(
        "app.utils.agent_readers.claude_reader._claude_roots",
        lambda: [tmp_path],
    )
    return projects


class TestClaudeReader:
    """Claude Code 读取器"""

    def test_basic_read_and_aggregate(self, claude_tree):
        from app.utils.agent_readers.claude_reader import read_claude_records

        _write_claude_jsonl(
            claude_tree / "a.jsonl",
            [
                _claude_entry(input_tokens=100, output_tokens=10),
                _claude_entry(
                    timestamp="2026-01-03T03:04:05.000Z",
                    message_id="msg_2",
                    input_tokens=200,
                    output_tokens=20,
                ),
            ],
        )
        result = read_claude_records(date(2026, 1, 1), date(2026, 1, 31))
        assert len(result.records) == 2
        by_date = {r["record_date"]: r for r in result.records}
        assert by_date[date(2026, 1, 2)]["input_tokens"] == 100
        assert by_date[date(2026, 1, 3)]["input_tokens"] == 200

    def test_dedupe_keeps_most_complete_entry(self, claude_tree):
        """同一 message id 的多条记录保留 token 总量最大的一条

        Claude Code 会按内容块把一次请求拆成多行，其中首行可能是 0 token 的
        占位行；若保留首行会严重少计。
        """
        from app.utils.agent_readers.claude_reader import read_claude_records

        _write_claude_jsonl(
            claude_tree / "a.jsonl",
            [
                _claude_entry(message_id="msg_x", input_tokens=0, output_tokens=0),
                _claude_entry(
                    message_id="msg_x",
                    timestamp="2026-01-02T03:04:06.000Z",
                    input_tokens=500,
                    output_tokens=50,
                ),
            ],
        )
        result = read_claude_records(date(2026, 1, 1), date(2026, 1, 31))
        assert len(result.records) == 1
        assert result.records[0]["input_tokens"] == 500
        assert result.records[0]["output_tokens"] == 50

    def test_sidechain_records_collapsed_by_message_and_session(self, claude_tree):
        """sidechain 记录按 (message id, session id) 折叠，避免重复统计"""
        from app.utils.agent_readers.claude_reader import read_claude_records

        _write_claude_jsonl(
            claude_tree / "sub" / "a.jsonl",
            [
                _claude_entry(
                    message_id="msg_s", sidechain=True, input_tokens=10, output_tokens=1
                ),
                _claude_entry(
                    message_id="msg_s",
                    timestamp="2026-01-02T03:04:06.000Z",
                    sidechain=True,
                    input_tokens=10,
                    output_tokens=1,
                ),
            ],
        )
        result = read_claude_records(date(2026, 1, 1), date(2026, 1, 31))
        assert len(result.records) == 1
        assert result.records[0]["input_tokens"] == 10

    def test_synthetic_model_is_dropped(self, claude_tree):
        from app.utils.agent_readers.claude_reader import read_claude_records

        _write_claude_jsonl(
            claude_tree / "a.jsonl",
            [_claude_entry(model="<synthetic>", input_tokens=999)],
        )
        result = read_claude_records(date(2026, 1, 1), date(2026, 1, 31))
        assert result.records == []

    def test_null_request_id_rejects_line(self, claude_tree):
        """显式 null 的 requestId 会使整行作废（对齐 ccusage）"""
        from app.utils.agent_readers.claude_reader import read_claude_records

        entry = _claude_entry(input_tokens=777)
        entry["requestId"] = None
        _write_claude_jsonl(claude_tree / "a.jsonl", [entry])
        result = read_claude_records(date(2026, 1, 1), date(2026, 1, 31))
        assert result.records == []

    def test_cache_creation_breakdown_overrides_flat_field(self, claude_tree):
        """cache_creation 结构化对象优先于扁平字段"""
        from app.utils.agent_readers.claude_reader import read_claude_records

        entry = _claude_entry(input_tokens=100, output_tokens=10, cache_creation=5)
        entry["message"]["usage"]["cache_creation"] = {
            "ephemeral_5m_input_tokens": 7,
            "ephemeral_1h_input_tokens": 3,
        }
        _write_claude_jsonl(claude_tree / "a.jsonl", [entry])
        result = read_claude_records(date(2026, 1, 1), date(2026, 1, 31))
        assert result.records[0]["cache_creation_tokens"] == 10


# ========== MiniMax Code 读取器 ==========

def _create_minimax_db(db_path: Path, rows: list[tuple]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE local_runtime_token_usage (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                agent_name TEXT,
                framework_type TEXT,
                turn_id TEXT,
                model TEXT,
                ts INTEGER,
                input_tokens INTEGER,
                output_tokens INTEGER,
                reasoning_tokens INTEGER,
                cache_read_tokens INTEGER,
                cache_write_tokens INTEGER,
                cost_usd REAL,
                raw TEXT
            );
        """)
        for row in rows:
            conn.execute(
                "INSERT INTO local_runtime_token_usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                row,
            )
        conn.commit()
    finally:
        conn.close()


class TestMinimaxReader:
    """MiniMax Code 读取器"""

    def test_reads_and_aggregates(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.minimax_reader import read_minimax_records

        db_file = tmp_path / "runtime-state.sqlite"
        ts = 1767313445000  # 2026-01-02T03:04:05Z
        _create_minimax_db(
            db_file,
            [
                ("1", "s1", "mavis", "pi-agent", "t1", "minimax/M3", ts,
                 100, 10, 2, 300, 0, 0.0, "{}"),
                ("2", "s1", "mavis", "pi-agent", "t2", "minimax/M3", ts + 1000,
                 200, 20, 0, 400, 5, 0.0, "{}"),
            ],
        )
        monkeypatch.setattr(
            "app.utils.agent_readers.minimax_reader._db_candidates",
            lambda: [db_file],
        )
        result = read_minimax_records(date(2026, 1, 2), date(2026, 1, 2))
        assert len(result.records) == 1
        record = result.records[0]
        assert record["model"] == "minimax/M3"
        assert record["input_tokens"] == 300
        # reasoning 并入 output
        assert record["output_tokens"] == 32
        assert record["cache_read_tokens"] == 700
        assert record["cache_creation_tokens"] == 5
        assert record["total_tokens"] == 300 + 32 + 5 + 700

    def test_missing_db_is_skipped_silently(self, tmp_path, monkeypatch):
        """未安装 MiniMax Code 不是异常：静默跳过，不产生同步告警"""
        from app.utils.agent_readers.minimax_reader import read_minimax_records

        monkeypatch.setattr(
            "app.utils.agent_readers.minimax_reader._db_candidates",
            lambda: [tmp_path / "missing.sqlite"],
        )
        result = read_minimax_records(date(2026, 1, 1), date(2026, 1, 31))
        assert result.records == []
        assert result.errors == []

    def test_missing_table_reports_error(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.minimax_reader import read_minimax_records

        db_file = tmp_path / "runtime-state.sqlite"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE other (x INTEGER)")
        conn.commit()
        conn.close()
        monkeypatch.setattr(
            "app.utils.agent_readers.minimax_reader._db_candidates",
            lambda: [db_file],
        )
        result = read_minimax_records(date(2026, 1, 1), date(2026, 1, 31))
        assert result.records == []
        assert result.errors[0]["error_code"] == "TABLE_MISSING"


# ========== Kimi 读取器 ==========

class TestKimiReader:
    """Kimi / Kimi Code 读取器"""

    def _wire(self, tmp_path, monkeypatch, lines: list[dict]):
        sessions = tmp_path / "sessions" / "ws" / "sess" / "agents" / "main"
        sessions.mkdir(parents=True)
        wire = sessions / "wire.jsonl"
        with wire.open("w", encoding="utf-8") as handle:
            for line in lines:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        monkeypatch.setattr(
            "app.utils.agent_readers.kimi_reader._kimi_roots",
            lambda: [tmp_path],
        )
        return wire

    def test_reads_turn_scope_records(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.kimi_reader import read_kimi_records

        self._wire(
            tmp_path,
            monkeypatch,
            [
                {
                    "type": "usage.record",
                    "model": "kimi-code/kimi-for-coding",
                    "usageScope": "turn",
                    "usage": {
                        "inputOther": 100,
                        "output": 20,
                        "inputCacheRead": 300,
                        "inputCacheCreation": 5,
                    },
                    "time": 1767313445000,
                }
            ],
        )
        result = read_kimi_records(date(2026, 1, 2), date(2026, 1, 31))
        assert len(result.records) == 1
        record = result.records[0]
        assert record["model"] == "kimi-for-coding"
        assert record["input_tokens"] == 100
        assert record["output_tokens"] == 20
        assert record["cache_read_tokens"] == 300
        assert record["cache_creation_tokens"] == 5

    def test_session_scope_records_are_excluded(self, tmp_path, monkeypatch):
        """usageScope=session 是累计值，必须排除否则重复统计"""
        from app.utils.agent_readers.kimi_reader import read_kimi_records

        self._wire(
            tmp_path,
            monkeypatch,
            [
                {
                    "type": "usage.record",
                    "model": "kimi-code/kimi-for-coding",
                    "usageScope": "session",
                    "usage": {
                        "inputOther": 9999,
                        "output": 9999,
                        "inputCacheRead": 9999,
                        "inputCacheCreation": 0,
                    },
                    "time": 1767313445000,
                }
            ],
        )
        result = read_kimi_records(date(2026, 1, 2), date(2026, 1, 31))
        assert result.records == []


# ========== 注册表 ==========

class TestRegistry:
    """读取器注册表"""

    def test_source_ids_match_ccusage_agent_ids(self):
        """source id 必须与 ccusage agent id 一致，否则会与历史数据产生重复行"""
        from app.services.token_usage_sync_service import (
            NATIVE_READER_SOURCES,
            SOURCE_TOOL_MAPPING,
        )
        from app.utils.agent_readers import READERS

        for source in NATIVE_READER_SOURCES:
            assert source in READERS
            assert source in SOURCE_TOOL_MAPPING

    def test_minimax_has_no_ccusage_counterpart(self):
        from app.services.token_usage_sync_service import NATIVE_ONLY_SOURCES

        assert "minimax" in NATIVE_ONLY_SOURCES


# ========== 压缩文件与家目录展开 ==========

class TestCollectFiles:
    """文件收集：支持复合后缀（.jsonl.zst），大小写不敏感"""

    def test_collects_plain_jsonl(self, tmp_path):
        from app.utils.agent_readers.base import collect_files

        (tmp_path / "a.jsonl").write_text("{}\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("x", encoding="utf-8")
        found = collect_files(tmp_path, (".jsonl",))
        assert [p.name for p in found] == ["a.jsonl"]

    def test_collects_composite_suffix_jsonl_zst(self, tmp_path):
        """.jsonl.zst 必须能被收集到（Codex 新版本默认写压缩会话）"""
        from app.utils.agent_readers.base import collect_files

        (tmp_path / "rollout-1.jsonl.zst").write_bytes(b"\x28\xb5\x2f\xfd")
        found = collect_files(tmp_path, (".jsonl", ".jsonl.zst"))
        assert [p.name for p in found] == ["rollout-1.jsonl.zst"]

    def test_plain_suffix_does_not_match_composite_file(self, tmp_path):
        """只请求 .jsonl 时不能误收 .jsonl.zst"""
        from app.utils.agent_readers.base import collect_files

        (tmp_path / "rollout-1.jsonl.zst").write_bytes(b"\x28\xb5\x2f\xfd")
        assert collect_files(tmp_path, (".jsonl",)) == []

    def test_extension_match_is_case_insensitive(self, tmp_path):
        from app.utils.agent_readers.base import collect_files

        (tmp_path / "A.JSONL").write_text("{}\n", encoding="utf-8")
        assert len(collect_files(tmp_path, (".jsonl",))) == 1

    def test_missing_root_returns_empty(self, tmp_path):
        from app.utils.agent_readers.base import collect_files

        assert collect_files(tmp_path / "nope", (".jsonl",)) == []


class TestIterJsonl:
    """JSONL 逐行解析 + zstd 压缩流支持"""

    def test_plain_jsonl(self, tmp_path):
        from app.utils.agent_readers.base import iter_jsonl

        path = tmp_path / "a.jsonl"
        path.write_text('{"a":1}\n\nnot-json\n{"b":2}\n', encoding="utf-8")
        assert list(iter_jsonl(path)) == [{"a": 1}, {"b": 2}]

    def test_reads_zstd_compressed_jsonl(self, tmp_path):
        """zstd 压缩的 JSONL 必须能解出记录"""
        zstandard = pytest.importorskip("zstandard")
        from app.utils.agent_readers.base import iter_jsonl

        path = tmp_path / "rollout.jsonl.zst"
        payload = b'{"type":"event_msg"}\n{"type":"turn_context"}\n'
        path.write_bytes(zstandard.ZstdCompressor().compress(payload))
        assert [r["type"] for r in iter_jsonl(path)] == ["event_msg", "turn_context"]

    def test_corrupt_zstd_file_is_skipped(self, tmp_path):
        """压缩流损坏时只丢该文件，不抛异常中断整体"""
        pytest.importorskip("zstandard")
        from app.utils.agent_readers.base import iter_jsonl

        path = tmp_path / "broken.jsonl.zst"
        path.write_bytes(b"this is not a zstd frame")
        assert list(iter_jsonl(path)) == []


class TestExpandUserPath:
    """环境变量路径展开必须基于真实家目录（不受 HOME 覆盖影响）"""

    def test_expands_tilde_to_real_home(self, monkeypatch):
        from app.utils.agent_readers.base import expand_user_path, real_home

        expected = str(real_home())
        assert str(expand_user_path("~")) == expected
        assert str(expand_user_path("~/x")) == f"{expected}/x"

    def test_leaves_absolute_and_other_paths_untouched(self):
        from app.utils.agent_readers.base import expand_user_path

        assert str(expand_user_path("/tmp/x")) == "/tmp/x"
        assert str(expand_user_path("relative/x")) == "relative/x"


class TestCcusageHomeResolution:
    """ccusage 二进制发现必须绕过 config.py 对 HOME 的覆盖"""

    def test_expand_user_uses_real_home(self, monkeypatch):
        from app.utils import ccusage_invoker
        from app.utils.agent_readers.base import real_home

        monkeypatch.setenv("HOME", "/tmp/fake-home")
        expanded = ccusage_invoker._expand_user("~")
        assert expanded != "/tmp/fake-home"
        assert expanded == str(real_home())

    def test_nvm_fallback_path_uses_real_home(self, monkeypatch):
        """nvm 兜底路径必须落在真实家目录下，而不是缓存目录"""
        from app.utils import ccusage_invoker
        from app.utils.agent_readers.base import real_home

        monkeypatch.setenv("HOME", "/tmp/fake-home")
        paths = ccusage_invoker._ccusage_search_paths()
        expected = str(real_home())
        assert any(p.startswith(expected) for p in paths), paths
        assert not any("/tmp/fake-home" in p for p in paths), paths
