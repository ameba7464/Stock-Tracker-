#!/bin/bash
#
# PostgreSQL Backup Script with Yandex Object Storage (S3) Upload
# 
# Функционал:
# - Создание дампа PostgreSQL (pg_dump)
# - Сжатие gzip
# - Загрузка в Yandex Object Storage (S3-совместимое хранилище)
# - Ротация: удаление бэкапов старше N дней
# - Логирование операций
#
# Использование:
#   ./backup_postgres.sh
#
# Требования:
#   - pg_dump (postgresql-client)
#   - aws cli или s3cmd
#   - gzip
#

set -euo pipefail

# ================================
# КОНФИГУРАЦИЯ
# ================================

# PostgreSQL настройки (можно переопределить через переменные окружения)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-stock_tracker}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-stock_tracker_password}"
POSTGRES_DB="${POSTGRES_DB:-stock_tracker}"

# Yandex Object Storage (S3) настройки
S3_ENDPOINT="${S3_ENDPOINT:-https://storage.yandexcloud.net}"
S3_BUCKET="${S3_BUCKET:-stock-tracker-backups}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-}"
S3_SECRET_KEY="${S3_SECRET_KEY:-}"
S3_REGION="${S3_REGION:-ru-central1}"

# Параметры бэкапа
BACKUP_DIR="${BACKUP_DIR:-/tmp/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
LOG_FILE="${LOG_FILE:-/var/log/backup_postgres.log}"

# ================================
# ФУНКЦИИ
# ================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

check_dependencies() {
    local deps=("pg_dump" "gzip" "aws")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Зависимость '$dep' не найдена. Установите её перед запуском."
            exit 1
        fi
    done
    log_info "Все зависимости проверены"
}

check_s3_credentials() {
    if [[ -z "$S3_ACCESS_KEY" ]] || [[ -z "$S3_SECRET_KEY" ]]; then
        log_error "S3 credentials не настроены. Укажите S3_ACCESS_KEY и S3_SECRET_KEY"
        exit 1
    fi
}

setup_aws_config() {
    # Настройка AWS CLI для работы с Yandex Object Storage
    export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
    export AWS_DEFAULT_REGION="$S3_REGION"
}

create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log_info "Директория бэкапов: $BACKUP_DIR"
}

create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_filename="backup_${POSTGRES_DB}_${timestamp}.sql.gz"
    BACKUP_PATH="${BACKUP_DIR}/${backup_filename}"
    
    log_info "Создание бэкапа базы данных '$POSTGRES_DB'..."
    
    # Экспорт пароля для pg_dump
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Создание дампа с сжатием (без verbose для чистого вывода)
    pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --format=plain \
        --no-owner \
        --no-privileges \
        2>> "$LOG_FILE" | gzip > "$BACKUP_PATH"
    
    # Проверка что файл создан
    if [[ ! -f "$BACKUP_PATH" ]] || [[ ! -s "$BACKUP_PATH" ]]; then
        log_error "Ошибка создания бэкапа: файл не создан или пуст"
        exit 1
    fi
    
    local backup_size=$(du -h "$BACKUP_PATH" | cut -f1)
    log_success "Бэкап создан: $BACKUP_PATH (размер: $backup_size)"
}

upload_to_s3() {
    local backup_path="$1"
    local backup_filename=$(basename "$backup_path")
    local s3_path="s3://${S3_BUCKET}/postgres/${backup_filename}"
    
    log_info "Загрузка бэкапа в S3: $s3_path"
    
    aws s3 cp "$backup_path" "$s3_path" \
        --endpoint-url "$S3_ENDPOINT" \
        --only-show-errors
    
    if [[ $? -eq 0 ]]; then
        log_success "Бэкап загружен в S3: $s3_path"
    else
        log_error "Ошибка загрузки бэкапа в S3"
        exit 1
    fi
}

cleanup_local() {
    local backup_path="$1"
    
    log_info "Удаление локального файла бэкапа..."
    rm -f "$backup_path"
    log_info "Локальный файл удалён"
}

rotate_old_backups() {
    log_info "Ротация старых бэкапов (старше $BACKUP_RETENTION_DAYS дней)..."
    
    # Получаем список объектов в бакете
    local cutoff_date=$(date -d "-${BACKUP_RETENTION_DAYS} days" '+%Y-%m-%d')
    
    # Список всех бэкапов
    local backups=$(aws s3 ls "s3://${S3_BUCKET}/postgres/" \
        --endpoint-url "$S3_ENDPOINT" 2>/dev/null || true)
    
    if [[ -z "$backups" ]]; then
        log_info "Нет бэкапов для ротации"
        return
    fi
    
    local deleted_count=0
    
    while IFS= read -r line; do
        # Парсим дату из вывода aws s3 ls
        local file_date=$(echo "$line" | awk '{print $1}')
        local filename=$(echo "$line" | awk '{print $4}')
        
        if [[ -z "$filename" ]]; then
            continue
        fi
        
        # Сравниваем даты
        if [[ "$file_date" < "$cutoff_date" ]]; then
            log_info "Удаление старого бэкапа: $filename"
            aws s3 rm "s3://${S3_BUCKET}/postgres/${filename}" \
                --endpoint-url "$S3_ENDPOINT" \
                --only-show-errors
            ((deleted_count++))
        fi
    done <<< "$backups"
    
    log_success "Ротация завершена. Удалено бэкапов: $deleted_count"
}

send_notification() {
    local status="$1"
    local message="$2"
    
    # Опционально: отправка уведомлений в Telegram
    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=🗄️ Backup ${status}: ${message}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
}

# ================================
# ОСНОВНОЙ СКРИПТ
# ================================

# Глобальная переменная для пути бэкапа
BACKUP_PATH=""

main() {
    log_info "=========================================="
    log_info "Запуск бэкапа PostgreSQL"
    log_info "=========================================="
    
    local start_time=$(date +%s)
    
    # Проверки
    check_dependencies
    check_s3_credentials
    setup_aws_config
    create_backup_dir
    
    # Создание бэкапа (результат в BACKUP_PATH)
    create_backup
    
    # Загрузка в S3
    upload_to_s3 "$BACKUP_PATH"
    
    # Очистка локального файла
    cleanup_local "$BACKUP_PATH"
    
    # Ротация старых бэкапов
    rotate_old_backups
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "=========================================="
    log_success "Бэкап завершён успешно за ${duration} секунд"
    log_success "=========================================="
    
    send_notification "SUCCESS" "База данных $POSTGRES_DB успешно забэкаплена"
}

# Обработка ошибок
trap 'log_error "Скрипт завершился с ошибкой"; send_notification "FAILED" "Ошибка бэкапа базы $POSTGRES_DB"; exit 1' ERR

# Запуск
main "$@"
