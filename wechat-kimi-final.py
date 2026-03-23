#!/usr/bin/env python3
"""
WeChat-Kimi Bridge - 最终完整版
本地直连，无需云端，稳定可靠
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('wechat-kimi.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WechatKimiBridge:
    """微信-Kimi桥接器"""
    
    def __init__(self):
        self.bot = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.message_count = 0
        
    async def init_wechat(self) -> bool:
        """初始化微信连接"""
        try:
            from weixin_bot import WeixinBot
            
            logger.info("=" * 70)
            logger.info("  WeChat-Kimi Bridge 启动")
            logger.info("=" * 70)
            logger.info("")
            logger.info("正在初始化微信 Bot...")
            
            self.bot = WeixinBot()
            
            # 设置消息回调
            logger.info("注册消息处理器...")
            self.bot.on_message(self._on_message)
            
            # 扫码登录
            logger.info("")
            logger.info("请扫描二维码登录微信...")
            logger.info("（如果二维码没有自动弹出，请查看目录中的 qr_*.png 文件）")
            logger.info("")
            
            login_result = await self._login_with_retry()
            
            if login_result:
                logger.info("✅ 登录成功！")
                logger.info("")
                return True
            else:
                logger.error("❌ 登录失败")
                return False
                
        except ImportError:
            logger.error("❌ 未安装 weixin-bot-sdk")
            logger.info("请安装: pip install weixin-bot-sdk")
            return False
        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    async def _login_with_retry(self, max_retries: int = 3) -> bool:
        """带重试的登录"""
        for attempt in range(max_retries):
            try:
                logger.info(f"登录尝试 {attempt + 1}/{max_retries}...")
                result = await self.bot._login(force=False)
                if result:
                    return True
            except Exception as e:
                logger.warning(f"登录尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
        return False
    
    def _on_message(self, msg):
        """微信消息回调（在Bot线程中调用）"""
        try:
            # 将消息处理转到主事件循环
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._process_message(msg),
                    self.loop
                )
        except Exception as e:
            logger.error(f"消息回调错误: {e}")
    
    async def _process_message(self, msg):
        """处理消息"""
        try:
            self.message_count += 1
            msg_id = self.message_count
            
            # 解析消息
            msg_data = self._parse_message(msg)
            
            if not msg_data['text']:
                logger.debug("收到空消息，跳过")
                return
            
            logger.info(f"")
            logger.info(f"📩 [{msg_id}] 新消息")
            logger.info(f"   用户: {msg_data['user_name']} ({msg_data['user_id'][:20]}...)")
            logger.info(f"   内容: {msg_data['text'][:80]}{'...' if len(msg_data['text']) > 80 else ''}")
            
            # 调用Kimi处理
            logger.info(f"   正在调用 Kimi...")
            response = await self._call_kimi(msg_data['text'])
            
            # 发送回复
            logger.info(f"   Kimi回复: {response[:80]}{'...' if len(response) > 80 else ''}")
            
            if msg_data['user_id']:
                await self._send_reply(msg_data['user_id'], response)
                logger.info(f"✅ [{msg_id}] 回复已发送")
            else:
                logger.warning(f"⚠️  [{msg_id}] 无法发送回复（无用户ID）")
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
    
    def _parse_message(self, msg) -> dict:
        """解析微信消息"""
        result = {
            'msg_id': '',
            'user_id': '',
            'user_name': '',
            'text': '',
            'is_group': False,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if isinstance(msg, dict):
                result['msg_id'] = str(msg.get('msg_id', time.time()))
                result['text'] = msg.get('content', '') or msg.get('text', '')
                result['is_group'] = msg.get('is_group', False)
                
                # 解析用户信息
                from_user = msg.get('from_user', {})
                if isinstance(from_user, dict):
                    result['user_id'] = from_user.get('id', '')
                    result['user_name'] = from_user.get('name', '')
                else:
                    result['user_id'] = str(from_user)
                    
            else:
                # 如果是对象
                result['msg_id'] = str(getattr(msg, 'msg_id', time.time()))
                result['text'] = getattr(msg, 'content', '') or getattr(msg, 'text', '')
                result['is_group'] = getattr(msg, 'is_group', False)
                
                from_user = getattr(msg, 'from_user', None)
                if from_user:
                    result['user_id'] = getattr(from_user, 'id', '')
                    result['user_name'] = getattr(from_user, 'name', '')
                    
        except Exception as e:
            logger.error(f"解析消息失败: {e}")
            result['text'] = str(msg)
            
        return result
    
    async def _call_kimi(self, text: str) -> str:
        """调用本地Kimi CLI"""
        try:
            cmd = [
                "kimi",
                "--print",      # 非交互模式
                "--yolo",       # 自动确认
                "-c", text      # 输入文本
            ]
            
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,      # 2分钟超时
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # 提取最终回复（过滤中间步骤）
                lines = output.split('\n')
                # 找到最后一行非空的
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith('TurnBegin') and not line.startswith('StepBegin'):
                        return line
                return output[:500]  # 如果解析失败，返回前500字符
            else:
                error = result.stderr.strip()[:200]
                logger.error(f"Kimi错误: {error}")
                return f"抱歉，处理时出错了: {error}"
                
        except subprocess.TimeoutExpired:
            logger.error("Kimi调用超时")
            return "抱歉，处理时间过长，请稍后再试。"
        except Exception as e:
            logger.error(f"调用Kimi失败: {e}")
            return f"调用失败: {str(e)}"
    
    async def _send_reply(self, user_id: str, text: str):
        """发送回复到微信"""
        try:
            if not self.bot or not user_id:
                return
                
            # 截断过长消息（微信限制）
            max_length = 2000
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[消息已截断]"
            
            await self.bot.send_text(user_id, text)
            
        except Exception as e:
            logger.error(f"发送回复失败: {e}")
    
    def _run_bot_loop(self):
        """在独立线程中运行Bot消息循环"""
        try:
            logger.info("启动 Bot 消息循环...")
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行Bot（阻塞）
            loop.run_until_complete(self.bot.run())
            
        except Exception as e:
            logger.error(f"Bot循环错误: {e}", exc_info=True)
    
    async def run(self):
        """主运行函数"""
        # 保存主循环引用
        self.loop = asyncio.get_event_loop()
        
        # 初始化并登录
        if not await self.init_wechat():
            logger.error("启动失败，退出")
            return
        
        # 在后台线程启动Bot消息循环
        bot_thread = threading.Thread(target=self._run_bot_loop, daemon=True)
        bot_thread.start()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ 系统运行中！")
        logger.info("")
        logger.info("使用说明:")
        logger.info("  1. 在微信中给机器人发消息")
        logger.info("  2. 或在群里 @机器人")
        logger.info("  3. Kimi 会自动处理并回复")
        logger.info("")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 70)
        logger.info("")
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


def main():
    """入口函数"""
    bridge = WechatKimiBridge()
    
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 70)
        logger.info("系统已停止")
        logger.info("=" * 70)
    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
