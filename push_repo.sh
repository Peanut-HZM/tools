#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}      Git 智能提交工具 (Smart Push)     ${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. 执行代码更新
echo -e "${YELLOW}[1/3] 正在检查远程更新...${NC}"
if [ -f "./update_repo.sh" ]; then
    ./update_repo.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 代码更新失败，已终止提交操作。请先解决更新问题。${NC}"
        exit 1
    fi
else
    echo -e "${RED}[错误] 找不到 update_repo.sh 脚本，无法执行前置更新。${NC}"
    exit 1
fi

# 2. 检查本地变更
echo -e "${YELLOW}[2/3] 正在检查本地变更...${NC}"
STATUS=$(git status --porcelain)
if [ -z "$STATUS" ]; then
    echo -e "${GREEN}[提示] 本地没有需要提交的更改。${NC}"
    exit 0
fi

# 获取变更文件数量
FILE_COUNT=$(echo "$STATUS" | wc -l | xargs)
echo -e "${GREEN}检测到 ${FILE_COUNT} 个文件发生变更。${NC}"

# 3. 提交与推送
echo -e "${YELLOW}[3/3] 准备提交...${NC}"

# 获取提交信息
read -p "请输入提交信息 (Commit Message): " MSG
if [ -z "$MSG" ]; then
    MSG="Update code $(date +%Y-%m-%d)"
    echo -e "${YELLOW}未输入信息，使用默认: ${MSG}${NC}"
fi

# 批处理阈值
BATCH_LIMIT=200

if [ "$FILE_COUNT" -gt "$BATCH_LIMIT" ]; then
    echo -e "${YELLOW}警告: 变更文件数量 ($FILE_COUNT) 较多，建议分批提交以降低风险。${NC}"
    read -p "是否启用分批提交模式? (y/n) [默认: y]: " ENABLE_BATCH
    ENABLE_BATCH=${ENABLE_BATCH:-y}

    if [[ "$ENABLE_BATCH" == "y" ]]; then
        echo -e "${BLUE}>>> 启用分批模式 (每批 $BATCH_LIMIT 个文件) <<<${NC}"
        
        # 生成文件列表临时文件
        git status --porcelain | cut -c4- > .git_files_to_commit
        
        CURRENT_BATCH=1
        COUNTER=0
        PENDING_FILES=""
        
        while IFS= read -r FILE; do
            # 处理文件名中的引号 (简单处理)
            FILE="${FILE%\"}"
            FILE="${FILE#\"}"
            
            # 将文件添加到暂存区
            git add "$FILE"
            ((COUNTER++))
            
            # 达到批次限制，进行提交和推送
            if [ "$COUNTER" -eq "$BATCH_LIMIT" ]; then
                BATCH_MSG="$MSG (Batch $CURRENT_BATCH)"
                echo -e "${YELLOW}正在提交第 $CURRENT_BATCH 批...${NC}"
                
                if git commit -m "$BATCH_MSG"; then
                    echo -e "${YELLOW}正在推送第 $CURRENT_BATCH 批...${NC}"
                    if git push; then
                        echo -e "${GREEN}第 $CURRENT_BATCH 批推送成功！${NC}"
                    else
                        echo -e "${RED}第 $CURRENT_BATCH 批推送失败！请检查网络。${NC}"
                        rm .git_files_to_commit
                        exit 1
                    fi
                else
                     echo -e "${RED}第 $CURRENT_BATCH 批提交失败！${NC}"
                     rm .git_files_to_commit
                     exit 1
                fi
                
                # 重置计数器
                COUNTER=0
                ((CURRENT_BATCH++))
            fi
        done < .git_files_to_commit
        
        # 处理剩余文件
        if [ "$COUNTER" -gt 0 ]; then
            BATCH_MSG="$MSG (Batch $CURRENT_BATCH - Final)"
            echo -e "${YELLOW}正在提交最后一批...${NC}"
            git commit -m "$BATCH_MSG" && git push
        fi
        
        rm .git_files_to_commit
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}      所有批次提交完成！      ${NC}"
        echo -e "${GREEN}========================================${NC}"
        exit 0
    fi
fi

# 正常一次性提交模式
git add .
if git commit -m "$MSG"; then
    echo -e "${YELLOW}正在推送到远程仓库...${NC}"
    if git push; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}      提交并推送成功！      ${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo -e "${RED}[错误] 推送失败。可能是网络问题或远程拒绝。${NC}"
        echo -e "${YELLOW}建议: 尝试运行 ./update_repo.sh 再次更新，或检查 git push 错误信息。${NC}"
        exit 1
    fi
else
    echo -e "${RED}[错误] 提交失败。${NC}"
    exit 1
fi
