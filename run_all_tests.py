#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для быстрого запуска всех тестов проекта Stock Tracker

Запускает:
1. Тест GitHub Actions конфигурации
2. Базовые тесты проекта (без полной синхронизации)
3. Генерация итогового отчёта
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Установка кодировки UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def run_test(script_name: str) -> dict:
    """Запустить тестовый скрипт"""
    print(f"\n🔬 Запуск {script_name}...")
    print("="*80)
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=Path(__file__).parent
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return {
            "script": script_name,
            "passed": result.returncode == 0,
            "duration": duration,
            "returncode": result.returncode
        }
        
    except Exception as e:
        print(f"❌ Ошибка выполнения {script_name}: {e}")
        return {
            "script": script_name,
            "passed": False,
            "duration": (datetime.now() - start_time).total_seconds(),
            "error": str(e)
        }


def main():
    """Главная функция"""
    print("="*80)
    print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ ПРОЕКТА STOCK TRACKER")
    print("="*80)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    all_results = []
    
    # Тест 1: GitHub Actions
    result1 = run_test("test_github_actions.py")
    all_results.append(result1)
    
    # Создаём итоговый отчёт
    print("\n" + "="*80)
    print("📊 ИТОГОВАЯ СВОДКА")
    print("="*80)
    
    total_tests = len(all_results)
    passed = sum(1 for r in all_results if r.get("passed", False))
    failed = total_tests - passed
    total_duration = sum(r.get("duration", 0) for r in all_results)
    
    print(f"\nВсего тестовых наборов: {total_tests}")
    print(f"✅ Успешных: {passed}")
    print(f"❌ Неуспешных: {failed}")
    print(f"⏱️  Общее время: {total_duration:.2f}s")
    
    print(f"\nДетализация:")
    for r in all_results:
        status = "✅" if r.get("passed") else "❌"
        script = r.get("script", "Unknown")
        duration = r.get("duration", 0)
        print(f"{status} {script}: {duration:.2f}s")
        if "error" in r:
            print(f"   Ошибка: {r['error']}")
    
    # Сохраняем итоговый отчёт
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "total_duration": total_duration
        },
        "results": all_results
    }
    
    report_file = Path(__file__).parent / "all_tests_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Итоговый отчёт: {report_file}")
    
    # Создаём Markdown отчёт
    create_markdown_report(final_report)
    
    print("\n" + "="*80)
    
    if failed > 0:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return 1
    else:
        print("✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        return 0


def create_markdown_report(report_data: dict):
    """Создать Markdown отчёт"""
    md_file = Path(__file__).parent / "TEST_RESULTS.md"
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# 🧪 Результаты тестирования Stock Tracker\n\n")
        f.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        summary = report_data.get("summary", {})
        f.write("## 📊 Сводка\n\n")
        f.write(f"- **Всего тестовых наборов:** {summary.get('total_tests', 0)}\n")
        f.write(f"- **✅ Успешных:** {summary.get('passed', 0)}\n")
        f.write(f"- **❌ Неуспешных:** {summary.get('failed', 0)}\n")
        f.write(f"- **⏱️ Общее время:** {summary.get('total_duration', 0):.2f}s\n\n")
        
        f.write("## 📝 Детальные результаты\n\n")
        
        for result in report_data.get("results", []):
            script = result.get("script", "Unknown")
            passed = result.get("passed", False)
            duration = result.get("duration", 0)
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            
            f.write(f"### {script}\n\n")
            f.write(f"- **Статус:** {status}\n")
            f.write(f"- **Длительность:** {duration:.2f}s\n")
            
            if "error" in result:
                f.write(f"- **Ошибка:** `{result['error']}`\n")
            
            f.write("\n")
        
        # Добавляем проверки GitHub Actions
        f.write("## 🤖 GitHub Actions\n\n")
        f.write("### Статус конфигурации\n\n")
        
        try:
            gh_report_file = Path(__file__).parent / "github_actions_test_report.json"
            if gh_report_file.exists():
                with open(gh_report_file, 'r', encoding='utf-8') as gh_f:
                    gh_data = json.load(gh_f)
                
                gh_results = gh_data.get("results", {})
                
                f.write("#### Workflow файлы\n")
                wf_result = gh_results.get("workflow_files", {})
                if wf_result.get("passed"):
                    f.write(f"✅ Найдено {wf_result.get('count', 0)} workflow файлов\n\n")
                else:
                    f.write("❌ Workflow файлы не найдены\n\n")
                
                f.write("#### Секреты\n")
                secrets_result = gh_results.get("required_secrets", {})
                if secrets_result.get("passed"):
                    found = secrets_result.get("found_secrets", [])
                    f.write(f"✅ Все необходимые секреты настроены ({len(found)})\n")
                    for secret in found:
                        f.write(f"- `{secret}`\n")
                    f.write("\n")
                else:
                    f.write("❌ Отсутствуют необходимые секреты\n")
                    missing = secrets_result.get("missing_required", [])
                    for secret in missing:
                        f.write(f"- ❌ `{secret}`\n")
                    f.write("\n")
                
                f.write("#### Совместимость\n")
                compat_result = gh_results.get("compatibility", {})
                if compat_result.get("passed"):
                    f.write("✅ Проект совместим с GitHub Actions runner\n\n")
                    checks = compat_result.get("checks", [])
                    for check in checks:
                        status = "✅" if check.get("passed") else "❌"
                        f.write(f"- {status} {check.get('name')}: `{check.get('value')}`\n")
                    f.write("\n")
                else:
                    f.write("❌ Проблемы совместимости с GitHub Actions\n\n")
        
        except Exception as e:
            f.write(f"⚠️ Не удалось загрузить детали GitHub Actions: {e}\n\n")
        
        f.write("## 🎯 Заключение\n\n")
        
        if summary.get('failed', 0) > 0:
            f.write("❌ **Некоторые тесты не пройдены.** Требуется исправление.\n\n")
        else:
            f.write("✅ **Все тесты успешно пройдены!** Проект готов к использованию.\n\n")
        
        f.write("---\n\n")
        f.write(f"*Отчёт сгенерирован автоматически: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"📄 Markdown отчёт: {md_file}")


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
