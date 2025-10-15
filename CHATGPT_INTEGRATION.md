# 🤖 Подключение AmoCRM сервера к ChatGPT

Пошаговая инструкция по интеграции AmoCRM MCP Server с ChatGPT через Custom GPT Actions.

---

## 📋 Что нужно для подключения

- ✅ Аккаунт ChatGPT Plus или Enterprise
- ✅ Запущенный AmoCRM сервер (локально или на Railway)
- ✅ Публичный URL сервера (для продакшена)

---

## 🚀 СПОСОБ 1: Автоматический импорт (Рекомендуется)

### Шаг 1: Запустите сервер на публичном URL

Если сервер запущен локально, вам нужен публичный URL. Варианты:

**Вариант А: Railway (рекомендуется)**
```bash
# Задеплойте на Railway (см. README.md)
# Получите URL вида: https://your-app.up.railway.app
```

**Вариант Б: ngrok (для тестирования)**
```bash
# Установите ngrok: https://ngrok.com/download
ngrok http 8000

# Получите временный URL вида: https://xxxx-xx-xx-xx-xx.ngrok-free.app
```

### Шаг 2: Создайте Custom GPT

1. Зайдите в ChatGPT
2. Нажмите на ваше имя → **My GPTs**
3. Нажмите **Create a GPT**
4. Переключитесь на вкладку **Configure**

### Шаг 3: Настройте GPT

**Name (Название):**
```
AmoCRM Ассистент
```

**Description (Описание):**
```
Помощник для работы с AmoCRM: поиск клиентов, создание сделок, проверка контактов и умное создание клиентов с автоматическим связыванием сделок.
```

**Instructions (Инструкции):**
```
Ты - профессиональный помощник для работы с AmoCRM CRM системой. 

Твои возможности:
1. Поиск и проверка существования контактов по email или телефону
2. Создание новых контактов с полной информацией
3. Умное создание: проверка существования контакта → создание если нужно → создание сделки
4. Создание сделок и связывание их с контактами
5. Получение отчетов по сделкам
6. Получение информации об аккаунте, воронках и пользователях

Когда пользователь просит:
- "Найди контакт" → используй search_contacts
- "Проверь есть ли клиент" → используй check_contact_exists
- "Создай контакта и сделку" → используй smart_create_client_and_lead
- "Создай сделку" → используй create_lead_with_contact

ВАЖНО: Всегда спрашивай подтверждение перед созданием новых записей.
Показывай результаты работы в понятном формате.
Если контакт уже существует - предлагай создать сделку для него.
```

### Шаг 4: Добавьте Actions

Прокрутите вниз до секции **Actions** и нажмите **Create new action**

**Вариант А - Импорт по URL (проще):**

1. Нажмите **Import from URL**
2. Вставьте URL вашего OpenAPI schema:
   ```
   https://your-app.up.railway.app/openapi.json
   ```
3. Нажмите **Import**
4. ChatGPT автоматически настроит все endpoints!

**Вариант Б - Ручная настройка (если импорт не работает):**

См. ниже "СПОСОБ 2: Ручная настройка"

### Шаг 5: Настройте Authentication (опционально)

Если ваш сервер требует авторизацию:

1. В секции **Authentication** выберите **API Key**
2. **API Key**: `Bearer your_token_here`
3. **Auth Type**: `Bearer`

Для нашего сервера авторизация **не требуется** (токен AmoCRM настроен в .env)

### Шаг 6: Сохраните и протестируйте

1. Нажмите **Save** в правом верхнем углу
2. Выберите **Only me** или **Anyone with a link**
3. Нажмите **Save**

---

## 🛠️ СПОСОБ 2: Ручная настройка Schema

Если автоматический импорт не работает, используйте ручную схему:

### Минимальная Schema для ChatGPT:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "AmoCRM MCP Server",
    "version": "3.0.0",
    "description": "API для работы с AmoCRM"
  },
  "servers": [
    {
      "url": "https://your-app.up.railway.app"
    }
  ],
  "paths": {
    "/api/contacts/search": {
      "get": {
        "summary": "Поиск контактов",
        "operationId": "search_contacts",
        "parameters": [
          {
            "name": "query",
            "in": "query",
            "required": true,
            "schema": {"type": "string"},
            "description": "Email, телефон или имя для поиска"
          },
          {
            "name": "limit",
            "in": "query",
            "schema": {"type": "integer", "default": 10},
            "description": "Количество результатов"
          }
        ],
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    },
    "/api/contacts/check-exists": {
      "post": {
        "summary": "Проверить существование контакта",
        "operationId": "check_contact_exists",
        "parameters": [
          {
            "name": "query",
            "in": "query",
            "required": true,
            "schema": {"type": "string"},
            "description": "Email или телефон"
          }
        ],
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    },
    "/api/contacts/get-or-create": {
      "post": {
        "summary": "Получить или создать контакт",
        "operationId": "get_or_create_contact",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "query": {"type": "string", "description": "Email или телефон"},
                  "name": {"type": "string", "description": "Имя контакта"},
                  "email": {"type": "string", "description": "Email"},
                  "phone": {"type": "string", "description": "Телефон"}
                },
                "required": ["query", "name"]
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    },
    "/api/leads/create-with-contact": {
      "post": {
        "summary": "Создать сделку с контактом",
        "operationId": "create_lead_with_contact",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "lead_name": {"type": "string"},
                  "lead_price": {"type": "number"},
                  "contact_id": {"type": "integer"},
                  "contact_name": {"type": "string"},
                  "contact_email": {"type": "string"},
                  "contact_phone": {"type": "string"}
                },
                "required": ["lead_name"]
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    },
    "/api/smart/client-and-lead": {
      "post": {
        "summary": "Умное создание клиента и сделки (полный цикл)",
        "operationId": "smart_create_client_and_lead",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "contact_query": {"type": "string", "description": "Email или телефон для поиска"},
                  "contact_name": {"type": "string", "description": "Имя контакта"},
                  "contact_email": {"type": "string"},
                  "contact_phone": {"type": "string"},
                  "lead_name": {"type": "string", "description": "Название сделки"},
                  "lead_price": {"type": "number", "description": "Бюджет сделки"},
                  "check_existing_leads": {"type": "boolean", "default": true}
                },
                "required": ["contact_query", "contact_name", "lead_name"]
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    },
    "/api/account": {
      "get": {
        "summary": "Информация об аккаунте AmoCRM",
        "operationId": "get_account_info",
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    },
    "/api/pipelines": {
      "get": {
        "summary": "Получить воронки продаж",
        "operationId": "get_pipelines",
        "responses": {
          "200": {"description": "Успешно"}
        }
      }
    }
  }
}
```

**Как использовать эту схему:**

1. Скопируйте весь JSON выше
2. Замените `https://your-app.up.railway.app` на ваш реальный URL
3. В Custom GPT Actions нажмите **Import from URL** → **Manual**
4. Вставьте схему в поле **Schema**
5. Нажмите **Save**

---

## 🧪 Тестирование ChatGPT интеграции

После настройки протестируйте следующие команды:

### Тест 1: Проверка статуса
```
Получи информацию об аккаунте AmoCRM
```

### Тест 2: Поиск контакта
```
Найди контакт с email test@example.com
```

### Тест 3: Проверка существования
```
Проверь есть ли контакт с телефоном +79991234567
```

### Тест 4: Умное создание
```
Проверь есть ли клиент ivan@test.ru, если нет - создай с именем "Иван Петров", 
затем создай для него сделку "Консультация" на 50000 рублей
```

### Тест 5: Создание сделки
```
Создай сделку "Новая продажа" на 100000 рублей для контакта с ID 123456
```

---

## 🔧 Настройка для локальной разработки

Для тестирования локально используйте **ngrok**:

### Установка ngrok:

1. Скачайте с https://ngrok.com/download
2. Установите:
   ```bash
   # macOS
   brew install ngrok/ngrok/ngrok
   
   # Или скачайте и распакуйте
   ```

3. Аутентифицируйтесь (получите токен на ngrok.com):
   ```bash
   ngrok authtoken YOUR_TOKEN
   ```

### Запуск:

```bash
# В одном терминале - запустите сервер
cd mcp-amocrm-server
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000

# В другом терминале - запустите ngrok
ngrok http 8000
```

Скопируйте URL из ngrok (например, `https://xxxx.ngrok-free.app`) и используйте в Custom GPT.

**⚠️ Важно:** ngrok URL временный и меняется при каждом перезапуске!

---

## 📱 Примеры использования в ChatGPT

### Пример 1: Полный цикл работы
```
Пользователь: Найди клиента по email client@company.ru, 
если не найден - создай с именем "Иван Сидоров" и телефоном +79991234567. 
Затем создай для него сделку "Продажа CRM" на 200000 рублей.

ChatGPT: 
✅ Проверяю контакт client@company.ru...
✅ Контакт не найден, создаю нового...
✅ Контакт создан (ID: 987654)
✅ Создаю сделку "Продажа CRM"...
✅ Сделка создана (ID: 567890)
✅ Всё готово! Контакт и сделка связаны.
```

### Пример 2: Поиск и анализ
```
Пользователь: Найди всех клиентов с email содержащим @gmail.com

ChatGPT: Ищу контакты...
Найдено 5 контактов:
1. Иван Петров - ivan@gmail.com
2. Мария Сидорова - maria@gmail.com
...
```

---

## 🎯 Рекомендации по настройке GPT

### Conversation starters (Примеры команд):

Добавьте эти фразы как быстрые кнопки в вашем GPT:

```
"Найди контакт по email"
"Проверь существует ли клиент"
"Создай контакта и сделку"
"Покажи информацию об аккаунте"
```

### Capabilities (Возможности):

- ☑️ Web Browsing - **ВЫКЛ**
- ☑️ DALL-E Image Generation - **ВЫКЛ**
- ☑️ Code Interpreter - **ВКЛ** (для обработки JSON)

---

## 🔐 Безопасность

### Для Production:

1. **Используйте HTTPS** (Railway автоматически предоставляет)
2. **Добавьте API ключ** в FastAPI:
   ```python
   # В app.py добавьте проверку токена
   @app.middleware("http")
   async def verify_api_key(request: Request, call_next):
       api_key = request.headers.get("X-API-Key")
       if api_key != os.getenv("API_KEY"):
           return JSONResponse({"error": "Invalid API key"}, status_code=401)
       return await call_next(request)
   ```

3. **Настройте в ChatGPT Authentication**:
   - Type: **API Key**
   - Header name: `X-API-Key`
   - Value: ваш секретный ключ

---

## 🐛 Решение проблем

### Проблема: "Failed to fetch schema"

**Решение:**
- Проверьте что сервер доступен по URL
- Убедитесь что `/openapi.json` возвращает JSON
- Попробуйте ручную схему (см. выше)

### Проблема: "Action failed"

**Решение:**
- Проверьте логи сервера
- Убедитесь что токен AmoCRM настроен в `.env`
- Проверьте формат запроса в ChatGPT

### Проблема: ngrok требует подтверждение

**Решение:**
Добавьте в `.env`:
```
NGROK_SKIP_BROWSER_WARNING=true
```

---

## 📊 Сравнение: ChatGPT vs Claude Desktop

| Параметр | ChatGPT (Custom GPT) | Claude Desktop (MCP) |
|----------|---------------------|----------------------|
| Протокол | REST API | Model Context Protocol |
| Настройка | Web интерфейс | JSON конфиг файл |
| Доступность | Нужен Plus/Enterprise | Бесплатно с Claude |
| Публичный URL | Требуется | Не требуется (работает локально) |
| Инструментов | Ограничено schema | Все 24 инструмента |
| Простота | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Гибкость | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## ✅ Чеклист готовности

- [ ] Сервер задеплоен на Railway или запущен с ngrok
- [ ] Получен публичный URL
- [ ] Создан Custom GPT в ChatGPT
- [ ] Настроены Actions (импорт или ручная схема)
- [ ] Протестированы основные команды
- [ ] Настроена аутентификация (если нужно)

---

## 🎉 Готово!

Теперь ваш AmoCRM сервер подключен к ChatGPT! 

Можете использовать все умные функции прямо в чате:
- ✅ Поиск клиентов
- ✅ Проверка существования
- ✅ Автоматическое создание
- ✅ Умное связывание сделок

**Следующий шаг:** Протестируйте полный цикл работы с клиентом!

---

**Дополнительная помощь:**
- 📖 Полная документация: см. README.md
- 🚀 Быстрый старт: см. QUICKSTART.md
- 🧪 Отчет о тестировании: см. TEST_REPORT.md

