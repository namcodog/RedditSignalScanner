#!/usr/bin/env bash

# MCP 配置验证脚本
# 用于检查所有 MCP 工具是否正确配置

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   MCP 工具配置验证${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 配置文件路径
MCP_CONFIG="$HOME/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
SCRIPT_DIR="/Users/hujia/Desktop/RedditSignalScanner/scripts/mcp"

# 1. 检查配置文件是否存在
echo -e "${YELLOW}[1/6] 检查配置文件...${NC}"
if [ -f "$MCP_CONFIG" ]; then
    echo -e "${GREEN}✓ 配置文件存在${NC}"
    echo -e "   路径: $MCP_CONFIG"
else
    echo -e "${RED}✗ 配置文件不存在${NC}"
    exit 1
fi

# 2. 检查配置文件语法
echo -e "\n${YELLOW}[2/6] 验证 JSON 语法...${NC}"
if python3 -m json.tool "$MCP_CONFIG" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ JSON 格式正确${NC}"
else
    echo -e "${RED}✗ JSON 格式错误${NC}"
    exit 1
fi

# 3. 检查 MCP 脚本是否存在
echo -e "\n${YELLOW}[3/6] 检查 MCP 脚本...${NC}"
SCRIPTS=(
    "serena.sh"
    "exa-code.sh"
    "chrome-devtools.sh"
    "playwright.sh"
    "sequential-thinking.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPT_DIR/$script" ]; then
        if [ -x "$SCRIPT_DIR/$script" ]; then
            echo -e "${GREEN}✓ $script (可执行)${NC}"
        else
            echo -e "${YELLOW}⚠ $script (不可执行)${NC}"
        fi
    else
        echo -e "${RED}✗ $script (不存在)${NC}"
    fi
done

# 4. 检查依赖
echo -e "\n${YELLOW}[4/6] 检查依赖...${NC}"

# 检查 Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js 未安装${NC}"
fi

# 检查 npx
if command -v npx &> /dev/null; then
    echo -e "${GREEN}✓ npx 可用${NC}"
else
    echo -e "${RED}✗ npx 不可用${NC}"
fi

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python3 未安装${NC}"
fi

# 5. 检查 Serena MCP
echo -e "\n${YELLOW}[5/6] 检查 Serena MCP...${NC}"
SERENA_DIR="/Users/hujia/Desktop/RedditSignalScanner/.serena-mcp"
if [ -d "$SERENA_DIR" ]; then
    echo -e "${GREEN}✓ Serena MCP 目录存在${NC}"
    
    if [ -d "$SERENA_DIR/.venv" ]; then
        echo -e "${GREEN}✓ Serena 虚拟环境存在${NC}"
    else
        echo -e "${YELLOW}⚠ Serena 虚拟环境不存在 (将尝试使用系统 Python)${NC}"
    fi
else
    echo -e "${RED}✗ Serena MCP 目录不存在${NC}"
fi

# 6. 显示配置摘要
echo -e "\n${YELLOW}[6/6] 配置摘要...${NC}"
echo -e "${BLUE}已配置的 MCP 服务器:${NC}"
python3 -c "
import json
with open('$MCP_CONFIG', 'r') as f:
    config = json.load(f)
    servers = config.get('mcpServers', {})
    for i, (name, settings) in enumerate(servers.items(), 1):
        status = '启用' if not settings.get('disabled', False) else '禁用'
        print(f'  {i}. {name} [{status}]')
        print(f'     命令: {settings.get(\"command\", \"N/A\")}')
" 2>/dev/null || echo -e "${RED}无法解析配置${NC}"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 验证完成！${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}下一步操作:${NC}"
echo -e "  1. 重启 Cursor/VS Code"
echo -e "  2. 在 Cline 侧边栏检查 MCP 连接状态"
echo -e "  3. 与 AI 对话时，工具会自动调用\n"

echo -e "${BLUE}提示: 如果遇到问题，查看日志:${NC}"
echo -e "  VS Code → 输出 → 选择 'Cline' 频道\n"
