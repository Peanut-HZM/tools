"""GitHub Copilot CLI 原生 Token 用量读取器测试

覆盖：

- **input 扣减**：Copilot 的 ``inputTokens`` 含 cache，必须扣掉
  ``cacheReadTokens + cacheWriteTokens``
- **差值基线**：同一 ``(session, model)`` 的多条 shutdown 是累计快照，
  逐条减去前一条（饱和减法）
- **去重**：同 ``dedup_key`` 只保留最后一条
- **模型名归一**：``-1m-internal`` / ``-1m`` 后缀剥离
- **时区归桶**：按本机时区自然日归桶
- **路径发现**：``COPILOT_HOME``、session-state 直接子目录、OTEL 递归、
  ``COPILOT_OTEL_FILE_EXPORTER_PATH``
- **容错**：单行解析失败只丢该行，非 shutdown 事件被忽略
- **reasoning token 不计入 total**（对齐 ccusage 口径）
"""

import json
import os
import time
from datetime import date
from pathlib import Path

import pytest

from app.utils.agent_readers import copilot_reader
from app.utils.agent_readers.copilot_reader import (
    _discover_sources,
    _normalize_model,
    _uncached_input_tokens,
    read_copilot_records,
)


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------


def _write_events(path: Path, events: list) -> None:
    """把事件列表写成 JSONL 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def _write_lines(path: Path, lines: list[str]) -> None:
    """把原始行写入 JSONL 文件（用于构造坏行）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _shutdown(event_id, timestamp, metrics, shutdown_type="session.shutdown"):
    """构造一个 shutdown / checkpoint 事件。"""
    return {
        "type": shutdown_type,
        "id": event_id,
        "timestamp": timestamp,
        "data": {"modelMetrics": metrics},
    }


def _usage(inp=0, out=0, cache_read=0, cache_write=0, reasoning=0):
    """构造 ``modelMetrics[*].usage``。"""
    return {
        "inputTokens": inp,
        "outputTokens": out,
        "cacheReadTokens": cache_read,
        "cacheWriteTokens": cache_write,
        "reasoningTokens": reasoning,
    }


def _records_by_key(result):
    """把聚合结果转成 ``{(date, model): record}``。"""
    out = {}
    for rec in result.records:
        rd = rec["record_date"]
        rd = rd.isoformat() if hasattr(rd, "isoformat") else rd
        out[(rd, rec["model"])] = rec
    return out


@pytest.fixture
def copilot_home(tmp_path, monkeypatch):
    """把 Copilot 根目录指向临时目录，并清掉相关环境变量。"""
    # 默认根目录是 <real_home>/.copilot
    root = tmp_path / ".copilot"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv(copilot_reader.COPILOT_HOME_ENV, raising=False)
    monkeypatch.delenv(
        copilot_reader.COPILOT_OTEL_FILE_EXPORTER_PATH_ENV, raising=False
    )
    monkeypatch.setattr(copilot_reader, "real_home", lambda: tmp_path)
    return root


@pytest.fixture(autouse=True)
def fixed_tz():
    """把进程时区固定为 UTC+8（POSIX ``TZ=UTC-8``），结束后恢复。

    日期断言依赖"本机时区归桶"，固定时区后结果确定，不受跑测试的机器
    时区设置影响。
    """
    original = os.environ.get("TZ")
    os.environ["TZ"] = "UTC-8"
    time.tzset()
    yield
    if original is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = original
    time.tzset()


# ---------------------------------------------------------------------------
# 模型名归一
# ---------------------------------------------------------------------------


class TestNormalizeModel:
    """``normalize_copilot_model``：先 trim，再剥离 -1m 后缀。"""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (" claude-opus-4.7-1m-internal ", "claude-opus-4.7"),
            ("claude-opus-4.6-1m", "claude-opus-4.6"),
            ("gpt-5.4", "gpt-5.4"),
            ("claude-haiku-4.5", "claude-haiku-4.5"),
            ("  gpt-5-mini  ", "gpt-5-mini"),
            ("-1m", ""),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert _normalize_model(raw) == expected


class TestUncachedInputTokens:
    """input 含 cache，必须扣减后才是净 input。"""

    def test_subtracts_cache_from_input(self):
        assert _uncached_input_tokens(100, 10, 20) == 70

    def test_saturates_at_zero(self):
        assert _uncached_input_tokens(10, 20, 20) == 0
        assert _uncached_input_tokens(0, 0, 0) == 0


# ---------------------------------------------------------------------------
# session-state 解析
# ---------------------------------------------------------------------------


class TestSessionStateParsing:
    """逐 model 产出一条 entry，input 扣减后入账。"""

    def test_input_tokens_subtracts_cache(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "shutdown-1",
                    "2026-04-15T09:52:27.352Z",
                    {
                        "test-model": {
                            "usage": _usage(inp=100, out=50, cache_read=10, cache_write=20),
                            "requests": {"count": 1},
                        }
                    },
                )
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert ("2026-04-15", "test-model") in records
        rec = records[("2026-04-15", "test-model")]
        assert rec["input_tokens"] == 70
        assert rec["output_tokens"] == 50
        assert rec["cache_creation_tokens"] == 20
        assert rec["cache_read_tokens"] == 10
        assert rec["total_tokens"] == 150

    def test_skips_model_with_all_zero_usage_and_zero_requests(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "shutdown-1",
                    "2026-04-15T09:52:27.352Z",
                    {
                        "empty-model": {"usage": _usage()},
                        "real-model": {"usage": _usage(inp=5, out=6)},
                    },
                )
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert ("2026-04-15", "empty-model") not in records
        assert ("2026-04-15", "real-model") in records

    def test_normalizes_model_name_in_output(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "shutdown-1",
                    "2026-04-15T09:52:27.352Z",
                    {"claude-opus-4.7-1m-internal": {"usage": _usage(inp=5, out=6)}},
                )
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert ("2026-04-15", "claude-opus-4.7") in records
        assert ("2026-04-15", "claude-opus-4.7-1m-internal") not in records

    def test_ignores_non_shutdown_events(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                {
                    "type": "tool",
                    "id": "tool-1",
                    "timestamp": "2026-04-15T09:52:27.352Z",
                    "data": {"message": "session.shutdown"},
                },
                _shutdown(
                    "checkpoint-1",
                    "2026-04-15T09:53:00.000Z",
                    {"test-model": {"usage": _usage(inp=999, out=999)}},
                    shutdown_type="session.usage_checkpoint",
                ),
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records == []

    def test_drops_only_broken_line(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_lines(
            session_dir / "events.jsonl",
            [
                "not json at all",
                json.dumps(
                    _shutdown(
                        "shutdown-1",
                        "2026-04-15T09:52:27.352Z",
                        {"test-model": {"usage": _usage(inp=3, out=4)}},
                    )
                ),
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert records[("2026-04-15", "test-model")]["input_tokens"] == 3

    def test_reasoning_tokens_not_counted_in_total(self, copilot_home):
        """reasoningTokens 单独记录，不进 output 也不进 extra。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "shutdown-1",
                    "2026-05-04T02:45:11.821Z",
                    {
                        "gpt-5-mini": {
                            "usage": _usage(inp=31982, out=505, reasoning=448),
                            "requests": {"count": 1},
                        }
                    },
                )
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-05-04", "gpt-5-mini")]

        assert rec["input_tokens"] == 31982
        assert rec["output_tokens"] == 505
        assert rec["total_tokens"] == 32487


# ---------------------------------------------------------------------------
# 差值基线
# ---------------------------------------------------------------------------


class TestDeltaBaseline:
    """同一 (session, model) 的多条 shutdown 是累计快照，必须逐条做差。"""

    def test_subtracts_previous_snapshot(self, copilot_home):
        """复刻本机 2026-04-13 的三条 shutdown，合计必须等于 ccusage 的 208179。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "e359d904",
                    "2026-04-13T02:14:26.804Z",
                    {
                        "claude-haiku-4.5": {
                            "usage": _usage(inp=80465, out=511),
                            "requests": {"count": 1},
                        }
                    },
                ),
                _shutdown(
                    "2d4d5a80",
                    "2026-04-13T02:24:10.303Z",
                    {
                        "claude-haiku-4.5": {
                            "usage": _usage(inp=81963, out=201),
                            "requests": {"count": 1},
                        }
                    },
                ),
                _shutdown(
                    "eb28500c",
                    "2026-04-13T02:25:48.495Z",
                    {
                        "claude-haiku-4.5": {
                            "usage": _usage(inp=128278, out=763, cache_read=125143),
                            "requests": {"count": 3},
                        }
                    },
                ),
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-13", "claude-haiku-4.5")]

        assert rec["input_tokens"] == 81963
        assert rec["output_tokens"] == 1073
        assert rec["cache_read_tokens"] == 125143
        assert rec["cache_creation_tokens"] == 0
        assert rec["total_tokens"] == 208179

    def test_delta_saturates_at_zero(self, copilot_home):
        """累计值回退（重启导致）时饱和减到 0，不会产生负数。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "a",
                    "2026-04-13T02:14:26.804Z",
                    {"m": {"usage": _usage(inp=100, out=50)}},
                ),
                _shutdown(
                    "b",
                    "2026-04-13T02:20:00.000Z",
                    {"m": {"usage": _usage(inp=10, out=5)}},
                ),
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-13", "m")]

        assert rec["input_tokens"] == 100
        assert rec["output_tokens"] == 50

    def test_delta_chain_spans_out_of_range_entries(self, copilot_home):
        """差值基线覆盖区间外的 shutdown：先做完整差值链，再按日期裁剪。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "a",
                    "2026-04-13T02:14:26.804Z",
                    {"m": {"usage": _usage(inp=100, out=50)}},
                ),
                _shutdown(
                    "b",
                    "2026-04-14T02:14:26.804Z",
                    {"m": {"usage": _usage(inp=300, out=150)}},
                ),
            ],
        )

        result = read_copilot_records(date(2026, 4, 14), date(2026, 4, 14))
        rec = _records_by_key(result)[("2026-04-14", "m")]

        # 第二条减去第一条：300-100 / 150-50
        assert rec["input_tokens"] == 200
        assert rec["output_tokens"] == 100


# ---------------------------------------------------------------------------
# 去重
# ---------------------------------------------------------------------------


class TestDeduplication:
    """同 dedup_key 只保留最后一条。"""

    def test_keeps_last_entry_for_same_event_id(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "same-id",
                    "2026-04-15T09:00:00.000Z",
                    {"m": {"usage": _usage(inp=100, out=10)}},
                ),
                _shutdown(
                    "same-id",
                    "2026-04-15T09:30:00.000Z",
                    {"m": {"usage": _usage(inp=200, out=20)}},
                ),
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-15", "m")]

        # 重复事件被去掉，只剩后一条（且它是链条第一条，无基线）
        assert rec["input_tokens"] == 200
        assert rec["output_tokens"] == 20

    def test_keeps_earlier_entry_when_duplicate_is_older(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "same-id",
                    "2026-04-15T09:30:00.000Z",
                    {"m": {"usage": _usage(inp=200, out=20)}},
                ),
                _shutdown(
                    "same-id",
                    "2026-04-15T09:00:00.000Z",
                    {"m": {"usage": _usage(inp=100, out=10)}},
                ),
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-15", "m")]

        assert rec["input_tokens"] == 200
        assert rec["output_tokens"] == 20

    def test_without_event_id_dedup_key_uses_usage_fields(self, copilot_home):
        """无 id 时去重键包含时间戳与全部 usage 值，不同用量不互相去重。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                {
                    "type": "session.shutdown",
                    "timestamp": "2026-04-15T09:00:00.000Z",
                    "data": {"modelMetrics": {"m": {"usage": _usage(inp=100, out=10)}}},
                },
                {
                    "type": "session.shutdown",
                    "timestamp": "2026-04-15T09:30:00.000Z",
                    "data": {"modelMetrics": {"m": {"usage": _usage(inp=300, out=30)}}},
                },
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-15", "m")]

        # 两条都保留，第二条做差：300-100 / 30-10
        assert rec["input_tokens"] == 300
        assert rec["output_tokens"] == 30

    def test_identical_entries_without_event_id_are_deduplicated(self, copilot_home):
        session_dir = copilot_home / "session-state" / "session-1"
        event = {
            "type": "session.shutdown",
            "timestamp": "2026-04-15T09:00:00.000Z",
            "data": {"modelMetrics": {"m": {"usage": _usage(inp=100, out=10)}}},
        }
        _write_events(session_dir / "events.jsonl", [event, event])

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-15", "m")]

        assert rec["input_tokens"] == 100
        assert rec["output_tokens"] == 10


# ---------------------------------------------------------------------------
# 时区归桶
# ---------------------------------------------------------------------------


class TestLocalDateBucketing:
    """按本机时区自然日归桶（ccusage format_date_tz 默认系统时区）。"""

    def test_buckets_by_local_date(self, copilot_home, fixed_tz):
        """UTC 2026-04-13T20:00Z 在 UTC+8 下是本地 2026-04-14 04:00。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "a",
                    "2026-04-13T20:00:00.000Z",
                    {"m": {"usage": _usage(inp=10, out=1)}},
                )
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert ("2026-04-14", "m") in records
        assert ("2026-04-13", "m") not in records

    def test_early_utc_stays_same_local_date(self, copilot_home, fixed_tz):
        """UTC 2026-04-13T02:14Z 在 UTC+8 下仍是本地 2026-04-13。"""
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "a",
                    "2026-04-13T02:14:26.804Z",
                    {"m": {"usage": _usage(inp=10, out=1)}},
                )
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert ("2026-04-13", "m") in records

    def test_filters_by_requested_date_range(self, copilot_home, fixed_tz):
        session_dir = copilot_home / "session-state" / "session-1"
        _write_events(
            session_dir / "events.jsonl",
            [
                _shutdown(
                    "a",
                    "2026-04-13T02:14:26.804Z",
                    {"m": {"usage": _usage(inp=10, out=1)}},
                ),
                _shutdown(
                    "b",
                    "2026-05-04T02:45:11.821Z",
                    {"m": {"usage": _usage(inp=20, out=2)}},
                ),
            ],
        )

        result = read_copilot_records(date(2026, 5, 1), date(2026, 5, 31))
        records = _records_by_key(result)

        assert set(records) == {("2026-05-04", "m")}


# ---------------------------------------------------------------------------
# 路径发现
# ---------------------------------------------------------------------------


class TestPathDiscovery:
    """COPILOT_HOME / session-state 直接子目录 / OTEL 递归 / 显式 OTEL 文件。"""

    def test_discovers_session_state_and_otel(self, copilot_home):
        _write_events(
            copilot_home / "otel" / "trace.jsonl", [{"attributes": {}}]
        )
        _write_events(
            copilot_home / "otel" / "nested" / "deep.jsonl", [{"attributes": {}}]
        )
        _write_events(
            copilot_home / "session-state" / "session-a" / "events.jsonl", []
        )
        _write_events(
            copilot_home / "session-state" / "session-b" / "events.jsonl", []
        )
        # 更深层的 session-state 目录不纳入（Rust 只遍历一层）
        _write_events(
            copilot_home / "session-state" / "nested" / "session-c" / "events.jsonl",
            [],
        )

        sources = _discover_sources()
        paths = {str(path) for _, path in sources}

        assert str(copilot_home / "otel" / "trace.jsonl") in paths
        assert str(copilot_home / "otel" / "nested" / "deep.jsonl") in paths
        assert str(copilot_home / "session-state" / "session-a" / "events.jsonl") in paths
        assert str(copilot_home / "session-state" / "session-b" / "events.jsonl") in paths
        assert (
            str(copilot_home / "session-state" / "nested" / "session-c" / "events.jsonl")
            not in paths
        )

    def test_session_state_kind_is_marked(self, copilot_home):
        _write_events(
            copilot_home / "session-state" / "session-a" / "events.jsonl", []
        )
        _write_events(copilot_home / "otel" / "trace.jsonl", [{"attributes": {}}])

        kinds = {
            str(path): kind for kind, path in _discover_sources()
        }

        assert kinds[str(copilot_home / "session-state" / "session-a" / "events.jsonl")] == (
            "session-state"
        )
        assert kinds[str(copilot_home / "otel" / "trace.jsonl")] == "otel"

    def test_copilot_home_env_overrides_default(self, tmp_path, monkeypatch):
        relocated = tmp_path / "relocated"
        _write_events(relocated / "session-state" / "session-1" / "events.jsonl", [])
        _write_events(relocated / "otel" / "trace.jsonl", [{"attributes": {}}])

        monkeypatch.setenv(copilot_reader.COPILOT_HOME_ENV, str(relocated))
        monkeypatch.setattr(copilot_reader, "real_home", lambda: tmp_path / "home")

        paths = {str(path) for _, path in _discover_sources()}

        assert str(relocated / "session-state" / "session-1" / "events.jsonl") in paths
        assert str(relocated / "otel" / "trace.jsonl") in paths
        assert not any("home/.copilot" in p for p in paths)

    def test_blank_copilot_home_env_falls_back_to_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv(copilot_reader.COPILOT_HOME_ENV, "   ")
        monkeypatch.setattr(copilot_reader, "real_home", lambda: tmp_path)

        root = copilot_reader._copilot_root()

        assert root == tmp_path / ".copilot"

    def test_explicit_otel_exporter_path_is_included(self, tmp_path, monkeypatch):
        explicit = tmp_path / "explicit.jsonl"
        _write_events(explicit, [{"attributes": {}}])

        monkeypatch.setattr(copilot_reader, "real_home", lambda: tmp_path)
        monkeypatch.setenv(
            copilot_reader.COPILOT_OTEL_FILE_EXPORTER_PATH_ENV, str(explicit)
        )

        paths = {str(path) for _, path in _discover_sources()}

        assert str(explicit) in paths

    def test_missing_paths_are_silent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(copilot_reader, "real_home", lambda: tmp_path)
        monkeypatch.delenv(copilot_reader.COPILOT_HOME_ENV, raising=False)
        monkeypatch.delenv(
            copilot_reader.COPILOT_OTEL_FILE_EXPORTER_PATH_ENV, raising=False
        )

        assert _discover_sources() == []

    def test_duplicate_paths_are_deduplicated(self, copilot_home):
        _write_events(copilot_home / "otel" / "trace.jsonl", [{"attributes": {}}])

        paths = [str(path) for _, path in _discover_sources()]

        assert len(paths) == len(set(paths))


# ---------------------------------------------------------------------------
# OTEL 解析
# ---------------------------------------------------------------------------


class TestOtelParsing:
    """OTEL 分支（Rust ``parse_otel_file`` 移植）。

    注意：本机没有 OTEL 数据，该分支**未与 ccusage 做过数值对账**，
    这里只验证移植后的行为与 Rust 代码一致。
    """

    def _write_otel(self, copilot_home, records):
        path = copilot_home / "otel" / "trace.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return path

    def test_input_tokens_subtracts_cache(self, copilot_home):
        self._write_otel(
            copilot_home,
            [
                {
                    "type": "span",
                    "name": "chat gpt-5-mini",
                    "spanId": "s1",
                    "traceId": "t1",
                    "endTime": [1776000001, 0],
                    "attributes": {
                        "gen_ai.operation.name": "chat",
                        "gen_ai.response.model": "gpt-5-mini",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.usage.input_tokens": 1000,
                        "gen_ai.usage.output_tokens": 100,
                        "gen_ai.usage.cache_read.input_tokens": 200,
                        "gen_ai.usage.cache_write.input_tokens": 50,
                    },
                }
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)
        rec = records[("2026-04-12", "gpt-5-mini")]

        assert rec["input_tokens"] == 750
        assert rec["output_tokens"] == 100
        assert rec["cache_creation_tokens"] == 50
        assert rec["cache_read_tokens"] == 200
        assert rec["total_tokens"] == 1100

    def test_inference_log_is_suppressed_by_chat_span(self, copilot_home):
        """同 trace / 同 response id 的 inference log 被 chat span 抑制。"""
        self._write_otel(
            copilot_home,
            [
                {
                    "type": "span",
                    "name": "chat gpt-5-mini",
                    "spanId": "s1",
                    "traceId": "t1",
                    "endTime": [1776000001, 0],
                    "attributes": {
                        "gen_ai.operation.name": "chat",
                        "gen_ai.response.model": "gpt-5-mini",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.response.id": "resp-1",
                        "gen_ai.usage.input_tokens": 1000,
                        "gen_ai.usage.output_tokens": 100,
                    },
                },
                {
                    "event.name": "gen_ai.client.inference.operation.details",
                    "body": "GenAI inference: gpt-5-mini",
                    "spanId": "s2",
                    "traceId": "t1",
                    "timeUnixNano": "1776000002000000000",
                    "attributes": {
                        "gen_ai.response.model": "gpt-5-mini",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.response.id": "resp-1",
                        "gen_ai.usage.input_tokens": 1000,
                        "gen_ai.usage.output_tokens": 100,
                    },
                },
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-12", "gpt-5-mini")]

        # 只剩 chat span 的一次调用
        assert rec["input_tokens"] == 1000
        assert rec["output_tokens"] == 100
        assert rec["total_tokens"] == 1100

    def test_total_fallback_goes_to_extra_when_output_present(self, copilot_home):
        """来源自报 total 缺口在 output 非 0 时计入 extra（不计入 output）。"""
        self._write_otel(
            copilot_home,
            [
                {
                    "type": "span",
                    "name": "chat gpt-5-mini",
                    "spanId": "s1",
                    "traceId": "t1",
                    "endTime": [1776000001, 0],
                    "attributes": {
                        "gen_ai.operation.name": "chat",
                        "gen_ai.response.model": "gpt-5-mini",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.usage.input_tokens": 10,
                        "gen_ai.usage.output_tokens": 5,
                        "gen_ai.usage.total_tokens": 30,
                    },
                }
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-12", "gpt-5-mini")]

        assert rec["input_tokens"] == 10
        assert rec["output_tokens"] == 5
        assert rec["total_tokens"] == 30

    def test_total_fallback_goes_to_output_when_output_is_zero(self, copilot_home):
        self._write_otel(
            copilot_home,
            [
                {
                    "type": "span",
                    "name": "chat gpt-5-mini",
                    "spanId": "s1",
                    "traceId": "t1",
                    "endTime": [1776000001, 0],
                    "attributes": {
                        "gen_ai.operation.name": "chat",
                        "gen_ai.response.model": "gpt-5-mini",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.usage.input_tokens": 10,
                        "gen_ai.usage.output_tokens": 0,
                        "gen_ai.usage.total_tokens": 30,
                    },
                }
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-12", "gpt-5-mini")]

        assert rec["input_tokens"] == 10
        assert rec["output_tokens"] == 20
        assert rec["total_tokens"] == 30

    def test_records_without_attributes_are_skipped(self, copilot_home):
        self._write_otel(
            copilot_home,
            [
                {"type": "span", "name": "chat x", "spanId": "s4"},
                {
                    "type": "span",
                    "name": "chat gpt-5-mini",
                    "spanId": "s5",
                    "traceId": "t5",
                    "endTime": [1776000001, 0],
                    "attributes": {
                        "gen_ai.operation.name": "chat",
                        "gen_ai.response.model": "gpt-5-mini",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.usage.input_tokens": 7,
                        "gen_ai.usage.output_tokens": 3,
                    },
                },
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        rec = _records_by_key(result)[("2026-04-12", "gpt-5-mini")]

        assert rec["input_tokens"] == 7
        assert rec["output_tokens"] == 3

    def test_model_name_is_normalized(self, copilot_home):
        self._write_otel(
            copilot_home,
            [
                {
                    "type": "span",
                    "name": "chat m",
                    "spanId": "s1",
                    "traceId": "t1",
                    "endTime": [1776000001, 0],
                    "attributes": {
                        "gen_ai.operation.name": "chat",
                        "gen_ai.request.model": "claude-opus-4.7-1m-internal",
                        "gen_ai.conversation.id": "sess-1",
                        "gen_ai.usage.input_tokens": 7,
                        "gen_ai.usage.output_tokens": 3,
                    },
                }
            ],
        )

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert ("2026-04-12", "claude-opus-4.7") in records


# ---------------------------------------------------------------------------
# 容错
# ---------------------------------------------------------------------------


class TestFailureIsolation:
    """单个文件失败只丢该文件。"""

    def test_broken_file_does_not_break_others(self, copilot_home):
        _write_events(
            copilot_home / "session-state" / "session-ok" / "events.jsonl",
            [_shutdown("a", "2026-04-15T09:00:00.000Z", {"m": {"usage": _usage(inp=7, out=3)}})],
        )
        broken = copilot_home / "session-state" / "session-bad" / "events.jsonl"
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b"\x00\x01\x02not-json\xff")

        result = read_copilot_records(date(2026, 1, 1), date(2026, 12, 31))
        records = _records_by_key(result)

        assert records[("2026-04-15", "m")]["input_tokens"] == 7
