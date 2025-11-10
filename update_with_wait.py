"""
Обновление таблицы с ожиданием снятия rate limit.
"""

import asyncio
import time
import os
import sys

# Change to script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print("⏳ Ожидание снятия rate limit API Wildberries...")
print("   Rate limit обычно снимается через 1-2 минуты")
print()

# Обратный отсчёт
wait_seconds = 120  # 2 минуты
for remaining in range(wait_seconds, 0, -10):
    mins = remaining // 60
    secs = remaining % 60
    print(f"   Осталось: {mins}:{secs:02d}    ", end='\r')
    time.sleep(10)

print("\n\n✅ Ожидание завершено! Запуск обновления таблицы...")
print()

# Запустить основной скрипт
import subprocess
result = subprocess.run(
    [sys.executable, "update_table_fixed.py"],
    cwd=script_dir
)

sys.exit(result.returncode)
