# OpenSpec 课程导入导出系统设计文档

## 概述

本文档描述 OpenSpec VibeCoding 课程数据的导入导出系统设计方案，支持将数据库中的课程数据导出为 Markdown 文档，并可以从 Markdown 文档重新导入到数据库。

## 目标

1. 导出数据库中的课程数据到 Markdown 文档
2. 支持人工编辑 Markdown 文档后重新导入
3. 导入前自动备份现有数据
4. 支持增量导入，保留用户进度
5. 确保数据不丢失

## 项目结构

```
tools/
├── scripts/
│   ├── course_export.py          # 导出脚本
│   ├── course_import.py          # 导入脚本
│   └── course_backup.py          # 备份脚本
├── course_data/
│   ├── openspec-vibecoding.md    # 导出的课程数据
│   └── backups/                  # 备份目录
│       └── 20260308_143022_001.json
└── backend/
    └── app/
        └── models/
            └── openspec_course.py  # 现有模型
```

## Markdown 文档格式

采用 YAML Frontmatter + Markdown 内容的混合格式：

```markdown
# OpenSpec VibeCoding 课程数据

## 章节：intro-vibe-coding

```yaml
order: 1
title: 第一章：最初的我 - 谨慎使用 AI 😰
chapter_type: story
is_locked: false
```

章节内容 (Markdown)...

---

## 测验：VibeCoding 入门测验

```yaml
chapter_slug: intro-vibe-coding
passing_score: 60
```

### 题目 1

```yaml
question_type: single
correct_answer: "2"
explanation: 答案解析
```

**题目内容：** 题目文本...

- A) 选项 A
- B) 选项 B
- C) 选项 C
- D) 选项 D
```

## 模块设计

### 1. 导出模块 (course_export.py)

**类：CourseExporter**

```python
class CourseExporter:
    """课程导出器"""

    def __init__(self, db_session):
        self.session = db_session

    def fetch_all_data(self) -> dict:
        """获取所有课程数据"""
        # 返回 chapters, quizzes, questions, options, resources

    def format_chapter(self, chapter) -> str:
        """格式化章节为 Markdown"""

    def format_quiz(self, quiz) -> str:
        """格式化测验为 Markdown"""

    def format_resource(self, resource) -> str:
        """格式化资源为 Markdown"""

    def export_to_md(self, output_path: str) -> ExportReport:
        """导出到 Markdown 文件"""
```

### 2. 备份模块 (course_backup.py)

**类：CourseBackup**

```python
class CourseBackup:
    """课程数据备份"""

    def __init__(self, db_session, backup_dir: str):
        self.session = db_session
        self.backup_dir = backup_dir

    def get_next_version(self) -> str:
        """获取下一个备份版本号"""

    def backup_data(self) -> str:
        """备份数据，返回备份文件路径"""

    def list_backups(self) -> List[dict]:
        """列出所有备份"""

    def restore(self, backup_file: str):
        """从备份恢复"""
```

### 3. 导入模块 (course_import.py)

**类：CourseImporter**

```python
class CourseImporter:
    """课程导入器"""

    def __init__(self, db_session, backup_dir: str):
        self.session = db_session
        self.backup_dir = backup_dir

    def parse_markdown(self, md_content: str) -> dict:
        """解析 Markdown 内容"""

    def validate_data(self, data: dict) -> List[ValidationError]:
        """验证数据完整性"""

    def import_incremental(self, data: dict) -> ImportReport:
        """增量导入数据"""

    def import_with_backup(self, markdown_path: str) -> ImportReport:
        """完整导入流程（含备份）"""
```

## 数据验证规则

1. **章节验证**
   - slug 必须唯一
   - order 必须连续且不重复
   - title 不能为空
   - content 不能为空

2. **测验验证**
   - chapter_slug 必须存在
   - passing_score 范围 0-100

3. **题目验证**
   - quiz_title 必须存在
   - question_type 必须是 single/multiple
   - correct_answer 必须有效

4. **资源验证**
   - chapter_slug 必须存在
   - resource_type 必须有效

## 增量导入逻辑

```python
for chapter in markdown_chapters:
    existing = session.query(Chapter).filter_by(slug=chapter.slug).first()
    if existing:
        # 更新现有章节
        update_chapter(existing, chapter)
        action = "更新"
    else:
        # 新增章节
        session.add(chapter)
        action = "新增"

    # 处理章节关联的测验和资源
    process_quizzes(chapter)
    process_resources(chapter)

# 提交事务
session.commit()
```

## 错误处理

```python
try:
    # 1. 解析 Markdown
    data = parse_markdown(content)

    # 2. 验证数据
    errors = validate_data(data)
    if errors:
        raise ValidationError(errors)

    # 3. 备份现有数据
    backup_file = backup_data()

    # 4. 增量导入
    report = import_incremental(data)

except ValidationError as e:
    # 数据验证失败，不执行任何写入
    log.error(f"验证失败：{e}")
    rollback()

except Exception as e:
    # 其他错误，回滚到备份
    log.error(f"导入失败：{e}")
    restore_from_backup(backup_file)
```

## 报表格式

### 导出报告
```
✅ 导出完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
章节数：5
测验数：3
题目数：6
选项数：18
资源数：3
输出文件：course_data/openspec-vibecoding.md
```

### 导入报告
```
✅ 导入完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
新增章节：0
更新章节：5
跳过章节：0
新增测验：0
更新测验：3
导入失败：0
备份文件：course_data/backups/20260308_143022_001.json
```

## 备份文件命名规则

格式：`YYYYMMDD_HHMMSS_NNN.json`

示例：
- `20260308_143022_001.json` - 3 月 8 日 14:30:22 第 1 次备份
- `20260308_151045_002.json` - 3 月 8 日 15:10:45 第 2 次备份

## 用户进度保护

导入脚本**不会**修改以下表：
- `openspec_user_progress` - 用户学习进度
- 任何以 `user_` 开头的表

这样可以确保：
- 用户已学习的章节进度不会丢失
- 用户的测验成绩保留
- 用户收藏的资源保留

## 实施步骤

1. 创建目录结构
2. 编写导出脚本
3. 编写备份脚本
4. 编写导入脚本
5. 测试导出功能
6. 测试导入功能
7. 验证用户进度保留
