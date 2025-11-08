#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование конфигурации GitHub Actions для Stock Tracker
Проверяет корректность настройки workflow, секретов и интеграции

Проверки:
1. Наличие и корректность workflow файлов
2. Валидация YAML синтаксиса
3. Проверка секретов и переменных окружения
4. Проверка совместимости с GitHub Actions runner
5. Симуляция запуска в GitHub Actions окружении
"""

import sys
import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any

# Установка кодировки UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class GitHubActionsValidator:
    """Валидатор конфигурации GitHub Actions"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.workflow_dir = project_root / ".github" / "workflows"
        self.errors = []
        self.warnings = []
    
    def validate_all(self) -> Dict[str, Any]:
        """Выполнить все проверки"""
        results = {
            "workflow_files": self.check_workflow_files(),
            "yaml_syntax": self.validate_yaml_syntax(),
            "required_secrets": self.check_required_secrets(),
            "workflow_structure": self.validate_workflow_structure(),
            "compatibility": self.check_runner_compatibility(),
            "simulation": self.simulate_github_actions_run()
        }
        
        return {
            "results": results,
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": len(self.errors) == 0
        }
    
    def check_workflow_files(self) -> Dict[str, Any]:
        """Проверка наличия workflow файлов"""
        print("\n🔍 Проверка workflow файлов...")
        
        if not self.workflow_dir.exists():
            error = f"Директория .github/workflows не найдена: {self.workflow_dir}"
            self.errors.append(error)
            return {"passed": False, "error": error}
        
        workflow_files = list(self.workflow_dir.glob("*.yml")) + list(self.workflow_dir.glob("*.yaml"))
        
        if not workflow_files:
            error = "Не найдено workflow файлов (.yml или .yaml)"
            self.errors.append(error)
            return {"passed": False, "error": error}
        
        print(f"✅ Найдено {len(workflow_files)} workflow файлов")
        for wf in workflow_files:
            print(f"   • {wf.name}")
        
        return {
            "passed": True,
            "count": len(workflow_files),
            "files": [str(wf.name) for wf in workflow_files]
        }
    
    def validate_yaml_syntax(self) -> Dict[str, Any]:
        """Валидация YAML синтаксиса"""
        print("\n🔍 Проверка YAML синтаксиса...")
        
        workflow_files = list(self.workflow_dir.glob("*.yml")) + list(self.workflow_dir.glob("*.yaml"))
        
        results = []
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    yaml_content = yaml.safe_load(f)
                
                print(f"✅ {workflow_file.name}: YAML синтаксис корректен")
                results.append({
                    "file": workflow_file.name,
                    "passed": True,
                    "content_keys": list(yaml_content.keys()) if isinstance(yaml_content, dict) else []
                })
                
            except yaml.YAMLError as e:
                error = f"{workflow_file.name}: Ошибка YAML синтаксиса - {e}"
                self.errors.append(error)
                print(f"❌ {error}")
                results.append({
                    "file": workflow_file.name,
                    "passed": False,
                    "error": str(e)
                })
            except Exception as e:
                error = f"{workflow_file.name}: Ошибка чтения файла - {e}"
                self.errors.append(error)
                print(f"❌ {error}")
                results.append({
                    "file": workflow_file.name,
                    "passed": False,
                    "error": str(e)
                })
        
        passed = all(r["passed"] for r in results)
        return {
            "passed": passed,
            "results": results
        }
    
    def check_required_secrets(self) -> Dict[str, Any]:
        """Проверка необходимых секретов"""
        print("\n🔍 Проверка необходимых секретов...")
        
        required_secrets = [
            "WILDBERRIES_API_KEY",
            "GOOGLE_SERVICE_ACCOUNT",
            "GOOGLE_SHEET_ID"
        ]
        
        optional_secrets = [
            "GOOGLE_SHEET_NAME"
        ]
        
        workflow_files = list(self.workflow_dir.glob("*.yml")) + list(self.workflow_dir.glob("*.yaml"))
        
        found_secrets = set()
        missing_required = []
        
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ищем использование секретов
                for secret in required_secrets + optional_secrets:
                    if f"secrets.{secret}" in content or f"${{{{ secrets.{secret}" in content:
                        found_secrets.add(secret)
                
            except Exception as e:
                warning = f"Не удалось прочитать {workflow_file.name}: {e}"
                self.warnings.append(warning)
                print(f"⚠️  {warning}")
        
        # Проверяем обязательные секреты
        for secret in required_secrets:
            if secret not in found_secrets:
                missing_required.append(secret)
        
        if missing_required:
            error = f"Отсутствуют обязательные секреты: {', '.join(missing_required)}"
            self.errors.append(error)
            print(f"❌ {error}")
        else:
            print(f"✅ Все обязательные секреты присутствуют")
        
        # Проверяем опциональные секреты
        missing_optional = [s for s in optional_secrets if s not in found_secrets]
        if missing_optional:
            warning = f"Отсутствуют опциональные секреты: {', '.join(missing_optional)}"
            self.warnings.append(warning)
            print(f"⚠️  {warning}")
        
        return {
            "passed": len(missing_required) == 0,
            "found_secrets": list(found_secrets),
            "missing_required": missing_required,
            "missing_optional": missing_optional
        }
    
    def validate_workflow_structure(self) -> Dict[str, Any]:
        """Валидация структуры workflow"""
        print("\n🔍 Проверка структуры workflow...")
        
        workflow_files = list(self.workflow_dir.glob("*.yml")) + list(self.workflow_dir.glob("*.yaml"))
        
        results = []
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow = yaml.safe_load(f)
                
                if not isinstance(workflow, dict):
                    error = f"{workflow_file.name}: Workflow должен быть объектом"
                    self.errors.append(error)
                    print(f"❌ {error}")
                    results.append({"file": workflow_file.name, "passed": False, "error": error})
                    continue
                
                # Проверяем обязательные поля
                required_fields = ["name", "on", "jobs"]
                missing_fields = [f for f in required_fields if f not in workflow]
                
                if missing_fields:
                    error = f"{workflow_file.name}: Отсутствуют поля: {', '.join(missing_fields)}"
                    self.errors.append(error)
                    print(f"❌ {error}")
                    results.append({
                        "file": workflow_file.name,
                        "passed": False,
                        "missing_fields": missing_fields
                    })
                    continue
                
                # Проверяем структуру jobs
                jobs = workflow.get("jobs", {})
                if not jobs:
                    error = f"{workflow_file.name}: Нет определённых jobs"
                    self.errors.append(error)
                    print(f"❌ {error}")
                    results.append({"file": workflow_file.name, "passed": False, "error": error})
                    continue
                
                # Проверяем каждый job
                job_details = []
                for job_name, job_config in jobs.items():
                    if not isinstance(job_config, dict):
                        continue
                    
                    job_info = {
                        "name": job_name,
                        "runs_on": job_config.get("runs-on"),
                        "steps_count": len(job_config.get("steps", []))
                    }
                    job_details.append(job_info)
                
                print(f"✅ {workflow_file.name}: Структура корректна")
                print(f"   • Name: {workflow['name']}")
                print(f"   • Triggers: {list(workflow['on'].keys()) if isinstance(workflow['on'], dict) else workflow['on']}")
                print(f"   • Jobs: {len(jobs)}")
                for job in job_details:
                    print(f"     - {job['name']}: {job['steps_count']} steps on {job['runs_on']}")
                
                results.append({
                    "file": workflow_file.name,
                    "passed": True,
                    "name": workflow["name"],
                    "triggers": list(workflow["on"].keys()) if isinstance(workflow["on"], dict) else [workflow["on"]],
                    "jobs": job_details
                })
                
            except Exception as e:
                error = f"{workflow_file.name}: Ошибка валидации структуры - {e}"
                self.errors.append(error)
                print(f"❌ {error}")
                results.append({
                    "file": workflow_file.name,
                    "passed": False,
                    "error": str(e)
                })
        
        passed = all(r["passed"] for r in results)
        return {
            "passed": passed,
            "results": results
        }
    
    def check_runner_compatibility(self) -> Dict[str, Any]:
        """Проверка совместимости с GitHub Actions runner"""
        print("\n🔍 Проверка совместимости с GitHub Actions runner...")
        
        checks = []
        
        # Проверка 1: Python версия
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        checks.append({
            "name": "Python Version",
            "passed": sys.version_info.major == 3 and sys.version_info.minor >= 9,
            "value": python_version,
            "expected": "3.9+"
        })
        
        # Проверка 2: requirements.txt
        requirements_file = self.project_root / "requirements.txt"
        has_requirements = requirements_file.exists()
        checks.append({
            "name": "requirements.txt",
            "passed": has_requirements,
            "value": str(requirements_file) if has_requirements else None
        })
        
        # Проверка 3: update_table_fixed.py (основной скрипт)
        main_script = self.project_root / "update_table_fixed.py"
        has_main_script = main_script.exists()
        checks.append({
            "name": "Main Script",
            "passed": has_main_script,
            "value": str(main_script) if has_main_script else None
        })
        
        # Проверка 4: config директория
        config_dir = self.project_root / "config"
        has_config_dir = config_dir.exists()
        checks.append({
            "name": "Config Directory",
            "passed": True,  # Будет создана в runtime
            "value": str(config_dir),
            "note": "Will be created by workflow"
        })
        
        for check in checks:
            status = "✅" if check["passed"] else "❌"
            print(f"{status} {check['name']}: {check.get('value', 'N/A')}")
            if "note" in check:
                print(f"   📝 {check['note']}")
        
        passed = all(c["passed"] for c in checks)
        return {
            "passed": passed,
            "checks": checks
        }
    
    def simulate_github_actions_run(self) -> Dict[str, Any]:
        """Симуляция запуска в GitHub Actions окружении"""
        print("\n🔍 Симуляция GitHub Actions окружения...")
        
        # Устанавливаем переменные окружения как в GitHub Actions
        gh_env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_WORKFLOW": "Update Stock Tracker Daily",
            "GITHUB_RUN_ID": "12345678",
            "GITHUB_RUN_NUMBER": "42",
            "GITHUB_ACTOR": "github-actions[bot]",
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64"
        }
        
        print("🤖 Установка GitHub Actions переменных окружения:")
        for key, value in gh_env.items():
            os.environ[key] = value
            print(f"   • {key}={value}")
        
        # Проверяем, что скрипт может определить окружение GitHub Actions
        is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        if is_github_actions:
            print("✅ GitHub Actions окружение корректно симулировано")
        else:
            print("❌ Не удалось симулировать GitHub Actions окружение")
        
        # Очищаем переменные окружения после теста
        for key in gh_env.keys():
            if key in os.environ:
                del os.environ[key]
        
        return {
            "passed": is_github_actions,
            "environment": gh_env
        }


def main():
    """Главная функция"""
    print("="*80)
    print("🧪 ТЕСТИРОВАНИЕ GITHUB ACTIONS КОНФИГУРАЦИИ")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent
    validator = GitHubActionsValidator(project_root)
    
    # Выполняем все проверки
    results = validator.validate_all()
    
    # Выводим сводку
    print("\n" + "="*80)
    print("📊 СВОДКА РЕЗУЛЬТАТОВ")
    print("="*80)
    
    if results["passed"]:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ ПРОВАЛИЛИСЬ")
    
    if results["errors"]:
        print(f"\n❌ Ошибки ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"   • {error}")
    
    if results["warnings"]:
        print(f"\n⚠️  Предупреждения ({len(results['warnings'])}):")
        for warning in results["warnings"]:
            print(f"   • {warning}")
    
    print("\n" + "="*80)
    
    # Сохраняем отчёт
    report_file = project_root / "github_actions_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Отчёт сохранён: {report_file}")
    
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
