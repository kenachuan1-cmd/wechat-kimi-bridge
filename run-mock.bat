@echo off
echo ========================================
echo Kimi Bridge - 测试模式 (Mock)
echo ========================================
echo.
echo 此模式使用命令行模拟微信消息
echo 无需扫码登录真实微信
echo.
pause

python wechat-kimi-bridge-stable.py --mock

pause
