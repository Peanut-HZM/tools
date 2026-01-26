# 🧱 ContextBricks

**Git-aware statusline for Claude Code CLI**

[![npm version](https://img.shields.io/npm/v/contextbricks.svg)](https://www.npmjs.com/package/contextbricks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A custom status line for Claude Code with rich git integration, context tracking, and session metrics.

## ✨ Features

- 🧱 **Brick visualization** showing context usage at a glance
- 🎯 **Accurate context tracking** using `current_usage` API (Claude Code 2.0.70+)
- 🔧 **Git integration**: repo:branch [commit] message | github-repo *↑↓
- ⏱️ **Session duration**: track how long you've been working
- 💰 **Session cost**: API users see spending (hidden for Max subscribers)
- 📊 **Session metrics**: model name, lines changed
- ⚡ **Zero config**: Auto-detects everything, just install and go

## 🚀 Quick Start

```bash
# Install and configure (one command!)
npx contextbricks

# Restart Claude Code to see your new status line
```

That's it! Your status line now shows real-time context tracking.

**Note**: Just `npx contextbricks` - no need for `init`! It runs the installer automatically.

## 📦 Installation Options

### Option 1: npx (Recommended - No Install)

```bash
npx contextbricks        # Runs installer automatically
```

### Option 2: Global Install

```bash
npm install -g contextbricks
contextbricks              # Also runs installer automatically
```

### Option 3: From Source

```bash
git clone https://github.com/jezweb/claude-skills
cd claude-skills/tools/statusline
./install.sh
```

## 🎨 What It Looks Like

**Line 1: Git + Model + Changes**
```
[Sonnet 4.5] claude-skills:main [5f2ce67] Remove auth-js skill | jezweb/claude-skills *↑2 | +145/-23
```

**Line 2: Context Bricks + Duration + Cost**
```
[■■■■■■■■■■■■■■■■■□□□□□□□□□□□□□□□□□□□□□□□] 43% (86k/200k) | 113k free | 12m45s | $0.87
```

For Max subscribers (no API cost):
```
[■■■■■■■■■■■■■■■■■□□□□□□□□□□□□□□□□□□□□□□□] 43% (86k/200k) | 113k free | 12m45s
```

![ContextBricks in action](assets/contextbricks02.png)

**Color Legend:**
- 🟦 Cyan = Used context
- ⬜ Dim hollow = Free space

## 🔧 Requirements

- **Node.js** ≥14 (you already have this for Claude Code)
- **jq** - JSON processor
  ```bash
  sudo apt install jq  # Ubuntu/Debian
  brew install jq      # macOS
  ```
- **git** (optional) - For git info display

## 📚 Commands

```bash
contextbricks               # Interactive install (default - recommended)
contextbricks init          # Interactive install (same as above)
contextbricks install       # Install status line (non-interactive)
contextbricks uninstall     # Uninstall status line
contextbricks --help        # Show help
contextbricks --version     # Show version
```

## 🎯 How It Works

### Claude Code 2.0.70+ (current_usage API)

ContextBricks v3.1 uses the **`current_usage` field** for accurate context tracking:

```json
{
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 45000,
      "cache_creation_input_tokens": 3000,
      "cache_read_input_tokens": 5000
    }
  }
}
```

This provides accurate current context usage that properly reflects the state after compaction.

### Older Versions (Fallback)

For Claude Code < 2.0.70 without `current_usage`, the status line shows 0% until data becomes available.

## 🔄 Updates

```bash
# If installed globally
npm update -g contextbricks

# If using npx
npx contextbricks@latest init
```

## 📋 Changelog

### v3.1.0 (2025-12-16)
- **Re-enabled context tracking** - Uses new `current_usage` API (Claude Code 2.0.70+)
- **Simplified code** - Removed complex compaction detection (~100 lines removed)
- **Accurate tracking** - `current_usage` provides proper context state after compaction

### v3.0.0 (2025-12-15)
- **Disabled context tracking** - Temporary due to Anthropic API bug #13783
- **Git-only mode** - Shows git info, duration, and cost while waiting for fix

### v2.1.0 (2025-12-13)
- **Compaction detection** - Shows accurate context usage after automatic compaction
- **📦 indicator** - Purple box emoji when context has been compacted
- **Hybrid calculation** - Uses cumulative tokens when normal, transcript parsing when compacted

### v2.0.0 (2025-12-11)
- **Native context_window support** - Uses Claude Code 2.0.65+ native data
- **Added session duration** - Shows time spent in session (e.g., `12m45s`)
- **Added session cost** - Shows API cost (only if > $0, hidden for Max subscribers)
- **Simplified visualization** - Single cyan colour for used context
- **Removed breakdown estimates** - No more estimated sys/tools/mcp/mem/msg
- **Backwards compatible** - Falls back to transcript parsing for older versions

### v1.0.x
- Initial release with transcript parsing and multi-colour breakdown

## 🐛 Troubleshooting

### Status line shows 0% (0k/200k tokens)

**Cause**: jq not installed, no context data available (new session), or Claude Code < 2.0.70

**Fix**:
```bash
# Check jq
which jq || sudo apt install jq

# Test with current_usage data (2.0.70+)
echo '{"context_window":{"context_window_size":200000,"current_usage":{"input_tokens":50000,"cache_creation_input_tokens":3000,"cache_read_input_tokens":2000}},"model":{"display_name":"Sonnet 4.5"},"workspace":{"current_dir":"'"$PWD"'"},"cost":{"total_duration_ms":300000}}' | ~/.claude/statusline.sh
```

### Git info not showing

**Cause**: Not in a git repository

**Fix**: Initialize git or cd into a git repo

### Brick visualization looks wrong

**Cause**: Terminal color support

**Fix**: Ensure your terminal supports 256 colors
```bash
export TERM=xterm-256color
```

## 🤝 Contributing

Found a bug or have a feature request?

- GitHub: https://github.com/jezweb/claude-skills
- Issues: https://github.com/jezweb/claude-skills/issues

## 📄 License

MIT License - See [LICENSE](./LICENSE)

## 🙏 Credits

- Part of the [claude-skills](https://github.com/jezweb/claude-skills) collection
- Inspired by [ccstatusline](https://github.com/sirmalloc/ccstatusline)
- Token parsing approach from [codelynx.dev](https://codelynx.dev/posts/calculate-claude-code-context)

## 📖 Full Documentation

For complete documentation, customization options, and advanced usage, see:
[Full Documentation](https://github.com/jezweb/claude-skills/tree/main/tools/statusline)

---

**Made with ❤️ for the Claude Code community**
