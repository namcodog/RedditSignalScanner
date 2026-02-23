#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/hujia/Desktop/RedditSignalScanner/backend')

print('Test 1: Importing app.core.config')
from app.core.config import get_settings

print('Test 2: get_settings() works')
settings = get_settings()

print(f'Test 3: Redis URL = {settings.redis_url[:20] if settings.redis_url else "None"}...')
print('✅ All imports successful')

