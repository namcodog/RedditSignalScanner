#!/usr/bin/env python3
"""
更新 OpenAPI Schema 基线

当 API 发生有意的变更时，使用此脚本更新基线 schema。

用法:
    python scripts/update_baseline_schema.py
"""
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import create_application
from app.core.config import get_settings


def main():
    """更新基线 schema"""
    print("=" * 80)
    print("📝 更新 OpenAPI Schema 基线")
    print("=" * 80)
    print()
    
    # 生成当前 schema
    print("🔄 生成当前 schema...")
    app = create_application(get_settings())
    schema = app.openapi()
    
    # 保存到文件
    output_path = backend_dir / "docs" / "openapi-schema.json"
    
    print(f"💾 保存到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print()
    print("✅ 基线 schema 已更新")
    print()
    print(f"📊 Schema 信息:")
    print(f"   - 路径数: {len(schema.get('paths', {}))}")
    print(f"   - 组件数: {len(schema.get('components', {}).get('schemas', {}))}")
    print()
    print("💡 请将此文件提交到 Git:")
    print(f"   git add {output_path.relative_to(backend_dir.parent)}")
    print(f"   git commit -m 'docs(api): update OpenAPI schema baseline'")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

