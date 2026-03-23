#!/usr/bin/env python3
"""
微信桥接器 - 轮询版本（更可靠）
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from aiohttp import web
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wechat-bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WechatBridge:
    def __init__(self):
        self.bot = None
        self.local_url = os.environ.get('LOCAL_URL', 'http://localhost:8766')
        self.running = False
        self.last_msg_id = 0
        
    async def init_bot(self):
        """初始化微信机器人"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("="*60)
            logger.info("正在初始化微信 Bot...")
            logger.info("="*60)
            
            self.bot = WeixinBot()
            
            # 登录
            logger.info("等待微信登录...")
            login_result = await self.bot._login(force=False)
            
            if login_result:
                logger.info("✅ 登录成功！")
                return True
            else:
                logger.error("❌ 登录失败")
                return False
                
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    async def poll_messages(self):
        """轮询微信消息"""
        while self.running:
            try:
                if not self.bot:
                    await asyncio.sleep(5)
                    continue
                
                # 获取更新（使用 bot 的 get_updates 或类似方法）
                # 注意：这里需要根据实际的 weixin_bot API 调整
                logger.debug("轮询消息...")
                
                # 模拟：假设 bot 有 get_updates 方法
                # messages = await self.bot.get_updates()
                # for msg in messages:
                #     await self.handle_message(msg)
                
                await asyncio.sleep(2)  # 每2秒轮询一次
                
            except Exception as e:
                logger.error(f"轮询出错: {e}")
                await asyncio.sleep(5)
    
    async def handle_message(self, msg_data):
        """处理微信消息"""
        try:
            logger.info(f"收到消息: {msg_data}")
            
            message = {
                "type": "message",
                "msg_id": str(time.time()),
                "user_id": msg_data.get('from_user', {}).get('id', ''),
                "user_name": msg_data.get('from_user', {}).get('name', ''),
                "text": msg_data.get('content', ''),
                "is_group": msg_data.get('is_group', False),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"[微信→本地] {message['user_name']}: {message['text'][:50]}...")
            
            # 转发到本地
            await self.forward_to_local(message)
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def forward_to_local(self, message):
        """转发到本地"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.local_url}/receive",
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"本地处理完成: {result}")
                        
                        # 发送回复
                        if result.get('status') == 'ok' and result.get('response'):
                            await self.send_reply(message['user_id'], result['response'])
                    else:
                        logger.warning(f"本地返回错误: {resp.status}")
        except Exception as e:
            logger.error(f"转发失败: {e}")
    
    async def send_reply(self, user_id, text):
        """发送回复到微信"""
        if not self.bot:
            return
        try:
            await self.bot.send_text(user_id, text)
            logger.info(f"[本地→微信] 已发送: {text[:50]}...")
        except Exception as e:
            logger.error(f"发送失败: {e}")
    
    async def run(self):
        """运行"""
        if not await self.init_bot():
            return
        
        self.running = True
        logger.info("开始轮询消息...")
        
        # 启动轮询
        await self.poll_messages()


# HTTP 服务器
bridge = WechatBridge()

async def handle_index(request):
    return web.Response(text="""
    <h1>WeChat Bridge</h1>
    <p>微信桥接器运行中</p>
    <ul>
        <li><a href="/status">查看状态</a></li>
    </ul>
    """, content_type='text/html')

async def handle_status(request):
    return web.json_response({
        "status": "running",
        "wechat_connected": bridge.bot is not None,
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
    
    logger.info(f"HTTP 服务器: http://0.0.0.0:{port}")
    
    # 启动微信桥接
    asyncio.create_task(bridge.run())
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已停止")
