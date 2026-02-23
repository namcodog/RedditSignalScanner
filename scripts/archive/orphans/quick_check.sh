#!/bin/bash
# 快速检查抓取状态

echo "=========================================="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

echo ""
echo "【1. 测试文件状态】"
echo "命令: ls -lh backend/data/reddit_corpus/ecommerce_test.jsonl*"
ls -lh backend/data/reddit_corpus/ecommerce_test.jsonl* 2>&1

echo ""
echo "【2. 进度文件内容】"
echo "命令: cat backend/data/reddit_corpus/ecommerce_test.jsonl.progress.json"
if [ -f "backend/data/reddit_corpus/ecommerce_test.jsonl.progress.json" ]; then
    cat backend/data/reddit_corpus/ecommerce_test.jsonl.progress.json | python3 -m json.tool 2>/dev/null || cat backend/data/reddit_corpus/ecommerce_test.jsonl.progress.json
else
    echo "✗ 进度文件不存在"
fi

echo ""
echo "【3. JSONL 行数】"
echo "命令: wc -l backend/data/reddit_corpus/ecommerce_test.jsonl"
wc -l backend/data/reddit_corpus/ecommerce_test.jsonl 2>&1

echo ""
echo "【4. 进程状态】"
echo "命令: ps aux | grep 'crawl_for_lexicon.py --mode time-sliced --subreddit ecommerce'"
ps aux | grep "crawl_for_lexicon.py --mode time-sliced --subreddit ecommerce" | grep -v grep || echo "无相关抓取进程运行"

echo ""
echo "=========================================="
echo "请将以上 4 个命令的输出复制给 AI"
echo "=========================================="

