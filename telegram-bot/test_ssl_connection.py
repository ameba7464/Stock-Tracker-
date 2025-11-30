"""Тест SSL соединения с Google API."""
import requests
import ssl
import socket

def test_basic_connection():
    """Тест базового подключения к Google API."""
    print("🔍 Тест подключения к Google API")
    print("=" * 60)
    
    # Тест 1: Простой HTTP запрос
    print("\n1️⃣ Тест requests библиотеки:")
    try:
        response = requests.get("https://www.googleapis.com/", timeout=10)
        print(f"✅ Успешно! Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 2: SSL соединение
    print("\n2️⃣ Тест SSL соединения:")
    try:
        context = ssl.create_default_context()
        with socket.create_connection(("www.googleapis.com", 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname="www.googleapis.com") as ssock:
                print(f"✅ SSL соединение установлено")
                print(f"   Версия: {ssock.version()}")
                print(f"   Cipher: {ssock.cipher()}")
    except Exception as e:
        print(f"❌ Ошибка SSL: {e}")
    
    # Тест 3: Проверка сертификатов
    print("\n3️⃣ Проверка SSL сертификата:")
    try:
        import certifi
        print(f"✅ certifi установлен")
        print(f"   Путь: {certifi.where()}")
    except ImportError:
        print(f"❌ certifi не установлен")
        print(f"   Установите: pip install certifi")
    
    # Тест 4: Проверка переменных окружения
    print("\n4️⃣ Проверка переменных окружения:")
    import os
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    found_proxy = False
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"   {var} = {value}")
            found_proxy = True
    if not found_proxy:
        print("   Прокси не настроен")
    
    print("\n" + "=" * 60)
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Попробуйте отключить антивирус временно")
    print("   2. Проверьте настройки файрвола")
    print("   3. Если используете корпоративную сеть - может требоваться прокси")
    print("   4. Попробуйте: pip install --upgrade certifi")

if __name__ == "__main__":
    test_basic_connection()
