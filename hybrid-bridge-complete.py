#!/usr/bin/env python3
"""
混合架构完整版 - 云端微信桥接 + WebSocket转发
部署在 GitHub Codespaces，连接微信并转发到本地
"""

import asyncio
import json
import logging
import os
import sys
import websockets
from datetime import datetime
from typing import Dict, Optional, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hybrid-bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ==================== WebSocket 服务器 ====================

class BridgeServer:
    """桥接服务器 - 转发微信消息到本地客户端"""
    
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
    async def register(self, websocket):
        """注册客户端"""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address}"
        logger.info(f"✓ 本地客户端连接 [{client_info}]，当前连接数: {len(self.clients)}")
        
        # 发送队列中的积压消息
        while not self.message_queue.empty():
            try:
                msg = self.message_queue.get_nowait()
                await websocket.send(json.dumps(msg))
                logger.info(f"  发送积压消息: {msg.get('msg_id')}")
            except Exception as e:
                logger.error(f"发送积压消息失败: {e}")
                break
    
    async def unregister(self, websocket):
        """注销客户端"""
        self.clients.discard(websocket)
        logger.info(f"✗ 本地客户端断开，当前连接数: {len(self.clients)}")
    
    async def broadcast(self, message: dict):
        """广播消息到所有客户端"""
        if not self.clients:
            logger.warning("无本地客户端连接，消息进入队列")
            await self.message_queue.put(message)
            return False
        
        dead_clients = set()
        data = json.dumps(message)
        
        for client in self.clients:
            try:
                await client.send(data)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                dead_clients.add(client)
        
        # 清理断开的客户端
        for client in dead_clients:
            await self.unregister(client)
        
        return len(dead_clients) < len(self.clients)
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(data, websocket)
                except json.JSONDecodeError:
                    logger.error(f"收到无效JSON: {message[:100]}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def handle_client_message(self, data: dict, client):
        """处理客户端发来的消息"""
        msg_type = data.get('type')
        
        if msg_type == 'pong':
            pass  # 心跳响应
        elif msg_type == 'response':
            # 收到Kimi的回复，转发到微信
            logger.info(f"收到Kimi回复: {data.get('text', '')[:50]}...")
            await self.handle_kimi_response(data)
        else:
            logger.info(f"收到客户端消息: {msg_type}")
    
    async def handle_kimi_response(self, data: dict):
        """处理Kimi回复，发送到微信"""
        # TODO: 集成微信发送功能
        logger.info(f"[转发到微信] {data.get('text', '')[:50]}...")
    
    async def start(self):
        """启动服务器"""
        self.running = True
        logger.info("=" * 60)
        logger.info("  混合桥接服务器启动")
        logger.info("=" * 60)
        logger.info(f"WebSocket: ws://{self.host}:{self.port}")
        
        # 获取Codespaces公网URL
        codespace_name = os.environ.get('CODESPACE_NAME')
        if codespace_name:
            public_url = f"wss://{codespace_name}-8765.github.dev"
            logger.info(f"公网地址: {public_url}")
        
        logger.info("")
        logger.info("本地客户端连接命令:")
        logger.info(f"  python hybrid-bridge-client.py ws://localhost:{self.port}")
        if codespace_name:
            logger.info(f"  python hybrid-bridge-client.py wss://{codespace_name}-8765.github.dev")
        logger.info("")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # 永久运行


# ==================== 微信桥接集成 ====================

class HybridWeixinBridge:
    """混合微信桥接器"""
    
    def __init__(self, server: BridgeServer):
        self.server = server
        self.bot = None
        
    async def on_wechat_message(self, msg_data: dict):
        """收到微信消息"""
        # 构建消息
        message = {
            "type": "message",
            "msg_id": msg_data.get('msg_id', ''),
            "user_id": msg_data.get('user_id', ''),
            "user_name": msg_data.get('user_name', ''),
            "text": msg_data.get('text', ''),
            "is_group": msg_data.get('is_group', False),
            "group_id": msg_data.get('group_id'),
            "group_name": msg_data.get('group_name'),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[微信→本地] {message['user_name']}: {message['text'][:50]}...")
        
        # 转发到本地客户端
        await self.server.broadcast(message)
    
    async def start_wechat(self):
        """启动微信连接"""
        logger.info("启动微信连接...")
        
        try:
            from weixin_bot import WeixinBot
            
            bot = WeixinBot()
            
            # 登录
            logger.info("等待微信登录...")
            login_result = await bot._login(force=False)
            
            if not login_result:
                logger.error("微信登录失败")
                return False
            
            logger.info("✓ 微信登录成功")
            self.bot = bot
            
            # 设置消息回调
            # 注意: 这里需要根据实际的weixin_bot API调整
            # bot.on_message(self.on_wechat_message)
            
            # 启动消息监听循环
            # await bot.run()
            
            # 模拟运行（测试用）
            await self._mock_run()
            
        except ImportError:
            logger.warning("weixin-bot-sdk 未安装，使用模拟模式")
            await self._mock_run()
        except Exception as e:
            logger.error(f"启动微信失败: {e}")
            await self._mock_run()
    
    async def _mock_run(self):
        """模拟运行（测试用）"""
        logger.info("进入模拟模式（测试用）")
        logger.info("每10秒发送一条测试消息...")
        
        counter = 0
        while True:
            await asyncio.sleep(10)
            counter += 1
            
            test_msg = {
                "msg_id": f"mock_{counter}",
                "user_id": f"user_{counter}",
                "user_name": f"测试用户{counter}",
                "text": f"这是第{counter}条测试消息，帮我写一个Python脚本",
                "is_group": False
            }
            
            await self.on_wechat_message(test_msg)


# ==================== 主程序 ====================

async def main():
    """主函数"""
    # 创建服务器
    server = BridgeServer(host='0.0.0.0', port=8765)
    
    # 创建微信桥接
    bridge = HybridWeixinBridge(server)
    
    # 同时启动服务器和微信连接
    await asyncio.gather(
        server.start(),
        bridge.start_wechat()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务器已停止")
