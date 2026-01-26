# Claude Skills Marketplace

Welcome to the **claude-skills** marketplace - a curated collection of 62 production-ready skills for Claude Code CLI, organized into 7 plugins.

## Quick Start

### Step 1: Add the Marketplace

```bash
/plugin marketplace add https://github.com/jezweb/claude-skills
```

### Step 2: Install Plugins

Skills are grouped into logical plugins. Install the ones you need:

```bash
# Install all Cloudflare skills (22 skills)
/plugin install cloudflare-skills@claude-skills

# Install AI/LLM skills (15 skills)
/plugin install ai-skills@claude-skills

# Install frontend/UI skills (7 skills)
/plugin install frontend-skills@claude-skills

# Install all plugins at once
/plugin install cloudflare-skills@claude-skills ai-skills@claude-skills frontend-skills@claude-skills auth-skills@claude-skills cms-skills@claude-skills database-skills@claude-skills tooling-skills@claude-skills
```

### Step 3: Use the Skills

Once installed, Claude Code automatically discovers and uses skills when relevant:

```
User: "Set up a new Cloudflare Worker project with Hono"
Claude: [Automatically uses cloudflare-worker-base skill]

User: "Add Tailwind v4 with shadcn/ui to my React project"
Claude: [Automatically uses tailwind-v4-shadcn skill]
```

### Alternative: Manual Installation

For development or if you prefer symlinks:

```bash
git clone https://github.com/jezweb/claude-skills.git
cd claude-skills

# Install single skill
./scripts/install-skill.sh cloudflare-worker-base

# Install all skills
./scripts/install-all.sh
```

---

## Available Plugins (7)

### cloudflare-skills (22 skills)

Core infrastructure and services for edge computing:

| Skill | Description |
|-------|-------------|
| `cloudflare-worker-base` | Production Workers setup with Hono, Vite, Static Assets |
| `cloudflare-d1` | SQLite database with migrations and schemas |
| `cloudflare-r2` | Object storage (S3-compatible) |
| `cloudflare-kv` | Key-value storage for caching |
| `cloudflare-workers-ai` | LLM inference and embeddings |
| `cloudflare-vectorize` | Vector search and embeddings storage |
| `cloudflare-queues` | Async message processing |
| `cloudflare-workflows` | Multi-step process orchestration |
| `cloudflare-durable-objects` | Stateful coordination and WebSockets |
| `cloudflare-agents` | AI agents on the edge |
| `cloudflare-mcp-server` | Deploy MCP servers on Workers |
| `cloudflare-nextjs` | Next.js on Cloudflare Pages |
| `cloudflare-cron-triggers` | Scheduled tasks |
| `cloudflare-email-routing` | Handle incoming emails |
| `cloudflare-hyperdrive` | Accelerated Postgres connections |
| `cloudflare-images` | Image optimization and delivery |
| `cloudflare-browser-rendering` | Headless browser automation |
| `cloudflare-turnstile` | CAPTCHA-free bot protection |
| `cloudflare-zero-trust-access` | Secure authentication |
| `cloudflare-full-stack-scaffold` | Complete full-stack template |
| `cloudflare-full-stack-integration` | Integrate multiple CF services |
| `cloudflare-sandbox` | Testing and development environment |

### ai-skills (15 skills)

LLM integrations, agents, and AI frameworks:

| Skill | Description |
|-------|-------------|
| `ai-sdk-core` | Vercel AI SDK for unified LLM integration |
| `ai-sdk-ui` | AI SDK UI for chat interfaces |
| `openai-api` | OpenAI GPT models and embeddings |
| `openai-agents` | OpenAI Agents SDK with realtime voice |
| `openai-assistants` | Stateful AI assistants |
| `openai-responses` | Conversational AI applications |
| `google-gemini-api` | Google Gemini multimodal models |
| `google-gemini-embeddings` | Gemini embeddings for search |
| `google-gemini-file-search` | Managed RAG with File Search API |
| `claude-api` | Anthropic Claude API integration |
| `claude-agent-sdk` | Claude autonomous agents |
| `thesys-generative-ui` | LLM-powered dynamic UI |
| `elevenlabs-agents` | Voice AI applications |
| `better-chatbot` | Production chatbot patterns |
| `better-chatbot-patterns` | Advanced chatbot architectures |

### frontend-skills (7 skills)

React, Next.js, and modern UI components:

| Skill | Description |
|-------|-------------|
| `tailwind-v4-shadcn` | Tailwind v4 + shadcn/ui setup (gold standard) |
| `react-hook-form-zod` | Forms with validation |
| `tanstack-query` | Data fetching and caching |
| `zustand-state-management` | Lightweight state management |
| `nextjs` | Next.js App Router development |
| `hono-routing` | Hono for Workers and edge |
| `firecrawl-scraper` | Web scraping API |

### auth-skills (2 skills)

User management and auth solutions:

| Skill | Description |
|-------|-------------|
| `clerk-auth` | Clerk user management |
| `better-auth` | Better Auth library |

### cms-skills (3 skills)

Git-based and WordPress CMS:

| Skill | Description |
|-------|-------------|
| `tinacms` | TinaCMS Git-backed CMS |
| `sveltia-cms` | Sveltia CMS for Git |
| `wordpress-plugin-core` | WordPress plugin development |

### database-skills (4 skills)

ORMs and serverless databases:

| Skill | Description |
|-------|-------------|
| `drizzle-orm-d1` | Drizzle ORM with D1 |
| `neon-vercel-postgres` | Neon Postgres with Vercel |
| `vercel-kv` | Vercel KV Redis storage |
| `vercel-blob` | Vercel Blob file storage |

### tooling-skills (9 skills)

Development tools and workflow automation:

| Skill | Description |
|-------|-------------|
| `project-workflow` | Complete project lifecycle with 7 slash commands |
| `project-planning` | Generate planning docs |
| `project-session-management` | Session handoff protocol |
| `gemini-cli` | Use Gemini CLI for second opinions and code review |
| `typescript-mcp` | Build MCP servers with TypeScript |
| `fastmcp` | FastMCP Python framework |
| `firecrawl-scraper` | Web scraping API integration |
| `hugo` | Hugo static site generator |
| `github-project-automation` | Automate GitHub Projects |
| `open-source-contributions` | Open-source workflow best practices |

---

## Benefits

### For Users

- ✅ **One-command installation**: Install entire skill categories at once
- ✅ **Automatic updates**: Keep skills current with `/plugin update`
- ✅ **Auto-discovery**: Claude automatically uses relevant skills
- ✅ **Team deployment**: Share via `.claude/settings.json`

### For Projects

- ✅ **60-70% token savings** vs manual implementation
- ✅ **395+ errors prevented** across all skills
- ✅ **Production-tested** patterns and templates
- ✅ **Current packages** (verified quarterly)

---

## Managing Plugins

### Update Plugins

```bash
# Update single plugin
/plugin update cloudflare-skills@claude-skills

# Update all plugins from marketplace
/plugin update-all@claude-skills
```

### List Installed Plugins

```bash
/plugin list
```

### Remove Plugins

```bash
/plugin uninstall cloudflare-skills@claude-skills
```

---

## Team Deployment

Add to `.claude/settings.json` for automatic marketplace availability:

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "jezweb-skills",
      "url": "https://github.com/jezweb/claude-skills"
    }
  ]
}
```

Team members will automatically have access to the marketplace.

---

## Alternative: Direct Installation

If you prefer manual installation or want to contribute:

```bash
# Clone repository
git clone https://github.com/jezweb/claude-skills.git
cd claude-skills

# Install single skill
./scripts/install-skill.sh cloudflare-worker-base

# Install all skills
./scripts/install-all.sh
```

See [README.md](README.md) for development workflow.

---

## Troubleshooting

### Skills not triggering automatically

Skills auto-trigger based on keywords in their description. If a skill isn't triggering:

1. Try explicitly asking: "Use the tailwind-v4-shadcn skill to..."
2. Restart Claude Code after installing new plugins
3. Verify the plugin is installed: `/plugin list`

### Plugin not found

Make sure you've added the marketplace first:
```bash
/plugin marketplace add https://github.com/jezweb/claude-skills
```

Then install the plugin (not individual skills):
```bash
/plugin install frontend-skills@claude-skills
```

---

## Support

**Issues**: https://github.com/jezweb/claude-skills/issues
**Email**: jeremy@jezweb.net
**Documentation**: See individual skill directories for detailed guides

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick process**:
1. Fork repository
2. Create new skill in `skills/` directory
3. Run `./scripts/generate-plugin-manifests.sh`
4. Submit pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Last Updated**: 2025-12-12
**Marketplace Version**: 2.0.0
**Plugins**: 7 (containing 62 skills)
**Maintainer**: Jeremy Dawes | Jezweb
