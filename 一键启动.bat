@echo off
chcp 65001 >nul
echo ========================================
echo WeChat-Kimi Bridge 一键启动
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未安装Python，请先安装Python 3.10+
    pause
    exit /b 1
)

:: 检查Kimi
kimi info >nul 2>&1
if errorlevel 1 (
    echo [错误] Kimi CLI未登录
    echo 请运行: kimi login
    pause
    exit /b 1
)

echo [1/3] 环境检查通过
echo.

:: 检查依赖
python -c "import aiohttp,weixin_bot,qrcode" >nul 2>&1
if errorlevel 1 (
    echo [2/3] 安装依赖...
    pip install aiohttp weixin-bot-sdk qrcode[pil] -q
) else (
    echo [2/3] 依赖已安装
)
echo.

echo [3/3] 启动微信桥接器...
echo.
echo 提示:
echo - 程序会显示二维码，请立即用微信扫描
echo - 扫码后点击"确认登录"
echo - 按Ctrl+C可停止程序
echo.
pause

echo.
echo 正在启动...
echo ========================================
python wechat-kimi-bridge-stable.py

echo.
echo 程序已停止
pause
