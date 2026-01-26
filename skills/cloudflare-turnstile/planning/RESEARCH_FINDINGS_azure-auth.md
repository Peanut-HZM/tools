# Community Knowledge Research: azure-auth

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/azure-auth/SKILL.md
**Packages Researched**: @azure/msal-react@3.0.23, @azure/msal-browser@4.27.0, jose@5.9.6
**Official Repo**: AzureAD/microsoft-authentication-library-for-js
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 5 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 2 |
| Already in Skill | 4 |
| Recommended to Add | 6 |

**Critical Discovery**: MSAL packages have major version update to 5.0.2 (January 2026) - skill currently documents v3.0.23/v4.27.0.

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Major Version Update - MSAL.js v5.0.2 Released

**Trust Score**: TIER 1 - Official
**Source**: [NPM @azure/msal-react](https://www.npmjs.com/package/@azure/msal-react) | [NPM @azure/msal-browser](https://www.npmjs.com/package/@azure/msal-browser)
**Date**: 2026-01-17
**Verified**: Yes (npm registry)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
MSAL.js has released v5.0.2 (both @azure/msal-browser and @azure/msal-react) as the new stable version. The current skill documents v3.0.23 and v4.27.0. This represents a major version change that may include breaking changes.

**Official Status**:
- [x] Released as latest version
- [ ] Breaking changes documented (needs verification)
- [ ] Requires skill update

**Recommendation**: Update skill to document v5.0.2 and investigate breaking changes between v4 → v5.

---

### Finding 1.2: React Router PublicClientApplication Initialization Edge Case

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #7068](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/7068)
**Date**: 2024-04-30
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using React Router loaders with acquireTokenSilent, the MsalProvider state gets updated during rendering if the same PublicClientApplication instance is used in both the loader and the provider. This causes React errors about updating another component's state during rendering.

**Reproduction**:
```typescript
// Router loader
const protectedLoader = async () => {
  const response = await msalInstance.acquireTokenSilent(request);
  // This updates MsalProvider state while Router is rendering
  return { data: fetchedData };
};

// App.tsx
<MsalProvider instance={msalInstance}>
  <RouterProvider router={router} />
</MsalProvider>
```

**Solution/Workaround**:
```typescript
// In the React Router loader, call initialize() again
const protectedLoader = async () => {
  await msalInstance.initialize(); // Prevents state update conflict
  const response = await msalInstance.acquireTokenSilent(request);
  return { data: fetchedData };
};
```

**Official Status**:
- [ ] Fixed in version
- [x] Documented behavior (in GitHub issue)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to: React Router v6 integration (partially covered in skill)

---

### Finding 1.3: Third-Party Cookie Blocking on iOS 18 Safari

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #7384](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/7384)
**Date**: 2024-10-17
**Verified**: Yes (maintainer confirmed)
**Impact**: HIGH
**Already in Skill**: Yes (Safari cookie issue documented)

**Description**:
On iOS 18 Safari (not Chrome), even with third-party cookies explicitly allowed in settings, silent token refresh fails with AADSTS50058. This is because Safari doesn't store the required session cookies for login.microsoftonline.com.

**Testing Note**: Works in Chrome on iOS 18, fails in Safari on iOS 18.

**Official Status**:
- [ ] Fixed in version
- [x] Documented behavior
- [x] Known issue, browser limitation
- [ ] Won't fix

**Cross-Reference**:
- Already in Skill: Error #5 "Safari/Edge Cookie Issues"
- Note: Should add iOS 18-specific caveat

---

### Finding 1.4: MsalAuthenticationTemplate Redirect Loop on Token Expiry

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5089](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/5089) (21 comments)
**Date**: 2022-08-09 (still relevant)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Yes (partially covered)

**Description**:
When a tab is left open for 24+ hours and the SPA refresh token expires (AADSTS700084), MsalAuthenticationTemplate causes an infinite redirect loop. The component tries to acquire a token, fails, redirects to login, comes back, and repeats.

**Root Cause**: MsalAuthenticationTemplate re-triggers authentication on every render when token acquisition fails, without checking if a redirect is already in progress.

**Solution/Workaround**:
```typescript
// Instead of MsalAuthenticationTemplate, use manual check
function ProtectedRoute({ children }) {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  // CRITICAL: Wait for in-progress operations to complete
  if (inProgress !== InteractionStatus.None) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    // Only redirect if not already in progress
    instance.loginRedirect(loginRequest);
    return null;
  }

  return <>{children}</>;
}
```

**Official Status**:
- [x] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix (template component limitation)

**Cross-Reference**:
- Already in Skill: Error #2 "AADSTS700084 - Refresh Token Expired"
- Partially covered in Protected Route Component section

---

### Finding 1.5: loadExternalTokens Fixes in v4.28.1

**Trust Score**: TIER 1 - Official
**Source**: [Release Notes msal-browser-v4.28.1](https://github.com/AzureAD/microsoft-authentication-library-for-js/releases/tag/msal-browser-v4.28.1)
**Date**: 2026-01-17
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The latest patch release (v4.28.1) includes fixes for `loadExternalTokens()` functionality and adds telemetry support for loading external tokens. This is relevant for scenarios where tokens are obtained outside of MSAL (e.g., from a backend) and loaded into MSAL's cache.

**Official Status**:
- [x] Fixed in version 4.28.1
- [ ] Documented in skill
- [x] Active maintenance

**Recommendation**: Update skill to reference v4.28.1 as minimum for external token scenarios.

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: setActiveAccount Doesn't Trigger Re-render

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #6989](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/6989)
**Date**: 2024-03-13
**Verified**: Multiple users confirmed
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Calling `msalInstance.setActiveAccount()` does not trigger a re-render of MsalProvider's children. This means that components using `useMsal()` won't automatically update when the active account changes. Developers must manually trigger re-renders or use workarounds.

**Reproduction**:
```typescript
// User switches accounts
msalInstance.setActiveAccount(newAccount);

// Components still show old account data
const { accounts } = useMsal();
console.log(accounts); // Still shows previous account
```

**Solution/Workaround**:
```typescript
// Option 1: Force re-render with state
const [accountKey, setAccountKey] = useState(0);

const switchAccount = (newAccount) => {
  msalInstance.setActiveAccount(newAccount);
  setAccountKey(prev => prev + 1); // Force MsalProvider re-render
};

// Option 2: Use instance.getActiveAccount() in components
// and manually check for changes
useEffect(() => {
  const activeAccount = instance.getActiveAccount();
  // Update local state
}, [instance]);
```

**Community Validation**:
- Multiple users confirmed: Yes
- Documented in GitHub issue with workarounds

**Recommendation**: Add to Known Issues section with workaround.

---

### Finding 2.2: Common Mistake - getActiveAccount vs getAllAccounts

**Trust Score**: TIER 2 - Community Pattern
**Source**: [Dev.to Tutorial](https://dev.to/ib1/docusaurus-authentication-with-entra-id-and-msal-417b) | Community patterns
**Date**: 2025
**Verified**: Code review
**Impact**: LOW
**Already in Skill**: No

**Description**:
A common developer mistake is calling `msalInstance.setActiveAccount(msalInstance.getActiveAccount()[0])` which throws an error because `getActiveAccount()` returns a single account object (or null), not an array.

**Wrong Pattern**:
```typescript
// WRONG - getActiveAccount() is not an array
msalInstance.setActiveAccount(msalInstance.getActiveAccount()[0]); // TypeError
```

**Correct Pattern**:
```typescript
// CORRECT - getAllAccounts() returns array
const accounts = msalInstance.getAllAccounts();
if (accounts.length > 0) {
  msalInstance.setActiveAccount(accounts[0]);
}
```

**Community Validation**:
- Appears in multiple tutorials and blog posts
- Common beginner mistake

**Recommendation**: Add to Quick Start or Common Pitfalls section.

---

### Finding 2.3: Authentication Template Timing Change (v2.0.14 → v2.0.22)

**Trust Score**: TIER 2 - Community Report
**Source**: [GitHub Issue #7232](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/7232)
**Date**: 2025-07-27
**Verified**: Version-specific behavior change
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Between msal-react v2.0.14 and v2.0.22, the behavior of AuthenticatedTemplate/UnauthenticatedTemplate changed. Previously, `setActiveAccount()` was called before authentication state updated. After the change, users are considered authenticated before `setActiveAccount()` is called, which can cause authenticated routes to fail if they depend on `getActiveAccount()` returning a value.

**Workaround**:
```typescript
// Ensure setActiveAccount is called during initialization
useEffect(() => {
  const accounts = instance.getAllAccounts();
  if (accounts.length > 0 && !instance.getActiveAccount()) {
    instance.setActiveAccount(accounts[0]);
  }
}, [instance]);
```

**Community Validation**:
- Confirmed by maintainer response
- Version-specific issue

**Recommendation**: Add to Breaking Changes section if updating from v2.x.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Azure AD B2C Sunset Timeline Extended

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2119363/migrating-existing-azure-ad-b2c-to-microsoft-entra) | [Envision IT Blog](https://envisionit.com/resources/articles/microsoft-to-end-sale-of-azure-ad-b2b2c-on-may-1-2025-shifting-to-entra-id-external-identities)
**Date**: 2025
**Verified**: Multiple sources agree
**Impact**: MEDIUM
**Already in Skill**: Yes (documented as "May 2025 - complete")

**Description**:
Azure AD B2C sunset timeline clarified:
- May 1, 2025: No new customers can sign up for B2C
- May 2030: Microsoft will continue supporting existing B2C customers
- March 15, 2026: Azure AD B2C P2 discontinued for all customers

The skill currently states "May 2025 - complete" which is misleading. Existing customers can continue using B2C until 2030.

**Consensus Evidence**:
- Microsoft official documentation confirms timeline
- Multiple migration guides reference these dates
- Contradicts skill's "complete" status

**Recommendation**: Update Azure AD B2C Sunset section with accurate timeline.

---

### Finding 3.2: Microsoft Entra External ID Migration Still in Preview

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Microsoft Learn](https://learn.microsoft.com/en-us/entra/external-id/customers/how-to-migrate-users) | [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2145947/seamless-migration-from-azure-ad-b2c-to-microsoft)
**Date**: 2025
**Verified**: Microsoft documentation
**Impact**: LOW
**Already in Skill**: No

**Description**:
Microsoft has not yet released a public migration path from Azure AD B2C to Entra External ID. The migration process remains in testing phase. When released for public preview, detailed migration steps will be documented.

**Current Guidance**:
- Seamless user migration samples exist on GitHub
- Self-Service Password Reset (SSPR) approach available
- No automated migration tool yet

**Consensus Evidence**:
- Microsoft Q&A confirms no public release yet
- Official docs provide "how to prepare" but not "how to migrate"

**Recommendation**: Add to Azure AD B2C section as migration guidance note.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Cloudflare Workers MSAL.js Incompatibility

**Trust Score**: TIER 4 - Single Source Blog
**Source**: [Hajek's Blog 2021](https://hajekj.net/2021/11/12/cloudflare-workers-and-azure-ad/)
**Date**: 2021-11-12
**Verified**: No (outdated)
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [x] Outdated (pre-2024)
- [ ] Cannot reproduce
- [ ] Contradicts official docs

**Description**:
Blog post from 2021 discusses using jose library for Azure AD token validation in Cloudflare Workers. However, this is outdated and the skill already documents this pattern comprehensively.

**Recommendation**: Already covered in skill. No action needed.

---

### Finding 4.2: JWKS Caching Duration Best Practices

**Trust Score**: TIER 4 - Unverified Pattern
**Source**: Various blog posts
**Date**: 2024-2025
**Verified**: No official guidance
**Impact**: LOW

**Why Flagged**:
- [x] Single source pattern
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [x] No official recommendation

**Description**:
Various sources suggest different JWKS cache durations (1 hour, 24 hours, etc.) but there's no official Microsoft guidance on optimal caching strategy for Azure AD JWKS.

The skill currently documents 1-hour caching:
```typescript
const JWKS_CACHE_DURATION = 3600000; // 1 hour
```

**Recommendation**: Keep current 1-hour pattern until official guidance emerges.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| AADSTS50058 silent sign-in loop | Known Issues #1 | Fully covered |
| AADSTS700084 refresh token expiry | Known Issues #2 | Fully covered |
| Safari cookie issues | Known Issues #5 | Fully covered, could add iOS 18 note |
| React Router redirect loops | Known Issues #3 | Fully covered with CustomNavigationClient |
| JWKS URL non-standard path | Backend JWT Validation | Fully documented with correct openid-configuration fetch |

---

## Recommended Actions

### Priority 1: Critical Updates (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Major Version Update (v5.0.2) | Package Versions header | Update versions, investigate breaking changes |
| 1.2 React Router loader edge case | Known Issues | Add as Issue #7 with workaround |
| 1.5 loadExternalTokens fixes | Package Versions | Update minimum version to v4.28.1 |

### Priority 2: Improvements (TIER 1-2, Medium Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 2.1 setActiveAccount no re-render | Known Issues | Add as Issue #8 with workaround |
| 2.2 getActiveAccount vs getAllAccounts | Quick Start or Common Pitfalls | Add code example correction |
| 3.1 B2C sunset timeline | Azure AD B2C Sunset section | Update with accurate 2030 timeline |

### Priority 3: Enhancements (TIER 2-3, Low Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 iOS 18 Safari specifics | Known Issues #5 | Add iOS 18 caveat to existing Safari issue |
| 2.3 Template timing change | Breaking Changes | Document if upgrading from v2.x |
| 3.2 External ID migration status | Azure AD B2C section | Add migration timeline note |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "AADSTS50058" in official repo | 10 | 2 |
| "AADSTS700084" in official repo | 10 | 1 |
| "React Router" in official repo | 10 | 2 |
| "redirect loop" in official repo | 10 | 1 |
| Latest releases | 10 | 3 |

### Stack Overflow

Search returned no results with proper filters. Used WebSearch instead.

### Other Sources

| Source | Notes |
|--------|-------|
| NPM Registry | Version verification for msal-react, msal-browser, jose |
| Microsoft Learn Docs | B2C sunset timeline, migration guidance |
| WebSearch | Community patterns, blog posts |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `gh release list` and `gh release view` for release notes
- `npm view` for package version verification
- `WebSearch` for community knowledge and official docs

**Limitations**:
- Stack Overflow searches returned no results (may need manual verification)
- MSAL v5.0.2 breaking changes not yet analyzed (released Jan 17, 2026)
- Some searches returned no 2024+ results (most issues are older)

**Time Spent**: ~15 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
1. Verify MSAL v5.0.2 breaking changes against official changelog
2. Cross-reference Azure AD B2C timeline against Microsoft official announcements
3. Verify loadExternalTokens documentation in official MSAL docs

**For api-method-checker**:
1. Verify that `instance.initialize()` workaround in Finding 1.2 is still valid in v5.x
2. Check if `setActiveAccount()` behavior changed in v5.x

**For code-example-validator**:
1. Validate React Router loader workaround code
2. Test setActiveAccount re-render workaround code
3. Verify getActiveAccount/getAllAccounts examples

---

## Integration Guide

### Adding TIER 1-2 Findings to SKILL.md

#### Update Package Versions (Finding 1.1)

```markdown
**Package Versions**: @azure/msal-react@5.0.2, @azure/msal-browser@5.0.2, jose@6.1.3
**Breaking Changes**: MSAL v4→v5 migration (January 2026), Azure AD B2C sunset (May 2025 - new signups blocked, existing until 2030), ADAL retirement (Sept 2025 - complete)
**Last Updated**: 2026-01-21
```

#### Add New Known Issue #7 (Finding 1.2)

```markdown
### 7. React Router Loader State Conflict

**Error**: React warning about updating state during render when using `acquireTokenSilent` in React Router loaders.

**Cause**: Using the same `PublicClientApplication` instance in both the router loader and `MsalProvider` causes state updates during rendering.

**Fix**: Call `initialize()` again in the loader:
```typescript
const protectedLoader = async () => {
  await msalInstance.initialize(); // Prevents state conflict
  const response = await msalInstance.acquireTokenSilent(request);
  return { data };
};
```

**Source**: [GitHub Issue #7068](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/7068)
```

#### Add New Known Issue #8 (Finding 2.1)

```markdown
### 8. setActiveAccount Doesn't Trigger Re-render

**Error**: Components using `useMsal()` don't update after calling `setActiveAccount()`.

**Cause**: `setActiveAccount()` updates the MSAL instance but doesn't notify React of the change.

**Fix**: Force re-render with state:
```typescript
const [accountKey, setAccountKey] = useState(0);

const switchAccount = (newAccount) => {
  msalInstance.setActiveAccount(newAccount);
  setAccountKey(prev => prev + 1); // Force update
};
```

**Source**: [GitHub Issue #6989](https://github.com/AzureAD/microsoft-authentication-library-for-js/issues/6989)
```

#### Update Azure AD B2C Section (Finding 3.1)

```markdown
## Azure AD B2C Sunset

**Timeline**:
- **May 1, 2025**: Azure AD B2C no longer available for new customer signups
- **March 15, 2026**: Azure AD B2C P2 discontinued for all customers
- **May 2030**: Microsoft will continue supporting existing B2C customers with standard support

**Existing B2C Customers**: Can continue using B2C until 2030, but should plan migration to Entra External ID.

**New Projects**: Use **Microsoft Entra External ID** for consumer/customer identity scenarios.

**Migration Status**: As of January 2026, automated migration tools are in testing phase. Manual migration guidance available at Microsoft Learn.

**Migration Path**:
- Different authority URL format (`{tenant}.ciamlogin.com` vs `{tenant}.b2clogin.com`)
- Updated SDK support (same MSAL libraries)
- New pricing model (consumption-based)

See: https://learn.microsoft.com/en-us/entra/external-id/
```

---

**Research Completed**: 2026-01-21
**Next Research Due**: After MSAL v6.x release or next major breaking change
