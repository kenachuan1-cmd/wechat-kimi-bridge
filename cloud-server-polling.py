#!/usr/bin/env python3
"""
云端服务器 - 支持轮询模式
微信连接 + HTTP轮询接口
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloud-polling.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class CloudServer:
    def __init__(self):
        self.bot = None
        self.messages = []  # 待发送给客户端的消息
        self.responses = {}  # 客户端返回的回复
        self.loop = None
        
    async def init_wechat(self):
        """初始化微信"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("=" * 60)
            logger.info("初始化微信 Bot...")
            
            self.bot = WeixinBot()
            self.bot.on_message(self._on_message)
            
            logger.info("等待扫码登录...")
            result = await self.bot._login(force=False)
            
            if result:
                logger.info("✅ 登录成功！")
                return True
            return False
            
        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    def _on_message(self, msg):
        """收到微信消息"""
        try:
            logger.info(f"收到微信消息: {msg}")
            
            # 解析
            if isinstance(msg, dict):
                text = msg.get('content', '')
                user = msg.get('from_user', {})
                user_id = user.get('id', '') if isinstance(user, dict) else ''
                user_name = user.get('name', '') if isinstance(user, dict) else ''
            else:
                text = str(msg)
                user_id = ''
                user_name = ''
            
            # 添加到队列
            self.messages.append({
                'msg_id': str(time.time()),
                'user_id': user_id,
                'user_name': user_name,
                'text': text,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"[微信→队列] {user_name}: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    def _run_bot(self):
        """运行 Bot"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.run())
        except Exception as e:
            logger.error(f"Bot 运行错误: {e}")
    
    async def run(self):
        """运行"""
        if not await self.init_wechat():
            logger.error("启动失败")
            return
        
        # 后台运行 Bot
        bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        bot_thread.start()
        
        logger.info("Bot 已启动，等待消息...")


# HTTP 接口
server = CloudServer()

async def handle_poll(request):
    """客户端轮询消息"""
    # 返回待处理消息
    messages = server.messages.copy()
    server.messages = []  # 清空已发送的
    
    return web.json_response({
        'messages': messages,
        'timestamp': datetime.now().isoformat()
    })

async def handle_respond(request):
    """客户端返回处理结果"""
    try:
        data = await request.json()
        msg_id = data.get('msg_id')
        text = data.get('text')
        
        logger.info(f"[客户端回复] {text[:50]}...")
        
        # 发送回微信
        # 这里需要实现发送到微信的逻辑
        
        return web.json_response({'status': 'ok'})
    except Exception as e:
        logger.error(f"处理回复失败: {e}")
        return web.json_response({'status': 'error', 'message': str(e)})

async def handle_status(request):
    """状态"""
    return web.json_response({
        'status': 'running',
        'wechat_connected': server.bot is not None,
        'pending_messages': len(server.messages),
        'timestamp': datetime.now().isoformat()
    })

async def main():
    """主函数"""
    # 启动微信
    asyncio.create_task(server.run())
    
    # 启动 HTTP
    app = web.Application()
    app.router.add_get('/poll', handle_poll)
    app.router.add_post('/respond', handle_respond)
    app.router.add_get('/status', handle_status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8081))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"HTTP 服务器: http://0.0.0.0:{port}")
    logger.info("等待客户端连接...")
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已停止")
