# DEPRECATED

> 本文档已归档，不再作为当前口径。请以 docs/2025-10-10-文档阅读指南.md 指定的文档为准。

# MCP 工具配置指南

**日期**: 2025-10-11  
**目的**: 配置 Exa Code 和 Chrome DevTools MCP 工具，用于深度代码分析和浏览器调试

---

## 📋 概述

本项目使用三个 MCP (Model Context Protocol) 工具：

1. **exa-mcp-server**: 用于代码搜索和最佳实践查找
2. **chrome-devtools-mcp**: 用于浏览器自动化和性能分析
3. **spec-kit**: GitHub 的 Spec-Driven Development 工具包

前两个工具通过 `npx` 运行，Spec Kit 通过 `uv` 安装。

---

## 🔑 API Keys

### Exa API Key

已配置在 `.env.local` 文件中：

```bash
EXA_API_KEY=b885d11f-2022-4559-b1cb-c3b4d3e67103
```

**获取新的 API Key**:
- 访问: https://dashboard.exa.ai/api-keys
- 注册并创建新的 API Key
- 更新 `.env.local` 文件

---

## 🛠️ 配置步骤

### 步骤 1: 安装 MCP 工具

```bash
make mcp-install
```

这会：
1. 安装 Spec Kit (Python CLI)
2. 显示完整的配置说明
3. 提供配置示例

### 步骤 2: 配置 MCP Servers

根据你使用的 IDE/编辑器，将以下配置添加到对应的配置文件中：

#### Claude Desktop

配置文件位置:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

配置内容:

```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": {
        "EXA_API_KEY": "b885d11f-2022-4559-b1cb-c3b4d3e67103"
      }
    },
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    },
    "spec-kit": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/github/spec-kit.git",
        "specify"
      ]
    }
  }
}
```

#### Cursor

1. 打开 Cursor Settings
2. 进入 MCP 设置
3. 点击 "New MCP Server"
4. 添加以下配置：

**Exa MCP Server**:
```json
{
  "name": "exa",
  "command": "npx",
  "args": ["-y", "exa-mcp-server"],
  "env": {
    "EXA_API_KEY": "b885d11f-2022-4559-b1cb-c3b4d3e67103"
  }
}
```

**Chrome DevTools MCP**:
```json
{
  "name": "chrome-devtools",
  "command": "npx",
  "args": ["-y", "chrome-devtools-mcp@latest"]
}
```

#### VS Code (Copilot)

使用 VS Code CLI:

```bash
# Exa MCP Server
code --add-mcp '{"name":"exa","command":"npx","args":["-y","exa-mcp-server"],"env":{"EXA_API_KEY":"b885d11f-2022-4559-b1cb-c3b4d3e67103"}}'

# Chrome DevTools MCP
code --add-mcp '{"name":"chrome-devtools","command":"npx","args":["-y","chrome-devtools-mcp@latest"]}'
```

### 步骤 3: 验证安装

```bash
make mcp-verify
```

这会测试两个 MCP 工具是否可以正常运行。

---

## 🎯 使用示例

### Exa MCP Server

**用途**: 查找代码最佳实践、解决方案和示例

**示例提示**:

```text
使用 exa-code 查找 pytest-asyncio 事件循环冲突的最佳实践
```

```text
使用 exa-code 搜索 SQLAlchemy AsyncEngine 连接池管理的示例
```

### Chrome DevTools MCP

**用途**: 浏览器自动化、性能分析、端到端测试

**示例提示**:

```text
使用 chrome-devtools 检查 http://localhost:3007 的性能
```

```text
使用 chrome-devtools 打开浏览器并截图 http://localhost:3007/report/123
```

### Spec Kit

**用途**: Spec-Driven Development 工作流，从需求到实现

**可用命令**:

- `/speckit.constitution`: 创建项目治理原则
- `/speckit.specify`: 定义功能需求
- `/speckit.plan`: 创建技术实现计划
- `/speckit.tasks`: 生成任务列表
- `/speckit.implement`: 执行实现

**示例提示**:

```text
使用 /speckit.specify 创建一个照片管理应用的需求规格
```

```text
使用 /speckit.plan 为这个应用选择 React + FastAPI 技术栈
```

---

## 🔧 故障排查

### 问题 1: exa-mcp-server 启动失败

**症状**: `EXA_API_KEY is required`

**解决方案**:
1. 检查 `.env.local` 文件中的 `EXA_API_KEY`
2. 确保 MCP 配置中正确设置了 `env.EXA_API_KEY`
3. 重启 IDE/编辑器

### 问题 2: chrome-devtools-mcp 无法启动浏览器

**症状**: `Failed to launch browser`

**解决方案**:
1. 确保 Chrome 已安装
2. 检查 Chrome 路径是否正确
3. 尝试使用 `--headless=false` 参数查看浏览器窗口

### 问题 3: npx 命令找不到

**症状**: `npx: command not found`

**解决方案**:
1. 确保 Node.js 已安装: `node --version`
2. 确保 npm 已安装: `npm --version`
3. 重新安装 Node.js: https://nodejs.org/

---

## 📚 文档链接

- **Exa MCP Server**: <https://docs.exa.ai/reference/exa-mcp>
- **Chrome DevTools MCP**: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
- **Spec Kit**: <https://github.com/github/spec-kit>
- **MCP Protocol**: <https://modelcontextprotocol.io/>

---

## 🚀 快速开始

1. 运行配置指南:
   ```bash
   make mcp-install
   ```

2. 根据你的 IDE 配置 MCP servers

3. 验证安装:
   ```bash
   make mcp-verify
   ```

4. 在你的 IDE 中测试:
   ```
   使用 exa-code 查找 FastAPI 异步测试的最佳实践
   ```

---

## 📝 注意事项

1. **API Key 安全**: 不要将 API Key 提交到 Git 仓库
2. **Chrome 权限**: Chrome DevTools MCP 需要启动浏览器，确保有足够的权限
3. **网络连接**: Exa MCP Server 需要网络连接来搜索代码
4. **资源使用**: Chrome DevTools MCP 会启动浏览器进程，注意资源使用

---

**配置完成后，你可以在 IDE 中直接使用这两个 MCP 工具来辅助开发和调试！**

