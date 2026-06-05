#!/bin/bash
set -e

EVIDENCE_DIR="/Users/huazhongmin/IdeaProjects/tools/docs/superpowers/e2e-evidence/2026-06-05-sql-executor"
mkdir -p "$EVIDENCE_DIR"

cd /Users/huazhongmin/IdeaProjects/tools

agent-browser open http://localhost:5178/tools/database-tool
agent-browser wait 3000
agent-browser screenshot "$EVIDENCE_DIR/02-default-state.png"

agent-browser eval "document.querySelector('[data-testid=drag-handle]')?.dispatchEvent(new MouseEvent('mousedown', {clientY: 300, bubbles: true}))"
agent-browser eval "window.dispatchEvent(new MouseEvent('mousemove', {clientY: 500, bubbles: true}))"
agent-browser eval "window.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}))"
agent-browser wait 200
agent-browser screenshot "$EVIDENCE_DIR/03-after-drag.png"

agent-browser open http://localhost:5178/tools/database-tool
agent-browser wait 3000
agent-browser screenshot "$EVIDENCE_DIR/04-persisted-height.png"

agent-browser click "[data-testid=fullscreen-toggle]"
agent-browser wait 200
agent-browser screenshot "$EVIDENCE_DIR/05-fullscreen.png"

agent-browser press Escape
agent-browser wait 200
agent-browser screenshot "$EVIDENCE_DIR/06-after-esc.png"

agent-browser eval "JSON.stringify(window.__errors || [])"
agent-browser screenshot "$EVIDENCE_DIR/07-console-check.png"

echo "E2E done: $EVIDENCE_DIR"
