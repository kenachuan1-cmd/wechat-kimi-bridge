# 混合架构部署指南

## 架构概述

```
┌─────────────────────┐         WebSocket          ┌─────────────────────┐
│   GitHub Codespaces │  ◄──────────────────────►  │     你的本地电脑     │
│                     │                             │                     │
│  ┌───────────────┐  │                             │  ┌───────────────┐  │
│  │  微信桥接器    │  │                             │  │ 本地Kimi客户端 │  │
│  │ (连接微信服务器)│  │      转发微信消息          │  │ (调用本地Kimi) │  │
│  └───────┬───────┘  │  ◄──────────────────────►  │  └───────┬───────┘  │
│          │          │                             │          │          │
│  ┌───────▼───────┐  │                             │  ┌───────▼───────┐  │
│  │ WebSocket服务器 │ │      返回Kimi回复          │  │  Kimi CLI     │  │
│  │  (端口8765)   │  │  ◄──────────────────────►  │  │  (操作本地文件)│  │
│  └───────────────┘  │                             │  └───────────────┘  │
└─────────────────────┘                             └─────────────────────┘
```

## 优势

- ✅ **微信连接稳定** - 使用GitHub Codespaces的优质网络
- ✅ **可操作本地文件** - Kimi运行在本地，完全访问本地文件系统
- ✅ **安全** - 通过WebSocket加密传输，不暴露本地端口到公网

## 部署步骤

### 第一步：部署云端服务器（GitHub Codespaces）

1. **上传项目到GitHub**
   ```bash
   cd wechat-kimi-project
   git add .
   git commit -m "Add hybrid bridge"
   git push origin main
   ```

2. **打开 Codespaces**
   - 访问 `https://github.com/kenachuan1-cmd/wechat-kimi-bridge`
   - 点击 `Code` -> `Codespaces` -> `Create codespace`

3. **在 Codespaces 中运行服务器**
   ```bash
   pip install websockets
   python hybrid-bridge-complete.py
   ```

4. **获取公网WebSocket地址**
   - 服务器启动后会显示类似：
     ```
     公网地址: wss://xxx-8765.github.dev
     ```
   - 复制这个地址

### 第二步：配置并启动本地客户端

1. **在本地电脑上**，创建配置文件：
   ```json
   {
     "server_url": "wss://xxx-8765.github.dev"
   }
   ```

2. **安装依赖**
   ```bash
   pip install websockets
   ```

3. **启动本地客户端**
   ```bash
   python hybrid-bridge-client.py wss://xxx-8765.github.dev
   ```

4. **验证连接**
   - 云端日志应显示：`✓ 本地客户端连接 [...]`

### 第三步：使用

1. **在微信中**
   - 给机器人发消息或@机器人
   - 消息会自动转发到本地

2. **本地Kimi处理**
   - 本地客户端收到消息
   - 调用本地Kimi CLI处理
   - 可以操作本地文件

3. **回复到微信**
   - Kimi生成回复
   - 通过WebSocket返回云端
   - 云端发送到微信

## 测试模式

如果不方便部署到Codespaces，可以先在本地测试：

**终端1（模拟云端服务器）**
```bash
python hybrid-bridge-complete.py
```

**终端2（本地客户端）**
```bash
python hybrid-bridge-client.py ws://localhost:8765
```

服务器每10秒会发送一条测试消息。

## 故障排查

### 连接问题

**问题**: 本地无法连接到云端
```
连接失败: [Errno 111] Connection refused
```

**解决**:
1. 检查云端服务器是否运行
2. 检查WebSocket地址是否正确
3. 检查Codespaces端口是否转发（8765）

### 端口转发配置

在 Codespaces 中确保端口8765是公开的：

1. 点击底部状态栏的"端口"标签
2. 找到端口 8765
3. 右键 -> "端口可见性" -> "Public"

### 消息丢失

**问题**: 本地客户端离线时消息丢失

**解决**:
- 云端会自动缓存消息
- 本地客户端重新连接后会收到积压消息

## 安全提示

1. **WebSocket地址不要泄露** - 任何人知道地址都可以连接
2. **使用完后停止Codespaces** - 防止意外费用和未授权访问
3. **定期更换连接** - 每次新的Codespaces会话地址都会变化

## 进阶配置

### 自定义端口

修改 `hybrid-config.json`:
```json
{
  "server": {
    "port": 8080
  }
}
```

### 心跳检测

默认每30秒发送一次心跳，可在代码中调整：
```python
heartbeat_interval = 30  # 秒
```

### 消息加密

生产环境建议使用wss（WebSocket Secure）：
```python
server_url = "wss://your-domain.com"
```

## 现在就开始

1. 上传项目到GitHub
2. 打开Codespaces
3. 启动云端服务器
4. 复制WebSocket地址
5. 启动本地客户端
6. 开始用微信控制本地Kimi！

有任何问题请查看日志文件 `hybrid-bridge.log`
