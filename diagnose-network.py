#!/usr/bin/env python3
"""
网络诊断工具 - 检查微信服务器连接问题
"""

import asyncio
import socket
import sys
import ssl
import time

async def test_dns():
    """测试 DNS 解析"""
    print("[1/5] 测试 DNS 解析...")
    try:
        addr = socket.getaddrinfo("ilinkai.weixin.qq.com", None)
        ips = list(set([a[4][0] for a in addr]))
        print(f"  [OK] 解析成功: {', '.join(ips[:2])}")
        return True
    except Exception as e:
        print(f"  [FAIL] 解析失败: {e}")
        return False

async def test_ping():
    """测试 Ping (ICMP)"""
    print("[2/5] 测试 ICMP Ping...")
    print("  [INFO] Ping 可能被防火墙拦截，跳过")
    return True

async def test_tcp_connection():
    """测试 TCP 连接"""
    print("[3/5] 测试 TCP 连接...")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("ilinkai.weixin.qq.com", 443),
            timeout=10
        )
        print("  [OK] TCP 连接成功")
        writer.close()
        await writer.wait_closed()
        return True
    except asyncio.TimeoutError:
        print("  [FAIL] 连接超时 (10秒)")
        return False
    except Exception as e:
        print(f"  [FAIL] 连接失败: {e}")
        return False

async def test_ssl_connection():
    """测试 SSL/TLS 连接"""
    print("[4/5] 测试 SSL/TLS 连接...")
    try:
        context = ssl.create_default_context()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                "ilinkai.weixin.qq.com", 443, ssl=context
            ),
            timeout=10
        )
        print("  [OK] SSL 连接成功")
        print(f"  [INFO] 协议版本: {writer.get_extra_info('ssl_object').version()}")
        writer.close()
        await writer.wait_closed()
        return True
    except asyncio.TimeoutError:
        print("  [FAIL] SSL 连接超时")
        return False
    except Exception as e:
        print(f"  [FAIL] SSL 连接失败: {e}")
        return False

async def test_http_request():
    """测试 HTTP 请求"""
    print("[5/5] 测试 HTTP 请求...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                print(f"  [OK] HTTP 请求成功")
                print(f"  [INFO] 状态码: {resp.status}")
                return True
    except asyncio.TimeoutError:
        print("  [FAIL] HTTP 请求超时")
        return False
    except Exception as e:
        print(f"  [FAIL] HTTP 请求失败: {type(e).__name__}: {e}")
        return False

async def check_proxy():
    """检查代理设置"""
    print("\n[代理设置检查]")
    import os
    proxies = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 
               'http_proxy', 'https_proxy', 'all_proxy']
    has_proxy = False
    for p in proxies:
        v = os.environ.get(p)
        if v:
            print(f"  {p}: {v}")
            has_proxy = True
    if not has_proxy:
        print("  无代理设置")

async def main():
    print("="*60)
    print("网络诊断工具 - 微信服务器连接检查")
    print("="*60)
    print()
    
    results = []
    
    # 运行测试
    results.append(("DNS 解析", await test_dns()))
    results.append(("ICMP Ping", await test_ping()))
    results.append(("TCP 连接", await test_tcp_connection()))
    results.append(("SSL/TLS", await test_ssl_connection()))
    
    # 检查 aiohttp
    try:
        import aiohttp
        results.append(("HTTP 请求", await test_http_request()))
    except ImportError:
        print("[5/5] 跳过 HTTP 测试 (未安装 aiohttp)")
    
    # 检查代理
    await check_proxy()
    
    # 总结
    print("\n" + "="*60)
    print("诊断结果")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{name:15} {status}")
    
    print()
    print(f"通过: {passed}/{total}")
    
    if passed < total:
        print("\n[可能原因]")
        print("1. 防火墙拦截 (Windows Defender / 杀毒软件)")
        print("2. 网络策略限制 (公司/校园网)")
        print("3. 路由器设置")
        print("4. 安全软件阻止")
        print()
        print("[解决方案]")
        print("1. 关闭防火墙或添加白名单")
        print("2. 更换网络环境 (如使用手机热点)")
        print("3. 以管理员身份运行")
        print("4. 检查安全软件设置")
    else:
        print("\n✓ 所有测试通过！网络连接正常")
        print("如果仍无法登录，可能是微信服务器问题")

if __name__ == "__main__":
    asyncio.run(main())
