#!/usr/bin/env python3
"""
桥接诊断工具 - 排查消息流转问题
"""

import urllib.request
import ssl
import json
import time

CLOUD_URL = "https://boulevard-knowing-implementation-evans.trycloudflare.com"
LOCAL_URL = "http://localhost:8766"

def test_cloud():
    """测试云端"""
    print("="*60)
    print("1. 测试云端服务器")
    print("="*60)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        response = urllib.request.urlopen(
            f"{CLOUD_URL}/status", 
            timeout=10, 
            context=ctx
        )
        data = json.loads(response.read().decode())
        print(f"✓ 云端可访问")
        print(f"  微信连接: {data.get('wechat_connected')}")
        print(f"  待处理消息: {data.get('pending_messages')}")
        return data.get('wechat_connected', False)
    except Exception as e:
        print(f"✗ 云端连接失败: {e}")
        return False


def test_local():
    """测试本地服务器"""
    print()
    print("="*60)
    print("2. 测试本地服务器")
    print("="*60)
    
    try:
        response = urllib.request.urlopen(
            f"{LOCAL_URL}/status", 
            timeout=5
        )
        data = json.loads(response.read().decode())
        print(f"✓ 本地服务器运行中")
        print(f"  云端地址: {data.get('cloud_url')}")
        return True
    except Exception as e:
        print(f"✗ 本地服务器未响应: {e}")
        return False


def test_message_flow():
    """测试消息流转"""
    print()
    print("="*60)
    print("3. 测试消息流转")
    print("="*60)
    
    # 模拟微信消息发送到本地
    test_msg = {
        "msg_id": "test_diag_001",
        "user_id": "user_test",
        "user_name": "诊断测试",
        "text": "你好，这是一个测试消息",
        "is_group": False,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    print(f"发送测试消息: {test_msg['text']}")
    
    try:
        req = urllib.request.Request(
            f"{LOCAL_URL}/receive",
            data=json.dumps(test_msg).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        response = urllib.request.urlopen(req, timeout=60)
        result = json.loads(response.read().decode())
        print(f"✓ 本地处理成功")
        print(f"  状态: {result.get('status')}")
        print(f"  回复摘要: {result.get('response', 'N/A')[:50]}...")
        return True
    except Exception as e:
        print(f"✗ 消息处理失败: {e}")
        return False


def main():
    print("*"*60)
    print("  WeChat-Kimi 桥接诊断工具")
    print("*"*60)
    
    cloud_ok = test_cloud()
    local_ok = test_local()
    
    if cloud_ok and local_ok:
        print()
        print("✓ 基础连接正常，测试消息流转...")
        flow_ok = test_message_flow()
        
        if flow_ok:
            print()
            print("="*60)
            print("✓✓✓ 所有测试通过！系统正常工作")
            print("="*60)
            print()
            print("如果在微信发送消息没回复，请检查:")
            print("1. 云端是否正确转发消息（看 Codespaces 日志）")
            print("2. 微信是否已扫码登录")
            print("3. 网络连接是否稳定")
        else:
            print()
            print("✗ 消息流转有问题")
    else:
        print()
        print("✗ 基础连接有问题，请检查:")
        if not cloud_ok:
            print("  - 云端服务器是否运行")
            print("  - cloudflared 隧道是否正常")
        if not local_ok:
            print("  - 本地服务器是否运行")
            print(f"  - 端口 8766 是否被占用")


if __name__ == "__main__":
    main()
    input("\n按回车键退出...")
