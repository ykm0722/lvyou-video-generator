#!/bin/bash

echo "启动旅游视频生成平台..."

# 启动后端
echo "启动后端服务 (端口 8000)..."
cd backend
python3 -m uvicorn app:app --reload --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "启动前端服务 (端口 5173)..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 服务已启动！"
echo "前端: http://localhost:5173"
echo "后端: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
wait
