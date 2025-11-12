#!/usr/bin/env python3
"""简化的 Excel 导入脚本 - 默认读取 data/community/社区筛选.xlsx"""

import json
import sys
from pathlib import Path

import pandas as pd


def convert_excel_to_json(excel_path: str, output_path: str) -> None:
    """从 Excel 转换为 JSON"""
    
    # 读取 Excel，跳过第一行标题
    df = pd.read_excel(excel_path, skiprows=1)
    
    print(f"📊 读取 Excel: {len(df)} 行")
    print(f"📋 列名: {list(df.columns)}")
    
    communities = []
    
    for idx, row in df.iterrows():
        # 获取社区名称
        name = str(row['子版块名称']).strip()
        
        # 跳过分类行和空行
        if not name or name.startswith('职业与实践') or name.startswith('产品与创新') or name.startswith('技术与工具'):
            continue
        
        # 确保以 r/ 开头
        if not name.startswith('r/'):
            name = f'r/{name}'
        
        # 获取最终入选状态
        is_active_raw = str(row.get('最终入选', '是')).strip()
        is_active = is_active_raw in ['是', '1', 'True', 'true', 'YES', 'yes']
        
        # 只导入最终入选的社区
        if not is_active:
            continue
        
        # 获取质量评分
        try:
            health_score = float(row.get('量化健康分 (1-100)', 50))
            quality_score = health_score / 100.0  # 转换为 0-1 范围
        except:
            quality_score = 0.5
        
        # 根据质量评分确定层级
        if quality_score >= 0.8:
            tier = 'gold'
        elif quality_score >= 0.6:
            tier = 'silver'
        else:
            tier = 'bronze'
        
        # 获取分类
        categories_raw = str(row.get('主要分类', '')).strip()
        if categories_raw and categories_raw != 'nan':
            categories = [c.strip() for c in categories_raw.replace('，', ',').split(',') if c.strip()]
        else:
            categories = ['general']
        
        # 获取关键词
        keywords_raw = str(row.get('观察到的核心痛点 (备注)', '')).strip()
        if keywords_raw and keywords_raw != 'nan':
            keywords = [k.strip() for k in keywords_raw.replace('，', ',').split(',') if k.strip()]
        else:
            keywords = []
        
        community = {
            'name': name,
            'tier': tier,
            'categories': categories,
            'description_keywords': keywords,
            'daily_posts': 0,  # 默认值
            'avg_comment_length': 0,  # 默认值
            'quality_score': round(quality_score, 2)
        }
        
        communities.append(community)
    
    # 保存为 JSON
    output = {'seed_communities': communities}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    
    print(f"✅ 已生成 {len(communities)} 个社区到 {output_path}")
    
    # 显示层级分布
    tier_counts = {}
    for c in communities:
        tier = c['tier']
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    print(f"\n📊 层级分布:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")


if __name__ == '__main__':
    default_excel = Path('data/community/社区筛选.xlsx')
    legacy_excel = Path('社区筛选.xlsx')

    if len(sys.argv) > 1:
        excel_input = Path(sys.argv[1])
    else:
        excel_input = default_excel
        if not excel_input.exists() and legacy_excel.exists():
            print("⚠️  data/community 未发现社区筛选Excel，回退读取仓库根目录副本 ...")
            excel_input = legacy_excel

    output_file = sys.argv[2] if len(sys.argv) > 2 else 'backend/config/seed_communities.json'
    
    convert_excel_to_json(str(excel_input), output_file)
