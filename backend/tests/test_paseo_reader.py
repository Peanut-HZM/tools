"""Paseo Token 用量读取器测试

覆盖 paseo_reader 的：
- 路径发现（PASEO_USAGE_FILE 优先，回退真实家目录）
- 四桶映射（input / output / cache_creation / cache_read）
- extra 桶归位（total 与四桶之和不一致时的兜底）
- 日期归桶（UTC 时间戳 → 本机时区自然日）
- 损坏行跳过
- 与 SOURCE_TOOL_MAPPING / READERS / VERIFIED_AGENTS 的登记一致性

所有期望值都是**手工核算**的常量，不依赖外部 CLI，也不依赖本机恰好有数据。
"""
import json
import os
from datetime import date, datetime, timedelta, timezone

import pytest

from app.utils.agent_readers import READERS, VERIFIED_AGENTS
from app.utils.agent_readers.paseo_reader import (
    SOURCE,
    _NATIVELY_COVERED_PROVIDERS,
    _row_to_usage,
    read_paseo_records,
)
from app.services.token_usage_sync_service import (
    KNOWN_SOURCES,
    NATIVE_READER_SOURCES,
    SOURCE_TOOL_MAPPING,
)


def _write_lines(tmp_path, lines, name="acp-usage.jsonl"):
    """把若干行写入临时用量文件并返回其路径。"""
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _iso(dt: datetime) -> str:
    """生成 ISO-8601 UTC 字符串（与 shim 落盘格式一致）。"""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class TestRowParsing:
    """单行 JSONL → 归一化用量桶"""

    def test_four_bucket_mapping(self):
        """四桶直传：input 不含 cache，无需扣减。

        手工核算：
          input=1000, output=200, cache_read=300, cache_creation=100
          四桶之和 = 1000+200+300+100 = 1600
          thought=50 计入 output → output=250
          total=1600 时四桶和(1600)+thought(50)=1650 > total
          → known=1650 > missing=0，不触发兜底
        """
        row = {
            "ts": _iso(datetime(2026, 11, 10, 10, 0, 0)),
            "model": "glm-5.3",
            "inputTokens": 1000,
            "outputTokens": 200,
            "totalTokens": 1600,
            "cachedReadTokens": 300,
            "cachedWriteTokens": 100,
            "thoughtTokens": 50,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 250  # 200 + 50 thought
        assert usage["cache_read_tokens"] == 300
        assert usage["cache_creation_tokens"] == 100
        assert usage["extra_total_tokens"] == 0

    def test_thought_tokens_belong_to_output(self):
        """推理 token 计入 output（ACP 的 outputTokens 不含推理）。"""
        row = {
            "ts": _iso(datetime(2026, 11, 10, 10, 0, 0)),
            "model": "glm-5.3-flash",
            "inputTokens": 10,
            "outputTokens": 20,
            "totalTokens": 100,
            "thoughtTokens": 30,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        assert usage["output_tokens"] == 50
        # 自报 total=100 远大于四桶和(10+50)=60，差值 40 归 extra 桶
        assert usage["extra_total_tokens"] == 40

    def test_extra_bucket_when_total_exceeds_sum(self):
        """total 大于四桶之和且 output != 0 时，差值归 extra 桶。

        手工核算：四桶和 = 10+20+0+0 = 30，total=100，missing=70
        output 非 0 → 70 归 extra。
        """
        row = {
            "ts": _iso(datetime(2026, 11, 10, 10, 0, 0)),
            "model": "m",
            "inputTokens": 10,
            "outputTokens": 20,
            "totalTokens": 100,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        assert usage["extra_total_tokens"] == 70
        assert usage["output_tokens"] == 20  # output 非 0，不被改写

    def test_missing_total_falls_back_to_output(self):
        """output 为 0 且 total 大于四桶和时，差值补进 output。"""
        row = {
            "ts": _iso(datetime(2026, 11, 10, 10, 0, 0)),
            "model": "m",
            "inputTokens": 10,
            "outputTokens": 0,
            "totalTokens": 100,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        assert usage["output_tokens"] == 90  # 100 - 10
        assert usage["extra_total_tokens"] == 0

    def test_negative_and_bool_values_clamped_to_zero(self):
        """非法数值（负数 / bool / 字符串）按 0 处理，不污染统计。"""
        row = {
            "ts": _iso(datetime(2026, 11, 10, 10, 0, 0)),
            "model": "m",
            "inputTokens": -5,
            "outputTokens": True,
            "totalTokens": "100",
            "cachedReadTokens": None,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["cache_read_tokens"] == 0

    def test_missing_model_falls_back_to_unknown(self):
        """缺模型名归入 unknown，不丢数据。"""
        row = {
            "ts": _iso(datetime(2026, 11, 10, 10, 0, 0)),
            "inputTokens": 5,
            "outputTokens": 5,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        assert usage["model"] == "unknown"

    def test_missing_timestamp_returns_none(self):
        """缺时间戳的行无法归日，返回 None 由调用方跳过。"""
        assert _row_to_usage({"model": "m", "inputTokens": 1}) is None

    def test_invalid_timestamp_returns_none(self):
        """时间戳格式非法同样跳过。"""
        assert _row_to_usage({"ts": "not-a-date", "model": "m"}) is None


class TestDateBucketing:
    """日期归桶：UTC 时间戳 → 本机时区自然日"""

    def test_utc_timestamp_bucketed_to_local_date(self):
        """UTC 深夜的记录应归到本机时区的当天，不是 UTC 前一天。

        以本机时区为准构造：给定 UTC 11-09T16:30Z，
        本机（Asia/Shanghai, UTC+8）为 11-10 00:30 → 归 11-10。
        """
        row = {
            "ts": "2026-11-09T16:30:00Z",
            "model": "m",
            "inputTokens": 1,
            "outputTokens": 1,
        }
        usage = _row_to_usage(row)
        assert usage is not None
        local = datetime.fromtimestamp(
            datetime(2026, 11, 9, 16, 30, tzinfo=timezone.utc).timestamp()
        ).date()
        assert usage["record_date"] == local


class TestReadPaseoRecords:
    """读取器整体行为"""

    def test_reads_and_aggregates_by_date_and_model(self, tmp_path, monkeypatch):
        """同一 (日期, 模型) 的多行会被聚合成一条记录。

        手工核算：11-10 两条 glm-5.3（1000+500 input，100+50 output）
        + 一条 glm-5.3-flash，聚合后 glm-5.3 = input 1500 / output 150。
        """
        path = _write_lines(
            tmp_path,
            [
                json.dumps({
                    "ts": "2026-11-10T02:00:00Z", "model": "glm-5.3",
                    "inputTokens": 1000, "outputTokens": 100, "totalTokens": 1100,
                }),
                json.dumps({
                    "ts": "2026-11-10T03:00:00Z", "model": "glm-5.3",
                    "inputTokens": 500, "outputTokens": 50, "totalTokens": 550,
                }),
                json.dumps({
                    "ts": "2026-11-10T04:00:00Z", "model": "glm-5.3-flash",
                    "inputTokens": 10, "outputTokens": 5, "totalTokens": 15,
                }),
            ],
        )
        monkeypatch.setenv("PASEO_USAGE_FILE", str(path))

        result = read_paseo_records(date(2026, 11, 1), date(2026, 11, 30))
        assert result.errors == []
        assert len(result.records) == 2

        by_model = {r["model"]: r for r in result.records}
        assert by_model["glm-5.3"]["input_tokens"] == 1500
        assert by_model["glm-5.3"]["output_tokens"] == 150
        assert by_model["glm-5.3-flash"]["input_tokens"] == 10

    def test_corrupted_lines_are_skipped(self, tmp_path, monkeypatch):
        """损坏行 / 非对象行只丢该行，不中断整体。"""
        path = _write_lines(
            tmp_path,
            [
                "not json at all",
                json.dumps([1, 2, 3]),  # 非对象
                json.dumps({
                    "ts": "2026-11-10T02:00:00Z", "model": "m",
                    "inputTokens": 7, "outputTokens": 3, "totalTokens": 10,
                }),
                "",
            ],
        )
        monkeypatch.setenv("PASEO_USAGE_FILE", str(path))

        result = read_paseo_records(date(2026, 11, 1), date(2026, 11, 30))
        assert result.errors == []
        assert len(result.records) == 1
        assert result.records[0]["input_tokens"] == 7

    def test_missing_file_returns_empty_without_error(self, tmp_path, monkeypatch):
        """文件不存在时静默跳过，不算同步告警（与其它读取器一致）。"""
        monkeypatch.setenv(
            "PASEO_USAGE_FILE", str(tmp_path / "nope" / "acp-usage.jsonl")
        )
        result = read_paseo_records(date(2026, 11, 1), date(2026, 11, 30))
        assert result.records == []
        assert result.errors == []

    def test_date_range_filtering(self, tmp_path, monkeypatch):
        """区间外的记录被过滤掉。

        注意：ts 是 UTC，归日按**本机时区**。这里用本地时间 12:00
        对应的 UTC 时刻，保证落点日期与预期一致。
        """
        local_noon = datetime(2026, 11, 20, 12, 0, 0).astimezone(timezone.utc)
        local_noon_iso = _iso(local_noon)
        path = _write_lines(
            tmp_path,
            [
                json.dumps({
                    "ts": "2026-11-01T04:00:00Z", "model": "m",
                    "inputTokens": 1, "outputTokens": 1, "totalTokens": 2,
                }),
                json.dumps({
                    "ts": local_noon_iso, "model": "m",
                    "inputTokens": 2, "outputTokens": 2, "totalTokens": 4,
                }),
            ],
        )
        monkeypatch.setenv("PASEO_USAGE_FILE", str(path))

        result = read_paseo_records(date(2026, 11, 10), date(2026, 11, 15))
        assert len(result.records) == 0

        # 扩大区间后两条都在
        result_all = read_paseo_records(date(2026, 10, 25), date(2026, 11, 25))
        assert len(result_all.records) == 2


    def test_natively_covered_providers_are_skipped(self, tmp_path, monkeypatch):
        """已有原生读取器的 provider 必须跳过，避免重复统计。

        kimi / minimax 等 Agent 自己会落盘用量，原生读取器已在采集；
        若 paseo 读取器再采一遍，汇总会翻倍。
        """
        path = _write_lines(
            tmp_path,
            [
                json.dumps({
                    "ts": "2026-11-10T04:00:00Z", "provider": "kimi",
                    "model": "kimi-for-coding", "inputTokens": 100,
                    "outputTokens": 10, "totalTokens": 110,
                }),
                json.dumps({
                    "ts": "2026-11-10T04:00:00Z", "provider": "minimax",
                    "model": "MiniMax-M3.1-Flash", "inputTokens": 200,
                    "outputTokens": 20, "totalTokens": 220,
                }),
                json.dumps({
                    "ts": "2026-11-10T04:00:00Z", "provider": "glm",
                    "model": "glm-5.3", "inputTokens": 300,
                    "outputTokens": 30, "totalTokens": 330,
                }),
            ],
        )
        monkeypatch.setenv("PASEO_USAGE_FILE", str(path))

        result = read_paseo_records(date(2026, 11, 1), date(2026, 11, 30))
        assert len(result.records) == 1
        assert result.records[0]["model"] == "glm-5.3"
        assert result.records[0]["input_tokens"] == 300

    def test_natively_covered_set_is_valid(self):
        """跳过名单里的 provider 必须都真的有原生读取器（防止名单腐化）。"""
        from app.utils.agent_readers import READERS

        assert _NATIVELY_COVERED_PROVIDERS <= set(READERS.keys())
        # paseo 自己不能在自己的跳过名单里
        assert SOURCE not in _NATIVELY_COVERED_PROVIDERS


class TestRegistration:
    """登记一致性：source id 必须三处一致"""

    def test_reader_registered(self):
        assert "paseo" in READERS
        assert READERS["paseo"].__name__ == "read_paseo_records"

    def test_source_id_matches_tool_mapping(self):
        """source id 必须与 SOURCE_TOOL_MAPPING 的 key 完全一致。

        不一致会产生重复行、汇总翻倍——本项目的硬性要求。
        """
        assert SOURCE in SOURCE_TOOL_MAPPING
        assert SOURCE in KNOWN_SOURCES
        assert SOURCE in NATIVE_READER_SOURCES

    def test_verified_agents_in_sync_with_readers(self):
        """VERIFIED_AGENTS 与 READERS 必须同步登记。"""
        assert set(VERIFIED_AGENTS) <= set(READERS.keys())
        assert "paseo" in VERIFIED_AGENTS
