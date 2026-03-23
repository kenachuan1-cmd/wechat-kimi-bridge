#!/usr/bin/env python3
"""
显示微信登录二维码
"""

import asyncio
import sys
import os

# 尝试导入二维码生成器
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    from weixin_bot import WeixinBot
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("错误: 未安装 weixin-bot-sdk")
    print("请运行: pip install weixin-bot-sdk")
    sys.exit(1)


class QRBot:
    def __init__(self):
        self.bot = WeixinBot()
        self.qr_url = None
        
    def on_qr(self, url):
        """捕获二维码"""
        self.qr_url = url
        print("\n" + "="*70)
        print("请扫描下方二维码登录微信")
        print("="*70 + "\n")
        
        # 尝试显示ASCII二维码
        if QR_AVAILABLE:
            try:
                qr = qrcode.QRCode(
                    version=3,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=2,
                    border=2,
                )
                qr.add_data(url)
                qr.make(fit=True)
                qr.print_ascii(invert=True)
                print()
            except Exception as e:
                print(f"[无法生成二维码图形: {e}]")
        
        print(f"二维码链接: {url}")
        print("\n如果无法扫描，请复制上方链接到浏览器打开")
        print("="*70)
        print("等待扫码...")
        print("="*70 + "\n")


async def main():
    print("="*70)
    print("WeChat Login - QR Code Display")
    print("="*70)
    print()
    
    qr_bot = QRBot()
    
    # 尝试获取二维码
    print("正在连接微信服务器获取二维码...")
    print("(这可能需要几秒钟)\n")
    
    try:
        # 登录（会显示二维码）
        #  weixin_bot 会自动在控制台输出二维码URL
        result = await qr_bot.bot._login(force=False)
        
        if result:
            print("\n✓ 登录成功！")
            print("\n现在可以将此微信接入 Kimi Bridge 了")
        else:
            print("\n✗ 登录失败")
            
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n可能的原因:")
        print("1. 网络连接问题")
        print("2. 微信服务器暂时不可用")
        print("3. 账号被限制登录")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n已取消")
