# AmoCRM MCP Server 🚀

Полнофункциональный интеграционный сервер для AmoCRM с поддержкой **Model Context Protocol (MCP)**. Позволяет подключить AmoCRM к AI-ассистентам (Claude, ChatGPT и другим) для автоматизации работы с контактами, сделками, компаниями и задачами.

## 🎯 Основные возможности

### ✨ Умные операции
- ✅ **Автоматическая проверка** существования контактов по email/телефону
- ✅ **Создание контакта если не существует** с автоматическим заполнением полей
- ✅ **Проверка наличия сделок** у контакта перед созданием новой
- ✅ **Комплексное создание** "контакт + сделка" одной операцией
- ✅ **Полный цикл работы** с клиентом: поиск → создание → связывание → сделка

### 🔧 Базовые операции
- **Контакты**: поиск, создание, обновление, удаление
- **Сделки**: создание, обновление, фильтрация, отчеты
- **Компании**: создание, поиск, связывание с контактами
- **Задачи**: создание, привязка к сделкам/контактам
- **Отчеты**: сделки с фильтрами по датам, статусам, воронкам

### 🤖 Интеграции
- **Claude Desktop** через MCP (24 инструмента)
- **ChatGPT** через Custom GPT Actions
- **REST API** для любых приложений

---

## 📋 Список всех MCP инструментов (24 команды)

### 👥 Контакты (8 команд)
1. `search_contact` - Поиск контакта по email/телефону
2. `get_contacts` - Получить список контактов
3. `get_contact_by_id` - Получить контакт по ID
4. `create_contact` - Создать новый контакт
5. `update_contact` - Обновить контакт
6. `check_contact_exists` - Проверить существование контакта
7. `get_or_create_contact` - Получить или создать контакт
8. (delete через универсальный endpoint)

### 💼 Сделки (7 команд)
9. `get_leads` - Получить список сделок
10. `get_lead_by_id` - Получить сделку по ID
11. `create_lead` - Создать сделку
12. `create_complex_lead` - Создать сделку + контакт
13. `update_lead` - Обновить сделку
14. `delete_lead` - Удалить сделку
15. `get_leads_by_contact` - Получить сделки контакта

### 🏢 Компании (2 команды)
16. `get_companies` - Получить список компаний
17. `create_company` - Создать компанию

### ✅ Задачи (1 команда)
18. `create_task` - Создать задачу

### ⚙️ Настройки (3 команды)
19. `get_account_info` - Информация об аккаунте
20. `get_pipelines` - Получить воронки
21. `get_users` - Получить пользователей

### 🧠 Умные операции (2 команды)
22. `smart_create_client_and_lead` - Полный цикл создания
23. `get_or_create_contact` - Получить или создать

### 📊 Отчеты (1 команда)
24. `get_deals_report` - Отчет по сделкам

---

## 🚀 Быстрый старт

### Шаг 1: Установка

```bash
# Клонируем репозиторий
git clone https://github.com/Garrik24/mcp-amocrm-server.git
cd mcp-amocrm-server

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

### Шаг 2: Настройка переменных окружения

Создайте файл `.env` на основе `env.example`:

```bash
cp env.example .env
```

Заполните обязательные параметры в `.env`:

```env
# Ваш поддомен AmoCRM
AMOCRM_SUBDOMAIN=mycompany

# Долгосрочный токен доступа
AMOCRM_ACCESS_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...

# URL сервера (для MCP)
AMOCRM_SERVER_URL=http://localhost:8000
AMO_SSL_VERIFY=true
```

### Шаг 3: Запуск сервера

```bash
# Запуск FastAPI сервера
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Проверка работы:
```bash
curl http://localhost:8000
```

Документация API: http://localhost:8000/docs

---

## 🔌 Подключение к Claude Desktop

### 1. Найдите файл конфигурации Claude

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

### 2. Добавьте конфигурацию MCP сервера

Откройте файл и добавьте (или создайте) секцию `mcpServers`:

```json
{
  "mcpServers": {
    "amocrm-server": {
      "command": "/Users/YOUR_USERNAME/path/to/mcp-amocrm-server/venv/bin/python",
      "args": ["/Users/YOUR_USERNAME/path/to/mcp-amocrm-server/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/YOUR_USERNAME/path/to/mcp-amocrm-server",
        "AMOCRM_SERVER_URL": "http://localhost:8000",
        "AMO_SSL_VERIFY": "true"
      }
    }
  }
}
```

**Важно:** Замените `/Users/YOUR_USERNAME/path/to/` на реальный путь к проекту!

### 3. Перезапустите Claude Desktop

После перезапуска Claude, MCP инструменты AmoCRM будут доступны. Проверьте, увидев иконку 🔧 в интерфейсе Claude.

### 4. Примеры команд для Claude

Попробуйте задать Claude эти команды:

```
"Найди контакт с email test@example.com"
"Создай контакт Иван Петров с email ivan@test.ru"
"Получи список всех сделок"
"Создай сделку 'Новая продажа' на 50000 рублей"
"Проверь есть ли контакт с телефоном +79991234567, если нет - создай с именем 'Новый клиент', затем создай для него сделку"
```

---

## 📡 REST API Endpoints

### Базовые endpoints

```http
GET  /                          # Статус сервера
GET  /health                    # Health check
GET  /docs                      # Swagger документация
POST /api/entities              # Универсальный endpoint для всех сущностей
```

### Новые умные endpoints

```http
# Поиск контактов
GET  /api/contacts/search?query=email@test.com

# Проверка существования
POST /api/contacts/check-exists?query=+79991234567

# Получить или создать
POST /api/contacts/get-or-create
Body: {
  "query": "email@test.com",
  "name": "Иван Петров",
  "email": "email@test.com",
  "phone": "+79991234567"
}

# Создать сделку с контактом
POST /api/leads/create-with-contact
Body: {
  "lead_name": "Новая сделка",
  "lead_price": 50000,
  "contact_id": 123456  // или создаст новый контакт
}

# Умное создание (полный цикл)
POST /api/smart/client-and-lead
Body: {
  "contact_query": "email@test.com",
  "contact_name": "Иван Петров",
  "contact_email": "email@test.com",
  "lead_name": "Новая продажа",
  "lead_price": 100000
}
```

### Примеры запросов

**Проверить существование контакта:**
```bash
curl -X POST "http://localhost:8000/api/contacts/check-exists?query=test@example.com"
```

**Умное создание клиента и сделки:**
```bash
curl -X POST "http://localhost:8000/api/smart/client-and-lead" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_query": "ivan@test.ru",
    "contact_name": "Иван Петров",
    "contact_email": "ivan@test.ru",
    "contact_phone": "+79991234567",
    "lead_name": "Новая продажа",
    "lead_price": 50000,
    "check_existing_leads": true
  }'
```

---

## 🌐 Деплой на Railway

### 1. Подключение к Railway

1. Зайдите на [railway.app](https://railway.app)
2. Создайте новый проект
3. Подключите GitHub репозиторий

### 2. Настройка переменных окружения

В Railway → Project → Variables добавьте:

```
AMOCRM_SUBDOMAIN=your_subdomain
AMOCRM_ACCESS_TOKEN=your_token
```

### 3. Автоматический деплой

Railway автоматически обнаружит:
- `requirements.txt` - для установки зависимостей
- `Procfile` - для запуска приложения
- `runtime.txt` - для версии Python

### 4. Получение домена

1. Settings → Networking → Generate Domain
2. Скопируйте URL (например, `https://your-app.up.railway.app`)
3. Обновите `AMOCRM_SERVER_URL` в конфиге Claude Desktop

---

## 🔐 Получение токена AmoCRM

### Способ 1: Интеграция (рекомендуется)

1. Зайдите в AmoCRM → Настройки → Интеграции
2. Создайте новую интеграцию
3. Настройте права доступа
4. Получите **Долгосрочный токен** (Long-lived Access Token)

### Способ 2: OAuth (для продакшена)

1. Создайте OAuth приложение в AmoCRM
2. Получите `client_id` и `client_secret`
3. Реализуйте OAuth flow (код для этого есть в проекте)

---

## 🎓 Примеры использования

### Пример 1: Проверка и создание контакта

```python
# Через MCP в Claude:
"Проверь есть ли контакт с email client@company.com, если нет - создай с именем 'Иван Петров'"
```

### Пример 2: Создание сделки для существующего клиента

```python
# Через API:
POST /api/leads/create-with-contact
{
  "lead_name": "Продажа сервиса",
  "lead_price": 150000,
  "contact_id": 123456
}
```

### Пример 3: Полный цикл работы

```python
# Через MCP в Claude:
"Найди клиента с телефоном +79991234567, если не найден - создай с именем 'Новый клиент'. Затем проверь есть ли у него открытые сделки. Если нет - создай сделку 'Консультация' на 50000 рублей"
```

Это выполнит автоматически:
1. ✅ Поиск контакта
2. ✅ Создание если не найден
3. ✅ Проверка сделок
4. ✅ Создание сделки если нужно

---

## 🛠️ Troubleshooting

### Проблема: MCP сервер не подключается

**Решение:**
1. Проверьте пути в `claude_desktop_config.json`
2. Убедитесь что FastAPI сервер запущен (`http://localhost:8000`)
3. Проверьте логи Claude: `~/Library/Logs/Claude/mcp*.log`

### Проблема: SSL ошибки

**Решение:**
Временно отключите проверку SSL:
```json
"env": {
  "AMO_SSL_VERIFY": "false"
}
```

### Проблема: 401 Unauthorized

**Решение:**
1. Проверьте токен в `.env`
2. Убедитесь что токен не истек
3. Проверьте права доступа интеграции в AmoCRM

### Проблема: 404 Not Found

**Решение:**
Проверьте правильность поддомена в `AMOCRM_SUBDOMAIN`

---

## 📚 Документация AmoCRM API

- [Официальная документация](https://www.amocrm.ru/developers/content/crm_platform/)
- [API v4 Reference](https://www.amocrm.ru/developers/content/crm_platform/leads-api)
- [OAuth авторизация](https://www.amocrm.ru/developers/content/oauth/step-by-step)

---

## 🤝 Вклад в проект

Приветствуются Pull Requests! Если нашли баг или хотите добавить функционал:

1. Fork проекта
2. Создайте ветку (`git checkout -b feature/AmazingFeature`)
3. Commit изменений (`git commit -m 'Add some AmazingFeature'`)
4. Push в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📝 Лицензия

MIT License - используйте свободно для любых целей.

---

## 👨‍💻 Автор

**Garrik24** - [GitHub](https://github.com/Garrik24)

---

## ⭐ Поддержите проект

Если проект оказался полезен - поставьте ⭐ на GitHub!

---

## 📞 Поддержка

Возникли вопросы? Создайте [Issue](https://github.com/Garrik24/mcp-amocrm-server/issues) на GitHub.

---

**Версия:** 3.0.0  
**Обновлено:** Октябрь 2025
