"""把订阅额度账号从远程主库迁移到本机 SQLite

## 为什么

订阅额度数据（供应商、API Key、切换指针）是**每台设备各不相同**的本机状态：
同一账号在办公机和家里电脑登录的 CLI、配置的供应商、看到的余额都不一样。
存到远程主库会让多台设备互相覆盖，也把本机凭据上传到了服务器。

2026-11 起默认改存本机（``~/.toolbox/toolbox.db``），本脚本用于把**已经在
远程主库里**的历史数据搬到本机，避免用户重新录入。

## 安全约定

* **默认 dry-run**：只打印将要迁移什么，不写任何库
* **幂等**：本机已有同 (user_id, provider_id, label) 的账号则跳过，不覆盖
* **两把密钥不同**：远程密文用服务器主密钥加密，本机库用本机文件密钥。
  必须用远程密钥解密 → 再用本机密钥重新加密，禁止直接拷贝密文。
* **原表不删**：迁移后远程表原样保留，作为回滚保障
* **不打印任何密钥**：只输出供应商名与掩码

## 用法

```bash
cd backend
python -m scripts.migrate_quota_to_local --list-users
python -m scripts.migrate_quota_to_local --user-id <uid>            # dry-run
python -m scripts.migrate_quota_to_local --user-id <uid> --apply    # 真正写入
```
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.models.base import engine as remote_engine  # noqa: E402
from app.services.subscription_quota import accounts as accounts_mod  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

TABLE_NAME = accounts_mod.TABLE_NAME


def _mask(key: str | None) -> str:
    if not key:
        return "(无)"
    if len(key) <= 12:
        return "***"
    return f"{key[:6]}…{key[-4:]}"


def _list_user_ids() -> list[str]:
    with remote_engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT DISTINCT user_id FROM {TABLE_NAME} "
                "WHERE user_id <> '' ORDER BY user_id"
            )
        ).fetchall()
    return [r[0] for r in rows]


def _read_remote_rows(user_id: str) -> list[dict]:
    """读取远程库里的原始行（含密文列，稍后用远程密钥解密）"""
    with remote_engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM {TABLE_NAME} WHERE user_id = :uid ORDER BY sort_order, created_at"),
            {"uid": user_id},
        ).fetchall()
    result = []
    for row in rows:
        m = row._mapping if hasattr(row, "_mapping") else row
        result.append(dict(m))
    return result


def _decrypt_remote(cipher: str | None) -> str | None:
    """用远程密钥解密（远程密文由服务器主密钥加密）"""
    if not cipher:
        return None
    from app.core.security import decrypt_api_key

    return decrypt_api_key(cipher)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把订阅额度账号从远程主库迁移到本机 SQLite"
    )
    parser.add_argument("--user-id", help="目标用户 id")
    parser.add_argument("--list-users", action="store_true", help="列出远程库里有账号的用户 id")
    parser.add_argument("--apply", action="store_true", help="真正写入本机（默认 dry-run）")
    args = parser.parse_args()

    if args.list_users:
        ids = _list_user_ids()
        if not ids:
            print("远程主库里还没有任何订阅额度账号")
        for uid in ids:
            print(uid)
        return 0

    if not args.user_id:
        parser.error("需要 --user-id（或先用 --list-users 查看）")

    remote_rows = _read_remote_rows(args.user_id)
    if not remote_rows:
        print(f"远程主库里没有用户 {args.user_id} 的订阅额度账号，无需迁移")
        return 0

    print(f"远程账号数：{len(remote_rows)}")
    print(f"目标用户  ：{args.user_id}")
    print(f"目标位置  ：{accounts_mod._get_engine().url}")
    print(f"模式      ：{'写入' if args.apply else 'dry-run（不写库）'}\n")

    # 本机已有账号：按 (provider_id, label) 精确匹配，避免覆盖用户在本机手工加的账号
    local_existing = {
        (a.provider_id, a.label): a for a in accounts_mod.list_accounts(args.user_id)
    }

    created = skipped = failed = 0
    for row in remote_rows:
        provider_id = str(row.get("provider_id") or "")
        label = str(row.get("label") or "")

        # 只为打印掩码而解密（明文不落盘、不进日志，只在内存里转瞬即弃）
        try:
            masked = _mask(_decrypt_remote(row.get("api_key_enc")))
        except Exception:
            masked = "(解密失败)"

        if (provider_id, label) in local_existing:
            print(f"  跳过（本机已存在）: {provider_id:<16} {label}")
            skipped += 1
            continue

        print(f"  迁移: {provider_id:<16} {label:<32} key={masked}")

        if not args.apply:
            created += 1
            continue

        # 远程密文 → 明文（内存） → 本机密钥重新加密（create_account 内部完成）
        try:
            plain_key = _decrypt_remote(row.get("api_key_enc"))
        except Exception as exc:
            print(f"    !! 解密失败，跳过该条（不写入错误数据）: {exc}")
            failed += 1
            continue

        extra = {}
        raw_extra = row.get("extra_json")
        if raw_extra:
            import json

            try:
                extra = json.loads(raw_extra)
            except (json.JSONDecodeError, TypeError):
                extra = {}

        try:
            accounts_mod.create_account(
                args.user_id,
                provider_id,
                label=label,
                api_key=plain_key,
                extra=extra if isinstance(extra, dict) else {},
                category=str(row.get("category") or "official"),
                app=str(row.get("app") or ""),
                notes=str(row.get("notes") or ""),
                website_url=str(row.get("website_url") or ""),
                manual_total=float(row.get("manual_total") or 0),
                manual_used=float(row.get("manual_used") or 0),
                quota_unit=str(row.get("quota_unit") or "credits"),
                window_type=str(row.get("window_type") or "none"),
                window_reset_at=str(row.get("window_reset_at") or ""),
            )
            created += 1
        except Exception as exc:
            print(f"    !! 写入本机失败: {exc}")
            failed += 1

    print(
        f"\n结果：新建 {created} / 跳过 {skipped} / 失败 {failed}"
        + ("（dry-run，未写库）" if not args.apply else "")
    )
    if not args.apply and created:
        print("确认无误后加 --apply 执行写入")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
