#!/usr/bin/env python3
"""
wechat-kimi-bridge-stable.py - 稳定版微信桥接器
使用更可靠的微信接入方式
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import aiohttp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wechat-kimi-bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ==================== 配置 ====================

class GroupChatStrategy(Enum):
    PER_GROUP = "per_group"
    PER_USER_IN_GROUP = "per_user"
    GLOBAL = "global"


@dataclass
class BridgeConfig:
    default_work_dir: str = "."
    group_strategy: GroupChatStrategy = GroupChatStrategy.PER_GROUP
    bot_name: str = "Kimi"
    max_image_size: int = 5 * 1024 * 1024
    message_buffer_time: float = 0.5
    max_message_length: int = 2000
    auto_approve: bool = True
    temp_dir: str = "./temp_images"


# ==================== 微信 Bot 基类 ====================

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"


@dataclass
class WeChatMessage:
    msg_id: str
    user_id: str
    user_name: str
    text: str
    msg_type: MessageType = MessageType.TEXT
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    is_at_me: bool = False
    image_url: Optional[str] = None
    
    @property
    def is_group(self) -> bool:
        return self.group_id is not None


class BaseWeixinBot:
    """微信 Bot 基类"""
    
    def __init__(self, bot_name: str = "Kimi"):
        self.bot_name = bot_name
        self._handlers: List[Callable] = []
        self._running = False
    
    def on_message(self, handler):
        self._handlers.append(handler)
        return handler
    
    def _dispatch(self, msg: WeChatMessage):
        """分发消息"""
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(msg))
                else:
                    handler(msg)
            except Exception as e:
                logger.error(f"消息处理失败: {e}")
    
    async def send_text(self, user_id: str, text: str, group_id: Optional[str] = None):
        raise NotImplementedError
    
    async def send_typing(self, user_id: str, group_id: Optional[str] = None):
        pass
    
    async def login(self) -> bool:
        raise NotImplementedError
    
    async def run(self):
        raise NotImplementedError


class MockWeixinBot(BaseWeixinBot):
    """模拟微信 Bot - 用于测试"""
    
    async def login(self) -> bool:
        logger.info("[Mock Bot] 模拟登录成功")
        return True
    
    async def send_text(self, user_id: str, text: str, group_id: Optional[str] = None):
        prefix = f"[群 {group_id}]" if group_id else f"[私聊 {user_id}]"
        print(f"\n{'='*60}")
        print(f"{prefix} Kimi 回复:")
        print(f"{'-'*60}")
        print(text[:2000])
        print(f"{'='*60}\n")
    
    async def run(self):
        """命令行交互模式"""
        self._running = True
        print("\n" + "="*60)
        print("Kimi 微信桥接器 - 命令行测试模式")
        print("="*60)
        print("\n命令:")
        print("  直接输入     - 模拟私聊")
        print("  @Kimi <消息> - 模拟群聊@")
        print("  /img <描述>  - 模拟图片")
        print("  /quit        - 退出")
        print("="*60 + "\n")
        
        msg_counter = 0
        
        while self._running:
            try:
                user_input = input("你 > ").strip()
                
                if not user_input:
                    continue
                
                if user_input == "/quit":
                    break
                
                # 解析输入
                is_group = user_input.startswith("@")
                is_image = user_input.startswith("/img")
                
                if is_image:
                    parts = user_input.split(maxsplit=1)
                    text = parts[1] if len(parts) > 1 else "描述这张图片"
                    msg_type = MessageType.IMAGE
                    image_url = "https://via.placeholder.com/400x300/4CAF50/FFFFFF?text=Test+Image"
                else:
                    text = user_input
                    msg_type = MessageType.TEXT
                    image_url = None
                    
                    if is_group:
                        text = text[5:].strip() if text.startswith("@Kimi") else text[1:].strip()
                
                msg_counter += 1
                
                # 创建消息
                msg = WeChatMessage(
                    msg_id=f"mock_{msg_counter}",
                    user_id=f"user_{msg_counter % 3 + 1}",
                    user_name=f"User{msg_counter % 3 + 1}",
                    text=text,
                    msg_type=msg_type,
                    group_id="test_group" if is_group else None,
                    group_name="测试群" if is_group else None,
                    is_at_me=is_group,
                    image_url=image_url
                )
                
                self._dispatch(msg)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"输入处理失败: {e}")


class WeixinBotSDKWrapper(BaseWeixinBot):
    """weixin-bot-sdk 包装器"""
    
    def __init__(self, bot_name: str = "Kimi"):
        super().__init__(bot_name)
        self._bot = None
        self._init_sdk()
    
    def _init_sdk(self):
        """初始化 SDK"""
        try:
            from weixin_bot import WeixinBot
            self._bot = WeixinBot()
        except ImportError:
            logger.error("weixin-bot-sdk 未安装")
            raise
    
    def login_sync(self):
        """同步登录（用于线程）"""
        try:
            # 在新的事件循环中运行登录
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._bot._login(force=False))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False
    
    async def login(self) -> bool:
        """登录"""
        logger.info("启动登录线程...")
        
        # 在线程中运行登录（避免事件循环冲突）
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.login_sync)
            result = await asyncio.get_event_loop().run_in_executor(None, future.result)
        
        return result
    
    async def send_text(self, user_id: str, text: str, group_id: Optional[str] = None):
        """发送文本"""
        try:
            if group_id:
                await self._bot.send_text(group_id, text)
            else:
                await self._bot.send_text(user_id, text)
        except Exception as e:
            logger.error(f"发送失败: {e}")
    
    async def send_typing(self, user_id: str, group_id: Optional[str] = None):
        """发送输入中状态"""
        try:
            target = group_id or user_id
            await self._bot.send_typing(target)
        except Exception:
            pass
    
    def _on_sdk_message(self, raw_msg):
        """处理 SDK 消息"""
        try:
            msg = self._parse_message(raw_msg)
            if msg:
                self._dispatch(msg)
        except Exception as e:
            logger.error(f"解析消息失败: {e}")
    
    def _parse_message(self, raw_msg) -> Optional[WeChatMessage]:
        """解析消息 - 处理对象或字典"""
        try:
            # 判断是否为对象（IncomingMessage）
            is_object = hasattr(raw_msg, '__dict__') or not isinstance(raw_msg, dict)
            
            if is_object:
                # 是 IncomingMessage 对象
                msg_type_code = getattr(raw_msg, 'msg_type', 1)
                content = getattr(raw_msg, 'content', '')
                at_list = getattr(raw_msg, 'at_list', [])
                msg_id = getattr(raw_msg, 'msg_id', str(uuid.uuid4()))
                
                # from_user 也可能是对象
                from_user = getattr(raw_msg, 'from_user', None)
                if from_user and hasattr(from_user, '__dict__'):
                    user_id = getattr(from_user, 'id', '')
                    user_name = getattr(from_user, 'name', '')
                elif from_user and isinstance(from_user, dict):
                    user_id = from_user.get('id', '')
                    user_name = from_user.get('name', '')
                else:
                    user_id = ''
                    user_name = ''
                
                group_id = getattr(raw_msg, 'group_id', None)
                is_group = getattr(raw_msg, 'is_group', False)
                group_name = getattr(raw_msg, 'group_name', None)
                image_url = getattr(raw_msg, 'image_url', None)
                if not image_url and msg_type_code == 3:
                    image_url = content
            else:
                # 是字典
                msg_type_code = raw_msg.get('msg_type', 1)
                content = raw_msg.get('content', '')
                at_list = raw_msg.get('at_list', [])
                msg_id = raw_msg.get('msg_id', str(uuid.uuid4()))
                from_user = raw_msg.get('from_user', {}) or {}
                user_id = from_user.get('id', '')
                user_name = from_user.get('name', '')
                group_id = raw_msg.get('group_id')
                is_group = raw_msg.get('is_group', False)
                group_name = raw_msg.get('group_name')
                image_url = raw_msg.get('image_url') or (content if msg_type_code == 3 else None)
            
            msg_type = MessageType.TEXT
            if msg_type_code == 3:
                msg_type = MessageType.IMAGE
            elif msg_type_code == 34:
                msg_type = MessageType.VOICE
            
            # 检查 @
            is_at_me = False
            text = content
            
            if at_list:
                is_at_me = any(self.bot_name in str(at) for at in at_list)
                for at in at_list:
                    text = text.replace(str(at), '').strip()
            
            if not is_at_me and text.startswith(f'@{self.bot_name}'):
                is_at_me = True
                text = text[len(f'@{self.bot_name}'):].strip()
            
            return WeChatMessage(
                msg_id=str(msg_id),
                user_id=user_id,
                user_name=user_name,
                text=text,
                msg_type=msg_type,
                group_id=group_id if is_group else None,
                group_name=group_name,
                is_at_me=is_at_me,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return None
    
    async def run(self):
        """运行消息循环"""
        # 注册消息处理器
        self._bot.on_message(self._on_sdk_message)
        
        # 在新线程中运行 SDK 的消息循环
        def run_sdk():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._bot.run())
            except Exception as e:
                logger.error(f"SDK 运行失败: {e}")
        
        import threading
        sdk_thread = threading.Thread(target=run_sdk, daemon=True)
        sdk_thread.start()
        
        # 保持主线程运行
        self._running = True
        while self._running:
            await asyncio.sleep(1)


# ==================== Kimi Wire 客户端 ====================

class KimiWireClient:
    """Kimi Wire 客户端"""
    
    def __init__(self, work_dir: str = ".", session_id: Optional[str] = None, auto_approve: bool = True):
        self.work_dir = work_dir
        self.session_id = session_id
        self.auto_approve = auto_approve
        self.process: Optional[subprocess.Process] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._handlers: List[Callable] = []
        self._msg_id = 0
        
    async def start(self):
        """启动"""
        cmd = ["kimi", "--wire", "-w", self.work_dir]
        if self.session_id:
            cmd.extend(["--session", self.session_id])
        else:
            cmd.append("--continue")
        
        if self.auto_approve:
            cmd.append("--yolo")
        
        logger.info(f"启动 Kimi: {' '.join(cmd)}")
        
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        asyncio.create_task(self._read_loop())
        asyncio.create_task(self._error_loop())
        
        await asyncio.sleep(0.5)
        await self._init()
        logger.info("Kimi 就绪")
    
    async def _error_loop(self):
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stderr.readline()
                if line:
                    logger.debug(f"[Kimi stderr] {line.decode().strip()}")
            except Exception:
                break
    
    async def _read_loop(self):
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                await self._handle(line.decode().strip())
            except Exception as e:
                logger.error(f"读取失败: {e}")
        logger.info("Kimi 进程退出")
    
    async def _handle(self, line: str):
        try:
            msg = json.loads(line)
            if "jsonrpc" not in msg:
                return
            
            if "id" in msg and ("result" in msg or "error" in msg):
                req_id = msg.get("id")
                if req_id in self._pending:
                    fut = self._pending.pop(req_id)
                    if "error" in msg:
                        fut.set_exception(Exception(msg["error"].get("message")))
                    else:
                        fut.set_result(msg.get("result", {}))
            
            elif msg.get("method") == "event":
                params = msg.get("params", {})
                event_type = params.get("type")
                payload = params.get("payload", {})
                
                for handler in self._handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(event_type, payload))
                        else:
                            handler(event_type, payload)
                    except Exception as e:
                        logger.error(f"事件处理失败: {e}")
            
            elif msg.get("method") == "request":
                req_id = msg.get("id")
                params = msg.get("params", {})
                req_type = params.get("type")
                payload = params.get("payload", {})
                
                if req_type == "ApprovalRequest":
                    resp = {"request_id": payload.get("id"), "response": "approve"}
                elif req_type == "QuestionRequest":
                    resp = {"request_id": payload.get("id"), "answers": {}}
                else:
                    resp = {}
                
                await self._send({"jsonrpc": "2.0", "id": req_id, "result": resp})
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def _init(self):
        await self._request("initialize", {
            "protocol_version": "1.5",
            "client": {"name": "wechat-kimi", "version": "1.0"},
            "capabilities": {"supports_question": True}
        })
    
    async def _request(self, method: str, params: dict) -> dict:
        self._msg_id += 1
        msg_id = str(self._msg_id)
        
        msg = {"jsonrpc": "2.0", "method": method, "id": msg_id, "params": params}
        
        fut = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = fut
        
        await self._send(msg)
        
        return await asyncio.wait_for(fut, timeout=300)
    
    async def _send(self, msg: dict):
        if not self.process or self.process.stdin.is_closing():
            raise Exception("Kimi 未运行")
        
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        self.process.stdin.write(line.encode())
        await self.process.stdin.drain()
    
    def on_event(self, handler):
        self._handlers.append(handler)
        return handler
    
    async def send_prompt(self, user_input: Union[str, List[dict]]) -> str:
        chunks = []
        
        def handler(event_type, payload):
            if event_type == "ContentPart" and payload.get("type") == "text":
                chunks.append(payload.get("text", ""))
        
        self.on_event(handler)
        
        try:
            await self._request("prompt", {"user_input": user_input})
        except Exception as e:
            logger.error(f"发送失败: {e}")
        
        return "".join(chunks)
    
    async def send_image(self, text: str, image_b64: str, mime: str):
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
            {"type": "text", "text": text}
        ]
        return await self.send_prompt(content)
    
    async def stop(self):
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except Exception:
                self.process.kill()
            self.process = None


# ==================== 会话管理 ====================

@dataclass
class ChatSession:
    key: str
    user_id: str
    group_id: Optional[str] = None
    work_dir: str = "."
    client: Optional[KimiWireClient] = None
    last_active: float = field(default_factory=time.time)
    msg_count: int = 0


class SessionManager:
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.sessions: Dict[str, ChatSession] = {}
    
    def get_key(self, msg: WeChatMessage) -> str:
        if not msg.is_group:
            return f"p:{msg.user_id}"
        if self.config.group_strategy == GroupChatStrategy.PER_GROUP:
            return f"g:{msg.group_id}"
        elif self.config.group_strategy == GroupChatStrategy.PER_USER_IN_GROUP:
            return f"g:{msg.group_id}:u:{msg.user_id}"
        return "global"
    
    async def get_or_create(self, msg: WeChatMessage) -> ChatSession:
        key = self.get_key(msg)
        
        if key not in self.sessions:
            logger.info(f"新建会话: {key}")
            self.sessions[key] = ChatSession(
                key=key,
                user_id=msg.user_id,
                group_id=msg.group_id,
                work_dir=self.config.default_work_dir
            )
        
        session = self.sessions[key]
        session.last_active = time.time()
        session.msg_count += 1
        
        return session


# ==================== 图片处理 ====================

class ImageProcessor:
    def __init__(self, config: BridgeConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def process(self, url: str) -> tuple:
        session = await self.get_session()
        
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"下载失败: {resp.status}")
            
            data = await resp.read()
            if len(data) > self.config.max_image_size:
                raise Exception("图片过大")
            
            mime = resp.headers.get('Content-Type', 'image/jpeg')
            b64 = base64.b64encode(data).decode()
            return b64, mime
    
    async def close(self):
        if self._session:
            await self._session.close()


# ==================== 主桥接器 ====================

class Bridge:
    def __init__(self, config: BridgeConfig, use_mock: bool = False):
        self.config = config
        
        if use_mock:
            self.bot = MockWeixinBot(config.bot_name)
        else:
            self.bot = WeixinBotSDKWrapper(config.bot_name)
        
        self.sessions = SessionManager(config)
        self.images = ImageProcessor(config)
        
        self.buffers: Dict[str, List[str]] = {}
        self.timers: Dict[str, asyncio.TimerHandle] = {}
    
    def should_handle(self, msg: WeChatMessage) -> bool:
        if not msg.is_group:
            return True
        return msg.is_at_me
    
    async def handle(self, msg: WeChatMessage):
        if not self.should_handle(msg):
            return
        
        await self.bot.send_typing(msg.user_id, msg.group_id)
        
        session = await self.sessions.get_or_create(msg)
        
        # 确保客户端
        if session.client is None:
            session.client = KimiWireClient(
                session.work_dir,
                auto_approve=self.config.auto_approve
            )
            await session.client.start()
        
        try:
            if msg.msg_type == MessageType.IMAGE and msg.image_url:
                await self._handle_image(msg, session)
            else:
                await self._handle_text(msg, session)
        except Exception as e:
            logger.error(f"处理失败: {e}")
            await self._send(msg, f"错误: {e}")
    
    async def _handle_text(self, msg: WeChatMessage, session: ChatSession):
        text = msg.text.strip()
        
        if text.startswith("/"):
            resp = await self._cmd(text, session)
            await self._send(msg, resp)
            return
        
        result = await session.client.send_prompt(text)
        await self._send(msg, result)
    
    async def _handle_image(self, msg: WeChatMessage, session: ChatSession):
        if not msg.image_url:
            await self._send(msg, "无法获取图片")
            return
        
        b64, mime = await self.images.process(msg.image_url)
        text = msg.text.strip() if msg.text else "描述图片"
        
        result = await session.client.send_image(text, b64, mime)
        await self._send(msg, result)
    
    async def _send(self, msg: WeChatMessage, text: str):
        max_len = self.config.max_message_length
        for i in range(0, len(text), max_len):
            chunk = text[i:i+max_len]
            await self.bot.send_text(msg.user_id, chunk, msg.group_id)
            if i + max_len < len(text):
                await asyncio.sleep(0.3)
    
    async def _cmd(self, text: str, session: ChatSession) -> str:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/help":
            return "命令: /new /clear /status /cd /compact /help"
        
        if cmd == "/new":
            if session.client:
                await session.client.stop()
                session.client = None
            return "新会话已创建"
        
        if cmd == "/clear":
            if session.client:
                await session.client.send_prompt("/clear")
            return "上下文已清空"
        
        if cmd == "/status":
            return f"会话: {session.key}, 消息: {session.msg_count}"
        
        if cmd == "/cd":
            if not arg:
                return f"当前: {session.work_dir}"
            if not os.path.exists(arg):
                return f"目录不存在: {arg}"
            session.work_dir = os.path.abspath(arg)
            if session.client:
                await session.client.stop()
                session.client = None
            return f"工作目录: {session.work_dir}"
        
        if cmd == "/compact":
            if session.client:
                await session.client.send_prompt("/compact")
            return "上下文已压缩"
        
        return f"未知命令: {cmd}"
    
    async def run(self):
        logger.info("="*60)
        logger.info("WeChat-Kimi Bridge 启动")
        logger.info(f"策略: {self.config.group_strategy.value}")
        logger.info("="*60)
        
        # 注册处理器
        self.bot.on_message(lambda m: asyncio.create_task(self.handle(m)))
        
        # 登录
        logger.info("登录中...")
        if await self.bot.login():
            logger.info("登录成功!")
        else:
            logger.error("登录失败")
            return
        
        # 运行
        await self.bot.run()
    
    async def stop(self):
        for session in self.sessions.sessions.values():
            if session.client:
                await session.client.stop()
        await self.images.close()


async def main():
    # 检查参数
    use_mock = "--mock" in sys.argv
    
    config = BridgeConfig(
        auto_approve=True,  # 测试时自动审批
    )
    
    bridge = Bridge(config, use_mock=use_mock)
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
