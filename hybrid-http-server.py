#!/usr/bin/env python3
"""
HTTP轮询版 - 云端服务器
更稳定的实现，无WebSocket兼容性问题
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 消息队列
messages = []  # 待发送给本地的消息
responses = {}  # 本地返回的回复
clients = set()  # 连接的客户端


async def get_messages(request):
    """本地客户端轮询获取消息"""
    client_id = request.query.get('client', 'unknown')
    clients.add(client_id)
    
    global messages
    msgs = messages.copy()
    messages = []  # 清空已发送的消息
    
    return web.json_response({
        'status': 'ok',
        'messages': msgs,
        'timestamp': datetime.now().isoformat()
    })


async def post_response(request):
    """本地客户端返回Kimi回复"""
    try:
        data = await request.json()
        msg_id = data.get('msg_id')
        text = data.get('text')
        
        responses[msg_id] = {
            'text': text,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"收到Kimi回复: {text[:50]}...")
        
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)})


async def send_message(request):
    """外部调用：添加消息到队列"""
    try:
        data = await request.json()
        msg = {
            'msg_id': data.get('msg_id', str(datetime.now().timestamp())),
            'user_id': data.get('user_id', ''),
            'user_name': data.get('user_name', ''),
            'text': data.get('text', ''),
            'is_group': data.get('is_group', False),
            'timestamp': datetime.now().isoformat()
        }
        messages.append(msg)
        logger.info(f"消息入队 [{msg['user_name']}]: {msg['text'][:50]}...")
        return web.json_response({'status': 'ok', 'msg_id': msg['msg_id']})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)})


async def get_status(request):
    """获取服务器状态"""
    return web.json_response({
        'status': 'running',
        'clients': list(clients),
        'pending_messages': len(messages),
        'pending_responses': len(responses),
        'timestamp': datetime.now().isoformat()
    })


async def index(request):
    """首页"""
    return web.Response(text="""
    <h1>WeChat-Kimi Hybrid Bridge</h1>
    <p>混合架构桥接服务器</p>
    <ul>
        <li><a href="/status">状态</a></li>
        <li>GET /poll - 客户端轮询消息</li>
        <li>POST /respond - 客户端返回回复</li>
    </ul>
    """, content_type='text/html')


async def simulate_wechat():
    """模拟微信消息（测试用）"""
    counter = 0
    while True:
        await asyncio.sleep(15)  # 每15秒发送一条测试消息
        counter += 1
        
        msg = {
            'msg_id': f'test_{counter}',
            'user_id': f'user_{counter}',
            'user_name': f'测试用户{counter}',
            'text': f'这是第{counter}条测试消息，帮我写一个Python脚本',
            'is_group': False
        }
        messages.append(msg)
        logger.info(f"[测试消息] 已添加到队列: {msg['text'][:50]}...")


async def main():
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/status', get_status)
    app.router.add_get('/poll', get_messages)
    app.router.add_post('/respond', post_response)
    app.router.add_post('/send', send_message)
    
    # 启动测试消息生成
    asyncio.create_task(simulate_wechat())
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logger.info("=" * 60)
    logger.info("  HTTP轮询版混合桥接服务器")
    logger.info("=" * 60)
    logger.info(f"服务器地址: http://0.0.0.0:{port}")
    logger.info("")
    
    codespace_name = os.environ.get('CODESPACE_NAME')
    if codespace_name:
        logger.info(f"公网地址: https://{codespace_name}-{port}.github.dev")
    
    logger.info("")
    logger.info("API端点:")
    logger.info(f"  GET  http://localhost:{port}/poll")
    logger.info(f"  POST http://localhost:{port}/respond")
    logger.info("")
    logger.info("本地客户端启动命令:")
    if codespace_name:
        logger.info(f"  python hybrid-http-client.py https://{codespace_name}-{port}.github.dev")
    else:
        logger.info(f"  python hybrid-http-client.py http://localhost:{port}")
    logger.info("")
    
    await site.start()
    
    # 永久运行
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(main())
