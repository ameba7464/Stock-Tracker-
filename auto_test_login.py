"""
Автоматический тест логина в админ-панель.
"""
import time
import requests
import json

def test_login():
    url = "http://127.0.0.1:8000/api/v1/auth/login"
    data = {
        "email": "miroslavbabenko228@gmail.com",
        "password": "asacud"
    }
    
    print("🔄 Ожидание запуска сервера...")
    time.sleep(5)
    
    for attempt in range(5):
        try:
            print(f"\n📡 Попытка {attempt + 1}/5: Отправка запроса на {url}")
            response = requests.post(url, json=data, timeout=10)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ ===== УСПЕШНЫЙ ВХОД! =====")
                print(f"✓ Email: {data['email']}")
                print(f"✓ Access Token: {result.get('access_token', '')[:50]}...")
                print(f"✓ Token Type: {result.get('token_type', 'bearer')}")
                
                # Проверяем доступ к админ-панели
                headers = {"Authorization": f"Bearer {result['access_token']}"}
                admin_response = requests.get("http://127.0.0.1:8000/api/v1/admin/stats", headers=headers, timeout=10)
                
                if admin_response.status_code == 200:
                    stats = admin_response.json()
                    print(f"\n📊 Статистика админ-панели:")
                    print(json.dumps(stats, indent=2, ensure_ascii=False))
                    print(f"\n🎉 ВСЕ РАБОТАЕТ! Админ-панель доступна!")
                else:
                    print(f"\n⚠️ Вход выполнен, но админ-панель недоступна: {admin_response.status_code}")
                
                return True
            else:
                print(f"❌ Ошибка входа: {response.json()}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"⏳ Сервер еще не готов, жду 3 секунды...")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(3)
    
    print("\n❌ Не удалось подключиться к серверу после 5 попыток")
    return False

if __name__ == "__main__":
    success = test_login()
    exit(0 if success else 1)
