# AmoCRM MCP Server

Интеграционный сервер для AmoCRM на базе FastAPI. Поддерживает универсальные операции с сущностями (leads/contacts/companies), отчёты, вебхуки, а также два типа подключений к ИИ:

- Claude Desktop (MCP — Model Context Protocol)
- ChatGPT (Custom GPT Actions / OpenAPI)

## Возможности

- Универсальный эндпоинт работы с сущностями (`POST /api/entities`)
- Отчёты по сделкам с фильтрами дат (`GET /api/report/deals`)
- Прямой маршрут удаления сущности (`DELETE /api/entities/{entity_type}/{entity_id}`) + POST-обёртка
- Готовая OpenAPI-спецификация (`/openapi.json`, `/docs`)
- MCP-сервер для Claude Desktop (скрипт `mcp_server.py`)

---

## Требования

- Python 3.11+ (локально) / указана версия в `runtime.txt`
- pip

---

## Установка (локально)

```bash
git clone https://github.com/Garrik24/mcp-amocrm-server.git
cd mcp-amocrm-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Переменные окружения

Создайте файл `.env` (на основе `.env.example`) и заполните:

- `AMOCRM_SUBDOMAIN` — поддомен AmoCRM (например, `stavgeo26`)
- `AMOCRM_ACCESS_TOKEN` — долгосрочный токен (или реализуйте OAuth потоки)
- (опционально) `REDIRECT_URI`

Дополнительно для MCP/алиасов (опционально):

- `AMO_PIPELINE_ID` — дефолтная воронка
- `AMO_STATUS_ID` — дефолтный статус
- `AMO_RESPONSIBLE_ID` — дефолтный ответственный

### Запуск

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Проверка статуса:

```bash
curl -s http://127.0.0.1:8000 | jq
```

Документация API: `http://127.0.0.1:8000/docs`

---

## Основные эндпоинты

- `GET /` — статус сервера
- `GET /health` — healthcheck (200 OK)
- `POST /api/entities` — универсальная работа с сущностями
  - body пример (получить 10 сделок):
    ```json
    { "entity_type": "leads", "method": "get", "params": { "limit": 10 } }
    ```
  - body пример (создать сделку):
    ```json
    { "entity_type": "leads", "method": "post", "data": [{ "name": "Тест 10000", "price": 10000 }] }
    ```
- `GET /api/report/deals` — отчёт/фильтр по сделкам
  - параметры: `created_at_from`, `created_at_to`, `limit`, `pipeline_id`, `status_id`, `query`
- `DELETE /api/entities/{entity_type}/{entity_id}` — прямое удаление
- `POST /api/entities/{entity_type}/{entity_id}/delete` — POST-обёртка удаления

---

## MCP для Claude Desktop

1) Установите зависимости проекта (см. выше)
2) Убедитесь, что сервер доступен по HTTP(S). Для MCP укажите переменные в конфиге Claude:

Файл конфига macOS:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```
Пример секции:
```json
{
  "mcpServers": {
    "amocrm-server": {
      "command": "/Users/USERNAME/Projects/mcp-amocrm-server/venv/bin/python",
      "args": ["/Users/USERNAME/Projects/mcp-amocrm-server/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/USERNAME/Projects/mcp-amocrm-server",
        "AMOCRM_SERVER_URL": "https://YOUR-RAILWAY-DOMAIN.up.railway.app",
        "AMO_SSL_VERIFY": "true"
      }
    }
  }
}
```
3) Перезапустите Claude Desktop. Инструменты MCP: `get_leads_by_date`, `create_simple_lead`, `delete_lead`, `amocrm_request`.

> Примечание: для тестов можно временно выставить `AMO_SSL_VERIFY=false`.

---

## ChatGPT (Custom GPT Actions)

Вариант A — импорт по URL:

- Actions → Import from URL → `https://YOUR-RAILWAY-DOMAIN.up.railway.app/openapi.json`

Вариант B — вручную (минимальная схема):

- См. файл `chatgpt_railway_schema.json` в репозитории. Вставьте в поле Schema и замените URL на свой домен Railway.

Быстрые проверки:

- “Покажи статус AmoCRM сервера”
- “Получи 10 сделок”
- “Создай сделку ‘Тест 10000’ на 10000”

---

## Деплой на Railway

1) Подключите репозиторий GitHub к Railway
2) Переменные окружения (Project → Variables):
   - `AMOCRM_SUBDOMAIN`
   - `AMOCRM_ACCESS_TOKEN`
   - (опц.) `REDIRECT_URI`
3) Файлы для автосборки: `requirements.txt`, `Procfile`, `runtime.txt`
4) Домен: Settings → Domains → Generate Domain

---

## Troubleshooting

- 405 на `HEAD /` в ChatGPT: используйте `GET /health` как проверочный маршрут
- SSL ошибки в MCP: временно `AMO_SSL_VERIFY=false`, затем вернуть `true`
- Невидимые символы в Python (U+00A0): перезагрузите файл, убедитесь, что используются обычные пробелы
- AmoCRM требует массив при `POST`: в сервере нормализуется `data` в массив автоматически
- Удаление: если 405/403 — проверьте права токена, можно использовать POST-обёртку `/api/entities/{type}/{id}/delete`

---

## Лицензия

MIT
