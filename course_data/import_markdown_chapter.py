#!/usr/bin/env python3
"""
从 Markdown 文件导入章节更新

用法:
    python import_markdown_chapter.py <chapter_id> <markdown_file> [--preview]

示例:
    python import_markdown_chapter.py 1 ./markdown_exports/intro-vibe-coding.md
    python import_markdown_chapter.py 1 ./markdown_exports/intro-vibe-coding.md --preview
"""

import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.config import settings
from app.services.course_import_export_service import CourseImportService
from app.models.openspec_course import OpenSpecCourseChapter


def main():
    import argparse

    parser = argparse.ArgumentParser(description="从 Markdown 导入章节更新")
    parser.add_argument("chapter_id", type=int, help="章节 ID")
    parser.add_argument("markdown_file", help="输入的 Markdown 文件路径")
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="仅预览变更，不实际执行导入"
    )

    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.markdown_file):
        print(f"❌ 文件不存在：{args.markdown_file}")
        sys.exit(1)

    # 创建数据库会话
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 检查章节是否存在
        chapter = session.query(OpenSpecCourseChapter).filter(
            OpenSpecCourseChapter.id == args.chapter_id
        ).first()

        if not chapter:
            print(f"❌ 章节不存在：{args.chapter_id}")
            sys.exit(1)

        print(f"📖 章节：{chapter.title} ({chapter.slug})")
        print(f"📥 加载 Markdown 文件：{args.markdown_file}")

        with open(args.markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        print(f"✅ 加载成功，{len(markdown_content)} 字节")

        # 创建导入服务
        import_service = CourseImportService(session)

        if args.preview:
            # 预览变更
            print(f"\n📊 变更预览:")
            print(f"=" * 50)

            preview = import_service.parse_markdown_import(markdown_content, args.chapter_id)

            print(f"原标题：{preview.original_title}")
            print(f"新标题：{preview.proposed_title}")
            print(f"\n变更内容:")
            for change in preview.changes:
                print(f"   - {change}")

        else:
            # 先显示预览
            preview = import_service.parse_markdown_import(markdown_content, args.chapter_id)
            print(f"\n📊 变更预览:")
            print(f"=" * 50)
            print(f"原标题：{preview.original_title}")
            print(f"新标题：{preview.proposed_title}")
            print(f"\n变更内容:")
            for change in preview.changes:
                print(f"   - {change}")

            # 询问是否继续
            print(f"\n❓ 是否继续执行导入？(y/N): ", end="")
            response = input().strip().lower()
            if response not in ['y', 'yes']:
                print(f"❌ 已取消导入")
                return

            # 执行导入
            result = import_service.import_from_markdown(markdown_content, args.chapter_id, apply_changes=True)

            print(f"\n✅ 导入成功！")
            print(f"📋 结果:")
            print(f"   - 章节 ID: {result.get('chapter_id')}")
            print(f"   - 章节 Slug: {result.get('chapter_slug')}")
            print(f"   - 应用变更：{result.get('changes_applied')} 项")

    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
