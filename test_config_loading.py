#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест загрузки конфигурации после исправления
"""

import sys
import os

# ИСПРАВЛЕНИЕ: Меняем рабочую директорию на директорию скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, os.path.join(script_dir, 'src'))

print(f"📂 Рабочая директория: {os.getcwd()}")
print(f"📝 .env файл существует: {os.path.exists('.env')}")

from stock_tracker.utils.config import get_config

try:
    config = get_config()
    print("\n✅ Конфигурация загружена успешно!")
    print(f"   Sheet ID: {config.google_sheet_id[:20]}...")
    print(f"   API Key length: {len(config.wildberries_api_key)} символов")
    print(f"   Service Account: {config.google_service_account_key_path}")
    print(f"   File exists: {os.path.exists(config.google_service_account_key_path)}")
except Exception as e:
    print(f"\n❌ Ошибка загрузки конфигурации: {e}")
    sys.exit(1)
