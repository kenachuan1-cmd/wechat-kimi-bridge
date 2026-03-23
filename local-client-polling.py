#!/usr/bin/env python3
"""
本地客户端 - 轮询云端获取消息
解决云端无法直连本地的问题
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalPollingClient:
    def __init__(self, cloud_url: str):
        self.cloud_url = cloud_url
        self.session = None
        self.last_check_time = 0
        
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
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # 提取最后非空行
                lines = [l.strip() for l in output.split('\n') if l.strip()]
                for line in reversed(lines):
                    if not line.startswith('Turn') and not line.startswith('Step'):
                        return line
                return output[:500]
            else:
                return f"错误: {result.stderr[:100]}"
                
        except Exception as e:
            return f"调用失败: {e}"
    
    async def poll_messages(self):
        """轮询云端消息"""
        url = f"{self.cloud_url}/poll"
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('messages', [])
                return []
        except Exception as e:
            logger.debug(f"轮询失败: {e}")
            return []
    
    async def send_response(self, msg_id: str, text: str):
        """发送回复到云端"""
        url = f"{self.cloud_url}/respond"
        
        try:
            payload = {
                'msg_id': msg_id,
                'text': text,
                'timestamp': datetime.now().isoformat()
            }
            async with self.session.post(url, json=payload, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"发送回复失败: {e}")
            return False
    
    async def process_messages(self):
        """处理消息主循环"""
        logger.info("=" * 60)
        logger.info("  本地客户端启动")
        logger.info("=" * 60)
        logger.info(f"云端地址: {self.cloud_url}")
        logger.info("")
        
        async with aiohttp.ClientSession() as self.session:
            logger.info("开始轮询消息...")
            logger.info("按 Ctrl+C 停止")
            logger.info("")
            
            while True:
                try:
                    # 获取消息
                    messages = await self.poll_messages()
                    
                    for msg in messages:
                        logger.info(f"收到消息 [{msg.get('user_name')}]: {msg.get('text', '')[:50]}...")
                        
                        # 调用 Kimi
                        response = await self.call_kimi(msg['text'])
                        
                        # 发送回复
                        await self.send_response(msg['msg_id'], response)
                        logger.info(f"回复已发送: {response[:50]}...")
                    
                    # 等待下次轮询
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"处理消息错误: {e}")
                    await asyncio.sleep(5)
    
    async def run(self):
        """运行"""
        try:
            await self.process_messages()
        except KeyboardInterrupt:
            logger.info("已停止")


def main():
    if len(sys.argv) < 2:
        print("用法: python local-client-polling.py <云端URL>")
        print("示例: python local-client-polling.py https://xxx.trycloudflare.com")
        sys.exit(1)
    
    cloud_url = sys.argv[1]
    client = LocalPollingClient(cloud_url)
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
