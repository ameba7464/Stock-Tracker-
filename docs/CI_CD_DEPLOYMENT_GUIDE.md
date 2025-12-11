# 🚀 CI/CD Deployment Guide

Автоматический деплой системы мониторинга в production через GitHub Actions.

## 📋 Что настроено

### GitHub Actions Workflows

1. **deploy-monitoring.yml** - Автоматический деплой
   - Триггер: push в main (изменения в `monitoring/`, `docker-compose.yml`)
   - Валидация конфигов (Prometheus, Alertmanager)
   - Деплой на production сервер через SSH
   - Health checks после деплоя
   - Telegram уведомления о статусе

2. **monitoring-health-check.yml** - Периодические проверки
   - Запуск: каждые 6 часов
   - Проверка всех сервисов мониторинга
   - Уведомления при сбоях

## 🔐 Настройка GitHub Secrets

### Автоматическая настройка (рекомендуется)

**Windows (PowerShell):**
```powershell
.\scripts\setup_github_secrets.ps1
```

**Linux/Mac (Bash):**
```bash
chmod +x scripts/setup_github_secrets.sh
./scripts/setup_github_secrets.sh
```

Скрипт автоматически:
- Проверит установку GitHub CLI
- Авторизуется (если нужно)
- Установит все необходимые secrets
- Покажет статус установки

### Ручная настройка

1. Перейдите в Settings → Secrets and variables → Actions
2. Нажмите "New repository secret"
3. Добавьте следующие secrets:

#### Мониторинг
| Secret Name | Value | Description |
|------------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | `8558236991:AAHFu2k...` | Telegram bot token (from @BotFather) |
| `TELEGRAM_ALERT_CHAT_ID` | `1651759646` | Your Telegram chat ID |
| `GRAFANA_PASSWORD` | `StockTrackerMonitoring2024!` | Grafana admin password |

#### Деплой
| Secret Name | Value | Description |
|------------|-------|-------------|
| `PRODUCTION_HOST` | `158.160.188.247` | Production server IP |
| `PRODUCTION_USER` | `ubuntu` / `root` | SSH username |
| `SSH_PRIVATE_KEY` | `-----BEGIN...` | SSH private key |
| `SSH_PORT` | `22` (default) | SSH port |

## 🎯 Как работает деплой

### 1. Push в GitHub
```bash
git add .
git commit -m "feat: update monitoring config"
git push origin main
```

### 2. Автоматический запуск workflow
GitHub Actions автоматически:
1. ✅ Проверяет Prometheus конфиг
2. ✅ Проверяет Alertmanager конфиг  
3. ✅ Тестирует metrics endpoint
4. ✅ Подключается к production серверу
5. ✅ Создает backup текущей конфигурации
6. ✅ Пуллит последний код
7. ✅ Создает monitoring secrets
8. ✅ Обновляет .env файл
9. ✅ Перезапускает monitoring сервисы
10. ✅ Проверяет health endpoints
11. ✅ Отправляет уведомление в Telegram

### 3. Получение результата
Вы получите Telegram уведомление:
- ✅ "Monitoring deployment SUCCESSFUL" - если успешно
- ❌ "Monitoring deployment FAILED" - если ошибка

## 📊 Мониторинг деплоя

### Через GitHub CLI
```bash
# Список последних запусков
gh run list

# Просмотр текущего запуска
gh run watch

# Логи последнего запуска
gh run view --log
```

### Через GitHub UI
https://github.com/YOUR_USERNAME/Stock-Tracker/actions

## 🔧 Troubleshooting

### Workflow падает на валидации конфигов

**Проблема:** Prometheus/Alertmanager конфиг невалидный

**Решение:**
```bash
# Проверить локально
docker run --rm -v $(pwd)/monitoring/prometheus.yml:/prometheus.yml \
  prom/prometheus:v2.48.0 promtool check config /prometheus.yml

docker run --rm -v $(pwd)/monitoring/alertmanager.yml:/alertmanager.yml \
  prom/alertmanager:v0.26.0 amtool check-config /alertmanager.yml
```

### SSH connection failed

**Проблема:** Не может подключиться к production серверу

**Решение:**
1. Проверьте `PRODUCTION_HOST` и `PRODUCTION_USER`
2. Убедитесь что `SSH_PRIVATE_KEY` правильный:
   ```bash
   # Сгенерировать новую пару ключей
   ssh-keygen -t ed25519 -C "github-actions"
   
   # Добавить публичный ключ на сервер
   ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server
   
   # Скопировать приватный ключ в GitHub Secret
   cat ~/.ssh/id_ed25519
   ```

### Health check failed

**Проблема:** Сервисы не отвечают после деплоя

**Решение:**
```bash
# На production сервере
docker ps  # Проверить что сервисы запущены
docker logs stock-tracker-prometheus --tail 50
docker logs stock-tracker-alertmanager --tail 50
docker logs stock-tracker-grafana --tail 50

# Перезапустить вручную
docker-compose restart prometheus alertmanager grafana
```

### Secrets не работают

**Проблема:** Monitoring secrets не создаются на сервере

**Решение:**
```bash
# На production сервере вручную
cd /path/to/Stock-Tracker
mkdir -p monitoring/secrets
echo "YOUR_BOT_TOKEN" > monitoring/secrets/telegram_bot_token.txt
chmod 600 monitoring/secrets/telegram_bot_token.txt
docker-compose restart alertmanager
```

## 🎨 Кастомизация

### Изменение пути на сервере

В `.github/workflows/deploy-monitoring.yml`:
```yaml
script: |
  cd /path/to/Stock-Tracker  # ← Измените здесь
```

### Изменение ветки деплоя

```yaml
on:
  push:
    branches:
      - main      # ← Измените на production, release, etc.
```

### Добавление дополнительных проверок

```yaml
- name: Custom validation
  run: |
    # Ваши проверки
```

## 📝 Best Practices

1. **Тестируйте локально перед push**
   ```bash
   docker-compose config  # Проверить синтаксис
   docker-compose up -d   # Запустить локально
   ```

2. **Используйте feature branches**
   ```bash
   git checkout -b feature/monitoring-update
   # make changes
   git push origin feature/monitoring-update
   # create PR, review, then merge to main
   ```

3. **Мониторьте логи деплоя**
   ```bash
   gh run watch  # Во время деплоя
   ```

4. **Сохраняйте backups**
   Workflow автоматически создает backup:
   ```
   backups/docker-compose.yml.20251211_200000
   ```

5. **Проверяйте health после деплоя**
   ```bash
   curl http://YOUR_HOST:9090/-/healthy  # Prometheus
   curl http://YOUR_HOST:9093/-/healthy  # Alertmanager
   curl http://YOUR_HOST:3000/api/health # Grafana
   ```

## 🔗 Полезные ссылки

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub CLI](https://cli.github.com/)
- [appleboy/ssh-action](https://github.com/appleboy/ssh-action)
- [Docker Secrets Setup](monitoring/DOCKER_SECRETS_SETUP.md)
- [Monitoring Guide](docs/MONITORING_GUIDE.md)

## 📞 Поддержка

При проблемах с CI/CD:
1. Проверьте логи workflow в GitHub Actions
2. Проверьте логи на production сервере
3. Убедитесь что все secrets установлены правильно
4. Проверьте что SSH ключи работают

---

**Следующий шаг:** [Setup GitHub Secrets](scripts/setup_github_secrets.ps1) → Push в main → Получить уведомление в Telegram ✅
