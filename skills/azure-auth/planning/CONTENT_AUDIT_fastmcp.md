# Content Audit: fastmcp

**Date**: 2026-01-09
**Overall Score**: 8.5/10
**Status**: PASS

---

## Summary

| Category | Score | Status | Key Finding |
|----------|-------|--------|-------------|
| API Coverage | 8.5/10 | ✅ | Comprehensive, missing `Depends()`, `@mcp.custom_route`, Context logging methods |
| Pattern Validation | 8.5/10 | ✅ | Image import path needs `.types` submodule correction |
| Error Documentation | 7/10 | ⚠️ | Missing `mask_error_details` security note, `*args/**kwargs` limitation |
| Ecosystem Accuracy | 10/10 | ✅ | Perfect - correct registry, versions, dependencies |

**Score Legend**:
- ✅ 8-10: Accurate, minor updates only
- ⚠️ 5-7: Needs attention, some gaps
- ❌ 1-4: Critical issues, major updates needed

---

## Critical Issues

> No critical issues found. The skill is production-ready.

---

## Recommended Updates

### High Priority

- [ ] Fix Error 28 Image import path: `from fastmcp.utilities.types import Image, Audio, File` (not just `fastmcp.utilities`)
- [ ] Add `mask_error_details=True` security note to error handling section
- [ ] Document `*args/**kwargs` limitation (functions with these are not supported as tools)

### Medium Priority

- [ ] Add `Depends()` parameter hiding pattern with examples (v2.14.0+)
- [ ] Add `@mcp.custom_route` decorator documentation for HTTP endpoints
- [ ] Document Context logging methods (`ctx.debug()`, `ctx.info()`, `ctx.warning()`)
- [ ] Add `ToolResult` import path: `from fastmcp.tools.tool import ToolResult`
- [ ] Add `ToolError` import path: `from fastmcp.exceptions import ToolError`

### Low Priority

- [ ] Add `result_type` parameter to sampling section (v2.14.1+)
- [ ] Expand `@mcp.prompt` decorator parameters documentation
- [ ] Document `Audio` and `File` media helper types alongside `Image`
- [ ] Add `tool_names` parameter on `mount()` (v2.14.1+)

---

## Agent Reports

### 1. API Coverage Agent

**Score**: 8.5/10

#### Missing APIs (documented but not in skill)
| API/Method | Description | Priority |
|------------|-------------|----------|
| `@mcp.custom_route` | HTTP endpoint registration alongside MCP | MED |
| `Depends()` | Parameter hiding from LLM (v2.14.0+) | HIGH |
| `ctx.debug()`, `ctx.info()`, `ctx.warning()` | Context logging methods | MED |
| `result_type` parameter | Typed responses in sampling (v2.14.1+) | LOW |
| `tool_names` parameter | Mount tool naming (v2.14.1+) | LOW |
| `FastMCP.as_proxy()` | Proxy server composition | LOW |

#### Deprecated APIs (in skill but removed from docs)
| API/Method | Replacement | Notes |
|------------|-------------|-------|
| `BearerAuthProvider` | `JWTVerifier` or `OAuthProxy` | Correctly documented in Error 26 |
| `Context.get_http_request()` | Middleware access | Correctly documented in Error 27 |
| `fastmcp.Image` import | `fastmcp.utilities.types.Image` | Correctly documented in Error 28 |

#### New Features Not Covered
- **Structured output via `result_type`**: `ctx.sample(..., result_type=MyModel)` for typed responses
- **Full `annotations` support**: `title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **`exclude_args` deprecation**: Migration path to `Depends()` not documented

#### Accurate Coverage
- Core decorators (`@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`)
- Background tasks (`task=True`)
- Sampling with tools (`ctx.sample(tools=[...])`)
- Storage backends (Memory, Disk, Redis)
- Server lifespans with v2.13.0 breaking change
- Middleware system (all 8 types)
- Server composition (`import_server()` vs `mount()`)
- OAuth patterns (4 authentication strategies)
- All 28 documented errors

---

### 2. Pattern Validation Agent

**Score**: 8.5/10

#### Deprecated Patterns Found
| Skill Shows | Docs Show | Location | Priority |
|-------------|-----------|----------|----------|
| `from fastmcp.utilities import Image` | `from fastmcp.utilities.types import Image, Audio, File` | Error 28 | HIGH |
| Missing `ToolResult` import | `from fastmcp.tools.tool import ToolResult` | Not documented | MED |
| Missing `ToolError` import | `from fastmcp.exceptions import ToolError` | Not documented | MED |

#### Import Changes
| Old Import | New Import | Notes |
|------------|------------|-------|
| `from fastmcp import Image` | `from fastmcp.utilities.types import Image` | v2.14.0 breaking change |
| `from fastmcp.auth import BearerAuthProvider` | `from fastmcp.auth import JWTVerifier` | v2.14.0 breaking change |

#### Configuration Changes
- None - all configuration patterns are current

#### Accurate Patterns
- `from fastmcp import FastMCP` at module level
- `from fastmcp import Context` for context injection
- `@mcp.tool()` decorator with parentheses
- Async/await patterns for I/O operations
- Resource URI syntax with schemes
- OAuth Proxy with consent screens
- Storage with `FernetEncryptionWrapper`
- Middleware execution order
- `import_server()` vs `mount()` distinction
- Background tasks with `task=True`
- Sampling with tools

---

### 3. Error/Issues Agent

**Score**: 7/10

#### Missing Error Coverage
| Error | Cause | Fix | Priority |
|-------|-------|-----|----------|
| `mask_error_details` security | Not documented | Add note that only `ToolError` messages exposed when enabled | HIGH |
| `*args/**kwargs` not supported | Functions with these fail as tools | Document as limitation | HIGH |
| Pydantic model JSON constraint | Models must be JSON objects, not stringified | Add note to Error 6 | MED |

#### Fixed Issues Still Documented
| Issue | Fixed In | Notes |
|-------|----------|-------|
| All v2.14.0 breaking changes | v2.14.0 | Correctly documented as migrations, not bugs |

#### New Common Errors
- **`$ref` resolution in outputSchema**: Fixed in v2.14.2, may affect v2.14.0-2.14.1 users
- **Lazy import of DiskStore missing sqlite3**: Fixed in v2.14.2

#### Accurate Error Docs
- All 28 errors correctly identified and explained
- Breaking changes (v2.13.0, v2.14.0) properly documented
- Migration paths provided for deprecated APIs

---

### 4. Ecosystem Agent

**Score**: 10/10

#### Registry Validation
- **Expected**: pypi
- **Skill Shows**: pypi
- **Status**: ✅

#### Package Name Validation
- **Expected**: fastmcp
- **Skill Shows**: fastmcp
- **Status**: ✅

#### Install Command Validation
| Skill Shows | Should Be | Status |
|-------------|-----------|--------|
| `pip install fastmcp` | `pip install fastmcp` | ✅ |
| `uv pip install fastmcp` | `uv pip install fastmcp` | ✅ |

#### Version Validation
- **Current Version**: 2.14.2
- **Skill References**: 2.14.2
- **Breaking Changes**: All documented (v2.14.0)

#### Dependency Validation
- httpx ✅
- pydantic ✅
- py-key-value-aio ✅
- cryptography ✅
- MCP SDK <2.x ✅

---

## Sources Audited

| Source | URL | Size | Status |
|--------|-----|------|--------|
| primary | https://gofastmcp.com/getting-started/welcome | 8 KB | ✅ |
| tools | https://gofastmcp.com/servers/tools | 43 KB | ✅ |

---

## Audit Metadata

- **Audited By**: /deep-audit command
- **Cache Used**: Yes (age: 0 days)
- **Firecrawl Credits**: ~$0.003
- **Agent Tokens**: ~35k (4 parallel agents)

---

## Next Steps

1. [x] ~~Fix critical issues~~ (None found)
2. [ ] Update Image import path in Error 28 (add `.types` submodule)
3. [ ] Add missing security documentation (`mask_error_details`)
4. [ ] Add `*args/**kwargs` limitation to errors
5. [ ] Re-run `/deep-audit fastmcp` to verify fixes
