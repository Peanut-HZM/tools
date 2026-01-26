# Community Knowledge Research: FastMCP

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/fastmcp/SKILL.md
**Packages Researched**: fastmcp>=2.14.2
**Official Repo**: jlowin/fastmcp
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 18 |
| TIER 1 (Official) | 10 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 3 |
| TIER 4 (Low Confidence) | 2 |
| Already in Skill | 6 |
| Recommended to Add | 12 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: FastAPI Integration Requires Lifespan Pass-Through

**Trust Score**: TIER 1 - Official (Maintainer Confirmed)
**Source**: [GitHub Issue #2961](https://github.com/jlowin/fastmcp/issues/2961)
**Date**: 2026-01-20
**Verified**: Yes (Maintainer: "You're absolutely right")
**Impact**: HIGH
**Already in Skill**: Partially (lifespan documented, but FastAPI-specific gotcha missing)

**Description**:
When mounting FastMCP server in FastAPI, two critical gotchas exist:
1. The FastMCP server's lifespan **must** be passed to FastAPI app (same as Starlette requirement)
2. Mounting at `/mcp` actually creates endpoint at `/mcp/mcp` due to path prefix duplication

**Reproduction**:
```python
# ❌ WRONG - Lifespan not passed, mount path doubles
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("server")
app = FastAPI()  # Missing lifespan!
app.mount("/mcp", mcp)  # Creates /mcp/mcp endpoint
```

**Solution/Workaround**:
```python
# ✅ CORRECT
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("server")
app = FastAPI(lifespan=mcp.lifespan)  # CRITICAL: Pass lifespan
app.mount("/", mcp)  # Mount at root to get /mcp endpoint
# OR adjust client config to point to /mcp/mcp
```

**Official Status**:
- [x] Known issue, workaround required
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (partially - Starlette section mentions it)

**Cross-Reference**:
- Related duplicate issues: #2467, #1849, #1176
- Skill section: Error #17 covers lifespan requirement, but not FastAPI-specific mount path issue

---

### Finding 1.2: Task Status Messages Not Forwarded to Client

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2904](https://github.com/jlowin/fastmcp/issues/2904)
**Date**: 2026-01-18
**Verified**: Yes (Root cause identified)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using background tasks (`task=True`), the `statusMessage` field from `ctx.report_progress()` is **not forwarded** to MCP clients during task polling. Progress messages appear in server logs but not in client UI (e.g., VS Code chat).

**Root Cause** (from issue investigation):
- Code references `execution.progress.message` which doesn't exist in pydocket 0.16.6
- `Context.report_progress()` only handles foreground progress via `progressToken`
- For background tasks, it returns early without storing progress anywhere

**Reproduction**:
```python
@mcp.tool(task=True)
async def long_task(context: Context) -> dict:
    for i in range(10):
        # Message appears in logs but NOT in client UI
        await context.report_progress(i + 1, 10, f"Processing {i + 1}/10")
        await asyncio.sleep(1)
    return {"status": "done"}
```

**Solution/Workaround**:
1. Use official MCP SDK (`mcp>=1.10.0` from `modelcontextprotocol/python-sdk`) instead of FastMCP (fully works)
2. Wait for fix in FastMCP (PR #2906 submitted with Docket ExecutionProgress fallback)

**Official Status**:
- [ ] Fixed in version X.Y.Z (PR pending)
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related: #2879 (Background job doesn't produce valid CreateTaskResult)
- Skill section: Background Tasks (v2.14.0+) - should add this limitation

---

### Finding 1.3: Background Tasks Fail with "No Active Context" in FastAPI Mount

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2877](https://github.com/jlowin/fastmcp/issues/2877)
**Date**: 2026-01-17
**Verified**: Yes (ContextVar propagation issue)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Background tasks with `task=True` and `Context` parameter fail with `RuntimeError: No active context found` when FastMCP is mounted in FastAPI/Starlette. This is a ContextVar propagation issue in ASGI apps.

**Reproduction**:
```python
from fastapi import FastAPI
from fastmcp import FastMCP, Context

mcp = FastMCP("server")
app = FastAPI(lifespan=mcp.lifespan)

@mcp.tool(task=True)
async def sample_tool(name: str, ctx: Context) -> dict:
    # Fails with: RuntimeError: No active context found
    await ctx.report_progress(1, 1, "Processing")
    return {"status": "OK"}

app.mount("/", mcp)
```

**Solution/Workaround**:
- Fixed in v2.14.3 via [PR #2844](https://github.com/jlowin/fastmcp/pull/2844)
- Upgrade to fastmcp>=2.14.3

**Official Status**:
- [x] Fixed in version 2.14.3
- [ ] Documented behavior
- [ ] Known issue, workaround required

**Cross-Reference**:
- Related: #2671 (Same issue: 'require a running FastMCP server context')
- Skill section: Should add to Error #17 or create new error for ASGI mounting

---

### Finding 1.4: HTTP Transport Timeout Default Too Aggressive

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v2.14.3](https://github.com/jlowin/fastmcp/releases/tag/v2.14.3), [Issue #2845](https://github.com/jlowin/fastmcp/issues/2845)
**Date**: 2026-01-12
**Verified**: Yes (Fixed in 2.14.3)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
HTTP transport was defaulting to 5-second timeout instead of MCP's 30-second default, causing premature timeouts for operations taking >5 seconds. Tools would fail silently, and clients would hang on 4xx/5xx errors.

**Reproduction**:
```python
# In v2.14.2 and earlier
mcp = FastMCP("server")

@mcp.tool()
async def slow_operation(query: str) -> dict:
    await asyncio.sleep(10)  # Fails after 5 seconds in v2.14.2
    return {"result": "done"}

# Run with HTTP transport
mcp.run(transport="http", port=8000)  # Default timeout was 5s
```

**Solution/Workaround**:
- Upgrade to fastmcp>=2.14.3 (timeout now respects MCP's 30s default)
- Or manually set timeout in v2.14.2: Pass `timeout=30` to client config

**Official Status**:
- [x] Fixed in version 2.14.3
- [ ] Documented behavior
- [ ] Known issue, workaround required

**Cross-Reference**:
- Related: #2803 (Client hanging on HTTP 4xx/5xx errors)
- Skill section: Should add to Error #7 (Transport/Protocol Mismatch)

---

### Finding 1.5: OAuth Token Storage Lost on Server Restart (Memory Backend Default)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1577](https://github.com/jlowin/fastmcp/issues/1577), [Issue #2479](https://github.com/jlowin/fastmcp/issues/2479)
**Date**: 2025-11-25
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Yes (Error #16)

**Description**:
OAuth tokens stored in default memory backend are lost on server restart, forcing users to re-authenticate. This is especially problematic in production with server restarts.

**Solution/Workaround**:
Use persistent storage (DiskStore or RedisStore) with encryption:
```python
from key_value.stores import RedisStore, DiskStore
from key_value.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

# Production: Redis with encryption
storage = FernetEncryptionWrapper(
    key_value=RedisStore(host=os.getenv("REDIS_HOST")),
    fernet=Fernet(os.getenv("STORAGE_ENCRYPTION_KEY"))
)

auth = OAuthProxy(
    client_storage=storage,  # Persistent encrypted storage
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    # ... other config
)
```

**Official Status**:
- [x] Documented behavior (working as designed)
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required

**Cross-Reference**:
- Skill section: Error #16 (Storage Backend Not Configured)
- Related: #2403 (PostgreSQL Storage Backend request)

---

### Finding 1.6: MCP SDK Pinned to <2.x for Compatibility

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v2.14.2](https://github.com/jlowin/fastmcp/releases/tag/v2.14.2)
**Date**: 2024-12-31
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Yes (partially - mentioned in v2.14.2 notes)

**Description**:
FastMCP v2.14.2+ pins MCP SDK to `<2.x` for compatibility. This prevents breaking changes from MCP SDK 2.x affecting FastMCP users.

**Official Status**:
- [x] Documented behavior
- [x] Known compatibility constraint

**Cross-Reference**:
- Skill section: "What's New in v2.14.x" already mentions this

---

### Finding 1.7: v3.0.0 Breaking Changes - Major Architectural Refactor

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v3.0.0b1](https://github.com/jlowin/fastmcp/releases/tag/v3.0.0b1)
**Date**: 2026-01-20
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
FastMCP 3.0.0b1 (beta) introduces **massive breaking changes** with provider-based architecture:
- **Provider Architecture**: All components sourced via providers (FileSystemProvider, SkillsProvider, OpenAPIProvider, ProxyProvider)
- **Transforms**: Component modification middleware (namespace, rename, filter, version)
- **Component Versioning**: `@tool(version="2.0")` with client version selection
- **Session-Scoped State**: `await ctx.set_state()` persists across requests
- **Breaking**: Most v2 APIs remain compatible, but internal refactor is significant

**Key New Features**:
- `--reload` flag for auto-restart during development
- Automatic threadpool dispatch for sync functions
- Tool timeouts
- OpenTelemetry tracing
- Component authorization: `@tool(auth=require_scopes("admin"))`
- ResourcesAsTools and PromptsAsTools transforms

**Migration**:
```python
# Pin to v2 to avoid unexpected upgrades
# In requirements.txt:
fastmcp<3  # Stay on v2.x
# OR opt into beta:
fastmcp>=3.0.0b1
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (beta release)
- [ ] Known issue, workaround required

**Cross-Reference**:
- Skill section: Should add v3.0.0 section with migration guidance
- [Migration guide](https://github.com/jlowin/fastmcp/blob/main/docs/development/upgrade-guide.mdx)

---

### Finding 1.8: Supabase Provider Gains auth_route Parameter

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v2.14.2](https://github.com/jlowin/fastmcp/releases/tag/v2.14.2), [PR #2632](https://github.com/jlowin/fastmcp/pull/2632)
**Date**: 2024-12-31
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Supabase provider now supports custom `auth_route` parameter for flexible authentication routing.

```python
from fastmcp.auth import SupabaseProvider

auth = SupabaseProvider(
    auth_route="/custom-auth",  # New in v2.14.2
    # ... other config
)
```

**Official Status**:
- [x] Fixed in version 2.14.2
- [x] Documented behavior

**Cross-Reference**:
- Skill section: Could add to OAuth & Authentication section

---

### Finding 1.9: OutputSchema $ref Resolution Bug Fixed

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v2.14.2](https://github.com/jlowin/fastmcp/releases/tag/v2.14.2), [Issue #2720](https://github.com/jlowin/fastmcp/issues/2720)
**Date**: 2024-12-31
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Root-level `$ref` in `outputSchema` wasn't being dereferenced, causing MCP spec non-compliance and client compatibility issues.

**Reproduction**:
```python
# Before v2.14.2: $ref not resolved
@mcp.tool()
async def get_data() -> MyModel:
    # outputSchema contained: {"$ref": "#/$defs/MyModel"}
    # Clients couldn't parse schema
    return MyModel(...)
```

**Solution/Workaround**:
- Upgrade to fastmcp>=2.14.2 (auto-dereferences $ref)

**Official Status**:
- [x] Fixed in version 2.14.2
- [ ] Documented behavior

**Cross-Reference**:
- Related: #2814 (Dereference $ref in tool schemas for MCP client compatibility)
- Skill section: Could add to Error #11 (Schema Generation Failures)

---

### Finding 1.10: Python 3.13 Support Added

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v2.14.1](https://github.com/jlowin/fastmcp/releases/tag/v2.14.1)
**Date**: 2024-12-15
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Python 3.13 support officially added in v2.14.1.

**Official Status**:
- [x] Fixed in version 2.14.1
- [x] Documented behavior

**Cross-Reference**:
- Skill section: Could update package versions section

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Type Compatibility - Custom Classes Must Be Dictionaries

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [WebSearch: Firecrawl Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
**Date**: 2025
**Verified**: Code Review Only
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
FastMCP supports all Pydantic-compatible types, but custom classes must be converted to dictionaries for tool returns. This is a common gotcha when returning complex objects.

**Reproduction**:
```python
class MyCustomClass:
    def __init__(self, value: str):
        self.value = value

# ❌ NOT SUPPORTED
@mcp.tool()
async def get_custom() -> MyCustomClass:
    return MyCustomClass("test")  # Serialization error

# ✅ SUPPORTED - Use dict or Pydantic model
@mcp.tool()
async def get_custom() -> dict[str, str]:
    obj = MyCustomClass("test")
    return {"value": obj.value}

# OR use Pydantic
from pydantic import BaseModel

class MyModel(BaseModel):
    value: str

@mcp.tool()
async def get_model() -> MyModel:
    return MyModel(value="test")  # Works!
```

**Community Validation**:
- Source: Reputable tutorial site (Firecrawl)
- Multiple tutorials mention this pattern
- Aligns with Pydantic best practices

**Cross-Reference**:
- Related to Error #12 (JSON Serialization)
- Should add as Error #29 or tip

---

### Finding 2.2: Tool Return Value Format - Wrap Top-Level Lists

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [WebSearch: Firecrawl Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
**Date**: 2025
**Verified**: Code Review Only
**Impact**: LOW
**Already in Skill**: No

**Description**:
If a tool returns a top-level list, wrap it in a dict to keep client handling simple and consistent.

**Reproduction**:
```python
# ❌ LESS IDEAL - Top-level list
@mcp.tool()
async def get_items() -> list[str]:
    return ["item1", "item2", "item3"]

# ✅ BETTER - Wrapped in dict
@mcp.tool()
async def get_items() -> dict[str, list[str]]:
    return {"items": ["item1", "item2", "item3"]}
```

**Community Validation**:
- Recommendation from tutorial
- Best practice for consistent client handling
- Not a hard error, but improves UX

**Cross-Reference**:
- Could add to Best Practices section

---

### Finding 2.3: Sampling Not Supported in Multi-Server Client Scenarios

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #699](https://github.com/jlowin/fastmcp/issues/699), WebSearch results
**Date**: 2025
**Verified**: GitHub issue confirms
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
`ctx.sample()` works when client connects to a single server but fails with "Sampling not supported" error when multiple servers are configured. Tools without sampling work fine.

**Reproduction**:
```python
# Works with single server, fails with multi-server setup
@mcp.tool()
async def analyze(text: str, context: Context) -> str:
    response = await context.sample(  # Fails if client has multiple servers
        messages=[{"role": "user", "content": f"Analyze: {text}"}]
    )
    return response["content"]
```

**Community Validation**:
- GitHub issue confirms behavior
- Multiple users report same issue
- Limitation of multi-server architecture

**Cross-Reference**:
- Should add to Sampling section (v2.14.1+)

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Pin Dependency to v2 to Avoid v3 Breaking Changes

**Trust Score**: TIER 3 - Community Consensus
**Source**: [WebSearch: Multiple tutorials](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
**Date**: 2025
**Verified**: Cross-Referenced with v3.0.0b1 release
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Community recommends pinning to `fastmcp<3` to avoid unexpected breaking changes from v3.0.0 when it's released.

```python
# requirements.txt
fastmcp<3  # Stay on v2.x
```

**Consensus Evidence**:
- Multiple tutorials recommend pinning
- v3.0.0b1 confirms significant breaking changes
- Standard practice for major version upgrades

**Recommendation**: Add to installation/setup section

---

### Finding 3.2: Restart Clients After Configuration Changes

**Trust Score**: TIER 3 - Community Consensus
**Source**: WebSearch tutorials
**Date**: 2025
**Verified**: Cross-Referenced Only
**Impact**: LOW
**Already in Skill**: No

**Description**:
MCP clients (Claude Desktop, VS Code) need to be restarted after changing server configuration for changes to take effect.

**Recommendation**: Add to troubleshooting tips

---

### Finding 3.3: Documentation Confusion Between FastMCP and Native MCP SDK

**Trust Score**: TIER 3 - Community Consensus
**Source**: WebSearch tutorials
**Date**: 2025
**Verified**: Multiple sources mention
**Impact**: LOW
**Already in Skill**: No

**Description**:
Users report confusion when comparing FastMCP documentation with official Anthropic MCP SDK capabilities. FastMCP is a higher-level framework that doesn't expose all low-level SDK features.

**Recommendation**: Add note clarifying FastMCP vs native SDK trade-offs

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: PyInstaller Compatibility Issues with diskcache

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #2514](https://github.com/jlowin/fastmcp/issues/2514)
**Date**: 2025-12-02
**Verified**: No (single source, specific use case)
**Impact**: LOW

**Why Flagged**:
- [x] Single source only
- [x] May be version-specific (old)
- [ ] Cannot reproduce
- [ ] Contradicts official docs

**Description**:
FastMCP frozen with PyInstaller fails due to missing diskcache dependency detection. Very niche use case.

**Recommendation**: Monitor only. Most users don't package MCP servers with PyInstaller.

---

### Finding 4.2: Visual Studio Code OAuth Authorization Issues

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #1868](https://github.com/jlowin/fastmcp/issues/1868)
**Date**: 2025-09-19
**Verified**: Closed (likely client-specific issue)
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [x] Issue closed (may be resolved)

**Description**:
User reported VS Code couldn't authorize with FastMCP OAuth. Issue closed, likely client-side problem or fixed.

**Recommendation**: Do not add. Insufficient evidence.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| OAuth tokens lost on restart (memory storage) | Error #16 | Fully covered |
| Lifespan not passed to ASGI app | Error #17 | Fully covered |
| MCP SDK pinned to <2.x | v2.14.2 notes | Fully documented |
| Module-level server export for Cloud | Error #1, Cloud Deployment | Fully covered |
| Async/await confusion | Error #2 | Fully covered |
| Context injection requires type hint | Error #3 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 FastAPI mount path doubling | Known Issues | Add as Error #27 |
| 1.2 Task status messages not forwarded | Background Tasks section | Add limitation note + workaround |
| 1.3 Background tasks context failure in ASGI | Error section | Add as Error #28 (fixed in 2.14.3) |
| 1.4 HTTP transport timeout too aggressive | Error #7 or new | Document 5s→30s fix in v2.14.3 |
| 1.7 v3.0.0 breaking changes | What's New section | Add v3.0.0b1 section with migration guide |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.8 Supabase auth_route parameter | OAuth section | Minor feature, low priority |
| 1.9 OutputSchema $ref resolution | Error #11 | Add note about fix in v2.14.2 |
| 1.10 Python 3.13 support | Package Versions | Update Python version requirements |
| 2.1 Custom classes must be dicts | Error section or Tips | Add as Error #29 or best practice |
| 2.3 Sampling not supported multi-server | Sampling section | Add known limitation |

### Priority 3: Monitor (TIER 3-4, Needs Verification or Low Impact)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 Pin to v2 to avoid v3 changes | Community advice | Add to installation section |
| 3.2 Restart clients after config | Common knowledge | Add to troubleshooting |
| 4.1 PyInstaller compatibility | Niche use case | Monitor only |
| 4.2 VS Code OAuth issues | Closed issue, may be resolved | Ignore |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| All issues (bug label) | 2961+ total | 15 reviewed |
| "fastmcp lifespan" | 7 | 3 |
| "fastmcp oauth" | 10 | 4 |
| Recent releases | 10 | 3 (v2.14.3, v2.14.2, v3.0.0b1) |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "fastmcp site:stackoverflow.com" | 0 | N/A (too new) |

### Other Sources

| Source | Notes |
|--------|-------|
| [Firecrawl Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python) | 3 relevant tips |
| [MCPcat Guide](https://mcpcat.io/guides/building-mcp-server-python-fastmcp/) | 2 relevant patterns |
| Official docs (gofastmcp.com) | Error handling patterns |

---

## Methodology Notes

**Tools Used**:
- `gh issue list` and `gh issue view` for GitHub discovery
- `gh release list` and `gh release view` for changelog analysis
- `WebSearch` for community tutorials and Stack Overflow
- Manual review of 15+ GitHub issues

**Limitations**:
- Stack Overflow has no FastMCP content (package too new, released mid-2024)
- v3.0.0 is in beta - breaking changes may evolve before GA
- Some issues may be client-specific (VS Code, Claude Desktop) rather than FastMCP bugs

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify v3.0.0b1 migration guide accuracy against actual breaking changes when v3.0.0 GA is released.

**For api-method-checker**: Verify that `ctx.report_progress()` fix in PR #2906 is merged and works as expected.

**For code-example-validator**: Validate FastAPI mount examples before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### Error #27: FastAPI Mount Path Doubling

```markdown
### Error 27: FastAPI Mount Path Doubling

**Error**: Client can't connect to `/mcp` endpoint, gets 404
**Source**: [GitHub Issue #2961](https://github.com/jlowin/fastmcp/issues/2961)
**Cause**: Mounting FastMCP at `/mcp` creates endpoint at `/mcp/mcp` due to path prefix
**Solution**: Mount at root `/` or adjust client config

```python
# ❌ WRONG - Creates /mcp/mcp endpoint
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("server")
app = FastAPI(lifespan=mcp.lifespan)
app.mount("/mcp", mcp)  # Endpoint becomes /mcp/mcp

# ✅ CORRECT - Mount at root
app.mount("/", mcp)  # Endpoint is /mcp

# ✅ OR adjust client config
# In claude_desktop_config.json:
{"url": "http://localhost:8000/mcp/mcp", "transport": "http"}
```

**Critical**: Must also pass `lifespan=mcp.lifespan` to FastAPI (see Error #17).
```

#### Background Tasks Section Update

```markdown
**Known Limitation (v2.14.x)**:
- `statusMessage` from `ctx.report_progress()` is **not forwarded** to clients during background task polling
- Progress messages appear in server logs but not in client UI
- **Workaround**: Use official MCP SDK (`mcp>=1.10.0`) instead of FastMCP for now
- **Status**: Fix pending in [PR #2906](https://github.com/jlowin/fastmcp/pull/2906)
- **Reference**: [GitHub Issue #2904](https://github.com/jlowin/fastmcp/issues/2904)
```

#### Error #28: Background Tasks Context Failure in ASGI

```markdown
### Error 28: Background Tasks Fail with "No Active Context" (ASGI Mount)

**Error**: `RuntimeError: No active context found`
**Source**: [GitHub Issue #2877](https://github.com/jlowin/fastmcp/issues/2877)
**Cause**: ContextVar propagation issue when FastMCP mounted in FastAPI/Starlette with background tasks
**Solution**: Upgrade to fastmcp>=2.14.3

```python
# In v2.14.2 and earlier - FAILS
from fastapi import FastAPI
from fastmcp import FastMCP, Context

mcp = FastMCP("server")
app = FastAPI(lifespan=mcp.lifespan)

@mcp.tool(task=True)
async def sample(name: str, ctx: Context) -> dict:
    # RuntimeError: No active context found
    await ctx.report_progress(1, 1, "Processing")
    return {"status": "OK"}

app.mount("/", mcp)

# ✅ FIXED in v2.14.3
pip install fastmcp>=2.14.3
```

**Note**: Related to Error #17 (Lifespan Not Passed to ASGI App).
```

### Adding v3.0.0 Section

```markdown
## What's New in v3.0.0 (Beta - January 2026)

**⚠️ MAJOR BREAKING CHANGES** - FastMCP 3.0 is a complete architectural refactor.

### Provider Architecture

All components now sourced via **Providers**:
- `FileSystemProvider` - Discover decorated functions from directories with hot-reload
- `SkillsProvider` - Expose agent skill files as MCP resources
- `OpenAPIProvider` - Auto-generate from OpenAPI specs
- `ProxyProvider` - Proxy to remote MCP servers

```python
from fastmcp import FastMCP
from fastmcp.providers import FileSystemProvider

mcp = FastMCP("server")
mcp.add_provider(FileSystemProvider(path="./tools", reload=True))
```

### Transforms (Component Middleware)

Modify components without changing source code:
- Namespace, rename, filter by version
- `ResourcesAsTools` - Expose resources as tools
- `PromptsAsTools` - Expose prompts as tools

```python
from fastmcp.transforms import Namespace, VersionFilter

mcp.add_transform(Namespace(prefix="api"))
mcp.add_transform(VersionFilter(min_version="2.0"))
```

### Component Versioning

```python
@mcp.tool(version="2.0")
async def fetch_data(query: str) -> dict:
    # Clients see highest version by default
    # Can request specific version
    return {"data": [...]}
```

### Session-Scoped State

```python
@mcp.tool()
async def set_preference(key: str, value: str, ctx: Context) -> dict:
    await ctx.set_state(key, value)  # Persists across session
    return {"saved": True}

@mcp.tool()
async def get_preference(key: str, ctx: Context) -> dict:
    value = await ctx.get_state(key, default=None)
    return {"value": value}
```

### Other Features

- `--reload` flag for auto-restart during development
- Automatic threadpool dispatch for sync functions
- Tool timeouts
- OpenTelemetry tracing
- Component authorization: `@tool(auth=require_scopes("admin"))`

### Migration Guide

**Pin to v2 if not ready**:
```
# requirements.txt
fastmcp<3
```

**For most servers**, updating the import is all you need:
```python
# v2.x and v3.0 compatible
from fastmcp import FastMCP

mcp = FastMCP("server")
# ... rest of code works the same
```

**See**: [Official Migration Guide](https://github.com/jlowin/fastmcp/blob/main/docs/development/upgrade-guide.mdx)
```

---

**Research Completed**: 2026-01-21 11:45 AM
**Next Research Due**: After v3.0.0 GA release or v2.15.0 (whichever comes first)
