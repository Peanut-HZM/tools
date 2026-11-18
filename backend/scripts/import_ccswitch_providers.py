"""从 cc-switch 导入供应商配置到订阅额度账号库

## 为什么需要它

用户已有 cc-switch（`~/.cc-switch/cc-switch.db`），里面存着 19 个供应商配置，
包括：
* `settings_config` 里的推理 Key（`sk-...` / `ANTHROPIC_AUTH_TOKEN`）
* **`meta.usage_script.apiKey` 里的控制面 Key**（OpenDesign 的 `vela_ctrl_...`
  就在这里；推理 Key 查不了账单，控制面 Key 才行）

本脚本从 cc-switch 的只读副本读出这些 Key，映射到本工具的供应商 id，
用 `app/core/security.encrypt_api_key` 加密后写进 `subscription_quota_accounts`。

## 用法

```bash
cd backend
python -m scripts.import_ccswitch_providers --user-id <你的用户ID>
python -m scripts.import_ccswitch_providers --user-id <uid> --dry-run
python -m scripts.import_ccswitch_providers --user-id <uid> --db "D:/path/cc-switch.db"
```

脚本只打印脱敏后的 Key（前 6 位 + 后 4 位），不打印完整凭据。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.subscription_quota.accounts import (  # noqa: E402
    create_account,
    list_accounts,
    update_account,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

#: cc-switch 供应商名/URL 关键词 → 本工具 provider_id
#: 顺序有意义：先匹配更具体的词
PROVIDER_HINTS: tuple[tuple[str, str], ...] = (
    ("opendesign", "opendesign"),
    ("open-design", "opendesign"),
    ("minimax", "minimax"),
    ("kimi", "kimi"),
    ("zhipu", "zhipu"),
    ("bigmodel", "zhipu"),
    ("deepseek", "deepseek"),
    ("siliconflow", "siliconflow"),
    ("openrouter", "openrouter"),
    ("stepfun", "stepfun"),
    ("novita", "novita"),
    ("ollama.com", "ollama_cloud"),
    ("zenmux", "zenmux"),
    ("commandcode", "command_code"),
    ("command code", "command_code"),
    # OpenCode Go 只在地址命中 opencode.ai 的 go 入口时才算（中转站不算）
    ("opencode.ai/zen/go", "opencode_go"),
    ("opencode.ai/inference/go", "opencode_go"),
    ("volces", "volcengine"),
    ("volcengine", "volcengine"),
)

_SENSITIVE_HINTS = ("key", "token", "secret", "auth", "password", "credential")


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:6]}…{value[-4:]}" if len(value) > 12 else "***"


def _match_provider(*texts: str) -> str | None:
    for text in texts:
        if not text:
            continue
        lowered = str(text).lower()
        for hint, provider_id in PROVIDER_HINTS:
            if hint in lowered:
                return provider_id
    return None


def _collect_secrets(obj, prefix: str = "") -> dict[str, str]:
    """递归收集看起来像凭据的字符串字段"""
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for key, val in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, (dict, list)):
                out.update(_collect_secrets(val, path))
            elif isinstance(val, str) and val.strip():
                if any(h in key.lower() for h in _SENSITIVE_HINTS):
                    out[path] = val.strip()
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            out.update(_collect_secrets(item, f"{prefix}[{idx}]"))
    return out


def _collect_urls(obj, out: set[str] | None = None) -> set[str]:
    if out is None:
        out = set()
    if isinstance(obj, dict):
        for val in obj.values():
            _collect_urls(val, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_urls(item, out)
    elif isinstance(obj, str) and obj.startswith("http"):
        out.add(obj)
    return out


def _region_of(text: str) -> str:
    lowered = text.lower()
    if any(h in lowered for h in ("minimax.io", "kimi.ai", "api.z.ai", "siliconflow.com")):
        return "intl"
    return "cn"


def _pick_key(secrets: dict[str, str]) -> str | None:
    """挑一个最像 API Key 的值（优先 apiKey / AUTH_TOKEN / OPENAI_API_KEY）"""
    priority = ("apikey", "auth_token", "openai_api_key", "api_key", "token")
    for hint in priority:
        for path, value in secrets.items():
            if hint in path.lower() and len(value) >= 20:
                return value
    for value in secrets.values():
        if len(value) >= 20:
            return value
    return None


def load_candidates(db_path: Path) -> list[dict]:
    """从 cc-switch.db 读出可映射的供应商（含控制面 Key）"""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM providers ORDER BY sort_index").fetchall()
    conn.close()

    candidates: list[dict] = []
    for row in rows:
        name = row["name"] or ""
        app = row["app_type"] or ""
        try:
            cfg = json.loads(row["settings_config"] or "{}")
        except (json.JSONDecodeError, TypeError):
            cfg = {}
        try:
            meta = json.loads(row["meta"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}

        urls = sorted(_collect_urls(cfg))
        # 注意：不能拿 app_type 参与匹配 —— app_type=opencode 只表示这条配置给
        # OpenCode 用（可能是任意中转站），不代表它是 OpenCode Go 订阅。
        # 只按供应商名 + 实际 base_url 判断。
        provider_id = _match_provider(name, " ".join(urls))
        if provider_id is None:
            continue

        secrets = _collect_secrets(cfg)
        inference_key = _pick_key(secrets)

        # 控制面 Key（OpenDesign 的 vela_ctrl_… 在 usage_script.apiKey）
        usage_script = meta.get("usage_script") if isinstance(meta.get("usage_script"), dict) else {}
        control_key = usage_script.get("apiKey") if isinstance(usage_script.get("apiKey"), str) else None
        control_key = control_key.strip() if control_key else None

        api_key = control_key or inference_key
        if not api_key:
            continue

        candidates.append(
            {
                "provider_id": provider_id,
                "source_app": app,
                "source_name": name,
                "api_key": api_key,
                "from_control_key": bool(control_key),
                "inference_key": inference_key,
                "base_url": urls[0] if urls else None,
                "region": _region_of(" ".join(urls)),
            }
        )
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="从 cc-switch 导入供应商到订阅额度账号库")
    parser.add_argument("--user-id", required=True, help="目标用户 id")
    parser.add_argument(
        "--db",
        default=str(Path(os.environ.get("USERPROFILE") or Path.home()) / ".cc-switch" / "cc-switch.db"),
        help="cc-switch.db 路径",
    )
    parser.add_argument("--dry-run", action="store_true", help="只显示会导入什么，不写库")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"找不到 cc-switch 数据库: {db_path}")
        return 1

    candidates = load_candidates(db_path)
    if not candidates:
        print("cc-switch 里没有可导入的供应商凭据")
        return 1

    # 同一 provider 只保留一条（优先带控制面 Key 的）
    best: dict[str, dict] = {}
    for item in candidates:
        current = best.get(item["provider_id"])
        if current is None or (item["from_control_key"] and not current["from_control_key"]):
            best[item["provider_id"]] = item

    print(f"从 cc-switch 识别到 {len(best)} 个可导入供应商：")
    for pid, item in best.items():
        source = "控制面 Key" if item["from_control_key"] else "推理 Key"
        print(
            f"  {pid:<14} ← [{item['source_app']}] {item['source_name']:<24} "
            f"{source} {_mask(item['api_key'])}"
        )

    if args.dry_run:
        print("\n（--dry-run：没有写库）")
        return 0

    existing = {a.provider_id: a for a in list_accounts(args.user_id)}
    created = updated = 0

    for pid, item in best.items():
        extra: dict = {"region": item["region"], "api_key": item["api_key"]}
        if pid == "opendesign":
            extra["control_key"] = item["api_key"]
            extra["base_url"] = "https://amr-api.open-design.ai"
        elif item["base_url"]:
            extra["base_url"] = item["base_url"]

        label = f"{item['source_name']}（cc-switch 导入）"
        if pid in existing:
            update_account(
                args.user_id, existing[pid].id, label=label, api_key=item["api_key"], extra=extra
            )
            updated += 1
        else:
            create_account(args.user_id, pid, label=label, api_key=item["api_key"], extra=extra)
            created += 1

    print(f"\n完成：新建 {created} 个，更新 {updated} 个")
    print("回到页面「订阅套餐额度」点「全部刷新」即可看到这些供应商。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
