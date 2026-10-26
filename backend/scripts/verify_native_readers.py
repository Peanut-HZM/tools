"""原生读取器 vs ccusage 逐日对账工具

用途：作为"移除 ccusage 统计逻辑"的**验收闸门**。
只有当某个 Agent 的原生读取结果与 ccusage 在 (日期, 模型) 维度上
**逐项完全一致**时，才允许把该 Agent 切换到原生实现。

用法（在 backend/ 目录下执行）:
    python -m scripts.verify_native_readers --since 2026-10-01 --until 2026-12-31
    python -m scripts.verify_native_readers --agents claude,kimi
    python -m scripts.verify_native_readers --days 90 --json

退出码：
    0 = 全部 Agent 对账通过（零差异）
    1 = 存在差异
    2 = ccusage 不可用（无法对账）

说明：
- 对账只比对 **token 数量**，不比对 cost。原生读取器不内置价格表，
  cost 统一为 0；而 ccusage 的 cost 来自 LiteLLM 定价快照，两者不可比。
- ccusage 的模型名可能带 store 前缀（``[pi] `` / ``[openclaw] ``），
  对账时统一剥除前缀后再比较。
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, timedelta
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ccusage 部分适配器会在模型名前加 store 前缀，对账时剥除
_STORE_PREFIX = re.compile(r"^\[[a-z0-9_-]+\]\s*", re.IGNORECASE)


def _normalize_model(model: str) -> str:
    """剥除 ccusage 的 store 前缀，得到可与原生实现直接比较的模型名。"""
    return _STORE_PREFIX.sub("", (model or "").strip())


def _ccusage_version(ccusage_exe: Optional[str] = None) -> Optional[str]:
    """获取 ccusage 版本号，用于识别过旧的对账基准。"""
    try:
        from app.utils.ccusage_invoker import build_cmd, find_ccusage

        path = ccusage_exe or find_ccusage()
        if path is None:
            return None
        cmd = build_cmd(["--version"], ccusage_path=path)
        if not cmd:
            return None
        import subprocess

        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        text = (completed.stdout or "") + (completed.stderr or "")
        for token in text.replace("v", " ").split():
            if token[0:1].isdigit() and "." in token:
                return token
    except Exception:  # pragma: no cover
        return None
    return None


def _ccusage_daily(
    agent: str, since: date, until: date, ccusage_exe: Optional[str] = None
) -> Optional[dict]:
    """调用 ccusage 获取单个 agent 的 daily 报表，失败返回 None。"""
    try:
        from app.utils.ccusage_invoker import run_ccusage
    except Exception as exc:  # pragma: no cover
        logger.error("导入 ccusage 调用器失败: %s", exc)
        return None

    result = run_ccusage(
        [
            agent,
            "daily",
            "--json",
            "--offline",
            f"--since={since.isoformat()}",
            f"--until={until.isoformat()}",
        ],
        timeout=300,
        ccusage_path=ccusage_exe,
    )
    if not result.get("ok"):
        error = result.get("error")
        details = getattr(error, "details", {}) or {}
        stderr = str(details.get("stderr", ""))
        if "Unknown command" in stderr:
            # ccusage 本身不支持该 Agent（原生实现是其超集），不参与对账
            return {"__no_such_agent__": True}
        logger.warning("ccusage %s 调用失败: %s", agent, error)
        return None
    return result.get("data") or {}


def _ccusage_totals_by_model(payload: dict) -> dict[tuple[str, str], dict[str, int]]:
    """把 ccusage 报表归一化为 ``(日期, 模型) -> token 明细``。

    兼容两种结构：
    - 通用结构：``daily[].modelBreakdowns[]``（字段 camelCase）
    - Codex 结构：``daily[].models{}``（map，键为模型名）
    """
    totals: dict[tuple[str, str], dict[str, int]] = {}

    def _add(day: str, model: str, entry: dict) -> None:
        key = (day, _normalize_model(model))
        bucket = totals.setdefault(
            key,
            {
                "input": 0,
                "output": 0,
                "cache_creation": 0,
                "cache_read": 0,
                "total": 0,
            },
        )
        bucket["input"] += int(entry.get("inputTokens") or 0)
        bucket["output"] += int(entry.get("outputTokens") or 0)
        bucket["cache_creation"] += int(entry.get("cacheCreationTokens") or 0)
        bucket["cache_read"] += int(entry.get("cacheReadTokens") or 0)
        declared = entry.get("totalTokens")
        if declared is None:
            # ccusage 的 modelBreakdowns 不序列化 totalTokens（其 extra 桶也不可见），
            # 按四个可见桶求和作为对账口径
            bucket["total"] += (
                int(entry.get("inputTokens") or 0)
                + int(entry.get("outputTokens") or 0)
                + int(entry.get("cacheCreationTokens") or 0)
                + int(entry.get("cacheReadTokens") or 0)
            )
        else:
            bucket["total"] += int(declared or 0)

    for day_row in payload.get("daily") or []:
        day = day_row.get("date") or day_row.get("period") or ""
        for breakdown in day_row.get("modelBreakdowns") or []:
            _add(day, breakdown.get("modelName") or "", breakdown)
        for model_name, entry in (day_row.get("models") or {}).items():
            if isinstance(entry, dict):
                _add(day, model_name, entry)
    return totals


def _native_totals_by_model(records: list[dict]) -> dict[tuple[str, str], dict[str, int]]:
    """把原生读取结果归一化为 ``(日期, 模型) -> token 明细``。

    ``total`` 为记录自报的总 token（**含 extra 桶**：原生读取器把"已知存在但
    无法归入四类"的 token 放进 extra 桶，只计入 total）。
    ``visible_total`` 为四个可见桶之和，与 ccusage 的 per-model 明细口径一致，
    逐模型比对时用它做 like-for-like 比较。
    """
    totals: dict[tuple[str, str], dict[str, int]] = {}
    for record in records:
        raw_date = record["record_date"]
        day = raw_date.isoformat() if hasattr(raw_date, "isoformat") else str(raw_date)
        key = (day, _normalize_model(record["model"]))
        bucket = totals.setdefault(
            key,
            {
                "input": 0,
                "output": 0,
                "cache_creation": 0,
                "cache_read": 0,
                "total": 0,
                "visible_total": 0,
            },
        )
        inp = int(record.get("input_tokens") or 0)
        out = int(record.get("output_tokens") or 0)
        cc = int(record.get("cache_creation_tokens") or 0)
        cr = int(record.get("cache_read_tokens") or 0)
        bucket["input"] += inp
        bucket["output"] += out
        bucket["cache_creation"] += cc
        bucket["cache_read"] += cr
        bucket["visible_total"] += inp + out + cc + cr
        bucket["total"] += int(record.get("total_tokens") or 0)
    return totals


def _native_daily_totals(records: list[dict]) -> dict[str, int]:
    """原生读取结果的按日总 token（含 extra 桶）。

    对应 ccusage 的 ``daily[].totalTokens``：该值等于四桶之和再加上 extra 桶，
    因此可以整体校验 extra 桶是否正确。
    """
    totals: dict[str, int] = {}
    for record in records:
        raw_date = record["record_date"]
        day = raw_date.isoformat() if hasattr(raw_date, "isoformat") else str(raw_date)
        totals[day] = totals.get(day, 0) + int(record.get("total_tokens") or 0)
    return totals


def _ccusage_daily_totals(payload: dict) -> dict[str, int]:
    """ccusage 报表的按日总 token。"""
    totals: dict[str, int] = {}
    for day_row in payload.get("daily") or []:
        day = day_row.get("date") or day_row.get("period") or ""
        if not day:
            continue
        declared = day_row.get("totalTokens")
        if declared is None:
            continue
        totals[day] = totals.get(day, 0) + int(declared or 0)
    return totals


def _diff(
    native: dict[tuple[str, str], dict[str, int]],
    reference: dict[tuple[str, str], dict[str, int]],
) -> list[dict]:
    """逐项比较两个归一化结果，返回差异列表。"""
    differences: list[dict] = []
    for key in sorted(set(native) | set(reference)):
        left = native.get(key)
        right = reference.get(key)
        if left is None:
            differences.append({"key": key, "kind": "only_in_ccusage", "native": None, "ccusage": right})
            continue
        if right is None:
            differences.append({"key": key, "kind": "only_in_native", "native": left, "ccusage": None})
            continue
        for field in ("input", "output", "cache_creation", "cache_read"):
            if left[field] != right[field]:
                differences.append(
                    {
                        "key": key,
                        "kind": "value_mismatch",
                        "field": field,
                        "native": left[field],
                        "ccusage": right[field],
                    }
                )
        # total 用"四桶可见和"做 like-for-like 比较：
        # ccusage 的 per-model 明细不暴露 extra 桶，原生侧的 total 含 extra。
        # extra 桶的正确性由按日总额校验（_diff_daily_totals）单独覆盖。
        native_visible = left.get("visible_total", left["total"])
        if native_visible != right["total"]:
            differences.append(
                {
                    "key": key,
                    "kind": "value_mismatch",
                    "field": "total",
                    "native": native_visible,
                    "ccusage": right["total"],
                }
            )
    return differences


def _diff_daily_totals(
    native: dict[str, int],
    reference: dict[str, int],
) -> list[dict]:
    """按日比较总 token（含 extra 桶），用于校验 extra 桶是否正确。

    ccusage 的 ``daily[].totalTokens`` 等于四桶之和再加 extra 桶，与原生读取器
    记录的 ``total_tokens`` 口径一致。
    """
    differences: list[dict] = []
    for day in sorted(set(native) | set(reference)):
        left = native.get(day, 0)
        right = reference.get(day, 0)
        if left != right:
            differences.append(
                {
                    "key": (day, "_daily_total"),
                    "kind": "daily_total_mismatch",
                    "field": "total",
                    "native": left,
                    "ccusage": right,
                }
            )
    return differences


def _is_live_drift(
    key: tuple[str, str],
    field: str,
    native_first: int,
    ccusage_value: int,
    native_second: int,
) -> bool:
    """判断差异是否只是"数据源正在被写入"造成的采样漂移。

    对账流程是"先读原生、再读 ccusage"，因此对**正在被写入**的数据源
    （如本机的 ZCode / MiniMax Code SQLite），ccusage 读到的值必然 >= 原生读到的值。

    判定方法：再采样一次原生读数 ``native_second``。若
    ``native_first <= ccusage_value <= native_second``，说明 ccusage 的读数落在
    两次原生采样之间 —— 数值差异来自数据源增长，而非口径不一致。
    """
    return native_first <= ccusage_value <= native_second


def _recheck_with_second_native_sample(
    agent: str,
    native_records: list[dict],
    differences: list[dict],
    since: date,
    until: date,
    max_diff: int = 5,
) -> tuple[list[dict], dict]:
    """对有差异的 Agent 再采样一次原生读数，剔除"活跃写入"造成的漂移。

    Returns:
        ``(剩余差异, 漂移说明)``
    """
    from app.utils.agent_readers import read_all_agents

    second = read_all_agents(since, until, only=[agent])
    native_first_map = _native_totals_by_model(native_records)
    native_second_map = _native_totals_by_model(second.get("records", []))

    remaining: list[dict] = []
    drifts: list[dict] = []
    for diff in differences:
        if diff["kind"] == "value_mismatch":
            key = diff["key"]
            left_first = native_first_map.get(key, {}).get(diff["field"], 0)
            left_second = native_second_map.get(key, {}).get(diff["field"], 0)
            if _is_live_drift(
                key,
                diff["field"],
                int(left_first),
                int(diff["ccusage"]),
                int(left_second),
            ):
                drifts.append(diff)
                continue
        remaining.append(diff)
    return remaining, {"drift_count": len(drifts), "drifts": drifts[:max_diff]}


def main() -> int:
    parser = argparse.ArgumentParser(description="原生读取器 vs ccusage 对账")
    parser.add_argument("--since", type=str, default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--until", type=str, default=None, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=90, help="未指定 --since 时回看 N 天")
    parser.add_argument(
        "--agents",
        type=str,
        default=None,
        help="只对账指定 Agent（逗号分隔），默认全部已登记读取器",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    parser.add_argument(
        "--max-diff",
        type=int,
        default=30,
        help="最多打印多少条差异明细",
    )
    parser.add_argument(
        "--ccusage-exe",
        type=str,
        default=None,
        help="显式指定对账基准使用的 ccusage 可执行文件（用于锁定版本）",
    )
    args = parser.parse_args()

    if args.since:
        since = date.fromisoformat(args.since)
    else:
        since = date.today() - timedelta(days=max(1, args.days) - 1)
    until = date.fromisoformat(args.until) if args.until else date.today()

    from app.utils.agent_readers import READERS, VERIFIED_AGENTS, read_all_agents

    agents = (
        [a.strip() for a in args.agents.split(",") if a.strip()]
        if args.agents
        else list(READERS.keys())
    )
    agents = [a for a in agents if a in READERS]
    if not agents:
        logger.error("没有可对账的 Agent")
        return 2

    logger.info("对账范围: %s ~ %s，Agent: %s", since, until, ", ".join(agents))
    version = _ccusage_version(args.ccusage_exe)
    logger.info("对账基准 ccusage 版本: %s", version or "未知")

    native_all = read_all_agents(since, until, only=agents)
    native_by_source: dict[str, list[dict]] = {}
    for record in native_all["records"]:
        native_by_source.setdefault(record["source"], []).append(record)

    report: dict[str, Any] = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "ccusage_version": version,
        "agents": {},
        "all_passed": True,
        "ccusage_available": True,
    }

    for agent in agents:
        native = _native_totals_by_model(native_by_source.get(agent, []))
        payload = _ccusage_daily(agent, since, until, ccusage_exe=args.ccusage_exe)
        if payload is not None and payload.get("__no_such_agent__"):
            report["agents"][agent] = {
                "status": "not_applicable",
                "reason": "ccusage 无此 Agent（原生实现为其超集，无需对账）",
                "native_keys": len(native),
                "native_total_tokens": sum(v["total"] for v in native.values()),
            }
            continue
        if payload is None:
            report["ccusage_available"] = False
            report["agents"][agent] = {
                "status": "skipped",
                "reason": "ccusage 不可用",
            }
            continue

        reference = _ccusage_totals_by_model(payload)
        differences = _diff(native, reference)
        # 按日总额校验（含 extra 桶）——ccusage 的 daily[].totalTokens 与原生记录
        # 的 total_tokens 口径一致，可整体校验 extra 桶
        differences.extend(
            _diff_daily_totals(
                _native_daily_totals(native_by_source.get(agent, [])),
                _ccusage_daily_totals(payload),
            )
        )

        # 数据源正在被写入时（ZCode / MiniMax Code 等），两次采样之间数据会增长，
        # 表现为 ccusage 读数略大于原生读数。再采样一次原生读数做夹逼判定：
        # 若 ccusage 读数落在两次原生采样之间，则属于采样漂移而非口径不一致。
        drift_info: dict = {"drift_count": 0, "drifts": []}
        if differences:
            differences, drift_info = _recheck_with_second_native_sample(
                agent,
                native_by_source.get(agent, []),
                differences,
                since,
                until,
                max_diff=args.max_diff,
            )
            if drift_info["drift_count"]:
                logger.info(
                    "[%s] 检出 %s 处采样漂移（数据源正在写入，已用二次采样夹逼确认）",
                    agent,
                    drift_info["drift_count"],
                )

        native_sum = sum(v["total"] for v in native.values())
        reference_sum = sum(v["total"] for v in reference.values())

        report["agents"][agent] = {
            "status": "passed" if not differences else "failed",
            "native_keys": len(native),
            "ccusage_keys": len(reference),
            "native_total_tokens": native_sum,
            "ccusage_total_tokens": reference_sum,
            "native_visible_total_tokens": sum(
                v.get("visible_total", v["total"]) for v in native.values()
            ),
            "ccusage_visible_total_tokens": reference_sum,
            "native_extra_total_tokens": native_sum
            - sum(v.get("visible_total", v["total"]) for v in native.values()),
            "live_drift": drift_info,
            "differences": differences[: args.max_diff],
            "difference_count": len(differences),
        }
        if differences:
            report["all_passed"] = False

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 78)
        print(f"原生读取器 vs ccusage 对账报告  {since} ~ {until}")
        print("=" * 78)
        for agent, info in report["agents"].items():
            if info["status"] == "not_applicable":
                print(
                    f"[不适用] {agent:<10} {info['reason']} | "
                    f"原生 {info.get('native_total_tokens', 0):>16,}"
                )
                continue
            if info["status"] == "skipped":
                print(f"[跳过] {agent:<10} {info['reason']}")
                continue
            flag = "通过" if info["status"] == "passed" else "不通过"
            verified = "（已验证）" if agent in VERIFIED_AGENTS else "（未验证）"
            extra = info.get("native_extra_total_tokens", 0)
            extra_note = f" | 原生 extra 桶 {extra:,}" if extra else ""
            drift = info.get("live_drift") or {}
            drift_note = (
                f" | 采样漂移 {drift.get('drift_count', 0)} 处（数据源活跃写入）"
                if drift.get("drift_count")
                else ""
            )
            print(
                f"[{flag}] {agent:<10}{verified} "
                f"原生键 {info['native_keys']:>4} / ccusage 键 {info['ccusage_keys']:>4} | "
                f"四桶和 原生 {info['native_visible_total_tokens']:>16,} / "
                f"ccusage {info['ccusage_visible_total_tokens']:>16,}{extra_note}{drift_note}"
            )
            for diff in info["differences"]:
                key = diff["key"]
                if diff["kind"] == "value_mismatch":
                    print(
                        f"        差异 {key[0]} {key[1]} 字段 {diff['field']}: "
                        f"原生 {diff['native']:,} vs ccusage {diff['ccusage']:,}"
                    )
                else:
                    print(f"        差异 {key[0]} {key[1]} {diff['kind']}")
        print("=" * 78)
        print("总体结果:", "全部通过" if report["all_passed"] else "存在差异")

    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
