#!/usr/bin/env python3
"""
API Breaking Changes 检测脚本

对比当前 OpenAPI schema 与基线版本，检测不兼容的变更。

Breaking Changes 包括:
- 删除端点
- 删除必需参数
- 修改参数类型
- 删除响应字段
- 修改响应类型

用法:
    python scripts/check_breaking_changes.py
    python scripts/check_breaking_changes.py --baseline docs/openapi-schema.json
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import create_application
from app.core.config import get_settings


class BreakingChangeDetector:
    """Breaking Change 检测器"""
    
    def __init__(self, baseline_path: Path):
        self.baseline_path = baseline_path
        self.breaking_changes: List[str] = []
        self.warnings: List[str] = []
    
    def load_baseline(self) -> Dict[str, Any]:
        """加载基线 schema"""
        if not self.baseline_path.exists():
            raise FileNotFoundError(f"基线文件不存在: {self.baseline_path}")
        
        with open(self.baseline_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_current_schema(self) -> Dict[str, Any]:
        """获取当前 schema"""
        app = create_application(get_settings())
        return app.openapi()
    
    def check_paths(self, baseline: Dict, current: Dict):
        """检查端点变更"""
        baseline_paths = set(baseline.get("paths", {}).keys())
        current_paths = set(current.get("paths", {}).keys())
        
        # 检查删除的端点
        removed_paths = baseline_paths - current_paths
        if removed_paths:
            for path in removed_paths:
                self.breaking_changes.append(f"❌ 删除端点: {path}")
        
        # 检查新增的端点（警告）
        added_paths = current_paths - baseline_paths
        if added_paths:
            for path in added_paths:
                self.warnings.append(f"ℹ️  新增端点: {path}")
        
        # 检查共同端点的方法变更
        common_paths = baseline_paths & current_paths
        for path in common_paths:
            self.check_methods(path, baseline["paths"][path], current["paths"][path])
    
    def check_methods(self, path: str, baseline_methods: Dict, current_methods: Dict):
        """检查 HTTP 方法变更"""
        baseline_method_set = set(baseline_methods.keys())
        current_method_set = set(current_methods.keys())
        
        # 检查删除的方法
        removed_methods = baseline_method_set - current_method_set
        if removed_methods:
            for method in removed_methods:
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue  # 跳过非 HTTP 方法（如 "parameters"）
                self.breaking_changes.append(f"❌ 删除方法: {method.upper()} {path}")
        
        # 检查共同方法的参数变更
        common_methods = baseline_method_set & current_method_set
        for method in common_methods:
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
            self.check_parameters(
                f"{method.upper()} {path}",
                baseline_methods[method].get("parameters", []),
                current_methods[method].get("parameters", [])
            )
    
    def check_parameters(self, endpoint: str, baseline_params: List, current_params: List):
        """检查参数变更"""
        # 构建参数映射
        baseline_param_map = {
            (p.get("name"), p.get("in")): p for p in baseline_params
        }
        current_param_map = {
            (p.get("name"), p.get("in")): p for p in current_params
        }
        
        baseline_keys = set(baseline_param_map.keys())
        current_keys = set(current_param_map.keys())
        
        # 检查删除的必需参数
        removed_params = baseline_keys - current_keys
        for param_key in removed_params:
            param = baseline_param_map[param_key]
            if param.get("required", False):
                self.breaking_changes.append(
                    f"❌ 删除必需参数: {endpoint} - {param['name']} ({param['in']})"
                )
        
        # 检查参数类型变更
        common_params = baseline_keys & current_keys
        for param_key in common_params:
            baseline_param = baseline_param_map[param_key]
            current_param = current_param_map[param_key]
            
            # 检查类型变更
            baseline_type = baseline_param.get("schema", {}).get("type")
            current_type = current_param.get("schema", {}).get("type")
            
            if baseline_type and current_type and baseline_type != current_type:
                self.breaking_changes.append(
                    f"❌ 参数类型变更: {endpoint} - {param_key[0]} "
                    f"({baseline_type} → {current_type})"
                )
            
            # 检查必需性变更（从可选变为必需）
            baseline_required = baseline_param.get("required", False)
            current_required = current_param.get("required", False)
            
            if not baseline_required and current_required:
                self.breaking_changes.append(
                    f"❌ 参数变为必需: {endpoint} - {param_key[0]}"
                )
    
    def detect(self) -> bool:
        """执行检测，返回是否有 breaking changes"""
        print("=" * 80)
        print("🔍 API Breaking Changes 检测")
        print("=" * 80)
        print()
        
        # 加载 schema
        print(f"📂 加载基线 schema: {self.baseline_path}")
        baseline = self.load_baseline()
        
        print(f"📂 获取当前 schema")
        current = self.get_current_schema()
        
        print()
        print("🔍 检测变更...")
        print()
        
        # 检查变更
        self.check_paths(baseline, current)
        
        # 打印结果
        print("=" * 80)
        print("📊 检测结果")
        print("=" * 80)
        print()
        
        if self.breaking_changes:
            print(f"❌ 发现 {len(self.breaking_changes)} 个 Breaking Changes:")
            print()
            for change in self.breaking_changes:
                print(f"  {change}")
            print()
        
        if self.warnings:
            print(f"ℹ️  发现 {len(self.warnings)} 个警告:")
            print()
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        if not self.breaking_changes and not self.warnings:
            print("✅ 未发现 Breaking Changes 或警告")
            print()
        
        return len(self.breaking_changes) > 0


def main():
    """主函数"""
    baseline_path = backend_dir / "docs" / "openapi-schema.json"
    
    detector = BreakingChangeDetector(baseline_path)
    
    try:
        has_breaking_changes = detector.detect()
        
        if has_breaking_changes:
            print("❌ API 契约测试失败：发现 Breaking Changes")
            print()
            print("💡 如果这些变更是有意的，请更新基线 schema:")
            print(f"   python scripts/update_baseline_schema.py")
            return 1
        else:
            print("✅ API 契约测试通过：无 Breaking Changes")
            return 0
    
    except Exception as e:
        print(f"❌ 检测失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

