# 快速部署到GitHub（3分钟完成）

## 🚀 超简单步骤

### 1. 复制以下命令

打开命令行（Win+R → cmd），复制粘贴：

```bash
cd C:\Users\lenovo\wechat-kimi-project
git init
git add .
git commit -m "Initial commit"
```

### 2. 在浏览器中创建仓库

1. 访问：https://github.com/new
2. 输入仓库名：`wechat-kimi-bridge`
3. 点击 **"Create repository"**
4. **复制仓库URL**（如：`https://github.com/你的用户名/wechat-kimi-bridge.git`）

### 3. 推送代码

在命令行中继续：

```bash
git remote add origin https://github.com/你的用户名/wechat-kimi-bridge.git
git branch -M main
git push -u origin main
```

### 4. 打开Codespaces

1. 访问：`https://github.com/你的用户名/wechat-kimi-bridge`
2. 点击绿色 **"<> Code"** 按钮
3. 选择 **"Codespaces"**
4. 点击 **"Create codespace on main"**

### 5. 运行程序

等待环境准备好后，在终端输入：

```bash
python wechat-kimi-bridge-stable.py
```

### 6. 扫码

- 程序显示二维码
- **立即**用手机微信扫描
- 点击"确认登录"
- 完成！

---

## 💡 不想用命令行？

### 用GitHub网页直接上传

1. 访问：https://github.com/new
2. 创建仓库
3. 点击 "uploading an existing file"
4. 选择项目文件夹中的所有文件
5. 点击 "Commit changes"
6. 然后按步骤4-6操作

---

## ⚡ 立即开始

**选择一种方式，3分钟内搞定！**

推荐：**网页直接上传**（最简单）

完成后告诉我，我会帮你检查配置！🚀
