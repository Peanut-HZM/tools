# Implementation Phases: streamlit-snowflake Skill

**Project**: Claude Code Skill for Streamlit in Snowflake
**Type**: Skill Creation
**Estimated Total**: 2-3 hours (~5-10 min human time)
**Created**: 2024-12-24

---

## Phase 1: Skill Foundation (30 min)

**Type**: Setup
**Objective**: Create skill directory structure with SKILL.md and README.md

### Tasks

1. Create skill directory: `skills/streamlit-snowflake/`
2. Create SKILL.md with:
   - YAML frontmatter (name, description)
   - Overview section
   - Quick start guide
   - When to use / when not to use
   - Known limitations (no custom components, package restrictions)
   - Error prevention table
3. Create README.md with:
   - Auto-trigger keywords (streamlit snowflake, SiS, native app marketplace)
   - Brief description
   - Link to SKILL.md

### Verification
- [ ] SKILL.md has valid YAML frontmatter
- [ ] Description is 250-350 characters
- [ ] README.md has trigger keywords
- [ ] Skill structure matches repo standards

### Key Files
- `skills/streamlit-snowflake/SKILL.md`
- `skills/streamlit-snowflake/README.md`

---

## Phase 2: Core Templates (1 hour)

**Type**: Templates
**Objective**: Create production-ready project scaffold templates

### Tasks

1. Create `templates/snowflake.yml`:
   - Definition version 2
   - Placeholder for warehouse, stage, identifier
   - External access integrations section
   - Secrets section
   - Artifacts list
   - Grants section

2. Create `templates/environment.yml`:
   - Required `channels: - snowflake`
   - Explicit `streamlit=1.35.0`
   - Common packages: pandas, plotly, altair
   - snowflake-snowpark-python

3. Create `templates/streamlit_app.py`:
   - Snowpark session via `st.connection("snowflake")`
   - `@st.cache_data` pattern for queries
   - Basic layout structure
   - Error handling pattern

4. Create `templates/pages/data_explorer.py`:
   - Multi-page example
   - DataFrame display
   - Chart example

5. Create `templates/common/utils.py`:
   - Reusable query helpers
   - Session getter

6. Create `templates/.gitignore`:
   - .snowflake/
   - __pycache__/
   - .env
   - *.pyc

### Verification
- [ ] snowflake.yml is valid YAML
- [ ] environment.yml has required channels field
- [ ] streamlit_app.py runs locally (syntax check)
- [ ] No hardcoded credentials in any template

### Key Files
- `skills/streamlit-snowflake/templates/`

---

## Phase 3: Native App Templates (30 min)

**Type**: Templates
**Objective**: Add Marketplace publishing templates

### Tasks

1. Create `templates-native-app/manifest.yml`:
   - Version format
   - Artifacts section
   - Streamlit configuration
   - Privileges required

2. Create `templates-native-app/setup.sql`:
   - CREATE APPLICATION ROLE
   - CREATE SCHEMA IF NOT EXISTS
   - CREATE STREAMLIT statement
   - GRANT statements

3. Create `templates-native-app/README.md`:
   - Provider profile setup steps
   - Listing creation workflow
   - Stripe setup (for paid listings)
   - Approval process overview

### Verification
- [ ] manifest.yml follows Snowflake Native App spec
- [ ] setup.sql has valid SQL syntax
- [ ] README covers complete publishing workflow

### Key Files
- `skills/streamlit-snowflake/templates-native-app/`

---

## Phase 4: References & Scripts (30 min)

**Type**: Documentation
**Objective**: Add supporting reference docs and helper scripts

### Tasks

1. Create `references/available-packages.md`:
   - How to query available packages (SQL)
   - Link to Snowpark Python Packages Explorer
   - Common packages list with versions

2. Create `references/authentication.md`:
   - Key-pair authentication pattern
   - OAuth client credentials pattern
   - Password deprecation timeline (Oct 2026)
   - Workload Identity Federation mention

3. Create `references/ci-cd.md`:
   - GitHub Actions workflow template
   - Secrets configuration
   - Deploy command patterns

4. Create `scripts/check-packages.sql`:
   - Query to list available packages
   - Filter by name pattern

### Verification
- [ ] All reference docs have working links
- [ ] SQL script is valid
- [ ] Authentication patterns are current (2025)

### Key Files
- `skills/streamlit-snowflake/references/`
- `skills/streamlit-snowflake/scripts/`

---

## Phase 5: Install & Test (30 min)

**Type**: Verification
**Objective**: Install skill and validate it works

### Tasks

1. Run install script:
   ```bash
   ./scripts/install-skill.sh streamlit-snowflake
   ```

2. Verify symlink created:
   ```bash
   ls -la ~/.claude/skills/streamlit-snowflake
   ```

3. Test skill discovery:
   - Ask Claude Code: "Help me set up a Streamlit app in Snowflake"
   - Verify skill is proposed/discovered

4. Generate marketplace manifest:
   ```bash
   ./scripts/generate-plugin-manifests.sh streamlit-snowflake
   ```

5. Run metadata check:
   ```bash
   ./scripts/check-metadata.sh streamlit-snowflake
   ```

6. Commit skill to repo:
   ```bash
   git add skills/streamlit-snowflake/
   git commit -m "Add streamlit-snowflake skill for native Snowflake apps"
   ```

### Verification
- [ ] Symlink exists and points correctly
- [ ] Skill discovered by Claude Code
- [ ] Marketplace manifest generated
- [ ] Metadata check passes
- [ ] Committed to git

### Key Files
- `~/.claude/skills/streamlit-snowflake` (symlink)
- `skills/streamlit-snowflake/.claude-plugin/plugin.json`

---

## Success Criteria (All Phases)

- [ ] Skill structure matches repo standards (SKILL.md, README.md, templates/)
- [ ] YAML frontmatter valid with 250-350 char description
- [ ] Templates are production-ready (no hardcoded values)
- [ ] Error prevention documented (5+ common errors)
- [ ] References include current auth patterns (2025)
- [ ] Skill installs and is discoverable
- [ ] Token savings estimated ≥50%

---

## Estimated Token Savings

| Scenario | Without Skill | With Skill | Savings |
|----------|---------------|------------|---------|
| Project setup | ~8k tokens | ~3k tokens | ~62% |
| Marketplace publishing | ~6k tokens | ~2k tokens | ~67% |
| Auth troubleshooting | ~4k tokens | ~1k tokens | ~75% |
| **Average** | **~6k tokens** | **~2k tokens** | **~67%** |

---

## Dependencies

- None (skill creation only requires text files)
- Testing requires Snowflake account (optional, can validate syntax only)
