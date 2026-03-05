#!/usr/bin/env python3
"""
初始化 OpenSpec 课程数据
"""

import sys
import json

sys.path.insert(0, "/Users/huazhongmin/IdeaProjects/tools/backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, engine
from app.models.openspec_course import (
    CourseChapter,
    CourseQuiz,
    CourseQuizQuestion,
    CourseQuizOption,
    CourseResource,
)
from app.config.config import settings


def init_course_data():
    """初始化课程数据"""

    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 检查是否已有数据
        existing_chapters = session.query(CourseChapter).count()
        if existing_chapters > 0:
            print(f"⚠️  已存在 {existing_chapters} 个章节，跳过初始化")
            return

        # ============ 创建章节 ============

        chapters_data = [
            {
                "slug": "intro-vibe-coding",
                "title": "第一章：最初的我 - 谨慎使用 AI 😰",
                "order": 1,
                "content": """## 故事开始...

还记得第一次接触 AI 编程时的我，心里充满了忐忑和不安。

### 我的心态

- 😰 **生怕 AI 理解错了**：每个需求都要写超级详细
- 📝 **复制粘贴所有代码**：要让 AI 改代码？先把整段代码贴给它
- 🤔 **反复确认**：AI 生成的代码真的要逐行检查

### 当时的 Prompt 示例

```
请帮我写一个 Python 函数，功能是：
1. 接收一个字符串参数
2. 判断这个字符串是否是合法的邮箱地址
3. 如果是邮箱返回 True，否则返回 False
4. 需要使用正则表达式
5. 要考虑各种边界情况
6. 要添加详细的注释
7. 要写单元测试
```

### 现在回想起来

当时的我虽然谨慎，但这种使用方式效率真的很低... 😅

**但这是每个人的必经之路！** 所以不要觉得自己笨，大家都是这样过来的。

---

**下一章**：我们会遇到什么问题？AI 为什么会让我头疼？敬请期待！
""",
                "chapter_type": "story",
                "is_locked": False,
            },
            {
                "slug": "ai-problems",
                "title": "第二章：遇到问题 - AI 乱改代码的困扰 🤯",
                "order": 2,
                "content": """## 问题出现了...

随着使用 AI 的频率增加，问题也随之而来。

### 经典场景

#### 场景 1：修改一个函数，结果改了十个文件

```
我：请帮我修改 login 函数的密码验证逻辑

AI：好的，我修改了以下内容：
- ✅ 修改了 login 函数
- ✅ 修改了 user 模型
- ✅ 修改了数据库迁移文件
- ✅ 修改了前端登录页面
- ✅ 修改了 API 文档
- ✅ ...（还有 20 个文件）
```

**我**：？？？我只是想改个密码验证啊！

#### 场景 2：理解错了需求

```
我：把这个按钮改成蓝色

AI：好的，我把整个页面的主题色都改成了蓝色
```

**我**：...

### 当时的感受

> "这个 AI 怎么这么笨啊！"
> "它能不能只听我的话，不要自作主张？"
> "每次都要花大量时间 review 它改的代码..."

### 转折点

就在我快要放弃的时候，我发现了一个神器...

---

**下一章**：rules 是如何拯救我的！
""",
                "chapter_type": "story",
                "is_locked": True,
                "required_quiz_id": None,
            },
            {
                "slug": "discover-rules",
                "title": "第三章：发现规则 - rules 的拯救 🎉",
                "order": 3,
                "content": """## 柳暗花明！

当我发现 rules 的时候，感觉就像发现了新大陆！

### 什么是 Rules？

Rules 是一组规则文件，用来规范 AI 的行为。它告诉 AI：

- ✅ **应该做什么**
- ❌ **不应该做什么**
- 📋 **如何思考和行动**

### 我的第一条 Rules

```markdown
# AI 助手行为规范

## 代码修改原则
1. **最小化修改**：只修改我明确要求修改的部分
2. **不要擅自添加**：不要添加我未要求的功能
3. **保持原有风格**：保持代码的原有风格和格式
4. **说明变更**：修改前先告诉我改了哪里

## 代码质量要求
1. 添加必要的注释
2. 遵循项目的代码规范
3. 考虑边界情况
```

### 使用 Rules 后的变化

| 之前 | 之后 |
|------|------|
| AI 乱改一堆代码 | 只改我要求的地方 ✅ |
| 需要大量 review | 改动清晰，快速 review ✅ |
| 经常要反复修正 | 第一次就做对 ✅ |
| 感觉 AI 很笨 | 感觉 AI 变聪明了 ✅ |

### 实战示例

**Before (没有 rules)**:
```
用户：修改 login 函数的密码验证
AI：改了 50 个文件，包括一些不该改的...
```

**After (有 rules)**:
```
用户：修改 login 函数的密码验证
AI：好的，我只修改了 login 函数中的密码验证逻辑，变更如下：
- 第 10 行：添加了密码长度检查
- 第 15 行：添加了特殊字符检查
```

---

**动手试试**：下一章我们会学习更强大的工具！
""",
                "chapter_type": "code",
                "is_locked": True,
            },
            {
                "slug": "advanced-tools",
                "title": "第四章：进阶工具 - OpenSpec & Superpowers 🚀",
                "order": 4,
                "content": """## 进入高手阶段！

掌握了 rules 之后，我开始探索更强大的工具。

### OpenSpec 是什么？

OpenSpec 是一个基于 Spec 的开发方法论，核心思想是：

1. **Spec First**：先写规范，再生成代码
2. **AI Native**：专为 AI 协作设计
3. **Iterative**：支持迭代和版本管理

### Spec 文件示例

```yaml
# user-login.spec
feature: 用户登录
description: 用户可以通过邮箱和密码登录系统

requirements:
  - 用户输入邮箱和密码
  - 验证邮箱格式
  - 验证密码正确性
  - 登录成功返回 token
  - 失败显示错误信息

constraints:
  - 密码至少 8 位
  - token 有效期 24 小时
  - 支持记住登录状态
```

### Superpowers 技能包

Superpowers 是一套增强 AI 能力的技能系统：

- 🔍 **代码理解**：快速理解大型代码库
- 📝 **文档生成**：自动生成技术文档
- 🧪 **测试生成**：自动编写单元测试
- 🐛 **Bug 修复**：智能定位和修复问题

### 我的工作流

```mermaid
graph LR
    A[写 Spec] --> B[AI 生成代码]
    B --> C[Code Review]
    C --> D{通过？}
    D -->|是 | E[合并]
    D -->|否 | A
```

### 效率对比

| 开发阶段 | 传统方式 | AI + OpenSpec |
|----------|----------|---------------|
| 需求分析 | 2 小时 | 30 分钟 |
| 代码实现 | 8 小时 | 2 小时 |
| 代码 Review | 2 小时 | 30 分钟 |
| 单元测试 | 4 小时 | 1 小时 |
| **总计** | **16 小时** | **4 小时** |

效率提升 **4 倍**！🚀

---

**最后一章**：OpenSpec vs spec-kit 大对比！
""",
                "chapter_type": "code",
                "is_locked": True,
            },
            {
                "slug": "openspec-vs-speckit",
                "title": "第五章：对比思考 - OpenSpec vs spec-kit ⚖️",
                "order": 5,
                "content": """## 终极对比！

GitHub 也推出了 spec-kit，它和 OpenSpec 有什么区别？

### 功能对比表

| 功能 | OpenSpec | spec-kit |
|------|----------|----------|
| Spec 语法 | YAML/Markdown | Markdown |
| 版本管理 | ✅ 完整支持 | ⚠️ 基础支持 |
| AI 集成 | 🔥 深度集成 | 🔌 插件模式 |
| 学习曲线 | 🟢 平缓 | 🟡 中等 |
| 社区生态 | 🟡 发展中 | 🟢 GitHub 背书 |
| 本地化 | ✅ 优秀 | ⚠️ 一般 |
| 扩展性 | ✅ 强 | ✅ 强 |

### 各自优势

#### OpenSpec 的优势

1. **中文友好**：对中文 Spec 支持更好
2. **开箱即用**：配置简单，快速上手
3. **VibeCoding 理念**：更符合国内开发者习惯
4. **活跃社区**：国内开发者社区活跃

#### spec-kit 的优势

1. **GitHub 原生**：与 GitHub 深度集成
2. **企业支持**：适合大型企业
3. **成熟稳定**：经过大量项目验证
4. **生态丰富**：丰富的插件和模板

### 我的建议

**选择 OpenSpec，如果你：**
- ✅ 是 AI 编程新手
- ✅ 想要快速上手
- ✅ 主要写中文文档
- ✅ 喜欢 VibeCoding 文化

**选择 spec-kit，如果你：**
- ✅ 已经在用 GitHub 生态
- ✅ 需要企业级支持
- ✅ 有国际化需求
- ✅ 需要高度定制

### 最终总结

无论是 OpenSpec 还是 spec-kit，**核心都是提升开发效率**。

> **工具只是手段，高效开发才是目的。**

重要的是掌握 Spec-Driven 的思维方式，而不是纠结于选择哪个工具。

---

## 🎉 恭喜你完成课程！

现在你已经掌握了：
- ✅ VibeCoding 的核心理念
- ✅ Rules 的使用方法
- ✅ OpenSpec 的基础知识
- ✅ Spec 文件的编写技巧

**开始你的 VibeCoding 之旅吧！** 🚀
""",
                "chapter_type": "video",
                "is_locked": True,
            },
        ]

        created_chapters = []
        for chapter_data in chapters_data:
            chapter = CourseChapter(**chapter_data)
            session.add(chapter)
            session.flush()
            created_chapters.append(chapter)
            print(f"✅ 创建章节：{chapter.title}")

        # ============ 创建测验 ============

        quizzes_data = [
            {
                "chapter_id": 1,
                "title": "VibeCoding 入门测验",
                "passing_score": 60,
                "questions": [
                    {
                        "question_text": "初次使用 AI 编程时，以下哪种做法是正确的？",
                        "question_type": "single",
                        "correct_answer": "2",
                        "explanation": "清晰简洁的指令配合必要上下文是最高效的沟通方式。",
                        "options": [
                            {"option_text": "越详细越好，把所有想到的都写上去", "option_index": 0},
                            {"option_text": "越简单越好，AI 应该能理解我的意图", "option_index": 1},
                            {"option_text": "清晰简洁的指令，配合必要的上下文", "option_index": 2},
                            {"option_text": "直接让 AI 猜我想要什么", "option_index": 3},
                        ],
                    },
                    {
                        "question_text": "以下哪种 Prompt 方式更容易获得好结果？",
                        "question_type": "single",
                        "correct_answer": "1",
                        "explanation": "提供上下文、期望和约束条件，AI 更容易理解需求。",
                        "options": [
                            {"option_text": "帮我写个函数", "option_index": 0},
                            {"option_text": "用 Python 写一个验证邮箱的函数，需要考虑边界情况，添加注释", "option_index": 1},
                            {"option_text": "写代码，要能用的", "option_index": 2},
                            {"option_text": "你看着写吧，反正你要帮我写好", "option_index": 3},
                        ],
                    },
                ],
            },
            {
                "chapter_id": 2,
                "title": "AI 问题识别测验",
                "passing_score": 60,
                "questions": [
                    {
                        "question_text": "AI 经常乱改代码，可能的原因是什么？（多选）",
                        "question_type": "multiple",
                        "correct_answer": "0,1,2",
                        "explanation": "以上三个选项都是常见原因。",
                        "options": [
                            {"option_text": "没有明确的 Rules 约束", "option_index": 0},
                            {"option_text": "需求描述不够清晰", "option_index": 1},
                            {"option_text": "AI 过度理解了需求", "option_index": 2},
                            {"option_text": "电脑配置不够好", "option_index": 3},
                        ],
                    },
                    {
                        "question_text": "当你发现 AI 改了不该改的文件时，应该怎么做？",
                        "question_type": "single",
                        "correct_answer": "1",
                        "explanation": "使用 Rules 明确约束 AI 的行为是最有效的解决方案。",
                        "options": [
                            {"option_text": "放弃使用 AI，太难用了", "option_index": 0},
                            {"option_text": "使用 Rules 明确告诉 AI 只修改指定文件", "option_index": 1},
                            {"option_text": "每次都手动改回来", "option_index": 2},
                            {"option_text": "把 AI 骂一顿", "option_index": 3},
                        ],
                    },
                ],
            },
            {
                "chapter_id": 3,
                "title": "Rules 使用测验",
                "passing_score": 80,
                "questions": [
                    {
                        "question_text": "Rules 的主要作用是什么？",
                        "question_type": "single",
                        "correct_answer": "2",
                        "explanation": "Rules 的核心作用是规范 AI 的行为模式。",
                        "options": [
                            {"option_text": "让代码运行更快", "option_index": 0},
                            {"option_text": "自动生成代码", "option_index": 1},
                            {"option_text": "规范 AI 的行为模式", "option_index": 2},
                            {"option_text": "美化代码格式", "option_index": 3},
                        ],
                    },
                    {
                        "question_text": "以下哪些内容适合放入 Rules？（多选）",
                        "question_type": "multiple",
                        "correct_answer": "0,1,3",
                        "explanation": "代码规范、沟通偏好、项目约束都是 Rules 的内容，但业务逻辑不应该放在 Rules 中。",
                        "options": [
                            {"option_text": "代码风格和规范", "option_index": 0},
                            {"option_text": "具体的业务逻辑", "option_index": 1},
                            {"option_text": "今天的天气", "option_index": 2},
                            {"option_text": "沟通方式和偏好", "option_index": 3},
                        ],
                    },
                ],
            },
        ]

        created_quizzes = []
        for quiz_data in quizzes_data:
            questions = quiz_data.pop("questions")
            quiz = CourseQuiz(**quiz_data)
            session.add(quiz)
            session.flush()

            for q_idx, q_data in enumerate(questions):
                options = q_data.pop("options")
                question = CourseQuizQuestion(
                    quiz_id=quiz.id,
                    question_text=q_data["question_text"],
                    question_type=q_data["question_type"],
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data["explanation"],
                    order=q_idx,
                )
                session.add(question)
                session.flush()

                for opt_data in options:
                    option = CourseQuizOption(
                        question_id=question.id,
                        option_text=opt_data["option_text"],
                        option_index=opt_data["option_index"],
                    )
                    session.add(option)

            created_quizzes.append(quiz)
            print(f"✅ 创建测验：{quiz.title}")

        # 更新章节的 required_quiz_id
        created_chapters[0].required_quiz_id = created_quizzes[0].id if created_quizzes else None
        created_chapters[1].required_quiz_id = created_quizzes[1].id if len(created_quizzes) > 1 else None

        session.commit()

        # ============ 创建资源 ============
        import json

        resources_data = [
            {
                "chapter_id": created_chapters[0].id,
                "resource_type": "code_sample",
                "title": "Prompt 模板示例",
                "content": "这是一个好的 Prompt 模板示例，展示了如何清晰地描述需求。",
                "extra_data": json.dumps({"template": "请帮我 [任务]，需要 [要求]，使用 [技术栈]"}, ensure_ascii=False),
            },
            {
                "chapter_id": created_chapters[2].id,
                "resource_type": "template",
                "title": "Rules 模板",
                "content": "可以直接使用的 Rules 模板，包含常用规范。",
                "extra_data": json.dumps({
                    "template": """# AI 助手行为规范

## 代码修改原则
1. 最小化修改
2. 不要擅自添加
3. 保持原有风格

## 沟通原则
1. 先说明变更内容
2. 提供修改理由
3. 询问是否继续"""
                }, ensure_ascii=False),
            },
            {
                "chapter_id": created_chapters[3].id,
                "resource_type": "code_sample",
                "title": "Spec 文件示例",
                "content": "完整的 Spec 文件示例，包含功能需求和技术约束。",
                "extra_data": json.dumps({"example": "user-login.spec"}, ensure_ascii=False),
            },
        ]

        for resource_data in resources_data:
            resource = CourseResource(**resource_data)
            session.add(resource)
            print(f"✅ 创建资源：{resource.title}")

        session.commit()

        print("\n✅ OpenSpec 课程数据初始化完成！")
        print(f"📊 总计：{len(created_chapters)} 个章节，{len(created_quizzes)} 个测验，{len(resources_data)} 个资源")

    except Exception as e:
        session.rollback()
        print(f"❌ 初始化失败：{e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_course_data()
