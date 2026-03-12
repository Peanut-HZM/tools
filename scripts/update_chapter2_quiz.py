#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新第 2 章测验内容为实战导向
"""
import json

# 第 2 章测验数据 - 实战导向设计
chapter2_quiz = {
    "title": "AI 问题识别测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】你和 AI 的对话：\n\n你：请帮我修改 login 函数的密码验证逻辑\nAI：好的，我修改了以下内容：\n  - ✅ 修改了 login 函数\n  - ✅ 修改了 user 模型\n  - ✅ 修改了数据库迁移文件\n  - ✅ 修改了前端登录页面\n  - ✅ 修改了 API 文档\n\n你：？？？我只是想改个密码验证啊！\n\n问题：导致 AI 改了这么多文件的根本原因是什么？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "指令没有明确指定修改范围，AI 默认进行'完整实现'。应该在 Prompt 中明确限制修改范围，如'只修改 login 函数中的密码验证逻辑，不要改动其他文件'。",
            "order": 0,
            "options": [
                {"option_text": "AI 过于兴奋，想要展示自己的能力", "option_index": 0},
                {"option_text": "指令没有明确指定修改范围，AI 默认进行完整实现", "option_index": 1},
                {"option_text": "密码验证本身就需要修改这么多文件", "option_index": 2},
                {"option_text": "AI 模型有 bug，无法理解函数级别修改", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】以下需求描述存在什么问题？\n\n'把这个页面弄得好看一点，用户友好一些'",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "'好看'和'用户友好'是主观且模糊的描述，AI 无法准确理解。应该具体说明：颜色方案、布局调整、交互反馈等具体要求。",
            "order": 1,
            "options": [
                {"option_text": "描述太长，AI 记不住", "option_index": 0},
                {"option_text": "'好看'和'用户友好'是主观模糊的描述，无法执行", "option_index": 1},
                {"option_text": "没有指定使用什么 CSS 框架", "option_index": 2},
                {"option_text": "应该提供设计稿而不是文字描述", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】当你发现 AI 改了不该改的文件时，应该怎么做？",
            "question_type": "single",
            "correct_answer": 2,
            "explanation": "最佳做法是：1) 撤销改动；2) 用更明确的指令重新沟通，指定修改范围；3) 考虑将此约束加入 Rules。抱怨或放弃都不是建设性的做法。",
            "order": 2,
            "options": [
                {"option_text": "放弃使用 AI，太不可靠了", "option_index": 0},
                {"option_text": "继续让 AI 改，改到对为止", "option_index": 1},
                {"option_text": "撤销改动，用更明确的指令重新沟通，指定修改范围", "option_index": 2},
                {"option_text": "向 AI 抱怨它理解能力太差", "option_index": 3}
            ]
        }
    ]
}

# 读取课程数据
with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 更新第 2 章测验
data['chapters'][1]['quizzes'] = [chapter2_quiz]

# 写回文件
with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 第 2 章测验已更新")
print(f"   - 题目数量：{len(chapter2_quiz['questions'])}")
print(f"   - 题型：场景分析 + 诊断 + 决策")
