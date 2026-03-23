#!/usr/bin/env python3
"""
真实微信启动器 - 处理登录和二维码显示
"""

import asyncio
import threading
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

# 自定义微信Bot，显示二维码
class RealWeixinBot(stable.WeixinBotSDKWrapper):
    def login_sync(self):
        """同步登录，显示二维码"""
        try:
            import asyncio as aio
            loop = aio.new_event_loop()
            aio.set_event_loop(loop)
            
            # 这里 weixin_bot 会自动显示二维码
            print("\n" + "="*60)
            print("请扫描二维码登录微信")
            print("="*60 + "\n")
            
            result = loop.run_until_complete(self._bot._login(force=False))
            loop.close()
            return result
        except Exception as e:
            print(f"登录错误: {e}")
            return False

async def main():
    print("="*60)
    print("WeChat-Kimi Bridge - 真实微信模式")
    print("="*60)
    print()
    
    config = BridgeConfig(
        default_work_dir=".",
        group_strategy=GroupChatStrategy.PER_GROUP,
        bot_name="Kimi",
        auto_approve=True,  # 自动审批，生产环境可设为False
    )
    
    # 创建桥接器
    bridge = Bridge(config, use_mock=False)
    
    # 替换为真实Bot
    bridge.bot = RealWeixinBot(bot_name=config.bot_name)
    bridge.bot.on_message(lambda m: asyncio.create_task(bridge.handle(m)))
    
    print("准备登录微信...")
    print("提示: 如果二维码显示为链接，请复制到浏览器打开")
    print()
    
    try:
        # 登录
        if await bridge.bot.login():
            print("\n✓ 微信登录成功！")
            print("现在可以:")
            print("  1. 私聊: 直接给机器人发消息")
            print("  2. 群聊: @机器人发送消息")
            print("  3. 命令: /help 查看帮助")
            print()
            print("按 Ctrl+C 停止")
            print("-"*60)
            
            # 运行主循环
            await bridge.run()
        else:
            print("\n✗ 登录失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n正在关闭...")
        await bridge.stop()
        print("已关闭")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
