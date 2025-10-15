#!/usr/bin/env bash
# MCP 工具运行状态验证脚本
# 用途：检查所有 6 个 MCP 工具是否真正在运行

set -euo pipefail

echo "=== MCP 工具运行状态验证 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查进程
echo "1. 检查 Serena 进程:"
if ps aux | grep -E "serena.*mcp-server" | grep -v grep > /dev/null; then
    echo "   ✅ Serena 正在运行"
    ps aux | grep -E "serena.*mcp-server" | grep -v grep | head -2
else
    echo "   ❌ Serena 未运行"
fi
echo ""

echo "2. 检查 Context7 进程:"
if ps aux | grep -E "context7-mcp" | grep -v grep > /dev/null; then
    echo "   ✅ Context7 正在运行"
    ps aux | grep -E "context7-mcp" | grep -v grep | head -2
else
    echo "   ❌ Context7 未运行"
fi
echo ""

echo "3. 检查 Sequential Thinking 进程:"
if ps aux | grep -E "sequential-thinking" | grep -v grep > /dev/null; then
    echo "   ✅ Sequential Thinking 正在运行"
    ps aux | grep -E "sequential-thinking" | grep -v grep | head -2
else
    echo "   ❌ Sequential Thinking 未运行"
fi
echo ""

echo "4. 检查 Playwright 进程:"
if ps aux | grep -E "playwright.*mcp" | grep -v grep > /dev/null; then
    echo "   ✅ Playwright 正在运行"
    ps aux | grep -E "playwright.*mcp" | grep -v grep | head -2
else
    echo "   ❌ Playwright 未运行"
fi
echo ""

echo "5. 检查 Exa-Code 进程:"
if ps aux | grep -E "exa-code-mcp" | grep -v grep > /dev/null; then
    echo "   ✅ Exa-Code 正在运行"
    ps aux | grep -E "exa-code-mcp" | grep -v grep | head -2
else
    echo "   ❌ Exa-Code 未运行"
fi
echo ""

echo "6. 检查 Chrome DevTools 进程:"
if ps aux | grep -E "chrome-devtools-mcp" | grep -v grep > /dev/null; then
    echo "   ✅ Chrome DevTools 正在运行"
    ps aux | grep -E "chrome-devtools-mcp" | grep -v grep | head -2
else
    echo "   ❌ Chrome DevTools 未运行"
fi
echo ""

echo "=== 总结 ==="
RUNNING=$(ps aux | grep -E "serena.*mcp-server|context7-mcp|sequential-thinking|playwright.*mcp|exa-code-mcp|chrome-devtools-mcp" | grep -v grep | wc -l | tr -d ' ')
echo "当前运行的 MCP 工具数量: $RUNNING / 6"
echo ""

if [ "$RUNNING" -eq 6 ]; then
    echo "🎉 所有 MCP 工具都在正常运行！"
    exit 0
elif [ "$RUNNING" -gt 0 ]; then
    echo "⚠️  部分 MCP 工具未运行，请检查配置"
    exit 1
else
    echo "❌ 所有 MCP 工具都未运行，请重新配置"
    exit 2
fi

