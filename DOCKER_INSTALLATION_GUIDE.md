# 🐳 Docker Desktop Installation Guide for Windows

## Предварительные требования

- Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 or higher)
- OR Windows 11 64-bit
- WSL 2 должен быть установлен
- Virtualization должна быть включена в BIOS

---

## 📥 Шаг 1: Установка WSL 2 (если еще не установлен)

### Открыть PowerShell от имени Администратора и выполнить:

```powershell
# Установить WSL
wsl --install

# Перезагрузить компьютер после установки
```

### После перезагрузки проверить:

```powershell
wsl --list --verbose
```

Должно показать установленный Ubuntu или другой дистрибутив.

---

## 📥 Шаг 2: Скачать Docker Desktop

1. Перейти на официальный сайт: https://www.docker.com/products/docker-desktop/
2. Нажать **"Download for Windows"**
3. Скачать файл **Docker Desktop Installer.exe** (~500MB)

---

## 🔧 Шаг 3: Установить Docker Desktop

1. Запустить **Docker Desktop Installer.exe**
2. В окне установки:
   - ✅ Отметить **"Use WSL 2 instead of Hyper-V"** (рекомендуется)
   - ✅ Отметить **"Add shortcut to desktop"**
3. Нажать **"Ok"** и дождаться установки
4. **Перезагрузить компьютер**

---

## 🚀 Шаг 4: Запустить Docker Desktop

1. Открыть **Docker Desktop** из меню Пуск
2. Дождаться полного запуска (может занять 1-2 минуты)
3. В правом нижнем углу появится иконка Docker с зеленым статусом

---

## ✅ Шаг 5: Проверить установку

Открыть PowerShell и выполнить:

```powershell
# Проверить версию Docker
docker --version

# Проверить версию Docker Compose
docker compose version

# Запустить тестовый контейнер
docker run hello-world
```

Должно вывести версии и успешно запустить hello-world контейнер.

---

## ⚙️ Шаг 6: Настроить Docker Desktop (опционально)

### Открыть Docker Desktop → Settings:

1. **General**
   - ✅ Start Docker Desktop when you log in

2. **Resources**
   - **Memory:** 4-8 GB (рекомендуется 6GB для Stock Tracker)
   - **CPUs:** 2-4 (рекомендуется 4 для Stock Tracker)
   - **Disk:** 60GB+ (для образов и контейнеров)

3. **Docker Engine**
   - Оставить настройки по умолчанию

4. Нажать **"Apply & restart"**

---

## 🎯 Следующие шаги после установки Docker

После успешной установки Docker Desktop вернитесь к тестированию проекта:

```powershell
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"
docker compose up -d
```

---

## 🐛 Troubleshooting

### Проблема: "WSL 2 installation is incomplete"

**Решение:**
```powershell
# Установить обновление ядра WSL 2
# Скачать с: https://aka.ms/wsl2kernel
# Установить и перезагрузить
```

### Проблема: "Hardware assisted virtualization is not enabled"

**Решение:**
1. Перезагрузить компьютер
2. Войти в BIOS (обычно F2, F10, Delete при загрузке)
3. Найти "Intel VT-x" или "AMD-V" в разделе CPU
4. Включить (Enable)
5. Сохранить и выйти

### Проблема: Docker Desktop очень медленный

**Решение:**
1. Увеличить Memory до 6-8GB в Settings → Resources
2. Увеличить CPUs до 4 cores
3. Выключить антивирус для Docker папки (C:\Program Files\Docker)

### Проблема: "Error response from daemon: open \\.\pipe\docker_engine..."

**Решение:**
```powershell
# Перезапустить Docker Desktop
# Или выполнить в PowerShell от имени Администратора:
Stop-Service docker
Start-Service docker
```

---

## 📚 Дополнительные ресурсы

- **Docker Desktop Documentation:** https://docs.docker.com/desktop/
- **WSL 2 Documentation:** https://docs.microsoft.com/en-us/windows/wsl/
- **Docker Compose Documentation:** https://docs.docker.com/compose/

---

## 🎉 После установки

Когда Docker Desktop установлен и работает, выполните:

```powershell
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"

# Запустить все сервисы
docker compose up -d

# Применить миграции базы данных
docker compose exec api alembic upgrade head

# Проверить статус сервисов
docker compose ps

# Просмотр логов
docker compose logs -f api
```

---

**Good luck! 🚀**
