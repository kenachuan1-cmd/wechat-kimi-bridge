#!/usr/bin/env python3
"""
持续刷新二维码直到扫码成功
"""

import subprocess
import sys
import time
import threading
import qrcode

def generate_qr(url, filename):
    """生成二维码图片"""
    try:
        qr = qrcode.QRCode(version=5, box_size=8, border=4, error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        img.save(filename)
        return True
    except Exception as e:
        print(f"生成二维码失败: {e}")
        return False

def main():
    print("="*70)
    print("持续获取微信登录二维码")
    print("="*70)
    print()
    
    # 启动桥接器
    print("启动桥接器...")
    proc = subprocess.Popen(
        [sys.executable, "wechat-kimi-bridge-stable.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='ignore'
    )
    
    # 读取输出
    for line in iter(proc.stdout.readline, ''):
        if not line:
            break
        
        line = line.strip()
        if not line:
            continue
        
        # 打印输出
        try:
            print(line)
        except:
            pass
        
        # 检测到二维码URL
        if 'weixin.qq.com' in line and 'http' in line:
            url = line.strip()
            if url.startswith('http'):
                print("\n" + "="*70)
                print("检测到二维码！")
                print("="*70)
                
                # 生成二维码
                filename = f"qr_latest.png"
                if generate_qr(url, filename):
                    print(f"二维码已保存到: {filename}")
                    print(f"链接: {url}")
                    print("\n请立即扫码！")
                    print("="*70 + "\n")
                
                # 继续等待登录成功
                print("等待登录确认...")
    
    proc.wait()

if __name__ == "__main__":
    main()
