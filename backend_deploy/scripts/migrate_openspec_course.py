#!/usr/bin/env python3
"""
数据迁移脚本：将现有 OpenSpec VibeCoding 课程内容迁移到新的课程平台表

使用方法:
    python scripts/migrate_openspec_course.py
"""

import sys
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config.config import settings


def migrate_data():
    """迁移 OpenSpec 课程数据到新表"""

    # 解析 PostgreSQL 连接
    db_url = settings.DATABASE_URL
    print(f"数据库：{db_url[:30]}...")

    # 连接数据库
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. 检查是否已有新课程数据
        cursor.execute("SELECT id FROM courses WHERE slug = 'openspec-vibecoding' LIMIT 1")
        if cursor.fetchone():
            print("⚠️  已存在课程 'openspec-vibecoding'，跳过迁移")
            return False

        # 2. 检查是否有旧的 OpenSpec 数据
        cursor.execute("""
            SELECT id, slug, title, content, chapter_type, video_url, is_locked, "order"
            FROM openspec_course_chapters
            ORDER BY "order"
        """)
        old_chapters = cursor.fetchall()

        if not old_chapters:
            print("⚠️  没有找到旧的 OpenSpec 课程数据")
            return False

        print(f"📚 找到 {len(old_chapters)} 个旧章节")

        # 3. 创建课程记录
        cursor.execute("""
            INSERT INTO courses (title, slug, description, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, ("OpenSpec VibeCoding 课程", "openspec-vibecoding",
              "从 AI 小白到 Spec 高手的进阶之路 | 故事驱动 × 互动学习 × 实战练习", "published"))
        course_id = cursor.fetchone()['id']
        print(f"✅ 创建课程：OpenSpec VibeCoding 课程 (ID={course_id})")

        # 4. 迁移章节数据
        chapter_map = {}  # 旧章节 ID -> 新章节 ID
        for old in old_chapters:
            old_id = old['id']
            slug = old['slug']
            title = old['title']
            content = old['content']
            chapter_type = old['chapter_type']
            video_url = old['video_url']
            is_locked = old['is_locked']
            order = old['order']

            cursor.execute("""
                INSERT INTO course_chapters
                (course_id, slug, title, "order", content, chapter_type, video_url, is_locked, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (course_id, slug, title, order, content, chapter_type, video_url, is_locked))
            new_chapter_id = cursor.fetchone()['id']
            chapter_map[old_id] = new_chapter_id
            print(f"  ✅ 迁移章节：{title} (ID={old_id} -> {new_chapter_id})")

        # 5. 迁移测验数据
        cursor.execute("SELECT id, chapter_id, title, passing_score FROM openspec_course_quizzes")
        old_quizzes = cursor.fetchall()
        quiz_map = {}

        for old in old_quizzes:
            old_id = old['id']
            old_chapter_id = old['chapter_id']
            title = old['title']
            passing_score = old['passing_score']

            new_chapter_id = chapter_map.get(old_chapter_id)
            if not new_chapter_id:
                print(f"  ⚠️  跳过测验 {title}，因为章节未迁移")
                continue

            cursor.execute("""
                INSERT INTO course_quizzes (chapter_id, title, passing_score, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (new_chapter_id, title, passing_score))
            new_quiz_id = cursor.fetchone()['id']
            quiz_map[old_id] = new_quiz_id
            print(f"  ✅ 迁移测验：{title} (ID={old_id} -> {new_quiz_id})")

            # 5.1 迁移测验题目
            cursor.execute("""
                SELECT id, question_text, question_type, correct_answer, explanation, "order"
                FROM openspec_course_quiz_questions WHERE quiz_id = %s
            """, (old_id,))
            old_questions = cursor.fetchall()

            for old_q in old_questions:
                old_q_id = old_q['id']
                question_text = old_q['question_text']
                question_type = old_q['question_type']
                correct_answer = old_q['correct_answer']
                explanation = old_q['explanation']
                order = old_q['order']

                cursor.execute("""
                    INSERT INTO course_quiz_questions
                    (quiz_id, question_text, question_type, correct_answer, explanation, "order", created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (new_quiz_id, question_text, question_type, correct_answer, explanation, order))
                new_question_id = cursor.fetchone()['id']

                # 5.2 迁移测验选项
                cursor.execute("""
                    SELECT option_text, option_index FROM openspec_course_quiz_options WHERE question_id = %s
                """, (old_q_id,))
                old_options = cursor.fetchall()

                for old_o in old_options:
                    option_text = old_o['option_text']
                    option_index = old_o['option_index']
                    cursor.execute("""
                        INSERT INTO course_quiz_options (question_id, option_text, option_index, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (new_question_id, option_text, option_index))

            cursor.execute("SELECT COUNT(*) FROM course_quiz_questions WHERE quiz_id = %s", (new_quiz_id,))
            question_count = cursor.fetchone()['count']
            print(f"    ✅ 迁移 {question_count} 道题目")

        # 6. 迁移资源数据
        cursor.execute("""
            SELECT id, chapter_id, resource_type, title, content, extra_data
            FROM openspec_course_resources
        """)
        old_resources = cursor.fetchall()
        resource_count = 0

        for old in old_resources:
            old_id = old['id']
            old_chapter_id = old['chapter_id']
            resource_type = old['resource_type']
            title = old['title']
            content = old['content']
            extra_data = old['extra_data']

            new_chapter_id = chapter_map.get(old_chapter_id)
            if not new_chapter_id:
                continue

            cursor.execute("""
                INSERT INTO course_resources
                (chapter_id, resource_type, title, content, extra_data, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, (new_chapter_id, resource_type, title, content, extra_data))
            resource_count += 1

        print(f"  ✅ 迁移 {resource_count} 个资源")

        # 7. 初始化统计数据
        cursor.execute("""
            INSERT INTO course_statistics (course_id, updated_at)
            VALUES (%s, NOW())
        """, (course_id,))
        print(f"  ✅ 初始化统计数据")

        # 8. 提交事务
        conn.commit()

        # 9. 验证迁移结果
        cursor.execute("SELECT COUNT(*) FROM course_chapters WHERE course_id = %s", (course_id,))
        new_chapter_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) FROM course_quizzes cq
            JOIN course_chapters cc ON cq.chapter_id = cc.id
            WHERE cc.course_id = %s
        """, (course_id,))
        new_quiz_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) FROM course_quiz_questions cqq
            JOIN course_quizzes cq ON cqq.quiz_id = cq.id
            JOIN course_chapters cc ON cq.chapter_id = cc.id
            WHERE cc.course_id = %s
        """, (course_id,))
        new_question_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) FROM course_resources cr
            JOIN course_chapters cc ON cr.chapter_id = cc.id
            WHERE cc.course_id = %s
        """, (course_id,))
        new_resource_count = cursor.fetchone()['count']

        print("\n=== 迁移完成 ===")
        print(f"📚 课程：1")
        print(f"📖 章节：{new_chapter_count}")
        print(f"📝 测验：{new_quiz_count}")
        print(f"❓ 题目：{new_question_count}")
        print(f"📁 资源：{new_resource_count}")
        print(f"📊 统计：1")

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=== OpenSpec 课程数据迁移 ===\n")
    success = migrate_data()
    sys.exit(0 if success else 1)
