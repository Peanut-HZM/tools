#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新第 3 章测验内容为实战导向
"""
import json

# 第 3 章测验数据 - 实战导向设计
chapter3_quiz = {
    "title": "Rules 应用测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】对比两次 AI 编程体验：\n\n使用前：\n- 每次都要重复说明'用 TypeScript''用中文回复''要写注释'\n- AI 经常忘记之前的约束\n- 同样的话要说很多遍\n\n使用后（配置了 Rules）：\n- AI 自动遵循预设规范\n- 代码风格一致\n- 沟通效率大幅提升\n\n问题：Rules 为什么有效？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "Rules 作为系统上下文的一部分被注入到每次对话中，AI 会优先遵循这些明确的指令。这比每次重复沟通要高效得多。",
            "order": 0,
            "options": [
                {"option_text": "AI 被 Rules 限制了，不敢乱来", "option_index": 0},
                {"option_text": "Rules 作为系统上下文，每次对话都会被 AI 优先考虑", "option_index": 1},
                {"option_text": "Rules 改变了 AI 模型的权重", "option_index": 2},
                {"option_text": "心理作用，实际上没区别", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】以下这条 Rules 存在什么问题？\n\n'修改代码时要小心，不要破坏现有功能，保持代码整洁'",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "'小心''不要破坏''整洁'都是模糊词汇，AI 无法准确执行。好的 Rules 应该是可执行的，如'修改前先运行测试''保持与现有代码风格一致'。",
            "order": 1,
            "options": [
                {"option_text": "规则太长，AI 记不住", "option_index": 0},
                {"option_text": "规则过于模糊，'小心''整洁'等词汇无法执行", "option_index": 1},
                {"option_text": "规则数量太少，需要更多", "option_index": 2},
                {"option_text": "规则没有用编号列表", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】当你想要 AI 只修改指定文件而不改动其他文件时，应该使用哪条 Rules？",
            "question_type": "single",
            "correct_answer": 2,
            "explanation": "选项 3 最具体且可执行：明确了修改范围（仅指定文件）、禁止行为（不新增/删除文件）、额外要求（修改前说明）。其他选项要么太模糊，要么不够全面。",
            "order": 2,
            "options": [
                {"option_text": "不要乱改代码", "option_index": 0},
                {"option_text": "修改代码前要先思考", "option_index": 1},
                {"option_text": "仅修改用户明确指定的文件，不新增或删除任何文件；修改前需先说明改动范围", "option_index": 2},
                {"option_text": "尽量保持代码整洁", "option_index": 3}
            ]
        }
    ]
}

# 读取课程数据
with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 更新第 3 章测验
data['chapters'][2]['quizzes'] = [chapter3_quiz]

# 写回文件
with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 第 3 章测验已更新")
print(f"   - 题目数量：{len(chapter3_quiz['questions'])}")
print(f"   - 题型：场景分析 + 诊断 + 决策")
