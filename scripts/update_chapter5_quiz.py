#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新第 5 章测验内容为实战导向
"""
import json

# 第 5 章测验数据 - 实战导向设计
chapter5_quiz = {
    "title": "OpenSpec 技能测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】OpenSpec 工作流案例：\n\n1. /opsx:new - 创建变更提案\n2. /opsx:continue - 继续设计\n3. /opsx:apply - 应用变更\n4. /opsx:verify - 验证实现\n\n问题：这个工作流体现了什么核心理念？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "OpenSpec 的核心理念是 Spec-Driven（规格驱动）：先写清楚规格，再开始实现。每个步骤都有明确的工件产出。",
            "order": 0,
            "options": [
                {"option_text": "快速迭代，边做边改", "option_index": 0},
                {"option_text": "Spec-Driven：先明确规格，再逐步实现", "option_index": 1},
                {"option_text": "让 AI 自动完成所有工作", "option_index": 2},
                {"option_text": "尽可能减少人工干预", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】以下哪个技能用于快速向前推进变更，自动创建所有工件？",
            "question_type": "single",
            "correct_answer": 0,
            "explanation": "/opsx:ff（fast-forward）用于快速向前推进，自动创建提案、设计、规格等所有工件。适合需求明确的场景。",
            "order": 1,
            "options": [
                {"option_text": "/opsx:ff", "option_index": 0},
                {"option_text": "/opsx:explore", "option_index": 1},
                {"option_text": "/opsx:new", "option_index": 2},
                {"option_text": "/opsx:apply", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】当你想要探索需求但还不确定具体实现方案时，应该使用哪个技能？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "/opsx:explore 用于探索阶段，帮助分析需求的各个方面，适合需求不明确的场景。/opsx:ff 适合需求明确时快速推进。",
            "order": 2,
            "options": [
                {"option_text": "/opsx:ff 快速推进", "option_index": 0},
                {"option_text": "/opsx:explore 探索需求", "option_index": 1},
                {"option_text": "/opsx:apply 直接实现", "option_index": 2},
                {"option_text": "/opsx:archive 归档变更", "option_index": 3}
            ]
        }
    ]
}

# 读取课程数据
with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 更新第 5 章测验
data['chapters'][4]['quizzes'] = [chapter5_quiz]

# 写回文件
with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 第 5 章测验已更新")
print(f"   - 题目数量：{len(chapter5_quiz['questions'])}")
print(f"   - 题型：场景分析 + 诊断 + 决策")
