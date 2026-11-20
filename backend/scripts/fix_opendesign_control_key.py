"""修复 OpenDesign 账号里存的 Key：推理 Key → 控制面 Key

## 背景

OpenDesign 的账单接口只认 AMR **控制面 Key**（`vela_ctrl_…`），而
ZCode / magpie / OpenCode 的推理配置里存的是**运行时推理 Key**
（`sk-amr-ew__…`）。早期同步把推理 Key 写进了 `control_key`，导致：
卡片显示「登录已过期 / 额度查询失败」。

## 本脚本做什么

1. 找出所有 `provider_id='opendesign'` 的账号
2. 若 `extra.control_key` 不是控制面形态（不以 `vela_ctrl_` 开头）
3. 从本机 cc-switch 库读出真正的控制面 Key（`providers.meta.usage_script.apiKey`）
4. 写回 `extra.control_key`（**只改这一个字段**，label / 手工额度 / 启停都不动）

## 安全

* 默认 dry-run，`--apply` 才写库
* 打印一律脱敏（只显示前缀 + 末 4 位）
* 找不到控制面 Key 时**跳过并说明**，不编造

用法：

```bash
cd backend
python -m scripts.fix_opendesign_control_key                      # dry-run
python -m scripts.fix_opendesign_control_key --apply              # 写入
python -m scripts.fix_opendesign_control_key --user-id <uid> --apply
```
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.subscription_quota.accounts import (  # noqa: E402
    list_accounts,
    update_account,
)
from app.services.subscription_quota.opendesign_key import (  # noqa: E402
    discover_control_keys,
    is_control_key,
    looks_like_runtime_key,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")


def _mask(value: str) -> str:
    if not value:
        return "(空)"
    return f"{value[:12]}…{value[-4:]} (len={len(value)})" if len(value) > 20 else "***"


def main() -> int:
    parser = argparse.ArgumentParser(description="修复 OpenDesign 账号的控制面 Key")
    parser.add_argument("--user-id", help="只处理指定用户（默认处理所有用户）")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认 dry-run）")
    args = parser.parse_args()

    print(f"模式：{'写入' if args.apply else 'dry-run（不写库）'}\n")

    control_keys = discover_control_keys()
    if not control_keys:
        print("✗ 本机 cc-switch 库里没有 OpenDesign 控制面 Key（vela_ctrl_…）")
        print("  请先在 cc-switch 里为 OpenDesign 配置用量脚本，或手动填写 controlKey。")
        return 1
    print(f"从 cc-switch 发现 {len(control_keys)} 个控制面 Key：")
    for key in control_keys:
        print(f"  {_mask(key)}")
    print()

    # 账号表按用户隔离，这里先枚举已知用户
    from sqlalchemy import text

    from app.services.subscription_quota.accounts import _get_engine

    with _get_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT DISTINCT user_id FROM subscription_quota_accounts "
                "WHERE provider_id = 'opendesign' AND user_id <> ''"
            )
        ).fetchall()
    user_ids = [r[0] for r in rows]
    if args.user_id:
        user_ids = [u for u in user_ids if u == args.user_id]

    if not user_ids:
        print("没有找到任何 OpenDesign 账号")
        return 0

    fixed = skipped = 0
    for uid in user_ids:
        accounts = [a for a in list_accounts(uid) if a.provider_id == "opendesign"]
        for account in accounts:
            current = str(account.extra.get("control_key") or "")
            api_key = account.api_key or ""
            if is_control_key(current):
                print(f"  [{uid[:8]}] {account.label}: 已是控制面 Key，跳过")
                skipped += 1
                continue

            shape = "推理 Key" if looks_like_runtime_key(current or api_key) else "非控制面形态"
            print(
                f"  [{uid[:8]}] {account.label}: control_key={_mask(current)} "
                f"（{shape}）→ 将改为控制面 Key"
            )

            if not args.apply:
                fixed += 1
                continue

            extra = dict(account.extra)
            extra["control_key"] = control_keys[0]
            update_account(uid, account.id, extra=extra)
            fixed += 1

    print()
    if args.apply:
        print(f"完成：修复 {fixed} 个，跳过 {skipped} 个")
    else:
        print(f"dry-run：将修复 {fixed} 个，跳过 {skipped} 个；确认后加 --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
