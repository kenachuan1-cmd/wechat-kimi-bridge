#!/bin/bash
# 在 Codespaces 中运行此脚本检查服务器状态

echo "=== 服务器状态检查 ==="
echo ""

# 检查进程
echo "[1] 检查 Python 进程:"
ps aux | grep python | grep -v grep

echo ""
echo "[2] 检查端口监听:"
netstat -tlnp 2>/dev/null | grep 8080 || ss -tlnp | grep 8080

echo ""
echo "[3] 本地测试:"
curl -s http://localhost:8080/status | head -20

echo ""
echo "[4] 端口转发信息:"
cat /workspaces/.codespaces/shared/port_forwarding.json 2>/dev/null || echo "端口转发文件不存在"

echo ""
echo "=== 完成 ==="
