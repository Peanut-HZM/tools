"""下线「订阅套餐额度」工具（软删除，可回滚）

## 为什么

「订阅套餐额度」(`subscription-quota`) 的全部能力已并入「Agent 订阅中心」
(`agent-hub`)：

* 24 家供应商注册表、AES 加密 Key、ZCode 凭据解密、cc-switch 导入
* 12 个额度查询器 + 手动额度
* 本地网关、Agent 配置切换

保留两个入口会让用户以为这是两个不同的工具。因此下线旧入口。

## 为什么用软删除而不是物理删除

* 可回滚：`--undo` 一条命令恢复
* 不破坏历史：`usage_count`、管理员在后台改过的标题/描述都保留
* 安全：不动任何业务数据（账号、订阅、切换指针都不受影响）

## 用法

```bash
cd backend
python -m scripts.retire_subscription_quota_tool              # dry-run，只看会改什么
python -m scripts.retire_subscription_quota_tool --apply      # 真正下线
python -m scripts.retire_subscription_quota_tool --apply --undo   # 恢复
```
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.models.base import engine  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

#: 下线的工具 id → 替代入口
RETIRED_TOOLS: dict[str, str] = {
    "subscription-quota": "agent-hub",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="下线「订阅套餐额度」工具（软删除，可回滚）")
    parser.add_argument("--apply", action="store_true", help="真正执行（默认 dry-run）")
    parser.add_argument("--undo", action="store_true", help="恢复被下线的工具")
    args = parser.parse_args()

    mode = "恢复" if args.undo else "下线"
    print(f"模式：{mode} / {'写入' if args.apply else 'dry-run（不写库）'}\n")

    changed = 0
    with engine.begin() as conn:
        for tool_id, replacement in RETIRED_TOOLS.items():
            row = conn.execute(
                text("SELECT id, title, deleted FROM tools WHERE id = :tid"), {"tid": tool_id}
            ).fetchone()
            if row is None:
                print(f"  {tool_id}: 库里没有这条工具（无需处理）")
                continue

            _, title, deleted = row
            target_deleted = not args.undo
            if bool(deleted) == target_deleted:
                print(f"  {tool_id}（{title}）: 已是目标状态，跳过")
                continue

            print(
                f"  {tool_id}（{title}）: deleted {bool(deleted)} → {target_deleted}"
                f"（入口改为 {replacement}）"
            )
            if args.apply:
                conn.execute(
                    text("UPDATE tools SET deleted = :d WHERE id = :tid"),
                    {"d": target_deleted, "tid": tool_id},
                )
            changed += 1

        # 确认替代入口存在，避免下线后无处可去
        for replacement in set(RETIRED_TOOLS.values()):
            exists = conn.execute(
                text("SELECT 1 FROM tools WHERE id = :tid AND deleted = FALSE"),
                {"tid": replacement},
            ).scalar()
            if not exists:
                print(f"  ⚠ 替代入口 {replacement} 不存在或已被删除，请先修复再执行")

    print()
    if args.apply:
        print(f"完成：{changed} 条已{mode}")
    else:
        print(f"dry-run：将{mode} {changed} 条，确认无误后加 --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
