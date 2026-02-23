import os
from pathlib import Path

def check_file_content():
    env_path = Path("backend/.env").resolve()
    print(f"Checking file: {env_path}")
    
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "OPENAI_API_KEY" in line:
                    # 只显示前 40 个字符，包括 Key 的开头部分
                    print(f"Line {i+1}: {line.strip()[:45]}...")
                    return
        print("❌ OPENAI_API_KEY not found in file!")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    check_file_content()