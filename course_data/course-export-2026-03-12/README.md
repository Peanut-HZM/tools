# OpenSpec VibeCoding 实践指南 - 导出包

**导出时间**: 2026-03-12T16:08:02.488950
**导出版本**: 1.0

## 统计信息

- 章节数量：6
- 测验数量：6
- 问题数量：31
- 选项数量：124
- 资源数量：14

## 文件结构

```
OpenSpec VibeCoding 实践指南-export/
├── README.md                  # 本文件
├── course-export.json         # 完整课程数据（JSON 格式）
└── markdowns/                 # 章节 Markdown 文件目录
    ├── chapter-1.md           # 第 1 章
    ├── chapter-2.md           # 第 2 章
    └── ...
```

## 使用说明

### 导入 JSON 文件

1. 在管理后台点击"导入课程"
2. 选择 `course-export.json` 文件
3. 选择导入策略（合并/替换/跳过）
4. 确认导入

### 导入 Markdown 文件

Markdown 文件包含完整的章节内容、测验和资源数据，可直接用于版本控制或手动编辑。

每个 Markdown 文件包含：
- Frontmatter 元数据（slug, title, order, chapter_type 等）
- 章节正文内容
- 测验部分（如果有）
- 资源部分（如果有）

## 注意事项

- 导入前建议先备份现有数据
- Markdown 文件的 Frontmatter 必须保持有效的 YAML 格式
- 测验和资源部分由分隔符 `---` 标识，不要手动修改这些区域
