# Community Knowledge Research: MCP OAuth Cloudflare

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/mcp-oauth-cloudflare/SKILL.md
**Packages Researched**: @cloudflare/workers-oauth-provider@0.2.2, agents@0.3.3, @modelcontextprotocol/sdk@1.25.1
**Official Repo**: cloudflare/workers-oauth-provider
**Time Window**: March 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 11 |
| TIER 1 (Official) | 7 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 2 |
| Recommended to Add | 7 |

**Key Insight**: The workers-oauth-provider library is very new (January 2025) and actively evolving. Multiple critical issues have been discovered post-training-cutoff, including RFC 8707 audience validation bugs, Claude.ai compatibility issues, and refresh token lifecycle challenges.

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Audience Validation Fails for RFC 8707 Resource Indicators with Paths

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [Issue #108](https://github.com/cloudflare/workers-oauth-provider/issues/108)
**Date**: 2025-11-10
**Verified**: Yes (detailed reproduction steps provided)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using RFC 8707 Resource Indicators with a path component (e.g., `resource=https://example.com/api`), token validation fails with `invalid_token: Token audience does not match resource server`. This breaks OAuth flows for services like ChatGPT custom connectors.

**Root Cause**:
The `resourceServer` is computed using only the origin:
```typescript
const resourceServer = `${requestUrl.protocol}//${requestUrl.host}`;
```

But RFC 8707 recommends using **full URLs with paths** for resource indicators. The `audienceMatches` function performs strict equality, so:
- Token audience: `https://example.com/api` (from `resource` parameter)
- Resource server: `https://example.com` (computed from request URL)
- Result: Validation fails

**Reproduction**:
```typescript
// 1. Configure OAuth provider with apiRoute: '/api'
// 2. Client sends auth request with resource=https://server.example.com/api
// 3. Token issued with aud: "https://server.example.com/api"
// 4. Client sends API request to https://server.example.com/api
// 5. Validation fails: resourceServer doesn't match aud
```

**Workaround**:
```typescript
// Vendor the library and modify handleApiRequest:
const resourceServer = `${requestUrl.protocol}//${requestUrl.host}${requestUrl.pathname}`;
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to v0.1.0 release (added audience validation per RFC 7519)
- Affects ChatGPT custom connectors and other RFC 8707-compliant clients

---

### Finding 1.2: Claude Client Cannot Use Library Due to Slash in Audience Validation

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [Issue #133](https://github.com/cloudflare/workers-oauth-provider/issues/133)
**Date**: 2026-01-15 (Very recent)
**Verified**: Limited info, but from official repo
**Impact**: HIGH (blocks Claude.ai integration)
**Already in Skill**: No

**Description**:
The Claude client cannot use the library. There is a '/' somewhere in the `audienceMatches` function that prevents Claude.ai from connecting. Issue is terse but high-impact.

**Reproduction**:
Not detailed in issue (minimal bug report).

**Solution/Workaround**:
Awaiting maintainer response. Likely related to Finding 1.1 (audience validation path handling).

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, open
- [ ] Won't fix

**Cross-Reference**:
- Likely related to Finding 1.1 (RFC 8707 path handling)
- Blocks Claude.ai MCP server integration

---

### Finding 1.3: Refresh Token Rotation Allows Previous Token (Security Debate)

**Trust Score**: TIER 1 - Official (GitHub Issue + README)
**Source**: [Issue #43](https://github.com/cloudflare/workers-oauth-provider/issues/43)
**Date**: 2025-06-06
**Verified**: Yes (documented in README)
**Impact**: MEDIUM (security trade-off)
**Already in Skill**: No

**Description**:
The library implements a **non-standard refresh token rotation** strategy. At any time, a grant may have **two valid refresh tokens**. When the client uses one, the other is invalidated, and a new one is generated.

**Why It Differs from OAuth 2.1**:
OAuth 2.1 requires single-use refresh tokens for public clients. However, the library author argues:
> "The single-use requirement is seemingly fundamentally flawed as it assumes that every refresh request will complete with no errors. In the real world, a transient network error, machine failure, or software fault could mean that the client fails to store the new refresh token."

**Security Trade-off**:
Allowing the previous refresh token to be used disables the replay attack detection. Some OAuth providers solve this by putting a **strict time limit** on how long the previous RT remains valid.

**Solution/Workaround**:
This is an intentional design decision, not a bug. For confidential clients (most MCP servers), this is compliant with OAuth 2.1. For public clients, consider implementing stricter rotation if needed.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (in README)
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Documented in README: https://github.com/cloudflare/workers-oauth-provider?tab=readme-ov-file#single-use-refresh-tokens
- Intentional trade-off between security and reliability

---

### Finding 1.4: No Provision to Restart Auth Flow When Upstream OAuth Doesn't Provide Refresh Tokens

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [Issue #34](https://github.com/cloudflare/workers-oauth-provider/issues/34)
**Date**: 2025-05-29
**Verified**: Yes (detailed code example)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When the upstream OAuth server doesn't provide refresh tokens, throwing an `invalid_grant` error in `tokenExchangeCallback` triggers re-authorization, but **props are not updated** after `completeAuthorization()`. This results in an infinite loop until the OAuth client restarts.

**Reproduction**:
```typescript
tokenExchangeCallback: async (options) => {
  if (options.grantType === "refresh_token") {
    const response = await fetch(upstreamTokenUrl, { /* ... */ });

    if (!response.ok) {
      // This triggers re-auth, but props don't update
      throw new Error(JSON.stringify({
        error: "invalid_grant",
        error_description: "access token expired. Please reauthenticate."
      }));
    }
  }
}
```

**Behavior**:
After throwing `invalid_grant`, the /authorize endpoint is called and token fetched, BUT props remain stale. Only after restarting the OAuth client (e.g., Claude) do props update correctly.

**Solution/Workaround**:
No clean workaround documented. Likely requires changes to how `completeAuthorization()` updates props after re-authorization.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to refresh token lifecycle (Finding 1.3)
- Blocks graceful re-auth for MCP servers with upstream OAuth providers

---

### Finding 1.5: Client ID Metadata Document (CIMD) Support Added in v0.2.2

**Trust Score**: TIER 1 - Official (Release Notes)
**Source**: [Release v0.2.2](https://github.com/cloudflare/workers-oauth-provider/releases/tag/v0.2.2)
**Date**: 2025-12-20
**Verified**: Yes
**Impact**: MEDIUM (new feature)
**Already in Skill**: No

**Description**:
v0.2.2 added **Client ID Metadata Document (CIMD) support**, allowing clients to use HTTPS URLs as `client_id` values that point to metadata documents.

**How It Works**:
When a `client_id` is an HTTPS URL with a non-root path, the provider fetches and validates the metadata document instead of looking up in KV storage. Added validation ensures:
- `client_id` in the document matches the URL
- `redirect_uris` are present

**Use Case**:
Matches the new MCP authorization spec: https://modelcontextprotocol.io/specification/draft/basic/authorization

**Solution/Workaround**:
No workaround needed - this is a new feature.

**Official Status**:
- [x] Fixed in version 0.2.2
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Latest version (0.2.2) as of 2025-12-20
- Implements MCP authorization spec

---

### Finding 1.6: Audience Validation Added in v0.1.0

**Trust Score**: TIER 1 - Official (Release Notes)
**Source**: [Release v0.1.0](https://github.com/cloudflare/workers-oauth-provider/releases/tag/v0.1.0)
**Date**: 2025-11-07
**Verified**: Yes
**Impact**: MEDIUM (new feature + Breaking)
**Already in Skill**: Partially (no migration notes)

**Description**:
v0.1.0 added **audience validation for OAuth tokens per RFC 7519**. This is a potentially breaking change for existing deployments.

**Impact**:
If your MCP server was deployed before v0.1.0 without audience validation, upgrading will require:
1. Ensuring tokens include correct `aud` claim
2. Verifying `audienceMatches` logic works for your use case

**Solution/Workaround**:
Test audience validation thoroughly after upgrading from v0.0.x to v0.1.0+.

**Official Status**:
- [x] Fixed in version 0.1.0
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to Finding 1.1 (audience validation bugs)
- First introduced in v0.1.0, refined in v0.2.2

---

### Finding 1.7: Feature Request - Disable Plain PKCE, Enforce S256 Only

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [Issue #113](https://github.com/cloudflare/workers-oauth-provider/issues/113)
**Date**: 2025-12-04
**Verified**: Yes
**Impact**: LOW (security enhancement request)
**Already in Skill**: No

**Description**:
There is currently no way to configure Workers OAuth Provider to allow only S256, which is the modern OAuth 2.1 recommended and most secure PKCE method. The /authorize endpoint accepts `code_challenge_method=plain`.

**Request**:
Add configuration option to disable plain PKCE and enforce S256 only.

**Solution/Workaround**:
No workaround. This is a feature request for improved security posture.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, feature request
- [ ] Won't fix

**Cross-Reference**:
- OAuth 2.1 best practices
- Security hardening

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Redirect URI Mismatch in Production (Development vs Production Behavior)

**Trust Score**: TIER 2 - High-Quality Community (GitHub Issue with detailed investigation)
**Source**: [Issue #29](https://github.com/cloudflare/workers-oauth-provider/issues/29)
**Date**: 2025-05-05
**Verified**: Partial (user-reported, multiple comments)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Users report `Invalid redirect URI. The redirect URI provided does not match any registered URI for this client` error in **production only**. Works fine in local dev with `wrangler dev`.

**Symptoms**:
- Local dev → MCP client connects successfully, `clientInfo` properly extracted
- Production → Fails with redirect URI error, no additional context
- User notes: "My MCP server never sets the redirect URIs so I am not sure how can I address this at all?"

**Root Cause Hypothesis**:
Likely related to Dynamic Client Registration (DCR) behavior differences between local and production environments. Redirect URIs are auto-registered during DCR, but something fails in production.

**Community Validation**:
- 15 comments on issue
- Multiple users confirming similar behavior
- Active discussion but no resolution yet

**Solution/Workaround**:
No confirmed workaround. Issue remains open.

**Recommendation**: Flag as TIER 2 (high-quality report) but needs official maintainer response to confirm root cause.

---

### Finding 2.2: General MCP Client Instability in Production

**Trust Score**: TIER 2 - High-Quality Community (Same issue as 2.1)
**Source**: [Issue #29](https://github.com/cloudflare/workers-oauth-provider/issues/29)
**Date**: 2025-05-05
**Verified**: Partial (user-reported)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Beyond redirect URI issues, users report general instability with MCP clients (Cursor, Windsurf, PyCharm) in production environments that don't occur in local development.

**Community Validation**:
- Grouped into "2 large buckets" by original reporter
- Multiple MCP clients affected
- Production-specific issue

**Recommendation**: Monitor this issue for updates. May be related to environment-specific configuration or Workers runtime differences.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Cloudflare Access Integration for Internal MCP Servers

**Trust Score**: TIER 3 - Community Consensus (Official Changelog + Blog)
**Source**: [Cloudflare Changelog](https://developers.cloudflare.com/changelog/2025-08-26-access-mcp-oauth/)
**Date**: 2025-08-26
**Verified**: Cross-referenced with Cloudflare docs
**Impact**: MEDIUM (new use case)
**Already in Skill**: No

**Description**:
Cloudflare Access now supports OAuth-based authentication for **internal MCP servers**, allowing organizations to control access through existing Access policies.

**Use Case**:
Restrict internal MCP server access to authorized personnel only, independent of which MCP client they use. OAuth tokens carry authenticated user's permissions and scopes to the MCP server.

**Integration Pattern**:
- Users authenticate through Cloudflare Access policies
- System issues OAuth tokens with user-specific permissions
- Works with MCP server portals (unified endpoint managing multiple MCP servers)

**Consensus Evidence**:
- Official Cloudflare changelog
- Documented in Cloudflare Agents docs
- Blog posts from Stytch and Auth0 discuss similar patterns

**Recommendation**: Add to skill as "Advanced Use Case" or "Enterprise Features" section.

---

### Finding 3.2: OAuth Provider as Both Client and Server

**Trust Score**: TIER 3 - Community Consensus (Multiple sources)
**Source**: Multiple blog posts ([Cloudflare Blog](https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp/), Stytch, Auth0)
**Date**: 2025 (various)
**Verified**: Cross-referenced
**Impact**: MEDIUM (architectural pattern)
**Already in Skill**: Partially (not emphasized)

**Description**:
When using a third-party OAuth provider, the MCP Server acts as **both an OAuth client (to upstream service) and as an OAuth server (to MCP clients)**. The Worker:
1. Stores encrypted access token in Workers KV
2. Issues its own token to the client
3. workers-oauth-provider handles spec compliance

**Key Point**:
The MCP server **generates and issues its own token** rather than passing through the third-party token. This is critical for security and spec compliance.

**Consensus Evidence**:
- Documented in Cloudflare MCP guides
- Blog posts from Stytch, Auth0 describe this pattern
- Official Cloudflare Agents documentation

**Recommendation**: Emphasize this architectural pattern in skill's "Architecture Overview" section.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

*No TIER 4 findings identified in this research.*

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Basic OAuth flow | OAuth Flow Diagram | Fully covered |
| CSRF protection | Security Features | Well documented with code examples |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 RFC 8707 Audience Path Bug | Known Issues Prevention | Add as new issue with workaround |
| 1.2 Claude Client Slash Bug | Known Issues Prevention | Add as issue #8 (blocking Claude.ai) |
| 1.4 Refresh Token Re-auth Loop | Known Issues Prevention | Add as issue #9 with props update warning |
| 1.5 CIMD Support (v0.2.2) | What's New / Recent Changes | Add to changelog section |
| 1.6 Audience Validation (v0.1.0) | Migration Notes | Add breaking change warning |
| 2.1 Redirect URI Prod vs Dev | Common Issues | Add troubleshooting entry |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 Refresh Token Rotation | Security Features | Add "Design Decision" callout |
| 1.7 Plain PKCE Enforcement | Configuration | Note as future enhancement |
| 3.1 Cloudflare Access Integration | Advanced Use Cases | New section for enterprise features |
| 3.2 Dual OAuth Role Pattern | Architecture Overview | Emphasize this pattern |

### Priority 3: Monitor (Open Issues)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 1.2 Claude Client Bug | Very recent (2026-01-15) | Watch for maintainer response |
| 2.2 General MCP Instability | Vague, needs more investigation | Monitor issue #29 for updates |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| OAuth issues in workers-sdk | 30 | 2 (mostly wrangler login) |
| All issues in workers-oauth-provider | 50 | 19 open |
| Recent releases | 10 | 3 major (v0.1.0, v0.2.2) |
| Issue #133 (Claude client) | 1 | HIGH |
| Issue #108 (RFC 8707) | 1 | HIGH |
| Issue #43 (RT rotation) | 1 | MEDIUM |
| Issue #34 (Re-auth loop) | 1 | HIGH |
| Issue #29 (Redirect URI) | 1 | HIGH |
| Issue #113 (PKCE enforcement) | 1 | LOW |
| Issue #116 (Token exchange RFC 8693) | 1 | MEDIUM (feature request) |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "workers-oauth-provider site:stackoverflow.com" | 0 | N/A (no results) |

**Note**: No Stack Overflow content found - library is too new (Jan 2025).

### Other Sources

| Source | Notes |
|--------|-------|
| [Stytch Blog](https://stytch.com/blog/building-an-mcp-server-oauth-cloudflare-workers/) | Content not extractable (CSS only) |
| [Cloudflare Changelog](https://developers.cloudflare.com/changelog/2025-08-26-access-mcp-oauth/) | TIER 3 - Access integration |
| [Cloudflare Blog - MCP](https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp/) | TIER 3 - Architecture patterns |
| GitHub issues | Primary source (19 findings) |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `gh release list/view` for changelog review
- `WebSearch` for Stack Overflow and blogs (limited results)
- `npm view` for package version history

**Limitations**:
- Stytch blog post not accessible (CSS-only response from WebFetch)
- No Stack Overflow content (package too new)
- Issue #133 has minimal details (terse bug report)
- Several issues remain open without resolution

**Time Spent**: ~25 minutes

**Research Window**: March 2025 - January 2026 (post-training-cutoff)

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference Finding 1.1 (RFC 8707) and Finding 1.2 (Claude client) against current library source code to verify if these are still present in v0.2.2.

**For api-method-checker**: Verify that the `audienceMatches` function and `handleApiRequest` method exist in @cloudflare/workers-oauth-provider@0.2.2 as described in Finding 1.1.

**For code-example-validator**: Validate the workaround code in Finding 1.1 and the tokenExchangeCallback example in Finding 1.4.

**For skill-findings-applier**: Use this report to update skills/mcp-oauth-cloudflare/SKILL.md with Priority 1 and Priority 2 findings.

---

## Integration Guide

### Adding TIER 1-2 Findings to SKILL.md

```markdown
### Issue #7: Audience Validation Fails for RFC 8707 Resource Indicators with Paths (v0.1.0+)

**Error**: `invalid_token: Token audience does not match resource server`
**Source**: [GitHub Issue #108](https://github.com/cloudflare/workers-oauth-provider/issues/108)
**Affects**: v0.1.0+ when using RFC 8707 resource indicators with paths (e.g., ChatGPT custom connectors)

**Why It Happens**: The `resourceServer` is computed using only the origin (`https://example.com`) but RFC 8707 recommends using full URLs with paths (`https://example.com/api`). Strict equality check fails.

**Prevention**:

If using RFC 8707 resource indicators with paths:

```typescript
// Workaround: Vendor the library and modify handleApiRequest
const resourceServer = `${requestUrl.protocol}//${requestUrl.host}${requestUrl.pathname}`;
```

Or avoid using paths in resource indicators until this is fixed upstream.

---

### Issue #8: Claude Client Cannot Connect (v0.2.2)

**Error**: Claude.ai MCP client fails to connect
**Source**: [GitHub Issue #133](https://github.com/cloudflare/workers-oauth-provider/issues/133)
**Affects**: v0.2.2, Claude.ai MCP clients

**Why It Happens**: There is a '/' in the `audienceMatches` function that prevents Claude.ai from connecting. Likely related to Issue #7.

**Prevention**: Monitor [Issue #133](https://github.com/cloudflare/workers-oauth-provider/issues/133) for updates. May require library update.

---

### Issue #9: Props Not Updated After Re-authorization When Upstream OAuth Expires

**Error**: Infinite re-auth loop when upstream OAuth doesn't provide refresh tokens
**Source**: [GitHub Issue #34](https://github.com/cloudflare/workers-oauth-provider/issues/34)
**Affects**: MCP servers using upstream OAuth providers without refresh tokens

**Why It Happens**: Throwing `invalid_grant` in `tokenExchangeCallback` triggers re-authorization, but `completeAuthorization()` doesn't update props. Stale props cause repeated auth failures.

**Prevention**:

If your upstream OAuth provider doesn't issue refresh tokens:

1. Implement a fallback strategy (store token expiry, re-auth before expiration)
2. Monitor [Issue #34](https://github.com/cloudflare/workers-oauth-provider/issues/34) for official fix
3. Consider restarting OAuth client as temporary workaround

```typescript
// This pattern causes the issue:
tokenExchangeCallback: async (options) => {
  if (options.grantType === "refresh_token") {
    const response = await fetchNewToken(options.props.accessToken);

    if (!response.ok) {
      // Triggers re-auth but props remain stale
      throw new Error(JSON.stringify({
        error: "invalid_grant",
        error_description: "access token expired"
      }));
    }
  }
}
```
```

### Adding Version History Section

```markdown
## Version History & Breaking Changes

### v0.2.2 (2025-12-20)

**New Features**:
- Client ID Metadata Document (CIMD) support - allows HTTPS URLs as `client_id` values
- Matches new MCP authorization spec

**Migration**: No breaking changes.

---

### v0.1.0 (2025-11-07)

**New Features**:
- Audience validation for OAuth tokens per RFC 7519

**Breaking Changes**:
- Tokens now require correct `aud` claim
- May break existing deployments without audience validation
- See Issue #108 for RFC 8707 path handling bug

**Migration**:
1. Ensure all tokens include correct `aud` claim
2. Test audience validation thoroughly
3. If using resource indicators with paths, apply workaround from Issue #108

---

### v0.0.x (Pre-November 2025)

Initial releases without audience validation.
```

---

## Additional Context

### Library Maturity

@cloudflare/workers-oauth-provider is **very new**:
- First release: v0.0.6 (August 2025)
- Major versions: v0.1.0 (November 2025), v0.2.2 (December 2025)
- Written with AI assistance (January 2025)
- Actively evolving with new features and bug fixes

**Recommendation**: Document version compatibility explicitly in skill, as breaking changes are likely as the library matures.

### Skill Version Alignment

Current skill references:
- `@cloudflare/workers-oauth-provider@^0.2.2` ✓ (Latest)
- `agents@^0.3.3` ✓
- `@modelcontextprotocol/sdk@^1.25.1` ✓

All versions current. No updates needed.

---

**Research Completed**: 2026-01-21 14:45 UTC
**Next Research Due**: After v0.3.0 release or June 2026 (whichever comes first)

---

## Sources

- [GitHub - cloudflare/workers-oauth-provider](https://github.com/cloudflare/workers-oauth-provider)
- [Authorization · Cloudflare Agents docs](https://developers.cloudflare.com/agents/model-context-protocol/authorization/)
- [Cloudflare Changelog - Access MCP OAuth](https://developers.cloudflare.com/changelog/2025-08-26-access-mcp-oauth/)
- [Building an MCP server with OAuth and Cloudflare Workers](https://stytch.com/blog/building-an-mcp-server-oauth-cloudflare-workers/)
- [Secure and Deploy Remote MCP Servers with Auth0 and Cloudflare](https://auth0.com/blog/secure-and-deploy-remote-mcp-servers-with-auth0-and-cloudflare/)
- [Build and deploy Remote Model Context Protocol (MCP) servers to Cloudflare](https://blog.cloudflare.com/remote-model-context-protocol-servers-mcp/)
