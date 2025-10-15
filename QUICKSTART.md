# 🚀 Быстрый старт - AmoCRM MCP Server

## 📋 Что было создано

Полнофункциональный MCP сервер для AmoCRM с:
- ✅ **24 MCP инструмента** для Claude Desktop
- ✅ **4 умных endpoint'а** для автоматизации
- ✅ **Полная документация** на русском языке

---

## ⚡ Запуск за 3 минуты

### 1️⃣ Установка зависимостей

```bash
cd mcp-amocrm-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Настройка .env

Создайте файл `.env`:

```bash
cp env.example .env
```

Заполните **обязательные** параметры:

```env
AMOCRM_SUBDOMAIN=your_subdomain
AMOCRM_ACCESS_TOKEN=your_token
AMOCRM_SERVER_URL=http://localhost:8000
```

### 3️⃣ Запуск сервера

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Откройте: http://localhost:8000/docs

---

## 🤖 Подключение к Claude Desktop

### Найдите конфиг Claude:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Добавьте в файл:

```json
{
  "mcpServers": {
    "amocrm-server": {
      "command": "/полный/путь/к/mcp-amocrm-server/venv/bin/python",
      "args": ["/полный/путь/к/mcp-amocrm-server/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/полный/путь/к/mcp-amocrm-server",
        "AMOCRM_SERVER_URL": "http://localhost:8000",
        "AMO_SSL_VERIFY": "true"
      }
    }
  }
}
```

**Замените `/полный/путь/к/` на реальный путь!**

Узнать путь:
```bash
pwd
# Результат: /Users/makbuk/Desktop/gh mcp amocrm/mcp-amocrm-server
```

### Перезапустите Claude Desktop

---

## 🧪 Тестирование

### Проверка API:

```bash
curl http://localhost:8000
```

### Проверка в Claude:

Попросите Claude:
```
"Получи информацию об аккаунте AmoCRM"
"Найди контакт с email test@example.com"
"Создай сделку 'Тест' на 10000 рублей"
```

---

## 🎯 Основные возможности

### 🧠 Умные операции

**1. Проверка + Создание контакта:**
```
"Проверь есть ли контакт ivan@test.ru, если нет - создай с именем Иван Петров"
```

**2. Полный цикл (контакт + сделка):**
```
"Найди контакт с телефоном +79991234567, если не найден - создай. 
Затем проверь есть ли у него сделки, если нет - создай сделку 'Новая продажа' на 50000"
```

**3. Поиск и анализ:**
```
"Найди все сделки созданные за последние 7 дней"
"Покажи всех контактов с email содержащим @gmail.com"
```

---

## 📡 REST API примеры

### Умное создание клиента и сделки:

```bash
curl -X POST http://localhost:8000/api/smart/client-and-lead \
  -H "Content-Type: application/json" \
  -d '{
    "contact_query": "test@example.com",
    "contact_name": "Тестовый клиент",
    "contact_email": "test@example.com",
    "contact_phone": "+79991234567",
    "lead_name": "Новая продажа",
    "lead_price": 50000,
    "check_existing_leads": true
  }'
```

### Проверка существования контакта:

```bash
curl -X POST "http://localhost:8000/api/contacts/check-exists?query=test@example.com"
```

---

## 🔑 Где взять токен AmoCRM?

1. Зайдите в **AmoCRM** → **Настройки** → **Интеграции**
2. Создайте **новую интеграцию**
3. Настройте **права доступа** (контакты, сделки, задачи)
4. Скопируйте **Долгосрочный токен доступа**
5. Вставьте в `.env` файл

---

## 🐛 Проблемы?

### MCP не подключается:
- Проверьте путь в конфиге Claude
- Убедитесь что сервер запущен на порту 8000
- Посмотрите логи: `~/Library/Logs/Claude/mcp*.log`

### 401 Unauthorized:
- Проверьте токен в `.env`
- Убедитесь что токен не истек

### SSL ошибки:
Измените в конфиге Claude:
```json
"AMO_SSL_VERIFY": "false"
```

---

## 📚 Полная документация

См. **README.md** для подробной информации о всех 24 инструментах и расширенных настройках.

---

## ✅ Чеклист готовности

- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Создан файл `.env` с токеном
- [ ] Запущен FastAPI сервер (порт 8000)
- [ ] Обновлен конфиг Claude Desktop
- [ ] Перезапущен Claude Desktop
- [ ] Протестированы команды в Claude

---

**Готово! Теперь можете использовать AmoCRM через Claude!** 🎉

