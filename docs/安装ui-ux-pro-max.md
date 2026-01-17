# 全局安装 CLI 工具
npm install -g uipro-cli

# 进入你的项目目录
cd /path/to/your/project

# 为指定 AI 助手安装技能
uipro init --ai claude      # Claude Code
uipro init --ai cursor      # Cursor
uipro init --ai windsurf    # Windsurf
uipro init --ai antigravity # Antigravity (.agent + .shared)
uipro init --ai copilot     # GitHub Copilot
uipro init --ai kiro        # Kiro
uipro init --ai all         # 所有 AI 助手


uipro versions              # 列出可用版本
uipro update                # 更新到最新版本
uipro init --version v1.0.0 # 安装指定版本