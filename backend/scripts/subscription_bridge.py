#!/usr/bin/env python3
"""订阅中心 ↔ 本机 CC Switch / Magpie 同步桥（在**本机**执行）

设计依据：``specs/agent-subscription-bridge-design.md`` §7 / §8

为什么需要它：网页（云端）读不到本机的 ``~/.cc-switch``、``~/.config/magpie``，
只有本机进程能读写这两个应用；因此「双向同步 + 按 URL+Key 去重」由本脚本完成。

用法::

    # 1) 建一把带作用域的设备 Token（网页「同步到本机」页可一键生成，或走接口）
    #    scope 需要 subscription:read,subscription:export
    set TOOLS_DEVICE_TOKEN=pat_xxx

    # 2) 看差集（不写任何东西）
    python -m scripts.subscription_bridge plan --server https://tools.peanuthzm.com.cn

    # 3) 云端 → 本机
    python -m scripts.subscription_bridge push --server https://... [--target both|ccswitch|magpie] [--dry-run]

    # 4) 本机 → 云端
    python -m scripts.subscription_bridge pull --server https://...

退出码：0 成功；1 参数/网络错误；2 部分失败（明细见输出）。
安全：任何输出只出现掩码 Key；订阅 Key 只走 HTTPS 响应体，不进命令行参数。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.subscription_quota.dedupe import mask_key, sha256_hex  # noqa: E402
from app.services.subscription_quota.link_builder import (  # noqa: E402
    build_ccswitch_link,
    build_magpie_link,
)
from app.services.subscription_quota.magpie_sync import (  # noqa: E402
    find_magpie_binary,
    providers_json_path,
)
from app.services.subscription_quota.url_norm import normalize_base_url  # noqa: E402

TOKEN_ENV = "TOOLS_DEVICE_TOKEN"
TIMEOUT = 30
RETRIES = 2


# ---------------------------------------------------------------- HTTP（云端）


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _request(method: str, url: str, token: str, payload: Optional[dict] = None) -> dict:
    """带超时与重试的 JSON 请求（失败抛 RuntimeError）"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    last_error: Optional[Exception] = None
    for attempt in range(RETRIES + 1):
        req = urllib.request.Request(url, data=data, method=method)
        for key, value in _headers(token).items():
            req.add_header(key, value)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "ignore")[:300]
            if exc.code in (401, 403):
                raise RuntimeError(f"认证失败（HTTP {exc.code}）：{body}") from exc
            last_error = RuntimeError(f"HTTP {exc.code}：{body}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        if attempt < RETRIES:
            time.sleep(1 + 2 * attempt)
    raise RuntimeError(f"请求失败 {method} {url}：{last_error}")


def fetch_cloud_accounts(server: str, token: str) -> list[dict]:
    base = server.rstrip("/") + "/api/subscription-quota"
    payload = _request("GET", f"{base}/export/accounts", token)
    return payload.get("items", [])


def push_items_to_cloud(server: str, token: str, items: list[dict], dry_run: bool) -> dict:
    base = server.rstrip("/") + "/api/subscription-quota"
    return _request(
        "POST", f"{base}/subscriptions/push-items", token, {"dry_run": dry_run, "items": items}
    )


# ---------------------------------------------------------------- 本机状态（只读）


def local_magpie_accounts() -> list[dict]:
    """读 ``~/.config/magpie/providers.json``（providers[]）"""
    path = providers_json_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[bridge] 读取 magpie providers.json 失败: {exc}", file=sys.stderr)
        return []
    providers = raw.get("providers") if isinstance(raw, dict) else raw
    out: list[dict] = []
    for item in providers or []:
        if not isinstance(item, dict):
            continue
        base_url = item.get("anthropic") or item.get("chat") or item.get("responses") or ""
        out.append(
            {
                "provider_id": item.get("preset") or item.get("id") or "custom",
                "label": item.get("name") or item.get("id") or "",
                "base_url": base_url,
                "api_key": item.get("key") or "",
            }
        )
    return out


def local_ccswitch_accounts() -> list[dict]:
    """读 cc-switch sqlite（复用 scripts.import_ccswitch_providers.load_candidates）"""
    from app.services.subscription_quota.opendesign_key import _ccswitch_db_path
    from scripts.import_ccswitch_providers import load_candidates

    db_path = Path(_ccswitch_db_path())
    if not db_path.exists():
        return []
    try:
        candidates = load_candidates(db_path)
    except Exception as exc:  # 库被占用/结构变化 → 如实报告，不静默成功
        print(f"[bridge] 读取 cc-switch 库失败: {exc}", file=sys.stderr)
        return []
    return [
        {
            "provider_id": item.get("provider_id") or "custom",
            "label": item.get("source_name") or "",
            "base_url": item.get("base_url") or "",
            "api_key": item.get("api_key") or "",
        }
        for item in candidates
    ]


def _local_index() -> dict[tuple, dict]:
    """本机现存订阅索引：去重键 → 记录"""
    index: dict[tuple, dict] = {}
    for item in local_ccswitch_accounts() + local_magpie_accounts():
        key = item["api_key"]
        if not key:
            continue
        index[(normalize_base_url(item["base_url"]), sha256_hex(key))] = item
    return index


# ---------------------------------------------------------------- 写入本机


def _magpie_binary() -> Optional[str]:
    binary = find_magpie_binary()
    if binary:
        return binary
    for candidate in (r"D:\Program Files\magpie\magpie.exe", "/usr/local/bin/magpie"):
        if Path(candidate).exists():
            return candidate
    return None


def write_magpie(item: dict) -> tuple[bool, str]:
    """用官方 CLI 静默写入（``magpie import -y``；同 id 会覆盖，因此先查重）"""
    binary = _magpie_binary()
    if not binary:
        return False, "未找到 magpie 可执行文件"
    result = build_magpie_link(
        provider_id=item["providerId"],
        label=item["label"],
        base_url=item["baseUrl"],
        api_key=item["apiKey"],
        extra={"region": item.get("region") or ""},
    )
    if not result.url:
        return False, "；".join(result.warnings) or "无法生成 magpie 链接"
    try:
        proc = subprocess.run(
            [binary, "import", "-y", result.url],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"调用 magpie 失败: {exc}"
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "").strip()[:200]
    return True, "已写入 magpie"


def write_ccswitch(item: dict) -> tuple[bool, str]:
    """用系统协议打开 CC Switch 导入确认框（官方唯一写入通道）"""
    result = build_ccswitch_link(
        provider_id=item["providerId"],
        label=item["label"],
        base_url=item["baseUrl"],
        api_key=item["apiKey"],
        extra={},
    )
    if not result.url:
        return False, "；".join(result.warnings) or "无法生成 ccswitch 链接"
    try:
        if os.name == "nt":
            os.startfile(result.url)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", result.url], check=False, timeout=30)
        else:
            subprocess.run(["xdg-open", result.url], check=False, timeout=30)
    except OSError as exc:
        return False, f"打开 CC Switch 失败: {exc}"
    return True, "已唤起 CC Switch（请在弹窗里点确认）"


# ---------------------------------------------------------------- 差集


def compute_plan(cloud_items: list[dict], local_index: dict[tuple, dict]) -> list[dict]:
    """云端条目 vs 本机现状：返回每条带 action=create|skip"""
    plan: list[dict] = []
    for item in cloud_items:
        key = (normalize_base_url(item.get("baseUrl") or ""), sha256_hex(item.get("apiKey") or ""))
        exists = key in local_index
        plan.append(
            {
                **item,
                "action": "skip" if exists else "create",
                "reason": "duplicate" if exists else None,
                "dedupeKey": key,
            }
        )
    return plan


def _print_plan(plan: list[dict]) -> None:
    creates = [item for item in plan if item["action"] == "create"]
    skips = [item for item in plan if item["action"] == "skip"]
    print(f"[bridge] 云端 {len(plan)} 条：待新增 {len(creates)}，本机已存在（跳过）{len(skips)}")
    for item in plan:
        mark = "+" if item["action"] == "create" else "="
        print(f"  {mark} {item['label'] or item['providerId']} [{mask_key(item.get('apiKey') or '')}]")


# ---------------------------------------------------------------- 子命令


def cmd_plan(args) -> int:
    plan = compute_plan(fetch_cloud_accounts(args.server, args.token), _local_index())
    if args.json:
        print(json.dumps([{k: v for k, v in item.items() if k != "apiKey"} for item in plan], ensure_ascii=False))
    else:
        _print_plan(plan)
    return 0


def cmd_push(args) -> int:
    plan = compute_plan(fetch_cloud_accounts(args.server, args.token), _local_index())
    _print_plan(plan)
    pending = [item for item in plan if item["action"] == "create"]

    if args.dry_run:
        print("[bridge] dry-run：未写入本机")
        return 0

    targets = ["magpie", "ccswitch"] if args.target == "both" else [args.target]
    failures = 0
    for item in pending:
        for target in targets:
            ok, message = write_magpie(item) if target == "magpie" else write_ccswitch(item)
            tag = "OK " if ok else "FAIL"
            print(f"  [{tag}] {target}: {item['label'] or item['providerId']} — {message}")
            if not ok:
                failures += 1
            if ok and target == "ccswitch":
                # 让 CC Switch 有时间弹确认框，避免连点被合并
                time.sleep(1.5)
    if failures:
        print(f"[bridge] 完成，但有 {failures} 个目标失败（见上）")
        return 2
    print("[bridge] 完成")
    return 0


def cmd_pull(args) -> int:
    """本机 → 云端：扫描本机订阅并上传（去重由服务端统一裁决）"""
    from app.services.subscription_quota.agent_subscription_scan import scan_local_subscriptions

    report = scan_local_subscriptions()
    items: list[dict] = []
    seen: set[tuple] = set()
    for item in report.items:
        key = item.api_key.strip()
        if not key:
            continue
        dedupe = (normalize_base_url(item.base_url), sha256_hex(key))
        if dedupe in seen:
            continue
        seen.add(dedupe)
        items.append(
            {
                "provider_id": item.provider_id,
                "provider_name": item.provider_name,
                "base_url": item.base_url,
                "region": item.region,
                "channel": item.channel,
                "api_key": key,
                "source_agents": item.source_agents,
            }
        )

    # magpie 里的供应商也一并上传（扫描器不覆盖 magpie）
    for item in local_magpie_accounts():
        if not item["api_key"]:
            continue
        dedupe = (normalize_base_url(item["base_url"]), sha256_hex(item["api_key"]))
        if dedupe in seen:
            continue
        seen.add(dedupe)
        items.append(
            {
                "provider_id": item["provider_id"],
                "provider_name": item["label"] or item["provider_id"],
                "base_url": item["base_url"],
                "region": "",
                "channel": "",
                "api_key": item["api_key"],
                "source_agents": ["magpie"],
            }
        )

    print(f"[bridge] 本机扫描到 {len(items)} 条待上传（目标：{args.server}）")
    if args.dry_run:
        for item in items:
            print(f"  ? {item['provider_name']} [{mask_key(item['api_key'])}]")
        print("[bridge] dry-run：未上传")
        return 0

    result = push_items_to_cloud(args.server, args.token, items, dry_run=False)
    print(
        f"[bridge] 云端裁决：新建 {result.get('created', 0)}，跳过 {result.get('skipped', 0)}，"
        f"回填 hash {result.get('backfilled', 0)}"
    )
    for item in result.get("items", []):
        mark = "+" if item.get("action") == "create" else "="
        print(f"  {mark} {item.get('label') or item.get('providerName')} [{item.get('maskedKey')}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="订阅中心 ↔ CC Switch / Magpie 同步桥")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--server", required=True, help="云端地址，如 https://tools.peanuthzm.com.cn")
        p.add_argument("--token", default=os.getenv(TOKEN_ENV, ""), help=f"设备 Token（默认取 ${TOKEN_ENV}）")
        p.add_argument("--json", action="store_true", help="输出 JSON")
        p.add_argument("--dry-run", action="store_true", help="只预览不写入")

    plan = sub.add_parser("plan", help="查看差集（不写任何东西）")
    common(plan)
    plan.set_defaults(func=cmd_plan)

    push = sub.add_parser("push", help="云端 → 本机")
    common(push)
    push.add_argument("--target", choices=["both", "ccswitch", "magpie"], default="both")
    push.set_defaults(func=cmd_push)

    pull = sub.add_parser("pull", help="本机 → 云端")
    common(pull)
    pull.set_defaults(func=cmd_pull)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.token:
        print(f"[bridge] 缺少设备 Token：设置环境变量 {TOKEN_ENV} 或传 --token", file=sys.stderr)
        return 1
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"[bridge] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())