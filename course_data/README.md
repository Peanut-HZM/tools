# 课程数据导入/导出功能使用说明

## 功能概述

本课程管理系统支持完整的数据导入/导出功能，包括：

- **JSON 导出**: 将所有课程数据（章节、测验、资源）导出为 JSON 文件
- **JSON 导入**: 从 JSON 文件恢复课程数据
- **Markdown 导出**: 将章节内容导出为可编辑的 Markdown 文档
- **Markdown 导入**: 从 Markdown 文档更新章节内容

## 后端 API

### 导出课程数据

```http
POST /api/openspec-course/export
Content-Type: application/json

{
  "course_id": 1,           // 可选，课程 ID
  "course_title": "课程名称"  // 可选，课程标题
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "version": "1.0",
    "export_timestamp": "2026-03-10T12:00:00",
    "chapters": [...],
    "export_stats": {
      "chapters_count": 5,
      "quizzes_count": 3,
      "questions_count": 6,
      "options_count": 24,
      "resources_count": 3
    }
  },
  "filename": "course-export-20260310-120000.json"
}
```

### 预览导入

```http
POST /api/openspec-course/import/preview
Content-Type: application/json

{
  "import_data": { /* 导出数据 */ },
  "strategy": "merge"  // merge | replace | skip_existing
}
```

**导入策略说明**:

| 策略 | 说明 |
|------|------|
| `merge` | 合并模式：跳过已存在的章节 slug，只导入新的 |
| `replace` | 替换模式：更新已存在的章节 slug，导入新的 |
| `skip_existing` | 完全跳过：不导入任何已存在的章节 |

### 执行导入

```http
POST /api/openspec-course/import
Content-Type: application/json

{
  "import_data": { /* 导出数据 */ },
  "strategy": "merge"
}
```

### 导出章节为 Markdown

```http
GET /api/openspec-course/chapters/{chapter_id}/export-md
```

响应为 Markdown 格式，包含 Frontmatter 元数据。

### 预览 Markdown 导入

```http
POST /api/openspec-course/chapters/{chapter_id}/import-md/preview
Content-Type: application/json

{
  "markdown_content": "---\nslug: ...\n---\n\n章节内容..."
}
```

### 从 Markdown 导入更新

```http
PUT /api/openspec-course/chapters/{chapter_id}/import-md
Content-Type: application/json

{
  "markdown_content": "---\nslug: ...\n---\n\n章节内容..."
}
```

---

## 命令行工具

`course_data` 目录下提供了完整的命令行工具：

### 导出课程数据

```bash
cd course_data

# 导出为 JSON
python export_course_data.py

# 指定输出目录
python export_course_data.py --output-dir ./backups

# 导出为 Markdown
python export_course_data.py --markdown

# 导出指定章节为 Markdown
python export_course_data.py --markdown --chapter-ids 1 2 3
```

### 导入课程数据

```bash
# 预览导入（不实际执行）
python import_course_data.py ./backups/20260310_120000_course_export.json --preview

# 使用 merge 策略导入
python import_course_data.py ./backups/20260310_120000_course_export.json --strategy merge

# 使用 replace 策略导入
python import_course_data.py ./backups/20260310_120000_course_export.json --strategy replace
```

### 从 Markdown 导入章节更新

```bash
# 预览变更
python import_markdown_chapter.py 1 ./markdown_exports/intro-vibe-coding.md --preview

# 执行导入
python import_markdown_chapter.py 1 ./markdown_exports/intro-vibe-coding.md
```

---

## 前端使用

### 课程详情页

1. 进入后台管理 → 课程管理 → 选择课程
2. 点击右上角 **导入/导出** 按钮

#### 导出数据

1. 切换到 **导出** 标签
2. 点击 **导出数据** 按钮
3. 自动下载 JSON 文件

#### 导入数据

1. 切换到 **导入** 标签
2. 选择导入策略：
   - **合并**: 跳过已存在的章节
   - **替换**: 更新已存在的章节
   - **完全跳过**: 不导入已存在的章节
3. 选择 JSON 文件
4. 点击 **预览导入** 查看将要执行的操作
5. 确认无误后点击 **确认导入**

---

## 数据格式

### JSON 导出格式

```json
{
  "version": "1.0",
  "export_timestamp": "2026-03-10T12:00:00",
  "course_id": 1,
  "course_title": "OpenSpec VibeCoding 互动课程",
  "chapters": [
    {
      "slug": "intro-vibe-coding",
      "title": "第一章：最初的我 - 谨慎使用 AI 😰",
      "order": 1,
      "content": "## 故事开始...",
      "chapter_type": "story",
      "is_locked": false,
      "required_quiz_slug": "quiz-11-5",
      "quizzes": [
        {
          "slug": "quiz-11-5",
          "title": "VibeCoding 入门测验",
          "passing_score": 60,
          "questions": [
            {
              "question_text": "初次使用 AI 编程时，以下哪种做法是正确的？",
              "question_type": "single",
              "correct_answer": "2",
              "explanation": "清晰简洁的指令配合必要上下文是最高效的沟通方式。",
              "order": 0,
              "options": [
                {
                  "option_text": "越详细越好，把所有想到的都写上去",
                  "option_index": 0
                }
              ]
            }
          ]
        }
      ],
      "resources": [
        {
          "resource_type": "code_sample",
          "title": "Prompt 模板示例",
          "content": "这是一个好的 Prompt 模板示例",
          "extra_data": {
            "template": "请帮我 [任务]，需要 [要求]，使用 [技术栈]"
          }
        }
      ]
    }
  ],
  "export_stats": {
    "chapters_count": 5,
    "quizzes_count": 3,
    "questions_count": 6,
    "options_count": 24,
    "resources_count": 3
  }
}
```

### Markdown 导出格式

```markdown
---
slug: intro-vibe-coding
title: 第一章：最初的我 - 谨慎使用 AI 😰
order: 1
chapter_type: story
is_locked: false
---

## 故事开始...

还记得第一次接触 AI 编程时的我，心里充满了忐忑和不安。

### 我的心态

- 😰 **生怕 AI 理解错了**：每个需求都要写超级详细

---

## 测验：VibeCoding 入门测验

**及格分数**: 60

### 问题 1

初次使用 AI 编程时，以下哪种做法是正确的？

- [ ] 越详细越好，把所有想到的都写上去
- [x] 清晰简洁的指令，配合必要的上下文

**答案**: 2
**解析**: 清晰简洁的指令配合必要上下文是最高效的沟通方式。

---

## 资源

### Prompt 模板示例

**类型**: code_sample

这是一个好的 Prompt 模板示例，展示了如何清晰地描述需求。
```

---

## 最佳实践

### 数据备份

1. **定期导出**: 建议每周或每次重大修改后导出课程数据
2. **版本管理**: 使用日期命名备份文件，如 `20260310_course_export.json`
3. **多地存储**: 将备份文件存储到多个位置（本地、云存储等）

### 离线编辑

1. 导出章节为 Markdown
2. 在本地编辑器中修改内容
3. 使用 `import_markdown_chapter.py` 预览变更
4. 确认后执行导入

### 数据迁移

1. 在源环境导出课程数据
2. 将 JSON 文件复制到目标环境
3. 使用 `import_course_data.py --preview` 预览
4. 执行导入

---

## 故障排除

### 导入失败

**问题**: 导入时提示 "JSON 解析失败"

**解决**:
- 确保 JSON 文件格式正确
- 检查文件是否完整
- 使用 JSON 验证工具检查

### 章节冲突

**问题**: 导入时提示章节 slug 冲突

**解决**:
- 使用 `--strategy replace` 更新已存在的章节
- 或修改导出文件中的 slug 避免冲突

### Markdown 导入后内容丢失

**问题**: 导入 Markdown 后，测验和资源内容丢失

**说明**: Markdown 导入仅更新章节正文内容，不包含测验和资源。测验和资源需通过 JSON 导入恢复。

---

## 技术细节

### 文件位置

- 后端服务：`backend/app/services/course_import_export_service.py`
- API 路由：`backend/app/routes/openspec_course.py`
- Schema 定义：`backend/app/schemas/openspec_course.py`
- 前端服务：`frontend/src/services/openspecCourseAdmin.ts`
- 前端组件：`frontend/src/components/Admin/CourseManagement/ImportExportDialog.tsx`
- 命令行工具：`course_data/` 目录

### 依赖

- 后端：FastAPI, SQLAlchemy, Pydantic
- 前端：React, TypeScript, Axios, Zustand

---

## 更新日志

### 2026-03-10

- ✅ 新增 JSON 导出/导入功能
- ✅ 新增 Markdown 导出/导入功能
- ✅ 新增命令行工具
- ✅ 新增前端导入/导出对话框
- ✅ 新增三种导入策略（merge/replace/skip_existing）
- ✅ 新增导入预览功能
