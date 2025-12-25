"""
Скрипт для проверки статуса Telegram бота.
Проверяет, может ли бот получать обновления и отвечать на команды.
"""
import asyncio
import os
import sys
from aiogram import Bot
from aiogram.types import BotCommand


async def check_bot():
    """Проверка статуса бота."""
    # Получаем токен из .env или переменной окружения
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        print("❌ BOT_TOKEN не найден!")
        print("Убедитесь, что файл .env существует и содержит BOT_TOKEN")
        return False
    
    print(f"🔑 Token: {bot_token[:10]}...{bot_token[-10:]}")
    print()
    
    try:
        bot = Bot(token=bot_token)
        
        # 1. Проверка информации о боте
        print("1️⃣ Проверка информации о боте...")
        me = await bot.get_me()
        print(f"✅ Бот найден:")
        print(f"   - ID: {me.id}")
        print(f"   - Username: @{me.username}")
        print(f"   - Name: {me.first_name}")
        print(f"   - Can read messages: {me.can_read_all_group_messages}")
        print()
        
        # 2. Проверка команд бота
        print("2️⃣ Проверка зарегистрированных команд...")
        commands = await bot.get_my_commands()
        if commands:
            print(f"✅ Команды зарегистрированы ({len(commands)}):")
            for cmd in commands:
                print(f"   - /{cmd.command}: {cmd.description}")
        else:
            print("⚠️  Команды не зарегистрированы")
        print()
        
        # 3. Проверка webhook
        print("3️⃣ Проверка webhook...")
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            print(f"⚠️  Webhook установлен: {webhook_info.url}")
            print(f"   - Pending updates: {webhook_info.pending_update_count}")
            print(f"   - Last error: {webhook_info.last_error_message or 'Нет'}")
            print()
            print("⚠️  ВНИМАНИЕ: При установленном webhook polling не работает!")
            print("   Удалите webhook командой: await bot.delete_webhook()")
        else:
            print("✅ Webhook не установлен (polling mode)")
        print()
        
        # 4. Проверка получения обновлений
        print("4️⃣ Проверка получения обновлений...")
        try:
            updates = await bot.get_updates(limit=1, timeout=2)
            print(f"✅ Бот может получать обновления")
            if updates:
                print(f"   Найдено необработанных обновлений: {len(updates)}")
            else:
                print(f"   Необработанных обновлений нет")
        except Exception as e:
            print(f"❌ Ошибка получения обновлений: {e}")
        print()
        
        # 5. Итоги
        print("=" * 50)
        print("📊 ИТОГИ ПРОВЕРКИ:")
        print("=" * 50)
        
        if webhook_info.url:
            print("⚠️  ПРОБЛЕМА: Webhook установлен!")
            print("   Это блокирует polling режим.")
            print("   Решение:")
            print("   1. Удалите webhook: python -c 'from aiogram import Bot; import asyncio; asyncio.run(Bot(\"YOUR_TOKEN\").delete_webhook())'")
            print("   2. Или используйте webhook вместо polling")
            return False
        else:
            print("✅ Бот настроен правильно для polling режима")
            print("✅ Можно запускать: python -m app.main")
            return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        print()
        print("Возможные причины:")
        print("- Неправильный токен бота")
        print("- Нет интернет-соединения")
        print("- Telegram API недоступен")
        return False
    finally:
        await bot.session.close()


async def main():
    """Главная функция."""
    print("=" * 50)
    print("🤖 ПРОВЕРКА СТАТУСА TELEGRAM БОТА")
    print("=" * 50)
    print()
    
    # Загружаем .env если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env файл загружен")
    except ImportError:
        print("⚠️  python-dotenv не установлен, используем переменные окружения")
    print()
    
    success = await check_bot()
    
    print()
    print("=" * 50)
    if success:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
        sys.exit(0)
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
