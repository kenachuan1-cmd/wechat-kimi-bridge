#!/usr/bin/env python3
"""
真实微信启动器 - 捕获并显示二维码
"""

import asyncio
import threading
import sys
import os
import io
import json
from typing import Optional

# 添加项目目录到路径
sys.path.insert(0, os.path.dirname(__file__))

# 尝试导入二维码生成器
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("[提示] 安装 qrcode 库可在终端显示二维码: pip install qrcode[pil]")

# 导入主程序
import importlib.util
spec = importlib.util.spec_from_file_location("stable", "wechat-kimi-bridge-stable.py")
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)

Bridge = stable.Bridge
BridgeConfig = stable.BridgeConfig
GroupChatStrategy = stable.GroupChatStrategy


class QRCodeWeixinBot(stable.BaseWeixinBot):
    """捕获二维码的微信Bot"""
    
    def __init__(self, bot_name="Kimi"):
        super().__init__(bot_name)
        self._qr_url = None
        self._qr_image = None
        self._sdk_bot = None
        
    async def login(self) -> bool:
        """异步登录，捕获二维码"""
        try:
            from weixin_bot import WeixinBot
            
            self._sdk_bot = WeixinBot()
            
            # 显示提示
            print("\n" + "="*60)
            print("正在获取登录二维码...")
            print("="*60 + "\n")
            
            # 登录（会输出二维码URL到控制台）
            result = await self._sdk_bot._login(force=False)
            
            # 显示二维码
            self._display_qr()
            
            return result
            
        except Exception as e:
            print(f"登录错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_text(self, user_id: str, text: str, group_id: Optional[str] = None):
        """发送文本消息"""
        try:
            if group_id:
                await self._sdk_bot.send_text(group_id, text)
            else:
                await self._sdk_bot.send_text(user_id, text)
        except Exception as e:
            print(f"发送失败: {e}")
    
    async def send_typing(self, user_id: str, group_id: Optional[str] = None):
        """发送输入中状态"""
        try:
            target = group_id or user_id
            await self._sdk_bot.send_typing(target)
        except:
            pass
    
    def _display_qr(self):
        """显示二维码"""
        if not self._qr_url and not QR_AVAILABLE:
            return
            
        print("\n" + "="*60)
        print("请扫描下方二维码登录微信")
        print("="*60 + "\n")
        
        if QR_AVAILABLE and self._qr_url:
            try:
                # 生成并显示ASCII二维码
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=1,
                    border=2,
                )
                qr.add_data(self._qr_url)
                qr.make(fit=True)
                
                # 打印ASCII二维码
                qr.print_ascii(invert=True)
                print()
            except Exception as e:
                print(f"[无法显示二维码图形: {e}]")
        
        if self._qr_url:
            print(f"二维码链接: {self._qr_url}")
            print("\n如果无法扫描，请复制上方链接到浏览器打开")
        
        print("-"*60)
        print("等待扫码...")
        print("-"*60 + "\n")
    
    async def run(self):
        """运行消息循环"""
        # 注册消息处理器
        self._sdk_bot.on_message(self._on_sdk_message)
        
        # 运行SDK的消息循环
        await self._sdk_bot.run()
    
    def _on_sdk_message(self, raw_msg):
        """处理SDK消息"""
        try:
            msg = self._parse_message(raw_msg)
            if msg:
                self._dispatch(msg)
        except Exception as e:
            print(f"解析消息失败: {e}")
    
    def _parse_message(self, raw_msg: dict):
        """解析消息"""
        try:
            msg_type_code = raw_msg.get('msg_type', 1)
            
            msg_type = stable.MessageType.TEXT
            image_url = None
            
            if msg_type_code == 3:
                msg_type = stable.MessageType.IMAGE
                image_url = raw_msg.get('image_url') or raw_msg.get('content')
            
            # 检查@
            is_at_me = False
            text = raw_msg.get('content', '')
            at_list = raw_msg.get('at_list', [])
            
            if at_list:
                is_at_me = any(self.bot_name in at for at in at_list)
                for at in at_list:
                    text = text.replace(at, '').strip()
            
            if not is_at_me and text.startswith(f'@{self.bot_name}'):
                is_at_me = True
                text = text[len(f'@{self.bot_name}'):].strip()
            
            return stable.WeChatMessage(
                msg_id=str(raw_msg.get('msg_id', __import__('uuid').uuid4())),
                user_id=raw_msg.get('from_user', {}).get('id', ''),
                user_name=raw_msg.get('from_user', {}).get('name', ''),
                text=text,
                msg_type=msg_type,
                group_id=raw_msg.get('group_id') if raw_msg.get('is_group') else None,
                group_name=raw_msg.get('group_name'),
                is_at_me=is_at_me,
                image_url=image_url
            )
        except Exception as e:
            print(f"解析失败: {e}")
            return None


async def main():
    print("="*60)
    print("WeChat-Kimi Bridge - 真实微信模式")
    print("="*60)
    print()
    
    config = BridgeConfig(
        default_work_dir=".",
        group_strategy=GroupChatStrategy.PER_GROUP,
        bot_name="Kimi",
        auto_approve=True,
    )
    
    # 创建桥接器
    bridge = Bridge(config, use_mock=False)
    
    # 使用带二维码的Bot
    bridge.bot = QRCodeWeixinBot(bot_name=config.bot_name)
    bridge.bot.on_message(lambda m: asyncio.create_task(bridge.handle(m)))
    
    print("准备登录微信...")
    print()
    
    try:
        # 登录（会显示二维码）
        if await bridge.bot.login():
            print("\n[OK] 微信登录成功！")
            print()
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
            print("\n[FAIL] 登录失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n正在关闭...")
        await bridge.stop()
        print("已关闭")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
