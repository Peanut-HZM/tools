"""把本机 CLI 凭据一次性导入订阅额度账号库

## 为什么需要这个脚本

订阅额度后端通常以 Windows 服务（`LocalSystem`）运行，而 `LocalSystem`
**读不到当前用户的 Credential Manager / Keychain**。ZCode 的
`oauth:bigmodel:access_token` 就用用户的 Credential Manager 里的 AES key 加密，
所以服务进程无法解密。

这个脚本在**你自己的用户会话**里运行（能读凭据），把解密后的 Key 用
`app/core/security.encrypt_api_key` 加密后写进 `subscription_quota_accounts`。
之后服务进程从数据库读到的是已加密的值，用服务自己的 app_secret 就能解开——
不需要以用户身份运行服务。

## 用法

```bash
cd backend
python -m scripts.import_local_quota_keys --user-id <你的用户ID>
python -m scripts.import_local_quota_keys --user-id <你的用户ID> --list-users
```

脚本只做**只读**凭据读取 + 本地加密入库，不打印任何明文 Key。
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.subscription_quota.accounts import (  # noqa: E402
    create_account,
    get_account,
    list_accounts,
    update_account,
)
from app.services.subscription_quota.local_credentials import (  # noqa: E402
    discover_local_accounts,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("import-local-quota-keys")


def _user_ids() -> list[str]:
    """列出所有已有订阅账号的用户 id（方便确认 --user-id 该填什么）"""
    from sqlalchemy import text

    from app.models.base import engine

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT user_id FROM subscription_quota_accounts ORDER BY user_id")
        ).fetchall()
    return [row[0] for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="导入本机 CLI 凭据到订阅额度账号库")
    parser.add_argument("--user-id", help="目标用户 id")
    parser.add_argument("--list-users", action="store_true", help="列出已有订阅账号的用户 id")
    parser.add_argument(
        "--dry-run", action="store_true", help="只显示会导入哪些供应商，不写库"
    )
    args = parser.parse_args()

    if args.list_users:
        ids = _user_ids()
        if not ids:
            print("数据库里还没有任何订阅额度账号；请先在页面上添加一个供应商，再运行本脚本")
        for uid in ids:
            print(uid)
        return 0

    if not args.user_id:
        parser.error("需要 --user-id（或先用 --list-users 查看）")

    discovered = discover_local_accounts()
    if not discovered:
        print("没有发现可用的本机凭据（Kimi Code / ZCode 登录都没检测到）")
        return 1

    existing = {a.provider_id: a for a in list_accounts(args.user_id)}

    for account in discovered:
        provider = account.provider_id
        label = account.label
        api_key = account.api_key or account.extra.get("api_key") or account.extra.get("control_key")
        if not api_key:
            continue

        print(f"→ {provider}（{label}）密钥已就绪，长度 {len(api_key)}")

        if args.dry_run:
            continue

        extra = {k: v for k, v in (account.extra or {}).items() if k != "api_key"}
        extra["api_key"] = api_key
        if provider == "opendesign":
            extra["control_key"] = api_key

        if provider in existing:
            update_account(
                args.user_id,
                existing[provider].id,
                label=label,
                api_key=api_key,
                extra=extra,
            )
            print(f"  已更新现有账号 {existing[provider].id[:8]}…")
        else:
            created = create_account(
                args.user_id, provider, label=label, api_key=api_key, extra=extra
            )
            print(f"  已新建账号 {created.id[:8]}…")

    if args.dry_run:
        print("\n（--dry-run：没有写库）")
    else:
        print("\n完成。回到页面的「订阅套餐额度」点「全部刷新」即可看到这些供应商。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
