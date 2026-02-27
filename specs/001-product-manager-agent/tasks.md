# Tasks: 产品经理 Agent

**Feature**: 001-product-manager-agent  
**Input**: Design documents from `/specs/001-product-manager-agent/`  
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.yaml, research.md  

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [P] Install backend dependencies: fastapi, sqlalchemy, alembic, cryptography, redis, openai, anthropic, httpx, python-docx, PyPDF2 in backend/requirements.txt
- [x] T002 [P] Install frontend dependencies: mermaid, html2pdf.js, docx, diff-match-patch in frontend/package.json
- [x] T003 Create backend directory structure: backend/src/api/routes/, backend/src/services/llm/, backend/src/models/, backend/src/core/, backend/tests/
- [x] T004 Create frontend directory structure: frontend/src/components/ProductManagerAgent/, frontend/src/services/, frontend/src/hooks/
- [x] T005 [P] Create environment configuration template (.env.example) with MASTER_KEY, REDIS_URL, SERPAPI_KEY placeholders
- [x] T006 [P] Setup Alembic migration configuration in backend/alembic/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### 2.1 Security & Core Utilities

- [x] T007 [P] Implement AES-256-GCM encryption/decryption in backend/src/core/security.py (encrypt_api_key, decrypt_api_key functions)
- [x] T008 Implement rate limiter using Redis in backend/src/core/rate_limiter.py (check_limit, increment_counter functions)
- [ ] T009 [P] Setup logging configuration in backend/src/core/logging.py

### 2.2 LLM Provider Infrastructure

- [x] T010 Create LLM Provider abstract base class in backend/src/services/llm/base.py (LLMProvider ABC with generate() and test_connection() methods)
- [x] T011 Implement OpenAI adapter in backend/src/services/llm/openai_adapter.py
- [x] T012 [P] Implement Anthropic adapter in backend/src/services/llm/anthropic_adapter.py
- [ ] T013 [P] Implement Azure OpenAI adapter in backend/src/services/llm/azure_adapter.py
- [ ] T014 [P] Implement Baidu Wenxin adapter in backend/src/services/llm/baidu_adapter.py
- [ ] T015 [P] Implement Aliyun Qwen adapter in backend/src/services/llm/aliyun_adapter.py
- [x] T016 Create adapter factory in backend/src/services/llm/factory.py (get_provider() function)

### 2.3 Database Models (All Stories Depend On These)

- [x] T017 Create Conversation model in backend/src/models/conversation.py (id, user_id, title, current_stage, version, timestamps)
- [x] T018 Create Message model in backend/src/models/message.py (id, conversation_id, sender_type, content, message_type, sent_at)
- [x] T019 Create PRDDocument model in backend/src/models/prd.py (id, conversation_id, version_number, content, status, created_at)
- [x] T020 Create CompetitorAnalysis model in backend/src/models/competitor.py (id, conversation_id, competitors JSON, suggestions, created_at)
- [x] T021 Create LLMConfig model in backend/src/models/llm_config.py (id, name, provider_type, base_url, api_key_encrypted, model_name, params, is_default, is_active)
- [ ] T022 Create database migration script for all models (alembic revision --autogenerate)

### 2.4 API Dependencies & Middleware

- [x] T023 Setup FastAPI dependencies in backend/src/api/dependencies.py (get_db, get_redis, get_current_user)
- [ ] T024 Create rate limiting middleware in backend/src/api/middleware/rate_limit.py
- [ ] T025 [P] Setup API router configuration in backend/src/api/router.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 4 - 后台管理大模型配置 (Priority: P1) 🎯 Foundational

**Goal**: 管理员可以在后台配置大模型API信息(baseUrl, apiKey等)，支持多供应商接入

**Independent Test**: 管理员可以CRUD大模型配置，测试连接，前端能调用配置的大模型API

### 3.1 Backend - LLM Config API

- [x] T026 Create LLMConfig service in backend/src/services/llm_config_service.py (create, update, delete, list, test_connection, set_default)
- [x] T027 Implement LLM config admin routes in backend/src/api/routes/llm_config.py (GET/POST/PUT/DELETE /admin/llm-configs, POST /test, POST /set-default)
- [x] T028 Implement LLM stats endpoint in backend/src/api/routes/llm_config.py (GET /admin/llm-stats)
- [x] T029 Implement rate limit admin endpoint in backend/src/api/routes/llm_config.py (GET/PUT /admin/rate-limits)

### 3.2 Frontend - Admin UI

- [x] T030 Create LLM config API service in frontend/src/services/llmConfigApi.ts
- [x] T031 Create LLM config management component in frontend/src/components/Admin/LLMConfigManager.tsx (list, add, edit, delete, test connection)
- [ ] T032 Create LLM config form component in frontend/src/components/Admin/LLMConfigForm.tsx (name, provider, baseUrl, apiKey, model, params)
- [ ] T033 Create LLM stats component in frontend/src/components/Admin/LLMStats.tsx
- [ ] T034 Integrate LLM config admin into existing admin layout in frontend/src/components/Admin/SystemSettings.tsx

**Checkpoint**: LLM配置管理功能完成，可以配置和测试各种大模型供应商

---

## Phase 4: User Story 1 - 一句话需求生成完整PRD (Priority: P1) 🎯 MVP

**Goal**: 用户输入一句话需求，Agent通过多轮对话引导，最终生成完整PRD文档

**Independent Test**: 用户可以输入"我想做个记账软件"，经过对话获得包含8个章节的PRD

### 4.1 Backend - Conversation Service

- [x] T035 Create conversation service in backend/src/services/conversation_service.py (create_conversation, get_conversation, update_stage, optimistic_lock_update)
- [x] T036 Create message service in backend/src/services/message_service.py (create_message, get_messages, build_context)
- [x] T037 Create conversation routes in backend/src/api/routes/conversations.py (GET/POST /conversations, GET/PUT/DELETE /conversations/{id})
- [ ] T038 Create message routes in backend/src/api/routes/messages.py (GET /messages, POST /conversations/{id}/messages)

### 4.2 Backend - PRD Generation

- [ ] T039 Create PRD generator service in backend/src/services/prd_generator.py (generate_prd, generate_section, create_mermaid_diagrams)
- [ ] T040 Create PRD template in backend/src/templates/prd_template.md (8章节标准结构)
- [ ] T041 Create PRD routes in backend/src/api/routes/prd.py (GET/POST /conversations/{id}/prd, PUT /prd/{version}, POST /export)
- [ ] T042 Create stage transition logic in backend/src/services/stage_manager.py (handle_user_input, determine_next_stage)

### 4.3 Backend - Competitor Analysis

- [ ] T043 Create competitor analyzer service in backend/src/services/competitor_analyzer.py (search_competitors, analyze_features, generate_comparison_table)
- [ ] T044 Integrate SerpAPI for competitor search in backend/src/services/competitor_analyzer.py
- [ ] T045 Create competitor routes in backend/src/api/routes/competitor.py (GET/POST /conversations/{id}/competitors)

### 4.4 Frontend - Chat Interface

- [ ] T046 Create conversation API service in frontend/src/services/conversationApi.ts
- [ ] T047 Create conversation hook in frontend/src/hooks/useConversation.ts
- [ ] T048 Create ChatInterface component in frontend/src/components/ProductManagerAgent/ChatInterface.tsx (message list, input, send button)
- [ ] T049 Create MessageBubble component in frontend/src/components/ProductManagerAgent/MessageBubble.tsx (user/agent messages, structured content)
- [ ] T050 Create Sidebar component in frontend/src/components/ProductManagerAgent/Sidebar.tsx (conversation list, current stage indicator)
- [ ] T051 Integrate chat interface into main tool page in frontend/src/components/Tools/ProductManagerAgent.tsx

### 4.5 Frontend - PRD Preview

- [ ] T052 Create PRD API service in frontend/src/services/prdApi.ts
- [ ] T053 Create PRDPreview component in frontend/src/components/ProductManagerAgent/PRDPreview.tsx (markdown rendering, mermaid diagrams)
- [ ] T054 Create export functionality in frontend/src/components/ProductManagerAgent/ExportDialog.tsx (markdown, pdf, word)
- [ ] T055 [P] Implement Mermaid chart rendering in frontend/src/utils/mermaidRenderer.ts

**Checkpoint**: User Story 1 MVP complete - users can create conversations, chat with AI, and generate/export PRDs

---

## Phase 5: User Story 2 - 上传现有文档进行补全 (Priority: P2)

**Goal**: 用户可以上传Markdown/Word/PDF文档，Agent识别缺失信息并补全成完整PRD

**Independent Test**: 用户上传文档后，Agent能解析并识别缺失信息，引导补充后生成完整PRD

### 5.1 Backend - Document Parsing

- [ ] T056 Create document parser service in backend/src/services/document_parser.py (parse_markdown, parse_docx, parse_pdf)
- [ ] T057 Implement document upload endpoint in backend/src/api/routes/messages.py (POST with file upload)
- [ ] T058 Create missing info detection logic in backend/src/services/document_parser.py (detect_missing_sections, suggest_questions)
- [ ] T059 Integrate document parsing into conversation flow in backend/src/services/conversation_service.py

### 5.2 Frontend - Document Upload

- [ ] T060 Create file upload component in frontend/src/components/ProductManagerAgent/FileUpload.tsx (drag & drop, file type validation)
- [ ] T061 Create missing info display component in frontend/src/components/ProductManagerAgent/MissingInfoPanel.tsx (list missing sections, questions)
- [ ] T062 Integrate upload into chat interface in frontend/src/components/ProductManagerAgent/ChatInterface.tsx (upload button, file preview)

### 5.3 Backend - Partial PRD Update

- [ ] T063 Create partial update service in backend/src/services/prd_generator.py (update_section, merge_changes)
- [ ] T064 Implement partial PRD generation endpoint in backend/src/api/routes/prd.py (POST with section parameter)

**Checkpoint**: User Story 2 complete - users can upload documents and get AI-assisted completion

---

## Phase 6: User Story 3 - 多轮迭代优化PRD (Priority: P3)

**Goal**: 用户可以基于已生成的PRD进行多轮修改，支持版本管理和对比

**Independent Test**: 用户可以对PRD提出修改，系统保存新版本，支持版本对比和回滚

### 6.1 Backend - Version Management

- [ ] T065 Create version management service in backend/src/services/prd_version_service.py (create_version, list_versions, get_version, rollback)
- [ ] T066 Create diff generation utility in backend/src/utils/diff_generator.py (generate_diff, format_diff_view)
- [ ] T067 Implement version comparison endpoint in backend/src/api/routes/prd.py (POST /conversations/{id}/prd/compare)
- [ ] T068 Implement rollback endpoint in backend/src/api/routes/prd.py (POST /conversations/{id}/prd/rollback)

### 6.2 Frontend - Version History

- [ ] T069 Create PRD hook in frontend/src/hooks/usePRD.ts
- [ ] T070 Create VersionHistory component in frontend/src/components/ProductManagerAgent/VersionHistory.tsx (version list, timestamps, status)
- [ ] T071 Create VersionDiff component in frontend/src/components/ProductManagerAgent/VersionDiff.tsx (diff view, side-by-side comparison)
- [ ] T072 Create rollback confirmation dialog in frontend/src/components/ProductManagerAgent/RollbackDialog.tsx

### 6.3 Frontend - Partial Editing

- [ ] T073 Create PRD section editor in frontend/src/components/ProductManagerAgent/PRDSectionEditor.tsx (edit specific sections)
- [ ] T074 Implement inline editing in frontend/src/components/ProductManagerAgent/PRDPreview.tsx (edit buttons per section)

**Checkpoint**: User Story 3 complete - users can iterate on PRDs with full version control

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### 7.1 Error Handling & Edge Cases

- [ ] T075 [P] Implement irrelevant input detection in backend/src/services/conversation_service.py (detect off-topic queries)
- [ ] T076 [P] Implement API failure fallback in backend/src/services/llm/fallback.py (switch to backup config, error messages)
- [ ] T077 [P] Implement content safety filter in backend/src/services/content_filter.py (detect inappropriate content)
- [ ] T078 [P] Implement debounce for rapid calls in backend/src/api/middleware/debounce.py (30-second duplicate prevention)

### 7.2 UI/UX Polish

- [ ] T079 [P] Implement loading states and progress indicators in frontend/src/components/common/LoadingStates.tsx
- [ ] T080 Implement error message components in frontend/src/components/common/ErrorMessages.tsx
- [ ] T081 [P] Add responsive design breakpoints for tablet/mobile in frontend/src/styles/responsive.css
- [ ] T082 Implement dark/light mode support in frontend/src/styles/theme.ts

### 7.3 Performance & Monitoring

- [ ] T083 [P] Add database indexes for frequent queries in backend/alembic/versions/add_indexes.py
- [ ] T084 Implement Redis caching for LLM configs in backend/src/services/llm_config_service.py
- [ ] T085 Add API response time logging in backend/src/api/middleware/timing.py
- [ ] T086 Create health check endpoint in backend/src/api/routes/health.py

### 7.4 Documentation & Validation

- [ ] T087 Update README with feature documentation in docs/product-manager-agent/README.md
- [ ] T088 Validate quickstart.md steps work correctly (manual testing)
- [ ] T089 Add API examples to contracts/api.yaml

**Checkpoint**: All polish items complete, feature production-ready

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ───────────────────────────┐
    │                                              │
    ├──► T007 (Security) ──► ALL user stories    │
    ├──► T010-T016 (LLM adapters) ──► US1, US4   │
    ├──► T017-T022 (DB Models) ──► ALL stories   │
    └──► T023-T025 (API infra) ──► ALL stories   │
                                                   │
    ┌──────────────────────────────────────────────┘
    ▼
Phase 3 (US4 - LLM Config) ──► Can work in parallel with Phase 4
    │
    ▼
Phase 4 (US1 - MVP) ──► Core PRD generation
    │
    ▼
Phase 5 (US2 - Document Upload) ──► Depends on US1 conversation flow
    │
    ▼
Phase 6 (US3 - Version Management) ──► Depends on US1 PRD generation
    │
    ▼
Phase 7 (Polish)
```

### User Story Dependencies

| Story | Priority | Dependencies | Can Start After |
|-------|----------|--------------|-----------------|
| US4 (LLM Config) | P1 | Phase 2 complete | Phase 2 |
| US1 (MVP) | P1 | Phase 2 + US4 (for LLM calls) | Phase 2 + partial US4 |
| US2 (Doc Upload) | P2 | US1 complete | US1 |
| US3 (Versions) | P3 | US1 complete | US1 |

### Within Each User Story

1. Backend models (if not in foundational)
2. Backend services
3. Backend routes
4. Frontend API services
5. Frontend hooks
6. Frontend components
7. Integration

### Parallel Opportunities

**Maximum Parallelism (with full team)**:

```
Phase 1: All setup tasks marked [P] can run in parallel
Phase 2: 
  - Security + Rate limiter + Logging (parallel)
  - All 6 LLM adapters (parallel)
  - All 6 DB models (parallel)
  - API infra (parallel)
Phase 3+4: 
  - US4 and US1 can overlap (US4 provides LLM config for US1)
  - Within each story: backend and frontend can partially overlap
Phase 5+6:
  - US2 and US3 can be worked on in parallel after US1
```

---

## Implementation Strategy

### MVP First (User Story 1 + US4 Only)

1. ✅ Phase 1: Setup
2. ✅ Phase 2: Foundational (CRITICAL - blocks all stories)
3. ✅ Phase 3: User Story 4 (LLM Config - enables AI calls)
4. ✅ Phase 4: User Story 1 (Core PRD generation)
5. **STOP and VALIDATE**: Deploy MVP, get feedback

**MVP Scope**: T001-T055 only (~55 tasks)

### Incremental Delivery

```
Milestone 1: MVP (US1 + US4) ──► Deploy, test core flow
Milestone 2: Add US2 ──► Document upload & completion
Milestone 3: Add US3 ──► Version management
Milestone 4: Polish ──► Performance, monitoring, docs
```

### Task Count Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1: Setup | 6 | Dependencies, directories, config |
| Phase 2: Foundational | 19 | Security, LLM adapters, DB models |
| Phase 3: US4 (LLM Config) | 9 | Admin LLM management |
| Phase 4: US1 (MVP) | 21 | Core chat & PRD generation |
| Phase 5: US2 (Doc Upload) | 7 | Document parsing & completion |
| Phase 6: US3 (Versions) | 8 | Version control & diff |
| Phase 7: Polish | 15 | Error handling, UI, performance |
| **Total** | **85** | |

### Suggested Team Allocation

**Solo Developer**: Sequential through all phases (~4-6 weeks)

**2-Person Team**:
- Dev A: Backend (Phases 1-2, then backend for all stories)
- Dev B: Frontend (starts after Phase 2, frontend for all stories)

**3-Person Team**:
- Dev A: Backend infrastructure (Phases 1-2, US4, US1 backend)
- Dev B: AI/LLM features (LLM adapters, PRD generation, competitor analysis)
- Dev C: Frontend (all frontend components)

---

## Notes

- [P] tasks = can run in parallel (different files, no dependencies)
- Each user story should be independently completable and testable
- Verify foundational phase complete before starting user stories
- US4 (LLM Config) and US1 (MVP) have some overlap - US1 needs working LLM config
- Commit after each task or logical group
- Test each user story independently at checkpoint
- The MVP (US1 + US4) provides core value - consider deploying before US2/US3
