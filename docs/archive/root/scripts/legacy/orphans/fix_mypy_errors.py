#!/usr/bin/env python3
"""
自动修复 MyPy --strict 错误的脚本
"""
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def get_mypy_errors() -> List[Tuple[str, int, str]]:
    """运行 MyPy 并解析错误"""
    result = subprocess.run(
        ["python", "-m", "mypy", "--strict", "app"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    
    errors = []
    for line in result.stdout.split("\n"):
        # 解析格式: app/file.py:123: error: Message [error-code]
        match = re.match(r"^(app/[^:]+):(\d+): error: (.+)$", line)
        if match:
            file_path, line_num, message = match.groups()
            errors.append((file_path, int(line_num), message))
    
    return errors


def remove_unused_ignores(file_path: str, line_nums: List[int]) -> None:
    """移除未使用的 # type: ignore 注释"""
    path = Path("app") / file_path.replace("app/", "")
    if not path.exists():
        return
    
    lines = path.read_text().splitlines()
    modified = False
    
    for line_num in sorted(line_nums, reverse=True):
        idx = line_num - 1
        if idx < len(lines):
            line = lines[idx]
            # 移除 # type: ignore 注释
            new_line = re.sub(r'\s*#\s*type:\s*ignore.*$', '', line)
            if new_line != line:
                lines[idx] = new_line
                modified = True
    
    if modified:
        path.write_text("\n".join(lines) + "\n")
        print(f"✅ 修复 {file_path}: 移除了 {len(line_nums)} 个未使用的 type: ignore")


def remove_redundant_casts(file_path: str, line_nums: List[int]) -> None:
    """移除冗余的类型转换"""
    path = Path("app") / file_path.replace("app/", "")
    if not path.exists():
        return
    
    lines = path.read_text().splitlines()
    modified = False
    
    for line_num in sorted(line_nums, reverse=True):
        idx = line_num - 1
        if idx < len(lines):
            line = lines[idx]
            # 移除 cast(...) 包装
            new_line = re.sub(r'cast\(([^,]+),\s*([^)]+)\)', r'\2', line)
            if new_line != line:
                lines[idx] = new_line
                modified = True
    
    if modified:
        path.write_text("\n".join(lines) + "\n")
        print(f"✅ 修复 {file_path}: 移除了 {len(line_nums)} 个冗余类型转换")


def main():
    """主函数"""
    print("🔍 运行 MyPy --strict 检查...")
    errors = get_mypy_errors()
    
    # 按文件和错误类型分组
    unused_ignores: Dict[str, List[int]] = {}
    redundant_casts: Dict[str, List[int]] = {}
    
    for file_path, line_num, message in errors:
        if "Unused \"type: ignore\" comment" in message:
            if file_path not in unused_ignores:
                unused_ignores[file_path] = []
            unused_ignores[file_path].append(line_num)
        elif "Redundant cast" in message:
            if file_path not in redundant_casts:
                redundant_casts[file_path] = []
            redundant_casts[file_path].append(line_num)
    
    print(f"\n📊 发现错误统计:")
    print(f"  - 未使用的 type: ignore: {sum(len(v) for v in unused_ignores.values())} 个")
    print(f"  - 冗余的类型转换: {sum(len(v) for v in redundant_casts.values())} 个")
    print(f"  - 其他错误: {len(errors) - sum(len(v) for v in unused_ignores.values()) - sum(len(v) for v in redundant_casts.values())} 个")
    
    # 修复未使用的 type: ignore
    print("\n🔧 修复未使用的 type: ignore...")
    for file_path, line_nums in unused_ignores.items():
        remove_unused_ignores(file_path, line_nums)
    
    # 修复冗余的类型转换
    print("\n🔧 修复冗余的类型转换...")
    for file_path, line_nums in redundant_casts.items():
        remove_redundant_casts(file_path, line_nums)
    
    print("\n✅ 自动修复完成！")
    print("\n🔍 重新运行 MyPy 检查剩余错误...")
    subprocess.run(["python", "-m", "mypy", "--strict", "app"], cwd=Path(__file__).parent.parent)


if __name__ == "__main__":
    main()

