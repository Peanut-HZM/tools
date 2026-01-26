#!/usr/bin/env bash

# check-ai-models.sh - Check AI model references in skills
# Usage: ./scripts/check-ai-models.sh [skill-name] [--markdown REPORT_FILE]
#
# Checks for AI model references (OpenAI, Anthropic, Google, Cloudflare)
# Warns about deprecated or unavailable models
#
# Options:
#   --markdown FILE   Append results to markdown report file
#
# Exit code: Always 0 (info only, no failures)

# Don't use set -e - we want to always exit 0
set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

# Global counters
TOTAL_MODEL_REFS=0
CURRENT_MODELS=0
DEPRECATED_MODELS=0
UNKNOWN_MODELS=0

# Markdown report file (optional)
MARKDOWN_REPORT=""

# Parse arguments
SKILL_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --markdown)
            MARKDOWN_REPORT="$2"
            shift 2
            ;;
        *)
            SKILL_NAME="$1"
            shift
            ;;
    esac
done

# Function to append to markdown report
append_to_markdown() {
    local text="$1"
    if [ -n "$MARKDOWN_REPORT" ]; then
        echo "$text" >> "$MARKDOWN_REPORT"
    fi
}

# Model definitions (as of November 2025)
# Format: model_id|status|notes

declare -A OPENAI_MODELS=(
    ["gpt-5"]="current|Latest flagship model"
    ["gpt-5-mini"]="current|Fast, cost-efficient"
    ["gpt-5-nano"]="current|Smallest GPT-5 variant"
    ["gpt-4-turbo"]="current|Previous generation"
    ["gpt-4"]="deprecated|Use gpt-4-turbo or gpt-5"
    ["gpt-3.5-turbo"]="deprecated|Use gpt-5-mini instead"
)

declare -A ANTHROPIC_MODELS=(
    ["claude-sonnet-4-5"]="current|Latest Sonnet model"
    ["claude-haiku-4-5"]="current|Fast, cost-efficient"
    ["claude-sonnet-4-5-20250929"]="current|Dated model ID"
    ["claude-3-5-sonnet"]="deprecated|Use claude-sonnet-4-5"
    ["claude-3-opus"]="deprecated|Use claude-sonnet-4-5"
)

declare -A GOOGLE_MODELS=(
    ["gemini-3-pro-preview"]="current|Latest Gemini 3 (preview)"
    ["gemini-2.5-pro"]="current|Stable Pro model"
    ["gemini-2.5-flash"]="current|Fast model"
    ["gemini-2.5-flash-lite"]="current|Lightweight (not in CLI)"
    ["gemini-2.5-flash-image"]="current|Image-optimized"
    ["gemini-1.5-pro"]="deprecated|Use gemini-2.5-pro"
    ["gemini-1.5-flash"]="deprecated|Use gemini-2.5-flash"
)

declare -A CLOUDFLARE_MODELS=(
    ["@cf/meta/llama-3.1-8b-instruct"]="current|Llama 3.1 8B"
    ["@cf/meta/llama-3.1-70b-instruct"]="current|Llama 3.1 70B"
    ["@cf/mistral/mistral-7b-instruct"]="current|Mistral 7B"
    ["@cf/anthropic/claude-3-haiku"]="deprecated|Use claude-haiku-4-5"
)

# Function to check model status
check_model_status() {
    local model="$1"
    local provider="$2"

    case $provider in
        openai)
            if [[ -v OPENAI_MODELS["$model"] ]]; then
                echo "${OPENAI_MODELS[$model]}"
            else
                echo "unknown|Not in known models list"
            fi
            ;;
        anthropic|claude)
            if [[ -v ANTHROPIC_MODELS["$model"] ]]; then
                echo "${ANTHROPIC_MODELS[$model]}"
            else
                echo "unknown|Not in known models list"
            fi
            ;;
        google|gemini)
            if [[ -v GOOGLE_MODELS["$model"] ]]; then
                echo "${GOOGLE_MODELS[$model]}"
            else
                echo "unknown|Not in known models list"
            fi
            ;;
        cloudflare)
            if [[ -v CLOUDFLARE_MODELS["$model"] ]]; then
                echo "${CLOUDFLARE_MODELS[$model]}"
            else
                echo "unknown|Not in known models list"
            fi
            ;;
        *)
            echo "unknown|Unknown provider"
            ;;
    esac
}

# Function to check a single skill
check_skill_ai_models() {
    local skill_dir="$1"
    local skill_name="$2"
    local skill_file="$skill_dir/SKILL.md"

    if [ ! -f "$skill_file" ]; then
        return
    fi

    local found_models=false

    # Read file content
    local content=$(cat "$skill_file")

    # Check for OpenAI models
    local openai_models=$(echo "$content" | grep -oE 'gpt-[0-9](-[a-z-]+)?' | sort -u || true)

    # Check for Anthropic models
    local anthropic_models=$(echo "$content" | grep -oE 'claude-[a-z0-9-]+' | sort -u || true)

    # Check for Google models
    local google_models=$(echo "$content" | grep -oE 'gemini-[0-9.]+-[a-z-]+' | sort -u || true)

    # Check for Cloudflare models
    local cloudflare_models=$(echo "$content" | grep -oE '@cf/[a-z]+/[a-z0-9.-]+' | sort -u || true)

    # Only process if we found any models
    if [ -z "$openai_models" ] && [ -z "$anthropic_models" ] && [ -z "$google_models" ] && [ -z "$cloudflare_models" ]; then
        return
    fi

    found_models=true
    echo -e "${BLUE}Checking: $skill_name${NC}"

    # Start markdown section for this skill
    if [ -n "$MARKDOWN_REPORT" ]; then
        append_to_markdown ""
        append_to_markdown "### $skill_name"
        append_to_markdown ""
        append_to_markdown "| Model | Provider | Status | Notes |"
        append_to_markdown "|-------|----------|--------|-------|"
    fi

    # Process OpenAI models
    if [ -n "$openai_models" ]; then
        while IFS= read -r model; do
            if [ -z "$model" ]; then continue; fi

            ((TOTAL_MODEL_REFS++))
            local status_info=$(check_model_status "$model" "openai")
            local status="${status_info%%|*}"
            local notes="${status_info#*|}"

            case $status in
                current)
                    echo -e "  ${GREEN}✅${NC} $model (OpenAI) - $notes"
                    append_to_markdown "| $model | OpenAI | ✅ Current | $notes |"
                    ((CURRENT_MODELS++))
                    ;;
                deprecated)
                    echo -e "  ${YELLOW}⚠${NC}  $model (OpenAI) - DEPRECATED: $notes"
                    append_to_markdown "| $model | OpenAI | ⚠️ **Deprecated** | $notes |"
                    ((DEPRECATED_MODELS++))
                    ;;
                unknown)
                    echo -e "  ${YELLOW}?${NC}  $model (OpenAI) - $notes"
                    append_to_markdown "| $model | OpenAI | ❓ Unknown | $notes |"
                    ((UNKNOWN_MODELS++))
                    ;;
            esac
        done <<< "$openai_models"
    fi

    # Process Anthropic models
    if [ -n "$anthropic_models" ]; then
        while IFS= read -r model; do
            if [ -z "$model" ]; then continue; fi

            ((TOTAL_MODEL_REFS++))
            local status_info=$(check_model_status "$model" "anthropic")
            local status="${status_info%%|*}"
            local notes="${status_info#*|}"

            case $status in
                current)
                    echo -e "  ${GREEN}✅${NC} $model (Anthropic) - $notes"
                    append_to_markdown "| $model | Anthropic | ✅ Current | $notes |"
                    ((CURRENT_MODELS++))
                    ;;
                deprecated)
                    echo -e "  ${YELLOW}⚠${NC}  $model (Anthropic) - DEPRECATED: $notes"
                    append_to_markdown "| $model | Anthropic | ⚠️ **Deprecated** | $notes |"
                    ((DEPRECATED_MODELS++))
                    ;;
                unknown)
                    echo -e "  ${YELLOW}?${NC}  $model (Anthropic) - $notes"
                    append_to_markdown "| $model | Anthropic | ❓ Unknown | $notes |"
                    ((UNKNOWN_MODELS++))
                    ;;
            esac
        done <<< "$anthropic_models"
    fi

    # Process Google models
    if [ -n "$google_models" ]; then
        while IFS= read -r model; do
            if [ -z "$model" ]; then continue; fi

            ((TOTAL_MODEL_REFS++))
            local status_info=$(check_model_status "$model" "google")
            local status="${status_info%%|*}"
            local notes="${status_info#*|}"

            case $status in
                current)
                    echo -e "  ${GREEN}✅${NC} $model (Google) - $notes"
                    append_to_markdown "| $model | Google | ✅ Current | $notes |"
                    ((CURRENT_MODELS++))
                    ;;
                deprecated)
                    echo -e "  ${YELLOW}⚠${NC}  $model (Google) - DEPRECATED: $notes"
                    append_to_markdown "| $model | Google | ⚠️ **Deprecated** | $notes |"
                    ((DEPRECATED_MODELS++))
                    ;;
                unknown)
                    echo -e "  ${YELLOW}?${NC}  $model (Google) - $notes"
                    append_to_markdown "| $model | Google | ❓ Unknown | $notes |"
                    ((UNKNOWN_MODELS++))
                    ;;
            esac
        done <<< "$google_models"
    fi

    # Process Cloudflare models
    if [ -n "$cloudflare_models" ]; then
        while IFS= read -r model; do
            if [ -z "$model" ]; then continue; fi

            ((TOTAL_MODEL_REFS++))
            local status_info=$(check_model_status "$model" "cloudflare")
            local status="${status_info%%|*}"
            local notes="${status_info#*|}"

            case $status in
                current)
                    echo -e "  ${GREEN}✅${NC} $model (Cloudflare) - $notes"
                    append_to_markdown "| $model | Cloudflare | ✅ Current | $notes |"
                    ((CURRENT_MODELS++))
                    ;;
                deprecated)
                    echo -e "  ${YELLOW}⚠${NC}  $model (Cloudflare) - DEPRECATED: $notes"
                    append_to_markdown "| $model | Cloudflare | ⚠️ **Deprecated** | $notes |"
                    ((DEPRECATED_MODELS++))
                    ;;
                unknown)
                    echo -e "  ${YELLOW}?${NC}  $model (Cloudflare) - $notes"
                    append_to_markdown "| $model | Cloudflare | ❓ Unknown | $notes |"
                    ((UNKNOWN_MODELS++))
                    ;;
            esac
        done <<< "$cloudflare_models"
    fi

    if $found_models; then
        echo ""
    fi
}

# Initialize markdown report if specified
if [ -n "$MARKDOWN_REPORT" ]; then
    # Append to existing file or create new section
    if [ -f "$MARKDOWN_REPORT" ]; then
        echo "" >> "$MARKDOWN_REPORT"
        echo "---" >> "$MARKDOWN_REPORT"
        echo "" >> "$MARKDOWN_REPORT"
    fi
    echo "## AI Models" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
    echo "**Checked**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
fi

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  AI Model Checker${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Check if specific skill provided
if [ -n "$SKILL_NAME" ]; then
    SKILL_DIR="$SKILLS_DIR/$SKILL_NAME"

    if [ ! -d "$SKILL_DIR" ]; then
        echo -e "${RED}Error: Skill '$SKILL_NAME' not found${NC}"
        echo ""
        echo "Available skills:"
        ls -1 "$SKILLS_DIR" 2>/dev/null || echo "  (none found)"
        exit 0  # Still exit 0 (info only)
    fi

    check_skill_ai_models "$SKILL_DIR" "$SKILL_NAME"
    exit 0
fi

# Check all skills
TOTAL_SKILLS=0
SKILLS_WITH_MODELS=0

for skill_dir in "$SKILLS_DIR"/*/ ; do
    if [ ! -d "$skill_dir" ]; then
        continue
    fi

    skill_name=$(basename "$skill_dir")
    ((TOTAL_SKILLS++))

    # Check if skill references AI models
    before_count=$TOTAL_MODEL_REFS
    check_skill_ai_models "$skill_dir" "$skill_name"
    after_count=$TOTAL_MODEL_REFS

    if [ $after_count -gt $before_count ]; then
        ((SKILLS_WITH_MODELS++))
    fi
done

# Append summary to markdown
if [ -n "$MARKDOWN_REPORT" ]; then
    append_to_markdown ""
    append_to_markdown "---"
    append_to_markdown ""
    append_to_markdown "### AI Models Summary"
    append_to_markdown ""
    append_to_markdown "- **Total Model References**: $TOTAL_MODEL_REFS"
    append_to_markdown "- ✅ **Current Models**: $CURRENT_MODELS"
    append_to_markdown "- ⚠️ **Deprecated Models**: $DEPRECATED_MODELS"
    append_to_markdown "- ❓ **Unknown Models**: $UNKNOWN_MODELS"
    append_to_markdown ""
fi

# Terminal summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Total skills: $TOTAL_SKILLS"
echo "Skills with AI model references: $SKILLS_WITH_MODELS"
echo "Total model references: $TOTAL_MODEL_REFS"
echo ""
echo -e "${GREEN}✅${NC} Current models: $CURRENT_MODELS"
echo -e "${YELLOW}⚠${NC}  Deprecated models: $DEPRECATED_MODELS"
echo -e "${YELLOW}?${NC}  Unknown models: $UNKNOWN_MODELS"
echo ""

if [ $DEPRECATED_MODELS -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  WARNING: $DEPRECATED_MODELS deprecated model reference(s) found!"
    echo "  Consider updating to current models"
    echo ""
fi

if [ -n "$MARKDOWN_REPORT" ]; then
    echo -e "${GREEN}ℹ${NC}  Markdown report updated: $MARKDOWN_REPORT"
    echo ""
fi

echo -e "${GREEN}ℹ${NC}  This is informational only - no automatic updates performed"
echo -e "${GREEN}ℹ${NC}  Review deprecated models and update skills manually as needed"
echo ""

# Always exit 0 (informational only, never fail builds)
exit 0
