#!/usr/bin/env python3
"""
wechat-kimi-bridge-real.py - 真实微信接入版
使用 weixin-bot-sdk 连接真实微信

功能：
1. 私聊对话
2. 群聊@触发
3. 图片识别
4. 持久化会话
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import aiohttp
from weixin_bot import WeixinBot

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
    """群聊会话隔离策略"""
    PER_GROUP = "per_group"
    PER_USER_IN_GROUP = "per_user"
    GLOBAL = "global"


@dataclass
class BridgeConfig:
    """桥接器配置"""
    default_work_dir: str = "."
    group_strategy: GroupChatStrategy = GroupChatStrategy.PER_GROUP
    bot_name: str = "Kimi"
    max_image_size: int = 5 * 1024 * 1024
    supported_image_types: List[str] = field(default_factory=lambda: [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp'
    ])
    message_buffer_time: float = 0.5
    max_message_length: int = 2000
    enable_approval: bool = True
    auto_approve: bool = False
    temp_dir: str = "./temp_images"
    
    # 微信相关配置
    allowed_groups: List[str] = field(default_factory=list)  # 允许的群列表，空表示全部
    allowed_users: List[str] = field(default_factory=list)  # 允许的用户列表
    blocked_groups: List[str] = field(default_factory=list)  # 屏蔽的群
    blocked_users: List[str] = field(default_factory=list)  # 屏蔽的用户


# ==================== 消息类型适配 ====================

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"


@dataclass
class WeChatMessage:
    """统一消息格式"""
    msg_id: str
    user_id: str
    user_name: str
    text: str
    msg_type: MessageType = MessageType.TEXT
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    is_at_me: bool = False
    image_url: Optional[str] = None
    image_data: Optional[bytes] = None
    raw_message: Optional[dict] = None
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_group(self) -> bool:
        return self.group_id is not None
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.is_group:
            return f"{self.group_name or self.group_id}/{self.user_name}"
        return self.user_name or self.user_id


def parse_weixin_message(raw_msg: dict, bot_name: str) -> Optional[WeChatMessage]:
    """
    解析 weixin-bot-sdk 消息格式
    
    weixin-bot-sdk 消息格式示例:
    {
        "msg_id": "...",
        "msg_type": 1,  # 1=文本, 3=图片, 34=语音, etc.
        "from_user": {
            "id": "wxid_xxx",
            "name": "用户名"
        },
        "to_user": {...},
        "content": "消息内容",
        "is_group": true,
        "group_id": "...",
        "group_name": "群名",
        "at_list": ["@Kimi"],
        "image_url": "..."  # 图片消息
    }
    """
    try:
        msg_type_code = raw_msg.get('msg_type', 1)
        
        # 映射消息类型
        msg_type = MessageType.TEXT
        image_url = None
        
        if msg_type_code == 3:  # 图片
            msg_type = MessageType.IMAGE
            image_url = raw_msg.get('image_url') or raw_msg.get('content')
        elif msg_type_code == 34:  # 语音
            msg_type = MessageType.VOICE
        elif msg_type_code == 43:  # 视频
            msg_type = MessageType.VIDEO
        elif msg_type_code == 49:  # 文件
            msg_type = MessageType.FILE
        
        # 检查是否@了我
        is_at_me = False
        text = raw_msg.get('content', '')
        at_list = raw_msg.get('at_list', [])
        
        if at_list:
            is_at_me = any(bot_name in at for at in at_list)
            # 移除@文本
            for at in at_list:
                text = text.replace(at, '').strip()
        
        # 也可能是通过 @BotName 触发的
        if not is_at_me and text.startswith(f'@{bot_name}'):
            is_at_me = True
            text = text[len(f'@{bot_name}'):].strip()
        
        return WeChatMessage(
            msg_id=str(raw_msg.get('msg_id', uuid.uuid4())),
            user_id=raw_msg.get('from_user', {}).get('id', ''),
            user_name=raw_msg.get('from_user', {}).get('name', ''),
            text=text,
            msg_type=msg_type,
            group_id=raw_msg.get('group_id') if raw_msg.get('is_group') else None,
            group_name=raw_msg.get('group_name'),
            is_at_me=is_at_me,
            image_url=image_url,
            raw_message=raw_msg
        )
        
    except Exception as e:
        logger.error(f"解析消息失败: {e}")
        return None


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
        """读取 stdout"""
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
        """处理消息"""
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
        """处理通知"""
        method = msg.get("method")
        params = msg.get("params", {})
        
        if method == "event":
            event_type = params.get("type")
            payload = params.get("payload", {})
            
            if event_type == "ContentPart" and payload.get("type") == "text":
                self._current_turn_chunks.append(payload.get("text", ""))
            
            await self._dispatch_event(event_type, payload)
    
    async def _handle_request(self, msg: dict):
        """处理请求"""
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
        logger.info(f"审批请求: {payload.get('action')} - {payload.get('description')}")
        
        if not self.config.enable_approval or self.config.auto_approve:
            return {"request_id": payload.get("id"), "response": "approve"}
        
        await self._dispatch_event("approval_request", payload)
        
        # TODO: 这里应该等待用户在微信中回复
        return {"request_id": payload.get("id"), "response": "approve"}
    
    async def _handle_question_request(self, payload: dict) -> dict:
        """处理问题请求"""
        await self._dispatch_event("question_request", payload)
        return {"request_id": payload.get("id"), "answers": {}}
    
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
        """初始化"""
        result = await self._request("initialize", {
            "protocol_version": self.protocol_version,
            "client": {"name": "wechat-kimi-bridge", "version": "1.0.0"},
            "capabilities": {"supports_question": True, "supports_plan_mode": True}
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
        """发送请求"""
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
        """发送 prompt"""
        self._current_turn_chunks = []
        return await self._request("prompt", {"user_input": user_input})
    
    async def send_image_prompt(self, text: str, image_base64: str, image_type: str = "image/png"):
        """发送带图片的消息"""
        content = []
        
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{image_type};base64,{image_base64}"}
        })
        
        if text:
            content.append({"type": "text", "text": text})
        
        return await self.send_prompt(content)
    
    async def stop(self):
        """停止"""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutExpired:
                self.process.kill()
            self.process = None


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
        return time.time() - self.last_activity > timeout_hours * 3600


class SessionManager:
    """会话管理器"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.sessions: Dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()
        os.makedirs(config.temp_dir, exist_ok=True)
    
    def _get_session_key(self, msg: WeChatMessage) -> str:
        """生成会话 key"""
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


# ==================== 图片处理器 ====================

class ImageProcessor:
    """图片处理器"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
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
        return base64.b64encode(data).decode('utf-8')
    
    async def process_image(self, image_url: str) -> Tuple[str, str]:
        """处理图片"""
        data, mime_type = await self.download_image(image_url)
        
        if mime_type not in self.config.supported_image_types:
            raise Exception(f"不支持的图片类型: {mime_type}")
        
        base64_str = self.encode_base64(data)
        return base64_str, mime_type
    
    async def close(self):
        if self._session:
            await self._session.close()


# ==================== 主桥接器 ====================

class WeChatKimiBridge:
    """微信-Kimi 桥接器"""
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self.bot = WeixinBot()
        self.session_manager = SessionManager(self.config)
        self.image_processor = ImageProcessor(self.config)
        
        self._message_buffers: Dict[str, List[str]] = {}
        self._buffer_timers: Dict[str, asyncio.TimerHandle] = {}
        self._running = False
    
    def _should_handle(self, msg: WeChatMessage) -> bool:
        """判断是否应该处理"""
        # 检查黑名单
        if msg.user_id in self.config.blocked_users:
            return False
        if msg.group_id and msg.group_id in self.config.blocked_groups:
            return False
        
        # 检查白名单
        if self.config.allowed_users and msg.user_id not in self.config.allowed_users:
            pass  # 继续检查其他条件
        
        if self.config.allowed_groups and msg.group_id:
            if msg.group_id not in self.config.allowed_groups:
                return False
        
        # 私聊消息：直接处理
        if not msg.is_group:
            return True
        
        # 群聊消息：需要@我
        if msg.is_group and msg.is_at_me:
            return True
        
        # 群聊图片：检查是否@我
        if msg.msg_type == MessageType.IMAGE and msg.is_group:
            return msg.is_at_me
        
        return False
    
    async def _handle_weixin_message(self, raw_msg: dict):
        """处理微信消息"""
        try:
            # 解析消息
            msg = parse_weixin_message(raw_msg, self.config.bot_name)
            if not msg:
                return
            
            logger.info(f"收到消息 [{msg.display_name}]: {msg.text[:50]}...")
            
            # 判断是否处理
            if not self._should_handle(msg):
                logger.debug(f"忽略消息: {msg.display_name}")
                return
            
            # 显示输入中
            if msg.is_group:
                await self.bot.send_typing(msg.group_id)
            else:
                await self.bot.send_typing(msg.user_id)
            
            # 获取会话
            session = await self.session_manager.get_or_create_session(msg)
            
            # 确保 Kimi 客户端已启动
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
            
            # 处理消息
            if msg.msg_type == MessageType.IMAGE:
                await self._handle_image_message(msg, session)
            else:
                await self._handle_text_message(msg, session)
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            try:
                await self._send_reply(msg, f"处理失败: {str(e)}")
            except:
                pass
    
    async def _handle_text_message(self, msg: WeChatMessage, session: ChatSession):
        """处理文本消息"""
        text = msg.text.strip()
        
        # 处理命令
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
            
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            await self._send_reply(msg, f"图片处理失败: {str(e)}")
    
    def _create_stream_handler(self, msg: WeChatMessage) -> Callable:
        """创建流式处理器"""
        buffer_key = f"{msg.user_id}:{msg.group_id or 'private'}"
        
        async def handler(event_type: str, payload: dict):
            if event_type == "ContentPart" and payload.get("type") == "text":
                text = payload.get("text", "")
                await self._buffer_and_send(buffer_key, msg, text)
        
        return handler
    
    async def _buffer_and_send(self, buffer_key: str, msg: WeChatMessage, text: str):
        """缓冲发送"""
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
        buffer_key = f"{msg.user_id}:{msg.group_id or 'private'}"
        await self._flush_buffer_for_key(buffer_key, msg)
    
    async def _flush_buffer_for_key(self, buffer_key: str, msg: WeChatMessage):
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
            
            if msg.is_group:
                await self.bot.send_text(msg.group_id, chunk)
            else:
                await self.bot.send_text(msg.user_id, chunk)
            
            if i + max_len < len(text):
                await asyncio.sleep(0.3)
    
    async def _handle_command(self, msg: WeChatMessage, text: str, session: ChatSession) -> str:
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
        }
        
        handler = commands.get(cmd)
        if handler:
            return await handler(msg, arg, session)
        
        return f"未知命令 `{cmd}`，使用 /help 查看帮助"
    
    async def _cmd_help(self, msg, arg, session) -> str:
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
/mode <策略> - 切换群聊模式"""

    async def _cmd_new(self, msg, arg, session) -> str:
        if session.kimi_client:
            await session.kimi_client.stop()
            session.kimi_client = None
        session.kimi_session_id = None
        return "已开启新会话"

    async def _cmd_clear(self, msg, arg, session) -> str:
        if session.kimi_client:
            try:
                await session.kimi_client.send_prompt("/clear")
                return "上下文已清空"
            except Exception as e:
                return f"清空失败: {str(e)}"
        return "无活动会话"

    async def _cmd_cd(self, msg, arg, session) -> str:
        if not arg:
            return f"当前工作目录: {session.work_dir}"
        if not os.path.exists(arg):
            return f"目录不存在: {arg}"
        session.work_dir = os.path.abspath(arg)
        if session.kimi_client:
            await session.kimi_client.stop()
            session.kimi_client = None
        return f"工作目录切换至: {session.work_dir}"

    async def _cmd_status(self, msg, arg, session) -> str:
        from datetime import datetime
        return f"""会话状态

会话: {session.session_key}
工作目录: {session.work_dir}
消息数: {session.message_count}
创建: {datetime.fromtimestamp(session.created_at).strftime('%Y-%m-%d %H:%M')}
策略: {self.config.group_strategy.value}"""

    async def _cmd_compact(self, msg, arg, session) -> str:
        if session.kimi_client:
            try:
                await session.kimi_client.send_prompt("/compact")
                return "上下文已压缩"
            except Exception as e:
                return f"压缩失败: {str(e)}"
        return "无活动会话"

    async def _cmd_mode(self, msg, arg, session) -> str:
        if not arg:
            return f"当前: {self.config.group_strategy.value}"
        
        strategy_map = {
            "per_group": GroupChatStrategy.PER_GROUP,
            "per_user": GroupChatStrategy.PER_USER_IN_GROUP,
            "global": GroupChatStrategy.GLOBAL,
        }
        
        if arg not in strategy_map:
            return "无效模式，可选: per_group, per_user, global"
        
        self.config.group_strategy = strategy_map[arg]
        return f"群聊策略: {arg}"
    
    async def _on_kimi_event(self, event_type: str, payload: dict, session: ChatSession):
        """处理 Kimi 事件"""
        if event_type == "approval_request":
            logger.info(f"审批: {payload.get('description')}")
    
    async def _maintenance_loop(self):
        """维护循环"""
        while self._running:
            try:
                await self.session_manager.cleanup_expired()
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"维护失败: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """启动"""
        self._running = True
        
        logger.info("=" * 60)
        logger.info("WeChat-Kimi Bridge (Real) 启动")
        logger.info(f"策略: {self.config.group_strategy.value}")
        logger.info(f"目录: {self.config.default_work_dir}")
        logger.info("=" * 60)
        
        # 启动维护任务
        asyncio.create_task(self._maintenance_loop())
        
        # 登录微信
        logger.info("正在登录微信...")
        # 注意：weixin_bot SDK 的 login() 内部调用了 asyncio.run()
        # 我们需要直接调用其内部方法
        try:
            # 尝试使用异步登录
            await self.bot._login(force=False)
        except RuntimeError:
            # 如果已经在事件循环中，使用线程执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await asyncio.get_event_loop().run_in_executor(
                    pool, lambda: asyncio.run(self.bot._login(force=False))
                )
        logger.info("微信登录成功!")
        
        # 注册消息处理器
        def on_msg(raw_msg):
            # 创建新任务处理消息
            asyncio.create_task(self._handle_weixin_message(raw_msg))
        
        self.bot.on_message(on_msg)
        
        # 启动消息轮询
        logger.info("启动消息处理...")
        await self.bot.run()
    
    async def stop(self):
        """停止"""
        self._running = False
        logger.info("正在关闭...")
        
        for key in list(self.session_manager.sessions.keys()):
            await self.session_manager.remove_session(key)
        
        await self.image_processor.close()
        logger.info("已关闭")


async def main():
    """主入口"""
    config = BridgeConfig(
        default_work_dir=".",
        group_strategy=GroupChatStrategy.PER_GROUP,
        bot_name="Kimi",
        enable_approval=True,
        auto_approve=False,  # 生产环境建议设为 False，手动审批
    )
    
    bridge = WeChatKimiBridge(config)
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
