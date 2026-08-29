"""image_gen_backend metrics 测试"""
import json
import logging
import pytest

from app.services.harness.image_gen_backend.metrics import (
    log_image_gen_metric,
    summarize_recent_metrics,
)


class TestImageGenMetrics:
    def test_log_emits_structured_json(self, caplog):
        """日志输出结构化 JSON 便于解析"""
        import logging
        caplog.set_level(logging.INFO)

        log_image_gen_metric(
            request_id="req-1",
            backend="dual",
            primary_success=True,
            secondary_success=False,
            primary_urls=2,
            secondary_urls=1,
            elapsed_ms_primary=3000,
            elapsed_ms_secondary=2500,
            diff_reasons=["success_diff:True vs False"],
        )

        records = [r for r in caplog.records if "image_gen_metric" in r.message]
        assert len(records) == 1
        # JSON 内容应在 message 中
        msg = records[0].message
        assert "req-1" in msg
        assert "dual" in msg

    def test_summarize_aggregates_recent(self):
        """汇总最近 N 条指标的一致性比率"""
        # 模拟多次调用
        for i in range(10):
            log_image_gen_metric(
                request_id=f"req-{i}",
                backend="dual",
                primary_success=True,
                secondary_success=(i % 3 != 0),  # 70% 一致
                primary_urls=2,
                secondary_urls=2 if i % 3 != 0 else 1,
                elapsed_ms_primary=3000,
                elapsed_ms_secondary=2500,
                diff_reasons=[] if i % 3 != 0 else ["url_count_diff"],
            )

        summary = summarize_recent_metrics(window=10)
        assert summary["total"] == 10
        assert summary["consistent"] == 6  # i=0,3,6,9 不一致 = 4 个；其余 6 一致
        assert summary["consistency_rate"] >= 0.5
