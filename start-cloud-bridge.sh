#!/bin/bash
# 启动云端桥接器完整流程

echo "=== 停止现有服务 ==="
pkill -f "python.*hybrid-http-server" 2>/dev/null
pkill -f "cloudflared" 2>/dev/null
sleep 2

echo ""
echo "=== 启动云端桥接器 ==="
echo "端口: 8081"
echo ""

# 启动桥接器（后台）
python wechat-cloud-bridge.py &
BRIDGE_PID=$!

echo "桥接器 PID: $BRIDGE_PID"
sleep 3

echo ""
echo "=== 启动 cloudflared 隧道 ==="
echo "转发: 8081 -> 公网"
echo ""
cloudflared tunnel --url http://localhost:8081
