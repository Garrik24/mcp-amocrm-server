# 🤖 Подключение AmoCRM к Claude Desktop

**Статус:** ✅ Сервер на Railway работает идеально!  
**URL сервера:** https://mcp-amocrm-server-production.up.railway.app

---

## 📋 Быстрая настройка (5 минут)

### Шаг 1: Откройте конфигурацию Claude Desktop

**На macOS:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Или откройте файл вручную:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

---

### Шаг 2: Добавьте конфигурацию MCP сервера

Скопируйте и вставьте этот код в файл:

```json
{
  "mcpServers": {
    "amocrm-server": {
      "command": "/Users/makbuk/Desktop/gh mcp amocrm/mcp-amocrm-server/venv/bin/python",
      "args": [
        "/Users/makbuk/Desktop/gh mcp amocrm/mcp-amocrm-server/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/makbuk/Desktop/gh mcp amocrm/mcp-amocrm-server",
        "AMOCRM_SERVER_URL": "https://mcp-amocrm-server-production.up.railway.app",
        "AMO_SSL_VERIFY": "true"
      }
    }
  }
}
```

**ВАЖНО:** Путь `/Users/makbuk/Desktop/gh mcp amocrm/mcp-amocrm-server/` уже правильный для вашей системы!

---

### Шаг 3: Сохраните файл и перезапустите Claude Desktop

1. **Сохраните** файл (Cmd+S)
2. **Закройте Claude Desktop** полностью (Cmd+Q)
3. **Откройте Claude Desktop** снова

---

### Шаг 4: Проверьте подключение

После запуска Claude Desktop вы должны увидеть **иконку 🔧** в интерфейсе, что означает доступность MCP инструментов.

**Попробуйте команды:**

```
Получи информацию об аккаунте AmoCRM
```

```
Найди контакты в AmoCRM
```

```
Покажи список всех воронок продаж
```

```
Создай контакт с именем "Тест" и email test@example.com
```

---

## ✅ Что работает

### 🌐 **Railway сервер (Основной)**
- ✅ URL: https://mcp-amocrm-server-production.up.railway.app
- ✅ Токен: настроен и работает
- ✅ AmoCRM API: подключен
- ✅ Все endpoints: доступны

### 🤖 **MCP сервер (Для Claude)**
- ✅ 24 инструмента для работы с AmoCRM
- ✅ Умные операции (проверка дубликатов)
- ✅ Автоматическое создание связей

---

## 🎯 Доступные команды (24 инструмента)

### 👥 Контакты (8 команд)
- `search_contact` - Поиск контакта
- `get_contacts` - Список контактов
- `create_contact` - Создание контакта
- `update_contact` - Обновление контакта
- `check_contact_exists` - Проверка существования
- `get_or_create_contact` - Получить или создать

### 💼 Сделки (7 команд)
- `get_leads` - Список сделок
- `create_lead` - Создание сделки
- `create_complex_lead` - Создание сделки + контакт
- `update_lead` - Обновление сделки
- `delete_lead` - Удаление сделки
- `get_leads_by_contact` - Сделки контакта

### 🏢 Компании (2 команды)
- `get_companies` - Список компаний
- `create_company` - Создание компании

### ✅ Задачи (1 команда)
- `create_task` - Создание задачи

### ⚙️ Настройки (3 команды)
- `get_account_info` - Информация об аккаунте
- `get_pipelines` - Воронки продаж
- `get_users` - Пользователи

### 🧠 Умные операции (2 команды)
- `smart_create_client_and_lead` - Полный цикл создания
- `get_or_create_contact` - Умное создание контакта

### 📊 Отчеты (1 команда)
- `get_deals_report` - Отчет по сделкам

---

## 🔍 Примеры использования

### Пример 1: Поиск клиента
```
Найди контакт с телефоном +79887634034
```

### Пример 2: Создание сделки
```
Создай сделку "Межевание участка" на сумму 50000 рублей
```

### Пример 3: Умное создание
```
Проверь есть ли контакт с email test@mail.ru, если нет - создай с именем "Иван Петров", затем создай для него сделку "Консультация" на 30000 рублей
```

### Пример 4: Получение отчета
```
Покажи все сделки созданные за последний месяц в воронке КАДАСТР
```

---

## 🔧 Устранение проблем

### Проблема: MCP сервер не подключается

**Решение:**
1. Проверьте пути в `claude_desktop_config.json`
2. Убедитесь что виртуальное окружение активно
3. Проверьте логи Claude: `~/Library/Logs/Claude/mcp*.log`

### Проблема: Ошибка "Cannot find module"

**Решение:**
Установите зависимости:
```bash
cd "/Users/makbuk/Desktop/gh mcp amocrm/mcp-amocrm-server"
source venv/bin/activate
pip install -r requirements.txt
```

### Проблема: Railway сервер недоступен

**Решение:**
Проверьте статус на https://railway.app - возможно сервер спит (Railway переводит в сон неактивные сервисы).

---

## 📊 Архитектура решения

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ MCP Protocol
         ↓
┌─────────────────┐
│  mcp_server.py  │ ← Работает локально
│   (Local MCP)   │
└────────┬────────┘
         │ HTTP/REST API
         ↓
┌──────────────────────────────────┐
│  Railway Server (FastAPI)        │
│  mcp-amocrm-server-production    │ ← Работает в облаке
└────────┬─────────────────────────┘
         │ AmoCRM API v4
         ↓
┌─────────────────┐
│  AmoCRM         │
│  stavgeo26      │
└─────────────────┘
```

### Преимущества этой архитектуры:

✅ **Не нужно запускать локальный FastAPI сервер**  
✅ **Railway работает 24/7**  
✅ **Один токен на всех клиентов**  
✅ **Легко масштабировать**  
✅ **Работает из любой точки мира**

---

## 📝 Что НЕ нужно делать

❌ **Не запускайте** `uvicorn app:app` локально  
❌ **Не нужно** держать локальный FastAPI сервер  
❌ **Не меняйте** токен в Railway (он уже настроен)

---

## ✅ Финальный чеклист

- [x] Railway сервер работает
- [x] Токен AmoCRM настроен
- [x] .env файл обновлен
- [x] Виртуальное окружение готово
- [ ] Конфигурация добавлена в Claude Desktop
- [ ] Claude Desktop перезапущен
- [ ] Протестированы команды

---

## 🎉 Готово!

После выполнения всех шагов вы сможете работать с AmoCRM прямо из Claude Desktop!

**Попробуйте сказать Claude:**
> "Покажи мне информацию об аккаунте AmoCRM"

И Claude автоматически использует MCP инструменты для получения данных! 🚀

---

**Вопросы?** Проверьте логи:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```


