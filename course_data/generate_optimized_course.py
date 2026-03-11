"""
OpenSpec VibeCoding 实践指南课程优化 - 数据生成脚本

生成优化后的课程 JSON 数据，包含：
- 5 章优化后的内容
- 每章 3-5 道测验题
- 每章 2+ 个配套资源
"""

import json
from datetime import datetime

# 课程数据
course_data = {
    "version": "2.0",
    "course_id": 4,
    "course_title": "OpenSpec VibeCoding 实践指南",
    "export_timestamp": datetime.now().isoformat(),
    "chapters": [],
    "export_stats": {
        "chapters_count": 5,
        "quizzes_count": 5,
        "questions_count": 18,
        "options_count": 72,
        "resources_count": 12
    }
}

# ============ 第 1 章 ============
chapter1_content = """## 故事开始...

还记得第一次接触 AI 编程时的我，心里充满了忐忑和不安。

### 我的心态

- 😰 **生怕 AI 理解错了**：每个需求都要写超级详细
- 📝 **复制粘贴所有代码**：要让 AI 改代码？先把整段代码贴给它
- 🤔 **反复确认**：AI 生成的代码真的要逐行检查

### 为什么需要详细沟通？

在初级阶段，AI 没有上下文理解能力，需要用户提供完整的信息。

**❌ 糟糕的指令：**
```
"帮我改一下登录页面"
```

**✅ 好的指令：**
```
我需要修改前端登录页面，具体如下：
1. 前端组件：frontend/src/components/Auth/LoginPage.tsx
2. 修改内容：在表单底部添加"记住我"复选框
3. 样式要求：使用 Tailwind CSS，复选框右侧对齐，文字为灰色
4. 后端接口：POST /api/v1/auth/login
5. 入参示例：{"email": "user@example.com", "password": "123456", "remember": true}
6. 出参示例：{"token": "eyJhbGc...", "expiresIn": 86400}
7. 需要同时修改类型定义：frontend/src/types/auth.ts
```

### 技术背景：LLM 是如何工作的？

LLM（大型语言模型）通过分析大量文本数据学习语言模式。当你输入指令时：

1. **Token 化**：将你的输入拆分成 token（词元）
2. **模式匹配**：基于训练数据中的模式预测下一个 token
3. **上下文理解**：根据上下文生成最可能的回应

**关键点**：LLM 没有真正的"理解"，它是基于统计模式预测。这就是为什么清晰的指令如此重要！

### 前端修改沟通模板

修改前端组件时，需要说明的信息：

| 信息类别 | 说明内容 | 示例 |
|----------|----------|------|
| **目标组件** | 要修改的文件路径 | `frontend/src/components/Header/Header.tsx` |
| **容器/区域** | 具体修改的位置 | "Header 组件右侧，用户头像按钮旁边" |
| **样式变更** | CSS/Tailwind 类名 | "添加 `ml-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded`" |
| **功能逻辑** | 交互行为 | "点击后跳转到 /settings 页面，使用 useNavigate hook" |
| **调用接口** | 后端 API | "调用 GET /api/v1/user/profile 获取用户信息" |
| **入参示例** | 请求参数 | `{"userId": 123, "includeDetails": true}` |
| **出参示例** | 响应数据 | `{"id": 123, "name": "张三", "email": "..."}` |
| **类型定义** | TypeScript 类型 | "需要更新 `frontend/src/types/user.ts` 中的 User 接口" |

### 后端修改沟通模板

修改后端接口时，需要说明的信息：

| 信息类别 | 说明内容 | 示例 |
|----------|----------|------|
| **目标接口** | API 路径和方法 | `POST /api/v1/users` |
| **功能变更** | 新增/修改/删除 | "新增用户创建功能" |
| **数据模型** | 数据库表/字段变更 | "在 users 表添加 avatar 字段" |
| **错误处理** | 异常情况处理 | "用户已存在时返回 409" |
| **日志记录** | 关键日志点 | "记录用户创建成功/失败日志" |
| **测试要求** | 单元测试/集成测试 | "添加创建用户的单元测试" |

### 当时我的 Prompt 示例

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
"""

chapter1 = {
    "slug": "intro-vibe-coding",
    "title": "第一章：最初的我 - 谨慎使用 AI 😰",
    "order": 1,
    "content": chapter1_content,
    "chapter_type": "story",
    "video_url": None,
    "is_locked": False,
    "required_quiz_slug": "quiz-1-1",
    "quizzes": [
        {
            "slug": "quiz-1-1",
            "title": "VibeCoding 入门测验",
            "passing_score": 60,
            "questions": [
                {
                    "question_text": "初次使用 AI 编程时，以下哪种心态是正确的？",
                    "question_type": "single",
                    "correct_answer": "2",
                    "explanation": "AI 需要清晰的指令和必要的上下文，既不过于冗长也不过于简略。",
                    "order": 0,
                    "options": [
                        {"option_text": "越详细越好，把所有想到的都写上去", "option_index": 0},
                        {"option_text": "越简单越好，AI 应该能理解我的意图", "option_index": 1},
                        {"option_text": "清晰简洁的指令，配合必要的上下文", "option_index": 2},
                        {"option_text": "直接让 AI 猜我想要什么", "option_index": 3}
                    ]
                },
                {
                    "question_text": "修改前端组件时，以下哪些信息是必须提供的？（多选）",
                    "question_type": "multiple",
                    "correct_answer": "0,1,3",
                    "explanation": "目标组件文件路径、具体修改位置和类型定义都是必须提供的关键信息。",
                    "order": 1,
                    "options": [
                        {"option_text": "目标组件的文件路径", "option_index": 0},
                        {"option_text": "AI 的历史表现", "option_index": 1},
                        {"option_text": "具体修改的位置", "option_index": 2},
                        {"option_text": "相关的类型定义", "option_index": 3}
                    ]
                },
                {
                    "question_text": "以下哪种 Prompt 方式更容易获得好结果？",
                    "question_type": "single",
                    "correct_answer": "1",
                    "explanation": "提供上下文、期望和约束条件，AI 更容易理解需求。",
                    "order": 2,
                    "options": [
                        {"option_text": "帮我写个函数", "option_index": 0},
                        {"option_text": "用 Python 写一个验证邮箱的函数，需要考虑边界情况，添加注释", "option_index": 1},
                        {"option_text": "写代码，要能用的", "option_index": 2},
                        {"option_text": "你看着写吧，反正你要帮我写好", "option_index": 3}
                    ]
                }
            ]
        }
    ],
    "resources": [
        {
            "resource_type": "template",
            "title": "前端修改沟通模板",
            "content": "## 前端修改沟通模板\n\n### 必填信息\n\n1. **目标组件**：要修改的文件路径\n   - 示例：`frontend/src/components/Header/Header.tsx`\n\n2. **容器/区域**：具体修改的位置\n   - 示例："Header 组件右侧，用户头像按钮旁边"\n\n3. **样式变更**：CSS/Tailwind 类名\n   - 示例："添加 `ml-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded`"\n\n4. **功能逻辑**：交互行为\n   - 示例："点击后跳转到 /settings 页面，使用 useNavigate hook"\n\n5. **调用接口**：后端 API\n   - 示例："调用 GET /api/v1/user/profile 获取用户信息"\n\n6. **入参示例**：请求参数\n   - 示例：`{"userId": 123, "includeDetails": true}`\n\n7. **出参示例**：响应数据\n   - 示例：`{"id": 123, "name": "张三", "email": "..."}`\n\n8. **类型定义**：TypeScript 类型\n   - 示例："需要更新 `frontend/src/types/user.ts` 中的 User 接口"",
            "extra_data": {"template_type": "frontend"}
        },
        {
            "resource_type": "template",
            "title": "后端修改沟通模板",
            "content": "## 后端修改沟通模板\n\n### 必填信息\n\n1. **目标接口**：API 路径和方法\n   - 示例：`POST /api/v1/users`\n\n2. **功能变更**：新增/修改/删除\n   - 示例："新增用户创建功能"\n\n3. **数据模型**：数据库表/字段变更\n   - 示例："在 users 表添加 avatar 字段"\n\n4. **错误处理**：异常情况处理\n   - 示例："用户已存在时返回 409"\n\n5. **日志记录**：关键日志点\n   - 示例："记录用户创建成功/失败日志"\n\n6. **测试要求**：单元测试/集成测试\n   - 示例："添加创建用户的单元测试"",
            "extra_data": {"template_type": "backend"}
        }
    ]
}

course_data["chapters"].append(chapter1)
print("第 1 章完成...")
