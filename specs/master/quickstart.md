# Quick Start Guide: Google Sheets Stock Tracker

**Version**: 1.0  
**Date**: 21 октября 2025 г.  
**Prerequisites**: Google Account, Wildberries Seller Account с API токеном

## Overview

Stock Tracker автоматически обновляет Google-таблицу данными об остатках и заказах товаров с Wildberries. Система работает через Google Apps Script и обновляется ежедневно в 00:00.

## Step 1: Setup Google Sheets

### 1.1 Create New Spreadsheet

1. Откройте [Google Sheets](https://sheets.google.com)
2. Создайте новую таблицу
3. Переименуйте её в "Wildberries Stock Tracker"
4. Скопируйте URL таблицы - понадобится позже

### 1.2 Setup Headers

Добавьте заголовки в первую строку:

| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| Артикул продавца | Артикул товара | Заказы (всего) | Остатки (всего) | Оборачиваемость | Название склада | Заказы со склада | Остатки на складе |

### 1.3 Apply Formatting

1. Выделите строку заголовков (A1:H1)
2. **Формат** → **Жирный**
3. **Формат** → **Заливка** → выберите цвет фона
4. Выделите колонки F, G, H
5. **Формат** → **Перенос текста** → **Перенос**

## Step 2: Get Wildberries API Token

### 2.1 Access API Settings

1. Войдите в [Личный кабинет Wildberries](https://seller.wildberries.ru)
2. Перейдите в **Настройки** → **Доступ к API**
3. Создайте новый токен или используйте существующий
4. Скопируйте токен - **ВАЖНО: храните его в безопасности!**

### 2.2 Required Permissions

Убедитесь что токен имеет права доступа к:
- ✅ Статистика (получение остатков)
- ✅ Поставки (получение заказов)

## Step 3: Setup Google Apps Script

### 3.1 Open Script Editor

1. В вашей Google таблице: **Расширения** → **Apps Script**
2. Удалите код по умолчанию из `Code.gs`
3. Скопируйте и вставьте код из `src/sheets/tracker_template.gs` (будет создан в Phase 2)

### 3.2 Configure Settings

В редакторе скриптов добавьте конфигурацию:

```javascript
function setupConfig() {
  const properties = PropertiesService.getScriptProperties();
  
  properties.setProperties({
    'WILDBERRIES_TOKEN': 'YOUR_API_TOKEN_HERE',
    'SPREADSHEET_ID': 'YOUR_SPREADSHEET_ID_HERE',
    'TIMEZONE': 'Europe/Moscow',
    'UPDATE_TIME': '00:00',
    'DATA_RETENTION_DAYS': '7'
  });
  
  Logger.log('Configuration saved successfully');
}
```

**Замените**:
- `YOUR_API_TOKEN_HERE` - на ваш Wildberries API токен
- `YOUR_SPREADSHEET_ID_HERE` - на ID вашей таблицы (из URL)

### 3.3 Run Initial Setup

1. Выберите функцию `setupConfig` в dropdown
2. Нажмите **▶ Выполнить**
3. Разрешите необходимые права доступа
4. Проверьте логи: **Вид** → **Логи**

## Step 4: Setup Daily Trigger

### 4.1 Create Time Trigger

```javascript
function createDailyTrigger() {
  // Удаляем существующие триггеры
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'updateStockData') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // Создаем новый триггер на 00:00
  ScriptApp.newTrigger('updateStockData')
    .timeBased()
    .everyDays(1)
    .atHour(0)
    .create();
    
  Logger.log('Daily trigger created for 00:00');
}
```

1. Сохраните функцию в скрипте
2. Выберите `createDailyTrigger` и выполните
3. Проверьте: **Триггеры** (слева в меню) → должен появиться новый триггер

## Step 5: Test Manual Update

### 5.1 Run Test Update

```javascript
function testUpdate() {
  try {
    Logger.log('Starting test update...');
    updateStockData();
    Logger.log('Test update completed successfully');
  } catch (error) {
    Logger.log('Test update failed: ' + error.toString());
  }
}
```

1. Добавьте функцию в скрипт
2. Выполните `testUpdate`
3. Проверьте результаты в таблице
4. Проверьте логи на наличие ошибок

### 5.2 Verify Results

В таблице должны появиться:
- ✅ Данные товаров с вашего аккаунта
- ✅ Правильные суммы в колонках C и D
- ✅ Корректная оборачиваемость в колонке E
- ✅ Множественные склады в колонках F, G, H (если применимо)

## Step 6: Monitor and Maintain

### 6.1 Check Execution Status

Просматривайте выполнения:
1. **Apps Script** → **Мои выполнения**
2. Проверяйте статус ежедневных обновлений
3. Изучайте логи при ошибках

### 6.2 Common Issues & Solutions

**Проблема**: "Exception: Request failed for https://..."
**Решение**: Проверьте API токен и его права доступа

**Проблема**: "Exception: You do not have permission..."
**Решение**: Проверьте права доступа к таблице

**Проблема**: Пустая таблица после обновления
**Решение**: Проверьте наличие товаров в личном кабинете WB

**Проблема**: Некорректная оборачиваемость
**Решение**: Проверьте формулы в колонках C, D, E

## Advanced Configuration

### Custom Update Time

Изменить время обновления:
```javascript
// Обновление в 6:00 утра
ScriptApp.newTrigger('updateStockData')
  .timeBased()
  .everyDays(1)
  .atHour(6)
  .create();
```

### Data Retention Period

Изменить период данных (по умолчанию 7 дней):
```javascript
PropertiesService.getScriptProperties().setProperty('DATA_RETENTION_DAYS', '14');
```

### Error Notifications

Добавить уведомления об ошибках:
```javascript
function onUpdateError(error) {
  const email = 'your-email@example.com';
  const subject = 'Stock Tracker Error';
  const body = `Update failed: ${error.message}\nTime: ${new Date()}`;
  
  GmailApp.sendEmail(email, subject, body);
}
```

## Troubleshooting

### Debug Mode

Включить детальное логирование:
```javascript
PropertiesService.getScriptProperties().setProperty('DEBUG_MODE', 'true');
```

### Manual API Test

Тестирование API подключения:
```javascript
function testAPI() {
  const token = PropertiesService.getScriptProperties().getProperty('WILDBERRIES_TOKEN');
  const url = 'https://statistics-api.wildberries.ru/api/v1/supplier/stocks';
  
  const options = {
    method: 'GET',
    headers: {
      'Authorization': 'Bearer ' + token
    }
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    Logger.log('API Response: ' + response.getContentText());
  } catch (error) {
    Logger.log('API Error: ' + error.toString());
  }
}
```

### Reset Configuration

Сброс настроек:
```javascript
function resetConfig() {
  PropertiesService.getScriptProperties().deleteAll();
  Logger.log('All configuration deleted');
}
```

## Security Best Practices

### 1. API Token Security
- ❌ НЕ делитесь API токеном
- ❌ НЕ публикуйте токен в коде
- ✅ Используйте PropertiesService для хранения
- ✅ Регулярно обновляйте токен

### 2. Spreadsheet Access
- ✅ Ограничьте доступ к таблице
- ✅ Используйте корпоративный аккаунт если возможно
- ✅ Регулярно проверяйте список пользователей

### 3. Script Permissions
- ✅ Просматривайте разрешения перед их предоставлением
- ✅ Ограничивайте доступ к скрипту
- ✅ Используйте версионирование для отката изменений

## Support

### Resources
- 📖 [Google Apps Script Documentation](https://developers.google.com/apps-script)
- 📖 [Wildberries API Documentation](https://openapi.wildberries.ru/)
- 📖 [Google Sheets API Reference](https://developers.google.com/sheets/api)

### Common Commands

**View Logs**: Apps Script → Мои выполнения → View logs  
**Edit Triggers**: Apps Script → Триггеры  
**Check Quotas**: Apps Script → Квоты  
**Version History**: Apps Script → Версии

### Getting Help

1. Проверьте логи выполнения
2. Убедитесь в правильности конфигурации
3. Протестируйте API подключение отдельно
4. Проверьте права доступа к таблице

**Next Steps**: После успешной настройки система будет автоматически обновлять данные каждый день в 00:00. Мониторьте выполнения и логи для обеспечения стабильной работы.