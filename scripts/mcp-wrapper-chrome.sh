#!/usr/bin/env bash
# Chrome DevTools MCP 包装脚本
LOG_FILE="/tmp/mcp-chrome-devtools.log"

echo "=== Chrome DevTools MCP 启动 ===" >> "$LOG_FILE"
echo "时间: $(date)" >> "$LOG_FILE"
echo "参数: $@" >> "$LOG_FILE"
echo "PATH: $PATH" >> "$LOG_FILE"
echo "PWD: $PWD" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 设置工作目录和 npm 缓存
cd "$HOME" || cd /tmp
export npm_config_cache="$HOME/.npm"
export npm_config_prefix="$HOME/.npm-global"

# 使用 headless 模式和 isolated 模式
# 这样可以避免与现有 Chrome 实例冲突
exec /usr/local/bin/npx -y chrome-devtools-mcp@latest --headless=true --isolated=true "$@" 2>> "$LOG_FILE"

