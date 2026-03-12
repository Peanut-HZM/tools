#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新第 1 章测验内容为实战导向
"""
import json

# 第 1 章测验数据 - 实战导向设计
chapter1_quiz = {
    "title": "VibeCoding 入门测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】你和 AI 的对话：\n\n你：把这个按钮改成蓝色\nAI：好的，我已将全站主题色改为蓝色\n你：...我只是说登录按钮而已\n\n问题：AI 为什么会误解你的需求？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "指令没有指定具体范围和目标（如'登录页面的提交按钮'），导致 AI 过度泛化。正确的做法是指定明确的选择器和范围，如'将登录表单中的提交按钮背景色改为蓝色'。",
            "order": 0,
            "options": [
                {"option_text": "AI 模型理解能力有限，无法识别'按钮'的指代", "option_index": 0},
                {"option_text": "指令没有指定具体范围和目标，导致过度泛化", "option_index": 1},
                {"option_text": "AI 故意曲解用户意图，想要做更多改动", "option_index": 2},
                {"option_text": "蓝色在 AI 训练数据中代表'全局'含义", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】以下 Prompt 存在什么问题？\n\n'帮我写个函数'",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "完整的 Prompt 应包含功能描述、输入输出示例、边界条件、异常处理等关键信息。'帮我写个函数'缺少所有这些要素，AI 无法准确理解需求。",
            "order": 1,
            "options": [
                {"option_text": "没有指定函数名称", "option_index": 0},
                {"option_text": "缺少功能描述、输入输出、边界条件等关键信息", "option_index": 1},
                {"option_text": "没有说明使用什么编程语言", "option_index": 2},
                {"option_text": "太短了，应该写得更长", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】修改前端组件时，以下哪组信息是必须提供的？",
            "question_type": "single",
            "correct_answer": 0,
            "explanation": "目标组件文件路径、具体修改内容、相关类型定义是 AI 准确修改代码的必要信息。其他选项中的信息要么不重要，要么可以在后续沟通中补充。",
            "order": 2,
            "options": [
                {"option_text": "目标组件文件路径、具体修改内容、相关类型定义", "option_index": 0},
                {"option_text": "AI 的历史表现、修改原因、预期效果", "option_index": 1},
                {"option_text": "项目预算、交付时间、团队成员", "option_index": 2},
                {"option_text": "代码风格偏好、注释语言、测试覆盖率要求", "option_index": 3}
            ]
        }
    ]
}

# 读取课程数据
with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 更新第 1 章测验
data['chapters'][0]['quizzes'] = [chapter1_quiz]

# 写回文件
with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 第 1 章测验已更新")
print(f"   - 题目数量：{len(chapter1_quiz['questions'])}")
print(f"   - 题型：场景分析 + 诊断 + 决策")
