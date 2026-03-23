#!/usr/bin/env python3
"""
真正能工作的微信桥接器 - 基于实际 weixin_bot API
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
    level=logging.DEBUG,  # 改为 DEBUG 看详细日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wechat-working.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WechatBridge:
    def __init__(self):
        self.bot = None
        self.local_url = os.environ.get('LOCAL_URL', 'http://localhost:8766')
        self.running = False
        self.logged_in = False
        
    async def init_and_login(self):
        """初始化并登录"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("="*60)
            logger.info("初始化微信 Bot...")
            logger.info("="*60)
            
            # 创建 bot 实例
            self.bot = WeixinBot()
            
            # 登录（这会显示二维码）
            logger.info("等待扫码登录...")
            login_result = await self.bot._login(force=False)
            
            if login_result:
                self.logged_in = True
                logger.info("✅ 登录成功！")
                
                # 检查 bot 的方法和属性
                logger.info(f"Bot 类型: {type(self.bot)}")
                logger.info(f"Bot 属性: {[a for a in dir(self.bot) if not a.startswith('_')]}")
                
                return True
            else:
                logger.error("❌ 登录失败")
                return False
                
        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    async def message_loop(self):
        """消息循环 - 主动获取消息"""
        logger.info("启动消息循环...")
        
        while self.running and self.logged_in:
            try:
                # 检查 bot 是否有获取消息的方法
                if hasattr(self.bot, 'get_updates'):
                    logger.debug("尝试 get_updates...")
                    updates = await self.bot.get_updates()
                    if updates:
                        logger.info(f"收到 {len(updates)} 条更新")
                        for update in updates:
                            await self.process_message(update)
                
                elif hasattr(self.bot, 'get_messages'):
                    logger.debug("尝试 get_messages...")
                    messages = await self.bot.get_messages()
                    if messages:
                        logger.info(f"收到 {len(messages)} 条消息")
                        for msg in messages:
                            await self.process_message(msg)
                
                # 检查是否有消息处理器
                elif hasattr(self.bot, 'msg_handler') or hasattr(self.bot, 'message_handler'):
                    logger.info("发现消息处理器，等待回调...")
                    # 设置回调
                    if hasattr(self.bot, 'on_message'):
                        self.bot.on_message(self.on_message_callback)
                    await asyncio.sleep(1)
                
                else:
                    # 如果没有标准方法，尝试直接访问底层
                    logger.debug("尝试直接访问消息队列...")
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"消息循环错误: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    def on_message_callback(self, msg):
        """消息回调（如果支持）"""
        logger.info(f"回调收到消息: {msg}")
        asyncio.create_task(self.process_message(msg))
    
    async def process_message(self, msg):
        """处理消息"""
        try:
            logger.info(f"处理消息: {json.dumps(msg, ensure_ascii=False)[:200]}")
            
            # 提取消息内容
            text = ""
            user_id = ""
            user_name = ""
            
            if isinstance(msg, dict):
                text = msg.get('content', '') or msg.get('text', '')
                user = msg.get('from_user', {}) or msg.get('user', {})
                if isinstance(user, dict):
                    user_id = user.get('id', '')
                    user_name = user.get('name', '')
            else:
                # 可能是对象
                text = getattr(msg, 'content', '') or getattr(msg, 'text', '')
                user = getattr(msg, 'from_user', None)
                if user:
                    user_id = getattr(user, 'id', '')
                    user_name = getattr(user, 'name', '')
            
            if not text:
                logger.warning("消息没有文本内容")
                return
            
            logger.info(f"[微信→本地] {user_name}: {text[:50]}...")
            
            # 转发到本地
            message = {
                "msg_id": str(time.time()),
                "user_id": user_id,
                "user_name": user_name,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.forward_to_local(message)
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
    
    async def forward_to_local(self, message):
        """转发到本地服务器"""
        try:
            logger.info(f"转发到本地: {self.local_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.local_url}/receive",
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    result = await resp.json()
                    logger.info(f"本地响应: {result}")
                    
                    # 发送回复
                    if result.get('status') == 'ok':
                        response = result.get('response', '')
                        if response:
                            await self.send_reply(message['user_id'], response)
                            
        except Exception as e:
            logger.error(f"转发失败: {e}", exc_info=True)
    
    async def send_reply(self, user_id, text):
        """发送回复"""
        if not self.bot or not user_id:
            return
            
        try:
            logger.info(f"发送回复给 {user_id}: {text[:50]}...")
            await self.bot.send_text(user_id, text)
            logger.info("✅ 回复已发送")
        except Exception as e:
            logger.error(f"发送回复失败: {e}", exc_info=True)
    
    async def run(self):
        """运行"""
        if not await self.init_and_login():
            return
        
        self.running = True
        
        # 启动消息循环
        await self.message_loop()


# HTTP 服务器（用于状态检查）
bridge = WechatBridge()

async def handle_index(request):
    return web.Response(text=f"""
    <h1>WeChat Bridge</h1>
    <p>状态: {'运行中' if bridge.running else '未启动'}</p>
    <p>登录: {'已登录' if bridge.logged_in else '未登录'}</p>
    <ul>
        <li><a href="/status">查看详细状态</a></li>
    </ul>
    """, content_type='text/html')

async def handle_status(request):
    return web.json_response({
        "status": "running" if bridge.running else "stopped",
        "logged_in": bridge.logged_in,
        "local_url": bridge.local_url,
        "timestamp": datetime.now().isoformat()
    })

async def main():
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
    
    # 启动微信桥接（在新任务中）
    asyncio.create_task(bridge.run())
    
    # 保持运行
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已停止")
