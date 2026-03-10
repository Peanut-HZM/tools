#!/usr/bin/env python3
"""
从 JSON 文件导入课程数据

用法:
    python import_course_data.py <input_file> [--strategy STRATEGY] [--preview]

策略说明:
    - merge: 合并模式，跳过已存在的章节 slug
    - replace: 替换模式，更新已存在的章节 slug
    - skip_existing: 完全跳过已存在的章节

示例:
    python import_course_data.py ./backups/20260310_120000_course_export.json
    python import_course_data.py ./backups/20260310_120000_course_export.json --strategy replace
    python import_course_data.py ./backups/20260310_120000_course_export.json --preview
"""

import sys
import os
import json

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.config import settings
from app.services.course_import_export_service import CourseImportService
from app.schemas.openspec_course import CourseExportData, ImportStrategy


def load_export_data(filepath: str) -> CourseExportData:
    """加载导出的 JSON 数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CourseExportData(**data)


def preview_import(session, export_data: CourseExportData, strategy: ImportStrategy):
    """预览导入结果"""
    import_service = CourseImportService(session)
    preview = import_service.preview_import(export_data, strategy)

    print(f"\n📊 导入预览（策略：{strategy.value}）")
    print(f"=" * 50)
    print(f"📌 章节导入：{preview.chapters_to_import} 个")
    print(f"📌 章节更新：{preview.chapters_to_update} 个")
    print(f"📌 章节跳过：{preview.chapters_to_skip} 个")

    if preview.conflicts:
        print(f"\n📋 冲突详情:")
        for conflict in preview.conflicts:
            status_map = {
                "exists": "⏭️  已存在（将跳过）",
                "will_update": "🔄 已存在（将更新）",
                "new": "✨ 新章节",
            }
            status = status_map.get(conflict.conflict_type, conflict.conflict_type)
            print(f"   {status} - {conflict.chapter_title} ({conflict.chapter_slug})")

    if preview.warnings:
        print(f"\n⚠️  警告:")
        for warning in preview.warnings:
            print(f"   - {warning}")

    return preview


def do_import(session, export_data: CourseExportData, strategy: ImportStrategy):
    """执行导入"""
    import_service = CourseImportService(session)
    result = import_service.import_from_json(export_data, strategy)

    print(f"\n📊 导入结果")
    print(f"=" * 50)
    print(f"{'✅' if result.success else '❌'} {result.message}")

    print(f"\n📋 详细统计:")
    for key, value in result.imported_stats.items():
        print(f"   - {key}: {value}")

    if result.warnings:
        print(f"\n⚠️  警告:")
        for warning in result.warnings:
            print(f"   - {warning}")

    if result.errors:
        print(f"\n❌ 错误:")
        for error in result.errors:
            print(f"   - {error}")

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="从 JSON 导入课程数据")
    parser.add_argument("input_file", help="输入的 JSON 文件路径")
    parser.add_argument(
        "--strategy", "-s",
        default="merge",
        choices=["merge", "replace", "skip_existing"],
        help="导入策略（默认：merge）"
    )
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="仅预览，不实际执行导入"
    )

    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.input_file):
        print(f"❌ 文件不存在：{args.input_file}")
        sys.exit(1)

    # 创建数据库会话
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print(f"📥 加载导入文件：{args.input_file}")
        export_data = load_export_data(args.input_file)
        print(f"✅ 加载成功，包含 {len(export_data.chapters)} 个章节")

        # 解析策略
        strategy = ImportStrategy(args.strategy)

        if args.preview:
            # 仅预览
            preview_import(session, export_data, strategy)
        else:
            # 先显示预览
            preview = preview_import(session, export_data, strategy)

            # 询问是否继续
            print(f"\n❓ 是否继续执行导入？(y/N): ", end="")
            response = input().strip().lower()
            if response not in ['y', 'yes']:
                print(f"❌ 已取消导入")
                return

            # 执行导入
            do_import(session, export_data, strategy)

    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
