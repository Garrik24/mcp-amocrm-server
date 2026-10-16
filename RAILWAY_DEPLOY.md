# 🚀 ПОШАГОВЫЙ ДЕПЛОЙ НА RAILWAY

## ✅ ВСЁ ГОТОВО ДЛЯ ДЕПЛОЯ!

GitHub обновлен с последними изменениями. Теперь деплоим на Railway:

## 📋 ШАГИ ДЛЯ ДЕПЛОЯ:

### ШАГ 1: Открой Railway.app
1. Перейди на [railway.app](https://railway.app)
2. Нажми **"Login"** (войти через GitHub)

### ШАГ 2: Создай новый проект
1. Нажми **"New Project"**
2. Выбери **"Deploy from GitHub repo"**
3. Найди и выбери репозиторий: **"Garrik24/mcp-amocrm-server"**

### ШАГ 3: Railway автоматически настроит деплой
Railway автоматически:
- Обнаружит Python проект
- Установит зависимости из `requirements.txt`
- Запустит сервер через `Procfile`

### ШАГ 4: Получи URL
После деплоя (2-3 минуты):
1. В панели Railway найди секцию **"Domains"**
2. Нажми **"Generate Domain"**
3. Получишь URL вида: `https://mcp-amocrm-server.up.railway.app`

### ШАГ 5: Настрой переменные окружения (опционально)
В разделе **"Variables"** добавь:
```
AMOCRM_CLIENT_ID=твой_client_id
AMOCRM_CLIENT_SECRET=твой_secret
AMOCRM_SUBDOMAIN=stavgeo26
AMOCRM_ACCESS_TOKEN=твой_токен
```

## 🤖 ПОСЛЕ ДЕПЛОЯ: Обнови ChatGPT

1. **Скопируй полученный URL Railway**
2. **В ChatGPT Actions замени Schema:**

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "AmoCRM GPT Assistant",
    "description": "API для интеграции AmoCRM с ChatGPT",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://твой-url.up.railway.app",
      "description": "AmoCRM сервер на Railway"
    }
  ],
  "paths": {
    "/": {
      "get": {
        "summary": "Статус сервера",
        "operationId": "get_server_status",
        "responses": {
          "200": {
            "description": "Статус сервера"
          }
        }
      }
    },
    "/api/entities": {
      "post": {
        "summary": "Работа с сущностями AmoCRM",
        "operationId": "manage_amocrm_entities",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "entity_type": {
                    "type": "string",
                    "enum": ["leads", "contacts", "companies"],
                    "description": "Тип сущности"
                  },
                  "method": {
                    "type": "string", 
                    "enum": ["get", "post"],
                    "description": "Метод операции"
                  },
                  "params": {
                    "type": "object",
                    "description": "Параметры"
                  }
                },
                "required": ["entity_type", "method"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Результат операции"
          }
        }
      }
    }
  }
}
```

## 🧪 ТЕСТИРОВАНИЕ

После настройки тестируй в ChatGPT:
- **"Покажи статус AmoCRM сервера"**
- **"Получи данные о сделках"**

## 🎯 ГОТОВО!

Твой AmoCRM сервер будет работать 24/7 на Railway с постоянным HTTPS URL!

