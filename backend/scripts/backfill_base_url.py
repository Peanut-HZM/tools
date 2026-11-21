#!/usr/bin/env python3
"""回填订阅账号的 base_url / base_url_norm（默认 dry-run）

设计依据：``specs/agent-subscription-bridge-design.md`` §4.4

* 只补「base_url 为空或 base_url_norm 为空」的行（行级 WHERE，重复执行安全）
* JSON 解析失败的行计入 skipped，不中断
* 归一化只在 Python 侧实现（``url_norm.normalize_base_url``）

用法::

    cd backend
    python -m scripts.backfill_base_url --user-id <uid>              # 预览
    python -m scripts.backfill_base_url --user-id <uid> --apply      # 写库
    python -m scripts.backfill_base_url --user-id <uid> --apply --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.services.subscription_quota.accounts import (  # noqa: E402
    TABLE_NAME,
    _get_engine,
    ensure_schema,
)
from app.services.subscription_quota.url_norm import normalize_base_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="回填订阅账号的 base_url / base_url_norm")
    parser.add_argument("--user-id", required=True, help="目标用户 ID")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认只预览）")
    parser.add_argument("--verbose", action="store_true", help="打印每条明细（掩码脱敏）")
    args = parser.parse_args()

    ensure_schema()
    engine = _get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, provider_id, label, base_url, base_url_norm, extra_json, api_key_hash "
                f"FROM {TABLE_NAME} "
                f"WHERE user_id = :uid AND (base_url = '' OR base_url_norm = '')"
            ),
            {"uid": args.user_id},
        ).fetchall()

    to_update: list[dict] = []
    skipped: list[dict] = []

    for row in rows:
        mapping = row._mapping if hasattr(row, "_mapping") else row
        extra: dict = {}
        raw_extra = mapping["extra_json"] or "{}"
        try:
            parsed = json.loads(raw_extra)
            extra = parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            skipped.append({"id": mapping["id"], "reason": "extra_json 解析失败"})
            continue

        base_url = (mapping["base_url"] or "").strip() or str(extra.get("base_url") or "").strip()
        norm = normalize_base_url(base_url)
        if not base_url and norm == "official":
            # 官方直连：不需要原始地址，但 norm 要落成 official
            base_url = ""
        to_update.append(
            {
                "id": mapping["id"],
                "provider_id": mapping["provider_id"],
                "label": mapping["label"] or "",
                "base_url": base_url,
                "base_url_norm": norm,
                "has_hash": bool(mapping["api_key_hash"]),
            }
        )

    print(f"[backfill] 待补行：{len(to_update)}；跳过：{len(skipped)}（dry-run={not args.apply}）")
    for item in to_update if args.verbose else to_update[:20]:
        print(
            f"  - {item['id'][:8]} provider={item['provider_id']} "
            f"base_url={item['base_url'] or '(official)'} norm={item['base_url_norm']}"
        )
    if not args.verbose and len(to_update) > 20:
        print(f"  ... 其余 {len(to_update) - 20} 条省略（--verbose 查看全部）")
    for item in skipped:
        print(f"  ! {item['id'][:8]} 跳过：{item['reason']}")

    if not args.apply:
        print("[backfill] 预览模式，未写库。加 --apply 执行。")
        return 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = 0
    for item in to_update:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    f"UPDATE {TABLE_NAME} "
                    f"SET base_url = :url, base_url_norm = :norm, updated_at = :now "
                    f"WHERE id = :id AND user_id = :uid AND (base_url = '' OR base_url_norm = '')"
                ),
                {
                    "url": item["base_url"],
                    "norm": item["base_url_norm"],
                    "now": now,
                    "id": item["id"],
                    "uid": args.user_id,
                },
            )
            updated += result.rowcount or 0

    print(f"[backfill] 已更新 {updated} 行（跳过 {len(skipped)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())