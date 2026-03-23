#!/usr/bin/env python3
"""
混合架构 - 本地客户端
运行在你的电脑上，连接云端桥接服务器
调用本地Kimi CLI处理消息
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KimiLocalClient:
    """本地Kimi客户端"""
    
    def __init__(self, server_url: str = None):
        self.server_url = server_url or self._get_server_url()
        self.ws = None
        self.kimi_process = None
        
    def _get_server_url(self) -> str:
        """获取服务器URL"""
        # 默认使用本地测试，实际使用时需要修改为云端地址
        # 格式: "wss://your-codespace-xxx.github.dev/ws"
        default = "ws://localhost:8765"
        
        # 从配置文件读取
        config_file = "hybrid-config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('server_url', default)
            except:
                pass
        return default
    
    async def connect(self):
        """连接到云端服务器"""
        import websockets
        
        logger.info(f"正在连接云端服务器: {self.server_url}")
        try:
            self.ws = await websockets.connect(self.server_url)
            logger.info("✓ 已连接到云端服务器")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    async def process_with_kimi(self, message: dict) -> str:
        """调用本地Kimi处理消息"""
        text = message.get('text', '')
        user_name = message.get('user_name', '用户')
        
        logger.info(f"处理消息 [{user_name}]: {text[:50]}...")
        
        # 构建Kimi命令
        cmd = [
            "kimi", "--no-interactive",
            "-c", text
        ]
        
        try:
            # 调用Kimi CLI
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                logger.info(f"Kimi回复: {response[:100]}...")
                return response
            else:
                error = result.stderr.strip()
                logger.error(f"Kimi错误: {error}")
                return f"抱歉，处理失败: {error[:100]}"
                
        except subprocess.TimeoutExpired:
            logger.error("Kimi处理超时")
            return "抱歉，处理时间过长，请稍后再试"
        except Exception as e:
            logger.error(f"调用Kimi失败: {e}")
            return f"抱歉，调用失败: {str(e)}"
    
    async def handle_messages(self):
        """处理来自云端的消息"""
        import websockets
        
        while True:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                msg_type = data.get('type')
                
                if msg_type == 'message':
                    # 收到微信消息，调用Kimi处理
                    logger.info(f"收到微信消息: {data.get('text', '')[:50]}...")
                    
                    response = await self.process_with_kimi(data)
                    
                    # 发送回复回云端
                    reply = {
                        "type": "response",
                        "msg_id": data.get('msg_id'),
                        "text": response,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.ws.send(json.dumps(reply))
                    logger.info("回复已发送回云端")
                    
                elif msg_type == 'ping':
                    # 心跳
                    await self.ws.send(json.dumps({"type": "pong"}))
                    
                else:
                    logger.info(f"收到未知消息类型: {msg_type}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("与云端服务器断开连接")
                break
            except json.JSONDecodeError as e:
                logger.error(f"收到无效JSON: {e}")
            except Exception as e:
                logger.error(f"处理消息错误: {e}")
    
    async def run(self):
        """运行客户端"""
        logger.info("=" * 60)
        logger.info("  混合架构 - 本地Kimi客户端")
        logger.info("=" * 60)
        logger.info("")
        
        if not await self.connect():
            logger.error("无法连接到云端服务器，请检查:")
            logger.error("  1. 云端服务器是否已启动")
            logger.error("  2. server_url 配置是否正确")
            logger.error("  3. 网络连接是否正常")
            return
        
        logger.info("✓ 客户端运行中，等待微信消息...")
        logger.info("  按 Ctrl+C 停止")
        logger.info("")
        
        try:
            await self.handle_messages()
        except KeyboardInterrupt:
            logger.info("客户端停止")
        finally:
            if self.ws:
                await self.ws.close()


async def main():
    """主函数"""
    # 检查命令行参数
    server_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    client = KimiLocalClient(server_url)
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
