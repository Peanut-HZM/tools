#!/bin/bash
# 安全重启前后端服务脚本

set -e

echo "=== 安全重启工具箱前后端服务 ==="

# 1. 只杀死特定的 uvicorn 进程（后端），不影响其他 Python 进程
echo "1. 停止后端服务..."
if pgrep -f "uvicorn.*19092" > /dev/null; then
    pkill -f "uvicorn.*19092" || true
    sleep 1
    echo "   ✅ 后端已停止"
else
    echo "   ℹ️ 后端未运行"
fi

# 2. 杀死 node 进程（前端）- 只匹配 Vite 开发服务器
echo "2. 停止前端服务..."
if pgrep -f "vite.*5178" > /dev/null; then
    pkill -f "vite.*5178" || true
    sleep 1
    echo "   ✅ 前端已停止"
else
    echo "   ℹ️ 前端未运行"
fi

# 3. 检查端口是否释放
echo "3. 检查端口..."
sleep 1
if lsof -i :19092 > /dev/null 2>&1; then
    echo "   ⚠️ 警告: 端口 19092 仍被占用"
else
    echo "   ✅ 端口 19092 已释放"
fi

if lsof -i :5178 > /dev/null 2>&1; then
    echo "   ⚠️ 警告: 端口 5178 仍被占用"
else
    echo "   ✅ 端口 5178 已释放"
fi

# 4. 启动后端
echo "4. 启动后端服务..."
cd /Users/huazhongmin/IdeaProjects/tools/backend
nohup uvicorn app.main:app --reload --port 19092 > /tmp/backend.log 2>&1 &
echo "   ✅ 后端启动中 (PID: $!)"

# 5. 启动前端
echo "5. 启动前端服务..."
cd /Users/huazhongmin/IdeaProjects/tools/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
echo "   ✅ 前端启动中 (PID: $!)"

echo ""
echo "=== 启动完成 ==="
echo "后端日志: tail -f /tmp/backend.log"
echo "前端日志: tail -f /tmp/frontend.log"
echo ""
echo "访问地址:"
echo "  - 前端: http://localhost:5178"
echo "  - 后端: http://127.0.0.1:19092"
