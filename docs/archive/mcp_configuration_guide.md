# DEPRECATED

> 本文档已归档，不再作为当前口径。请以 docs/2025-10-10-文档阅读指南.md 指定的文档为准。

# MCP 工具配置指南

> **更新时间**: 2025-12-06  
> **配置位置**: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

---

## 📦 已配置的 MCP 工具

### 1️⃣ **Serena MCP** - 本地代码库分析引擎

**功能**：
- 深度代码库分析
- 符号检索和跳转
- 项目结构理解
- 代码质量评估

**配置**：
```json
{
  "command": "/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/serena.sh",
  "args": [],
  "env": {
    "PYTHONPATH": "/Users/hujia/Desktop/RedditSignalScanner/.serena-mcp/src"
  }
}
```

**启动脚本**: `scripts/mcp/serena.sh`

---

### 2️⃣ **Exa Code MCP** - 最佳实践搜索

**功能**：
- 从互联网搜索最新的编程最佳实践
- 查找类似代码示例
- 对比行业标准

**配置**：
```json
{
  "command": "/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/exa-code.sh",
  "args": [],
  "env": {}
}
```

**NPM 包**: `exa-code-mcp@latest`

---

### 3️⃣ **Chrome DevTools MCP** - 浏览器调试

**功能**：
- 端到端 UI 验证
- DOM 检查和性能分析
- 前端组件测试
- 网络请求监控

**配置**：
```json
{
  "command": "/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/chrome-devtools.sh",
  "args": [],
  "env": {}
}
```

**NPM 包**: `chrome-devtools-mcp@latest`

---

### 4️⃣ **Playwright MCP** - 自动化测试

**功能**：
- 模拟真实用户交互
- E2E 端到端测试
- 自动截图和录屏
- 跨浏览器测试

**配置**：
```json
{
  "command": "/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/playwright.sh",
  "args": [],
  "env": {}
}
```

**NPM 包**: `@playwright/mcp@latest`

---

### 5️⃣ **Sequential Thinking MCP** - 链式思考

**功能**：
- 多步推理和问题分解
- 复杂逻辑分析
- 决策树构建

**配置**：
```json
{
  "command": "/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/sequential-thinking.sh",
  "args": [],
  "env": {}
}
```

**NPM 包**: `@modelcontextprotocol/server-sequential-thinking@latest`

---

## 🔧 如何使用

### 在 Antigravity/Cline 中启用

1. **重启 Cursor/VS Code**  
   配置修改后需要重启编辑器才能生效

2. **检查 MCP 状态**  
   在 Cline 侧边栏中查看 MCP 服务器连接状态

3. **调用工具**  
   直接在对话中提到相关功能，AI 会自动调用对应的 MCP 工具

### 手动测试工具

```bash
# 测试 Serena MCP
/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/serena.sh

# 测试 Exa Code
/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/exa-code.sh

# 测试 Chrome DevTools
/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/chrome-devtools.sh

# 测试 Playwright
/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/playwright.sh

# 测试 Sequential Thinking
/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/sequential-thinking.sh
```

---

## 🛠️ 故障排查

### 工具无法连接

**检查步骤**：
1. 确认所有脚本都有执行权限：
   ```bash
   chmod +x scripts/mcp/*.sh
   ```

2. 查看 Cline 日志：
   - 打开 VS Code 输出面板
   - 选择 "Cline" 频道
   - 查找 MCP 相关错误信息

3. 手动测试 MCP 服务器：
   ```bash
   # 启动服务器（应该保持运行状态）
   /Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/serena.sh
   ```

### Serena MCP 特别注意

Serena MCP 依赖本地 Python 环境，确保：
- `.serena-mcp/.venv` 存在且已安装依赖
- 或者系统 Python 可以找到 `serena` 模块

### NPM 工具安装失败

所有 NPM 工具使用 `npx -y` 自动安装，如果遇到问题：
```bash
# 手动安装
npm install -g exa-code-mcp
npm install -g chrome-devtools-mcp
npm install -g @playwright/mcp
npm install -g @modelcontextprotocol/server-sequential-thinking
```

---

## 📝 配置文件位置

**主配置**:  
`~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

**备份**:  
`~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json.backup`

**本地脚本**:  
`/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp/`

---

## 🔄 更新配置

如需修改配置：

1. 编辑配置文件
2. 重启 Cursor/VS Code
3. 验证连接状态

或者直接运行：
```bash
code ~/Library/Application\ Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

---

## ✅ 验证清单

- [x] 5 个 MCP 工具已配置
- [x] Serena MCP 包装脚本已创建
- [x] 所有脚本具有执行权限
- [x] 配置文件语法正确
- [ ] Cursor/VS Code 已重启
- [ ] MCP 服务器连接成功

---

**下一步**：请重启 Cursor，然后在 Cline 中验证 MCP 工具是否正常连接。
