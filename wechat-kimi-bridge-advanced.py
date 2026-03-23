#!/usr/bin/env python3
"""
wechat-kimi-bridge-advanced.py - 高级版微信-Kimi桥接器
支持功能：
1. 群聊支持（@触发、群隔离策略）
2. 图片识别（接收图片并分析）
3. 持久化会话管理
4. 流式输出

基于 Kimi Wire 协议实现
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import mimetypes
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path

import aiohttp
import aiofiles

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


# ==================== 配置类 ====================

class GroupChatStrategy(Enum):
    """群聊会话隔离策略"""
    PER_GROUP = "per_group"           # 按群隔离，群内共享上下文
    PER_USER_IN_GROUP = "per_user"    # 按用户+群隔离，每人独立上下文
    GLOBAL = "global"                 # 全局共享（不推荐）


@dataclass
class BridgeConfig:
    """桥接器配置"""
    default_work_dir: str = "."
    group_strategy: GroupChatStrategy = GroupChatStrategy.PER_GROUP
    bot_name: str = "Kimi"  # 机器人在群里的名称，用于@识别
    max_image_size: int = 5 * 1024 * 1024  # 最大图片 5MB
    supported_image_types: List[str] = field(default_factory=lambda: [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp'
    ])
    message_buffer_time: float = 0.5  # 流式消息缓冲时间（秒）
    max_message_length: int = 2000  # 微信单条消息最大长度
    enable_approval: bool = True  # 是否启用审批
    auto_approve: bool = False  # 是否自动通过审批
    temp_dir: str = "./temp_images"  # 临时图片存储目录


# ==================== 微信 Bot SDK (Mock/Real) ====================

class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"


@dataclass
class WeChatMessage:
    """微信消息结构"""
    msg_id: str
    user_id: str  # 发送者ID
    user_name: str  # 发送者昵称
    text: str
    msg_type: MessageType = MessageType.TEXT
    group_id: Optional[str] = None  # 群ID，私聊为None
    group_name: Optional[str] = None  # 群名称
    is_at_me: bool = False  # 是否在群里@了我
    image_url: Optional[str] = None  # 图片URL
    image_data: Optional[bytes] = None  # 图片二进制数据
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_group(self) -> bool:
        """是否为群消息"""
        return self.group_id is not None
    
    @property
    def session_key(self) -> str:
        """生成会话标识key"""
        if self.group_id:
            return f"group:{self.group_id}"
        return f"private:{self.user_id}"


class WeixinBotSDK:
    """
    微信 Bot SDK 封装
    实际使用时替换为真实的 weixin-bot SDK
    """
    
    def __init__(self, bot_name: str = "Kimi"):
        self.bot_name = bot_name
        self._message_handlers: List[Callable] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._bot_token: Optional[str] = None
        self._base_url: Optional[str] = None
        self._context_token: Optional[str] = None
        
    async def login(self) -> bool:
        """登录微信（扫码）"""
        logger.info("[BOT] 登录成功")
        self._session = aiohttp.ClientSession()
        return True
    
    async def get_updates(self) -> List[WeChatMessage]:
        """长轮询获取消息"""
        await asyncio.sleep(1)
        return []
    
    async def send_typing(self, user_id: str, group_id: Optional[str] = None):
        """发送正在输入状态"""
        logger.info(f"[TYPING] {'群' + group_id if group_id else '用户'} {user_id}")
    
    async def send_text(self, 
                       user_id: str, 
                       text: str, 
                       group_id: Optional[str] = None,
                       reply_to_msg_id: Optional[str] = None):
        """发送文本消息"""
        prefix = f"[群 {group_id}]" if group_id else f"[用户 {user_id}]"
        logger.info(f"{prefix} 发送: {text[:100]}...")
    
    async def send_image(self,
                        user_id: str,
                        image_path: str,
                        group_id: Optional[str] = None):
        """发送图片消息"""
        prefix = f"[群 {group_id}]" if group_id else f"[用户 {user_id}]"
        logger.info(f"{prefix} 发送图片: {image_path}")
    
    def on_message(self, handler: Callable[[WeChatMessage], Any]):
        """注册消息处理器"""
        self._message_handlers.append(handler)
        return handler
    
    async def run(self):
        """启动消息轮询循环"""
        logger.info("[BOT] 消息轮询已启动")
        while True:
            try:
                messages = await self.get_updates()
                for msg in messages:
                    for handler in self._message_handlers:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(msg))
                        else:
                            handler(msg)
            except Exception as e:
                logger.error(f"消息轮询错误: {e}")
                await asyncio.sleep(5)
    
    async def download_image(self, image_url: str) -> bytes:
        """下载图片"""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        async with self._session.get(image_url) as resp:
            if resp.status == 200:
                return await resp.read()
            raise Exception(f"下载图片失败: {resp.status}")
    
    def parse_message(self, raw_msg: dict) -> WeChatMessage:
        """解析微信消息"""
        msg_type_str = raw_msg.get('msg_type', 'text')
        msg_type = MessageType.TEXT
        
        if msg_type_str == 'image':
            msg_type = MessageType.IMAGE
        elif msg_type_str == 'voice':
            msg_type = MessageType.VOICE
        elif msg_type_str == 'file':
            msg_type = MessageType.FILE
        
        group_id = raw_msg.get('group_id')
        text = raw_msg.get('content', '')
        is_at_me = False
        
        if group_id:
            at_pattern = f"@{self.bot_name}"
            if at_pattern in text or raw_msg.get('is_at'):
                is_at_me = True
                text = text.replace(at_pattern, '').strip()
        
        return WeChatMessage(
            msg_id=raw_msg.get('msg_id', str(uuid.uuid4())),
            user_id=raw_msg.get('from_user_id', ''),
            user_name=raw_msg.get('from_user_name', ''),
            text=text,
            msg_type=msg_type,
            group_id=group_id,
            group_name=raw_msg.get('group_name'),
            is_at_me=is_at_me,
            image_url=raw_msg.get('image_url') if msg_type == MessageType.IMAGE else None
        )


# ==================== Kimi Wire 客户端 ====================

class KimiWireClient:
    """Kimi Wire 协议客户端"""
    
    def __init__(self, 
                 work_dir: str = ".", 
                 session_id: Optional[str] = None,
                 config: Optional[BridgeConfig] = None):
        self.work_dir = work_dir
        self.session_id = session_id
        self.config = config or BridgeConfig()
        self.process: Optional[subprocess.Process] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._event_handlers: List[Callable[[str, dict], None]] = []
        self._message_id_counter = 0
        self._initialized = False
        self.protocol_version = "1.5"
        self._current_turn_chunks: List[str] = []
        
    async def start(self):
        """启动 Kimi Wire 进程"""
        cmd = ["kimi", "--wire", "-w", self.work_dir]
        if self.session_id:
            cmd.extend(["--session", self.session_id])
        elif self.session_id is None:
            cmd.append("--continue")
        
        if self.config.auto_approve:
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
        await self._initialize()
        
        logger.info("Kimi Wire 客户端已就绪")
        
    async def _error_loop(self):
        """读取错误输出"""
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stderr.readline()
                if line:
                    logger.debug(f"[Kimi stderr] {line.decode('utf-8').strip()}")
            except Exception:
                break
                
    async def _read_loop(self):
        """读取 stdout 的循环"""
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                    
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                    
                await self._handle_message(line)
                
            except Exception as e:
                logger.error(f"读取消息失败: {e}")
                
        logger.info("Kimi 进程已退出")
    
    async def _handle_message(self, line: str):
        """处理来自 Kimi 的消息"""
        try:
            msg = json.loads(line)
            
            if "jsonrpc" not in msg:
                return
            
            if "id" in msg and ("result" in msg or "error" in msg):
                await self._handle_response(msg)
            elif "method" in msg and "id" not in msg:
                await self._handle_notification(msg)
            elif "method" in msg and "id" in msg:
                await self._handle_request(msg)
                
        except json.JSONDecodeError:
            logger.warning(f"JSON 解析失败: {line[:100]}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def _handle_response(self, msg: dict):
        """处理响应"""
        req_id = msg.get("id")
        if req_id in self._pending_requests:
            future = self._pending_requests.pop(req_id)
            if "error" in msg:
                future.set_exception(Exception(msg["error"].get("message", "Unknown error")))
            else:
                future.set_result(msg.get("result", {}))
    
    async def _handle_notification(self, msg: dict):
        """处理事件通知"""
        method = msg.get("method")
        params = msg.get("params", {})
        
        if method == "event":
            event_type = params.get("type")
            payload = params.get("payload", {})
            
            if event_type == "ContentPart" and payload.get("type") == "text":
                self._current_turn_chunks.append(payload.get("text", ""))
            
            await self._dispatch_event(event_type, payload)
    
    async def _handle_request(self, msg: dict):
        """处理来自 Kimi 的请求"""
        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})
        
        if method == "request":
            req_type = params.get("type")
            payload = params.get("payload", {})
            
            if req_type == "ApprovalRequest":
                response = await self._handle_approval_request(payload)
            elif req_type == "QuestionRequest":
                response = await self._handle_question_request(payload)
            elif req_type == "ToolCallRequest":
                response = await self._handle_tool_call(payload)
            else:
                response = {"error": f"Unknown request type: {req_type}"}
            
            await self._send_response(req_id, response)
    
    async def _handle_approval_request(self, payload: dict) -> dict:
        """处理审批请求"""
        if not self.config.enable_approval or self.config.auto_approve:
            return {
                "request_id": payload.get("id"),
                "response": "approve"
            }
        
        await self._dispatch_event("approval_request", payload)
        
        return {
            "request_id": payload.get("id"),
            "response": "approve"
        }
    
    async def _handle_question_request(self, payload: dict) -> dict:
        """处理问题请求"""
        await self._dispatch_event("question_request", payload)
        return {
            "request_id": payload.get("id"),
            "answers": {}
        }
    
    async def _handle_tool_call(self, payload: dict) -> dict:
        """处理工具调用"""
        tool_id = payload.get("id")
        name = payload.get("name")
        
        return {
            "tool_call_id": tool_id,
            "return_value": {
                "is_error": True,
                "output": f"工具 {name} 未实现",
                "message": f"工具 {name} 在此环境中不可用",
                "display": []
            }
        }
    
    async def _dispatch_event(self, event_type: str, payload: dict):
        """分发事件"""
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, payload)
                else:
                    handler(event_type, payload)
            except Exception as e:
                logger.error(f"事件处理器失败: {e}")
    
    def on_event(self, handler: Callable[[str, dict], None]):
        """注册事件处理器"""
        self._event_handlers.append(handler)
        return handler
    
    async def _initialize(self):
        """初始化握手"""
        result = await self._request("initialize", {
            "protocol_version": self.protocol_version,
            "client": {
                "name": "wechat-kimi-bridge",
                "version": "1.0.0"
            },
            "capabilities": {
                "supports_question": True,
                "supports_plan_mode": True
            }
        })
        
        self.protocol_version = result.get("protocol_version", "1.5")
        self._initialized = True
        
        if self.session_id:
            await self._replay_history()
    
    async def _replay_history(self):
        """回放历史"""
        try:
            result = await self._request("replay", {})
            logger.info(f"历史回放完成: {result.get('events', 0)} 事件")
        except Exception as e:
            logger.warning(f"回放失败: {e}")
    
    async def _request(self, method: str, params: dict) -> dict:
        """发送 JSON-RPC 请求"""
        self._message_id_counter += 1
        msg_id = str(self._message_id_counter)
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "id": msg_id,
            "params": params
        }
        
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[msg_id] = future
        
        await self._send_message(message)
        
        try:
            return await asyncio.wait_for(future, timeout=300)
        except asyncio.TimeoutError:
            self._pending_requests.pop(msg_id, None)
            raise Exception(f"请求超时: {method}")
    
    async def _send_response(self, msg_id: str, result: dict):
        """发送响应"""
        message = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }
        await self._send_message(message)
    
    async def _send_message(self, message: dict):
        """发送消息"""
        if not self.process or self.process.stdin.is_closing():
            raise Exception("Kimi 进程未运行")
        
        line = json.dumps(message, ensure_ascii=False) + "\n"
        self.process.stdin.write(line.encode('utf-8'))
        await self.process.stdin.drain()
    
    async def send_prompt(self, user_input: Union[str, List[dict]]) -> dict:
        """发送用户输入"""
        self._current_turn_chunks = []
        return await self._request("prompt", {"user_input": user_input})
    
    async def send_image_prompt(self, text: str, image_base64: str, image_type: str = "image/png"):
        """发送带图片的消息"""
        content = []
        
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image_type};base64,{image_base64}"
            }
        })
        
        if text:
            content.append({
                "type": "text",
                "text": text
            })
        
        return await self.send_prompt(content)
    
    async def steer(self, user_input: str) -> dict:
        """追加输入"""
        return await self._request("steer", {"user_input": user_input})
    
    async def cancel(self):
        """取消当前轮次"""
        return await self._request("cancel", {})
    
    async def stop(self):
        """停止进程"""
        if self.process:
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=5)
            self.process = None
    
    def get_current_output(self) -> str:
        """获取当前轮次的完整输出"""
        return "".join(self._current_turn_chunks)


# ==================== 会话管理 ====================

@dataclass
class ChatSession:
    """聊天会话"""
    session_key: str
    user_id: str
    group_id: Optional[str] = None
    work_dir: str = "."
    kimi_session_id: Optional[str] = None
    kimi_client: Optional[KimiWireClient] = None
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0
    created_at: float = field(default_factory=time.time)
    
    def touch(self):
        self.last_activity = time.time()
        self.message_count += 1
    
    @property
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """检查是否过期"""
        return time.time() - self.last_activity > timeout_hours * 3600


class SessionManager:
    """会话管理器"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.sessions: Dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()
        
        os.makedirs(config.temp_dir, exist_ok=True)
    
    def _get_session_key(self, msg: WeChatMessage) -> str:
        """根据策略生成会话 key"""
        if not msg.is_group:
            return f"private:{msg.user_id}"
        
        if self.config.group_strategy == GroupChatStrategy.PER_GROUP:
            return f"group:{msg.group_id}"
        elif self.config.group_strategy == GroupChatStrategy.PER_USER_IN_GROUP:
            return f"group:{msg.group_id}:user:{msg.user_id}"
        else:
            return "global"
    
    async def get_or_create_session(self, msg: WeChatMessage) -> ChatSession:
        """获取或创建会话"""
        session_key = self._get_session_key(msg)
        
        async with self._lock:
            if session_key not in self.sessions:
                logger.info(f"创建新会话: {session_key}")
                self.sessions[session_key] = ChatSession(
                    session_key=session_key,
                    user_id=msg.user_id,
                    group_id=msg.group_id,
                    work_dir=self.config.default_work_dir
                )
            
            session = self.sessions[session_key]
            session.touch()
            return session
    
    async def get_session(self, session_key: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.sessions.get(session_key)
    
    async def remove_session(self, session_key: str):
        """移除会话"""
        async with self._lock:
            if session_key in self.sessions:
                session = self.sessions.pop(session_key)
                if session.kimi_client:
                    await session.kimi_client.stop()
    
    async def cleanup_expired(self):
        """清理过期会话"""
        async with self._lock:
            expired_keys = [
                key for key, session in self.sessions.items()
                if session.is_expired
            ]
            for key in expired_keys:
                session = self.sessions.pop(key)
                if session.kimi_client:
                    await session.kimi_client.stop()
                logger.info(f"清理过期会话: {key}")
    
    async def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": sum(
                1 for s in self.sessions.values() 
                if not s.is_expired
            ),
            "strategy": self.config.group_strategy.value
        }


# ==================== 图片处理器 ====================

class ImageProcessor:
    """图片处理器"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def download_image(self, url: str) -> Tuple[bytes, str]:
        """下载图片"""
        session = await self._get_session()
        
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"下载失败: HTTP {resp.status}")
            
            data = await resp.read()
            
            if len(data) > self.config.max_image_size:
                raise Exception(f"图片过大: {len(data)} bytes")
            
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            return data, content_type
    
    def encode_base64(self, data: bytes) -> str:
        """编码为 base64"""
        return base64.b64encode(data).decode('utf-8')
    
    async def process_image(self, image_url: str) -> Tuple[str, str]:
        """处理图片：下载并编码"""
        data, mime_type = await self.download_image(image_url)
        
        if mime_type not in self.config.supported_image_types:
            raise Exception(f"不支持的图片类型: {mime_type}")
        
        base64_str = self.encode_base64(data)
        return base64_str, mime_type
    
    async def save_temp_image(self, data: bytes, ext: str = "jpg") -> str:
        """保存临时图片"""
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(self.config.temp_dir, filename)
        
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(data)
        
        return filepath
    
    async def cleanup_temp_images(self, max_age_hours: int = 24):
        """清理临时图片"""
        now = time.time()
        for filename in os.listdir(self.config.temp_dir):
            filepath = os.path.join(self.config.temp_dir, filename)
            try:
                stat = os.stat(filepath)
                if now - stat.st_mtime > max_age_hours * 3600:
                    os.remove(filepath)
                    logger.debug(f"清理临时图片: {filename}")
            except Exception as e:
                logger.error(f"清理失败 {filename}: {e}")
    
    async def close(self):
        """关闭"""
        if self._session:
            await self._session.close()


# ==================== 主桥接器 ====================

class WeChatKimiBridge:
    """微信-Kimi 桥接器（高级版）"""
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self.bot = WeixinBotSDK(bot_name=self.config.bot_name)
        self.session_manager = SessionManager(self.config)
        self.image_processor = ImageProcessor(self.config)
        
        self._message_buffers: Dict[str, List[str]] = {}
        self._buffer_timers: Dict[str, asyncio.TimerHandle] = {}
        
        self.bot.on_message(self._handle_message)
        
        self._running = False
    
    async def _handle_message(self, msg: WeChatMessage):
        """处理微信消息"""
        try:
            if not self._should_handle(msg):
                return
            
            await self.bot.send_typing(msg.user_id, msg.group_id)
            
            session = await self.session_manager.get_or_create_session(msg)
            
            if session.kimi_client is None:
                session.kimi_client = KimiWireClient(
                    work_dir=session.work_dir,
                    session_id=session.kimi_session_id,
                    config=self.config
                )
                session.kimi_client.on_event(
                    lambda t, p: self._on_kimi_event(t, p, session)
                )
                await session.kimi_client.start()
            
            if msg.msg_type == MessageType.IMAGE:
                await self._handle_image_message(msg, session)
            else:
                await self._handle_text_message(msg, session)
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            await self._send_reply(msg, f"处理失败: {str(e)}")
    
    def _should_handle(self, msg: WeChatMessage) -> bool:
        """判断是否应该处理此消息"""
        if not msg.is_group:
            return True
        
        if msg.is_group and msg.is_at_me:
            return True
        
        if msg.msg_type == MessageType.IMAGE:
            if not msg.is_group or msg.is_at_me:
                return True
        
        return False
    
    async def _handle_text_message(self, msg: WeChatMessage, session: ChatSession):
        """处理文本消息"""
        text = msg.text.strip()
        
        if text.startswith("/"):
            response = await self._handle_command(msg, text, session)
            await self._send_reply(msg, response)
            return
        
        kimi = session.kimi_client
        if not kimi:
            await self._send_reply(msg, "Kimi 客户端未就绪")
            return
        
        try:
            stream_handler = self._create_stream_handler(msg)
            kimi.on_event(stream_handler)
            
            result = await kimi.send_prompt(text)
            
            await self._flush_buffer(msg)
            
            logger.info(f"会话 {session.session_key}: 处理了 {len(text)} 字符的文本")
            
        except Exception as e:
            logger.error(f"Kimi 调用失败: {e}")
            await self._send_reply(msg, f"Kimi 响应失败: {str(e)}")
    
    async def _handle_image_message(self, msg: WeChatMessage, session: ChatSession):
        """处理图片消息"""
        if not msg.image_url:
            await self._send_reply(msg, "无法获取图片")
            return
        
        try:
            logger.info(f"下载图片: {msg.image_url}")
            base64_str, mime_type = await self.image_processor.process_image(msg.image_url)
            
            accompanying_text = msg.text.strip() if msg.text else "描述这张图片"
            
            kimi = session.kimi_client
            
            stream_handler = self._create_stream_handler(msg)
            kimi.on_event(stream_handler)
            
            await kimi.send_image_prompt(accompanying_text, base64_str, mime_type)
            
            await self._flush_buffer(msg)
            
            logger.info(f"会话 {session.session_key}: 处理了图片 ({mime_type})")
            
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            await self._send_reply(msg, f"图片处理失败: {str(e)}")
    
    def _create_stream_handler(self, msg: WeChatMessage) -> Callable:
        """创建流式输出处理器"""
        buffer_key = f"{msg.user_id}:{msg.group_id or 'private'}"
        
        async def handler(event_type: str, payload: dict):
            if event_type == "ContentPart" and payload.get("type") == "text":
                text = payload.get("text", "")
                await self._buffer_and_send(buffer_key, msg, text)
        
        return handler
    
    async def _buffer_and_send(self, buffer_key: str, msg: WeChatMessage, text: str):
        """缓冲并发送流式输出"""
        if buffer_key not in self._message_buffers:
            self._message_buffers[buffer_key] = []
        
        self._message_buffers[buffer_key].append(text)
        
        if buffer_key in self._buffer_timers:
            self._buffer_timers[buffer_key].cancel()
        
        buffer = self._message_buffers[buffer_key]
        current_text = "".join(buffer)
        
        if len(current_text) >= self.config.max_message_length:
            await self._flush_buffer_for_key(buffer_key, msg)
        else:
            loop = asyncio.get_event_loop()
            self._buffer_timers[buffer_key] = loop.call_later(
                self.config.message_buffer_time,
                lambda: asyncio.create_task(
                    self._flush_buffer_for_key(buffer_key, msg)
                )
            )
    
    async def _flush_buffer(self, msg: WeChatMessage):
        """刷新指定消息的缓冲"""
        buffer_key = f"{msg.user_id}:{msg.group_id or 'private'}"
        await self._flush_buffer_for_key(buffer_key, msg)
    
    async def _flush_buffer_for_key(self, buffer_key: str, msg: WeChatMessage):
        """刷新指定 key 的缓冲"""
        if buffer_key not in self._message_buffers:
            return
        
        buffer = self._message_buffers.pop(buffer_key, [])
        if not buffer:
            return
        
        text = "".join(buffer)
        if not text.strip():
            return
        
        await self._send_reply(msg, text)
    
    async def _send_reply(self, msg: WeChatMessage, text: str):
        """发送回复"""
        max_len = self.config.max_message_length
        for i in range(0, len(text), max_len):
            chunk = text[i:i + max_len]
            await self.bot.send_text(
                msg.user_id,
                chunk,
                group_id=msg.group_id
            )
            if i + max_len < len(text):
                await asyncio.sleep(0.3)
    
    async def _handle_command(self, 
                             msg: WeChatMessage, 
                             text: str, 
                             session: ChatSession) -> str:
        """处理命令"""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        commands = {
            "/help": self._cmd_help,
            "/new": self._cmd_new,
            "/clear": self._cmd_clear,
            "/cd": self._cmd_cd,
            "/status": self._cmd_status,
            "/compact": self._cmd_compact,
            "/mode": self._cmd_mode,
            "/stats": self._cmd_stats,
        }
        
        handler = commands.get(cmd)
        if handler:
            return await handler(msg, arg, session)
        
        return f"未知命令 `{cmd}`，使用 /help 查看帮助"
    
    async def _cmd_help(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """帮助命令"""
        return """Kimi 微信助手

基础命令：
/help - 显示此帮助
/new - 开启新会话
/clear - 清空上下文
/status - 查看会话状态

工作目录：
/cd <路径> - 切换工作目录

高级：
/compact - 压缩上下文
/mode <strategy> - 切换群聊模式
  per_group - 群内共享上下文
  per_user - 群内每人独立上下文
/stats - 查看全局统计

使用说明：
- 私聊：直接发送消息
- 群聊：@我后发送消息
- 图片：发送图片（可加描述）"""

    async def _cmd_new(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """新会话命令"""
        if session.kimi_client:
            await session.kimi_client.stop()
            session.kimi_client = None
        
        session.kimi_session_id = None
        return "已开启新会话，上下文已重置"

    async def _cmd_clear(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """清空命令"""
        if session.kimi_client:
            try:
                await session.kimi_client.send_prompt("/clear")
                return "上下文已清空"
            except Exception as e:
                return f"清空失败: {str(e)}"
        return "无活动会话"

    async def _cmd_cd(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """切换目录命令"""
        if not arg:
            return f"当前工作目录: `{session.work_dir}`"
        
        if not os.path.exists(arg):
            return f"目录不存在: `{arg}`"
        
        session.work_dir = os.path.abspath(arg)
        
        if session.kimi_client:
            await session.kimi_client.stop()
            session.kimi_client = None
        
        return f"工作目录切换至: `{session.work_dir}`"

    async def _cmd_status(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """状态命令"""
        from datetime import datetime
        
        return f"""会话状态

会话 Key: {session.session_key}
工作目录: {session.work_dir}
消息数: {session.message_count}
创建时间: {datetime.fromtimestamp(session.created_at).strftime('%Y-%m-%d %H:%M')}
最后活动: {datetime.fromtimestamp(session.last_activity).strftime('%H:%M:%S')}

群聊策略: {self.config.group_strategy.value}
Kimi 在线: {'是' if session.kimi_client else '否'}"""

    async def _cmd_compact(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """压缩命令"""
        if session.kimi_client:
            try:
                await session.kimi_client.send_prompt("/compact")
                return "上下文已压缩"
            except Exception as e:
                return f"压缩失败: {str(e)}"
        return "无活动会话"

    async def _cmd_mode(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """切换模式命令"""
        if not arg:
            return f"当前模式: `{self.config.group_strategy.value}`"
        
        strategy_map = {
            "per_group": GroupChatStrategy.PER_GROUP,
            "per_user": GroupChatStrategy.PER_USER_IN_GROUP,
            "global": GroupChatStrategy.GLOBAL,
        }
        
        if arg not in strategy_map:
            return "无效模式，可选: per_group, per_user, global"
        
        self.config.group_strategy = strategy_map[arg]
        return f"群聊策略已切换为: `{arg}`"

    async def _cmd_stats(self, msg: WeChatMessage, arg: str, session: ChatSession) -> str:
        """统计命令"""
        stats = await self.session_manager.get_stats()
        return f"""全局统计

总会话数: {stats['total_sessions']}
活跃会话: {stats['active_sessions']}
当前策略: {stats['strategy']}"""

    async def _on_kimi_event(self, event_type: str, payload: dict, session: ChatSession):
        """处理 Kimi 事件"""
        if event_type == "approval_request":
            logger.info(f"审批请求: {payload.get('description', 'N/A')}")
    
    async def _maintenance_loop(self):
        """维护循环"""
        while self._running:
            try:
                await self.session_manager.cleanup_expired()
                await self.image_processor.cleanup_temp_images()
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"维护任务失败: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """启动桥接器"""
        self._running = True
        
        logger.info("=" * 60)
        logger.info("WeChat-Kimi Bridge (Advanced) 启动中...")
        logger.info(f"群聊策略: {self.config.group_strategy.value}")
        logger.info(f"工作目录: {self.config.default_work_dir}")
        logger.info("=" * 60)
        
        asyncio.create_task(self._maintenance_loop())
        
        logger.info("请扫码登录微信...")
        await self.bot.login()
        
        logger.info("桥接器已启动，按 Ctrl+C 停止")
        await self.bot.run()
    
    async def stop(self):
        """停止桥接器"""
        self._running = False
        logger.info("正在关闭服务...")
        
        for session_key in list(self.session_manager.sessions.keys()):
            await self.session_manager.remove_session(session_key)
        
        await self.image_processor.close()
        
        logger.info("服务已停止")


async def main():
    """主入口"""
    config = BridgeConfig(
        default_work_dir=".",
        group_strategy=GroupChatStrategy.PER_GROUP,
        bot_name="Kimi",
        enable_approval=True,
        auto_approve=False,
    )
    
    bridge = WeChatKimiBridge(config)
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
