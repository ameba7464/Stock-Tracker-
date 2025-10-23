#!/usr/bin/env python3
"""Проверка конфигурации Google Sheets ID."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from stock_tracker.utils.config import get_config
    config = get_config()
    
    print("🔧 Проверка конфигурации:")
    print(f"Google Sheet ID: {getattr(config, 'google_sheet_id', 'NOT_FOUND')}")
    print(f"Service Account Path: {getattr(config, 'google_service_account_key_path', 'NOT_FOUND')}")
    print(f"WB API Key: {'Настроен' if getattr(config, 'wildberries_api_key', None) else 'НЕ НАСТРОЕН'}")
    
    # Проверяем файл service account
    service_path = getattr(config, 'google_service_account_key_path', './config/service-account.json')
    if os.path.exists(service_path):
        print(f"Service Account файл: ✅ Найден")
    else:
        print(f"Service Account файл: ❌ НЕ найден ({service_path})")
    
except Exception as e:
    print(f"❌ Ошибка конфигурации: {e}")