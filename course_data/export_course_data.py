#!/usr/bin/env python3
"""
导出课程数据为 JSON 文件

用法:
    python export_course_data.py [--output-dir OUTPUT_DIR] [--course-id ID] [--course-title TITLE]

示例:
    python export_course_data.py
    python export_course_data.py --output-dir ./backups --course-id 1 --course-title "OpenSpec 课程"
"""

import sys
import os
import json
from datetime import datetime

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.config import settings
from app.services.course_import_export_service import CourseExportService


def export_course_data(output_dir: str = None, course_id: int = None, course_title: str = None):
    """导出课程数据"""

    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "backups")

    os.makedirs(output_dir, exist_ok=True)

    # 创建数据库会话
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print(f"📊 开始导出课程数据...")

        # 创建导出服务
        export_service = CourseExportService(session)
        export_data = export_service.export_to_json(course_id=course_id, course_title=course_title)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_course_export.json"
        filepath = os.path.join(output_dir, filename)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data.model_dump(), f, ensure_ascii=False, indent=2)

        print(f"✅ 导出完成！")
        print(f"📁 文件路径：{filepath}")
        print(f"📊 导出统计:")
        print(f"   - 章节数：{export_data.export_stats.get('chapters_count', 0)}")
        print(f"   - 测验数：{export_data.export_stats.get('quizzes_count', 0)}")
        print(f"   - 问题数：{export_data.export_stats.get('questions_count', 0)}")
        print(f"   - 选项数：{export_data.export_stats.get('options_count', 0)}")
        print(f"   - 资源数：{export_data.export_stats.get('resources_count', 0)}")

        return filepath

    except Exception as e:
        print(f"❌ 导出失败：{e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        session.close()


def export_chapters_to_markdown(output_dir: str = None, chapter_ids: list = None):
    """导出章节为 Markdown 文件"""

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "markdown_exports")

    os.makedirs(output_dir, exist_ok=True)

    # 创建数据库会话
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        from app.models.openspec_course import OpenSpecCourseChapter

        print(f"📝 开始导出章节为 Markdown...")

        # 获取所有章节或指定章节
        if chapter_ids:
            chapters = session.query(OpenSpecCourseChapter).filter(
                OpenSpecCourseChapter.id.in_(chapter_ids)
            ).order_by(OpenSpecCourseChapter.order).all()
        else:
            chapters = session.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()

        export_service = CourseExportService(session)
        exported_files = []

        for chapter in chapters:
            try:
                markdown_content, filename = export_service.export_chapter_to_markdown(chapter.id)
                filepath = os.path.join(output_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                exported_files.append(filepath)
                print(f"   ✅ {chapter.title} -> {filename}")

            except Exception as e:
                print(f"   ❌ 导出章节 {chapter.id} 失败：{e}")

        print(f"\n✅ Markdown 导出完成！共导出 {len(exported_files)} 个文件")
        return exported_files

    except Exception as e:
        print(f"❌ 导出失败：{e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出课程数据")
    parser.add_argument("--output-dir", "-o", default=None, help="输出目录")
    parser.add_argument("--course-id", type=int, default=None, help="课程 ID（可选）")
    parser.add_argument("--course-title", default=None, help="课程标题（可选）")
    parser.add_argument("--markdown", "-m", action="store_true", help="导出为 Markdown 格式")
    parser.add_argument("--chapter-ids", type=int, nargs="+", default=None, help="章节 ID 列表（仅 Markdown 模式）")

    args = parser.parse_args()

    if args.markdown:
        export_chapters_to_markdown(output_dir=args.output_dir, chapter_ids=args.chapter_ids)
    else:
        export_course_data(output_dir=args.output_dir, course_id=args.course_id, course_title=args.course_title)
