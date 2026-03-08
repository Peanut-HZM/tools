# OpenSpec 课程导入导出工具

将 OpenSpec VibeCoding 课程数据导出为 Markdown 文档，支持编辑后重新导入，方便课程内容的管理和版本控制。

## 功能特性

- ✅ **导出功能**：将数据库中的课程数据导出为结构化的 Markdown 文档
- ✅ **导入功能**：支持从 Markdown 文档导入课程数据到数据库
- ✅ **增量导入**：按 slug 匹配，存在则更新，不存在则新增
- ✅ **数据验证**：导入前验证数据完整性和一致性
- ✅ **自动备份**：导入前自动备份现有数据，防止数据丢失
- ✅ **失败回滚**：导入失败时自动回滚到备份状态
- ✅ **用户进度保护**：导入不影响用户学习进度

## 目录结构

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
└── docs/plans/
    └── 2026-03-08-course-import-export-design.md
```

## 使用方法

### 1. 导出课程数据

```bash
# 导出数据库中的课程数据到 Markdown 文件
python3 scripts/course_export.py
```

输出：
```
============================================================
OpenSpec 课程数据导出工具
============================================================

正在连接数据库...
✅ 数据库连接成功，共有 5 个章节

正在导出课程数据到：course_data/openspec-vibecoding.md

✅ 导出完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
章节数：5
测验数：3
题目数：6
选项数：24
资源数：3
输出文件：course_data/openspec-vibecoding.md
```

### 2. 编辑课程数据

使用任意文本编辑器编辑 `course_data/openspec-vibecoding.md` 文件，修改课程内容、测验题目等。

**Markdown 格式示例：**

```markdown
## 章节：intro-vibe-coding

```yaml
order: 1
title: 第一章：最初的我 - 谨慎使用 AI 😰
chapter_type: story
is_locked: false
```

## 内容

这里是章节的 Markdown 内容...

---

## 测验：VibeCoding 入门测验

```yaml
passing_score: 60
```

### 题目 1

```yaml
question_type: single
correct_answer: 2
explanation: 答案解析
```

**题目内容：** 初次使用 AI 编程时，以下哪种做法是正确的？

- A) 越详细越好，把所有想到的都写上去
- B) 越简单越好，AI 应该能理解我的意图
- C) 清晰简洁的指令，配合必要的上下文
- D) 直接让 AI 猜我想要什么
```

### 3. 导入课程数据

```bash
# 模拟导入（不实际写入，预览结果）
python3 scripts/course_import.py course_data/openspec-vibecoding.md --dry-run

# 实际导入（会自动备份现有数据）
python3 scripts/course_import.py course_data/openspec-vibecoding.md

# 强制导入（跳过数据验证）
python3 scripts/course_import.py course_data/openspec-vibecoding.md --force

# 不备份直接导入（不推荐）
python3 scripts/course_import.py course_data/openspec-vibecoding.md --no-backup
```

输出：
```
============================================================
OpenSpec 课程数据导入工具
============================================================

读取文件：course_data/openspec-vibecoding.md
正在连接数据库...
正在解析 Markdown 内容...
✅ 解析成功，共 5 个章节
   - intro-vibe-coding: 第一章：最初的我 - 谨慎使用 AI 😰
     └─ 1 个测验
     └─ 1 个资源
   ...

正在验证数据...
✅ 数据验证通过

正在备份现有数据...
✅ 备份完成：course_data/backups/20260308_234935_001.json

正在导入数据...

✅ 导入完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
新增章节：0
更新章节：5
新增测验：0
更新测验：3
新增题目：0
更新题目：6
新增资源：0
更新资源：3
备份文件：course_data/backups/20260308_234935_001.json
```

### 4. 备份管理

```bash
# 备份当前数据
python3 scripts/course_backup.py

# 列出所有备份
python3 scripts/course_backup.py --list

# 从备份恢复
python3 scripts/course_backup.py --restore course_data/backups/20260308_234935_001.json

# 模拟恢复（不实际写入）
python3 scripts/course_backup.py --restore course_data/backups/20260308_234935_001.json --dry-run
```

## 数据验证规则

导入脚本会自动验证以下规则：

### 章节验证
- ✅ slug 必须唯一
- ✅ order 必须连续且不重复
- ✅ title 不能为空
- ✅ content 不能为空
- ✅ chapter_type 必须是：story, code, quiz, video, quiz-only

### 测验验证
- ✅ passing_score 范围必须在 0-100 之间
- ✅ chapter_slug 必须存在

### 题目验证
- ✅ question_type 必须是：single, multiple
- ✅ correct_answer 不能为空
- ✅ options 不能为空

### 资源验证
- ✅ resource_type 必须是：code_sample, contrast, video, template, image

## 备份文件命名规则

格式：`YYYYMMDD_HHMMSS_NNN.json`

示例：
- `20260308_143022_001.json` - 3 月 8 日 14:30:22 第 1 次备份
- `20260308_151045_002.json` - 3 月 8 日 15:10:45 第 2 次备份

## 用户进度保护

导入脚本**不会**修改以下表：
- `openspec_user_progress` - 用户学习进度

这样可以确保：
- ✅ 用户已学习的章节进度不会丢失
- ✅ 用户的测验成绩保留
- ✅ 用户收藏的资源保留

## 完整工作流

1. **导出当前数据**
   ```bash
   python3 scripts/course_export.py
   ```

2. **编辑 Markdown 文件**
   - 修改课程内容
   - 添加/删除章节
   - 更新测验题目

3. **模拟导入测试**
   ```bash
   python3 scripts/course_import.py course_data/openspec-vibecoding.md --dry-run
   ```

4. **执行导入**
   ```bash
   python3 scripts/course_import.py course_data/openspec-vibecoding.md
   ```

5. **验证结果**
   - 检查导入报告
   - 访问网站查看更新内容

## 故障排除

### 问题 1：导入时提示"章节 slug 重复"
**原因**：Markdown 文件中有两个章节使用了相同的 slug。
**解决**：检查并确保每个章节的 slug 唯一。

### 问题 2：导入时提示"章节 order 重复"
**原因**：两个章节的 order 值相同。
**解决**：确保章节的 order 值连续且不重复。

### 问题 3：导入失败后如何恢复
**方法 1**：导入脚本会自动回滚到备份。
**方法 2**：手动从备份恢复：
```bash
python3 scripts/course_backup.py --restore course_data/backups/YYYYMMDD_HHMMSS_NNN.json
```

### 问题 4：如何查看备份内容
备份文件是 JSON 格式，可以用任意文本编辑器打开查看。

## 注意事项

1. **编辑 Markdown 时不要修改 YAML 块的格式**，否则可能无法正确解析。
2. **导入前会删除不在 Markdown 中的测验和资源**，确保 Markdown 文件包含完整数据。
3. **定期备份数据库**，以防意外数据丢失。
4. **在生产环境使用前，先在测试环境验证**。

## 依赖

- Python 3.10+
- SQLAlchemy
- PyYAML（可选，未安装时使用内置解析器）
