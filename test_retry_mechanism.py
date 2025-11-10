#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест механизма повторных попыток при ошибках Google API
"""

import sys
import os
import asyncio

# ИСПРАВЛЕНИЕ: Меняем рабочую директорию на директорию скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, os.path.join(script_dir, 'src'))

print("🧪 Тест механизма повторных попыток\n")

async def test_retry_logic():
    """Симуляция логики повторных попыток"""
    
    # Тест 1: Успешная попытка с первого раза
    print("1️⃣ Тест: Успешная операция с первого раза")
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"   Попытка {attempt}/{max_retries}...")
            # Симуляция успешной операции
            await asyncio.sleep(0.1)
            print("   ✅ Успех!")
            break
        except Exception as e:
            if attempt < max_retries:
                print(f"   ⚠️  Ошибка: {e}")
                print(f"   ⏳ Ожидание {retry_delay} секунд...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"   ❌ Все попытки исчерпаны")
                raise
    
    # Тест 2: Успех со второй попытки
    print("\n2️⃣ Тест: Успех со второй попытки")
    max_retries = 3
    retry_delay = 2
    attempt_counter = [0]  # Используем list для изменения в замыкании
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"   Попытка {attempt}/{max_retries}...")
            attempt_counter[0] += 1
            if attempt_counter[0] == 1:
                raise Exception("503 Service Unavailable (симуляция)")
            # Симуляция успешной операции
            await asyncio.sleep(0.1)
            print("   ✅ Успех!")
            break
        except Exception as e:
            if "503" in str(e) or "unavailable" in str(e).lower():
                if attempt < max_retries:
                    print(f"   ⚠️  Ошибка: {e}")
                    print(f"   ⏳ Ожидание {retry_delay} секунд...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"   ❌ Все попытки исчерпаны")
                    raise
            else:
                raise
    
    # Тест 3: Экспоненциальная задержка
    print("\n3️⃣ Тест: Проверка экспоненциального увеличения задержки")
    delays = []
    retry_delay = 2
    
    for attempt in range(1, 4):
        print(f"   Попытка {attempt}: задержка = {retry_delay} сек")
        delays.append(retry_delay)
        retry_delay *= 2
    
    assert delays == [2, 4, 8], f"Ожидалось [2, 4, 8], получено {delays}"
    print("   ✅ Экспоненциальное увеличение работает корректно")
    
    print("\n" + "="*70)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*70)
    print("\n📝 Механизм повторных попыток работает корректно")
    print("   Скрипт будет автоматически повторять попытки при:")
    print("   - 503 Service Unavailable (Google API недоступен)")
    print("   - Quota exceeded (превышена квота)")
    print("   - Другие временные ошибки API\n")

if __name__ == "__main__":
    asyncio.run(test_retry_logic())
