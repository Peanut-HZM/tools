# Content Audit: [SKILL_NAME]

**Date**: [YYYY-MM-DD]
**Overall Score**: [X.X]/10
**Status**: [PASS | NEEDS_UPDATE | CRITICAL]

---

## Summary

| Category | Score | Status | Key Finding |
|----------|-------|--------|-------------|
| API Coverage | X/10 | ✅/⚠️/❌ | [Brief summary] |
| Pattern Validation | X/10 | ✅/⚠️/❌ | [Brief summary] |
| Error Documentation | X/10 | ✅/⚠️/❌ | [Brief summary] |
| Ecosystem Accuracy | X/10 | ✅/⚠️/❌ | [Brief summary] |

**Score Legend**:
- ✅ 8-10: Accurate, minor updates only
- ⚠️ 5-7: Needs attention, some gaps
- ❌ 1-4: Critical issues, major updates needed

---

## Critical Issues

> Issues requiring immediate attention before skill should be used

1. **[Issue Title]**
   - Location: [Section/line in SKILL.md]
   - Problem: [Description]
   - Fix: [Recommended action]

---

## Recommended Updates

### High Priority

- [ ] [Update description]
- [ ] [Update description]

### Medium Priority

- [ ] [Update description]
- [ ] [Update description]

### Low Priority

- [ ] [Update description]

---

## Agent Reports

### 1. API Coverage Agent

**Score**: X/10

#### Missing APIs (documented but not in skill)
| API/Method | Description | Priority |
|------------|-------------|----------|
| `methodName()` | [What it does] | HIGH/MED/LOW |

#### Deprecated APIs (in skill but removed from docs)
| API/Method | Replacement | Notes |
|------------|-------------|-------|
| `oldMethod()` | `newMethod()` | Removed in vX.X |

#### New Features Not Covered
- **Feature Name**: [Description, why it matters]

#### Accurate Coverage
- [List of correctly documented APIs]

---

### 2. Pattern Validation Agent

**Score**: X/10

#### Deprecated Patterns Found
| Skill Shows | Docs Show | Location | Priority |
|-------------|-----------|----------|----------|
| `old syntax` | `new syntax` | Section X | HIGH/MED |

#### Import Changes
| Old Import | New Import | Breaking? |
|------------|------------|-----------|
| `from x import y` | `from x.z import y` | Yes/No |

#### Configuration Changes
- [List config format changes]

#### Accurate Patterns
- [List patterns that are correct]

---

### 3. Error/Issues Agent

**Score**: X/10

#### Missing Error Coverage
| Error | Cause | Fix | Priority |
|-------|-------|-----|----------|
| `ErrorName` | [Cause] | [Fix] | HIGH/MED |

#### Fixed Issues Still Documented
| Issue | Fixed In | Notes |
|-------|----------|-------|
| [Issue] | vX.X | Remove from skill |

#### New Common Errors
- **ErrorName**: [Description, when it occurs]

#### Accurate Error Docs
- [List correctly documented errors]

---

### 4. Ecosystem Agent

**Score**: X/10

#### Registry Validation
- **Expected**: [npm | pypi | github]
- **Skill Shows**: [what skill says]
- **Status**: ✅/❌

#### Package Name Validation
- **Expected**: [correct name]
- **Skill Shows**: [what skill says]
- **Status**: ✅/❌

#### Install Command Validation
| Skill Shows | Should Be | Status |
|-------------|-----------|--------|
| `pip install x` | `pip install y` | ❌ |

#### Version Validation
- **Current Version**: X.X.X
- **Skill References**: Y.Y.Y
- **Breaking Changes**: [List if any]

#### Dependency Validation
- [List dependency issues]

---

## Sources Audited

| Source | URL | Size | Status |
|--------|-----|------|--------|
| primary | [URL] | X KB | ✅/❌ |
| api | [URL] | X KB | ✅/❌ |
| changelog | [URL] | X KB | ✅/❌ |

---

## Audit Metadata

- **Audited By**: /deep-audit command
- **Cache Used**: Yes/No (age: X days)
- **Firecrawl Credits**: ~$0.00X
- **Agent Tokens**: ~Xk

---

## Next Steps

1. [ ] Fix critical issues
2. [ ] Update deprecated patterns
3. [ ] Add missing API coverage
4. [ ] Update version references
5. [ ] Re-run `/deep-audit [skill]` to verify fixes
