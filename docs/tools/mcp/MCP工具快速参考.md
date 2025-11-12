# MCP 工具快速参考卡片

> 快速查找常用的 AI 提示和命令

## 🎯 Chrome DevTools MCP

### 性能分析

```
✅ 分析 https://example.com 的性能
✅ 检查 https://mysite.com 的 Core Web Vitals
✅ 详细分析 LCP 性能瓶颈
✅ 为什么页面有布局偏移？
✅ 如何优化渲染阻塞资源？
✅ 第三方脚本对性能有什么影响？
```

### 网络分析

```
✅ 列出页面的所有网络请求
✅ 显示加载时间最长的 5 个资源
✅ 找出失败的网络请求
✅ 查看主文档的请求详情
✅ 检查图片资源的缓存策略
```

### 调试

```
✅ 显示页面的控制台错误
✅ 查看所有 console.log 输出
✅ 检查是否有 JavaScript 错误
✅ 截取当前页面的截图
✅ 执行 JavaScript 获取页面标题
```

### 模拟测试

```
✅ 模拟 3G 网络环境
✅ 模拟 4 倍 CPU 降速
✅ 调整浏览器窗口为 1920x1080
✅ 模拟移动设备视口 375x667
```

---

## 🎭 Playwright MCP

### 页面导航

```
✅ 打开 https://example.com
✅ 刷新当前页面
✅ 返回上一页
✅ 列出所有打开的标签页
✅ 切换到第 2 个标签页
```

### 交互操作

```
✅ 点击"登录"按钮
✅ 在搜索框中输入"React hooks"
✅ 填写用户名为 "test@example.com"
✅ 选择下拉菜单中的"中国"
✅ 上传文件 /path/to/file.pdf
✅ 等待"加载完成"文本出现
```

### 截图与快照

```
✅ 截取当前页面的截图
✅ 截取整个页面的截图（包括滚动区域）
✅ 获取页面的文本快照
```

---

## 🔄 Context7

### 文档查询

```
✅ 用 Context7 查找 React 的文档
✅ 查找 Next.js 的路由文档
✅ 获取 TypeScript 的类型系统文档
```

---

## 💻 Exa-Code

### 代码搜索

```
✅ 用 Exa-Code 搜索 React hooks 的最佳实践
✅ 搜索 TypeScript 泛型的代码示例
✅ 查找 Node.js 错误处理的最佳实践
```

---

## 🧠 Sequential Thinking

### 复杂问题分析

```
✅ 用 Sequential Thinking 分析如何优化 React 应用性能
✅ 分步骤解决数据库查询慢的问题
✅ 设计一个可扩展的微服务架构
```

---

## 📊 组合使用示例

### 性能优化工作流

```
1️⃣ 用 Chrome DevTools 分析 https://mysite.com 的性能
2️⃣ 用 Exa-Code 搜索相关优化方案
3️⃣ 实施优化
4️⃣ 用 Playwright 进行回归测试
5️⃣ 用 Chrome DevTools 验证优化效果
```

### 调试工作流

```
1️⃣ 用 Playwright 重现问题
2️⃣ 用 Chrome DevTools 查看控制台错误
3️⃣ 用 Chrome DevTools 分析网络请求
4️⃣ 用 Sequential Thinking 分析根本原因
5️⃣ 用 Exa-Code 查找解决方案
6️⃣ 用 Playwright 验证修复
```

### 学习新技术

```
1️⃣ 用 Context7 查找官方文档
2️⃣ 用 Exa-Code 搜索代码示例
3️⃣ 用 Sequential Thinking 理解核心概念
4️⃣ 用 Playwright 实践自动化测试
```

---

## 🎯 性能指标参考

### Core Web Vitals 标准

| 指标 | 良好 | 需要改进 | 差 |
|------|------|----------|-----|
| **LCP** | <2.5s | 2.5s-4.0s | >4.0s |
| **FID** | <100ms | 100ms-300ms | >300ms |
| **CLS** | <0.1 | 0.1-0.25 | >0.25 |
| **FCP** | <1.8s | 1.8s-3.0s | >3.0s |
| **TTFB** | <0.8s | 0.8s-1.8s | >1.8s |

### 网络速度参考

| 网络类型 | 下载速度 | 延迟 | 适用场景 |
|---------|---------|------|----------|
| **Fast 4G** | 4 Mbps | 170ms | 城市 4G |
| **Slow 4G** | 1.6 Mbps | 300ms | 郊区 4G |
| **Fast 3G** | 1.6 Mbps | 562ms | 城市 3G |
| **Slow 3G** | 400 Kbps | 2000ms | 弱网环境 |

### CPU 限流参考

| 限流倍数 | 适用场景 |
|---------|----------|
| **1x** | 高性能设备 |
| **2x** | 中等性能设备 |
| **4x** | 低性能设备 |
| **6x** | 极低性能设备 |

---

## 🔧 常用配置

### Chrome DevTools 配置

```json
{
  "name": "chrome-devtools",
  "command": "npx",
  "args": [
    "chrome-devtools-mcp@latest",
    "--headless=true",
    "--isolated=true"
  ]
}
```

### Playwright 配置

```json
{
  "name": "playwright",
  "command": "npx",
  "args": ["-y", "@playwright/mcp"]
}
```

### Exa-Code 配置（需要 API Key）

```json
{
  "name": "exa-code",
  "command": "npx",
  "args": ["-y", "exa-code-mcp"],
  "env": {
    "EXA_API_KEY": "your-api-key-here"
  }
}
```

---

## 📝 快速故障排查

### Chrome DevTools 显示红点

**原因**：按需启动机制，正常现象

**验证**：
```
打开 https://example.com
```
如果能成功打开，说明工具正常。

### Exa-Code 无法使用

**原因**：缺少 API Key

**解决**：
1. 在 `.env.local` 中添加 `EXA_API_KEY`
2. 在配置中添加 `env` 字段

### 性能数据不准确

**原因**：缓存影响

**解决**：
1. 使用 `--isolated=true` 参数
2. 多次测试取平均值
3. 清理浏览器缓存

### Playwright 操作超时

**原因**：元素未加载或选择器错误

**解决**：
1. 增加等待时间
2. 使用更精确的选择器
3. 检查元素是否真的存在

---

## 💡 专业提示

### 性能优化优先级

1. **🔴 高优先级**（影响 >500ms）
   - 优化 TTFB
   - 压缩图片
   - 减少渲染阻塞

2. **🟡 中优先级**（影响 200-500ms）
   - 代码分割
   - 延迟加载
   - 优化字体

3. **🟢 低优先级**（影响 <200ms）
   - 第三方脚本优化
   - 细节优化

### 测试最佳实践

1. ✅ 建立性能基线
2. ✅ 多次测试取平均值
3. ✅ 在不同条件下测试
4. ✅ 自动化测试流程
5. ✅ 持续监控性能

### 调试技巧

1. ✅ 先查看控制台错误
2. ✅ 分析网络请求
3. ✅ 使用性能追踪
4. ✅ 截图保存现场
5. ✅ 记录重现步骤

---

## 🔗 相关资源

- [Chrome DevTools MCP 使用指南](./Chrome-DevTools-MCP使用指南.md)
- [实战案例](./Chrome-DevTools与Playwright实战案例.md)
- [Web.dev 性能优化](https://web.dev/performance/)
- [Playwright 官方文档](https://playwright.dev/)

---

**最后更新**：2025-10-12

