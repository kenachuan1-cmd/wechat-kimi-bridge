#!/usr/bin/env python3
"""
运行并捕获二维码
"""

import subprocess
import sys
import re
import time

print("="*70)
print("启动微信登录 (实时捕获二维码)")
print("="*70)
print()

# 运行 weixin_bot 并实时捕获输出
proc = subprocess.Popen(
    [sys.executable, "login_script.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='ignore'
)

print("等待二维码出现...\n")

qr_shown = False
try:
    import qrcode
    HAS_QR = True
except:
    HAS_QR = False

for line in iter(proc.stdout.readline, ''):
    if not line:
        break
    
    line = line.strip()
    if not line:
        continue
    
    # 打印所有输出（处理编码问题）
    try:
        print(line)
    except:
        print(line.encode('utf-8', errors='ignore').decode('ascii', errors='ignore'))
    
    # 查找二维码URL
    if 'weixin.qq.com' in line and 'http' in line:
        url = line.strip()
        print("\n" + "="*70)
        print("找到二维码!")
        print("="*70)
        
        # 显示二维码
        if HAS_QR:
            print()
            try:
                qr = qrcode.QRCode(version=3, box_size=3, border=2)
                qr.add_data(url)
                qr.make(fit=True)
                qr.print_ascii(invert=True)
                print()
            except:
                pass
        
        print(f"\n链接: {url}")
        print("\n请用微信扫描上方二维码")
        print("="*70 + "\n")
        qr_shown = True

proc.wait()

if not qr_shown:
    print("\n未能捕获到二维码")
