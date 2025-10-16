# CI/CD 和 Pull Request 使用指南

**目标读者**: 不熟悉 CI/CD 和 PR 的开发者  
**阅读时间**: 10 分钟  
**难度**: 入门级

---

## 📚 目录

1. [什么是 CI/CD？](#什么是-cicd)
2. [什么是 Pull Request？](#什么是-pull-request)
3. [实战：第一个 Pull Request](#实战第一个-pull-request)
4. [实战：启用 CI/CD](#实战启用-cicd)
5. [常见问题](#常见问题)

---

## 什么是 CI/CD？

### 🎯 **一句话解释**

**CI/CD = 自动化测试 + 自动化部署**

### 📖 **详细解释**

#### **CI (Continuous Integration - 持续集成)**

**问题**: 多人协作时，如何确保每个人的代码都不会破坏项目？

**解决方案**: 每次提交代码后，自动运行测试

**例子**:
```
你提交代码 → GitHub 自动运行测试 → 测试通过 ✅ 或 失败 ❌
```

**好处**:
- ✅ 早发现问题（提交后几分钟就知道有没有 Bug）
- ✅ 不用手动运行测试（机器自动做）
- ✅ 保证代码质量

#### **CD (Continuous Deployment - 持续部署)**

**问题**: 测试通过后，如何快速部署到服务器？

**解决方案**: 测试通过后，自动部署

**例子**:
```
测试通过 → 自动构建 Docker 镜像 → 自动部署到服务器 → 用户看到新功能
```

**好处**:
- ✅ 快速上线（几分钟而不是几小时）
- ✅ 减少人为错误
- ✅ 随时可以发布

---

## 什么是 Pull Request？

### 🎯 **一句话解释**

**Pull Request = 请求合并代码 + 代码审查**

### 📖 **详细解释**

#### **工作流程**

```
1. 创建分支
   main ──┬─→ feature/fix-bug
          │
          └─→ 在这个分支上写代码

2. 提交代码到分支
   git add .
   git commit -m "fix: 修复登录 Bug"
   git push origin feature/fix-bug

3. 在 GitHub 上创建 Pull Request
   "我修复了登录 Bug，请审查我的代码"

4. 团队成员审查
   👤 张三: "代码看起来不错 ✅"
   👤 李四: "这里可以优化一下 💬"

5. 修改代码（如果需要）
   根据反馈修改 → 再次提交

6. 合并到 main
   审查通过 → 点击 "Merge" → 代码进入主分支
```

#### **为什么需要 PR？**

**场景 1: 防止错误**
```
❌ 没有 PR:
你直接推送到 main → 代码有 Bug → 整个项目崩溃 → 😱

✅ 有 PR:
你创建 PR → CI 自动测试 → 发现 Bug → 修复后再合并 → 😊
```

**场景 2: 知识共享**
```
你写了一个复杂的功能 → 创建 PR → 团队成员看到你的代码 → 学习新技巧
```

**场景 3: 代码质量**
```
你的代码 → 其他人审查 → 发现可以优化的地方 → 代码质量提升
```

---

## 实战：第一个 Pull Request

### 📝 **场景：修复 mypy 类型警告**

#### **步骤 1: 创建分支**

```bash
# 确保在 main 分支
git checkout main
git pull origin main

# 创建新分支
git checkout -b fix/mypy-warnings

# 查看当前分支
git branch
# * fix/mypy-warnings  ← 当前分支
#   main
```

#### **步骤 2: 修改代码**

```bash
# 打开文件
vim backend/app/services/monitoring.py

# 修复类型警告（例子）
# 修改前:
categories = {}

# 修改后:
categories: dict[str, Any] = {}
```

#### **步骤 3: 提交代码**

```bash
# 查看修改
git status

# 添加文件
git add backend/app/services/monitoring.py

# 提交
git commit -m "fix: add type annotations to monitoring.py

- Add type hints for categories dict
- Fix mypy warnings in monitoring service
- Resolves 2 of 13 mypy errors"

# 推送到 GitHub
git push origin fix/mypy-warnings
```

#### **步骤 4: 在 GitHub 上创建 PR**

1. **访问仓库**: https://github.com/namcodog/RedditSignalScanner

2. **点击 "Compare & pull request"** 按钮（GitHub 会自动显示）

3. **填写 PR 信息**:
   ```
   标题: fix: add type annotations to monitoring.py
   
   描述:
   ## 修改内容
   - 为 monitoring.py 添加类型注解
   - 修复 2 个 mypy 类型警告
   
   ## 测试
   - [x] 运行 mypy 检查
   - [x] 运行相关测试
   
   ## 相关 Issue
   Closes #1
   ```

4. **点击 "Create pull request"**

#### **步骤 5: 等待审查**

- CI 会自动运行测试
- 团队成员会审查代码
- 根据反馈修改（如果需要）

#### **步骤 6: 合并**

- 审查通过后，点击 "Merge pull request"
- 删除分支（可选）

---

## 实战：启用 CI/CD

### 🚀 **方案 1: 使用简化版 CI（推荐入门）**

我已经为您创建了 `.github/workflows/simple-ci.yml`

**功能**:
- ✅ 检查 Python 语法
- ✅ 检查 TypeScript 类型
- ✅ 检查是否有敏感信息泄露

**启用方法**:

```bash
# 1. 提交 CI 配置文件
git add .github/workflows/simple-ci.yml
git commit -m "ci: add simple CI workflow"
git push origin main

# 2. 访问 GitHub Actions 页面
# https://github.com/namcodog/RedditSignalScanner/actions

# 3. 查看运行结果
# 每次推送代码后，会自动运行
```

**查看结果**:
- ✅ 绿色勾号 = 通过
- ❌ 红色叉号 = 失败（点击查看详情）

---

### 🚀 **方案 2: 使用完整版 CI（进阶）**

我已经为您创建了 `.github/workflows/ci.yml`

**功能**:
- ✅ 运行所有测试（需要数据库）
- ✅ 检查代码质量（mypy, eslint）
- ✅ 检查代码覆盖率
- ✅ 安全扫描

**启用方法**:

```bash
# 1. 提交 CI 配置文件
git add .github/workflows/ci.yml
git commit -m "ci: add full CI/CD pipeline"
git push origin main

# 2. 配置 Secrets（如果需要）
# GitHub → Settings → Secrets and variables → Actions
# 添加必要的环境变量
```

**注意**: 完整版 CI 会运行更多检查，时间更长（5-10 分钟）

---

## 常见问题

### ❓ **Q1: 什么时候必须使用 PR？**

**A**: 取决于团队规则

**个人项目**:
- 可以直接推送到 main（快速迭代）
- 也可以用 PR（养成好习惯）

**团队项目**:
- **必须**使用 PR（保护主分支）
- 设置分支保护规则

**开源项目**:
- **必须**使用 PR（维护者审查）

---

### ❓ **Q2: CI/CD 会增加开发时间吗？**

**A**: 短期会，长期不会

**短期**（第一次配置）:
- 配置 CI: 30 分钟
- 学习使用: 1 小时

**长期**（日常使用）:
- 节省手动测试时间: 每天 30 分钟
- 减少 Bug 修复时间: 每周 2 小时
- 提高代码质量: 无价 ✨

---

### ❓ **Q3: CI 失败了怎么办？**

**A**: 不要慌，按步骤排查

**步骤 1: 查看错误信息**
```
GitHub Actions → 点击失败的任务 → 查看日志
```

**步骤 2: 本地复现**
```bash
# 在本地运行相同的命令
cd backend
pytest -v
```

**步骤 3: 修复问题**
```bash
# 修复代码
git add .
git commit -m "fix: resolve CI failure"
git push
```

**步骤 4: 等待 CI 重新运行**
```
GitHub 会自动重新运行测试
```

---

### ❓ **Q4: 如何设置分支保护？**

**A**: 在 GitHub 仓库设置中配置

**步骤**:

1. **访问设置**:
   ```
   GitHub → Settings → Branches → Add rule
   ```

2. **配置规则**:
   ```
   Branch name pattern: main
   
   ✅ Require a pull request before merging
   ✅ Require status checks to pass before merging
      - Select: CI checks
   ✅ Require conversation resolution before merging
   ```

3. **保存**

**效果**:
- ❌ 不能直接推送到 main
- ✅ 必须通过 PR
- ✅ 必须通过 CI 检查
- ✅ 必须有人审查

---

### ❓ **Q5: 一个人开发也需要 PR 吗？**

**A**: 看情况

**不需要 PR 的情况**:
- 快速原型开发
- 个人学习项目
- 紧急 Bug 修复

**建议使用 PR 的情况**:
- 重要功能开发（方便回顾）
- 需要记录决策过程
- 练习最佳实践

**折中方案**:
```bash
# 创建 PR，但自己审查并立即合并
git checkout -b feature/xxx
# ... 写代码 ...
git push origin feature/xxx
# 创建 PR → 自己审查 → 立即合并
```

---

## 📚 推荐阅读

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Pull Request 最佳实践](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests)
- [CI/CD 入门教程](https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment)

---

## 🎯 下一步

1. **启用简化版 CI**: 提交 `simple-ci.yml`
2. **创建第一个 PR**: 修复 mypy 警告
3. **设置分支保护**: 保护 main 分支
4. **学习 GitHub Actions**: 自定义 CI 流程

---

**有问题？** 查看 [GitHub Discussions](https://github.com/namcodog/RedditSignalScanner/discussions) 或创建 Issue！

