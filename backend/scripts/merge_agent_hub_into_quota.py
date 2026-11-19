"""把 agent-hub 的存量数据迁移到合并后的 subscription_quota_accounts

## 为什么

两个工具合并后，数据统一存 `subscription_quota_accounts`（AES 加密 Key）。
agent-hub 的 `agent_hub_providers` / `agent_hub_subscriptions` 里有用户已配置的
数据，必须完整搬过来，**不能丢**。

## 安全约定

* **默认 dry-run**：只打印将要做什么，不写库；加 `--apply` 才执行
* **幂等**：按 `(user_id, provider_id, label)` 判定已存在则跳过
* **原表不删**：迁移后 `agent_hub_*` 表原样保留，作为回滚保障
* **不打印任何密钥**：只输出供应商名与掩码

## 用法

```bash
cd backend
python -m scripts.merge_agent_hub_into_quota --list-users
python -m scripts.merge_agent_hub_into_quota --user-id <uid>            # dry-run
python -m scripts.merge_agent_hub_into_quota --user-id <uid> --apply    # 真正写入
```
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.models.base import engine  # noqa: E402
from app.services.subscription_quota.accounts import (  # noqa: E402
    create_account,
    get_account,
    list_accounts,
    update_account,
)
from app.services.subscription_quota.registry import get_spec  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

#: agent-hub 的 kind → 本工具的 provider_id（官方订阅两边命名不同）
_KIND_ALIAS = {
    "claude_official": "claude",
    "codex_official": "codex",
    "gemini_official": "gemini",
}


def _resolve_provider_id(kind: str) -> str:
    return _KIND_ALIAS.get(kind, kind)


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}…{value[-4:]}" if len(value) > 10 else "***"


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        text("SELECT to_regclass(:n) IS NOT NULL"), {"n": f"public.{name}"}
    ).scalar()
    return bool(row)


def _load_agent_hub_rows() -> tuple[list[dict], list[dict]]:
    """读出 agent_hub 的供应商与订阅（只读）"""
    with engine.connect() as conn:
        if not _table_exists(conn, "agent_hub_providers"):
            return [], []

        providers = [
            dict(row._mapping)
            for row in conn.execute(text("SELECT * FROM agent_hub_providers")).fetchall()
        ]
        subscriptions = (
            [
                dict(row._mapping)
                for row in conn.execute(
                    text("SELECT * FROM agent_hub_subscriptions")
                ).fetchall()
            ]
            if _table_exists(conn, "agent_hub_subscriptions")
            else []
        )
    return providers, subscriptions


def _list_user_ids() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT DISTINCT user_id FROM subscription_quota_accounts "
                "WHERE user_id <> '' ORDER BY user_id"
            )
        ).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="把 agent-hub 存量数据迁移到合并后的账号表")
    parser.add_argument("--user-id", help="目标用户 id")
    parser.add_argument("--list-users", action="store_true", help="列出已有账号的用户 id")
    parser.add_argument("--apply", action="store_true", help="真正写入（默认 dry-run）")
    args = parser.parse_args()

    if args.list_users:
        ids = _list_user_ids()
        if not ids:
            print("账号表里还没有任何用户；请先在页面添加一个供应商")
        for uid in ids:
            print(uid)
        return 0

    if not args.user_id:
        parser.error("需要 --user-id（或先用 --list-users 查看）")

    providers, subscriptions = _load_agent_hub_rows()
    if not providers and not subscriptions:
        print("agent_hub 表里没有数据（或表不存在），无需迁移")
        return 0

    print(f"agent_hub 存量：{len(providers)} 个供应商 / {len(subscriptions)} 个订阅")
    print(f"目标用户：{args.user_id}")
    print(f"模式：{'写入' if args.apply else 'dry-run（不写库）'}\n")

    existing = {a.provider_id: a for a in list_accounts(args.user_id)}
    # 同一 provider 可能有多个账号（多账号 failover），按 (provider_id, label) 精确匹配，
    # 避免把第二个同 kind 的订阅覆盖掉第一个
    existing_by_label = {(a.provider_id, a.label): a for a in list_accounts(args.user_id)}
    created = updated = skipped = 0

    # ---- 1) 供应商 → 账号 ----
    for provider in providers:
        kind = str(provider.get("kind") or "")
        provider_id = _resolve_provider_id(kind)
        # agent_hub 的 kind 与本工具 provider_id 对齐（官方订阅用别名表映射）
        spec = get_spec(provider_id)
        if spec is None:
            print(f"  跳过（未知 kind）: {provider.get('name')} / {kind}")
            skipped += 1
            continue

        name = str(provider.get("name") or "")
        api_key = str(provider.get("api_key") or "")
        usage_key = str(provider.get("usage_api_key") or "")
        base_url = str(provider.get("base_url") or "")
        usage_base = str(provider.get("usage_base_url") or "")

        extra: dict = {}
        if base_url:
            extra["base_url"] = base_url
        if usage_base:
            extra["usage_base_url"] = usage_base
        if usage_key:
            extra["control_key"] = usage_key
        if api_key:
            extra["api_key"] = api_key

        try:
            notes = json.loads(provider.get("extra_json") or "{}")
        except json.JSONDecodeError:
            notes = {}

        print(
            f"  供应商 {name:<28} kind={kind:<16} key={_mask(api_key)} "
            f"usage_key={_mask(usage_key)}"
        )

        if not args.apply:
            created += 1
            continue

        # 用 usage_key 优先（额度查询通常需要控制面 Key）
        key_for_query = usage_key or api_key
        # 供应商：按 (provider_id, label) 匹配
        match = existing_by_label.get((provider_id, name)) or existing.get(provider_id)
        if match is not None:
            update_account(
                args.user_id,
                match.id,
                label=name,
                api_key=key_for_query or None,
                extra=extra,
                category=str(provider.get("category") or "official"),
                app=str(provider.get("app") or ""),
                notes=str(provider.get("notes") or ""),
                website_url=str(provider.get("website_url") or ""),
                enabled=bool(provider.get("enabled", 1)),
            )
            updated += 1
        else:
            create_account(
                args.user_id,
                provider_id,
                label=name,
                api_key=key_for_query or None,
                extra={**extra, **notes},
                category=str(provider.get("category") or "official"),
                app=str(provider.get("app") or ""),
                notes=str(provider.get("notes") or ""),
                website_url=str(provider.get("website_url") or ""),
            )
            created += 1

    # ---- 2) 订阅 → 账号（manual 模式保留总额/已用）----
    for sub in subscriptions:
        kind = str(sub.get("kind") or "")
        provider_id = _resolve_provider_id(kind)
        spec = get_spec(provider_id)
        if spec is None:
            print(f"  跳过（未知 kind）: {sub.get('name')} / {kind}")
            skipped += 1
            continue

        name = str(sub.get("name") or "")
        credential = str(sub.get("credential") or "")
        # 官方订阅（claude/codex/gemini）靠本机登录自动发现，不需要账号行；
        # 没有凭据的官方订阅直接跳过（否则会多出一张「未配置」的卡片）
        if provider_id in ("claude", "codex", "gemini") and not credential:
            print(f"  跳过（官方订阅走本机登录自动发现）: {name}")
            skipped += 1
            continue
        print(
            f"  订阅   {name:<28} kind={kind:<16} "
            f"total={sub.get('total_quota')} used={sub.get('used_quota')} "
            f"cred={_mask(credential)}"
        )

        if not args.apply:
            created += 1
            continue

        extra: dict = {}
        base_url = str(sub.get("base_url") or "")
        if base_url:
            extra["base_url"] = base_url
        if credential:
            extra["api_key"] = credential

        # 订阅：按 (provider_id, label) 匹配；同 kind 的多个订阅各自保留
        match = existing_by_label.get((provider_id, name)) or (
            existing.get(provider_id) if kind == "manual" else None
        )
        if match is not None:
            update_account(
                args.user_id,
                match.id,
                label=name,
                api_key=credential or None,
                extra=extra,
                manual_total=float(sub.get("total_quota") or 0),
                manual_used=float(sub.get("used_quota") or 0),
                quota_unit=str(sub.get("quota_unit") or "credits"),
                window_type=str(sub.get("window_type") or "none"),
                window_reset_at=str(sub.get("window_reset_at") or ""),
                enabled=bool(sub.get("enabled", 1)),
            )
            updated += 1
        else:
            create_account(
                args.user_id,
                provider_id,
                label=name,
                api_key=credential or None,
                extra=extra,
                category="manual" if kind == "manual" else "official",
                app=str(sub.get("agent_app") or ""),
                manual_total=float(sub.get("total_quota") or 0),
                manual_used=float(sub.get("used_quota") or 0),
                quota_unit=str(sub.get("quota_unit") or "credits"),
                window_type=str(sub.get("window_type") or "none"),
                window_reset_at=str(sub.get("window_reset_at") or ""),
            )
            created += 1

    print()
    if args.apply:
        print(f"完成：新建 {created}，更新 {updated}，跳过 {skipped}")
        print("agent_hub_* 原表已保留，可随时回滚。")
    else:
        print(f"dry-run：将新建 {created}，跳过 {skipped}")
        print("确认无误后加 --apply 执行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
