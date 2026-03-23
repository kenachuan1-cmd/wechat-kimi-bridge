#!/usr/bin/env python3
"""
微信桥接器 - 最终版 V2（正确使用 on_message + run）
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from aiohttp import web
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wechat-final.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WechatBridge:
    def __init__(self):
        self.bot = None
        self.local_url = os.environ.get('LOCAL_URL', 'http://localhost:8766')
        self.loop = None
        
    async def init_and_login(self):
        """初始化并登录"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("="*60)
            logger.info("初始化微信 Bot...")
            logger.info("="*60)
            
            self.bot = WeixinBot()
            
            # 设置消息回调
            logger.info("设置消息回调...")
            self.bot.on_message(self.on_message)
            
            # 登录
            logger.info("等待扫码登录...")
            result = await self.bot._login(force=False)
            
            if result:
                logger.info("✅ 登录成功！")
                return True
            return False
            
        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    def on_message(self, msg):
        """消息回调（在独立线程中被调用）"""
        logger.info(f"📩 收到消息回调: {msg}")
        
        # 由于回调在独立线程，需要使用 asyncio.run_coroutine_threadsafe
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.handle_message(msg), 
                self.loop
            )
    
    async def handle_message(self, msg):
        """异步处理消息"""
        try:
            # 解析消息
            text = msg.get('content', '') if isinstance(msg, dict) else str(msg)
            user_id = msg.get('from_user', {}).get('id', '') if isinstance(msg, dict) else ''
            user_name = msg.get('from_user', {}).get('name', '') if isinstance(msg, dict) else ''
            
            if not text:
                logger.warning("消息没有文本内容")
                return
            
            logger.info(f"[微信→本地] {user_name}: {text[:50]}...")
            
            # 构建消息
            message = {
                "msg_id": str(time.time()),
                "user_id": user_id,
                "user_name": user_name,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
            
            # 转发到本地
            await self.forward_to_local(message)
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
    
    async def forward_to_local(self, message):
        """转发到本地"""
        try:
            logger.info(f"转发到: {self.local_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.local_url}/receive",
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    result = await resp.json()
                    logger.info(f"本地响应: {result}")
                    
                    # 发送回复
                    if result.get('status') == 'ok' and result.get('response'):
                        await self.send_reply(message['user_id'], result['response'])
                        
        except Exception as e:
            logger.error(f"转发失败: {e}", exc_info=True)
    
    async def send_reply(self, user_id, text):
        """发送回复"""
        if not self.bot or not user_id:
            return
        try:
            logger.info(f"回复: {text[:50]}...")
            await self.bot.send_text(user_id, text)
            logger.info("✅ 已发送")
        except Exception as e:
            logger.error(f"发送失败: {e}")
    
    def run_bot(self):
        """在新线程中运行 bot（阻塞）"""
        logger.info("启动 bot 消息循环...")
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行 bot
            loop.run_until_complete(self.bot.run())
        except Exception as e:
            logger.error(f"Bot 运行错误: {e}", exc_info=True)
    
    async def run(self):
        """主运行"""
        # 保存事件循环引用
        self.loop = asyncio.get_event_loop()
        
        # 初始化并登录
        if not await self.init_and_login():
            logger.error("启动失败")
            return
        
        # 在新线程中启动 bot（因为 run() 是阻塞的）
        bot_thread = threading.Thread(target=self.run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        logger.info("✅ Bot 消息循环已启动（后台线程）")
        logger.info("等待微信消息...")


# HTTP 服务器
bridge = WechatBridge()

async def handle_index(request):
    return web.Response(text="""
    <h1>WeChat Bridge V2</h1>
    <p>微信桥接器运行中</p>
    <ul>
        <li><a href="/status">查看状态</a></li>
    </ul>
    """, content_type='text/html')

async def handle_status(request):
    return web.json_response({
        "status": "running",
        "timestamp": datetime.now().isoformat()
    })

async def main():
    # 启动 HTTP
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/status', handle_status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8081))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"HTTP: http://0.0.0.0:{port}")
    
    # 启动微信桥接
    await bridge.run()
    
    # 保持运行
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已停止")
