# 🛠️ Scripts Directory

Автоматизационные скрипты для Stock Tracker мониторинга и обслуживания.

## 📋 Обзор

Эта директория содержит 20+ скриптов для полной автоматизации работы системы мониторинга.

### 🎯 Quick Start

```powershell
# Windows - System Overview
.\overview.ps1

# Check system status
.\scripts\monitoring_status.ps1

# Quick update monitoring services
.\scripts\quick_update.ps1
```

---

## 📊 Мониторинг

### `monitoring_status.ps1` / `monitoring_status.sh`
**Быстрая проверка состояния системы**

- ✅ Docker services status
- ✅ Health checks (Prometheus, Grafana, Alertmanager)
- ✅ Prometheus targets (6/8 UP)
- ✅ Active alerts count
- ✅ Docker volumes disk usage
- ✅ Quick links

**Использование:**
```powershell
# Windows
.\scripts\monitoring_status.ps1

# Linux/Mac
./scripts/monitoring_status.sh
```

### `check_monitoring.ps1` / `check_monitoring.sh`
**Подробная проверка конфигурации**

- Validates Prometheus config
- Checks Alertmanager rules
- Verifies Docker Compose syntax
- Tests all endpoints

---

## 🔧 Обслуживание

### `maintenance.ps1` / `maintenance.sh`
**Полное автоматическое обслуживание**

**Что делает:**
1. ✅ Pull latest Docker images
2. ✅ Clean up unused resources
3. ✅ Backup configurations
4. ✅ Restart unhealthy services
5. ✅ Check disk usage
6. ✅ Verify Prometheus targets

**Использование:**
```powershell
.\scripts\maintenance.ps1
```

**Автоматический запуск:** Ежедневно в 3:00 AM (через Scheduled Tasks)

### `quick_update.ps1`
**Быстрое обновление мониторинга**

- Pull latest images для monitoring сервисов
- Restart с force-recreate
- Health checks после обновления

**Использование:**
```powershell
.\scripts\quick_update.ps1
```

---

## 🚨 Аварийное восстановление

### `emergency_recovery.ps1` / `emergency_recovery.sh`
**Восстановление при сбоях**

**Порядок действий:**
1. Stop all services
2. Clean up problematic containers
3. Start databases first (PostgreSQL, Redis)
4. Start API and workers
5. Start monitoring stack
6. Health check all services

**Использование:**
```powershell
.\scripts\emergency_recovery.ps1
```

**Когда использовать:**
- Система не отвечает
- Множественные сбои контейнеров
- После критических ошибок
- Corrupted state

---

## 📦 Backup & Cleanup

### `backup_configs.ps1`
**Резервное копирование конфигураций**

Сохраняет:
- `docker-compose.yml`
- `monitoring/*` (все конфиги)
- `.env.example`

**Расположение:** `backups/YYYYMMDD_HHMMSS/`

**Автоматический запуск:** Ежедневно в 1:00 AM

### `docker_cleanup.ps1`
**Очистка Docker ресурсов**

Удаляет:
- Unused containers
- Unused images
- Unused volumes
- Unused networks

**Автоматический запуск:** Еженедельно (воскресенье, 2:00 AM)

---

## ⚙️ Автоматизация

### `setup_automation.ps1` / `setup_automation.sh`
**Настройка автоматических задач**

**Windows:** Создает Scheduled Tasks
**Linux:** Создает cron jobs

**Задачи:**
| Задача | Расписание | Описание |
|--------|------------|----------|
| Daily Maintenance | 3:00 AM | Полное обслуживание |
| Health Check | Каждые 6 часов | Проверка системы |
| Docker Cleanup | Воскресенье 2:00 AM | Очистка ресурсов |
| Config Backup | 1:00 AM | Backup конфигов |

**Использование:**
```powershell
# Windows
.\scripts\setup_automation.ps1

# Linux/Mac
./scripts/setup_automation.sh
```

**Проверка задач:**
```powershell
# Windows
Get-ScheduledTask | Where-Object { $_.TaskName -like "StockTracker_*" }

# Linux/Mac
crontab -l
```

---

## 🔐 GitHub Integration

### `setup_github_secrets.ps1` / `setup_github_secrets.sh`
**Автоматическая настройка GitHub Secrets**

**Устанавливает:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALERT_CHAT_ID`
- `GRAFANA_PASSWORD`
- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`

**Требования:** GitHub CLI (`gh`)

**Использование:**
```powershell
.\scripts\setup_github_secrets.ps1
```

**Проверка:**
```bash
gh secret list
```

---

## 👨‍💼 Admin Tools

### `create_admin.py`
**Создание admin пользователя**

```bash
python scripts/create_admin.py
```

### `test_admin_api.ps1`
**Тестирование admin API endpoints**

```powershell
.\scripts\test_admin_api.ps1
```

### `configure_postgres_remote.sh`
**Настройка remote PostgreSQL**

```bash
./scripts/configure_postgres_remote.sh
```

---

## 📊 System Overview

### `../overview.ps1`
**Центр управления системой**

**Показывает:**
- 🌐 Quick links ко всем dashboards
- 🛠️ Доступные actions (6 команд)
- 📚 Документация (5 гайдов)
- 🚀 CI/CD pipelines info
- 📊 Текущий статус системы
  - Running containers
  - Prometheus targets
  - Active alerts
  - Disk usage
  - Scheduled tasks

**Использование:**
```powershell
.\overview.ps1
```

---

## 📝 Рекомендации

### Ежедневное использование

```powershell
# Утром - проверка статуса
.\scripts\monitoring_status.ps1

# При проблемах - recovery
.\scripts\emergency_recovery.ps1

# Обновление системы
.\scripts\quick_update.ps1
```

### Еженедельное обслуживание

```powershell
# Вручную запустить maintenance
.\scripts\maintenance.ps1

# Проверить backups
Get-ChildItem backups\ | Sort-Object LastWriteTime -Descending
```

### Настройка новой системы

```powershell
# 1. Setup automation
.\scripts\setup_automation.ps1

# 2. Setup GitHub Secrets
.\scripts\setup_github_secrets.ps1

# 3. Проверка
.\overview.ps1
```

---

## 🔍 Troubleshooting

### Скрипт не запускается

**Проблема:** Execution Policy

**Решение:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Health check fails

**Проблема:** Сервисы не отвечают

**Решение:**
```powershell
.\scripts\emergency_recovery.ps1
```

### Scheduled Tasks не работают

**Проблема:** Задачи не выполняются

**Решение:**
```powershell
# Проверить статус
Get-ScheduledTaskInfo -TaskName "StockTracker_DailyMaintenance"

# Запустить вручную
Start-ScheduledTask -TaskName "StockTracker_DailyMaintenance"

# Переустановить
.\scripts\setup_automation.ps1
```

---

## 📊 Логи

Все автоматические задачи пишут логи:

**Расположение:** `logs/`

**Файлы:**
- `maintenance.log` - Daily maintenance
- `health_check.log` - Health checks
- `docker_cleanup.log` - Docker cleanup
- `disk_check.log` - Disk usage checks

**Просмотр:**
```powershell
# Последние 50 строк
Get-Content logs\maintenance.log -Tail 50

# Следить в реальном времени
Get-Content logs\health_check.log -Wait
```

---

## 🔗 Связь с другими компонентами

```
scripts/
├── monitoring_status.ps1 → Prometheus, Grafana, Alertmanager
├── maintenance.ps1 → Docker, backups/, logs/
├── quick_update.ps1 → docker-compose.yml
├── emergency_recovery.ps1 → Все сервисы
├── setup_automation.ps1 → Windows Task Scheduler
└── setup_github_secrets.ps1 → GitHub Secrets
```

---

## 📚 Дополнительные ресурсы

- [Monitoring Guide](../docs/MONITORING_GUIDE.md)
- [CI/CD Deployment Guide](../docs/CI_CD_DEPLOYMENT_GUIDE.md)
- [Docker Secrets Setup](../monitoring/DOCKER_SECRETS_SETUP.md)
- [Automation Summary](../AUTOMATION_SUMMARY.md)

---

**Создано:** 11 декабря 2025 г.  
**Всего скриптов:** 20+  
**Поддерживаемые ОС:** Windows (PowerShell), Linux/Mac (Bash)
