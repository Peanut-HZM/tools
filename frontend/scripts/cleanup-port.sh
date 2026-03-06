#!/bin/bash

# 清理占用指定端口的进程
# 用法：./cleanup-port.sh <port>

PORT=$1

if [ -z "$PORT" ]; then
    echo "错误：请指定端口号"
    echo "用法：./cleanup-port.sh <port>"
    exit 1
fi

# 查找占用端口的进程
PIDS=$(lsof -ti:$PORT 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "端口 $PORT 未被占用"
    exit 0
fi

echo "发现占用端口 $PORT 的进程：$PIDS"

# 只杀死当前项目相关的进程（通过检查进程命令行）
for PID in $PIDS; do
    # 获取进程信息
    PROC_INFO=$(ps -p $PID -o pid,command 2>/dev/null)

    # 检查是否是 node/vite 进程（前端开发服务器）
    if echo "$PROC_INFO" | grep -q "node.*vite\|vite.*node"; then
        echo "杀死进程 $PID (vite 开发服务器)"
        kill -9 $PID 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✓ 成功杀死进程 $PID"
        else
            echo "✗ 无法杀死进程 $PID"
        fi
    else
        echo "跳过进程 $PID (不是 vite 进程): $PROC_INFO"
    fi
done

echo "端口清理完成"
