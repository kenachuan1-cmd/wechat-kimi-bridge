#!/usr/bin/env python3
"""快速获取二维码"""
import asyncio
from weixin_bot import WeixinBot
import qrcode

async def main():
    bot = WeixinBot()
    
    print("Getting QR code...")
    # 获取二维码但不等待登录完成
    try:
        # 只获取二维码URL
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3"
            ) as resp:
                data = await resp.json()
                qr_url = data.get("qrcode_url", "")
                if qr_url:
                    print(f"\nQR_URL: {qr_url}\n")
                    # 生成二维码
                    qr = qrcode.QRCode(version=5, box_size=6, border=4)
                    qr.add_data(qr_url)
                    qr.make(fit=True)
                    qr.print_ascii(invert=True)
                    print(f"\n链接: {qr_url}")
                else:
                    print("Failed to get QR:", data)
    except Exception as e:
        print(f"Error: {e}")
        # 回退到正常登录
        print("\nTrying normal login...")
        await bot._login(force=False)

asyncio.run(main())
