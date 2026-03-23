#!/usr/bin/env python3
"""
快速启动脚本 - 自动检测环境并运行
"""

import subprocess
import sys
import os

def check_kimi():
    """检查 Kimi CLI"""
    result = subprocess.run(
        ["kimi", "info"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    return result.returncode == 0

def main():
    print("=" * 60)
    print("WeChat-Kimi Bridge 启动器")
    print("=" * 60)
    print()
    
    # 检查 Kimi
    print("[1/3] 检查 Kimi CLI...")
    if check_kimi():
        print("      OK - Kimi CLI 已就绪")
    else:
        print("      FAIL - 请先运行: kimi login")
        input("按回车退出...")
        return 1
    
    # 检查依赖
    print("[2/3] 检查依赖...")
    try:
        import aiohttp
        print("      OK - 依赖已安装")
    except ImportError:
        print("      安装依赖中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
        print("      OK - 依赖安装完成")
    
    # 选择模式
    print("[3/3] 选择运行模式:")
    print()
    print("  1. 测试模式 (Mock) - 命令行模拟微信")
    print("  2. 真实微信模式 - 需要扫码登录")
    print()
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        print()
        print("启动测试模式...")
        print("提示: 直接输入消息即可开始对话")
        print()
        subprocess.run([sys.executable, "wechat-kimi-bridge-stable.py", "--mock"])
    elif choice == "2":
        print()
        print("启动真实微信模式...")
        print("提示: 首次运行需要扫码登录")
        print()
        subprocess.run([sys.executable, "wechat-kimi-bridge-stable.py"])
    else:
        print("无效选择")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
