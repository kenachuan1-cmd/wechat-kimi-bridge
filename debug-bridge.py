#!/usr/bin/env python3
"""
调试工具 - 检查消息流转
在 Codespaces 运行此脚本查看微信消息
"""

import asyncio
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_wechat():
    """调试微信连接"""
    try:
        from weixin_bot import WeixinBot
        
        logger.info("="*60)
        logger.info("微信连接调试工具")
        logger.info("="*60)
        
        bot = WeixinBot()
        
        # 尝试所有可能的消息获取方式
        logger.info("检查可用的方法...")
        methods = [m for m in dir(bot) if not m.startswith('_')]
        logger.info(f"可用方法: {methods}")
        
        # 登录
        logger.info("尝试登录...")
        result = await bot._login(force=False)
        logger.info(f"登录结果: {result}")
        
        if result:
            logger.info("登录成功，开始监听消息...")
            logger.info("请在微信发送一条测试消息")
            
            # 尝试不同的消息获取方式
            for i in range(30):  # 监听30秒
                logger.info(f"监听中... {i+1}/30")
                
                # 方法1: get_updates
                if hasattr(bot, 'get_updates'):
                    try:
                        updates = await bot.get_updates()
                        if updates:
                            logger.info(f"收到更新: {updates}")
                    except Exception as e:
                        logger.debug(f"get_updates 失败: {e}")
                
                # 方法2: get_messages
                if hasattr(bot, 'get_messages'):
                    try:
                        messages = await bot.get_messages()
                        if messages:
                            logger.info(f"收到消息: {messages}")
                    except Exception as e:
                        logger.debug(f"get_messages 失败: {e}")
                
                await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"调试失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(debug_wechat())
