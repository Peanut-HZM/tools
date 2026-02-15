# Tasks: Markdown OSS 文件管理功能

**Input**: Design documents from `/specs/001-markdown-oss-manager/`  
**Branch**: `001-markdown-oss-manager`  
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md

**Tests**: Optional - backend API tests and frontend component tests included

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and IndexedDB infrastructure setup

**Note**: Backend OSS infrastructure already exists. Focus is on frontend IndexedDB setup.

- [X] T001 Create IndexedDB utility module for offline caching in `frontend/src/utils/indexedDb.ts`
- [X] T002 [P] Define IndexedDB schema with object stores: `files`, `syncQueue`, `metadata` in `frontend/src/utils/indexedDb.ts`
- [X] T003 [P] Add TypeScript types for IndexedDB entities in `frontend/src/types/offlineCache.ts`
- [X] T004 Create offline store state management in `frontend/src/stores/offlineStore.ts`
- [X] T005 Add offline status detection and network monitoring in `frontend/src/hooks/useNetworkStatus.ts`
- [X] T006 [P] Extend existing fileStore to support OSS file operations in `frontend/src/stores/fileStore.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Backend Extensions** (扩展现有 API):
- [X] T007 [P] Extend OSS API with version history endpoints in `backend/app/routes/markdown_editor.py`
- [ ] T008 [P] Add multipart upload endpoints for large files in `backend/app/routes/markdown_editor.py`
- [ ] T009 [P] Add directory management endpoints in `backend/app/routes/markdown_editor.py`
- [X] T010 Implement version history service in `backend/app/services/oss_version_service.py`

**Frontend Infrastructure**:
- [X] T011 [P] Create API client functions for OSS operations in `frontend/src/api/markdownEditorApi.ts`
- [X] T012 [P] Create API client functions for version history in `frontend/src/api/versionHistoryApi.ts`
- [X] T013 Create offline sync service for IndexedDB-OSS synchronization in `frontend/src/services/offlineSyncService.ts`
- [X] T014 Create file upload service with chunk support in `frontend/src/services/fileUploadService.ts`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 上传文件到OSS (Priority: P1) 🎯 MVP

**Goal**: 用户可以上传 Markdown 文件到阿里云 OSS，支持拖拽和点击上传

**Independent Test**: 用户登录后，点击上传按钮或拖拽文件到编辑器区域，文件成功上传到 OSS 并出现在左侧文件列表中

### Backend Tasks for US1

- [ ] T015 [US1] Implement file upload endpoint with type validation in `backend/app/routes/markdown_editor.py` (POST /oss/upload)
- [ ] T016 [US1] Add file size validation (10MB limit) and error handling in `backend/app/routes/markdown_editor.py`
- [ ] T017 [US1] Implement multipart upload initiation for large files in `backend/app/routes/markdown_editor.py`

### Frontend Tasks for US1

- [X] T018 [P] [US1] Extend FileUpload component with drag-and-drop support in `frontend/src/components/MarkdownEditor/FileUpload/FileUpload.tsx`
- [X] T019 [P] [US1] Add file type validation (.md, .markdown, .txt) in `frontend/src/components/MarkdownEditor/FileUpload/FileUpload.tsx`
- [X] T020 [US1] Implement upload progress indicator in `frontend/src/components/MarkdownEditor/FileUpload/FileUpload.tsx`
- [ ] T021 [US1] Add overwrite confirmation dialog for existing files in `frontend/src/components/MarkdownEditor/FileUpload/FileUploadDialog.tsx`
- [ ] T022 [P] [US1] Create useFileUpload hook for upload logic in `frontend/src/hooks/useFileUpload.ts`
- [ ] T023 [US1] Integrate FileUpload with markdownEditorApi in `frontend/src/api/markdownEditorApi.ts`
- [ ] T024 [US1] Add error handling and user notifications for upload failures in `frontend/src/components/MarkdownEditor/FileUpload/FileUpload.tsx`

**Checkpoint**: User Story 1 complete - file upload functionality should be fully working

---

## Phase 4: User Story 2 - 浏览 OSS 文件列表 (Priority: P1) 🎯 MVP

**Goal**: 在 Markdown 编辑器左侧显示文件树视图，展示 OSS 文件，支持文件夹层级

**Independent Test**: 用户登录后，左侧自动加载并显示该用户的所有 OSS Markdown 文件列表，可以展开/收起文件夹

### Backend Tasks for US2

- [X] T025 [US2] Implement list OSS files endpoint with user filtering in `backend/app/routes/markdown_editor.py` (GET /oss/list)
- [X] T026 [US2] Add directory tree structure building from OSS objects in `backend/app/services/oss_service.py`
- [ ] T027 [US2] Add pagination support for large file lists in `backend/app/routes/markdown_editor.py`

### Frontend Tasks for US2

- [ ] T028 [P] [US2] Extend FileTree component to support storage type icons in `frontend/src/components/MarkdownEditor/FileTree/FileTree.tsx`
- [ ] T029 [P] [US2] Add OSS file icon (cloud icon) with distinct styling in `frontend/src/components/MarkdownEditor/FileTree/FileTree.tsx`
- [X] T030 [US2] Create useOssFiles hook for fetching and managing OSS file list in `frontend/src/hooks/useOssFiles.ts`
- [X] T031 [US2] Add loading state and skeleton UI for file list in `frontend/src/components/MarkdownEditor/FileTree/FileTree.tsx`
- [X] T032 [US2] Implement empty state UI for users with no OSS files in `frontend/src/components/MarkdownEditor/FileTree/FileTree.tsx`
- [X] T033 [P] [US2] Add file metadata display (size, last modified) in file tree items in `frontend/src/components/MarkdownEditor/FileTree/FileTree.tsx`
- [X] T034 [US2] Merge local files and OSS files into unified file tree in `frontend/src/stores/fileStore.ts`
- [X] T035 [US2] Add automatic file list refresh after upload in `frontend/src/stores/fileStore.ts`

**Checkpoint**: User Story 2 complete - file browsing functionality should be fully working

---

## Phase 5: User Story 3 - 打开和编辑 OSS 文件 (Priority: P1) 🎯 MVP

**Goal**: 用户可以点击左侧文件列表中的 OSS 文件，在编辑器中打开并编辑保存

**Independent Test**: 用户点击左侧 OSS 文件，内容加载到编辑器中，用户修改后点击保存，文件成功更新到 OSS

### Backend Tasks for US3

- [ ] T036 [US3] Implement read OSS file endpoint in `backend/app/routes/markdown_editor.py` (GET /oss/read)
- [ ] T037 [US3] Implement save file to OSS endpoint with version creation in `backend/app/routes/markdown_editor.py` (POST /oss/save)
- [ ] T038 [US3] Add file content caching for performance in `backend/app/services/oss_service.py`

### Frontend Tasks for US3

- [ ] T039 [P] [US3] Extend file opening logic to handle OSS files in `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`
- [ ] T040 [US3] Add OSS file indicator banner in editor when editing OSS file in `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`
- [ ] T041 [US3] Implement save handler for OSS files in `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`
- [ ] T042 [P] [US3] Create useOssFileEditor hook for OSS file editing operations in `frontend/src/hooks/useOssFileEditor.ts`
- [ ] T043 [US3] Add unsaved changes confirmation dialog when switching files in `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`
- [ ] T044 [US3] Implement auto-save to IndexedDB when editing OSS files in `frontend/src/services/offlineSyncService.ts`
- [ ] T045 [US3] Add save success/failure toast notifications in `frontend/src/components/MarkdownEditor/Toast/Toast.tsx`
- [ ] T046 [US3] Handle network errors during save with retry option in `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`

**Checkpoint**: User Story 3 complete - file editing functionality should be fully working

---

## Phase 6: User Story 7 - 用户数据隔离与权限 (Priority: P1) 🎯 MVP

**Goal**: 每个用户只能看到和操作自己的 OSS 文件，数据完全隔离

**Independent Test**: 用户 A 登录后上传文件，用户 B 登录后看不到用户 A 的文件

### Backend Tasks for US7

- [ ] T047 [US7] Add user_id path prefix validation middleware in `backend/app/middleware/auth.py`
- [ ] T048 [US7] Implement OSS path permission checking in `backend/app/services/oss_service.py`
- [ ] T049 [US7] Add authorization checks to all OSS endpoints in `backend/app/routes/markdown_editor.py`
- [ ] T050 [US7] Create path traversal prevention in `backend/app/utils/security.py`

### Frontend Tasks for US7

- [ ] T051 [US7] Add auth token handling to all OSS API calls in `frontend/src/api/markdownEditorApi.ts`
- [ ] T052 [US7] Implement logout cleanup for IndexedDB cached data in `frontend/src/stores/offlineStore.ts`
- [ ] T053 [US7] Add user context to offline cache keys in `frontend/src/utils/indexedDb.ts`

**Checkpoint**: User Story 7 complete - security and isolation should be fully working

---

## Phase 7: User Story 4 - 创建文件夹管理文件 (Priority: P2)

**Goal**: 用户可以在 OSS 中创建文件夹来组织 Markdown 文件

**Independent Test**: 用户在左侧文件树中右键点击，选择"新建文件夹"，输入名称后创建成功

### Backend Tasks for US4

- [ ] T054 [US4] Implement create directory endpoint in `backend/app/routes/markdown_editor.py` (POST /oss/directory/create)
- [ ] T055 [US4] Implement delete directory endpoint with recursive option in `backend/app/routes/markdown_editor.py` (DELETE /oss/directory/delete)
- [ ] T056 [US4] Implement rename file/directory endpoint in `backend/app/routes/markdown_editor.py` (POST /oss/rename)
- [ ] T057 [US4] Add directory validation (check if not empty) in `backend/app/services/oss_service.py`

### Frontend Tasks for US4

- [ ] T058 [P] [US4] Extend FileTree context menu with OSS operations in `frontend/src/components/MarkdownEditor/FileTree/FileTree.tsx`
- [ ] T059 [P] [US4] Add "New Folder" dialog component in `frontend/src/components/MarkdownEditor/FileTree/NewFolderDialog.tsx`
- [ ] T060 [US4] Add "Rename" dialog component in `frontend/src/components/MarkdownEditor/FileTree/RenameDialog.tsx`
- [ ] T061 [US4] Add "Delete" confirmation dialog with recursive warning in `frontend/src/components/MarkdownEditor/FileTree/DeleteConfirmDialog.tsx`
- [ ] T062 [P] [US4] Create useOssDirectory hook for directory operations in `frontend/src/hooks/useOssDirectory.ts`
- [ ] T063 [US4] Integrate directory operations with API in `frontend/src/api/markdownEditorApi.ts`
- [ ] T064 [US4] Add optimistic updates for directory operations in `frontend/src/stores/fileStore.ts`

**Checkpoint**: User Story 4 complete - folder management should be fully working

---

## Phase 8: User Story 5 - 文件版本历史管理 (Priority: P2)

**Goal**: 系统自动保存版本历史，用户可以查看和回滚到任意历史版本

**Independent Test**: 用户编辑并保存文件多次后，可以打开版本历史面板查看并回滚

### Backend Tasks for US5

- [ ] T065 [US5] Implement automatic version creation on save in `backend/app/services/oss_version_service.py`
- [ ] T066 [US5] Create list versions endpoint with pagination in `backend/app/routes/markdown_editor.py` (GET /oss/versions)
- [ ] T067 [US5] Create read version content endpoint in `backend/app/routes/markdown_editor.py` (GET /oss/versions/read)
- [ ] T068 [US5] Create rollback endpoint in `backend/app/routes/markdown_editor.py` (POST /oss/versions/rollback)
- [ ] T069 [US5] Implement version cleanup (keep last 100 versions) in `backend/app/services/oss_version_service.py`
- [ ] T070 [US5] Add version metadata extraction (content preview) in `backend/app/services/oss_version_service.py`

### Frontend Tasks for US5

- [ ] T071 [P] [US5] Create VersionHistory component in `frontend/src/components/MarkdownEditor/VersionHistory/VersionHistory.tsx`
- [ ] T072 [P] [US5] Add version list item component with timestamp and preview in `frontend/src/components/MarkdownEditor/VersionHistory/VersionListItem.tsx`
- [ ] T073 [US5] Create version preview modal in `frontend/src/components/MarkdownEditor/VersionHistory/VersionPreviewModal.tsx`
- [ ] T074 [US5] Add rollback confirmation dialog in `frontend/src/components/MarkdownEditor/VersionHistory/RollbackConfirmDialog.tsx`
- [ ] T075 [P] [US5] Create useVersionHistory hook for version operations in `frontend/src/hooks/useVersionHistory.ts`
- [ ] T076 [US5] Add version history button to editor toolbar in `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`
- [ ] T077 [US5] Implement version list pagination in `frontend/src/components/MarkdownEditor/VersionHistory/VersionHistory.tsx`
- [ ] T078 [US5] Add version rollback success notification in `frontend/src/components/MarkdownEditor/Toast/Toast.tsx`

**Checkpoint**: User Story 5 complete - version history should be fully working

---

## Phase 9: User Story 6 - 离线编辑与自动同步 (Priority: P2)

**Goal**: OSS 服务不可用时，用户可以继续编辑本地缓存的文件，服务恢复后自动同步

**Independent Test**: 用户断开网络继续编辑并保存，恢复网络后系统自动将离线期间的修改同步到 OSS

### Backend Tasks for US6

- [ ] T079 [US6] Add conflict detection endpoint for sync operations in `backend/app/routes/markdown_editor.py`
- [ ] T080 [US6] Implement bulk sync endpoint for offline changes in `backend/app/routes/markdown_editor.py`
- [ ] T081 [US6] Add last_modified timestamp comparison for conflict detection in `backend/app/services/oss_service.py`

### Frontend Tasks for US6

- [ ] T082 [P] [US6] Create OfflineIndicator component with sync status in `frontend/src/components/MarkdownEditor/OfflineIndicator/OfflineIndicator.tsx`
- [ ] T083 [P] [US6] Add sync progress modal in `frontend/src/components/MarkdownEditor/OfflineIndicator/SyncProgressModal.tsx`
- [ ] T084 [US6] Create conflict resolution dialog in `frontend/src/components/MarkdownEditor/OfflineIndicator/ConflictResolutionDialog.tsx`
- [ ] T085 [P] [US6] Create useOfflineSync hook for sync logic in `frontend/src/hooks/useOfflineSync.ts`
- [ ] T086 [US6] Implement IndexedDB sync queue management in `frontend/src/services/offlineSyncService.ts`
- [ ] T087 [US6] Add automatic sync trigger on network restore in `frontend/src/hooks/useNetworkStatus.ts`
- [ ] T088 [US6] Add offline save indicator in editor status bar in `frontend/src/components/MarkdownEditor/StatusBar/StatusBar.tsx`
- [ ] T089 [US6] Implement conflict resolution strategy (keep both) in `frontend/src/services/offlineSyncService.ts`
- [ ] T090 [US6] Add sync retry logic with exponential backoff in `frontend/src/services/offlineSyncService.ts`

**Checkpoint**: User Story 6 complete - offline editing should be fully working

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T091 [P] Add comprehensive error boundaries for OSS operations in `frontend/src/components/ErrorBoundary/OssErrorBoundary.tsx`
- [ ] T092 [P] Create loading skeleton components for all async operations in `frontend/src/components/Common/Skeletons/`
- [ ] T093 Add keyboard shortcuts for common OSS operations in `frontend/src/hooks/useKeyboardShortcuts.ts`
- [ ] T094 [P] Implement debounced auto-save to IndexedDB in `frontend/src/services/offlineSyncService.ts`
- [ ] T095 Add OSS configuration validation on startup in `backend/app/main.py`
- [ ] T096 [P] Create API documentation with examples in `docs/api/oss-api.md`
- [ ] T097 Add user guide for OSS features in `docs/user-guide/oss-features.md`
- [ ] T098 [P] Write unit tests for offline sync service in `frontend/src/services/offlineSyncService.test.ts`
- [ ] T099 [P] Write unit tests for file upload service in `frontend/src/services/fileUploadService.test.ts`
- [ ] T100 Add integration tests for critical OSS flows in `backend/tests/test_oss_integration.py`
- [ ] T101 Performance optimization: cache file list in sessionStorage in `frontend/src/stores/fileStore.ts`
- [ ] T102 Add OSS lifecycle rule configuration documentation in `docs/deployment/oss-lifecycle.md`
- [ ] T103 Run quickstart.md validation and fix any issues

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKING - must complete before user stories)
    ↓
Phase 3: User Story 1 (P1) ────────┐
Phase 4: User Story 2 (P1) ────────┼─── Can run in parallel after Phase 2
Phase 5: User Story 3 (P1) ────────┤
Phase 6: User Story 7 (P1) ────────┘ (security integrated throughout)
    ↓
Phase 7: User Story 4 (P2) ────────┐
Phase 8: User Story 5 (P2) ────────┼─── Can run in parallel
Phase 9: User Story 6 (P2) ────────┘
    ↓
Phase 10: Polish & Cross-Cutting
```

### User Story Dependencies

| Story | Depends On | Can Run Parallel With |
|-------|-----------|----------------------|
| US1 (上传) | Phase 2 | None (first story) |
| US2 (浏览) | Phase 2 | US1 |
| US3 (编辑) | Phase 2, US1 | US2 |
| US7 (安全) | Phase 2 | US1, US2, US3 (security layer) |
| US4 (文件夹) | Phase 2, US1, US2 | US3, US5, US6 |
| US5 (版本) | Phase 2, US1, US3 | US4, US6 |
| US6 (离线) | Phase 2, US1, US3 | US4, US5 |

### Within Each User Story

1. Backend API endpoints (can be done in parallel for same story)
2. Frontend hooks and services
3. Frontend components
4. Integration and testing
5. Story complete checkpoint

### Parallel Opportunities

**Maximum Parallel Execution** (with 5 developers):
- Developer 1: Phase 1 + Phase 2 backend
- Developer 2: Phase 2 frontend infrastructure
- Developer 3: US1 + US2
- Developer 4: US3 + US7 (security)
- Developer 5: US4 + US5 + US6 (after P1 stories)

**Recommended Sequential** (solo developer):
1. Complete Phase 1 + Phase 2 (foundation)
2. Implement US1 → Test → Demo
3. Implement US2 → Test → Demo
4. Implement US3 + US7 → Test → Demo (MVP Complete! 🎉)
5. Implement US4 → Test
6. Implement US5 → Test
7. Implement US6 → Test
8. Phase 10 Polish

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3, 7)

**MVP Scope**: File upload, browse, edit, and security

1. ✅ Phase 1: Setup (IndexedDB, offline store)
2. ✅ Phase 2: Foundational (API extensions, services)
3. ✅ Phase 3: US1 - Upload files
4. ✅ Phase 4: US2 - Browse files
5. ✅ Phase 5: US3 - Edit files
6. ✅ Phase 6: US7 - Security & isolation
7. **🎉 MVP COMPLETE** - Deploy and demo!

### Incremental Delivery

Each story adds value:
- **US1+US2+US3+US7** = MVP (basic cloud file management)
- **+ US4** = Folder organization
- **+ US5** = Version history (safety net)
- **+ US6** = Offline capability (productivity boost)

### Risk Mitigation

**High Risk Items**:
- US6 (离线同步): Complex state management, test early
- US5 (版本历史): OSS storage costs, monitor usage
- US7 (安全): Critical, add security review checkpoint

**Recommended Order**:
1. Do US7 security early (don't leave to end)
2. Do US1, US2, US3 sequentially (core flow)
3. Do US6 after core flow stable (complex feature)
4. Do US4, US5 in parallel (independent features)

---

## Task Count Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1 (Setup) | 6 | IndexedDB, types, stores, hooks |
| Phase 2 (Foundational) | 8 | API extensions, services |
| Phase 3 (US1 - Upload) | 10 | File upload functionality |
| Phase 4 (US2 - Browse) | 9 | File tree, list display |
| Phase 5 (US3 - Edit) | 10 | Edit, save, auto-save |
| Phase 6 (US7 - Security) | 7 | Auth, isolation, permissions |
| Phase 7 (US4 - Folders) | 9 | Directory management |
| Phase 8 (US5 - Versions) | 14 | Version history, rollback |
| Phase 9 (US6 - Offline) | 12 | Offline edit, sync, conflicts |
| Phase 10 (Polish) | 13 | Tests, docs, optimization |
| **TOTAL** | **98** | Complete feature implementation |

---

## Next Steps

### Option 1: Start MVP (Recommended)
Begin with just Phase 1-6 to deliver core functionality quickly:
```bash
# Start with Phase 1
Task: "T001 Create IndexedDB utility module..."
```

### Option 2: Full Feature
Implement all phases for complete feature:
```bash
# Start from beginning
Task: "T001 Create IndexedDB utility module..."
```

### Option 3: Parallel Team
Assign different user stories to different team members after Phase 2 complete.

---

**Ready to start implementation?** Run `/speckit.implement` or start with Task T001!
