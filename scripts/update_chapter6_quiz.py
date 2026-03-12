#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新第 6 章测验内容为实战导向
"""
import json

# 第 6 章测验数据 - 实战导向设计
chapter6_quiz = {
    "title": "三大工具对比测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】某创业公司（5 人团队）正在开发 SaaS 产品，技术栈为 TypeScript + React + Node.js。团队需求：\n\n1. 需要快速迭代，每两周一个版本\n2. 团队成员 AI 工具偏好不同（有人用 Claude Code，有人用 Cursor）\n3. 希望保持灵活性，随时调整需求\n4. 需要一定的文档追溯能力\n\n问题：以下哪个工具最适合这个团队？",
            "question_type": "single",
            "correct_answer": 0,
            "explanation": "OpenSpec 最适合小团队：支持 20+ AI 工具（满足偏好差异），灵活迭代（适应快速变化），artifact 驱动（提供基本追溯）。Spec-Kit 流程过重，Superpowers 协作支持弱。",
            "order": 0,
            "options": [
                {"option_text": "OpenSpec - 平衡灵活性和结构性，支持多工具", "option_index": 0},
                {"option_text": "Spec-Kit - GitHub 官方，企业级支持", "option_index": 1},
                {"option_text": "Superpowers - 高度自动化，零配置", "option_index": 2},
                {"option_text": "三个工具都适合，随意选择", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】某团队使用 Spec-Kit 进行开发，以下哪个流程是正确的？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "Spec-Kit 采用线性 SDD 流程：specify（创建规格）→ plan（生成计划）→ tasks（生成任务）→ 实现。这个顺序体现了规格驱动开发的核心理念。",
            "order": 1,
            "options": [
                {"option_text": "直接编写代码，然后补充规格文档", "option_index": 0},
                {"option_text": "/speckit.specify → /speckit.plan → /speckit.tasks → 实现", "option_index": 1},
                {"option_text": "先写测试，再写实现代码，最后写规格", "option_index": 2},
                {"option_text": "根据上下文自动触发，无需手动调用命令", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】企业级项目（20+ 人团队）需要严格的合规审查和统一规范，应该选择哪个工具组合？",
            "question_type": "single",
            "correct_answer": 2,
            "explanation": "Spec-Kit 专为大型企业设计，提供严格流程和统一规范。Superpowers 不适合大型团队协作，OpenSpec 虽好但企业特性不如 Spec-Kit。",
            "order": 2,
            "options": [
                {"option_text": "Superpowers + OpenSpec - 自动化与灵活性结合", "option_index": 0},
                {"option_text": "OpenSpec + Superpowers - 多工具支持与自动化", "option_index": 1},
                {"option_text": "Spec-Kit - 企业级流程和严格审查", "option_index": 2},
                {"option_text": "三个工具混合使用 - 取长补短", "option_index": 3}
            ]
        }
    ]
}

# 读取课程数据
with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 更新第 6 章测验
data['chapters'][5]['quizzes'] = [chapter6_quiz]

# 写回文件
with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 第 6 章测验已更新")
print(f"   - 题目数量：{len(chapter6_quiz['questions'])}")
print(f"   - 题型：场景分析 + 诊断 + 决策")
print(f"   - 主题：三大工具对比（OpenSpec vs Spec-Kit vs Superpowers）")
