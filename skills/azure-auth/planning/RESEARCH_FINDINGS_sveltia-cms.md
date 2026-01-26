# Community Knowledge Research: sveltia-cms

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/sveltia-cms/SKILL.md
**Packages Researched**: @sveltia/cms@0.128.5
**Official Repo**: sveltia/sveltia-cms
**Time Window**: January 2025 - January 2026 (post-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 11 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 4 |
| Recommended to Add | 11 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Version 0.128.5 Released (Post-Cutoff)

**Trust Score**: TIER 1 - Official
**Source**: [npm @sveltia/cms](https://www.npmjs.com/package/@sveltia/cms)
**Date**: 2026-01-20
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Skill documents version 0.127.0 (December 2025) but current version is 0.128.5 (January 20, 2026). Multiple releases since December 2025 with bug fixes and new features.

**Major releases since skill last updated:**
- v0.128.0 (2026-01-12): Global slug lowercase option, Developer Mode help menu
- v0.128.1 (2026-01-13): Bug fixes
- v0.128.2-0.128.5 (January 2026): Incremental fixes

**Official Status**:
- [x] Current stable version
- [x] Documented in releases

**Recommendation**: Update skill version reference from 0.127.0 to 0.128.5

---

### Finding 1.2: Global Slug Lowercase Option (v0.128.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.128.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.128.0)
**Date**: 2026-01-12
**Verified**: Yes via GitHub issue #594
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
New global slug option `lowercase` (boolean) controls whether slugs are automatically converted to lowercase. Default is `true` to maintain backward compatibility, but can be set to `false` to preserve original casing.

**Use Case**:
Solves issue where users want mixed-case slugs (e.g., "MyBlogPost" instead of "myblogpost").

**Configuration**:
```yaml
slug:
  encoding: unicode-normalized
  clean_accents: false
  sanitize_replacement: '-'
  lowercase: false  # NEW - preserve original casing
```

**Official Status**:
- [x] Released in v0.128.0
- [x] Solves GitHub issue #594

**Recommendation**: Add to "Configuration Options" section

---

### Finding 1.3: Paths with Parentheses Break Entry Loading (Fixed v0.128.1)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #596](https://github.com/sveltia/sveltia-cms/issues/596)
**Date**: 2026-01-13 (reported), 2026-01-13 (fixed)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Sveltia CMS fails to load existing entries when the `path` option contains parentheses `()`. This affects Next.js/Nextra users using route groups like `app/(content)/(writing)/`.

**Reproduction**:
```yaml
collections:
  - name: pages
    folder: app/(pages)
    path: "{{slug}}/page"  # ← Fails to load existing entries
    extension: mdx
```

**Error Behavior**:
- Creating new entries works
- Loading/listing existing entries fails silently
- CMS shows "No entries found" despite files existing

**Solution/Workaround**:
Fixed in v0.128.1 - no workaround needed for current version.

**Official Status**:
- [x] Fixed in version v0.128.1
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects Next.js App Router route groups
- Affects Nextra documentation sites

**Recommendation**: Add to "Common Errors & Solutions" as historical note (fixed in current version)

---

### Finding 1.4: Root Folder Collections Break GitHub Backend (Fixed v0.125.0)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #580](https://github.com/sveltia/sveltia-cms/issues/580)
**Date**: 2025-12-20 (reported), 2025-12-20 (fixed)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Collections with `folder: ""` or `folder: "."` or `folder: "/"` fail when creating new entries via GitHub backend. GraphQL query incorrectly constructs path starting with `/` (absolute) instead of relative path.

**Reproduction**:
```yaml
collections:
  - name: root-pages
    folder: ""  # or "." or "/"
    # ← Breaks when creating entries via GitHub backend
```

**Error Behavior**:
- Works locally via browser File API
- Fails with GitHub backend (GraphQL error)
- Leading slash breaks GraphQL mutation

**Solution/Workaround**:
Fixed in v0.125.0 - no workaround needed for v0.125.0+.

**Official Status**:
- [x] Fixed in version v0.125.0
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Use Case**: VitePress and other frameworks storing content at repository root.

**Recommendation**: Add to "Common Errors & Solutions" as historical note

---

### Finding 1.5: Datetime Widget Missing Timezone (Fixed v0.126.0)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #565](https://github.com/sveltia/sveltia-cms/issues/565)
**Date**: 2025-12-10 (reported), 2025-12-26 (fixed)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Default datetime widget outputs timestamps WITHOUT timezone suffix (e.g., `2025-12-10T22:56:00` instead of `2025-12-10T22:56:00Z`). This causes Hugo to infer UTC, which can mark posts as "future" and skip building them for users in timezones ahead of UTC.

**Reproduction**:
```yaml
fields:
  - label: Date
    name: date
    widget: datetime
    # Outputs: 2025-12-10T22:56:00 (no timezone)
```

**Problems**:
1. Hugo infers UTC when timezone missing
2. Users in UTC+X timezones create "future" posts
3. Posts don't build until time passes in UTC
4. Documentation was incorrect about default format

**Solution/Workaround**:
```yaml
# Option 1: Use picker_utc
fields:
  - label: Date
    name: date
    widget: datetime
    picker_utc: true

# Option 2: Specify format with timezone
fields:
  - label: Date
    name: date
    widget: datetime
    format: "YYYY-MM-DDTHH:mm:ss.SSSZ"

# Option 3: Configure Hugo to accept missing timezone
# config.toml
[frontmatter]
  date = [":default", ":fileModTime"]
```

**Additional Gotcha**:
When `format` is specified, Sveltia becomes **strict** - existing entries with different formats show as blank and get overwritten if saved. This is SILENT data loss.

**Official Status**:
- [x] Fixed in version v0.126.0 (improved date parser)
- [x] Documentation corrected
- [ ] Still potential issue with strict format matching

**Recommendation**: Update "Common Errors & Solutions" #8 with format strictness warning

---

### Finding 1.6: Raw Format for Text Files (v0.126.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.126.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.126.0)
**Date**: 2025-12-26
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
New `raw` format allows editing files without front matter (CSV, JSON, YAML, plain text). Must have single `body` field with widget type: `code`, `markdown`, `richtext`, or `text`.

**Use Case**:
- Edit configuration files (JSON, YAML)
- Manage CSV data
- Edit plain text files

**Configuration**:
```yaml
collections:
  - name: config
    label: Configuration Files
    files:
      - label: Site Config
        name: site_config
        file: config.json
        format: raw  # ← NEW format type
        fields:
          - label: Config
            name: body
            widget: code
            default_language: json
```

**Restrictions**:
- Only one field allowed (must be named `body`)
- Widget must be: `code`, `markdown`, `richtext`, or `text`
- No front matter parsing

**Official Status**:
- [x] Released in v0.126.0
- [x] Solves Decap CMS issue #1152

**Recommendation**: Add to "Configuration Patterns" or "Advanced Features"

---

### Finding 1.7: Editor Pane Locale via URL Query (v0.126.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.126.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.126.0)
**Date**: 2025-12-26
**Verified**: Yes via issue #585
**Impact**: LOW
**Already in Skill**: No

**Description**:
Can override editor locale via URL query parameter `?_locale=fr` to get edit links for specific locales.

**Use Case**:
Generate direct edit links for translators or content editors for specific languages.

**Example**:
```
https://yourdomain.com/admin/#/collections/posts/entries/my-post?_locale=fr
```

**Official Status**:
- [x] Released in v0.126.0
- [x] Solves issue #585

**Recommendation**: Add to "i18n Patterns" section

---

### Finding 1.8: Number Field String Encoding (v0.125.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.125.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.125.0)
**Date**: 2025-12-20
**Verified**: Yes via issue #574
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
New `value_type` option for Number field accepts `int/string` and `float/string` to save numbers as strings instead of numbers in front matter.

**Use Case**:
Some static site generators or schemas require numeric values stored as strings (e.g., `age: "25"` instead of `age: 25`).

**Configuration**:
```yaml
fields:
  - label: Age
    name: age
    widget: number
    value_type: int/string  # Saves as "25" not 25

  - label: Price
    name: price
    widget: number
    value_type: float/string  # Saves as "19.99" not 19.99
```

**Official Status**:
- [x] Released in v0.125.0
- [x] Solves issue #574

**Recommendation**: Add to "Field Configuration" section

---

### Finding 1.9: slug_length Deprecation (v0.127.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.127.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.127.0)
**Date**: 2025-12-29
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `slug_length` collection option is deprecated and will be removed in v1.0. Use new `maxlength` option in global slug options instead.

**Migration**:
```yaml
# ❌ Deprecated (pre-v0.127.0)
collections:
  - name: posts
    slug_length: 50

# ✅ New (v0.127.0+)
slug:
  maxlength: 50
```

**Timeline**: Will be removed in Sveltia CMS 1.0 (expected early 2026).

**Official Status**:
- [x] Deprecated in v0.127.0
- [ ] Breaking change in v1.0

**Recommendation**: Add to "Breaking Changes & Updates" section

---

### Finding 1.10: Google Gemini 2.5 Flash-Lite Support (v0.127.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.127.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.127.0)
**Date**: 2025-12-29
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Added support for Google Gemini 2.5 Flash-Lite model for AI translations (one-click translation feature).

**Use Case**:
Faster, cheaper AI translations for i18n workflows.

**Official Status**:
- [x] Released in v0.127.0

**Recommendation**: Add to "AI Integration" or "i18n Features" if skill covers those

---

### Finding 1.11: Richtext Field Type Alias (v0.124.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.124.0](https://github.com/sveltia/sveltia-cms/releases/tag/v0.124.0)
**Date**: 2025-12-14
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Added `richtext` as an alias for `markdown` widget to align with Decap CMS terminology. Both work identically.

**Configuration**:
```yaml
fields:
  - label: Body
    name: body
    widget: richtext  # ← NEW alias for markdown
```

**Future**: HTML output support planned for `richtext` field type.

**Official Status**:
- [x] Released in v0.124.0
- [ ] HTML output planned

**Recommendation**: Add to "Field Types" documentation

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: GDPR Concern with Google Fonts CDN

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #443](https://github.com/sveltia/sveltia-cms/issues/443)
**Date**: 2025-07-01
**Verified**: Maintainer acknowledged, workaround provided
**Impact**: HIGH (for EU users)
**Already in Skill**: No

**Description**:
Sveltia CMS loads Google Fonts and Material Symbols from Google CDN without user consent, potentially violating GDPR in EU. Google tracks font usage and collects IP addresses.

**Why It Matters**:
- EU data protection law violation
- Blocking issue for EU public sector
- Privacy concern for privacy-focused sites

**Workarounds**:

**Option 1: Vite Plugin (Recommended)**
```typescript
// vite.config.ts
function ensureGDPRCompliantFonts(): Plugin {
  const fontsURLRegex = /fonts\.googleapis\.com\/css2/g
  const replacement = 'fonts.bunny.net/css'
  return {
    name: 'gdpr-compliant-fonts',
    enforce: 'post',
    transform(code) {
      if (fontsURLRegex.test(code)) {
        return code.replaceAll(fontsURLRegex, replacement)
      }
    },
  }
}

export default defineConfig({
  plugins: [ensureGDPRCompliantFonts()],
})
```

**Option 2: Bunny Fonts (1:1 Google Fonts replacement)**
- Use https://fonts.bunny.net instead of fonts.googleapis.com
- EU-based, GDPR-compliant
- Same API as Google Fonts

**Option 3: Self-hosted fonts**
- Use `@fontsource` npm packages
- Bundle fonts with application
- No external requests

**Maintainer Response**:
- Acknowledged issue
- Plans to add system font option (post-v1.0)
- Sveltia itself collects no data (fonts are only concern)
- Each developer must implement privacy policy

**Official Status**:
- [ ] Fix planned (post-v1.0)
- [x] Workarounds available
- [ ] Documentation needed

**Community Validation**:
- Multiple users confirmed concern
- Workaround tested and working
- EU public sector blocker

**Recommendation**: Add to "Known Issues Prevention" with workaround

---

### Finding 2.2: Documentation Site Active Development

**Trust Score**: TIER 2 - Official announcement
**Source**: Multiple release notes (v0.124.0+)
**Date**: December 2025 - January 2026
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Official documentation site at https://sveltiacms.app is under active development. In-app docs now link there instead of GitHub README. Multiple releases note "development pace slower than usual" due to docs work.

**Current Status**:
- New docs site: https://sveltiacms.app/en/docs
- Still incomplete (WIP)
- GitHub README being phased out

**Impact**:
- Skill should reference new docs site
- Some docs may be incomplete/inaccurate
- GitHub README still useful fallback

**Official Status**:
- [x] Active development
- [ ] Complete

**Recommendation**: Update skill references to point to https://sveltiacms.app/en/docs with note that some sections may be incomplete

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Beta Status and Single-Developer Project

**Trust Score**: TIER 3 - Official docs + community discussion
**Source**: [Official Docs](https://sveltiacms.app/en/docs), [Migration article](https://dubasipavankumar.com/blog/sveltia-cms-migration-decap-replacement/)
**Date**: 2026-01-21
**Verified**: Cross-referenced multiple sources
**Impact**: MEDIUM
**Already in Skill**: Partially (version status mentioned)

**Description**:
Sveltia CMS is a **single-developer personal project** currently in beta with v1.0 due early 2026. Development pace is slower than enterprise-backed projects.

**Key Points**:
1. Single maintainer (not a team)
2. Beta software (breaking changes possible)
3. v1.0 release early 2026
4. Development pace explicitly "slower than usual"

**Implications**:
- Not suitable for large enterprises needing compliance certifications
- Best for small-to-medium projects
- Technical knowledge required for setup
- Limited support compared to commercial CMS

**Documentation Quote**: "This is a single-developer personal project... development pace may be slower than you expect."

**Recommendation**: Already in skill ("Public Beta" status). Consider adding note about single-developer nature to set expectations.

---

### Finding 3.2: Custom Widgets Not Supported

**Trust Score**: TIER 3 - Community consensus + official limitation
**Source**: [Migration article](https://dubasipavankumar.com/blog/sveltia-cms-migration-decap-replacement/), GitHub discussions
**Date**: 2025+
**Verified**: Multiple sources confirm
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Cannot create custom input widgets like Decap CMS's React-based system. Built-in widgets only.

**Why It Matters**:
- Decap CMS allowed custom React widgets
- Sveltia is Svelte-based (not React)
- No extension API for custom widgets yet

**Workaround**:
None - use built-in widgets or wait for API.

**Consensus Evidence**:
- Migration guides mention this limitation
- GitHub discussions confirm
- Not on v1.0 roadmap

**Recommendation**: Add to "When NOT to Use" section or "Known Limitations"

---

## Already Documented in Skill

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| OAuth authentication failures | Known Issues #1 | Fully covered |
| TOML front matter errors | Known Issues #2 | Fully covered |
| YAML parse errors | Known Issues #3 | Fully covered |
| Missing type="module" | Known Issues #5 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Version 0.128.5 | Current Versions | Update from 0.127.0 to 0.128.5 |
| 1.2 Slug lowercase option | Configuration Options | Add new `lowercase` option |
| 1.3 Paths with parentheses | Common Errors (historical) | Add note "Fixed in v0.128.1" |
| 1.4 Root folder collections | Common Errors (historical) | Add note "Fixed in v0.125.0" |
| 1.5 Datetime timezone | Common Errors #8 | Update with format strictness warning |
| 1.9 slug_length deprecation | Breaking Changes | Add deprecation notice |
| 2.1 GDPR Google Fonts | Known Issues Prevention | Add with Vite workaround |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.6 Raw format | Advanced Features | New format type for text files |
| 1.7 Locale via URL | i18n Patterns | Useful for translators |
| 1.8 Number string encoding | Field Configuration | Niche use case |
| 1.10 Gemini 2.5 Flash-Lite | AI Features | If skill covers AI |
| 1.11 Richtext alias | Field Types | Terminology alignment |
| 2.2 Docs site development | Resources | Update docs URLs |

### Priority 3: Monitor (TIER 3, Contextual)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 Single-developer note | Already partially covered | Consider adding to caveats |
| 3.2 No custom widgets | Limitation, not bug | Add to "When NOT to Use" |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Open issues | 30 | 8 feature requests, 2 bugs |
| Closed issues (recent) | 20 | 4 critical bugs (fixed) |
| Recent releases (v0.122-0.128) | 15 | 11 with breaking changes/features |

### npm Registry

| Query | Result |
|-------|--------|
| Latest version | 0.128.5 (2026-01-20) |
| Version history | 300+ releases since 2023 |

### Stack Overflow

| Query | Results |
|-------|---------|
| "sveltia cms" 2025 2026 | 0 results |

**Note**: No Stack Overflow presence yet (new project, niche CMS).

### Community Articles

| Source | Notes |
|--------|-------|
| Migration guide (dubasipavankumar.com) | Real-world migration experience |
| Official docs (sveltiacms.app) | Beta status, limitations documented |

---

## Methodology Notes

**Tools Used**:
- `gh` CLI for GitHub issue/release search
- `npm view` for package version verification
- `WebSearch` for community content
- `WebFetch` for documentation extraction

**Limitations**:
- No Stack Overflow presence (project too new/niche)
- GitHub Discussions API returned no recent results
- Limited to English-language sources

**Time Spent**: ~18 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference datetime timezone findings (1.5) with current Hugo/Jekyll documentation to ensure workarounds are still valid.

**For version-checker**: Run `npm view @sveltia/cms` regularly to catch new releases (high velocity - 5 releases in January 2026 alone).

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### Update Version

```markdown
## Current Versions

- **@sveltia/cms**: 0.128.5 (verified January 2026)
- **Status**: Public Beta (v1.0 expected early 2026)
```

#### Add Slug Lowercase Option

```markdown
### Global Slug Options (v0.128.0+)

Configure slug generation behavior:

```yaml
slug:
  encoding: unicode-normalized
  clean_accents: false
  sanitize_replacement: '-'
  lowercase: true  # Default: convert to lowercase
  maxlength: 50    # Default: unlimited
```

**lowercase** (v0.128.0+): Set to `false` to preserve original casing in slugs.
```

#### Update Datetime Widget Error

```markdown
### 8. ❌ Datetime Widget Missing Timezone

**⚠️ CRITICAL: Format Strictness Warning (v0.124.1+)**

When you specify a `format` option, Sveltia becomes **strict**:
- Existing entries with different formats show as **blank**
- Saving will **overwrite** with blank value (SILENT DATA LOSS)
- No error message shown

**Workarounds**:
1. Don't specify `format` if you have mixed formats
2. Normalize all dates first before adding `format`
3. Use `picker_utc: true` instead (more flexible)
```

#### Add GDPR Workaround

```markdown
### 9. ❌ GDPR Violation: Google Fonts CDN

**Error**: Sveltia loads Google Fonts without consent
**Impact**: GDPR violation in EU, privacy concern

**Symptoms**:
- Privacy-focused sites blocked
- EU public sector cannot use

**Causes**:
- Google Fonts CDN tracks users
- IP addresses collected
- No opt-out option

**Solution (Vite Plugin)**:

```typescript
// vite.config.ts
import { defineConfig, type Plugin } from 'vite'

function ensureGDPRCompliantFonts(): Plugin {
  const fontsURLRegex = /fonts\.googleapis\.com\/css2/g
  const replacement = 'fonts.bunny.net/css'
  return {
    name: 'gdpr-compliant-fonts',
    enforce: 'post',
    transform(code) {
      if (fontsURLRegex.test(code)) {
        return code.replaceAll(fontsURLRegex, replacement)
      }
    },
  }
}

export default defineConfig({
  plugins: [ensureGDPRCompliantFonts()],
})
```

**Alternative**: Use Bunny Fonts (1:1 Google Fonts replacement, EU-based, GDPR-compliant).
```

---

**Research Completed**: 2026-01-21 19:30 UTC
**Next Research Due**: After v1.0 release (early 2026) or in 3 months (whichever comes first)
