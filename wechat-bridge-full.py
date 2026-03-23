#!/usr/bin/env python3
"""
完整版微信桥接器 - 真正连接微信并转发消息
"""

import asyncio
import json
import logging
import os
import sys
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
        logging.FileHandler('wechat-bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WechatBridge:
    def __init__(self):
        self.bot = None
        self.message_queue = []  # 来自微信的消息
        self.local_url = os.environ.get('LOCAL_URL', 'http://localhost:8766')
        self.running = False
        
    async def init_bot(self):
        """初始化微信机器人"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("="*60)
            logger.info("正在初始化微信 Bot...")
            logger.info("="*60)
            
            self.bot = WeixinBot()
            
            # 设置消息回调
            self.bot.on_message(self.on_message)
            
            logger.info("微信 Bot 初始化完成，等待登录...")
            return True
            
        except ImportError as e:
            logger.error(f"weixin-bot-sdk 未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def on_message(self, msg):
        """微信消息回调"""
        try:
            logger.info(f"收到微信消息: {msg}")
            
            # 解析消息
            message = {
                "type": "message",
                "msg_id": str(time.time()),
                "user_id": msg.get('from_user', {}).get('id', ''),
                "user_name": msg.get('from_user', {}).get('name', ''),
                "text": msg.get('content', ''),
                "is_group": msg.get('is_group', False),
                "group_id": msg.get('group_id'),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"[微信→本地] {message['user_name']}: {message['text'][:50]}...")
            
            # 转发到本地
            asyncio.create_task(self.forward_to_local(message))
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def forward_to_local(self, message):
        """转发消息到本地服务器"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.local_url}/receive",
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"本地处理完成: {result.get('status')}")
                        
                        # 如果有回复，发送回微信
                        if result.get('status') == 'ok' and result.get('response'):
                            await self.send_to_wechat(message['user_id'], result['response'])
                    else:
                        logger.warning(f"本地返回错误: {resp.status}")
        except Exception as e:
            logger.error(f"转发到本地失败: {e}")
    
    async def send_to_wechat(self, user_id, text):
        """发送消息到微信"""
        if not self.bot:
            logger.error("微信未连接")
            return
            
        try:
            await self.bot.send_text(user_id, text)
            logger.info(f"[本地→微信] 已发送: {text[:50]}...")
        except Exception as e:
            logger.error(f"发送到微信失败: {e}")
    
    async def run(self):
        """运行机器人"""
        if not await self.init_bot():
            logger.error("初始化失败")
            return
            
        self.running = True
        
        # 启动登录（会显示二维码）
        logger.info("启动登录流程...")
        try:
            # 在新线程中运行登录，避免阻塞
            import threading
            login_thread = threading.Thread(target=self._login_sync)
            login_thread.start()
            login_thread.join(timeout=300)  # 5分钟超时
            
            if login_thread.is_alive():
                logger.error("登录超时")
                return
                
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return
        
        logger.info("登录流程完成，保持运行...")
        
        # 保持运行
        while self.running:
            await asyncio.sleep(1)
    
    def _login_sync(self):
        """同步登录（在独立线程）"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.bot._login(force=False))
            loop.close()
            
            if result:
                logger.info("✅ 登录成功！")
            else:
                logger.error("❌ 登录失败")
        except Exception as e:
            logger.error(f"登录异常: {e}")


# ==================== HTTP 服务器 ====================

async def handle_index(request):
    """首页"""
    return web.Response(text="""
    <h1>WeChat Bridge</h1>
    <p>微信桥接器运行中</p>
    <ul>
        <li><a href="/status">查看状态</a></li>
    </ul>
    """, content_type='text/html')

async def handle_status(request):
    """状态接口"""
    return web.json_response({
        "status": "running",
        "wechat_connected": bridge.bot is not None,
        "timestamp": datetime.now().isoformat()
    })


async def main():
    """主函数"""
    global bridge
    
    # 创建桥接器
    bridge = WechatBridge()
    
    # 启动 HTTP 服务器
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/status', handle_status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8081))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"HTTP 服务器: http://0.0.0.0:{port}")
    logger.info("等待 cloudflared 连接...")
    
    # 同时启动微信机器人
    asyncio.create_task(bridge.run())
    
    # 保持运行
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已停止")
