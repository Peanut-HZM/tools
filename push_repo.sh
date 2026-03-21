#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
BATCH_SIZE=${BATCH_SIZE:-500}
FORCE_REBASE=false
SKIP_REBASE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE_PUSH=true
            shift
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --no-rebase)
            SKIP_REBASE=true
            shift
            ;;
        --help|-h)
            echo -e "${BLUE}========================================${NC}"
            echo -e "${BLUE}      Git 智能提交工具 (Smart Push)     ${NC}"
            echo -e "${BLUE}========================================${NC}"
            echo ""
            echo "用法：$0 [选项]"
            echo ""
            echo "选项:"
            echo "  --force, -f          强制推送（使用 --force-with-lease）"
            echo "  --batch-size N       每批次提交的文件数量（默认：500）"
            echo "  --no-rebase          跳过 rebase 直接推送"
            echo "  --help, -h           显示帮助信息"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}[错误] 未知参数：$1${NC}"
            echo -e "${YELLOW}使用 --help 查看帮助信息${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}      Git 智能提交工具 (Smart Push)     ${NC}"
echo -e "${BLUE}========================================${NC}"

# 获取当前分支
BRANCH=$(git branch --show-current)
if [ -z "$BRANCH" ]; then
    echo -e "${RED}[错误] 无法获取当前分支${NC}"
    exit 1
fi

echo -e "${GREEN}当前分支：${BRANCH}${NC}"

# 获取未推送的 commit 数量
get_unpushed_count() {
    local count=$(git rev-list --count HEAD..@{u} 2>/dev/null)
    echo "${count:-0}"
}

UNPUSHED_COUNT=$(get_unpushed_count)
echo -e "${GREEN}已提交未推送：${UNPUSHED_COUNT} 个 commit${NC}"

# 检查本地变更
echo -e "${YELLOW}正在检查本地变更...${NC}"
STATUS=$(git status --porcelain)
if [ -z "$STATUS" ]; then
    echo -e "${GREEN}未提交的变更：否${NC}"
    HAS_UNCOMMITTED=false
else
    echo -e "${GREEN}未提交的变更：是${NC}"
    HAS_UNCOMMITTED=true
fi

# 场景 1: 有未提交的变更
if [ "$HAS_UNCOMMITTED" = true ]; then
    # 获取变更文件数量
    FILE_COUNT=$(echo "$STATUS" | wc -l | xargs)
    echo -e "${GREEN}检测到 ${FILE_COUNT} 个文件发生变更${NC}"

    # 获取提交信息
    read -p "请输入提交信息 (Commit Message): " MSG
    if [ -z "$MSG" ]; then
        MSG="Update code $(date +%Y-%m-%d)"
        echo -e "${YELLOW}未输入信息，使用默认：${MSG}${NC}"
    fi

    echo -e "${YELLOW}确认提交并推送？(yes/no): ${NC}\c"
    read RESPONSE
    if [[ ! "$RESPONSE" =~ ^[Yy](es)?$ ]]; then
        echo -e "${YELLOW}取消操作${NC}"
        exit 0
    fi

    # 判断是否需要分批提交
    if [ "$FILE_COUNT" -gt "$BATCH_SIZE" ]; then
        echo -e "${YELLOW}警告：变更文件数量 ($FILE_COUNT) 超过批次大小 ($BATCH_SIZE)，启用分批提交模式${NC}"

        # 生成文件列表临时文件
        git status --porcelain | cut -c4- > .git_files_to_commit

        CURRENT_BATCH=1
        COUNTER=0
        TOTAL_FILES=$FILE_COUNT

        while IFS= read -r FILE; do
            # 处理文件名中的引号
            FILE="${FILE%\"}"
            FILE="${FILE#\"}"

            # 将文件添加到暂存区
            git add "$FILE"
            ((COUNTER++))

            # 达到批次限制，进行提交
            if [ "$COUNTER" -eq "$BATCH_SIZE" ]; then
                BATCH_MSG="$MSG (Batch $CURRENT_BATCH)"
                echo -e "${YELLOW}正在提交第 $CURRENT_BATCH 批...${NC}"

                if git commit -m "$BATCH_MSG"; then
                    echo -e "${GREEN}第 $CURRENT_BATCH 批提交成功${NC}"
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
            if git commit -m "$BATCH_MSG"; then
                echo -e "${GREEN}最后一批提交成功${NC}"
            else
                echo -e "${RED}最后一批提交失败！${NC}"
                rm .git_files_to_commit
                exit 1
            fi
        fi

        rm .git_files_to_commit
        echo -e "${GREEN}所有批次提交完成！${NC}"
    else
        # 正常一次性提交模式
        git add .
        if git commit -m "$MSG"; then
            echo -e "${GREEN}提交成功！${NC}"
        else
            echo -e "${RED}[错误] 提交失败${NC}"
            exit 1
        fi
    fi

    # 更新未推送计数
    UNPUSHED_COUNT=$(get_unpushed_count)
fi

# 场景 2: 有已提交未推送的 commit
if [ "$UNPUSHED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}检测到有 ${UNPUSHED_COUNT} 个未推送的提交${NC}"

    # 检查是否需要 rebase（远程有新提交）
    NEED_REBASE=false
    if [ "$SKIP_REBASE" = false ]; then
        GIT_STATUS=$(git status)
        if [[ "$GIT_STATUS" == *"Your branch is behind"* ]] || [[ "$GIT_STATUS" == *"can be fast-forwarded"* ]]; then
            NEED_REBASE=true
        fi
    fi

    if [ "$NEED_REBASE" = true ]; then
        echo -e "${YELLOW}远程仓库有新提交，需要先变基...${NC}"
        read -p "是否执行 git rebase? (yes/no): " RESPONSE
        if [[ "$RESPONSE" =~ ^[Yy](es)?$ ]]; then
            echo -e "${BLUE}正在变基到 origin/$BRANCH...${NC}"
            echo -e "${YELLOW}提示：如果遇到冲突，请解决后运行 'git rebase --continue'${NC}"
            echo -e "${YELLOW}      或运行 'git rebase --abort' 放弃变基${NC}"

            # 先 fetch 获取远程最新状态
            echo -e "${BLUE}正在获取远程状态...${NC}"
            git fetch origin

            # 执行 rebase
            if git rebase "origin/$BRANCH"; then
                echo -e "${GREEN}变基成功！${NC}"
            else
                echo -e "${RED}变基遇到冲突，请手动解决后运行 'git rebase --continue'${NC}"
                echo -e "${YELLOW}变基中止，请解决冲突后手动执行 git push${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}跳过 rebase，直接推送可能导致失败${NC}"
        fi
    fi

    # 推送到远程
    echo -e "${YELLOW}正在推送到远程仓库...${NC}"
    if [ "$FORCE_PUSH" = true ]; then
        PUSH_CMD="git push --force-with-lease origin $BRANCH"
    else
        PUSH_CMD="git push origin $BRANCH"
    fi

    if $PUSH_CMD; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}      提交并推送成功！      ${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo -e "${RED}[错误] 推送失败${NC}"
        echo -e "${YELLOW}建议：运行 'git fetch origin' 检查远程状态，或解决冲突后重试${NC}"
        exit 1
    fi
fi

# 场景 3: 没有变更，也没有未推送的提交
if [ "$HAS_UNCOMMITTED" = false ] && [ "$UNPUSHED_COUNT" -eq 0 ]; then
    echo -e "${GREEN}工作区是干净的，无需操作${NC}"
    exit 0
fi

# 显示最终状态
echo -e "${BLUE}当前仓库状态:${NC}"
git status

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}      ✓ 提交并推送完成！      ${NC}"
echo -e "${GREEN}========================================${NC}"
