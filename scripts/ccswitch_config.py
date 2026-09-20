#!/usr/bin/env python3
"""
CC Switch 配置导出/导入工具

用法:
  python ccswitch_config.py export [输出文件路径]
  python ccswitch_config.py import  <配置文件路径>  [--strategy skip|overwrite]
  python ccswitch_config.py list    <配置文件路径>

策略说明:
  skip      — 导入时跳过已存在的条目，只新增不存在的（默认，最安全）
  overwrite — 导入时覆盖已存在的同名/同 ID 条目（谨慎使用）

导出内容:
  - settings.json（应用设置）
  - _extracted.json（Provider 扁平配置）
  - model-pricing.json（模型定价覆盖）
  - cc-switch.db 关键表:
      providers, provider_endpoints, settings, mcp_servers,
      skill_repos, proxy_config, model_pricing, profiles
  - Electron app_paths.json（应用路径映射）

安全保证:
  - 导入前自动备份当前所有配置文件到 backups/ 目录
  - skip 模式下绝不覆盖任何已有条目
  - 导出/导入均不影响 CC Switch 运行状态（SQLite 使用只读模式导出）
"""

import argparse
import io
import json
import os
import platform
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Windows 控制台强制 UTF-8 输出，避免 emoji/中文 GBK 编码错误
if platform.system() == "Windows":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

# ─────────────────────────── 常量 ───────────────────────────

EXPORT_VERSION = 1
MANIFEST_NAME = "ccswitch_export.json"

# 导出时排除的大表（日志/统计，非配置）
EXCLUDED_DB_TABLES = {
    "proxy_request_logs",
    "stream_check_logs",
    "provider_health",
    "proxy_live_backup",
    "session_log_sync",
    "session_usage_dedup",
    "usage_daily_rollups",
    "sqlite_sequence",
}

# 导入时操作的 DB 表及其主键/唯一键
DB_TABLE_KEYS = {
    "providers": "id",
    "provider_endpoints": "id",
    "settings": "key",
    "mcp_servers": "id",
    "skill_repos": ("owner", "name"),  # 复合键
    "proxy_config": "app_type",
    "model_pricing": "model_id",
    "profiles": "id",
}


# ─────────────────────────── 目录检测 ───────────────────────────

def find_ccswitch_dir() -> Path | None:
    """自动检测 CC Switch 配置目录"""
    home = Path.home()
    system = platform.system()

    candidates: list[Path] = []

    if system == "Windows":
        candidates = [
            home / ".cc-switch",
            home / "AppData" / "Roaming" / ".cc-switch",
            home / "AppData" / "Local" / ".cc-switch",
        ]
    elif system == "Darwin":
        candidates = [
            home / ".cc-switch",
            home / "Library" / "Application Support" / "cc-switch",
            home / "Library" / "Application Support" / "com.ccswitch.desktop",
        ]
    else:  # Linux
        candidates = [
            home / ".cc-switch",
            home / ".config" / "cc-switch",
        ]

    for path in candidates:
        if path.is_dir() and (path / "settings.json").exists():
            return path

    return None


def find_electron_dir() -> Path | None:
    """检测 CC Switch Electron 应用数据目录"""
    home = Path.home()
    system = platform.system()

    candidates: list[Path] = []

    if system == "Windows":
        candidates = [
            home / "AppData" / "Roaming" / "com.ccswitch.desktop",
        ]
    elif system == "Darwin":
        candidates = [
            home / "Library" / "Application Support" / "com.ccswitch.desktop",
        ]
    else:
        candidates = [
            home / ".config" / "com.ccswitch.desktop",
        ]

    for path in candidates:
        if path.is_dir():
            return path

    return None


# ─────────────────────────── 导出 ───────────────────────────

def export_config(output_path: str | None = None) -> str:
    """导出 CC Switch 配置到 zip 文件"""
    cc_dir = find_ccswitch_dir()
    if not cc_dir:
        print("❌ 未找到 CC Switch 配置目录（~/.cc-switch）", file=sys.stderr)
        print("   请确认 CC Switch 已安装并至少运行过一次。", file=sys.stderr)
        sys.exit(1)

    electron_dir = find_electron_dir()

    # 默认输出文件名
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"ccswitch_export_{timestamp}.zip"

    output_path = os.path.abspath(output_path)
    print(f"📦 CC Switch 配置导出")
    print(f"   配置目录: {cc_dir}")
    if electron_dir:
        print(f"   Electron 目录: {electron_dir}")
    print(f"   输出文件: {output_path}")
    print()

    export_data: dict = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now().isoformat(),
        "source_machine": platform.node(),
        "source_os": f"{platform.system()} {platform.release()}",
        "sections": {},
    }

    # ── 1. JSON 文件 ──
    json_files = {
        "settings": cc_dir / "settings.json",
        "extracted": cc_dir / "_extracted.json",
        "model_pricing": cc_dir / "model-pricing.json",
    }

    for section_name, file_path in json_files.items():
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    export_data["sections"][section_name] = json.load(f)
                print(f"   ✅ {file_path.name}")
            except (json.JSONDecodeError, OSError) as e:
                print(f"   ⚠️  {file_path.name} 读取失败: {e}", file=sys.stderr)
        else:
            print(f"   ⏭️  {file_path.name} 不存在，跳过")

    # ── 2. SQLite 数据库 ──
    db_path = cc_dir / "cc-switch.db"
    if db_path.exists():
        try:
            db_data = _export_database(db_path)
            export_data["sections"]["database"] = db_data
            table_count = sum(len(rows) for rows in db_data.values())
            print(f"   ✅ cc-switch.db ({len(db_data)} 表, {table_count} 行)")
        except Exception as e:
            print(f"   ⚠️  cc-switch.db 导出失败: {e}", file=sys.stderr)
    else:
        print(f"   ⏭️  cc-switch.db 不存在，跳过")

    # ── 3. Electron app_paths.json ──
    if electron_dir:
        app_paths_file = electron_dir / "app_paths.json"
        if app_paths_file.exists():
            try:
                with open(app_paths_file, "r", encoding="utf-8") as f:
                    export_data["sections"]["app_paths"] = json.load(f)
                print(f"   ✅ app_paths.json")
            except (json.JSONDecodeError, OSError) as e:
                print(f"   ⚠️  app_paths.json 读取失败: {e}", file=sys.stderr)

    # ── 写入 zip ──
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 将脚本自身打包进 zip，方便在其他机器直接使用
        script_path = os.path.abspath(__file__)
        if os.path.exists(script_path):
            zf.write(script_path, "ccswitch_config.py")
        manifest_json = json.dumps(export_data, indent=2, ensure_ascii=False)
        zf.writestr(MANIFEST_NAME, manifest_json)

    file_size = os.path.getsize(output_path)
    size_str = (
        f"{file_size / 1024:.1f} KB"
        if file_size < 1024 * 1024
        else f"{file_size / (1024 * 1024):.1f} MB"
    )
    print(f"\n✅ 导出完成: {output_path} ({size_str})")

    # 统计信息
    sections = export_data["sections"]
    print(f"   包含 {len(sections)} 个配置区段:")
    for name, data in sections.items():
        if isinstance(data, dict):
            print(f"     - {name}: {len(data)} 个键")
        elif isinstance(data, list):
            print(f"     - {name}: {len(data)} 条")

    return output_path


def _export_database(db_path: Path) -> dict:
    """从 SQLite 数据库导出关键表"""
    # 使用只读 URI 打开，避免写锁影响运行中的 CC Switch
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = {row["name"] for row in cursor.fetchall()}
    target_tables = all_tables - EXCLUDED_DB_TABLES

    db_data: dict = {}
    for table in sorted(target_tables):
        try:
            cursor.execute(f"SELECT * FROM [{table}]")
            columns = [desc[0] for desc in cursor.description]
            rows = []
            for row in cursor.fetchall():
                row_dict = {}
                for col in columns:
                    val = row[col]
                    # 布尔值序列化
                    if isinstance(val, bool):
                        val = int(val)
                    row_dict[col] = val
                rows.append(row_dict)
            if rows:
                db_data[table] = rows
        except Exception as e:
            print(f"   ⚠️  表 {table} 导出失败: {e}", file=sys.stderr)

    conn.close()
    return db_data


# ─────────────────────────── 导入 ───────────────────────────

def import_config(
    input_path: str,
    strategy: str = "skip",
    dry_run: bool = False,
) -> None:
    """导入 CC Switch 配置"""
    input_path = os.path.abspath(input_path)

    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 读取导出文件
    export_data = _load_export_file(input_path)
    if not export_data:
        sys.exit(1)

    version = export_data.get("version", "?")
    exported_at = export_data.get("exported_at", "?")
    source = export_data.get("source_machine", "?")

    print(f"📥 CC Switch 配置导入")
    print(f"   来源文件: {input_path}")
    print(f"   导出时间: {exported_at}")
    print(f"   来源机器: {source}")
    print(f"   格式版本: {version}")
    print(f"   导入策略: {'跳过已有' if strategy == 'skip' else '覆盖已有'}")
    if dry_run:
        print(f"   ⚡ 试运行模式（不实际写入）")
    print()

    # 检测目标目录
    cc_dir = find_ccswitch_dir()
    if not cc_dir:
        print("❌ 未找到 CC Switch 配置目录", file=sys.stderr)
        sys.exit(1)

    electron_dir = find_electron_dir()
    print(f"   目标配置目录: {cc_dir}")

    sections = export_data.get("sections", {})
    stats = {"added": 0, "skipped": 0, "updated": 0}

    if not dry_run:
        # 备份现有配置
        _create_backup(cc_dir)

    # ── 1. 导入 JSON 文件 ──
    json_mappings = {
        "settings": cc_dir / "settings.json",
        "extracted": cc_dir / "_extracted.json",
        "model_pricing": cc_dir / "model-pricing.json",
    }

    for section_name, target_file in json_mappings.items():
        if section_name in sections:
            _import_json_file(
                section_name,
                sections[section_name],
                target_file,
                strategy,
                dry_run,
                stats,
            )

    # ── 2. 导入数据库 ──
    if "database" in sections:
        db_path = cc_dir / "cc-switch.db"
        _import_database(db_path, sections["database"], strategy, dry_run, stats)

    # ── 3. 导入 Electron app_paths ──
    if "app_paths" in sections and electron_dir:
        target = electron_dir / "app_paths.json"
        _import_json_file("app_paths", sections["app_paths"], target, strategy, dry_run, stats)

    # ── 统计 ──
    print()
    if dry_run:
        print(f"🔍 试运行完成（未修改任何文件）:")
    else:
        print(f"✅ 导入完成:")
    print(f"   新增: {stats['added']} 条")
    print(f"   跳过: {stats['skipped']} 条")
    print(f"   更新: {stats['updated']} 条")

    if strategy == "skip" and stats["skipped"] > 0:
        print(f"\n💡 有 {stats['skipped']} 条已有配置被保留（未被覆盖）")

    if not dry_run:
        print(f"\n⚠️  建议重启 CC Switch 使配置生效")


def _load_export_file(path: str) -> dict | None:
    """加载导出文件（支持 zip 和纯 JSON）"""
    if path.endswith(".zip"):
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if MANIFEST_NAME not in zf.namelist():
                    print(f"❌ zip 文件中未找到 {MANIFEST_NAME}", file=sys.stderr)
                    return None
                with zf.open(MANIFEST_NAME) as f:
                    return json.loads(f.read().decode("utf-8"))
        except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as e:
            print(f"❌ 读取 zip 文件失败: {e}", file=sys.stderr)
            return None
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"❌ 读取 JSON 文件失败: {e}", file=sys.stderr)
            return None


def _create_backup(cc_dir: Path) -> None:
    """创建配置备份"""
    backup_dir = cc_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_prefix = backup_dir / f"pre_import_{timestamp}"

    backed_up = []
    for filename in ["settings.json", "_extracted.json", "model-pricing.json"]:
        src = cc_dir / filename
        if src.exists():
            dst = backup_dir / f"{filename}.bak_{timestamp}"
            shutil.copy2(src, dst)
            backed_up.append(filename)

    # 备份数据库
    db_src = cc_dir / "cc-switch.db"
    if db_src.exists():
        db_dst = backup_dir / f"cc-switch.db.bak_{timestamp}"
        try:
            shutil.copy2(db_src, db_dst)
            backed_up.append("cc-switch.db")
        except OSError as e:
            print(f"   ⚠️  数据库备份失败（可能正在被占用）: {e}", file=sys.stderr)

    print(f"   💾 已备份: {', '.join(backed_up)} → backups/")


def _import_json_file(
    section_name: str,
    imported_data: dict,
    target_file: Path,
    strategy: str,
    dry_run: bool,
    stats: dict,
) -> None:
    """导入单个 JSON 文件（merge 模式）"""
    print(f"   📄 {section_name} → {target_file.name}")

    existing: dict = {}
    if target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    merged = _deep_merge(existing, imported_data, strategy, stats, section_name)

    if not dry_run:
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)


def _deep_merge(
    existing: dict,
    incoming: dict,
    strategy: str,
    stats: dict,
    context: str = "",
) -> dict:
    """深度合并两个字典"""
    result = dict(existing)  # 浅拷贝 existing 作为基础

    for key, new_val in incoming.items():
        if key in result:
            old_val = result[key]
            # 如果两边都是字典，递归合并
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                result[key] = _deep_merge(old_val, new_val, strategy, stats, f"{context}.{key}")
            elif strategy == "overwrite":
                result[key] = new_val
                stats["updated"] += 1
            else:
                # skip 模式：保留已有值
                stats["skipped"] += 1
        else:
            result[key] = new_val
            stats["added"] += 1

    return result


def _import_database(
    db_path: Path,
    db_data: dict,
    strategy: str,
    dry_run: bool,
    stats: dict,
) -> None:
    """导入数据库表数据"""
    print(f"   🗄️  cc-switch.db")

    if not db_path.exists():
        print(f"      ⚠️  数据库文件不存在，跳过", file=sys.stderr)
        return

    if dry_run:
        # 试运行：只统计差异
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except Exception as e:
            print(f"      ⚠️  无法打开数据库: {e}", file=sys.stderr)
            return

        for table, rows in db_data.items():
            if table not in DB_TABLE_KEYS:
                continue
            key_field = DB_TABLE_KEYS[table]
            try:
                if isinstance(key_field, tuple):
                    # 复合键
                    existing_keys = set()
                    for row in conn.execute(f"SELECT * FROM [{table}]"):
                        existing_keys.add(tuple(row[k] for k in key_field))
                    for row in rows:
                        k = tuple(row.get(k) for k in key_field)
                        if k in existing_keys:
                            stats["skipped"] += 1
                        else:
                            stats["added"] += 1
                else:
                    cursor = conn.execute(f"SELECT [{key_field}] FROM [{table}]")
                    existing_keys = {r[0] for r in cursor.fetchall()}
                    for row in rows:
                        k = row.get(key_field)
                        if k in existing_keys:
                            if strategy == "overwrite":
                                stats["updated"] += 1
                            else:
                                stats["skipped"] += 1
                        else:
                            stats["added"] += 1
            except Exception as e:
                print(f"      ⚠️  表 {table} 检查失败: {e}", file=sys.stderr)

        conn.close()
        return

    # 实际导入
    try:
        conn = sqlite3.connect(str(db_path))
    except Exception as e:
        print(f"      ❌ 无法打开数据库（CC Switch 可能正在运行）: {e}", file=sys.stderr)
        print(f"      💡 请先关闭 CC Switch 再重试", file=sys.stderr)
        return

    try:
        for table, rows in db_data.items():
            if table not in DB_TABLE_KEYS or not rows:
                continue

            key_field = DB_TABLE_KEYS[table]
            columns = list(rows[0].keys())

            for row in rows:
                if isinstance(key_field, tuple):
                    key_val = tuple(row.get(k) for k in key_field)
                    placeholders = " AND ".join(f"[{k}] = ?" for k in key_field)
                    cursor = conn.execute(
                        f"SELECT 1 FROM [{table}] WHERE {placeholders}",
                        list(key_val),
                    )
                else:
                    key_val = row.get(key_field)
                    cursor = conn.execute(
                        f"SELECT 1 FROM [{table}] WHERE [{key_field}] = ?",
                        [key_val],
                    )

                exists = cursor.fetchone() is not None

                if exists and strategy == "skip":
                    stats["skipped"] += 1
                    continue

                if exists and strategy == "overwrite":
                    set_clause = ", ".join(
                        f"[{c}] = ?" for c in columns if c != key_field
                    )
                    values = [row[c] for c in columns if c != key_field]
                    if isinstance(key_field, tuple):
                        where_vals = list(key_val)
                    else:
                        where_vals = [key_val]
                    conn.execute(
                        f"UPDATE [{table}] SET {set_clause} WHERE [{key_field}] = ?",
                        values + where_vals,
                    )
                    stats["updated"] += 1
                elif not exists:
                    col_names = ", ".join(f"[{c}]" for c in columns)
                    placeholders = ", ".join("?" for _ in columns)
                    values = [row[c] for c in columns]
                    conn.execute(
                        f"INSERT INTO [{table}] ({col_names}) VALUES ({placeholders})",
                        values,
                    )
                    stats["added"] += 1
                else:
                    stats["skipped"] += 1

        conn.commit()
        print(f"      ✅ 数据库导入成功")
    except Exception as e:
        conn.rollback()
        print(f"      ❌ 数据库导入失败: {e}", file=sys.stderr)
    finally:
        conn.close()


# ─────────────────────────── list ───────────────────────────

def list_config(input_path: str) -> None:
    """列出导出文件中的配置内容摘要"""
    export_data = _load_export_file(input_path)
    if not export_data:
        sys.exit(1)

    version = export_data.get("version", "?")
    exported_at = export_data.get("exported_at", "?")
    source = export_data.get("source_machine", "?")

    print(f"📋 CC Switch 配置导出摘要")
    print(f"   格式版本: {version}")
    print(f"   导出时间: {exported_at}")
    print(f"   来源机器: {source}")
    print()

    sections = export_data.get("sections", {})

    for section_name, data in sections.items():
        if section_name == "database":
            print(f"   🗄️  database:")
            for table, rows in data.items():
                print(f"      - {table}: {len(rows)} 行")
        elif isinstance(data, dict):
            keys = list(data.keys())
            print(f"   📄 {section_name}: {len(keys)} 个键")
            # 显示前几个键名
            for k in keys[:8]:
                v = data[k]
                if isinstance(v, str) and len(v) > 60:
                    v = v[:60] + "..."
                elif isinstance(v, dict):
                    v = f"{{...}} ({len(v)} 键)"
                elif isinstance(v, list):
                    v = f"[...] ({len(v)} 项)"
                print(f"      - {k}: {v}")
            if len(keys) > 8:
                print(f"      ... 还有 {len(keys) - 8} 个")
        elif isinstance(data, list):
            print(f"   📄 {section_name}: {len(data)} 条")
        print()


# ─────────────────────────── extract-script ───────────────────────────

def extract_script(zip_path: str, output_path: str | None = None) -> None:
    """从导出 zip 中提取 ccswitch_config.py 脚本"""
    zip_path = os.path.abspath(zip_path)

    if not os.path.exists(zip_path):
        print(f"❌ 文件不存在: {zip_path}", file=sys.stderr)
        sys.exit(1)

    if not output_path:
        output_path = os.path.join(os.path.dirname(zip_path), "ccswitch_config.py")

    output_path = os.path.abspath(output_path)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "ccswitch_config.py" not in zf.namelist():
                print(f"❌ zip 中未包含 ccswitch_config.py", file=sys.stderr)
                print(f"   该 zip 可能由旧版本导出，请手动复制脚本。", file=sys.stderr)
                sys.exit(1)

            with zf.open("ccswitch_config.py") as src, open(
                output_path, "wb"
            ) as dst:
                dst.write(src.read())

        print(f"✅ 脚本已提取到: {output_path}")
        print(f"\n💡 使用方式:")
        print(f"   python {os.path.basename(output_path)} import {os.path.basename(zip_path)}")

    except (zipfile.BadZipFile, OSError) as e:
        print(f"❌ 提取失败: {e}", file=sys.stderr)
        sys.exit(1)


# ─────────────────────────── 主入口 ───────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CC Switch 配置导出/导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # export
    export_parser = subparsers.add_parser("export", help="导出配置到文件")
    export_parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="输出文件路径（默认: ccswitch_export_<时间戳>.zip）",
    )

    # import
    import_parser = subparsers.add_parser("import", help="从文件导入配置")
    import_parser.add_argument("input", help="导入文件路径（.zip 或 .json）")
    import_parser.add_argument(
        "--strategy",
        choices=["skip", "overwrite"],
        default="skip",
        help="导入策略: skip=跳过已有(默认), overwrite=覆盖已有",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行，只统计差异不实际修改",
    )

    # list
    list_parser = subparsers.add_parser("list", help="查看导出文件内容摘要")
    list_parser.add_argument("input", help="导出文件路径")

    # extract-script
    extract_parser = subparsers.add_parser(
        "extract-script", help="从导出 zip 中提取脚本到当前目录"
    )
    extract_parser.add_argument("input", help="导出 zip 文件路径")
    extract_parser.add_argument(
        "--output",
        default=None,
        help="输出路径（默认: 当前目录下的 ccswitch_config.py）",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "export":
        export_config(args.output)
    elif args.command == "import":
        import_config(args.input, args.strategy, args.dry_run)
    elif args.command == "list":
        list_config(args.input)
    elif args.command == "extract-script":
        extract_script(args.input, args.output)


if __name__ == "__main__":
    main()
