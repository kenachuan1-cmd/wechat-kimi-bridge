#!/usr/bin/env python3
"""
HTTP轮询版 - 本地客户端
调用本地Kimi处理消息
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
from datetime import datetime
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KimiLocalClient:
    """本地Kimi客户端 - HTTP轮询版"""
    
    def __init__(self, server_url: str = None):
        self.server_url = server_url or "http://localhost:8080"
        self.session = None
        self.running = False
        
    async def connect(self):
        """连接测试"""
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(f"{self.server_url}/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✓ 已连接到云端服务器")
                    logger.info(f"  服务器状态: {data}")
                    return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    async def call_kimi(self, text: str, work_dir: str = ".") -> str:
        """调用本地Kimi CLI"""
        logger.info(f"调用Kimi: {text[:50]}...")
        
        try:
            # 使用 kimi --wire 模式
            cmd = [
                "kimi", "--no-interactive",
                "-c", text
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                cwd=work_dir
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error = result.stderr.strip()
                logger.error(f"Kimi错误: {error}")
                return f"处理失败: {error[:100]}"
                
        except subprocess.TimeoutExpired:
            return "处理超时，请稍后再试"
        except Exception as e:
            logger.error(f"调用Kimi失败: {e}")
            return f"调用失败: {str(e)}"
    
    async def poll_messages(self):
        """轮询获取消息"""
        try:
            async with self.session.get(
                f"{self.server_url}/poll",
                params={"client": "local_001"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('messages', [])
                return []
        except Exception as e:
            logger.error(f"轮询失败: {e}")
            return []
    
    async def send_response(self, msg_id: str, text: str):
        """发送回复到云端"""
        try:
            payload = {
                'msg_id': msg_id,
                'text': text,
                'timestamp': datetime.now().isoformat()
            }
            async with self.session.post(
                f"{self.server_url}/respond",
                json=payload
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"发送回复失败: {e}")
            return False
    
    async def process_messages(self):
        """处理消息主循环"""
        logger.info("开始轮询消息...")
        
        while self.running:
            try:
                # 获取消息
                messages = await self.poll_messages()
                
                for msg in messages:
                    logger.info(f"收到消息 [{msg['user_name']}]: {msg['text'][:50]}...")
                    
                    # 调用Kimi处理
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
        """运行客户端"""
        logger.info("=" * 60)
        logger.info("  HTTP轮询版 - 本地Kimi客户端")
        logger.info("=" * 60)
        logger.info(f"服务器: {self.server_url}")
        logger.info("")
        
        if not await self.connect():
            logger.error("无法连接到云端服务器")
            return
        
        self.running = True
        logger.info("✓ 客户端运行中...")
        logger.info("  按 Ctrl+C 停止")
        logger.info("")
        
        try:
            await self.process_messages()
        except KeyboardInterrupt:
            logger.info("客户端停止")
        finally:
            self.running = False
            if self.session:
                await self.session.close()


async def main():
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    client = KimiLocalClient(server_url)
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
