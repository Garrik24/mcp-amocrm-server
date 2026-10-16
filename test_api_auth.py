#!/usr/bin/env python3
"""
Тест middleware авторизации для REST API /api/* эндпоинтов.
"""
import os
import sys

# Устанавливаем тестовые переменные окружения
os.environ["AMOCRM_SUBDOMAIN"] = "test"
os.environ["AMOCRM_ACCESS_TOKEN"] = "test_token"
os.environ["MCP_PATH_SECRET"] = "test_secret"
os.environ["API_SECRET_KEY"] = "test_api_key_32chars_minimum_len"

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_endpoint_no_auth():
    """Health endpoint должен быть доступен без авторизации"""
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✅ /health доступен без авторизации")

def test_root_endpoint_no_auth():
    """Root endpoint должен быть доступен без авторизации"""
    response = client.get("/")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✅ / доступен без авторизации")

def test_webhook_endpoint_no_auth():
    """Webhook endpoint должен быть доступен без авторизации"""
    response = client.post("/webhooks/receive", data="test=data")
    # Может вернуть ошибку парсинга, но не 401
    assert response.status_code != 401, f"Webhook не должен требовать авторизацию"
    print("✅ /webhooks/receive доступен без авторизации")

def test_api_endpoint_no_auth():
    """API endpoint должен требовать авторизацию"""
    response = client.get("/api/account")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    data = response.json()
    assert "error" in data and data["error"] == "Unauthorized"
    print("✅ /api/account требует авторизацию (401 без токена)")

def test_api_endpoint_invalid_auth():
    """API endpoint должен отклонять неверный токен"""
    response = client.get("/api/account", headers={"Authorization": "Bearer wrong_token"})
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("✅ /api/account отклоняет неверный токен")

def test_api_endpoint_valid_bearer():
    """API endpoint должен принимать валидный Bearer token"""
    response = client.get("/api/account", headers={"Authorization": "Bearer test_api_key_32chars_minimum_len"})
    # Может вернуть ошибку от amoCRM, но не 401
    assert response.status_code != 401, f"Valid token rejected with {response.status_code}"
    print("✅ /api/account принимает валидный Bearer token")

def test_api_endpoint_valid_api_key():
    """API endpoint должен принимать валидный X-API-Key"""
    response = client.get("/api/account", headers={"X-API-Key": "test_api_key_32chars_minimum_len"})
    # Может вернуть ошибку от amoCRM, но не 401
    assert response.status_code != 401, f"Valid API key rejected with {response.status_code}"
    print("✅ /api/account принимает валидный X-API-Key")

def test_api_chat_endpoint_auth():
    """API /api/chat/* должен требовать авторизацию"""
    response = client.get("/api/chat/recent")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("✅ /api/chat/recent требует авторизацию")

def test_api_entities_post_auth():
    """POST /api/entities должен требовать авторизацию"""
    response = client.post("/api/entities", json={"entity_type": "leads", "method": "get"})
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("✅ POST /api/entities требует авторизацию")

def test_api_entities_delete_auth():
    """DELETE /api/entities должен требовать авторизацию"""
    response = client.delete("/api/entities/leads/123")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("✅ DELETE /api/entities/leads/123 требует авторизацию")

def test_no_api_key_fail_closed():
    """При отсутствии API_SECRET_KEY сервер должен отказывать (fail closed)"""
    # Сохраняем текущий ключ
    original_key = os.environ.get("API_SECRET_KEY")
    
    # Удаляем ключ
    if "API_SECRET_KEY" in os.environ:
        del os.environ["API_SECRET_KEY"]
    
    # Пересоздаём app (импорт обновит глобальную переменную)
    import importlib
    import app as app_module
    importlib.reload(app_module)
    
    test_client = TestClient(app_module.app)
    response = test_client.get("/api/account", headers={"Authorization": "Bearer any_token"})
    
    # Должен вернуть 503 (Service Unavailable), так как ключ не настроен
    assert response.status_code == 503, f"Expected 503 (fail closed), got {response.status_code}"
    data = response.json()
    assert "not configured" in data.get("detail", "").lower()
    print("✅ Без API_SECRET_KEY сервер отказывает (fail closed, 503)")
    
    # Восстанавливаем ключ
    if original_key:
        os.environ["API_SECRET_KEY"] = original_key

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование middleware авторизации REST API")
    print("=" * 60)
    
    tests = [
        test_health_endpoint_no_auth,
        test_root_endpoint_no_auth,
        test_webhook_endpoint_no_auth,
        test_api_endpoint_no_auth,
        test_api_endpoint_invalid_auth,
        test_api_endpoint_valid_bearer,
        test_api_endpoint_valid_api_key,
        test_api_chat_endpoint_auth,
        test_api_entities_post_auth,
        test_api_entities_delete_auth,
        test_no_api_key_fail_closed,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Неожиданная ошибка: {e}")
            failed += 1
    
    print("=" * 60)
    if failed == 0:
        print("✅ Все тесты пройдены!")
        sys.exit(0)
    else:
        print(f"❌ Провалено тестов: {failed}/{len(tests)}")
        sys.exit(1)
