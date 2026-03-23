#!/usr/bin/env python3
"""
继续登录流程 - 扫码后启动桥接器
"""

import asyncio
import sys
import os

# 添加项目目录到路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入
import importlib.util
spec = importlib.util.spec_from_file_location("stable", "wechat-kimi-bridge-stable.py")
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)

Bridge = stable.Bridge
BridgeConfig = stable.BridgeConfig
GroupChatStrategy = stable.GroupChatStrategy

# 使用 SDK 的 Bot
from weixin_bot import WeixinBot

class RealBot(stable.BaseWeixinBot):
    def __init__(self, bot_name="Kimi"):
        super().__init__(bot_name)
        self._sdk = WeixinBot()
    
    async def login(self) -> bool:
        """登录（应该已经扫码完成）"""
        print("检查登录状态...")
        try:
            # 尝试登录，如果已扫码会自动成功
            result = await self._sdk._login(force=False)
            if result:
                print("[OK] 微信登录成功！")
                return True
            else:
                print("[FAIL] 登录失败，可能需要重新扫码")
                return False
        except Exception as e:
            print(f"[ERROR] 登录错误: {e}")
            return False
    
    async def send_text(self, user_id: str, text: str, group_id: str = None):
        try:
            if group_id:
                await self._sdk.send_text(group_id, text)
            else:
                await self._sdk.send_text(user_id, text)
        except Exception as e:
            print(f"发送失败: {e}")
    
    async def send_typing(self, user_id: str, group_id: str = None):
        try:
            target = group_id or user_id
            await self._sdk.send_typing(target)
        except:
            pass
    
    def _on_msg(self, raw_msg):
        """处理消息"""
        try:
            # 解析消息
            msg_type = raw_msg.get('msg_type', 1)
            text = raw_msg.get('content', '')
            is_at = False
            
            # 检查@
            at_list = raw_msg.get('at_list', [])
            if at_list:
                is_at = any(self.bot_name in at for at in at_list)
                for at in at_list:
                    text = text.replace(at, '').strip()
            
            if text.startswith(f'@{self.bot_name}'):
                is_at = True
                text = text[len(f'@{self.bot_name}'):].strip()
            
            msg = stable.WeChatMessage(
                msg_id=str(raw_msg.get('msg_id', __import__('uuid').uuid4())),
                user_id=raw_msg.get('from_user', {}).get('id', ''),
                user_name=raw_msg.get('from_user', {}).get('name', ''),
                text=text,
                msg_type=stable.MessageType.TEXT if msg_type == 1 else stable.MessageType.IMAGE,
                group_id=raw_msg.get('group_id') if raw_msg.get('is_group') else None,
                group_name=raw_msg.get('group_name'),
                is_at_me=is_at,
                image_url=raw_msg.get('image_url') if msg_type == 3 else None
            )
            
            self._dispatch(msg)
        except Exception as e:
            print(f"消息解析失败: {e}")
    
    async def run(self):
        """运行消息循环"""
        print("启动消息接收...")
        self._sdk.on_message(self._on_msg)
        await self._sdk.run()

async def main():
    print("="*60)
    print("WeChat-Kimi Bridge - 启动")
    print("="*60)
    print()
    
    # 创建桥接器
    config = stable.BridgeConfig(
        default_work_dir=".",
        group_strategy=GroupChatStrategy.PER_GROUP,
        bot_name="Kimi",
        auto_approve=True,
    )
    
    bridge = Bridge(config, use_mock=False)
    bridge.bot = RealBot(bot_name="Kimi")
    bridge.bot.on_message(lambda m: asyncio.create_task(bridge.handle(m)))
    
    # 登录
    if not await bridge.bot.login():
        print("\n登录失败，请重新扫码")
        print("运行: python login_script.py")
        return 1
    
    print("\n" + "="*60)
    print("微信登录成功！")
    print("="*60)
    print()
    print("现在可以:")
    print("  1. 私聊: 直接给机器人发消息")
    print("  2. 群聊: @Kimi 发送消息")
    print("  3. 图片: 发送图片并@Kimi")
    print("  4. 命令: /help 查看帮助")
    print()
    print("按 Ctrl+C 停止")
    print("="*60)
    print()
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        print("\n\n正在关闭...")
        await bridge.stop()
        print("已关闭")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
