#!/usr/bin/env python3
"""
网络修复工具 - 解决微信服务器连接问题
"""

import socket
import os
import sys

HOST = 'ilinkai.weixin.qq.com'
KNOWN_IPS = [
    '43.137.175.32',
    '43.137.191.185', 
    '43.171.124.85',
    '43.171.116.194'
]


def test_connection(ip, port=443, timeout=5):
    """测试到指定IP的连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def find_best_ip():
    """找到响应最快的IP"""
    print("[1] 测试可用IP...")
    working_ips = []
    
    for ip in KNOWN_IPS:
        print(f"    测试 {ip}...", end=" ")
        if test_connection(ip):
            print("OK")
            working_ips.append(ip)
        else:
            print("FAIL")
    
    return working_ips


def update_hosts_file(ip):
    """更新hosts文件"""
    hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
    entry = f"{ip} {HOST}\n"
    
    print(f"\n[2] 更新hosts文件...")
    print(f"    路径: {hosts_path}")
    print(f"    添加: {entry.strip()}")
    
    try:
        # 读取现有内容
        with open(hosts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已有该条目
        if HOST in content:
            print("    [提示] hosts中已有该域名记录，请先手动删除")
            return False
        
        # 追加新条目
        with open(hosts_path, 'a', encoding='utf-8') as f:
            f.write(f"\n# WeChat-Kimi Bridge fix\n{entry}")
        
        print("    成功！")
        return True
        
    except PermissionError:
        print("    [错误] 需要管理员权限！")
        print("    请用管理员权限运行: 右键 -> 以管理员身份运行")
        return False
    except Exception as e:
        print(f"    [错误] {e}")
        return False


def flush_dns():
    """刷新DNS缓存"""
    print("\n[3] 刷新DNS缓存...")
    os.system('ipconfig /flushdns')
    print("    完成")


def main():
    print("=" * 60)
    print("    WeChat-Kimi Bridge 网络修复工具")
    print("=" * 60)
    print()
    
    # 1. 找到可用IP
    working_ips = find_best_ip()
    
    if not working_ips:
        print("\n[警告] 所有已知IP都无法连接！")
        print("可能的原因:")
        print("  - 网络完全不通")
        print("  - 防火墙/安全软件拦截")
        print("  - 需要代理才能访问")
        print()
        print("建议解决方案:")
        print("  1. 检查网络连接")
        print("  2. 暂时关闭防火墙测试")
        print("  3. 配置代理后重试")
        print("  4. 使用 GitHub Codespaces")
        return
    
    print(f"\n[信息] 可用IP: {working_ips}")
    best_ip = working_ips[0]
    
    # 2. 询问是否修复
    print()
    choice = input(f"是否将 {HOST} 指向 {best_ip}? (y/n): ").strip().lower()
    
    if choice == 'y':
        if update_hosts_file(best_ip):
            flush_dns()
            print()
            print("=" * 60)
            print("修复完成！请重新运行: python wechat-kimi-bridge-stable.py")
            print("=" * 60)
            print()
            print("如果仍有问题，请:")
            print("  1. 重启电脑后重试")
            print("  2. 使用管理员权限运行")
            print("  3. 考虑使用 GitHub Codespaces")
    else:
        print("\n已取消修复")


if __name__ == "__main__":
    main()
