#!/usr/bin/env python3
"""
获取微信登录二维码并显示
"""

import asyncio
import sys
import subprocess
import threading
import time

# 尝试导入二维码
try:
    import qrcode
    QR_AVAILABLE = True
except:
    QR_AVAILABLE = False

def show_qr(url):
    """显示二维码"""
    print("\n" + "="*70)
    print("请用微信扫描下方二维码")
    print("="*70 + "\n")
    
    if QR_AVAILABLE:
        try:
            qr = qrcode.QRCode(version=3, box_size=3, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
            print()
        except Exception as e:
            print(f"[无法显示图形: {e}]")
    
    print(f"链接: {url}")
    print("\n" + "="*70)

def main():
    print("="*70)
    print("微信登录二维码获取")
    print("="*70)
    print()
    
    # 运行 weixin-bot 登录并捕获输出
    from weixin_bot import WeixinBot
    
    bot = WeixinBot()
    qr_url = None
    
    # 在新线程中运行登录
    result_container = {}
    
    def do_login():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 这会打印二维码URL
            result = loop.run_until_complete(bot._login(force=False))
            result_container['success'] = result
        except Exception as e:
            result_container['error'] = str(e)
        finally:
            loop.close()
    
    # 启动登录线程
    thread = threading.Thread(target=do_login)
    thread.daemon = True
    thread.start()
    
    # 等待二维码出现（从输出中捕获）
    print("正在获取二维码...")
    time.sleep(3)
    
    # 由于无法直接捕获输出，我们尝试直接运行并显示
    print("\n二维码通常在以下位置显示:")
    print("- 控制台输出")
    print("- 或浏览器打开链接")
    
    # 尝试通过打印到 stderr 来获取
    import io
    import contextlib
    
    # 重新运行以捕获输出
    print("\n重新获取二维码...\n")
    
    # 使用子进程运行
    proc = subprocess.Popen(
        [sys.executable, "-c", "
from weixin_bot import WeixinBot
import asyncio
bot = WeixinBot()
asyncio.run(bot._login(force=False))
"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # 读取输出，查找二维码URL
    lines = []
    start_time = time.time()
    qr_found = False
    
    while proc.poll() is None and time.time() - start_time < 30:
        line = proc.stdout.readline()
        if line:
            lines.append(line)
            print(line, end='')
            
            # 检查是否包含二维码URL
            if 'weixin.qq.com' in line or 'qrcode' in line.lower():
                url = line.strip()
                if url.startswith('http'):
                    show_qr(url)
                    qr_found = True
                    break
    
    if not qr_found:
        print("\n未在输出中找到二维码")
        print("\n完整输出:")
        print(''.join(lines))
    
    # 等待扫码完成
    if qr_found:
        print("\n等待扫码...")
        proc.wait()
    
    print("\n完成")

if __name__ == "__main__":
    main()
