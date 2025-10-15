#!/usr/bin/env bash
# Exa-Code MCP 包装脚本 - 用于调试
LOG_FILE="/tmp/mcp-exa-code.log"

echo "=== Exa-Code MCP 启动 ===" >> "$LOG_FILE"
echo "时间: $(date)" >> "$LOG_FILE"
echo "参数: $@" >> "$LOG_FILE"
echo "PATH: $PATH" >> "$LOG_FILE"
echo "PWD: $PWD" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 设置工作目录和 npm 缓存
cd "$HOME" || cd /tmp
export npm_config_cache="$HOME/.npm"
export npm_config_prefix="$HOME/.npm-global"

# 加载 .env.local 中的 EXA_API_KEY
ENV_FILE="/Users/hujia/Desktop/RedditSignalScanner/.env.local"
if [ -f "$ENV_FILE" ]; then
    export EXA_API_KEY=$(grep "^EXA_API_KEY=" "$ENV_FILE" | cut -d '=' -f2)
    echo "EXA_API_KEY 已加载: ${EXA_API_KEY:0:10}..." >> "$LOG_FILE"
else
    echo "警告: 未找到 .env.local 文件" >> "$LOG_FILE"
fi

# 执行实际的 MCP 工具
exec /usr/local/bin/npx -y exa-code-mcp "$@" 2>> "$LOG_FILE"

