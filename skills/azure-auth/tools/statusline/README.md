# Claude Code Custom Status Line

A custom status line for Claude Code CLI that displays real-time context tracking, git information, and session metrics with a beautiful brick visualization.

![ContextBricks Status Line](assets/context-bricks.png)

## ✨ Features

### Real-Time Context Tracking
- **Official percentage fields** (Claude Code 2.1.6+) for most accurate display
- **Fallback calculation** using `current_usage` API (Claude Code 2.0.70+)
- **Brick visualization** showing context usage at a glance
- **Session duration** - track how long you've been working
- **Session cost** - API users see spending (hidden for Max subscribers)

### Workspace Context
- **Working directory** (tilde-compressed, e.g., `~/Documents/project`)

### Git Integration
- Current **repo name and branch**
- Latest **commit hash and message**
- **GitHub repo** name (if remote exists)
- **Status indicators**:
  - `*` = uncommitted changes
  - `↑3` = ahead of remote by 3 commits
  - `↓2` = behind remote by 2 commits

### Session Metrics
- **Model name** (Sonnet 4.5, Opus 4, Haiku, etc.)
- **Lines changed** this session (+added/-removed)
- **Free space** remaining in context
- **Duration** - time spent in session
- **Cost** - API usage cost (only shown if > $0)

## 📦 Installation

### Quick Install (Recommended)

**Via npm** (easiest - one command!):
```bash
npx contextbricks
```
No need for `init` - it runs the installer automatically!

**Or from source**:
```bash
cd tools/statusline
./install.sh
```

The installer will:
1. Check dependencies (jq, git)
2. Back up existing status line configuration
3. Install the script to `~/.claude/statusline.sh`
4. Update `~/.claude/settings.json`

**NPM Package**: [contextbricks](https://www.npmjs.com/package/contextbricks) - Install with one command!

### Manual Install

1. Copy the script:
   ```bash
   cp statusline.sh ~/.claude/statusline.sh
   chmod +x ~/.claude/statusline.sh
   ```

2. Update `~/.claude/settings.json`:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "/home/YOUR_USERNAME/.claude/statusline.sh",
       "padding": 0
     }
   }
   ```

3. Restart Claude Code

## 🎨 What It Looks Like

### Line 1: Path + Git + Model + Changes
```
[Sonnet 4.5] ~/Documents/claude-skills claude-skills:main [5f2ce67] Remove auth-js skill | jezweb/claude-skills *↑2 | +145/-23
```

### Line 2: Context Bricks + Duration + Cost
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

- **jq** - JSON processor
  ```bash
  sudo apt install jq  # Ubuntu/Debian
  brew install jq      # macOS
  ```

- **git** (optional) - For git info display
  ```bash
  sudo apt install git
  ```

## 📖 How It Works

### Context Tracking (v3.3.0+)

**Claude Code 2.1.6+** provides pre-calculated percentage fields for the most accurate display:
```json
{
  "context_window": {
    "context_window_size": 200000,
    "used_percentage": 43.5,
    "remaining_percentage": 56.5
  }
}
```

The status line uses these official percentages directly, avoiding any calculation drift.

### Fallback: Token Calculation (v2.0.70+)

For Claude Code 2.0.70 - 2.1.5 without percentage fields, falls back to `current_usage`:
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

Calculates as:
```
used_tokens = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
```

### Older Versions

For Claude Code < 2.0.70, the status line shows 0% until data becomes available.

### Git Information

Queries git commands in the current workspace:
- `git rev-parse --show-toplevel` - Repo name
- `git branch --show-current` - Current branch
- `git rev-parse --short HEAD` - Commit hash
- `git log -1 --pretty=%s` - Commit message
- `git status --porcelain` - Uncommitted changes
- `git rev-list --count` - Ahead/behind tracking

## 🐛 Troubleshooting

### Status line shows 0% (0k/200k tokens)

**Cause**: No context data available (new session) or Claude Code < 2.0.70

**Debug**:
```bash
# Check if jq is installed
which jq

# Test with percentage fields (2.1.6+)
echo '{"context_window":{"context_window_size":200000,"used_percentage":43.5,"remaining_percentage":56.5},"model":{"display_name":"Sonnet 4.5"},"workspace":{"current_dir":"'"$PWD"'"},"cost":{"total_duration_ms":300000}}' | ~/.claude/statusline.sh

# Test with current_usage data (2.0.70 - 2.1.5)
echo '{"context_window":{"context_window_size":200000,"current_usage":{"input_tokens":50000,"cache_creation_input_tokens":3000,"cache_read_input_tokens":2000}},"model":{"display_name":"Sonnet 4.5"},"workspace":{"current_dir":"'"$PWD"'"},"cost":{"total_duration_ms":300000}}' | ~/.claude/statusline.sh
```

### Brick visualization looks wrong

**Cause**: Terminal color support or ANSI escape codes

**Fix**:
- Ensure your terminal supports 256 colors
- Check `$TERM` environment variable
- Try: `export TERM=xterm-256color`

### Git info not showing

**Cause**: Not in a git repository or git not installed

**Fix**:
```bash
# Check if in git repo
git rev-parse --git-dir

# Install git
sudo apt install git
```

## 🎛️ Customization

### Change Brick Count

Edit `statusline.sh` line ~156:
```bash
total_bricks=40  # Increase for more granular visualization
```

### Hide Git Status

Comment out lines ~85-88:
```bash
# if [[ -n "$git_status" ]]; then
#     line1+=" \033[1;31m$git_status\033[0m"
# fi
```

### Compact Mode (Single Line)

Comment out the second echo:
```bash
echo -e "$line1"
# echo -e "$brick_line"  # Disable context line
```

## 🗑️ Uninstallation

```bash
cd tools/statusline
./uninstall.sh
```

The uninstaller will:
1. Remove the status line script
2. Offer to restore settings.json from backup
3. Optionally delete backup files

Manual uninstall:
```bash
rm ~/.claude/statusline.sh
# Edit ~/.claude/settings.json and remove the "statusLine" section
```

## 📋 Changelog

### v3.4.0 (2026-01-13)
- **Working directory display** - Shows tilde-compressed path (e.g., `~/Documents/project`)
- **Official percentage fields** - Uses `used_percentage` and `remaining_percentage` (Claude Code 2.1.6+)
- **More accurate context display** - No calculation drift, uses official values directly
- **Backwards compatible** - Falls back to token calculation for older versions

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

### v1.0.0
- Initial release with transcript parsing and multi-colour breakdown

## 🤝 Contributing

Found a bug or have a feature request?

1. Open an issue: [github.com/jezweb/claude-skills/issues](https://github.com/jezweb/claude-skills/issues)
2. Submit a PR with improvements
3. Share your customizations!

## 📄 License

MIT License - See [LICENSE](../../LICENSE) file

## 🙏 Credits

- Inspired by [ccstatusline](https://github.com/sirmalloc/ccstatusline)
- Token parsing approach from [codelynx.dev](https://codelynx.dev/posts/calculate-claude-code-context)
- Built for the [claude-skills](https://github.com/jezweb/claude-skills) repository

## 📚 Related Resources

- [Claude Code Documentation](https://code.claude.com/docs)
- [Status Line API](https://code.claude.com/docs/en/statusline)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)

---

**Made with ❤️ for the Claude Code community**
