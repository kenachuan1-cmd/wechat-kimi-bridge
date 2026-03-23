#!/usr/bin/env python3
"""
刷新二维码并直接在终端显示
"""

import os
import sys
from datetime import datetime

# 尝试导入二维码生成器
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def display_qr_in_terminal(image_path: str):
    """从图片文件显示二维码为ASCII"""
    if not PIL_AVAILABLE:
        print("[错误] 未安装 PIL，请运行: pip install Pillow")
        return False
    
    try:
        img = Image.open(image_path)
        
        # 缩小图片以适应终端
        width, height = img.size
        aspect_ratio = height / width
        new_width = 40
        new_height = int(aspect_ratio * new_width * 0.5)
        
        img = img.resize((new_width, new_height))
        img = img.convert('L')  # 转为灰度
        
        print("")
        print("=" * 70)
        print("           [请用微信扫描下方二维码]")
        print("=" * 70)
        print("")
        
        # 打印二维码
        for y in range(new_height):
            line = ""
            for x in range(new_width):
                pixel = img.getpixel((x, y))
                if pixel < 128:
                    line += "##"
                else:
                    line += "  "
            print("  " + line)
        
        print("")
        print("=" * 70)
        mod_time = datetime.fromtimestamp(os.path.getmtime(image_path))
        print(f"[文件] {image_path}")
        print(f"[时间] {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("[注意] 二维码有效期约5分钟，请尽快扫描！")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[错误] 显示二维码失败: {e}")
        return False


def generate_new_qr():
    """生成新的二维码"""
    if not QR_AVAILABLE:
        print("[错误] 未安装 qrcode，请运行: pip install qrcode[pil]")
        return None
    
    try:
        from weixin_bot import WeixinBot
        
        print("[信息] 正在连接微信服务器获取二维码...")
        print("(这可能需要几秒钟)")
        
        bot = WeixinBot()
        
        # weixin_bot 会自动处理登录并显示二维码
        # 这里我们只是触发登录流程
        import asyncio
        
        async def do_login():
            return await bot._login(force=True)
        
        result = asyncio.run(do_login())
        
        if result:
            print("[成功] 登录成功！")
            return True
        else:
            print("[失败] 登录失败")
            return False
            
    except Exception as e:
        print(f"[错误] 获取二维码失败: {e}")
        print("")
        print("可能的原因:")
        print("1. 网络连接问题 (无法连接到微信服务器)")
        print("2. weixin-bot-sdk 未正确安装")
        print("3. 微信服务器暂时不可用")
        return False


def main():
    print("=" * 70)
    print("     WeChat-Kimi Bridge - 二维码终端显示")
    print("=" * 70)
    print("")
    
    # 查找现有的二维码
    qr_files = [f for f in os.listdir('.') if f.startswith('qr_') and f.endswith('.png')]
    
    if qr_files:
        # 按修改时间排序，获取最新的
        qr_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        latest_qr = qr_files[0]
        
        print(f"[信息] 找到现有二维码: {latest_qr}")
        print("")
        
        # 显示二维码
        if display_qr_in_terminal(latest_qr):
            print("")
            print("-" * 70)
            print("提示:")
            print("  - 如果二维码已过期，请删除 qr_*.png 文件后重新运行本工具")
            print("  - 或者直接运行: python wechat-kimi-bridge-stable.py")
            print("-" * 70)
    else:
        print("[信息] 未找到现有二维码，尝试获取新的...")
        print("")
        generate_new_qr()
    
    print("")
    print("=" * 70)
    print("使用步骤:")
    print("  1. 用手机微信扫描上方的二维码")
    print("  2. 点击'确认登录'")
    print("  3. 保持微信在线，然后运行: python wechat-kimi-bridge-stable.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
