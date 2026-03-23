# WeChat-Kimi Bridge

在GitHub Codespaces中运行的微信-Kimi桥接器

## 🚀 快速开始

### 1. 创建GitHub仓库

1. 在GitHub上创建新仓库
2. 上传所有代码文件
3. 进入仓库页面

### 2. 打开Codespaces

1. 点击绿色的 **"<> Code"** 按钮
2. 选择 **"Codespaces"** 标签
3. 点击 **"Create codespace on main"**

### 3. 等待环境准备

Codespaces会自动：
- 安装Python 3.11
- 安装所有依赖
- 配置环境

### 4. 运行程序

在终端中运行：
```bash
python wechat-kimi-bridge-stable.py
```

### 5. 扫码登录

- 程序会显示二维码
- **立即**用手机微信扫描
- 点击"确认登录"

## 📱 使用说明

### 私聊
直接给机器人发消息

### 群聊
@机器人发送消息：
```
@Kimi 你好
```

### 命令
- `/help` - 显示帮助
- `/new` - 新会话
- `/status` - 查看状态

## ⚠️ 注意事项

1. **二维码有效期5分钟**，请立即扫描
2. **手机微信必须保持在线**
3. **网络要稳定**

## 🔧 故障排除

### 二维码过期
关闭程序重新运行，获取新二维码

### 登录失败
检查网络连接，或重新创建Codespaces

### 依赖安装失败
手动运行：
```bash
pip install -r requirements.txt
```

## 📦 文件说明

- `wechat-kimi-bridge-stable.py` - 主程序
- `config.json` - 配置文件
- `requirements.txt` - Python依赖

## 📝 许可证

MIT License
