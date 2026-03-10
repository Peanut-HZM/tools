#!/usr/bin/env python3
"""
添加 OpenSpec 课程资源数据
"""

import sys
import json

sys.path.insert(0, "/Users/huazhongmin/IdeaProjects/tools/backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, engine
from app.models.openspec_course import CourseChapter, CourseResource


def add_resources():
    """添加课程资源"""

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 检查是否已有资源
        existing_resources = session.query(CourseResource).count()
        if existing_resources > 0:
            print(f"⚠️  已存在 {existing_resources} 个资源")

        # 获取章节
        chapters = session.query(CourseChapter).order_by(CourseChapter.order).all()
        if len(chapters) < 4:
            print("❌ 章节数据不完整")
            return

        # 添加资源
        resources_data = [
            {
                "chapter_id": chapters[0].id,
                "resource_type": "code_sample",
                "title": "Prompt 模板示例",
                "content": "这是一个好的 Prompt 模板示例，展示了如何清晰地描述需求。",
                "extra_data": json.dumps({"template": "请帮我 [任务]，需要 [要求]，使用 [技术栈]"}, ensure_ascii=False),
            },
            {
                "chapter_id": chapters[2].id,
                "resource_type": "template",
                "title": "Rules 模板",
                "content": "可以直接使用的 Rules 模板，包含常用规范。",
                "extra_data": json.dumps({
                    "template": """# AI 助手行为规范

## 代码修改原则
1. 最小化修改
2. 不要擅自添加
3. 保持原有风格

## 沟通原则
1. 先说明变更内容
2. 提供修改理由
3. 询问是否继续"""
                }, ensure_ascii=False),
            },
            {
                "chapter_id": chapters[3].id,
                "resource_type": "code_sample",
                "title": "Spec 文件示例",
                "content": "完整的 Spec 文件示例，包含功能需求和技术约束。",
                "extra_data": json.dumps({"example": "user-login.spec"}, ensure_ascii=False),
            },
        ]

        for resource_data in resources_data:
            # 检查是否已存在
            existing = session.query(CourseResource).filter(
                CourseResource.chapter_id == resource_data["chapter_id"],
                CourseResource.title == resource_data["title"]
            ).first()
            if existing:
                print(f"⏭️  跳过已存在的资源：{existing.title}")
                continue

            resource = CourseResource(**resource_data)
            session.add(resource)
            print(f"✅ 创建资源：{resource.title}")

        session.commit()
        print("\n✅ 资源添加完成！")

    except Exception as e:
        session.rollback()
        print(f"❌ 添加失败：{e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    add_resources()
