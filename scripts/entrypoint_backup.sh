#!/bin/bash
#
# Entrypoint для контейнера бэкапа
# Поддерживает два режима:
# - cron: запуск планировщика (по умолчанию)
# - backup: однократный бэкап
#

set -e

MODE="${BACKUP_MODE:-cron}"

case "$MODE" in
    cron)
        echo "[$(date)] Запуск планировщика бэкапов..."
        echo "[$(date)] Расписание: 03:00 каждый день (Europe/Moscow)"
        echo "[$(date)] Для ручного запуска: docker-compose run --rm -e BACKUP_MODE=backup backup"
        
        # Экспорт переменных окружения в файл для cron
        printenv | grep -E "^(POSTGRES_|S3_|BACKUP_|TELEGRAM_|LOG_)" > /app/scripts/env.sh
        sed -i 's/^/export /' /app/scripts/env.sh
        
        # Обновляем crontab чтобы загружать переменные
        echo "0 3 * * * . /app/scripts/env.sh && /app/scripts/backup_postgres.sh >> /var/log/backup_cron.log 2>&1" | crontab -
        
        # Запуск crond в foreground (busybox crond)
        exec crond -f -d 8
        ;;
    backup)
        echo "[$(date)] Однократный запуск бэкапа..."
        exec /app/scripts/backup_postgres.sh
        ;;
    *)
        echo "Неизвестный режим: $MODE"
        echo "Используйте: cron или backup"
        exit 1
        ;;
esac
