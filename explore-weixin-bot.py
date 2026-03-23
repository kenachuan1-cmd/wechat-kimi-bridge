#!/usr/bin/env python3
"""
探索 weixin_bot 实际 API
"""

import asyncio
import json

async def explore():
    try:
        from weixin_bot import WeixinBot
        
        print("="*60)
        print("探索 weixin_bot API")
        print("="*60)
        
        bot = WeixinBot()
        
        # 列出所有属性和方法
        print("\n所有属性和方法:")
        for attr in dir(bot):
            if not attr.startswith('__'):
                try:
                    val = getattr(bot, attr)
                    if not callable(val):
                        print(f"  属性: {attr} = {val}")
                    else:
                        print(f"  方法: {attr}")
                except:
                    pass
        
        # 检查是否有消息相关方法
        print("\n消息相关:")
        msg_methods = [m for m in dir(bot) if 'msg' in m.lower() or 'message' in m.lower()]
        print(f"  找到: {msg_methods}")
        
        # 检查是否有 run 或 start 方法
        print("\n运行相关:")
        run_methods = [m for m in dir(bot) if m in ['run', 'start', 'serve', 'listen', 'poll']]
        print(f"  找到: {run_methods}")
        
        # 尝试登录
        print("\n尝试登录...")
        result = await bot._login(force=False)
        print(f"登录结果: {result}")
        
        if result:
            print("\n登录成功，等待消息...")
            print("请在微信发送测试消息")
            
            # 尝试多种方式获取消息
            for i in range(30):
                # 检查是否有 msg_queue
                if hasattr(bot, 'msg_queue'):
                    queue = bot.msg_queue
                    print(f"  发现消息队列: {type(queue)}")
                    if hasattr(queue, 'get') and callable(getattr(queue, 'get')):
                        try:
                            msg = await asyncio.wait_for(queue.get(), timeout=1)
                            print(f"  收到消息: {msg}")
                        except asyncio.TimeoutError:
                            pass
                
                # 检查是否有 updates
                if hasattr(bot, 'updates'):
                    updates = bot.updates
                    if updates:
                        print(f"  发现更新: {updates}")
                
                await asyncio.sleep(1)
                print(f"  等待... {i+1}/30")
                
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(explore())
