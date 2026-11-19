"""本机数据存储位置核验（需求 1(b)）

打印订阅额度相关的三份数据实际落在哪里：
* 账号表 subscription_quota_accounts
* 切换指针表 subscription_quota_switches
* 表所在的数据库文件

只读，不改任何数据。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, r"D:\CodeProjects\tools\backend")

from sqlalchemy import text

from app.services.subscription_quota import accounts as accounts_mod


def main() -> int:
    print("=== 存储位置判定 ===")
    print(f"QUOTA_STORAGE 环境变量 : {os.environ.get('QUOTA_STORAGE') or '(未设置 → 默认 local)'}")
    print(f"_storage_location()    : {accounts_mod._storage_location()}")
    print(f"_use_local()           : {accounts_mod._use_local()}")

    engine = accounts_mod._get_engine()
    url = engine.url
    print(f"engine.url             : {url.render_as_string(hide_password=True)}")
    if url.get_backend_name() == "sqlite":
        db_path = url.database
        p = Path(db_path)
        print(f"数据库文件             : {db_path}")
        print(f"  文件存在             : {p.exists()}")
        if p.exists():
            print(f"  文件大小             : {p.stat().st_size} bytes")
            print(f"  最后写入             : {p.stat().st_mtime}")

    print()
    print("=== 账号数据 ===")
    accounts_mod.ensure_schema()
    with engine.connect() as conn:
        tables = [
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).fetchall()
        ] if url.get_backend_name() == "sqlite" else []
        rows = conn.execute(
            text(
                "SELECT provider_id, label, enabled FROM subscription_quota_accounts "
                "ORDER BY provider_id"
            )
        ).fetchall()
        switch_rows = []
        if "subscription_quota_switches" in tables or url.get_backend_name() != "sqlite":
            try:
                switch_rows = conn.execute(
                    text(
                        "SELECT agent, provider_id, switched_at "
                        "FROM subscription_quota_switches ORDER BY agent"
                    )
                ).fetchall()
            except Exception as exc:  # 表尚未创建
                print(f"（切换指针表尚未创建：{exc.__class__.__name__}）")

    print(f"账号数: {len(rows)}")
    for r in rows:
        print(f"  {r[0]:<18} {r[1]:<36} enabled={r[2]}")
    print(f"切换指针数: {len(switch_rows)}")
    for r in switch_rows:
        print(f"  agent={r[0]:<10} provider={r[1] or '(默认)':<20} at={r[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
