#!/usr/bin/env bash

# release-check.sh
# Automated release safety checks for GitHub releases
# Can be run standalone or invoked by /release command

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output functions
error() { echo -e "${RED}❌ $1${NC}" >&2; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Check counters
BLOCKERS=0
WARNINGS=0
RECOMMENDATIONS=0

# Results arrays
declare -a BLOCKER_LIST
declare -a WARNING_LIST
declare -a RECOMMENDATION_LIST

# Add result to tracking
add_blocker() { BLOCKER_LIST+=("$1"); ((BLOCKERS++)); }
add_warning() { WARNING_LIST+=("$1"); ((WARNINGS++)); }
add_recommendation() { RECOMMENDATION_LIST+=("$1"); ((RECOMMENDATIONS++)); }

# ========================================
# Phase 1: Critical Safety Checks
# ========================================

check_secrets() {
  echo ""
  echo "🔐 Checking for secrets..."

  # Check if gitleaks is installed
  if command -v gitleaks &> /dev/null; then
    info "Running gitleaks scan..."

    if gitleaks detect --no-git --source=. --verbose --exit-code=1 &> /tmp/gitleaks-output.txt; then
      success "No secrets detected by gitleaks"
    else
      error "Secrets detected by gitleaks!"
      cat /tmp/gitleaks-output.txt
      add_blocker "Secrets detected in files (see above)"
      return 1
    fi
  else
    warning "gitleaks not installed, skipping automated scan"
    info "To install: brew install gitleaks"
    add_recommendation "Install gitleaks for automated secret scanning"

    # Manual checks
    echo "  Running manual checks..."

    # Check for .env files
    if find . -name ".env*" -o -name "*.env" | grep -v node_modules | grep -q .; then
      warning ".env files detected (verify not committed)"
      find . -name ".env*" -o -name "*.env" | grep -v node_modules
      add_warning ".env files present (verify in .gitignore)"
    fi

    # Check wrangler.toml for potential secrets
    if [ -f "wrangler.toml" ]; then
      if grep -qi "api_key\|token\|secret\|password" wrangler.toml; then
        warning "Potential secrets in wrangler.toml"
        add_warning "Check wrangler.toml for hardcoded secrets"
      fi
    fi
  fi

  return 0
}

check_personal_artifacts() {
  echo ""
  echo "📝 Checking for personal artifacts..."

  ARTIFACTS_FOUND=()

  # Check SESSION.md
  if [ -f "SESSION.md" ]; then
    ARTIFACTS_FOUND+=("SESSION.md")
  fi

  # Check planning directory
  if [ -d "planning" ]; then
    ARTIFACTS_FOUND+=("planning/")
  fi

  # Check screenshots directory
  if [ -d "screenshots" ]; then
    ARTIFACTS_FOUND+=("screenshots/")
  fi

  # Check test files
  TEST_FILES=$(find . -name "test-*.js" -o -name "test-*.ts" -o -name "*.test.local.*" 2>/dev/null | head -10)
  if [ -n "$TEST_FILES" ]; then
    ARTIFACTS_FOUND+=("test-* files")
  fi

  if [ ${#ARTIFACTS_FOUND[@]} -gt 0 ]; then
    warning "Personal artifacts detected:"
    printf '  %s\n' "${ARTIFACTS_FOUND[@]}"
    add_warning "Personal artifacts present (SESSION.md, planning/, etc.)"
  else
    success "No personal artifacts detected"
  fi
}

check_remote_url() {
  echo ""
  echo "🌐 Checking git remote..."

  if ! git remote -v &> /dev/null; then
    error "No git remote configured"
    add_blocker "No git remote configured"
    return 1
  fi

  REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

  if [ -z "$REMOTE_URL" ]; then
    error "No origin remote configured"
    add_blocker "No origin remote set"
    return 1
  fi

  info "Remote URL: $REMOTE_URL"
  success "Git remote configured"
}

# ========================================
# Phase 2: Documentation Validation
# ========================================

check_license() {
  echo ""
  echo "📄 Checking LICENSE..."

  if [ -f "LICENSE" ] || [ -f "LICENSE.md" ] || [ -f "LICENSE.txt" ]; then
    LICENSE_TYPE=$(head -5 LICENSE* 2>/dev/null | grep -oi "MIT\|Apache\|GPL\|BSD" | head -1 || echo "Unknown")
    success "LICENSE present ($LICENSE_TYPE)"
  else
    error "LICENSE file missing"
    add_blocker "No LICENSE file (repository not legally open source)"
  fi
}

check_readme() {
  echo ""
  echo "📖 Checking README..."

  if [ ! -f "README.md" ]; then
    error "README.md missing"
    add_blocker "No README.md"
    return 1
  fi

  WORD_COUNT=$(wc -w < README.md)

  if [ "$WORD_COUNT" -lt 100 ]; then
    warning "README is very short ($WORD_COUNT words)"
    add_warning "README incomplete (< 100 words)"
  else
    success "README present ($WORD_COUNT words)"
  fi

  # Check for key sections
  MISSING_SECTIONS=()

  if ! grep -qi "## Install" README.md; then
    MISSING_SECTIONS+=("Installation")
  fi

  if ! grep -qi "## Usage\|## Example" README.md; then
    MISSING_SECTIONS+=("Usage")
  fi

  if ! grep -qi "## License" README.md; then
    MISSING_SECTIONS+=("License")
  fi

  if [ ${#MISSING_SECTIONS[@]} -gt 0 ]; then
    warning "README missing sections: ${MISSING_SECTIONS[*]}"
    add_warning "README missing: ${MISSING_SECTIONS[*]}"
  fi
}

check_contributing() {
  echo ""
  echo "🤝 Checking CONTRIBUTING.md..."

  # Count lines of code
  LOC=$(find . -name "*.ts" -o -name "*.js" -o -name "*.tsx" -o -name "*.jsx" | \
    grep -v node_modules | grep -v dist | grep -v build | \
    xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")

  if [ "$LOC" -gt 500 ]; then
    if [ -f "CONTRIBUTING.md" ]; then
      success "CONTRIBUTING.md present"
    else
      info "CONTRIBUTING.md missing (recommended for projects >500 LOC)"
      add_recommendation "Add CONTRIBUTING.md for contributor guidance"
    fi
  else
    info "Project small enough to skip CONTRIBUTING.md"
  fi
}

# ========================================
# Phase 3: Configuration Validation
# ========================================

check_gitignore() {
  echo ""
  echo "🚫 Checking .gitignore..."

  if [ ! -f ".gitignore" ]; then
    warning ".gitignore missing"
    add_warning "No .gitignore file"
    return 1
  fi

  MISSING_PATTERNS=()

  if ! grep -q "node_modules" .gitignore; then
    MISSING_PATTERNS+=("node_modules/")
  fi

  if ! grep -q "\.env" .gitignore; then
    MISSING_PATTERNS+=(".env*")
  fi

  if ! grep -q "\.log" .gitignore; then
    MISSING_PATTERNS+=("*.log")
  fi

  if ! grep -qE "dist/|build/" .gitignore; then
    MISSING_PATTERNS+=("dist/ or build/")
  fi

  if [ ${#MISSING_PATTERNS[@]} -gt 0 ]; then
    warning ".gitignore missing patterns: ${MISSING_PATTERNS[*]}"
    add_warning ".gitignore incomplete (missing: ${MISSING_PATTERNS[*]})"
  else
    success ".gitignore valid"
  fi
}

check_package_json() {
  echo ""
  echo "📦 Checking package.json..."

  if [ ! -f "package.json" ]; then
    info "No package.json (not a Node.js project)"
    return 0
  fi

  MISSING_FIELDS=()

  if ! grep -q "\"name\":" package.json; then
    MISSING_FIELDS+=("name")
  fi

  if ! grep -q "\"version\":" package.json; then
    MISSING_FIELDS+=("version")
  fi

  if ! grep -q "\"description\":" package.json; then
    MISSING_FIELDS+=("description")
  fi

  if ! grep -q "\"license\":" package.json; then
    MISSING_FIELDS+=("license")
  fi

  if ! grep -q "\"repository\":" package.json; then
    MISSING_FIELDS+=("repository")
  fi

  if [ ${#MISSING_FIELDS[@]} -gt 0 ]; then
    warning "package.json missing fields: ${MISSING_FIELDS[*]}"
    add_warning "package.json incomplete (missing: ${MISSING_FIELDS[*]})"
  else
    success "package.json complete"
  fi
}

check_branch() {
  echo ""
  echo "🌿 Checking git branch..."

  CURRENT_BRANCH=$(git branch --show-current)

  if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    warning "On $CURRENT_BRANCH branch (recommend using feature branch)"
    add_recommendation "Create release-prep branch for release changes"
  else
    success "On feature branch: $CURRENT_BRANCH"
  fi
}

# ========================================
# Phase 4: Quality Checks
# ========================================

check_build() {
  echo ""
  echo "🔨 Checking build..."

  if [ ! -f "package.json" ]; then
    info "No package.json (skipping build check)"
    return 0
  fi

  if grep -q "\"build\":" package.json; then
    info "Running build test..."

    if npm run build &> /tmp/build-output.txt; then
      success "Build succeeds"
    else
      warning "Build failed (see /tmp/build-output.txt for details)"
      add_warning "Build fails (non-blocking, but recommended to fix)"
    fi
  else
    info "No build script in package.json"
  fi
}

check_dependencies() {
  echo ""
  echo "🔍 Checking dependencies..."

  if [ ! -f "package.json" ]; then
    info "No package.json (skipping dependency check)"
    return 0
  fi

  if command -v npm &> /dev/null; then
    if npm audit --audit-level=high &> /tmp/audit-output.txt; then
      success "No critical dependency vulnerabilities"
    else
      warning "Dependency vulnerabilities detected"
      cat /tmp/audit-output.txt | grep -A 5 "high\|critical" || true
      add_warning "Dependency vulnerabilities (run: npm audit fix)"
    fi
  else
    info "npm not available (skipping dependency check)"
  fi
}

check_large_files() {
  echo ""
  echo "📏 Checking for large files..."

  LARGE_FILES=$(find . -type f -size +1M | grep -v node_modules | grep -v .git | grep -v dist | grep -v build | head -5)

  if [ -n "$LARGE_FILES" ]; then
    warning "Large files detected (>1MB):"
    echo "$LARGE_FILES" | while read -r file; do
      SIZE=$(du -h "$file" | cut -f1)
      echo "  $file ($SIZE)"
    done
    add_warning "Large files present (consider Git LFS or external storage)"
  else
    success "No large files detected"
  fi
}

# ========================================
# Report Generation
# ========================================

generate_report() {
  echo ""
  echo "═══════════════════════════════════════════════"
  echo "   RELEASE READINESS REPORT"
  echo "═══════════════════════════════════════════════"
  echo ""

  # Blockers
  if [ $BLOCKERS -gt 0 ]; then
    echo -e "${RED}🚫 BLOCKERS: $BLOCKERS${NC}"
    for item in "${BLOCKER_LIST[@]}"; do
      echo "  - $item"
    done
    echo ""
  fi

  # Warnings
  if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS: $WARNINGS${NC}"
    for item in "${WARNING_LIST[@]}"; do
      echo "  - $item"
    done
    echo ""
  fi

  # Recommendations
  if [ $RECOMMENDATIONS -gt 0 ]; then
    echo -e "${BLUE}ℹ️  RECOMMENDATIONS: $RECOMMENDATIONS${NC}"
    for item in "${RECOMMENDATION_LIST[@]}"; do
      echo "  - $item"
    done
    echo ""
  fi

  echo "═══════════════════════════════════════════════"

  # Final verdict
  if [ $BLOCKERS -gt 0 ]; then
    error "CANNOT RELEASE: $BLOCKERS blockers must be fixed"
    echo ""
    return 1
  elif [ $WARNINGS -gt 0 ]; then
    warning "CAN RELEASE WITH WARNINGS"
    info "Recommended to fix $WARNINGS warnings before release"
    echo ""
    return 0
  else
    success "READY TO RELEASE!"
    echo ""
    return 0
  fi
}

# ========================================
# Main Execution
# ========================================

main() {
  echo "═══════════════════════════════════════════════"
  echo "   RELEASE SAFETY CHECK"
  echo "═══════════════════════════════════════════════"

  # Check if in git repo
  if ! git rev-parse --git-dir &> /dev/null; then
    error "Not a git repository"
    exit 1
  fi

  # Run all checks
  check_secrets
  check_personal_artifacts
  check_remote_url

  check_license
  check_readme
  check_contributing

  check_gitignore
  check_package_json
  check_branch

  check_build
  check_dependencies
  check_large_files

  # Generate final report
  generate_report

  EXIT_CODE=$?

  if [ $EXIT_CODE -eq 0 ]; then
    if [ $WARNINGS -eq 0 ] && [ $RECOMMENDATIONS -eq 0 ]; then
      echo "🎉 All checks passed! Your project is ready for public release."
    else
      echo "📋 Review warnings/recommendations above before releasing."
    fi
  else
    echo "🛑 Fix blockers above before attempting release."
  fi

  exit $EXIT_CODE
}

# Run main if executed directly
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
  main "$@"
fi
