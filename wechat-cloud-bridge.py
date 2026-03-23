#!/usr/bin/env python3
"""
云端微信桥接器 - 连接真实微信，转发到本地
部署在 Codespaces，通过 cloudflared 隧道通信
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from aiohttp import web
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloud-bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class WechatCloudBridge:
    def __init__(self):
        self.bot = None
        self.messages = []  # 来自微信的消息
        self.responses = {}  # 本地返回的回复
        self.local_server_url = None  # 本地服务器地址
        
    async def init_wechat(self):
        """初始化微信连接"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("初始化微信 Bot...")
            self.bot = WeixinBot()
            
            # 登录
            logger.info("等待微信登录...")
            login_result = await self.bot._login(force=False)
            
            if login_result:
                logger.info("✅ 微信登录成功！")
                return True
            else:
                logger.error("❌ 微信登录失败")
                return False
                
        except ImportError:
            logger.error("weixin-bot-sdk 未安装")
            logger.info("请运行: pip install weixin-bot-sdk")
            return False
        except Exception as e:
            logger.error(f"初始化微信失败: {e}")
            return False
    
    async def handle_wechat_message(self, msg_data):
        """处理微信消息，转发到本地"""
        message = {
            "type": "message",
            "msg_id": msg_data.get('msg_id', str(datetime.now().timestamp())),
            "user_id": msg_data.get('user_id', ''),
            "user_name": msg_data.get('user_name', ''),
            "text": msg_data.get('text', ''),
            "is_group": msg_data.get('is_group', False),
            "group_id": msg_data.get('group_id'),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[微信→本地] {message['user_name']}: {message['text'][:50]}...")
        
        # 添加到消息队列
        self.messages.append(message)
        
        # 如果有本地服务器，直接转发
        if self.local_server_url:
            await self.forward_to_local(message)
    
    async def forward_to_local(self, message):
        """直接转发到本地服务器"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.local_server_url}/receive",
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        logger.info("✅ 消息已转发到本地")
                    else:
                        logger.warning(f"转发失败: {resp.status}")
        except Exception as e:
            logger.error(f"转发到本地失败: {e}")
    
    async def send_to_wechat(self, user_id, text):
        """发送消息到微信"""
        if not self.bot:
            logger.error("微信未连接")
            return False
            
        try:
            await self.bot.send_text(user_id, text)
            logger.info(f"[本地→微信] 已发送到 {user_id}: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"发送到微信失败: {e}")
            return False

# ==================== HTTP 服务器 ====================

bridge = WechatCloudBridge()

async def handle_receive(request):
    """接收本地返回的回复"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        text = data.get('text')
        
        logger.info(f"[本地→云端] 收到回复: {text[:50]}...")
        
        # 发送到微信
        success = await bridge.send_to_wechat(user_id, text)
        
        return web.json_response({
            "status": "ok" if success else "error"
        })
    except Exception as e:
        logger.error(f"处理回复失败: {e}")
        return web.json_response({"status": "error", "message": str(e)})

async def handle_status(request):
    """状态检查"""
    return web.json_response({
        "wechat_connected": bridge.bot is not None,
        "pending_messages": len(bridge.messages),
        "timestamp": datetime.now().isoformat()
    })

async def index(request):
    """首页"""
    return web.Response(text="""
    <h1>WeChat Cloud Bridge</h1>
    <p>云端微信桥接器运行中</p>
    <ul>
        <li><a href="/status">查看状态</a></li>
    </ul>
    """, content_type='text/html')

async def main():
    """主函数"""
    logger.info("="*60)
    logger.info("  云端微信桥接器启动")
    logger.info("="*60)
    
    # 初始化微信
    if not await bridge.init_wechat():
        logger.error("微信初始化失败，退出")
        return
    
    # 创建 HTTP 应用
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/status', handle_status)
    app.router.add_post('/receive', handle_receive)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # 使用不同端口（避免冲突）
    port = int(os.environ.get('PORT', 8081))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logger.info(f"HTTP 服务器: http://0.0.0.0:{port}")
    logger.info("等待 cloudflared 隧道连接...")
    logger.info("本地客户端连接后，微信消息将自动转发")
    logger.info("="*60)
    
    await site.start()
    
    # 保持运行
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已停止")
