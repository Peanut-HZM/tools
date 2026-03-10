# 设计文档：OpenSpec VibeCoding 实践指南课程优化

## Context

**背景**：现有课程 #4 "OpenSpec VibeCoding 实践指南" 是一个 5 章节的入门课程，采用故事化叙述方式。课程已导出为 JSON 格式（`course_data/course-export-2026-03-10.json`），可通过导入 API 更新。

**现状**：
- 课程内容偏向故事化，技术深度不足
- OpenSpec 技能系统讲解简略，缺乏实操指导
- 测验和资源数量有限，不足以支撑实战学习

**约束**：
- 保持现有章节结构（5 章）
- 使用现有课程数据模型和导入 API
- 内容格式为 Markdown

**利益相关者**：
- 学习者：有经验但想提升 AI 协作效率的开发者
- 维护者：课程内容的后续更新团队

## Goals / Non-Goals

**Goals:**
- 优化 5 章内容，增加 Rules 详解和 OpenSpec 技能系统讲解
- 每章包含 3-5 道测验题和 2+ 个配套资源
- 提供多个实战案例，展示 OpenSpec 在不同场景下的应用
- 内容技术深度达到中等水平（用途 + 原理 + 最佳实践）

**Non-Goals:**
- 不改变课程数据结构
- 不增加新的章节
- 不涉及视频内容制作
- 不创建新的 API 接口

## Decisions

### 决策 1：内容组织方式

**选择**：保持现有章节结构，逐章优化内容

**理由**：
- 保持学习路径的连贯性
- 减少学习者的认知负担
- 便于渐进式学习

**替代方案**：
- 重新设计章节结构 → 过于激进，破坏现有学习体验
- 模块化设计 → 适合查阅，但不利于系统学习

### 决策 2：技术深度

**选择**：中等深度（用途 + 原理 + 最佳实践）

**理由**：
- 目标受众是有经验的开发者，需要一定的技术深度
- 过深会偏离实战指南的定位
- 过浅无法满足学习需求

### 决策 3：案例来源

**选择**：多个项目案例结合

**理由**：
- 展示 OpenSpec 在不同场景下的应用
- 增强课程的普适性
- 提供更全面的学习体验

### 决策 4：测验和资源设计

**选择**：重新设计，与优化后的内容匹配

**理由**：
- 现有测验基于故事化内容，不适合新技术深度
- 资源需要配合实战内容提供可复用模板

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 内容过多导致课程冗长 | 学习者可能失去耐心 | 保持中等深度，进阶内容放入延伸阅读 |
| 技术细节错误 | 误导学习者 | 参考官方文档和现有技能文件，进行多轮验证 |
| 导入失败 | 数据无法更新 | 先预览导入，确认无误再执行，保留备份 |
| 测验难度不当 | 学习者挫败感或过于简单 | 设置合理及格分数 (60%)，提供详细解析 |

## Migration Plan

### 部署步骤

1. **备份现有数据**
   ```bash
   # 导出当前课程数据作为备份
   curl http://localhost:19092/api/openspec-course/export -o course-backup.json
   ```

2. **预览导入**
   ```bash
   # 使用 REPLACE 策略预览导入
   curl -X POST http://localhost:19092/api/openspec-course/import/preview \
     -H "Content-Type: application/json" \
     -d @course-export-optimized.json
   ```

3. **执行导入**
   ```bash
   # 确认预览无误后执行导入
   curl -X POST http://localhost:19092/api/openspec-course/import \
     -H "Content-Type: application/json" \
     -d @course-export-optimized.json \
     -G -d strategy=replace
   ```

4. **验证**
   - 访问课程详情页面检查章节内容
   - 测试测验功能
   - 验证资源下载

### 回滚策略

如导入后发现问题，使用备份数据恢复：
```bash
curl -X POST http://localhost:19092/api/openspec-course/import \
  -H "Content-Type: application/json" \
  -d @course-backup.json \
  -G -d strategy=replace
```

## Open Questions

- 无（所有设计决策已明确）
