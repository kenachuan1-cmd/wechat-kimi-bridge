#!/usr/bin/env python3
"""
简化版 - 直接与 Kimi Wire 对话
"""

import asyncio
import json
import subprocess
import sys

class SimpleKimiWire:
    def __init__(self):
        self.process = None
        self.msg_id = 0
        
    async def start(self):
        cmd = ["kimi", "--wire", "-w", ".", "--yolo"]
        print(f"启动: {' '.join(cmd)}")
        
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        asyncio.create_task(self._read_output())
        await asyncio.sleep(1)
        
        # 初始化
        await self._send({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": "1",
            "params": {
                "protocol_version": "1.5",
                "client": {"name": "simple-chat", "version": "1.0"}
            }
        })
        print("[OK] Kimi 已就绪\n")
        
    async def _read_output(self):
        while self.process and self.process.returncode is None:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                data = json.loads(line.decode().strip())
                
                # 显示文本输出
                if data.get("method") == "event":
                    params = data.get("params", {})
                    if params.get("type") == "ContentPart":
                        payload = params.get("payload", {})
                        if payload.get("type") == "text":
                            text = payload.get("text", "")
                            print(text, end="", flush=True)
                
                # 轮次结束
                if data.get("result") and data.get("id") == str(self.msg_id):
                    print("\n")
                    
            except Exception as e:
                pass
                
    async def _send(self, msg):
        if not self.process:
            return
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        self.process.stdin.write(line.encode('utf-8'))
        await self.process.stdin.drain()
        
    async def chat(self, text):
        self.msg_id += 1
        await self._send({
            "jsonrpc": "2.0",
            "method": "prompt",
            "id": str(self.msg_id),
            "params": {"user_input": text}
        })
        # 等待回复
        await asyncio.sleep(0.5)
        
    async def stop(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()

async def main():
    print("="*60)
    print("Kimi 简易对话")
    print("="*60)
    print("输入消息与 Kimi 对话，输入 /quit 退出\n")
    
    kimi = SimpleKimiWire()
    await kimi.start()
    
    try:
        while True:
            user_input = input("你 > ").strip()
            if user_input == "/quit":
                break
            if not user_input:
                continue
                
            print("Kimi > ", end="", flush=True)
            await kimi.chat(user_input)
            await asyncio.sleep(2)  # 等待完整回复
            
    except KeyboardInterrupt:
        pass
    finally:
        await kimi.stop()
        print("\n再见！")

if __name__ == "__main__":
    asyncio.run(main())
