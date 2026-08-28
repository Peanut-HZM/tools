---
name: smart-multi-commit
description: 智能拆分、提交并推送多模块仓库改动。用户明确要求”提交/commit/按模块提交/分前后端提交”时必须使用：先通过 rebase 更新当前分支，再根据当前项目实际结构识别后端模块、前端子项目、公共模块、CI/构建配置和文档边界，自动拆分多个本地 commit；所有分组 commit 成功后必须统一执行普通 git push 推送远程；默认排除无关文档，但自动关联与代码变更属于同一功能迭代的设计文档、计划文档和 openspec 变更文件。
---

# Smart Multi Commit

## Overview

Use this skill when the user explicitly asks to commit repository changes and the working tree may contain multiple logical changes, modules, frontend/backend projects, CI/build files, or documentation. The goal is to create small, accurate local commits that reflect real diff boundaries, then push them to the current upstream so remote deployments can pick up the latest code.

This skill is conservative because Git writes history. If the user has not clearly authorized a commit, only analyze and propose a commit plan.

## Trigger Rules

Use this skill only when the user clearly says they want a commit, for example:

- `提交代码`
- `commit`
- `按模块提交`
- `分前后端提交`
- `把这些改动提交到本地`

Do not treat these as authorization:

- `改好了`
- `下一步可以提交`
- `帮我看下 diff`
- `生成提交建议`
- `准备提交`

When authorization is missing, stop before any Git write operation and explain what would be committed.

## Git Safety Gate

Before doing anything that changes Git state:

- Never run `git add` or `git commit` unless the user explicitly asked to commit.
- When the user explicitly asks this skill to commit, commit means commit and push to the current upstream.
- After all commit groups succeed, run one ordinary `git push`.
- Never run `git push --force` or `git push --force-with-lease`.
- Never run destructive or history-changing commands such as `git reset --hard`, `git clean`, force push, `git rebase -i`, or `git commit --amend` unless the user explicitly asks and the repository safety rules allow it.
- Never skip hooks with `--no-verify` unless the user explicitly asks.
- Never update Git config.
- Never stage secrets, credentials, private keys, certificates, tokens, passwords, `.env` files, or similar sensitive files without stopping for explicit confirmation.
- 敏感文件必须先拦截并单独确认，不能因为用户说“提交全部”就直接纳入提交。
- If files are already staged, inspect them first. Do not overwrite the user's staged intent blindly.

Default behavior is commit and push. If push fails, local commits exist but the remote branch is not updated, and deployment will not include those local commits.

## Required Pre-Commit Rebase

Before creating any commit, update the current branch by rebase:

```bash
git status --porcelain
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git fetch --all --prune
git pull --rebase --autostash
```

Rules:

- If the current branch has no upstream, stop and ask the user to set an upstream or specify the base branch.
- If `git fetch` or `git pull --rebase --autostash` exits non-zero, stop immediately.
- If rebase reports conflicts, stop immediately. Do not run `git add` or `git commit` while rebase is unresolved.
- If autostash restore fails, stop and report the state.
- After a successful rebase, reread `git status --porcelain`, `git diff`, and `git diff --staged`. Build the commit plan from the updated working tree, not from stale pre-rebase output.

## Required Analysis

Always inspect:

```bash
git status --porcelain
git diff
git diff --staged
git log --oneline -n 10
```

Use the output to determine:

- Which files are modified, new, deleted, or already staged.
- Whether any staged files conflict with the automatic grouping.
- The repository's recent commit message style.
- Whether any files should be excluded by default.

If staged files do not match the grouping that this skill would create, stop and ask whether to keep the staged grouping or restage by logical groups.

## Project Profiling

Build a project profile before grouping commits.

General rules:

- Maven backend modules: identify by root `pom.xml`, child `pom.xml`, `src/main/java`, `src/main/resources`, and `src/test/java`.
- Frontend subprojects: identify by `package.json`, `vue.config.*`, `vite.config.*`, `src/`, `public/`, and common frontend lockfiles.
- CI/deploy files: identify by `.github/`, `.gitlab-ci.yml`, `Jenkinsfile`, `deploy/`, `*.pipeline`, Docker files, and deployment scripts.
- Documentation and plans: identify by `docs/`, `README.md`, `CHANGELOG.md`, design plans, implementation plans, and Markdown-only changes.
- SQL/domain scripts: identify by `sql/<domain>/**`; treat business-domain SQL as module-owned change, not as generic scripts.
- Scripts and tools: identify by `scripts/`, `tools/`, `*.sh`, `*.py`, and classify by actual diff content.

Repository-specific rules for `dhr_glodon_rlcb`:

- Treat `tpehr-modules/<module>` as backend module boundaries.
- Treat `app-*-web` as frontend subproject boundaries.
- Treat `deploy/jenkins` as CI/deployment configuration.
- Treat `logs/`, smoke output files, generated local output, and temporary artifacts as excluded by default.
- Treat `sql/portal/**` as `portal-bff` database changes.
- Treat `sql/recruit/**` as `recruit-bff` database changes.
- Treat `sql/system/**` as `system` database or configuration changes.
- Treat `sql/report/**`, `sql/bonus/**`, and `sql/budget/**` as their matching business-domain changes.
- Treat `sql/job/**` and `sql/menu/**` as cross-domain directories that must be mapped by filename, SQL comments, menu names, route names, or domain words before considering a standalone SQL commit.
- Treat `docs/plans/` as design/plan documents that may be correlated with code changes; apply document correlation rules.
- Treat `docs/superpowers/specs/` as brainstorming-generated specs that may be correlated with code changes.
- Treat `openspec/changes/` and `openspec/specs/` as openspec change documents that may be correlated with code changes.

## Document Correlation Rules

After grouping code changes, scan untracked and modified documents and correlate them with code groups.

**Correlation scope** (files eligible for correlation):

- `docs/plans/YYYY-MM-DD-*design*.md` — design documents
- `docs/plans/YYYY-MM-DD-*implementation-plan*.md` — implementation plans
- `docs/superpowers/specs/YYYY-MM-DD-*design*.md` — brainstorming-generated specs
- `openspec/changes/*/` — openspec change directories and their files
- `openspec/specs/` — modified spec files

**Matching strategy** (apply in priority order):

1. **Date matching**: Documents created on the same day or adjacent days as the code changes are prioritized for correlation.
2. **Keyword matching**: Extract functional keywords from code diff and match against document filenames.
   - Class names: `OrgReview` → `org-review`
   - Method names: `importJudge` → `import-judge`
   - SQL table names: `employment_certificate` → `employment-certificate`
   - Module names: `office-bff` → `office`, `portal-bff` → `portal`
3. **Module mapping**:
   - `tpehr-office-bff` code → match `employment-certificate`, `org-review`, `office` keywords
   - `tpehr-portal-bff` code → match `portal`, `team-dashboard`, `team-roster`, `team-attendance` keywords
   - `tpehr-recruit-bff` code → match `recruit` keywords
4. **Content scan**: When filename matching is insufficient, scan the first 50 lines of documents for class names, method names, table names, or feature names that appear in the code diff.

**Do NOT correlate** (exclude by default):

- Standalone analysis reports (e.g., `xxx流程分析.md`, `xxx需求评估.md`)
- Pure README updates with no code correlation
- Requirements documents without corresponding code changes
- Binary files (images, PDFs, screenshots) unless user explicitly requests inclusion
- Documents where no code changes exist in the working tree

**Correlation outcome**:

- Correlated documents are merged into the same commit as their matching code group.
- Non-correlated documents are excluded by default (reported as skipped).
- Pure document-only changes (no code) are excluded by default.

## SQL Grouping Rules

Business SQL is not a generic script. If a SQL file can be mapped to a business module, group it with that module.

- `sql/portal/**` belongs with `portal-bff`.
- `sql/recruit/**` belongs with `recruit-bff`.
- `sql/system/**` belongs with `system` or auth/system changes based on surrounding diff.
- `sql/report/**`, `sql/bonus/**`, and `sql/budget/**` belong with their matching business-domain modules.
- `sql/job/**` and `sql/menu/**` are not standalone modules by default; map by filename, SQL comments, menu names, route names, or domain words first.
- If source code and related SQL in the same business domain are both changed, commit them together.
- If only SQL changed but the domain is clear, use the business module scope, not `sql`.
- If SQL supports a frontend and backend feature together, group it with the backend BFF or persistence-owning module; keep frontend code in its own frontend commit.
- If ownership is ambiguous or spans multiple domains, stop and ask the user.
- Highlight risky SQL such as `DROP`, `TRUNCATE`, unconditional `DELETE`, unconditional `UPDATE`, or broad DDL in the plan/final report instead of silently committing it.

## Grouping Rules

Prefer one logical change per commit.

- Put backend source, mapper, resource, and related tests from the same module in the same commit.
- Put frontend pages, components, API wrappers, styles, and tests from the same subproject in the same commit.
- Group business-domain SQL with the owning backend or business module; do not split it into a standalone SQL commit merely because it lives under `sql/`.
- Split frontend and backend commits by default, even when they support the same feature.
- Split different backend modules by default.
- Commit shared/common module changes separately from business module changes.
- Commit CI, build, dependency, and deployment configuration separately unless the diff is inseparable from a single module.
- After grouping code changes, apply Document Correlation Rules to correlate design documents, plan documents, and openspec changes with code groups.
- Correlated documents are committed together with their matching code in a single commit representing one feature iteration.
- If a file cannot be classified confidently, do not commit it. List it as requiring user confirmation.

## Default Exclusions

Exclude unless the user explicitly asks to include them and they are not sensitive:

- `logs/`
- `*.log`
- smoke output files such as `smoke-output.*`
- local test output bodies, downloaded PDFs, screenshots, and ad hoc artifacts
- temporary files, IDE caches, and generated local data
- `docs/` documents that fail Document Correlation Rules matching (no correlated code change)

Apply Document Correlation Rules before exclusion: design documents, implementation plans, and openspec changes correlated with code are included in the same commit.

Even with explicit inclusion, never include sensitive files without stopping for separate confirmation.

## Commit Message Rules

Use Chinese Conventional Commit style:

```text
<type>(<scope>): <description>
```

Common types:

- `feat`: 新增功能
- `fix`: 修复问题
- `perf`: 性能优化
- `refactor`: 重构
- `test`: 测试
- `docs`: 文档
- `ci`: CI 配置
- `build`: 构建配置
- `chore`: 维护类改动

Examples:

```text
fix(portal-bff): 修复团队看板快照批量写入逻辑
test(portal-bff): 补充团队看板快照写入测试
feat(portal-bff): 新增团队编制看板表结构和数据源
feat(recruit-bff): 初始化招聘菜单与字典数据
ci(file-svc): 调整文件服务流水线配置
docs: 更新本地登录设计说明
```

Message requirements:

- Base the message on the real diff for that commit group, including correlated documents.
- Do not use vague messages such as `更新代码`, `修改文件`, or `调整逻辑`.
- Use the narrowest meaningful scope, such as `portal-bff`, `system-web`, `file-svc`, `ci`, or `docs`.
- When documents are correlated with code, generate a unified message that covers the entire feature iteration (code + documents).
- Read correlated document titles and content to inform the commit message description when the document better describes the feature than the code diff alone.

## Execution Workflow

1. Confirm the user explicitly authorized committing.
2. Read Git status, unstaged diff, staged diff, and recent commit style.
3. Check the current branch and upstream branch.
4. Fetch and update by `git pull --rebase --autostash`.
5. Stop if rebase, upstream, or autostash handling fails.
6. Reread Git status and diffs after rebase.
7. Build the project profile.
8. Split changes into logical groups by module.
9. Apply Document Correlation Rules: scan untracked/modified documents and correlate with code groups.
10. Merge correlated documents into matching code groups; exclude non-correlated documents by default.
11. Stop on sensitive files, staged conflicts, or unclassified files.
12. Generate one Chinese commit message per group based on code diff and correlated document content.
13. For each group, run `git add` with explicit file paths only, then commit with a HEREDOC message:

```bash
git commit -m "$(cat <<'EOF'
fix(scope): 中文提交说明

EOF
)"
```

1. After each commit, reread `git status --porcelain` to verify the group was committed.
2. Continue with the next group only if the previous commit succeeded.
3. After all commit groups succeed, run one ordinary `git push`.
4. If push succeeds, include the pushed branch in the final report.
5. If push fails, report that local commits exist but remote was not updated and deployment will not include those commits.
6. Summarize created commits, push result, and remaining files.

## Failure Handling

- Rebase conflict or failure: stop, report the current state, and do not stage or commit.
- Missing upstream: stop and ask the user to set upstream or specify how to update.
- Hook failure: stop subsequent commits and report the hook output and completed commits.
- Commit failure before all groups finish: do not push.
- Push failure: do not force push or retry with history-changing commands; report that deployment will not include local commits until push succeeds.
- Existing staged files conflict with grouping: stop and ask whether to preserve staged intent.
- Sensitive file found: stop and request explicit confirmation for that file.
- Only excluded files remain: do not commit; report skipped files and reasons.
- Commit succeeds but hooks modify files: do not amend automatically; report the new changes and wait for instructions.

## Final Report

Always finish with a concise report:

```markdown
## 提交结果
- `<hash>` `fix(portal-bff): 修复团队看板快照批量写入逻辑` — 3 个文件
  关联文档：docs/plans/2026-05-22-portal-snapshot-fix-design.md
- `<hash>` `ci(file-svc): 调整文件服务流水线配置` — 1 个文件

## 跳过文件
- `docs/plans/2026-05-21-team-roster-display-export-design.md`：未找到关联的代码变更
- `docs/任务实战/团队费用计算逻辑.md`：独立分析报告，默认排除
- `logs/...`：本地日志默认排除

## 未提交文件
- `path/to/file`：无法归类，需要确认

## 远程推送结果
- 成功：已执行普通 `git push`，远程分支已更新
- 失败：本地已提交但远程未更新，部署不会包含这些本地 commit

## 验证说明
未主动运行编译或测试；本 skill 仅完成 Git 分组与提交。
```

If no commit was created, say so clearly and explain why.
