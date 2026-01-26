#!/bin/bash
# Install agents from skill bundles to ~/.claude/agents/
# Usage: ./scripts/install-skill-agents.sh [bundle-name]
# Example: ./scripts/install-skill-agents.sh design
#          ./scripts/install-skill-agents.sh all

set -e

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/skills"
USER_AGENTS_DIR="$HOME/.claude/agents"

# Define bundles and their skills
declare -A BUNDLES
BUNDLES[design]="accessibility color-palette favicon-gen icon-design image-gen responsive-images seo-meta tailwind-patterns"
BUNDLES[cloudflare]="cloudflare-worker-base cloudflare-d1 cloudflare-r2 cloudflare-kv cloudflare-workers-ai cloudflare-vectorize cloudflare-queues cloudflare-workflows cloudflare-durable-objects cloudflare-agents cloudflare-mcp-server cloudflare-turnstile cloudflare-hyperdrive cloudflare-images cloudflare-browser-rendering cloudflare-python-workers"
BUNDLES[ai]="ai-sdk-core ai-sdk-ui openai-api openai-agents openai-assistants openai-responses google-gemini-api google-gemini-embeddings claude-api claude-agent-sdk elevenlabs-agents"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [bundle-name|all|list]"
    echo ""
    echo "Commands:"
    echo "  list              List available bundles and their agents"
    echo "  all               Install agents from ALL skills"
    echo "  <bundle-name>     Install agents from specific bundle"
    echo ""
    echo "Available bundles:"
    for bundle in "${!BUNDLES[@]}"; do
        echo "  - $bundle"
    done
    echo ""
    echo "Examples:"
    echo "  $0 design         # Install design bundle agents"
    echo "  $0 cloudflare     # Install cloudflare bundle agents"
    echo "  $0 all            # Install all agents from all skills"
    exit 1
}

list_bundles() {
    echo -e "${BLUE}Available bundles and their agents:${NC}"
    echo ""
    for bundle in "${!BUNDLES[@]}"; do
        echo -e "${GREEN}$bundle:${NC}"
        for skill in ${BUNDLES[$bundle]}; do
            agents_dir="$SKILLS_DIR/$skill/agents"
            if [[ -d "$agents_dir" ]]; then
                for agent in "$agents_dir"/*.md; do
                    if [[ -f "$agent" ]]; then
                        agent_name=$(basename "$agent" .md)
                        echo "  - $agent_name (from $skill)"
                    fi
                done
            fi
        done
        echo ""
    done
}

install_agents_from_skill() {
    local skill="$1"
    local agents_dir="$SKILLS_DIR/$skill/agents"

    if [[ -d "$agents_dir" ]]; then
        for agent in "$agents_dir"/*.md; do
            if [[ -f "$agent" ]]; then
                agent_name=$(basename "$agent")
                cp "$agent" "$USER_AGENTS_DIR/$agent_name"
                echo -e "  ${GREEN}✓${NC} Installed: $agent_name (from $skill)"
            fi
        done
    fi
}

install_bundle() {
    local bundle="$1"

    if [[ -z "${BUNDLES[$bundle]}" ]]; then
        echo -e "${YELLOW}Unknown bundle: $bundle${NC}"
        echo "Available bundles: ${!BUNDLES[*]}"
        exit 1
    fi

    echo -e "${BLUE}Installing agents from '$bundle' bundle...${NC}"
    echo ""

    local count=0
    for skill in ${BUNDLES[$bundle]}; do
        install_agents_from_skill "$skill"
    done

    echo ""
    echo -e "${GREEN}Done!${NC} Restart Claude Code to use the new agents."
}

install_all() {
    echo -e "${BLUE}Installing agents from ALL skills...${NC}"
    echo ""

    for skill_dir in "$SKILLS_DIR"/*/; do
        skill=$(basename "$skill_dir")
        install_agents_from_skill "$skill"
    done

    echo ""
    echo -e "${GREEN}Done!${NC} Restart Claude Code to use the new agents."
}

# Main
if [[ $# -eq 0 ]]; then
    usage
fi

# Ensure target directory exists
mkdir -p "$USER_AGENTS_DIR"

case "$1" in
    list)
        list_bundles
        ;;
    all)
        install_all
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        install_bundle "$1"
        ;;
esac
