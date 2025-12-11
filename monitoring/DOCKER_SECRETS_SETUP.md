# Docker Secrets для Alertmanager

Этот гайд объясняет как безопасно хранить токен Telegram бота для Alertmanager.

## 🔐 Что такое Docker Secrets (через Volume Mount)?

Вместо хранения секретов в environment variables или прямо в YAML конфигах, мы используем файлы с секретами, которые монтируются в контейнер только для чтения.

## 📁 Структура

```
monitoring/secrets/
├── .gitkeep                          # В git
├── telegram_bot_token.txt.example   # В git (template)
├── telegram_chat_id.txt.example     # В git (template)
├── telegram_bot_token.txt           # НЕ В GIT! (actual token)
└── telegram_chat_id.txt             # НЕ В GIT! (actual chat ID)
```

## 🚀 Настройка для нового окружения

1. **Скопируйте примеры:**
```bash
cd monitoring/secrets
cp telegram_bot_token.txt.example telegram_bot_token.txt
cp telegram_chat_id.txt.example telegram_chat_id.txt
```

2. **Отредактируйте файлы с секретами:**
```bash
# telegram_bot_token.txt
echo "YOUR_BOT_TOKEN_HERE" > telegram_bot_token.txt

# telegram_chat_id.txt
echo "YOUR_CHAT_ID_HERE" > telegram_chat_id.txt
```

3. **Проверьте что файлы НЕ в git:**
```bash
git status
# Не должно показывать telegram_bot_token.txt и telegram_chat_id.txt
```

## 🔧 Как это работает?

### docker-compose.yml
```yaml
alertmanager:
  volumes:
    # Монтируем секретные файлы только для чтения
    - ./monitoring/secrets/telegram_bot_token.txt:/run/secrets/telegram_bot_token:ro
    - ./monitoring/secrets/telegram_chat_id.txt:/run/secrets/telegram_chat_id:ro
```

### alertmanager.yml
```yaml
receivers:
  - name: 'telegram-default'
    telegram_configs:
      # Используем _file вместо прямых значений
      - bot_token_file: '/run/secrets/telegram_bot_token'
        chat_id_file: '/run/secrets/telegram_chat_id'
```

## ✅ Преимущества

1. **Безопасность**: Секреты не в коде, не в environment variables
2. **Простота**: Не нужен Docker Swarm или Kubernetes
3. **Git-friendly**: Примеры в git, реальные значения - нет
4. **CI/CD ready**: В pipeline создаете файлы из secrets хранилища

## 🏭 Production Setup

### GitHub Actions Example
```yaml
- name: Create secrets for monitoring
  run: |
    mkdir -p monitoring/secrets
    echo "${{ secrets.TELEGRAM_BOT_TOKEN }}" > monitoring/secrets/telegram_bot_token.txt
    echo "${{ secrets.TELEGRAM_CHAT_ID }}" > monitoring/secrets/telegram_chat_id.txt
    chmod 600 monitoring/secrets/*.txt
```

### GitLab CI Example
```yaml
before_script:
  - mkdir -p monitoring/secrets
  - echo "$TELEGRAM_BOT_TOKEN" > monitoring/secrets/telegram_bot_token.txt
  - echo "$TELEGRAM_CHAT_ID" > monitoring/secrets/telegram_chat_id.txt
  - chmod 600 monitoring/secrets/*.txt
```

### Manual Server Setup
```bash
# На production сервере
cd /path/to/Stock-Tracker
mkdir -p monitoring/secrets

# Создайте файлы с вашими значениями
echo "8558236991:AAHFu2krkBMIWFKF6W_MkIYoIFbfw-d1kms" > monitoring/secrets/telegram_bot_token.txt
echo "1651759646" > monitoring/secrets/telegram_chat_id.txt

# Ограничьте доступ (только owner может читать)
chmod 600 monitoring/secrets/*.txt

# Проверьте
ls -la monitoring/secrets/
```

## 🧪 Тестирование

```bash
# Перезапустите Alertmanager
docker-compose restart alertmanager

# Проверьте что секреты загружены
docker exec stock-tracker-alertmanager cat /run/secrets/telegram_bot_token
# Должен показать ваш токен

# Проверьте логи
docker logs stock-tracker-alertmanager
# Не должно быть ошибок про telegram config
```

## ⚠️ Важно

- ✅ `.gitignore` уже настроен - файлы `*.txt` (кроме `*.example`) не попадут в git
- ✅ Файлы монтируются read-only (`:ro`) - контейнер не может их изменить
- ✅ Permissions `600` означают только owner может читать
- ⚠️ Не коммитьте реальные токены в git!
- ⚠️ Не пушьте `MONITORING_CREDENTIALS.md` (уже в .gitignore)

## 🔄 Ротация секретов

Если нужно сменить токен:
1. Обновите файл `monitoring/secrets/telegram_bot_token.txt`
2. Перезапустите: `docker-compose restart alertmanager`
3. Готово!

Никаких изменений в YAML конфигах не требуется.
