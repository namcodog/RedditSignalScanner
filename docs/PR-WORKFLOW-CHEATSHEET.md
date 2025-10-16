# Pull Request 工作流速查表

**快速参考** - 打印出来贴在桌上 📌

---

## 🚀 标准 PR 工作流（5 步）

```bash
# 1️⃣ 创建分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2️⃣ 写代码 + 提交
git add .
git commit -m "feat: add new feature"

# 3️⃣ 推送到 GitHub
git push origin feature/your-feature-name

# 4️⃣ 在 GitHub 上创建 PR
# 访问: https://github.com/namcodog/RedditSignalScanner
# 点击 "Compare & pull request"

# 5️⃣ 合并后清理
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```

---

## 📝 Commit Message 规范

```bash
# 格式
<type>: <subject>

<body>

# 类型 (type)
feat:     新功能
fix:      Bug 修复
docs:     文档更新
style:    代码格式（不影响功能）
refactor: 重构（不是新功能也不是 Bug 修复）
test:     测试相关
chore:    构建/工具相关

# 例子
git commit -m "feat: add email notification"
git commit -m "fix: resolve login timeout issue"
git commit -m "docs: update API documentation"
```

---

## 🌿 分支命名规范

```bash
# 格式
<type>/<short-description>

# 类型
feature/  - 新功能
fix/      - Bug 修复
docs/     - 文档
refactor/ - 重构
test/     - 测试

# 例子
feature/user-authentication
fix/login-timeout
docs/api-guide
refactor/database-layer
```

---

## ✅ PR 检查清单

创建 PR 前确认：

```
[ ] 代码已测试（本地运行通过）
[ ] Commit message 符合规范
[ ] 没有提交敏感信息（.env, API keys）
[ ] 代码格式正确（运行 lint）
[ ] 添加了必要的注释
[ ] 更新了相关文档
[ ] PR 描述清晰（说明改了什么、为什么改）
```

---

## 🔧 常用命令

```bash
# 查看当前分支
git branch

# 切换分支
git checkout <branch-name>

# 查看修改
git status
git diff

# 撤销修改（未 commit）
git checkout -- <file>

# 修改最后一次 commit
git commit --amend

# 同步 main 分支最新代码
git checkout main
git pull origin main
git checkout feature/xxx
git merge main  # 或 git rebase main

# 删除本地分支
git branch -d <branch-name>

# 删除远程分支
git push origin --delete <branch-name>
```

---

## 🚨 紧急情况处理

### 场景 1: 提交了错误的代码

```bash
# 撤销最后一次 commit（保留修改）
git reset --soft HEAD~1

# 撤销最后一次 commit（丢弃修改）
git reset --hard HEAD~1

# 如果已经推送到远程
git push origin <branch> --force  # ⚠️ 谨慎使用
```

### 场景 2: 提交了敏感信息

```bash
# 1. 从 Git 历史中删除文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch <file>" \
  --prune-empty --tag-name-filter cat -- --all

# 2. 强制推送
git push origin --force --all

# 3. 立即更换泄露的密钥/密码
```

### 场景 3: PR 冲突

```bash
# 1. 同步 main 分支
git checkout main
git pull origin main

# 2. 切换到你的分支
git checkout feature/xxx

# 3. 合并 main（解决冲突）
git merge main

# 4. 手动解决冲突
# 编辑冲突文件，删除 <<<<<<, ======, >>>>>> 标记

# 5. 提交解决结果
git add .
git commit -m "merge: resolve conflicts with main"
git push origin feature/xxx
```

---

## 📊 GitHub Actions 状态

```
✅ 绿色勾号 = 所有检查通过
❌ 红色叉号 = 检查失败（点击查看详情）
🟡 黄色圆圈 = 正在运行
⚪ 灰色圆圈 = 等待运行
```

---

## 🎯 最佳实践

### ✅ 好的 PR

```
✅ 小而专注（一个 PR 只做一件事）
✅ 描述清晰（说明改了什么、为什么改）
✅ 包含测试
✅ 及时响应审查意见
✅ Commit 历史清晰
```

### ❌ 不好的 PR

```
❌ 太大（改了 50 个文件）
❌ 描述模糊（"fix bug"）
❌ 没有测试
❌ 忽略审查意见
❌ Commit 历史混乱（"fix", "fix2", "fix3"）
```

---

## 🔗 快速链接

- **仓库**: https://github.com/namcodog/RedditSignalScanner
- **PR 列表**: https://github.com/namcodog/RedditSignalScanner/pulls
- **Actions**: https://github.com/namcodog/RedditSignalScanner/actions
- **Issues**: https://github.com/namcodog/RedditSignalScanner/issues

---

## 💡 提示

- 经常 `git pull` 保持同步
- 小步提交，频繁推送
- 写清楚 commit message（未来的你会感谢现在的你）
- 不确定时，先创建 PR 草稿（Draft PR）
- 善用 GitHub 的代码审查功能（添加评论、建议修改）

---

**打印这张表，贴在显示器旁边！** 📌

