@echo off
echo ========================================
echo 上传项目到GitHub
echo ========================================
echo.

:: 检查git
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未安装Git
    echo 请下载: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [1/5] 输入GitHub仓库信息
echo.
set /p repo_name=仓库名称(如: wechat-kimi-bridge): 
set /p username=GitHub用户名: 

echo.
echo [2/5] 初始化Git仓库...
git init
git add .
git commit -m "Initial commit"

echo.
echo [3/5] 添加远程仓库...
git remote add origin https://github.com/%username%/%repo_name%.git

echo.
echo [4/5] 推送到GitHub...
git branch -M main
git push -u origin main

echo.
echo [5/5] 完成！
echo.
echo 现在可以:
echo 1. 访问 https://github.com/%username%/%repo_name%
echo 2. 点击 "<> Code" 按钮
echo 3. 选择 "Codespaces" 标签
echo 4. 点击 "Create codespace on main"
echo.
pause
