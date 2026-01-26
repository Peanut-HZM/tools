# AI Agent Guide to Claude Code Skills

**Purpose**: Onboarding guide for AI agents (Gemini, GPT, Claude, etc.) to effectively use the Claude Code skills repository.

**Repository Path**: `/home/jez/Documents/claude-skills/`

**Last Updated**: 2025-11-20

---

## TL;DR - Quick Start

**What**: Production-tested implementation patterns for modern web development (59 skills covering Cloudflare, AI APIs, React, databases, auth, etc.)

**Where**: `/home/jez/Documents/claude-skills/skills/[skill-name]/SKILL.md`

**How**: Read `SKILL.md` for instructions → Copy `templates/` for starter code → Reference known errors sections

**Why**: Prevents documented production issues, uses current package versions, saves development time

**Quality**: All skills are production-tested, standards-compliant, regularly verified

---

## Navigation Priority

### Read These Files First

1. **README.md** - Repository overview
2. **CLAUDE.md** - Project standards, tech stack preferences, global context
3. **ONE_PAGE_CHECKLIST.md** - Quality standards reference
4. **skills/[skill-name]/SKILL.md** - The actual implementation knowledge
5. **skills/[skill-name]/README.md** - User-facing documentation

### Directory Structure Overview

```
claude-skills/
├── README.md                  # ← Repository overview
├── CLAUDE.md                  # ← Project context
├── CONTRIBUTING.md            # How to contribute
├── ONE_PAGE_CHECKLIST.md      # Quality standards
│
├── skills/                    # ← 63 production skills
│   ├── cloudflare-worker-base/
│   ├── tailwind-v4-shadcn/
│   ├── ai-sdk-core/
│   └── [56 more...]
│
├── templates/                 # Skill creation templates
├── planning/                  # Standards and research
├── scripts/                   # Automation tools
└── examples/                  # Working projects
```

---

## Understanding Skills

### What is a "Skill"?

A skill is a **knowledge package** containing:

- **Implementation patterns** - Step-by-step instructions
- **Working templates** - Copy-paste starter code
- **Known issues** - Documented production bugs and fixes
- **Current versions** - Verified package versions
- **Best practices** - Official patterns from docs

**Philosophy**: "Atomic Skills" - One skill = One focused domain

**Examples**:
- `cloudflare-d1` - D1 database setup and usage (NOT "all Cloudflare storage")
- `tailwind-v4-shadcn` - Tailwind v4 + shadcn/ui (NOT "all UI frameworks")
- `openai-api` - OpenAI API integration (NOT "all AI providers")

### Skill Directory Structure

```
skills/my-skill/
├── SKILL.md              # ← Main instructions (imperative)
├── README.md             # ← Description (third-person)
├── scripts/              # Automation scripts
│   └── setup.sh
├── references/           # Official docs, examples
│   └── cloudflare-docs.md
├── assets/               # Images, diagrams
│   └── architecture.png
└── templates/            # Copy-paste starter code
    ├── package.json
    ├── wrangler.jsonc
    └── src/
        └── index.ts
```

**Key Files**:
- **SKILL.md** - Contains the actual implementation knowledge
- **templates/** - Working starter code you can copy
- **README.md** - User-facing docs with auto-trigger keywords

---

## How to Extract Knowledge from a Skill

### Step-by-Step Workflow

When a user asks: *"Set up a Cloudflare Worker with D1 database"*

**Your Process**:

```
1. IDENTIFY SKILLS
   - Access: /home/jez/Documents/claude-skills/skills/
   - Skills needed: cloudflare-worker-base + cloudflare-d1

2. READ YAML FRONTMATTER
   - Open: cloudflare-worker-base/SKILL.md
   - Check: name, description fields
   - Verify: This is the right skill

3. SCAN "USE WHEN" SECTION
   - Confirms: When to apply this skill
   - Example: "Use when setting up new Cloudflare Workers project"

4. READ "COMMON ERRORS PREVENTED"
   - Lists: Documented production issues
   - Example: "node_compat flag is deprecated"
   - Solution: Use nodejs_compat instead

5. STUDY TEMPLATES
   - Location: cloudflare-worker-base/templates/
   - Extract: package.json, wrangler.jsonc, src/index.ts
   - Copy: Working starter code

6. CHECK VERSION INFO
   - Look for: "Package Versions" sections
   - Current: wrangler@4.x, @cloudflare/workers-types@4.x
   - Avoid: Outdated versions

7. COMBINE SKILLS
   - Read: cloudflare-d1/SKILL.md
   - Merge: D1 patterns with Worker base
   - Result: Complete working solution
```

### YAML Frontmatter Structure

**Required Fields** (top of SKILL.md):

```yaml
---
name: cloudflare-worker-base
description: |
  Use when setting up Cloudflare Workers projects with Vite, React, and static assets.
  Provides production-tested configuration for Workers with the @cloudflare/vite-plugin.
license: MIT
---
```

**Field Meanings**:
- `name` - Skill identifier (lowercase-with-hyphens)
- `description` - What it does + when to use it (third-person)
- `license` - Always MIT for this repo

**Optional Fields**:
- `allowed-tools` - Restrict tool usage (rarely used)
- `metadata` - Additional context (versions, last verified, etc.)

---

## Critical Standards to Know

### Writing Style Conventions

**SKILL.md Body**: Imperative form (commands)
```markdown
✅ "Install dependencies with npm install"
✅ "Configure wrangler.jsonc with account ID"
✅ "Deploy using wrangler deploy"

❌ "You should install dependencies"
❌ "The developer needs to configure..."
```

**README.md**: Third-person (descriptions)
```markdown
✅ "This skill helps you set up Cloudflare Workers"
✅ "Use when starting a new Workers project"

❌ "Install dependencies with npm install"
❌ "You should use this skill when..."
```

### Directory Naming Conventions

**Official Standard**:
- `scripts/` - Executable automation (bash, Python, etc.)
- `references/` - External docs, code examples, screenshots
- `assets/` - Images, diagrams, media files
- `templates/` - Copy-paste starter code

**Purpose**:
- Makes skills predictable and scannable
- AI agents know where to find what they need
- Consistent across all 59 skills

---

## Key Insights from Global Context

### Tech Stack Preferences (from CLAUDE.md)

**Cloudflare Platform**:
- ✅ Cloudflare Workers + Static Assets
- ❌ NEVER Cloudflare Pages (deprecated pattern)
- Storage: D1 (SQL), R2 (objects), KV (key-value)
- AI: Workers AI, Vectorize, Agents

**Frontend**:
- React 19 + Vite
- Tailwind v4 (NOT v3)
- shadcn/ui with semantic colors
- ❌ NEVER raw Tailwind colors (use `bg-primary` not `bg-blue-500`)

**Backend**:
- Hono for routing
- Drizzle ORM for D1
- better-auth or Clerk for authentication

**AI Models**:
- OpenAI: GPT-5 (gpt-5, gpt-5-mini, gpt-5-nano)
- Anthropic: Claude Sonnet 4.5 (claude-sonnet-4-5)
- Google: Gemini 3.0 Pro Preview (gemini-3-pro-preview), Gemini 2.5 (gemini-2.5-pro, gemini-2.5-flash)
- Vercel AI SDK V5 for multi-provider support

### Critical Rules (NEVER Break These)

From global CLAUDE.md:

- ❌ **Never use Cloudflare Pages** → Always Workers with Static Assets
- ❌ **Never use raw Tailwind colors** → Use semantic tokens (`bg-primary`, `text-foreground`)
- ❌ **Never commit .dev.vars or secrets** → Always in .gitignore
- ❌ **Never use node_compat** → Use `nodejs_compat` compatibility flag (Wrangler v4+)
- ✅ **Always check ~/.claude/skills/ first** → Use production-tested patterns
- ✅ **Always use SESSION.md for multi-phase projects** → Enables context handoff

### Token Efficiency Metrics

**Why Skills Matter**:

| Scenario | Without Skill | With Skill | Savings |
|----------|---------------|------------|---------|
| Setup Tailwind v4 + shadcn | ~15k tokens, 2-3 errors | ~5k tokens, 0 errors | ~67% |
| Cloudflare Worker setup | ~12k tokens, 1-2 errors | ~4k tokens, 0 errors | ~67% |
| D1 Database integration | ~10k tokens, 2 errors | ~4k tokens, 0 errors | ~60% |
| **Average** | **~12k tokens** | **~4.5k tokens** | **~62%** |

**Error Prevention**: 395+ documented errors prevented across all skills

---

## High-Value Skills to Prioritize

### Foundation Skills (Start Here)

**cloudflare-worker-base**
- Purpose: Core Workers setup with Vite + React
- Use when: Starting any Cloudflare Workers project
- Prevents: 8 common configuration errors
- Template: Full working starter project

**tailwind-v4-shadcn**
- Purpose: Tailwind v4 + shadcn/ui setup
- Use when: Building UI with React
- Prevents: 7 theming and color usage errors
- Template: Complete theme configuration
- **Gold Standard**: Best example of skill structure

**project-planning**
- Purpose: Generate planning docs (IMPLEMENTATION_PHASES.md, etc.)
- Use when: Starting new projects or major features
- Generates: DATABASE_SCHEMA.md, API_ENDPOINTS.md, ARCHITECTURE.md
- Template: Context-safe phase planning

### AI Integration Skills

**ai-sdk-core**
- Purpose: Vercel AI SDK core functionality
- Use when: Integrating AI streaming responses
- Version: V5 (breaking changes from V4)
- Template: Multi-provider setup

**openai-api**
- Purpose: OpenAI API integration
- Use when: Using GPT models directly
- Models: GPT-5, GPT-5-mini, GPT-5-nano
- Template: Chat completions, streaming

**openai-agents**
- Purpose: OpenAI Agents SDK
- Use when: Building agentic workflows
- Template: Agent configuration, tools

**google-gemini-api**
- Purpose: Gemini API integration
- Use when: Using Gemini models
- Models: Gemini 3.0 Pro Preview, Gemini 2.5 Pro/Flash
- Template: Chat, embeddings, file uploads

**claude-api**
- Purpose: Claude API integration
- Use when: Using Claude models directly
- Models: Claude Sonnet 4.5, Haiku 4.5
- Template: Messages API, streaming

### Data Storage Skills

**cloudflare-d1**
- Purpose: D1 SQL database setup
- Use when: Need relational data storage
- Template: Schema, migrations, queries
- Integration: Works with Drizzle ORM

**cloudflare-kv**
- Purpose: KV key-value store
- Use when: Need fast key-value lookups
- Template: CRUD operations, TTL

**cloudflare-r2**
- Purpose: R2 object storage
- Use when: Need file storage (S3-compatible)
- Template: Upload, download, presigned URLs

**drizzle-orm-d1**
- Purpose: Drizzle ORM with D1
- Use when: Want type-safe SQL queries
- Template: Schema definition, migrations, queries

### Auth Skills

**clerk-auth**
- Purpose: Clerk authentication
- Use when: Need full-featured auth
- Template: JWT verification, middleware

**better-auth**
- Purpose: better-auth with D1
- Use when: Want simple, database-backed auth
- Template: Auth setup, session management
- CLI: `npx @better-auth/cli generate`

---

## Quality Markers (Production-Tested Content)

### How to Recognize High-Quality Skills

**Version Numbers**:
```markdown
✅ "wrangler@4.20.0 or later"
✅ "@cloudflare/workers-types@4.20250106.0"

❌ "latest version of wrangler"
❌ "wrangler 3.x or 4.x"
```

**Known Errors with Sources**:
```markdown
✅ "Error: node_compat flag is deprecated (see: github.com/cloudflare/workers-sdk/issues/1234)"

❌ "May cause errors"
❌ "Sometimes doesn't work"
```

**Token Metrics**:
```markdown
✅ "Token savings: ~67% (15k → 5k tokens)"
✅ "Prevents 8 documented errors"

❌ "Saves time"
❌ "Reduces errors"
```

**Verification Commands**:
```markdown
✅ "Verify: npm run dev should start on http://localhost:5173"
✅ "Check: wrangler deploy should succeed without errors"

❌ "Test that it works"
❌ "Make sure deployment succeeds"
```

**Production References**:
```markdown
✅ "Production tested: WordPress Auditor (deployed 2025-10-15)"
✅ "Used in: 5+ production deployments"

❌ "Should work in production"
❌ "Tested locally"
```

---

## Command Reference

### Accessing Skills

```bash
# List all available skills
ls /home/jez/Documents/claude-skills/skills/

# Read a specific skill
cat /home/jez/Documents/claude-skills/skills/cloudflare-worker-base/SKILL.md

# Read skill README
cat /home/jez/Documents/claude-skills/skills/cloudflare-worker-base/README.md

# List skill templates
ls /home/jez/Documents/claude-skills/skills/cloudflare-worker-base/templates/

# Copy template to working directory
cp -r /home/jez/Documents/claude-skills/skills/cloudflare-worker-base/templates/* ./
```

### Repository Navigation

```bash
# Get repository overview
cat /home/jez/Documents/claude-skills/README.md

# Read project context
cat /home/jez/Documents/claude-skills/CLAUDE.md

# Check quality standards
cat /home/jez/Documents/claude-skills/ONE_PAGE_CHECKLIST.md
```

### Version Checking (If You Can Run Bash)

```bash
# Check all versions across skills
/home/jez/Documents/claude-skills/scripts/check-all-versions.sh

# Check specific skill
/home/jez/Documents/claude-skills/scripts/check-all-versions.sh cloudflare-worker-base

# Individual checkers
/home/jez/Documents/claude-skills/scripts/check-npm-versions.sh
/home/jez/Documents/claude-skills/scripts/check-github-releases.sh
/home/jez/Documents/claude-skills/scripts/check-metadata.sh
/home/jez/Documents/claude-skills/scripts/check-ai-models.sh
```

---

## Practical Examples

### Example 1: New Cloudflare Worker Project

**User Request**: "Set up a new Cloudflare Worker with React frontend"

**Your Workflow**:

```
1. Identify skills needed:
   - cloudflare-worker-base (core setup)
   - tailwind-v4-shadcn (if UI needed)

2. Read cloudflare-worker-base/SKILL.md:
   - Scan "Use When" → Confirms correct skill
   - Read "Common Errors Prevented" → 8 issues to avoid
   - Check "Package Versions" → Current versions

3. Extract template:
   - Location: cloudflare-worker-base/templates/
   - Files: package.json, wrangler.jsonc, vite.config.ts, src/

4. Apply patterns:
   - Copy template structure
   - Follow step-by-step instructions in SKILL.md
   - Avoid documented errors

5. Result:
   - Working Workers + Vite + React setup
   - No configuration errors
   - Current package versions
```

### Example 2: Add D1 Database to Existing Worker

**User Request**: "Add D1 database to my Cloudflare Worker"

**Your Workflow**:

```
1. Read cloudflare-d1/SKILL.md

2. Follow binding workflow (CRITICAL ORDER):
   - Deploy Worker first: npm run build && npx wrangler deploy
   - Create D1 database: npx wrangler d1 create my-db
   - Add binding to wrangler.jsonc
   - Redeploy: npx wrangler deploy

3. Copy schema template:
   - Location: cloudflare-d1/templates/schema.sql
   - Run migrations: npx wrangler d1 execute my-db --local --file=schema.sql

4. Reference known errors:
   - "Cannot create binding for Worker that doesn't exist" → Deploy first
   - "Migrations not found" → Wrangler looks in /migrations, Drizzle generates in /drizzle

5. Result:
   - D1 database properly bound
   - Schema deployed
   - No binding errors
```

### Example 3: Integrate OpenAI API

**User Request**: "Add GPT-5 chat completion to my app"

**Your Workflow**:

```
1. Read openai-api/SKILL.md

2. Check current model names:
   - GPT-5: gpt-5
   - GPT-5 Mini: gpt-5-mini
   - GPT-5 Nano: gpt-5-nano

3. Extract template:
   - Location: openai-api/templates/chat-completion.ts
   - Copy streaming setup

4. Reference error prevention:
   - "Use fetch adapter for Cloudflare Workers"
   - "Store API key in .dev.vars, never commit"

5. Result:
   - Working GPT-5 integration
   - Proper streaming setup
   - Secure key management
```

### Example 4: Combine Multiple Skills

**User Request**: "Build a chatbot with Gemini and D1 for conversation history"

**Your Workflow**:

```
1. Identify skills:
   - cloudflare-worker-base (foundation)
   - google-gemini-api (AI integration)
   - cloudflare-d1 (database)
   - ai-sdk-ui (optional, for UI components)

2. Read all four SKILL.md files:
   - Extract compatible patterns
   - Note any integration points
   - Check for conflicts

3. Merge templates:
   - Start with cloudflare-worker-base template
   - Add google-gemini-api chat setup
   - Add cloudflare-d1 schema for conversations
   - Add ai-sdk-ui components

4. Follow each skill's known errors:
   - Worker setup errors (8 from base)
   - Gemini API errors (6 from gemini-api)
   - D1 binding errors (5 from d1)

5. Result:
   - Integrated chatbot with history
   - All patterns compatible
   - Zero setup errors
```

---

## Integration Tips

### Combining Skills Effectively

**Principle**: Skills are designed to be composable

**Compatible Combinations**:
- `cloudflare-worker-base` + `cloudflare-d1` + `drizzle-orm-d1`
- `cloudflare-worker-base` + `tailwind-v4-shadcn` + `ai-sdk-ui`
- `openai-api` + `cloudflare-vectorize` (RAG pattern)
- `clerk-auth` + `cloudflare-d1` (authenticated database)

**How to Merge**:
1. Start with base skill (e.g., `cloudflare-worker-base`)
2. Read additional skills in dependency order
3. Merge `package.json` dependencies
4. Merge `wrangler.jsonc` bindings
5. Combine code patterns
6. Follow all "known errors" sections

**Conflict Resolution**:
- If skills conflict, prioritize more specific skill
- Check `metadata.last_verified` dates (newer = more current)
- Consult CLAUDE.md for global preferences

### When to Use Multiple Skills

**Indicators**:
- User request spans multiple technologies
- Need foundation + feature skills
- Building full-stack application
- Integrating external services

**Example Combinations**:

```
Full-Stack App:
├── cloudflare-worker-base (foundation)
├── tailwind-v4-shadcn (UI)
├── cloudflare-d1 (database)
├── clerk-auth (authentication)
└── openai-api (AI features)

AI Chat App:
├── cloudflare-worker-base (foundation)
├── ai-sdk-core (AI framework)
├── ai-sdk-ui (UI components)
├── cloudflare-kv (session storage)
└── google-gemini-api (AI provider)

Content Platform:
├── cloudflare-worker-base (foundation)
├── cloudflare-r2 (file storage)
├── cloudflare-images (image optimization)
├── tinacms (CMS)
└── cloudflare-d1 (metadata)
```

---

## Common Pitfalls to Avoid

### For AI Agents Using This Repository

**❌ Don't**:
- Assume skill names based on guessing (always ls skills/ first)
- Use outdated package versions (check "Package Versions" sections)
- Skip "Common Errors Prevented" sections (contains critical fixes)
- Mix incompatible patterns (e.g., Cloudflare Pages + Workers)
- Ignore YAML frontmatter (it's required metadata)

**✅ Do**:
- List available skills before recommending
- Read entire SKILL.md before extracting templates
- Reference specific error prevention notes
- Combine skills following integration tips
- Check metadata.last_verified for currency

### Common Misunderstandings

**Myth**: "Skills are just documentation"
**Reality**: Skills are executable knowledge packages with working code templates

**Myth**: "Use the most recent skill for everything"
**Reality**: Use the most specific skill for the task (atomic skills principle)

**Myth**: "Skills replace official docs"
**Reality**: Skills complement official docs with production-tested patterns

**Myth**: "Templates are examples, not starter code"
**Reality**: Templates are copy-paste-ready production code

---

## Full Skills Inventory

### All 59 Available Skills (Organized by Domain)

**Cloudflare Platform** (20):
- cloudflare-worker-base
- cloudflare-d1
- cloudflare-r2
- cloudflare-kv
- cloudflare-workers-ai
- cloudflare-vectorize
- cloudflare-queues
- cloudflare-workflows
- cloudflare-durable-objects
- cloudflare-agents
- cloudflare-mcp-server
- cloudflare-turnstile
- cloudflare-hyperdrive
- cloudflare-images
- cloudflare-browser-rendering

**AI & Machine Learning** (10):
- ai-sdk-core
- ai-sdk-ui
- openai-api
- openai-agents
- openai-assistants
- openai-responses
- openai-apps-mcp
- google-gemini-api
- google-gemini-embeddings
- google-gemini-file-search
- claude-api
- claude-agent-sdk
- thesys-generative-ui
- elevenlabs-agents

**Frontend & UI** (9):
- tailwind-v4-shadcn
- react-hook-form-zod
- tanstack-query
- tanstack-router
- tanstack-start
- tanstack-table
- zustand-state-management
- nextjs
- hono-routing
- auto-animate

**Auth & Security** (3):
- clerk-auth
- better-auth

**Content Management** (2):
- tinacms
- sveltia-cms

**Database & Storage** (5):
- drizzle-orm-d1
- neon-vercel-postgres
- vercel-kv
- vercel-blob

**Tooling & Development** (6):
- typescript-mcp
- fastmcp
- project-planning
- project-session-management
- gemini-cli
- claude-code-bash-patterns

**Specialized** (4):
- wordpress-plugin-core
- github-project-automation
- open-source-contributions
- skill-review

**Archived** (13):
- Preserved in `archive/low-priority-skills` branch
- Can be restored via git if needed

---

## Metadata Understanding

### What the Metadata Tells You

Skills often include metadata section in SKILL.md:

```yaml
metadata:
  category: cloudflare-platform
  subcategory: storage
  package_manager: npm
  primary_packages:
    - name: wrangler
      version: ^4.20.0
  last_verified: 2025-10-29
  production_tested: true
  token_savings: 67%
  errors_prevented: 8
```

**Key Fields**:
- `category` - High-level grouping (cloudflare-platform, ai-ml, frontend, etc.)
- `subcategory` - Specific domain (storage, auth, ui, etc.)
- `primary_packages` - Core dependencies with versions
- `last_verified` - When skill was last tested
- `production_tested` - Deployed to real projects
- `token_savings` - Measured efficiency gain
- `errors_prevented` - Count of documented issues avoided

**How to Use**:
- Check `last_verified` for currency (quarterly updates)
- Prioritize `production_tested: true` skills
- Use `primary_packages` for version reference
- Expect high quality if `errors_prevented` > 5

---

## Advanced Usage

### Creating Knowledge Graphs

When user has complex multi-technology request:

```
1. Map request to skill categories:
   "Build AI chatbot with auth and database"
   ↓
   - Foundation: cloudflare-worker-base
   - AI: ai-sdk-core, openai-api
   - Auth: clerk-auth
   - Database: cloudflare-d1

2. Build dependency graph:
   cloudflare-worker-base (base)
   ├── clerk-auth (middleware)
   ├── cloudflare-d1 (storage)
   └── ai-sdk-core (features)
       └── openai-api (provider)

3. Read skills in order:
   1. cloudflare-worker-base (foundation)
   2. cloudflare-d1 (database setup)
   3. clerk-auth (auth layer)
   4. ai-sdk-core (AI framework)
   5. openai-api (AI provider)

4. Merge patterns sequentially:
   - Each skill builds on previous
   - Check for conflicts at each step
   - Apply all "known errors" preventions
```

### Extracting Reusable Patterns

Skills contain reusable patterns beyond templates:

**Configuration Patterns**:
- wrangler.jsonc structure (from cloudflare-worker-base)
- vite.config.ts setup (from cloudflare-worker-base)
- Tailwind theme structure (from tailwind-v4-shadcn)

**Code Patterns**:
- Middleware setup (from clerk-auth)
- Error handling (from various skills)
- Streaming responses (from ai-sdk-core)

**Architectural Patterns**:
- Monorepo structure (from various skills)
- API route organization (from hono-routing)
- Database schema design (from cloudflare-d1)

### Keeping Skills Current

**If you can run bash**:

```bash
# Check if skills are current
/home/jez/Documents/claude-skills/scripts/check-all-versions.sh

# Output: VERSIONS_REPORT.md with outdated packages
```

**If you can't run bash**:
- Check `metadata.last_verified` in SKILL.md
- Skills verified within 3 months are current
- Flag skills with `last_verified` > 6 months old

---

## Getting Help

### When You're Stuck

**Can't find the right skill?**
```bash
# List all skills
ls /home/jez/Documents/claude-skills/skills/

# Search skill names
ls /home/jez/Documents/claude-skills/skills/ | grep -i "keyword"

# Read README.md for overview
cat /home/jez/Documents/claude-skills/README.md
```

**Skill seems outdated?**
- Check `metadata.last_verified` date
- Look for version numbers in SKILL.md
- Flag to user if > 6 months old

**Skills conflict?**
- Check CLAUDE.md for global preferences
- Prioritize more specific skill
- Consult user for architectural decision

**Need more context?**
- Read CLAUDE.md for project standards
- Check planning/claude-code-skill-standards.md
- Review ONE_PAGE_CHECKLIST.md

### Resources

**Documentation**:
- README.md - Repository overview
- CLAUDE.md - Project context
- CONTRIBUTING.md - How to contribute
- ONE_PAGE_CHECKLIST.md - Quality standards

**External**:
- Official Skills: https://github.com/anthropics/skills
- Skills Spec: https://github.com/anthropics/skills/blob/main/agent_skills_spec.md
- Claude Code Docs: https://docs.claude.com/en/docs/claude-code/skills

**Contact**:
- Issues: https://github.com/jezweb/claude-skills/issues
- Email: jeremy@jezweb.net
- Web: https://jezweb.com.au

---

## Success Checklist

### For AI Agents Using This Guide

After reading this guide, you should be able to:

- [ ] Locate skills directory (`/home/jez/Documents/claude-skills/skills/`)
- [ ] List available skills (`ls skills/`)
- [ ] Read a skill's SKILL.md file
- [ ] Extract templates from skills/[name]/templates/
- [ ] Identify when to use a specific skill
- [ ] Understand YAML frontmatter structure
- [ ] Recognize quality markers (versions, sources, metrics)
- [ ] Combine multiple skills for complex requests
- [ ] Follow "Common Errors Prevented" sections
- [ ] Navigate repository structure (README, CLAUDE, etc.)
- [ ] Use current package versions
- [ ] Apply production-tested patterns
- [ ] Reference global context from CLAUDE.md
- [ ] Understand atomic skills philosophy

**If you can do all of the above, you're ready to effectively use Claude Code skills!**

---

## Appendix: Quick Reference Cards

### Skill Selection Decision Tree

```
User request received
↓
Does it involve Cloudflare?
├─ Yes → Check cloudflare-* skills
└─ No → Continue

Does it involve AI?
├─ Yes → Check ai-*, openai-*, google-gemini-*, claude-* skills
└─ No → Continue

Does it involve UI?
├─ Yes → Check tailwind-v4-shadcn, react-*, tanstack-* skills
└─ No → Continue

Does it involve Auth?
├─ Yes → Check clerk-auth, better-auth skills
└─ No → Continue

Does it involve Database?
├─ Yes → Check cloudflare-d1, drizzle-orm-d1, neon-*, vercel-* skills
└─ No → Continue

Does it involve Project Planning?
├─ Yes → Check project-planning skill
└─ No → Search skills/ directory

Multiple categories matched?
└─ Use all relevant skills (they're composable)
```

### File Location Quick Reference

```
# Core Documentation
/home/jez/Documents/claude-skills/README.md
/home/jez/Documents/claude-skills/CLAUDE.md
/home/jez/Documents/claude-skills/CONTRIBUTING.md
/home/jez/Documents/claude-skills/ONE_PAGE_CHECKLIST.md

# Extended Docs (in docs/)
/home/jez/Documents/claude-skills/docs/GEMINI_GUIDE.md (this file)
/home/jez/Documents/claude-skills/docs/SKILLS_CATALOG.md
/home/jez/Documents/claude-skills/docs/MARKETPLACE.md

# Skills
/home/jez/Documents/claude-skills/skills/[skill-name]/SKILL.md
/home/jez/Documents/claude-skills/skills/[skill-name]/README.md
/home/jez/Documents/claude-skills/skills/[skill-name]/templates/

# Standards
/home/jez/Documents/claude-skills/planning/claude-code-skill-standards.md
/home/jez/Documents/claude-skills/planning/STANDARDS_COMPARISON.md
/home/jez/Documents/claude-skills/planning/research-protocol.md

# Scripts
/home/jez/Documents/claude-skills/scripts/check-all-versions.sh
/home/jez/Documents/claude-skills/scripts/install-skill.sh
```

### Common Commands

```bash
# Navigation
ls /home/jez/Documents/claude-skills/skills/
cat /home/jez/Documents/claude-skills/skills/[name]/SKILL.md

# Search
ls /home/jez/Documents/claude-skills/skills/ | grep -i "keyword"

# Copy templates
cp -r /home/jez/Documents/claude-skills/skills/[name]/templates/* ./

# Version checking
/home/jez/Documents/claude-skills/scripts/check-all-versions.sh [skill-name]
```

---

**End of Guide**

**Version**: 1.0
**Last Updated**: 2025-11-20
**Maintainer**: Jeremy Dawes | jeremy@jezweb.net
**Repository**: https://github.com/jezweb/claude-skills
