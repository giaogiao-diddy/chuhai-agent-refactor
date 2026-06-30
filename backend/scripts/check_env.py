# 环境变量检查: cd backend && python scripts/check_env.py

import os
import sys

# 确保 backend/ 在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from config import get_settings

REQUIRED = [
    "DATABASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_BASE_URL",
    "DEEPSEEK_EMBEDDING_MODEL",
]

settings = get_settings()
missing = [name for name in REQUIRED if not getattr(settings, name, None)]

if missing:
    print(f"缺少环境变量: {', '.join(missing)}")
    sys.exit(1)

print("环境变量检查通过")
