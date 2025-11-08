# ⚡ Быстрый старт GitHub Actions

## 3 шага до автоматизации

### 1️⃣ Получите Service Account JSON

1. Перейдите на https://console.cloud.google.com/
2. Создайте Service Account
3. Скачайте JSON ключ
4. Дайте доступ к Google Sheets (email из JSON)

### 2️⃣ Добавьте секреты в GitHub

Settings → Secrets → Actions → New repository secret:

| Секрет | Описание | Где взять |
|--------|----------|-----------|
| `GOOGLE_SERVICE_ACCOUNT` | Весь JSON из шага 1 | Service Account JSON |
| `WILDBERRIES_API_KEY` | API токен WB | Личный кабинет WB → API |
| `GOOGLE_SHEET_ID` | ID таблицы | URL таблицы между `/d/` и `/edit` |
| `GOOGLE_SHEET_NAME` | Название листа | По умолчанию: "Stock Tracker" |

### 3️⃣ Загрузите код на GitHub

```powershell
git add .github/workflows/update-stocks.yml
git add update_table_fixed.py
git commit -m "feat: Add GitHub Actions auto-update"
git push origin main
```

## ✅ Готово!

- **Автоматический запуск**: каждый день в 00:01 МСК
- **Ручной запуск**: Actions → "Update Stock Tracker Daily" → "Run workflow"
- **Логи**: Вкладка Actions на GitHub

📖 Подробная инструкция: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
