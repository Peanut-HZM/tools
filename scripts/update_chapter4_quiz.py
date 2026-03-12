#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新第 4 章测验内容为实战导向
"""
import json

# 第 4 章测验数据 - 实战导向设计
chapter4_quiz = {
    "title": "Skill 系统测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】对比两种工作流程：\n\n流程 A（无 Skills）：\n用户：帮我设计一个用户登录功能\nAI：好的，请问需要支持哪些登录方式？\n用户：邮箱和密码\nAI：需要记住登录状态吗？\n用户：需要\nAI：错误处理有什么要求？\n用户：...（来回沟通 10 轮）\n\n流程 B（使用 Skills）：\n用户：/brainstorming 设计一个用户登录功能，支持邮箱和密码，需要记住登录状态\nAI：好的，我来帮你探索这个需求。让我们从几个维度分析：\n1. 认证流程设计\n2. 安全性考虑\n3. 会话管理\n...（一次性输出完整分析）\n\n问题：流程 B 的优势是什么？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "Skills 通过预设的框架和流程，让 AI 一次性输出结构化、全面的分析，避免了重复沟通。这是 Skill 系统的核心价值。",
            "order": 0,
            "options": [
                {"option_text": "流程 B 更省时间，因为 AI 回答更快", "option_index": 0},
                {"option_text": "Skills 通过预设框架让 AI 一次性输出结构化分析，避免重复沟通", "option_index": 1},
                {"option_text": "流程 A 太笨了，AI 学不会", "option_index": 2},
                {"option_text": "流程 B 看起来更高级", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】前端开发者设计新页面时，以下技能调用顺序哪个是正确的？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "正确的顺序是：/brainstorming（探索需求）→ /write-prd（定义需求）→ /design（技术方案）→ /implement（实现）。这个顺序符合软件开发的自然流程。",
            "order": 1,
            "options": [
                {"option_text": "/implement → /design → /write-prd → /brainstorming", "option_index": 0},
                {"option_text": "/brainstorming → /write-prd → /design → /implement", "option_index": 1},
                {"option_text": "/design → /implement → /brainstorming → /write-prd", "option_index": 2},
                {"option_text": "顺序不重要，可以随意调用", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】开发复杂功能时，正确的技能调用策略是？",
            "question_type": "single",
            "correct_answer": 2,
            "explanation": "对于复杂功能，应该按照 Skill 系统设计的流程逐步推进：探索→定义→设计→实现。每个阶段都有其特定价值，跳过任何阶段都可能导致问题。",
            "order": 2,
            "options": [
                {"option_text": "直接/implement，效率最高", "option_index": 0},
                {"option_text": "只用/brainstorming，其他不重要", "option_index": 1},
                {"option_text": "按流程逐步推进：探索→定义→设计→实现", "option_index": 2},
                {"option_text": "所有技能一起调用，让 AI 自己决定", "option_index": 3}
            ]
        }
    ]
}

# 读取课程数据
with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 更新第 4 章测验
data['chapters'][3]['quizzes'] = [chapter4_quiz]

# 写回文件
with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 第 4 章测验已更新")
print(f"   - 题目数量：{len(chapter4_quiz['questions'])}")
print(f"   - 题型：场景分析 + 诊断 + 决策")
