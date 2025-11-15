#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки настройки GitHub Actions.
Проверяет все необходимые переменные окружения и доступы.
"""

import os
import sys
import json


def check_env_var(name, description, is_required=True):
    """Проверить переменную окружения."""
    value = os.getenv(name)
    
    if value:
        # Маскируем чувствительные данные
        if any(keyword in name.lower() for keyword in ['key', 'token', 'secret', 'password']):
            masked = value[:10] + '...' + value[-10:] if len(value) > 20 else '***'
            print(f"  ✅ {name}: {masked}")
        else:
            print(f"  ✅ {name}: {value}")
        return True
    else:
        if is_required:
            print(f"  ❌ {name}: NOT SET (Required)")
            return False
        else:
            print(f"  ⚠️  {name}: NOT SET (Optional)")
            return True


def check_service_account_json():
    """Проверить Service Account JSON."""
    json_str = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    
    if not json_str:
        path = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_PATH', './config/service-account.json')
        if os.path.exists(path):
            print(f"  ✅ Файл service account найден: {path}")
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    print(f"     Email: {data.get('client_email', 'N/A')}")
                    print(f"     Project: {data.get('project_id', 'N/A')}")
                return True
            except Exception as e:
                print(f"  ❌ Ошибка чтения файла: {e}")
                return False
        else:
            print(f"  ❌ Файл service account не найден и переменная не установлена")
            return False
    else:
        try:
            data = json.loads(json_str)
            print(f"  ✅ GOOGLE_SERVICE_ACCOUNT установлен (JSON валиден)")
            print(f"     Email: {data.get('client_email', 'N/A')}")
            print(f"     Project: {data.get('project_id', 'N/A')}")
            return True
        except Exception as e:
            print(f"  ❌ GOOGLE_SERVICE_ACCOUNT: невалидный JSON: {e}")
            return False


def main():
    """Основная функция проверки."""
    print("🔍 Проверка конфигурации для GitHub Actions\n")
    
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    if is_github_actions:
        print("🤖 Обнаружен запуск в GitHub Actions")
        print(f"   Workflow: {os.getenv('GITHUB_WORKFLOW', 'N/A')}")
        print(f"   Runner: {os.getenv('RUNNER_OS', 'N/A')}")
        print()
    else:
        print("💻 Локальный запуск (не GitHub Actions)\n")
    
    all_good = True
    
    # Проверяем критические переменные
    print("📋 Критические переменные:")
    all_good &= check_env_var('WILDBERRIES_API_KEY', 'Wildberries API токен', is_required=True)
    all_good &= check_env_var('GOOGLE_SHEET_ID', 'ID Google Sheets документа', is_required=True)
    
    print("\n🔐 Google Service Account:")
    all_good &= check_service_account_json()
    
    # Проверяем опциональные переменные
    print("\n⚙️  Опциональные переменные:")
    check_env_var('GOOGLE_SHEET_NAME', 'Название листа', is_required=False)
    check_env_var('LOG_LEVEL', 'Уровень логирования', is_required=False)
    check_env_var('TIMEZONE', 'Часовой пояс', is_required=False)
    
    # Итоговый результат
    print("\n" + "="*60)
    if all_good:
        print("✅ Все критические настройки в порядке!")
        print("   GitHub Actions должен работать корректно.")
        return 0
    else:
        print("❌ Обнаружены проблемы с конфигурацией!")
        print("   Исправьте ошибки перед запуском в GitHub Actions.")
        print("\n📖 Инструкция: GITHUB_ACTIONS_SETUP.md")
        return 1


if __name__ == '__main__':
    sys.exit(main())
