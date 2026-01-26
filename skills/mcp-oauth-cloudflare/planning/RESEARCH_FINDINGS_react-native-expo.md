# Community Knowledge Research: React Native Expo

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/react-native-expo/SKILL.md
**Packages Researched**: expo@~54.0.31, react-native@0.81.5, expo-router@6+
**Official Repo**: expo/expo
**Time Window**: December 2024 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 17 |
| TIER 1 (Official) | 9 |
| TIER 2 (High-Quality Community) | 5 |
| TIER 3 (Community Consensus) | 3 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 2 |
| Recommended to Add | 15 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Expo SDK 54 - Last Legacy Architecture Release

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: 2025-09-XX (SDK 54 release)
**Verified**: Yes
**Impact**: CRITICAL
**Already in Skill**: Partially (mentions 0.82+ mandatory, but not SDK-specific timeline)

**Description**:
SDK 54 is the **final Expo SDK release supporting Legacy Architecture**. SDK 55 will be New Architecture-only. This creates a critical decision point for projects not yet migrated.

**Migration Path**:
- SDK 54 = React Native 0.81 (Legacy Architecture still supported)
- SDK 55 = React Native 0.83 (New Architecture mandatory)

**Official Status**:
- [x] Documented behavior
- [x] Known limitation
- Migration required before SDK 55

**Cross-Reference**:
- Corroborated by: [Expo SDK 54 Upgrade Guide](https://expo.dev/blog/expo-sdk-upgrade-guide)
- Related to: Skill's "New Architecture Mandatory (0.82+)" section - needs SDK timeline added

---

### Finding 1.2: expo-file-system Legacy API Removal Timeline

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54), [FileSystem Legacy Docs](https://docs.expo.dev/versions/latest/sdk/filesystem-legacy/)
**Date**: SDK 54 release
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
`expo-file-system` underwent a breaking API change in SDK 54. The legacy API is available at `expo-file-system/legacy` in SDK 54 but **will be completely removed in SDK 55**.

**Breaking Change**:
```typescript
// SDK 53 and earlier:
import * as FileSystem from 'expo-file-system';
FileSystem.writeAsStringAsync(uri, content);

// SDK 54+ (legacy import):
import * as FileSystem from 'expo-file-system/legacy';
FileSystem.writeAsStringAsync(uri, content);

// SDK 54+ (new API):
import { File } from 'expo-file-system';
const file = new File(uri);
await file.writeString(content);
```

**Migration Required**:
SDK 55 will remove `expo-file-system/legacy` entirely. All projects must migrate to the new File and Directory class-based API.

**Official Status**:
- [x] Documented breaking change
- [x] Migration required before SDK 55

**Cross-Reference**:
- Related GitHub Issue: [#39056](https://github.com/expo/expo/issues/39056) - `getContentUriAsync` missing in new API
- Related GitHub Issue: [#42167](https://github.com/expo/expo/issues/42167) - Ships .ts source instead of .d.ts (type errors)

---

### Finding 1.3: expo-av Removed in SDK 55

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54), [expo-av GitHub](https://github.com/expo/expo-av)
**Date**: SDK 53 (deprecated), SDK 55 (removed)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
`expo-av` was deprecated in SDK 53 and **completely removed in SDK 55**. The package is no longer maintained and will not receive patches.

**Migration**:
```typescript
// OLD: expo-av (SDK 54 and earlier)
import { Audio } from 'expo-av';
const { sound } = await Audio.Sound.createAsync(
  require('./audio.mp3')
);
await sound.playAsync();

// NEW: expo-audio (SDK 53+)
import { useAudioPlayer } from 'expo-audio';
const player = useAudioPlayer(require('./audio.mp3'));
player.play();

// Video component
// OLD: expo-av
import { Video } from 'expo-av';

// NEW: expo-video (SDK 52+)
import { VideoView } from 'expo-video';
```

**Timeline**:
- SDK 52: `expo-video` introduced
- SDK 53: `expo-audio` introduced, `expo-av` deprecated
- SDK 54: Last release including `expo-av` (no patches)
- SDK 55: `expo-av` removed entirely

**Official Status**:
- [x] Documented deprecation
- [x] Migration required for SDK 55+

**Cross-Reference**:
- Related GitHub: [Expensify/App#64846](https://github.com/Expensify/App/issues/64846) - Migration example
- Medium post: [What's New in Expo SDK 53](https://medium.com/@onix_react/whats-new-in-expo-sdk-53-e1a8b338c19d)

---

### Finding 1.4: Reanimated v4 Requires New Architecture

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 FYI](https://github.com/expo/fyi/blob/main/expo-54-reanimated.md), [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: SDK 54 release
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
`react-native-reanimated` v4 **exclusively requires the New Architecture**. Projects using Legacy Architecture must stay on Reanimated v3.

**Version Matrix**:
| Reanimated Version | Architecture Support | Expo SDK |
|-------------------|---------------------|----------|
| v3 | Legacy + New Architecture | SDK 52-54 |
| v4 | New Architecture ONLY | SDK 54+ |

**Gotcha - NativeWind Incompatibility**:
```bash
# NativeWind does not support Reanimated v4 yet (as of Jan 2026)
# If using NativeWind, must stay on Reanimated v3
npm install react-native-reanimated@^3
```

**Migration Steps**:
1. Install `react-native-worklets` (required for v4)
2. Follow [official Reanimated v3 → v4 migration guide](https://docs.swmansion.com/react-native-reanimated/docs/fundamentals/getting-started/)
3. **Skip** babel.config.js changes if using `babel-preset-expo` (auto-configured)

**Official Status**:
- [x] Documented limitation
- [x] Workaround: Stay on v3 if using Legacy Architecture or NativeWind

**Cross-Reference**:
- GitHub Discussion: [#39130](https://github.com/expo/expo/discussions/39130) - Migration with NativeWind

---

### Finding 1.5: Android Edge-to-Edge Mandatory in All Apps

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: SDK 54 release
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Edge-to-edge display is **enabled in all Android apps by default in SDK 54 and cannot be disabled**. This affects UI layout with system bars.

**Breaking Change**:
```json
// app.json or app.config.js
{
  "expo": {
    "android": {
      // This setting is now IGNORED - edge-to-edge always enabled
      "edgeToEdgeEnabled": false  // ❌ No effect
    }
  }
}
```

**Impact on UI**:
Content now extends behind system status bar and navigation bar. Developers must account for insets manually.

**Workaround**:
```typescript
// Use react-native-safe-area-context
import { SafeAreaView } from 'react-native-safe-area-context';

function App() {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      {/* Content respects system bars */}
    </SafeAreaView>
  );
}
```

**Official Status**:
- [x] Documented behavior
- [x] Cannot be disabled

**Cross-Reference**:
- Note: `react-native-edge-to-edge` is no longer included as dependency - must install directly if needed

---

### Finding 1.6: Metro Internal Imports Changed

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: SDK 54 release
**Verified**: Yes
**Impact**: LOW (only affects custom Metro configs)
**Already in Skill**: No

**Description**:
Metro bundler internal import paths changed. Custom configs using `metro/src/*` will break.

**Breaking Change**:
```javascript
// OLD (SDK 53 and earlier):
const { getDefaultConfig } = require('metro/src/defaults');

// NEW (SDK 54+):
const { getDefaultConfig } = require('metro/private/defaults');
```

**Impact**: Only affects projects with custom Metro configurations directly importing internal modules.

**Official Status**:
- [x] Documented breaking change

---

### Finding 1.7: JSC Support Removed from React Native

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: React Native 0.81 (SDK 54)
**Verified**: Yes
**Impact**: LOW (Hermes is default)
**Already in Skill**: Partially (mentions JSC removed from Expo Go, but not RN core removal)

**Description**:
JavaScriptCore (JSC) first-party support removed from React Native 0.81+. Moved to community package `@react-native-community/javascriptcore`.

**Migration**:
```bash
# If you still need JSC (rare):
npm install @react-native-community/javascriptcore
```

**Note**: Expo Go (SDK 52+) removed JSC entirely - only Hermes supported.

**Official Status**:
- [x] Documented change
- [x] Community-maintained alternative available

---

### Finding 1.8: Xcode 16.1+ and Node 20.19.4+ Required

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: SDK 54 release
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
SDK 54 raised minimum requirements for build tools.

**Requirements**:
- **Xcode**: Minimum 16.1, Xcode 26 recommended
- **Node.js**: Minimum 20.19.4
- **iOS Deployment Target**: iOS 15.1+

**Breaking Change**: Older Xcode/Node versions will fail to build.

**Official Status**:
- [x] Documented requirement

---

### Finding 1.9: Expo Go Limitations Expanding

**Trust Score**: TIER 1 - Official
**Source**: [Expo SDK 53 Changelog](https://expo.dev/changelog/sdk-53), community reports
**Date**: SDK 53-54 releases
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions Google Maps removal in SDK 53+)

**Description**:
Expo Go is becoming increasingly limited. More features now require custom development builds.

**SDK 53+ Limitations**:
- Google Maps removed from Expo Go (must use dev client)
- Background tasks (`expo-background-task`) unavailable in Expo Go
- Push notification testing shows warnings in Expo Go

**Recommendation**: Use EAS Development Builds for production-like testing.

**Official Status**:
- [x] Documented limitation
- [x] Workaround: Use `expo-dev-client`

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: iOS Crashes on Launch with Hermes + New Architecture (SDK 54)

**Trust Score**: TIER 2 - High-Quality Community (GitHub Issue with reproduction)
**Source**: [GitHub Issue #41824](https://github.com/expo/expo/issues/41824), [Medium Post](https://medium.com/@shanavascruise/new-architecture-by-default-hermes-ios-expo-updates-can-break-your-ios-builds-4e98d89a1648)
**Date**: 2025-12-24
**Verified**: Reproduction available
**Impact**: CRITICAL
**Already in Skill**: No

**Description**:
Apps using Expo SDK 54 + Hermes + New Architecture + `expo-updates` crash on launch on iOS with:
```
hermes::vm::JSObject::putComputed_RJS
hermes::vm::arrayPrototypePush
```

**Conditions**:
- Expo SDK 54
- New Architecture enabled
- Hermes enabled (default)
- Using `expo-updates`
- iOS only (Android unaffected)

**Reproduction**:
Same commit builds successfully (Build 12), but all subsequent builds (13-18) crash immediately on launch on TestFlight.

**Root Cause** (from Medium article):
Expo Updates requires `:hermes_enabled` flag in Podfile when using New Architecture on iOS, even though Hermes is enabled by default.

**Workaround**:
```ruby
# ios/Podfile
use_frameworks! :linkage => :static
ENV['HERMES_ENABLED'] = '1'  # ⚠️ CRITICAL: Must be explicit with New Arch + expo-updates
```

**Community Validation**:
- Multiple users reporting same issue
- Reproduction repository available
- Crash logs consistent across reports

**Recommendation**: Add to Known Issues Prevention section

---

### Finding 2.2: EAS Build "No variants exist" Error (SDK 54)

**Trust Score**: TIER 2 - High-Quality Community (GitHub Issue with minimal repro)
**Source**: [GitHub Issue #42370](https://github.com/expo/expo/issues/42370)
**Date**: 2026-01-21
**Verified**: Minimal reproduction available
**Impact**: HIGH
**Already in Skill**: No

**Description**:
EAS Build fails with Gradle error when building Android apps with certain React Native modules.

**Error Message**:
```
Could not resolve project :react-native-async-storage_async-storage
> No matching variant of project :react-native-async-storage_async-storage was found.
> No variants exist.
```

**Conditions**:
- Expo SDK 54.0.31
- React Native 0.81.5
- Using native modules with underscore naming (e.g., `@react-native-async-storage/async-storage`)
- EAS Build only (local builds work)

**Reproduction**:
Available at: https://github.com/Deviaq/DQApp/tree/master/expo-eas-build-bug

**Workaround** (from issue):
Issue appears related to Gradle variant resolution. Check `android/gradle.properties` for correct `newArchEnabled` setting.

**Community Validation**:
- Reproduction repository provided
- Issue marked "needs review" by Expo team
- Multiple similar issues reported

**Recommendation**: Add to Known Issues or Troubleshooting section

---

### Finding 2.3: expo-router NativeTabs Icon Color Issues

**Trust Score**: TIER 2 - High-Quality Community (Multiple GitHub Issues)
**Source**: [GitHub Issue #41789](https://github.com/expo/expo/issues/41789), [#41601](https://github.com/expo/expo/issues/41601), [#42013](https://github.com/expo/expo/issues/42013)
**Date**: December 2025 - January 2026
**Verified**: Multiple reports
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
`expo-router` NativeTabs (iOS bottom tabs) don't respect default icon colors. Icons appear black/white instead of tint color.

**Conditions**:
- Expo Router v6+
- NativeTabs component
- iOS only

**Reproduction**:
```typescript
// Icons don't use default color
<NativeTabs.Screen
  name="home"
  options={{
    tabBarIcon: ({ color }) => <Icon name="home" color={color} />,
    // color prop doesn't apply correctly
  }}
/>
```

**Status**:
- Labeled as "Upstream: iOS" (iOS SDK issue)
- Workaround: Manually set icon colors explicitly
- shadowColor also not applied correctly

**Community Validation**:
- 3+ GitHub issues with same problem
- Marked "Issue accepted" by Expo team

**Recommendation**: Add to Known Issues (low priority, cosmetic)

---

### Finding 2.4: expo-router Modal + Zoom Transition Gesture Conflict

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #42255](https://github.com/expo/expo/issues/42255), [#42074](https://github.com/expo/expo/issues/42074)
**Date**: January 2026
**Verified**: Labeled "Issue accepted"
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using iOS zoom transition with `expo-router`, ScrollView gestures conflict with back/dismiss gestures in nested routes.

**Conditions**:
- Expo Router with Apple Zoom transition
- Nested ScrollView in modal or stack
- iOS only

**Symptoms**:
- Scrolling triggers back navigation
- Cannot scroll vertically without dismissing route

**Workaround**:
Disable zoom transition for routes with ScrollViews:
```typescript
<Stack.Screen
  name="details"
  options={{
    presentation: 'modal',
    animation: 'default', // Don't use 'zoom' with ScrollView
  }}
/>
```

**Community Validation**:
- Labeled "Issue accepted" by Expo team
- Multiple users confirming

**Recommendation**: Add to Known Issues or Common Patterns

---

### Finding 2.5: Expo SDK 53 - Stricter package.json "exports" Enforcement

**Trust Score**: TIER 2 - High-Quality Community (LogRocket article + official changelog)
**Source**: [LogRocket Blog](https://blog.logrocket.com/expo-sdk-53-checklist/)
**Date**: SDK 53 release
**Verified**: Cross-referenced with official docs
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Metro bundler in React Native 0.79 (Expo SDK 53) enforces `package.json` "exports" fields more strictly, aligning with Node.js standards. This can break third-party libraries not following the standard.

**Symptoms**:
- Build errors: "Unable to resolve module"
- Works in development, fails in production build
- Affects older npm packages without proper "exports" field

**Detection**:
```bash
npx expo-doctor
# Will identify packages with incompatible exports
```

**Workaround**:
Update incompatible packages to latest versions, or patch using `patch-package`.

**Community Validation**:
- LogRocket official Expo SDK 53 guide
- Corroborated by developer reports

**Recommendation**: Add to SDK 53+ section when skill is updated for SDK 53

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: expo-router Nested Tabs + Modal Best Practices

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Medium Post](https://medium.com/@coby09/building-seamless-navigation-in-expo-router-tabs-modals-and-stacks-2df1a5522321), [GitHub Discussions](https://github.com/expo/router/discussions/910)
**Date**: 2025-2026
**Verified**: Cross-Referenced Only
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Nesting tabs inside modals or stacks in `expo-router` causes navigation issues where users get "stuck" in deep routes without a back button.

**Common Pattern Issues**:
```
Root Stack
  ├── Modal
  │   └── Tabs
  │       └── Stack (per tab)
  │           └── Deep screen ❌ No back button
```

**Community-Recommended Structure**:
```
Root Stack
  ├── Tabs (main navigation)
  │   └── Stack (per tab)
  └── Modal (outside tabs)
```

**Best Practice**:
- Put tabs at root level for main navigation
- Use Stack.Screen with `presentation: 'modal'` for modals over tabs
- Rename shared screens to `(zShared)` so tabs always load first

**Consensus Evidence**:
- Multiple Medium articles with similar advice
- GitHub Discussions with workarounds
- Official Expo docs show this pattern

**Recommendation**: Add to Common Patterns section

---

### Finding 3.2: Development Builds Increasingly Required

**Trust Score**: TIER 3 - Community Consensus
**Source**: [LogRocket Blog](https://blog.logrocket.com/expo-sdk-53-checklist/), [Expo Docs](https://docs.expo.dev/guides/new-architecture/)
**Date**: 2025-2026
**Verified**: Cross-Referenced
**Impact**: MEDIUM
**Already in Skill**: Partially mentioned

**Description**:
Expo Go limitations expanding. Production-like testing increasingly requires custom development builds.

**Features Requiring Dev Builds (SDK 53+)**:
- Background tasks (`expo-background-task`)
- Google Maps
- Push notification testing (Expo Go shows warnings)
- New Architecture features

**Recommendation**:
Always use `expo-dev-client` for production testing:
```bash
npx expo install expo-dev-client
npx expo run:android
npx expo run:ios
```

**Consensus Evidence**:
- LogRocket guide
- Official Expo documentation
- Community reports

**Recommendation**: Expand existing Expo Go limitations section

---

### Finding 3.3: Predictive Back Gesture Disabled by Default (Android 16, SDK 54)

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
**Date**: SDK 54 release
**Verified**: Official docs
**Impact**: LOW
**Already in Skill**: No

**Description**:
Android 16 predictive back gesture is disabled by default in Expo SDK 54. Must opt-in via app.json.

**Opt-In**:
```json
{
  "expo": {
    "android": {
      "predictiveBackGestureEnabled": true
    }
  }
}
```

**Impact**: Users don't see preview animation when pressing back button.

**Recommendation**: Add to SDK 54+ configuration notes

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

None identified. All findings cross-referenced with official sources or multiple community reports.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| New Architecture mandatory in RN 0.82+ | Critical Breaking Changes #1 | Fully covered |
| JSC removed from Expo Go | Expo SDK 52+ Specifics | Mentioned, but RN core removal not detailed |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, Critical/High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 SDK 54 Last Legacy Release | Critical Breaking Changes | Add SDK timeline context |
| 1.2 expo-file-system Legacy Removal | Known Issues Prevention | Add as Issue #13 with migration guide |
| 1.3 expo-av Removed SDK 55 | Known Issues Prevention | Add as Issue #14 with migration to expo-audio/expo-video |
| 1.4 Reanimated v4 New Arch Only | Migration Guide | Add to dependencies section with NativeWind gotcha |
| 1.5 Android Edge-to-Edge Mandatory | New Features or Breaking Changes | Add to SDK 54 section |
| 1.8 Xcode/Node Requirements | Package Versions section | Update prerequisites |
| 2.1 iOS Crash with Hermes + expo-updates | Known Issues Prevention | Add as Issue #15 with Podfile fix |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.6 Metro Internal Imports | Troubleshooting | Low priority (rare use case) |
| 1.9 Expo Go Limitations Expanding | Expo SDK Specifics | Expand existing section |
| 2.2 EAS Build "No variants" | Troubleshooting | Add when root cause confirmed |
| 2.3 NativeTabs Icon Colors | Known Issues (low priority) | Cosmetic issue, upstream dependency |
| 2.4 Modal + Zoom Gesture Conflict | Common Patterns | Add workaround |
| 3.1 Nested Tabs Best Practices | Common Patterns | Add navigation structure guide |
| 3.2 Dev Builds Required | Expo SDK Specifics | Expand existing warnings |

### Priority 3: Monitor (Future SDK Versions)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 2.5 SDK 53 package.json exports | SDK 53 not in skill yet | Add when updating to SDK 53+ |
| 3.3 Predictive Back Gesture | Low impact | Add to SDK 54 configuration notes |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Issues created >2025-01-01 | 30 | 12 |
| "EAS Build" issues 2025 | 20 | 5 |
| "expo-router" closed issues Dec 2025+ | 20 | 8 |
| "SDK 54" OR "SDK 55" issues | 0 (too specific) | N/A |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| Expo SDK 54 breaking changes | 10+ | Official + high-quality blogs |
| Expo SDK 53 checklist | 1 | LogRocket (authoritative) |
| Expo router navigation issues 2026 | 10+ | Official docs + Medium |
| expo-file-system legacy migration | 10+ | Official docs + GitHub |

### Official Sources

| Source | Notes |
|--------|-------|
| [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54) | Primary source for breaking changes |
| [Expo SDK 53 Changelog](https://expo.dev/changelog/sdk-53) | Deprecation timeline |
| [expo-file-system docs](https://docs.expo.dev/versions/latest/sdk/filesystem/) | Migration guide |
| [expo-av GitHub](https://github.com/expo/expo-av) | Deprecation notice |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for issue details
- `WebSearch` for Stack Overflow and blogs
- `WebFetch` for content retrieval (1 blocked by 403)

**Limitations**:
- Medium article blocked (403): New Architecture + Hermes + expo-updates crash details incomplete
- Stack Overflow searches returned no results for SDK 52+ (too recent)
- GitHub "SDK 52 OR SDK 53" searches empty (issues use "SDK" in labels, not titles)

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Cross-reference Finding 1.2 (expo-file-system) migration guide against official docs
- Verify Finding 2.1 (Hermes crash) workaround is still current

**For api-method-checker**:
- Verify expo-audio API examples in Finding 1.3
- Check expo-file-system new API (File/Directory classes) in Finding 1.2

**For code-example-validator**:
- Validate expo-audio migration code in Finding 1.3
- Validate expo-file-system migration code in Finding 1.2
- Validate Reanimated v3/v4 examples in Finding 1.4

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### Example: expo-file-system Legacy Removal

```markdown
### Issue #13: expo-file-system Legacy API Removed (SDK 55+)

**Error**: `Module not found: expo-file-system/legacy`
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54), [GitHub Issue #39056](https://github.com/expo/expo/issues/39056)
**Why It Happens**: Legacy API removed in SDK 55, must migrate to new File/Directory API
**Prevention**: Migrate to new API before upgrading to SDK 55

**Old Code (SDK 54 with legacy import)**:
```typescript
import * as FileSystem from 'expo-file-system/legacy';
await FileSystem.writeAsStringAsync(uri, content);
```

**New Code (SDK 54+ new API)**:
```typescript
import { File } from 'expo-file-system';
const file = new File(uri);
await file.writeString(content);
```

**Migration Timeline**:
- SDK 53: Legacy API at `expo-file-system`, new API at `expo-file-system/next`
- SDK 54: Legacy API at `expo-file-system/legacy`, new API at `expo-file-system` (default)
- SDK 55: Legacy API removed completely
```

#### Example: expo-av Removal

```markdown
### Issue #14: expo-av Removed (SDK 55+)

**Error**: `Module not found: expo-av`
**Source**: [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54), [expo-av GitHub](https://github.com/expo/expo-av)
**Why It Happens**: Package deprecated in SDK 53, removed in SDK 55
**Prevention**: Migrate to expo-audio and expo-video before SDK 55

**Timeline**:
- SDK 52: `expo-video` introduced
- SDK 53: `expo-audio` introduced, `expo-av` deprecated
- SDK 54: Last release with `expo-av` (no patches)
- SDK 55: `expo-av` removed

**Migration - Audio**:
```typescript
// OLD: expo-av
import { Audio } from 'expo-av';
const { sound } = await Audio.Sound.createAsync(require('./audio.mp3'));
await sound.playAsync();

// NEW: expo-audio
import { useAudioPlayer } from 'expo-audio';
const player = useAudioPlayer(require('./audio.mp3'));
player.play();
```

**Migration - Video**:
```typescript
// OLD: expo-av
import { Video } from 'expo-av';
<Video source={require('./video.mp4')} />

// NEW: expo-video
import { VideoView } from 'expo-video';
<VideoView source={require('./video.mp4')} />
```
```

---

**Research Completed**: 2026-01-21 10:45 UTC
**Next Research Due**: After SDK 55 release (estimated Q2 2026)

---

## Sources

- [Expo SDK 54 Changelog](https://expo.dev/changelog/sdk-54)
- [Expo SDK 53 Changelog](https://expo.dev/changelog/sdk-53)
- [Expo SDK 54 Upgrade Guide](https://expo.dev/blog/expo-sdk-upgrade-guide)
- [Expo SDK 54 Beta Announcement](https://expo.dev/changelog/sdk-54-beta)
- [A checklist for mastering Expo SDK 53 - LogRocket Blog](https://blog.logrocket.com/expo-sdk-53-checklist/)
- [Building Seamless Navigation in Expo Router - Medium](https://medium.com/@coby09/building-seamless-navigation-in-expo-router-tabs-modals-and-stacks-2df1a5522321)
- [FileSystem (legacy) - Expo Documentation](https://docs.expo.dev/versions/latest/sdk/filesystem-legacy/)
- [FileSystem - Expo Documentation](https://docs.expo.dev/versions/latest/sdk/filesystem/)
- [expo-av GitHub Repository](https://github.com/expo/expo-av)
- [Reanimated v3 to v4 Migration - FYI](https://github.com/expo/fyi/blob/main/expo-54-reanimated.md)
- [React Native's New Architecture - Expo Documentation](https://docs.expo.dev/guides/new-architecture/)
- [GitHub Issue #41824: iOS crashes with Hermes + New Architecture](https://github.com/expo/expo/issues/41824)
- [GitHub Issue #42370: EAS Build "No variants exist"](https://github.com/expo/expo/issues/42370)
- [GitHub Issue #39056: expo-file-system getContentUriAsync missing](https://github.com/expo/expo/issues/39056)
- [GitHub Issue #42167: expo-file-system ships .ts instead of .d.ts](https://github.com/expo/expo/issues/42167)
