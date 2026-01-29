# 小缘 Web 工具

## 使用 GitHub Actions 自动打包 Windows .exe

### 第一次设置（只需一次）

1. 在 GitHub 创建新仓库

2. 把代码推到 GitHub：
```bash
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/你的仓库名.git
git branch -M main
git push -u origin main
```

3. 推送后会自动开始打包，等待几分钟

4. 在 GitHub 仓库页面点击 Actions → 点击最新的构建 → 在 Artifacts 下载 `小缘Web工具-Windows`

### 以后修改代码后重新打包

1. 修改 `src/` 中的代码

2. 推送到 GitHub：
```bash
git add .
git commit -m "Update code"
git push origin main
```

3. 自动打包，等待完成后下载新的 .exe

4. 把 .exe 发给同事

### 同事使用

1. 收到 `小缘Web工具.exe`
2. 双击运行
3. 浏览器自动打开 http://127.0.0.1:5000
4. 配置API密钥后开始测试

### 手动触发打包

1. GitHub 仓库 → Actions
2. 选择 "Build Windows Executable"
3. 点击 "Run workflow" → "Run workflow"
4. 等待完成，下载 .exe
