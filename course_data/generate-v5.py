#!/usr/bin/env python3
"""
整合第四章内容，生成完整的课程导出文件 v5
- 新增第 4 章：Skill 系统
- 原第 4 章 → 第 5 章：OpenSpec
- 原第 5 章 → 第 6 章：工具对比
"""

import json
from datetime import datetime


def load_chapter4():
    """加载第四章数据"""
    base_path = '/Users/huazhongmin/IdeaProjects/tools/course_data'

    # 读取内容
    with open(f'{base_path}/chapter4-skills-content.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # 读取测验
    with open(f'{base_path}/chapter4-quiz.json', 'r', encoding='utf-8') as f:
        quiz_data = json.load(f)

    # 读取资源
    with open(f'{base_path}/chapter4-resources.json', 'r', encoding='utf-8') as f:
        resources = json.load(f)

    return {
        "slug": "skills-system-guide",
        "title": "第 4 章：Skill 系统 - 提升 AI 编程效率的利器",
        "order": 4,
        "content": content,
        "chapter_type": "story",
        "video_url": None,
        "is_locked": False,
        "required_quiz_slug": "quiz-4-1",
        "quizzes": [quiz_data],
        "resources": resources
    }


def main():
    print("=" * 60)
    print("生成 v5 课程数据")
    print("=" * 60)

    # 读取 v4 数据
    print("\n1. 读取 v4 课程数据...")
    with open('/Users/huazhongmin/IdeaProjects/tools/course_data/course-export-optimized-v4.json', 'r', encoding='utf-8') as f:
        v4_data = json.load(f)
    print(f"   ✓ 读取成功：{len(v4_data['chapters'])} 个章节")

    # 创建 v5 数据结构
    v5_data = {
        "version": "2.0",
        "course_id": v4_data.get("course_id", 4),
        "course_title": v4_data["course_title"],
        "export_timestamp": datetime.now().isoformat(),
        "export_stats": {
            "total_chapters": 6,
            "total_quizzes": 6,
            "total_questions": 25,
            "total_resources": 12
        },
        "chapters": []
    }

    # 添加第 1-3 章（保持不变）
    print("\n2. 复制第 1-3 章...")
    for i in range(3):
        chapter = v4_data["chapters"][i].copy()
        v5_data["chapters"].append(chapter)
        print(f"   ✓ 第{i+1}章：{chapter['title']}")

    # 添加第 4 章（新增 Skills）
    print("\n3. 添加第 4 章（新增）...")
    chapter4 = load_chapter4()
    v5_data["chapters"].append(chapter4)
    print(f"   ✓ 第 4 章：{chapter4['title']}")
    print(f"      - 测验数：{len(chapter4['quizzes'])}")
    print(f"      - 资源数：{len(chapter4['resources'])}")

    # 添加原第 4 章作为第 5 章（OpenSpec）
    print("\n4. 迁移原第 4 章 → 第 5 章...")
    old_ch4 = v4_data["chapters"][3].copy()
    old_ch4["order"] = 5
    old_ch4["title"] = "第 5 章：OpenSpec 技能系统 - Spec-Driven 开发实践"
    old_ch4["slug"] = "openspec-skills-system"
    v5_data["chapters"].append(old_ch4)
    print(f"   ✓ 第 5 章：{old_ch4['title']}")

    # 添加原第 5 章作为第 6 章（工具对比）
    print("\n5. 迁移原第 5 章 → 第 6 章...")
    old_ch5 = v4_data["chapters"][4].copy()
    old_ch5["order"] = 6
    old_ch5["title"] = "第 6 章：工具对比 - Rules vs OpenSpec vs 对话驱动"
    old_ch5["slug"] = "tools-comparison"
    v5_data["chapters"].append(old_ch5)
    print(f"   ✓ 第 6 章：{old_ch5['title']}")

    # 写入 v5 文件
    print("\n6. 写入 v5 课程数据...")
    with open('/Users/huazhongmin/IdeaProjects/tools/course_data/course-export-v5.json', 'w', encoding='utf-8') as f:
        json.dump(v5_data, f, ensure_ascii=False, indent=2)
    print(f"   ✓ 文件：course_data/course-export-v5.json")

    # 统计信息
    print("\n" + "=" * 60)
    print("v5 课程数据统计")
    print("=" * 60)
    print(f"章节数：{len(v5_data['chapters'])}")

    total_questions = 0
    total_resources = 0
    for chapter in v5_data["chapters"]:
        chapter_questions = sum(len(q.get("questions", [])) for q in chapter.get("quizzes", []))
        chapter_resources = len(chapter.get("resources", []))
        total_questions += chapter_questions
        total_resources += chapter_resources
        print(f"  - {chapter['title']}: {chapter_questions} 题，{chapter_resources} 资源")

    print(f"\n总计：{total_questions} 道测验题，{total_resources} 个资源文件")
    print("=" * 60)

    # 验证 JSON 格式
    print("\n7. 验证 JSON 格式...")
    try:
        json.dumps(v5_data, ensure_ascii=False)
        print("   ✓ JSON 格式正确")
    except Exception as e:
        print(f"   ✗ JSON 格式错误：{e}")
        return 1

    print("\n✓ v5 课程数据生成完成！")
    print("\n下一步：")
    print("1. 启动后端服务：cd backend && uvicorn app.main:app --reload --port 19092")
    print("2. 启动前端服务：cd frontend && npm run dev")
    print("3. 访问管理后台导入 course_data/course-export-v5.json")

    return 0


if __name__ == '__main__':
    exit(main())
