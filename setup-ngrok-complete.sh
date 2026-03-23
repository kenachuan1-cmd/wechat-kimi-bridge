#!/bin/bash
# 完整的 ngrok 配置脚本

TOKEN=$1

if [ -z "$TOKEN" ]; then
    echo "用法: ./setup-ngrok-complete.sh <你的ngrok token>"
    exit 1
fi

echo "=== 安装 ngrok ==="

# 安装 ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list >/dev/null
sudo apt update && sudo apt install ngrok -y

echo ""
echo "=== 配置 ngrok ==="
ngrok config add-authtoken $TOKEN

echo ""
echo "=== 配置完成 ==="
echo "启动命令: ngrok http 8080"
echo ""
echo "启动后会显示公网URL，格式如:"
echo "  https://xxxx.ngrok-free.app"
