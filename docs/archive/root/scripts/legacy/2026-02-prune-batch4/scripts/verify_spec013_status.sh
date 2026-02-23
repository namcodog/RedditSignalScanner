#!/usr/bin/env bash
# Spec 013 状态核查脚本
# 用途：验证所有已实施的功能是否正常运行
# 使用：bash scripts/verify_spec013_status.sh

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 检查函数
check_item() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "\n${BLUE}[检查 $TOTAL_CHECKS]${NC} $name"
    echo -e "${YELLOW}执行:${NC} $command"
    
    if eval "$command" > /tmp/check_output.txt 2>&1; then
        local output=$(cat /tmp/check_output.txt)
        if [[ -n "$expected" ]] && ! echo "$output" | grep -q "$expected"; then
            echo -e "${RED}❌ 失败${NC} - 未找到预期输出: $expected"
            echo -e "${YELLOW}实际输出:${NC}"
            cat /tmp/check_output.txt | head -5
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        else
            echo -e "${GREEN}✅ 通过${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        fi
    else
        echo -e "${RED}❌ 失败${NC} - 命令执行失败"
        cat /tmp/check_output.txt | head -5
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

echo "=========================================="
echo "  Spec 013 状态核查"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ============================================
# Phase 0: 基础设施检查
# ============================================
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 0: 基础设施检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Redis 运行状态
check_item "Redis 运行状态" \
    "redis-cli ping" \
    "PONG"

# 2. PostgreSQL 连接
check_item "PostgreSQL 连接" \
    "psql -h localhost -p 5432 -U postgres -d reddit_signal_scanner -c 'SELECT 1' -t" \
    "1"

# 3. Celery Worker 运行
check_item "Celery Worker 运行" \
    "ps aux | grep 'celery.*worker' | grep -v grep" \
    "celery"

# 4. Celery Beat 运行
check_item "Celery Beat 运行" \
    "ps aux | grep 'celery.*beat' | grep -v grep" \
    "celery"

# 5. Beat 日志存在
check_item "Beat 日志文件存在" \
    "ls -lh backend/tmp/celery_beat.log" \
    "celery_beat.log"

# 6. Worker 日志存在
check_item "Worker 日志文件存在" \
    "ls -lh backend/tmp/celery_worker.log" \
    "celery_worker.log"

# 7. 自愈守护运行（已归档，跳过）
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} 自愈守护运行"
echo -e "${YELLOW}⚠️  已归档，不再检查${NC}"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# ============================================
# Phase 1: 社区池检查
# ============================================
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 1: 社区池检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 8. 社区池规模
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} 社区池规模"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
POOL_SIZE=$(psql -h localhost -p 5432 -U postgres -d reddit_signal_scanner -t -c "SELECT COUNT(*) FROM community_pool WHERE is_active=true" 2>/dev/null | xargs)
if [[ -n "$POOL_SIZE" ]] && [[ "$POOL_SIZE" -ge 200 ]]; then
    echo -e "${GREEN}✅ 通过${NC} - 社区池规模: $POOL_SIZE (目标 ≥200)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    if [[ "$POOL_SIZE" -ge 300 ]]; then
        echo -e "${GREEN}🎉 优秀${NC} - 已达到扩充目标 (≥300)"
    else
        echo -e "${YELLOW}💡 建议${NC} - 执行 make pool-import-top1000 扩充到 300+"
    fi
else
    echo -e "${RED}❌ 失败${NC} - 社区池规模: $POOL_SIZE (目标 ≥200)"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 9. Tier 分布
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} Tier 分布"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -e "${YELLOW}执行:${NC} make pool-stats"
if make pool-stats > /tmp/pool_stats.txt 2>&1; then
    echo -e "${GREEN}✅ 通过${NC}"
    cat /tmp/pool_stats.txt | grep -E "T[123]|总计"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================
# Phase 2: 数据积累检查
# ============================================
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 2: 数据积累检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 10. 最近30天数据量
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} 最近30天数据量"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
POSTS_30D=$(psql -h localhost -p 5432 -U postgres -d reddit_signal_scanner -t -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '30 days'" 2>/dev/null | xargs)
if [[ -n "$POSTS_30D" ]]; then
    echo -e "${GREEN}✅ 数据量:${NC} $POSTS_30D 条"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    if [[ "$POSTS_30D" -ge 20000 ]]; then
        echo -e "${GREEN}🎉 优秀${NC} - 已达到目标 (≥20,000)"
    elif [[ "$POSTS_30D" -ge 15000 ]]; then
        echo -e "${YELLOW}💡 良好${NC} - 接近目标 (≥20,000)"
    else
        echo -e "${YELLOW}⚠️  不足${NC} - 需要继续积累 (目标 ≥20,000)"
    fi
else
    echo -e "${RED}❌ 失败${NC} - 无法查询数据量"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 11. 最近7天增长趋势
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} 最近7天增长趋势"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -e "${YELLOW}执行:${NC} make posts-growth-7d"
if make posts-growth-7d > /tmp/growth_7d.txt 2>&1; then
    echo -e "${GREEN}✅ 通过${NC}"
    cat /tmp/growth_7d.txt | tail -10
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    # 计算平均日增
    AVG_DAILY=$(cat /tmp/growth_7d.txt | grep -E "^\d{4}-\d{2}-\d{2}," | awk -F',' '{sum+=$2; count++} END {if(count>0) print int(sum/count); else print 0}')
    if [[ -n "$AVG_DAILY" ]] && [[ "$AVG_DAILY" -ge 1000 ]]; then
        echo -e "${GREEN}🎉 优秀${NC} - 平均日增: $AVG_DAILY 条/天 (目标 ≥1,000)"
    elif [[ -n "$AVG_DAILY" ]] && [[ "$AVG_DAILY" -ge 500 ]]; then
        echo -e "${YELLOW}💡 良好${NC} - 平均日增: $AVG_DAILY 条/天 (目标 ≥1,000)"
    else
        echo -e "${YELLOW}⚠️  不足${NC} - 平均日增: $AVG_DAILY 条/天 (目标 ≥1,000)"
    fi
else
    echo -e "${RED}❌ 失败${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 12. Celery 任务执行痕迹
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} Celery 任务执行痕迹"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -e "${YELLOW}执行:${NC} make celery-meta-count"
if make celery-meta-count > /tmp/meta_count.txt 2>&1; then
    META_COUNT=$(cat /tmp/meta_count.txt | grep -oE '[0-9]+' | head -1)
    if [[ -n "$META_COUNT" ]] && [[ "$META_COUNT" -gt 0 ]]; then
        echo -e "${GREEN}✅ 通过${NC} - 任务元数据: $META_COUNT 条"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}❌ 失败${NC} - 无任务执行痕迹"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    echo -e "${RED}❌ 失败${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# ============================================
# Phase 3: 质量检查（可选）
# ============================================
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 3: 质量检查（可选）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 13. 端到端健康快照
echo -e "\n${BLUE}[检查 $((TOTAL_CHECKS + 1))]${NC} 端到端健康快照"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -e "${YELLOW}执行:${NC} make pipeline-health"
if make pipeline-health > /tmp/pipeline_health.txt 2>&1; then
    echo -e "${GREEN}✅ 通过${NC}"
    cat /tmp/pipeline_health.txt | tail -20
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${YELLOW}⚠️  跳过${NC} - 可选检查"
fi

# ============================================
# 总结
# ============================================
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查总结${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

PASS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo -e "\n总检查项: $TOTAL_CHECKS"
echo -e "${GREEN}通过: $PASSED_CHECKS${NC}"
echo -e "${RED}失败: $FAILED_CHECKS${NC}"
echo -e "通过率: ${PASS_RATE}%"

if [[ "$PASS_RATE" -ge 90 ]]; then
    echo -e "\n${GREEN}🎉 优秀！Spec 013 运行状态良好！${NC}"
    exit 0
elif [[ "$PASS_RATE" -ge 70 ]]; then
    echo -e "\n${YELLOW}💡 良好，但有改进空间。${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  需要关注！多个检查项失败。${NC}"
    exit 1
fi
