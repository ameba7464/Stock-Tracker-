"""
Скрипт запуска FastAPI сервера с правильным PYTHONPATH
"""
import sys
import os
from pathlib import Path

# Добавляем src в путь поиска модулей
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Загружаем .env файл
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️ Warning: {env_file} not found")

print(f"📂 Project root: {project_root}")
print(f"📦 Python path: {src_path}")

# Теперь можем импортировать stock_tracker
try:
    import stock_tracker
    print(f"✅ stock_tracker module found: version {stock_tracker.__version__}")
except ImportError as e:
    print(f"❌ Error importing stock_tracker: {e}")
    sys.exit(1)

# Запускаем uvicorn
import uvicorn

if __name__ == "__main__":
    print("\n🚀 Starting Stock Tracker API...")
    print("📝 API docs: http://localhost:8000/docs")
    print("🏥 Health check: http://localhost:8000/api/v1/health/\n")
    
    uvicorn.run(
        "stock_tracker.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(src_path)]
    )
