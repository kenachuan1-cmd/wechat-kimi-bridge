# WeChat-Kimi Bridge 真实微信接入指南

## 前置要求

1. **Python 3.10+**
2. **Kimi Code CLI** - 已登录
3. **微信号** - 实名认证，可正常使用

## 安装依赖

```bash
pip install aiohttp aiofiles weixin-bot-sdk
```

## 配置

编辑 `config.json`：

```json
{
  "bot_name": "Kimi",
  "default_work_dir": ".",
  "group_strategy": "per_group",
  "auto_approve": false,
  "allowed_groups": [],
  "blocked_groups": []
}
```

### 配置说明

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `bot_name` | 机器人在群里的昵称 | `"Kimi"` |
| `group_strategy` | 群聊策略 | `"per_group"` 或 `"per_user"` |
| `auto_approve` | 自动审批工具调用 | `false`（建议生产环境关闭） |
| `allowed_groups` | 白名单群ID | `["群ID1", "群ID2"]` |
| `blocked_groups` | 黑名单群ID | `["群ID3"]` |

## 首次运行

### 1. 确保 Kimi 已登录

```bash
kimi info
```

如果显示版本信息则正常。如果提示未登录：

```bash
kimi login
```

### 2. 运行桥接器

```bash
python wechat-kimi-bridge-real.py
```

### 3. 扫码登录微信

首次运行会显示二维码，使用微信扫码登录。

登录成功后，程序会保存凭证，下次自动登录。

## 使用方式

### 私聊

直接发送消息给机器人：

```
你好，帮我写一个 Python 脚本
```

### 群聊

在群里 @机器人：

```
@Kimi 总结一下今天的讨论
```

### 图片识别

发送图片并 @机器人：

```
@Kimi [图片] 分析一下这个图表
```

### 斜杠命令

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/new` | 开启新会话 |
| `/clear` | 清空上下文 |
| `/status` | 查看状态 |
| `/cd <路径>` | 切换工作目录 |
| `/compact` | 压缩上下文 |
| `/mode <策略>` | 切换群聊模式 |

## 群聊策略说明

### per_group（默认）
- 群内所有人共享同一个上下文
- 适合：团队协作、项目讨论
- 示例：A 问了问题，B 可以继续这个话题

### per_user
- 群内每人有独立的上下文
- 适合：个人助手、隐私保护
- 示例：A 和 B 的会话完全隔离

切换命令：

```
/mode per_user
```

## 注意事项

### 1. 账号安全

- 建议使用小号运行机器人
- 不要频繁发送消息，避免被限制
- 不要在多个设备同时登录

### 2. 消息限制

- 图片大小：默认 5MB
- 消息长度：自动分段，每段 2000 字符
- 超时：5 分钟无响应会超时

### 3. 会话管理

- 会话 24 小时无活动自动清理
- 可使用 `/new` 手动开启新会话
- 工作目录切换会重置会话

## 故障排查

### 无法登录微信

1. 检查网络连接
2. 确保微信号可正常登录网页版
3. 尝试删除 `~/.wechat_bot/` 重新登录

### Kimi 无响应

1. 检查 `kimi info` 是否正常
2. 查看日志 `wechat-kimi-bridge.log`
3. 重启程序

### 图片无法识别

1. 检查图片格式（支持 JPG、PNG、GIF、WebP）
2. 检查图片大小（不超过 5MB）
3. 检查网络连接

## 后台运行

### Linux/macOS

```bash
nohup python wechat-kimi-bridge-real.py > bridge.log 2>&1 &
```

### Windows

使用 PowerShell:

```powershell
Start-Process python -ArgumentList "wechat-kimi-bridge-real.py" -WindowStyle Hidden
```

或使用任务计划程序。

## Docker 运行

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install aiohttp aiofiles weixin-bot-sdk

# 安装 Kimi CLI
RUN pip install kimi-cli

COPY wechat-kimi-bridge-real.py .
COPY config.json .

CMD ["python", "wechat-kimi-bridge-real.py"]
```

运行：

```bash
docker build -t wechat-kimi .
docker run -it --rm -v ~/.kimi:/root/.kimi -v $(pwd)/data:/app/data wechat-kimi
```

## 日志查看

```bash
# 实时查看
tail -f wechat-kimi-bridge.log

# 查看最后 100 行
tail -n 100 wechat-kimi-bridge.log
```

## 更新

```bash
# 更新依赖
pip install -U aiohttp aiofiles weixin-bot-sdk

# 更新 Kimi CLI
pip install -U kimi-cli
```

## 开源协议

MIT License
