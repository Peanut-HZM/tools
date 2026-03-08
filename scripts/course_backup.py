#!/usr/bin/env python3
"""
OpenSpec 课程数据备份脚本

备份数据库中的课程数据到 JSON 文件，支持版本管理和恢复功能。

用法:
    python scripts/course_backup.py           # 备份数据
    python scripts/course_backup.py --list    # 列出所有备份
    python scripts/course_backup.py --restore <file>  # 从备份恢复

输出:
    - course_data/backups/YYYYMMDD_HHMMSS_NNN.json
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, engine
from app.models.openspec_course import (
    OpenSpecCourseChapter,
    OpenSpecCourseQuiz,
    OpenSpecCourseQuizQuestion,
    OpenSpecCourseQuizOption,
    OpenSpecCourseResource,
)
from app.config.config import settings


class CourseBackup:
    """课程数据备份"""

    def __init__(self, session, backup_dir: str):
        self.session = session
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_next_version(self) -> str:
        """获取下一个备份版本号"""
        # 获取今天的备份文件
        today = datetime.now().strftime("%Y%m%d")
        existing_backups = list(self.backup_dir.glob(f"{today}_*.json"))

        if not existing_backups:
            return "001"

        # 提取最大的序号
        max_version = 0
        for backup in existing_backups:
            try:
                # 文件名格式：YYYYMMDD_HHMMSS_NNN.json
                parts = backup.stem.split("_")
                if len(parts) >= 3:
                    version = int(parts[2])
                    max_version = max(max_version, version)
            except (ValueError, IndexError):
                continue

        return f"{max_version + 1:03d}"

    def fetch_all_data(self) -> dict:
        """获取所有课程数据"""
        chapters = self.session.query(OpenSpecCourseChapter).all()
        quizzes = self.session.query(OpenSpecCourseQuiz).all()
        questions = self.session.query(OpenSpecCourseQuizQuestion).all()
        options = self.session.query(OpenSpecCourseQuizOption).all()
        resources = self.session.query(OpenSpecCourseResource).all()

        # 序列化数据
        def serialize(obj):
            """将 SQLAlchemy 对象序列化为字典"""
            data = {}
            for column in obj.__table__.columns:
                value = getattr(obj, column.name)
                if isinstance(value, datetime):
                    data[column.name] = value.isoformat()
                elif isinstance(value, (str, int, float, bool, type(None))):
                    data[column.name] = value
                else:
                    data[column.name] = str(value)
            return data

        return {
            "backup_timestamp": datetime.now().isoformat(),
            "chapters": [serialize(c) for c in chapters],
            "quizzes": [serialize(q) for q in quizzes],
            "quiz_questions": [serialize(q) for q in questions],
            "quiz_options": [serialize(o) for o in options],
            "resources": [serialize(r) for r in resources],
        }

    def backup_data(self) -> str:
        """备份数据，返回备份文件路径"""
        # 获取数据
        data = self.fetch_all_data()

        # 统计
        stats = {
            "chapters_count": len(data["chapters"]),
            "quizzes_count": len(data["quizzes"]),
            "questions_count": len(data["quiz_questions"]),
            "options_count": len(data["quiz_options"]),
            "resources_count": len(data["resources"]),
        }
        data["backup_stats"] = stats

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = self.get_next_version()
        filename = f"{timestamp}_{version}.json"
        backup_path = self.backup_dir / filename

        # 写入文件
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(backup_path), stats

    def list_backups(self) -> List[dict]:
        """列出所有备份"""
        backups = []
        for backup_file in sorted(self.backup_dir.glob("*.json")):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    backups.append({
                        "filename": backup_file.name,
                        "timestamp": data.get("backup_timestamp", "未知"),
                        "path": str(backup_file),
                        "stats": data.get("backup_stats", {}),
                    })
            except Exception as e:
                backups.append({
                    "filename": backup_file.name,
                    "timestamp": "读取失败",
                    "path": str(backup_file),
                    "error": str(e),
                })
        return backups

    def restore(self, backup_file: str, dry_run: bool = False) -> dict:
        """从备份恢复"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在：{backup_file}")

        # 读取备份数据
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stats = {
            "restored_chapters": 0,
            "restored_quizzes": 0,
            "restored_questions": 0,
            "restored_options": 0,
            "restored_resources": 0,
            "skipped_chapters": 0,
        }

        # 创建 ID 映射（旧 ID -> 新 ID）
        id_mapping = {}

        try:
            # 恢复章节
            for chapter_data in data.get("chapters", []):
                # 检查是否已存在（按 slug）
                existing = self.session.query(OpenSpecCourseChapter).filter_by(
                    slug=chapter_data["slug"]
                ).first()

                if existing:
                    stats["skipped_chapters"] += 1
                    id_mapping[chapter_data["id"]] = existing.id
                    if not dry_run:
                        # 更新现有章节
                        for key, value in chapter_data.items():
                            if key not in ["id", "created_at", "updated_at"]:
                                setattr(existing, key, value)
                        self.session.add(existing)
                    continue

                if dry_run:
                    # 模拟 ID
                    id_mapping[chapter_data["id"]] = f"new_{chapter_data['slug']}"
                    stats["restored_chapters"] += 1
                    continue

                # 创建新章节
                chapter = OpenSpecCourseChapter()
                for key, value in chapter_data.items():
                    if key not in ["id", "created_at", "updated_at"]:
                        setattr(chapter, key, value)
                self.session.add(chapter)
                self.session.flush()
                id_mapping[chapter_data["id"]] = chapter.id
                stats["restored_chapters"] += 1

            # 恢复测验
            for quiz_data in data.get("quizzes", []):
                old_chapter_id = quiz_data["chapter_id"]
                new_chapter_id = id_mapping.get(old_chapter_id, old_chapter_id)

                if isinstance(new_chapter_id, str) and new_chapter_id.startswith("new_"):
                    # 章节是新增的，跳过测验恢复（会在导入时处理）
                    continue

                quiz = OpenSpecCourseQuiz()
                for key, value in quiz_data.items():
                    if key == "chapter_id":
                        value = new_chapter_id
                    elif key not in ["id", "created_at", "updated_at"]:
                        setattr(quiz, key, value)
                self.session.add(quiz)
                self.session.flush()
                id_mapping[quiz_data["id"]] = quiz.id
                stats["restored_quizzes"] += 1

            # 恢复题目
            for q_data in data.get("quiz_questions", []):
                old_quiz_id = q_data["quiz_id"]
                new_quiz_id = id_mapping.get(old_quiz_id, old_quiz_id)

                if isinstance(new_quiz_id, str):
                    continue

                question = OpenSpecCourseQuizQuestion()
                for key, value in q_data.items():
                    if key == "quiz_id":
                        value = new_quiz_id
                    elif key not in ["id", "created_at"]:
                        setattr(question, key, value)
                self.session.add(question)
                self.session.flush()
                id_mapping[q_data["id"]] = question.id
                stats["restored_questions"] += 1

            # 恢复选项
            for opt_data in data.get("quiz_options", []):
                old_question_id = opt_data["question_id"]
                new_question_id = id_mapping.get(old_question_id, old_question_id)

                if isinstance(new_question_id, str):
                    continue

                option = OpenSpecCourseQuizOption()
                for key, value in opt_data.items():
                    if key == "question_id":
                        value = new_question_id
                    elif key not in ["id", "created_at"]:
                        setattr(option, key, value)
                self.session.add(option)
                self.session.flush()
                stats["restored_options"] += 1

            # 恢复资源
            for res_data in data.get("resources", []):
                old_chapter_id = res_data["chapter_id"]
                new_chapter_id = id_mapping.get(old_chapter_id, old_chapter_id)

                if isinstance(new_chapter_id, str) and new_chapter_id.startswith("new_"):
                    continue

                resource = OpenSpecCourseResource()
                for key, value in res_data.items():
                    if key == "chapter_id":
                        value = new_chapter_id
                    elif key not in ["id", "created_at", "updated_at"]:
                        setattr(resource, key, value)
                self.session.add(resource)
                self.session.flush()
                stats["restored_resources"] += 1

            if not dry_run:
                self.session.commit()

            return stats

        except Exception as e:
            if not dry_run:
                self.session.rollback()
            raise e


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenSpec 课程数据备份工具")
    parser.add_argument("--list", action="store_true", help="列出所有备份")
    parser.add_argument("--restore", type=str, metavar="<file>", help="从备份文件恢复")
    parser.add_argument("--dry-run", action="store_true", help="模拟恢复，不实际写入")
    args = parser.parse_args()

    print("=" * 60)
    print("OpenSpec 课程数据备份工具")
    print("=" * 60)
    print()

    # 创建数据库会话
    print("正在连接数据库...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        backup_dir = Path(__file__).parent.parent / "course_data" / "backups"

        # 列出备份
        if args.list:
            backup_mgr = CourseBackup(session, str(backup_dir))
            backups = backup_mgr.list_backups()

            if not backups:
                print("暂无备份")
                return

            print(f"找到 {len(backups)} 个备份:\n")
            for backup in backups:
                print(f"  📄 {backup['filename']}")
                print(f"     时间：{backup['timestamp']}")
                if "stats" in backup:
                    stats = backup["stats"]
                    print(f"     章节：{stats.get('chapters_count', 0)}, "
                          f"测验：{stats.get('quizzes_count', 0)}, "
                          f"资源：{stats.get('resources_count', 0)}")
                print()
            return

        # 从备份恢复
        if args.restore:
            print(f"正在从备份恢复：{args.restore}")
            backup_mgr = CourseBackup(session, str(backup_dir))

            if args.dry_run:
                print("(模拟恢复模式)")

            stats = backup_mgr.restore(args.restore, dry_run=args.dry_run)

            print()
            if args.dry_run:
                print("✅ 模拟恢复完成（未实际写入）")
            else:
                print("✅ 恢复完成")
            print("━" * 60)
            print(f"恢复章节：{stats['restored_chapters']}")
            print(f"恢复测验：{stats['restored_quizzes']}")
            print(f"恢复题目：{stats['restored_questions']}")
            print(f"恢复选项：{stats['restored_options']}")
            print(f"恢复资源：{stats['restored_resources']}")
            if stats.get('skipped_chapters', 0) > 0:
                print(f"跳过章节：{stats['skipped_chapters']}")
            print()
            return

        # 默认：备份数据
        chapters_count = session.query(OpenSpecCourseChapter).count()
        if chapters_count == 0:
            print("⚠️  数据库中没有课程数据，无法备份")
            return

        print(f"✅ 数据库连接成功，共有 {chapters_count} 个章节")
        print()

        backup_mgr = CourseBackup(session, str(backup_dir))

        print("正在备份数据...")
        backup_path, stats = backup_mgr.backup_data()

        print()
        print("✅ 备份完成")
        print("━" * 60)
        print(f"章节数：{stats['chapters_count']}")
        print(f"测验数：{stats['quizzes_count']}")
        print(f"题目数：{stats['questions_count']}")
        print(f"选项数：{stats['options_count']}")
        print(f"资源数：{stats['resources_count']}")
        print(f"备份文件：{backup_path}")
        print()

    except Exception as e:
        print(f"❌ 操作失败：{e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
