# 课程测验实战化重新设计实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重新设计并实现 6 章课程的测验内容，从记忆型题目转为实战导向的场景分析、诊断、决策题

**Architecture:**
- 保持现有 JSON 数据结构不变
- 逐章替换测验内容，每章 3 道题（场景分析 + 诊断 + 决策）
- 使用课程导入功能更新数据

**Tech Stack:** Python, JSON, React, TypeScript

---

## 数据准备

### 章节测验映射表

| 章节 | 文件名 | 测验标题 |
|------|--------|----------|
| 第 1 章 | `intro-vibe-coding` | VibeCoding 入门测验 |
| 第 2 章 | `ai-problems` | AI 问题识别测验 |
| 第 3 章 | `discover-rules` | Rules 应用测验 |
| 第 4 章 | `skills-system` | Skill 系统测验 |
| 第 5 章 | `openspec-skills` | OpenSpec 技能测验 |
| 第 6 章 | `tools-comparison` | 三大工具对比测验 |

### 测验数据结构

```json
{
  "title": "测验名称",
  "passing_score": 60,
  "questions": [
    {
      "question_text": "问题描述",
      "question_type": "single",
      "correct_answer": 1,
      "explanation": "解析内容",
      "order": 0,
      "options": [
        {"option_text": "选项 A", "option_index": 0},
        {"option_text": "选项 B", "option_index": 1},
        {"option_text": "选项 C", "option_index": 2},
        {"option_text": "选项 D", "option_index": 3}
      ]
    }
  ]
}
```

---

## Task 1: 第 1 章测验 - VibeCoding 入门测验

**Files:**
- Modify: `course_data/course-export-2026-03-12/course-export.json`
- Test: `tests/test_quiz_chapter1.py`

### 步骤 1: 创建测试文件

```python
# tests/test_quiz_chapter1.py
import json

def test_chapter1_quiz_structure():
    """验证第 1 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
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
        assert q['explanation'], "必须有解析"

def test_chapter1_scene_analysis_question():
    """验证场景分析题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    scene_q = quiz['questions'][0]

    # 场景题必须包含【场景】标记
    assert '【场景】' in scene_q['question_text'] or '场景' in scene_q['question_text']
    assert len(scene_q['question_text']) > 50, "场景描述不能太短"

def test_chapter1_diagnosis_question():
    """验证诊断题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    diag_q = quiz['questions'][1]

    # 诊断题必须包含【诊断】标记
    assert '【诊断】' in diag_q['question_text'] or '诊断' in diag_q['question_text']

def test_chapter1_decision_question():
    """验证决策题"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    quiz = data['chapters'][0]['quizzes'][0]
    decision_q = quiz['questions'][2]

    # 决策题必须包含【决策】标记
    assert '【决策】' in decision_q['question_text'] or '决策' in decision_q['question_text']
```

### 步骤 2: 运行测试验证失败

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python -m pytest tests/test_quiz_chapter1.py -v
```

预期：FAIL - 题目内容不符合新要求

### 步骤 3: 编写第 1 章测验内容

```python
# 第 1 章测验数据（直接修改 JSON 文件中的 quizzes 数组）
chapter1_quiz = {
    "title": "VibeCoding 入门测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】你和 AI 的对话：\n\n你：把这个按钮改成蓝色\nAI：好的，我已将全站主题色改为蓝色\n你：...我只是说登录按钮而已\n\n问题：AI 为什么会误解你的需求？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "指令没有指定具体范围和目标（如'登录页面的提交按钮'），导致 AI 过度泛化。正确的做法是指定明确的选择器和范围。",
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
            "explanation": "完整的 Prompt 应包含功能描述、输入输出示例、边界条件、异常处理等关键信息。'帮我写个函数'缺少所有这些要素。",
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
```

### 步骤 4: 更新 JSON 文件

```python
# scripts/update_chapter1_quiz.py
import json

with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
    data = json.load(f)

# 更新第 1 章测验
data['chapters'][0]['quizzes'] = [chapter1_quiz]

with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("第 1 章测验已更新")
```

运行脚本：
```bash
python scripts/update_chapter1_quiz.py
```

### 步骤 5: 运行测试验证通过

```bash
python -m pytest tests/test_quiz_chapter1.py -v
```

预期：全部 PASS

### 步骤 6: 提交

```bash
git add course_data/ tests/test_quiz_chapter1.py scripts/update_chapter1_quiz.py
git commit -m "feat: 重新设计第 1 章测验 - 实战导向"
```

---

## Task 2: 第 2 章测验 - AI 问题识别测验

**Files:**
- Modify: `course_data/course-export-2026-03-12/course-export.json`
- Test: `tests/test_quiz_chapter2.py`

### 步骤 1: 创建测试文件

```python
# tests/test_quiz_chapter2.py
import json

def test_chapter2_quiz_structure():
    """验证第 2 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    chapter2 = data['chapters'][1]
    quiz = chapter2['quizzes'][0]

    assert quiz['title'] == 'AI 问题识别测验'
    assert len(quiz['questions']) == 3

def test_chapter2_no_duplicate_questions():
    """验证第 2 章没有重复题目"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    quiz = data['chapters'][1]['quizzes'][0]
    questions = [q['question_text'] for q in quiz['questions']]

    # 验证没有完全重复的题目
    assert len(questions) == len(set(questions)), "存在重复题目"
```

### 步骤 2: 运行测试验证失败

```bash
python -m pytest tests/test_quiz_chapter2.py -v
```

### 步骤 3: 编写第 2 章测验内容

```python
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
```

### 步骤 4: 更新 JSON 文件

```python
# scripts/update_chapter2_quiz.py
import json

with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
    data = json.load(f)

data['chapters'][1]['quizzes'] = [chapter2_quiz]

with open('course_data/course-export-2026-03-12/course-export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("第 2 章测验已更新")
```

### 步骤 5: 运行测试验证通过

```bash
python -m pytest tests/test_quiz_chapter2.py -v
```

### 步骤 6: 提交

```bash
git add tests/test_quiz_chapter2.py scripts/update_chapter2_quiz.py
git commit -m "feat: 重新设计第 2 章测验 - AI 问题识别"
```

---

## Task 3: 第 3 章测验 - Rules 应用测验

**Files:**
- Modify: `course_data/course-export-2026-03-12/course-export.json`
- Test: `tests/test_quiz_chapter3.py`

### 步骤 1: 创建测试文件

```python
# tests/test_quiz_chapter3.py
import json

def test_chapter3_quiz_structure():
    """验证第 3 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    chapter3 = data['chapters'][2]
    quiz = chapter3['quizzes'][0]

    assert quiz['title'] == 'Rules 应用测验'
    assert len(quiz['questions']) == 3
```

### 步骤 2: 编写第 3 章测验内容

```python
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
```

### 步骤 3-6: 更新、测试、提交（同 Task 1）

```bash
python scripts/update_chapter3_quiz.py
python -m pytest tests/test_quiz_chapter3.py -v
git add tests/test_quiz_chapter3.py scripts/update_chapter3_quiz.py
git commit -m "feat: 重新设计第 3 章测验 - Rules 应用"
```

---

## Task 4: 第 4 章测验 - Skill 系统测验

**Files:**
- Modify: `course_data/course-export-2026-03-12/course-export.json`
- Test: `tests/test_quiz_chapter4.py`

### 步骤 1: 创建测试文件

```python
# tests/test_quiz_chapter4.py
import json

def test_chapter4_quiz_structure():
    """验证第 4 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    chapter4 = data['chapters'][3]
    quiz = chapter4['quizzes'][0]

    assert quiz['title'] == 'Skill 系统测验'
    assert len(quiz['questions']) == 3
```

### 步骤 2: 编写第 4 章测验内容

```python
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
```

### 步骤 3-6: 更新、测试、提交（同 Task 1）

---

## Task 5: 第 5 章测验 - OpenSpec 技能测验

**Files:**
- Modify: `course_data/course-export-2026-03-12/course-export.json`
- Test: `tests/test_quiz_chapter5.py`

### 步骤 1: 创建测试文件

```python
# tests/test_quiz_chapter5.py
import json

def test_chapter5_quiz_structure():
    """验证第 5 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    chapter5 = data['chapters'][4]
    quiz = chapter5['quizzes'][0]

    assert quiz['title'] == 'OpenSpec 技能测验'
    assert len(quiz['questions']) == 3
```

### 步骤 2: 编写第 5 章测验内容

```python
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
```

### 步骤 3-6: 更新、测试、提交（同 Task 1）

---

## Task 6: 第 6 章测验 - 三大工具对比测验

**Files:**
- Modify: `course_data/course-export-2026-03-12/course-export.json`
- Test: `tests/test_quiz_chapter6.py`

### 步骤 1: 创建测试文件

```python
# tests/test_quiz_chapter6.py
import json

def test_chapter6_quiz_structure():
    """验证第 6 章测验结构"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    chapter6 = data['chapters'][5]
    quiz = chapter6['quizzes'][0]

    assert quiz['title'] == '三大工具对比测验'
    assert len(quiz['questions']) == 3
```

### 步骤 2: 编写第 6 章测验内容

```python
chapter6_quiz = {
    "title": "三大工具对比测验",
    "passing_score": 60,
    "questions": [
        {
            "question_text": "【场景】团队工具选型：\n\n某 20 人技术团队，需要引入 AI 编程辅助工具。团队特点：\n- 有规范的开发流程\n- 需要多人协作\n- 需要审计追踪\n- 重视代码质量\n\n问题：以下哪个工具最合适？",
            "question_type": "single",
            "correct_answer": 0,
            "explanation": "OpenSpec 定位为'规格驱动的 AI 协作开发框架'，提供完整的变更追踪、工件管理、审计功能，适合企业级团队协作。Spec-Kit 更轻量，Superpowers 更个人化。",
            "order": 0,
            "options": [
                {"option_text": "OpenSpec - 规格驱动的协作框架，适合企业级团队", "option_index": 0},
                {"option_text": "Spec-Kit - 轻量级工具，适合小团队", "option_index": 1},
                {"option_text": "Superpowers - 个人效率工具", "option_index": 2},
                {"option_text": "三个工具都引入，让成员自己选", "option_index": 3}
            ]
        },
        {
            "question_text": "【诊断】OpenSpec 的核心工作流 OPSX 的特点是什么？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "OPSX 是 OpenSpec 的核心工作流，特点是 Artifact-Driven（工件驱动）：每个阶段都有明确的工件产出（proposal.md, design.md, specs/等）。",
            "order": 1,
            "options": [
                {"option_text": "完全自动化，不需要人工干预", "option_index": 0},
                {"option_text": "Artifact-Driven：每个阶段有明确的工件产出", "option_index": 1},
                {"option_text": "只能按固定顺序执行，不能跳过", "option_index": 2},
                {"option_text": "只适用于大型项目", "option_index": 3}
            ]
        },
        {
            "question_text": "【决策】以下哪种工具组合推荐给 3-5 人的创业团队？",
            "question_type": "single",
            "correct_answer": 1,
            "explanation": "3-5 人的创业团队需要快速迭代，但又需要一定的规范。Spec-Kit 或 OpenSpec 的轻量级使用是合适的选择。Superpowers 作为个人工具也可搭配使用。",
            "order": 2,
            "options": [
                {"option_text": "只用 OpenSpec，最强大", "option_index": 0},
                {"option_text": "Spec-Kit（主）+ Superpowers（辅）", "option_index": 1},
                {"option_text": "三个工具全部引入", "option_index": 2},
                {"option_text": "不用工具，手动沟通更高效", "option_index": 3}
            ]
        }
    ]
}
```

### 步骤 3-6: 更新、测试、提交（同 Task 1）

---

## Task 7: 验证与导入

### 步骤 1: 批量验证所有测验

```python
# tests/test_all_quizzes.py
import json

def test_all_chapters_have_quizzes():
    """验证所有章节都有测验"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    assert len(data['chapters']) == 6, "应该有 6 章"

    for i, chapter in enumerate(data['chapters']):
        assert 'quizzes' in chapter, f"第{i+1}章缺少 quizzes 字段"
        assert len(chapter['quizzes']) > 0, f"第{i+1}章没有测验"
        assert len(chapter['quizzes'][0]['questions']) == 3, f"第{i+1}章应该有 3 道题"

def test_no_duplicate_questions():
    """验证没有重复题目"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    all_questions = []
    for chapter in data['chapters']:
        for quiz in chapter['quizzes']:
            for q in quiz['questions']:
                all_questions.append(q['question_text'])

    assert len(all_questions) == len(set(all_questions)), "存在重复题目"

def test_all_questions_have_explanation():
    """验证所有题目都有解析"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r') as f:
        data = json.load(f)

    for chapter in data['chapters']:
        for quiz in chapter['quizzes']:
            for q in quiz['questions']:
                assert q.get('explanation'), f"题目缺少解析：{q['question_text'][:50]}..."

def test_json_format_valid():
    """验证 JSON 格式有效"""
    with open('course_data/course-export-2026-03-12/course-export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 验证必要字段
    assert 'version' in data
    assert 'course_title' in data
    assert 'chapters' in data
```

### 步骤 2: 运行批量验证

```bash
python -m pytest tests/test_all_quizzes.py -v
```

### 步骤 3: 使用导入功能更新课程

```bash
# 1. 通过前端导入功能上传更新后的 JSON 文件
# 访问 http://localhost:5178/admin/course/{id}
# 点击"导入"按钮，选择 course-export.json 文件
# 选择"替换"策略，确认导入
```

### 步骤 4: 前端验证

1. 访问课程详情页
2. 进入"测验管理"标签
3. 逐章检查测验内容
4. 完整答题流程验证

### 步骤 5: 提交

```bash
git add tests/test_all_quizzes.py
git commit -m "test: 添加全章测验验证测试"

# 导入后提交数据更新
git add course_data/
git commit -m "data: 完成全部 6 章测验实战化重新设计"
```

---

## 验收清单

### 内容质量
- [ ] 每章 3 道题（场景分析 + 诊断 + 决策）
- [ ] 所有题目无重复
- [ ] 每题都有详尽解析
- [ ] 场景来自真实工作场景

### 技术验证
- [ ] JSON 格式有效
- [ ] 所有测试通过
- [ ] 能正常导入系统
- [ ] 前端显示正常

### 实战性
- [ ] 场景题有完整对话记录
- [ ] 诊断题有明确问题点
- [ ] 决策题有多个合理选项
