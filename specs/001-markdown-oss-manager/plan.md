# Implementation Plan: Markdown OSS 文件管理功能

**Branch**: `001-markdown-oss-manager` | **Date**: 2026-02-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-markdown-oss-manager/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

为 Markdown 编辑器添加阿里云 OSS 文件管理功能，支持用户上传、浏览、编辑云端 Markdown 文件。核心功能包括：统一文件树展示本地和 OSS 文件（带视觉区分）、自动版本历史管理（存储在 OSS versions/ 前缀下）、分块上传大文件、离线编辑本地缓存与自动同步。后端已具备 OSS API 基础，主要工作集中在前端集成：扩展 FileTree 组件支持 OSS 文件列表、添加版本历史 UI、实现 IndexedDB 离线缓存机制。

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript/React 18 (Frontend)
**Primary Dependencies**: FastAPI, oss2 (阿里云 OSS SDK), React, Zustand (状态管理), IndexedDB (离线缓存)
**Storage**: Aliyun OSS (文件存储), IndexedDB (浏览器本地缓存)
**Testing**: pytest (Backend), React Testing Library (Frontend)
**Target Platform**: Web application (Chrome, Firefox, Safari, Edge)
**Project Type**: web (前后端分离架构)
**Performance Goals**:
- 文件列表加载 < 2s (100个文件)
- 文件保存 < 3s (95%成功率)
- 版本历史加载 < 2s
- 离线同步 < 10s (网络恢复后)
**Constraints**:
- 单文件大小限制 10MB（分块上传可突破）
- 版本历史保留 30 天
- 支持 1000 个文件以内（无需复杂分页）
- 用户数据完全隔离（user_id 前缀）
**Scale/Scope**:
- 单用户文件数 < 1000
- 版本历史数 < 100/文件
- 并发用户依赖 OSS 服务能力

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Architecture Principles**:
- ✅ 前后端分离，通过 REST API 通信
- ✅ 用户数据隔离（user_id 前缀路径）
- ✅ 离线优先，支持本地缓存和自动同步
- ✅ 版本控制，自动保存历史版本到独立前缀

**Code Quality**:
- ✅ 使用 TypeScript 类型安全
- ✅ 遵循 React Hooks 最佳实践
- ✅ API 错误处理和用户友好提示
- ✅ 组件化设计，可复用的文件树组件

**Testing Strategy**:
- ✅ API 单元测试（oss2 集成测试）
- ✅ 前端组件测试（FileTree, 版本历史）
- ✅ 离线同步逻辑测试
- ⚠️ E2E 测试（手动验证）

**Documentation**:
- ✅ API 文档（FastAPI 自动生成）
- ✅ 组件使用文档
- ⚠️ 部署文档（需要补充 OSS 配置说明）

**Security**:
- ✅ JWT 认证
- ✅ OSS 路径权限验证（后端）
- ✅ 文件类型白名单
- ✅ 文件大小限制

**Decision**: 通过 Constitution Check，可以进入 Phase 0 研究阶段。

## Project Structure

### Documentation (this feature)

```text
specs/001-markdown-oss-manager/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routes/
│   │   └── markdown_editor.py      # OSS API 端点（已存在，需扩展）
│   ├── services/
│   │   └── oss_service.py          # OSS 服务（已存在）
│   └── models/
│       └── oss_models.py           # 数据模型（已存在）
└── tests/
    └── test_oss.py                 # OSS 服务测试

frontend/
├── src/
│   ├── components/
│   │   └── MarkdownEditor/
│   │       ├── FileTree/
│   │       │   └── FileTree.tsx    # 扩展：支持 OSS 文件
│   │       ├── FileUpload/
│   │       │   └── FileUpload.tsx  # 扩展：分块上传
│   │       ├── VersionHistory/     # 新增：版本历史组件
│   │       │   └── VersionHistory.tsx
│   │       └── OfflineIndicator/   # 新增：离线状态指示器
│   │           └── OfflineIndicator.tsx
│   ├── api/
│   │   └── markdownEditorApi.ts    # 扩展：版本历史 API
│   ├── stores/
│   │   ├── fileStore.ts            # 扩展：OSS 文件状态
│   │   └── offlineStore.ts         # 新增：离线缓存状态
│   ├── hooks/
│   │   ├── useOssFiles.ts          # 新增：OSS 文件列表 Hook
│   │   ├── useVersionHistory.ts    # 新增：版本历史 Hook
│   │   └── useOfflineSync.ts       # 新增：离线同步 Hook
│   └── utils/
│       └── indexedDb.ts            # 新增：IndexedDB 工具
└── tests/
    └── components/
        └── MarkdownEditor/
            └── FileTree.test.tsx
```

**Structure Decision**: Web application (Option 2)。项目已采用前后端分离架构，后端 FastAPI 提供 API，前端 React 提供 UI。OSS 相关功能主要在现有代码基础上扩展：
- 后端：扩展 `/api/markdown-editor/oss/*` 端点，添加版本历史 API
- 前端：扩展现有 FileTree 组件，新增版本历史、离线状态组件

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**无严重违规项**，以下是需要关注的中等复杂度点：

1. **离线同步机制** (复杂度: 中等)
   - 需要处理 IndexedDB 和 OSS 之间的双向同步
   - 需要检测文件冲突（同一文件离线期间被其他设备修改）
   - 需要处理同步失败的重试逻辑

2. **分块上传** (复杂度: 中等)
   - 需要实现断点续传
   - 需要处理分块失败的重试
   - 需要显示上传进度

3. **版本历史管理** (复杂度: 中等)
   - 需要优化 OSS 调用（列出大量版本时的性能）
   - 需要实现版本预览（不覆盖当前编辑内容）
   - 需要处理版本回滚的原子性

**缓解措施**:
- 使用 Zustand 管理复杂状态
- 使用 React Query 处理数据获取和缓存
- 使用 Web Workers 处理大文件分块（可选优化）
