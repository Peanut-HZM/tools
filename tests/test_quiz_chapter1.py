import json
import pytest

def test_chapter1_quiz_structure():
    """验证第 1 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapter1 = data['chapters'][0]
    quiz = chapter1['quizzes'][0]

    # 验证基本结构
    assert quiz['title'] == 'VibeCoding 入门测验'
    assert len(quiz['questions']) == 3, "应该有 3 道题"

    # 验证题型
    types = [q['question_type'] for q in quiz['questions']]
    assert 'single' in types, "应该有单选题"

    # 验证选项数量
    for q in quiz['questions']:
        assert len(q['options']) >= 2, "至少 2 个选项"
        assert q.get('explanation'), "必须有解析"

def test_chapter1_scene_analysis_question():
    """验证场景分析题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    scene_q = quiz['questions'][0]

    # 场景题必须包含【场景】标记
    assert '【场景】' in scene_q['question_text'] or '场景' in scene_q['question_text']
    assert len(scene_q['question_text']) > 50, "场景描述不能太短"

def test_chapter1_diagnosis_question():
    """验证诊断题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    diag_q = quiz['questions'][1]

    # 诊断题必须包含【诊断】标记
    assert '【诊断】' in diag_q['question_text'] or '诊断' in diag_q['question_text']

def test_chapter1_decision_question():
    """验证决策题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    decision_q = quiz['questions'][2]

    # 决策题必须包含【决策】标记
    assert '【决策】' in decision_q['question_text'] or '决策' in decision_q['question_text']

def test_chapter1_no_duplicate_questions():
    """验证第 1 章没有重复题目"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    questions = [q['question_text'] for q in quiz['questions']]

    # 验证没有完全重复的题目
    assert len(questions) == len(set(questions)), "存在重复题目"
