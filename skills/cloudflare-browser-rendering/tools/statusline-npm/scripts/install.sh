#!/bin/bash

# Claude Code Status Line - Installation Script
# Installs custom status line with real-time context tracking and git info

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
STATUSLINE_SCRIPT="$SCRIPT_DIR/statusline.sh"
INSTALL_PATH="$HOME/.claude/statusline.sh"
SETTINGS_FILE="$HOME/.claude/settings.json"
BACKUP_SUFFIX=".backup-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Installing Claude Code Custom Status Line..."
echo ""

# Check dependencies
echo "Checking dependencies..."
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is required but not installed."
    echo "   Install with: sudo apt install jq"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "⚠️  Warning: git not found. Git info will not be available."
fi

echo "✅ Dependencies OK"
echo ""

# Backup existing statusline script if it exists
if [[ -f "$INSTALL_PATH" ]]; then
    echo "📦 Backing up existing status line script..."
    cp "$INSTALL_PATH" "${INSTALL_PATH}${BACKUP_SUFFIX}"
    echo "   Backup saved: ${INSTALL_PATH}${BACKUP_SUFFIX}"
fi

# Copy statusline script
echo "📝 Installing status line script..."
cp "$STATUSLINE_SCRIPT" "$INSTALL_PATH"
chmod +x "$INSTALL_PATH"
echo "   Installed: $INSTALL_PATH"
echo ""

# Update settings.json
if [[ -f "$SETTINGS_FILE" ]]; then
    echo "⚙️  Updating settings.json..."

    # Backup settings
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}${BACKUP_SUFFIX}"
    echo "   Backup saved: ${SETTINGS_FILE}${BACKUP_SUFFIX}"

    # Update statusLine config using jq
    jq '.statusLine = {
        "type": "command",
        "command": "'"$INSTALL_PATH"'",
        "padding": 0
    }' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

    echo "   Settings updated"
else
    echo "⚙️  Creating settings.json..."
    mkdir -p "$HOME/.claude"
    cat > "$SETTINGS_FILE" <<EOF
{
  "statusLine": {
    "type": "command",
    "command": "$INSTALL_PATH",
    "padding": 0
  }
}
EOF
    echo "   Settings created: $SETTINGS_FILE"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📊 Your status line will show:"
echo "   • Model name (Sonnet 4.5, Opus 4, etc.)"
echo "   • Git repo:branch [commit] message"
echo "   • GitHub repo name"
echo "   • Git status indicators (*uncommitted, ↑ahead, ↓behind)"
echo "   • Lines changed this session (+added/-removed)"
echo "   • Real-time context usage with brick visualization"
echo "   • Token breakdown (system, tools, MCP, memory, messages)"
echo ""
echo "🔄 Restart Claude Code to see your new status line!"
echo ""
echo "ℹ️  To uninstall: ./uninstall.sh"
echo "ℹ️  To restore backup: cp ${INSTALL_PATH}${BACKUP_SUFFIX} $INSTALL_PATH"
