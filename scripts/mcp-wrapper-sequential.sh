#!/usr/bin/env bash
# Sequential Thinking MCP 包装脚本
LOG_FILE="/tmp/mcp-sequential-thinking.log"

echo "=== Sequential Thinking MCP 启动 ===" >> "$LOG_FILE"
echo "时间: $(date)" >> "$LOG_FILE"
echo "参数: $@" >> "$LOG_FILE"
echo "PATH: $PATH" >> "$LOG_FILE"
echo "PWD: $PWD" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 设置工作目录和 npm 缓存
cd "$HOME" || cd /tmp
export npm_config_cache="$HOME/.npm"
export npm_config_prefix="$HOME/.npm-global"

# 执行实际的 MCP 工具
exec /usr/local/bin/npx -y @modelcontextprotocol/server-sequential-thinking "$@" 2>> "$LOG_FILE"

