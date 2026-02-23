"""验证领域痛点是否加载"""
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path.cwd() / "backend"))

from app.services import text_classifier

def verify():
    # Force load
    text_classifier._load_aspect_keywords()
    
    kws = text_classifier._ASPECT_KEYWORDS
    print(f"Total Aspects: {len(kws)}")
    
    # Check specific domain keywords
    # coffee -> quality -> sour shot
    quality = kws.get('quality', [])
    print(f"Quality Keywords Count: {len(quality)}")
    if "sour shot" in quality:
        print("✅ Found 'sour shot' (Coffee Domain)")
    else:
        print("❌ 'sour shot' NOT found")

    # pet -> quality -> upset stomach
    if "upset stomach" in quality:
         print("✅ Found 'upset stomach' (Pet Domain)")
    else:
         print("❌ 'upset stomach' NOT found")
         
    # Check source stats
    print("\\nFirst 10 quality keywords:")
    print(quality[:10])

if __name__ == "__main__":
    verify()
