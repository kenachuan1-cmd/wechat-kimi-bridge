# WeChat-Kimi Bridge 项目

快速将 Kimi Code CLI 接入微信

## 文件说明

| 文件 | 用途 |
|------|------|
| `wechat-kimi-bridge-stable.py` | 主程序（稳定版） |
| `wechat-kimi-bridge-real.py` | 完整功能版 |
| `wechat-kimi-bridge-advanced.py` | 高级版（多策略） |
| `quick-start.py` | 快速启动向导 |
| `config.json` | 配置文件 |
| `run-mock.bat` | Windows 测试启动 |

## 快速开始（3步）

### 1. 安装依赖
```bash
pip install aiohttp weixin-bot-sdk
```

### 2. 确保 Kimi 已登录
```bash
kimi login
kimi info  # 验证
```

### 3. 运行

**测试模式（推荐先试）：**
```bash
python wechat-kimi-bridge-stable.py --mock
```

**真实微信模式：**
```bash
python wechat-kimi-bridge-stable.py
```
扫码登录后即可使用

## 使用方式

### 私聊
直接发送消息给机器人

### 群聊
@机器人发送消息：
```
@Kimi 总结一下今天的讨论
```

### 图片识别
发送图片并@机器人：
```
@Kimi [图片] 这是什么？
```

### 命令
| 命令 | 功能 |
|------|------|
| `/help` | 帮助 |
| `/new` | 新会话 |
| `/clear` | 清空上下文 |
| `/status` | 查看状态 |
| `/cd <路径>` | 切换工作目录 |

## 配置

编辑 `config.json`：
```json
{
  "bot_name": "Kimi",
  "group_strategy": "per_group",
  "auto_approve": true
}
```

## 群聊策略

- `per_group`: 群内共享上下文（推荐）
- `per_user`: 每人独立上下文

## 注意事项

1. 首次运行需要扫码登录
2. 建议用小号运行机器人
3. 会话24小时无活动自动清理
4. 图片限制5MB

## 问题排查

**无法登录微信**
- 确保微信号可登录网页版
- 删除 `~/.wechat_bot/` 重试

**Kimi 无响应**
- 检查 `kimi info`
- 查看日志 `wechat-kimi-bridge.log`

**乱码**
- Windows: `chcp 65001`
- 设置 `PYTHONIOENCODING=utf-8`

## 技术支持

- Kimi CLI: https://moonshotai.github.io/kimi-cli/
- 微信 SDK: https://github.com/epiral/weixin-bot

---

祝使用愉快！
