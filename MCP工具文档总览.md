# MCP 工具文档总览

> 本项目配置了 6 个强大的 MCP (Model Context Protocol) 工具，用于提升 AI 辅助开发的能力。

## 📚 文档导航

### 🎯 快速开始

- **[MCP 工具快速参考](./MCP工具快速参考.md)** - 常用命令速查表
  - 适合：日常快速查找
  - 内容：常用 AI 提示、配置示例、故障排查

### 📖 详细指南

- **[Chrome DevTools MCP 使用指南](./Chrome-DevTools-MCP使用指南.md)** - 完整功能说明
  - 适合：深入了解工具能力
  - 内容：核心功能、使用示例、与 Playwright 对比、最佳实践

- **[Chrome DevTools 与 Playwright 实战案例](./Chrome-DevTools与Playwright实战案例.md)** - 真实场景应用
  - 适合：学习实际应用方法
  - 内容：6 个完整案例、高级技巧、组合使用策略

---

## 🛠️ 已配置的 MCP 工具

### 1. Chrome DevTools MCP ⭐⭐⭐

**定位**：专业的性能分析和调试工具

**核心能力**：
- ✅ 深度性能分析（LCP、CLS、FCP 等）
- ✅ AI 驱动的性能优化建议
- ✅ 网络请求详细分析
- ✅ 控制台调试
- ✅ 性能追踪和洞察

**适用场景**：
- 网站性能优化
- Core Web Vitals 优化
- 性能瓶颈诊断
- 前端性能监控

**快速开始**：
```
分析 https://example.com 的性能
```

**文档**：[Chrome DevTools MCP 使用指南](./Chrome-DevTools-MCP使用指南.md)

---

### 2. Playwright MCP ⭐⭐⭐

**定位**：强大的端到端测试和自动化工具

**核心能力**：
- ✅ 跨浏览器支持（Chrome、Firefox、Safari）
- ✅ 可靠的自动化（自动等待、重试）
- ✅ 丰富的交互（表单、拖拽、文件上传）
- ✅ 网络控制（拦截、模拟离线）
- ✅ 多页面管理

**适用场景**：
- 端到端测试
- UI 自动化测试
- 网页爬虫
- 表单自动填写

**快速开始**：
```
打开 https://example.com 并点击"登录"按钮
```

**文档**：[Chrome DevTools MCP 使用指南](./Chrome-DevTools-MCP使用指南.md#与-playwright-对比)

---

### 3. Context7 ⭐⭐

**定位**：文档检索工具

**核心能力**：
- ✅ 查询任何库的官方文档
- ✅ 获取代码示例
- ✅ 支持多个版本

**适用场景**：
- 学习新技术
- 查找 API 文档
- 获取最佳实践

**快速开始**：
```
用 Context7 查找 React 的文档
```

**文档**：[MCP 工具快速参考](./MCP工具快速参考.md#-context7)

---

### 4. Exa-Code ⭐⭐

**定位**：代码搜索工具

**核心能力**：
- ✅ 搜索代码示例
- ✅ 查找最佳实践
- ✅ 获取实际应用案例

**适用场景**：
- 学习编程模式
- 查找解决方案
- 代码参考

**快速开始**：
```
用 Exa-Code 搜索 React hooks 的最佳实践
```

**配置要求**：需要 API Key（已在 `.env.local` 中配置）

**文档**：[MCP 工具快速参考](./MCP工具快速参考.md#-exa-code)

---

### 5. Sequential Thinking ⭐⭐

**定位**：顺序化思考工具

**核心能力**：
- ✅ 分步骤分析复杂问题
- ✅ 结构化思考过程
- ✅ 生成解决方案

**适用场景**：
- 复杂问题分析
- 架构设计
- 算法设计

**快速开始**：
```
用 Sequential Thinking 分析如何优化 React 应用性能
```

**文档**：[MCP 工具快速参考](./MCP工具快速参考.md#-sequential-thinking)

---

### 6. Serena ⭐⭐⭐

**定位**：IDE 辅助工具集（18 个工具）

**核心能力**：
- ✅ 代码搜索和导航
- ✅ 符号查找
- ✅ 引用查找
- ✅ 文件操作
- ✅ 内存管理

**适用场景**：
- 代码库导航
- 重构
- 代码分析

**快速开始**：
```
在项目中查找所有使用 useState 的地方
```

---

## 🎯 推荐使用场景

### 场景 1：性能优化

**工具组合**：Chrome DevTools + Exa-Code + Playwright

**工作流**：
1. 用 Chrome DevTools 分析性能
2. 用 Exa-Code 搜索优化方案
3. 实施优化
4. 用 Playwright 回归测试
5. 用 Chrome DevTools 验证效果

**参考**：[实战案例 - 电商网站性能优化](./Chrome-DevTools与Playwright实战案例.md#案例-1电商网站性能优化)

---

### 场景 2：调试问题

**工具组合**：Playwright + Chrome DevTools + Sequential Thinking

**工作流**：
1. 用 Playwright 重现问题
2. 用 Chrome DevTools 查看错误
3. 用 Sequential Thinking 分析根因
4. 修复问题
5. 用 Playwright 验证修复

**参考**：[实战案例 - SPA 应用调试](./Chrome-DevTools与Playwright实战案例.md#案例-2spa-应用调试)

---

### 场景 3：学习新技术

**工具组合**：Context7 + Exa-Code + Serena

**工作流**：
1. 用 Context7 查找官方文档
2. 用 Exa-Code 搜索代码示例
3. 用 Serena 在项目中实践
4. 用 Sequential Thinking 理解核心概念

---

### 场景 4：自动化测试

**工具组合**：Playwright + Chrome DevTools

**工作流**：
1. 用 Playwright 执行测试流程
2. 用 Chrome DevTools 监控性能
3. 自动化性能回归检测

**参考**：[实战案例 - 自动化性能监控](./Chrome-DevTools与Playwright实战案例.md#案例-4自动化性能监控)

---

## 📊 工具对比矩阵

| 功能 | Chrome DevTools | Playwright | Context7 | Exa-Code | Sequential | Serena |
|------|----------------|------------|----------|----------|------------|--------|
| **性能分析** | ⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **浏览器自动化** | ⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| **文档查询** | ❌ | ❌ | ⭐⭐⭐ | ❌ | ❌ | ❌ |
| **代码搜索** | ❌ | ❌ | ❌ | ⭐⭐⭐ | ❌ | ⭐⭐ |
| **问题分析** | ❌ | ❌ | ❌ | ❌ | ⭐⭐⭐ | ❌ |
| **代码导航** | ❌ | ❌ | ❌ | ❌ | ❌ | ⭐⭐⭐ |

---

## 🚀 快速开始

### 验证工具状态

```bash
./scripts/verify-mcp-tools.sh
```

**预期输出**：所有 6 个工具都显示 ✅

### 测试工具

**测试 Chrome DevTools**：
```
分析 https://example.com 的性能
```

**测试 Playwright**：
```
打开 https://google.com 并截图
```

**测试 Context7**：
```
用 Context7 查找 React 的文档
```

**测试 Exa-Code**：
```
用 Exa-Code 搜索 TypeScript 最佳实践
```

---

## 🔧 配置文件

### 主配置文件

- **VSCode Settings**：`~/Library/Application Support/Code/User/settings.json`
- **环境变量**：`.env.local`
- **包装脚本**：`scripts/mcp-wrapper-*.sh`

### 验证脚本

- **验证工具状态**：`scripts/verify-mcp-tools.sh`

### 配置示例

完整配置示例请参考：[MCP 工具快速参考 - 常用配置](./MCP工具快速参考.md#-常用配置)

---

## 📝 常见问题

### Q: 工具显示红点是否正常？

**A**: 正常。Chrome DevTools 采用按需启动机制。

**详细说明**：[Chrome DevTools MCP 使用指南 - 常见问题](./Chrome-DevTools-MCP使用指南.md#常见问题)

### Q: 如何优化性能？

**A**: 使用 Chrome DevTools 进行分析。

**完整指南**：[实战案例 - 电商网站性能优化](./Chrome-DevTools与Playwright实战案例.md#案例-1电商网站性能优化)

### Q: 如何组合使用多个工具？

**A**: 根据场景选择合适的工具组合。

**参考**：[推荐使用场景](#-推荐使用场景)

---

## 📖 学习路径

### 初学者

1. 阅读 [MCP 工具快速参考](./MCP工具快速参考.md)
2. 尝试基本的 AI 提示
3. 验证工具是否正常工作

### 进阶用户

1. 阅读 [Chrome DevTools MCP 使用指南](./Chrome-DevTools-MCP使用指南.md)
2. 学习工具的核心功能
3. 了解与 Playwright 的对比

### 高级用户

1. 阅读 [实战案例](./Chrome-DevTools与Playwright实战案例.md)
2. 学习组合使用策略
3. 建立自动化工作流

---

## 🎓 最佳实践

### 性能优化

1. ✅ 建立性能基线
2. ✅ 使用 Chrome DevTools 分析
3. ✅ 实施优化
4. ✅ 用 Playwright 回归测试
5. ✅ 持续监控

**详细指南**：[Chrome DevTools MCP 使用指南 - 最佳实践](./Chrome-DevTools-MCP使用指南.md#最佳实践)

### 调试问题

1. ✅ 用 Playwright 重现问题
2. ✅ 用 Chrome DevTools 分析
3. ✅ 用 Sequential Thinking 思考
4. ✅ 用 Exa-Code 查找方案
5. ✅ 验证修复

**详细案例**：[实战案例 - SPA 应用调试](./Chrome-DevTools与Playwright实战案例.md#案例-2spa-应用调试)

---

## 🔗 相关资源

### 官方文档

- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [Playwright](https://playwright.dev/)
- [Web.dev 性能优化](https://web.dev/performance/)
- [Core Web Vitals](https://web.dev/vitals/)

### 项目文档

- [README.md](./README.md) - 项目总览
- [PRD 文档](./PRD/) - 产品需求文档

---

## 📞 获取帮助

### 故障排查

参考：[MCP 工具快速参考 - 快速故障排查](./MCP工具快速参考.md#-快速故障排查)

### 常见问题

参考：[Chrome DevTools MCP 使用指南 - 常见问题](./Chrome-DevTools-MCP使用指南.md#常见问题)

---

**最后更新**：2025-10-12

**文档版本**：1.0.0

**维护者**：Reddit Signal Scanner 项目团队

