#!/bin/bash
# 获取 Codespaces 端口转发 URL

echo "Codespaces 端口信息:"
echo ""

# 检查端口文件
if [ -f /workspaces/.codespaces/shared/port_forwarding.json ]; then
    echo "找到端口转发配置:"
    cat /workspaces/.codespaces/shared/port_forwarding.json 2>/dev/null || echo "无法读取"
fi

echo ""
echo "请在 VS Code 中查看:"
echo "1. 按 Ctrl+Shift+P"
echo "2. 输入: Ports: Focus on Ports View"
echo "3. 查看端口 8080 的转发 URL"
echo ""
echo "或者运行:"
echo "  cat /workspaces/.codespaces/shared/port_forwarding.json"
