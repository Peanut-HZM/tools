# 课程数据导入/导出功能设计文档

**创建日期**: 2026-03-10
**作者**: AI Assistant
**状态**: 设计中

---

## 1. 概述

### 1.1 目标

为 OpenSpec 课程管理系统实现完整的课程数据导入/导出功能，支持：
- 将课程数据（章节、测验、资源）导出为 JSON 格式备份
- 从 JSON 备份文件导入恢复课程数据
- 导出章节内容为可编辑的 Markdown 文档
- 从 Markdown 文档更新章节内容

### 1.2 使用场景

| 场景 | 描述 |
|------|------|
| 数据备份 | 定期导出课程数据，防止数据丢失 |
| 数据迁移 | 在不同环境间迁移课程数据 |
| 离线编辑 | 导出 Markdown 文档，离线编辑后导入更新 |
| 版本管理 | 使用 Markdown 文件进行版本控制 |
| 批量修改 | 通过修改导出文件批量更新课程内容 |

---

## 2. 架构设计

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端界面层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │
│  │ 课程管理列表 │  │  课程详情页  │  │  导入/导出对话框     │     │
│  └─────────────┘  └─────────────┘  └─────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API 网关层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ /export     │  │ /import     │  │ /export-md  │             │
│  │ /import-md  │  │ /backup     │  │ /restore    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        服务层                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           CourseExportService / CourseImportService     │   │
│  │  - export_to_json()    - import_from_json()             │   │
│  │  - export_to_markdown() - import_from_markdown()        │   │
│  │  - validate_import_data() - resolve_conflicts()         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据访问层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Chapter    │  │   Quiz      │  │  Resource   │             │
│  │  Repository │  │  Repository │  │  Repository │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据库                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  openspec_course_chapters / quizzes / questions / ...   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据格式

#### 2.2.1 JSON 导出格式

```json
{
  "version": "1.0",
  "export_timestamp": "2026-03-10T12:00:00Z",
  "course_id": 1,
  "course_title": "OpenSpec VibeCoding 互动课程",
  "chapters": [
    {
      "slug": "intro-vibe-coding",
      "title": "第一章：最初的我 - 谨慎使用 AI 😰",
      "order": 1,
      "content": "## 故事开始...",
      "chapter_type": "story",
      "video_url": null,
      "is_locked": false,
      "required_quiz_slug": "vibeCoding-quiz-1",
      "quizzes": [
        {
          "slug": "vibeCoding-quiz-1",
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
                {"option_text": "越详细越好，把所有想到的都写上去", "option_index": 0},
                {"option_text": "越简单越好，AI 应该能理解我的意图", "option_index": 1},
                {"option_text": "清晰简洁的指令，配合必要的上下文", "option_index": 2},
                {"option_text": "直接让 AI 猜我想要什么", "option_index": 3}
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
          "extra_data": {"template": "请帮我 [任务]，需要 [要求]，使用 [技术栈]"}
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

#### 2.2.2 Markdown 导出格式

```markdown
---
slug: intro-vibe-coding
title: 第一章：最初的我 - 谨慎使用 AI 😰
order: 1
chapter_type: story
is_locked: false
video_url: null
---

## 故事开始...

还记得第一次接触 AI 编程时的我，心里充满了忐忑和不安。

### 我的心态

- 😰 **生怕 AI 理解错了**：每个需求都要写超级详细
- 📝 **复制粘贴所有代码**：要让 AI 改代码？先把整段代码贴给它

---

## 测验：VibeCoding 入门测验

**及格分数**: 60

### 问题 1

初次使用 AI 编程时，以下哪种做法是正确的？

- [ ] 越详细越好，把所有想到的都写上去
- [ ] 越简单越好，AI 应该能理解我的意图
- [x] 清晰简洁的指令，配合必要的上下文
- [ ] 直接让 AI 猜我想要什么

**答案**: 2
**解析**: 清晰简洁的指令配合必要上下文是最高效的沟通方式。

---

## 资源

### Prompt 模板示例

**类型**: code_sample

这是一个好的 Prompt 模板示例，展示了如何清晰地描述需求。

**元数据**:
```json
{"template": "请帮我 [任务]，需要 [要求]，使用 [技术栈]"}
```
```

---

## 3. API 设计

### 3.1 导出课程数据

```
POST /api/openspec-course/{course_id}/export
```

**请求参数**: 无

**响应**:
```json
{
  "success": true,
  "data": { /* JSON 导出数据 */ },
  "download_url": "/api/openspec-course/export/download?file=xxx.json"
}
```

### 3.2 导入课程数据

```
POST /api/openspec-course/{course_id}/import
Content-Type: multipart/form-data
```

**请求参数**:
- `file`: 上传的 JSON 文件
- `strategy`: 导入策略 (`merge` | `replace` | `skip_existing`)

**响应**:
```json
{
  "success": true,
  "message": "导入成功",
  "imported_stats": {
    "chapters_imported": 5,
    "chapters_updated": 0,
    "chapters_skipped": 0,
    "quizzes_imported": 3,
    "resources_imported": 3
  },
  "warnings": []
}
```

### 3.3 导出章节为 Markdown

```
GET /api/openspec-course/chapters/{chapter_id}/export-md
```

**响应**:
```
Content-Type: text/markdown
Content-Disposition: attachment; filename="chapter-1.md"

---
slug: intro-vibe-coding
...
---

章节内容...
```

### 3.4 从 Markdown 更新章节

```
PUT /api/openspec-course/chapters/{chapter_id}/import-md
Content-Type: multipart/form-data
```

**请求参数**:
- `file`: 上传的 Markdown 文件
- `preview`: 是否仅预览不实际导入 (boolean)

**响应 (preview=true)**:
```json
{
  "success": true,
  "preview": {
    "original": { "title": "...", "content": "..." },
    "proposed": { "title": "...", "content": "..." },
    "changes": ["content 字段将更新", "title 字段不变"]
  }
}
```

---

## 4. 实现计划

### 4.1 后端实现

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 4.1.1 | 创建 `CourseExportService` 服务类 | P0 |
| 4.1.2 | 实现 `export_to_json()` 方法 | P0 |
| 4.1.3 | 实现 `export_to_markdown()` 方法 | P0 |
| 4.1.4 | 创建 `CourseImportService` 服务类 | P0 |
| 4.1.5 | 实现 `import_from_json()` 方法 | P0 |
| 4.1.6 | 实现 `import_from_markdown()` 方法 | P1 |
| 4.1.7 | 实现数据验证和冲突检测 | P1 |
| 4.1.8 | 添加 API 路由 | P0 |
| 4.1.9 | 添加 Pydantic Schema 定义 | P0 |

### 4.2 命令行工具

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 4.2.1 | 创建 `export_course_data.py` 脚本 | P0 |
| 4.2.2 | 创建 `import_course_data.py` 脚本 | P0 |
| 4.2.3 | 创建 `export_chapters_md.py` 脚本 | P1 |
| 4.2.4 | 创建 `import_chapters_md.py` 脚本 | P1 |

### 4.3 前端实现

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 4.3.1 | 添加导入/导出 API 服务方法 | P0 |
| 4.3.2 | 创建导入/导出对话框组件 | P0 |
| 4.3.3 | 在课程详情页添加导入/导出按钮 | P0 |
| 4.3.4 | 实现文件上传和预览功能 | P1 |
| 4.3.5 | 添加导入结果展示和错误处理 | P1 |

---

## 5. 错误处理

### 5.1 导出错误

| 错误码 | 描述 | 处理方式 |
|--------|------|----------|
| EXPORT_COURSE_NOT_FOUND | 课程不存在 | 返回 404 |
| EXPORT_NO_DATA | 课程没有数据 | 返回空数据集 |
| EXPORT_FILE_ERROR | 文件生成失败 | 返回 500 |

### 5.2 导入错误

| 错误码 | 描述 | 处理方式 |
|--------|------|----------|
| IMPORT_INVALID_FORMAT | JSON 格式无效 | 返回 400，提示具体错误 |
| IMPORT_MISSING_FIELDS | 缺少必填字段 | 返回 400，列出缺失字段 |
| IMPORT_SLUG_CONFLICT | Slug 冲突 | 根据策略处理或返回冲突信息 |
| IMPORT_FILE_TOO_LARGE | 文件过大 | 返回 413 |

---

## 6. 安全考虑

1. **文件上传限制**
   - 最大文件大小：10MB
   - 仅允许 `.json` 和 `.md` 文件
   - 文件类型白名单验证

2. **数据验证**
   - 严格的 JSON Schema 验证
   - Markdown frontmatter 解析验证
   - 防止 XSS 攻击（内容转义）

3. **权限控制**
   - 仅管理员可执行导入/导出操作
   - JWT 令牌验证

4. **数据完整性**
   - 事务性导入（全部成功或全部失败）
   - 导入前自动备份当前数据

---

## 7. 测试计划

### 7.1 单元测试

- [ ] `export_to_json()` 输出格式验证
- [ ] `export_to_markdown()` 格式验证
- [ ] `import_from_json()` 数据解析验证
- [ ] 冲突检测逻辑验证
- [ ] 数据验证错误处理

### 7.2 集成测试

- [ ] 完整导出流程测试
- [ ] 完整导入流程测试
- [ ] 大文件处理测试
- [ ] 并发导入测试

### 7.3 端到端测试

- [ ] 前端导出按钮点击 → 文件下载
- [ ] 前端导入文件 → 结果显示
- [ ] Markdown 编辑 → 导入更新

---

## 8. 验收标准

1. ✅ 能够将课程数据完整导出为 JSON 文件
2. ✅ 能够从 JSON 文件导入恢复课程数据
3. ✅ 能够导出章节为 Markdown 文档
4. ✅ 能够从 Markdown 文档更新章节内容
5. ✅ 导入时正确处理数据冲突
6. ✅ 前端界面友好，错误提示清晰
7. ✅ 命令行工具可独立使用
8. ✅ 所有测试通过

---

## 9. 后续优化

1. 支持导出为 PDF 格式
2. 支持增量导出（只导出变更内容）
3. 支持 Git 集成（自动提交 Markdown 变更）
4. 支持定时自动备份
5. 支持导出到云存储（阿里云 OSS、S3 等）
