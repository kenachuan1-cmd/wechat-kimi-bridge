#!/usr/bin/env python3
from weixin_bot import WeixinBot
import asyncio
bot = WeixinBot()
asyncio.run(bot._login(force=False))
