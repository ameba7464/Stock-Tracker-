#!/bin/bash
#
# PostgreSQL Restore Script from Yandex Object Storage (S3)
# 
# Функционал:
# - Скачивание бэкапа из Yandex Object Storage
# - Распаковка и восстановление базы данных
# - Опциональное пересоздание базы
#
# Использование:
#   ./restore_postgres.sh <s3_path_or_filename>
#   ./restore_postgres.sh backup_stock_tracker_20241201_030000.sql.gz
#   ./restore_postgres.sh s3://stock-tracker-backups/postgres/backup_stock_tracker_20241201_030000.sql.gz
#
# Опции:
#   --recreate-db   Пересоздать базу данных перед восстановлением
#   --list          Показать список доступных бэкапов
#   --latest        Восстановить из последнего бэкапа
#

set -euo pipefail

# ================================
# КОНФИГУРАЦИЯ
# ================================

# PostgreSQL настройки
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

# Параметры восстановления
RESTORE_DIR="${RESTORE_DIR:-/tmp/restore}"
LOG_FILE="${LOG_FILE:-/var/log/restore_postgres.log}"

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

show_usage() {
    cat << EOF
Использование: $0 [ОПЦИИ] <backup_name>

Восстановление PostgreSQL из бэкапа в Yandex Object Storage.

Аргументы:
  backup_name         Имя файла бэкапа или полный S3 путь

Опции:
  --list              Показать список доступных бэкапов
  --latest            Восстановить из последнего бэкапа
  --recreate-db       Пересоздать базу данных перед восстановлением
  --help              Показать эту справку

Примеры:
  $0 --list
  $0 --latest
  $0 backup_stock_tracker_20241201_030000.sql.gz
  $0 --recreate-db backup_stock_tracker_20241201_030000.sql.gz
  $0 s3://stock-tracker-backups/postgres/backup.sql.gz
EOF
}

check_dependencies() {
    local deps=("psql" "gunzip" "aws")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Зависимость '$dep' не найдена."
            exit 1
        fi
    done
}

setup_aws_config() {
    export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
    export AWS_DEFAULT_REGION="$S3_REGION"
}

list_backups() {
    log_info "Список доступных бэкапов:"
    echo ""
    aws s3 ls "s3://${S3_BUCKET}/postgres/" \
        --endpoint-url "$S3_ENDPOINT" \
        --human-readable
    echo ""
}

get_latest_backup() {
    local latest=$(aws s3 ls "s3://${S3_BUCKET}/postgres/" \
        --endpoint-url "$S3_ENDPOINT" 2>/dev/null | sort -k1,2 | tail -1 | awk '{print $4}')
    
    if [[ -z "$latest" ]]; then
        log_error "Не найдено ни одного бэкапа в S3"
        exit 1
    fi
    
    echo "$latest"
}

download_backup() {
    local backup_name="$1"
    local s3_path
    
    # Определяем полный S3 путь
    if [[ "$backup_name" == s3://* ]]; then
        s3_path="$backup_name"
    else
        s3_path="s3://${S3_BUCKET}/postgres/${backup_name}"
    fi
    
    local local_path="${RESTORE_DIR}/$(basename "$s3_path")"
    
    log_info "Скачивание бэкапа: $s3_path"
    
    mkdir -p "$RESTORE_DIR"
    
    aws s3 cp "$s3_path" "$local_path" \
        --endpoint-url "$S3_ENDPOINT" \
        --only-show-errors
    
    if [[ $? -ne 0 ]]; then
        log_error "Ошибка скачивания бэкапа"
        exit 1
    fi
    
    local file_size=$(du -h "$local_path" | cut -f1)
    log_success "Бэкап скачан: $local_path (размер: $file_size)"
    
    echo "$local_path"
}

decompress_backup() {
    local backup_path="$1"
    local sql_path="${backup_path%.gz}"
    
    if [[ "$backup_path" == *.gz ]]; then
        log_info "Распаковка бэкапа..."
        gunzip -f "$backup_path"
        log_success "Бэкап распакован: $sql_path"
    else
        sql_path="$backup_path"
    fi
    
    echo "$sql_path"
}

recreate_database() {
    log_info "Пересоздание базы данных '$POSTGRES_DB'..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Отключаем все соединения и пересоздаём БД
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres << EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$POSTGRES_DB'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS $POSTGRES_DB;
CREATE DATABASE $POSTGRES_DB;
EOF
    
    log_success "База данных пересоздана"
}

restore_database() {
    local sql_path="$1"
    
    log_info "Восстановление базы данных из $sql_path..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    psql -h "$POSTGRES_HOST" \
         -p "$POSTGRES_PORT" \
         -U "$POSTGRES_USER" \
         -d "$POSTGRES_DB" \
         -f "$sql_path" \
         --quiet \
         --set ON_ERROR_STOP=off 2>> "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "База данных восстановлена успешно"
    else
        log_error "Восстановление завершилось с ошибками (см. лог)"
    fi
}

cleanup() {
    log_info "Очистка временных файлов..."
    rm -rf "$RESTORE_DIR"
    log_info "Очистка завершена"
}

# ================================
# ОСНОВНОЙ СКРИПТ
# ================================

main() {
    local backup_name=""
    local recreate_db=false
    local list_only=false
    local use_latest=false
    
    # Парсинг аргументов
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help)
                show_usage
                exit 0
                ;;
            --list)
                list_only=true
                shift
                ;;
            --latest)
                use_latest=true
                shift
                ;;
            --recreate-db)
                recreate_db=true
                shift
                ;;
            -*)
                log_error "Неизвестная опция: $1"
                show_usage
                exit 1
                ;;
            *)
                backup_name="$1"
                shift
                ;;
        esac
    done
    
    log_info "=========================================="
    log_info "Восстановление PostgreSQL из бэкапа"
    log_info "=========================================="
    
    # Проверки
    check_dependencies
    setup_aws_config
    
    # Режим списка
    if [[ "$list_only" == true ]]; then
        list_backups
        exit 0
    fi
    
    # Определение бэкапа для восстановления
    if [[ "$use_latest" == true ]]; then
        backup_name=$(get_latest_backup)
        log_info "Выбран последний бэкап: $backup_name"
    fi
    
    if [[ -z "$backup_name" ]]; then
        log_error "Не указан файл бэкапа"
        show_usage
        exit 1
    fi
    
    # Подтверждение
    echo ""
    echo "⚠️  ВНИМАНИЕ: Восстановление перезапишет текущие данные!"
    echo ""
    echo "База данных: $POSTGRES_DB"
    echo "Бэкап: $backup_name"
    echo "Пересоздание БД: $recreate_db"
    echo ""
    read -p "Продолжить? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "Восстановление отменено"
        exit 0
    fi
    
    local start_time=$(date +%s)
    
    # Скачивание бэкапа
    local backup_path
    backup_path=$(download_backup "$backup_name")
    
    # Распаковка
    local sql_path
    sql_path=$(decompress_backup "$backup_path")
    
    # Пересоздание БД (опционально)
    if [[ "$recreate_db" == true ]]; then
        recreate_database
    fi
    
    # Восстановление
    restore_database "$sql_path"
    
    # Очистка
    cleanup
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "=========================================="
    log_success "Восстановление завершено за ${duration} секунд"
    log_success "=========================================="
}

# Обработка ошибок
trap 'log_error "Скрипт завершился с ошибкой"; exit 1' ERR

# Запуск
main "$@"
