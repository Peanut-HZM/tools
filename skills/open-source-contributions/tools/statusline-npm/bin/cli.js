#!/usr/bin/env node

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const command = process.argv[2];
const scriptsDir = path.join(__dirname, '../scripts');

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
};

// Check for jq dependency
function checkDependencies() {
  const jqCheck = spawnSync('which', ['jq'], { encoding: 'utf-8' });
  if (jqCheck.status !== 0) {
    console.error(`${colors.red}❌ Error: jq is required but not installed.${colors.reset}`);
    console.error(`   ${colors.cyan}Install with:${colors.reset}`);
    console.error(`     sudo apt install jq      ${colors.yellow}# Ubuntu/Debian${colors.reset}`);
    console.error(`     brew install jq          ${colors.yellow}# macOS${colors.reset}`);
    console.error(`     yum install jq           ${colors.yellow}# RHEL/CentOS${colors.reset}`);
    process.exit(1);
  }

  const gitCheck = spawnSync('which', ['git'], { encoding: 'utf-8' });
  if (gitCheck.status !== 0) {
    console.warn(`${colors.yellow}⚠️  Warning: git not found. Git info will not be available.${colors.reset}`);
  }
}

// Display help
function showHelp() {
  console.log(`
${colors.cyan}🧱 ContextBricks${colors.reset} - Claude Code Status Line

${colors.green}Usage:${colors.reset}
  contextbricks init          Interactive install
  contextbricks install       Install status line
  contextbricks uninstall     Uninstall status line
  contextbricks --help        Show this help
  contextbricks --version     Show version

${colors.green}Quick Start:${colors.reset}
  npx contextbricks init

${colors.green}Features:${colors.reset}
  • Real-time context tracking from transcript files
  • Brick visualization showing token breakdown
  • Git integration (repo, branch, commit, status)
  • Model-aware context limits (200k for all models in Claude Code)
  • Session metrics (lines changed, free space)

${colors.green}More Info:${colors.reset}
  GitHub: https://github.com/jezweb/claude-skills/tree/main/tools/statusline
  Issues: https://github.com/jezweb/claude-skills/issues
`);
}

// Main command handler
function main() {
  switch (command) {
    case 'install':
    case 'init':
      checkDependencies();
      const installResult = spawnSync('bash', [path.join(scriptsDir, 'install.sh')], {
        stdio: 'inherit',
        env: { ...process.env, NPM_INSTALL: '1' }
      });
      process.exit(installResult.status || 0);
      break;

    case 'uninstall':
      const uninstallResult = spawnSync('bash', [path.join(scriptsDir, 'uninstall.sh')], {
        stdio: 'inherit',
        env: { ...process.env, NPM_INSTALL: '1' }
      });
      process.exit(uninstallResult.status || 0);
      break;

    case '--version':
    case '-v':
      const packageJson = require('../package.json');
      console.log(`contextbricks v${packageJson.version}`);
      break;

    case '--help':
    case '-h':
    case 'help':
      showHelp();
      break;

    default:
      if (command) {
        // Unknown command - show error + help
        console.error(`${colors.red}❌ Unknown command: ${command}${colors.reset}\n`);
        showHelp();
        process.exit(1);
      } else {
        // No command - run interactive install as default
        checkDependencies();
        const defaultInstallResult = spawnSync('bash', [path.join(scriptsDir, 'install.sh')], {
          stdio: 'inherit',
          env: { ...process.env, NPM_INSTALL: '1' }
        });
        process.exit(defaultInstallResult.status || 0);
      }
  }
}

main();
