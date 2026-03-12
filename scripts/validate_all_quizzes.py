#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量验证所有章节测验（第 1-6 章）
"""
import json

def validate_all_chapters():
    """验证所有章节测验"""
    print('=' * 60)
    print('=== 课程测验批量验证（第 1-6 章）===')
    print('=' * 60)

    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_passed = True
    total_questions = 0

    for i, chapter in enumerate(data['chapters']):
        chapter_num = i + 1
        print(f'\n--- 第{chapter_num}章：{chapter["title"]} ---')

        if not chapter['quizzes']:
            print('  ⚠️  无测验')
            continue

        quiz = chapter['quizzes'][0]
        print(f'  测验标题：{quiz["title"]}')
        print(f'  题目数量：{len(quiz["questions"])}', end='')

        if len(quiz['questions']) == 3:
            print(' ✅')
        else:
            print(' ❌ (应为 3 道)')
            all_passed = False

        questions = quiz['questions']
        total_questions += len(questions)

        if len(questions) >= 1:
            q1 = questions[0]
            if '【场景】' in q1['question_text'] or '场景' in q1['question_text']:
                print('  - 第 1 题【场景分析】✅')
            else:
                print('  - 第 1 题【场景分析】❌')
                all_passed = False

        if len(questions) >= 2:
            q2 = questions[1]
            if '【诊断】' in q2['question_text'] or '诊断' in q2['question_text']:
                print('  - 第 2 题【诊断】✅')
            else:
                print('  - 第 2 题【诊断】❌')
                all_passed = False

        if len(questions) >= 3:
            q3 = questions[2]
            if '【决策】' in q3['question_text'] or '决策' in q3['question_text']:
                print('  - 第 3 题【决策】✅')
            else:
                print('  - 第 3 题【决策】❌')
                all_passed = False

    print('\n' + '=' * 60)
    if all_passed:
        print('✅ 所有章节测验验证通过！')
    else:
        print('❌ 部分章节测验验证失败')
    print(f'总题目数量：{total_questions}')
    print('=' * 60)

    return all_passed

if __name__ == '__main__':
    import sys
    success = validate_all_chapters()
    sys.exit(0 if success else 1)
