"""OpenClaw 原生 Token 用量读取器测试

覆盖：

- token 口径（input 不含 cache、不做 cache 扣减）
- 总数兜底（apply_total_token_fallback 语义）
- 状态化模型追踪（model_change / model-snapshot）
- 模型名 ``[openclaw] `` 前缀与优先级
- 时区归桶（epoch 毫秒 / ISO 字符串）
- 文件命名规则（``.jsonl`` / ``.jsonl.deleted.*`` / ``.jsonl.reset.*``）
- 符号链接跳过
- 去重与单行容错
"""

import json
import os
from datetime import date

import pytest


@pytest.fixture
def openclaw_dir(tmp_path, monkeypatch):
    """构造一个独立的 OpenClaw 数据根，并通过 OPENCLAW_DIR 注入。"""
    root = tmp_path / "openclaw-root"
    (root / "agents" / "main" / "sessions").mkdir(parents=True)
    monkeypatch.setenv("OPENCLAW_DIR", str(root))
    return root


def _write_session(root, name, lines):
    """写入一个会话文件（自动补齐目录）。"""
    path = root / "agents" / "main" / "sessions" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n")
    return path


def _assistant(ts, usage, model="kimi-k2.5", provider="moonshot", extra=None):
    """构造一条 assistant message 记录。"""
    message = {
        "role": "assistant",
        "provider": provider,
        "model": model,
        "usage": usage,
        "timestamp": ts,
    }
    if extra:
        message.update(extra)
    return {"type": "message", "id": "evt-1", "timestamp": ts, "message": message}


# ========== token 口径 ==========


class TestTokenBuckets:
    """四桶映射与 input 不含 cache 的语义"""

    def test_maps_usage_fields_to_buckets(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                _assistant(
                    1769753935279,
                    {
                        "input": 6800,
                        "output": 250,
                        "cacheRead": 5376,
                        "cacheWrite": 0,
                        "totalTokens": 12426,
                    },
                )
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert len(result.records) == 1
        record = result.records[0]
        assert record["input_tokens"] == 6800
        assert record["output_tokens"] == 250
        assert record["cache_read_tokens"] == 5376
        assert record["cache_creation_tokens"] == 0
        # total_tokens = 四桶之和 + extra（base.aggregate_records 的统一口径）
        assert record["total_tokens"] == 6800 + 250 + 5376

    def test_input_does_not_subtract_cache(self, openclaw_dir):
        """OpenClaw 的 usage.input 不含 cache，不能做 cache 扣减。"""
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                _assistant(
                    1769753935279,
                    {
                        "input": 1000,
                        "output": 100,
                        "cacheRead": 800,
                        "cacheWrite": 0,
                        "totalTokens": 1900,
                    },
                )
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["input_tokens"] == 1000
        assert result.records[0]["cache_read_tokens"] == 800


class TestTotalFallback:
    """总数兜底（对齐 ccusage apply_total_token_fallback）"""

    def test_missing_tokens_go_to_output_when_output_is_zero(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                _assistant(
                    1769753935279,
                    {"input": 100, "output": 0, "cacheRead": 25, "totalTokens": 175},
                )
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        record = result.records[0]
        # output 为 0 时，缺口补进 output（不进入不可见的 extra 桶）
        assert record["output_tokens"] == 50
        assert record["total_tokens"] == 175

    def test_missing_tokens_go_to_extra_when_output_is_known(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                _assistant(
                    1769753935279,
                    {
                        "input": 100,
                        "output": 50,
                        "cacheRead": 25,
                        "totalTokens": 200,
                    },
                )
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        record = result.records[0]
        # output 已知时，缺口进入不可见的 extra 桶：四个可见桶不变，总数补齐
        assert record["output_tokens"] == 50
        assert record["input_tokens"] == 100
        assert record["cache_read_tokens"] == 25
        assert record["total_tokens"] == 200
        assert record["total_tokens"] > (
            record["input_tokens"]
            + record["output_tokens"]
            + record["cache_creation_tokens"]
            + record["cache_read_tokens"]
        )

    def test_all_zero_usage_is_dropped(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [_assistant(1769753935279, {"input": 0, "output": 0, "totalTokens": 0})],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records == []


# ========== 模型追踪 ==========


class TestModelTracking:
    """状态化模型追踪（model_change / model-snapshot）"""

    def test_model_change_sets_current_model(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "model_change",
                    "id": "mc-1",
                    "timestamp": "2026-01-30T10:00:00.000Z",
                    "provider": "openai-codex",
                    "modelId": "gpt-5.2",
                },
                # usage 记录本身不带 model，需要回落到追踪到的当前模型
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": "2026-01-30T10:00:07.279Z",
                    "message": {
                        "role": "assistant",
                        "usage": {"input": 1660, "output": 55, "cacheRead": 108928},
                    },
                },
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] gpt-5.2"

    def test_model_snapshot_sets_current_model(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "custom",
                    "customType": "model-snapshot",
                    "id": "snap-1",
                    "timestamp": "2026-03-05T01:19:44.699Z",
                    "data": {"provider": "deepseek", "modelId": "deepseek-v4-flash"},
                },
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": "2026-03-05T01:19:50.000Z",
                    "message": {
                        "role": "assistant",
                        "usage": {"input": 100, "output": 50},
                    },
                },
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] deepseek-v4-flash"

    def test_non_snapshot_custom_record_does_not_change_model(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "custom",
                    "customType": "openclaw:prompt-error",
                    "id": "err-1",
                    "timestamp": "2026-03-05T01:19:44.699Z",
                    "data": {"provider": "deepseek", "modelId": "deepseek-v4-flash"},
                },
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": "2026-03-05T01:19:50.000Z",
                    "message": {
                        "role": "assistant",
                        "usage": {"input": 100, "output": 50},
                    },
                },
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] unknown"

    def test_malformed_message_does_not_drop_model_tracking(self, openclaw_dir):
        """model_change 行的 message 字段非法时，仍要更新追踪状态。"""
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "model_change",
                    "id": "mc-1",
                    "timestamp": "2026-01-30T10:00:00.000Z",
                    "provider": "openai",
                    "modelId": "gpt-5.2",
                    "message": "not-an-object",
                },
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": "2026-01-30T10:00:07.279Z",
                    "message": {
                        "role": "assistant",
                        "usage": {"input": 10, "output": 20},
                    },
                },
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] gpt-5.2"


class TestModelNaming:
    """模型名优先级与 [openclaw] 前缀"""

    def test_model_prefix_is_applied(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                _assistant(
                    1769753935279,
                    {"input": 10, "output": 20},
                    model="kimi-k2.5",
                )
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] kimi-k2.5"

    def test_message_model_id_wins_over_message_model(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": "2026-01-30T10:00:07.279Z",
                    "message": {
                        "role": "assistant",
                        "modelId": "from-model-id",
                        "model": "from-model",
                        "usage": {"input": 10, "output": 20},
                    },
                }
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] from-model-id"

    def test_unknown_model_when_nothing_available(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": "2026-01-30T10:00:07.279Z",
                    "message": {"role": "assistant", "usage": {"input": 10, "output": 20}},
                }
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["model"] == "[openclaw] unknown"


# ========== 时间戳与归桶 ==========


class TestTimestampBucket:
    """时间戳解析与本机时区归桶"""

    def test_epoch_milliseconds_are_used(self, openclaw_dir):
        from app.utils.agent_readers.base import epoch_ms_to_local_date
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [_assistant(1769753935279, {"input": 10, "output": 20})],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["record_date"].isoformat() == epoch_ms_to_local_date(
            1769753935279
        )

    def test_iso_string_timestamp_is_used(self, openclaw_dir):
        from app.utils.agent_readers.base import epoch_ms_to_local_date, parse_iso_timestamp_ms
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        iso = "2026-02-28T02:54:40.470Z"
        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": iso,
                    "message": {
                        "role": "assistant",
                        "usage": {"input": 10, "output": 20},
                    },
                }
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["record_date"].isoformat() == epoch_ms_to_local_date(
            parse_iso_timestamp_ms(iso)
        )

    def test_message_timestamp_wins_over_record_timestamp(self, openclaw_dir):
        """对齐 ccusage：message.timestamp 优先于记录级 timestamp。"""
        from app.utils.agent_readers.base import epoch_ms_to_local_date
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        message_ts = 1769753935279  # 2026-01-30 本机时区
        record_ts = 1767225600000  # 2026-01-01 本机时区
        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": record_ts,
                    "message": {
                        "role": "assistant",
                        "usage": {"input": 10, "output": 20},
                        "timestamp": message_ts,
                    },
                }
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["record_date"].isoformat() == epoch_ms_to_local_date(
            message_ts
        )

    def test_records_outside_range_are_filtered(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [_assistant(1769753935279, {"input": 10, "output": 20})],
        )

        result = read_openclaw_records(date(2025, 1, 1), date(2025, 12, 31))

        assert result.records == []


# ========== 文件发现 ==========


class TestFileDiscovery:
    """文件命名规则与软链跳过"""

    @pytest.mark.parametrize(
        "filename",
        [
            "session.jsonl",
            "session.jsonl.deleted.1700000000000",
            "session.jsonl.reset.2026-03-20T06-34-44.520Z",
        ],
    )
    def test_accepted_filenames(self, openclaw_dir, filename):
        from app.utils.agent_readers.openclaw_reader import (
            _is_openclaw_session_file,
            read_openclaw_records,
        )

        assert _is_openclaw_session_file(filename) is True

        _write_session(
            openclaw_dir,
            filename,
            [_assistant(1769753935279, {"input": 10, "output": 20})],
        )
        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))
        assert len(result.records) == 1

    @pytest.mark.parametrize(
        "filename",
        ["session.json", "session.jsonl.bak", "session.jsonlreset", "notes.txt"],
    )
    def test_rejected_filenames(self, filename):
        from app.utils.agent_readers.openclaw_reader import _is_openclaw_session_file

        assert _is_openclaw_session_file(filename) is False

    def test_symlink_is_skipped(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        target = _write_session(
            openclaw_dir,
            "real.jsonl",
            [_assistant(1769753935279, {"input": 10, "output": 20})],
        )
        link = openclaw_dir / "agents" / "main" / "sessions" / "link.jsonl"
        os.symlink(target, link)

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        # 只统计真实文件一次
        assert len(result.records) == 1
        assert result.records[0]["input_tokens"] == 10

    def test_symlinked_directory_is_not_traversed(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        # 真实目录放在扫描根之外，只通过软链可达
        real_dir = openclaw_dir.parent / "real-sessions"
        real_dir.mkdir()
        (real_dir / "inner.jsonl").write_text(
            json.dumps(_assistant(1769753935279, {"input": 10, "output": 20})) + "\n"
        )
        os.symlink(real_dir, openclaw_dir / "agents" / "main" / "sessions" / "linked")

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records == []


# ========== 去重与容错 ==========


class TestDedupAndResilience:
    """去重与单行容错"""

    def test_identical_records_are_deduplicated(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        line = _assistant(1769753935279, {"input": 1, "output": 1, "totalTokens": 2})
        _write_session(openclaw_dir, "session.jsonl", [line, line])

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert len(result.records) == 1
        assert result.records[0]["input_tokens"] == 1

    def test_broken_line_does_not_abort_file(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        path = openclaw_dir / "agents" / "main" / "sessions" / "a.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        good = json.dumps(_assistant(1769753935279, {"input": 10, "output": 20}))
        path.write_text(
            "{not json}\n" + good + "\n" + "[]\n" + json.dumps({"type": "message"}) + "\n"
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert len(result.records) == 1
        assert result.records[0]["input_tokens"] == 10

    def test_non_assistant_roles_are_ignored(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [
                {
                    "type": "message",
                    "id": "evt-1",
                    "timestamp": 1769753935279,
                    "message": {"role": "user", "usage": {"input": 10, "output": 0}},
                },
                {
                    "type": "message",
                    "id": "evt-2",
                    "timestamp": 1769753935280,
                    "message": {"role": "toolResult", "usage": {"input": 10, "output": 0}},
                },
            ],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records == []

    def test_source_and_source_raw_are_set(self, openclaw_dir):
        from app.utils.agent_readers.openclaw_reader import read_openclaw_records

        _write_session(
            openclaw_dir,
            "a.jsonl",
            [_assistant(1769753935279, {"input": 10, "output": 20})],
        )

        result = read_openclaw_records(date(2026, 1, 1), date(2026, 12, 31))

        assert result.records[0]["source"] == "openclaw"
        assert result.records[0]["source_raw"] == "openclaw-jsonl"


# ========== 路径发现 ==========


class TestPathDiscovery:
    """数据根发现"""

    def test_openclaw_dir_env_takes_precedence(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.openclaw_reader import _openclaw_roots

        custom = tmp_path / "custom"
        custom.mkdir()
        monkeypatch.setenv("OPENCLAW_DIR", str(custom))

        assert _openclaw_roots() == [custom]

    def test_missing_openclaw_dir_env_entries_are_ignored(self, tmp_path, monkeypatch):
        from app.utils.agent_readers.openclaw_reader import _openclaw_roots

        existing = tmp_path / "existing"
        existing.mkdir()
        monkeypatch.setenv(
            "OPENCLAW_DIR", f"{existing}, {tmp_path / 'missing'}, {existing}"
        )

        assert _openclaw_roots() == [existing]

    def test_tilde_is_expanded_with_real_home(self, monkeypatch):
        """``~`` 必须用 real_home() 展开，不能用被 config.py 覆盖的 HOME。"""
        from app.utils.agent_readers.base import real_home
        from app.utils.agent_readers.openclaw_reader import _expand_home

        monkeypatch.setenv("HOME", "/tmp/fake-home")

        assert _expand_home("~") == real_home()
        assert _expand_home("~/x") == real_home() / "x"
        assert _expand_home("/abs/path") == __import__("pathlib").Path("/abs/path")
