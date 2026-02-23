#!/bin/bash
# 清理 mypy unused-ignore 错误

set -e

cd "$(dirname "$0")/../backend"

echo "🧹 清理 mypy unused-ignore 错误..."

# 获取所有 unused-ignore 错误
mypy --strict app/ tests/ 2>&1 | grep "Unused \"type: ignore\" comment" | while read -r line; do
    # 提取文件名和行号
    file=$(echo "$line" | cut -d: -f1)
    lineno=$(echo "$line" | cut -d: -f2)
    
    if [ -f "$file" ]; then
        echo "  修复: $file:$lineno"
        # 删除该行的 # type: ignore 注释
        sed -i '' "${lineno}s/  *# type: ignore.*$//" "$file"
    fi
done

echo "✅ 清理完成！"
echo ""
echo "📊 重新运行 mypy 检查..."
mypy --strict app/tasks/crawler_task.py app/services/incremental_crawler.py 2>&1 | head -20

