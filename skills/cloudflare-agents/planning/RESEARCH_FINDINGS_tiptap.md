# Community Knowledge Research: tiptap

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/tiptap/SKILL.md
**Packages Researched**: @tiptap/react@3.15.3, @tiptap/starter-kit@3.15.3, @tiptap/pm@3.15.3
**Official Repo**: ueberdosis/tiptap
**Time Window**: 2024 - Present (Focus on v3.x releases and post-cutoff changes)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 10 |
| TIER 1 (Official) | 5 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 2 |
| Recommended to Add | 8 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: React 19 Compatibility - Drag Handle Extension Issue

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5876](https://github.com/ueberdosis/tiptap/issues/5876)
**Date**: 2024-11-25
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
The @tiptap-pro/extension-drag-handle depends on tippyjs-react, which was archived on November 9, 2024 without React 19 support. This causes ref-related errors in React 19 applications.

**Error**:
```
TypeError: Cannot read properties of undefined (reading 'refs')
```

**Reproduction**:
```typescript
// Using drag-handle extension with React 19
import { Editor } from '@tiptap/react'
import DragHandle from '@tiptap-pro/extension-drag-handle'

const editor = useEditor({
  extensions: [StarterKit, DragHandle],
  // Fails in React 19 due to tippyjs-react dependency
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Document that React 18 is recommended when using Pro extensions with drag handles. Core Tiptap supports React 19 as of v2.10.0.

**Cross-Reference**:
- Related to: [GitHub Discussion #5816](https://github.com/ueberdosis/tiptap/discussions/5816) - Feature Request: Support for React 19
- Note: UI Components currently work best with React 18 per official docs

---

### Finding 1.2: Drag Handle Regression in v3.14.0

**Trust Score**: TIER 1 - Official
**Source**: [v3.14.0 Release Notes](https://github.com/ueberdosis/tiptap/releases/tag/v3.14.0)
**Date**: 2025-12-19
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
A regression introduced by PR #6972 caused elements appended to the editor's parent node to stay detached. This specifically affected the drag handle plugin.

**Reproduction**:
Elements that got appended to editor's parent node would not attach to DOM properly, making drag handles non-functional.

**Solution**:
Fixed in v3.14.0 patch - "Append all children of editors parent node to element"

**Official Status**:
- [x] Fixed in version 3.14.0
- [x] Documented behavior

**Recommendation**: Update skill to mention v3.14.0 as minimum version if using drag handles, or note the regression existed in earlier 3.x versions.

---

### Finding 1.3: ProseMirror Multiple Versions Conflict

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #577](https://github.com/ueberdosis/tiptap/issues/577) (131 comments), [Issue #6171](https://github.com/ueberdosis/tiptap/issues/6171)
**Date**: 2020-2025 (ongoing)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Partially (mentions @tiptap/pm peer dependency)

**Description**:
Installing extensions can pull in different versions of prosemirror-model or prosemirror-view, causing "multiple versions of prosemirror-model were loaded" errors. The unique-id extension is particularly problematic in testing environments.

**Error**:
```
Error: Looks like multiple versions of prosemirror-model were loaded
```

**Reproduction**:
```bash
# Install tiptap
npm install @tiptap/react @tiptap/starter-kit

# Install additional extension
npm install @tiptap/extension-unique-id

# Extensions may pull different prosemirror versions
# Results in duplicate prosemirror-model in node_modules
```

**Solution**:
```json
// package.json - Force single ProseMirror version
{
  "resolutions": {
    "prosemirror-model": "~1.21.0",
    "prosemirror-view": "~1.33.0",
    "prosemirror-state": "~1.4.3"
  }
}
```

Or reinstall dependencies:
```bash
rm -rf node_modules package-lock.json
npm install
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior
- [x] Known issue, workaround required

**Recommendation**: Add to Known Issues section with resolutions pattern. Emphasize importance of @tiptap/pm package.

---

### Finding 1.4: Vue 3 Performance Issue with Large Documents

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5031](https://github.com/ueberdosis/tiptap/issues/5031)
**Date**: 2024-04-04
**Verified**: Yes
**Impact**: HIGH (Vue users only)
**Already in Skill**: No

**Description**:
Migrating from @tiptap/vue-2 to @tiptap/vue-3 causes quadratic performance degradation with documents containing 1500+ nodes. NodeViewRenderer takes excessive time per component.

**Reproduction**:
Documents with 1500+ nodes load significantly slower in Vue 3 compared to Vue 2 implementation.

**Official Status**:
- [x] Documented behavior
- [x] Known issue, being investigated

**Recommendation**: If skill ever adds Vue support, document this performance gotcha. Currently skill is React-focused, so not urgent.

---

### Finding 1.5: New Audio Extension in v3.16.0

**Trust Score**: TIER 1 - Official
**Source**: [v3.16.0 Release Notes](https://github.com/ueberdosis/tiptap/releases/tag/v3.16.0)
**Date**: 2026-01-20
**Verified**: Yes
**Impact**: LOW (new feature)
**Already in Skill**: No

**Description**:
Tiptap added a native audio extension with demos and tests in v3.16.0 (released 2026-01-20, after skill last update).

**Official Status**:
- [x] New feature in v3.16.0

**Recommendation**: Update skill package versions to v3.16.0+ and mention audio extension in extension catalog if comprehensive.

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: EditorProvider vs useEditor Confusion

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #5856 Comment](https://github.com/ueberdosis/tiptap/issues/5856#issuecomment-2493124171)
**Date**: 2024-11-22
**Verified**: Maintainer comment
**Impact**: MEDIUM
**Already in Skill**: Partially (shows useEditor pattern)

**Description**:
Users commonly misuse EditorProvider and useEditor together, leading to SSR errors. EditorProvider is a wrapper around useEditor for React Context setup - they should not be used simultaneously.

**Error**:
```
SSR has been detected, please set `immediatelyRender` explicitly to `false`
```

**Incorrect Pattern**:
```typescript
// Don't use both together
<EditorProvider>
  <MyComponent />
</EditorProvider>

function MyComponent() {
  const editor = useEditor({ ... }) // ❌ Wrong - EditorProvider already created editor
}
```

**Correct Pattern**:
```typescript
// Option 1: Use EditorProvider only
<EditorProvider immediatelyRender={false} extensions={[StarterKit]}>
  <EditorContent />
</EditorProvider>

// Option 2: Use useEditor only
function Editor() {
  const editor = useEditor({
    extensions: [StarterKit],
    immediatelyRender: false,
  })
  return <EditorContent editor={editor} />
}
```

**Community Validation**:
- Source: Contributor comment (nperez0111)
- Reactions: 2 thumbs up
- Confirmed by multiple users in thread

**Recommendation**: Add to Known Issues or Common Patterns section to clarify EditorProvider vs useEditor usage.

---

### Finding 2.2: Content Not Updating with setContent After immediatelyRender: false

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #5856 Comment](https://github.com/ueberdosis/tiptap/issues/5856#issuecomment-2627854854)
**Date**: 2025-01-31
**Verified**: Partial (user report, needs testing)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using `immediatelyRender: false`, dynamically loaded content set via `editor.commands.setContent()` may not render visually, even though it exists in editor state.

**Reproduction**:
```typescript
const editor = useEditor({
  extensions: [StarterKit],
  content: '', // Initially empty
  immediatelyRender: false,
})

// Later, after content loads
useEffect(() => {
  if (editor && loadedContent) {
    editor.commands.setContent(loadedContent)
    // Content exists in editor (verified via console.log)
    // But doesn't display visually
  }
}, [editor, loadedContent])
```

**Community Validation**:
- Upvotes: 2
- Multiple users experiencing same issue
- No official resolution yet

**Recommendation**: Flag as TIER 3 until official workaround confirmed. May need to use `content` prop reactively instead of setContent.

---

### Finding 2.3: Markdown Extension Now Official (v3.15.0)

**Trust Score**: TIER 2 - High-Quality Community + Official
**Source**: [v3.15.0 Release Notes](https://github.com/ueberdosis/tiptap/releases/tag/v3.15.0), [PR #6821](https://github.com/ueberdosis/tiptap/pull/6821)
**Date**: 2026-01-05
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Yes (documented as beta)

**Description**:
The Markdown extension received significant fixes in v3.15.0+, including fixes for overlapping underline/bold/italic serialization. Still beta but increasingly stable.

**Fix in v3.16.0**:
```
Fix incorrect Markdown output when underline is mixed with bold or italic
and their ranges do not fully overlap.
```

**Official Status**:
- [x] Beta status
- [x] Fixes in v3.15.0 and v3.16.0

**Recommendation**: Update skill to note v3.15.0+ fixes for markdown, particularly underline+formatting edge cases.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Headless Nature Causes Setup Confusion

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Tiptap Reviews 2025](https://tiptap.dev/blog/release-notes), Web search results
**Date**: 2024-2025
**Verified**: Cross-referenced
**Impact**: LOW (documentation/expectation issue)
**Already in Skill**: Partially addressed via Quick Start

**Description**:
Users commonly report that Tiptap is "not plug-and-play" and has a learning curve because it's headless - the library provides infrastructure but users must design and implement UI.

**Common Caveats** (from user reviews):
- Not plug-and-play
- Requires work to shape UI and features
- Occasional minor UI inconsistencies
- Text color vs background color icons cause confusion

**Recommendation**: Skill already addresses this with Quick Start and shadcn integration, but could add a "What to Expect" section explaining headless architecture.

---

### Finding 3.2: Collaborative Editing Scale Limits (100+ Clients)

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Tiptap Collaboration Docs](https://tiptap.dev/docs/hocuspocus/guides/collaborative-editing), [Yjs Docs](https://docs.yjs.dev/ecosystem/editor-bindings/tiptap2)
**Date**: 2024-2025
**Verified**: Official documentation
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions Y.js pattern, not limits)

**Description**:
Tiptap collaborative editing with Y.js doesn't scale well beyond 100+ concurrent clients in the same document. WebRTC connections become problematic at scale.

**Known Limitations**:
- WebRTC: Browsers refuse to connect with too many clients
- Y.js indirect connections help but still don't scale to 100+ clients
- Schema version conflicts: Clients with different schemas can cause content loss

**Official Guidance**:
Use Hocuspocus backend for scalability beyond basic WebRTC setup.

**Recommendation**: Add scale limitations to Collaborative Editing pattern section (Issue #4 mentions "Never load more than 100 widgets" which seems related but unclear).

---

## Already Documented in Skill

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| immediatelyRender: false for SSR | Issue #1, Quick Start | Fully covered |
| @tiptap/pm peer dependency | Dependencies, Quick Start | Fully covered |
| Base64 image bloat | Issue #4 | Fully covered with R2 upload pattern |
| Performance with large docs | Issue #2 | Covered via useEditorState pattern |
| Markdown extension beta status | Pattern 2 | Documented as beta, notes API may change |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 React 19 Compatibility | Dependencies / Known Issues | Add note that Pro extensions require React 18, core supports React 19 |
| 1.3 ProseMirror Version Conflicts | Known Issues Prevention | Add as Issue #6 with resolutions pattern |
| 2.1 EditorProvider vs useEditor | Common Patterns | Add clarification about not using both together |
| 1.5 Audio Extension | Dependencies | Update to v3.16.0, mention audio extension availability |
| 2.3 Markdown Fixes | Pattern 2 | Update to note v3.15.0+ fixes for underline+formatting |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.2 Drag Handle Regression | Known Issues | Document v3.14.0 as minimum for drag handles |
| 3.2 Collaborative Scale Limits | Collaborative Pattern | Add note about 100+ client limitations |
| 2.2 setContent with immediatelyRender | Community Tips | Verify workaround first, may need reactive content prop |

### Priority 3: Monitor (Not Urgent)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 1.4 Vue 3 Performance | Skill is React-focused | Monitor if Vue support added later |
| 3.1 Headless Confusion | Already addressed via Quick Start | No action needed |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| High-comment issues (API) | 50 | 8 |
| "error OR bug" in repo | 30 | 2 |
| "collaborative OR yjs" | 15 | 1 |
| "performance OR slow" | 15 | 1 |
| Recent releases | 10 | 4 |

**Top Issues by Comments**:
- #577: Multiple ProseMirror versions (131 comments)
- #547: Tiptap v2 announcement (103 comments)
- #1166: Vue 3 support (76 comments)
- #4492: ReactNodeViewRender performance (52 comments)
- #5856: immediatelyRender SSR error (active)

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "tiptap site:stackoverflow.com error 2024 2025" | 0 | N/A |
| "tiptap gotcha edge case 2024 2025" | Web results | 1 GitHub issue found |

**Note**: Stack Overflow has limited recent Tiptap content. GitHub Issues are primary community knowledge source.

### Web Search

| Query | Key Findings |
|-------|-------------|
| "tiptap immediatelyRender SSR" | Confirmed Issue #5856, official docs updated |
| "tiptap image upload R2 cloudflare" | Community using R2 pattern, official UI components exist |
| "tiptap collaborative editing Y.js" | Scale limitations documented, Hocuspocus recommended |
| "tiptap performance large documents" | Vue 3 regression, long texts demo exists |
| "tiptap React 19 compatibility" | v2.10.0 added support, Pro extensions lag behind |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `gh release view` for release notes
- `gh api` for high-comment issue discovery
- `WebSearch` for Stack Overflow, blogs, and official docs

**Limitations**:
- Stack Overflow has minimal recent Tiptap Q&A (GitHub is primary source)
- Some Pro extension issues require Pro access to verify
- Vue-specific findings deprioritized (skill is React-focused)
- Couldn't access full discussion threads for some closed issues

**Time Spent**: ~20 minutes

**Coverage**:
- ✅ Post-training-cutoff releases (v3.14.0 - v3.16.0)
- ✅ SSR/hydration issues
- ✅ Performance issues
- ✅ Collaborative editing
- ✅ Image upload patterns
- ✅ React 19 compatibility
- ⚠️ Extension ordering (limited findings)
- ⚠️ ProseMirror integration (covered via version conflicts)

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Verify that React 19 support status (finding 1.1) matches current official Tiptap docs
- Cross-reference v3.16.0 audio extension against official docs

**For api-method-checker**:
- Verify `editor.commands.setContent()` behavior with `immediatelyRender: false` (finding 2.2)
- Confirm package.json resolutions pattern works for ProseMirror deduplication

**For code-example-validator**:
- Test EditorProvider vs useEditor patterns (finding 2.1)
- Validate resolutions pattern for ProseMirror conflicts (finding 1.3)

---

## Integration Guide

### Adding Finding 1.3 to SKILL.md (ProseMirror Conflicts)

```markdown
### Issue #6: ProseMirror Multiple Versions Conflict

**Error**: `Error: Looks like multiple versions of prosemirror-model were loaded`
**Source**: [GitHub Issue #577](https://github.com/ueberdosis/tiptap/issues/577) (131 comments), [Issue #6171](https://github.com/ueberdosis/tiptap/issues/6171)
**Why It Happens**: Installing additional Tiptap extensions can pull different versions of prosemirror-model or prosemirror-view, creating duplicate dependencies in node_modules
**Prevention**: Use package resolutions to force a single ProseMirror version

```json
// package.json
{
  "resolutions": {
    "prosemirror-model": "~1.21.0",
    "prosemirror-view": "~1.33.0",
    "prosemirror-state": "~1.4.3"
  }
}
```

Or reinstall dependencies:
```bash
rm -rf node_modules package-lock.json
npm install
```

**Note**: The @tiptap/pm package is designed to prevent this issue, but extensions may still introduce conflicts.
```

### Adding Finding 2.1 to Common Patterns

```markdown
### Pattern 4: EditorProvider vs useEditor

**When to use EditorProvider**:
```typescript
// Use when you need React Context for the editor
import { EditorProvider, EditorContent } from '@tiptap/react'

<EditorProvider
  immediatelyRender={false}
  extensions={[StarterKit]}
  content="<p>Hello World!</p>"
>
  <EditorContent />
</EditorProvider>
```

**When to use useEditor**:
```typescript
// Use when you don't need Context or want more control
import { useEditor, EditorContent } from '@tiptap/react'

function Editor() {
  const editor = useEditor({
    extensions: [StarterKit],
    content: '<p>Hello World!</p>',
    immediatelyRender: false,
  })

  return <EditorContent editor={editor} />
}
```

**CRITICAL**: ❌ Never use EditorProvider and useEditor together
EditorProvider is a wrapper around useEditor for automatic React Context setup. Using both will create two editor instances and cause SSR errors.

**Source**: [Contributor comment](https://github.com/ueberdosis/tiptap/issues/5856#issuecomment-2493124171)
```

### Updating Dependencies Section (Finding 1.1 + 1.5)

```markdown
**Required**:
- `@tiptap/react@^3.16.0` - React integration (React 19 supported)
- `@tiptap/starter-kit@^3.16.0` - Essential extensions bundle
- `@tiptap/pm@^3.16.0` - ProseMirror peer dependency
- `react@^19.0.0` - React framework

**React Version Note**:
- **Core Tiptap**: Supports React 19 as of v2.10.0
- **UI Components**: Best with React 18 (Next.js 15 recommended)
- **Pro Extensions**: May require React 18 (drag-handle uses archived tippyjs-react)

**Optional**:
- `@tiptap/extension-audio@^3.16.0` - Audio support (NEW in v3.16.0)
- `@tiptap/extension-image@^3.16.0` - Image support
[...rest of optional dependencies...]
```

---

## Sources

### GitHub Issues & PRs
- [Issue #5856: SSR immediatelyRender error](https://github.com/ueberdosis/tiptap/issues/5856)
- [Issue #5602: Drag handle SSR compatibility](https://github.com/ueberdosis/tiptap/issues/5602)
- [Issue #577: Multiple ProseMirror versions](https://github.com/ueberdosis/tiptap/issues/577)
- [Issue #6171: Unique ID ProseMirror conflict](https://github.com/ueberdosis/tiptap/issues/6171)
- [Issue #5031: Vue 3 performance regression](https://github.com/ueberdosis/tiptap/issues/5031)
- [Issue #5876: React 19 drag handle compatibility](https://github.com/ueberdosis/tiptap/issues/5876)
- [Discussion #5816: React 19 support request](https://github.com/ueberdosis/tiptap/discussions/5816)

### Release Notes
- [v3.16.0 Release](https://github.com/ueberdosis/tiptap/releases/tag/v3.16.0) - Audio extension, markdown fixes
- [v3.15.0 Release](https://github.com/ueberdosis/tiptap/releases/tag/v3.15.0) - dispatchTransaction hook
- [v3.14.0 Release](https://github.com/ueberdosis/tiptap/releases/tag/v3.14.0) - Drag handle regression fix

### Documentation
- [Tiptap Next.js Docs](https://tiptap.dev/docs/editor/getting-started/install/nextjs)
- [Tiptap Performance Guide](https://tiptap.dev/docs/guides/performance)
- [Tiptap Collaboration Docs](https://tiptap.dev/docs/hocuspocus/guides/collaborative-editing)
- [Yjs + Tiptap Integration](https://docs.yjs.dev/ecosystem/editor-bindings/tiptap2)

### Community Resources
- [Liveblocks Tiptap Best Practices](https://liveblocks.io/docs/guides/tiptap-best-practices-and-tips)
- [Liveblocks + Tiptap + Next.js Guide](https://liveblocks.io/docs/get-started/nextjs-tiptap)
- [Which Rich Text Editor 2025 Comparison](https://liveblocks.io/blog/which-rich-text-editor-framework-should-you-choose-in-2025)

---

**Research Completed**: 2026-01-21 16:45
**Next Research Due**: After v4.0.0 release or Q2 2026 (whichever comes first)
**Skill Version at Time of Research**: Last updated 2026-01-09, packages at v3.15.3
