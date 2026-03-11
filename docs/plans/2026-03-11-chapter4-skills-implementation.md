# 第四章：Skill 系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建课程第四章内容，介绍 Skill 系统的概念、用法、与 Rules 的区别，并推荐实用技能工具。

**Architecture:** 延续故事驱动风格，先创建章节 Markdown 内容，再创建测验和资源文件，最后更新章节顺序（原 Ch4→Ch5，原 Ch5→Ch6），生成新的导出文件并导入数据库。

**Tech Stack:** Markdown 内容生成，Python 脚本处理 JSON，OpenSpec Course Admin API 导入。

---

## Task 1: 创建第四章 Markdown 内容

**Files:**
- Create: `course_data/chapter4-skills-content.md`

**Step 1: 创建第四章内容文件**

创建完整的故事驱动内容，包含：
- 故事引入（从 Rules 到 Skills 的进化）
- Skills 概念讲解
- 与 Rules 的对比
- 使用方法
- 实用技能推荐
- 最佳实践
- 实战案例

**Step 2: 验证内容格式**

确保：
- 使用 `##` 作为主要标题
- 代码块使用 ```bash 和 ```json 语法高亮
- 表格格式正确
- 与前面章节风格一致

**Step 3: 提交**

```bash
git add course_data/chapter4-skills-content.md
git commit -m "feat: 创建第四章 Skill 系统内容"
```

---

## Task 2: 创建第四章测验内容

**Files:**
- Create: `course_data/chapter4-quiz.json`

**Step 1: 创建测验 JSON 结构**

```json
{
  "slug": "quiz-4-1",
  "title": "Skill 系统测验",
  "passing_score": 60,
  "questions": [
    {
      "question_text": "Skills 和 Rules 的核心区别是什么？",
      "question_type": "single",
      "correct_answer": "1",
      "explanation": "Rules 是约束 AI 行为的规范，Skills 是扩展 AI 能力的工具。",
      "order": 0,
      "options": [
        {"option_text": "没有区别，只是名称不同", "option_index": 0},
        {"option_text": "Rules 约束行为，Skills 扩展能力", "option_index": 1},
        {"option_text": "Rules 更高级，Skills 更基础", "option_index": 2},
        {"option_text": "Skills 只能用于前端，Rules 用于后端", "option_index": 3}
      ]
    },
    {
      "question_text": "以下哪些场景适合使用 Skills？（多选）",
      "question_type": "multiple",
      "correct_answer": "0,2,3",
      "explanation": "Skills 适合复杂工作流、重复性任务和专业场景，简单问答不需要。",
      "order": 1,
      "options": [
        {"option_text": "开发一个完整的新功能", "option_index": 0},
        {"option_text": "询问今天天气如何", "option_index": 1},
        {"option_text": "执行标准化的代码审查", "option_index": 2},
        {"option_text": "设计 UI 页面配色方案", "option_index": 3}
      ]
    },
    {
      "question_text": "前端开发者设计新页面时，首选哪个技能？",
      "question_type": "single",
      "correct_answer": "2",
      "explanation": "ui-ux-pro-max 专门提供 UI/UX 设计指导，包含配色、字体、布局建议。",
      "order": 2,
      "options": [
        {"option_text": "/writing-plans", "option_index": 0},
        {"option_text": "/simplify", "option_index": 1},
        {"option_text": "/ui-ux-pro-max", "option_index": 2},
        {"option_text": "/openspec-new-change", "option_index": 3}
      ]
    },
    {
      "question_text": "开发复杂功能时，正确的技能调用顺序是？",
      "question_type": "single",
      "correct_answer": "1",
      "explanation": "先用 brainstorming 探索需求，再用 writing-plans 创建计划，最后用 openspec-new-change 启动变更。",
      "order": 3,
      "options": [
        {"option_text": "直接开始写代码", "option_index": 0},
        {"option_text": "/brainstorming → /writing-plans → /openspec-new-change", "option_index": 1},
        {"option_text": "/simplify → /frontend-design → /ui-ux-pro-max", "option_index": 2},
        {"option_text": "随便调用，顺序不重要", "option_index": 3}
      ]
    },
    {
      "question_text": "以下哪些是 Skills 的正确使用方式？（多选）",
      "question_type": "multiple",
      "correct_answer": "0,1,3",
      "explanation": "Skills 需要明确调用、提供清晰任务描述、选择适合场景的技能。",
      "order": 4,
      "options": [
        {"option_text": "明确调用技能名称", "option_index": 0},
        {"option_text": "同时调用多个冲突的技能", "option_index": 1},
        {"option_text": "在简单任务上使用复杂技能", "option_index": 2},
        {"option_text": "结合具体场景选择技能", "option_index": 3}
      ]
    }
  ]
}
```

**Step 2: 验证 JSON 格式**

```bash
python -m json.tool course_data/chapter4-quiz.json > /dev/null && echo "JSON 格式正确"
```

**Step 3: 提交**

```bash
git add course_data/chapter4-quiz.json
git commit -m "feat: 创建第四章测验内容"
```

---

## Task 3: 创建第四章资源文件

**Files:**
- Create: `course_data/chapter4-resources.json`

**Step 1: 创建资源文件 1 - Skills 快速参考卡**

```json
{
  "resource_type": "cheatsheet",
  "title": "Skills 快速参考卡",
  "content": "# Skills 快速参考卡\n\n## 通用技能\n\n| 技能名称 | 用途 | 调用示例 |\n|----------|------|----------|\n| brainstorming | 探索需求、设计思路 | `/brainstorming 我想设计...` |\n| writing-plans | 创建实现计划 | `/writing-plans 实现用户认证` |\n| simplify | 代码审查优化 | `/simplify 审查这段代码` |\n\n## 前端技能\n\n| 技能名称 | 用途 | 调用示例 |\n|----------|------|----------|\n| ui-ux-pro-max | UI/UX 设计指导 | `/ui-ux-pro-max plan: SaaS 仪表盘` |\n| frontend-design | 生成前端代码 | `/frontend-design 实现用户列表` |\n| vercel-react-best-practices | React 性能优化 | `/vercel-react-best-practices 检查组件` |\n\n## 后端技能\n\n| 技能名称 | 用途 | 调用示例 |\n|----------|------|----------|\n| openspec-new-change | 启动新变更 | `/openspec-new-change add-api` |\n| opsx:ff | 快速创建变更 | `/opsx:ff add-feature` |\n| opsx:apply | 实现变更任务 | `/opsx:apply change-name` |\n\n## 调用语法\n\n```bash\n# 基础调用\n/skill-name 任务描述\n\n# 带参数调用\n/skill-name param:value 任务描述\n\n# 多技能协作\n1. /brainstorming 探索需求\n2. /writing-plans 创建计划\n3. /openspec-new-change 启动变更\n```\n\n## 最佳实践\n\n### ✅ DO's\n- 明确调用技能名称\n- 提供清晰的任务描述\n- 结合具体场景选择技能\n- 允许多技能协作\n\n### ❌ DON'Ts\n- 不要同时调用冲突的技能\n- 不要在简单任务上使用复杂技能\n- 不要忘记技能也有适用范围"
}
```

**Step 2: 创建资源文件 2 - Skills vs Rules 对比表**

```json
{
  "resource_type": "comparison",
  "title": "Skills 与 Rules 对比表",
  "content": "# Skills vs Rules 对比表\n\n## 核心区别\n\n| 维度 | Rules | Skills |\n|------|-------|--------|\n| **定位** | 约束规范 | 能力扩展 |\n| **触发方式** | 自动应用 | 主动调用 |\n| **内容** | 行为准则 | 工作流程 |\n| **持久性** | 配置文件 | 临时调用 |\n| **示例** | \"用中文回复\" | \"/brainstorming ...\" |\n\n## 使用场景对比\n\n| 场景 | 推荐方式 | 原因 |\n|------|----------|------|\n| 统一回复语言 | Rules | 全局适用，无需每次指定 |\n| 代码风格规范 | Rules | 约束所有输出格式 |\n| 需求探索 | Skills | 需要结构化工作流 |\n| 实现计划 | Skills | 需要多步骤分析 |\n| UI 设计 | Skills | 需要专业设计知识 |\n| 代码审查 | Skills | 需要系统化检查 |\n\n## 配合使用示例\n\n```bash\n# Rules 配置（.clinerules）\n- 所有代码必须使用 TypeScript\n- 回复使用中文\n- 代码要有注释\n\n# 对话中调用 Skills\n/brainstorming 我想实现用户认证功能\n/writing-plans 根据需求创建详细计划\n```\n\n## 常见误区\n\n| 误区 | 正确做法 |\n|------|----------|\n| Rules 和 Skills 混为一谈 | 理解它们是不同概念 |\n| 所有事都用 Rules 解决 | 复杂任务使用 Skills |\n| 所有事都调用 Skills | 简单规则配置到 Rules |\n| 同时调用多个冲突技能 | 一次专注于一个技能 |\n```\n\n**Step 3: 提交**

```bash
git add course_data/chapter4-resources.json\n\ngit commit -m "feat: 创建第四章资源文件"
```

---

## Task 4: 整合课程数据（新版本 v5）

**Files:**
- Modify: `course_data/add_course_resources.py`
- Create: `course_data/course-export-v5.json`

**Step 1: 更新 Python 脚本以包含新章节**

修改 `course_data/add_course_resources.py`，添加处理第四章资源的逻辑。

**Step 2: 创建课程数据整合脚本**

```python\n#!/usr/bin/env python3\n\"\"\"\n整合第四章内容，生成完整的课程导出文件 v5\n\"\"\"\n\nimport json\nfrom datetime import datetime\n\ndef create_chapter4():\n    \"\"\"创建第四章完整数据\"\"\"\n    with open('course_data/chapter4-skills-content.md', 'r', encoding='utf-8') as f:\n        content = f.read()\n    \n    with open('course_data/chapter4-quiz.json', 'r', encoding='utf-8') as f:\n        quiz_data = json.load(f)\n    \n    with open('course_data/chapter4-resources.json', 'r', encoding='utf-8') as f:\n        resources = json.load(f)\n    \n    return {\n        \"slug\": \"skills-system-guide\",\n        \"title\": \"第 4 章：Skill 系统 - 提升 AI 编程效率的利器\",\n        \"order\": 4,\n        \"content\": content,\n        \"chapter_type\": \"story\",\n        \"video_url\": None,\n        \"is_locked\": False,\n        \"required_quiz_slug\": \"quiz-4-1\",\n        \"quizzes\": [quiz_data],\n        \"resources\": resources if isinstance(resources, list) else [resources]\n    }\n\ndef main():\n    # 读取 v4 数据\n    with open('course_data/course-export-optimized-v4.json', 'r', encoding='utf-8') as f:\n        v4_data = json.load(f)\n    \n    # 创建新章节\n    chapter4 = create_chapter4()\n    \n    # 构建 v5 数据结构\n    v5_data = {\n        \"version\": \"2.0\",\n        \"course_id\": v4_data.get(\"course_id\", 4),\n        \"course_title\": v4_data[\"course_title\"],\n        \"export_timestamp\": datetime.now().isoformat(),\n        \"chapters\": []\n    }\n    \n    # 添加第 1-3 章（保持不变）\n    for chapter in v4_data[\"chapters\"][:3]:\n        v5_data[\"chapters\"].append(chapter)\n    \n    # 添加第 4 章（新增 Skills）\n    v5_data[\"chapters\"].append(chapter4)\n    \n    # 添加原第 4 章作为第 5 章（OpenSpec）\n    old_ch4 = v4_data[\"chapters\"][3].copy()\n    old_ch4[\"order\"] = 5\n    old_ch4[\"title\"] = \"第 5 章：OpenSpec 技能系统 - Spec-Driven 开发实践\"\n    v5_data[\"chapters\"].append(old_ch4)\n    \n    # 添加原第 5 章作为第 6 章（工具对比）\n    old_ch5 = v4_data[\"chapters\"][4].copy()\n    old_ch5[\"order\"] = 6\n    old_ch5[\"title\"] = \"第 6 章：工具对比 - Rules vs OpenSpec vs 对话驱动\"\n    v5_data[\"chapters\"].append(old_ch5)\n    \n    # 写入 v5 文件\n    with open('course_data/course-export-v5.json', 'w', encoding='utf-8') as f:\n        json.dump(v5_data, f, ensure_ascii=False, indent=2)\n    \n    print(f\"✓ v5 课程数据已生成\")\n    print(f\"  章节数：{len(v5_data['chapters'])}\")\n    print(f\"  文件：course_data/course-export-v5.json\")\n\nif __name__ == '__main__':\n    main()\n```\n\n**Step 3: 执行脚本生成 v5 数据**\n\n```bash\ncd course_data\npython course-export-v5-generator.py\n```\n\n**Step 4: 验证生成的 JSON**\n\n```bash\npython -m json.tool course_data/course-export-v5.json > /dev/null && echo \"v5 JSON 格式正确"\n```\n\n**Step 5: 提交**\n\n```bash\ngit add course_data/course-export-v5.json course_data/add_course_resources.py\ngit commit -m "feat: 生成 v5 课程数据，新增第四章 Skill 系统"\n```\n\n---\n\n## Task 5: 导入课程数据到数据库\n\n**Files:**\n- Modify: 使用现有 API\n\n**Step 1: 启动后端服务**\n\n```bash\ncd backend\nuvicorn app.main:app --reload --port 19092\n```\n\n**Step 2: 启动前端服务**\n\n```bash\ncd frontend\nnpm run dev\n```\n\n**Step 3: 访问管理后台**\n\n打开浏览器访问 `http://localhost:5173/admin/course-management`\n\n**Step 4: 预览导入**\n\n1. 点击\"导入课程数据\"\n2. 选择 `course_data/course-export-v5.json`\n3. 导入策略选择\"replace\"\n4. 点击\"预览导入\"\n\n**预期输出：**\n- 章节数：6\n- 新章节：1（第 4 章）\n- 更新章节：2（原第 4、5 章）\n\n**Step 5: 确认导入**\n\n点击\"确认导入\"按钮\n\n**预期输出：**\n```json\n{\n  \"success\": true,\n  \"message\": \"课程数据导入成功\",\n  \"imported_stats\": {\n    \"chapters_imported\": 1,\n    \"chapters_updated\": 5,\n    \"chapters_skipped\": 0,\n    \"quizzes_imported\": 6,\n    \"questions_imported\": 23,\n    \"options_imported\": 92,\n    \"resources_imported\": 12\n  }\n}\n```\n\n**Step 6: 验证导入结果**\n\n访问 `http://localhost:5173/admin/chapter-management` 确认：\n- 共有 6 个章节\n- 第 4 章标题为\"Skill 系统 - 提升 AI 编程效率的利器\"\n- 第 5 章标题为\"OpenSpec 技能系统 - Spec-Driven 开发实践\"\n- 第 6 章标题为\"工具对比 - Rules vs OpenSpec vs 对话驱动\"\n\n---\n\n## Task 6: 验证与测试\n\n**Files:**\n- Test: 浏览器验证\n\n**Step 1: 验证第 4 章详情页**\n\n访问第 4 章详情页面，确认：\n- 标题显示正确\n- 内容完整无乱码\n- 表格格式正常\n- 代码块高亮正确\n\n**Step 2: 验证第 4 章测验**\n\n完成第 4 章测验，确认：\n- 5 道题目都显示\n- 答案判断正确\n- 解释显示正常\n\n**Step 3: 验证第 4 章资源**\n\n访问第 4 章资源，确认：\n- 快速参考卡显示\n- 对比表显示\n- 内容格式正确\n\n**Step 4: 验证章节顺序**\n\n在章节列表中确认顺序：\n1. 第 1 章：AI 编程入门\n2. 第 2 章：常见问题\n3. 第 3 章：Rules 详解\n4. 第 4 章：Skill 系统（新增）\n5. 第 5 章：OpenSpec 技能系统（原第 4 章）\n6. 第 6 章：工具对比（原第 5 章）\n\n**Step 5: 提交最终验证**\n\n```bash\ngit add .\ngit commit -m \"chore: 完成第四章验证\"\n```\n\n---\n\n## 完成标准\n\n- [ ] 第四章内容完整且风格一致\n- [ ] 测验 5 题全部正确\n- [ ] 资源文件有实用价值\n- [ ] 章节顺序正确（6 章）\n- [ ] 数据库导入成功\n- [ ] 浏览器验证通过\n\n---\n\n## 执行选择\n\n计划已完成并保存到 `docs/plans/2026-03-11-chapter4-skills-implementation.md`。\n\n**两个执行选项：**\n\n**1. Subagent-Driven（本 session）** - 我为每个任务分派新的 subagent，在任务之间审查，快速迭代\n\n**2. Parallel Session（独立 session）** - 在新 session 中打开 executing-plans，批量执行带检查点\n\n**选择哪种方式？**
