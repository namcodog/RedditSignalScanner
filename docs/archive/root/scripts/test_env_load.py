import os
from pathlib import Path
from dotenv import load_dotenv

def run_test():
    print("--- Environment Diagnosis ---")
    root_env = Path(".env").resolve()
    backend_env = Path("backend/.env").resolve()
    
    print(f"Root .env path: {root_env} (Exists: {root_env.exists()})")
    print(f"Backend .env path: {backend_env} (Exists: {backend_env.exists()})")
    
    # Reset env for clean test
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    if "DATABASE_URL" in os.environ:
        print("Note: DATABASE_URL is currently set in shell.")

    # Simulate logic
    print("Attempting load...")
    load_dotenv(dotenv_path=backend_env, override=True)  # 强制加载测试
    
    key = os.getenv("OPENAI_API_KEY")
    if key:
        print(f"✅ Key loaded successfully: {key[:8]}...")
    else:
        print("❌ Key failed to load.")

if __name__ == "__main__":
    run_test()