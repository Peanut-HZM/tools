#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}      Git Rebase 更新工具      ${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. 检查是否在 git 仓库中
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo -e "${RED}[错误] 当前目录不是一个有效的 git 仓库。${NC}"
    exit 1
fi

# 获取当前分支名称
CURRENT_BRANCH=$(git symbolic-ref --short HEAD)
echo -e "${YELLOW}当前分支: ${CURRENT_BRANCH}${NC}"

# 2. 检查是否有未提交的更改
# git diff-index --quiet HEAD -- 返回 1 表示有变动
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}[提示] 检测到本地有未提交的更改。${NC}"
    echo -e "${YELLOW}正在尝试使用 --autostash 自动暂存更改...${NC}"
    AUTOSTASH_FLAG="--autostash"
else
    AUTOSTASH_FLAG=""
fi

echo -e "${YELLOW}正在执行: git pull --rebase $AUTOSTASH_FLAG ...${NC}"

# 3. 执行 git pull --rebase
if git pull --rebase $AUTOSTASH_FLAG; then
    echo -e "${GREEN}----------------------------------------${NC}"
    echo -e "${GREEN}[成功] 代码仓库已更新至最新状态！${NC}"
    echo -e "${GREEN}----------------------------------------${NC}"
else
    echo -e "${RED}----------------------------------------${NC}"
    echo -e "${RED}[失败] 更新过程中遇到问题（通常是代码冲突）。${NC}"
    echo -e "${RED}----------------------------------------${NC}"
    
    # 检查是否处于 rebase 过程中
    if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
        echo -e "${YELLOW}>>> 解决指南 <<<${NC}"
        echo -e "1. 请使用 IDE 或运行 ${BLUE}git status${NC} 查看冲突文件。"
        echo -e "2. 手动编辑文件解决冲突。"
        echo -e "3. 解决后，将文件标记为已解决: ${BLUE}git add <文件名>${NC}"
        echo -e "4. 继续执行变基: ${BLUE}git rebase --continue${NC}"
        echo -e ""
        echo -e "${YELLOW}>>> 放弃更新 <<<${NC}"
        echo -e "如果想放弃本次更新并回到更新前的状态，请运行: ${RED}git rebase --abort${NC}"
    else
        echo -e "${YELLOW}请检查网络连接或远程仓库权限。${NC}"
    fi
    exit 1
fi
