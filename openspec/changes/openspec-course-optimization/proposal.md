# 提案：OpenSpec VibeCoding 实践指南课程优化

## Why

现有课程 (#4 "OpenSpec VibeCoding 实践指南") 内容偏向故事化叙述，缺乏对 OpenSpec 核心概念和技能系统的深入讲解。开发者学习后仍不清楚如何实际使用 OpenSpec 进行项目开发。本课程优化旨在打造面向有经验开发者的实战指南，重点讲解 Rules、OpenSpec 核心概念、技能系统的使用方法和实战案例。

## What Changes

- **内容优化**：保持现有 5 章结构，逐章增强技术深度和实战内容
- **Rules 详解**：新增 Rules 概念、编写指南、实战案例和效果对比
- **OpenSpec 技能系统**：新增 7 个核心技能的详细讲解（用途、场景、方法、案例）
- **实战案例**：增加多个真实项目案例，展示 OpenSpec 在不同场景下的应用
- **测验重新设计**：每章 3-5 题，包含基础题、应用题和场景题
- **资源重新设计**：每章 2+ 个配套资源（模板、检查清单、实战案例）

## Capabilities

### New Capabilities
- `course-content-optimization`: 课程章节内容优化，包含 Rules 详解、OpenSpec 技能系统讲解、实战案例
- `course-assessment-redesign`: 测验重新设计，每章 3-5 题，覆盖基础、应用和场景分析
- `course-resources-expansion`: 资源扩展，每章 2+ 个配套资源（模板、检查清单、指南）

### Modified Capabilities
- 无（现有课程数据结构不变，仅优化内容）

## Impact

- ** affected code**: 无代码变更，仅更新课程数据
- **APIs**: 使用现有 `/api/openspec-course/import` API 导入课程数据
- **Dependencies**: 依赖现有课程导入/导出服务
- **Systems**: 课程管理系统（后台管理页面）
