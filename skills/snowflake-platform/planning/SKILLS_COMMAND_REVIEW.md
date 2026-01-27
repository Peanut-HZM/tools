# Skills Command Review

**Date**: 2026-01-10
**Purpose**: Determine which skills should have entry commands and/or `user-invocable: true`

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Already has `user-invocable: true` | 10 | Done |
| Should add `user-invocable: true` | 25 | Phase 2 |
| Knowledge-only (no commands needed) | 28 | None |
| Has commands already | 1 | Done |
| Needs init/scaffold command | 15 | Phase 3 |
| Needs setup/configure command | 12 | Phase 3 |
| **Total Skills** | **73** | |

---

## ✅ Already Has `user-invocable: true` (10 skills)

These were updated in this session:

1. `cloudflare-worker-base` - Also has `commands/init.md` prototype
2. `tailwind-v4-shadcn`
3. `drizzle-orm-d1`
4. `cloudflare-d1`
5. `clerk-auth`
6. `hono-routing`
7. `ai-sdk-core`
8. `react-hook-form-zod`
9. `typescript-mcp`
10. `playwright-local`

---

## 📚 Knowledge-Only Skills (28 skills)

These are primarily reference material and corrections. Auto-discovery is sufficient.

**No changes needed:**

| Skill | Reason |
|-------|--------|
| `ai-sdk-ui` | UI patterns reference |
| `claude-api` | API reference |
| `claude-agent-sdk` | SDK reference |
| `openai-api` | API reference |
| `openai-agents` | Agent patterns reference |
| `openai-assistants` | Assistants API reference |
| `openai-responses` | Responses API reference |
| `openai-apps-mcp` | MCP reference |
| `google-gemini-api` | API reference |
| `google-gemini-embeddings` | Embeddings reference |
| `google-gemini-file-search` | File search reference |
| `cloudflare-workers-ai` | AI models reference |
| `cloudflare-vectorize` | Vector DB reference |
| `cloudflare-browser-rendering` | Browser API reference |
| `cloudflare-images` | Images API reference |
| `cloudflare-hyperdrive` | Postgres proxy reference |
| `cloudflare-python-workers` | Python workers reference |
| `hono-routing` | Already invocable, patterns reference |
| `neon-vercel-postgres` | Postgres reference |
| `vercel-blob` | Blob storage reference |
| `vercel-kv` | KV reference |
| `firecrawl-scraper` | Scraping reference |
| `mcp-cli-scripts` | CLI scripts reference |
| `sub-agent-patterns` | Agent patterns reference |
| `open-source-contributions` | Contribution guide |
| `google-spaces-updates` | Webhook reference |
| `auto-animate` | Animation library reference |
| `motion` | Framer Motion reference |

---

## 🔧 Should Add `user-invocable: true` (25 skills)

These would benefit from manual invocation but don't need full command workflows.

### Priority 1 - Frequently Used (8 skills)

| Skill | Why Invocable |
|-------|---------------|
| `cloudflare-r2` | Common storage setup |
| `cloudflare-kv` | Common KV setup |
| `cloudflare-queues` | Queue setup |
| `cloudflare-workflows` | Workflow setup |
| `cloudflare-durable-objects` | DO setup |
| `better-auth` | Auth setup |
| `tanstack-query` | Data fetching setup |
| `zustand-state-management` | State management setup |

### Priority 2 - Specialized (10 skills)

| Skill | Why Invocable |
|-------|---------------|
| `cloudflare-agents` | Agent development |
| `cloudflare-mcp-server` | MCP server development |
| `cloudflare-turnstile` | Captcha integration |
| `fastmcp` | Python MCP servers |
| `nextjs` | Next.js projects |
| `tanstack-start` | TanStack Start projects |
| `tanstack-router` | Router setup |
| `tanstack-table` | Table setup |
| `azure-auth` | Azure AD auth |
| `mcp-oauth-cloudflare` | OAuth for MCP |

### Priority 3 - Niche (7 skills)

| Skill | Why Invocable |
|-------|---------------|
| `react-native-expo` | Mobile app development |
| `fastapi` | Python API projects |
| `flask` | Python web projects |
| `snowflake-platform` | Snowflake apps |
| `streamlit-snowflake` | Streamlit apps |
| `elevenlabs-agents` | Voice agents |
| `tiptap` | Rich text editor |

---

## 📁 Already Has Commands (1 skill)

| Skill | Commands |
|-------|----------|
| `project-workflow` | wrap-session, continue-session, plan-project, plan-feature, explore-idea, release, workflow |

---

## 🚀 Needs Init/Scaffold Command (15 skills)

These skills would benefit from a `/skill-name/init` command that scaffolds a new project or component.

| Skill | Command | Purpose |
|-------|---------|---------|
| `cloudflare-worker-base` | `init` ✅ | Scaffold Workers project (DONE) |
| `cloudflare-mcp-server` | `init` | Scaffold MCP server |
| `cloudflare-agents` | `init` | Scaffold agent project |
| `cloudflare-durable-objects` | `init` | Scaffold DO class |
| `cloudflare-workflows` | `init` | Scaffold workflow |
| `drizzle-orm-d1` | `init` | Scaffold schema + migrations |
| `fastmcp` | `init` | Scaffold Python MCP server |
| `typescript-mcp` | `init` | Scaffold TS MCP server |
| `nextjs` | `init` | Scaffold Next.js project |
| `tanstack-start` | `init` | Scaffold TanStack Start project |
| `react-native-expo` | `init` | Scaffold Expo app |
| `fastapi` | `init` | Scaffold FastAPI project |
| `flask` | `init` | Scaffold Flask project |
| `snowflake-platform` | `init` | Scaffold Snowflake app |
| `wordpress-plugin-core` | `init` | Scaffold WP plugin |

---

## ⚙️ Needs Setup/Configure Command (12 skills)

These skills would benefit from a `/skill-name/setup` command that adds functionality to an existing project.

| Skill | Command | Purpose |
|-------|---------|---------|
| `tailwind-v4-shadcn` | `setup` | Add Tailwind + shadcn to project |
| `clerk-auth` | `setup` | Add Clerk auth to project |
| `better-auth` | `setup` | Add better-auth to project |
| `azure-auth` | `setup` | Add Azure AD auth |
| `mcp-oauth-cloudflare` | `setup` | Add OAuth to MCP server |
| `tanstack-query` | `setup` | Add TanStack Query |
| `tanstack-table` | `setup` | Add TanStack Table |
| `zustand-state-management` | `setup` | Add Zustand store |
| `cloudflare-turnstile` | `setup` | Add Turnstile captcha |
| `tinacms` | `setup` | Add TinaCMS |
| `sveltia-cms` | `setup` | Add Sveltia CMS |
| `email-gateway` | `setup` | Add email sending |

---

## 📋 Meta/Workflow Skills (5 skills)

These are special skills for skill development or project management.

| Skill | Status | Commands |
|-------|--------|----------|
| `project-workflow` | Has commands | 7 commands |
| `project-planning` | Knowledge only | Could add `plan` command |
| `project-session-management` | Knowledge only | Could merge into project-workflow |
| `skill-creator` | Could be invocable | `init` command for new skills |
| `skill-review` | Could be invocable | `review` command |

---

## Implementation Phases

### Phase 1 (DONE)
- ✅ Add `user-invocable: true` to top 10 skills
- ✅ Create `commands/init.md` prototype for cloudflare-worker-base
- ✅ Document architecture in `docs/SKILLS_COMMANDS_ARCHITECTURE.md`

### Phase 2 (Next)
- Add `user-invocable: true` to Priority 1 skills (8 skills)
- Add `user-invocable: true` to Priority 2 skills (10 skills)
- Total: 18 more skills

### Phase 3 (Future)
- Create `init` commands for scaffolding skills (15 skills)
- Create `setup` commands for integration skills (12 skills)
- Evaluate remaining Priority 3 skills

### Phase 4 (Future)
- Review meta skills (skill-creator, skill-review)
- Consider merging project-session-management into project-workflow
- Add argument passing to commands (e.g., `/skill/init --name myproject`)

---

## Decision Framework

**Add `user-invocable: true` when:**
- Users might want to explicitly invoke the skill
- The skill has a clear "entry point" use case
- The skill scaffolds or sets up something

**Add commands when:**
- The skill has multiple distinct workflows
- Guided step-by-step execution improves UX
- The workflow is complex enough to benefit from automation

**Keep knowledge-only when:**
- The skill is primarily reference/documentation
- Auto-discovery via keywords is sufficient
- There's no clear "start here" workflow
