#!/usr/bin/env python3
from weixin_bot import WeixinBot
import asyncio

async def main():
    bot = WeixinBot()
    # force=True 强制获取新二维码
    result = await bot._login(force=True)
    print("Login result:", result)

asyncio.run(main())
