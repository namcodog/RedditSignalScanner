#!/bin/bash
#
# 数据库备份脚本
#
# 功能:
# 1. 备份 PostgreSQL 数据库到 .sql.gz 文件
# 2. 保留最近7天的备份
# 3. 记录备份日志
#
# 使用方法:
#   ./scripts/backup_database.sh
#
# Cron 配置:
#   0 2 * * * /path/to/backup_database.sh >> /tmp/backup.log 2>&1

set -e  # 遇到错误立即退出

# 配置
DB_NAME="reddit_scanner"
DB_USER="postgres"
BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/backup"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 开始备份
echo "✅ 开始备份数据库 ${DB_NAME}..."
echo "   时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 执行备份
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

# 检查备份文件
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ 备份完成: $BACKUP_FILE"
    echo "   大小: $BACKUP_SIZE"
else
    echo "❌ 备份失败: 文件未生成"
    exit 1
fi

# 清理旧备份（保留最近7天）
echo "🧹 清理旧备份（保留 ${RETENTION_DAYS} 天）..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# 列出当前备份
echo "📋 当前备份列表:"
ls -lh "$BACKUP_DIR"/${DB_NAME}_*.sql.gz | tail -5

echo "✅ 备份任务完成"

