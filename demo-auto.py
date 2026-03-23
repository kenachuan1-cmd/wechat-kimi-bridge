#!/usr/bin/env python3
"""
自动演示版本 - 自动发送测试消息，无需人工输入
"""

import asyncio
import importlib.util
import sys

# 动态导入主程序（处理文件名中的连字符）
spec = importlib.util.spec_from_file_location("stable", "wechat-kimi-bridge-stable.py")
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)

Bridge = stable.Bridge
BridgeConfig = stable.BridgeConfig
GroupChatStrategy = stable.GroupChatStrategy
WeChatMessage = stable.WeChatMessage
MessageType = stable.MessageType
MockWeixinBot = stable.MockWeixinBot

class AutoDemoBot(MockWeixinBot):
    """自动演示Bot - 自动发送预设消息"""
    
    def __init__(self, bot_name="Kimi"):
        super().__init__(bot_name)
        self.test_messages = [
            # (user_id, text, is_group, delay)
            ("user_1", "你好，请介绍一下自己", False, 3),
            ("user_2", "@Kimi 写一个Python快速排序", True, 5),
            ("user_1", "/help", False, 2),
            ("user_3", "@Kimi 1+1等于几", True, 3),
        ]
        self.msg_index = 0
    
    async def run(self):
        """自动运行测试"""
        print("\n" + "="*60)
        print("Kimi Bridge - 自动演示模式")
        print("="*60)
        print(f"\n将自动发送 {len(self.test_messages)} 条测试消息:\n")
        
        for i, (user, text, is_group, delay) in enumerate(self.test_messages, 1):
            prefix = "[群聊]" if is_group else "[私聊]"
            print(f"{i}. {prefix} {user}: {text[:40]}")
        
        print("\n" + "="*60 + "\n")
        
        for user_id, text, is_group, delay in self.test_messages:
            self.msg_index += 1
            
            print(f"\n>>> 消息 {self.msg_index}/{len(self.test_messages)}")
            print(f"用户: {user_id}")
            print(f"内容: {text}")
            print("-" * 40)
            
            # 创建消息
            is_at = is_group
            clean_text = text[5:].strip() if text.startswith("@Kimi") else text
            
            msg = WeChatMessage(
                msg_id=f"demo_{self.msg_index}",
                user_id=user_id,
                user_name=f"User_{user_id}",
                text=clean_text,
                msg_type=MessageType.TEXT,
                group_id="demo_group" if is_group else None,
                group_name="Demo群" if is_group else None,
                is_at_me=is_at
            )
            
            # 分发
            self._dispatch(msg)
            
            # 等待回复完成
            await asyncio.sleep(delay)
        
        print("\n" + "="*60)
        print("演示完成！")
        print("="*60)
        
        # 保持运行一段时间
        await asyncio.sleep(2)

async def main():
    config = BridgeConfig(
        default_work_dir=".",
        group_strategy=GroupChatStrategy.PER_GROUP,
        bot_name="Kimi",
        auto_approve=True,
        message_buffer_time=0.1,  # 快速输出
    )
    
    # 创建桥接器
    bridge = Bridge(config, use_mock=True)
    
    # 替换为自动演示Bot
    bridge.bot = AutoDemoBot(bot_name=config.bot_name)
    bridge.bot.on_message(lambda m: asyncio.create_task(bridge.handle(m)))
    
    print("启动自动演示...")
    print("注意: 这将启动 Kimi Wire 进程并发送真实请求")
    print()
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        pass
    finally:
        # 清理
        for session in bridge.sessions.sessions.values():
            if session.client:
                await session.client.stop()
        await bridge.images.close()

if __name__ == "__main__":
    asyncio.run(main())
