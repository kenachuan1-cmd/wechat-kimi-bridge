# GitHub Codespaces 部署指南

## 🎯 方案3：使用GitHub Codespaces

这是最佳方案！Codespaces的网络环境更稳定，二维码可以实时显示。

---

## 📦 第一步：准备文件

确保项目文件夹包含以下文件：
```
wechat-kimi-project/
├── .devcontainer/
│   └── devcontainer.json    ← 已创建
├── .github/
│   └── README.md            ← 已创建
├── wechat-kimi-bridge-stable.py
├── config.json
├── requirements.txt         ← 已创建
└── GITHUB上传指南.md        ← 本文件
```

---

## 🚀 第二步：上传到GitHub

### 方法1：使用Git命令行

1. **打开命令行**，进入项目目录：
   ```bash
   cd C:\Users\lenovo\wechat-kimi-project
   ```

2. **初始化Git仓库**：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

3. **创建GitHub仓库**（在浏览器中）：
   - 访问 https://github.com/new
   - 输入仓库名称（如：wechat-kimi-bridge）
   - 点击 "Create repository"

4. **连接并推送**：
   ```bash
   git remote add origin https://github.com/你的用户名/仓库名.git
   git branch -M main
   git push -u origin main
   ```

### 方法2：使用GitHub Desktop（推荐新手）

1. 下载安装GitHub Desktop：https://desktop.github.com/
2. 选择项目文件夹
3. 填写提交信息，点击 "Commit"
4. 点击 "Publish repository"

### 方法3：直接上传文件

1. 访问 https://github.com/new
2. 创建新仓库
3. 点击 "uploading an existing file"
4. 拖拽所有文件上传

---

## 💻 第三步：在Codespaces中运行

### 1. 打开Codespaces

1. 访问你的GitHub仓库页面
2. 点击绿色的 **"<> Code"** 按钮
3. 选择 **"Codespaces"** 标签
4. 点击 **"Create codespace on main"**

### 2. 等待环境准备（约1-2分钟）

Codespaces会自动：
- ✅ 安装Python 3.11
- ✅ 安装所有依赖
- ✅ 配置环境

你会看到：
```
Running pip install -r requirements.txt
...
Done!
```

### 3. 运行程序

在终端中输入：
```bash
python wechat-kimi-bridge-stable.py
```

### 4. 扫码登录

- 程序会显示二维码（在终端中）
- **立即**用手机微信扫描
- 点击"确认登录"

---

## 📱 使用技巧

### 如何查看二维码更清晰？

如果终端中的二维码不清晰：

1. **放大终端**：
   - VS Code: `Ctrl + =`

2. **或使用链接**：
   - 复制控制台输出的URL
   - 在浏览器中打开

3. **或生成图片**：
   ```bash
   python -c "import qrcode; qr=qrcode.QRCode(); qr.add_data('URL'); qr.make(); qr.print_ascii()"
   ```

---

## ⚡ 为什么Codespaces更好？

| 特性 | 本地运行 | Codespaces |
|------|---------|-----------|
| 网络环境 | 取决于你的网络 | GitHub高速网络 |
| 二维码显示 | 可能有编码问题 | 标准Linux终端 |
| 依赖安装 | 需要手动安装 | 自动安装 |
| 访问速度 | 本地快 | 云端快 |
| 多设备 | 只能在本地用 | 任何设备访问 |

---

## 🔧 故障排除

### 问题1：Codespaces创建失败
**解决**：刷新页面重试，或更换浏览器

### 问题2：依赖安装失败
**解决**：在终端中手动运行：
```bash
pip install aiohttp weixin-bot-sdk qrcode
```

### 问题3：二维码显示乱码
**解决**：调整终端字体大小，或使用链接方式

### 问题4：登录超时
**解决**：
1. 关闭程序（Ctrl+C）
2. 重新运行
3. 立即扫码

---

## 🎉 完成！

现在你可以在Codespaces中稳定运行WeChat-Kimi Bridge了！

**优势**：
- 网络稳定，二维码实时显示
- 无需配置本地环境
- 随时随地访问
- 自动保存代码

**开始体验吧！** 🚀
