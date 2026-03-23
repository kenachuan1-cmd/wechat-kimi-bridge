#!/usr/bin/env python3
"""
本地 Kimi 服务器 - 接收云端消息，调用本地 Kimi 处理
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from aiohttp import web
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalKimiServer:
    def __init__(self, cloud_url=None):
        self.cloud_url = cloud_url
        self.session = None
        
    async def call_kimi(self, text: str, work_dir: str = ".") -> str:
        """调用本地 Kimi CLI"""
        logger.info(f"调用 Kimi: {text[:50]}...")
        
        try:
            cmd = ["kimi", "--no-interactive", "-c", text]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                cwd=work_dir
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                logger.info(f"Kimi 回复: {response[:100]}...")
                return response
            else:
                error = result.stderr.strip()
                logger.error(f"Kimi 错误: {error}")
                return f"抱歉，处理失败: {error[:100]}"
                
        except subprocess.TimeoutExpired:
            return "抱歉，处理时间过长，请稍后再试"
        except Exception as e:
            logger.error(f"调用 Kimi 失败: {e}")
            return f"调用失败: {str(e)}"
    
    async def handle_message(self, request):
        """处理来自云端的消息"""
        try:
            data = await request.json()
            
            user_id = data.get('user_id')
            user_name = data.get('user_name', '用户')
            text = data.get('text', '')
            
            logger.info(f"收到消息 [{user_name}]: {text[:50]}...")
            
            # 调用 Kimi 处理
            response = await self.call_kimi(text)
            
            # 发送回复回云端
            if self.cloud_url:
                await self.send_response(user_id, response)
            
            return web.json_response({
                "status": "ok",
                "response": response[:100]  # 返回摘要
            })
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            })
    
    async def send_response(self, user_id: str, text: str):
        """发送回复到云端"""
        try:
            if not self.cloud_url:
                return
                
            payload = {
                "user_id": user_id,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cloud_url}/receive",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        logger.info("✅ 回复已发送到云端")
                    else:
                        logger.warning(f"发送回复失败: {resp.status}")
                        
        except Exception as e:
            logger.error(f"发送回复失败: {e}")
    
    async def handle_status(self, request):
        """状态检查"""
        return web.json_response({
            "status": "running",
            "cloud_url": self.cloud_url,
            "timestamp": datetime.now().isoformat()
        })
    
    async def run(self, port=8766):
        """运行本地服务器"""
        logger.info("="*60)
        logger.info("  本地 Kimi 服务器启动")
        logger.info("="*60)
        logger.info(f"端口: {port}")
        logger.info(f"云端地址: {self.cloud_url or '未配置'}")
        logger.info("")
        
        app = web.Application()
        app.router.add_get('/status', self.handle_status)
        app.router.add_post('/receive', self.handle_message)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"✅ 服务器运行中: http://localhost:{port}")
        logger.info("等待云端消息...")
        logger.info("="*60)
        
        # 保持运行
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    import sys
    
    cloud_url = sys.argv[1] if len(sys.argv) > 1 else None
    server = LocalKimiServer(cloud_url)
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("已停止")
