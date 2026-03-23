#!/usr/bin/env python3
"""
本地完整微信桥接器
直接连接微信，调用本地 Kimi，无需云端
"""

import asyncio
import logging
import os
import subprocess
import threading
import time
from datetime import datetime

# 设置代理（如果需要）
# os.environ['HTTP_PROXY'] = 'http://127.0.0.1:10809'
# os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:10809'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('local-bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class LocalWechatBridge:
    def __init__(self):
        self.bot = None
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
        """消息回调"""
        logger.info(f"📩 收到消息: {msg}")
        
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.handle_message(msg), 
                self.loop
            )
    
    async def handle_message(self, msg):
        """处理消息"""
        try:
            # 解析消息
            if isinstance(msg, dict):
                text = msg.get('content', '')
                user = msg.get('from_user', {})
                user_id = user.get('id', '') if isinstance(user, dict) else ''
                user_name = user.get('name', '') if isinstance(user, dict) else ''
            else:
                text = str(msg)
                user_id = ''
                user_name = ''
            
            if not text:
                return
            
            logger.info(f"[{user_name}]: {text[:50]}...")
            
            # 调用 Kimi
            response = await self.call_kimi(text)
            
            # 发送回复
            if user_id:
                await self.send_reply(user_id, response)
                
        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
    
    async def call_kimi(self, text: str) -> str:
        """调用本地 Kimi"""
        try:
            logger.info(f"调用 Kimi: {text[:50]}...")
            
            cmd = ["kimi", "--print", "--yolo", "-c", text]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"错误: {result.stderr[:100]}"
                
        except Exception as e:
            return f"调用失败: {str(e)}"
    
    async def send_reply(self, user_id: str, text: str):
        """发送回复"""
        try:
            logger.info(f"回复: {text[:50]}...")
            await self.bot.send_text(user_id, text)
            logger.info("✅ 已发送")
        except Exception as e:
            logger.error(f"发送失败: {e}")
    
    def run_bot_thread(self):
        """在新线程中运行 bot"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.run())
        except Exception as e:
            logger.error(f"Bot 线程错误: {e}")
    
    async def run(self):
        """运行"""
        self.loop = asyncio.get_event_loop()
        
        if not await self.init_and_login():
            logger.error("启动失败")
            return
        
        # 启动 bot 线程
        bot_thread = threading.Thread(target=self.run_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
        
        logger.info("✅ 系统运行中！")
        logger.info("等待微信消息...")
        logger.info("="*60)
        
        # 保持运行
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    bridge = LocalWechatBridge()
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        logger.info("已停止")
