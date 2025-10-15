#!/usr/bin/env bash
# 测试 MCP 工具是否能通过 stdio 正常通信
set -euo pipefail

echo "=== 测试 MCP 工具 stdio 通信 ==="
echo ""

# 测试 Context7
echo "1. 测试 Context7..."
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | /usr/local/bin/npx -y @upstash/context7-mcp 2>&1 | head -3
echo ""

# 测试 Sequential Thinking
echo "2. 测试 Sequential Thinking..."
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | /usr/local/bin/npx -y @modelcontextprotocol/server-sequential-thinking 2>&1 | head -3
echo ""

# 测试 Playwright
echo "3. 测试 Playwright..."
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | /usr/local/bin/npx -y @playwright/mcp 2>&1 | head -3
echo ""

# 测试 Exa-Code
echo "4. 测试 Exa-Code..."
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | /usr/local/bin/npx -y exa-code-mcp 2>&1 | head -3
echo ""

# 测试 Chrome DevTools
echo "5. 测试 Chrome DevTools..."
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | /usr/local/bin/npx -y chrome-devtools-mcp 2>&1 | head -3
echo ""

echo "=== 测试完成 ==="

