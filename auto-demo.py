#!/usr/bin/env python3
"""
自动演示 - 运行测试对话
"""

import subprocess
import sys
import time
import threading

# 启动桥接器
proc = subprocess.Popen(
    [sys.executable, "wechat-kimi-bridge-stable.py", "--mock"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# 读取输出线程
def read_output():
    for line in iter(proc.stdout.readline, ''):
        if line:
            print(line, end='')

thread = threading.Thread(target=read_output)
thread.daemon = True
thread.start()

# 等待启动
time.sleep(3)

# 发送测试消息
test_messages = [
    "你好，请介绍一下自己",
    "/help",
    "@Kimi 写一个Python Hello World",
]

for msg in test_messages:
    print(f"\n[发送] {msg}")
    proc.stdin.write(msg + "\n")
    proc.stdin.flush()
    time.sleep(5)  # 等待回复

# 退出
proc.stdin.write("/quit\n")
proc.stdin.flush()
proc.wait()
print("\n演示完成")
