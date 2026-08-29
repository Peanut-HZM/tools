"""image_gen_backend 指标收集

结构化日志 + 滑动窗口一致性统计，供 dual 模式验证阶段使用。

参考 spec §7.1 阶段 1 验证清单
"""
import json
import logging
import time
from collections import deque
from threading import Lock
from typing import Any, Deque, Dict, Optional

logger = logging.getLogger(__name__)

# 滑动窗口：保存最近 N 次调用结果（线程安全）
_METRICS_WINDOW: Deque[Dict[str, Any]] = deque(maxlen=1000)
_METRICS_LOCK = Lock()


def log_image_gen_metric(
    request_id: str,
    backend: str,
    primary_success: bool,
    secondary_success: bool,
    primary_urls: int,
    secondary_urls: int,
    elapsed_ms_primary: int,
    elapsed_ms_secondary: int,
    diff_reasons: list,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """记录一条 image_gen 指标到日志 + 滑动窗口

    结构化 JSON 便于运维 grep 聚合。
    """
    consistent = (
        primary_success == secondary_success
        and primary_urls == secondary_urls
        and not diff_reasons
    )

    payload = {
        "image_gen_metric": True,
        "ts": time.time(),
        "request_id": request_id,
        "backend": backend,
        "primary_success": primary_success,
        "secondary_success": secondary_success,
        "primary_urls": primary_urls,
        "secondary_urls": secondary_urls,
        "elapsed_ms_primary": elapsed_ms_primary,
        "elapsed_ms_secondary": elapsed_ms_secondary,
        "diff_reasons": diff_reasons,
        "consistent": consistent,
    }
    if extra:
        payload.update(extra)

    logger.info("image_gen_metric %s", json.dumps(payload, ensure_ascii=False))

    with _METRICS_LOCK:
        _METRICS_WINDOW.append(payload)


def summarize_recent_metrics(window: int = 100) -> Dict[str, Any]:
    """汇总最近 N 条指标的一致性

    Returns:
        dict: {total, consistent, consistency_rate, primary_success_rate, ...}
    """
    with _METRICS_LOCK:
        recent = list(_METRICS_WINDOW)[-window:]

    if not recent:
        return {"total": 0, "consistent": 0, "consistency_rate": 0.0}

    total = len(recent)
    consistent = sum(1 for m in recent if m.get("consistent"))
    primary_success = sum(1 for m in recent if m.get("primary_success"))
    secondary_success = sum(1 for m in recent if m.get("secondary_success"))

    return {
        "total": total,
        "consistent": consistent,
        "consistency_rate": consistent / total,
        "primary_success_rate": primary_success / total,
        "secondary_success_rate": secondary_success / total,
        "diff_reason_counts": _count_diff_reasons(recent),
    }


def _count_diff_reasons(recent: list) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for m in recent:
        for reason in m.get("diff_reasons", []):
            key = reason.split(":")[0]
            counts[key] = counts.get(key, 0) + 1
    return counts
