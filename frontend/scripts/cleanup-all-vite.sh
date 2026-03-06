#!/bin/bash

# 清理所有 Vite 开发服务器进程
# 用法：./cleanup-all-vite.sh

echo "=== 清理所有 Vite 开发服务器进程 ==="

# 1. 查找并杀死当前项目目录下的 vite 进程
echo "扫描当前项目的 Vite 进程..."
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "项目根目录：$PROJECT_ROOT"

# 使用 pgrep 查找 vite 进程
VITE_PIDS=$(pgrep -f "vite" 2>/dev/null)

if [ -z "$VITE_PIDS" ]; then
    echo "✓ 没有发现运行中的 Vite 进程"
else
    for PID in $VITE_PIDS; do
        # 获取进程的工作目录
        PWD=$(lsof -p $PID 2>/dev/null | grep cwd | awk '{print $9}')

        # 检查是否是当前项目的 vite 进程
        if echo "$PWD" | grep -q "$PROJECT_ROOT"; then
            echo "杀死项目进程 $PID (路径：$PWD)"
            kill -9 $PID 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "✓ 成功杀死进程 $PID"
            fi
        else
            echo "跳过进程 $PID (不属于当前项目)"
        fi
    done
fi

# 2. 清理 5173-5199 范围内被占用的端口
echo ""
echo "=== 检查 5173-5199 端口范围内的占用情况 ==="
for PORT in $(seq 5173 5199); do
    PORT_PID=$(lsof -ti:$PORT 2>/dev/null)
    if [ -n "$PORT_PID" ]; then
        PROC_INFO=$(ps -p $PORT_PID -o pid,command 2>/dev/null)
        if echo "$PROC_INFO" | grep -q "node.*vite\|vite.*node"; then
            echo "清理端口 $PORT 的 Vite 进程 $PORT_PID"
            kill -9 $PORT_PID 2>/dev/null
        fi
    fi
done

echo ""
echo "✓ 清理完成！"
