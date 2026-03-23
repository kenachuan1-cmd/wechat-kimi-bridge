#!/usr/bin/env python3
"""
混合架构 - 云端桥接服务器
运行在 GitHub Codespaces，负责连接微信
通过 WebSocket 将消息转发到本地客户端
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Dict, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 存储连接的本地客户端
connected_clients: Set[websockets.WebSocketServerProtocol] = set()

# 消息队列（用于本地客户端离线时的消息缓存）
message_queue: asyncio.Queue = asyncio.Queue()


async def register_client(websocket):
    """注册本地客户端"""
    connected_clients.add(websocket)
    logger.info(f"本地客户端已连接，当前连接数: {len(connected_clients)}")


async def unregister_client(websocket):
    """注销本地客户端"""
    connected_clients.discard(websocket)
    logger.info(f"本地客户端已断开，当前连接数: {len(connected_clients)}")


async def forward_to_clients(message: dict):
    """转发消息到所有连接的本地客户端"""
    if not connected_clients:
        logger.warning("没有本地客户端连接，消息将进入队列")
        await message_queue.put(message)
        return
    
    dead_clients = set()
    for client in connected_clients:
        try:
            await client.send(json.dumps(message))
        except Exception as e:
            logger.error(f"转发消息失败: {e}")
            dead_clients.add(client)
    
    # 清理断开的客户端
    for client in dead_clients:
        connected_clients.discard(client)


async def handle_client(websocket, path):
    """处理本地客户端连接"""
    await register_client(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type')
                
                if msg_type == 'pong':
                    # 心跳响应
                    pass
                elif msg_type == 'response':
                    # 收到Kimi的回复，需要发送到微信
                    logger.info(f"收到Kimi回复: {data.get('text', '')[:50]}...")
                    # 这里需要将回复发送回微信
                    # TODO: 实现微信消息发送
                else:
                    logger.info(f"收到未知消息类型: {msg_type}")
                    
            except json.JSONDecodeError:
                logger.error(f"收到无效JSON: {message}")
    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端连接关闭")
    finally:
        await unregister_client(websocket)


async def simulate_wechat_message():
    """模拟收到微信消息（测试用）"""
    await asyncio.sleep(5)
    test_msg = {
        "type": "message",
        "msg_id": "test_001",
        "user_id": "user_test",
        "user_name": "测试用户",
        "text": "你好，帮我写一个Python脚本",
        "is_group": False,
        "timestamp": datetime.now().isoformat()
    }
    await forward_to_clients(test_msg)
    logger.info("已转发测试消息到本地客户端")


async def start_server(host='0.0.0.0', port=8765):
    """启动WebSocket服务器"""
    logger.info(f"启动混合桥接服务器...")
    logger.info(f"监听地址: {host}:{port}")
    logger.info("")
    logger.info("使用说明:")
    logger.info("1. 在本地运行: python hybrid-bridge-client.py")
    logger.info("2. 本地客户端会自动连接到此服务器")
    logger.info("3. 微信消息将通过WebSocket转发到本地Kimi处理")
    logger.info("")
    
    async with websockets.serve(handle_client, host, port):
        # 启动测试消息发送
        asyncio.create_task(simulate_wechat_message())
        await asyncio.Future()  # 永久运行


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("服务器已停止")
