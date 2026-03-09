# OpenSpec 课程导入导出工具

将 OpenSpec VibeCoding 课程数据导出为 Markdown 文档，支持编辑后重新导入，方便课程内容的管理、版本控制和团队协作。

## 功能特性

- ✅ **导出功能**：将数据库中的课程数据导出为结构化的 Markdown 文档
- ✅ **导入功能**：支持从 Markdown 文档导入课程数据到数据库
- ✅ **增量导入**：按 slug 匹配，存在则更新，不存在则新增
- ✅ **数据验证**：导入前验证数据完整性和一致性
- ✅ **自动备份**：导入前自动备份现有数据，防止数据丢失
- ✅ **失败回滚**：导入失败时自动回滚到备份状态
- ✅ **用户进度保护**：导入不影响用户学习进度
- ✅ **版本管理**：备份文件按日期 + 次数版本号命名

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
│       └── 20260309_100000_001.json
└── docs/plans/
    └── 2026-03-08-course-import-export-design.md
```

---

## 脚本一：导出脚本 (course_export.py)

### 功能说明

将数据库中的课程数据导出为 Markdown 文档，包含：
- 章节数据（slug, title, content, chapter_type 等）
- 测验数据（题目、选项、答案、解析）
- 资源数据（code_sample, template 等）

### 使用方法

#### 基本用法（导出到默认路径）
```bash
python3 scripts/course_export.py
```

#### 指定输出文件
```bash
python3 scripts/course_export.py -o my-course.md
python3 scripts/course_export.py --output /path/to/output.md
```

#### 查看帮助
```bash
python3 scripts/course_export.py --help
```

### 输出文件格式

导出的 Markdown 文件采用 YAML Frontmatter + Markdown 内容的混合格式：

```markdown
# OpenSpec VibeCoding 课程数据

> 导出时间：2026-03-09 10:00:00

---

## 章节：intro-vibe-coding

```yaml
order: 1
title: 第一章：最初的我 - 谨慎使用 AI 😰
chapter_type: story
is_locked: false
```

## 内容

还记得第一次接触 AI 编程时的我，心里充满了忐忑和不安...

---

## 测验：VibeCoding 入门测验

```yaml
passing_score: 60
```

### 题目 1

```yaml
question_type: single
correct_answer: 2
explanation: 清晰简洁的指令配合必要上下文是最高效的沟通方式。
```

**题目内容：** 初次使用 AI 编程时，以下哪种做法是正确的？

- A) 越详细越好，把所有想到的都写上去
- B) 越简单越好，AI 应该能理解我的意图
- C) 清晰简洁的指令，配合必要的上下文
- D) 直接让 AI 猜我想要什么

---

## 资源：Prompt 模板示例

```yaml
resource_type: code_sample
```

这是一个好的 Prompt 模板示例...
```

### 输出报告示例

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

### 注意事项

1. 确保数据库连接配置正确（检查 `backend/app/config/config.py` 中的 `DATABASE_URL`）
2. 如果数据库中没有课程数据，脚本会提示并退出
3. 导出文件默认保存在 `course_data/openspec-vibecoding.md`

---

## 脚本二：导入脚本 (course_import.py)

### 功能说明

从 Markdown 文档导入课程数据到数据库，支持：
- 增量导入（按 slug 匹配，存在则更新，不存在则新增）
- 数据验证（slug 唯一性、order 连续性、必填字段等）
- 自动备份（导入前自动备份现有数据）
- 失败回滚（导入失败时恢复到备份状态）

### 使用方法

#### 基本用法
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md
```

#### 模拟导入（不实际写入）
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md --dry-run
```

#### 强制导入（跳过验证）
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md --force
```

#### 不备份直接导入（不推荐）
```bash
python3 scripts/course_import.py course_data/openspec-vibecoding.md --no-backup
```

#### 查看帮助
```bash
python3 scripts/course_import.py --help
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `markdown_file` | Markdown 文件路径（必填） |
| `--dry-run` | 模拟导入模式，不实际写入数据库，用于预览导入结果 |
| `--force` | 强制导入，跳过数据验证步骤 |
| `--no-backup` | 不备份现有数据直接导入（数据有风险，操作需谨慎） |

### 工作流程

1. **读取 Markdown 文件** - 解析章节、测验、题目、资源数据
2. **数据验证** - 检查 slug 唯一性、order 连续性、必填字段等
3. **备份现有数据** - 自动生成备份文件（格式：`YYYYMMDD_HHMMSS_NNN.json`）
4. **增量导入** - 按 slug 匹配，存在则更新，不存在则新增
5. **生成报告** - 输出导入结果统计

### 导入报告示例

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
   - ai-problems: 第二章：遇到问题 - AI 乱改代码的困扰 🤯
     └─ 1 个测验
   ...

正在验证数据...
✅ 数据验证通过

正在备份现有数据...
✅ 备份完成：course_data/backups/20260309_100000_001.json

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
备份文件：course_data/backups/20260309_100000_001.json
```

### 数据验证规则

#### 章节验证
- ✅ slug 必须唯一
- ✅ order 必须连续且不重复
- ✅ title 不能为空
- ✅ content 不能为空
- ✅ chapter_type 必须是：story, code, quiz, video, quiz-only

#### 测验验证
- ✅ passing_score 范围必须在 0-100 之间

#### 题目验证
- ✅ question_type 必须是：single, multiple
- ✅ correct_answer 不能为空
- ✅ options 不能为空

#### 资源验证
- ✅ resource_type 必须是：code_sample, contrast, video, template, image

### 注意事项

1. **编辑 Markdown 时不要修改 YAML 块的格式**，否则可能无法正确解析
2. **导入前会删除不在 Markdown 中的测验和资源**，确保 Markdown 文件包含完整数据
3. **定期备份数据库**，以防意外数据丢失
4. **在生产环境使用前，先在测试环境验证**

### 常见问题

**Q: 提示"章节 slug 重复"？**
A: Markdown 文件中有两个章节使用了相同的 slug，检查并确保每个章节的 slug 唯一。

**Q: 提示"章节 order 重复"？**
A: 两个章节的 order 值相同，确保章节的 order 值连续且不重复。

**Q: 导入失败后如何恢复？**
A: 导入脚本会自动回滚到备份，或手动执行：
```bash
python3 scripts/course_backup.py --restore <备份文件>
```

**Q: 如何验证导入结果？**
A: 访问网站查看课程内容，或运行导出脚本重新导出对比。

---

## 脚本三：备份脚本 (course_backup.py)

### 功能说明

备份数据库中的课程数据到 JSON 文件，支持：
- 自动备份（全量备份课程数据）
- 版本管理（按日期 + 次数版本号命名）
- 备份列表（查看所有备份文件及其统计信息）
- 数据恢复（从备份文件恢复数据）
- 模拟恢复（预览恢复结果，不实际写入）

### 使用方法

#### 备份数据
```bash
python3 scripts/course_backup.py
```

#### 列出所有备份
```bash
python3 scripts/course_backup.py --list
```

#### 从备份恢复
```bash
python3 scripts/course_backup.py --restore course_data/backups/20260309_100000_001.json
```

#### 模拟恢复（不实际写入）
```bash
python3 scripts/course_backup.py --restore course_data/backups/20260309_100000_001.json --dry-run
```

#### 查看帮助
```bash
python3 scripts/course_backup.py --help
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--list` | 列出所有备份文件及其统计信息 |
| `--restore <file>` | 从指定的备份文件恢复数据 |
| `--dry-run` | 模拟模式，不实际写入数据库 |

### 备份文件命名规则

格式：`YYYYMMDD_HHMMSS_NNN.json`

示例：
- `20260309_100000_001.json` - 3 月 9 日 10:00:00 第 1 次备份
- `20260309_143022_002.json` - 3 月 9 日 14:30:22 第 2 次备份

同一天内备份序号自动递增。

### 备份文件内容

备份文件为 JSON 格式，包含：

```json
{
  "backup_timestamp": "2026-03-09T10:00:00",
  "backup_stats": {
    "chapters_count": 5,
    "quizzes_count": 3,
    "questions_count": 6,
    "options_count": 24,
    "resources_count": 3
  },
  "chapters": [...],
  "quizzes": [...],
  "quiz_questions": [...],
  "quiz_options": [...],
  "resources": [...]
}
```

### 输出示例

#### 备份输出
```
============================================================
OpenSpec 课程数据备份工具
============================================================

正在连接数据库...
✅ 数据库连接成功，共有 5 个章节

正在备份数据...

✅ 备份完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
章节数：5
测验数：3
题目数：6
选项数：24
资源数：3
备份文件：course_data/backups/20260309_100000_001.json
```

#### 列出备份输出
```
============================================================
OpenSpec 课程数据备份工具
============================================================

正在连接数据库...
找到 3 个备份:

  📄 20260309_100000_001.json
     时间：2026-03-09T10:00:00
     章节：5, 测验：3, 资源：3

  📄 20260309_143022_002.json
     时间：2026-03-09T14:30:22
     章节：5, 测验：3, 资源：3

  📄 20260309_150000_003.json
     时间：2026-03-09T15:00:00
     章节：5, 测验：3, 资源：3
```

#### 恢复输出
```
============================================================
OpenSpec 课程数据备份工具
============================================================

正在从备份恢复：course_data/backups/20260309_100000_001.json

✅ 恢复完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
恢复章节：5
恢复测验：3
恢复题目：6
恢复选项：24
恢复资源：3
```

### 注意事项

1. **定期备份**：建议每次修改课程数据前后备份
2. **备份存储**：定期将备份文件复制到其他位置保存（如云盘、外部硬盘）
3. **恢复测试**：定期测试恢复功能，确保备份文件可用
4. **空间管理**：定期清理过期的备份文件，释放磁盘空间

### 常见问题

**Q: 备份文件保存在哪里？**
A: 默认保存在 `course_data/backups/` 目录。

**Q: 如何手动删除备份文件？**
A: 直接删除 `course_data/backups/` 目录下的文件即可。

**Q: 恢复时会覆盖现有数据吗？**
A: 恢复会按 slug 匹配更新现有数据，不会删除用户进度数据。

**Q: 备份文件可以手动编辑吗？**
A: 可以，但请保持 JSON 格式正确，否则恢复时可能失败。

---

## 完整工作流

### 场景一：修改课程内容

1. **导出当前数据**
   ```bash
   python3 scripts/course_export.py
   ```

2. **编辑 Markdown 文件**
   - 使用文本编辑器打开 `course_data/openspec-vibecoding.md`
   - 修改课程内容、测验题目等
   - 保存文件

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

### 场景二：回滚到之前的版本

1. **查看备份列表**
   ```bash
   python3 scripts/course_backup.py --list
   ```

2. **从备份恢复**
   ```bash
   python3 scripts/course_backup.py --restore course_data/backups/20260309_100000_001.json
   ```

3. **验证恢复结果**
   - 访问网站查看课程内容

### 场景三：团队协作

1. **导出课程数据**
   ```bash
   python3 scripts/course_export.py
   ```

2. **将 Markdown 文件提交到 Git**
   ```bash
   git add course_data/openspec-vibecoding.md
   git commit -m "更新课程内容"
   git push
   ```

3. **团队成员拉取并导入**
   ```bash
   git pull
   python3 scripts/course_import.py course_data/openspec-vibecoding.md
   ```

---

## 依赖

- Python 3.10+
- SQLAlchemy
- PyYAML（可选，未安装时使用内置解析器）

## 环境要求

- 数据库连接配置正确（检查 `backend/app/config/config.py` 中的 `DATABASE_URL`）
- 有读写数据库的权限
- 确保 `course_data/` 和 `course_data/backups/` 目录存在且有写权限

## 测试验证

所有脚本已经过测试，确保功能正常：

```bash
# 测试导出
python3 scripts/course_export.py -o course_data/test-export.md

# 测试导入（模拟）
python3 scripts/course_import.py course_data/test-export.md --dry-run

# 测试备份
python3 scripts/course_backup.py

# 测试备份列表
python3 scripts/course_backup.py --list

# 清理测试文件
rm -f course_data/test-export.md
```

---

## Git 双远程仓库同步工具

本目录包含两个用于管理双远程仓库（GitHub + Gitee）的 Python 脚本。

### 前置条件

确保已配置两个远程仓库：

```bash
# 添加 GitHub 远程仓库
git remote add github git@github.com:USERNAME/tools.git

# 添加 Gitee 远程仓库（或使用 origin）
git remote add origin git@gitee.com:USERNAME/tools.git

# 验证配置
git remote -v
```

### 脚本一：sync_to_remotes.py - 双仓库同步推送

**功能**：将本地提交同时推送到所有配置的远程仓库

**主要特性**：
- ✅ 自动检测远程分支是否存在
- ✅ 推送前自动 rebase 更新本地代码（避免推送失败）
- ✅ 首次推送新分支时自动设置上游分支
- ✅ 支持排除指定仓库、强制推送等选项

**使用方法**：

```bash
# 基本用法（推送到所有远程仓库，推送前自动 rebase 更新）
python scripts/sync_to_remotes.py

# 指定分支
python scripts/sync_to_remotes.py -b main

# 强制推送（谨慎使用）
python scripts/sync_to_remotes.py -f

# 排除特定远程仓库（只推送到 github）
python scripts/sync_to_remotes.py -e origin

# 排除特定远程仓库（只推送到 gitee）
python scripts/sync_to_remotes.py -e github

# 跳过推送前的 rebase 更新（直接推送）
python scripts/sync_to_remotes.py --skip-rebase
```

**参数说明**：
| 参数 | 说明 |
|------|------|
| `-p, --path` | Git 仓库路径，默认为当前目录 |
| `-b, --branch` | 指定要推送的分支，默认为当前分支 |
| `-f, --force` | 强制推送 |
| `-e, --exclude` | 要排除的远程仓库名称 |
| `--skip-rebase` | 跳过推送前的 rebase 更新 |
| `-v, --verbose` | 显示详细信息 |

### 脚本二：rebase_update.py - Rebase 方式更新

**功能**：使用 rebase 方式从远程仓库更新本地代码，保持提交历史线性

**使用方法**：

```bash
# 从默认 remote 更新
python scripts/rebase_update.py

# 从指定 remote 更新（如 gitee）
python scripts/rebase_update.py -r origin

# 从 github 更新
python scripts/rebase_update.py -r github

# 指定分支
python scripts/rebase_update.py -b main

# 冲突时自动中止 rebase
python scripts/rebase_update.py --abort-on-conflict

# 中止正在进行的 rebase
python scripts/rebase_update.py --abort
```

**参数说明**：
| 参数 | 说明 |
|------|------|
| `-p, --path` | Git 仓库路径，默认为当前目录 |
| `-b, --branch` | 指定要更新的分支，默认为当前分支 |
| `-r, --remote` | 指定远程仓库名称 |
| `--abort` | 中止正在进行的 rebase |
| `--abort-on-conflict` | 冲突时自动中止 rebase |

### 典型工作流

#### 场景 1：日常开发，推送变更到两个仓库

```bash
# 1. 提交本地更改
git add .
git commit -m "feat: 添加新功能"

# 2. 同步到两个远程仓库（自动 rebase 更新）
python scripts/sync_to_remotes.py
```

#### 场景 2：本地落后于远程，需要更新后推送

```bash
# 脚本会自动检测并 rebase 更新
python scripts/sync_to_remotes.py

# 如果 rebase 失败，手动使用 rebase_update.py
python scripts/rebase_update.py -r origin

# 解决冲突后再次同步
python scripts/sync_to_remotes.py
```

#### 场景 3：新建分支首次推送

```bash
# 创建新分支
git checkout -b feature/new-feature

# 提交更改
git add .
git commit -m "feat: 新功能"

# 同步脚本会自动检测远程分支不存在，执行首次推送并设置上游
python scripts/sync_to_remotes.py
```

#### 场景 4：跳过 rebase 直接推送

```bash
# 确定不需要更新时，跳过 rebase 直接推送
python scripts/sync_to_remotes.py --skip-rebase
```

### 注意事项

1. **自动 Rebase 更新**：脚本默认在推送前自动 rebase 更新本地代码。如果本地落后于远程，会自动执行 rebase。

2. **Rebase 冲突处理**：如果 rebase 过程中出现冲突：
   - 手动编辑冲突文件解决冲突
   - 运行 `git add <文件名>` 标记为解决
   - 运行 `git rebase --continue` 继续
   - 或运行 `git rebase --abort` 中止

3. **首次推送新分支**：当远程仓库不存在当前分支时，脚本会自动使用 `-u` 参数设置上游分支。

4. **跳过 Rebase**：如果确定本地是最新且不想 rebase，使用 `--skip-rebase` 参数。

5. **推送顺序**：脚本会自动从第一个配置的远程仓库（通常是 origin/gitee）fetch 更新进行 rebase。
