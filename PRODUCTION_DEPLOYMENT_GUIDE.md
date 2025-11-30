# 🚀 Production Deployment Guide

Полное руководство по развертыванию Stock Tracker в production окружении.

## 📋 Содержание

1. [Требования](#требования)
2. [Подготовка к развертыванию](#подготовка-к-развертыванию)
3. [Развертывание через Docker Compose](#развертывание-через-docker-compose)
4. [Развертывание на различных платформах](#развертывание-на-различных-платформах)
5. [Настройка мониторинга](#настройка-мониторинга)
6. [Backup и восстановление](#backup-и-восстановление)
7. [Troubleshooting](#troubleshooting)

---

## Требования

### Минимальные системные требования

- **CPU:** 2 cores (рекомендуется 4)
- **RAM:** 4 GB (рекомендуется 8 GB)
- **Disk:** 20 GB SSD
- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+

### Необходимое ПО

```bash
# Docker и Docker Compose
docker --version  # >= 24.0
docker-compose --version  # >= 2.20

# PostgreSQL (если не используете Docker)
psql --version  # >= 15.0

# Redis (если не используете Docker)
redis-cli --version  # >= 7.0

# Git
git --version
```

---

## Подготовка к развертыванию

### 1. Клонирование репозитория

```bash
# Клонируйте репозиторий
git clone https://github.com/yourusername/stock-tracker.git
cd stock-tracker

# Переключитесь на production ветку
git checkout main
```

### 2. Генерация секретных ключей

```bash
# SECRET_KEY для JWT
python -c "import secrets; print(secrets.token_urlsafe(32))"

# FERNET_KEY для шифрования credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Настройка переменных окружения

Создайте `.env` файл:

```bash
cp .env.docker .env
```

Отредактируйте `.env`:

```bash
# Database
POSTGRES_USER=stock_tracker
POSTGRES_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
POSTGRES_DB=stock_tracker

# Security (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!)
SECRET_KEY=your_generated_secret_key_here
FERNET_KEY=your_generated_fernet_key_here

# Application
ENVIRONMENT=production
CORS_ORIGINS=https://yourdomain.com

# Monitoring
SENTRY_DSN=https://your_sentry_dsn@sentry.io/project
SENTRY_TRACES_SAMPLE_RATE=0.1

# Rate Limiting
RATE_LIMIT_GLOBAL=1000
RATE_LIMIT_TENANT=100

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=CHANGE_THIS_PASSWORD
```

### 4. SSL сертификаты (для HTTPS)

```bash
# Создайте директорию для SSL
mkdir -p nginx/ssl

# Скопируйте ваши сертификаты
cp /path/to/fullchain.pem nginx/ssl/cert.pem
cp /path/to/privkey.pem nginx/ssl/key.pem

# Или используйте Let's Encrypt
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

---

## Развертывание через Docker Compose

### Быстрый старт

```bash
# 1. Запустите все сервисы
docker-compose up -d

# 2. Проверьте статус
docker-compose ps

# 3. Примените миграции БД
docker-compose exec api alembic upgrade head

# 4. Создайте первого администратора
docker-compose exec api python -c "
from stock_tracker.db.session import SessionLocal
from stock_tracker.db.models import User, Tenant
from stock_tracker.core.security import get_password_hash

db = SessionLocal()
tenant = Tenant(company_name='Admin Company', is_active=True)
db.add(tenant)
db.commit()

admin = User(
    email='admin@example.com',
    hashed_password=get_password_hash('AdminPassword123!'),
    full_name='Admin User',
    tenant_id=tenant.id,
    is_active=True,
    role='admin'
)
db.add(admin)
db.commit()
print('Admin created: admin@example.com / AdminPassword123!')
"
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/api/v1/health/

# Readiness check
curl http://localhost:8000/api/v1/health/ready

# Liveness check
curl http://localhost:8000/api/v1/health/live

# Metrics
curl http://localhost:8000/metrics
```

### Доступ к сервисам

- **API:** http://localhost:8000
- **Flower (Celery UI):** http://localhost:5555
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin / ваш_пароль)

---

## Развертывание на различных платформах

### AWS EC2

```bash
# 1. Создайте EC2 instance (t3.medium или выше)
# 2. Установите Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# 3. Настройте Security Group
# Разрешите порты: 80, 443, 8000 (временно)

# 4. Разверните приложение
git clone https://github.com/yourusername/stock-tracker.git
cd stock-tracker
cp .env.docker .env
# Отредактируйте .env
docker-compose up -d

# 5. Настройте Elastic Load Balancer (опционально)
```

### DigitalOcean Droplet

```bash
# 1. Создайте Droplet (4GB RAM минимум)
# 2. Подключитесь по SSH
ssh root@your-droplet-ip

# 3. Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Разверните приложение
git clone https://github.com/yourusername/stock-tracker.git
cd stock-tracker
cp .env.docker .env
# Отредактируйте .env
docker-compose up -d

# 5. Настройте Firewall
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### Heroku

```bash
# 1. Установите Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# 2. Войдите в Heroku
heroku login

# 3. Создайте приложение
heroku create stock-tracker-production

# 4. Добавьте addons
heroku addons:create heroku-postgresql:standard-0
heroku addons:create heroku-redis:premium-0

# 5. Настройте переменные окружения
heroku config:set SECRET_KEY=your_secret_key
heroku config:set FERNET_KEY=your_fernet_key
heroku config:set ENVIRONMENT=production

# 6. Разверните приложение
git push heroku main

# 7. Примените миграции
heroku run alembic upgrade head
```

### GCP Cloud Run

```bash
# 1. Установите gcloud CLI
curl https://sdk.cloud.google.com | bash

# 2. Войдите в GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. Создайте Cloud SQL (PostgreSQL)
gcloud sql instances create stock-tracker-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1

# 4. Создайте Memorystore (Redis)
gcloud redis instances create stock-tracker-cache \
    --size=1 \
    --region=us-central1

# 5. Build и push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/stock-tracker

# 6. Deploy to Cloud Run
gcloud run deploy stock-tracker \
    --image gcr.io/YOUR_PROJECT_ID/stock-tracker \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

---

## Настройка мониторинга

### Prometheus + Grafana

Уже настроено в `docker-compose.yml`. Доступ:

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000

### Импорт готовых dashboards

```bash
# 1. Откройте Grafana (http://localhost:3000)
# 2. Перейдите в Configuration > Data Sources
# 3. Добавьте Prometheus (http://prometheus:9090)
# 4. Импортируйте dashboard из monitoring/grafana/dashboards/
```

### Sentry (Error Tracking)

```bash
# 1. Зарегистрируйтесь на sentry.io
# 2. Создайте проект "stock-tracker"
# 3. Скопируйте DSN
# 4. Добавьте в .env:
echo "SENTRY_DSN=https://xxx@sentry.io/project" >> .env

# 5. Перезапустите сервисы
docker-compose restart api worker beat
```

---

## Backup и восстановление

### Backup PostgreSQL

```bash
# Ручной backup
docker-compose exec postgres pg_dump -U stock_tracker stock_tracker > backup_$(date +%Y%m%d).sql

# Автоматический backup (добавьте в cron)
cat > /etc/cron.daily/stock-tracker-backup << 'EOF'
#!/bin/bash
BACKUP_DIR=/backups/stock-tracker
mkdir -p $BACKUP_DIR
docker-compose -f /app/stock-tracker/docker-compose.yml exec -T postgres \
    pg_dump -U stock_tracker stock_tracker | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz
# Удаляем старые backup (старше 30 дней)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
EOF

chmod +x /etc/cron.daily/stock-tracker-backup
```

### Восстановление PostgreSQL

```bash
# 1. Остановите приложение
docker-compose stop api worker beat

# 2. Восстановите backup
cat backup_20250120.sql | docker-compose exec -T postgres psql -U stock_tracker stock_tracker

# 3. Запустите приложение
docker-compose start api worker beat
```

### Backup Redis (кэш)

```bash
# Redis backup (опционально, т.к. кэш можно пересоздать)
docker-compose exec redis redis-cli SAVE
docker cp stock-tracker-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

---

## Troubleshooting

### Проблема: API не отвечает

```bash
# Проверьте логи
docker-compose logs api

# Проверьте ресурсы
docker stats

# Перезапустите сервис
docker-compose restart api
```

### Проблема: БД не подключается

```bash
# Проверьте статус PostgreSQL
docker-compose ps postgres

# Проверьте логи
docker-compose logs postgres

# Проверьте соединение
docker-compose exec api psql -h postgres -U stock_tracker -d stock_tracker
```

### Проблема: Celery worker не обрабатывает задачи

```bash
# Проверьте статус worker
docker-compose logs worker

# Проверьте очередь в Redis
docker-compose exec redis redis-cli
> KEYS celery*

# Перезапустите worker
docker-compose restart worker beat
```

### Проблема: Высокая нагрузка

```bash
# Увеличьте количество воркеров
# В docker-compose.yml измените:
command: celery -A stock_tracker.workers.celery_app worker --loglevel=info --concurrency=8

# Или увеличьте количество uvicorn workers
command: uvicorn stock_tracker.api.main:app --host 0.0.0.0 --port 8000 --workers 8
```

---

## Production Checklist

- [ ] SECRET_KEY и FERNET_KEY сгенерированы и безопасны
- [ ] PostgreSQL пароль изменен
- [ ] Grafana пароль изменен
- [ ] SSL сертификаты настроены
- [ ] CORS_ORIGINS настроен на ваш домен
- [ ] Sentry DSN настроен
- [ ] Backup скрипт настроен и протестирован
- [ ] Firewall настроен (только 80, 443 открыты)
- [ ] Health checks проходят успешно
- [ ] Мониторинг работает (Prometheus + Grafana)
- [ ] Логи ротируются (logrotate настроен)
- [ ] GitHub Actions secrets настроены
- [ ] DNS настроен на ваш сервер

---

## Масштабирование

### Horizontal Scaling (Kubernetes)

```yaml
# Пример deployment для Kubernetes (k8s/deployment.yaml)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-tracker-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: stock-tracker-api
  template:
    metadata:
      labels:
        app: stock-tracker-api
    spec:
      containers:
      - name: api
        image: yourusername/stock-tracker:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: stock-tracker-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Load Balancing (Nginx)

```nginx
# Уже настроено в nginx/nginx.conf
# Для добавления дополнительных backend серверов:

upstream fastapi_backend {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}
```

---

## Поддержка

- **GitHub Issues:** https://github.com/yourusername/stock-tracker/issues
- **Documentation:** https://docs.stock-tracker.example.com
- **Email:** support@stock-tracker.example.com

