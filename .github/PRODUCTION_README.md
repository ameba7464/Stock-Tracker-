# 🌐 Production Environment - Quick Reference

> Быстрая справка по production окружению Stock Tracker

## 🟢 Статус системы

**Telegram Bot:** ✅ Работает 24/7 в Yandex Cloud  
**FastAPI App:** ✅ Готово к запуску (Docker Compose)  
**Monitoring:** ✅ Настроено (запуск по требованию)

📊 **[Полный статус системы →](../PRODUCTION_STATUS.md)**

---

## 🚀 Быстрые команды

### Проверка статуса

```bash
# Telegram Bot (на Yandex Cloud VM)
sudo docker ps | grep stock-tracker-bot
sudo docker logs --tail 50 stock-tracker-bot

# FastAPI (локальный Docker Compose)
docker-compose ps
docker-compose logs -f api worker
```

### Перезапуск сервисов

```bash
# Telegram Bot (автоматически через GitHub Actions)
git push origin main  # Автодеплой при изменениях в telegram-bot/

# Или вручную на VM
sudo docker restart stock-tracker-bot

# FastAPI
docker-compose restart api worker
docker-compose restart  # Все сервисы
```

### Просмотр логов

```bash
# Последние логи
sudo docker logs --tail 100 stock-tracker-bot
docker-compose logs --tail 100 api worker beat

# В реальном времени
sudo docker logs -f stock-tracker-bot
docker-compose logs -f api worker
```

---

## 🔧 CI/CD Workflows

### Активные

- ✅ **Deploy Telegram Bot** - Автодеплой при push в `main`
- ✅ **Validate Monitoring Config** - Проверка конфигурации

### Отключенные

- ⚠️ **Monitoring Health Check** - Отключен (только ручной запуск)

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [PRODUCTION_STATUS.md](../PRODUCTION_STATUS.md) | Полный статус production системы |
| [PRODUCTION_DEPLOYMENT_GUIDE.md](../PRODUCTION_DEPLOYMENT_GUIDE.md) | Руководство по развертыванию |
| [MONITORING_QUICKSTART.md](../MONITORING_QUICKSTART.md) | Быстрый старт мониторинга |
| [telegram-bot/YANDEX_CLOUD_DEPLOY.md](../telegram-bot/YANDEX_CLOUD_DEPLOY.md) | Деплой бота в Yandex Cloud |

---

## 🆘 Troubleshooting

### Бот не отвечает

```bash
# 1. Проверить статус контейнера
sudo docker ps -a | grep stock-tracker-bot

# 2. Посмотреть логи
sudo docker logs --tail 100 stock-tracker-bot

# 3. Перезапустить
sudo docker restart stock-tracker-bot

# 4. Если не помогло - редеплой через GitHub Actions
```

### API не работает

```bash
# 1. Проверить все сервисы
docker-compose ps

# 2. Проверить логи
docker-compose logs api postgres redis

# 3. Перезапустить проблемный сервис
docker-compose restart api

# 4. Полный перезапуск
docker-compose down && docker-compose up -d
```

---

## 📞 Быстрые ссылки

- 🤖 Telegram Bot: `@your_bot_username`
- 📊 Grafana: `http://your-server:3000`
- 🌸 Flower (Celery): `http://your-server:5555`
- 📈 Prometheus: `http://your-server:9090`
- 🚨 Alertmanager: `http://your-server:9093`

---

*Последнее обновление: 25 декабря 2025 г.*
