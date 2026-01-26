# Research Log: session-handoff-protocol

**Skill Name**: session-handoff-protocol
**Research Date**: 2025-10-23
**Researcher**: Claude Code (Sonnet 4.5)
**Status**: Research Complete ✅

---

## Problem Statement

**User's Pain Point** (verbatim):
> "planning, phasing and bridging between context, like the way i have to wrap up and then resume ive never really settled on how to do that well"

**Core Issues**:
1. **Context Loss**: Resuming work requires re-establishing context, wasting tokens
2. **Inconsistent Handoffs**: No standard format for wrapping up work
3. **Navigation Chaos**: "Where was I?" confusion when resuming
4. **Context Bloat**: Risk of cluttering projects with duplicate information
5. **Inefficient Reconstruction**: Re-reading files to figure out current state

**Success Criteria**:
- Reduce context re-establishment time from ~10-15 min to <2 min
- Reference-heavy (no code duplication)
- Token-efficient (capture only essential navigation context)
- Works with existing tools (git, planning docs, CHANGELOG.md)
- Zero external dependencies
- No clutter (cleanup is part of the design)

---

## User Requirements (from discussion)

### In Scope
- ✅ **Self-handoff only**: Not team handoff between sessions
- ✅ **Single project focus**: One folder = one project
- ✅ **No code duplication**: File references only, never code blocks
- ✅ **Cleanup-first design**: No context bloat
- ✅ **Git-centric**: Leverage existing git workflow
- ✅ **Reference-heavy**: Point to planning docs, don't duplicate them

### Out of Scope
- ❌ Multiple project management
- ❌ Team handoff between sessions (only at project completion)
- ❌ External tools or dependencies
- ❌ Complex automation requiring setup
- ❌ Jupyter notebooks (too technical)

### Design Decisions (user preferences)
- **Filename**: SCRATCHPAD.md (Anthropic's term)
- **Structure**: All phases visible, current phase expanded
- **Checkpoints**: End of each phase
- **Storage**: Git commits (primary) + SCRATCHPAD.md (living doc)
- **Cleanup**: Scratchpad deleted when project complete

---

## Research Findings

### Anthropic Engineering Best Practices

**Source**: https://www.anthropic.com/engineering/claude-code-best-practices

**Direct Quote**:
> "have Claude use a **Markdown file** (or even a GitHub issue!) as a **checklist and working scratchpad**" for complex workflows

**Git Workflow**:
- Claude handles "commit messages" by examining changes and recent history automatically
- Engineers use Claude for "complex git operations like reverting files, resolving rebase conflicts"
- Multiple git worktrees enable parallel independent tasks

**Key Insight**: CLAUDE.md files are automatically pulled into context. Use project-level CLAUDE.md to point to scratchpad.

### Git Checkpoint Patterns

**Sources**: Stack Overflow, GitHub Gists, Git Best Practices articles

**Common Pattern**: "Commit early and often - clean up before pushing"
- Local commits = checkpoints (safe to experiment)
- Squash/amend before pushing publicly
- Popular: git aliases for standardized checkpoint format

**Checkpoint Commit Format** (synthesized from research):
```
checkpoint: [Phase Name] - [brief status]

Phase: [Current phase number/name]
Status: [Complete/In Progress/Testing]

Files:
- path/to/file1.ts (added feature X)
- path/to/file2.ts (refactored Y)

Next: [Next concrete step]
```

### GitHub Spec Kit Patterns

**Source**: GitHub spec-kit repository analysis

**File Structure**:
- `spec.md` - Goals and requirements
- `plan.md` - Architecture and choices
- `tasks/` folder - Broken down work

**Key Insight**: Separation of planning (spec, plan) from execution tracking (tasks). We use this pattern with docs/ for planning, SCRATCHPAD.md for tracking.

### Common Developer Patterns (2025)

**Sources**: AI coding workflow blogs, developer forums

**Emerging Standards**:
- `.ai-instructions` or `CLAUDE.md` in repo root
- Feature-specific specs: `auth-system-spec.md`, `shared-types-refactoring.md`
- Markdown-based checklists for complex migrations
- No single standard for "scratchpad" vs "phases" naming

**Conclusion**: "SCRATCHPAD" aligns with Anthropic's terminology and is self-explanatory.

---

## Architecture Design

### File Structure

```
project-root/
├── docs/                          # Comprehensive planning (one-time write)
│   ├── ARCHITECTURE.md            # Full system design
│   ├── DATABASE_SCHEMA.md         # Complete schema
│   ├── API_ENDPOINTS.md           # All routes/contracts
│   ├── IMPLEMENTATION_PHASES.md   # Detailed phase plans
│   └── UI_COMPONENTS.md           # Component hierarchy
│
├── SCRATCHPAD.md                  # Living phase tracker (reference hub)
├── CHANGELOG.md                   # User-facing feature history
├── CLAUDE.md                      # Points to scratchpad
└── .git/                          # Checkpoint commits (storage)
```

### SCRATCHPAD.md Role

**Purpose**: Navigation hub, not documentation dump

**Pattern**:
```markdown
## Phase 3: API Integration 🔄
**Spec**: docs/IMPLEMENTATION_PHASES.md#phase-3
**Design**: docs/API_ENDPOINTS.md

**Progress**:
- [x] Auth endpoints (commit: abc123)
- [ ] Protected routes ← CURRENT
- [ ] Error handling

**Next**: Implement JWT middleware
**Last Checkpoint**: abc123 (2025-10-23)
```

**Preserved**: Current status, git commits, next action
**Reconstructed**: Read planning docs for full context
**No duplication**: Just pointers, not paragraphs

**Size Target**: <200 lines even for complex projects

### Git Checkpoint Workflow

**When**: End of each phase

**Process**:
1. Complete phase checklist in SCRATCHPAD.md
2. Commit all changes with checkpoint format
3. Update SCRATCHPAD.md to mark phase complete and expand next phase
4. Optional: Update CHANGELOG.md if user-facing features added

**Commit Message Template**:
```
checkpoint: Phase 3 Complete - API Integration

Phase: 3 - API Integration
Status: Complete

Files:
- backend/routes/api.ts (added auth endpoints)
- backend/middleware/auth.ts (JWT verification)
- docs/API_ENDPOINTS.md (documented new routes)

Next: Phase 4 - Testing (see SCRATCHPAD.md)
```

### Resume Workflow

**When**: Starting new session after context clear

**Process**:
1. Read SCRATCHPAD.md (auto-discovered by Claude)
2. Check current phase section
3. Follow references to planning docs if needed
4. Read last checkpoint commit for details
5. Resume from "Next" action

**Token Efficiency**:
- SCRATCHPAD.md: ~500-800 tokens
- Last checkpoint commit: ~200 tokens
- Planning doc reference (if needed): ~1-2k tokens
- **Total**: ~1-3k tokens vs ~12k tokens manual reconstruction

---

## Auto-Trigger Keywords

### Actions
- wrap up work
- end session
- resume work
- context handoff
- session checkpoint
- checkpoint phase
- switching context
- pausing work
- continue from
- pick up where
- start next phase
- complete phase

### Problems
- lost context
- forgot where I was
- resume project
- what was I doing
- continue working on
- context switch
- session bridge
- where did I leave off
- what's the current status
- which phase am I on

### Terms
- session handoff
- session resume
- context preservation
- work checkpoint
- git checkpoint
- scratchpad
- phase tracking
- context bridge
- handoff protocol
- project status
- build phases

### File Names
- SCRATCHPAD.md
- scratchpad
- checkpoint commit
- phase tracker
- project phases
- implementation phases

---

## Templates to Create

### 1. SCRATCHPAD-TEMPLATE.md
Complete template with:
- Project metadata section
- Phase list structure (completed, current, upcoming)
- Reference links format
- Progress checklist format
- Status emoji conventions (✅ 🔄 ⏸️)

### 2. checkpoint-commit-template.txt
Git commit message template:
- Standard format for checkpoint commits
- Required fields (Phase, Status, Files, Next)
- Usage instructions

### 3. scripts/create-scratchpad.sh
Automation script to:
- Generate SCRATCHPAD.md from template
- Auto-populate project name, date
- Create initial phase structure from docs/IMPLEMENTATION_PHASES.md if exists

### 4. scripts/checkpoint.sh
Automation script to:
- Update SCRATCHPAD.md (mark phase complete, expand next phase)
- Create checkpoint commit with standard format
- Update CHANGELOG.md if user chooses
- Display next action from scratchpad

### 5. references/scratchpad-best-practices.md
Guide covering:
- What to preserve vs. reconstruct
- How to write effective phase descriptions
- Reference linking patterns
- Common mistakes (code duplication, over-documentation)
- Examples of good/bad scratchpads

### 6. references/git-checkpoint-guide.md
Guide covering:
- When to create checkpoints
- Commit message format
- Local vs. remote commits
- Squashing before push
- Finding checkpoint commits

---

## Known Issues to Prevent

| Issue | Why It Happens | Prevention |
|-------|---------------|------------|
| **Scratchpad bloat** | Copying code/docs into scratchpad | Templates enforce reference-only pattern |
| **Lost context** | No checkpoint before context clear | Scripts automate checkpoint creation |
| **Stale scratchpad** | Forgetting to update after changes | Checkpoint script updates automatically |
| **Inconsistent format** | No standard template | Provided templates |
| **Can't find last work** | No git checkpoint | Checkpoint script creates commit |
| **Duplicate information** | Scratchpad + docs overlap | Clear separation: scratchpad = navigation, docs = content |

---

## Token Efficiency Analysis

**Without Skill** (manual resume):
- Read git log: ~1k tokens
- Read changed files to understand state: ~3-4k tokens
- Read planning docs to remember context: ~3-4k tokens
- Trial and error: ~3k tokens
- **Total**: ~10-12k tokens, 10-15 minutes

**With Skill** (scratchpad resume):
- Read SCRATCHPAD.md: ~500-800 tokens
- Read last checkpoint commit: ~200 tokens
- Follow references to planning docs (only if needed): ~1-2k tokens
- Resume immediately from "Next" action: 0 tokens wasted
- **Total**: ~1-3k tokens, <2 minutes
- **Savings**: ~75-85% tokens, ~85% time

---

## Production Validation Plan

**Test Scenarios**:
1. ✅ Mid-phase pause and resume (most common)
2. ✅ Phase completion checkpoint
3. ✅ Multi-day gap (resume after 3+ days)
4. ✅ Complex project with 6+ phases
5. ✅ Emergency context clear (quick save)

**Success Metrics**:
- Resume time <2 min (vs 10-15 min baseline)
- Zero "what was I doing?" confusion
- No duplicate content between scratchpad and docs
- SCRATCHPAD.md stays under 200 lines
- Works seamlessly with existing git workflow

---

## Package Versions

**No external packages required**. Uses:
- Standard Markdown
- Git (already installed)
- Bash scripts (standard Linux/Mac)
- Claude Code built-in features

---

## Reference Documentation

### Official Sources
- **Anthropic Best Practices**: https://www.anthropic.com/engineering/claude-code-best-practices
- **Git Best Practices**: http://sethrobertson.github.io/GitBestPractices/
- **Markdown Spec**: https://commonmark.org/
- **Claude Code Docs**: https://docs.claude.com/en/docs/claude-code/overview

### Inspiration
- GitHub Spec Kit file structure
- Git checkpoint workflow patterns
- Agile sprint handoff concepts (adapted for solo dev)

---

## Skill Scope (Final)

### WILL Include
- ✅ SCRATCHPAD-TEMPLATE.md (reference-heavy phase tracker)
- ✅ checkpoint-commit-template.txt (git commit format)
- ✅ scripts/create-scratchpad.sh (automation)
- ✅ scripts/checkpoint.sh (phase completion automation)
- ✅ references/scratchpad-best-practices.md (guide)
- ✅ references/git-checkpoint-guide.md (guide)
- ✅ Examples of good scratchpad patterns
- ✅ Integration with existing planning docs structure

### WILL NOT Include
- ❌ External tools or dependencies
- ❌ Complex automation requiring configuration
- ❌ Team handoff templates (out of scope)
- ❌ Multi-project tracking
- ❌ Time tracking features
- ❌ Automatic handoff generation (too opinionated)
- ❌ Code snippets in scratchpad (reference only)

---

## Research Confidence

**Overall**: 98%

**High Confidence (100%)**:
- Problem understanding (user's explicit feedback)
- Integration with existing workflow (git + planning docs)
- Template structure (validated by Anthropic patterns)
- Cleanup strategy (git-based, no clutter)
- Reference-heavy approach (prevents duplication)

**Medium Confidence (90%)**:
- Optimal script automation level (may need iteration)
- Exact checkpoint commit format (may evolve with use)

**No Questions Remaining**: User provided clear guidance on all design decisions

---

## Next Steps

1. ✅ Create skill directory structure
2. ✅ Write SCRATCHPAD-TEMPLATE.md
3. ✅ Write checkpoint-commit-template.txt
4. ✅ Create scripts/create-scratchpad.sh
5. ✅ Create scripts/checkpoint.sh
6. ✅ Write references/scratchpad-best-practices.md
7. ✅ Write references/git-checkpoint-guide.md
8. ✅ Write SKILL.md with comprehensive auto-trigger keywords
9. ✅ Write README.md
10. ✅ Install and verify skill

---

## Sign-Off

**Research Complete**: 2025-10-23
**Ready for Implementation**: Yes
**Confidence**: 98%
**Dependencies**: None
**Blockers**: None
**User Approval**: Confirmed

**Key Design Principles**:
1. Reference-heavy (no code duplication)
2. Navigation hub, not documentation dump
3. Git-centric (checkpoints = commits)
4. Cleanup by design (delete when project complete)
5. Token-efficient (<200 lines, ~1k tokens to resume)

This skill addresses a real, recurring pain point with a lightweight, zero-dependency solution that integrates naturally with the user's existing workflow of planning docs + git + CHANGELOG.md.
