import json
import pytest

def test_chapter3_quiz_structure():
    """验证第 3 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapter3 = data['chapters'][2]
    quiz = chapter3['quizzes'][0]

    assert quiz['title'] == 'Rules 应用测验'
    assert len(quiz['questions']) == 3, "应该有 3 道题"

def test_chapter3_scene_analysis_question():
    """验证场景分析题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][2]['quizzes'][0]
    scene_q = quiz['questions'][0]

    assert '【场景】' in scene_q['question_text'] or '场景' in scene_q['question_text']

def test_chapter3_diagnosis_question():
    """验证诊断题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][2]['quizzes'][0]
    diag_q = quiz['questions'][1]

    assert '【诊断】' in diag_q['question_text'] or '诊断' in diag_q['question_text']

def test_chapter3_decision_question():
    """验证决策题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    quiz = data['chapters'][2]['quizzes'][0]
    decision_q = quiz['questions'][2]

    assert '【决策】' in decision_q['question_text'] or '决策' in decision_q['question_text']
