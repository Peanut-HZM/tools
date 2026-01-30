#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}      Git 强制推送工具 (Force Push)     ${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "${RED}警告: 此操作将强制覆盖远程仓库的内容，远程的变更将会丢失！${NC}"
echo -e "${YELLOW}当前操作将以本地代码为准，忽略远程仓库的变更。${NC}"

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}检测到本地有未提交的更改，正在提交...${NC}"
    git add .
    read -p "请输入提交信息 (Commit Message): " MSG
    if [ -z "$MSG" ]; then
        MSG="Force update $(date +%Y-%m-%d)"
        echo -e "${YELLOW}使用默认提交信息: ${MSG}${NC}"
    fi
    git commit -m "$MSG"
fi

echo -e "${YELLOW}正在强制推送到远程仓库...${NC}"
if git push -f origin master; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}      强制推送成功！      ${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}[错误] 强制推送失败。${NC}"
    exit 1
fi
